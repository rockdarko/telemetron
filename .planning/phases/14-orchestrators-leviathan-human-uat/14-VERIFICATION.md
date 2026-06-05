---
phase: 14-orchestrators-leviathan-human-uat
verified: 2026-06-04T19:00:00Z
re_verified: 2026-06-05T02:55:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
gaps: []
human_verification: []
---

# Phase 14: Orchestrators + Leviathan HUMAN-UAT Verification Report

**Phase Goal:** Operators have two symmetric orchestrator playbooks (`backup_docker.yml` and `restore_docker.yml`) with the same `--tags <role>`, `--ask-vault-pass`, and UX conventions as `deploy_docker.yml` and `undeploy_docker.yml`, proven end-to-end on leviathan via the full backup → purge-data undeploy → redeploy → restore → re-smoke round-trip.

**Verified:** 2026-06-04T19:00:00Z
**Re-verified:** 2026-06-05T02:55:00Z
**Status:** passed
**Re-verification:** Yes -- post-G-03-addendum + G-04 closure (Plan 14-08); round-3 leviathan UAT proved scenarios 3a + 4d-restore PASS (see 14-HUMAN-UAT.md round-3 evidence)

## Goal Achievement

The phase ships two symmetric orchestrators with the correct tag UX, banner shapes, and confirm-gate / bail-out / cross-cutting verb contracts. The live leviathan Round 2 UAT was executed 2026-06-05 against the post-14-05+14-06 codebase. 9 of 11 scenarios pass.

G-01 is FULLY CLOSED: scenario 1 (the 7-step round-trip) now completes with `PLAY RECAP failed=0`, NO manual workaround between steps 6 and 7. The writer-config rerender fires correctly under the untagged full play, handler chain fires (loki/tempo/mimir Docker restart), and step 7 smoke re-asserts the same `trace_id c3e28f9aa4cebcc6ffde77a9a5642e44` and `run_id 1780602309` across all 4 OTLP signal types. SC6 is now VERIFIED.

G-03 is FUNCTIONALLY CLOSED for the opt-in case: scenario 3b now delivers 3 of 4 tarballs when `backup_continue_on_failure=true` with a Prometheus fault -- the block/rescue + `meta: clear_host_errors` mechanism works. However:

- **G-03-addendum**: The block/rescue fix has a side effect -- under default mode (`backup_continue_on_failure=false`), the rescue block completing with a SKIPPED `clear_host_errors` task is treated as "handled" by Ansible. The play-level failure counter is not incremented, `any_errors_fatal: true` never triggers, and grafana/alertmanager run anyway. Default bail-out semantics broken. PLAY RECAP shows `rescued=1 failed=0` instead of `failed=1`. Scenario 3a regresses.

- **G-04**: Plan 14-05's writer-rerender tasks are tagged `[garage, restore]` on the include_role invocations, but the tasks inside `loki/tempo/mimir/tasks/main.yml` do NOT carry `restore` tags. Under `--tags restore`, Ansible selects the include_role invocations but then filters out all subtasks within the role body (none have `restore` tag). Zero subtasks execute, zero handlers fire, configs not re-rendered, writers crash-loop. Scenario 4d-restore fails on a clean post-purge state.

Both new gaps (G-03-addendum + G-04) are small, concrete, and fixable in a follow-up plan (14-08+). The core correctness of the orchestrators is validated for the primary (untagged) use case.

All 4 gaps from rounds 1 and 2 are now closed via Plans 14-05 + 14-06 + 14-08. The round-3 leviathan UAT (2026-06-05) empirically verified the two remaining gaps closed: PLAY RECAP `failed=1` for scenario 3a (default-mode bail-out restored by Plan 14-08 Task 1 explicit re-raise in rescue), and PLAY RECAP `failed=0` with 3 role-body subtasks firing (TASK [loki : Render Loki config], TASK [tempo : Render Tempo config], TASK [mimir : Render Mimir config] all CHANGED) for scenario 4d-restore (Plan 14-08 Task 2 `apply: tags: [garage, restore]` propagates tags into role bodies). All 6 must-haves are now verified. Phase 14 milestone acceptance gate closes. Phase 15 (documentation cascade) is unblocked.

### Observable Truths

| # | Truth (Success Criterion from ROADMAP.md) | Status | Evidence |
|---|-------------------------------------------|--------|----------|
| 1 | SC1: `backup_docker.yml` exists, 4 stateful roles in forward order, D-160 PLAY-start banner with target dir + continue-on-failure status; stateless-role tag invocations produce empty 0-task play not a failure | ✓ VERIFIED | `playbooks/backup_docker.yml` (257 lines post-G-03 fix). Lines have 4 block/rescue wrappers in garage→prometheus→grafana→alertmanager order, each carrying tags `[<role>, backup]`. Lines 119-127: D-186 banner with `tags: [always]`. UAT scenario 4a proves `--tags garage` runs only the garage include_role; UAT scenario 4d-backup proves `--tags backup` cross-cutting works (all 4 tarballs at shared ts 20260605T010738Z). Round 2 re-confirmed. |
| 2 | SC2: `restore_docker.yml` stops writers before Garage restore, restores in garage→prometheus→grafana→alertmanager, restarts writers; PLAY-start WARN banner states restore is destructive | ✓ VERIFIED | `playbooks/restore_docker.yml` (313 lines post-G-01 fix). Writer-stop loop at lines 137-149 before Garage restore. Lines 154-173: poll until State.Running==false. Lines 178-184: `include_role: name=garage tasks_from=restore`. Lines 220-242: NEW writer-rerender include_role calls (loki/tempo/mimir tasks_from=main) + flush_handlers. Lines 247-259: writer-restart loop. Lines 265-285: poll until State.Health.Status==healthy. Lines 290-312: prometheus→grafana→alertmanager restore in order. Lines 110-117: D-187 WARN banner. UAT scenario 1 step 6 detail (round 2) confirms all these elements fire. |
| 3 | SC3: `restore_docker.yml` refuses without `--extra-vars backup_restore_confirm=true` at both orchestrator-level AND per-role-level (defence-in-depth) | ✓ VERIFIED | Orchestrator gate: lines 96-105, `ansible.builtin.fail` with `when: not (backup_restore_confirm | default(false) | bool)`, `tags: [always]`. Per-role gates: all 4 stateful roles carry identical gate. UAT scenarios 2a/2b/2c re-confirmed round 2. |
| 4 | SC4: Both playbooks honour `--tags <role>`; `--tags backup` / `--tags restore` cross-cutting verbs work | ✓ VERIFIED | Backup: `--tags backup` cross-cutting works (4d-backup round 2 pass). Restore: `--tags restore` fully works post-Plan-14-08 (4d-restore round 3 pass -- `apply: tags: [garage, restore]` propagates tags into writer role bodies; 3 Render config tasks CHANGED; writers come up healthy). `--tags garage`, `--tags loki`, `--tags grafana` all work per 4a/4b/4c round 2 re-confirmation. G-04 CLOSED. |
| 5 | SC5: `backup_docker.yml` defaults to bail-out on first failure; `backup_continue_on_failure=true` opts into continuing | ✓ VERIFIED | Opt-in side CLOSED (G-03 Plan 14-06): UAT 3b round 2 shows 3 of 4 tarballs at shared ts 20260605T010222Z, `meta: clear_host_errors` fires on Prometheus rescue. Default bail-out RESTORED (G-03-addendum Plan 14-08): UAT 3a round 3 shows PLAY RECAP `failed=1` -- the new explicit ansible.builtin.fail as first rescue task fires under `when: not (backup_continue_on_failure \| default(false) \| bool)`, grafana+alertmanager include_role calls do NOT run (confirmed via grep: 0 matches). Only garage tarball at run-ts 20260605T023305Z. Banner alt-text for default mode is now accurate. Round-3 scenario 3a PLAY RECAP: `leviathan : ok=19   changed=3    unreachable=0    failed=1    skipped=0    rescued=1    ignored=0`. G-03-addendum CLOSED by Plan 14-08 Task 1. |
| 6 | SC6: 14-HUMAN-UAT.md 7-step round-trip completes on leviathan with no manual intervention | ✓ VERIFIED | UAT scenario 1 round 2: PLAY RECAP `ok=126 changed=32 failed=0` for restore step. G-01 fix tasks fired: slurp+set_fact populated garage_s3_access_key_id=GK18e062108528078b3e7ea4f6; loki/tempo/mimir Render config tasks CHANGED; Docker restart handlers FIRED; writer healthy-poll passed. Step 7 smoke PLAY RECAP `ok=9 failed=0` with trace_id=c3e28f9aa4cebcc6ffde77a9a5642e44 and run_id=1780602309 re-emerging. Zero manual intervention. SC6 "no manual intervention" clause UPHELD. Round-3 scenario 4d-restore also verifies the `--tags restore` cross-cutting form: PLAY RECAP `ok=126 changed=32 failed=0`, 3 writer role-body Render tasks CHANGED, all 11 containers healthy, no Forbidden: No such key errors. G-04 CLOSED by Plan 14-08 Task 2. |

**Score:** 6/6 truths verified (all 4 gaps closed: G-01 Plan 14-05, G-03 opt-in Plan 14-06, G-03-addendum Plan 14-08 Task 1, G-04 Plan 14-08 Task 2)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `playbooks/backup_docker.yml` | Thin orchestrator, 4 include_role calls, D-186 banner, shared timestamp, bail-out knob | ✓ VERIFIED | 257 lines. All structural elements present. 4 block/rescue wrappers. G-03 opt-in contract delivered. Post-14-08: each rescue block now has an explicit `ansible.builtin.fail` as first task guarded by `when: not (backup_continue_on_failure \| default(false) \| bool)` to re-raise the failure under default mode; PLAY RECAP `failed=1` (round-3 scenario 3a empirically confirmed). G-03-addendum CLOSED. |
| `playbooks/restore_docker.yml` | Confirm-gated orchestrator, writer-quiesce around Garage, D-187 WARN banner, 4 role restores, NEW writer-config-rerender step (Plan 14-05) | ✓ VERIFIED | 313 lines. Writer-config-rerender step fires correctly under untagged play (scenario 1 round 2 PASS) AND under `--tags restore` (scenario 4d-restore round 3 PASS). Post-14-08: `apply: tags: [garage, restore]` on the 3 writer-rerender include_role calls makes the role body tasks selectable under `--tags restore` (round-3 scenario 4d-restore empirically confirmed; 3 Render config tasks CHANGED, all handlers fired). G-04 CLOSED. |
| `roles/garage/tasks/restore.yml` | Main block + always-restart + NEW slurp+set_fact tail for G-01 fact-population (Plan 14-05) | ✓ VERIFIED | Tail tasks added: `Load restored Garage S3 credentials from host file (G-01 fact-population...)` + `Set Garage S3 credential facts from restored host file (G-01)`. Both tagged [garage, restore]. Fire correctly under both untagged play AND `--tags restore`. |
| `roles/prometheus/tasks/backup.yml` | D-191 timestamp_override amendment via `backup_timestamp_effective` set_fact | ✓ VERIFIED | Line 79 set_fact + lines 133, 143 filename references. |
| `roles/grafana/tasks/backup.yml` | Same amendment | ✓ VERIFIED | Line 88 set_fact + lines 140, 150 filename references. |
| `roles/alertmanager/tasks/backup.yml` | Same amendment | ✓ VERIFIED | Line 119 set_fact + lines 162, 170 filename references. |
| `roles/{4 stateful}/tasks/restore.yml` | Per-role confirm-gate (defence-in-depth) | ✓ VERIFIED | All 4 roles carry `Fail unless backup_restore_confirm is set` task. Scenario 2b round 2 re-confirmed. |
| `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md` | Live UAT round-trip with 11 sub-scenarios | ✓ VERIFIED | Round 3: 11/11 pass. All 4 gaps (G-01, G-03, G-03-addendum, G-04) closed. Milestone acceptance gate verified. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `backup_docker.yml` pre_tasks | 4 role `tasks/backup.yml` | `vars: backup_timestamp_override` → `backup_timestamp_effective` set_fact | ✓ WIRED | Shared-timestamp indirection correctly resolves at each role. UAT scenario 4d-backup round 2 empirically proves all 4 tarballs share one suffix (20260605T010738Z). |
| `restore_docker.yml` writer-stop | Garage restore | Sequential loop + `docker_container_info` poll for State.Running==false | ✓ WIRED | UAT scenario 1 step 6 round 2 confirms writer-stop fires before Garage restore. Scenario 4c round 2 confirms writers untouched when `--tags grafana`. |
| `restore_docker.yml` Garage restore | Writer-config rerender (Plan 14-05) | `roles/garage/tasks/restore.yml` tail slurp+set_fact → `include_role: name=loki tasks_from=main` (and tempo, mimir) | ✓ WIRED | Wiring fires under full untagged play (scenario 1 round 2: loki/tempo/mimir Render config CHANGED, handlers fired) AND under `--tags restore` (scenario 4d-restore round 3: TASK [loki : Render Loki config] changed, TASK [tempo : Render Tempo config] changed, TASK [mimir : Render Mimir config] changed). Post-14-08 `apply: tags: [garage, restore]` propagates tags into role body at runtime. G-04 CLOSED. |
| `restore_docker.yml` writer-rerender | Writer-restart | `meta: flush_handlers` forces restart handlers before healthy-poll | ✓ WIRED | Docker restart handlers fired for loki/tempo/mimir in scenario 1 round 2 AND in scenario 4d-restore round 3 (`RUNNING HANDLER [loki : Docker restart loki]`, `RUNNING HANDLER [tempo : Docker restart tempo]`, `RUNNING HANDLER [mimir : Docker restart mimir]` all fired under `--tags restore`). G-04 CLOSED. |
| `restore_docker.yml` orchestrator gate | Per-role gates | Identical `backup_restore_confirm` var name, both have `when: not (... | default(false) | bool)` | ✓ WIRED | UAT scenarios 2a/2b/2c round 2 all re-confirmed. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BACKUP-V13-05 | 14-02-backup-docker-orchestrator-PLAN.md | `backup_docker.yml` orchestrator iterates 4 stateful roles in forward order, serial, D-160 banner, stateless-tag empty play | ✓ SATISFIED | SC1 verified; UAT scenarios 4a/4d-backup round 2 prove tag UX empirically. |
| RESTORE-V13-05 | 14-03-restore-docker-orchestrator-PLAN.md | `restore_docker.yml` orchestrator: writer-stop → garage→prometheus→grafana→alertmanager → writer-restart with WARN banner | ✓ SATISFIED | G-01 closed: scenario 1 round 2 PLAY RECAP `ok=126 failed=0` proves writers restart healthy after restore with NO manual config-rerender workaround. G-04 also closed: scenario 4d-restore round 3 PLAY RECAP `ok=126 failed=0` on clean post-purge state proves the same writer-stop/rerender/restart chain fires correctly under `--tags restore`. No Forbidden: No such key errors. All 11 containers healthy. |
| OPS-V13-01 | 14-03-restore-docker-orchestrator-PLAN.md | restore_docker.yml refuses without confirm flag; gate fires orchestrator + per-role | ✓ SATISFIED | SC3 verified; UAT scenarios 2a/2b/2c round 2 empirically prove defence-in-depth. Round 3 spot-checked -- no regression. |
| OPS-V13-02 | 14-02-backup-docker-orchestrator-PLAN.md | backup_docker.yml defaults to bail-out; backup_continue_on_failure=true opts into continuing | ✓ SATISFIED | Opt-in mode SATISFIED (scenario 3b round 2: 3 of 4 tarballs, clear_host_errors fired). Default bail-out RESTORED (G-03-addendum Plan 14-08 Task 1): scenario 3a round 3 PLAY RECAP `failed=1`, grafana+alertmanager not attempted. Banner alt-text accurate in both modes. Both contracts empirically verified on leviathan. |
| OPS-V13-03 | Both 14-02 and 14-03 | Both playbooks honour `--tags <role>`; `--tags backup` / `--tags restore` cross-cutting valid | ✓ SATISFIED | `--tags backup` cross-cutting verified (4d-backup round 2 pass). `--tags restore` cross-cutting verified (4d-restore round 3 pass: 3 Render config tasks CHANGED, handlers fired, writers healthy, PLAY RECAP `failed=0`). Per-role tags verified (4a/4b/4c). G-04 CLOSED by Plan 14-08 Task 2. |
| UAT-V13-01 | 14-04-human-uat-PLAN.md | Full backup ↔ restore round-trip proven on leviathan via 14-HUMAN-UAT.md 7-step scenario; round-trip ends with no manual intervention required | ✓ SATISFIED | Round 2 scenario 1 step 6 PLAY RECAP `ok=126 failed=0` with NO manual intervention. Same trace_id+run_id re-emerged across all 4 OTLP signal types after restore. "No manual intervention required" clause upheld. Round-3 scenario 4d-restore also confirms: `--tags restore` cross-cutting form (full purge+redeploy+restore cycle) PLAY RECAP `failed=0`, no Forbidden errors, all 11 containers healthy. Both untagged full play AND `--tags restore` forms are now proven. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `playbooks/restore_docker.yml` | 186-191 | Comment asserts incorrect invariant ("no config re-render needed") -- RESOLVED by Plan 14-05 (comment replaced with correct G-01 rationale) | ✓ RESOLVED | Plan 14-05 replaced the incorrect comment with a 30-line corrected rationale explaining G-01, D-183 REVERSED, and the two-part fix mechanism. |
| `playbooks/restore_docker.yml` | 137-149, 192-204 | `docker stop` / `docker start` loops have no `failed_when:` tolerance (WR-02 / WR-03 in REVIEW) | ⚠️ Warning | Retry after partial failure or against a missing/already-running container produces confusing errors. Not a SC blocker but a hardening gap noted by REVIEW. Pre-existing; out of Phase 14 scope. |
| `playbooks/restore_docker.yml` | 137-149, 192-204 | `docker stop` / `docker start` loops have no `failed_when:` tolerance (WR-02 / WR-03 in REVIEW) | ⚠️ Warning | Retry after partial failure or against a missing/already-running container produces confusing errors. Not a SC blocker but a hardening gap noted by REVIEW. |
| `playbooks/backup_docker.yml`, `playbooks/restore_docker.yml` | banner lines | Some banner var references lack `\| default(...)` (WR-04 in REVIEW) | ℹ️ Info | A BYO inventory missing the backup group_var triggers Jinja stacktrace BEFORE the safety gate. Not a SC blocker. |

Note: No TBD/FIXME/XXX debt markers present in any Phase 14 files.

### Human Verification Required

None -- the live leviathan UAT (both round 1 and round 2) was actually executed. Round 2 surfaces 2 new gaps that need code fixes, not verification.

### Gaps Summary

All 4 gaps from rounds 1 and 2 are now closed:

1. **G-01 (CLOSED by Plan 14-05)**: `restore_docker.yml` writer-config rerender is now operational under the full untagged play. Scenario 1 round 2 step 6 PLAY RECAP `ok=126 failed=0`. Zero manual intervention. Plan 14-05 fix confirmed behaviorally correct.

2. **G-03 (CLOSED for opt-in by Plan 14-06)**: `backup_continue_on_failure=true` opt-in now delivers 3 of 4 tarballs (scenario 3b round 2 PASS). Plan 14-06 block/rescue + `meta: clear_host_errors` works for opt-in mode.

3. **G-03-addendum (CLOSED by Plan 14-08 Task 1)**: The block/rescue side effect from G-03 fix is resolved. An explicit `ansible.builtin.fail` as the first rescue task guarded by `when: not (backup_continue_on_failure | default(false) | bool)` re-raises the failure under default mode. Round-3 scenario 3a PLAY RECAP `failed=1`; grafana + alertmanager not attempted. Banner text ("first role failure will abort the playbook") is now accurate.

4. **G-04 (CLOSED by Plan 14-08 Task 2)**: Plan 14-05's writer-rerender include_role tasks now carry `apply: tags: [garage, restore]`, which propagates the tag list into the loki/tempo/mimir role body tasks at runtime. Round-3 scenario 4d-restore verbose-log shows `TASK [loki : Render Loki config]`, `TASK [tempo : Render Tempo config]`, `TASK [mimir : Render Mimir config]` all firing with CHANGED status. Handlers chain. Writers come up healthy against the restored Garage S3 key. PLAY RECAP `failed=0`.

SC5 + SC6 are both ✓ VERIFIED. RESTORE-V13-05 / OPS-V13-02 / OPS-V13-03 / UAT-V13-01 are all ✓ SATISFIED. Phase 14 milestone acceptance gate closes.

### Recommended Next Path

Phase 14 is now complete with 6/6 must-haves verified. Recommended next step: plan Phase 15 (Documentation Cascade + Gate 11) via `/gsd:plan-phase 15`. The doc cascade references the final playbook flags and operator UX surface, which are now settled.

---

_Verified: 2026-06-04T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verified: 2026-06-05T02:20:00Z_
_Re-verifier: Claude (gsd-verifier; post-G-01+G-03 closure re-UAT round 2)_
_Re-verified: 2026-06-05T02:55:00Z_
_Re-verifier: Claude (gsd-verifier; post-G-03-addendum+G-04 closure re-UAT round 3 -- milestone acceptance gate)_
