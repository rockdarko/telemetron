---
phase: 14-orchestrators-leviathan-human-uat
plan: "08"
subsystem: orchestrators
tags: [gap-closure, G-03-addendum, G-04, ansible, backup, restore, backup_docker, restore_docker]
dependency_graph:
  requires: [14-06, 14-07]
  provides: [G-03-addendum-structural-closure, G-04-structural-closure]
  affects:
    - playbooks/backup_docker.yml
    - playbooks/restore_docker.yml
tech_stack:
  added: []
  patterns:
    - "ansible.builtin.fail as explicit re-raise in rescue block under when: not (knob) guard"
    - "apply: tags: [garage, restore] in dynamic include_role to propagate tags into role body"
key_files:
  created: []
  modified:
    - playbooks/backup_docker.yml
    - playbooks/restore_docker.yml
decisions:
  - "G-03-addendum: add explicit ansible.builtin.fail (not meta:clear_host_errors) as FIRST rescue task guarded by when: not (backup_continue_on_failure | default(false) | bool) -- the rescue otherwise absorbs the failure (rescued=1 failed=0) so any_errors_fatal never fires; explicit re-fail restores failed=1 which triggers play abort under default mode"
  - "G-04: use apply: tags: [garage, restore] inside the ansible.builtin.include_role mapping (sibling of name: and tasks_from:) to propagate tag list into role body tasks at runtime -- dynamic include_role does not expand body tasks in --list-tasks but the apply: mechanism ensures body tasks are not skipped at runtime when --tags restore is in effect; outer task-level tags: [garage, restore] preserved as include-task-scope selector"
  - "No edits to roles/loki, roles/tempo, or roles/mimir -- the orchestrator-side apply: is the canonical Ansible fix; adding [restore] to render task tags in the role bodies would pollute the deploy-time tag surface"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-05T02:07:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 14 Plan 08: Gap Closure (G-03-addendum + G-04) Summary

**One-liner:** Structural closure of two gaps from round-2 UAT: re-raise explicit fail in backup rescue blocks to restore default-mode bail-out (G-03-addendum), and tag-propagation via `apply:` on writer-rerender include_role calls to make `--tags restore` fire writer config re-renders (G-04).

## What Was Built

Two minimal structural edits to the two orchestrator playbooks, closing the two remaining open gaps from the 14-07 round-2 leviathan UAT:

**G-03-addendum closure (playbooks/backup_docker.yml):**
- Added `ansible.builtin.fail` as the FIRST task in each of the 4 rescue blocks (garage, prometheus, grafana, alertmanager)
- The new fail task is guarded by `when: not (backup_continue_on_failure | default(false) | bool)` -- the exact logical negation of the existing `meta: clear_host_errors` guard
- Under default mode: the fail fires, Ansible increments the play-level failure counter, `any_errors_fatal: true` aborts the play before subsequent roles run (bail-out contract restored)
- Under opt-in mode: the fail is when:-skipped, control falls through to `meta: clear_host_errors` as before (14-06 G-03 opt-in contract preserved)
- No `tags:` field on new fail task (inherits from enclosing block); does NOT appear under `--list-tasks --tags backup` (W-4 invariant preserved)

**G-04 closure (playbooks/restore_docker.yml):**
- Added `apply: tags: [garage, restore]` inside the `ansible.builtin.include_role:` mapping for all 3 writer-rerender tasks (loki, tempo, mimir tasks_from=main)
- The `apply:` key propagates the tag list to all tasks loaded by the dynamic include at runtime, making them selectable under `--tags restore` filtering
- Outer task-level `tags: [garage, restore]` preserved (include-task-scope selector; the two are complementary, not redundant)
- Task `name:` strings amended to include `; G-04 tag-propagation` for greppability
- Comment block added above the loki writer-rerender entry explaining the mechanism
- No edits to `roles/loki`, `roles/tempo`, or `roles/mimir`

## Verification Results

| Check | Result |
|-------|--------|
| `ansible-playbook --syntax-check` backup_docker.yml | PASS (exits 0) |
| `ansible-playbook --syntax-check` restore_docker.yml | PASS (exits 0) |
| YAML round-trip: 4 rescue blocks with [fail, clear_host_errors] in order | PASS |
| YAML round-trip: fail task guards correct (not-knob vs knob, mutually exclusive) | PASS |
| YAML round-trip: 3 writer-rerender tasks with apply: tags: {garage, restore} | PASS |
| YAML round-trip: outer task tags preserved as {garage, restore} | PASS |
| YAML round-trip: flush_handlers immediately after mimir writer-rerender | PASS |
| `grep -c 'G-03-addendum' backup_docker.yml` >= 4 | 8 (PASS) |
| `grep -c 'G-04' restore_docker.yml` >= 3 | 4 (PASS) |
| `--list-tasks --tags backup` shows exactly 4 `Invoke <role> backup` lines | PASS (W-4 preserved) |
| `--list-tasks --tags restore` shows 3 `Re-render <Role>` lines | PASS |
| Only playbooks/backup_docker.yml and playbooks/restore_docker.yml modified | PASS |
| No French-language strings | PASS |

Note on `--list-tasks --tags restore` and role-body task enumeration: Dynamic `include_role` (vs static `import_role`) does not expand body tasks in `--list-tasks` output -- this is fundamental Ansible behavior, not a deficiency of the `apply:` fix. The `apply:` mechanism operates at runtime task execution, propagating the tag list into loaded tasks so they are not skipped when the `--tags restore` filter is active. Behavioral confirmation (config re-renders fire, handlers chain, writers come up healthy under `--tags restore` on a clean post-purge state) is Plan 14-09's empirical gate.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: G-03-addendum (backup rescue re-raise) | b5dca0f | playbooks/backup_docker.yml |
| Task 2: G-04 (apply: tag propagation) | d04efcb | playbooks/restore_docker.yml |

## Deviations from Plan

None -- plan executed exactly as written. The two structural edits are the minimal targeted changes the plan specified.

## Next

**Plan 14-09: Round-3 leviathan re-UAT** is the behavioral closure gate. Scenarios to re-run:
- Scenario 3a (default bail-out): expect `PLAY RECAP failed=1` (G-03-addendum behavioral proof)
- Scenario 4d-restore (`--tags restore` after clean purge+redeploy): expect `PLAY RECAP failed=0`, no `Forbidden: No such key:` (G-04 behavioral proof)

If both pass, Phase 14 verification can be re-run with status: passed and 6/6 must-haves verified.

## Self-Check: PASSED

Files exist:
- playbooks/backup_docker.yml: FOUND
- playbooks/restore_docker.yml: FOUND
- .planning/phases/14-orchestrators-leviathan-human-uat/14-08-SUMMARY.md: FOUND (this file)

Commits exist:
- b5dca0f: FOUND (fix(14-08): close G-03-addendum)
- d04efcb: FOUND (fix(14-08): close G-04)
