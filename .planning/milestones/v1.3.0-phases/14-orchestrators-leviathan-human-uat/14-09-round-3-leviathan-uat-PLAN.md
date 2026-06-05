---
phase: 14-orchestrators-leviathan-human-uat
plan: "09"
type: execute
wave: 1
depends_on:
  - 14-08
files_modified:
  - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
  - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
autonomous: true
gap_closure: true
requirements:
  - BACKUP-V13-05
  - OPS-V13-02
  - RESTORE-V13-05
  - UAT-V13-01
tags: [gap-closure, round-3, leviathan, uat, G-03-addendum-behavioral, G-04-behavioral, milestone-acceptance-gate]

must_haves:
  truths:
    - "Round-3 live UAT executed on leviathan post-Plan-14-08 structural fix. Two scenarios re-run end-to-end via passwordless SSH (Rock pre-authorized Claude-driven mode b -- no checkpoint task)."
    - "Scenario 3a (default mode + Prometheus file-as-dir fault): PLAY RECAP shows `failed=1` (G-03-addendum behavioral closure -- the new `ansible.builtin.fail` in the rescue under `when: not (knob)` re-raises the failure, `any_errors_fatal: true` aborts the play). Banner fires default-mode alt text (`first role failure will abort the playbook`). Only the garage tarball appears at the run timestamp; grafana + alertmanager tarballs are NOT created (their include_role never ran)."
    - "Scenario 4d-restore (W-5 closure on clean post-purge state under `--tags restore`): PLAY RECAP shows `failed=0`. The verbose-log shows the 3 writer role-body template-render tasks firing under the `--tags restore` filter -- empirically proving the new `apply: tags: [garage, restore]` mechanism on the 3 writer-rerender include_role invocations propagates the tag list into the loki/tempo/mimir role bodies (G-04 behavioral closure). Writers come up healthy against the restored Garage S3 key; no `Forbidden: No such key:` errors in container logs."
    - "The 9 round-2-passing scenarios (1, 2a, 2b, 2c, 3b, 4a, 4b, 4c, 4d-backup) are NOT re-executed in full. They are re-confirmed via a one-line round-3 spot-check marker appended to each `detail:` field stating no regression (the 14-08 structural fixes do not touch their surface area)."
    - "Behavioral-correctness gate: this plan does NOT silently flip `14-VERIFICATION.md` to `passed` when empirical evidence says otherwise. If either scenario 3a or 4d-restore still fails post-14-08, the failed scenario stays `result: fail`, a Plan 14-10 is opened, and VERIFICATION stays `gaps_found`."
    - "14-HUMAN-UAT.md frontmatter flips `status: partial` to `status: complete`. `## Current Test` bracket replaced with the round-3 closure note. `## Summary` updates `passed: 11`, `pending: 0`, `issues: 0`. Both new gap entries (G-03-addendum, G-04) added to `## Gaps` with `status: closed`, `closed-in: 14-08-gap-closure-bail-out-and-restore-tags-PLAN.md`, and `closure-evidence:` field quoting the round-3 PLAY RECAP excerpts."
    - "14-VERIFICATION.md frontmatter flips `status: gaps_found` to `status: passed`; `score: 5.5/6 must-haves verified` to `score: 6/6 must-haves verified`; `re_verified:` ISO timestamp updated to round-3 time; `gaps:` block replaced with empty `gaps: []`."
    - "14-VERIFICATION.md body: SC5 row evidence cell amended with round-3 scenario 3a evidence (default-mode bail-out PLAY RECAP `failed=1`) combined with the round-2 scenario 3b evidence (opt-in continue-on-failure 3-of-4 tarballs preserved). SC6 row evidence cell amended with round-3 scenario 4d-restore evidence (clean exercise of `--tags restore` cross-cutting writer-rerender; verbose-log grep proves role-body subtasks fired). RESTORE-V13-05 / OPS-V13-02 / UAT-V13-01 rows cite round-3 closure evidence."
    - "14-VERIFICATION.md body `**Re-verified:**` line updated to round-3 ISO timestamp; `**Re-verification:**` line updated to `Yes -- post-G-03-addendum + G-04 closure (Plan 14-08); round-3 leviathan UAT proved scenarios 3a + 4d-restore PASS`. `## Goal Achievement` appended with closure paragraph confirming all 6 must-haves verified, citing Plans 14-05 / 14-06 / 14-08 + round-3 UAT. `## Gaps Summary` replaced with closure narrative (all 4 gaps closed: G-01, G-03 opt-in, G-03-addendum, G-04). `## Recommended Next Path` points at Phase 15."
    - "Both updated docs are committed in a single git commit citing G-03-addendum closure + G-04 closure + round-3 leviathan UAT + 6/6 must-haves verified + Phase 15 next. Commit follows the `docs(14): ...` convention used by prior phase-14 commits (cddb3cd, b93ef4b)."
  artifacts:
    - path: ".planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md"
      provides: "Round-3 closure audit doc -- all 11 sub-scenarios pass post-fix; all 4 gaps (G-01, G-03 opt-in, G-03-addendum, G-04) marked closed."
      min_lines: 60
      contains: "Round 3"
    - path: ".planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md"
      provides: "Final verification report -- status: passed; 6/6 must-haves; all rows VERIFIED/SATISFIED; gaps block empty; recommended next path = Phase 15."
      min_lines: 80
      contains: "status: passed"
  key_links:
    - from: "Scenario 3a round-3 (default mode + Prometheus file-as-dir fault on leviathan, post-Plan-14-08 fix)"
      to: "PLAY RECAP `failed=1`; only garage tarball at run-ts; grafana + alertmanager NOT attempted"
      via: "The new `ansible.builtin.fail` (Plan 14-08 Task 1) as FIRST rescue task with `when: not (backup_continue_on_failure | default(false) | bool)` re-raises the Prometheus failure; play-level failure counter increments; `any_errors_fatal: true` aborts the play before subsequent role include_role calls"
      pattern: "failed=1"
    - from: "Scenario 4d-restore round-3 (`--tags restore` on clean post-purge state with new Garage key, post-Plan-14-08 fix)"
      to: "PLAY RECAP `failed=0`; verbose-log shows `TASK [loki : Render Loki config]`, `TASK [tempo : Render Tempo config]`, `TASK [mimir : Render Mimir config]` firing; writers healthy against restored S3 key"
      via: "The new `apply: tags: [garage, restore]` mapping (Plan 14-08 Task 2) inside each writer-rerender include_role propagates the tag list into the loaded role-body tasks at runtime, so the `Render <role> config` tasks are not skipped under the `--tags restore` filter"
      pattern: "loki : Render Loki config|tempo : Render Tempo config|mimir : Render Mimir config"
    - from: "14-VERIFICATION.md frontmatter `status: gaps_found` and `gaps:` block with G-03-addendum + G-04 entries"
      to: "Updated to `status: passed` and `gaps: []` -- the milestone acceptance gate source of truth"
      via: "Manual edit in Task 2 conditional on Task 1 empirical proof (both scenarios PASS); if Task 1 leaves a scenario `result: fail`, Task 2 does NOT flip status to passed -- VERIFICATION stays `gaps_found` and a Plan 14-10 is opened instead"
      pattern: "status: passed"
---

<objective>
Plan 14-08 landed the two structural fixes that close G-03-addendum (explicit `ansible.builtin.fail` in each backup rescue under default mode) and G-04 (`apply: tags: [garage, restore]` on writer-rerender include_role calls in restore_docker.yml). All Plan-14-08 structural assertions passed (ansible-playbook --syntax-check, YAML round-trip Python checks, --list-tasks invariants). This plan is the empirical proof on leviathan that the fixes deliver behaviorally.

Scope: re-run ONLY scenarios 3a + 4d-restore (the two that were `result: fail` after Plan 14-07 Round 2). The other 9 sub-scenarios remain `pass` from round-2 and are spot-checked with a one-line round-3 marker (no full re-execution; the 14-08 structural fixes do not touch their surface area). Then flip `14-HUMAN-UAT.md` and `14-VERIFICATION.md` to closure state, commit, return.

Purpose: This is the LAST plan needed to close the Phase 14 milestone acceptance gate. After this plan completes with VERIFICATION.md flipped to passed (6/6), the v1.3.0 backup/restore round-trip is empirically proven end-to-end on leviathan under BOTH the untagged full-play form AND the `--tags restore` cross-cutting form, with bail-out semantics correct under both default and opt-in modes. Phase 15 (documentation cascade) is unblocked.

This plan is `autonomous: true`. Rock has pre-authorized Claude-driven mode b (passwordless SSH against leviathan; vault password not needed because `inventory/leviathan/host_vars/leviathan/secrets.yml` is plaintext per the 14-07 Summary discovery). There is NO checkpoint task. Behavioral correctness on the live host is the gate; if the empirical evidence contradicts the 14-08 structural fix, this plan documents the failure faithfully rather than silently passing.

Output: amended `14-HUMAN-UAT.md` (round-3 results for 3a + 4d-restore flipped to `pass` with empirical PLAY RECAP / verbose-log evidence; other 9 scenarios get round-3 spot-check markers; all 4 gaps marked closed); amended `14-VERIFICATION.md` (status: passed; 6/6 must-haves; SC5 + SC6 fully VERIFIED; gaps block empty; recommended next path = Phase 15); single git commit referencing both Plan-14-08 closures + round-3 UAT.
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
@.planning/phases/14-orchestrators-leviathan-human-uat/14-07-re-uat-leviathan-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-08-gap-closure-bail-out-and-restore-tags-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-08-SUMMARY.md

@playbooks/backup_docker.yml
@playbooks/restore_docker.yml
@playbooks/deploy_docker.yml
@playbooks/undeploy_docker.yml

<interfaces>
<!-- leviathan inventory (gitignored; lives on Rock's workstation per MEMORY.md project_leviathan_uat_host.md) -->

inventory/leviathan/    : passwordless SSH; Docker 29 on the target; single member host `leviathan` in `telemetron` group; host_vars/leviathan/secrets.yml is plaintext (no --ask-vault-pass needed) per 14-07-SUMMARY discovery.

<!-- Scenario 3a fault-injection (file-as-dir; round-1 + round-2 proven method) -->

  Setup:
    ssh leviathan "sudo mv /opt/telemetron/backups/prometheus /opt/telemetron/backups/prometheus.SAVED"
    ssh leviathan "sudo touch /opt/telemetron/backups/prometheus"
  Cleanup (MANDATORY -- runs even if scenario fails):
    ssh leviathan "sudo rm /opt/telemetron/backups/prometheus"
    ssh leviathan "sudo mv /opt/telemetron/backups/prometheus.SAVED /opt/telemetron/backups/prometheus"

NOTE: chmod 000 does NOT work as fault-injection because the backup task runs `become: true` (root) and root
bypasses directory perms (CAP_DAC_OVERRIDE). The file-as-dir fault is the proven method.

<!-- Scenario 4d-restore clean-state setup (W-5; documented verbatim in 14-07-PLAN scenario 4d-restore) -->

The round-2 4d-restore exercise was on a clean post-purge state. For round-3:
  1. (Optional) Take a fresh backup as setup material if no recent tarball exists at /opt/telemetron/backups/.
     ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml
     Capture the shared timestamp (e.g., 20260606T120000Z) from the resulting tarballs.
  2. Full purge: ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --extra-vars "telemetron_purge_data=true"
     Confirms volumes are wiped; the next deploy will bootstrap a NEW Garage key.
  3. Fresh redeploy: ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml
     Stack returns; Garage bootstrap generates NEW S3 key; writer configs templated against this NEW key.
  4. Targeted restore: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --tags restore --extra-vars "backup_restore_confirm=true backup_restore_from=<shared-ts-from-step-1>" -v
     The `-v` is mandatory so the verbose log shows individual role-body tasks under the include_role
     invocations.

CRITICAL difference from round-2: in round-3 the writer-rerender include_role calls in restore_docker.yml
now carry `apply: tags: [garage, restore]` (Plan 14-08 Task 2). The empirical proof is:
- grep the verbose log for `TASK \[loki : Render Loki config\]`, `TASK \[tempo : Render Tempo config\]`,
  `TASK \[mimir : Render Mimir config\]` -- these MUST appear (round-2 had ZERO matches).
- grep the verbose log for `RUNNING HANDLER.*loki : Docker restart loki|tempo : Docker restart tempo|mimir : Docker restart mimir`
  -- these MUST appear (round-2 had ZERO matches).
- Tempo container log post-restart MUST NOT contain `Forbidden: No such key: GK...` -- the writer is now
  using the correct restored key.

<!-- Round-2 PLAY RECAP shapes for reference (what was wrong, what we expect to flip in round-3) -->

Scenario 3a round-2 (FAIL -- G-03-addendum):
  leviathan : ok=64   changed=9   unreachable=0  failed=0  skipped=0  rescued=1  ignored=0
  3 of 4 tarballs (garage + grafana + alertmanager); prometheus absent.

Scenario 3a round-3 EXPECTED (PASS -- G-03-addendum closure):
  leviathan : ok=??   changed=?   unreachable=0  failed=1  skipped=0  rescued=?  ignored=0
  ONLY garage tarball at run-ts; grafana + alertmanager NOT attempted.
  (The rescued counter may or may not increment; what matters is failed=1 and that grafana/alertmanager
  include_role calls did not execute.)

Scenario 4d-restore round-2 (FAIL -- G-04):
  leviathan : ok=30   changed=10  unreachable=0  failed=1  skipped=4  rescued=0  ignored=0
  Writer-rerender included but role body subtasks all skipped; Tempo crash-loop on `Forbidden: No such key`.

Scenario 4d-restore round-3 EXPECTED (PASS -- G-04 closure):
  leviathan : ok=??   changed=?   unreachable=0  failed=0  skipped=?  rescued=0  ignored=0
  Verbose log MUST contain `TASK [loki : Render Loki config]`, `TASK [tempo : Render Tempo config]`,
  `TASK [mimir : Render Mimir config]` lines; writers healthy at end; no `Forbidden: No such key:` in
  any container log.

<!-- Pre-existing UAT-round-2 evidence to PRESERVE for the 9 passing scenarios -->

Scenarios 1, 2a, 2b, 2c, 3b, 4a, 4b, 4c, 4d-backup all show `result: pass` in 14-HUMAN-UAT.md after
round-2. Their `detail:` fields contain BOTH round-1 and round-2 evidence (the latter as a "Round 2
re-confirmation" amend). The 14-08 structural fixes (explicit fail in rescue under default; apply: tags
on writer-rerender) do NOT touch their surface area:
- Scenarios 2a/2b/2c (confirm-gate): no rescue code path, no writer-rerender
- Scenario 3b (opt-in continue-on-failure): the rescue still runs its meta:clear_host_errors; the new
  fail task is when-skipped under opt-in
- Scenarios 4a/4b/4c (--tags isolation): different tag scopes from --tags restore
- Scenario 1 (untagged full play): writer-rerender include_role still runs without tag filtering
- Scenario 4d-backup (--tags backup): touches backup rescue blocks but the new fail task is in scope
  of --tags backup ONLY through the enclosing block tag list [<role>, backup] -- spot-check confirms
  no regression

Pragmatic guidance: append one-line round-3 spot-check markers; no full re-execution.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Round-3 live UAT on leviathan -- re-run scenarios 3a + 4d-restore + spot-check the 9 passing scenarios; update 14-HUMAN-UAT.md</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md</files>
  <read_first>
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md (round-2 state; round-3 amends and flips scenario 3a + 4d-restore)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-08-SUMMARY.md (what Plan 14-08 actually shipped -- the structural edits to backup_docker.yml + restore_docker.yml)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-08-gap-closure-bail-out-and-restore-tags-PLAN.md (the plan that produced the 14-08 edits; documents the expected behavioral contract)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-07-re-uat-leviathan-PLAN.md (round-2 plan -- the scenario 3a + 4d-restore sections document the fault-injection method and the W-5 clean-state setup; this plan reuses those methods verbatim)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md (round-2 evidence + the precise PLAY RECAP shapes that demonstrated the failures we expect to flip)
    - playbooks/backup_docker.yml (post-14-08 state; contains the new `ansible.builtin.fail` re-raise tasks in each rescue)
    - playbooks/restore_docker.yml (post-14-08 state; contains the new `apply: tags: [garage, restore]` on writer-rerender include_role calls)
    - MEMORY.md project_leviathan_uat_host.md (leviathan SSH config; vault password discovery from 14-07)
  </read_first>
  <action>
    PRE-FLIGHT (mandatory first; mirrors Plan 14-04/14-07 W-4 mitigation): Run
    `ssh -o BatchMode=yes -o ConnectTimeout=5 leviathan true`. If non-zero exit, ABORT this task
    immediately and return to the orchestrator with: "leviathan unreachable -- fix host connectivity
    before running round-3 UAT". Do NOT leave the task in `in_progress` indefinitely. Per Memory
    `project_leviathan_uat_host.md` and 14-07 mode-b precedent, Claude drives the SSH commands directly
    (no checkpoint -- Rock has pre-authorized round-3 Claude-driven mode b for this plan).

    Vault password: per 14-07-SUMMARY discovery, `inventory/leviathan/host_vars/leviathan/secrets.yml`
    is plaintext (no --ask-vault-pass needed). All `ansible-playbook` invocations in this task run WITHOUT
    `--ask-vault-pass`.

    --- SCENARIO 3a RE-RUN (G-03-addendum behavioral closure proof) ---

    Setup (file-as-dir fault):
      ssh leviathan "sudo mv /opt/telemetron/backups/prometheus /opt/telemetron/backups/prometheus.SAVED && sudo touch /opt/telemetron/backups/prometheus"

    Run (no --extra-vars; default mode):
      ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml 2>&1 | tee /tmp/14-09-scenario-3a.log

    Cleanup (MANDATORY -- runs even if scenario fails; do this BEFORE moving to 4d-restore):
      ssh leviathan "sudo rm /opt/telemetron/backups/prometheus && sudo mv /opt/telemetron/backups/prometheus.SAVED /opt/telemetron/backups/prometheus"

    EXPECTED behavior (Plan 14-08 G-03-addendum closure):
      - Banner fires default-mode alt text: `(first role failure will abort the playbook)`.
      - Garage backup succeeds (garage-<ts>.tar.zst at /opt/telemetron/backups/garage/).
      - Prometheus backup fails at `Ensure Prometheus backup destination directory exists`:
        `/opt/telemetron/backups/prometheus already exists as a file`.
      - The rescue block enters. The NEW first rescue task `<Role> backup failed -- re-raise under
        default mode (G-03-addendum)` FIRES (its `when: not (backup_continue_on_failure | default(false)
        | bool)` evaluates true). The play-level failure counter increments.
      - The second rescue task `clear_host_errors (G-03; opt-in only)` is SKIPPED (its `when: knob`
        evaluates false).
      - `any_errors_fatal: true` (default-mode evaluation) aborts the play.
      - Grafana + Alertmanager include_role calls do NOT run.
      - PLAY RECAP shows `failed=1`. The `rescued=` counter may show 0 or 1 depending on Ansible's
        accounting after the explicit fail; what matters is `failed=1` and that grafana/alertmanager
        did not execute.

    EMPIRICAL VERIFICATION (grep the on-disk log; do NOT hold the full log in context):
      grep -E "PLAY RECAP|failed=" /tmp/14-09-scenario-3a.log | tail -5
      grep -E "re-raise under default mode|G-03-addendum" /tmp/14-09-scenario-3a.log
      grep -E "Invoke grafana backup|Invoke alertmanager backup" /tmp/14-09-scenario-3a.log
        (Expected: zero matches for the grafana/alertmanager include_role invocations.)
      ssh leviathan "ls -1 /opt/telemetron/backups/garage/ /opt/telemetron/backups/prometheus/ /opt/telemetron/backups/grafana/ /opt/telemetron/backups/alertmanager/ 2>/dev/null | tail -20"
        (Expected: garage shows new tarball at the run timestamp; prometheus shows nothing new
        (still in fault-state at run time, but cleanup restored it after the test); grafana +
        alertmanager show no new tarball at the run timestamp.)

    --- SCENARIO 4d-restore RE-RUN (G-04 behavioral closure proof; W-5 clean state) ---

    Setup (clean-state per W-5 -- do NOT run scenario 1 first; the writer configs must be "fresh"
    against the post-purge/redeploy Garage key BEFORE the targeted --tags restore exercises the
    new apply: tag-propagation):

      Step 1: Take a fresh backup as setup material (this provides a known shared timestamp the
      restore will target):
        ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml 2>&1 | tee /tmp/14-09-scenario-4d-restore-setup-backup.log
        # Capture the shared timestamp from the resulting tarballs:
        SHARED_TS=$(ssh leviathan "ls -1 /opt/telemetron/backups/garage/ | grep -E 'garage-[0-9]+T[0-9]+Z\.tar\.zst' | tail -1 | sed -E 's/garage-([0-9TZ]+)\\.tar\\.zst/\\1/'")
        # Sanity-check it looks like a timestamp (e.g., 20260606T120000Z):
        echo "Captured shared_ts: $SHARED_TS"

      Step 2: Full purge (wipes volumes + s3-credentials; next deploy will bootstrap a NEW Garage key):
        ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --extra-vars "telemetron_purge_data=true" 2>&1 | tee /tmp/14-09-scenario-4d-restore-setup-purge.log
        # Expected: PLAY RECAP failed=0. ssh leviathan "docker volume ls | grep telemetron_" returns 0 telemetron volumes.

      Step 3: Fresh redeploy (NEW Garage key bootstrapped; writers templated against this new key):
        ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml 2>&1 | tee /tmp/14-09-scenario-4d-restore-setup-deploy.log
        # Expected: PLAY RECAP failed=0. 11 telemetron-* containers healthy.

    Run (targeted --tags restore with -v for verbose log; this is the G-04 behavioral test):
      ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --tags restore --extra-vars "backup_restore_confirm=true backup_restore_from=${SHARED_TS}" -v 2>&1 | tee /tmp/14-09-scenario-4d-restore.log

    EXPECTED behavior (Plan 14-08 G-04 closure via `apply: tags: [garage, restore]`):
      - Confirm-gate passes (flag set).
      - WARN banner fires (tagged [always]).
      - Writer-stop loop fires (loki/tempo/mimir stop; State.Running == false poll passes).
      - Garage restore include_role fires (restores volumes + s3-credentials with the ORIGINAL key
        GK... from the SHARED_TS backup).
      - Garage restore.yml tail set_fact tasks fire (load restored s3-credentials, populate
        garage_s3_access_key_id and garage_s3_secret_key facts).
      - The 3 writer-rerender include_role tasks fire AND their role-body subtasks ALSO fire (this
        is the G-04 closure: `apply: tags: [garage, restore]` propagates the tag list into the
        role body):
          TASK [Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed); G-04 tag-propagation]
            included: loki for leviathan
          TASK [loki : Render Loki config]
            changed: [leviathan]                      <-- THIS IS THE G-04 CLOSURE PROOF
          TASK [Re-render Tempo config ...]
            included: tempo for leviathan
          TASK [tempo : Render Tempo config]
            changed: [leviathan]
          TASK [Re-render Mimir config ...]
            included: mimir for leviathan
          TASK [mimir : Render Mimir config]
            changed: [leviathan]
      - meta:flush_handlers fires; restart handlers run (RUNNING HANDLER lines for
        loki/tempo/mimir : Docker restart <role>).
      - Writer-restart docker_start loop fires (idempotent).
      - Writer healthy-poll passes (State.Health.Status == healthy for all 3 writers).
      - prometheus/grafana/alertmanager restores fire in order.
      - PLAY RECAP `failed=0`. All 11 containers healthy.

    EMPIRICAL VERIFICATION (grep the on-disk log; G-04 closure is binary -- either the role-body
    tasks fired or they did not):

      grep -E "PLAY RECAP|failed=" /tmp/14-09-scenario-4d-restore.log | tail -5
      grep -E "TASK \[loki : Render Loki config\]|TASK \[tempo : Render Tempo config\]|TASK \[mimir : Render Mimir config\]" /tmp/14-09-scenario-4d-restore.log
        (Expected: 3 matches -- one per writer. Round-2 had ZERO matches; round-3 MUST have 3.)
      grep -E "RUNNING HANDLER.*(loki|tempo|mimir).*Docker restart" /tmp/14-09-scenario-4d-restore.log
        (Expected: 3 matches.)
      ssh leviathan "docker logs --tail 50 telemetron-tempo 2>&1 | grep -i 'Forbidden: No such key' || echo NO_FORBIDDEN_ERROR"
        (Expected: NO_FORBIDDEN_ERROR -- the writer is now reading the correct restored key.)
      ssh leviathan "docker ps --filter 'name=telemetron-' --format '{{.Names}}\t{{.Status}}' | wc -l"
        (Expected: 11 -- all containers up.)

    --- 9 PASSING-FROM-ROUND-2 SCENARIOS (round-3 spot-check markers; NO full re-execution) ---

    The 9 scenarios that already pass (1, 2a, 2b, 2c, 3b, 4a, 4b, 4c, 4d-backup) are NOT re-executed
    in this plan. Per the round-2 evidence and the 14-08 Plan's surface-area analysis, the 14-08
    structural fixes do NOT touch:
      - The full untagged restore path (scenario 1: writer-rerender include_role runs without any
        tag filtering; the new apply: clause is a no-op when no --tags filter is active).
      - The confirm-gate code paths (2a, 2b, 2c: identical orchestrator-level and per-role gates).
      - The opt-in continue-on-failure path (3b: the new explicit-fail task is when-skipped under
        opt-in, so the existing clear_host_errors path runs unchanged).
      - The --tags isolation paths (4a, 4b, 4c: different tag scopes; the new apply: clause is
        scoped to --tags restore + the writer-rerender include_role calls, none of which match
        --tags garage / --tags loki / --tags grafana).
      - The --tags backup cross-cutting path (4d-backup: the new explicit-fail task IS inside a
        block tagged [<role>, backup], so it could in principle be selected by --tags backup;
        however the fail's `when:` guard evaluates true only on a failure, and 4d-backup runs
        against a clean state with no fault, so the fail task is never reached).

    Each of the 9 scenarios gets a one-line round-3 spot-check marker appended to its `detail:`
    field in 14-HUMAN-UAT.md:
      `Round 3 spot-check 2026-06-XX (post-G-03-addendum/G-04 fix): PASS, no regression -- 14-08 structural fixes do not touch this scenario's surface area.`

    (Replace 2026-06-XX with the actual round-3 date.)

    --- DOCUMENT UPDATE: 14-HUMAN-UAT.md ---

    Edit `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md`:

    1. Frontmatter:
       - `status: partial` -> `status: complete`
       - `updated:` set to the round-3 ISO 8601 UTC timestamp with Z suffix.

    2. `## Current Test`: replace the round-2 bracket with:
       `[Round 3 complete <round-3 date>. All 11 sub-scenarios pass on leviathan post-G-01/G-03/G-03-addendum/G-04 closure (Plans 14-05, 14-06, 14-08). Milestone acceptance gate verified.]`

    3. Scenario 3a: `result: fail` -> `result: pass`. REWRITE `detail:` with the round-3 evidence
       (round-2 detail is REPLACED, not preserved -- round-2 detail documented the regression;
       round-3 documents the closure). The new detail MUST quote:
       - Round-3 PLAY RECAP excerpt showing `failed=1`
       - The PLAY OUTPUT line confirming the new `<role> backup failed -- re-raise under default mode (G-03-addendum)` task fired (this is the structural proof from Plan 14-08)
       - The PLAY OUTPUT line confirming the second rescue task `clear_host_errors (G-03; opt-in only)` was SKIPPED
       - The ssh ls output proving only the garage tarball appears at the run timestamp (grafana + alertmanager NOT created)
       - One-sentence summary: "G-03-addendum CLOSED. The 14-08 explicit-fail in rescue under default mode restores bail-out semantics: PLAY RECAP `failed=1`, grafana + alertmanager not attempted."

    4. Scenario 4d-restore: `result: fail` -> `result: pass`. REWRITE `detail:` with the round-3 evidence
       (round-2 detail REPLACED). The new detail MUST quote:
       - Round-3 PLAY RECAP excerpt showing `failed=0`
       - The verbose-log grep lines proving the 3 role-body tasks `TASK [loki : Render Loki config]`,
         `TASK [tempo : Render Tempo config]`, `TASK [mimir : Render Mimir config]` fired (and were
         CHANGED) -- this is the G-04 closure proof
       - The verbose-log grep lines proving the 3 handlers (`RUNNING HANDLER loki : Docker restart loki`, tempo, mimir) fired
       - The container log check showing no `Forbidden: No such key:` errors in telemetron-tempo
         (the round-2 crash log signature)
       - The docker ps count = 11 (all containers healthy at end)
       - One-sentence summary: "G-04 CLOSED. The 14-08 `apply: tags: [garage, restore]` mapping on the 3 writer-rerender include_role calls propagates the tag list into the loki/tempo/mimir role bodies at runtime, so `Render <role> config` tasks are selectable under the `--tags restore` filter (round-2 had ZERO role-body matches; round-3 has 3 matches with CHANGED status)."

    5. The other 9 scenarios (1, 2a, 2b, 2c, 3b, 4a, 4b, 4c, 4d-backup): `result:` stays `pass`.
       `detail:` is AMENDED (not replaced) with a one-line round-3 spot-check marker:
       `Round 3 spot-check <round-3 date> (post-G-03-addendum/G-04 fix): PASS, no regression -- 14-08 structural fixes do not touch this scenario's surface area.`

    6. `## Summary`:
       - `passed: 11`
       - `pending: 0`
       - `issues: 0`
       (Other counters stay at 0.)

    7. `## Gaps`:
       - G-01 entry: `status: closed` (already closed in round 2; preserve closure-evidence).
       - G-03 entry: `status: closed` (already closed in round 2 for opt-in; preserve closure-evidence).
       - ADD a new entry for G-03-addendum with `status: closed`,
         `closed-in: 14-08-gap-closure-bail-out-and-restore-tags-PLAN.md`,
         and a `closure-evidence:` field citing the round-3 scenario-3a PLAY RECAP `failed=1` excerpt
         plus the PLAY OUTPUT line for the explicit-fail task firing.
       - ADD a new entry for G-04 with `status: closed`,
         `closed-in: 14-08-gap-closure-bail-out-and-restore-tags-PLAN.md`,
         and a `closure-evidence:` field citing the round-3 scenario-4d-restore PLAY RECAP `failed=0`
         plus the 3 verbose-log grep lines (TASK [loki : Render Loki config] etc.) plus the docker
         ps count = 11.

    ISSUE HANDLING (BEHAVIORAL CORRECTNESS GATE):
    - If `ssh leviathan true` returns non-zero exit at pre-flight: ABORT and surface to orchestrator
      ("leviathan unreachable -- fix connectivity").
    - If scenario 3a still shows `failed=0 rescued=1` (i.e., the 14-08 explicit-fail did NOT actually
      flip behavior): LEAVE scenario 3a `result: fail` in 14-HUMAN-UAT.md, do NOT mark its gap as
      closed, document the new failure mode in a new gap entry, and signal the orchestrator that
      Plan 14-10 is needed. Do NOT proceed to Task 2 doc flip in this failure path.
    - If scenario 4d-restore still shows `failed=1` with Tempo crash-loop (i.e., the 14-08 apply:
      tags fix did NOT actually flip behavior): same handling -- LEAVE 4d-restore `result: fail`,
      do NOT mark G-04 as closed, document the new failure mode, signal Plan 14-10 needed. Do NOT
      proceed to Task 2 doc flip.
    - If a previously-passing scenario regresses (extremely unlikely given the surface-area analysis
      above, but possible): re-execute that scenario in full, document the regression, leave it
      `result: fail`, do NOT proceed to Task 2.
    - If both scenarios PASS as expected: proceed to Task 2.

    The pipe-and-tee discipline (`2>&1 | tee /tmp/14-09-scenario-<NN>.log`) is mandatory so that
    Claude can grep evidence from on-disk logs rather than holding multiple full PLAY OUTPUTs in
    context.
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
        test -s "$F"

        # Frontmatter status flip
        grep -q "^status: complete" "$F"

        # 11 pass; 0 fail; 0 pending
        pass_count=$(grep -c "^result: pass" "$F" || true)
        fail_count=$(grep -c "^result: fail" "$F" || true)
        pending_count=$(grep -c "^result: pending" "$F" || true)
        if [ "$pass_count" -ne 11 ]; then echo "FAIL: expected 11 pass results, got $pass_count"; exit 1; fi
        if [ "$fail_count" -ne 0 ]; then echo "FAIL: expected 0 fail results, got $fail_count"; exit 1; fi
        if [ "$pending_count" -ne 0 ]; then echo "FAIL: expected 0 pending results, got $pending_count"; exit 1; fi

        # Summary block
        grep -q "^passed: 11" "$F"
        grep -q "^pending: 0" "$F"
        grep -q "^issues: 0" "$F"

        # Round 3 marker in Current Test bracket
        grep -q "Round 3" "$F"

        # G-03-addendum + G-04 gap entries both marked closed
        # (Look for the gap headers, then verify a closed status appears nearby.)
        grep -q "G-03-addendum" "$F"
        grep -q "G-04" "$F"
        # All gap status fields must be closed (G-01, G-03, G-03-addendum, G-04 = 4 closed)
        closed_count=$(grep -c "^status: closed" "$F" || true)
        if [ "$closed_count" -lt 4 ]; then echo "FAIL: expected at least 4 status: closed entries (G-01, G-03, G-03-addendum, G-04), got $closed_count"; exit 1; fi

        # Closure plan reference for G-03-addendum + G-04
        grep -q "14-08-gap-closure-bail-out-and-restore-tags-PLAN.md" "$F"

        # Round-3 evidence quoted: 4d-restore must reference Render <role> config role-body task lines
        grep -q "loki : Render Loki config" "$F"
        grep -q "tempo : Render Tempo config" "$F"
        grep -q "mimir : Render Mimir config" "$F"

        # Round-3 evidence quoted: 3a must reference the explicit-fail task
        grep -qE "re-raise under default mode|G-03-addendum" "$F"

        echo "PASS: 14-HUMAN-UAT.md round-3 closure recorded"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - leviathan SSH pre-flight passed; round-3 UAT actually executed (not stubbed).
    - Scenario 3a PLAY RECAP empirically shows `failed=1` and only the garage tarball at the run timestamp; grafana + alertmanager NOT created. The new `re-raise under default mode (G-03-addendum)` task is visible in the captured log; the `clear_host_errors (G-03; opt-in only)` task is visible as SKIPPED.
    - Scenario 4d-restore PLAY RECAP empirically shows `failed=0`; verbose log contains 3 `TASK [<writer> : Render <Writer> config]` lines (loki/tempo/mimir) AND 3 `RUNNING HANDLER ... Docker restart <writer>` lines; no `Forbidden: No such key:` in any telemetron-* container log; all 11 containers healthy at end.
    - 14-HUMAN-UAT.md frontmatter: `status: complete`, `updated:` round-3 ISO timestamp.
    - 14-HUMAN-UAT.md body: exactly 11 `^result: pass`, 0 `^result: fail`, 0 `^result: pending`.
    - 14-HUMAN-UAT.md body: scenario 3a + 4d-restore `detail:` REWRITTEN with round-3 evidence (not just amended); other 9 scenarios `detail:` AMENDED with the round-3 spot-check marker.
    - 14-HUMAN-UAT.md `## Summary`: `passed: 11`, `pending: 0`, `issues: 0`.
    - 14-HUMAN-UAT.md `## Gaps`: 4 entries total (G-01, G-03, G-03-addendum, G-04), all `status: closed`; the 2 new entries cite `14-08-gap-closure-bail-out-and-restore-tags-PLAN.md` as the closure plan and include a `closure-evidence:` field citing the round-3 PLAY RECAP excerpts.
    - Behavioral-correctness gate honored: if either scenario empirically fails, the failed scenario stays `result: fail`, gap stays `status: open`, and Task 2 does NOT execute (instead the orchestrator is signaled that Plan 14-10 is needed).
  </acceptance_criteria>
  <done>
    `14-HUMAN-UAT.md` records the round-3 closure: 11/11 scenarios pass on leviathan post-Plan-14-08;
    both new gaps (G-03-addendum, G-04) closed with empirical PLAY RECAP / verbose-log evidence;
    the round-3 spot-check markers confirm no regression in the 9 previously-passing scenarios.
    Task 2 (VERIFICATION.md flip) is unblocked IFF both scenarios empirically passed.
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip 14-VERIFICATION.md status to passed (6/6 must-haves) -- conditional on Task 1 empirical success</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md</files>
  <read_first>
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md (current state: round-2 status: gaps_found; 5.5/6 must-haves; gaps block contains G-03-addendum + G-04 entries)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md (post-Task-1 state; the round-3 audit doc this update cites as the empirical proof of closure)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-08-SUMMARY.md (the 14-08 structural-fix evidence; the SHAs b5dca0f and d04efcb are the closure commits this verification report references)
  </read_first>
  <action>
    PRECONDITION CHECK: Before editing 14-VERIFICATION.md, verify Task 1's empirical outcome:
      grep -c "^result: pass" .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
        (Must return 11; if not, ABORT this task -- behavioral closure failed.)
      grep -c "^result: fail" .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
        (Must return 0; if not, ABORT this task.)
    If either precondition check fails, do NOT proceed; signal to orchestrator that Task 1 left
    open gaps and Plan 14-10 is needed.

    Once preconditions pass, edit `.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md`:

    1. Frontmatter:
       - `status: gaps_found` -> `status: passed`.
       - `score: 5.5/6 must-haves verified` -> `score: 6/6 must-haves verified`.
       - `re_verified:` -> update value to the round-3 ISO 8601 UTC timestamp (Z suffix) -- this
         REPLACES the round-2 re_verified value; the audit trail is preserved via the body section
         (see step 11).
       - `gaps:` block: REPLACE the two-entry array (G-03-addendum + G-04) with empty `gaps: []`.
       - `overrides_applied:` stays 0.
       - `human_verification:` stays `[]`.

    2. Body header block (the `**Verified:**` / `**Re-verified:**` / `**Status:**` /
       `**Re-verification:**` lines):
       - `**Verified:**` round-1 timestamp: PRESERVE verbatim (audit trail).
       - `**Re-verified:**` line: REPLACE the round-2 value with the round-3 ISO timestamp.
       - `**Status:**` flip from `gaps_found (2 new gaps opened in Round 2: G-03-addendum + G-04)`
         to `passed`.
       - `**Re-verification:**` flip from `Yes -- post-G-01+G-03 closure round 2 ...` to
         `Yes -- post-G-03-addendum + G-04 closure (Plan 14-08); round-3 leviathan UAT proved scenarios 3a + 4d-restore PASS (see 14-HUMAN-UAT.md round-3 evidence)`.

    3. `## Goal Achievement`: APPEND a new paragraph at the end of the section stating that all 4
       gaps (G-01, G-03 opt-in, G-03-addendum, G-04) are now closed via Plans 14-05 + 14-06 + 14-08,
       that the round-3 leviathan UAT empirically verified the two remaining gaps closed (PLAY RECAP
       `failed=1` for scenario 3a default-mode bail-out, PLAY RECAP `failed=0` with role-body subtasks
       firing for scenario 4d-restore --tags restore), and that all 6 must-haves are now verified.
       Phase 14 milestone acceptance gate closes. Phase 15 (documentation cascade) is unblocked.

    4. `### Observable Truths` table:
       - SC5 row: flip `⚠️ PARTIAL` to `✓ VERIFIED`. Update the Evidence cell to AMEND (not replace)
         the existing round-2 evidence with the round-3 scenario-3a closure evidence: "Round-3
         scenario 3a (default mode + file-as-dir fault) PLAY RECAP `failed=1`; only garage tarball at
         run-ts; grafana + alertmanager not attempted. Combined with round-2 scenario 3b opt-in
         evidence (3 of 4 tarballs), both default-mode bail-out AND opt-in continue-on-failure
         contracts are now empirically verified. G-03-addendum CLOSED by Plan 14-08."
       - SC6 row: flip `✓ VERIFIED (with G-04 caveat for restore)` to `✓ VERIFIED`. Update the
         Evidence cell to AMEND the existing round-2 untagged-play evidence with the round-3
         scenario-4d-restore closure evidence: "Round-3 scenario 4d-restore (`--tags restore` on
         clean post-purge state) PLAY RECAP `failed=0`; verbose-log shows the 3 writer role-body
         template-render tasks firing (TASK [loki : Render Loki config], etc.). G-04 caveat RESOLVED:
         `--tags restore` cross-cutting now exercises the writer-rerender path correctly. G-04 CLOSED
         by Plan 14-08 (`apply: tags: [garage, restore]` propagates tags into role body)."
       - The other 4 rows (SC1/SC2/SC3/SC4) stay UNCHANGED -- their round-2 ✓ VERIFIED status and
         evidence remain valid. (SC4 may have referenced the G-04 caveat -- if so, remove the
         caveat sentence and reference round-3 4d-restore evidence.)

    5. `### Required Artifacts` table:
       - `playbooks/restore_docker.yml` row: amend the Details cell to remove the "Does NOT fire
         under `--tags restore` (G-04)" caveat; add a one-line note: "Post-14-08: `apply: tags:
         [garage, restore]` on the 3 writer-rerender include_role calls makes the role body tasks
         selectable under `--tags restore` (round-3 scenario 4d-restore empirically confirmed)."
       - `playbooks/backup_docker.yml` row: amend (if applicable) -- if there was a G-03-addendum
         note in the round-2 doc, remove it; add a one-line note: "Post-14-08: each rescue block
         now has an explicit `ansible.builtin.fail` as first task guarded by `when: not (knob)`
         to re-raise the failure under default mode; PLAY RECAP `failed=1` (round-3 scenario 3a
         empirically confirmed)."

    6. `### Key Link Verification` table:
       - The `restore_docker.yml Garage restore -> Writer-config rerender` row currently says
         `✓ WIRED (untagged play only)`. Flip to `✓ WIRED`. Update Details to remove the "Does NOT
         fire under `--tags restore` (G-04)" caveat; add the round-3 scenario-4d-restore evidence
         (3 role-body task names + handler chain firing).
       - The `restore_docker.yml writer-rerender -> Writer-restart` row currently says
         `✓ WIRED (untagged play only)`. Flip to `✓ WIRED`. Update Details to remove the "Not
         triggered under `--tags restore` (G-04)" caveat; add the round-3 evidence (handler chain
         fires under --tags restore).

    7. `### Requirements Coverage` table:
       - `RESTORE-V13-05` row: flip `✓ SATISFIED (untagged play)` to `✓ SATISFIED`. Update Evidence
         to remove the "G-04 caveat" reference; cite round-3 scenario 4d-restore PLAY RECAP `failed=0`.
       - `OPS-V13-02` row: flip `⚠️ PARTIAL` to `✓ SATISFIED`. Update Evidence to confirm both
         contracts: default-mode bail-out via round-3 scenario 3a (PLAY RECAP `failed=1`); opt-in
         continue-on-failure via round-2 scenario 3b (3 of 4 tarballs); banner alt text accurate
         in both modes; G-03-addendum closed by Plan 14-08.
       - `OPS-V13-03` row: flip `⚠️ PARTIAL` to `✓ SATISFIED`. Update Evidence to confirm both
         cross-cutting tags work: `--tags backup` via round-2 scenario 4d-backup; `--tags restore`
         via round-3 scenario 4d-restore (verbose-log proves role-body subtasks fire); per-role
         tags work; G-04 closed by Plan 14-08.
       - `UAT-V13-01` row: flip `✓ SATISFIED (untagged play)` to `✓ SATISFIED`. Update Evidence to
         remove the "G-04 caveat" reference; cite both round-2 scenario 1 (untagged round-trip) AND
         round-3 scenario 4d-restore (`--tags restore` clean exercise).

    8. `### Anti-Patterns Found` table:
       - The `playbooks/backup_docker.yml | rescue blocks` row (G-03-addendum): mark as ✓ RESOLVED
         by Plan 14-08 Task 1 (explicit `ansible.builtin.fail` added to each rescue); either delete
         the row or add a Resolution note (deletion is cleaner).
       - The `playbooks/restore_docker.yml | writer-rerender include_role tasks` row (G-04): mark
         as ✓ RESOLVED by Plan 14-08 Task 2 (`apply: tags: [garage, restore]` added to each
         writer-rerender include_role); either delete the row or add a Resolution note.
       - The WR-02/03 docker stop/start idempotency row STAYS (pre-existing concern, out of
         Phase 14 scope; documented as known debt).
       - The WR-04 banner default(...) row STAYS (pre-existing info-level concern).

    9. `### Gaps Summary` section: REPLACE the round-2 paragraph (which lists G-03-addendum + G-04
       as open) with a closure narrative:
       "All 4 gaps from rounds 1 and 2 are now closed:
        - G-01 (writer-config re-render): CLOSED by Plan 14-05 (round 2 evidence).
        - G-03 (backup_continue_on_failure=true): CLOSED for opt-in by Plan 14-06 (round 2 evidence).
        - G-03-addendum (default bail-out broken by rescue): CLOSED by Plan 14-08 Task 1 (round 3
          scenario 3a PLAY RECAP `failed=1` empirical evidence).
        - G-04 (writer-rerender skipped under --tags restore): CLOSED by Plan 14-08 Task 2 (round 3
          scenario 4d-restore verbose-log shows role-body tasks firing).
        SC5 + SC6 are both VERIFIED. RESTORE-V13-05 / OPS-V13-02 / OPS-V13-03 / UAT-V13-01 are all
        SATISFIED. Phase 14 milestone acceptance gate closes."

    10. `### Recommended Next Path` section: REPLACE the round-2 "Open a follow-up plan (14-08)..."
        paragraph with: "Phase 14 is now complete with 6/6 must-haves verified. Recommended next step:
        plan Phase 15 (Documentation Cascade + Gate 11) via `/gsd:plan-phase 15`. The doc cascade
        references the final playbook flags and operator UX surface, which are now settled."

    11. Trailing audit signature lines: update to add the round-3 re-verifier line:
        `_Verified: <round-1 timestamp>_`
        `_Verifier: Claude (gsd-verifier)_`
        `_Re-verified: <round-2 timestamp>_`
        `_Re-verifier: Claude (gsd-verifier; post-G-01+G-03 closure re-UAT round 2)_`
        `_Re-verified: <round-3 timestamp>_`
        `_Re-verifier: Claude (gsd-verifier; post-G-03-addendum+G-04 closure re-UAT round 3 -- milestone acceptance gate)_`

    Constraints:
    - English-only.
    - PRESERVE round-1 and round-2 timestamps + their evidence (audit trail).
    - The round-3 update AMENDS evidence cells rather than replacing them; the round-2 evidence
      remains valid as foundational proof of the structural fixes (Plans 14-05, 14-06); the round-3
      evidence proves the empirical behavioral closure of the 14-08 structural fixes.
    - Unchanged rows (SC1/SC2/SC3 + their requirements) retain their existing ✓ VERIFIED status.
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
        test -s "$F"

        # PRECONDITION: 14-HUMAN-UAT.md must show 11 pass / 0 fail
        HUAT=.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
        huat_pass=$(grep -c "^result: pass" "$HUAT" || true)
        huat_fail=$(grep -c "^result: fail" "$HUAT" || true)
        if [ "$huat_pass" -ne 11 ]; then echo "PRECONDITION FAIL: 14-HUMAN-UAT.md must have 11 pass, got $huat_pass"; exit 1; fi
        if [ "$huat_fail" -ne 0 ]; then echo "PRECONDITION FAIL: 14-HUMAN-UAT.md must have 0 fail, got $huat_fail"; exit 1; fi

        # Frontmatter: status flip to passed, score 6/6, re_verified updated, gaps emptied
        grep -q "^status: passed" "$F"
        grep -q "^score: 6/6 must-haves verified" "$F"
        grep -q "^re_verified:" "$F"
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

        # Body: no remaining FAILED / BLOCKED / PARTIAL caveats in cell text (excluding the audit-trail
        # PARTIAL anti-pattern row which is allowed to stay if it references resolved gaps)
        if grep -q "✗ FAILED" "$F"; then echo "FAIL: ✗ FAILED still present"; exit 1; fi
        if grep -q "✗ BLOCKED" "$F"; then echo "FAIL: ✗ BLOCKED still present"; exit 1; fi
        # Allow at most 0 PARTIAL after round-3 closure
        partial_count=$(grep -c "⚠️ PARTIAL" "$F" || true)
        if [ "$partial_count" -gt 0 ]; then echo "FAIL: expected 0 ⚠️ PARTIAL cells, got $partial_count"; exit 1; fi

        # Closure plan references
        grep -q "14-05" "$F"
        grep -q "14-06" "$F"
        grep -q "14-08" "$F"
        # All 4 gap IDs referenced in closure narrative
        grep -q "G-01" "$F"
        grep -q "G-03-addendum" "$F"
        grep -q "G-04" "$F"
        # G-03 base ID also referenced (separately from G-03-addendum)
        grep -qE "G-03[^-]|G-03$" "$F"

        # Round-3 markers in body (Re-verified line + recommended next path = Phase 15)
        grep -q "round 3\|Round 3\|round-3\|Round-3" "$F"
        grep -q "Phase 15" "$F"

        # Audit-trail preserved: both round-1 verifier and round-2 + round-3 re-verifier lines present
        grep -q "_Verifier: Claude" "$F"
        grep -qE "_Re-verifier: Claude.*round 2|_Re-verifier: Claude.*round-2" "$F"
        grep -qE "_Re-verifier: Claude.*round 3|_Re-verifier: Claude.*round-3" "$F"

        echo "PASS: 14-VERIFICATION.md flipped to status: passed with 6/6 must-haves (round-3 closure)"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - PRECONDITION verified: 14-HUMAN-UAT.md (post-Task-1) shows 11 `^result: pass` and 0 `^result: fail`. If precondition fails, this task did NOT execute the doc flip.
    - 14-VERIFICATION.md frontmatter: `status: passed`, `score: 6/6 must-haves verified`, `re_verified:` updated to round-3 ISO timestamp (Z suffix), `gaps: []` (empty array).
    - Body: zero `✗ FAILED`, zero `✗ BLOCKED`, zero `⚠️ PARTIAL` strings in cell-status columns.
    - Body: Plan IDs `14-05`, `14-06`, `14-08` all cited as closure plans for the 4 gaps.
    - Body: `G-01`, `G-03` (base), `G-03-addendum`, `G-04` all referenced in the closure narrative.
    - Body: `Phase 15` cited as the recommended next path (doc cascade).
    - Body: round-1 `**Verified:**` timestamp preserved verbatim (audit trail).
    - Body: round-2 and round-3 re-verifier signature lines both present at end of file (audit trail).
    - Body: SC1/SC2/SC3 rows (and their evidence) in `### Observable Truths` retain their existing ✓ VERIFIED status from round 2.
    - Body: `### Goal Achievement` includes the closure paragraph confirming 6/6 must-haves and citing Plans 14-05/14-06/14-08 + round-3 UAT.
  </acceptance_criteria>
  <done>
    `14-VERIFICATION.md` now declares Phase 14 milestone-complete: 6/6 must-haves verified, all 4
    gaps closed with closure-plan citations spanning Plans 14-05/14-06/14-08, recommended next path
    points at Phase 15. The audit trail (round-1 + round-2 + round-3 timestamps and re-verifier
    signatures) preserves the full closure history. Ready for the git commit in Task 3.
  </done>
</task>

<task type="auto">
  <name>Task 3: Single git commit covering both doc updates (14-HUMAN-UAT.md + 14-VERIFICATION.md) citing G-03-addendum + G-04 closure + round-3 leviathan UAT</name>
  <files>
    .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md,
    .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
  </files>
  <read_first>
    - git log --oneline -10 (recent commit style: `b93ef4b docs(14): VERIFICATION -- gaps_found, 5/6 must-haves verified`, `cddb3cd docs(14): HUMAN-UAT + VERIFICATION -- round-2 re-UAT, G-01 closed, G-03 opt-in closed, 2 new gaps (G-03-addendum, G-04)`, `1801ae1 test(14-04): live UAT round-trip on leviathan ...`. The convention is `docs(14): <doc-name> -- <one-line summary>`.)
  </read_first>
  <action>
    PRECONDITION CHECK: Verify Tasks 1 + 2 actually landed their edits:
      git status --porcelain | grep -E "14-(HUMAN-UAT|VERIFICATION)\\.md"
        (Both files must show as modified (M) -- if neither does, Tasks 1+2 did not run; ABORT.)

    Create a single git commit that captures the round-3 closure. Suggested commit message (use this
    verbatim or improve as the executor sees fit; the type MUST be `docs(14)` matching the prior
    phase-14 commit convention -- see git log -10):

      docs(14): HUMAN-UAT + VERIFICATION -- round-3 closure, G-03-addendum + G-04 closed, 6/6 must-haves verified

      Round 3 re-UAT on leviathan post-Plan-14-08 structural fix:
      - Scenario 3a (default bail-out + Prometheus file-as-dir fault): PASS -- PLAY RECAP failed=1.
        The new explicit ansible.builtin.fail in each rescue block (Plan 14-08 Task 1) re-raises the
        failure under default mode; any_errors_fatal aborts the play; grafana + alertmanager
        include_role calls do not execute. G-03-addendum CLOSED.
      - Scenario 4d-restore (--tags restore on clean post-purge state with new Garage key): PASS --
        PLAY RECAP failed=0. The new apply: tags: [garage, restore] mapping on the 3 writer-rerender
        include_role calls (Plan 14-08 Task 2) propagates the tag list into the loki/tempo/mimir role
        bodies; verbose log shows TASK [loki : Render Loki config], TASK [tempo : Render Tempo
        config], TASK [mimir : Render Mimir config] firing with CHANGED status; restart handlers
        chain; writers come up healthy against the restored Garage S3 key; no Forbidden: No such key
        errors. G-04 CLOSED.
      - Other 9 scenarios (1, 2a, 2b, 2c, 3b, 4a, 4b, 4c, 4d-backup) spot-checked: no regression
        (14-08 structural fixes do not touch their surface area).
      - All 4 gaps from rounds 1+2 now closed: G-01 (Plan 14-05), G-03 opt-in (Plan 14-06),
        G-03-addendum (Plan 14-08 Task 1), G-04 (Plan 14-08 Task 2).
      - VERIFICATION status flipped from gaps_found to passed (6/6 must-haves verified).
      - Phase 14 milestone acceptance gate closes. Next: /gsd:plan-phase 15 (documentation cascade).

    Stage EXACTLY these 2 files (no others; Plan 14-08 already committed the playbook fixes in
    b5dca0f + d04efcb -- this commit is documentation-only):
      .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
      .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md

    Use the GSD HEREDOC pattern to preserve commit message formatting:

      git add .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md \
              .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
      git commit -m "$(cat <<'EOF'
      docs(14): HUMAN-UAT + VERIFICATION -- round-3 closure, G-03-addendum + G-04 closed, 6/6 must-haves verified

      <full multi-line body as above>

      Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
      EOF
      )"

    Run `git status` after the commit to verify clean state on the 2 files (they should no longer
    appear as modified).
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"

        # Latest commit must touch both files
        LAST=$(git log -1 --name-only --pretty=format:"")
        echo "$LAST" | grep -q "14-HUMAN-UAT.md"
        echo "$LAST" | grep -q "14-VERIFICATION.md"

        # Latest commit must NOT touch any other files (this is a docs-only commit)
        commit_file_count=$(echo "$LAST" | grep -E "^\\S" | wc -l)
        if [ "$commit_file_count" -gt 2 ]; then echo "FAIL: commit touches >2 files (got $commit_file_count)"; exit 1; fi

        # Commit message references G-03-addendum + G-04 + round-3 + 6/6 closure
        LAST_MSG=$(git log -1 --pretty=%B)
        echo "$LAST_MSG" | grep -qi "G-03-addendum"
        echo "$LAST_MSG" | grep -qi "G-04"
        echo "$LAST_MSG" | grep -qiE "round 3|round-3"
        echo "$LAST_MSG" | grep -qiE "6/6|passed|closure|closed"
        echo "$LAST_MSG" | grep -q "Co-Authored-By: Claude"

        # Commit follows docs(14) convention
        echo "$LAST_MSG" | head -1 | grep -qE "^docs\\(14\\):"

        # No uncommitted changes on the 2 doc files
        if git status --porcelain | grep -E "14-(HUMAN-UAT|VERIFICATION)\\.md"; then
          echo "FAIL: 14-HUMAN-UAT.md or 14-VERIFICATION.md still uncommitted"; exit 1
        fi

        echo "PASS: round-3 closure commit landed (docs-only; 2 files; G-03-addendum + G-04 closure cited)"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - Single commit landed with EXACTLY `14-HUMAN-UAT.md` and `14-VERIFICATION.md` in its file list (no other files).
    - Commit message header follows `docs(14): ...` convention.
    - Commit message body references `G-03-addendum`, `G-04`, round 3 (or `round-3`), and the closure / 6/6 keyword.
    - Co-Authored-By trailer follows the GSD convention (`Claude Opus 4.7 <noreply@anthropic.com>`).
    - `git status` shows clean for the 2 updated files post-commit.
  </acceptance_criteria>
  <done>
    The round-3 closure is committed. Phase 14 milestone acceptance gate is closed -- v1.3.0
    backup/restore round-trip is empirically proven on leviathan under BOTH the untagged full-play
    AND the `--tags restore` cross-cutting forms, with bail-out semantics correct under both default
    and opt-in modes. Next step: `/gsd:plan-phase 15` for the documentation cascade.
  </done>
</task>

</tasks>

<verification>
- Task 1 is a fully-autonomous live UAT (no checkpoint -- Rock pre-authorized round-3 Claude-driven mode b). Behavioral correctness is the gate: if either scenario empirically fails, the plan does NOT silently flip docs to passed; instead it leaves the failure on record and signals Plan 14-10 needed.
- Task 2 verification is fully automated: PRECONDITION check on 14-HUMAN-UAT.md results + YAML frontmatter parse + structural grep gates verify the status flip + closure-plan references + zero remaining PARTIAL/FAILED/BLOCKED cells.
- Task 3 verification is fully automated: git log inspection verifies a docs-only commit with both files + the right closure references + the docs(14) convention header.
- After all 3 tasks complete, Phase 14 milestone acceptance gate is closed (6/6 must-haves; all 4 gaps closed). v1.3.0 backup/restore round-trip empirically proven on leviathan under all relevant invocation forms.
</verification>

<success_criteria>
- BACKUP-V13-05: SATISFIED. `backup_docker.yml` orchestrator + 4 stateful roles in forward order + D-186 banner + stateless-tag empty play all verified across rounds 1+2; round-3 confirms G-03-addendum closure does not regress backup mechanics.
- OPS-V13-02: SATISFIED. Both contracts verified empirically: default-mode bail-out via round-3 scenario 3a (PLAY RECAP `failed=1`, grafana + alertmanager not attempted); opt-in continue-on-failure via round-2 scenario 3b (3 of 4 tarballs). Banner alt text accurate under both modes.
- RESTORE-V13-05: SATISFIED. Writer-stop / Garage restore / writer-config rerender / writer-restart / healthy-poll chain verified under BOTH untagged full play (round-2 scenario 1) AND `--tags restore` cross-cutting (round-3 scenario 4d-restore). No `Forbidden: No such key:` errors in either invocation form.
- UAT-V13-01: SATISFIED. 7-step round-trip verified end-to-end on leviathan with no manual intervention (round 2); `--tags restore` cross-cutting form also verified clean on leviathan (round 3). Same OTLP signals round-trip across all 4 signal types.
- All 4 gaps closed: G-01 (Plan 14-05), G-03 opt-in (Plan 14-06), G-03-addendum (Plan 14-08 Task 1 -- round-3 empirical proof), G-04 (Plan 14-08 Task 2 -- round-3 empirical proof).
- `14-VERIFICATION.md` status: passed. Score 6/6. All Observable Truths rows ✓ VERIFIED. All Requirements Coverage rows ✓ SATISFIED. `gaps:` block empty.
- `14-HUMAN-UAT.md` status: complete. 11/11 sub-scenarios pass. 4/4 gap entries closed.
- Single round-3 closure commit on git (docs-only; 2 files). Phase 14 milestone acceptance gate closed; Phase 15 unblocked.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator workstation -> leviathan via passwordless SSH | Claude-driven UAT execution via ssh; leviathan is the live UAT host (Memory `project_leviathan_uat_host.md`). The fault-injection in scenario 3a modifies its filesystem (`mv` + `touch`). Cleanup is mandatory and runs immediately after the scenario regardless of pass/fail outcome. |
| Scenario 3a fault-injection state -> scenario 4d-restore setup | If 3a cleanup is forgotten, the 4d-restore setup backup step (which is the first step in the 4d-restore sequence) would itself fail at the Prometheus role. Mitigation: 3a cleanup is the IMMEDIATE next step after the 3a run, before any 4d-restore setup. |
| Round-3 doc edits -> rounds-1+2 audit trail | Round-1 and round-2 evidence is factual and must be preserved (timestamps + scenarios that passed in those rounds). Round-3 amends evidence cells (not replaces) for unchanged scenarios; round-3 fully rewrites only scenario 3a and 4d-restore detail sections (their round-2 evidence documented failure paths that are now obsolete). |
| Task 2 doc flip -> Task 1 empirical result | If Task 1 leaves any scenario at `result: fail`, Task 2 must NOT execute the VERIFICATION.md flip. Mitigation: Task 2 begins with a PRECONDITION check (grep 14-HUMAN-UAT.md for 11 pass / 0 fail); precondition failure aborts Task 2. |
| Task 3 commit -> uncommitted other files | The Plan 14-08 commit already landed the playbook fixes (b5dca0f, d04efcb). Task 3 must commit ONLY the 2 doc files. Mitigation: explicit `git add` of the 2 files only (not `git add -A`); verify gate asserts commit_file_count <= 2. |
| Behavioral-correctness gate -> developer trust | The plan explicitly disclaims silent success: if the empirical evidence on leviathan contradicts the 14-08 structural fix, the plan documents the failure rather than flipping docs to passed. This preserves developer trust in the gsd verification chain. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-09-01 | Denial of Service | Forgotten cleanup of scenario 3a file-as-dir fault leaves /opt/telemetron/backups/prometheus as a regular file, breaking the 4d-restore setup backup step | mitigate | Task 1 action explicitly calls out the cleanup commands as a MANDATORY step immediately after the 3a run (before any 4d-restore setup), regardless of 3a pass/fail outcome. |
| T-14-09-02 | Tampering | Round-3 doc edit accidentally deletes round-1 or round-2 audit trail entries (verified timestamps, prior-round evidence) | mitigate | Task 2 action explicitly preserves the `**Verified:**` round-1 timestamp and the round-2 audit-signature line; Task 1 action explicitly amends (not replaces) the detail sections of the 9 passing scenarios so their round-1+2 evidence remains. Acceptance_criteria assert SC1/SC2/SC3 rows retain their round-2 ✓ VERIFIED status. |
| T-14-09-03 | Repudiation | Closure commit lands but round-3 empirical evidence is not actually captured -- VERIFICATION.md says "passed" but HUMAN-UAT.md detail sections still show round-2 fail evidence for scenarios 3a / 4d-restore | mitigate | Task 1 acceptance_criteria require scenario 3a + 4d-restore `detail:` to be REWRITTEN with the round-3 PLAY RECAP / verbose-log evidence; Task 2 PRECONDITION check asserts 11 pass / 0 fail in 14-HUMAN-UAT.md before flipping VERIFICATION.md; Task 3 verify gates assert the commit message references G-03-addendum + G-04 + round-3 keywords. |
| T-14-09-04 | Denial of Service | UAT task hangs because leviathan is unreachable mid-run (e.g., between scenario 3a and scenario 4d-restore) | mitigate | Task 1 pre-flight uses `ssh -o BatchMode=yes -o ConnectTimeout=5` to fail fast on connectivity issues; if 3a completes but 4d-restore setup fails because leviathan is unreachable, ABORT and signal orchestrator (per W-4 mitigation pattern from Plan 14-04). |
| T-14-09-05 | Tampering | A previously-passing scenario regresses due to an unexpected 14-08 side effect (e.g., scenario 4d-backup catches the new explicit-fail task under --tags backup and fails) and is overlooked because round-3 only re-runs 3a + 4d-restore in full | mitigate | Task 1 explicitly addresses this in the issue-handling clause: if a previously-passing scenario regresses (detected via spot-check or downstream observation), re-execute that scenario in full and leave it `result: fail` until investigated. The surface-area analysis in the `<interfaces>` block argues this is extremely unlikely but the plan does not assume it cannot happen. |
| T-14-09-06 | Tampering (behavioral correctness gate) | The structural 14-08 fix did NOT actually deliver the expected behavioral change (e.g., the `apply: tags:` mechanism does not propagate as expected in Ansible's version on leviathan) but the plan flips VERIFICATION to passed anyway | mitigate | EXPLICIT in plan objective and Task 2 PRECONDITION check: this plan does NOT silently flip VERIFICATION.md to passed when empirical evidence contradicts. If either scenario empirically fails, Task 1 leaves it `result: fail`, Task 2 ABORTS at PRECONDITION check, and the orchestrator is signaled that Plan 14-10 is needed. Behavioral correctness is the gate, not structural plan completion. |
| T-14-09-07 | Information Disclosure | The fault-injection (file-as-dir on /opt/telemetron/backups/prometheus) leaves a stale state on leviathan that bleeds into subsequent UAT sessions or production smoke tests | mitigate | Cleanup commands are documented inline and run IMMEDIATELY after each fault-injecting scenario. Cleanup is verified visually by the operator-equivalent (Claude) inspecting `ls -ld /opt/telemetron/backups/prometheus` post-cleanup; if the SAVED rename is not restored, the next backup_docker.yml run would catch it. |
| T-14-09-SC | Tampering | Round-3 inadvertently introduces supply-chain risk (new package installs, dependency updates) outside the scope of doc + UAT-evidence work | accept | This plan does NOT install any new packages, modify any roles, or touch any Ansible / Python dependency surface. The only writes are to 2 Markdown files. The only runtime activity is ansible-playbook invocations against existing playbooks + roles already shipped by Plans 14-01..14-08. No package-legitimacy gate is needed because no `package` / `pip` / `npm` / `cargo` install is invoked. |
</threat_model>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-09-SUMMARY.md` when done. The SUMMARY captures:
- Whether both scenarios (3a + 4d-restore) actually PASSED round-3 empirically (the binary closure outcome)
- The verbatim PLAY RECAP one-liner for each of the 2 re-run scenarios
- The 3 verbose-log grep lines that prove G-04 closure (`TASK [loki : Render Loki config]`, etc.)
- The closure-commit SHA from Task 3
- A one-line declaration of Phase 14 milestone-gate closure
- Reference the closure-plan IDs (14-05, 14-06, 14-08) explicitly so the SUMMARY is self-contained
- If the empirical evidence did NOT close one of the gaps, the SUMMARY documents the failure mode explicitly and references the open Plan 14-10
</output>
</content>
