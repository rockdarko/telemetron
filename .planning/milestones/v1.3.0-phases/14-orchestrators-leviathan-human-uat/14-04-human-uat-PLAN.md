---
phase: 14-orchestrators-leviathan-human-uat
plan: 04
type: execute
wave: 3
depends_on:
  - 14-01
  - 14-02
  - 14-03
files_modified:
  - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
autonomous: false
requirements:
  - UAT-V13-01

must_haves:
  truths:
    - "`14-HUMAN-UAT.md` exists with the verbatim format used in `.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` (YAML frontmatter + `## Current Test` + `## Tests` + numbered scenarios with `expected:` / `result:` / `detail:` three-line shape + `## Summary` block)."
    - "Scenario 1 documents the 7-step round-trip happy-path on leviathan (deploy -> smoke[record trace_id+run_id] -> backup -> undeploy --purge-data -> deploy -> restore --confirm --from=<ts> -> smoke[re-assert same trace_id+run_id]) -- proves UAT-V13-01. Step 7 asserts the SAME OTLP log + metric + trace signals visible in Grafana (smoke_test.yml asserts Loki + Prometheus + Mimir + Tempo via Grafana datasource-proxy queries -- ALL FOUR signal types verified, including Loki, per the smoke_test.yml asserter task list)."
    - "Scenario 2 documents the confirm-gate proof in 3 sub-tests: 2a orchestrator-level fail under default invocation, 2b custom-playbook include_role-level fail, 2c orchestrator-level fail under stateless-tag invocation (`--tags loki` WITHOUT confirm flag still fails at the orchestrator gate before tag-filtering, proving the gate is identity-level per D-188 amended by SC4 reconciliation) -- proves OPS-V13-01 at both layers (D-185 defence-in-depth) AND proves the D-188 amendment is upheld in practice."
    - "Scenario 3 documents the bail-out vs continue-on-failure proof in 2 sub-tests: 3a default run aborts on Prometheus (Garage tarball exists, Grafana+Alertmanager NOT attempted), 3b opt-in run lets all 4 attempt (Prometheus fails, others succeed) -- proves OPS-V13-02."
    - "Scenario 4 documents the tag-scoped proof in 5 sub-tests: 4a `--tags garage` backup produces only garage tarball; 4b `--tags loki --extra-vars backup_restore_confirm=true` (restore_docker.yml) produces empty 0-task play after gate passes (D-188 amended); 4c `--tags grafana --extra-vars backup_restore_confirm=true backup_restore_from=<ts>` restores only Grafana with writers untouched (D-189 amended -- `--tags grafana` does NOT fire writer-stop because writer-stop carries `[garage, restore]` only, not `[grafana]`); 4d-backup `--tags backup` cross-cutting backup runs all 4 roles (SC4 cross-cutting backup verb); 4d-restore `--tags restore --extra-vars backup_restore_confirm=true backup_restore_from=<ts>` cross-cutting restore runs the bracketed Garage unit + the other 3 roles (SC4 cross-cutting restore verb) -- proves OPS-V13-03 AND SC4 cross-cutting empirically."
    - "After live UAT execution on leviathan: frontmatter `status: complete`, all 11 scenarios (including all sub-tests) show `result: pass`, `smoke_trace_id` + `smoke_run_id` recorded in scenario 1 step 2 evidence and reused in step 7 evidence (proving end-to-end data round-trip across log+metric+trace via Loki+Prometheus+Mimir+Tempo asserter results)."
  artifacts:
    - path: ".planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md"
      provides: "Audit doc for Phase 14 with 4 scenarios (1 happy-path + 3 negative, expanded to 11 sub-scenarios total) -- starts at status: in_progress; flips to status: complete after live UAT."
      min_lines: 100
      contains: "## Tests"
  key_links:
    - from: "Scenario 1 step 2 PLAY OUTPUT (smoke_test.yml first run)"
      to: "Scenario 1 step 7 PLAY OUTPUT (smoke_test.yml second run)"
      via: "Operator captures smoke_trace_id + smoke_run_id from step 2 and re-passes via --extra-vars on step 7"
      pattern: "smoke_trace_id|smoke_run_id"
    - from: "Scenario 2a `ansible-playbook restore_docker.yml` (no confirm)"
      to: "Orchestrator-level fail pre_task fires"
      via: "stderr/PLAY OUTPUT contains 'backup_restore_confirm'"
      pattern: "Pass --extra-vars backup_restore_confirm=true"
    - from: "Scenario 2c `ansible-playbook restore_docker.yml --tags loki` (no confirm)"
      to: "Orchestrator-level fail pre_task fires under stateless tag (proves D-188 amended -- identity-level safety)"
      via: "stderr/PLAY OUTPUT contains 'backup_restore_confirm'"
      pattern: "Pass --extra-vars backup_restore_confirm=true"
    - from: "Scenario 3a default invocation -> Prometheus tar fails (chmod fault-injection)"
      to: "PLAY RECAP shows failed=1 on Prometheus, garage tarball present, grafana+alertmanager tarballs absent"
      via: "any_errors_fatal default branch (false -> bail-out)"
      pattern: "failed=1"
    - from: "Scenario 4a `--tags garage` backup invocation"
      to: "Only garage-<ts>.tar.zst written; no prometheus/grafana/alertmanager tarball touched"
      via: "Ansible tag selection on per-role include_role tags: [<role>, backup]"
      pattern: "tags: garage"
    - from: "Scenario 4d-backup `--tags backup` cross-cutting backup invocation"
      to: "All 4 stateful-role tarballs written under one shared timestamp"
      via: "SC4 cross-cutting [backup] tag on every include_role"
      pattern: "tags: backup"
    - from: "Scenario 4d-restore `--tags restore` cross-cutting restore invocation"
      to: "All 4 stateful roles restored AND writer-quiesce bracket executes (writer-stop -> Garage -> writer-restart)"
      via: "SC4 cross-cutting [restore] tag on every include_role AND on the 4 writer-quiesce tasks"
      pattern: "tags: restore"
---

<objective>
Ship `14-HUMAN-UAT.md` -- the live audit doc that proves Phase 14 ships on Rock's leviathan host. Doc starts at `status: in_progress` with all 11 sub-scenarios at `result: pending`, then a live UAT run on leviathan flips each sub-scenario to `result: pass` with verbatim PLAY OUTPUT excerpts captured in `detail:`. The 7-step round-trip in Scenario 1 closes UAT-V13-01; the negative scenarios close OPS-V13-01..03 with field evidence; the new Scenario 4d sub-tests close SC4 cross-cutting tag claim with field evidence.

Purpose: this is the milestone acceptance gate for Phase 14. The single doc is both the test plan AND the test report -- mirrors the v1.2.0 Phase 11 HUMAN-UAT workflow Rock proved out 2026-05-30. No other artifact is required for UAT-V13-01; this doc IS the artifact.
Output: one new audit doc at `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md`. No other files changed.
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
@.planning/phases/14-orchestrators-leviathan-human-uat/14-PATTERNS.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-01-amend-backup-yml-timestamp-override-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-02-backup-docker-orchestrator-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-03-restore-docker-orchestrator-PLAN.md

@.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md
@playbooks/backup_docker.yml
@playbooks/restore_docker.yml
@playbooks/smoke_test.yml
@playbooks/deploy_docker.yml
@playbooks/undeploy_docker.yml

<interfaces>
<!-- The doc consumes outputs from Plans 01/02/03 (the new playbooks + amended backup.yml files) -->
<!-- and from existing playbooks (deploy/undeploy/smoke). It does NOT modify any playbook. -->

inventory: inventory/leviathan/    (GITIGNORED -- present on Rock's workstation per MEMORY.md project_leviathan_uat_host.md; ssh passwordless; Docker 29)
host: telemetron group, single member `leviathan`

smoke_test.yml outputs to capture (scenario 1 step 2):
  smoke_trace_id : hex string (lookup('password', length=32, chars=hexdigits))
  smoke_run_id   : epoch seconds (ansible_date_time.epoch)

  Both printed in PLAY OUTPUT at smoke_test.yml lines 219-220 (`trace_id:` + `run_id:`).
  Operator captures and re-passes.

  smoke_test.yml asserter task names (all 4 signal-types verified via Grafana datasource-proxy):
    - "Smoke assert -- Loki received smoke log"        (line 119, register: smoke_assert_loki)
    - "Smoke assert -- Prometheus received smoke metric" (line 141, register: smoke_assert_prometheus)
    - "Smoke assert -- Mimir received smoke metric (remote_write validation)" (line 164, register: smoke_assert_mimir)
    - "Smoke assert -- Tempo received smoke trace"      (line 190, register: smoke_assert_tempo)

  PLAY OUTPUT summary lines 215-224 print "loki: ok", "prom: ok", "mimir: ok", "tempo: ok".

scenario 3 fault-injection (Claude's-Discretion: manual instruction in doc, not throwaway playbook):
  Setup  : `ssh leviathan sudo chmod 000 /opt/telemetron/backups/prometheus/`  (denies tar write -> Prometheus backup fails at the destination-dir write step)
  Cleanup: `ssh leviathan sudo chmod 0700 /opt/telemetron/backups/prometheus/`  (restore mode for subsequent scenarios)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Ship 14-HUMAN-UAT.md skeleton -- frontmatter, all 11 sub-scenarios with expected:/result: pending/detail: TBD</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md</files>
  <read_first>
    - .planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md (verbatim format reference -- frontmatter, ## Current Test, ## Tests, scenario shape, sub-scenario letter suffix, ## Summary, optional ## Gaps)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-PATTERNS.md Patterns L (frontmatter), M (top-level structure), N (sub-scenarios), O (Summary block)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md D-192 (the 4 scenarios + which sub-tests each requires)
    - playbooks/smoke_test.yml (read lines 40-60 + 119-139 + 215-225 -- the 4 asserter tasks for Loki/Prometheus/Mimir/Tempo and how smoke_trace_id / smoke_run_id are printed; the doc must reference all 4 signal types in scenario 1 evidence section)
    - playbooks/backup_docker.yml + playbooks/restore_docker.yml (just-shipped Plan 02/03 -- the doc cites their exact command lines, including the SC4 cross-cutting `--tags backup` / `--tags restore` forms)
    - MEMORY.md `project_leviathan_uat_host.md` (the inventory path is `inventory/leviathan/`, gitignored)
  </read_first>
  <action>
    Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md` with the following EXACT structure (verbatim format from 11-HUMAN-UAT.md).

    1. YAML frontmatter (Pattern L) -- starting values per Claude's Discretion choice (CONTEXT.md says either `pending` or `in_progress` is valid; pick `in_progress` per memory of v1.2.0 prior phase Rock's convention):

       `---`
       `status: in_progress`
       `phase: 14-orchestrators-leviathan-human-uat`
       `started: <today's ISO 8601 UTC at time of file creation, e.g. 2026-06-03T00:00:00Z>`
       `updated: <same as started>`
       `---`

       Omit the `source: [14-VERIFICATION.md]` key (CONTEXT.md "Pattern L" notes this is optional; Phase 14 does not ship a VERIFICATION.md so the key is unused).

    2. `## Current Test` section -- one-line bracketed status:
       `[Skeleton shipped <ISO date>. 11 sub-scenarios pending live run on leviathan.]`

    3. `## Tests` heading.

    4. Scenarios -- ALL use the literal three-line shape with NO blank lines between expected/result/detail. Each scenario/sub-scenario gets a `### N[<letter>]. <title>` heading.

       Scenario 1:
       `### 1. 7-step round-trip happy-path (UAT-V13-01)`
       `expected: 7-step round-trip on leviathan completes with no manual intervention: (step 1) ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --ask-vault-pass completes failed=0 and 11 telemetron-* containers report healthy. (step 2) ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml --ask-vault-pass completes ok=9 failed=0; PLAY OUTPUT line "trace_id:" emits a 32-char hex value; PLAY OUTPUT line "run_id:" emits an epoch seconds value; PLAY OUTPUT summary block shows "loki: ok", "prom: ok", "mimir: ok", "tempo: ok" -- ALL FOUR asserter tasks (smoke_assert_loki, smoke_assert_prometheus, smoke_assert_mimir, smoke_assert_tempo) succeeded; BOTH the trace_id and run_id values captured by operator for step 7. (step 3) ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass completes failed=0; 4 tarballs at /opt/telemetron/backups/{garage,prometheus,grafana,alertmanager}/<role>-<shared-ts>.tar.zst with mode 0600; all 4 share the same <shared-ts> (D-191 shared timestamp). (step 4) ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --ask-vault-pass --extra-vars "telemetron_purge_data=true" completes failed=0; ssh leviathan docker volume ls | grep telemetron_ returns 0 telemetron-prefixed volumes. (step 5) ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --ask-vault-pass completes failed=0; stack returns; Grafana datasource panels show EMPTY data (proves fresh post-purge state). (step 6) ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<shared-ts-from-step-3>" completes failed=0; WARN banner displays the verbatim 3-line shape with the WARNING: irreversible -- prefix; writers stop and restart in order (Loki -> Tempo -> Mimir, then docker_container_info polls confirm healthy); 4 roles restored in garage -> prometheus -> grafana -> alertmanager order; all 11 containers healthy at end. (step 7) ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml --ask-vault-pass --extra-vars "smoke_trace_id=<captured> smoke_run_id=<captured>" completes ok=9 failed=0; the 4 asserter tasks (smoke_assert_loki, smoke_assert_prometheus, smoke_assert_mimir, smoke_assert_tempo) ALL succeed against the captured identifiers -- proves the SAME OTLP log + metric + trace signals from step 2 are visible in Grafana again after restore (proves restore round-trip succeeded -- step-2 data survived the purge + restore cycle).`
       `result: pending`
       `detail: TBD -- to be populated after live UAT run. Capture the verbatim trace_id and run_id values from step 2 PLAY OUTPUT; quote them in step 7 evidence; quote PLAY RECAP lines (ok=N changed=N failed=0) for each of the 7 invocations; quote the shared-timestamp value once per scenario for cross-reference; quote each of the 4 asserter PLAY OUTPUT result lines ("loki: ok", "prom: ok", "mimir: ok", "tempo: ok") for both step 2 and step 7.`

       Scenario 2 (uses Pattern N sub-scenarios with letter suffix; expanded to 3 sub-tests per B-2 reconciliation):
       `### 2a. Orchestrator-level confirm-gate refuses default invocation without flag (OPS-V13-01 orchestrator side)`
       `expected: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass invoked WITHOUT --extra-vars backup_restore_confirm=true fails at the pre_tasks ansible.builtin.fail gate; PLAY OUTPUT contains the verbatim msg "Restore refused. Pass --extra-vars backup_restore_confirm=true to proceed."; PLAY RECAP shows failed=1 on leviathan; NO docker stop on Loki/Tempo/Mimir occurred (verifiable via ssh leviathan docker ps showing all 11 containers still running); WARN banner NOT printed (gate fires before banner).`
       `result: pending`
       `detail: TBD -- quote the verbatim fail msg from PLAY OUTPUT; quote PLAY RECAP failed=1 line; quote ssh leviathan docker ps -q | wc -l output (expect 11).`

       `### 2b. Per-role gate refuses via custom playbook bypassing orchestrator (OPS-V13-01 defence-in-depth)`
       `expected: A throwaway custom playbook contents inline below invokes include_role: name=grafana tasks_from=restore WITHOUT setting backup_restore_confirm; ansible-playbook run fails at the per-role assert/fail gate inside roles/grafana/tasks/restore.yml; PLAY RECAP failed=1; Grafana container still running. Throwaway playbook content (operator runs it via ssh + temp file or just inline -i):  - hosts: telemetron\n    tasks:\n      - include_role:\n          name: grafana\n          tasks_from: restore`
       `result: pending`
       `detail: TBD -- create the throwaway playbook, run it, capture PLAY OUTPUT failing at the per-role gate, delete the throwaway playbook after capture. Quote the per-role gate message text verbatim.`

       `### 2c. Orchestrator-level confirm-gate refuses stateless-tag invocation without flag (D-188 amended by SC4 reconciliation)`
       `expected: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --tags loki invoked WITHOUT --extra-vars backup_restore_confirm=true fails at the pre_tasks ansible.builtin.fail gate BEFORE tag-filtering. Rationale: the gate is tagged [always] so it fires under any --tags filter -- this is the playbook's identity-level safety per the D-188 amendment. PLAY OUTPUT contains the same verbatim msg "Restore refused. Pass --extra-vars backup_restore_confirm=true to proceed." and additionally references the identity-level safety contract. PLAY RECAP shows failed=1 on leviathan. NO docker stop occurred. Proves the gate is not bypassable via stateless-tag invocation.`
       `result: pending`
       `detail: TBD -- quote the verbatim fail msg from PLAY OUTPUT; quote PLAY RECAP failed=1; quote ssh leviathan docker ps -q | wc -l output (expect 11).`

       Scenario 3 (uses Pattern N sub-scenarios with letter suffix; fault-injection step is a manual instruction per Claude's-Discretion default):
       `### 3a. Default backup bails on Prometheus failure (OPS-V13-02 default)`
       `expected: Pre-step: ssh leviathan "sudo chmod 000 /opt/telemetron/backups/prometheus" (deny write access -- tar create dest will fail). Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass. Result: Garage backup succeeds (garage-<ts>.tar.zst exists at /opt/telemetron/backups/garage/). Prometheus backup fails at the tar dest write step (PLAY OUTPUT shows Permission denied). any_errors_fatal: false default flips to true (because backup_continue_on_failure default is false) -> play aborts. Grafana + Alertmanager tarballs ABSENT (their include_role never ran). PLAY RECAP failed=1 on leviathan. Cleanup: ssh leviathan "sudo chmod 0700 /opt/telemetron/backups/prometheus" to restore mode for subsequent scenarios.`
       `result: pending`
       `detail: TBD -- quote the pre-step chmod command; quote PLAY RECAP failed=1; quote ssh leviathan ls /opt/telemetron/backups/{garage,prometheus,grafana,alertmanager}/ output showing only garage has a tarball with the test timestamp; quote the cleanup chmod command and verify mode is back to 0700.`

       `### 3b. backup_continue_on_failure=true lets remaining roles run past the failure (OPS-V13-02 opt-in)`
       `expected: Pre-step: ssh leviathan "sudo chmod 000 /opt/telemetron/backups/prometheus" (same fault-injection). Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --extra-vars "backup_continue_on_failure=true". Result: PLAY-start banner shows the alternate category description "(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)". Garage SUCCEEDS. Prometheus FAILS (still the chmod block). Grafana SUCCEEDS. Alertmanager SUCCEEDS. PLAY RECAP failed=1 (Prometheus only). 3 of 4 tarballs present with the run's shared timestamp; Prometheus tarball absent. Cleanup: ssh leviathan "sudo chmod 0700 /opt/telemetron/backups/prometheus" before scenario 4.`
       `result: pending`
       `detail: TBD -- quote the alternate banner line "(all 4 roles will attempt ...)"; quote PLAY RECAP failed=1; quote ls output showing 3 of 4 tarballs present.`

       Scenario 4 (uses Pattern N sub-scenarios; expanded to 5 sub-tests per B-1 SC4 cross-cutting reconciliation):
       `### 4a. --tags garage backup produces only the garage tarball (OPS-V13-03 backup side)`
       `expected: Pre-step (clean slate): ssh leviathan to verify no /opt/telemetron/backups/<role>/ tarballs from previous scenarios remain with the same timestamp (no contamination check needed -- timestamps differ per run). Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --tags garage. Result: PLAY-start banner displays (tags: always); only the garage include_role runs; PLAY RECAP failed=0; ssh leviathan ls /opt/telemetron/backups/garage/ shows a new garage-<ts>.tar.zst; ssh leviathan ls /opt/telemetron/backups/{prometheus,grafana,alertmanager}/ shows no NEW tarball with this run's timestamp.`
       `result: pending`
       `detail: TBD -- quote the timestamp value from PLAY OUTPUT; quote ls listings showing only garage got a fresh tarball.`

       `### 4b. --tags loki restore (with confirm flag) produces empty 0-task play (D-188 amended by SC4 reconciliation)`
       `expected: Run: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --tags loki --extra-vars "backup_restore_confirm=true". Result: confirm-gate PASSES (flag set); PLAY OUTPUT shows the always-tagged confirm-gate and WARN banner fired (they are tagged [always] so they run under any --tags filter); the 4 role include_role calls and the 4 writer-quiesce tasks all carry [<role>, restore] or [garage, restore] -- none match --tags loki -- so NO role-level task runs; PLAY RECAP shows 0 role tasks executed; exit code 0; no docker stop, no docker start, no tarball read. Operator-friendly empty-result behavior that nevertheless ALWAYS requires the confirm flag (identity-level safety).`
       `result: pending`
       `detail: TBD -- quote PLAY OUTPUT confirming the WARN banner fired (proving confirm-gate passed); quote PLAY RECAP confirming 0 role-level tasks ran; document that ssh leviathan docker ps shows all 11 containers untouched.`

       `### 4c. --tags grafana restore restores only Grafana; writers untouched (OPS-V13-03 restore side; D-189 amended lock)`
       `expected: Pre-step: capture a known <ts> value from a previous successful full backup (use the scenario 1 step-3 shared-ts). Run: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>" --tags grafana. Result: confirm-gate passes (flag set); WARN banner displays (tags: always); writer-stop loop does NOT run (its tag list is [garage, restore], NEITHER matches --tags grafana per D-189 amended); writer-restart loop does NOT run; ONLY the Grafana include_role fires; PLAY RECAP failed=0; ssh leviathan docker ps confirms Loki/Tempo/Mimir/Garage stayed running throughout; Grafana container restart-cycled by the per-role restore tasks but came back healthy.`
       `result: pending`
       `detail: TBD -- quote PLAY OUTPUT; document ssh leviathan docker ps -a | grep telemetron-loki State.Started timestamp BEFORE and AFTER (must be unchanged -- writer never stopped); quote the Grafana healthcheck-healthy poll from per-role tasks.`

       `### 4d-backup. --tags backup cross-cutting backup runs all 4 stateful roles (SC4 cross-cutting backup verb)`
       `expected: Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --tags backup. Result: PLAY-start banner displays (always-tagged pre_tasks fire); shared timestamp generated once; all 4 role include_role calls execute (their tag list is [<role>, backup] so --tags backup matches each); PLAY RECAP failed=0; ssh leviathan ls /opt/telemetron/backups/{garage,prometheus,grafana,alertmanager}/ shows 4 new tarballs with the same shared timestamp suffix. Proves SC4 cross-cutting --tags backup invocation form works empirically against the live host.`
       `result: pending`
       `detail: TBD -- quote PLAY OUTPUT banner; quote PLAY RECAP failed=0; quote the shared timestamp value once; quote ls output across all 4 role dirs showing 4 fresh tarballs sharing that timestamp.`

       `### 4d-restore. --tags restore cross-cutting restore runs writer-quiesce + all 4 stateful role restores (SC4 cross-cutting restore verb)`
       `expected: Pre-step: capture a known <ts> from a recent full backup (e.g., the scenario 4d-backup output). Run: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>" --tags restore. Result: confirm-gate passes (flag set); WARN banner displays; writer-stop loop fires (its tag list is [garage, restore], --tags restore matches); writer-stop poll confirms Loki/Tempo/Mimir at State.Running == false; Garage restore fires; writer-restart loop fires; writer-restart poll confirms Loki/Tempo/Mimir at State.Health.Status == healthy; prometheus + grafana + alertmanager restores fire in that order; PLAY RECAP failed=0; ssh leviathan docker ps shows all 11 containers healthy at end. Proves SC4 cross-cutting --tags restore covers the full destructive surface (4 role restores + 4 writer-quiesce tasks) empirically against the live host.`
       `result: pending`
       `detail: TBD -- quote PLAY OUTPUT banner; quote PLAY RECAP failed=0; quote the writer-stop and writer-restart task names from PLAY OUTPUT (proves they actually fired under --tags restore); quote ssh leviathan "docker inspect -f '{{ .State.StartedAt }}' telemetron-loki" BEFORE and AFTER (writer was stopped+restarted because --tags restore IS supposed to fire the bracket); quote the shared timestamp used.`

    5. `## Summary` block (Pattern O) -- initial values:
       `total: 11`  (counting sub-scenarios: 1 + 2a + 2b + 2c + 3a + 3b + 4a + 4b + 4c + 4d-backup + 4d-restore = 11)
       `passed: 0`
       `issues: 0`
       `pending: 11`
       `skipped: 0`
       `blocked: 0`

    6. NO `## Gaps` section in the initial commit (Pattern P -- only added if defects open during UAT).

    Constraints:
    - English-only.
    - VERBATIM `WARNING: irreversible --` prefix mentioned in scenario 1 step 6 expected (this is the grep target).
    - Scenario 1 expected/detail MUST reference all 4 signal types (log + metric + trace) and explicitly name the 4 asserter tasks (smoke_assert_loki, smoke_assert_prometheus, smoke_assert_mimir, smoke_assert_tempo). smoke_test.yml verifies Loki at lines 119-139 and prints "loki: ok" in the summary -- this is the explicit Loki visibility check that proves the log signal round-tripped.
    - Use `inventory/leviathan` (NOT `inventory/example-homelab`) in every example command -- the live UAT runs on leviathan per Rock's setup.
    - Do NOT add `inventory/leviathan/` to the repo (gitignored per memory `project_leviathan_uat_host.md`).
    - Frontmatter dates use `YYYY-MM-DDTHH:MM:SSZ` ISO 8601 format with a literal `Z` suffix (matches 11-HUMAN-UAT.md frontmatter).
    - The `detail:` lines all start with `TBD` -- Task 2 (live UAT) flips them.
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md
        test -s "$F"
        # Frontmatter
        head -1 "$F" | grep -q "^---$"
        grep -q "^status: in_progress" "$F"
        grep -q "^phase: 14-orchestrators-leviathan-human-uat" "$F"
        grep -q "^started:" "$F"
        grep -q "^updated:" "$F"
        # Top-level structure
        grep -q "^## Current Test" "$F"
        grep -q "^## Tests" "$F"
        grep -q "^## Summary" "$F"
        # All 11 scenarios/sub-scenarios present
        grep -q "^### 1\\. " "$F"
        grep -q "^### 2a\\. " "$F"
        grep -q "^### 2b\\. " "$F"
        grep -q "^### 2c\\. " "$F"
        grep -q "^### 3a\\. " "$F"
        grep -q "^### 3b\\. " "$F"
        grep -q "^### 4a\\. " "$F"
        grep -q "^### 4b\\. " "$F"
        grep -q "^### 4c\\. " "$F"
        grep -q "^### 4d-backup\\. " "$F"
        grep -q "^### 4d-restore\\. " "$F"
        # Each scenario has the three-line shape -- count expected:/result:/detail: lines (must be 11 each)
        test "$(grep -c "^expected: " "$F")" -eq 11
        test "$(grep -c "^result: " "$F")" -eq 11
        test "$(grep -c "^detail: " "$F")" -eq 11
        # All results pending at skeleton-commit time
        test "$(grep -c "^result: pending" "$F")" -eq 11
        # Inventory path: inventory/leviathan referenced (W-5: use conventional if/then negation form)
        grep -q "inventory/leviathan" "$F"
        if grep -q "inventory/example-homelab" "$F"; then echo "FAIL: HUMAN-UAT must reference inventory/leviathan, not example-homelab"; exit 1; fi
        # Verbatim WARNING prefix mention
        grep -q "WARNING: irreversible --" "$F"
        # Requirements cited in scenario titles
        grep -q "UAT-V13-01" "$F"
        grep -q "OPS-V13-01" "$F"
        grep -q "OPS-V13-02" "$F"
        grep -q "OPS-V13-03" "$F"
        # SC4 cross-cutting verbs cited in 4d-backup and 4d-restore titles
        grep -q "SC4 cross-cutting backup verb" "$F"
        grep -q "SC4 cross-cutting restore verb" "$F"
        # Scenario 1 explicitly names the 4 asserter tasks AND the 4 OTLP-signal status lines (proves log + metric + trace coverage; B-3 reconciliation)
        grep -q "smoke_assert_loki" "$F"
        grep -q "smoke_assert_prometheus" "$F"
        grep -q "smoke_assert_mimir" "$F"
        grep -q "smoke_assert_tempo" "$F"
        grep -q "loki: ok" "$F"
        grep -q "tempo: ok" "$F"
        # D-188 amended reference present (scenario 2c + 4b)
        grep -q "D-188 amended" "$F"
        # Summary initial counts
        grep -q "^total: 11" "$F"
        grep -q "^passed: 0" "$F"
        grep -q "^pending: 11" "$F"
        echo "PASS: 14-HUMAN-UAT.md skeleton matches required shape"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md` exists, is non-empty, valid markdown.
    - Frontmatter contains `status: in_progress`, `phase: 14-orchestrators-leviathan-human-uat`, `started:` (ISO 8601 with Z suffix), `updated:` (same value).
    - Has `## Current Test` heading (with a one-line bracketed status line).
    - Has `## Tests` heading.
    - Has 11 numbered scenario headings: `### 1.`, `### 2a.`, `### 2b.`, `### 2c.`, `### 3a.`, `### 3b.`, `### 4a.`, `### 4b.`, `### 4c.`, `### 4d-backup.`, `### 4d-restore.`.
    - Each scenario has the three-line `expected:` + `result:` + `detail:` shape with NO blank lines between them.
    - Total: 11 `expected:` lines, 11 `result:` lines, 11 `detail:` lines.
    - All 11 `result:` values are `pending` at skeleton time.
    - Every example command line references `inventory/leviathan` (NOT `inventory/example-homelab`); enforcement uses the conventional `if grep -q ...; then echo FAIL; exit 1; fi` form (W-5).
    - The verbatim string `WARNING: irreversible --` appears at least once (in scenario 1 step 6 expected, as a grep-test for the restore banner).
    - Scenario titles cite the relevant requirement IDs: UAT-V13-01 (scenario 1), OPS-V13-01 (scenarios 2a + 2b + 2c), OPS-V13-02 (scenarios 3a + 3b), OPS-V13-03 (scenarios 4a + 4c at least). Scenarios 4d-backup and 4d-restore cite "SC4 cross-cutting backup verb" / "SC4 cross-cutting restore verb" in their titles.
    - Scenario 1 explicitly references the 4 asserter task names (smoke_assert_loki, smoke_assert_prometheus, smoke_assert_mimir, smoke_assert_tempo) and the 4 OTLP-signal status lines from smoke_test.yml ("loki: ok", "prom: ok", "mimir: ok", "tempo: ok") proving the log + metric + trace coverage claim (B-3 reconciliation: smoke_test.yml DOES query Loki at lines 119-139, so the log signal is verified end-to-end).
    - Scenario 2c and Scenario 4b explicitly reference "D-188 amended" -- proving the SC4 reconciliation contract is documented in the audit doc.
    - `## Summary` block has `total: 11`, `passed: 0`, `pending: 11`, `issues: 0`, `skipped: 0`, `blocked: 0`.
    - NO `## Gaps` section at skeleton time.
    - NO `inventory/leviathan/` directory is created or committed.
  </acceptance_criteria>
  <done>
    Skeleton of `14-HUMAN-UAT.md` is committed. The audit doc has 11 sub-scenarios at `result: pending` ready for Task 2 (live UAT execution) to flip results to `pass` and replace `TBD` detail with verbatim PLAY OUTPUT excerpts. Format matches 11-HUMAN-UAT.md verbatim. Scenarios 2c, 4b, 4d-backup, 4d-restore are the new B-1 / B-2 SC4-reconciliation sub-scenarios that prove the cross-cutting tag claims AND the D-188 identity-level safety amendment empirically. Scenario 1 evidence section references all 4 OTLP signal asserters (log via Loki, metric via Prometheus + Mimir, trace via Tempo) proving end-to-end round-trip across all 4 signal types. inventory/leviathan referenced in commands but not added to repo.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Execute live UAT round-trip on leviathan and flip 14-HUMAN-UAT.md results to pass</name>
  <files>.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md</files>
  <read_first>
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md (the skeleton just shipped in Task 1)
    - playbooks/backup_docker.yml + playbooks/restore_docker.yml (Plan 02/03 output -- the orchestrators under test)
    - playbooks/smoke_test.yml lines 40-60 + 119-139 + 215-225 (smoke_trace_id and smoke_run_id mechanics; Loki + Prometheus + Mimir + Tempo asserter tasks)
    - MEMORY.md `project_leviathan_uat_host.md` (leviathan is the UAT host; ssh passwordless; Docker 29; inventory/leviathan/ gitignored and present on workstation)
  </read_first>
  <what-built>
    Plans 01/02/03 shipped the 4 amended tasks/backup.yml files + backup_docker.yml + restore_docker.yml (with the SC4 cross-cutting `[backup]` / `[restore]` tag amendments and the D-188 identity-level confirm-gate amendment). Task 1 of this plan shipped the 14-HUMAN-UAT.md skeleton with 11 sub-scenarios at result: pending. This checkpoint task executes the live UAT against leviathan to flip results to pass (or fail and open a ## Gaps section).
  </what-built>
  <how-to-verify>
    LEVIATHAN PRE-FLIGHT (mandatory first step per W-4): Run `ssh -o BatchMode=yes -o ConnectTimeout=5 leviathan true` first. If non-zero exit, ABORT the task and surface to the developer with the explicit message: "leviathan unreachable -- fix host connectivity before running HUMAN-UAT". Do NOT leave the task in `in_progress` indefinitely; return control to the developer immediately so they can investigate (DNS, SSH key, host down, etc.) before re-invoking the checkpoint.

    Only proceed past the pre-flight if it succeeded.

    Execute the 11 sub-scenarios sequentially against leviathan. For each sub-scenario:

    1. Run the command(s) documented in the scenario `expected:` line via passwordless SSH or via ansible-playbook from the workstation against `inventory/leviathan/`.
    2. Capture PLAY RECAP + relevant PLAY OUTPUT lines into a temp note.
    3. Edit `14-HUMAN-UAT.md`: change `result: pending` to `result: pass` (or `result: fail` if a defect surfaces); replace `detail: TBD ...` with a one-sentence summary followed by quoted PLAY RECAP and key evidence lines.
    4. Save and verify the doc still parses (no broken markdown).

    Scenario-specific notes for the human running the UAT:

    - Scenario 1 (the round-trip): step 2 PLAY OUTPUT will print `trace_id: <32-hex>` and `run_id: <epoch>` from smoke_test.yml's summary block (lines 219-220). The summary block (lines 218-224) also prints `loki: ok`, `prom: ok`, `mimir: ok`, `tempo: ok` -- proving all 4 asserter tasks succeeded. Capture all 6 lines. Step 3 PLAY OUTPUT will show the shared timestamp in each tarball filename (`/opt/telemetron/backups/<role>/<role>-YYYYMMDDTHHMMSSZ.tar.zst`). Capture the shared <ts>. Step 6 passes the captured <ts> via `backup_restore_from=<ts>`. Step 7 passes the captured smoke_trace_id and smoke_run_id via `--extra-vars` AND must again show all 4 asserter results as `ok` (proves the SAME log, metric, and trace signals re-emerged after restore).

    - Scenario 2a/2b/2c: 2a runs the orchestrator without confirm flag in default form (fast -- gate fires immediately). 2c runs the orchestrator without confirm flag in stateless-tag form (`--tags loki` WITHOUT confirm) -- proves the gate is identity-level (fires before tag-filtering). 2b requires a 4-line throwaway playbook (operator can use `ansible-playbook -i inventory/leviathan /tmp/restore-grafana-only.yml --ask-vault-pass` against a temp file containing `- hosts: telemetron\n  tasks:\n    - include_role:\n        name: grafana\n        tasks_from: restore`); delete the temp file after capture.

    - Scenario 3a/3b: pre-step `ssh leviathan "sudo chmod 000 /opt/telemetron/backups/prometheus"` to inject the fault. Cleanup `ssh leviathan "sudo chmod 0700 /opt/telemetron/backups/prometheus"` after EACH sub-scenario (not just at the end -- subsequent scenarios may need the dir writable). Capture chmod output for both pre and cleanup steps.

    - Scenario 4a: run `--tags garage` invocation; ssh check to confirm only garage tarball touched (cite specific ls output).

    - Scenario 4b: run `--tags loki --extra-vars "backup_restore_confirm=true"` invocation; verify PLAY OUTPUT shows the WARN banner fired (proving the confirm-gate passed) and PLAY RECAP shows no role tasks executed (the role include_role calls and writer-quiesce tasks all carry `[<role>, restore]` or `[garage, restore]` -- none match `--tags loki`); exit 0.

    - Scenario 4c: run `--tags grafana --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>"`; before the run, capture `ssh leviathan "docker inspect -f '{{ "{{" }} .State.StartedAt {{ "}}" }}' telemetron-loki"`; after the run, capture the same; values MUST be identical (writer was not stopped -- writer-stop tag list is `[garage, restore]`, `grafana` does not match).

    - Scenario 4d-backup: run `--tags backup` invocation; PLAY RECAP shows all 4 role include_role tasks ran; ssh leviathan ls confirms 4 fresh tarballs share one timestamp.

    - Scenario 4d-restore: run `--tags restore --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>"`; before the run, capture `ssh leviathan "docker inspect -f '{{ "{{" }} .State.StartedAt {{ "}}" }}' telemetron-loki"`; after the run, capture the same; values MUST DIFFER (writer-stop tag list IS `[garage, restore]`, `--tags restore` MATCHES, so writer was stopped+restarted). Also confirm prometheus/grafana/alertmanager restores ran.

    After all 11 sub-scenarios:
    - Edit frontmatter: `status: complete`, update `updated:` to the latest ISO timestamp.
    - Edit `## Current Test`: replace the skeleton bracketed message with a one-line "Round N complete <date>. All 11 sub-scenarios pass on leviathan." (mirror the 11-HUMAN-UAT.md phrasing).
    - Edit `## Summary`: `passed: 11`, `pending: 0`.
    - If ANY sub-scenario fails: leave its result as `result: fail`; open a `## Gaps` section with a `### G-XX:` block per Pattern P (status, manifests-in, fix-plan); flag for follow-up work.

    Verification gates the orchestrator/human will use:
    - File contains `status: complete` in frontmatter.
    - 0 occurrences of `^result: pending`.
    - 0 occurrences of `^detail: TBD`.
    - At least 11 occurrences of `^result: pass` (or fewer if any sub-scenario failed -- then ## Gaps section is required).
    - `## Summary` has `passed: 11` (or N where N < 11 plus `issues: M` matching the failed count).
    - smoke_trace_id and smoke_run_id values appear in BOTH scenario 1 step 2 evidence AND step 7 evidence (proves the same identifiers were re-passed).
    - The 4 asserter status lines ("loki: ok", "prom: ok", "mimir: ok", "tempo: ok") appear in BOTH scenario 1 step 2 evidence AND step 7 evidence (proves all 4 OTLP signal types round-tripped).
    - At least one tarball path with the round's shared timestamp appears in scenario 1 step 3 evidence.
    - Scenario 4d-backup evidence quotes a single shared timestamp across all 4 role tarballs.
    - Scenario 4d-restore evidence quotes BOTH a BEFORE and AFTER `State.StartedAt` for telemetron-loki proving the writer was actually stopped+restarted.

    Issue/blocker handling:
    - If the leviathan pre-flight fails (W-4): abort, surface to developer, do NOT leave the task hanging.
    - If leviathan becomes unreachable mid-run: leave `status: in_progress`; note the partial state in `## Current Test`; flag for resume.
    - If a Phase 13 per-role gate misbehaves (e.g., scenario 2b's per-role gate does not fire): open `## Gaps` with G-XX entry; the FIX-PLAN is a follow-up plan in this phase OR a Phase 13 amendment plan -- planner will route depending on which layer is at fault.
  </how-to-verify>
  <resume-signal>
    Type "approved" if all 11 sub-scenarios pass and the doc is updated (status: complete, 0 pending, summary updated). Otherwise describe which sub-scenarios failed and whether a Gaps section was opened.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator workstation -> leviathan via SSH | Passwordless SSH per Rock's setup; leviathan is the live production-like UAT host. The fault-injection in scenario 3 modifies its filesystem (chmod 000). |
| Scenario 3 fault-injection state -> subsequent scenarios | If the chmod cleanup is forgotten, scenario 4 may inherit broken state. Mitigated by requiring per-sub-scenario cleanup. |
| Pre-flight skipped -> task hangs indefinitely | W-4 mitigation: explicit `ssh -o BatchMode=yes -o ConnectTimeout=5 leviathan true` at start of Task 2 with explicit abort + developer surface on failure. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-13 (T5) | Denial of Service | Forgotten `chmod 0700` cleanup after scenario 3a leaves /opt/telemetron/backups/prometheus inaccessible to subsequent runs | mitigate | The doc's scenario 3a + 3b `detail:` explicitly require quoting BOTH the pre-step chmod AND the cleanup chmod. The UAT checkpoint task instructions explicitly call out per-sub-scenario cleanup. |
| T-14-14 | Repudiation | Scenario 1 step 2's smoke_trace_id / smoke_run_id values not captured -> step 7 cannot prove the round-trip | mitigate | The UAT checkpoint instructions call out the capture explicitly; the acceptance grep requires both values to appear in BOTH step 2 evidence and step 7 evidence (operator cannot satisfy the grep without quoting both). Additionally, the 4 asserter status lines must appear in both step 2 and step 7 evidence (proves all 4 signal types round-tripped). |
| T-14-15 (T2) | Tampering | Scenario 1 step 6 restore is destructive; if it runs against the wrong inventory (workstation instead of leviathan), real data is lost | accept | inventory/leviathan is gitignored and only resolvable from Rock's workstation; the orchestrator confirm-gate provides defence-in-depth. Operator-controlled risk. ASVS L1. |
| T-14-16 | Repudiation | Scenario 4c writer-untouched evidence relies on docker inspect StartedAt -- if the operator forgets the BEFORE capture, the proof is unverifiable | mitigate | The UAT checkpoint task explicitly calls out the BEFORE + AFTER capture sequence. If only AFTER is captured, the scenario CANNOT be marked pass; it must remain pending or be re-run. |
| T-14-17 | Denial of Service | Task 2 hangs because leviathan is unreachable but the operator does not notice | mitigate | W-4 -- the `ssh -o BatchMode=yes -o ConnectTimeout=5 leviathan true` pre-flight at the start of `<how-to-verify>` aborts within 5 seconds on connectivity failure and explicitly surfaces to the developer. No silent hang. |
</threat_model>

<verification>
- Task 1 verification is fully automated (file shape + grep gates).
- Task 2 verification is by checkpoint -- live UAT involves running playbooks against leviathan, which Claude can do via passwordless SSH but the operator confirms results before flipping status to complete. The W-4 pre-flight ensures the task does not silently hang on connectivity failure.
- The audit doc itself IS the verification artifact for UAT-V13-01.
</verification>

<success_criteria>
- UAT-V13-01: After Task 2 completes successfully, `14-HUMAN-UAT.md` has `status: complete` in frontmatter, all 11 sub-scenarios show `result: pass`, scenario 1's evidence section quotes the verbatim trace_id + run_id appearing in both step 2 and step 7 PLAY OUTPUT excerpts (proves the round-trip preserves OTLP signal identity end-to-end across log + metric + trace), scenario 1's evidence quotes "loki: ok / prom: ok / mimir: ok / tempo: ok" appearing in both step 2 and step 7 (proves all 4 signal types round-trip), scenario 1's evidence quotes the shared timestamp value appearing in all 4 tarball filenames (proves D-191 shared-timestamp behavior), and `## Summary` shows `passed: 11` and `pending: 0`.
- B-1 reconciliation: Scenario 4d-backup and 4d-restore evidence prove the SC4 cross-cutting `--tags backup` / `--tags restore` claim empirically on leviathan.
- B-2 reconciliation: Scenario 2c evidence proves the D-188 identity-level confirm-gate amendment empirically on leviathan.
- If any sub-scenario fails: `## Gaps` section is opened with one `### G-XX:` block per defect documenting status/manifests-in/fix-plan; planner is informed via the checkpoint resume signal so a follow-up gap-closure plan can be created.
</success_criteria>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-04-SUMMARY.md` when done. The SUMMARY captures: which sub-scenarios passed, evidence of the shared-timestamp behavior and the trace_id round-trip across all 4 signal types, evidence of the SC4 cross-cutting tag claims (4d-backup + 4d-restore), evidence of the D-188 identity-level amendment (2c), and any opened gaps. The 14-HUMAN-UAT.md doc is the primary deliverable; the SUMMARY is the meta-summary feeding into v1.3.0 milestone close.
</output>
