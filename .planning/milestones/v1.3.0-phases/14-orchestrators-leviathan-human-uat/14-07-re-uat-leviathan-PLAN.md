---
phase: 14-orchestrators-leviathan-human-uat
plan: 07
type: execute
wave: 2
depends_on:
  - 14-05
  - 14-06
files_modified:
  - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
  - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
autonomous: false
gap_closure: true
requirements:
  - UAT-V13-01
  - RESTORE-V13-05
  - BACKUP-V13-05
  - OPS-V13-02
requirements_addressed:
  - UAT-V13-01
  - RESTORE-V13-05
  - BACKUP-V13-05
  - OPS-V13-02

must_haves:
  truths:
    - "Live re-UAT executed on leviathan post-G-01-and-G-03-fix. Scenario 1 (the 7-step round-trip) completes with NO manual `deploy_docker.yml --tags loki,tempo,mimir,garage` workaround between steps 6 and 7 -- `restore_docker.yml` step alone delivers healthy writers (proving G-01 closed)."
    - "Scenario 3b (`backup_continue_on_failure=true` with Prometheus fault injected) now produces 3 of 4 tarballs (garage + grafana + alertmanager) at the run's shared timestamp -- not just the Garage tarball -- with `PLAY RECAP failed=1` for Prometheus only (proving G-03 closed)."
    - "Scenario 3a (default `backup_continue_on_failure=false` with Prometheus fault) STILL bails out at Prometheus -- only Garage tarball at run-ts, Grafana + Alertmanager NOT attempted (proves no regression of default-mode behavior from the G-03 block/rescue change)."
    - "Scenario 4d-restore is RE-COLLECTED on a freshly-restored leviathan state (NOT piggybacking on scenario 1's writer-rerender). It is the FIRST CLEAN test of the writer-rerender path under `--tags restore` cross-cutting (vs scenario 1 which runs the full untagged play). The PLAY OUTPUT must show the 3 new writer-rerender include_role invocations + `meta: flush_handlers` fired under `--tags restore` (the round-1 4d-restore evidence is invalid for the post-fix state because round-1 4d-restore succeeded ONLY because scenario 1's workaround had already been applied -- in a clean post-fix environment, 4d-restore exercises the new code path for the first time)."
    - "All 11 sub-scenarios in `14-HUMAN-UAT.md` show `result: pass` after re-UAT. Frontmatter `status:` flips from `partial` to `complete`. `## Summary` updates `passed: 11`, `pending: 0`, `issues: 0`."
    - "`14-HUMAN-UAT.md` Gaps section: G-01 status flips to `closed` with closure commit (Plan 14-05); G-03 status flips to `closed` with closure commit (Plan 14-06). Each Gap entry's `fix-plan` field is amended to reference the actual closure plan (14-05 / 14-06)."
    - "`14-VERIFICATION.md` frontmatter `status:` flips from `gaps_found` to `passed`. `score:` flips to `6/6 must-haves verified`. SC5 status flips from `⚠️ PARTIAL` to `✓ VERIFIED` (with new evidence quoted from re-UAT scenario 3b). SC6 status flips from `✗ FAILED` to `✓ VERIFIED` (with new evidence quoted from re-UAT scenario 1)."
    - "`14-VERIFICATION.md` `gaps:` block in frontmatter is EMPTIED (both G-01 and G-03 are closed)."
    - "`14-VERIFICATION.md` body sections (Observable Truths, Requirements Coverage) are updated: SC5 row VERIFIED with re-UAT evidence; SC6 row VERIFIED with re-UAT evidence; RESTORE-V13-05 / OPS-V13-02 rows flip from ⚠️ PARTIAL to ✓ SATISFIED."
    - "Re-verification marker added: `re_verified: <ISO-timestamp>` in `14-VERIFICATION.md` frontmatter; body's `**Re-verification:**` line flips from `No -- initial verification` to `Yes -- post-G-01+G-03 closure (Plans 14-05, 14-06)`."
    - "Both updated docs are committed in a single git commit citing G-01 + G-03 closure and the re-UAT round number (e.g. 'Round 2')."
  artifacts:
    - path: ".planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md"
      provides: "Updated audit doc -- all 11 sub-scenarios pass post-fix; Gaps G-01 + G-03 marked closed."
      min_lines: 60
      contains: "status: closed"
    - path: ".planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md"
      provides: "Updated verification report -- status: passed; 6/6 must-haves; SC5 + SC6 VERIFIED; gaps block empty."
      min_lines: 80
      contains: "status: passed"
  key_links:
    - from: "Scenario 1 step 6 (`restore_docker.yml` on leviathan, post-14-05 fix)"
      to: "Step 7 (`smoke_test.yml` with captured trace_id + run_id)"
      via: "No manual `deploy_docker.yml --tags loki,tempo,mimir,garage` workaround between steps -- restore alone delivers healthy writers (G-01 closed)"
      pattern: "PLAY RECAP.*failed=0"
    - from: "Scenario 3b (`backup_continue_on_failure=true` + Prometheus fault on leviathan, post-14-06 fix)"
      to: "3 tarballs at shared timestamp (garage + grafana + alertmanager); Prometheus tarball absent; PLAY RECAP failed=1"
      via: "`block/rescue` with `meta: clear_host_errors` keeps leviathan in the active set after Prometheus failure (G-03 closed)"
      pattern: "clear_host_errors"
    - from: "Scenario 3a (default mode + Prometheus fault on leviathan, post-14-06 fix)"
      to: "Garage tarball only; Grafana + Alertmanager NOT attempted; PLAY RECAP failed=1"
      via: "rescue's `when: backup_continue_on_failure | default(false) | bool` evaluates false -> clear_host_errors skipped -> host stays in failed state -> any_errors_fatal aborts the play (no regression)"
      pattern: "failed=1"
    - from: "Scenario 4d-restore on a FRESHLY-RESTORED leviathan state (NOT piggybacking on scenario 1's writer-rerender)"
      to: "PLAY OUTPUT under `--tags restore` shows the 3 new include_role:tasks_from=main invocations (loki, tempo, mimir) + `meta: flush_handlers` firing; PLAY RECAP `failed=0`"
      via: "First clean test of the writer-rerender path under `--tags restore` cross-cutting. The round-1 4d-restore was contaminated by scenario-1's manual workaround having already touched the writer configs; in the post-fix clean state, 4d-restore is the FIRST exercise of the new code path under `--tags restore` (vs scenario 1 which exercises it under the untagged full play)."
      pattern: "include_role.*loki|include_role.*tempo|include_role.*mimir"
    - from: "14-VERIFICATION.md frontmatter `status: gaps_found` and `gaps: [G-01, G-03]`"
      to: "Updated to `status: passed` and empty `gaps: []` (or omitted) -- the source-of-truth for milestone close"
      via: "Manual edit in this plan's Task 2"
      pattern: "status: passed"
---

<objective>
Plans 14-05 and 14-06 land the structural fixes for G-01 and G-03 respectively. This plan is the empirical proof that the fixes work: re-run the 11 sub-scenarios of `14-HUMAN-UAT.md` (or the minimum subset that exercises both fixes -- scenarios 1, 3a, 3b, AND 4d-restore at minimum; planner's recommendation is the full re-run for clean closure) on leviathan and flip the audit doc results to `pass`. Then flip `14-VERIFICATION.md` from `gaps_found` to `passed` with 6/6 must-haves verified.

Purpose: This is the milestone acceptance gate closure for Phase 14. After this plan completes, the v1.3.0 backup/restore round-trip has been proven end-to-end on Rock's leviathan host WITHOUT any manual operator workaround -- the original SC6 acceptance contract.

Output: amended `14-HUMAN-UAT.md` (results flipped to pass; Gaps G-01 + G-03 closed); amended `14-VERIFICATION.md` (status flipped to passed; SC5 + SC6 VERIFIED; gaps block empty); single git commit referencing both fix-plan closures.

NOTE: This plan is `autonomous: false` because the live UAT involves running playbooks against the live leviathan host -- per memory `project_leviathan_uat_host.md`, Rock prefers to drive live UATs himself OR allow Claude to drive via passwordless SSH. The checkpoint format here mirrors Plan 14-04's Task 2 (the original UAT execution checkpoint). Rock decides whether to type the mode-(a) approval string to drive the SSH commands himself and report results back, OR the mode-(b) approval string to let Claude drive end-to-end.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-REVIEW.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-05-restore-writer-config-rerender-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-06-backup-continue-on-failure-clear-host-errors-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-04-human-uat-PLAN.md

@playbooks/backup_docker.yml
@playbooks/restore_docker.yml
@playbooks/smoke_test.yml
@playbooks/deploy_docker.yml
@playbooks/undeploy_docker.yml

<interfaces>
<!-- leviathan inventory (gitignored; lives on Rock's workstation per MEMORY.md project_leviathan_uat_host.md) -->

inventory/leviathan/    : passwordless SSH; Docker 29 on the target; single member host `leviathan` in `telemetron` group

<!-- smoke_test.yml outputs to capture (scenario 1 step 2) -->

smoke_test.yml prints to PLAY OUTPUT:
  trace_id: <32-char hex>     (line 219 of smoke_test.yml; lookup('password', length=32, chars=hexdigits))
  run_id:   <epoch seconds>   (line 220 of smoke_test.yml; ansible_date_time.epoch)
  loki:     ok                (line 215-224 summary block; smoke_assert_loki asserter)
  prom:     ok                (smoke_assert_prometheus)
  mimir:    ok                (smoke_assert_mimir)
  tempo:    ok                (smoke_assert_tempo)

Step 2 captures all 6 values; step 7 re-passes trace_id + run_id via --extra-vars and asserts the same 4
"<role>: ok" lines reappear (proving all 4 OTLP signal types round-tripped).

<!-- Scenario 3 fault-injection (per the actual UAT-round-1 evidence in 14-HUMAN-UAT.md scenario 3a detail) -->

The 14-04 plan documented `chmod 000` as the fault. Empirically that did NOT work because the backup task
runs with `become: true` and root bypasses directory permissions (CAP_DAC_OVERRIDE). The 14-HUMAN-UAT.md
scenario 3a detail pivoted to a "file-as-dir" fault:

  Setup:
    ssh leviathan "sudo mv /opt/telemetron/backups/prometheus /opt/telemetron/backups/prometheus.SAVED"
    ssh leviathan "sudo touch /opt/telemetron/backups/prometheus"
  Cleanup:
    ssh leviathan "sudo rm /opt/telemetron/backups/prometheus"
    ssh leviathan "sudo mv /opt/telemetron/backups/prometheus.SAVED /opt/telemetron/backups/prometheus"
    (mode back to 0700 -- preserved by the SAVED rename)

The re-UAT MUST use this proven fault-injection (matching the UAT-round-1 method), not the ineffective
chmod 000.

<!-- Pre-existing UAT-round-1 evidence to PRESERVE in the re-UAT update -->

For scenarios that already passed in round 1 (2a/2b/2c/3a/4a/4b/4c/4d-backup -- 8 total), their evidence
sections are factually correct and can be preserved verbatim (just append a "Round 2 re-confirmation:
<result>" line) -- the re-UAT confirms they still pass post-fix and does not need to re-collect every
byte of evidence. Pragmatic guidance: re-run them, confirm pass, append round-2 marker.

The scenarios that NEED full re-collection are scenario 1 (was: fail -- now: pass), scenario 3b (was:
fail -- now: pass), AND scenario 4d-restore (was: pass-but-contaminated -- now: pass-clean). Their detail
sections must be re-written with the fresh PLAY OUTPUT from the re-run.

W-5 EXPLANATION: scenario 4d-restore is PROMOTED from the "no-change-expected" bucket to the
"must-be-re-collected" bucket. Per the 14-HUMAN-UAT.md scenario 4d-restore detail (round 1): "4d-restore
succeeded here BECAUSE the G-01 workaround was already applied in scenario 1. In a clean environment,
4d-restore would also hit G-01." In the round-2 sequence (post-fix), the leviathan state at the time
4d-restore runs is freshly-restored (scenario 1's automatic writer-rerender has happened, but in a
clean repeat run that exercises `--tags restore` specifically -- not the untagged full play scenario 1
used). 4d-restore therefore becomes the FIRST clean test of the new writer-rerender path under
`--tags restore` cross-cutting. The round-1 evidence is invalidated by this distinction and must be
re-collected. Verification: the PLAY OUTPUT must show the 3 new writer-rerender include_role lines
(`Re-render Loki config from restored Garage s3-credentials`, etc.) AND the `meta: flush_handlers`
task firing under `--tags restore`. Grep the verbose log (`-v`) for those include_role names to
empirically confirm the new code path fired.
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Live re-UAT on leviathan -- re-run the 11 sub-scenarios post-G-01-and-G-03-fix and capture evidence</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md</files>
  <read_first>
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md (the round-1 audit doc; round-2 update will preserve the structure and update results)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md (the round-1 verification report; identifies the 2 gaps and SC5/SC6 status)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-05-restore-writer-config-rerender-PLAN.md (G-01 fix-plan -- what changed in restore_docker.yml AND roles/garage/tasks/restore.yml)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-06-backup-continue-on-failure-clear-host-errors-PLAN.md (G-03 fix-plan -- what changed in backup_docker.yml)
    - playbooks/restore_docker.yml + playbooks/backup_docker.yml + roles/garage/tasks/restore.yml (post-fix state; what is actually under test)
    - playbooks/smoke_test.yml lines 40-60 + 119-200 + 215-225 (smoke_trace_id and smoke_run_id mechanics; the 4 asserter tasks for Loki/Prometheus/Mimir/Tempo)
    - MEMORY.md project_leviathan_uat_host.md (leviathan is the UAT host; ssh passwordless; Docker 29; inventory/leviathan/ gitignored and present on workstation; Rock prefers to drive live UATs himself but Claude may drive via passwordless SSH)
  </read_first>
  <what-built>
    Plan 14-05 amended `playbooks/restore_docker.yml` to insert a writer-config-rerender step (3 `include_role: tasks_from=main` for loki/tempo/mimir + `meta: flush_handlers`) between the Garage restore and the writer-restart loop, AND amended `roles/garage/tasks/restore.yml` to slurp + set_fact `garage_s3_access_key_id` and `garage_s3_secret_key` after the restore (so the writer templates resolve correctly). Plan 14-06 amended `playbooks/backup_docker.yml` to wrap each per-role `include_role` in `block:/rescue:` with `ansible.builtin.meta: clear_host_errors` guarded by `when: backup_continue_on_failure | default(false) | bool`, while retaining the inner include_role tag list (W-4 mitigation). Both fixes preserve all pre-existing tag semantics and default-mode behavior. This checkpoint task runs the live re-UAT to empirically prove the fixes deliver G-01 + G-03 closure on leviathan.
  </what-built>
  <how-to-verify>
    LEVIATHAN PRE-FLIGHT (mandatory first step, mirrors Plan 14-04's W-4 mitigation): Run `ssh -o BatchMode=yes -o ConnectTimeout=5 leviathan true`. If non-zero exit, ABORT this task and surface to the developer: "leviathan unreachable -- fix host connectivity before running re-UAT". Do NOT leave the task in `in_progress` indefinitely.

    Only proceed past the pre-flight if it succeeded.

    OPERATOR CHOICE (W-3 disambiguated -- mode (a) Rock-driven OR mode (b) Claude-driven via passwordless SSH; per memory both modes are valid):
    Rock decides which mode at the checkpoint. The resume-signal string is the discriminator (see
    <resume-signal> below). The two modes have DIFFERENT post-checkpoint flows:

    (a) MODE A -- Rock-driven, evidence attached:
        Rock runs the 11 sub-scenarios himself via the workstation and attaches verbatim PLAY RECAP +
        key PLAY OUTPUT lines for each scenario as part of his resume-signal message. Claude then
        reads the attached evidence and proceeds to Tasks 2 + 3 to update the docs from Rock's
        reports. Claude does NOT re-run any scenarios.

    (b) MODE B -- Claude-driven via passwordless SSH:
        Claude runs the 11 sub-scenarios end-to-end via passwordless SSH and updates the docs.
        Rock's resume-signal authorizes Claude to drive; Claude reports back with a SUMMARY when
        all scenarios complete (or pauses to surface a failure for Rock's input).

    (b') MODE B' -- Claude-driven IN-FLIGHT (docs already updated):
        Variant of mode B where Claude updates 14-HUMAN-UAT.md detail sections as each scenario
        completes rather than batching at the end. Rock's resume-signal acknowledges that the
        docs are already updated in-flight; Claude verifies the docs were updated before marking
        Task 1 done.

    Execute the 11 sub-scenarios sequentially against leviathan. Scenario-specific guidance:

    --- SCENARIO 1 (the round-trip; the headline G-01 closure test) ---

    Re-run all 7 steps. Step 6 is the critical test: `ansible-playbook -i inventory/leviathan
    playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true
    backup_restore_from=<shared-ts-from-step-3>"`. POST-FIX EXPECTED BEHAVIOR:
      - PLAY OUTPUT shows the WARN banner.
      - Writer-stop loop fires (loki/tempo/mimir stop; poll confirms State.Running == false).
      - Garage restore include_role fires (restores volumes + s3-credentials).
      - NEW (post-G-01 Plan 14-05 Task 1): the tail of garage/restore.yml slurp + set_fact's
        `garage_s3_access_key_id` and `garage_s3_secret_key` from the restored credentials file
        (PLAY OUTPUT shows two tasks under the garage include_role label: `Load restored Garage S3
        credentials from host file (G-01 fact-population for writer-config re-render)` and
        `Set Garage S3 credential facts from restored host file (G-01; mirrors bootstrap.yml:140-147)`).
      - NEW (post-G-01 Plan 14-05 Task 2): 3 include_role calls for loki/tempo/mimir tasks_from=main
        -- each re-renders its writer config from the just-restored facts AND notifies its restart
        handler.
      - NEW (post-G-01 Plan 14-05 Task 2): meta: flush_handlers fires -- handlers run `docker
        restart <writer>` NOW (rather than at end of play).
      - Writer-restart `docker start` loop fires (idempotent against already-restarted containers).
      - Writer healthy-poll succeeds (State.Health.Status == healthy for all 3 writers).
      - prometheus + grafana + alertmanager restores fire in order.
      - PLAY RECAP `failed=0`. NO `Forbidden: No such key` error in any container log. All 11
        containers healthy.
    Capture: full PLAY RECAP, key task lines showing the new garage tail set_fact tasks AND the 3
    rerender + flush_handlers tasks fired, docker ps showing all 11 containers healthy.

    Step 7 (`smoke_test.yml` with captured trace_id + run_id) MUST pass with the same 4 "<role>: ok"
    lines re-emerging in PLAY OUTPUT -- this proves the same OTLP signals round-tripped AND that the
    G-01 fix did not introduce any data-survival regression.

    --- SCENARIO 3a (default-mode bail-out; the G-03-no-regression test) ---

    Re-run with the file-as-dir fault (NOT chmod 000 -- that does not work against become=true tasks):
      ssh leviathan "sudo mv /opt/telemetron/backups/prometheus /opt/telemetron/backups/prometheus.SAVED"
      ssh leviathan "sudo touch /opt/telemetron/backups/prometheus"
    Run: `ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass`
    POST-FIX EXPECTED BEHAVIOR (no regression):
      - PLAY-start banner shows default-mode alt text (`(first role failure will abort the playbook)`).
      - Garage backup succeeds (garage-<ts>.tar.zst at /opt/telemetron/backups/garage/).
      - Prometheus backup fails at the `Ensure Prometheus backup destination directory exists` task
        with `"/opt/telemetron/backups/prometheus already exists as a file"`.
      - The Prometheus block's rescue is REACHED but the `when: backup_continue_on_failure |
        default(false) | bool` guard evaluates FALSE -> meta: clear_host_errors is SKIPPED -> host
        stays in failed state.
      - `any_errors_fatal: true` (default-mode evaluation of the inverted expression) aborts the play.
      - Grafana + Alertmanager include_role calls do NOT run (no host in active set, AND play
        aborted).
      - PLAY RECAP `failed=1`. ls confirms only garage tarball at the run-ts.
    Cleanup:
      ssh leviathan "sudo rm /opt/telemetron/backups/prometheus"
      ssh leviathan "sudo mv /opt/telemetron/backups/prometheus.SAVED /opt/telemetron/backups/prometheus"
    Capture: PLAY RECAP, ls listings, confirmation that the rescue task fired then was when-skipped
    (the `skipped: [leviathan]` line on the clear_host_errors task is the key evidence -- proves the
    rescue structure is correct AND that default-mode behavior is preserved).

    --- SCENARIO 3b (opt-in mode; the headline G-03 closure test) ---

    Re-run with the SAME file-as-dir fault as 3a. Then run with the opt-in flag:
    `ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --extra-vars
    "backup_continue_on_failure=true"`
    POST-FIX EXPECTED BEHAVIOR:
      - PLAY-start banner shows opt-in alt text (`(all 4 roles will attempt their backup; failures
        aggregated in PLAY RECAP)`).
      - Garage backup succeeds.
      - Prometheus backup fails (same file-as-dir fault).
      - The Prometheus block's rescue is REACHED, `when: backup_continue_on_failure | default(false) |
        bool` evaluates TRUE, `meta: clear_host_errors` RUNS -> leviathan returns to the active set.
      - `any_errors_fatal: false` (opt-in mode evaluation) does NOT abort.
      - Grafana include_role RUNS -> grafana tarball at run-ts.
      - Alertmanager include_role RUNS -> alertmanager tarball at run-ts.
      - PLAY RECAP `failed=1` (Prometheus only). 3 of 4 tarballs at run-ts (garage + grafana +
        alertmanager; prometheus absent).
    Cleanup: same as 3a.
    Capture: PLAY RECAP, ls listings showing 3 of 4 tarballs sharing the run timestamp, the rescue
    task's PLAY OUTPUT line showing clear_host_errors RAN (not skipped) on the Prometheus rescue.
    THIS IS THE G-03 CLOSURE EVIDENCE.

    --- SCENARIO 4d-restore (W-5: PROMOTED from no-change-expected to must-be-re-collected) ---

    Per W-5 from the plan-checker, the round-1 4d-restore "passed" only because scenario 1's manual
    workaround had ALREADY been applied to writer configs -- the round-1 4d-restore did NOT actually
    exercise the writer-rerender code path under `--tags restore`. In a clean post-fix environment,
    4d-restore is the FIRST clean test of the new writer-rerender path under `--tags restore`
    cross-cutting (scenario 1 exercises the untagged full play; 4d-restore is the targeted-tag
    cousin).

    The 4d-restore re-run MUST be performed on a FRESHLY-RESTORED leviathan state (NOT immediately
    after scenario 1 -- the writer configs from scenario 1 are already "fresh" and would mask the
    rerender effect). Recommended setup:
      1. Run scenario 1 step 4 (undeploy --purge-data) to wipe state cleanly.
      2. Run scenario 1 step 5 (deploy_docker.yml) to bootstrap fresh Garage (NEW S3 key).
      3. (Do NOT run scenario 1 step 6 first.)
      4. Run: `ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass
         --tags restore --extra-vars "backup_restore_confirm=true backup_restore_from=<shared-ts>"`

    POST-FIX EXPECTED BEHAVIOR (4d-restore under --tags restore):
      - PLAY OUTPUT enumerates the writer-stop loop, garage restore include_role, the NEW garage
        restore.yml tail set_fact tasks, the 3 NEW writer-rerender include_role invocations (loki,
        tempo, mimir tasks_from=main), `meta: flush_handlers`, the writer-restart loop, the writer
        healthy-poll, and the prometheus/grafana/alertmanager restores.
      - PLAY RECAP `failed=0`. All writers healthy.
      - Empirical verification: pass `-v` (verbose) on the re-run AND grep the saved log for the
        include_role invocation names (e.g., `Re-render Loki config from restored Garage
        s3-credentials` substring) to PROVE the new code path fired under `--tags restore`. If
        those grep lines are absent, the tag inheritance is broken and the fix is incomplete --
        leave the scenario `result: fail` and open a follow-up gap.

    Capture: full PLAY RECAP, the verbose-log grep lines showing the 3 new include_role
    invocations + `meta: flush_handlers` fired under `--tags restore`, docker ps confirming all
    writers healthy. THIS IS THE W-5 CLOSURE EVIDENCE (clean exercise of the `--tags restore`
    cross-cutting path).

    --- SCENARIOS 2a/2b/2c/4a/4b/4c/4d-backup (no-change-expected; round-2 re-confirmation) ---

    These passed in round 1 and the fixes do NOT touch their surface area. Re-run each (cheap; each
    is a single ansible-playbook invocation with documented expected behavior) and append a round-2
    marker to each `detail:` field:
      `Round 2 re-confirmation (post-G-01/G-03 fix): PASS. PLAY RECAP <quote one-line recap>.`
    No need to re-collect the full verbatim evidence; the round-1 evidence is still factually correct.

    NOTE: 4d-restore is NOT in this bucket per W-5 -- see the dedicated 4d-restore section above.

    --- DOCUMENT UPDATES AFTER ALL 11 SCENARIOS COMPLETE ---

    Edit `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md`:
    - Frontmatter: `status: complete`, `updated:` to the latest ISO 8601 UTC timestamp with Z suffix.
    - `## Current Test`: replace round-1 bracket with `[Round 2 complete <date>. All 11 sub-scenarios
      pass on leviathan post-G-01/G-03 closure (Plans 14-05, 14-06). G-01 + G-03 behaviorally closed.]`
    - Scenario 1 `result:` flips from `fail` to `pass`. `detail:` is REWRITTEN with the round-2 PLAY
      RECAP, key task names confirming the garage restore.yml tail set_fact tasks fired AND the 3
      writer rerender + flush_handlers + writer-restart sequence fired, docker ps confirming 11
      healthy, and step 7 PLAY OUTPUT re-quoting the 4 asserter "ok" lines AND the same trace_id +
      run_id values. Round-1 detail is REPLACED (not retained) because the round-1 detail documented
      the failure path.
    - Scenario 3a `result:` stays `pass`. `detail:` is AMENDED with the round-2 marker AND a new
      sentence confirming `meta: clear_host_errors` was when-skipped under default mode (PLAY OUTPUT
      line: `skipping: [leviathan] => (item=...) <clear_host_errors task>`).
    - Scenario 3b `result:` flips from `fail` to `pass`. `detail:` is REWRITTEN with round-2 PLAY
      RECAP, ls output confirming 3 of 4 tarballs at the shared timestamp, and the PLAY OUTPUT line
      confirming `meta: clear_host_errors` RAN on the Prometheus rescue. THIS IS THE G-03 CLOSURE
      EVIDENCE.
    - Scenario 4d-restore `result:` stays `pass` BUT `detail:` is REWRITTEN (not amended) with the
      round-2 clean re-run evidence: PLAY RECAP `failed=0`, the verbose-log grep lines showing the 3
      new include_role invocations + `meta: flush_handlers` fired under `--tags restore`. Add an
      explicit sentence in the new detail noting that the round-1 evidence was contaminated by
      scenario-1's manual workaround and this is the first clean exercise of the writer-rerender
      path under `--tags restore` (W-5 closure).
    - Other 7 sub-scenarios `result:` stays `pass`. `detail:` is AMENDED with a one-line round-2 marker.
    - `## Summary`: `passed: 11`, `pending: 0`, `issues: 0`.
    - `## Gaps`: both G-01 and G-03 entries flip `status: open` -> `status: closed`. Add a `closed-in:`
      field citing `14-05-restore-writer-config-rerender-PLAN.md` for G-01 and
      `14-06-backup-continue-on-failure-clear-host-errors-PLAN.md` for G-03. Add a one-paragraph
      `closure-evidence:` field citing the round-2 PLAY OUTPUT excerpts that prove the gap is closed.

    Verification gates the orchestrator/human will use:
    - File contains `status: complete` in frontmatter.
    - 0 occurrences of `^result: pending`. 0 occurrences of `^result: fail` (all 11 are now pass).
    - At least 11 occurrences of `^result: pass`.
    - `## Summary` shows `passed: 11`, `pending: 0`, `issues: 0`.
    - Scenario 1 detail quotes `failed=0` for the restore step (NOT failed=1 like round 1).
    - Scenario 3b detail quotes 3 tarballs at the shared timestamp (garage + grafana + alertmanager).
    - Scenario 3a detail quotes `skipping` on the clear_host_errors task (proving default-mode
      preservation).
    - Scenario 4d-restore detail quotes the 3 writer-rerender include_role invocation names AND
      `meta: flush_handlers` firing under `--tags restore` (W-5 closure -- proves clean exercise
      of the `--tags restore` cross-cutting path).
    - Both Gaps show `status: closed` with `closed-in:` field citing the right closure plan.

    Issue/blocker handling:
    - If leviathan pre-flight fails: ABORT and surface to developer (W-4 from 14-04 Task 2).
    - If a re-run scenario STILL fails (G-01 or G-03 fix is incomplete): leave that scenario's
      `result: fail`; document the new failure mode in the Gap entry; open a follow-up plan (14-08+).
    - If a previously-passing scenario regresses (e.g., 4c writer-untouched breaks because the G-01
      fix accidentally fires writer-rerender under `--tags grafana`): leave that scenario's
      `result: fail`; flag the regression in the resume-signal.
    - If 4d-restore specifically shows that the writer-rerender did NOT fire under `--tags restore`
      (the verbose-log grep finds nothing): the W-4 mitigation in Plan 14-06 worked for backup
      tags but the analogous tag-resolution must be re-checked for the new restore tags from Plan
      14-05 Task 2; leave 4d-restore as `fail`, open a new gap G-04 (tag-leakage on writer-rerender
      under --tags restore).
  </how-to-verify>
  <resume-signal>
    Type ONE of these EXACT discriminators (the prefix `approved (mode <X>: ...)` is the parse key for
    Claude's downstream action):

      - `approved (mode a: Rock-driven, evidence attached)` -- Rock has run all 11 scenarios himself
        and attached PLAY RECAP + key PLAY OUTPUT lines for scenarios 1, 3a, 3b, and 4d-restore at
        MINIMUM in the resume message. If mode (a), Claude reads the attached evidence and proceeds
        to Tasks 2 + 3 to update docs from Rock's reports. Claude does NOT re-run any scenarios.

      - `approved (mode b: Claude-driven, docs already updated)` -- Claude drove the scenarios via
        passwordless SSH and updated 14-HUMAN-UAT.md detail sections in-flight. If mode (b), Claude
        verifies the docs were updated in-flight before marking Task 1 done.

    Otherwise, describe which scenarios failed or regressed and whether new Gap entries (G-04+) are
    needed. Any other response (a bare "approved" without the mode discriminator, or a "looks good")
    means Task 1 is NOT done -- Claude must surface ambiguity and re-prompt for the explicit
    discriminator.
  </resume-signal>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Flip 14-VERIFICATION.md status to passed and update SC5/SC6 rows + Requirements Coverage</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md</files>
  <read_first>
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md (current state; round-1 verification with status: gaps_found)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md (post-Task-1 state; the round-2 audit doc that this update cites as the proof)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-05-restore-writer-config-rerender-PLAN.md + 14-05-SUMMARY.md (the G-01 closure plan and its summary; cite the closure commit if known)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-06-backup-continue-on-failure-clear-host-errors-PLAN.md + 14-06-SUMMARY.md (the G-03 closure plan and its summary)
  </read_first>
  <action>
    Edit `.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md`:

    1. **Frontmatter updates:**
       - `status:` flip from `gaps_found` to `passed`.
       - `score:` flip from `5/6 must-haves verified` to `6/6 must-haves verified`.
       - Add a new field `re_verified: <ISO 8601 UTC timestamp with Z suffix>` reflecting now (e.g.,
         `re_verified: 2026-06-05T14:23:00Z`). Place it immediately under the existing `verified:` field.
       - `gaps:` block: REPLACE the array of 2 gap entries with an empty array `gaps: []` (or omit the key
         entirely if the YAML schema allows).
       - `overrides_applied:` stays 0.
       - `human_verification:` stays `[]`.

    2. **Body update -- the `**Verified:**` / `**Status:**` / `**Re-verification:**` block** (currently at
       lines 26-28):
       - `**Verified:**` is the ORIGINAL round-1 timestamp -- preserve verbatim (audit trail).
       - `**Re-verified:**` is NEW -- add a line `**Re-verified:** <ISO 8601 UTC>` immediately under
         `**Verified:**`.
       - `**Status:**` flip from `gaps_found` to `passed`.
       - `**Re-verification:**` flip from `No -- initial verification` to `Yes -- post-G-01+G-03 closure
         (Plans 14-05, 14-06; re-UAT round 2 -- see 14-HUMAN-UAT.md scenario 1 + 3a + 3b + 4d-restore)`.

    3. **Body update -- the `## Goal Achievement` paragraph** (currently the second sentence ends with
       "blocking a clean SC6 completion"): append a new paragraph at the END of the section stating that
       both G-01 and G-03 have been closed via Plans 14-05 + 14-06, that the re-UAT on leviathan (round 2)
       has flipped SC5 from PARTIAL to VERIFIED and SC6 from FAILED to VERIFIED, and that the milestone
       acceptance gate is now passed. Reference 14-HUMAN-UAT.md scenarios 1, 3a, 3b, and 4d-restore for the
       empirical evidence (4d-restore is the W-5 closure -- clean exercise of `--tags restore`
       cross-cutting writer-rerender).

    4. **Body update -- `### Observable Truths` table** (currently lines 41-48): two rows change:
       - SC5 row: flip `⚠️ PARTIAL` to `✓ VERIFIED`. REPLACE the Evidence cell with: a one-sentence note that
         default-mode bail-out still verified (UAT 3a round-2 confirms `meta: clear_host_errors` is
         when-skipped under default), PLUS new evidence from UAT 3b round-2: `backup_continue_on_failure=true`
         now produces 3 of 4 tarballs at the shared timestamp (garage + grafana + alertmanager). Quote the
         PLAY RECAP `failed=1` and the ls output from 14-HUMAN-UAT.md scenario 3b round-2 detail. Cite Plan
         14-06 as the closure plan.
       - SC6 row: flip `✗ FAILED` to `✓ VERIFIED`. REPLACE the Evidence cell with: a one-sentence note that
         the 7-step round-trip on leviathan now completes with NO manual intervention. Quote the round-2
         scenario-1 step-6 PLAY RECAP `failed=0` and the post-restore healthy-container count (11/11). Cite
         Plan 14-05 as the closure plan. ALSO cite scenario 4d-restore round-2 as the clean exercise of the
         `--tags restore` cross-cutting writer-rerender (W-5 closure -- proves the new code path fires
         under tag-scoped invocation, not only under the untagged full play).

    5. **Body update -- `### Required Artifacts` table**: the `playbooks/restore_docker.yml` row updates --
       remove the "missing writer-config-rerender step (G-01)" caveat from the Details cell; add a one-line
       note that the writer-config-rerender step now exists (cite Plan 14-05). Add a new row (or extend the
       existing garage row) for `roles/garage/tasks/restore.yml` noting the new slurp + set_fact tail tasks
       (G-01 fact-population, Plan 14-05 Task 1).

    6. **Body update -- `### Key Link Verification` table**: the writer-restart row (currently `⚠️ PARTIAL`)
       flips to `✓ WIRED`. Update the Details cell to remove the G-01 caveat about stale S3 key crash-loop;
       add a one-line note that writer configs are now re-rendered from restored s3-credentials before the
       restart healthy-poll fires (cite Plan 14-05).

    7. **Body update -- `### Requirements Coverage` table**: two rows change:
       - `RESTORE-V13-05` row: flip `⚠️ PARTIAL` to `✓ SATISFIED`. Update the Evidence cell to remove the
         G-01 caveat; add a one-line note citing round-2 scenario 1 step 6 PLAY RECAP `failed=0`.
       - `OPS-V13-02` row: flip `⚠️ PARTIAL` to `✓ SATISFIED`. Update the Evidence cell to confirm both
         default-mode bail-out AND opt-in continue-on-failure are now empirically verified. Cite round-2
         scenarios 3a (default, skipped clear_host_errors) and 3b (opt-in, ran clear_host_errors).
       - `UAT-V13-01` row: flip `✗ BLOCKED` to `✓ SATISFIED`. Update the Evidence cell to confirm the
         "no manual intervention" clause is now upheld; cite round-2 scenario 1 step 6 AND round-2
         scenario 4d-restore (clean `--tags restore` exercise per W-5 closure).

    8. **Body update -- `### Anti-Patterns Found` table** (currently lines 88-93): two rows update:
       - The `restore_docker.yml:186-191` row (the incorrect comment): mark as RESOLVED by Plan 14-05.
         Either delete the row OR add a `Resolution:` column citing Plan 14-05; pick the deletion form for
         cleanliness (the comment is gone from the file post-fix).
       - The `backup_docker.yml:76` row (`any_errors_fatal` alone is insufficient): mark as RESOLVED by
         Plan 14-06. Either delete the row OR add a Resolution note.
       - The WR-02/03 row (docker stop/start idempotency) STAYS -- those are pre-existing concerns NOT
         closed by this gap-closure phase; they remain as known debt.
       - The WR-04 banner default(...) row STAYS -- pre-existing info-level concern, not in scope.

    9. **Body update -- `### Gaps Summary` section** (currently lines 100-110): REPLACE the paragraph with
       a closure narrative: both G-01 and G-03 are closed via Plans 14-05 and 14-06; the round-2 leviathan
       re-UAT (14-HUMAN-UAT.md round 2) flipped scenarios 1 and 3b from fail to pass, and re-collected
       scenario 4d-restore on a clean state (W-5 closure), while preserving the 8 other previously-passing
       scenarios. SC5 + SC6 are now VERIFIED. The milestone acceptance gate is passed.

    10. **Body update -- `### Recommended Next Path` section** (currently lines 112-118): replace Option A
        / Option B with a single closure paragraph: Phase 14 is now complete with 6/6 must-haves verified;
        the recommended next step is to plan Phase 15 (documentation cascade) via `/gsd:plan-phase 15`.

    11. **Trailing audit lines** (currently lines 122-123): update the Verifier signature to add a second
        line: `_Re-verified: <ISO 8601 UTC>_` and `_Re-verifier: Claude (gsd-verifier; post-gap-closure
        re-UAT round 2)_`.

    Constraints:
    - English-only.
    - Preserve all unchanged structure and round-1 evidence (audit trail).
    - The 4 rows in `### Observable Truths` for SC1/SC2/SC3/SC4 stay UNCHANGED (still `✓ VERIFIED` with
      their round-1 evidence -- those fixes did not touch their surface area).
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
        test -s "$F"

        # Frontmatter: status flip to passed, score 6/6, re_verified added, gaps emptied
        grep -q "^status: passed" "$F"
        grep -q "^score: 6/6 must-haves verified" "$F"
        grep -q "^re_verified:" "$F"
        # gaps key either omitted or set to []
        python3 -c "
import yaml
with open(\"$F\") as fh:
    raw = fh.read()
assert raw.startswith(\"---\\n\"), \"frontmatter missing leading ---\"
end = raw.index(\"\\n---\\n\", 4)
fm = yaml.safe_load(raw[4:end])
assert fm.get(\"status\") == \"passed\", f\"status not flipped: {fm.get(\\\"status\\\")!r}\"
assert \"6/6\" in str(fm.get(\"score\", \"\")), f\"score not 6/6: {fm.get(\\\"score\\\")!r}\"
assert fm.get(\"re_verified\") is not None, \"re_verified missing\"
gaps = fm.get(\"gaps\", [])
assert gaps == [] or gaps is None, f\"gaps must be empty, got {gaps!r}\"
"
        # Body: SC5 + SC6 VERIFIED, RESTORE-V13-05 + OPS-V13-02 + UAT-V13-01 SATISFIED
        if grep -q "✗ FAILED" "$F"; then echo "FAIL: SC6 ✗ FAILED still present"; exit 1; fi
        if grep -q "✗ BLOCKED" "$F"; then echo "FAIL: UAT-V13-01 ✗ BLOCKED still present"; exit 1; fi
        partial_count=$(grep -c "⚠️ PARTIAL" "$F" || true)
        if [ "$partial_count" -gt 1 ]; then echo "FAIL: too many ⚠️ PARTIAL cells remaining (got $partial_count)"; exit 1; fi

        # Closure plan references
        grep -q "14-05" "$F"
        grep -q "14-06" "$F"
        # G-01 + G-03 closure narrative
        grep -q "G-01" "$F"
        grep -q "G-03" "$F"
        # Recommended next path is Phase 15
        grep -q "Phase 15" "$F"

        echo "PASS: 14-VERIFICATION.md flipped to status: passed with 6/6 must-haves"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - `.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md` frontmatter: `status: passed`, `score: 6/6 must-haves verified`, `re_verified:` field present with ISO 8601 UTC value (Z suffix), `gaps:` empty (either `gaps: []` or omitted entirely).
    - Body: NO `✗ FAILED` or `✗ BLOCKED` strings remain (round-1 SC6 row and UAT-V13-01 row both flipped).
    - Body: at most 1 `⚠️ PARTIAL` table-cell reference remains (it was 3+ in round 1; the SC5 row, RESTORE-V13-05 row, and OPS-V13-02 row all flip to VERIFIED/SATISFIED).
    - Body: Plan IDs `14-05` and `14-06` are cited (closure plan references).
    - Body: G-01 and G-03 are referenced in the closure narrative.
    - Body: Recommended Next Path now points at `Phase 15` (the doc cascade phase).
    - Body: `**Verified:**` round-1 timestamp preserved (audit trail) + new `**Re-verified:**` line.
    - Trailing audit signature includes the re-verifier line.
    - Unchanged rows (SC1/SC2/SC3/SC4 in Observable Truths) retain their round-1 `✓ VERIFIED` status and evidence.
  </acceptance_criteria>
  <done>
    `14-VERIFICATION.md` now declares Phase 14 milestone-complete: 6/6 must-haves verified, both gaps closed with closure-plan citations, recommended next path points at Phase 15. The audit trail (round-1 timestamp + round-2 timestamp + re-verifier signature) preserves the closure history. Ready for the git commit in Task 3.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Single git commit covering both doc updates (14-HUMAN-UAT.md + 14-VERIFICATION.md) citing G-01 + G-03 closure</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md, .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md</files>
  <read_first>
    - git log --oneline -5 (recent commit style: e.g., `b93ef4b docs(14): VERIFICATION -- gaps_found, 5/6 must-haves verified` and `1801ae1 test(14-04): live UAT round-trip on leviathan -- 9/11 pass, 2 gaps opened (G-01, G-03)`)
  </read_first>
  <action>
    Create a single git commit that captures the round-2 closure. Suggested commit message (use this verbatim or improve as the executor sees fit; the type should be `docs(14)` matching the prior phase-14 commit convention):

      docs(14): VERIFICATION + HUMAN-UAT -- gaps closed (G-01, G-03), 6/6 must-haves verified

      Round 2 re-UAT on leviathan post-Plan-14-05 + Plan-14-06 fix:
      - Scenario 1 (7-step round-trip): pass -- restore_docker.yml completes failed=0 with NO manual deploy_docker.yml --tags loki,tempo,mimir,garage workaround. Step 7 re-asserts same trace_id + run_id across all 4 OTLP signals. G-01 closed.
      - Scenario 3a (default bail-out): pass -- meta: clear_host_errors when-skipped under default mode; default-mode behavior preserved (no regression from G-03 block/rescue change).
      - Scenario 3b (opt-in continue-on-failure): pass -- meta: clear_host_errors fired on Prometheus rescue; 3 of 4 tarballs (garage + grafana + alertmanager) produced at shared timestamp; G-03 closed.
      - Scenario 4d-restore (W-5 closure): pass -- re-collected on clean state; verbose-log grep confirms 3 writer-rerender include_role invocations + meta: flush_handlers fired under --tags restore cross-cutting.
      - Other 7 scenarios re-confirmed pass.
      - VERIFICATION status flipped from gaps_found -> passed (6/6 must-haves).

    Stage exactly these 2 files:
      .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
      .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md

    Do NOT stage anything else in this commit. The playbook fixes were committed by Plans 14-05 / 14-06
    -- this commit is documentation-only (the audit-doc + verification-doc updates that record the round-2
    closure).

    Use a HEREDOC to pass the commit message via `git commit -m "$(cat <<'EOF' ... EOF)"` to preserve
    formatting per the GSD commit safety protocol. Include the GSD-standard Co-Authored-By trailer:

      Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

    Run `git status` after the commit to verify clean state on the 2 files (they should no longer appear
    as modified).
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        LAST=$(git log -1 --name-only --pretty=format:"")
        echo "$LAST" | grep -q "14-HUMAN-UAT.md"
        echo "$LAST" | grep -q "14-VERIFICATION.md"
        LAST_MSG=$(git log -1 --pretty=%B)
        echo "$LAST_MSG" | grep -qi "G-01"
        echo "$LAST_MSG" | grep -qi "G-03"
        echo "$LAST_MSG" | grep -qi "passed\\|closure\\|closed"
        echo "$LAST_MSG" | grep -q "Co-Authored-By: Claude"
        if git status --porcelain | grep -E "14-(HUMAN-UAT|VERIFICATION)\\.md"; then
          echo "FAIL: 14-HUMAN-UAT.md or 14-VERIFICATION.md still uncommitted"; exit 1
        fi
        echo "PASS: round-2 closure commit landed"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - Single commit landed with both `14-HUMAN-UAT.md` and `14-VERIFICATION.md` in its file list.
    - Commit message references G-01 closure, G-03 closure, and the round-2 re-UAT (the "passed" / "closure" / "closed" check accepts any of those keywords -- the executor's commit message wording can vary, but the closure concept must be cited).
    - Co-Authored-By trailer follows the GSD convention.
    - `git status` shows clean for the 2 updated files post-commit.
  </acceptance_criteria>
  <done>
    The round-2 closure is committed. Phase 14 milestone gate is closed -- v1.3.0 backup/restore round-trip is empirically proven on leviathan WITHOUT manual operator workaround. Next step: `/gsd:plan-phase 15` for the doc cascade.
  </done>
</task>

</tasks>

<verification>
- Task 1 is the live re-UAT checkpoint -- human-verified (Rock-driven or Claude-driven via passwordless SSH). The resume-signal discriminator (mode a / mode b) drives Claude's downstream action; ambiguous responses trigger a re-prompt.
- Task 2 verification is fully automated: YAML frontmatter parse + structural grep gates verify the status flip + closure-plan references.
- Task 3 verification is fully automated: git log inspection verifies the commit landed with both files and the right closure references.
- After all 3 tasks complete, Phase 14 milestone gate is passed (6/6 must-haves).
</verification>

<success_criteria>
- UAT-V13-01: SATISFIED. Round-2 scenario 1 PLAY RECAP `failed=0` for the restore step; all 4 OTLP signals (Loki + Prometheus + Mimir + Tempo) re-asserted via captured trace_id + run_id; NO manual workaround between steps 6 and 7. Round-2 scenario 4d-restore additionally confirms `--tags restore` cross-cutting writer-rerender fires cleanly (W-5 closure).
- RESTORE-V13-05: SATISFIED. Writers restart against restored Garage with healthy state, no `Forbidden: No such key` errors.
- BACKUP-V13-05: SATISFIED. Both default-mode bail-out (scenario 3a) and opt-in continue-on-failure (scenario 3b) deliver their contracts.
- OPS-V13-02: SATISFIED. Banner alt text is no longer a lie -- opt-in mode actually attempts all 4 roles past failures.
- G-01: closed. G-03: closed. `gaps:` in `14-VERIFICATION.md` frontmatter is empty.
- `14-VERIFICATION.md` status: passed. Score 6/6. SC5 + SC6 both VERIFIED.
- Single round-2 closure commit on git. Ready for Phase 15 planning.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator workstation -> leviathan via SSH | Passwordless SSH; leviathan is the live UAT host. The fault-injection in scenario 3 modifies its filesystem (`mv` + `touch`). Cleanup is mandatory and per-sub-scenario. |
| Scenario 3 fault-injection state -> subsequent scenarios | If cleanup is forgotten, scenario 4 may inherit broken state. Same mitigation as round 1: per-sub-scenario cleanup. |
| Round-2 doc edits -> round-1 audit trail | Round-1 evidence is factual and must be preserved (timestamp, scenarios that passed round 1). Round-2 amends; it does not overwrite the round-1 verification timestamp. |
| 4d-restore clean-state requirement (W-5) -> piggybacking risk | If 4d-restore is run immediately after scenario 1, the writer configs are already "fresh" and the writer-rerender path may report changed=false. Mitigation: explicit setup steps in how-to-verify (re-purge, re-deploy, then 4d-restore under --tags restore). |
| Resume-signal mode discriminator (W-3) | If Rock types a bare "approved" without the mode-(a)/(b) discriminator, Claude cannot deterministically choose between "read attached evidence" and "drive scenarios via SSH". Mitigation: resume-signal explicitly requires one of the two discriminator strings; any other response triggers Claude to re-prompt rather than proceed. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-RE-01 | Denial of Service | Forgotten cleanup of scenario 3 file-as-dir fault leaves /opt/telemetron/backups/prometheus broken for subsequent scenarios | mitigate | Task 1 how-to-verify explicitly calls out cleanup commands AFTER EACH scenario 3 sub-test (3a + 3b). |
| T-14-RE-02 | Tampering | Round-2 doc edit accidentally deletes round-1 audit trail (verified timestamp, round-1 evidence) | mitigate | Task 2 action explicitly preserves `**Verified:**` round-1 timestamp; round-1 evidence in unchanged rows stays. Acceptance_criteria asserts SC1/SC2/SC3/SC4 rows retain their round-1 ✓ VERIFIED status. |
| T-14-RE-03 | Repudiation | Closure commit lands but round-2 evidence is not actually captured -- VERIFICATION.md says "passed" but HUMAN-UAT.md detail sections still say `TBD` | mitigate | Task 1 acceptance_criteria requires re-written detail sections for scenarios 1 + 3b + 4d-restore; Task 3 acceptance_criteria requires the commit references G-01 + G-03. |
| T-14-RE-04 | Denial of Service | Re-UAT task hangs because leviathan is unreachable mid-run | mitigate | Same W-4 pre-flight from 14-04 Task 2 -- ssh BatchMode + ConnectTimeout 5 at the start, abort + surface on failure. |
| T-14-RE-05 | Tampering | A new regression (e.g., G-01 fix breaks scenario 4c writer-untouched semantics) is overlooked | mitigate | Task 1 requires re-running ALL 11 sub-scenarios, not just the ones that previously failed. Pre-existing-pass scenarios are explicitly re-confirmed with a round-2 marker. If any regression surfaces, the scenario stays `result: fail` and a new Gap entry is opened. |
| T-14-RE-06 | Tampering (W-5) | Scenario 4d-restore is mis-classified as "no-change-expected" and accepted with stale round-1 evidence; the clean exercise of `--tags restore` writer-rerender never actually runs | mitigate | W-5 explicit promotion of 4d-restore to "must-be-re-collected" bucket; verbose-log grep for the 3 include_role invocation names + `meta: flush_handlers` is the empirical proof; failure to find those lines opens new gap G-04 (tag-leakage on writer-rerender under --tags restore). |
| T-14-RE-07 | Repudiation (W-3) | Resume-signal mode is ambiguous; Claude proceeds with wrong assumption (e.g., re-runs scenarios when Rock already did, or skips Tasks 2+3 when Rock expected Claude to update docs) | mitigate | Resume-signal text explicitly demands one of two literal discriminator strings; any other response (including bare "approved") triggers a re-prompt rather than a guess. |
</threat_model>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md` when done. The SUMMARY captures: which scenarios were re-run and their round-2 results, the verbatim PLAY RECAP for scenarios 1 + 3a + 3b + 4d-restore (the 4 G-01/G-03/W-5-relevant tests), the closure-commit SHA, and a one-line declaration of Phase 14 milestone-gate closure. Reference the closure-plan IDs (14-05, 14-06) explicitly so the SUMMARY is self-contained. Explicitly note the W-3 resume-signal mode used (a or b) and the W-5 evidence (verbose-log grep lines for the 4d-restore clean exercise).
</output>
</content>
</invoke>