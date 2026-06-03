# Research Summary -- Telemetron v1.3.0 Backup & Restore

**Project:** Telemetron
**Milestone:** v1.3.0 -- Backup & Restore (cold-quiesce model)
**Researched:** 2026-06-02
**Confidence:** HIGH

## Executive Summary

Telemetron v1.3.0 adds a cold-quiesce backup and restore path for the 4 stateful roles in
the existing 12-role Docker stack: Garage, Prometheus, Grafana, and Alertmanager. This is a
brownfield milestone -- the stack ships, leviathan is live, and the 8 stateless roles carry
zero operator state worth backing up. The design is locked: stop containers, tar Docker
volumes with zstd compression, write dated tarballs to `/opt/telemetron/backups/<role>/`,
restart containers. No encryption, no off-host push, no incremental chains, no retention
pruning -- those are operator responsibility.

Two decisions are critical-path and non-negotiable. First, the Garage backup must include the
`s3-credentials` host file (a bind-mount outside both Docker volumes) alongside the two
named volumes. Without this file, a post-restore `deploy_docker.yml` regenerates a new S3
key that Loki, Tempo, and Mimir do not know about, requiring a full re-bootstrap. Second,
the stop-quiesce step in every backup and restore task must use
`ansible.builtin.command: docker stop` + a `docker_container_info` poll loop -- NOT
`community.docker.docker_container state: stopped`. The module's `state: stopped` strips
volume and mount metadata from the container; a subsequent `state: started` brings up the
container without its mounts, silently orphaning data. This is live-UAT-only catchable.

The 3-phase split is right-sized. Phase 13 writes 8 task files (4 roles x backup + restore).
Phase 14 writes the two orchestrator playbooks and runs the leviathan HUMAN-UAT round-trip
(backup -> purge-data undeploy -> redeploy -> restore -> smoke signals visible). Phase 15
runs the doc cascade: Gate 11 in `roles/README.md`, quickstart section, per-role README H2,
stateless role README one-liners. The leviathan live round-trip is the only gate that
validates end-to-end correctness -- v1.1.0 and v1.2.0 both proved that static verification
misses output-format and Docker-state regressions.

---

## Key Findings

### Stack (see STACK.md for full detail)

No new Ansible collections or Docker images required.

| Decision | Choice | Notes |
|----------|--------|-------|
| Compression | `tar --zstd` / `.tar.zst` | GNU tar 1.34 on all targets; `zstd` requires one `ansible.builtin.package` ensure-present task (not pre-installed on Ubuntu 22, Debian 12, or RHEL 9) |
| Volume snapshot | `ansible.builtin.command: tar` as root on host `_data/` path | Docker local-driver path is stable in practice; container must be stopped first |
| Restore wipe | `find {{ volume_data_path }} -mindepth 1 -delete` then untar | Preserves the Docker volume object; `docker_volume state=absent` is wrong here |
| Garage credentials | `{{ garage_s3_credentials_file }}` is inside `garage_config_dir`; captured when config dir is included in tar | THE critical Telemetron-specific finding -- see STACK.md section 4 |
| Prometheus WAL | Include WAL in tarball | Cold SIGTERM flushes WAL cleanly; excluding WAL makes the backup LESS accurate |
| Grafana SQLite WAL | No action needed | Grafana OSS 13 defaults `wal = false`; no `-wal`/`-shm` sidecar files on clean shutdown |
| Alertmanager state | Tar entire volume | SIGTERM triggers final maintenance flush; `silences` and `nflog` are current at stop time |

What NOT to add: restic, BorgBackup, rclone, age/gpg, `garage meta snapshot`,
`community.general.archive`, helper Alpine containers, `docker cp`. Each exclusion traces to
a locked PROJECT.md decision or a known race class from prior phases.

### Features (see FEATURES.md for full detail)

**Table stakes -- all must ship in v1.3.0:**

| Feature | Key Detail |
|---------|-----------|
| `tasks/backup.yml` + `tasks/restore.yml` for 4 stateful roles | Gate 11 mirrors Gate 10 shape |
| `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` | Symmetric pair; same invocation UX as `deploy_docker.yml` |
| Tarball naming: `<role>-YYYYMMDD-HHMMSS.tar.zst` | UTC, human-readable, lexicographically == chronologically sortable |
| Destination: `/opt/telemetron/backups/<role>/` mode 0700, tarballs mode 0600 | Per-role subdirs; no manifest file |
| Latest-tarball default on restore; `backup_restore_from=<timestamp>` to pin | `find + sort -r + head -1` -- no symlink management |
| `backup_restore_confirm=true` gate | Direct mirror of `telemetron_purge_data=true`; without it, restore is a misfire risk |
| `backup_continue_on_failure=true` opt-in | Bail-out default; opt-in override per D-148 |
| D-159 WARN before each destructive restore task | Exact contract: `WARNING: irreversible -- <role> restore: <targets>` |
| Tarball list-check + stat-size check after creation | `tar tf <archive>` + `failed_when: stat.size == 0` |
| Live leviathan HUMAN-UAT round-trip | 7-step: deploy -> smoke -> backup -> purge-data undeploy -> redeploy -> restore -> re-smoke |
| Documentation cascade (Gate 11 shape) | `roles/README.md` gate + quickstart section + per-role README H2 + stateless one-liners |

Deferred (v1.3.x or later): SHA256 checksum files, per-role timestamp pins,
`backup_before_restore` auto-snapshot, manifest.json, `<role>-latest` symlink.

Anti-features (explicitly excluded): off-host backup push, encryption at rest, automatic
retention pruning, incremental backups, hot backup via component APIs, cross-version migration,
backup of stateless roles.

### Architecture (see ARCHITECTURE.md for full detail)

**Per-role backup task shape (7 tasks):**

```
1. Pre-flight: assert destination dir exists (mode 0700)
2. Pre-flight: assert disk free space >= 1.5x volume size
3. Pre-flight: record timestamp as set_fact
4. Quiesce: docker stop <name> + docker_container_info poll (NOT state: stopped)
5. Snapshot: tar --zstd -cpf <dest> <volume _data dir> [+ config_dir for Garage]
6. Restart: docker start <name> + verify.yml
7. Verify: include_tasks: verify.yml
```

Wrap steps 4-5 in an Ansible `block`/`rescue`/`always` so the container restarts even on
backup failure. This prevents leaving containers stopped on bail-out.

**Per-role restore task shape (9 tasks):**

```
1. Pre-flight: stat backup source path (fail clearly if missing)
2. Pre-flight: tar tf integrity check
3. WARN: D-159 irreversible pattern
4. Gate: fail unless backup_restore_confirm=true (in the role task, not only orchestrator)
5. Quiesce: docker stop + docker_container_info poll
6. Clear: find _data/ -mindepth 1 -delete
7. Restore: tar --zstd -xpf <tarball> -C <volume _data dir>
8. Prometheus only: delete /prometheus/lock (and optionally queries.active) after untar
9. Restart: docker start + include_tasks: verify.yml
```

**Orchestrator tag pattern:** `tags: [<role>, backup]` and `tags: [<role>, restore]`.
Cross-cutting `backup` and `restore` tags are legitimate (`--tags backup` backs up all 4
roles). `<role>-backup` sub-tags are wrong per D-133 reasoning.

**Stateless roles:** no task files (Option A). Gate 11 scoped to 4 stateful roles only.
Stateless role READMEs get a `## Backup` H2 one-liner explaining where their data lives.

**Stop order for backup_docker.yml (XP-2 mitigation):** Stop Loki/Tempo/Mimir/OTel/FB
(Garage writers) BEFORE stopping Garage for its snapshot window. Restart Garage first after
snapshot; wait for healthy; then restart writers.

**New shared variables:**

| Variable | Default | Notes |
|----------|---------|-------|
| `backup_dest_root` | `/opt/telemetron/backups` | Root for all backup tarballs |
| `backup_continue_on_failure` | `false` | Opt-in bail-out override |
| `backup_restore_confirm` | `false` | Must be true for restore to run |
| `backup_restore_from` | `""` (empty = latest) | Timestamp string for specific restore |
| `backup_space_factor` | `1.5` | Pre-flight disk check multiplier |

**New files (complete list):**

| File | Phase |
|------|-------|
| `roles/garage/tasks/backup.yml` | 13 |
| `roles/garage/tasks/restore.yml` | 13 |
| `roles/prometheus/tasks/backup.yml` | 13 |
| `roles/prometheus/tasks/restore.yml` | 13 |
| `roles/grafana/tasks/backup.yml` | 13 |
| `roles/grafana/tasks/restore.yml` | 13 |
| `roles/alertmanager/tasks/backup.yml` | 13 |
| `roles/alertmanager/tasks/restore.yml` | 13 |
| `playbooks/backup_docker.yml` | 14 |
| `playbooks/restore_docker.yml` | 14 |

### Critical Pitfalls (see PITFALLS.md for full detail)

**CRITICAL -- must be handled in task code:**

| ID | Pitfall | Prevention | Live-UAT only? |
|----|---------|-----------|---------------|
| GP-1 | Garage LMDB cold-copy is silently corrupted if taken while Garage is running | Full container stop before tar; cold-quiesce is required for correctness | NO |
| XP-1 | `community.docker state=stopped` strips volume/mount specs; restart loses mounts | Use `docker stop` command + `docker_container_info` poll instead | YES |
| PP-1 | Prometheus lock file in restored tarball causes `Locked by other process` startup failure | Delete `/prometheus/lock` after untar, before container start | YES (PID race) |
| AN-1 | Accidental `state: absent` removes container, leaving half-state | Code review checklist; backup tasks use stop/start only, never `state: absent` | YES |
| XP-2 | Loki/Tempo/Mimir crash-loop if Garage stops while they are writing | Stop Garage writers before stopping Garage in backup_docker.yml | YES |

**MODERATE -- handle in task code or docs:**

| ID | Pitfall | Prevention |
|----|---------|-----------|
| GP-3 | Restored LMDB without matching `s3-credentials` file triggers D-146 recovery branch | Include `s3-credentials` in Garage tarball; restore before container start |
| AN-2 | Bail-out on failure leaves stopped container | `block`/`rescue`/`always` in each role backup.yml to always restart |
| GR-2 | Grafana plugins missed if backup only tars `grafana.db` | Tar entire `/var/lib/grafana/` volume |
| XP-3 | Partial restore creates timestamp skew between components | Document: full 4-role backup + restore is the standard path |
| AN-3 | `garage_admin_token` rotation between backup and restore breaks bootstrap verify with 401 | Document in quickstart section |

**LOW / operator education (Phase 15 docs):**

| ID | Pitfall | Where to document |
|----|---------|------------------|
| GP-4 | `garage key list` regex recurrence (Phase 11 class, 4-column format) | Copy regex from `bootstrap.yml` line 179 verbatim if any task parses key list |
| GR-4 | Grafana admin password reverts to backup-time value | Per-role README `## Backup` section |
| AP-2 | Restored stale nflog re-enables dedup memory from backup time | Per-role README; only affects operators with real receivers wired |
| PP-2 | 0-2h WAL data gap on cold backup (Mimir remote_write covers this gap) | Per-role README |

---

## Implications for Roadmap

### Phase 13 -- Per-Role Backup + Restore Tasks

**Rationale:** Orchestrators call `include_role tasks_from: backup/restore`; those files must
exist before orchestrators can run. The 4 roles are independent within Phase 13.

**Recommended sub-order:** Garage (most complex: two volumes + config dir + bootstrap
interaction) -> Prometheus (simplest: single volume; lock-file cleanup is the main nuance)
-> Grafana (full volume tar, SQLite WAL=off, admin password note) -> Alertmanager (simple;
guard for empty `data/` dir on fresh deploy).

**Critical task requirements:**
- All 4 roles: `docker stop` + `docker_container_info` poll, NOT `state: stopped` (XP-1)
- All 4 roles: `zstd` ensure-present task (not pre-installed on Ubuntu/Debian/RHEL)
- All 4 roles: `block`/`rescue`/`always` to always restart container even on failure (AN-2)
- Garage backup: two volumes (`telemetron_garage_meta`, `telemetron_garage_data`) + `garage_config_dir` (which contains `s3-credentials`)
- Prometheus restore: `ansible.builtin.file: path=.../lock state=absent` after untar (PP-1)
- Alertmanager backup: stat-guard for missing `data/` dir on fresh deploys

**Research flag:** No additional research phase needed. All task shapes are fully specified in
ARCHITECTURE.md. PITFALLS.md covers all edge cases. Verify exact Garage on-disk directory
names on leviathan before writing the task (open question 1 in STACK.md).

### Phase 14 -- Orchestrators + Leviathan HUMAN-UAT

**Rationale:** Requires Phase 13 task files to exist. Orchestrators are thin wrappers; the
hard work is the live round-trip UAT, the only gate that catches live-UAT-only pitfalls.

**Orchestrator requirements:**
- `backup_docker.yml`: stop Loki/Tempo/Mimir/OTel/FB BEFORE stopping Garage (XP-2); serial
  role iteration; `ignore_errors` on each `include_role` if `backup_continue_on_failure=true`;
  D-160 informational banner; only 4 stateful roles appear (no no-op entries for stateless roles)
- `restore_docker.yml`: deploy order (Garage first); `backup_restore_confirm` gate in both
  orchestrator AND per-role task; D-159/D-160 WARN banner; document that re-deploy of
  stateless roles after restore is a manual operator step
- Both playbooks: `--ask-vault-pass` required; `--tags <role>` for partial runs

**HUMAN-UAT 7-step round-trip:**

```
1. deploy_docker.yml
2. smoke_test.yml -> record smoke_trace_id + smoke_run_id
3. backup_docker.yml
4. undeploy_docker.yml --extra-vars telemetron_purge_data=true
5. deploy_docker.yml
6. restore_docker.yml --extra-vars backup_restore_confirm=true backup_restore_from=<timestamp>
7. smoke_test.yml with same smoke_trace_id + smoke_run_id -- assert results visible
```

**Live-UAT-only risks the 14-HUMAN-UAT.md must exercise:**

| Risk | UAT Validation |
|------|---------------|
| XP-1: `docker stop`/`start` preserves container config | `docker inspect` volumes/networks before vs after backup run |
| GP-1: Garage LMDB not corrupted by cold tar | Garage starts cleanly post-restore; no LMDB env errors in logs |
| PP-1: Prometheus lock file deleted | Container start succeeds; no `Locked by other process` in logs |
| GP-3: s3-credentials matches restored LMDB | D-146 recovery branch does NOT fire; bootstrap key reuse path takes the clean branch |
| XP-2: Writers stop before Garage stop | Loki/Tempo/Mimir do not crash-loop during Garage stop window in backup run |
| XP-4: Backup dir permissions | `/opt/telemetron/backups/` writable; tarballs are mode 0600 |
| XP-5: Direct `_data/` path access | `tar` via `/var/lib/docker/volumes/` path works on Ubuntu 24.04 |
| AN-1: No containers removed during backup | All 4 containers RUNNING after backup_docker.yml completes |
| GP-4: garage key list regex | If any verify step parses key list, output format matches 4-column expectation |

**Research flag:** No research phase. ARCHITECTURE.md section 7 gives the exact UAT scenario.
The live run is the research.

### Phase 15 -- Documentation Cascade + Gate 11

**Rationale:** Purely additive; does not block Phase 14. Mirrors Phase 12 exactly. Can be
drafted before Phase 14 UAT completes; finalize after UAT to capture any discovered gotchas.

**Gate 11 exact wording:**
> Every stateful role ships `tasks/backup.yml` and `tasks/restore.yml` with a tested
> leviathan round-trip. Every stateless role's README documents that it carries no operator
> state. The 4 stateful roles are: garage, prometheus, grafana, alertmanager.

**Gate 11 is explicitly NOT a blanket requirement on all roles** (contrast with Gate 10).
Stateless roles get a README `## Backup` H2, not an empty task file.

**Key content for quickstart `## Backup and restore`:**
- Backup scope: TSDB, SQLite, S3 objects, silence/nflog state
- Not in scope: `inventory/`, `secrets.yml`, vault password -- operator manages separately
- Garage credential note: `s3-credentials` IS in the backup; post-restore stateless roles find valid credentials without re-bootstrap
- `garage_admin_token` rotation warning: if rotated between backup and restore, bootstrap verify fails 401 (AN-3)
- Prometheus 0-2h WAL gap: expected; Mimir holds continuous long-term data covering the gap
- Grafana admin password reverts to backup-time value; post-restore re-rotation procedure
- Partial restore consistency warning: full 4-role is the standard; partial is for single-component recovery with healthy peers
- Cross-version restore: not tested or supported

**Research flag:** No research phase needed.

### Phase Ordering Rationale

Phase 13 -> Phase 14 is a hard dependency. Phase 15 is independent but gains content from
Phase 14 UAT findings. Recommended: run Phases 13 and 15 in parallel, gate Phase 14 on
Phase 13 completion, close Phase 15 after Phase 14 UAT.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack -- compression, tar mechanics | HIGH | GNU tar release notes + distro package pages verified |
| Stack -- Garage LMDB cold-copy safety | HIGH | Official Garage recovery docs quoted verbatim |
| Stack -- Prometheus WAL on SIGTERM | MEDIUM-HIGH | Official docs confirm cold backup semantics; exact flush guarantee is behavioral evidence |
| Stack -- Grafana SQLite WAL=off default | HIGH | `defaults.ini` in official Grafana repo verified |
| Stack -- Alertmanager SIGTERM flush | HIGH | Source code `nflog.go` + `silence/silence.go` reviewed directly |
| Features | HIGH | Prior-art convergence (Gitea, Nextcloud, vmbackup, Grafana Labs) + v1.2.0 UX contracts |
| Architecture -- task shapes | HIGH | Derived from v1.2.0 source files; no new patterns invented |
| Architecture -- `state: stopped` defect | MEDIUM | GitHub issue #791 closed; fix status in community.docker v5.x unconfirmed; `docker stop` native is safe regardless |
| Pitfalls | HIGH | Mix of official docs, source code review, and empirical v1.1.0/v1.2.0 history |

**Overall confidence:** HIGH

### Gaps to Address During Phase 13

1. **Garage LMDB directory name on leviathan** -- verify actual `ls /var/lib/garage/meta/`
   output on leviathan before writing the backup task. Expected: `db.lmdb/` subdirectory.
   (STACK.md open question 1)

2. **Alertmanager `data/` directory on fresh deploy** -- verify whether `data/nflog` and
   `data/silences` exist on leviathan before any alert fires. Backup task needs a stat guard.
   (STACK.md open question 2)

3. **Prometheus `.tmp` files after clean stop** -- run
   `find .../telemetron_prometheus_data/_data/ -name '*.tmp'` after `docker stop` on leviathan
   to confirm none present. Expected: none from clean SIGTERM.
   (STACK.md open question 3)

4. **Garage backup: single tarball vs two tarballs** -- ARCHITECTURE.md notes both are
   acceptable. Decide in Phase 13 and document in backup.yml header comment.
   Recommendation: single tarball (simpler restore).

5. **community.docker v5.x `state: stopped` fix status** -- use `docker stop` + poll
   unconditionally regardless; do not attempt `state: stopped` as a fallback.

---

## Sources

See `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md` for full
source lists. Key sources:

### HIGH confidence
- Garage HQ recovery docs -- LMDB cold-copy safety (GP-1, GP-2)
- Alertmanager source: `nflog.go` + `silence/silence.go` -- protobuf format, SIGTERM flush (AP-1)
- Prometheus storage docs + Vernekar TSDB deep-dive -- WAL architecture, cold backup (PP-2)
- Grafana `defaults.ini` (GitHub) -- `wal = false` default confirmed (GR-1)
- Grafana official backup docs -- shutdown requirement, plugin dir inclusion (GR-2)
- Telemetron `roles/garage/tasks/bootstrap.yml` -- D-112 credential format, D-146 recovery branch (GP-3)
- Phase 11 VERIFICATION.md -- G-01 closure, live-UAT-only regression class confirmed (GP-4, XP-1)

### MEDIUM confidence
- community.docker GitHub issue #791 -- `state: stopped` strips volume specs (XP-1)
- Prometheus GitHub issues #2689, helm-charts #2872 -- TSDB lock file behavior (PP-1)
- Docker volume `_data/` path stability -- implementation detail; stable in practice

---
*Research completed: 2026-06-02*
*Ready for roadmap: yes*
