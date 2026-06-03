# Pitfalls Research — v1.3.0 Backup & Restore

**Domain:** Cold-quiesce backup + restore for 4 stateful Telemetron roles on Docker via Ansible
**Researched:** 2026-06-02
**Confidence:** HIGH for Garage LMDB, Prometheus TSDB lock/WAL, Grafana SQLite WAL default,
Alertmanager protobuf snapshot, and `state: stopped` community.docker defect. MEDIUM for
Prometheus sparse-file behavior (no definitive upstream source found; LOW risk in practice at
homelab scale). LOW for Prometheus clean-SIGTERM WAL-flush guarantee (upstream docs ambiguous;
behavioral evidence is HIGH but no explicit contract in official docs).

This file covers **backup/restore-specific pitfalls only**. For prior-milestone pitfalls
(Garage migration, MinIO, Mimir retention, OTel label split), see
`.planning/research/v1.1.0/PITFALLS.md`.

---

## Component Pitfalls: Garage v2.3.0

### GP-1 (CRITICAL): LMDB cold-copy is safe only when Garage is fully stopped — no filesystem snapshot shortcut

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** NO — detectable from official docs; static-verifiable
**What goes wrong:**
The Garage docs explicitly warn: "filesystem-level snapshots of your metadata_dir, although
much faster, do not ensure the snapshot will be consistent. If the snapshot is taken during a
metadata write, the snapshot itself might be corrupted and thus not usable as a rollback
point." LMDB's `db.lmdb/` directory (containing `data.mdb` + `lock.mdb`) is an active
write-ahead log environment. Tarring it while Garage is running produces a silently corrupted
backup that appears complete but will fail on restore with an LMDB environment error.

**Prevention:**
The backup task MUST stop the Garage container (send SIGTERM, wait for `State.Running == false`)
before tarring `telemetron_garage_meta` volume contents. This is the one place in the stack
where the cold-quiesce model is not just a convenience — it is required for correctness.
After Garage stops cleanly, `db.lmdb/data.mdb` is safe to tar. The `lock.mdb` file is
small (8 KB) and gets recreated on next Garage startup; it is safe to include in the tar
(harmless) or exclude (slightly cleaner). Including it is the simpler policy.

**Garage's own snapshot alternative (not used in v1.3.0):**
`metadata_auto_snapshot_interval` in `garage.toml` causes Garage to write clean snapshots
under `<metadata_dir>/snapshots/` at regular intervals. These are safe to copy even while
Garage is running. Telemetron v1.3.0 uses the cold-quiesce model instead (per locked design
decision), but the restore task should verify the backup came from a stopped-Garage state
(i.e. that the tarball includes `db.lmdb/data.mdb` and not partial write frames). No
in-tar verification is practical — the cold-quiesce gate is the only real guard.

**Detection:**
- Restore fails with: `LMDB: MDB_CORRUPTED: Located page was wrong type` or
  `LMDB: MDB_PAGE_NOTFOUND` on Garage container start post-restore.
- Garage logs `db error: LMDB: ...` in first seconds after start.

**Source:** [Garage HQ recovering from failures](https://garagehq.deuxfleurs.fr/documentation/operations/recovering/)
— "filesystem-level snapshots ... may also be corrupted" — HIGH confidence.

---

### GP-2 (CRITICAL): LMDB volume contains `db.lmdb/`, `snapshots/` (if configured), plus layout state — all in meta volume

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** YES — tar path selection is only verified by running restore
**What goes wrong:**
The Garage metadata Docker volume (`telemetron_garage_meta`, mounted at
`/var/lib/garage/meta/`) contains everything Garage needs to reconstruct its cluster identity:
- `db.lmdb/` — the LMDB metadata database (buckets, objects, keys, cluster layout)
- `snapshots/` — auto-snapshot dir (empty if `metadata_auto_snapshot_interval` not set)

**Crucially, the cluster layout (which nodes exist, their zone assignments, their storage
capacity) is stored INSIDE the LMDB database — not in a separate `cluster_layout` text file.**
The Garage v2 migration guide references a conceptual `cluster_layout` but this is the
database content, not a stand-alone file on disk. After restore, no `garage layout assign` +
`garage layout apply` re-run is needed — the layout self-loads from the restored LMDB
database on next Garage start.

**Bucket and key reattachment:**
Garage bucket names, bucket-to-key permissions (`garage bucket allow`), and the key's
`access_key_id` / `secret_key` are all stored in the LMDB database. After restoring the
`telemetron_garage_meta` volume (LMDB), all bucket names, key IDs, and permissions are
restored verbatim. The S3 credentials host file (`{{ garage_config_dir }}/s3-credentials`)
and the LMDB metadata agree on the same key ID — no re-derivation or re-grant needed.

**What about data volume?**
The `telemetron_garage_data` volume (`/var/lib/garage/data/`) holds the actual S3 object
blocks (Loki chunk files, Tempo trace blocks, Mimir metric blocks). This volume must ALSO
be backed up if the operator wants to restore observability history. The meta volume alone
restores Garage's identity (keys, buckets, layout) but an empty data volume means Loki,
Tempo, and Mimir start fresh. For v1.3.0's round-trip UAT (backup → purge_data → redeploy
→ restore), BOTH volumes must be included in the Garage tarball.

**Tar scope (per v1.3.0 design):**
The Garage backup task should tar the entire meta volume (`/var/lib/garage/meta/`) plus the
entire data volume (`/var/lib/garage/data/`). These are two separate Docker volumes; two
separate tarballs or one combined tarball are both acceptable — document the choice in the
role's backup.yml header comment.

**Prevention:**
- Tar the full meta volume path (not just `db.lmdb/` — include the `snapshots/` subdir
  if present, to avoid confusion on restore about what the snapshot files mean).
- Tar the full data volume path.
- Restore both volumes before restarting Garage.
- Do NOT re-run `garage layout assign` / `garage layout apply` after restore; those steps
  are first-run-only and are gated in `bootstrap.yml` by the `NO ROLE ASSIGNED` check.

**Source:** [Garage recovery docs](https://garagehq.deuxfleurs.fr/documentation/operations/recovering/) + bootstrap.yml code review — HIGH confidence.

---

### GP-3 (CRITICAL): S3-credentials host file must be restored in sync with LMDB — partial restore breaks bootstrap idempotency

**Phase:** Phase 13 (per-role backup task) + Phase 14 (restore orchestrator)
**Live-UAT-only catchable:** YES — the orphan-key detection code path is only exercised live
**What goes wrong:**
The `garage_s3_credentials_file` (`/opt/telemetron/garage/s3-credentials`) holds the auto-
generated key ID and secret in plain text (two-line `key_id=...\nsecret=...` format, mode 0600).
This host file must match the `access_key_id` stored in the LMDB metadata volume. If the
LMDB is restored (with key GKxxx) but the host credentials file is absent or stale (pointing
to GKyyy), the next `deploy_docker.yml` run triggers the D-146 recovery branch: `not
garage_creds_file.stat.exists AND length == 1`. The recovery branch correctly detects one
existing key in the LMDB and re-reads its secret via `garage key info --show-secret`, then
re-persists the credentials file. **This means the host-credentials restore is not strictly
required for basic recovery** — the D-146 recovery branch handles it automatically.

However, there is a subtle timing risk: the recovery branch runs `garage key info --show-secret
<KEY_ID>` inside the running Garage container. If Garage hasn't finished starting yet (e.g.
the bootstrap is running before the HEALTHCHECK poll completes), this exec fails. The existing
pre-bootstrap HEALTHCHECK poll gate prevents this, but the recovery path is still more fragile
than a clean restore where the host file is present.

**Recommendation:**
Include the host credentials file in the Garage backup (as a separate file or as part of
the config-dir tar). Restore it before running `deploy_docker.yml`. This makes the restore
path the clean first-run path (no recovery branch fires) instead of the D-146 recovery path.

**What NOT to restore:**
Do NOT restore `garage.toml` from backup if `garage_admin_token` or `garage_rpc_secret`
have changed in `secrets.yml` between backup time and restore time. The rendered `garage.toml`
embeds these values; the deploy-time template render writes the correct values. Let
`deploy_docker.yml` render a fresh `garage.toml` from current inventory — only restore the
data volumes and the s3-credentials file.

**Source:** `roles/garage/tasks/bootstrap.yml` lines 107-276 (D-112 credential persistence,
D-146 recovery branch) — HIGH confidence (direct code review).

---

### GP-4 (MODERATE): Phase 11's regex regression class recurs in any backup `garage key list` parse

**Phase:** Phase 13 (per-role backup task) — specifically any backup verify step that
re-reads key list to confirm identity
**Live-UAT-only catchable:** YES — confirmed by Phase 11 UAT history
**What goes wrong:**
Phase 11 UAT proved the planner→checker→reviewer chain all assumed `garage key list` output
format from docs and all got it wrong. The live v2 output has 4 columns (ID, Created, Name,
Expiration), not 2. Any backup or restore task that needs to parse `garage key list` output
(e.g. a verify step that checks the key still exists after restore) will hit the same class
of bug if it uses a regex that doesn't skip the Created column.

**Existing fix (bootstrap.yml line 179):**
`regex_findall('(?m)^(\\S+)\\s+\\S+\\s+' ~ garage_s3_key_name ~ '(?:\\s|$)')`
This pattern skips the Created column by consuming `\S+` before the key name. Any backup/
restore task that parses `garage key list` must use this same regex, not a re-invented one.

**Prevention:**
If Phase 13 backup.yml or restore.yml adds a `garage key list` parse step (e.g. to verify
the key is present after metadata restore), copy the regex verbatim from `bootstrap.yml`
line 179 — do not re-derive it from documentation. Write a comment citing the Phase 11 bug.

**Source:** Phase 11 VERIFICATION.md G-01 gap closure; `bootstrap.yml` lines 161-183;
commits 2626989 + 319559f — HIGH confidence (empirical, live UAT).

---

## Component Pitfalls: Prometheus 3.11.3

### PP-1 (CRITICAL): Lock file left on SIGTERM — cold restore blocks Prometheus startup

**Phase:** Phase 13 (per-role restore task) + Phase 14 (restore orchestrator)
**Live-UAT-only catchable:** YES (intermittent; only manifests when the exact lock/PID state
matches an occupied PID on the restoring host)
**What goes wrong:**
Prometheus TSDB writes a PID-based lock file to `/prometheus/lock` when it opens the storage
directory. Under a clean SIGTERM (Docker `stop`), modern Prometheus (3.x) replaces the lock
on startup if the PID from the prior run is no longer active — it logs "A lockfile from a
previous execution already existed. It was replaced" as a warning and continues. However, the
TSDB lock uses a PID-file mechanism (not `flock()`). If the restored backup contains the old
lock file, and after restore the container starts with the same PID as the old lock file
(unlikely but non-zero probability), Prometheus refuses to start with:
`Opening storage failed: Locked by other process`.

The more common failure: backup is taken, then restored on a different host or after a system
reboot where PID namespace is fresh. The lock file references a PID that is now reused by an
unrelated process. Prometheus considers the DB locked and aborts.

**Prevention (two complementary options):**

Option A (recommended for v1.3.0 restore task): Delete the lock file after untarring and
before starting the container:
```
rm -f /prometheus/lock
```
This is safe because the container is stopped at this point and no Prometheus process holds
the lock. Add an explicit `ansible.builtin.file: path=/prometheus/lock state=absent` task
in `tasks/restore.yml` after volume contents are extracted.

Option B: Add `--storage.tsdb.no-lockfile` to the Prometheus container args. This
permanently disables lock-file creation. Acceptable for single-instance Docker; risky if
two Prometheus containers ever mount the same volume (not a concern in Telemetron's
single-host model).

Option A is cleaner for the restore path — it deletes the lock unconditionally (the container
is stopped, the lock is stale by definition) and doesn't require a permanent flags change.

**Source:** [prometheus/prometheus#2689](https://github.com/prometheus/prometheus/issues/2689),
[prometheus-community/helm-charts#2872](https://github.com/prometheus-community/helm-charts/issues/2872),
[Red Hat KB](https://access.redhat.com/solutions/6976141) — HIGH confidence.

---

### PP-2 (MODERATE): WAL is NOT guaranteed flushed on SIGTERM — in-flight samples (up to 2h) may be absent from cold backup

**Phase:** Phase 13 (per-role backup task) + operator education (Phase 15 docs)
**Live-UAT-only catchable:** NO — data loss window is expected and documented, not a bug
**What goes wrong:**
The Prometheus TSDB architecture is: in-memory head block → WAL → compacted on-disk blocks.
The in-memory HEAD holds recent samples (up to `prometheus_retention_time` or 2h of data,
whichever is shorter). At cold-quiesce backup time, the WAL on disk represents the durable
portion of what's in the head, but the WAL segments are typically **not** aligned to a clean
checkpoint boundary. Even after a clean SIGTERM, some samples from the last ~2-hour head
window may be in WAL segments that are correctly persisted to disk but reference in-memory
series information that is lost.

The official Prometheus docs state: "Backups made without snapshots run the risk of losing
data recorded since the last TSDB block was created" (block compaction runs every ~2h).

**For Telemetron's use case:** Prometheus is the SHORT-TERM metrics store (15d retention) and
remote_writes to Mimir (long-term store). Data visible in Prometheus but not yet compacted
to blocks may be absent from a restored Prometheus backup. However, this data was also
remote_written to Mimir BEFORE the backup (because the remote_write happens per scrape, not
per compaction). So Prometheus data loss from cold backup is: recent head data (up to ~2h)
visible in Prometheus but recoverable from Mimir. The restored Prometheus will simply show
a gap for the most recent 0-2h window before backup time, while Mimir shows continuous data.

**What to include in the backup:**
Tar the entire `/prometheus/` volume: WAL (`wal/`), compacted blocks
(`<ULID>/`), head chunks (`chunks_head/`), queries.active, and the lock file (to be deleted
on restore per PP-1). Excluding the WAL makes the gap worse. Including it makes the gap
as small as possible.

**Do NOT exclude `wal/`**: Prometheus docs note that excluding WAL "ensures a coherent backup
but may result in losing data covered by the WAL" — i.e., excluding it makes the cold backup
LESS accurate, not more. Include WAL in the tar.

**Source:** [Prometheus storage docs](https://prometheus.io/docs/prometheus/latest/storage/),
[TSDB WAL+checkpoint deep-dive](https://ganeshvernekar.com/blog/prometheus-tsdb-wal-and-checkpoint/) — HIGH confidence on architecture; LOW confidence on exact flush guarantee at SIGTERM.

---

### PP-3 (MODERATE): `queries.active` is stale-on-disk — harmless but logged on startup

**Phase:** Phase 13 (per-role backup task) + operator education
**Live-UAT-only catchable:** NO — static documentation verifiable
**What goes wrong:**
Prometheus tracks in-flight PromQL queries in `/prometheus/queries.active`. After a clean
shutdown, this file may be non-empty (recording queries that were in flight when SIGTERM
arrived). When Prometheus restarts with this file present, it logs: "These queries didn't
finish in prometheus' last run: ..." at startup. This is informational only — not an error,
not a data integrity concern. The queries are gone; the log is archaeology.

For the RESTORE path specifically: a backup tar includes `queries.active` from backup time.
After restore, Prometheus will log the stale queries from backup time at startup. This is
harmless and expected. The operator may see confusing log output on first post-restore start;
document this in the per-role README `## Backup` section.

**Optional cleanup:**
The restore task CAN delete `queries.active` after untarring (alongside the lock file per
PP-1). This suppresses the startup log noise. Whether this is worth the extra task line is
a judgment call; document the tradeoff.

**Source:** [ProMLabs training: active queries log](https://training.promlabs.com/training/monitoring-and-debugging-prometheus/logs/active-queries-log/) — HIGH confidence.

---

### PP-4 (LOW): `.tmp` directories from interrupted compaction — cold quiesce handles this

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** NO — cold quiesce prevents the problem by definition
**What goes wrong:**
Prometheus TSDB creates `.tmp` subdirectories inside `/prometheus/` during compaction
(writing the new merged block before atomically renaming it). If Prometheus is killed mid-
compaction (SIGKILL), the `.tmp` directory is left on disk. On a clean SIGTERM, Prometheus
completes or aborts in-progress compactions before exiting, so `.tmp` dirs should not be
present. However, if a backup is taken from a volume left over after a SIGKILL (e.g. from
host crash recovery), the restored Prometheus will scan for and clean up `.tmp` dirs
on startup. Prometheus does not refuse to start; it removes orphan `.tmp` blocks.

**For Telemetron's cold-quiesce model:** the `stop container → tar volume` sequence sends
SIGTERM (Docker's `docker stop` default). Prometheus 3.x handles SIGTERM gracefully and does
not leave `.tmp` dirs on a successful clean stop. This is low risk.

**What to do:** Include `.tmp` dirs in the tar if they exist (do not filter them out with
`--exclude='*.tmp'`). On restore, let Prometheus clean up on startup. Do not add logic to
detect or remove `.tmp` dirs in the backup/restore tasks.

**Source:** [prometheus/prometheus#8180](https://github.com/prometheus/prometheus/issues/8180) — MEDIUM confidence.

---

## Component Pitfalls: Grafana OSS 13.0.1

### GR-1 (CRITICAL): SQLite WAL mode is OFF by default — no `-wal`/`-shm` sidecar files to worry about, but shutdown still required

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** NO — default configuration is statically verifiable
**What goes wrong (the concern that turns out not to apply):**
SQLite WAL mode produces two sidecar files alongside the main database: `grafana.db-wal`
(write-ahead log) and `grafana.db-shm` (shared memory header). A common backup mistake is
to copy `grafana.db` while WAL mode is active but WITHOUT checkpointing the WAL first.
The result is an inconsistent backup: the main db file is from before the WAL writes, the
WAL captures newer writes, but only `grafana.db` was copied. On restore, the database looks
valid but is missing recent write transactions.

**Grafana's actual default (verified):**
Grafana 13.x ships with `wal = false` in `conf/defaults.ini` (confirmed via GitHub source).
WAL mode is off unless the operator explicitly sets `wal = true` in `grafana.ini`. Telemetron's
`roles/grafana/templates/grafana.ini.j2` does NOT set `wal = true`. Therefore:
- `grafana.db-wal` and `grafana.db-shm` do NOT exist under normal Telemetron operation.
- The sidecar checkpoint concern does NOT apply to the default Telemetron configuration.

**What this means for backup:**
The backup task only needs to tar `grafana.db` (and the plugins directory; see GR-2). The
container must still be stopped before tarring — Grafana documentation explicitly requires
shutdown before SQLite backup to ensure data integrity. A live `grafana.db` with open file
descriptors and fsync-in-progress writes is still unsafe to copy even without WAL mode.

**If the operator ever enables WAL mode:**
If `wal = true` appears in `grafana.ini`, the backup task must also include `grafana.db-wal`
and `grafana.db-shm` (or run a `PRAGMA wal_checkpoint(FULL)` SQL statement inside the
stopped-container volume before tarring). Add a comment in `tasks/backup.yml` flagging this
operator extension risk.

**Source:**
[grafana/grafana defaults.ini (GitHub)](https://github.com/grafana/grafana/blob/main/conf/defaults.ini) — `wal = false` — HIGH confidence.
[Grafana backup docs](https://grafana.com/docs/grafana/latest/administration/back-up-grafana/) — "Shut down your Grafana service before backing up" — HIGH confidence.

---

### GR-2 (MODERATE): Plugin files live in `telemetron_grafana_data` volume — include them in backup

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** NO — directory structure is static
**What goes wrong:**
Grafana stores operator-installed plugins in `/var/lib/grafana/plugins/` inside the named
volume. Telemetron v1.0.0 dropped the `grafana_plugins` install task from the upstream INSPQ
role (noted in the role README "Deviations" section). However, if an operator manually
installed plugins post-deploy (via `docker exec grafana grafana-cli plugins install ...`),
those plugins live in the volume. A backup that only captures `grafana.db` and misses
`plugins/` will restore Grafana to a state where operator-installed plugins are referenced
in the SQLite database but their binaries are absent.

**What Grafana does with missing plugins on startup:**
Grafana logs a warning for each missing plugin but starts normally. Dashboards that use
a missing plugin's panel type show a "Plugin not found" error in the UI. This is recoverable
by reinstalling the plugins, but the operator has to notice and act.

**Prevention:**
The backup task should tar the entire `/var/lib/grafana/` volume, not just `grafana.db`.
This captures: `grafana.db`, `plugins/`, `csv/` (if CSV data source is used), session
state files. The volume is typically small (tens of MB for a homelab install) — no need
to cherry-pick files.

**Source:** [Grafana backup docs](https://grafana.com/docs/grafana/latest/administration/back-up-grafana/) — "Copy ... plugin files" — HIGH confidence.

---

### GR-3 (LOW): Provisioned dashboards vs operator-edited dashboard interaction on restore

**Phase:** Phase 15 (docs cascade) — operator education
**Live-UAT-only catchable:** YES — provisioning behavior only observable in running Grafana
**What goes wrong:**
Telemetron provisions 7 curated dashboards via the provisioning filesystem path
(`/etc/grafana/provisioning/dashboards/telemetron/`). These are read from the bind-mount
config directory (`/opt/telemetron/grafana/provisioning/dashboards/telemetron/`) which is
part of the DEPLOY-TIME state, not the backup. The SQLite database also contains records for
provisioned dashboards (their UID, folder assignment, starred status, panel layout overrides).

When Grafana restarts after a restore, it re-reads the provisioning files and reconciles
them against SQLite. If the provisioning files have NOT changed (normal restore scenario),
the reconciliation is a no-op and the dashboards look exactly as before backup. If the
operator somehow DELETED a provisioned dashboard via the UI, the SQLite database records
its deletion, but the provisioning file still exists — Grafana re-provisions it on next
startup, overriding the operator's deletion. This is documented Grafana provisioning behavior.

**What this means for v1.3.0:**
Not a backup defect — it is the expected behavior of Grafana's provisioning system. Document
it in the per-role README `## Backup` section: "operator-deleted provisioned dashboards
will be re-added by Grafana on restart from provisioning files (this is Grafana's standard
provisioning behavior, not a restore defect)."

**Datasource UIDs after restore:**
Grafana's four hardcoded-UID datasources (`prometheus`, `loki`, `tempo`, `mimir`) are in the
provisioning files (deploy state), not in SQLite. They survive a full purge-data+redeploy
cycle without any backup. The restore of SQLite preserves only the operator state (org
settings, user accounts, custom dashboards, starred items). The datasource bindings from
the provisioning files re-apply correctly on Grafana start.

**Source:** Grafana provisioning docs; `roles/grafana/README.md` Datasources section — HIGH confidence.

---

### GR-4 (LOW): Grafana admin password is stored in SQLite on first boot only

**Phase:** Phase 15 (docs cascade) — operator education
**Live-UAT-only catchable:** NO — documented Grafana behavior
**What goes wrong:**
Grafana reads `GF_SECURITY_ADMIN_PASSWORD` at FIRST boot and writes the password hash to
SQLite. On subsequent restarts, it ignores the env var (the password is in the DB). After
a restore of SQLite from a backup, the admin password is whatever it was at backup time.
If the operator changed the password between backup time and restore time (via
`grafana-cli admin reset-admin-password`), the restore will silently revert to the old
password. The `GF_SECURITY_ADMIN_PASSWORD` env var (from `secrets.yml`) will NOT override
the SQLite-stored hash on restart.

**Prevention:**
Document in Phase 15 per-role README `## Backup` section: "After restore, the Grafana admin
password reverts to the value at backup time. If you rotated the password between backup and
restore, re-rotate it post-restore via `docker exec telemetron-grafana grafana-cli admin
reset-admin-password '<password>'`."

**Source:** `roles/grafana/README.md` Secrets section (existing doc) — HIGH confidence.

---

## Component Pitfalls: Alertmanager v0.32.1

### AP-1 (MODERATE): Alertmanager writes protobuf snapshot files, not BoltDB — both `silences` and `nflog` are plain files

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** NO — file format is statically verifiable from source
**What goes wrong:**
Community documentation (including some search results and older blog posts) incorrectly
describes Alertmanager as using BoltDB for its state files. **As of Alertmanager v0.22+
(and certainly v0.32.1), Alertmanager stores state in plain protobuf-encoded snapshot files**,
not BoltDB. The `/alertmanager/` volume at runtime typically contains:
- `silences` — protobuf-encoded silence state; written periodically by the maintenance loop
  (default interval: 15 minutes) and on graceful shutdown
- `nflog` — protobuf-encoded notification log; same write cadence

There is NO BoltDB `.db` file. There is NO WAL. There is NO lock file. The files are binary
(not human-readable) but are straightforward to copy with tar.

**Cold backup implication:**
Since Alertmanager writes these files on a PERIODIC schedule (every 15 min by default) and
on graceful SIGTERM shutdown, the cold-quiesce model (stop container → tar volume) ensures
the most recent snapshot is on disk. The snapshot at container stop time is the definitive
state. After SIGTERM, the maintenance code calls a final snapshot write before exit, so
the stop → tar sequence captures current state.

**What a "consistent backup" means for Alertmanager:**
It means stopping the container first (cold quiesce). The snapshot files are already
consistent because Alertmanager writes them atomically. Unlike LMDB (GP-1), there is no
partial-write corruption risk if the file is copied while the process is running — BUT the
content might be up to 15 minutes stale. Cold quiesce eliminates that 15-minute window.

**Source:**
[alertmanager/silence/silence.go](https://github.com/prometheus/alertmanager/blob/main/silence/silence.go) — protobuf + protodelim — HIGH confidence.
[alertmanager/nflog/nflog.go](https://github.com/prometheus/alertmanager/blob/main/nflog/nflog.go) — periodic maintenance + final snapshot on shutdown — HIGH confidence.

---

### AP-2 (LOW): Restoring stale nflog re-enables deduplication memory from backup time

**Phase:** Phase 15 (docs cascade) — operator education
**Live-UAT-only catchable:** NO — behavioral implication, documented
**What goes wrong:**
Alertmanager's notification log (nflog) tracks which alerts have been sent to which receivers.
This is the mechanism that prevents repeated notifications for the same ongoing alert (the
`repeat_interval: 4h` in Telemetron's config). After restoring a backup of the nflog, the
deduplication memory reverts to backup time. This means:
- Alerts that fired and were notified AFTER the backup time will fire and notify AGAIN
  on the restored Alertmanager (their nflog entry is absent from the restored state).
- Alerts that were silenced between backup time and restore time will become un-silenced
  (the silence state reverts to backup time).

**For Telemetron's current config (null receiver):**
Since Telemetron ships with a `null` receiver (no notification dispatch), the nflog is
functionally empty by default. The "re-firing" concern only applies to operators who have
wired a real receiver (Slack, email, PagerDuty) via `alertmanager_extra_receivers`. For
those operators, document this tradeoff in the per-role README `## Backup` section.

**Acceptable tradeoff:**
The alternatives — maintaining a consistent nflog that is continuously up-to-date — require
hot snapshots or streaming replication. Both are out of v1.3.0 scope. The cold-quiesce
tarball captures nflog state at backup time; that is the documented and expected behavior.

**Source:** Alertmanager architecture docs; `roles/alertmanager/README.md` Volumes section
"Pitfall 7 replay-storm risk" — HIGH confidence.

---

### AP-3 (LOW): Single-instance gossip-disabled — no cluster state pitfalls

**Phase:** Phase 13 (per-role backup task)
**Live-UAT-only catchable:** NO — configuration is static
**What goes wrong:**
HA Alertmanager clusters use gossip to synchronize state (silences, nflog) across replicas.
Restoring one replica from a backup without coordinating with other replicas can cause
split-brain silence state. **Telemetron runs with `--cluster.listen-address=""`**, which
disables gossip entirely. There is no cluster state, no mesh protocol, and no split-brain
risk. Backup and restore are single-node operations.

**Prevention:**
None needed. Document in per-role README that the single-instance model makes backup/restore
straightforward.

**Source:** `roles/alertmanager/README.md` Modes section — HIGH confidence.

---

## Cross-Component and Orchestrator Pitfalls

### XP-1 (CRITICAL): `community.docker state=stopped` strips container metadata — use `docker stop` command instead

**Phase:** Phase 13 (per-role backup tasks) + Phase 14 (orchestrator)
**Live-UAT-only catchable:** YES — the broken restart after backup is only observable with
a running Docker daemon
**What goes wrong:**
A known defect in `community.docker.docker_container` with `state: stopped` (GitHub issue
#791) strips container metadata: **volumes, bind mounts, restart policy, and network
configuration are removed from the stopped container**. When the backup task subsequently
does `state: started` to restart the container, Docker starts it without the original volume
mounts — the container runs but writes to nothing, and re-deploy is required to recover.

The native `docker stop <name>` command preserves all container configuration. Only the
Ansible module's `state: stopped` parameter triggers this defect.

**Community.docker version context:**
Issue #791 was filed against an older version. The operator's current install is v5.2.0.
The issue was marked closed, but the recommended safe practice remains to use
`command: docker stop` via `ansible.builtin.command` (or `community.docker.docker_container_exec`)
for quiescing rather than relying on `state: stopped` for containers that will be restarted
in the same run.

**Established Telemetron pattern:**
The v1.2.0 `undeploy_docker.yml` uses `state: absent` (not stopped) for permanent removal.
The `v1.2.0` per-role `uninstall.yml` files use `state: absent` too. Backup is the first
Telemetron use case where a container needs to be STOPPED (not removed) and then RESTARTED.
This is new territory; use `ansible.builtin.command: docker stop <name>` + explicit wait
instead of `state: stopped`.

**Prevention:**
```yaml
# Quiesce pattern for backup tasks -- use docker stop, NOT state: stopped
- name: Stop {{ role }}_container_name for cold-quiesce backup
  ansible.builtin.command: docker stop {{ role_container_name }}
  changed_when: true   # stopping is always a change

- name: Wait for {{ role }} container to be fully stopped
  community.docker.docker_container_info:
    name: "{{ role_container_name }}"
  register: container_state
  until: container_state.container.State.Running == false
  retries: 30
  delay: 2
  changed_when: false
```

After backup, restart with:
```yaml
- name: Restart {{ role }} container after backup
  ansible.builtin.command: docker start {{ role_container_name }}
```

**Do NOT use `state: started` with `force_kill: false` as an alternative restart**:
`state: started` on a container that was stopped with `docker stop` works correctly.
`state: started` on a container that was stopped with `state: stopped` is where the
configuration gets regenerated (sometimes losing the original bind mounts).

**Source:** [community.docker#791](https://github.com/ansible-collections/community.docker/issues/791) — MEDIUM confidence (issue closed, fix not confirmed in v5.x; native `docker stop` approach is the safe hedge regardless).

---

### XP-2 (CRITICAL): Restore order matters — Garage must be running before Loki/Tempo/Mimir restart

**Phase:** Phase 14 (restore orchestrator)
**Live-UAT-only catchable:** YES — ordering bugs only manifest with a live Docker stack
**What goes wrong:**
If `restore_docker.yml` restores Prometheus before Garage, the Prometheus container restarts
before Garage is healthy. This is fine — Prometheus doesn't depend on Garage. However, if
Loki, Tempo, or Mimir are RUNNING during restore (they are stateless from a backup
perspective — their DATA is in Garage), they are writing to Garage while Garage is being
stopped for restore. That write-during-restore corrupts the Garage data volume being restored.

**v1.3.0 design decision:** Only the 4 stateful roles have `tasks/backup.yml` and
`tasks/restore.yml`. Loki/Tempo/Mimir data is in Garage. The restore_docker.yml orchestrator
must:
1. Stop ALL containers that write to Garage (Loki, Tempo, Mimir — and the OTel Collector
   which may be writing OTLP to Loki/Tempo) before restoring the Garage volumes.
2. Restore Garage volumes.
3. Start Garage and wait for healthy.
4. Only then restart Loki, Tempo, Mimir, OTel Collector.

The backup_docker.yml does not have this concern (it only backs up the 4 stateful roles —
Garage backup stops Garage but does NOT stop Loki/Tempo/Mimir since they are only READING
from Garage during backup time, and the data being backed up is the volume contents while
Garage is stopped). Wait — this IS a concern: if Loki is writing to Garage at the moment
Garage is stopped for backup, Loki will crash-loop. The backup task should stop Garage last
(or stop all writers before stopping Garage).

**Revised backup order:**
1. Stop Alertmanager (no Garage dependency)
2. Stop Prometheus (no Garage dependency, but Prometheus data backed up separately)
3. Stop Grafana (SQLite backup; no Garage dependency)
4. Stop Loki, Tempo, Mimir, Fluent Bit, OTel Collector (Garage writers)
5. Stop Garage
6. Tar Garage volumes
7. Restart Garage
8. Wait for Garage healthy
9. Restart Loki, Tempo, Mimir, OTel Collector, Fluent Bit
10. Restart Prometheus, Grafana, Alertmanager

For v1.3.0 (4-role backup model), the backup_docker.yml can adopt the simpler model:
stop Garage for its own backup, but stop ALL Garage-writing containers (Loki, Tempo, Mimir)
before stopping Garage, to avoid Loki/Tempo/Mimir crash-loops during the Garage stop window.
This is a 30-60s extra stop window per Garage backup cycle.

**Source:** Telemetron architecture (Garage is the shared storage dependency) + Garage
monolithic mode documentation — HIGH confidence (architectural implication, not empirical).

---

### XP-3 (MODERATE): Partial restore consistency — restoring Garage without restoring Prometheus breaks TSDB→Mimir historical query

**Phase:** Phase 14 (restore orchestrator) + Phase 15 (docs)
**Live-UAT-only catchable:** NO — predictable from architecture
**What goes wrong:**
The 4-role backup model backs up Garage, Prometheus, Grafana, Alertmanager as independent
tarballs. The `restore_docker.yml` playbook accepts `--tags <role>` for partial restore
(per v1.3.0 design). Partial restores have consequences:

- Restore Garage only (without Prometheus): Prometheus TSDB has post-backup data that
  references Mimir blocks in Garage's `mimir-blocks` bucket. If Garage's data volume is
  from a DIFFERENT backup timestamp than Prometheus's current TSDB, the remote_read path
  (Prometheus → Mimir remote_read URL) may return gaps or errors for blocks that exist
  in Prometheus's query cache but not in the restored Garage.

- Restore Prometheus only (without Garage): Prometheus's local TSDB may have post-backup
  WAL entries that were remote_written to Mimir (pre-backup). The TSDB → Mimir remote_write
  queue will attempt to send them again on restart. Mimir deduplicates by timestamp+labels,
  so this is usually harmless.

- Restore Grafana only: SQLite reverts to backup state. Operator-edited dashboards after
  backup time are lost. Provisioned dashboards re-appear from provisioning files (GR-3).

**Prevention:**
Document the partial-restore consistency risk in Phase 15 docs (quickstart.md `## Backup and
restore` section). Recommend full 4-role backup + full 4-role restore as the standard
round-trip path. Tag-scoped partial restore is for recovery of a single component where
the other components are unaffected (e.g. Grafana SQLite corruption with healthy Garage).

---

### XP-4 (MODERATE): Backup destination permissions — `/opt/telemetron/backups/` must be root-writable

**Phase:** Phase 13 (per-role backup tasks) + Phase 14 (orchestrator)
**Live-UAT-only catchable:** YES — only observable with actual filesystem permissions on leviathan
**What goes wrong:**
The tarball destination is `/opt/telemetron/backups/<role>/<role>-<UTC-timestamp>.tar.zst`
(mode 0600 directory). Docker volume contents are owned by the container process UID:
- Garage: runs as root in the `dxflrs/garage` image
- Prometheus: runs as `nobody` (UID 65534)
- Grafana: runs as `grafana` (UID 472)
- Alertmanager: runs as user from quay.io image (check empirically on leviathan)

When the Ansible `become: true` (root) task tars the volume (via a one-shot tar container
or direct host filesystem access), root can read all UIDs — this is safe. The tarball is
then written to `/opt/telemetron/backups/<role>/` which is owned by root (mode 0600).
The `ansible-playbook` run uses `become: true` per Telemetron convention — this works.

**SELinux risk (RHEL 9 / Rocky 9 hosts):**
On SELinux-enforcing hosts, tar of Docker volumes may fail with `permission denied` on
files with unexpected SELinux contexts. Telemetron's primary UAT host (leviathan) runs
Ubuntu 24.04 (no SELinux by default — AppArmor only). **This pitfall is low priority for
the v1.3.0 UAT milestone but must be flagged in docs** for operators on RHEL 9.

If SELinux is a concern, the tar command should include `--selinux` flag on GNU tar to
preserve SELinux contexts.

**Source:** Telemetron role README volume sections (UIDs); SELinux tar docs — MEDIUM confidence.

---

### XP-5 (MODERATE): Docker volume path direct-access pattern vs helper container

**Phase:** Phase 13 (per-role backup tasks)
**Live-UAT-only catchable:** YES — Docker daemon implementation detail
**What goes wrong:**
Docker named volumes are stored at `/var/lib/docker/volumes/<name>/_data/` on a cgroup v2
Linux host. Reading this path directly from the Ansible host (with `become: true`) works on
Ubuntu 24.04 (leviathan's OS). However, this path is Docker implementation-internal and
is NOT guaranteed by the Docker API contract. The portable pattern for tarring a named volume
is to run a one-shot helper container:

```yaml
- name: Tar {{ role }} volume via helper container
  community.docker.docker_container:
    name: telemetron-backup-helper
    image: busybox:1.36
    volumes:
      - "{{ role_data_volume }}:/backup-source:ro"
      - "{{ backup_dest_dir }}:/backup-dest"
    command: "tar -czf /backup-dest/{{ tarball_name }} -C /backup-source ."
    state: started
    detach: false
    auto_remove: true
```

The helper container approach has its own pitfall: `auto_remove: true` + `detach: false` is
the same ansible/ansible#45272 auto_remove race that was banned by Gate 8 in Telemetron
(Phase 4 UAT finding). Use `auto_remove: false` and remove explicitly after status check.

**Recommendation for v1.3.0:**
For leviathan (Ubuntu 24.04), direct `/var/lib/docker/volumes/` path access is acceptable
and simpler. Use `ansible.builtin.archive` or `ansible.builtin.command: tar` with
`chdir: /var/lib/docker/volumes/<name>/_data`. Add a comment noting this is Docker-internal
path. For future portability, flag as "replace with helper container if mounting the path
fails on non-Ubuntu hosts."

**Source:** Docker volume internals; Phase 4 Gate 8 pattern; ansible/ansible#45272 — MEDIUM confidence.

---

### XP-6 (LOW): Symlinks inside volumes — tar default `--dereference` consideration

**Phase:** Phase 13 (per-role backup tasks)
**Live-UAT-only catchable:** NO — static analysis
**What goes wrong:**
Prometheus TSDB creates symlinks inside `/prometheus/` — specifically the `wal/` directory
may contain hardlink chains in checkpoint files, and compacted blocks may have symlinked
`chunks` directories in edge cases. GNU tar's default behavior is to PRESERVE symlinks (not
dereference). For backup/restore this is correct: tar preserves the symlink; tar x restores
the symlink. The only problem arises if the symlink target is outside the tar root (absolute
path symlinks). Prometheus TSDB uses only RELATIVE symlinks within the volume.

Garage's data volume contains object block files with a structured directory layout — no
symlinks.

Grafana's SQLite volume has no symlinks.

**Conclusion:** Default `tar -czf` behavior (preserve symlinks) is correct for all 4 volumes.
No special `--dereference` flag needed.

**Source:** Prometheus TSDB block layout documentation; empirical analysis — MEDIUM confidence.

---

### XP-7 (LOW): Sparse files — Prometheus blocks are NOT sparse on typical homelab storage

**Phase:** Phase 13 (per-role backup tasks)
**Live-UAT-only catchable:** NO
**What goes wrong (the concern that is unlikely to apply):**
Prometheus TSDB block files (chunks, index) COULD theoretically be sparse if written by a
filesystem that supports sparse files and the TSDB writer leaves large zero-filled regions.
In practice, Prometheus writes chunks densely (the chunk format is variable-length packed
records). On homelab storage (ext4 or xfs on a single host), TSDB files are not sparse.
The tar `--sparse` flag would have no effect on non-sparse files.

**When it could matter:**
Very large Prometheus deployments with many series that have gaps (all-zero chunks) might
produce sparse files. For a homelab with tens of thousands of series and `15d` retention,
this is not observed in practice.

**Recommendation:**
Omit `--sparse` from the tar invocation for simplicity. If a future operator reports
inflated backup tarballs for Prometheus, add `--sparse` as a diagnostic step.

**Source:** Prometheus TSDB chunk format docs; no empirical source found — LOW confidence.

---

## Ansible-Specific Pitfalls

### AN-1 (CRITICAL): Backup playbook stop-restart cycle must not use `state: absent` — volumes are preserved, containers are not removed

**Phase:** Phase 13 (per-role backup tasks) + Phase 14 (orchestrator)
**Live-UAT-only catchable:** YES — only observable in PLAY OUTPUT with a running Docker daemon
**What goes wrong:**
The v1.2.0 undeploy pattern uses `state: absent` (removes container). If the backup task
mistakenly uses `state: absent` instead of `docker stop`, the named volumes are preserved
(because Ansible's `state: absent` does not remove volumes unless `keep_volumes: false` is
set) but the CONTAINER is gone. The subsequent backup tar of the volume still works. However,
the "restart container after backup" step then fails because the container no longer exists —
it would need a full `deploy_docker.yml` re-run to come back. This is a half-state that
requires operator intervention.

**Prevention:**
- Backup task must use the stop/start pattern (XP-1 quiesce pattern) — NOT `state: absent`.
- Code review checklist for Phase 13: verify that no per-role `backup.yml` file contains
  `state: absent`.
- The playbook-level PLAY-start banner (D-160 pattern from v1.2.0) should display the
  stop/start model explicitly so operators understand backups do not remove containers.

**Source:** v1.2.0 `undeploy_docker.yml` pattern; `community.docker.docker_container`
`keep_volumes` default behavior — HIGH confidence.

---

### AN-2 (MODERATE): Failure half-state — bail-out default leaves partial-backup directory

**Phase:** Phase 14 (orchestrator design)
**Live-UAT-only catchable:** NO — design-time consideration
**What goes wrong:**
The v1.3.0 design specifies bail-out on first failure as the default. If the Prometheus
backup (role 3 of 4) fails (e.g. tar runs out of disk space), the `/opt/telemetron/backups/`
directory has:
- `garage/garage-<timestamp>.tar.zst` — valid
- `alertmanager/alertmanager-<timestamp>.tar.zst` — valid (if backup order is Garage, AM, Prometheus, Grafana)
- No Prometheus tarball
- No Grafana tarball

**The stopped containers:**
With the `docker stop` quiesce pattern (XP-1), a bail-out may leave a container in the
STOPPED state if the failure occurs after stop but before the restart step. The orchestrator
must either:
a) Always include an explicit "restart container on failure" rescue block in each role's
   backup.yml, or
b) Document that a failed backup may require `ansible-playbook deploy_docker.yml --tags <role>`
   to restart stopped containers.

**Recommendation for v1.3.0:**
Use Ansible `block`/`rescue`/`always` in each role's backup task to ensure the container
is ALWAYS restarted (even on failure), then bail-out at the orchestrator level:
```yaml
- block:
    - name: Stop container
    - name: Tar volume
  rescue:
    - name: Record failure (for orchestrator bail-out)
      set_fact: backup_failed=true
  always:
    - name: Restart container (always, even on failure)
      ansible.builtin.command: docker start {{ container_name }}
```

**Source:** v1.3.0 PROJECT.md locked design decisions (bail-out default) — HIGH confidence.

---

### AN-3 (MODERATE): Vault password is needed but backup does not capture secrets.yml

**Phase:** Phase 13 (per-role backup tasks) + operator education
**Live-UAT-only catchable:** NO — design implication
**What goes wrong:**
`backup_docker.yml` requires `--ask-vault-pass` (consistent with all Telemetron playbooks,
per CLAUDE.md: "Secrets are vault-encrypted in `secrets.yml`"). The vault is needed to read
`garage_admin_token` (used in Garage's health check invocation inside bootstrap.yml's tasks).

The backup playbook does NOT capture `secrets.yml` in the tarball — the design decision
(PROJECT.md) explicitly excludes secrets from the backup scope. Operators are responsible
for maintaining their own `secrets.yml` backups outside Telemetron's backup path.

**Restore implication:**
After a purge-data + redeploy + restore cycle, the operator must supply the SAME `secrets.yml`
vault contents as at backup time (specifically `garage_admin_token` and `garage_rpc_secret`)
because these values are embedded in `garage.toml` and the restored LMDB expects the same
admin token for API calls made during bootstrap verification. If `garage_admin_token` is
rotated between backup and restore, the bootstrap verify step (`garage key list`) will
fail with a 401 Unauthorized.

**Prevention:**
Document in Phase 15 `## Backup and restore` section: "Backup does not include `secrets.yml`.
Operators must independently back up their vault-encrypted secrets. The Garage backup will
not be restorable if `garage_admin_token` and `garage_rpc_secret` are rotated between
backup and restore time."

**Source:** PROJECT.md deferred items (encryption/secrets out of scope) + `roles/garage/README.md` Secrets section — HIGH confidence.

---

## Phase-to-Pitfall Assignment

| Pitfall | ID | Phase | Catchable Static? | Catchable Live-UAT only? |
|---------|----|-------|:-----------------:|:------------------------:|
| Garage LMDB cold-copy requires full stop | GP-1 | 13 | YES | NO |
| Garage meta volume scope (LMDB + layout inside DB) | GP-2 | 13 | YES | NO (restore tar path) |
| S3-credentials sync with LMDB | GP-3 | 13+14 | YES | YES (D-146 recovery) |
| `garage key list` regex class (Phase 11 recurrence) | GP-4 | 13 | NO | YES |
| Prometheus lock file on restore | PP-1 | 13+14 | YES | YES (PID race) |
| WAL not guaranteed flushed — 0-2h data gap | PP-2 | 13+15 | YES | NO |
| queries.active stale log on startup | PP-3 | 13+15 | YES | NO |
| `.tmp` from interrupted compaction | PP-4 | 13 | YES | NO |
| Grafana SQLite WAL is OFF by default | GR-1 | 13 | YES | NO |
| Plugin files in volume | GR-2 | 13 | YES | NO |
| Provisioned dashboards re-provision on restart | GR-3 | 15 | YES | YES |
| Admin password reverts to backup-time value | GR-4 | 15 | YES | NO |
| AM protobuf files (not BoltDB) | AP-1 | 13 | YES | NO |
| Stale nflog re-enables old dedup state | AP-2 | 15 | YES | NO |
| Single-instance AM — no cluster state pitfalls | AP-3 | 13 | YES | NO |
| `state: stopped` strips container metadata | XP-1 | 13+14 | NO | YES |
| Restore order: Garage before Loki/Tempo/Mimir writers | XP-2 | 14 | YES | YES |
| Partial restore consistency | XP-3 | 14+15 | YES | NO |
| Backup destination permissions / SELinux | XP-4 | 13+14 | NO | YES |
| Docker volume direct-path vs helper container | XP-5 | 13 | NO | YES |
| Symlinks in volumes — tar default is correct | XP-6 | 13 | YES | NO |
| Sparse files — unlikely at homelab scale | XP-7 | 13 | YES | NO |
| `state: absent` vs stop for backup quiesce | AN-1 | 13 | YES | YES |
| Bail-out leaves stopped container | AN-2 | 14 | YES | NO |
| Vault required, secrets not backed up | AN-3 | 13+15 | YES | NO |

---

## Live-UAT-Only Catchable Pitfalls — UAT Scenario Design Implications

The following pitfalls are NOT catchable by static analysis, plan-check, code review, or
verifier reading upstream docs. They WILL only surface when the playbook runs against a
live Docker host (leviathan). Phase 14's UAT scenarios must exercise each of them:

| Pitfall | UAT Scenario Needed |
|---------|---------------------|
| GP-3: D-146 recovery branch fires if creds file absent but LMDB has the key | Backup → `purge_host_dirs=true` undeploy → redeploy → restore; verify bootstrap recovery branch fires and smoke test passes |
| GP-4: `garage key list` regex recurrence | Any restore verify step that parses `garage key list` output |
| PP-1: Lock file PID race | Restore Prometheus TSDB volume → restart container → verify startup succeeds with no "Locked by other process" error |
| XP-1: `state: stopped` strips container metadata | Verify that the stop/start quiesce cycle leaves all 4 containers in the same configuration as before (check `docker inspect` volumes/networks post-restart) |
| XP-2: Garage restore stops writers first | Verify Loki/Tempo/Mimir do not crash-loop during Garage stop window in backup_docker.yml |
| XP-4: Backup destination permissions | Verify `/opt/telemetron/backups/` is writable and tarballs are mode 0600 |
| XP-5: Docker volume path access | Verify tar via direct `/var/lib/docker/volumes/` path works on leviathan Ubuntu 24.04 |
| AN-1: No `state: absent` in backup tasks | Verify 4 containers are RUNNING (not missing) after backup_docker.yml completes |

The principle established in v1.1.0 and confirmed in v1.2.0 (Phase 11 G-01):
**The planner, checker, code reviewer, and verifier all read upstream docs and assume output
formats. None of them run the actual binary. Live-UAT on leviathan is the only gate that
catches output-format-assumption regressions and Docker-state-interaction bugs.**

---

## Sources

### HIGH confidence
- [Garage HQ: Recovering from failures](https://garagehq.deuxfleurs.fr/documentation/operations/recovering/) — LMDB cold-copy safety, snapshot directory
- [Garage HQ: Known issues](https://garagehq.deuxfleurs.fr/documentation/reference-manual/known-issues/) — "LMDB is prone to database corruption after an unclean shutdown"
- [Garage HQ: Configuration reference](https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/) — `metadata_auto_snapshot_interval`, LMDB default, `db.lmdb/` layout
- [alertmanager/silence/silence.go (GitHub)](https://github.com/prometheus/alertmanager/blob/main/silence/silence.go) — protobuf encoding, maintenance loop, final snapshot on shutdown
- [alertmanager/nflog/nflog.go (GitHub)](https://github.com/prometheus/alertmanager/blob/main/nflog/nflog.go) — notification log protobuf, maintenance function
- [Prometheus storage docs](https://prometheus.io/docs/prometheus/latest/storage/) — WAL, block compaction, backup recommendation
- [Prometheus TSDB WAL deep-dive (Vernekar)](https://ganeshvernekar.com/blog/prometheus-tsdb-wal-and-checkpoint/) — WAL segments, checkpoint, HEAD flush
- [Prometheus snapshot-on-shutdown (Vernekar)](https://ganeshvernekar.com/blog/prometheus-tsdb-snapshot-on-shutdown/) — `chunk_snapshot.X.Y` files
- [grafana/grafana defaults.ini (GitHub)](https://github.com/grafana/grafana/blob/main/conf/defaults.ini) — `wal = false` default confirmed
- [Grafana backup docs](https://grafana.com/docs/grafana/latest/administration/back-up-grafana/) — shutdown requirement, plugin directory inclusion
- `roles/garage/tasks/bootstrap.yml` — D-112 credential format, D-146 recovery branch, GP-4 regex — direct code review
- Phase 11 VERIFICATION.md — G-01 closure, two regex regressions caught live-UAT only

### MEDIUM confidence
- [prometheus/prometheus#2689](https://github.com/prometheus/prometheus/issues/2689) — TSDB lock file on unclean shutdown
- [prometheus-community/helm-charts#2872](https://github.com/prometheus-community/helm-charts/issues/2872) — "lockfile from previous execution replaced" log message
- [community.docker#791](https://github.com/ansible-collections/community.docker/issues/791) — `state: stopped` strips container metadata (issue closed; exact fix version unconfirmed in v5.x)
- [Red Hat KB: Prometheus lock file](https://access.redhat.com/solutions/6976141) — `--storage.tsdb.no-lockfile` workaround

### LOW confidence
- Prometheus TSDB sparse files — no authoritative source found; empirical assertion based on chunk format analysis
- Prometheus clean-SIGTERM WAL flush guarantee — behavioral evidence only; no explicit upstream contract in v3.x docs
