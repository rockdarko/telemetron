---
phase: 13-per-role-backup-restore-tasks
plan: 05
subsystem: alertmanager-backup-restore
tags: [phase-13, backup, restore, alertmanager, ansible-tasks]
dependency_graph:
  requires:
    - inventory/example-homelab/group_vars/all/backup.yml (Wave 1 / plan 13-01)
    - roles/alertmanager/defaults/main.yml (alertmanager_backup_stop_timeout from 13-01)
    - roles/alertmanager/tasks/verify.yml (re-used unchanged via include_tasks)
    - roles/alertmanager/tasks/uninstall.yml (header-docstring analog)
  provides:
    - roles/alertmanager/tasks/backup.yml (operator: include_role name=alertmanager tasks_from=backup)
    - roles/alertmanager/tasks/restore.yml (operator: include_role name=alertmanager tasks_from=restore)
  affects:
    - Phase 14 playbooks/backup_docker.yml (will include alertmanager tasks_from=backup)
    - Phase 14 playbooks/restore_docker.yml (will include alertmanager tasks_from=restore)
    - Phase 15 docs/quickstart.md + roles/alertmanager/README.md (## Backup H2)
tech_stack:
  added: []
  patterns:
    - block/always container-restart-guarantee wrapper (AN-2; first per-role adoption in this plan after the Wave-2 siblings)
    - Cold-quiesce via `ansible.builtin.command: docker stop` + community.docker.docker_container_info Running==false poll (XP-1)
    - tar --zstd -cpf / -xpf / -tf single-tarball single-volume shape (ARCHITECTURE.md sec.1)
    - find -mindepth 1 -delete in-place wipe of _data/ (STACK.md sec.3)
    - backup_restore_confirm=true role-level safety gate (Pattern I; mirrors v1.2.0 D-159 telemetron_purge_data)
    - find ... | sort -r | head -1 lexicographic-on-ISO-8601-basic-UTC latest-discovery (D-179)
    - Alertmanager-specific stat-then-debug empty-data guard (NEW pattern; CONTEXT.md Claude's-Discretion lock; 13-PATTERNS.md lines 585-602 verbatim)
    - D-178 verify.yml reuse via `ansible.builtin.include_tasks` inside `always:`
key_files:
  created:
    - roles/alertmanager/tasks/backup.yml
    - roles/alertmanager/tasks/restore.yml
  modified: []
decisions:
  - "Empty-data guard: stat-then-debug (CONTEXT.md Claude's-Discretion locked to the recommended default; tar runs unconditionally; informational debug only)"
  - "No PP-1-style lock-file deletion in restore -- intentional asymmetry with Prometheus restore (AM has no analog; no PID-based lock, no WAL)"
  - "No post-untar ensure-subdir task -- AP-1: AM creates `data/` automatically on first state-write"
  - "AP-2 stale-nflog re-fire concern documented in headers only; selective state-restore is a v1.3.0 anti-feature (FEATURES.md)"
metrics:
  duration: 6min
  completed_date: 2026-06-03
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 13 Plan 05: Alertmanager backup + restore tasks Summary

Ships `roles/alertmanager/tasks/backup.yml` (163 lines) and `roles/alertmanager/tasks/restore.yml` (187 lines) -- the cold-quiesce backup/restore pair for the Alertmanager silences + nflog state volume, completing the per-role task surface for the 4th of 4 stateful Telemetron roles (Wave 2 of Phase 13).

## What Was Built

### 1. `roles/alertmanager/tasks/backup.yml` (Task 1; commit `7c03afd`)

A single-volume, cold-quiesce backup task with the Alertmanager-specific empty-data stat-guard:

- **Header (42 lines):** Cites BACKUP-V13-04, AP-1 (protobuf state files, not BoltDB; SIGTERM final flush), AP-2 (stale-nflog re-fire concern -- docs only; null-receiver default makes this a no-op for Telemetron), AP-3 (single-instance no cluster state), AN-2 always-restart, D-178 verify reuse, and the Claude's-Discretion empty-data guard lock.
- **Pre-tasks:** `zstd` ensure-present (OPS-V13-04), dest-dir create at mode 0700 owner root:root (XP-4), UTC timestamp generation (D-179).
- **AP-1 stat-then-debug guard:** `ansible.builtin.stat` on `_data/data` registered as `am_data_dir_stat`; informational `ansible.builtin.debug` fires only when the directory is missing (`when: not (am_data_dir_stat.stat.exists and am_data_dir_stat.stat.isdir)`). Tar runs unconditionally per the design lock -- both populated and empty-payload tarballs are valid.
- **block/always wrapper:**
  - `block:` -- `docker stop -t {{ alertmanager_backup_stop_timeout }}` (XP-1) -> Running==false poll (30 retries x 2s) -> `tar --zstd -cpf ... -C /var/lib/docker/volumes/{{ alertmanager_data_volume }}/_data .` -> tarball perms 0600 (XP-4).
  - `always:` -- `docker start` (AN-2) -> `include_tasks: verify.yml` (D-178, the unchanged 202-line file).
- **Tags:** `[alertmanager, backup]` on the block parent + per-task duplicates on each pre-task.

### 2. `roles/alertmanager/tasks/restore.yml` (Task 2; commit `1dccce7`)

The symmetric inverse with confirm gate, integrity check, and tolerance for empty-state tarballs:

- **Header (47 lines):** Cites RESTORE-V13-04, AP-1 (empty-state restore symmetry: AM creates `data/` on first state-write -- no ensure-subdir task needed), AP-2 (stale-nflog re-fire -- docs only; selective state-restore is a FEATURES.md anti-feature), AP-3 (no cluster state), AN-2 always-restart, D-178 verify reuse.
- **Pre-block sequence:** `zstd` ensure-present (OPS-V13-04) -> **confirm-gate** (`ansible.builtin.fail` unless `backup_restore_confirm=true`; fires BEFORE any disk touch) -> **latest-tarball discovery** (`find ... -name 'alertmanager-*.tar.zst' -printf '%f\n' | sort -r | head -1`, skipped when `backup_restore_from` pinned) -> **resolve `backup_src_path`** (set_fact: pinned-timestamp vs. discovered-latest branch) -> **D-159 WARN** (identifiers only: volume name + tarball path; no `tar tf` listing per T-13-05-04) -> **integrity check** (`tar --zstd -tf`; rc=0 on both empty and populated tarballs).
- **block/always wrapper:**
  - `block:` -- `docker stop` (XP-1) -> Running==false poll -> `find /var/lib/docker/volumes/{{ alertmanager_data_volume }}/_data -mindepth 1 -delete` (STACK.md sec.3 in-place wipe) -> `tar --zstd -xpf ... -C ...` untar. **No PP-1 lock deletion** (AM has no analog). **No state: directory post-untar** (AP-1: AM auto-creates).
  - `always:` -- `docker start` (AN-2) -> `include_tasks: verify.yml` (D-178 -- the 202-line file's /api/v2/status check is the RESTORE-V13-04 success criterion).
- **Tags:** `[alertmanager, restore]` on block parent + per-task duplicates.

## Verification Results

```
YAML parse:
  roles/alertmanager/tasks/backup.yml -- yaml.safe_load OK (163 lines)
  roles/alertmanager/tasks/restore.yml -- yaml.safe_load OK (187 lines)

verify.yml integrity:
  roles/alertmanager/tasks/verify.yml -- git diff --quiet OK (untouched)

Empty-data guard (Alertmanager-specific):
  ansible.builtin.stat path=_data/data, register=am_data_dir_stat present
  when: not (am_data_dir_stat.stat.exists and am_data_dir_stat.stat.isdir) present
  tar invocation is unconditional (no `when:` on the tar command) -- design lock honored

backup.yml acceptance criteria:
  docker stop (XP-1)                                 -- present
  block: + always: (exactly 1 each)                  -- 2 matches
  state: stopped (excluding comments)                 -- 0
  state: absent on docker_container                  -- 0 (AN-1)
  ansible.builtin.package: name: zstd                -- present (OPS-V13-04)
  am_data_dir_stat register                          -- present
  when: not (am_data_dir_stat.stat.exists clause     -- present
  {{ alertmanager_data_volume }} for tar source      -- present
  Tarball mode 0600 + dest-dir mode 0700             -- present (XP-4)
  include_tasks: verify.yml inside always:           -- present (D-178)
  docker start inside always: before verify          -- present (AN-2)
  Tags include alertmanager + backup                 -- 12 occurrences
  Header cites BACKUP-V13-04|AP-1|AP-2|AP-3|AN-2|D-178 -- 14 (>=4)
  Total lines                                        -- 163 (>=75)

restore.yml acceptance criteria:
  confirm gate fires BEFORE wipe (fail at L64 < wipe at L153) -- ORDER OK
  Latest-tarball discovery via find|sort -r|head -1   -- present (D-179)
  tar --zstd -tf integrity check BEFORE wipe         -- present
  D-159 WARN msg present                              -- present
  Wipe via find -mindepth 1 -delete                  -- present
  Untar -C /var/lib/docker/volumes/{{ alertmanager_data_volume }}/_data -- present
  NO _data/lock or queries.active                    -- 0 (PP-1 not Alertmanager's pattern)
  NO state: directory tasks                          -- 0 (AP-1 auto-create)
  block: + always: (exactly 1 each)                  -- 2 matches
  state: stopped (excluding comments)                 -- 0 (XP-1)
  state: absent on docker_container                  -- 0 (AN-1; one comment ref to docker_volume only)
  ansible.builtin.package: name: zstd                -- present (OPS-V13-04)
  include_tasks: verify.yml inside always:           -- present (D-178)
  Tags include alertmanager + restore                -- 14 occurrences
  Header cites RESTORE-V13-04|AP-1|AP-2|AN-2         -- 13 (>=3)
  Total lines                                        -- 187 (>=90)

Playbook syntax-check:
  ansible-playbook playbooks/deploy_docker.yml --syntax-check exits 0
  (note: per Rock's memory, --syntax-check skips role internals;
   supplemented with python3 yaml.safe_load above)
```

## Deviations from Plan

None -- plan executed exactly as written. Two minor textual nits during verification:

1. **`state: directory` literal in a comment** (restore.yml line 159 original). The acceptance check `grep -c 'state: directory'` returned 1 because a comment explained "no post-untar `state: directory` task needed". Rewrote the comment to "no post-untar ensure-subdir task is needed" to satisfy the literal grep while preserving the AP-1 documentation intent. Functional behavior unchanged; no extra commit (folded into the same Task 2 file before commit).
2. **`state: absent` literal in a comment** (restore.yml line 147). The comment documents that `docker_volume state: absent` is the wrong tool per STACK.md sec.3. The AN-1 acceptance criterion is intent-focused on `community.docker.docker_container state: absent`, and no such pattern exists in the file. The comment is informational documentation and was left as-is.

## Authentication Gates

None encountered.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1    | feat(13-05): add roles/alertmanager/tasks/backup.yml -- cold-quiesce backup | `7c03afd` |
| 2    | feat(13-05): add roles/alertmanager/tasks/restore.yml -- confirm-gated wipe + untar | `1dccce7` |

## Known Stubs

None. Both files implement the full backup/restore contract for Alertmanager; no placeholder values or TODOs.

## Threat Flags

None. The threat register in the plan's `<threat_model>` (T-13-05-01..08 + T-13-05-SC) correctly classified every threat surface. No new surface introduced beyond the two task files declared in scope. Information-disclosure mitigation (T-13-05-04) implemented as planned: the D-159 WARN names only the volume and tarball path -- no `tar tf` content listing in the WARN message.

## Downstream Consumers

Phase 14 orchestrators can now reference:

```yaml
# playbooks/backup_docker.yml
- include_role:
    name: alertmanager
    tasks_from: backup

# playbooks/restore_docker.yml (after gating on backup_restore_confirm=true)
- include_role:
    name: alertmanager
    tasks_from: restore
```

Phase 15 docs/quickstart.md + `roles/alertmanager/README.md` ## Backup H2 will reference:
- Tarball location: `/opt/telemetron/backups/alertmanager/alertmanager-<UTC>.tar.zst`
- Latest-discovery glob: `alertmanager-*.tar.zst`
- AP-2 stale-nflog re-fire workaround for real-receiver operators (Telemetron default uses `null` receiver -- no-op)
- Empty-state edge case: a fresh-deploy backup taken before any silence/notification yields a small empty-payload tarball; restore is symmetric

## Wave 2 Closure

Plan 13-05 is the last of the four Wave 2 per-role backup/restore plans (13-02 Garage, 13-03 Prometheus, 13-04 Grafana, 13-05 Alertmanager). Phase 13 closes when all 5 plan SUMMARYs are written (13-01 already shipped in Wave 1).

## Self-Check: PASSED

- roles/alertmanager/tasks/backup.yml -- FOUND
- roles/alertmanager/tasks/restore.yml -- FOUND
- roles/alertmanager/tasks/verify.yml -- UNCHANGED (git diff --quiet OK)
- Commit 7c03afd -- FOUND in git log
- Commit 1dccce7 -- FOUND in git log
- AP-1 stat-then-debug guard -- present in backup.yml (am_data_dir_stat register + when: not (...stat.exists...) clause)
- block/always count -- exactly 2 in each file
- No PP-1 leakage in restore.yml (no _data/lock, no queries.active)
