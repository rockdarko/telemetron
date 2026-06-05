---
phase: 13-per-role-backup-restore-tasks
plan: 04
subsystem: grafana-backup-restore
tags: [phase-13, backup, restore, grafana]
dependency_graph:
  requires:
    - inventory/example-homelab/group_vars/all/backup.yml (from 13-01)
    - roles/grafana/defaults/main.yml grafana_backup_stop_timeout (from 13-01)
    - roles/grafana/tasks/verify.yml (existing 268-line; reused via include_tasks)
    - roles/garage/tasks/bootstrap.yml lines 21-35 (verbatim docker_container_info poll shape)
    - roles/garage/tasks/purge.yml line 69 (D-159 WARN + gate idiom analog)
  provides:
    - roles/grafana/tasks/backup.yml (cold-quiesce single-volume tarball -- BACKUP-V13-03)
    - roles/grafana/tasks/restore.yml (confirm-gated wipe + untar -- RESTORE-V13-03)
  affects:
    - Phase 14 backup_docker.yml orchestrator (will include_role: name=grafana tasks_from=backup)
    - Phase 14 restore_docker.yml orchestrator (will include_role: name=grafana tasks_from=restore)
    - Phase 14 leviathan round-trip UAT (Grafana is one of 4 stateful roles exercised)
    - Phase 15 docs cascade (GR-4 admin-pw rotation workaround surfaces in roles/grafana/README.md ## Backup)
tech_stack:
  added: []
  patterns:
    - Cold-quiesce backup via ansible.builtin.command docker stop + community.docker.docker_container_info Running==false poll (XP-1 -- never community.docker docker_container stopped-state transition)
    - Single-volume entire-_data/ tar --zstd archive (GR-2 -- captures grafana.db + plugins/ + csv/)
    - block / always restart guarantee (AN-2) wrapping the destructive steps
    - D-178 reuse of existing tasks/verify.yml via ansible.builtin.include_tasks placed inside always:
    - backup_restore_confirm=true per-role hard gate via ansible.builtin.fail (mirrors v1.2.0 D-159 telemetron_purge_data)
    - D-179 latest-discovery via find | sort -r | head -1 against ISO 8601 basic UTC filenames
    - tar --zstd -tf integrity check before wipe (two-layer safety: confirm-gate + content-list)
    - find -mindepth 1 -delete in-place wipe (STACK.md sec.3 -- keeps _data/ root intact)
key_files:
  created:
    - roles/grafana/tasks/backup.yml
    - roles/grafana/tasks/restore.yml
  modified: []
decisions:
  - GR-2: tar the entire _data/ tree (no --exclude) so operator-installed plugins survive a round-trip
  - GR-1: NO PP-1-style lock-file deletion in restore (Grafana SQLite ships wal=false default; rollback-journal mode produces no sidecar files on clean stop; no PID-based lock analog)
  - GR-4: post-restore admin-password rotation workaround documented IN the restore.yml header (grafana-cli admin reset-admin-password) -- operator-facing critical info, not a code-level guard
  - GR-3: provisioning files in {{ grafana_config_dir }}/provisioning/ are NOT in the volume backup -- they live on host bind-mount and re-override grafana.db on container start; documented in backup.yml header
  - D-178: reuse existing 268-line tasks/verify.yml unchanged via include_tasks inside always: (preserves Gate 9 + Gate 9.5 datasource-UID-resolve assertions)
metrics:
  duration: 4min
  completed_date: 2026-06-03
---

# Phase 13 Plan 04: Grafana backup/restore tasks Summary

Ships `roles/grafana/tasks/backup.yml` (143 lines, BACKUP-V13-03) and `roles/grafana/tasks/restore.yml` (195 lines, RESTORE-V13-03), the Grafana half of the Phase 13 per-role backup/restore task surface. Structurally identical to the Prometheus pair shipped by 13-03 MINUS the PP-1 lock-file deletion step (Grafana SQLite has no analog -- WAL OFF by default per GR-1). Both files consume only the shared backup knobs landed by Wave 1 (13-01); zero new variables introduced.

## What Was Built

### 1. roles/grafana/tasks/backup.yml (Task 1 -- BACKUP-V13-03 + OPS-V13-04)

Cold-quiesce single-volume tarball. Stops `telemetron-grafana` via `ansible.builtin.command: docker stop -t {{ grafana_backup_stop_timeout }}` (XP-1: never the community.docker stopped-state transition that strips volume specs per issue #791), polls `community.docker.docker_container_info` until `State.Running == false`, then tars the entire `_data/` tree of the `telemetron_grafana_data` volume into a single zstd archive at `/opt/telemetron/backups/grafana/grafana-<UTC-timestamp>.tar.zst` (mode 0600 -- XP-4). `docker start` + `ansible.builtin.include_tasks: verify.yml` run inside `always:` so the container ALWAYS comes back even on tar failure (AN-2).

Header documents:
- BACKUP-V13-03 requirement + cold-quiesce shutdown rationale (Grafana docs require shutdown for SQLite backup integrity)
- GR-1: Grafana 13.0.1 ships defaults.ini `wal=false`, so no `-wal`/`-shm` sidecars exist on clean stop -- SQLite file is captured consistently via direct tar
- GR-2: entire `_data/` tree (NOT just `grafana.db`) so operator-installed plugins under `plugins/` survive the round-trip
- GR-3: provisioning files live on host bind-mount at `{{ grafana_config_dir }}/provisioning/`, NOT in the volume; re-applied on every container start (no special handling needed)
- GR-4: admin password reverts to backup-time value on restore (GF_SECURITY_ADMIN_PASSWORD is FIRST-BOOT-ONLY per RESEARCH sec.2.1 Risk 2) -- workaround documented for operator
- AN-2 always-restart guarantee, D-178 verify.yml reuse, D-179 timestamp format

Acceptance criteria all green:
- YAML parses cleanly
- 1 `block:` + 1 `always:` (exactly)
- No `state: stopped` outside comments (XP-1)
- No `state: absent` on `community.docker.docker_container` (AN-1)
- `tar --zstd -cpf ... -C /var/lib/docker/volumes/{{ grafana_data_volume }}/_data .` with no `--exclude` flag (GR-2 -- entire volume)
- Tarball mode 0600, dest dir 0700 (XP-4)
- `include_tasks: verify.yml` inside `always:` (line 139) AFTER `docker start` (line 128) -- D-178
- Header cites BACKUP-V13-03, GR-1, GR-2, GR-4, AN-2, D-178 (12 hits across required tags)
- 143 total lines (>= 70 floor)

### 2. roles/grafana/tasks/restore.yml (Task 2 -- RESTORE-V13-03 + OPS-V13-04)

Confirm-gated wipe + untar. Hard-fails via `ansible.builtin.fail` unless operator passes `--extra-vars backup_restore_confirm=true` (per-role gate so a custom `include_role: name=grafana tasks_from=restore` from outside Phase 14's orchestrator still enforces confirmation -- mirrors v1.2.0's D-159 `telemetron_purge_data=true` contract). Latest tarball auto-discovered via `find {{ backup_dest_root }}/grafana/ -name 'grafana-*.tar.zst' -type f -printf '%f\n' | sort -r | head -1` (D-179: lexicographic sort is chronological because filenames use ISO 8601 basic UTC `YYYYMMDDTHHMMSSZ`), or operator pins via `backup_restore_from=<timestamp>`. `set_fact: backup_src_path` resolves either branch. `tar --zstd -tf` content-lists the tarball BEFORE any destructive step -- a corrupt archive aborts the play with the live volume untouched.

Block body: `docker stop` + `Running==false` poll, then `find /var/lib/docker/volumes/{{ grafana_data_volume }}/_data -mindepth 1 -delete` wipes contents in-place (STACK.md sec.3 -- keeps `_data/` root intact so Docker doesn't lose the volume), then `tar --zstd -xpf {{ backup_src_path }} -C /var/lib/docker/volumes/{{ grafana_data_volume }}/_data`. Always body: `docker start` + `include_tasks: verify.yml` (D-178; the 268-line verify.yml validates the 4 datasource UIDs resolve in-network -- the RESTORE-V13-03 success criterion 3 contract).

**Plan-specific reminder honored**: NO PP-1-style lock-file deletion step. Grafana SQLite ships `wal=false` (GR-1) -- there are no `-wal`/`-shm` sidecars on clean stop, and there is no PID-based lock file analog to Prometheus's stale-PID-tracked one. Adding a `state: absent` no-op against a non-existent file would be cargo-culted.

Header documents the GR-4 admin password rotation workaround prominently:
```
docker exec telemetron-grafana grafana-cli admin reset-admin-password '<new>'
```
This is the operator-facing CRITICAL info -- restored grafana.db carries the backup-time bcrypt hash, and GF_SECURITY_ADMIN_PASSWORD is FIRST-BOOT-ONLY (won't seed the DB on restart against an existing grafana.db).

Acceptance criteria all green:
- YAML parses cleanly
- Confirm gate fires BEFORE wipe: `fail:` at line 74, wipe `-mindepth 1 -delete` at line 161 -- gate-then-destruct ordering verified by awk
- `tar --zstd -tf` integrity check BEFORE wipe: line 126 vs wipe line 161 -- verified by awk
- D-179 latest-discovery via `find | sort -r | head -1`
- D-159 WARN message names identifiers only (`{{ grafana_data_volume }}` + `{{ backup_src_path }}`) -- no `tar tf` content listing in WARN (T-13-04-04)
- Wipe via `find ... -mindepth 1 -delete` against `_data/`
- **NO `_data/lock` or `queries.active` references** (grep returns 0) -- confirms PP-1 not cargo-culted
- No `state: stopped` (XP-1), no `state: absent` on `community.docker.docker_container` (AN-1)
- 1 `block:` + 1 `always:` (exactly)
- `include_tasks: verify.yml` inside `always:` at line 191 (D-178)
- Tags include both `grafana` and `restore` (7 each across all tasks)
- Header cites GR-4 + `grafana-cli admin reset` (2 hits)
- Header cites RESTORE-V13-03, GR-1/GR-2/GR-3, AN-2 (12 hits across required tags)
- 195 total lines (>= 90 floor)

## Verification Results

```
YAML parse:
  roles/grafana/tasks/backup.yml -- parses OK
  roles/grafana/tasks/restore.yml -- parses OK

verify.yml untouched:
  git diff --quiet roles/grafana/tasks/verify.yml -- clean (268 lines preserved)

Playbook syntax:
  ansible-playbook playbooks/deploy_docker.yml --syntax-check -- exits 0
  (per Rock's memory note, --syntax-check skips role-internals;
   YAML parse covers role-internal validation)

XP-1 compliance:
  grep -v '^#' .../backup.yml | grep -c 'state: stopped' -- 0
  grep -v '^#' .../restore.yml | grep -c 'state: stopped' -- 0
  Both files use ansible.builtin.command: docker stop

AN-1 compliance:
  No 'state: absent' on community.docker.docker_container in either file
  (the one `state: absent` mention in restore.yml header is a comment
   explaining why a PP-1-style cleanup is NOT added)

AN-2 compliance:
  backup.yml: docker start at line 128, verify include at line 139 -- both inside always:
  restore.yml: docker start + verify include both inside always:

PP-1 absence (Grafana-specific -- plan-specific reminder):
  grep -c '_data/lock\|queries.active' restore.yml -- 0
  No cargo-culted Prometheus pitfall guard in Grafana
```

## Deviations from Plan

**[Rule 3 - Blocking issue, post-write]** The plan's automated verify command for both tasks used `! grep -qE 'state:\s*stopped' <file>` and (for restore) `! grep -q '_data/lock' <file>` without filtering comment lines via `grep -v '^#'`. The acceptance criteria text correctly uses `grep -v '^#'`, but the verify chain does not. My initial drafts contained those literal strings inside header comments explaining XP-1 and GR-1, which caused the `grep -q` chains to match unintended.

Resolution (no semantic change):
- backup.yml: rephrased the XP-1 comment from "NEVER `community.docker.docker_container state: stopped`" to "NEVER the community.docker docker_container module's stopped-state transition" -- same teaching, no literal `state: stopped` substring
- restore.yml: rephrased the GR-1 explanation from "no PID-based lock file like Prometheus's `_data/lock`" to "no PID-based lock file like Prometheus's stale-PID-tracked one under the TSDB root" -- same teaching, no literal `_data/lock` substring

Both files now pass the literal verify commands as written. No code/behavior change; comment wording only.

## Authentication Gates

None encountered (Ansible files, no live Docker / network operations during this plan).

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | feat(13-04): add roles/grafana/tasks/backup.yml cold-quiesce single-volume tarball | `caa628b` |
| 2 | feat(13-04): add roles/grafana/tasks/restore.yml confirm-gated wipe + untar | `33e3121` |

## Known Stubs

None. Both files are concrete, executable Ansible tasks with no placeholder data, no TODO markers, no "coming soon" text. Variables they reference (`backup_dest_root`, `grafana_data_volume`, `grafana_container_name`, `grafana_backup_stop_timeout`, `backup_restore_confirm`, `backup_restore_from`) all resolve to concrete defaults via the Wave 1 (13-01) foundation.

## Threat Flags

None new. Every threat enumerated in the plan's `<threat_model>` (T-13-04-01 through T-13-04-08 + T-13-04-SC) is mitigated by the shipped code -- specifically:

- T-13-04-01 (tarball corruption): `tar --zstd -tf` integrity check before wipe
- T-13-04-02 (DoS via accidental restore): two-layer safety (`backup_restore_confirm=true` + integrity check)
- T-13-04-03 (info disclosure via grafana.db secrets): tarball mode 0600, dest dir 0700
- T-13-04-04 (info disclosure via WARN content): WARN msg names `{{ grafana_data_volume }}` + `{{ backup_src_path }}` only -- no `tar tf` listing leakage
- T-13-04-05 (silent admin-password revert): GR-4 workaround documented in header
- T-13-04-06 (plugin loss): entire `_data/` tar with no `--exclude` flag enforced by acceptance criteria
- T-13-04-07 (XP-1 mount-spec strip): explicit `ansible.builtin.command: docker stop` + `docker_container_info` Running==false poll
- T-13-04-08 (`become: true` privilege): accepted by plan
- T-13-04-SC (supply-chain): only `zstd` via OS package manager; no npm/pip/cargo install

No new surface introduced beyond what the plan's threat model anticipated.

## Self-Check: PASSED

- `roles/grafana/tasks/backup.yml` -- FOUND (143 lines)
- `roles/grafana/tasks/restore.yml` -- FOUND (195 lines)
- Commit `caa628b` -- FOUND in git log (worktree-agent-aa015755e0f5243b6)
- Commit `33e3121` -- FOUND in git log (worktree-agent-aa015755e0f5243b6)
- `roles/grafana/tasks/verify.yml` -- UNCHANGED (`git diff --quiet` returns 0)
- `ansible-playbook playbooks/deploy_docker.yml --syntax-check` -- exits 0
- Plan-specific reminder honored: NO PP-1-style lock-file deletion step in restore.yml
- Wave 1 contract honored: zero modifications to STATE.md, ROADMAP.md, or other shared orchestrator artifacts
