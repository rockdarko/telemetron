---
phase: 14-orchestrators-leviathan-human-uat
plan: "05"
subsystem: backup-restore
tags: [garage, restore, writer-config, G-01-closure, gap-closure]
dependency_graph:
  requires: [14-01, 14-02, 14-03, 14-04]
  provides: [G-01-prerequisites, SC6-prerequisites, RESTORE-V13-05-prerequisites]
  affects: [playbooks/restore_docker.yml, roles/garage/tasks/restore.yml]
tech_stack:
  added: []
  patterns:
    - slurp+set_fact fact-population from host file (verbatim from bootstrap.yml:124-147)
    - include_role tasks_from=main for targeted writer-config re-render inside restore play
    - meta: flush_handlers between config re-render and healthy-poll
key_files:
  created: []
  modified:
    - roles/garage/tasks/restore.yml
    - playbooks/restore_docker.yml
decisions:
  - "D-183 locked assumption 'no config re-render needed' REVERSED by G-01 field evidence (14-HUMAN-UAT.md)"
  - "slurp+set_fact appended to restore.yml OUTSIDE block:/always: wrapper (siblings, not children) so they fire only on successful restore"
  - "writer-rerender include_role calls use tasks_from=main (not tasks_from=restore) because the template task lives in main.yml"
  - "meta: flush_handlers inserted between writer rerenders and writer-restart loop so handlers fire before healthy-poll"
  - "new tasks tagged [garage, restore] matching D-189 amended rationale -- not [loki/tempo/mimir] (rerender is Garage-restore prerequisite)"
metrics:
  duration: "~2 minutes"
  completed: "2026-06-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 14 Plan 05: G-01 Closure -- Restore Writer Config Re-render Summary

**One-liner:** Two-part G-01 fix: restore.yml tail slurp+set_fact populates garage_s3_access_key_id/secret_key facts; restore_docker.yml inserts loki/tempo/mimir include_role tasks_from=main + flush_handlers between Garage restore and writer-restart loop.

## What Was Built

### Task 1: roles/garage/tasks/restore.yml -- slurp + set_fact tail

Two new top-level tasks appended after the existing `block:/always:` wrapper (lines 374-376 pre-edit). They are SIBLINGS of the block, not children, so they fire only when the restore block completed without raising:

**Task added at end of file:**
```yaml
# G-01 closure comment block (13 lines) citing:
#   - 14-HUMAN-UAT.md G-01 as field evidence
#   - roles/garage/tasks/bootstrap.yml:124-147 as canonical shape
#   - lazy-Jinja dependency chain (loki/tempo/mimir templates -> secrets.yml -> garage_s3_* facts)

- name: Load restored Garage S3 credentials from host file (G-01 fact-population for writer-config re-render)
  ansible.builtin.slurp:
    src: "{{ garage_s3_credentials_file }}"
  register: garage_creds_raw
  changed_when: false
  tags: [garage, restore]
  # NO when: guard -- file existence is a postcondition of the block succeeding

- name: Set Garage S3 credential facts from restored host file (G-01; mirrors bootstrap.yml:140-147)
  ansible.builtin.set_fact:
    garage_s3_access_key_id: "{{ (garage_creds_raw.content | b64decode) | regex_search('(?m)^key_id=(.+)$', '\\1') | first }}"
    garage_s3_secret_key: "{{ (garage_creds_raw.content | b64decode) | regex_search('(?m)^secret=(.+)$', '\\1') | first }}"
  tags: [garage, restore]
  # NO when: guard
```

The regex_search expressions are copied VERBATIM from bootstrap.yml:142-143.

Total tasks in restore.yml after edit: 13 (was 11 in the block + 2 outer).

### Task 2: playbooks/restore_docker.yml -- writer-config-rerender step

**Incorrect comment replaced:** The 6-line block starting with `# D-183 + D-189 amended: restart the 3 Garage writers sequentially AFTER` (which ended with `no config re-render needed.`) was replaced with a 30-line corrected rationale citing:
- G-01 from 14-HUMAN-UAT.md
- D-183 REVERSED (with explanation of the 7-step round-trip's key-drift mechanism)
- The two-part fix mechanism (restore.yml fact-population + tasks_from=main re-render)
- flush_handlers timing rationale
- The preserved fallback role of the existing docker start loop

**4 new tasks inserted** between the Garage restore (index 2) and the writer-restart loop (now at index 7):

| Index | Task | Tags |
|-------|------|------|
| 3 | include_role: name=loki tasks_from=main | [garage, restore] |
| 4 | include_role: name=tempo tasks_from=main | [garage, restore] |
| 5 | include_role: name=mimir tasks_from=main | [garage, restore] |
| 6 | meta: flush_handlers | (inherited) |
| 7 | docker start loop (existing, unchanged) | [garage, restore] |

**Exact task ordering verified by YAML round-trip:**
`garage_restore(2) < loki(3) < tempo(4) < mimir(5) < flush_handlers(6) < writer_restart_loop(7)`

## Verification Results

| Check | Result |
|-------|--------|
| `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` | exit 0 |
| YAML round-trip: restore.yml last 2 tasks are slurp+set_fact | PASS |
| YAML round-trip: slurp tags == {garage, restore}, no when: guard | PASS |
| YAML round-trip: set_fact tags == {garage, restore}, no when: guard | PASS |
| YAML round-trip: set_fact regex_search shape matches bootstrap.yml:142-143 | PASS |
| YAML round-trip: restore_docker.yml ordering garage < loki < tempo < mimir < flush_handlers < restart_loop | PASS |
| YAML round-trip: all 3 writer rerenders tagged [garage, restore] | PASS |
| grep: `no config re-render needed` NOT present in restore_docker.yml | PASS |
| grep: G-01, 14-HUMAN-UAT.md, D-183 REVERSED all cited in restore_docker.yml | PASS |
| grep: confirm-gate (fail:), WARN banner, prometheus/grafana/alertmanager restores still present | PASS |
| Post-commit deletion check | No unexpected deletions |

**NOTE:** `ansible-playbook --syntax-check` is STRUCTURAL-ONLY (per MEMORY.md `feedback_ansible_syntax_check_role_gap.md`). It does NOT catch undefined-variable runtime failures. Runtime correctness -- specifically that `garage_s3_access_key_id` fact propagates across the include_role boundary to loki/tempo/mimir template renders and that writers come back healthy against the restored Garage S3 key WITHOUT `Forbidden: No such key:` errors -- is empirically verified by Plan 14-07 scenario 1 step 6 PLAY RECAP `failed=0`.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 35d038a | fix(14-05): G-01 -- append slurp+set_fact to garage/tasks/restore.yml |
| Task 2 | 67fec5f | fix(14-05): G-01 -- insert writer-config-rerender step in restore_docker.yml |

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None. All new task names, comments, and YAML structures are concrete and production-ready.

## Threat Flags

None. The new tasks operate entirely on files and facts already within the restore.yml trust boundary. The writer config re-render reads the same `garage_s3_credentials_file` that Phase 13's backup/restore already protects (mode 0600, integrity-checked tarball). No new network endpoints, auth paths, or schema changes introduced.

## Gap Closure Status

| Gap | Before | After |
|-----|--------|-------|
| G-01 (14-HUMAN-UAT.md) | OPEN -- writers crash-loop post-restore with `Forbidden: No such key:` | PREREQUISITES IN PLACE -- structural fix applied; empirical proof is Plan 14-07 |
| SC6 (ROADMAP.md Phase 14 #6) | FAILED | PREREQUISITES IN PLACE -- structural changes complete |
| RESTORE-V13-05 | UNMET -- writers required manual `deploy_docker.yml --tags loki,tempo,mimir,garage` workaround | PREREQUISITES IN PLACE |

Behavioral correctness (no `Forbidden: No such key:` in writer logs, PLAY RECAP `failed=0` after unmodified run) is Plan 14-07's empirical gate.

## Self-Check: PASSED

Files exist and commits verified:
- `roles/garage/tasks/restore.yml` -- present (13 top-level tasks, ends with slurp+set_fact)
- `playbooks/restore_docker.yml` -- present (4 new tasks inserted at correct indices)
- Commit 35d038a -- present (`git log --oneline` confirms)
- Commit 67fec5f -- present (`git log --oneline` confirms)
