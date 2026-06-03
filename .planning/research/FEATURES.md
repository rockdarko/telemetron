# Feature Research

**Domain:** Cold-quiesce backup and restore for a self-hosted, single-host, Ansible-Docker observability stack
**Milestone:** Telemetron v1.3.0
**Researched:** 2026-06-02
**Confidence:** HIGH (Grafana/Prometheus official docs + Alertmanager upstream + prior-art projects verified)

---

## Prior Art Survey

Five projects were studied to derive operator workflow conventions. Notes below inform every table that follows.

### 1. Gitea / Forgejo (`gitea dump` + restore)

`gitea dump -c /data/gitea/conf/app.ini` produces `gitea-dump-<unix-epoch>.zip` — a single archive containing the DB export, config, data, and repositories. The service MUST be stopped before dumping (documented as a hard requirement). Restore is fully manual: extract, move files to locations, re-run `./gitea admin regenerate hooks`. No restore subcommand exists.

**Convention takeaways:**
- "Stop service, dump, restart" is the established homelab quiesce pattern — operators expect brief downtime.
- Unix-epoch timestamp in the filename is simple but not human-readable; comparable tools prefer `YYYYMMDD` or ISO 8601 variants.
- No "latest" symlink; operators use `ls -t` to find the newest file.
- No backup-before-restore guard; the operator is responsible.

### 2. Nextcloud (`occ maintenance:mode` + db dump + rsync)

`occ maintenance:mode --on` quiesces the application, then the operator runs a database dump (`mariadb-dump --single-transaction`) and `rsync` of the data and config directories to a timestamped target (`nextcloud-dirbkp_$(date +"%Y%m%d")/`). Restore: turn off maintenance mode, copy files back, run `occ maintenance:data-fingerprint`. The `date +"%Y%m%d"` naming is the documented recommendation.

**Convention takeaways:**
- Maintenance mode = explicit quiesce state; operator knows the service is locked during backup.
- `YYYYMMDD` (8-digit date) is the standard Nextcloud-documented timestamp format. Sorting works; uniqueness does not (two runs on the same day collide). `YYYYMMDD-HHMMSS` resolves this.
- Post-restore integrity step (`data-fingerprint`) is a lightweight table-stakes guard.
- Backup-before-restore is not automated; the restore doc assumes the operator manages that.

### 3. VictoriaMetrics (`vmbackup` / `vmrestore`)

`vmbackup -storageDataPath /var/lib/victoriametrics -dst s3://bucket/backup-YYYYMMDD` writes a full backup to a storage destination. `vmrestore` requires VictoriaMetrics to be stopped: `vmrestore -src s3://bucket/backup-YYYYMMDD -storageDataPath /var/lib/victoriametrics`. Incremental backups are automatic if `-dst` points to an existing backup. The workflow is symmetric: one binary for backup, one for restore, same flags.

**Convention takeaways:**
- Stop-before-restore is universal even for tools that support hot-backup.
- Symmetric binary naming (`vmbackup` / `vmrestore`) mirrors the expectation for symmetric Ansible playbooks (`backup_docker.yml` / `restore_docker.yml`).
- `YYYYMMDD` is the documented naming convention in VictoriaMetrics examples.
- "Latest" detection is implicit: the operator names the `-dst` explicitly; no auto-discovery.
- No confirmation gate for restore — the explicit `-src` path IS the confirmation.

### 4. Grafana Labs official backup guidance

Official docs at `grafana.com/docs/grafana/latest/administration/back-up-grafana/` state:
- Stop Grafana before backing up SQLite: "shut down your Grafana service before backing up the SQLite database."
- Backup: copy `grafana.db` (the SQLite file at `/var/lib/grafana/grafana.db` inside the container, exposed via the named volume `telemetron_grafana_data`) plus the config and plugins directories.
- Restore: copy `grafana.db` back to its original location.
- Provisioned dashboards and datasources are version-controlled config, not DB state — they do NOT need to be in the backup tarball because `deploy_docker.yml` re-renders them from Ansible templates.

**Convention takeaways:**
- SQLite file is the backup target; provisioning config is NOT (already in the repo).
- Grafana's data volume is a single directory at `/var/lib/grafana`; a full volume snapshot is clean.
- No automated backup tooling from Grafana Labs; operator is expected to write their own.
- `grafana-tools/grafana-backup` (API-based) is community tooling for cloud-managed Grafana, not relevant for a version-controlled provisioning stack like Telemetron.

### 5. Prometheus TSDB backup

Official Prometheus docs and community consensus:
- Hot backup: `POST /api/v2/admin/tsdb/snapshot` (requires `--web.enable-admin-api`). Creates hard-linked snapshot at `<tsdb-path>/snapshots/<timestamp>` in `20060102T150405Z` format (Go time reference). Space cost is minimal because hard links.
- Cold backup (simpler, no API required): stop Prometheus, tar `<tsdb-path>` excluding `wal/` and `chunks_head/` for a coherent block-only backup, restart. The WAL covers only the last ~2 hours of data; excluding it accepts that loss but avoids partial-write inconsistency.
- Restore: stop Prometheus, clear `<tsdb-path>`, untar backup, restart.

**Convention takeaways:**
- Cold backup (stop + tar + restart) is the right choice for Telemetron v1.3.0 because it requires no API flag change, no API call in the backup task, and is symmetric with the restore operation. The ~2-hour WAL loss is acceptable for homelab backup semantics.
- Prometheus data volume path is `/prometheus` (image default, confirmed in `prometheus_data_path: /prometheus` in `roles/prometheus/defaults/main.yml`).
- Cold model aligns with the locked v1.3.0 design decision.

### 6. Alertmanager state files

Alertmanager stores two files in its data directory (`/alertmanager` inside the container, backed by `telemetron_alertmanager_data`):
- `silences` — active and expired silence rules in protobuf format.
- `nflog` — the notification log (which alerts fired to which receivers and when).

Both files are small (KB to low-MB for any homelab instance). Backing up the whole volume captures both. Restore is: stop Alertmanager, replace volume contents, restart. The `amtool silence import/export` JSON format is an alternative for silences-only backup but requires the container to be running; not appropriate for cold backup.

---

## Feature Landscape

### Table Stakes (Must-Have for v1.3.0)

Features the homelab operator expects. Without these, the milestone does not ship.

| Feature | Why Expected | Complexity | v1.2.0 Contract Dependency |
|---------|--------------|------------|---------------------------|
| **Per-role `tasks/backup.yml` for the 4 stateful roles** (Garage, Prometheus, Grafana, Alertmanager) | Gate 11 mirrors Gate 10: if every deploy role ships `tasks/uninstall.yml`, the natural v1.3.0 analogue is `tasks/backup.yml` + `tasks/restore.yml`. Homelab operators expect role-scoped artifacts. | MEDIUM | Inherits `--tags <role>` UX from Phase 11; role-tag-only convention (no sub-tags) per D-133 |
| **Cold-quiesce model per role: stop container, snapshot, restart** | All prior-art projects (Gitea, Nextcloud, vmbackup) use "stop service, backup, restart." Operators expect brief downtime per role (~30–60 s). Aligns with locked design decision. | SMALL (each role's backup task is 3–4 tasks: stop, tar, restart, verify) | `keep_volumes: true` + `state: stopped` pattern already established in `tasks/uninstall.yml` |
| **`playbooks/backup_docker.yml` orchestrator** | Mirrors `deploy_docker.yml` and `undeploy_docker.yml` shape. Operators who learned the `ansible-playbook playbooks/deploy_docker.yml --ask-vault-pass` pattern expect the same invocation for backup. | SMALL | Inherits D-160 PLAY-start informational banner; inherits `--ask-vault-pass` + `--tags <role>` UX from v1.2.0 |
| **`playbooks/restore_docker.yml` orchestrator** | Symmetric to backup; same UX shape. Operators expect `backup_docker.yml` and `restore_docker.yml` to be a matched pair. | SMALL | Inherits D-159 WARN template — restore is destructive (overwrites volume data) so it must emit `WARNING: irreversible -- <role> restore: <targets>` before overwriting |
| **Tarball naming: `<role>-<UTC-timestamp>.tar.zst`** | `YYYYMMDD-HHMMSS` format (e.g., `garage-20260602-140000.tar.zst`) is human-readable, filesystem-safe, and lexicographically sorted. Nextcloud's documented format is `YYYYMMDD`; adding `-HHMMSS` resolves same-day collisions. `tar.zst` is the established zstd-compressed tar extension. | SMALL | No existing Telemetron convention to align; establishes the v1.3.0 convention |
| **Destination layout: `/opt/telemetron/backups/<role>/`** | Operators can `ls /opt/telemetron/backups/garage/` to see all Garage backups. Consistent with existing `/opt/telemetron/<role>/` bind-mount structure. Mode 0600 on the backups directory gates casual access. | SMALL | `telemetron_config_root` variable already defines `/opt/telemetron/` as the base |
| **Default-to-latest tarball per role on restore** | Operators expect "just run the restore playbook" to use the most recent backup without needing to specify a timestamp. `find` + `sort -rn` + `head -1` against `YYYYMMDD-HHMMSS` filenames is correct because lexicographic order == chronological order. | SMALL | Applies to all 4 roles independently; each role finds its own latest |
| **`--extra-vars backup_restore_from=<YYYYMMDD-HHMMSS>` to pin a specific backup** | Operators need to restore from a specific point when the latest backup is itself corrupt or post-incident. Ansible Tower / vmbackup both use an explicit path extra-var for non-default restores. | SMALL | Single timestamp applies to all 4 roles (cross-role consistency); per-role pins deferred as differentiator |
| **`backup_continue_on_failure=true` opt-in** | Locked design decision: bail-out default on first failure. Homelab operators evaluating the feature want to know that a single role's failure does not silently corrupt a partial backup set. Opt-in override matches the v1.2.0 purge-flag pattern. | SMALL | Mirrors `telemetron_purge_data` / `telemetron_purge_images` pattern from Phase 11 |
| **Restore gated by `backup_restore_confirm=true`** | Restore overwrites volume data — it is irreversible in the same class as `telemetron_purge_data=true`. The v1.2.0 purge flags are the established pattern for bomb-button opt-in. Without a confirm gate, `restore_docker.yml` could accidentally destroy live data on a misfire. | SMALL | Direct mirror of `telemetron_purge_data` semantics; PLAY OUTPUT shows the gate state in the D-160-style banner |
| **D-159 WARN before each destructive restore task** | Restore is a destructive overwrite; it must emit `WARNING: irreversible -- <role> restore: <targets>` before overwriting volume data, matching the exact D-159 contract established in v1.2.0. | SMALL | D-159 contract is exact: `WARNING: irreversible -- <role> <action>: <targets>` — one WARN task per role before the overwrite task |
| **PLAY-start informational banner for `backup_docker.yml`** | Operators see what will happen before it happens. Backup is not destructive but the banner is informational: "Backing up 4 stateful roles to /opt/telemetron/backups/". Mirrors D-160 in shape but does NOT use `WARNING:` prefix — backup is not irreversible. | SMALL | D-160 contract (undeploy): WARN for destructive ops, informational for non-destructive. Backup banner = informational; restore banner = WARN |
| **Live leviathan round-trip UAT** | v1.1.0 and v1.2.0 lessons both demonstrated that static verification misses output-format regressions. The full round-trip — `backup_docker.yml` → `undeploy --purge-data` → `deploy_docker.yml` → `restore_docker.yml` → smoke signals visible in Grafana — is the only gate that validates end-to-end correctness. | MEDIUM | Mirrors v1.0.0 `smoke_test.yml` pattern as acceptance gate |
| **Documentation cascade (Gate 11 shape)** | v1.2.0 Phase 12 established the 3-layer cascade: `roles/README.md` gate → `docs/quickstart.md` section → per-role README section. v1.3.0 must apply the same shape: Gate 11 in `roles/README.md`, `## Backup and restore` in `docs/quickstart.md`, `## Backup` H2 in each of the 4 stateful role READMEs, one-liner "no backup needed" note for each stateless role README. | SMALL | Mirrors Phase 12 (Phases 10+11 → Phase 12 doc cascade) exactly |
| **Tarball integrity list-check after creation** | `tar --list --file=<archive>` (or `tar tf <archive>`) verifies the archive was written without corruption before the container is restarted. Fails the backup task if the archive cannot be listed. This is the table-stakes verification that the file is at minimum a valid tar archive. | SMALL | Single task added at the end of each `tasks/backup.yml`; uses `community.docker.docker_container_exec` or `ansible.builtin.command` against the host |
| **Backup task emits final archive path and size** | Operators need to know where the backup landed and whether it is non-zero size. A `debug: msg=` task showing the archive path + `stat` size after the list-check closes the loop. Comparable to how `gitea dump` prints the output path on completion. | SMALL | `ansible.builtin.stat` on the tarball; `failed_when: stat.size == 0` |

### Differentiators (Nice to Have, Can Defer Beyond v1.3.0)

Features that add value but are not required for the milestone to be credible.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-role timestamp pin via `--extra-vars`** (`backup_restore_from_garage=X`, `backup_restore_from_prometheus=Y`) | Operators restoring after a cascade failure might want Garage from Tuesday and Prometheus from Wednesday. Useful but rare. | SMALL | Too many knobs for v1.3.0; single `backup_restore_from` timestamp that applies to all 4 roles is the right default. Add per-role vars only if operators request them. |
| **`backup_docker.yml --check` dry-run mode** | Shows which roles would be backed up and where, without stopping any container. Useful for verifying inventory is correct. | SMALL | Ansible `--check` mode does not fully simulate `community.docker.docker_container` state changes; a custom `dry_run` var with early-exit tasks is more reliable but adds surface. Defer. |
| **Manifest file at `/opt/telemetron/backups/manifest.json`** | Machine-readable index of all backups with role, timestamp, size, and Telemetron version. Useful for tooling that wraps Telemetron (e.g., a future web UI or monitoring job). | MEDIUM | `ls` the directory is enough for v1.3.0. A manifest becomes useful when the operator has many backups or when off-host sync tools need to know what to transfer. Defer. |
| **`<role>-latest.tar.zst` symlink** | `ln -sf <role>-YYYYMMDD-HHMMSS.tar.zst <role>-latest.tar.zst` lets operators (and scripts) reference the latest backup without parsing timestamps. | SMALL | `find + sort + head -1` on `YYYYMMDD-HHMMSS` names is equally reliable and avoids symlink management complexity (what happens when the symlink target is deleted?). Defer until operators request scripting integration. |
| **SHA256 checksum file alongside each tarball** | `sha256sum <tarball> > <tarball>.sha256` enables verification without extracting. Restic and Borg both do this natively. | SMALL | Adds one task per backup; pairs with a verification task on restore (`sha256sum --check`). Worthwhile but not blocking v1.3.0 — the list-check provides structural integrity; SHA256 adds data integrity. Defer to v1.3.x. |
| **`backup_before_restore` auto-snapshot gate** | Automatically runs `backup_docker.yml` before executing `restore_docker.yml` so the current state is captured before being overwritten. Protects against "restore breaks something worse." | MEDIUM | Useful safety net. Complex to implement cleanly in Ansible (nested playbook invocation or `import_playbook`). The `backup_restore_confirm=true` gate + the operator's own pre-restore backup habit covers the v1.3.0 case. Defer. |
| **Stateless-role config snapshot** | Tar the config directory (`/opt/telemetron/<role>/`) for stateless roles (Loki, Tempo, Mimir, OTel, FB) to capture rendered config at a point in time. | SMALL | Redundant: rendered config is deterministic from Ansible templates + `group_vars`. Re-running `deploy_docker.yml` reproduces it exactly. No operator state exists in these roles. Not useful. |

### Anti-Features (Explicitly Out of Scope for v1.3.0)

Features to NOT build, with the rationale for each deferral.

| Anti-Feature | Why Excluded | Why Deferred and What Covers It Instead |
|--------------|--------------|----------------------------------------|
| **Off-host backup push (rsync, S3, rclone)** | Telemetron stays opinion-free on off-host storage. Different operators use restic, BorgBackup, rclone, or simple rsync — mandating one would gate adoption. | Operator wraps Telemetron's `/opt/telemetron/backups/` output with their preferred off-host tool. Telemetron writes dated local tarballs; the operator ships them off-host. |
| **Encryption at rest** | `age`, `gpg`, `restic`, and LUKS all encrypt at rest. Picking one imposes a key-management story on Telemetron. The `secrets.yml` surface already has enough complexity. | Operators who need encryption wrap with their chosen tool after the tarball is written. Telemetron does not decrypt on restore either — the same tool that encrypted must decrypt. |
| **Automatic retention / keep-last-N pruning** | Deleting backups is irreversible. The D-159 WARN contract exists precisely because silent deletion is the homelab disaster scenario. Adding pruning logic in v1.3.0 would require its own WARN + confirm gate, doubling the surface. | Operator manages retention with `find /opt/telemetron/backups -mtime +N -delete` or their off-host tool's retention policy. Telemetron writes and never deletes. |
| **Incremental backups** | Full-snapshot-per-run is simpler, predictable, and correct for homelab volumes. Incremental requires a reference snapshot chain; chain corruption invalidates all incrementals since the last full. | Operator uses restic or BorgBackup on top of the full snapshots if incremental semantics are needed. These tools handle deduplication transparently. |
| **Hot backup via per-component APIs** | Prometheus `/api/v2/admin/tsdb/snapshot`, Grafana SQLite `.backup` pragma, Garage `snapshot` subcommand — each has a different interface, each requires the container to be running and healthy, and each produces a different artifact shape. Four different mechanisms = four different failure modes to test in UAT. | Cold quiesce is uniform: stop all 4 containers with the same `state: stopped, keep_volumes: true` pattern, tar, restart. One mechanism, one UAT path. |
| **Cross-version backup migration** | A backup taken under v1.3.0 may not be directly restoreable under v1.4.0+ if role configs or volume schemas change. The operator needs to know this explicitly. | Document in `docs/quickstart.md` `## Backup and restore` section: "Backups are intended for same-version restore. Cross-version restore is not tested or supported." |
| **Backup verification by parallel-restore** | Spinning up a second stack on the same host to test-restore into it would require port remapping, separate volumes, and a separate inventory target. Too heavy for homelab. | The list-check (`tar tf`) + stat-size check after backup provides structural confidence. Full restore is tested in the leviathan UAT round-trip; that is the real verification. |
| **"Last good backup" auto-discovery via integrity check** | Scanning all tarballs to find the most recent one that passes `tar tf` would require iterating over N archives on every restore. Adds latency and complexity. The timestamp-sort heuristic is the right default. | Operators who need integrity discovery use `for f in $(ls -rt); do tar tf $f && break; done` manually. Not Telemetron's responsibility. |
| **Backup of stateless roles** | Loki, Tempo, and Mimir data lives in Garage (covered by the Garage backup). Their rendered config is reproducible from Ansible templates. Karma, node_exporter, OTel, and Fluent Bit carry zero operator state. | Operator re-runs `deploy_docker.yml` to restore stateless role config. It is idempotent and takes the same time as a restore would. |
| **Multi-host coordination** | v1.3.0 scope is single-host, single-deploy — the same surface as every prior milestone. Coordinating backups across multiple hosts would require a coordinator role and cross-host sequencing logic. | Deferred to the distributed-mode milestone (alongside `DIST-01..03`). |

---

## Feature Dependencies

```
[backup_docker.yml orchestrator]
    └──calls──> [tasks/backup.yml for each of 4 stateful roles]
                    └──requires──> [container state: stopped (community.docker.docker_container)]
                    └──produces──> [<role>-YYYYMMDD-HHMMSS.tar.zst in /opt/telemetron/backups/<role>/]
                    └──verifies──> [tar list-check + stat size check]
                    └──restarts──> [container state: started]

[restore_docker.yml orchestrator]
    └──gated by──> [backup_restore_confirm=true (anti-misfire gate)]
    └──calls──> [tasks/restore.yml for each of 4 stateful roles]
                    └──requires──> [tarball exists at resolved path (latest or explicit timestamp)]
                    └──requires──> [container state: stopped]
                    └──emits──> [D-159 WARNING before overwriting volume contents]
                    └──overwrites──> [volume contents from tarball]
                    └──restarts──> [container state: started]

[tasks/backup.yml] ──depends on order──> [tasks/main.yml deploying the container first]
[tasks/restore.yml] ──depends on order──> [tasks/main.yml deploying the container first]

[Garage backup] ──covers──> [Loki data (loki-chunks bucket)]
                ──covers──> [Tempo data (tempo-traces bucket)]
                ──covers──> [Mimir data (mimir-blocks, mimir-ruler, mimir-alerts buckets)]
[Garage backup] ──also covers──> [S3 credentials file at /opt/telemetron/garage/s3-credentials]

[leviathan UAT round-trip]
    └──requires──> [backup_docker.yml complete]
    └──requires──> [undeploy_docker.yml --extra-vars telemetron_purge_data=true complete]
    └──requires──> [deploy_docker.yml complete]
    └──requires──> [restore_docker.yml complete]
    └──validates via──> [smoke_test.yml: synthetic OTLP signals visible in Grafana]
```

### Dependency Notes

- **Garage backup covers Loki/Tempo/Mimir data:** Loki chunks, Tempo traces, and Mimir metric blocks all live in Garage's named volumes (`telemetron_garage_meta`, `telemetron_garage_data`). Backing up Garage IS backing up those three backends. No separate `tasks/backup.yml` for Loki, Tempo, or Mimir.
- **Garage backup must also capture the S3 credentials file:** The file at `/opt/telemetron/garage/s3-credentials` (mode 0600) holds the auto-generated S3 key/secret. On restore, Loki/Tempo/Mimir must be given the same credentials that their bucket ACLs were created with. If the credentials file is not in the backup, the post-restore deploy will generate a new key that Garage's bucket ACLs do not recognize, requiring a full bootstrap. The Garage `tasks/backup.yml` must include both the named volumes AND the `garage_s3_credentials_file` path.
- **Restore ordering mirrors deploy ordering:** Garage must be restored (and running) before Loki/Tempo/Mimir are started, since their startup requires S3 access. The `restore_docker.yml` orchestrator must follow the same dependency order as `deploy_docker.yml` for the 4 stateful roles.
- **`backup_restore_confirm=true` gate:** Restore without confirmation is a misfire risk. The gate mirrors `telemetron_purge_data=true`. Unlike purge (which is always opt-in), restore has a default action (restore latest) — the confirm gate ensures the operator typed the intent explicitly.

---

## v1.3.0 Build Scope

### Phase 13 (Per-Role Backup + Restore Tasks)

Minimum viable artifact set: each of the 4 stateful roles has `tasks/backup.yml` and `tasks/restore.yml`.

- [x] `roles/garage/tasks/backup.yml` — stop container; tar `telemetron_garage_meta` + `telemetron_garage_data` volumes AND `garage_s3_credentials_file`; restart; list-check; stat-size check
- [x] `roles/garage/tasks/restore.yml` — stop container; D-159 WARN; untar into volume mounts; restore `s3-credentials` file; restart
- [x] `roles/prometheus/tasks/backup.yml` — stop container; tar `telemetron_prometheus_data` volume (`/prometheus` path); restart; list-check; stat-size
- [x] `roles/prometheus/tasks/restore.yml` — stop; D-159 WARN; untar; restart
- [x] `roles/grafana/tasks/backup.yml` — stop container; tar `telemetron_grafana_data` volume (`/var/lib/grafana` path, contains `grafana.db`); restart; list-check; stat-size
- [x] `roles/grafana/tasks/restore.yml` — stop; D-159 WARN; untar; restart
- [x] `roles/alertmanager/tasks/backup.yml` — stop container; tar `telemetron_alertmanager_data` volume (`/alertmanager` path, contains `silences` + `nflog` files); restart; list-check; stat-size
- [x] `roles/alertmanager/tasks/restore.yml` — stop; D-159 WARN; untar; restart

### Phase 14 (Orchestrators + UAT)

- [x] `playbooks/backup_docker.yml` — informational PLAY-start banner + `include_role tasks_from: backup` for 4 stateful roles; `backup_continue_on_failure` flag; `--ask-vault-pass` + `--tags <role>` UX; deploy-order (not reverse-order)
- [x] `playbooks/restore_docker.yml` — D-159/D-160 WARN banner + `backup_restore_confirm` gate + `include_role tasks_from: restore` for 4 stateful roles; `backup_restore_from` timestamp var (empty = latest); deploy-order restore (Garage before Loki/Tempo/Mimir consumers)
- [x] Live leviathan round-trip UAT: backup → `undeploy --purge-data` → deploy → restore → smoke signals visible

### Phase 15 (Documentation Cascade + Gate 11)

- [x] `roles/README.md` Gate 11: "every stateful role ships a tested backup + restore path"
- [x] `docs/quickstart.md` `## Backup and restore` section
- [x] Root `README.md` cross-ref to `docs/quickstart.md#backup-and-restore`
- [x] Per-role `## Backup` H2 section in each of the 4 stateful role READMEs
- [x] One-liner "no backup needed" rationale in each stateless role README

---

## Operator UX Conventions Inherited from v1.2.0

The following contracts are established in v1.2.0 and MUST carry over without modification:

| Contract | v1.2.0 Origin | v1.3.0 Application |
|----------|--------------|-------------------|
| `--ask-vault-pass` on all playbooks | `playbooks/deploy_docker.yml` | Required on `backup_docker.yml` + `restore_docker.yml` |
| `--tags <role>` for per-role targeted runs | Phase 11 / D-133 | `--tags garage` backs up only Garage; `--tags prometheus` restores only Prometheus |
| Role-tag-only (no sub-tags) | D-133: `garage` tag only, never `garage-backup` | `tasks/backup.yml` and `tasks/restore.yml` carry only the role tag |
| D-159 WARN template for irreversible ops | Phase 11 / D-159 | `restore_docker.yml` emits `WARNING: irreversible -- <role> restore: <targets>` before each overwrite |
| D-160 PLAY-start banner | Phase 11 / D-160 | `backup_docker.yml`: informational banner (not WARN). `restore_docker.yml`: WARN banner (destructive) |
| Opt-in extra-var for irreversible operations | `telemetron_purge_data=true` | `backup_restore_confirm=true` (required to run `restore_docker.yml`) |
| Conservative-by-default | `undeploy_docker.yml` defaults to no purge | `restore_docker.yml` defaults to bail-out (`backup_continue_on_failure=false`); restore is blocked without `backup_restore_confirm=true` |
| Three-layer doc cascade | Phase 12 | Phase 15 applies same shape: `roles/README.md` gate → quickstart section → per-role README H2 |

---

## Backup Naming Convention — Decision

**Chosen format:** `<role>-<YYYYMMDD>-<HHMMSS>.tar.zst`

Example: `garage-20260602-140000.tar.zst`

**Rationale:**
- Human-readable: operator glancing at `ls /opt/telemetron/backups/garage/` immediately knows which backup is which.
- Filesystem-safe: no colons, no slashes, no ISO 8601 `T` or `Z` that some tools mishandle.
- Lexicographically sortable == chronologically sortable: `sort` and `find -name "garage-*.tar.zst" | sort -r | head -1` both work correctly.
- YYYYMMDD-HHMMSS resolves same-day collisions that Nextcloud's `YYYYMMDD`-only format suffers from.
- UTC assumed (Ansible `{{ now(utc=true, fmt='%Y%m%d-%H%M%S') }}`); no timezone ambiguity in the filename.

**Rejected alternatives:**
- Unix epoch (`garage-1748872800.tar.zst`): Gitea uses this; not human-readable without `date -d @<epoch>`.
- ISO 8601 with `T` and `Z` (`garage-20260602T140000Z.tar.zst`): technically correct but colons in ISO 8601 basic (`T140000Z`) are fine; however the `T` and `Z` are unfamiliar to operators not steeped in RFC 3339. The hyphen separator is more scan-friendly.
- Full ISO 8601 with colons (`garage-2026-06-02T14:00:00Z.tar.zst`): colons are illegal in filenames on Windows (irrelevant for homelab Linux but bad convention to establish).

**Latest-backup resolution on restore:**
`find /opt/telemetron/backups/<role>/ -name "<role>-*.tar.zst" | sort -r | head -1`

This is idiomatic shell, requires no symlink management, and works correctly with the `YYYYMMDD-HHMMSS` format. Ansible `ansible.builtin.find` + `sort` filter achieves the same.

No `<role>-latest.tar.zst` symlink. Symlink management on delete (if the operator manually prunes) creates stale-symlink risk. Timestamp sort is simpler and more robust.

---

## Data Surfaces per Role

What each `tasks/backup.yml` must capture:

| Role | Named Volume(s) | Key Files Inside Volume | Also Backup? |
|------|----------------|------------------------|--------------|
| Garage | `telemetron_garage_meta`, `telemetron_garage_data` | All S3 object data + metadata | YES: also capture `garage_s3_credentials_file` (`/opt/telemetron/garage/s3-credentials`) from host bind-mount |
| Prometheus | `telemetron_prometheus_data` | TSDB blocks + WAL (WAL covers ~2h; include for completeness, cold backup means WAL is quiesced) | No additional host files needed |
| Grafana | `telemetron_grafana_data` | `grafana.db` (SQLite, contains users/orgs/dashboards/alerts state), plugins, sessions | Provisioned config (datasources/dashboards YAML) is NOT included — re-rendered by deploy |
| Alertmanager | `telemetron_alertmanager_data` | `silences` (protobuf), `nflog` (protobuf) | No additional host files needed |

**Implementation note on Garage credential inclusion:** The Garage `tasks/backup.yml` must include the credentials file in the same tarball as the volume data. On restore, `tasks/restore.yml` must restore the credentials file to `garage_s3_credentials_file` BEFORE Garage starts, so that the subsequent Loki/Tempo/Mimir deploy finds the correct S3 key already in place. This is the most critical cross-role dependency in v1.3.0.

---

## Sources

- [Grafana official backup docs](https://grafana.com/docs/grafana/latest/administration/back-up-grafana/) — stop service before SQLite backup; `/var/lib/grafana/grafana.db` is the backup target (HIGH confidence)
- [Gitea backup and restore docs](https://docs.gitea.com/administration/backup-and-restore) — `gitea dump` pattern; stop-before-backup; Unix epoch naming (HIGH confidence)
- [Nextcloud backup docs](https://docs.nextcloud.com/server/stable/admin_manual/maintenance/backup.html) — `occ maintenance:mode`; `YYYYMMDD` naming; rsync data + DB dump (HIGH confidence)
- [VictoriaMetrics vmbackup](https://docs.victoriametrics.com/victoriametrics/vmbackup/) + [vmrestore](https://docs.victoriametrics.com/victoriametrics/vmrestore/) — symmetric backup/restore CLI; stop-before-restore; `YYYYMMDD` naming (HIGH confidence)
- [Prometheus TSDB snapshot API](https://prometheus.io/docs/prometheus/latest/querying/api/#tsdb-admin-apis) — hot snapshot path; cold backup = stop + tar + restart (HIGH confidence, confirmed via devopstales.github.io article)
- [Alertmanager data files — upstream issue #1000](https://github.com/prometheus/alertmanager/issues/1000) + [#1673](https://github.com/prometheus/alertmanager/issues/1673) — `silences` and `nflog` files at `--storage.path`; data directory = `/alertmanager` inside container (HIGH confidence)
- [Suraj Deshmukh: Prometheus backup and restore](https://suraj.io/post/how-to-backup-and-restore-prometheus/) — cold backup procedure; stop → tar TSDB path → restart (MEDIUM confidence)
- [spantaleev/matrix-docker-ansible-deploy](https://github.com/spantaleev/matrix-docker-ansible-deploy) — Ansible Docker project prior art; `--extra-vars` for restore path (MEDIUM confidence)
- [thedatabaseme/docker_backup](https://github.com/thedatabaseme/docker_backup) — cold Docker volume backup with Ansible; stop + tar + restart pattern (MEDIUM confidence)
- Telemetron `roles/garage/defaults/main.yml`, `roles/grafana/defaults/main.yml`, `roles/prometheus/defaults/main.yml`, `roles/alertmanager/defaults/main.yml` — volume names, data paths, credentials file paths (HIGH confidence, source of truth)
- Telemetron `playbooks/undeploy_docker.yml` — v1.2.0 UX contracts: D-159 WARN, D-160 banner, purge flag pattern, `--tags <role>`, `--ask-vault-pass` (HIGH confidence, direct precedent)
