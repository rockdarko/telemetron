---
phase: 14-orchestrators-leviathan-human-uat
plan: "06"
subsystem: backup-orchestrator
tags: [backup, ansible, g-03-closure, continue-on-failure, clear_host_errors]

dependency_graph:
  requires:
    - "14-04: UAT run that produced G-03 evidence"
    - "playbooks/backup_docker.yml pre-fix state (4 bare include_role calls)"
  provides:
    - "G-03 prerequisites: per-role block/rescue/clear_host_errors in backup_docker.yml"
    - "SC5 structural prerequisite: opt-in mode now structurally capable of running all 4 roles past failure"
    - "OPS-V13-02 opt-in contract deliverable on single-host inventories"
  affects:
    - "Plan 14-07: re-UAT on leviathan (empirical proof SC5 PARTIAL -> VERIFIED)"

tech_stack:
  added: []
  patterns:
    - "Ansible block/rescue/clear_host_errors pattern for per-role continue-on-failure on single-host inventories"
    - "Rescue when-guard pattern: rescue fires always but skips meta task under default mode"

key_files:
  created: []
  modified:
    - playbooks/backup_docker.yml

decisions:
  - "D-184 REVERSED: explicit block/rescue around each include_role accepted based on G-03 field evidence -- any_errors_fatal alone does not keep host in active set on single-host inventories"
  - "Rescue when-guard is the EXACT expression 'backup_continue_on_failure | default(false) | bool' matching line-76 idiom"
  - "Inner include_role retains its own tags: [<role>, backup] (W-4 mitigation) -- block-level tags are additive, not replacing"
  - "any_errors_fatal (line 76) preserved as complementary to rescue -- rescue handles host-removal semantic, any_errors_fatal handles play-level abort"

metrics:
  duration: "~10 minutes"
  completed: "2026-06-04"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 14 Plan 06: G-03 Closure -- block/rescue/clear_host_errors in backup_docker.yml Summary

**One-liner:** Four per-role block/rescue wrappers with `meta: clear_host_errors` guarded by `when: backup_continue_on_failure` close G-03 -- opt-in continue-on-failure now actually keeps the host in the active set across role failures on single-host inventories.

## What Was Built

`playbooks/backup_docker.yml` was amended to wrap each of the 4 per-role `include_role` calls (garage, prometheus, grafana, alertmanager in forward-deploy order) in a `block:` with a `rescue:` that calls `ansible.builtin.meta: clear_host_errors`.

### The G-03 Root Cause

UAT scenario 3b (14-HUMAN-UAT.md) on leviathan showed that with `backup_continue_on_failure=true` and a simulated Prometheus failure, only the Garage tarball was produced -- not the expected 3 of 4. Root cause: `any_errors_fatal: false` (from the line-76 inversion) prevents the _play_ from aborting, but Ansible's default error handling also removes the failed host from the active set independently. On a single-host inventory (the only inventory shape v1.3.0 targets), this means all subsequent `include_role` calls see zero hosts and are silently skipped.

### The Fix

For each role, the bare `include_role` call was replaced with:

```yaml
- name: <Role> backup (G-03 -- block/rescue allows continue-on-failure)
  tags:
    - <role>
    - backup
  block:
    - name: Invoke <role> backup
      ansible.builtin.include_role:
        name: <role>
        tasks_from: backup
      vars:
        backup_timestamp_override: "{{ backup_timestamp_shared }}"
      tags:
        - <role>
        - backup           # RETAINED on include_role (W-4 mitigation)
  rescue:
    - name: <Role> backup failed -- clear host errors so subsequent role backups still run (G-03; opt-in only)
      ansible.builtin.meta: clear_host_errors
      when: backup_continue_on_failure | default(false) | bool
```

### Default-Mode Preservation

Under `backup_continue_on_failure=false` (default):
- role fails -> block fails -> rescue entered
- `when: backup_continue_on_failure | default(false) | bool` evaluates false
- `clear_host_errors` is SKIPPED
- host remains in failed state
- `any_errors_fatal: true` (line-76 inversion) aborts the play
- UAT scenario 3a behavior: UNCHANGED

Under `backup_continue_on_failure=true` (opt-in):
- role fails -> block fails -> rescue entered
- `when:` evaluates true
- `clear_host_errors` runs -> host returns to active set
- `any_errors_fatal: false` (line-76) does NOT abort
- next role's include_role runs against the now-active host
- all 4 roles attempt their backup

### Key Invariants Preserved

| Invariant | Status |
|-----------|--------|
| Line-76 `any_errors_fatal: "{{ not (backup_continue_on_failure \| default(false) \| bool) }}"` | PRESERVED -- unchanged |
| Comment block documenting dynamic include_role tag resolution (lines 119-130 pre-fix) | PRESERVED -- extended with G-03 closure note |
| Forward-deploy role order: garage -> prometheus -> grafana -> alertmanager | PRESERVED |
| Inner include_role retains `tags: [<role>, backup]` (W-4 mitigation) | VERIFIED by YAML round-trip assertion |
| `--list-tasks --tags backup` enumerates all 4 include_role invocations | VERIFIED by execute-time canary |

## Verification Results

**Syntax check:** `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0.

**Tag canary (W-4 mitigation):** `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` output confirmed:
- `Invoke garage backup` (tags: backup, garage)
- `Invoke prometheus backup` (tags: backup, prometheus)
- `Invoke grafana backup` (tags: backup, grafana)
- `Invoke alertmanager backup` (tags: alertmanager, backup)

All 4 include_role invocations enumerated -- tag-leakage would have silently broken `--tags backup` on leviathan at run time.

**YAML round-trip assertion:** Python yaml.safe_load_all validated:
- 4 block/rescue wrappers present in forward-deploy order
- Each rescue has `meta: clear_host_errors` as its first task
- Each rescue is guarded by `when: backup_continue_on_failure | default(false) | bool`
- Each block has `tags: [<role>, backup]`
- Each inner include_role retains `tags: [<role>, backup]` (W-4)
- `any_errors_fatal` references `backup_continue_on_failure`

**Grep gates:** G-03 audit reference, `clear_host_errors`, `when: backup_continue_on_failure`, `any_errors_fatal:` all confirmed present.

**Forward-deploy order:** Python regex confirms garage/prometheus/grafana/alertmanager appear in that order.

## Deviations from Plan

None -- plan executed exactly as written.

The only noteworthy alignment: D-184's "explicit block/rescue rejected" rationale is formally reversed in the file's inline comment block, as the plan explicitly required. This is not a deviation -- it was specified in the plan.

## D-184 Reversal Audit Trail

D-184 (14-CONTEXT.md) originally rejected explicit block/rescue around each include_role as "4x the YAML for behavior `any_errors_fatal` gives natively." G-03 field evidence (UAT scenario 3b on leviathan, 14-HUMAN-UAT.md) proved this assessment wrong for single-host inventories: `any_errors_fatal` controls play-level abort, but Ansible independently removes the failed host from the active set. On a single-host inventory those are the same host, so `any_errors_fatal: false` alone cannot prevent the subsequent include_role calls from seeing zero hosts.

The 4x YAML cost is real and accepted. The per-role block/rescue is now the correct and necessary mechanism. The inline comment in `playbooks/backup_docker.yml` (the G-03 CLOSURE section in the file header) is the authoritative audit trail for future readers.

## Known Stubs

None -- all 4 block/rescue wrappers are fully wired with the correct `meta: clear_host_errors` guard.

## Threat Flags

None -- no new network endpoints, auth paths, file access patterns, or schema changes. The `meta: clear_host_errors` primitive is a play-control operation that neither runs shell nor modifies host state.

## Self-Check: PASSED

- `playbooks/backup_docker.yml` exists and is non-empty: confirmed
- Commit de4a082 exists: confirmed
- `--syntax-check` exits 0: confirmed
- `--list-tasks --tags backup` enumerates all 4 include_role invocations: confirmed
- Python YAML round-trip assertions: PASS
- G-03 audit reference, clear_host_errors, when guard, any_errors_fatal: all confirmed present
