---
phase: 14-orchestrators-leviathan-human-uat
plan: 01
subsystem: infra
tags: [ansible, backup, set_fact, override-knob, d-191]

# Dependency graph
requires:
  - phase: 13-per-role-backup-restore-tasks
    provides: 4 stateful-role tasks/backup.yml files with inline date+register: backup_timestamp + 2 filename construction sites per file
provides:
  - "backup_timestamp_effective fact derived from backup_timestamp_override | default(backup_timestamp.stdout) on all 4 stateful tasks/backup.yml"
  - "Variable contract for the Phase 14 Plan 02 orchestrator to propagate a single shared timestamp across all 4 tarballs in a multi-role run"
  - "Zero-regression standalone path: include_role: tasks_from=backup without override still uses the per-role inline date.stdout exactly as before Phase 14"
affects:
  - 14-02-backup-docker-orchestrator (will set backup_timestamp_override via include_role vars)
  - 14-04-human-uat (Scenario 1 step 3 will validate the shared-timestamp behavior end-to-end)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern K (D-191 minimum-diff override): existing register: X task keeps its shape; new set_fact: <X>_effective: '{{ <X>_override | default(<X>.stdout) }}' inserted immediately after; all downstream consumers switch from <X>.stdout to <X>_effective"

key-files:
  created: []
  modified:
    - roles/garage/tasks/backup.yml
    - roles/prometheus/tasks/backup.yml
    - roles/grafana/tasks/backup.yml
    - roles/alertmanager/tasks/backup.yml

key-decisions:
  - "Option B (D-191): always-call-date + set_fact, NOT when-gated date call. One extra microsecond-cost date invocation per role; in exchange the set_fact is unconditional and the standalone path keeps zero behavior change."
  - "backup_timestamp_override is intentionally NOT added to defaults/main.yml. Adding a default there would invert the precedence (default(...) filter would never see undefined) and silently break orchestrator override propagation."
  - "set_fact insertion placed immediately after the existing register: backup_timestamp task — adjacent to its source variable — before subsequent volume_info / stat / block tasks. Maintains read-order: date -> resolve -> use."

patterns-established:
  - "Pattern K (override + default): new override variable + set_fact derived fact + mechanical s/old_ref/new_ref/ at all consumer sites. Applies cleanly when (a) caller can opt into the override via include_role vars, (b) standalone callers must see zero behavior change. Reusable for any future per-role var that an orchestrator might want to homogenize across a batch run."

requirements-completed: [BACKUP-V13-05]

# Metrics
duration: 2min
completed: 2026-06-04
---

# Phase 14 Plan 01: Amend backup.yml D-191 timestamp override Summary

**4 stateful-role tasks/backup.yml files now accept an orchestrator-supplied backup_timestamp_override via set_fact backup_timestamp_effective; standalone include_role callers continue to use the inline backup_timestamp.stdout fallback unchanged.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-04T12:18:52Z
- **Completed:** 2026-06-04T12:21:01Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments

- Inserted 1 new `set_fact: backup_timestamp_effective` task per file (tagged `[<role>, backup]`, same as existing date task) on all 4 stateful roles
- Rewrote both filename construction sites per file (tar create dest + post-create stat path) from `{{ backup_timestamp.stdout }}` to `{{ backup_timestamp_effective }}`
- Preserved the existing `register: backup_timestamp` task verbatim on every file — fallback branch remains functional
- Preserved the cold-quiesce `block:` opener and all child tasks verbatim — no behavioral side-effects to stop/start/tar/verify
- Per D-191 explicit lock: no `backup_timestamp_override` default added to any role's `defaults/main.yml` — keeps the `default(...)` precedence working

## Task Commits

Each task was committed atomically:

1. **Task 1: Amend the 4 tasks/backup.yml files in lockstep -- insert set_fact and rewrite filename sites** — `c156702` (feat)

## Files Created/Modified

- `roles/garage/tasks/backup.yml` — set_fact backup_timestamp_effective inserted between date task and CR-02 volume_info tasks; filename sites at the tar shell cmd and post-create file mode step rewritten
- `roles/prometheus/tasks/backup.yml` — same shape; set_fact inserted between date task and CR-02 volume_info task; 2 filename sites rewritten
- `roles/grafana/tasks/backup.yml` — same shape; set_fact inserted between date task and CR-02 volume_info task; 2 filename sites rewritten
- `roles/alertmanager/tasks/backup.yml` — same shape; set_fact inserted between date task and cold-quiesce block; 2 filename sites rewritten

## Decisions Made

- **Option B over Option A (CONTEXT.md D-191 / PATTERNS.md Pattern K):** Always call `date`, then `set_fact` chooses override vs inline via `default(...)`. Picked over Option A (when-gated date with conditional set_fact) because: (1) unconditional set_fact is simpler to reason about and verify, (2) microsecond cost of the redundant date call is invisible, (3) the verification script can assert one exact set_fact line per file rather than two branches.
- **Insertion point placement:** Set_fact placed immediately after the existing `register: backup_timestamp` task (and its tags block), before any subsequent CR-02 volume_info / AP-1 stat / cold-quiesce block. Keeps the resolve-step adjacent to its source variable so a future reader sees: `date -> resolve -> consume` in linear order.
- **set_fact tags `[<role>, backup]` matching the existing date task:** Confirms the task is selected under both `--tags <role>` and `--tags backup` targeted runs. The set_fact MUST fire whenever the consumer filename sites fire; using the same tag set as the date task it depends on guarantees this.

## Deviations from Plan

None - plan executed exactly as written.

Verification script from the plan passed on first run; all 4 files contain the expected literal `backup_timestamp_override | default(backup_timestamp.stdout)`, no `backup_timestamp.stdout` remains in any `.tar.zst` filename context, each file has ≥2 `backup_timestamp_effective` references in `.tar.zst` contexts, and Python `yaml.safe_load` on each amended file succeeds. `git diff --stat` shows exactly 4 files modified (no creations, no deletions), 52 insertions + 8 deletions total — slightly above the plan's "roughly 7 lines added per file" estimate because the inserted set_fact carries Pattern K's recommended 4-line preamble comment (D-191 reference + standalone-fallback note) plus the 6 YAML lines of the task itself.

## Issues Encountered

None. The 4 files have nearly-identical timestamp generation idioms (mechanically uniform per PATTERNS.md "Landmines and Discovered Facts"), so the same 3-step recipe (insert set_fact, rewrite site #1, rewrite site #2) applied cleanly to each one in turn.

## Self-Check: PASSED

- Files modified verified: all 4 amended files contain literal `backup_timestamp_override | default(backup_timestamp.stdout)` (one occurrence each) and ≥2 `backup_timestamp_effective` references in `.tar.zst` filename contexts; all 4 parse cleanly via Python `yaml.safe_load`.
- Commit hash verified: `c156702` present in worktree branch git log.
- Defaults/main.yml unchanged for all 4 roles (forbidden change confirmed absent via `git diff --name-only`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 02 (backup_docker.yml orchestrator) unblocked:** the variable contract `backup_timestamp_override` is in place on every consumer. Plan 02 generates the shared timestamp at play start (`pre_tasks: date -> set_fact: backup_timestamp_shared`) and propagates it to each include_role via `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }`.
- **Plan 03 (restore_docker.yml) unaffected:** restore reads `backup_restore_from` and resolves it per-role (D-190); does NOT use `backup_timestamp_override`.
- **Plan 04 (HUMAN-UAT) Scenario 1 step 3 will validate end-to-end:** after Plan 02 ships, `ls /opt/telemetron/backups/*/*.tar.zst | awk -F- '{print $NF}' | sort -u | wc -l` must return 1 for a single backup_docker.yml invocation, proving the shared-timestamp propagation works in practice (current static verification only proves the variable contract is in place).

---
*Phase: 14-orchestrators-leviathan-human-uat*
*Completed: 2026-06-04*
