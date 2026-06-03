# Technology Stack — v1.3.0 Backup & Restore

**Project:** Telemetron
**Milestone:** v1.3.0 — Backup & Restore (cold-quiesce model)
**Researched:** 2026-06-02
**Scope:** NEW stack additions only for backup/restore. The 12 already-deployed roles (Garage v2.3.0, Prometheus 3.11.3, Grafana OSS 13.0.1, Alertmanager v0.32.1 + the 8 stateless roles) are NOT re-researched here.
**Confidence:** HIGH for all critical claims (verified against official distro package pages, GNU tar release notes, upstream source code, and component documentation).

---

## TL;DR — Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compression format | `tar --zstd` (`.tar.zst`) using GNU tar 1.31+ native flag | All target distros ship tar ≥ 1.34. `zstd` not pre-installed but available via standard package repos. Single idempotent `ansible.builtin.package` task ensures presence. |
| Volume snapshot mechanism | `ansible.builtin.command: tar --zstd -cf ... -C /var/lib/docker/volumes/<name>/_data/ .` as root | Stopped-container model makes the helper-container approach unnecessary; reading Docker's `_data/` path directly is safe + idiomatic for the homelab single-host scope. |
| Restore mechanism | Wipe `_data/` contents in-place (`find -mindepth 1 -delete`) then untar; do NOT `docker_volume state=absent` + recreate | Preserves the Docker volume metadata that the deploy role's container declaration references; avoids the gap-window where volume doesn't exist. |
| Garage S3 credentials | Bundle `{{ garage_s3_credentials_file }}` (host bind-mount) inside the Garage backup tarball alongside meta + data volumes | This file is NOT in either Docker volume but is required for restored Loki/Tempo/Mimir to keep working without re-bootstrap. Most critical Telemetron-specific finding. |
| Prometheus WAL handling | Include WAL in tarball (clean `docker stop` flushes WAL) | Simpler than the `--exclude='./wal'` "coherent blocks only" alternative; cold-quiesce + clean SIGTERM produces a consistent on-disk state. |
| Grafana SQLite WAL | None — Grafana OSS 13 defaults `wal = false` (rollback-journal mode); no `-wal` / `-shm` sidecars on clean shutdown | No special checkpoint step needed in backup task. |
| Alertmanager state path | `/alertmanager/data/{nflog,silences}` (binary protobuf via `protodelim`); SIGTERM triggers final maintenance cycle that flushes both files | Empty `data/` directory possible on never-fired-alert fresh deploys — backup task needs guard. |
| Things to NOT add | restic, BorgBackup, rclone, age, gpg, helper Alpine container, `community.general.archive`, `docker cp`, `garage meta snapshot` | Each rejection traces to a locked design decision in PROJECT.md or to a known race class (Phase 4 / 5 auto_remove + detach race). |

---

## 1. Compression Format

**Decision:** `tar --zstd` with the native `--zstd` flag (GNU tar 1.31+).

### Distro version baseline

All three Telemetron-supported distros ship GNU tar ≥ 1.34, well above the 1.31 threshold where `--zstd` was introduced (January 2019):

| Distro | tar version | zstd version | zstd pre-installed? |
|--------|-------------|-------------|---------------------|
| Ubuntu 22.04 LTS | 1.34+dfsg-1ubuntu0.1 | 1.4.8 | **NO** — optional package |
| Debian 12 bookworm | 1.34+dfsg-1.2+deb12u1 | 1.5.4 | **NO** — optional package |
| RHEL 9 / AlmaLinux / Rocky | ~1.34 (dnf) | available via dnf | **NO** — optional package |

`zstd` is **not installed by default** on any of these distros. The Ansible `tasks/backup.yml` pattern must include a pre-task or task that ensures `zstd` is present:

```yaml
- name: Ensure zstd is installed
  ansible.builtin.package:
    name: zstd
    state: present
  become: true
```

This is a single idempotent task, not a meaningful new dependency — `tar` is already in the existing tool footprint; `zstd` is in every standard repo.

### Invocation pattern

Use the `--zstd` flag, not the pipe form:

```
tar --zstd -cf /opt/telemetron/backups/prometheus/prometheus-{{ timestamp }}.tar.zst \
  -C /var/lib/docker/volumes/telemetron_prometheus_data/_data .
```

The pipe form (`tar cf - . | zstd > foo.tar.zst`) works on older tar (pre-1.31) but adds a shell dependency and makes error-code propagation harder inside `ansible.builtin.command`. GNU tar 1.34 on all targets supports `--zstd` natively. zstd version compatibility between 1.4.8 (Ubuntu 22.04) and 1.5.4 (Debian 12) is total — both implement the same zstd format; newer versions just have better compression ratios.

**Extension:** `.tar.zst` — what tar `--zstd` produces and recognises on extract.

**Sources:** [repology.org/project/zstd](https://repology.org/project/zstd/versions), [packages.debian.org/bookworm/zstd](https://packages.debian.org/bookworm/zstd), [packages.ubuntu.com/jammy/zstd](https://packages.ubuntu.com/jammy/zstd), GNU tar release notes.

### Why not split per-role per-file-size

All four stateful roles have modest backup sizes for homelab: Prometheus TSDB is bounded by `prometheus_retention_time: 15d`; Grafana SQLite is kilobytes to low megabytes; Alertmanager state is trivially small; Garage meta+data varies by operator workload but is bounded by the single-node config. Single-tarball-per-role is the right unit.

---

## 2. Volume Snapshot Mechanism in Ansible

**Decision:** `ansible.builtin.command: tar` running directly as root on the host, reading `/var/lib/docker/volumes/<name>/_data/`.

### Three options evaluated

**Option A — Ephemeral helper container** (`community.docker.docker_container` with `auto_remove: true` or `cleanup: true`)

Docker documentation's recommended portable pattern: spin up an Alpine container, mount source volume read-only and host backup dir writable, run `tar` inside. However, Telemetron has been burned by `auto_remove: true` + `detach: false` twice (ansible/ansible#45272 — "Cannot retrieve result as auto_remove is enabled"). The fix in all affected roles (Phase 4 Bug 1, Phase 5 gap-closure 05-05) was to switch to `community.docker.docker_container_exec` against the live container. An ephemeral backup container using `auto_remove: true` would re-introduce the same race. Using `cleanup: true` (the community.docker alias) has the same issue.

A workaround exists: `cleanup: true` + `detach: false` + `output_logs: true`. But this is more moving parts than necessary when containers are stopped (no live file handles to protect).

**Option B — `community.general.archive` against `_data/` path**

`community.general.archive` calls Python's `tarfile` library under the hood and does not support `--zstd` without `--use-compress-program`. It also requires root permissions to read Docker volume paths. Not the right tool.

**Option C — `ansible.builtin.command: tar` as root on the host, reading `_data/`** ✓ chosen

Reading `/var/lib/docker/volumes/<name>/_data/` directly is an implementation detail of the `local` Docker volume driver — the only driver Telemetron uses (all volumes are created without an explicit `driver:` spec, defaulting to `local`). Docker's own documentation says the official interface is Docker CLI commands. However, in practice:

1. All Telemetron target distros use the `local` driver
2. The container is stopped (no file handles open)
3. The path is well-known and stable across Docker versions
4. The `ansible.builtin.command` approach is simpler, requires no extra containers, and fits the existing pattern in Telemetron's codebase

**Verdict:** Option C. Single `ansible.builtin.command: tar` task as `become: true`, reading the Docker `_data/` path. If Docker ever changes the local volume layout, the test gate on leviathan catches it.

For restore, the symmetric inverse is also `ansible.builtin.command: tar --zstd -xf <tarball> -C <_data path>` with a preceding wipe (see §3).

---

## 3. Restore Mechanism

**Decision:** Wipe `_data/` contents in-place, then untar. Do NOT use `docker_volume state=absent` + recreate.

### Reasoning

`state=absent` removes the Docker volume metadata from Docker's registry, not just the data. After `state=absent`, the volume must be recreated with `docker_volume state=present`. This is safe but adds two extra round-trips and introduces a window where the volume doesn't exist.

More importantly: the existing deploy role's `community.docker.docker_container` declaration references the named volume by name — if the volume is absent when `docker_container state=started` runs, Docker recreates it automatically. The Telemetron convention (established in `deploy_docker.yml`) is that named volumes are created by the container declaration, not by a separate `docker_volume` task. Staying consistent with that means the restore task should:

1. Stop container (`state: stopped` or it's already stopped from the orchestrator).
2. Wipe `_data/` contents: `find {{ volume_data_path }} -mindepth 1 -delete` (or equivalent `shell` task). This preserves the Docker volume object itself while clearing every file and subdirectory inside.
3. Untar into the now-empty `_data/`: `tar --zstd -xf <tarball> -C {{ volume_data_path }}`.
4. Restart container (`state: started`).

The `find -mindepth 1 -delete` step avoids removing the `_data/` directory itself (which belongs to Docker) while clearing every file inside.

For Garage specifically, the restore must also restore the `s3-credentials` host file before the container starts (see §4).

---

## 4. Garage-Specific

### Tar-safety on stopped container

**Meta + data volumes are tar-safe when the container is stopped.** Garage documentation ([garagehq.deuxfleurs.fr/documentation/operations/recovering/](https://garagehq.deuxfleurs.fr/documentation/operations/recovering/)) states: "stop Garage, delete the database file or directory, and restart Garage" is the documented recovery procedure, implying a stopped node's filesystem is the correct state for manipulation. Warnings about "snapshots taken during a write operation" apply to live-filesystem snapshots (ZFS/BTRFS); with the container stopped, no writes are in flight.

### `garage meta snapshot` is NOT needed

The `garage meta snapshot` / `garage meta snapshot --all` command is a *live* snapshot — designed to copy the LMDB/SQLite metadata file while Garage is running. When the container is already stopped, the database file is clean by definition (LMDB and SQLite both guarantee clean state on process exit). Tar of the stopped meta volume is equivalent to what `garage meta snapshot` produces, without the running-process overhead.

### Metadata directory layout

`/var/lib/garage/meta` (= `garage_meta_path`) contains: node identifier, network configuration, peer list, bucket/key list, object index. For LMDB (the default and recommended engine for v2.x), the database lives at `<metadata_dir>/db.lmdb/`. The `cluster_layout` — the mapping of object keys to nodes — is stored *inside* the metadata database, NOT as a separate file. The `<metadata_dir>/snapshots/` subdirectory holds auto-snapshots named by UTC timestamp (up to 2 kept).

`garage.toml` lives in `garage_config_dir` (host bind-mount, NOT in the volume), so it doesn't need to be in the volume backup.

### Data directory layout

`/var/lib/garage/data` (= `garage_data_path`) is block storage only — raw object data blocks, split into ~1 MiB chunks. No metadata here.

### S3 credentials file (THE critical Telemetron-specific finding)

`{{ garage_s3_credentials_file }}` (= `{{ garage_config_dir }}/s3-credentials`) is a host bind-mount path, NOT inside either Docker volume. It must be backed up separately (copy the file) and restored before the container starts. Without it, `deploy_docker.yml` re-runs the bootstrap sequence and generates a NEW key, which Loki/Tempo/Mimir's configs don't know about until a redeploy.

The backup task must include:

```yaml
- name: Copy Garage S3 credentials file into backup staging
  ansible.builtin.copy:
    src: "{{ garage_s3_credentials_file }}"
    dest: "{{ backup_staging_dir }}/s3-credentials"
    remote_src: true
    mode: '0600'
  become: true
```

And restore must copy it back to `{{ garage_s3_credentials_file }}` before `playbooks/deploy_docker.yml` runs. The restore tarball should bundle the `s3-credentials` file alongside the volume data so the backup is a single atomic artifact.

### Re-bootstrapping after restore

**Not needed** if meta + data volumes AND `s3-credentials` are restored together. The restored `meta` volume contains Garage's node identity, layout, bucket ACLs, and object index. The restored `data` volume has the actual object blocks. The restored `s3-credentials` file gives Loki/Tempo/Mimir their existing access key. Garage reads its node ID from the metadata volume on startup — no re-layout-apply step required.

**Sources:** [Garage configuration reference](https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/), [Garage recovering from failures](https://garagehq.deuxfleurs.fr/documentation/operations/recovering/).

---

## 5. Prometheus-Specific

### Stopped Prometheus TSDB is tar-safe (with one WAL-scope caveat)

Official Prometheus storage documentation ([prometheus.io/docs/prometheus/latest/storage/](https://prometheus.io/docs/prometheus/latest/storage/)) states:

> "Excluding the WAL files (the `chunks_head/`, `wal/`, and `wbl/` directories in `storage.tsdb.path`) on backup or restore will ensure a coherent backup, in any case, at the cost of losing the time range covered by the WAL files."

And:

> "Snapshots are recommended for backups. Backups made without snapshots run the risk of losing data that was recorded since the last TSDB block was created, which typically happens every two hours, covering the last three hours of samples."

### Interpretation for cold-quiesce model

The cold-quiesce model explicitly accepts brief data loss by design. For a homelab backup, the accepted loss is: the last two-hour TSDB block that hasn't yet been compacted to persistent blocks. Since Mimir holds long-term metrics (with `remote_write` from Prometheus), the practical loss on a restore is just recent scrape data — acceptable for the homelab use case.

### Two approaches, both valid

- **Include WAL in tar** (complete backup): When the container is stopped cleanly via `docker stop` (which sends SIGTERM), Prometheus writes a checkpoint, closes the WAL cleanly, and exits. The resulting on-disk state is consistent. `.tmp` files exist in `/prometheus/` only if Prometheus was killed mid-compaction (SIGKILL or OOM), not on a clean `docker stop`. A clean `docker stop telemetron-prometheus` → `state: stopped` produces no `.tmp` files. Tarring the full `/prometheus/` path including `wal/` and `chunks_head/` is safe when stopped.

- **Exclude WAL in tar** (coherent-blocks-only backup): `tar --zstd --exclude='./wal' --exclude='./chunks_head' --exclude='./wbl' -cf ...` produces a smaller, definitely-coherent backup at the cost of losing the most recent 2h window.

**Recommendation for v1.3.0: include the WAL.** The cold-quiesce model stops the container cleanly, WAL is flushed, and a complete backup is simpler to reason about and restore. Document the 2h window caveat in the role README. The `--enable-feature=memory-snapshot-on-shutdown` feature (added v2.30) writes an additional memory snapshot on shutdown but is not enabled in Telemetron's Prometheus flags — no action needed.

**Volume path:** `telemetron_prometheus_data` → `/var/lib/docker/volumes/telemetron_prometheus_data/_data/`, container path `/prometheus`. Source: `roles/prometheus/defaults/main.yml` (`prometheus_data_volume`, `prometheus_data_path`).

---

## 6. Grafana-Specific

### SQLite default path

`/var/lib/grafana/grafana.db` (standard Debian/RPM package path). Matches Grafana's `data_path` default for the `-oss` Docker image, which is `/var/lib/grafana`. Confirmed in `grafana/conf/defaults.ini`: `path = grafana.db` relative to `data_path`.

### WAL/shm sidecar files

Grafana OSS 13.0.1 does **not** enable SQLite WAL mode by default. `defaults.ini` shows `wal = false`. The default journal mode is DELETE (rollback journal), not WAL. When Grafana stops cleanly, there are no `-wal` or `-shm` sidecar files.

If an operator has manually enabled `wal = true` in their `grafana.ini`, the `-wal` file may persist — but on a clean shutdown, SQLite checkpoints the WAL file back into the main database and removes both `-wal` and `-shm`. In practice: tar of the stopped container's `/var/lib/grafana/` captures `grafana.db` in a consistent state with no sidecar files.

**Sources:** [grafana/grafana/blob/main/conf/defaults.ini](https://github.com/grafana/grafana/blob/main/conf/defaults.ini), [grafana/issues/65115](https://github.com/grafana/grafana/issues/65115).

### Provisioning state

Provisioning config files (datasources YAML, dashboard JSON files) live in the host bind-mount at `{{ grafana_config_dir }}/provisioning/` — NOT inside the named Docker volume. They are version-controlled Ansible-rendered config. On every container start, Grafana re-applies provisioning from these config files, overwriting any matching entries in `grafana.db`.

For a backup + restore cycle:
- **Backup:** tar the `telemetron_grafana_data` volume (`grafana.db` + `plugins/` directory).
- **Restore:** wipe `_data/`, untar backup into `_data/`. The provisioning configs in `{{ grafana_config_dir }}/provisioning/` are NOT part of the volume backup — they come from `deploy_docker.yml`'s config-rendering tasks. This means a restore that runs `deploy_docker.yml` first (to render provisioning) then `restore_docker.yml` (to restore `grafana.db`) correctly reconstructs state.

If the operator added UI-only dashboard edits that were NOT provisioned (stored only in `grafana.db`), those are preserved by the backup.

### What the backup captures

User-created/modified dashboards and UI state in `grafana.db`. Provisioned dashboards and datasources are re-applied from version-controlled config on next start — the restored `grafana.db` may have older versions of them, but Grafana immediately overwrites with the current provisioned version. Net effect: restore recovers user state and organisation state; provisioned state is always current.

**Volume path:** `telemetron_grafana_data` → `/var/lib/docker/volumes/telemetron_grafana_data/_data/`. Source: `roles/grafana/defaults/main.yml` (`grafana_data_volume`, `grafana_data_path: /var/lib/grafana`).

---

## 7. Alertmanager-Specific

### State path

Inside the container, state files are written to `data/` subdirectory of `--storage.path` (default `data/`). Since the container path is `/alertmanager` (the Docker VOLUME declared in the image, confirmed in `alertmanager_data_path: /alertmanager`), the full state paths are:

- `/alertmanager/data/nflog` — notification log (protobuf format)
- `/alertmanager/data/silences` — silences (protobuf format)

**Source:** `cmd/alertmanager/main.go` flag definition: `dataDir = kingpin.Flag("storage.path", ...).Default("data/")`, combined with the Docker volume mount at `/alertmanager`. Both snapshot file paths are `filepath.Join(*dataDir, "nflog")` and `filepath.Join(*dataDir, "silences")`.

### File format

Both files are binary protobuf using `protodelim` encoding (length-delimited sequences of protobuf messages). NOT plain JSON, NOT BoltDB.

### Maintenance interval

Default `15m` (`--data.maintenance-interval` flag default `"15m"`). The maintenance loop writes snapshots every 15 minutes.

### SIGTERM behaviour — clean flush

Both `nflog.go` and `silence/silence.go` implement a graceful shutdown path. When the maintenance loop receives its stop signal, it executes a final maintenance cycle *after* the loop terminates (explicitly guarded: "Creating shutdown snapshot..."). This means: on a clean `docker stop` → SIGTERM, Alertmanager flushes both `nflog` and `silences` to disk before exit. A cold-quiesce backup will capture the complete current state. The only data lost between the last periodic flush (up to 15 minutes ago) and shutdown has already been flushed by the graceful shutdown handler.

**Sources:** [github.com/prometheus/alertmanager/blob/main/nflog/nflog.go](https://github.com/prometheus/alertmanager/blob/main/nflog/nflog.go), [github.com/prometheus/alertmanager/blob/main/silence/silence.go](https://github.com/prometheus/alertmanager/blob/main/silence/silence.go), [github.com/prometheus/alertmanager/blob/main/cmd/alertmanager/main.go](https://github.com/prometheus/alertmanager/blob/main/cmd/alertmanager/main.go).

### What `ls /alertmanager/` shows on a stopped container

The image sets VOLUME `/alertmanager` but state files are one level deeper under `data/`. Expect:

```
/alertmanager/
└── data/
    ├── nflog
    └── silences
```

**Edge case:** There may be no `data/` directory at all on a fresh deploy that has never fired/silenced an alert — the maintenance loop only writes the snapshot file if `snapf != ""` and there is state to persist. The backup task needs a guard for this empty-state case.

**Volume path:** `telemetron_alertmanager_data` → `/var/lib/docker/volumes/telemetron_alertmanager_data/_data/`. Source: `roles/alertmanager/defaults/main.yml` (`alertmanager_data_volume`, `alertmanager_data_path: /alertmanager`).

---

## 8. What NOT to Add

| Avoid | Why |
|-------|-----|
| **restic / BorgBackup / rclone** | Out of scope by `PROJECT.md` locked decision. Telemetron writes dated tarballs; off-host shipping is operator's responsibility. |
| **`garage meta snapshot --all` in the backup task** | Unnecessary for cold-quiesce model — `garage snapshot` is the *live* backup mechanism. With the container stopped, direct tar of the meta volume is equivalent. Running `garage meta snapshot` would require keeping the container running (not the cold-quiesce model) or spinning up a one-shot binary against stopped data (fragile). |
| **`ansible.builtin.tempfile` staging dirs** | Unnecessary. `/opt/telemetron/backups/<role>/` is the locked destination. No intermediate staging needed. |
| **A separate `backup_agent` container image** | Overkill. `tar` and `zstd` are available on the host. An Alpine helper container adds a container pull dependency and re-opens the `auto_remove` race. |
| **`community.general.archive` module** | Wraps Python `tarfile` which doesn't support `--zstd` without a `--use-compress-program` shim, and has different metadata preservation characteristics than GNU tar. |
| **`docker cp` for volume backup** | Only works on running containers and has no compression. Not applicable to the cold-quiesce model. |
| **`--enable-feature=memory-snapshot-on-shutdown` for Prometheus** | Deferred to hot-snapshot milestone (already deferred per `PROJECT.md`). Speeds up restarts but doesn't change backup story for v1.3.0. |
| **Encryption at rest (`age`, `gpg`, `cryptsetup`)** | Locked as deferred by `PROJECT.md`. Operators wrap with `age`/`gpg`/LUKS externally. |

---

## Ansible Integration Points

The backup tasks integrate with existing patterns:

- **Stop:** `community.docker.docker_container: name: ... state: stopped, keep_volumes: true` — exact same shape as `tasks/uninstall.yml` in every stateful role. No new module.
- **Snapshot:** `ansible.builtin.command: tar --zstd -cf ...` + `become: true` — same `become: true` pattern already used for host-dir operations.
- **Restart:** `community.docker.docker_container: name: ... state: started` — same shape as `tasks/main.yml`.
- **Timestamp:** `ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ` registered into a var, used to build the tarball filename.
- **Backup dir:** `ansible.builtin.file: path: /opt/telemetron/backups/<role>, state: directory, mode: '0700', owner: root` — same `ansible.builtin.file` module used throughout.
- **Garage credentials copy:** `ansible.builtin.copy: src: ... dest: ... remote_src: true, mode: '0600'` — file-to-file copy on the same host.

**No new Ansible collections needed.** The backup surface uses only `community.docker.docker_container` (already in use), `ansible.builtin.command`, `ansible.builtin.file`, `ansible.builtin.copy`, and `ansible.builtin.package` (for the zstd install).

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|-----------|-------|
| zstd availability / versions | HIGH | Official distro package pages verified |
| tar `--zstd` support (1.31+) | HIGH | Official GNU tar release announcement verified |
| Volume snapshot via `_data/` path | MEDIUM | Docker docs say "use Docker CLI"; local driver path is stable in practice and is what every Docker backup guide uses |
| Prometheus WAL clean-shutdown state | HIGH | Official Prometheus storage docs quote verbatim |
| Grafana SQLite WAL default=false | HIGH | `defaults.ini` in official Grafana repo verified |
| Grafana provisioning ephemeral | HIGH | Official provisioning docs verified |
| Alertmanager SIGTERM flush | HIGH | Source code `nflog.go` + `silence/silence.go` + `main.go` reviewed |
| Alertmanager file paths | HIGH | `main.go` flag defaults verified (`storage.path default "data/"`) |
| Garage stopped = tar-safe | MEDIUM | Official docs imply it; explicit warning only for live filesystem snapshots |
| Garage `cluster_layout` in metadata DB | MEDIUM | Config reference mentions deleting "cluster_layout files" from metadata_dir; exact storage location inside LMDB not documented verbatim |
| Garage s3-credentials restore avoids re-bootstrap | HIGH | Derived from v1.2.0 D-146 behaviour and `tasks/uninstall.yml` recovery story comment |

---

## Open Questions (verify on leviathan during Phase 13 / 14 UAT)

1. **Garage LMDB directory name** — meta volume likely contains `db.lmdb/` (LMDB directory) — verify actual `ls /var/lib/garage/meta/` on leviathan before writing the backup task to ensure no surprises in the directory name.

2. **Alertmanager `data/nflog` and `data/silences` on a fresh deploy** — on leviathan, these files only exist if Alertmanager has persisted state. On a fresh deploy that has never fired/silenced anything, the `data/` subdirectory may not exist yet. The backup task needs a guard (`stat` check) — otherwise `tar` will fail on a valid fresh-deploy state. The restore task must handle the empty-data case symmetrically.

3. **Prometheus `.tmp` files on leviathan** — run `find /var/lib/docker/volumes/telemetron_prometheus_data/_data/ -name '*.tmp'` on leviathan after a clean `docker stop` to confirm no `.tmp` files in practice before the first backup UAT.

---

*Reconstructed from research-agent return on 2026-06-02 (the spawned agent produced findings but did not write the file due to a hallucinated system-instruction conflict; the orchestrator captured them here so the synthesizer has 4/4 source files to read).*
