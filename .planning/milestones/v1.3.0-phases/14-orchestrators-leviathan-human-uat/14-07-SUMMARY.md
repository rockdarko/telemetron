---
phase: 14-orchestrators-leviathan-human-uat
plan: "07"
subsystem: backup-restore
tags: [uat, leviathan, round-2, gap-closure, G-01, G-03, G-04]
dependency_graph:
  requires: [14-05, 14-06]
  provides: [G-01-behavioral-proof, G-03-partial-behavioral-proof, G-03-addendum-gap, G-04-gap]
  affects:
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
tech_stack:
  added: []
  patterns:
    - "Live passwordless SSH UAT execution against leviathan (mode b: Claude-driven)"
    - "Per-scenario ansible-playbook invocation with tee to /tmp log files"
    - "Fault injection via file-as-dir method (mv + touch) for Prometheus backup fault"
key_files:
  created:
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md
  modified:
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
decisions:
  - "G-01 confirmed CLOSED: scenario 1 step 6 PLAY RECAP failed=0, no manual intervention, writer-rerender handler chain fired correctly under untagged full play"
  - "G-03 opt-in CLOSED: scenario 3b delivers 3 of 4 tarballs with backup_continue_on_failure=true"
  - "G-03-addendum NEW GAP: rescue block absorbs failure even when clear_host_errors skipped -- default bail-out semantics broken"
  - "G-04 NEW GAP: writer-rerender fails under --tags restore (role body tasks lack [restore] tag); scenario 4d-restore FAIL on clean state"
  - "Plan 14-07 NOT marked complete (scenarios 3a + 4d-restore still fail); plan 14-08 needed to close G-03-addendum + G-04"
  - "Vault password: leviathan host_vars/secrets.yml is plaintext (not vault-encrypted); no --ask-vault-pass needed for UAT runs"
metrics:
  duration: "~348 minutes"
  completed: "2026-06-05"
  tasks_completed: 1
  tasks_total: 3
  files_modified: 2
---

# Phase 14 Plan 07: Round-2 Re-UAT on Leviathan Summary

**One-liner:** Round-2 re-UAT on leviathan confirms G-01 closed (scenario 1 PASS, no manual intervention) and G-03 opt-in closed (scenario 3b 3-of-4 tarballs), but surfaces two new gaps: G-03-addendum (rescue absorbs default-mode failure) and G-04 (writer-rerender skipped under --tags restore).

## Mode Used (W-3 Discriminator)

**Mode B: Claude-driven via passwordless SSH.** Rock approved with: `approved (mode b: Claude-driven, docs already updated)`. All 11 sub-scenarios were driven by Claude via SSH against leviathan. Docs updated in-flight (this plan).

Vault discovery: `inventory/leviathan/host_vars/leviathan/secrets.yml` is plaintext (comment confirms "Plaintext for autonomous Claude-driven UAT runs"). No `--ask-vault-pass` flag needed; all ansible-playbook invocations ran without it.

## Re-UAT Execution Summary

| Scenario | Round 1 | Round 2 | Notes |
|----------|---------|---------|-------|
| 1 (7-step round-trip) | fail (G-01) | **PASS** | G-01 CLOSED -- restore_docker.yml completes failed=0, no workaround |
| 2a (orchestrator confirm-gate) | pass | pass | Re-confirmed |
| 2b (per-role confirm-gate) | pass | pass | Re-confirmed |
| 2c (stateless-tag confirm bypass) | pass | pass | Re-confirmed |
| 3a (default bail-out) | pass | **REGRESSION** | G-03-addendum: rescue absorbs failure; grafana+alertmanager run; PLAY RECAP rescued=1 failed=0 |
| 3b (opt-in continue-on-failure) | fail (G-03) | pass | G-03 functional contract CLOSED -- 3 of 4 tarballs |
| 4a (--tags garage) | pass | pass | Re-confirmed |
| 4b (--tags loki, empty play) | pass | pass | Re-confirmed |
| 4c (--tags grafana, writers untouched) | pass | pass | Re-confirmed |
| 4d-backup (--tags backup cross-cutting) | pass | pass | Re-confirmed |
| 4d-restore (--tags restore cross-cutting) | pass (contaminated) | **FAIL** | G-04: writer-rerender skipped under --tags restore; Tempo crash-loop |

## PLAY RECAP Evidence for Key Scenarios

### Scenario 1 Step 6 (G-01 Closure Evidence)

```
leviathan : ok=126  changed=32  unreachable=0  failed=0  skipped=13   rescued=0  ignored=0
```

Key tasks fired in PLAY OUTPUT:
- `garage : Load restored Garage S3 credentials from host file (G-01 fact-population...)` -- ok, garage_s3_access_key_id=GK18e062108528078b3e7ea4f6
- `garage : Set Garage S3 credential facts from restored host file (G-01)` -- ok
- `Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed)` -- included: loki
- `loki : Render Loki config` -- CHANGED
- `Re-render Tempo config from restored Garage s3-credentials (G-01 fix; D-183 reversed)` -- included: tempo
- `tempo : Render Tempo config` -- CHANGED
- `Re-render Mimir config from restored Garage s3-credentials (G-01 fix; D-183 reversed)` -- included: mimir
- `mimir : Render Mimir config` -- CHANGED
- `Flush restart handlers now...` -- RUNNING HANDLER `loki : Docker restart loki`, `tempo : Docker restart tempo`, `mimir : Docker restart mimir` (all fired)
- Writer healthy-poll: all 3 writers healthy (loki/tempo/mimir)

Step 7 smoke with trace_id=c3e28f9aa4cebcc6ffde77a9a5642e44, run_id=1780602309:
```
leviathan : ok=9    changed=0  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```
PLAY OUTPUT summary block: `trace_id: c3e28f9aa4cebcc6ffde77a9a5642e44`, `run_id: 1780602309`, `loki: ok`, `prom: ok`, `mimir: ok`, `tempo: ok`. Same identifiers re-emerged -- data survived the purge+restore cycle across all 4 OTLP signal types.

### Scenario 3a (G-03-addendum Evidence -- Regression)

Fault: `/opt/telemetron/backups/prometheus` replaced with regular file (file-as-dir fault).

```
leviathan : ok=64   changed=9   unreachable=0  failed=0  skipped=0  rescued=1  ignored=0
```

Key lines:
- Prometheus backup fails: `fatal: /opt/telemetron/backups/prometheus already exists as a file`
- Rescue entered; `Prometheus backup failed -- clear host errors (G-03; opt-in only)` -- **SKIPPING** (`when: backup_continue_on_failure | default(false) | bool` evaluates false)
- Grafana include_role RAN (grafana-20260605T010018Z.tar.zst created)
- Alertmanager include_role RAN (alertmanager-20260605T010018Z.tar.zst created)
- Tarballs at run-ts 20260605T010018Z: garage YES, prometheus ABSENT, grafana YES, alertmanager YES

Expected: `failed=1`, grafana/alertmanager NOT attempted. Actual: `rescued=1 failed=0`, all 3 remaining roles ran. **Default bail-out broken.**

### Scenario 3b (G-03 Closure Evidence -- PASS)

```
leviathan : ok=64   changed=9   unreachable=0  failed=0  skipped=0  rescued=1  ignored=0
```

Key lines:
- Banner: `backup_continue_on_failure=true\n  (all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)`
- Prometheus backup fails (same file-as-dir fault)
- Rescue entered; `Prometheus backup failed -- clear host errors (G-03; opt-in only)` -- **RAN** (when-guard evaluates true)
- Grafana include_role RAN (grafana-20260605T010222Z.tar.zst created)
- Alertmanager include_role RAN (alertmanager-20260605T010222Z.tar.zst created)
- Tarballs at run-ts 20260605T010222Z: garage YES, prometheus ABSENT, grafana YES, alertmanager YES

G-03 opt-in contract delivered: 3 of 4 tarballs on single-host inventory.

NOTE: `failed=0 rescued=1` -- PLAY RECAP does not show `failed=1` as originally expected. The rescue absorbs the failure into `rescued=1`. Both modes now produce `failed=0 rescued=1`, making them functionally identical in PLAY RECAP output. The only behavioral difference is whether clear_host_errors runs (and both modes already continue past failures due to the rescue structure).

### Scenario 4d-restore (G-04 Evidence -- FAIL)

Setup: fresh undeploy --purge-data (`ok=64 changed=31 failed=0`) + fresh deploy (`ok=150 changed=64 failed=0`). New S3 key GKc19f6aedb83da95c7756818a generated.

Run: `ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --tags restore --extra-vars "backup_restore_confirm=true backup_restore_from=20260604T194524Z" -v`

```
leviathan : ok=30   changed=10  unreachable=0  failed=1  skipped=4  rescued=0  ignored=0
```

G-01 slurp+set_fact tasks FIRED correctly (tagged [garage, restore]):
- `garage : Load restored Garage S3 credentials from host file (G-01 fact-population...)` -- ok, key GK18e062108528078b3e7ea4f6 populated
- `garage : Set Garage S3 credential facts from restored host file (G-01)` -- ok

Writer-rerender include_role tasks INCLUDED but NO SUBTASKS RAN:
```
TASK [Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed)]
included: loki for leviathan

TASK [Re-render Tempo config from restored Garage s3-credentials (G-01 fix; D-183 reversed)]
included: tempo for leviathan

TASK [Re-render Mimir config from restored Garage s3-credentials (G-01 fix; D-183 reversed)]
included: mimir for leviathan
```

Verbose-log grep: `grep "loki :\|tempo :\|mimir :"` returns 0 matches. `grep "RUNNING HANDLER"` returns 0 matches.

Tempo crash log: `level=error msg="error running Tempo" err="failed to init module services: ... unexpected error from ListObjects on tempo-traces: Forbidden: No such key: GKc19f6aedb83da95c7756818a"` (the post-purge/redeploy key, not the restored GK18e... key).

**G-04 ROOT CAUSE**: `include_role: tasks_from=main` tagged `[garage, restore]` is SELECTED under `--tags restore`, but Ansible's tag-filtering then applies to the role body tasks. Tasks inside `loki/tasks/main.yml` (e.g., `Render Loki config`) do not carry `[restore]` in their tag list. Under `--tags restore`, those subtasks are all skipped. The config file is never re-rendered, no handler is notified, and the writer comes up with the stale config pointing at the wrong S3 key.

Leviathan recovered via full untagged restore (PLAY RECAP `ok=126 changed=32 failed=0`).

## W-5 Closure Status

FAILED. The round-1 4d-restore "pass" was contaminated (scenario 1's workaround had already re-rendered configs). The round-2 clean test surfaces G-04. The writer-rerender path does NOT fire under `--tags restore`.

## New Gaps

### G-03-addendum

**Root cause**: Ansible's `block/rescue` semantics treat a rescue block completing (even with all tasks skipped) as "handling" the failure. The play-level failure counter is not incremented. `any_errors_fatal: true` (from the line-76 inversion in default mode) never triggers because it only fires on play-level FAILURES, not RESCUED outcomes.

**Fix** (1 line per rescue block, 4 rescue blocks): add to each rescue:
```yaml
- name: <Role> backup failed -- re-raise under default mode (G-03-addendum)
  ansible.builtin.fail:
    msg: "<Role> backup failed and backup_continue_on_failure is false -- bailing out (default mode)"
  when: not (backup_continue_on_failure | default(false) | bool)
```
This makes the rescue explicitly re-fail under default mode, propagating the error to play-level. `any_errors_fatal: true` then aborts the play as originally intended.

### G-04

**Root cause**: The writer-rerender include_role tasks in `restore_docker.yml` are tagged `[garage, restore]` at the task level, which selects them under `--tags restore`. But when Ansible descends into the role body, it applies the same `--tags restore` filter to all subtasks. The `loki/tasks/main.yml` tasks (e.g., `loki : Render Loki config`) carry tags like `[loki]` or none, but NOT `[restore]`. They are all skipped.

**Fix** (add `apply:` to each writer-rerender include_role in `restore_docker.yml`):
```yaml
- name: Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed)
  ansible.builtin.include_role:
    name: loki
    tasks_from: main
    apply:
      tags: [garage, restore]    # propagate tags into role body so --tags restore selects subtasks
  tags:
    - garage
    - restore
```
The `apply:` key inherits the specified tags to all tasks within the included role, making them visible to `--tags restore` filtering.

## Deviations from Plan

### [Auto-documented] Scenario 3a: Result is REGRESSION not PASS (G-03-addendum surfaced)

The plan expected scenario 3a to remain `pass` post-G-03 fix (default bail-out preserved). The empirical result is a behavioral regression: the rescue structure introduced by Plan 14-06 absorbs the failure in default mode, making grafana/alertmanager run even without opt-in. This is documented as G-03-addendum.

### [Auto-documented] Scenario 4d-restore: Result is FAIL not PASS (G-04 surfaced)

The plan expected scenario 4d-restore to PASS (W-5 clean closure). The clean re-run surfaces G-04 (tag-inheritance gap in writer-rerender under --tags restore). This was explicitly anticipated as a possible outcome in the plan: "If 4d-restore specifically shows that the writer-rerender did NOT fire under --tags restore: leave 4d-restore as fail, open a new gap G-04."

### [Auto-documented] Plan not marked complete

Per the plan's issue handling: "If any scenario fails or regresses: SUMMARY explicitly notes the failure, the plan is NOT marked complete in tracking." Scenarios 3a (regression) and 4d-restore (fail) prevent full closure. Plan 14-08 needed.

### [Auto-documented] Vault password not needed

The plan documented `--ask-vault-pass`. Discovery: leviathan `host_vars/secrets.yml` is plaintext (comment in file: "Plaintext for autonomous Claude-driven UAT runs"). All ansible-playbook invocations ran without `--ask-vault-pass`. Not a fix -- just a documentation gap in the plan.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Round-2 docs update | cddb3cd | docs(14): HUMAN-UAT + VERIFICATION -- round-2 re-UAT, G-01 closed, G-03 opt-in closed, 2 new gaps (G-03-addendum, G-04) |

## Gap Closure Status

| Gap | Before | After |
|-----|--------|-------|
| G-01 (14-HUMAN-UAT.md) | OPEN -- writers crash-loop post-restore with `Forbidden: No such key:` | CLOSED -- scenario 1 step 6 PLAY RECAP `failed=0`; writer-rerender fires correctly under untagged full play |
| G-03 (14-HUMAN-UAT.md) | OPEN -- backup_continue_on_failure=true no-op on single-host inventories | CLOSED (opt-in case) -- scenario 3b delivers 3 of 4 tarballs; clear_host_errors fires on Prometheus rescue |
| G-03-addendum (NEW) | n/a | OPEN -- default bail-out broken by rescue side effect; scenario 3a regression |
| G-04 (NEW) | n/a | OPEN -- writer-rerender skipped under --tags restore; scenario 4d-restore FAIL on clean state |
| SC5 (ROADMAP.md) | PARTIAL (opt-in broken) | PARTIAL (opt-in closed; default bail-out newly broken) |
| SC6 (ROADMAP.md) | FAILED (manual workaround required) | VERIFIED (untagged full play; G-04 caveat for --tags restore) |

## Self-Check

Files exist:
- `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md` -- present
- `.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md` -- present
- `.planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md` -- this file

Commits:
- cddb3cd -- present (`git log --oneline -1` confirms)

Plan completion: NOT complete (scenarios 3a regression + 4d-restore fail; 2 new gaps G-03-addendum + G-04 require follow-up plan 14-08).
