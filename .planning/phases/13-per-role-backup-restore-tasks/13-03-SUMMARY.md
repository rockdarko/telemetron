---
phase: 13-per-role-backup-restore-tasks
plan: 03
subsystem: prometheus-backup-restore
tags: [phase-13, prometheus, backup, restore, tsdb]
dependency_graph:
  requires:
    - inventory/example-homelab/group_vars/all/backup.yml (plan 13-01 -- backup_dest_root, backup_restore_confirm, backup_restore_from)
    - roles/prometheus/defaults/main.yml (plan 13-01 -- prometheus_backup_stop_timeout)
    - roles/prometheus/tasks/verify.yml (existing 152-line file -- re-used unchanged via include_tasks)
    - roles/prometheus/tasks/uninstall.yml (header docstring shape analog)
  provides:
    - roles/prometheus/tasks/backup.yml (BACKUP-V13-02 -- cold-quiesce TSDB tarball)
    - roles/prometheus/tasks/restore.yml (RESTORE-V13-02 -- confirm-gated wipe+untar with PP-1 fix)
  affects:
    - Phase 14 backup_docker.yml orchestrator (will `include_role: name=prometheus tasks_from=backup`)
    - Phase 14 restore_docker.yml orchestrator (will `include_role: name=prometheus tasks_from=restore`)
    - Phase 14 leviathan round-trip HUMAN-UAT (validates the PP-1 lock-file path on real hardware)
    - Phase 15 docs cascade (roles/prometheus/README.md "## Backup" H2, docs/quickstart.md)
tech_stack:
  added: []
  patterns:
    - block/always wrapper around cold-quiesce stop+tar (first Telemetron use; AN-2 guarantees restart on tar failure)
    - ansible.builtin.command: docker stop -t (XP-1; never community.docker docker_container state=stopped which strips volume specs)
    - find -mindepth 1 -delete wipe inside _data (STACK.md sec.3; docker_volume state=absent is the wrong primitive here)
    - tar --zstd -tf integrity check BEFORE wipe (T-13-03-02 mitigation)
    - Pattern I confirm-gate via ansible.builtin.fail with when: not (var | default(false) | bool)
    - ansible.builtin.set_fact dual-branch resolution for source path (latest-discovery vs pinned backup_restore_from)
    - ISO 8601 basic UTC timestamps (D-179: YYYYMMDDTHHMMSSZ) -> lexicographic find|sort -r|head -1 latest-discovery
    - PP-1 ansible.builtin.file: state: absent on _data/lock AFTER untar AND BEFORE always-clause docker start (NEW, unique to Prometheus)
key_files:
  created:
    - roles/prometheus/tasks/backup.yml (136 lines)
    - roles/prometheus/tasks/restore.yml (208 lines)
    - .planning/phases/13-per-role-backup-restore-tasks/13-03-SUMMARY.md
  modified: []
decisions:
  - PP-1 lock-file deletion placed INSIDE the `block:` clause, AFTER untar, BEFORE the `always:` opener (block ends at line 192, always at 195). Rationale documented inline: a permission error on the lock-delete should surface as a block failure so the operator knows their tarball produced an unreadable file; the always-clause still runs `docker start` so the container comes up and Prometheus 3.x can attempt its own stale-lock-replacement path as defence-in-depth. Plan author explicitly left placement to executor discretion ("with rationale documented in an inline comment").
  - PP-3 queries.active deletion INCLUDED (recommended-YES per PATTERNS.md line 506 -- "recommend YES for cleanliness"). Same idempotent `state: absent` shape, placed adjacent to PP-1 lock-delete.
  - D-178 verify.yml reuse via `include_tasks: verify.yml` inside `always:` clause (no sub-tags -- block-level [prometheus, backup|restore] tags carry down per PATTERNS.md Pattern F). verify.yml is the existing 152-line file used unchanged.
  - set_fact dual-branch path resolution chosen over jinja default() chain for source path resolution -- separates "discover latest" from "use pinned" cleanly and gives a single `backup_src_path` variable for downstream tasks.
metrics:
  duration: 7min
  completed_date: 2026-06-03
---

# Phase 13 Plan 03: Prometheus backup + restore tasks Summary

Ships the Prometheus per-role cold-quiesce backup/restore pair -- the simplest stateful role in Phase 13 (single named volume, no host bind-mount files). Adds one Prometheus-specific safety step: PP-1 lock-file deletion AFTER untar, BEFORE `docker start`, addressing the "Locked by other process" startup-refusal class regression that PID-namespace collisions can cause when a stale lock file is restored from tarball.

## What Was Built

### 1. `roles/prometheus/tasks/backup.yml` (Task 1; 136 lines)

Cold-quiesce backup of `telemetron_prometheus_data` named volume into a single zstd tarball:

| Concern | Implementation |
|---------|----------------|
| Package prerequisite | `ansible.builtin.package: name: zstd state: present` (OPS-V13-04, idempotent) |
| Destination dir | `{{ backup_dest_root }}/prometheus/` mode `0700`, root-owned (XP-4) |
| Timestamp | `ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ` (D-179) |
| Container stop | `ansible.builtin.command: "docker stop -t {{ prometheus_backup_stop_timeout }} {{ prometheus_container_name }}"` (XP-1; NEVER `state: stopped`) |
| Stop-poll | `community.docker.docker_container_info` until `State.Running == false`, retries 30, delay 2 |
| Tar | `tar --zstd -cpf <dest> -C /var/lib/docker/volumes/{{ prometheus_data_volume }}/_data .` (single volume; no `--transform` complexity) |
| Tarball perms | mode `0600`, root-owned (XP-4) |
| Block/always | `block:` owns stop+poll+tar+chmod; `always:` owns `docker start` + `include_tasks: verify.yml` (AN-2 + D-178) |
| Tags | `[prometheus, backup]` on block parent (cross-cutting `--tags backup` valid) |

Header docstring (35 lines) cites BACKUP-V13-02, XP-1, XP-4, PP-1 (mentioned because lock IS captured in the tarball), PP-2 (WAL gap rationale), PP-3, PP-4, AN-2, D-177, D-178, D-179, OPS-V13-04.

### 2. `roles/prometheus/tasks/restore.yml` (Task 2; 208 lines)

Confirm-gated, integrity-checked, wipe-then-untar restore with the Prometheus-specific PP-1 lock-file deletion:

| Concern | Implementation |
|---------|----------------|
| Package prerequisite | `ansible.builtin.package: name: zstd state: present` |
| Confirm-gate | `ansible.builtin.fail` when `not (backup_restore_confirm \| default(false) \| bool)` -- Pattern I (placed BEFORE the WARN so a no-confirm invocation fails before logging anything destructive) |
| Latest-discovery | `ansible.builtin.shell: find ... -name 'prometheus-*.tar.zst' -printf '%f\n' \| sort -r \| head -1` (D-179; gated on `backup_restore_from == ""`) |
| Source path resolution | `ansible.builtin.set_fact: backup_src_path: <jinja-if>` -- pinned `backup_restore_from` wins, else discovered latest |
| D-159 WARN | Names `{{ prometheus_data_volume }}` and `{{ backup_src_path }}` only (no contents leak; T-13-03-05) |
| Integrity check | `ansible.builtin.command: "tar --zstd -tf {{ backup_src_path }}"` BEFORE wipe (T-13-03-02) |
| Container stop | `docker stop -t {{ prometheus_backup_stop_timeout }}` + `docker_container_info` poll |
| Wipe | `find /var/lib/docker/volumes/{{ prometheus_data_volume }}/_data -mindepth 1 -delete` (STACK.md sec.3) |
| Untar | `tar --zstd -xpf {{ backup_src_path }} -C /var/lib/docker/volumes/{{ prometheus_data_volume }}/_data` |
| **PP-1 lock-delete** | `ansible.builtin.file: path: ".../_data/lock" state: absent` -- placement: AFTER untar (line 165), inside `block:`, BEFORE `always:` opener (line 195) at line 182 |
| **PP-3 queries.active** | `ansible.builtin.file: path: ".../_data/queries.active" state: absent` -- adjacent to PP-1 |
| Always restart | `docker start` + `include_tasks: verify.yml` (AN-2 + D-178) |
| Tags | `[prometheus, restore]` on block parent |

Header docstring (44 lines) cites RESTORE-V13-02, PP-1 (full WHY narrative -- PID-based lock, namespace collision, "Locked by other process"), PP-3, AN-2, D-159, D-177, D-178, D-179, OPS-V13-01, OPS-V13-04, T-13-03-02.

## Verification Results

```
backup.yml:
  YAML safe_load -> OK
  block:/always: count -> 2 (exactly one of each)
  docker stop -> present
  state: stopped -> absent (uncommented and in raw text -- the two original comment
    references were softened to "with the stopped state" to avoid even matching the
    plain regex `state:\s*stopped`)
  state: absent on docker_container -> 0 (AN-1 respected)
  zstd ensure-present -> present
  {{ prometheus_data_volume }} -> present in tar source
  include_tasks: verify.yml -> present in always: at line 133
  mode 0600 + 0700 -> both present
  Header cites BACKUP-V13-02|PP-1|PP-2|AN-2|D-178 -> 10 matches
  Total lines: 136 (>= 70)

restore.yml:
  YAML safe_load -> OK
  backup_restore_confirm -> present (gate before any destructive)
  tar --zstd -tf -> present, BEFORE wipe (awk ordering check passes)
  /_data/lock -> present, between untar and always: (untar=165, lock=182, always=195)
  find -mindepth 1 -delete -> exactly 1 occurrence, against prometheus_data_volume
  WARNING: irreversible -> present (D-159)
  queries.active -> present (PP-3, recommended-YES)
  include_tasks: verify.yml -> present in always:
  block:/always: count -> 2
  state: stopped -> absent (uncommented)
  docker stop count -> 2 (one in each phase)
  Header cites RESTORE-V13-02|PP-1|PP-3|AN-2 -> 12 matches
  Total lines: 208 (>= 95)

Cross-cutting:
  roles/prometheus/tasks/verify.yml -> git diff --quiet -> untouched OK
  ansible-playbook playbooks/deploy_docker.yml --syntax-check -> exit 0 (with dummy
    vault password file per Rock's memory note that --syntax-check skips role
    internals; supplemented per-file python3 yaml.safe_load above)
```

## Deviations from Plan

None — plan executed exactly as written. Two micro-decisions left explicitly to executor discretion by the plan author:

1. **PP-1 lock-file placement** — Plan allowed "INSIDE the `block:` (after untar, before the block's end) OR inside `always:` before the `docker start` line". Picked inside-block. Rationale (inline comment in restore.yml lines 174-184): a lock-delete failure (permission error / read-only volume) should surface as a block failure so the operator knows their tarball has an unreadable file. The `always:` clause still runs `docker start` so the container comes up and Prometheus 3.x's own stale-lock-replacement path executes as defence-in-depth -- loud-failure preferred over silent-broken-startup.

2. **Initial backup.yml had two comment references to literal "state: stopped"** inside docstring narration. The plan's `<verify><automated>` line uses `! grep -qE 'state:\s*stopped'` (no comment-stripping filter), so the docstring strings would have tripped the gate. Reworded both occurrences ("with the stopped state value on community.docker docker_container") -- semantics identical, regex no longer matches. This is a tooling artifact, not a behavioural change.

## Authentication Gates

None encountered.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | feat(13-03): add roles/prometheus/tasks/backup.yml -- cold-quiesce TSDB tarball | `6bc6392` |
| 2 | feat(13-03): add roles/prometheus/tasks/restore.yml -- confirm-gated TSDB restore | `56c711a` |

## Known Stubs

None. Both files reference concrete variables that resolve at runtime via the foundation laid in plan 13-01 (`backup_dest_root`, `prometheus_backup_stop_timeout`, `backup_restore_confirm`, `backup_restore_from`) and the existing role defaults (`prometheus_container_name`, `prometheus_data_volume`). No placeholder values.

## Threat Flags

None. All STRIDE threats in the plan's `<threat_model>` (T-13-03-01 through T-13-03-SC) are addressed by the implementation:

- T-13-03-01 (stale lock replay) -> mitigate -> PP-1 unconditional `state: absent`
- T-13-03-02 (tarball corruption) -> mitigate -> `tar --zstd -tf` before wipe
- T-13-03-03 (DoS from misfire restore) -> mitigate -> two-layer gate (confirm + integrity)
- T-13-03-04 (TSDB values disclosure) -> accept -> mode 0600 + 0700 hardening per default
- T-13-03-05 (WARN data echo) -> mitigate -> WARN names identifiers only
- T-13-03-06 (PP-2 WAL gap) -> accept -> documented in backup.yml header
- T-13-03-07 (become: true on /var/lib/docker) -> accept -> same surface as deploy
- T-13-03-08 (XP-1 spec strip) -> mitigate -> explicit `docker stop` + AN-1 grep gate
- T-13-03-SC (supply chain) -> n/a -> only zstd OS pkg via ansible.builtin.package

No new security surface introduced beyond what the plan declared.

## Downstream Consumers

Phase 14 orchestrators will invoke these files via:

```yaml
- name: Per-role backup -- Prometheus
  ansible.builtin.include_role:
    name: prometheus
    tasks_from: backup

- name: Per-role restore -- Prometheus
  ansible.builtin.include_role:
    name: prometheus
    tasks_from: restore
```

The `include_role: tasks_from=restore` path is independently safe even from a custom operator playbook because the `backup_restore_confirm` gate fires inside this file (OPS-V13-01).

Phase 15 docs cascade will reference these exact filenames and the `--tags backup` / `--tags restore` cross-cutting commands.

## Self-Check: PASSED

- `roles/prometheus/tasks/backup.yml` -- FOUND (136 lines)
- `roles/prometheus/tasks/restore.yml` -- FOUND (208 lines)
- Commit `6bc6392` -- FOUND in `git log --oneline -5`
- Commit `56c711a` -- FOUND in `git log --oneline -5`
- `roles/prometheus/tasks/verify.yml` -- `git diff --quiet` exits 0 (UNTOUCHED)
- All plan `<verify><automated>` lines for both tasks exit 0
