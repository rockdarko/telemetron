---
phase: 14-orchestrators-leviathan-human-uat
plan: 03
subsystem: infra
tags: [ansible, ansible-playbook, docker, restore, orchestrator, garage, loki, tempo, mimir, prometheus, grafana, alertmanager]

# Dependency graph
requires:
  - phase: 13-per-role-backup-restore-tasks
    provides: per-role tasks/restore.yml for garage/prometheus/grafana/alertmanager (consumed via include_role); group_vars/all/backup.yml knobs (backup_restore_confirm, backup_restore_from, backup_stop_timeout)
provides:
  - playbooks/restore_docker.yml -- confirm-gated restore orchestrator with writer-quiesce around Garage
  - identity-level safety pattern (D-188 amended): orchestrator-level `[always]`-tagged fail gate that fires on ANY restore_docker.yml invocation including stateless-tag invocations
  - writer-quiesce inline pattern (D-180): cross-role docker stop/start brackets around Garage restore live in the orchestrator, not in per-writer-role tasks
  - SC4 cross-cutting tag pattern: `[<role>, restore]` on each include_role + `[garage, restore]` on writer-quiesce -- `--tags restore` selects all 8 destructive tasks
affects: [14-04-human-uat, 15-doc-cascade]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Identity-level safety: `[always]`-tagged `fail:` pre_task on destructive orchestrator playbook fires on ANY invocation (D-188 amended by SC4 reconciliation)"
    - "Writer-quiesce inline-in-orchestrator: cross-role docker stop -> include_role -> docker start bracket tagged `[garage, restore]` so --tags garage AND --tags restore both run the bracketed unit"
    - "Container names hardcoded inline in loop list-of-dicts (no include_role for non-Garage writers -> defaults not loaded -> `| default('telemetron-<role>')` filter mirrors role defaults)"
    - "any_errors_fatal: true HARDCODED at play level for restore (D-185); no operator opt-out knob"

key-files:
  created:
    - "playbooks/restore_docker.yml -- restore orchestrator (257 lines)"
  modified: []

key-decisions:
  - "Followed plan as specified -- 0 deviations from the highly-detailed task spec (D-180..D-193 + 14-PATTERNS.md Patterns F-J + Shared Patterns 1-5)"
  - "Container names hardcoded inline (PATTERNS.md Mitigation Option 1) -- selected over Option 2 (add to group_vars) because the planner already locked Option 1 in the action body"
  - "SKIP optional pre-stop WARN debug (CONTEXT.md Claude's Discretion) -- top-level banner line 3 already names the stop order"
  - "SKIP optional success summary recommending smoke_test.yml (CONTEXT.md Claude's Discretion) -- Plan 04 HUMAN-UAT prescribes the smoke step explicitly"

patterns-established:
  - "Pattern: orchestrator-level identity-safety fail gate -- `[always]`-tagged so destructive playbook can be opted-in to even under --tags <stateless-role>"
  - "Pattern: writer-quiesce inline-in-orchestrator bracket -- docker stop + docker_container_info poll (Running==false) + include_role + docker start + docker_container_info poll (Health.Status==healthy), all tagged `[<storage-role>, <verb>]` for two-axis tag selection"
  - "Pattern: SC4 cross-cutting verb tag -- every destructive task carries the verb tag (`restore` here) IN ADDITION to its role tag, so `--tags <verb>` selects the full destructive surface without listing every role"

requirements-completed: [RESTORE-V13-05, OPS-V13-01, OPS-V13-03]

# Metrics
duration: ~12min
completed: 2026-06-04
---

# Phase 14 Plan 03: Restore Docker Orchestrator Summary

**Ships `playbooks/restore_docker.yml` -- identity-gated restore orchestrator that brackets the Garage `tasks_from=restore` with writer-stop/restart of Loki/Tempo/Mimir, then chains forward-deploy-ordered restores of prometheus/grafana/alertmanager under hardcoded `any_errors_fatal: true`.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-04T (worktree spawn)
- **Completed:** 2026-06-04T (commit `2f142b5`)
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments

- `playbooks/restore_docker.yml` ships as the single user-facing entry point for restores (RESTORE-V13-05).
- Orchestrator-level `[always]`-tagged `ansible.builtin.fail` gate refuses to run without `--extra-vars backup_restore_confirm=true` for ANY invocation including `--tags <stateless-role>` invocations (OPS-V13-01; D-188 amended by SC4 reconciliation -- playbook-identity-level safety).
- Writer-quiesce inline bracket: stop Loki/Tempo/Mimir sequentially via `docker stop -t {{ backup_stop_timeout }}` + `docker_container_info` poll until `State.Running == false`; run Garage restore; restart writers via `docker start` + healthy-poll (`State.Health.Status == 'healthy'`). All 5 tasks tagged `[garage, restore]` per D-189 amended so `--tags garage` runs the whole bracketed unit AND `--tags restore` cross-cutting (SC4) also runs it; original ban on `[loki]/[tempo]/[mimir]/[writers]/[always]` preserved on the bracket.
- Forward-deploy restore order matching backup order: garage -> prometheus -> grafana -> alertmanager. Each non-Garage include_role tagged `[<role>, restore]` for SC4 cross-cutting.
- `any_errors_fatal: true` HARDCODED at play level (D-185) -- restore is destructive; partial restore is worse than no restore. Documented in file header that `backup_continue_on_failure` does NOT apply.
- D-187 WARN banner with verbatim 3-line `WARNING: irreversible --` content (D-159 grep target).
- Container names hardcoded inline in loop list-of-dicts per 14-PATTERNS.md "Landmines" Mitigation Option 1 (no `include_role: name=loki` -> role defaults not loaded; `| default('telemetron-<role>')` filter mirrors role defaults; operator override via `--extra-vars loki_container_name=...` still works).
- D-193 layout: pre_tasks (confirm-gate + banner, both `[always]`) -> tasks (writer-stop + Garage restore + writer-restart + other 3 role restores). NO post_tasks (would break `--tags garage` symmetry).

## Task Commits

1. **Task 1: Create playbooks/restore_docker.yml -- confirm gate, WARN banner, writer-stop, 4 role restores, writer-restart** -- `2f142b5` (feat)

## Files Created/Modified

- `playbooks/restore_docker.yml` -- 257-line restore orchestrator. Pre_tasks: confirm-gate `ansible.builtin.fail` (`[always]`) + D-187 WARN banner (`[always]`). Tasks: writer-stop loop (`[garage, restore]`) -> writer-stop poll (`[garage, restore]`) -> garage include_role (`[garage, restore]`) -> writer-restart loop (`[garage, restore]`) -> writer-restart poll (`[garage, restore]`) -> prometheus include_role (`[prometheus, restore]`) -> grafana include_role (`[grafana, restore]`) -> alertmanager include_role (`[alertmanager, restore]`). NO post_tasks.

## Decisions Made

- **Followed plan exactly as specified.** The plan body was extremely prescriptive (D-180..D-193 verbatim mapping + 14-PATTERNS.md Patterns F-J + Shared Patterns 1-5 + hardcoded loop list-of-dicts with `| default('telemetron-<role>')` filter); no implementation judgement was required beyond mechanical execution.
- **Container-name strategy: hardcoded inline with default filter** -- selected over Option 2 (add `loki_container_name`/`tempo_container_name`/`mimir_container_name` to `inventory/example-homelab/group_vars/all/backup.yml`) because the planner already locked Option 1 in the action body's `loop:` list-of-dicts spec. Operator override via `--extra-vars loki_container_name=...` still works because the filter resolves to the override before falling through to the default.
- **Claude's Discretion items** (from 14-CONTEXT.md "Claude's Discretion"):
  - **SKIP** the optional pre-stop `WARN -- writers will be stopped` debug -- the top-level banner line 3 already names the stop order ("Restore order: stop Loki/Tempo/Mimir -> garage -> ..."). Plan action body also explicitly recommends SKIP.
  - **SKIP** the optional success summary recommending smoke_test.yml -- Plan 04 14-HUMAN-UAT prescribes the smoke step explicitly; orchestrator summary would be noise. Plan action body also explicitly recommends SKIP.

## Deviations from Plan

None -- plan executed exactly as written. The plan's action body was prescriptive enough that no auto-fix rules (Rules 1-3) fired during implementation; no architectural decisions (Rule 4) surfaced.

## Issues Encountered

None.

## Verification Results

All automated verification gates from the plan passed:

| Gate                                                                                                       | Result                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test -s playbooks/restore_docker.yml`                                                                     | PASS (257 lines; min_lines: 130 met)                                                                                                              |
| `python3 -c "yaml.safe_load(...)"`                                                                         | PASS (parses cleanly)                                                                                                                             |
| `grep -q "hosts: telemetron"`                                                                              | PASS                                                                                                                                              |
| `grep -q "any_errors_fatal: true"`                                                                         | PASS                                                                                                                                              |
| `grep -q "WARNING: irreversible --"`                                                                       | PASS (D-159 grep target)                                                                                                                          |
| `grep -q "ansible.builtin.fail"`                                                                           | PASS                                                                                                                                              |
| `grep -q "backup_restore_confirm"`                                                                         | PASS                                                                                                                                              |
| `grep -c "docker stop -t" >= 1`                                                                            | PASS (1 writer-stop loop)                                                                                                                         |
| `grep -c "docker start " >= 1`                                                                             | PASS (1 writer-restart loop)                                                                                                                      |
| `grep -cE "role:\s+loki" >= 4`                                                                             | PASS (4 -- one per writer-stop/poll/restart/poll loop)                                                                                            |
| `grep -cE "role:\s+tempo" >= 4`                                                                            | PASS (4)                                                                                                                                          |
| `grep -cE "role:\s+mimir" >= 4`                                                                            | PASS (4)                                                                                                                                          |
| `grep -c "community.docker.docker_container_info" >= 2`                                                    | PASS (2 polls -- stop + restart)                                                                                                                  |
| `grep -c "tasks_from: restore" == 4`                                                                       | PASS (garage + prometheus + grafana + alertmanager)                                                                                               |
| Order: writer_stopped_check < garage include < writer_healthy_check < prometheus include                   | PASS (lines 157 < 180 < 213 < 237)                                                                                                                |
| Writer-quiesce block: NO `[loki]/[tempo]/[mimir]/[writers]/[always]` tag                                   | PASS (D-189 original ban preserved)                                                                                                               |
| Writer-quiesce block: contains `[garage]` AND `[restore]` tags                                             | PASS (D-189 amended -- SC4 reconciliation)                                                                                                        |
| NO `state: stopped/started`                                                                                | PASS (XP-1 community.docker landmine avoided)                                                                                                     |
| NO `post_tasks:` block                                                                                     | PASS (D-193 -- writer-restart in `tasks:` so it fires under `--tags garage`)                                                                      |
| `become: true >= 2`                                                                                        | PASS (writer-stop command + writer-restart command)                                                                                               |
| Comment-stripped `- restore` tag count >= 8                                                                | PASS (exactly 8: 4 include_role + 4 writer-quiesce)                                                                                               |
| `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml`                | PASS (exit 0)                                                                                                                                     |
| `--list-tasks --tags restore` enumerates 4 `Invoke <role> restore` lines                                   | PASS                                                                                                                                              |
| `--list-tasks --tags restore` enumerates the 4 writer-quiesce task names                                   | PASS (Stop Garage writers, Wait for Garage writers to reach stopped state, Start Garage writers, Wait for Garage writers to report healthy)       |
| `git diff --stat` -- exactly 1 new file                                                                    | PASS                                                                                                                                              |

Additional tag-selection sanity checks (not in the plan's automated gate but verified manually):

| Invocation                  | Expected                                                                                                                  | Result                                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `--tags loki` (stateless)   | Only `[always]`-tagged confirm gate + banner (no role include matches). Gate fires if confirm flag missing (D-188 amend.) | PASS -- list-tasks shows only the 2 `[always]` tasks                                                                |
| `--tags garage`             | Confirm gate + banner + 5 bracketed tasks (writer-stop loop + poll + garage include + writer-restart loop + poll)         | PASS                                                                                                                |
| `--tags prometheus`         | Confirm gate + banner + only prometheus include (writers stay running)                                                    | PASS                                                                                                                |
| `--tags restore` (SC4)      | Confirm gate + banner + 4 writer-quiesce tasks + 4 role include_role calls                                                | PASS (8 destructive tasks under --tags restore)                                                                     |

## User Setup Required

None -- the restore orchestrator is a pure Ansible playbook; consumed via the same `ansible-playbook` invocation pattern as `deploy_docker.yml`/`undeploy_docker.yml`. Documentation cascade (root README + `docs/quickstart.md ## Backup and restore` + per-role `## Backup` H2) is Phase 15's scope.

## Next Phase Readiness

- `playbooks/restore_docker.yml` is ready to be consumed by Plan 14-04 (`14-HUMAN-UAT.md`) -- specifically:
  - Scenario 1 (7-step round-trip): step 6 invokes `playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>"` on leviathan.
  - Scenario 2 (confirm-gate proof): sub-test (a) invokes `playbooks/restore_docker.yml` WITHOUT the confirm flag -- MUST fail at the orchestrator-level `[always]` gate. The D-188 amendment specifies this fires for ANY invocation including `--tags <stateless-role>` invocations.
  - Scenario 4 (tag-scoped proof): `--tags grafana --extra-vars backup_restore_confirm=true` MUST restore only Grafana (writers stay running); `--tags loki --extra-vars backup_restore_confirm=true` MUST be an empty 0-task play (no role include matches); `--tags restore --extra-vars backup_restore_confirm=true` MUST run the full destructive surface.
- Phase 13 contract honored: per-role `tasks/restore.yml` gates on `backup_restore_confirm` are the defence-in-depth layer (D-185 acknowledgement); custom playbooks that `include_role: tasks_from=restore` directly still hit the per-role gate (confirmed via `roles/grafana/tasks/restore.yml` lines 84-90).
- No blockers for Plan 14-04 (HUMAN-UAT) or Phase 15 (doc cascade).

## Self-Check: PASSED

- File `playbooks/restore_docker.yml` exists: FOUND
- Commit `2f142b5` exists: FOUND (`feat(14-03): add playbooks/restore_docker.yml restore orchestrator`)

---
*Phase: 14-orchestrators-leviathan-human-uat*
*Plan: 03 -- restore-docker-orchestrator*
*Completed: 2026-06-04*
