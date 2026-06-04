---
phase: 14-orchestrators-leviathan-human-uat
verified: 2026-06-04T19:00:00Z
status: gaps_found
score: 5/6 must-haves verified
overrides_applied: 0
gaps:
  - truth: "SC6: 14-HUMAN-UAT.md 7-step round-trip completes on leviathan with no manual intervention"
    status: failed
    reason: "Round-trip data-survival was proven empirically (same trace_id 47ac47b7804eac0ef04c6f906b25c1ea and run_id 1780594240 re-emerged across all 4 OTLP signal types after restore), but step 6 (restore_docker.yml) failed with `PLAY RECAP failed=1` because Loki/Tempo crash-loop on `Forbidden: No such key: GKf41a2c5494e088bfda8b3a0d` after Garage restore overwrites s3-credentials with the original key while writer configs on host still reference the post-purge-redeploy key. A manual `ansible-playbook ... deploy_docker.yml --tags loki,tempo,mimir,garage` workaround was required before step 7 could pass. SC6 explicitly demands 'no manual intervention.'"
    artifacts:
      - path: "playbooks/restore_docker.yml"
        issue: "G-01: lines 186-230 (writer-restart loop) assume writer configs on host still match restored Garage s3-credentials; no writer-config-rerender step between Garage restore and writer-restart. Comment at lines 186-191 explicitly states the (incorrect) assumption: 'no config re-render needed.'"
      - path: "playbooks/backup_docker.yml"
        issue: "G-03: line 76 `any_errors_fatal: \"{{ not (backup_continue_on_failure | default(false) | bool) }}\"` correctly inverts the play-level abort knob, but Ansible's default behavior still removes the failed host from subsequent task execution. On single-host inventories (leviathan, example-homelab) the `backup_continue_on_failure=true` opt-in is a no-op: only the Garage tarball gets written, not 3 of 4 as the banner alt-text promises."
    missing:
      - "G-01 fix: Add a writer-config-rerender step (recommended: `include_role: name=loki tasks_from=main` for loki/tempo/mimir) to restore_docker.yml AFTER the Garage restore and BEFORE the writer-restart loop, so writer configs are re-rendered from the restored s3-credentials file."
      - "G-03 fix: Wrap each per-role `include_role` in backup_docker.yml with `block:`/`rescue:` where the rescue calls `meta: clear_host_errors` (optionally guarded by `when: backup_continue_on_failure | default(false) | bool` so default-mode behavior is unchanged), so failed-host removal does not silently disable continue-on-failure on single-host inventories."
human_verification: []
---

# Phase 14: Orchestrators + Leviathan HUMAN-UAT Verification Report

**Phase Goal:** Operators have two symmetric orchestrator playbooks (`backup_docker.yml` and `restore_docker.yml`) with the same `--tags <role>`, `--ask-vault-pass`, and UX conventions as `deploy_docker.yml` and `undeploy_docker.yml`, proven end-to-end on leviathan via the full backup → purge-data undeploy → redeploy → restore → re-smoke round-trip.

**Verified:** 2026-06-04T19:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

The phase ships two symmetric orchestrators with the correct tag UX, banner shapes, and confirm-gate / bail-out / cross-cutting verb contracts. The live leviathan UAT was actually executed (not just claimed) and 9 of 11 scenarios pass cleanly. The data-survival heart of UAT-V13-01 — that OTLP signals can be backed up, the stack purged + redeployed, the data restored, and the SAME signals visible in Grafana again — was proven empirically across all 4 signal types (Loki logs, Prometheus metrics, Mimir long-term metrics, Tempo traces) with the same trace_id `47ac47b7...` and run_id `1780594240` re-emerging after restore.

However, two real defects shipped — both caught by the UAT (which is what the UAT is for), both with documented manifests/evidence/fix-plans, both blocking a clean SC6 completion:

- **G-01** (CR-01 in REVIEW): `restore_docker.yml` does not re-render Loki/Tempo/Mimir configs after Garage restore. Step 6 of the round-trip FAILED with `PLAY RECAP failed=1`; a manual `deploy_docker.yml --tags loki,tempo,mimir,garage` workaround was required to bring the writers healthy so step 7 could run. SC6 says "no manual intervention" — this is manual intervention.
- **G-03** (WR-01 in REVIEW): `backup_continue_on_failure=true` is a no-op on single-host inventories. The banner alt-text promises "all 4 roles will attempt their backup," but only the Garage tarball was actually written when Prometheus failed under the opt-in flag.

### Observable Truths

| # | Truth (Success Criterion from ROADMAP.md) | Status | Evidence |
|---|-------------------------------------------|--------|----------|
| 1 | SC1: `backup_docker.yml` exists, 4 stateful roles in forward order, D-160 PLAY-start banner with target dir + continue-on-failure status; stateless-role tag invocations produce empty 0-task play not a failure | ✓ VERIFIED | `playbooks/backup_docker.yml` (174 lines, 7704 bytes). Lines 132-170: 4 `include_role` calls in garage→prometheus→grafana→alertmanager order, each carrying tags `[<role>, backup]`. Lines 89-97: D-186 banner with `tags: [always]` showing `backup_dest_root`, `backup_continue_on_failure` category description, and `backup_stop_timeout`; banner does NOT enumerate role names (D-186 stability principle). UAT scenario 4a proves `--tags garage` runs only the garage include_role; UAT scenario 4d-backup proves `--tags backup` cross-cutting works (all 4 tarballs at shared ts 20260604T175726Z). |
| 2 | SC2: `restore_docker.yml` stops writers before Garage restore, restores in garage→prometheus→grafana→alertmanager, restarts writers; PLAY-start WARN banner states restore is destructive | ✓ VERIFIED | `playbooks/restore_docker.yml` (257 lines, 12308 bytes). Lines 137-149: writer-stop loop over `[loki, tempo, mimir]` before Garage restore. Lines 154-173: poll until State.Running==false. Lines 178-184: `include_role: name=garage tasks_from=restore`. Lines 192-204: writer-restart loop (symmetric with stop). Lines 210-230: poll until State.Health.Status==healthy. Lines 235-257: prometheus→grafana→alertmanager restore in order. Lines 110-117: D-187 WARN banner with `WARNING: irreversible --` prefix, `tags: [always]`. UAT scenario 1 step 6 detail confirms banner fires verbatim. |
| 3 | SC3: `restore_docker.yml` refuses without `--extra-vars backup_restore_confirm=true` at both orchestrator-level AND per-role-level (defence-in-depth) | ✓ VERIFIED | Orchestrator gate: `playbooks/restore_docker.yml` lines 96-105, `ansible.builtin.fail` with `when: not (backup_restore_confirm | default(false) | bool)`, `tags: [always]` (identity-level safety per D-188 amended). Per-role gates (all 4 stateful roles): `roles/{garage,prometheus,grafana,alertmanager}/tasks/restore.yml` each carry the same fail/when pattern (garage:86, prometheus:79, grafana:84, alertmanager:74). UAT scenario 2a proves orchestrator-level refusal; scenario 2b proves per-role refusal via custom include_role playbook; scenario 2c proves the gate cannot be bypassed via `--tags loki` (gate fires before tag-filtering because of `tags: [always]`). |
| 4 | SC4: Both playbooks honour `--tags <role>`; `--tags backup` / `--tags restore` cross-cutting verbs work | ✓ VERIFIED | Backup orchestrator: each `include_role` carries `tags: [<role>, backup]` (lines 138-140, 148-150, 158-160, 168-170). Restore orchestrator: writer-quiesce loops + Garage restore tagged `[garage, restore]` (lines 147-149, 171-173, 182-184, 201-203, 228-230); other 3 role restores tagged `[<role>, restore]` (lines 240-241, 248-249, 256-257). UAT scenarios 4a/4b/4c/4d-backup/4d-restore all pass — `--tags garage`, `--tags loki` (empty), `--tags grafana` (writers untouched), `--tags backup`, `--tags restore` all behave as specified. |
| 5 | SC5: `backup_docker.yml` defaults to bail-out on first failure; `backup_continue_on_failure=true` opts into continuing | ⚠️ PARTIAL | Default bail-out works: line 76 `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` with default `backup_continue_on_failure: false` correctly aborts on first role failure. UAT scenario 3a proves default bail-out: Prometheus fails → grafana/alertmanager never attempted (PLAY RECAP `ok=19 failed=1`, only Garage tarball at run-ts). **However, the opt-in side (G-03) is broken on single-host inventories** — UAT scenario 3b fails: banner correctly fires alt-text, but only Garage tarball is written (grafana + alertmanager tarballs ABSENT at run-ts 20260604T175453Z) because Ansible removes the failed host from subsequent task execution. Counted as VERIFIED-with-caveat because the default-mode contract is met; the opt-in mode breaks the contract on the inventory shape v1.3.0 actually targets. G-03 surfaced here as a separate gap. |
| 6 | SC6: 14-HUMAN-UAT.md 7-step round-trip completes on leviathan with no manual intervention | ✗ FAILED | UAT scenario 1 result: `fail`. Steps 1-5 all pass cleanly (deploy ok=137, smoke ok=9 with trace_id+run_id captured, backup 4 tarballs at shared ts 20260604T173059Z, undeploy --purge-data 0 telemetron volumes, redeploy ok=150). Step 6 (restore) FAILS with `PLAY RECAP failed=1` — Garage restore succeeds, Loki/Tempo crash-loop on `Forbidden: No such key: GKf41a2c5494e088bfda8b3a0d` because writer configs were not re-rendered after Garage restored the s3-credentials file containing the ORIGINAL key. Manual workaround (`ansible-playbook ... deploy_docker.yml --tags loki,tempo,mimir,garage`) was required to bring writers healthy. Step 7 then passes — proves data DID survive the round-trip — but SC6's "no manual intervention" clause is broken by G-01. |

**Score:** 5/6 truths verified (SC5 is met-with-caveat / partial; SC6 is FAILED)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `playbooks/backup_docker.yml` | Thin orchestrator, 4 include_role calls, D-186 banner, shared timestamp, bail-out knob | ✓ VERIFIED | 174 lines, ~7.7 KB. All structural elements present per SC1. |
| `playbooks/restore_docker.yml` | Confirm-gated orchestrator, writer-quiesce around Garage, D-187 WARN banner, 4 role restores | ✓ VERIFIED | 257 lines, ~12.3 KB. All structural elements present per SC2-3; missing writer-config-rerender step (G-01). |
| `roles/garage/tasks/backup.yml` | D-191 timestamp_override amendment via `backup_timestamp_effective` set_fact | ✓ VERIFIED | Line 93: `backup_timestamp_effective: "{{ backup_timestamp_override | default(backup_timestamp.stdout) }}"`. Lines 184, 199 reference `backup_timestamp_effective` for filename. |
| `roles/prometheus/tasks/backup.yml` | Same amendment | ✓ VERIFIED | Line 79 set_fact + lines 133, 143 filename references. |
| `roles/grafana/tasks/backup.yml` | Same amendment | ✓ VERIFIED | Line 88 set_fact + lines 140, 150 filename references. |
| `roles/alertmanager/tasks/backup.yml` | Same amendment | ✓ VERIFIED | Line 119 set_fact + lines 162, 170 filename references. |
| `roles/{4 stateful}/tasks/restore.yml` | Per-role confirm-gate (defence-in-depth) | ✓ VERIFIED | All 4 roles carry `Fail unless backup_restore_confirm is set` task with identical `when: not (backup_restore_confirm | default(false) | bool)` guard (garage:86, prometheus:79, grafana:84, alertmanager:74). |
| `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md` | Live UAT round-trip with 11 sub-scenarios | ✓ VERIFIED | Status `partial`, 9/11 pass, 2 gaps (G-01 + G-03) with manifests/evidence/fix-plans. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `backup_docker.yml` pre_tasks | 4 role `tasks/backup.yml` | `vars: backup_timestamp_override` → `backup_timestamp_effective` set_fact | ✓ WIRED | Shared-timestamp indirection correctly resolves at each role (UAT scenarios 1 step 3 and 4d-backup empirically prove all 4 tarballs share one suffix). |
| `restore_docker.yml` writer-stop | Garage restore | Sequential loop + `docker_container_info` poll for State.Running==false | ✓ WIRED | UAT scenario 1 step 6 detail confirms writer-stop fires before Garage restore; scenario 4c confirms writers untouched when `--tags grafana` (D-189 amended lock holds). |
| `restore_docker.yml` Garage restore | Writer-restart | Symmetric loop + healthcheck poll | ⚠️ PARTIAL | Wiring exists structurally but the operational assumption is wrong (G-01): restart succeeds at docker daemon level but writers immediately crash-loop because configs hold stale S3 key. Healthy-poll times out (30 retries × 2s) and play fails. |
| `restore_docker.yml` orchestrator gate | Per-role gates | Identical `backup_restore_confirm` var name, both have `when: not (... | default(false) | bool)` | ✓ WIRED | UAT scenario 2a proves orchestrator gate; 2b proves per-role gate fires standalone; 2c proves orchestrator gate is unbypassable via `--tags`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BACKUP-V13-05 | 14-02-backup-docker-orchestrator-PLAN.md | `backup_docker.yml` orchestrator iterates 4 stateful roles in forward order, serial, D-160 banner, stateless-tag empty play | ✓ SATISFIED | SC1 verified; UAT scenarios 4a/4d-backup prove tag UX empirically. |
| RESTORE-V13-05 | 14-03-restore-docker-orchestrator-PLAN.md | `restore_docker.yml` orchestrator: writer-stop → garage→prometheus→grafana→alertmanager → writer-restart with WARN banner | ⚠️ PARTIAL | SC2 structurally verified, but G-01 means the writer-restart step does not produce healthy writers without manual config-rerender. |
| OPS-V13-01 | 14-03-restore-docker-orchestrator-PLAN.md | restore_docker.yml refuses without confirm flag; gate fires orchestrator + per-role | ✓ SATISFIED | SC3 verified; UAT scenarios 2a/2b/2c empirically prove defence-in-depth. |
| OPS-V13-02 | 14-02-backup-docker-orchestrator-PLAN.md | backup_docker.yml defaults to bail-out; backup_continue_on_failure=true opts into continuing | ⚠️ PARTIAL | Default bail-out verified (UAT 3a); opt-in side broken on single-host inventories (G-03 / UAT 3b fail). Contract delivered for default mode; contract violated for opt-in mode. |
| OPS-V13-03 | Both 14-02 and 14-03 | Both playbooks honour `--tags <role>`; `--tags backup` / `--tags restore` cross-cutting valid | ✓ SATISFIED | SC4 verified; UAT scenarios 4a/4b/4c/4d-backup/4d-restore prove full tag matrix empirically. |
| UAT-V13-01 | 14-04-human-uat-PLAN.md | Full backup ↔ restore round-trip proven on leviathan via 14-HUMAN-UAT.md 7-step scenario; round-trip ends with no manual intervention required | ✗ BLOCKED | Data-survival proven (same trace_id+run_id re-emerge across all 4 OTLP signal types after restore), but "no manual intervention required" clause violated by the G-01 workaround that step 7 depended on. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `playbooks/restore_docker.yml` | 186-191 | Comment asserts incorrect invariant ("no config re-render needed") that directly causes G-01 | ⚠️ Warning | Misleading rationale baked into the file; future readers may extend the same assumption. Fix should remove or correct the comment alongside the writer-config-rerender insertion. |
| `playbooks/backup_docker.yml` | 76 | `any_errors_fatal` alone does not implement the opt-in contract on single-host inventories | ⚠️ Warning | Operator sees PLAY-start banner promise that the playbook does not deliver. G-03 fix requires `meta: clear_host_errors` in a rescue path. |
| `playbooks/restore_docker.yml` | 137-149, 192-204 | `docker stop` / `docker start` loops have no `failed_when:` tolerance (WR-02 / WR-03 in REVIEW) | ⚠️ Warning | Retry after partial failure or against a missing/already-running container produces confusing errors. Not a SC blocker but a hardening gap noted by REVIEW. |
| `playbooks/backup_docker.yml`, `playbooks/restore_docker.yml` | banner lines | Some banner var references lack `\| default(...)` (WR-04 in REVIEW) | ℹ️ Info | A BYO inventory missing the backup group_var triggers Jinja stacktrace BEFORE the safety gate. Not a SC blocker. |

Note: No TBD/FIXME/XXX debt markers present in any Phase 14 files (grep returns 0 matches across the 6 modified files).

### Human Verification Required

None — the live leviathan UAT was already executed in Phase 14 (per 14-HUMAN-UAT.md). The 2 defects are real, reproducible, and have documented evidence; they do not need re-testing by a human, they need code fixes.

### Gaps Summary

Phase 14 ships substantial, well-structured orchestrators that meet 5 of 6 success criteria cleanly. The 2 defects that block clean SC6 completion are:

1. **G-01 (CR-01) — restore_docker.yml does not re-render writer configs after Garage restore.** Root cause: D-183's assumption (preserved as a comment at lines 186-191) is wrong — restored Garage `s3-credentials` and writer-config files on the host drift apart after a purge-redeploy-restore cycle. Fix: insert `include_role: name=loki tasks_from=main` (and tempo, mimir) between the Garage restore and the writer-restart loop; the role's templating re-reads the restored `garage_s3_credentials_file` and re-renders writer configs. The fix is additive, ~12 lines, and the G-01 fix-plan in 14-HUMAN-UAT.md is sufficient.

2. **G-03 (WR-01) — backup_continue_on_failure=true is a no-op on single-host inventories.** Root cause: `any_errors_fatal: false` controls play-abort but Ansible still removes the failed host from subsequent task execution. The banner promises a contract the orchestrator does not deliver on the very inventory shape v1.3.0 targets (leviathan, example-homelab — both single-host). Fix: wrap each `include_role` in `block:/rescue:` with `meta: clear_host_errors` in the rescue (optionally guarded by the knob); ~16 lines additive.

Both fix-plans are concrete, scoped, and small. Both could land in a single Phase 14.1 amendment plan addressing both gaps, or as a direct two-file amendment to `restore_docker.yml` + `backup_docker.yml`.

The data-survival claim of UAT-V13-01 — that OTLP signals genuinely round-trip through backup → purge → redeploy → restore — IS proven empirically by trace_id `47ac47b7804eac0ef04c6f906b25c1ea` and run_id `1780594240` re-emerging across all 4 signal types after the workaround. The round-trip works. The orchestrator just needs ~28 lines to make the workaround unnecessary.

### Recommended Next Path

**Option A (recommended):** `/gsd:plan-phase 14 --gaps` to produce a focused Phase 14.1 amendment plan addressing G-01 + G-03 together. Both gaps share the same surface area (orchestrator playbooks), have documented fix-plans, and benefit from being closed before Phase 15's documentation cascade locks in the operator-facing contract.

**Option B:** Direct two-file amendment (restore_docker.yml + backup_docker.yml) without a separate phase, if the user prefers a minimal-ceremony fix. Re-run UAT scenarios 1, 3b, and 4d-restore in a clean post-purge state on leviathan to prove closure.

Either path should result in a re-verification pass at 6/6 must-haves with status: passed.

---

_Verified: 2026-06-04T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
