---
status: in_progress
phase: 14-orchestrators-leviathan-human-uat
started: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
---

## Current Test

[Skeleton shipped 2026-06-04. 11 sub-scenarios pending live run on leviathan.]

## Tests

### 1. 7-step round-trip happy-path (UAT-V13-01)
expected: 7-step round-trip on leviathan completes with no manual intervention: (step 1) ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --ask-vault-pass completes failed=0 and 11 telemetron-* containers report healthy. (step 2) ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml --ask-vault-pass completes ok=9 failed=0; PLAY OUTPUT line "trace_id:" emits a 32-char hex value; PLAY OUTPUT line "run_id:" emits an epoch seconds value; PLAY OUTPUT summary block shows "loki: ok", "prom: ok", "mimir: ok", "tempo: ok" -- ALL FOUR asserter tasks (smoke_assert_loki, smoke_assert_prometheus, smoke_assert_mimir, smoke_assert_tempo) succeeded; BOTH the trace_id and run_id values captured by operator for step 7. (step 3) ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass completes failed=0; 4 tarballs at /opt/telemetron/backups/{garage,prometheus,grafana,alertmanager}/<role>-<shared-ts>.tar.zst with mode 0600; all 4 share the same <shared-ts> (D-191 shared timestamp). (step 4) ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --ask-vault-pass --extra-vars "telemetron_purge_data=true" completes failed=0; ssh leviathan docker volume ls | grep telemetron_ returns 0 telemetron-prefixed volumes. (step 5) ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --ask-vault-pass completes failed=0; stack returns; Grafana datasource panels show EMPTY data (proves fresh post-purge state). (step 6) ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<shared-ts-from-step-3>" completes failed=0; WARN banner displays the verbatim 3-line shape with the WARNING: irreversible -- prefix; writers stop and restart in order (Loki -> Tempo -> Mimir, then docker_container_info polls confirm healthy); 4 roles restored in garage -> prometheus -> grafana -> alertmanager order; all 11 containers healthy at end. (step 7) ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml --ask-vault-pass --extra-vars "smoke_trace_id=<captured> smoke_run_id=<captured>" completes ok=9 failed=0; the 4 asserter tasks (smoke_assert_loki, smoke_assert_prometheus, smoke_assert_mimir, smoke_assert_tempo) ALL succeed against the captured identifiers; PLAY OUTPUT summary block shows "loki: ok", "prom: ok", "mimir: ok", "tempo: ok" -- proves the SAME OTLP log + metric + trace signals from step 2 are visible in Grafana again after restore (proves restore round-trip succeeded -- step-2 data survived the purge + restore cycle).
result: pending
detail: TBD -- to be populated after live UAT run. Capture the verbatim trace_id and run_id values from step 2 PLAY OUTPUT; quote them in step 7 evidence; quote PLAY RECAP lines (ok=N changed=N failed=0) for each of the 7 invocations; quote the shared-timestamp value once per scenario for cross-reference; quote each of the 4 asserter PLAY OUTPUT result lines ("loki: ok", "prom: ok", "mimir: ok", "tempo: ok") for both step 2 and step 7.

### 2a. Orchestrator-level confirm-gate refuses default invocation without flag (OPS-V13-01 orchestrator side)
expected: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass invoked WITHOUT --extra-vars backup_restore_confirm=true fails at the pre_tasks ansible.builtin.fail gate; PLAY OUTPUT contains the verbatim msg "Restore refused. Pass --extra-vars backup_restore_confirm=true to proceed."; PLAY RECAP shows failed=1 on leviathan; NO docker stop on Loki/Tempo/Mimir occurred (verifiable via ssh leviathan docker ps showing all 11 containers still running); WARN banner NOT printed (gate fires before banner).
result: pending
detail: TBD -- quote the verbatim fail msg from PLAY OUTPUT; quote PLAY RECAP failed=1 line; quote ssh leviathan docker ps -q | wc -l output (expect 11).

### 2b. Per-role gate refuses via custom playbook bypassing orchestrator (OPS-V13-01 defence-in-depth)
expected: A throwaway custom playbook invokes include_role: name=grafana tasks_from=restore WITHOUT setting backup_restore_confirm; ansible-playbook run fails at the per-role assert/fail gate inside roles/grafana/tasks/restore.yml; PLAY RECAP failed=1; Grafana container still running. Throwaway playbook content (operator runs via temp file: ansible-playbook -i inventory/leviathan /tmp/restore-grafana-only.yml --ask-vault-pass): `- hosts: telemetron\n  tasks:\n    - include_role:\n        name: grafana\n        tasks_from: restore`.
result: pending
detail: TBD -- create the throwaway playbook, run it, capture PLAY OUTPUT failing at the per-role gate, delete the throwaway playbook after capture. Quote the per-role gate message text verbatim.

### 2c. Orchestrator-level confirm-gate refuses stateless-tag invocation without flag (D-188 amended by SC4 reconciliation)
expected: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --tags loki invoked WITHOUT --extra-vars backup_restore_confirm=true fails at the pre_tasks ansible.builtin.fail gate BEFORE tag-filtering. Rationale: the gate is tagged [always] so it fires under any --tags filter -- this is the playbook's identity-level safety per the D-188 amended contract. PLAY OUTPUT contains the same verbatim msg "Restore refused. Pass --extra-vars backup_restore_confirm=true to proceed." and additionally references the identity-level safety contract. PLAY RECAP shows failed=1 on leviathan. NO docker stop occurred. Proves the gate is not bypassable via stateless-tag invocation.
result: pending
detail: TBD -- quote the verbatim fail msg from PLAY OUTPUT; quote PLAY RECAP failed=1; quote ssh leviathan docker ps -q | wc -l output (expect 11).

### 3a. Default backup bails on Prometheus failure (OPS-V13-02 default)
expected: Pre-step: ssh leviathan "sudo chmod 000 /opt/telemetron/backups/prometheus" (deny write access -- tar create dest will fail). Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass. Result: Garage backup succeeds (garage-<ts>.tar.zst exists at /opt/telemetron/backups/garage/). Prometheus backup fails at the tar dest write step (PLAY OUTPUT shows Permission denied). any_errors_fatal: false default flips to true (because backup_continue_on_failure default is false) -> play aborts. Grafana + Alertmanager tarballs ABSENT (their include_role never ran). PLAY RECAP failed=1 on leviathan. Cleanup: ssh leviathan "sudo chmod 0700 /opt/telemetron/backups/prometheus" to restore mode for subsequent scenarios.
result: pending
detail: TBD -- quote the pre-step chmod command; quote PLAY RECAP failed=1; quote ssh leviathan ls /opt/telemetron/backups/{garage,prometheus,grafana,alertmanager}/ output showing only garage has a tarball with the test timestamp; quote the cleanup chmod command and verify mode is back to 0700.

### 3b. backup_continue_on_failure=true lets remaining roles run past the failure (OPS-V13-02 opt-in)
expected: Pre-step: ssh leviathan "sudo chmod 000 /opt/telemetron/backups/prometheus" (same fault-injection). Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --extra-vars "backup_continue_on_failure=true". Result: PLAY-start banner shows the alternate category description "(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)". Garage SUCCEEDS. Prometheus FAILS (still the chmod block). Grafana SUCCEEDS. Alertmanager SUCCEEDS. PLAY RECAP failed=1 (Prometheus only). 3 of 4 tarballs present with the run's shared timestamp; Prometheus tarball absent. Cleanup: ssh leviathan "sudo chmod 0700 /opt/telemetron/backups/prometheus" before scenario 4.
result: pending
detail: TBD -- quote the alternate banner line "(all 4 roles will attempt ...)"; quote PLAY RECAP failed=1; quote ls output showing 3 of 4 tarballs present.

### 4a. --tags garage backup produces only the garage tarball (OPS-V13-03 backup side)
expected: Pre-step (clean slate): ssh leviathan to verify no /opt/telemetron/backups/<role>/ tarballs from previous scenarios remain with the same timestamp (no contamination check needed -- timestamps differ per run). Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --tags garage. Result: PLAY-start banner displays (tags: always); only the garage include_role runs; PLAY RECAP failed=0; ssh leviathan ls /opt/telemetron/backups/garage/ shows a new garage-<ts>.tar.zst; ssh leviathan ls /opt/telemetron/backups/{prometheus,grafana,alertmanager}/ shows no NEW tarball with this run's timestamp.
result: pending
detail: TBD -- quote the timestamp value from PLAY OUTPUT; quote ls listings showing only garage got a fresh tarball.

### 4b. --tags loki restore (with confirm flag) produces empty 0-task play (D-188 amended by SC4 reconciliation)
expected: Run: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --tags loki --extra-vars "backup_restore_confirm=true". Result: confirm-gate PASSES (flag set); PLAY OUTPUT shows the always-tagged confirm-gate and WARN banner fired (they are tagged [always] so they run under any --tags filter); the 4 role include_role calls and the 4 writer-quiesce tasks all carry [<role>, restore] or [garage, restore] -- none match --tags loki -- so NO role-level task runs; PLAY RECAP shows 0 role tasks executed; exit code 0; no docker stop, no docker start, no tarball read. Operator-friendly empty-result behavior that nevertheless ALWAYS requires the confirm flag (identity-level safety).
result: pending
detail: TBD -- quote PLAY OUTPUT confirming the WARN banner fired (proving confirm-gate passed); quote PLAY RECAP confirming 0 role-level tasks ran; document that ssh leviathan docker ps shows all 11 containers untouched.

### 4c. --tags grafana restore restores only Grafana; writers untouched (OPS-V13-03 restore side; D-189 amended lock)
expected: Pre-step: capture a known <ts> value from a previous successful full backup (use the scenario 1 step-3 shared-ts). Run: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>" --tags grafana. Result: confirm-gate passes (flag set); WARN banner displays (tags: always); writer-stop loop does NOT run (its tag list is [garage, restore], NEITHER matches --tags grafana per D-189 amended); writer-restart loop does NOT run; ONLY the Grafana include_role fires; PLAY RECAP failed=0; ssh leviathan docker ps confirms Loki/Tempo/Mimir/Garage stayed running throughout; Grafana container restart-cycled by the per-role restore tasks but came back healthy.
result: pending
detail: TBD -- quote PLAY OUTPUT; document ssh leviathan docker ps -a | grep telemetron-loki State.Started timestamp BEFORE and AFTER (must be unchanged -- writer never stopped); quote the Grafana healthcheck-healthy poll from per-role tasks.

### 4d-backup. --tags backup cross-cutting backup runs all 4 stateful roles (SC4 cross-cutting backup verb)
expected: Run: ansible-playbook -i inventory/leviathan playbooks/backup_docker.yml --ask-vault-pass --tags backup. Result: PLAY-start banner displays (always-tagged pre_tasks fire); shared timestamp generated once; all 4 role include_role calls execute (their tag list is [<role>, backup] so --tags backup matches each); PLAY RECAP failed=0; ssh leviathan ls /opt/telemetron/backups/{garage,prometheus,grafana,alertmanager}/ shows 4 new tarballs with the same shared timestamp suffix. Proves SC4 cross-cutting --tags backup invocation form works empirically against the live host.
result: pending
detail: TBD -- quote PLAY OUTPUT banner; quote PLAY RECAP failed=0; quote the shared timestamp value once; quote ls output across all 4 role dirs showing 4 fresh tarballs sharing that timestamp.

### 4d-restore. --tags restore cross-cutting restore runs writer-quiesce + all 4 stateful role restores (SC4 cross-cutting restore verb)
expected: Pre-step: capture a known <ts> from a recent full backup (e.g., the scenario 4d-backup output). Run: ansible-playbook -i inventory/leviathan playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true backup_restore_from=<ts>" --tags restore. Result: confirm-gate passes (flag set); WARN banner displays; writer-stop loop fires (its tag list is [garage, restore], --tags restore matches); writer-stop poll confirms Loki/Tempo/Mimir at State.Running == false; Garage restore fires; writer-restart loop fires; writer-restart poll confirms Loki/Tempo/Mimir at State.Health.Status == healthy; prometheus + grafana + alertmanager restores fire in that order; PLAY RECAP failed=0; ssh leviathan docker ps shows all 11 containers healthy at end. Proves SC4 cross-cutting --tags restore covers the full destructive surface (4 role restores + 4 writer-quiesce tasks) empirically against the live host.
result: pending
detail: TBD -- quote PLAY OUTPUT banner; quote PLAY RECAP failed=0; quote the writer-stop and writer-restart task names from PLAY OUTPUT (proves they actually fired under --tags restore); quote ssh leviathan "docker inspect -f '{{ .State.StartedAt }}' telemetron-loki" BEFORE and AFTER (writer was stopped+restarted because --tags restore IS supposed to fire the bracket); quote the shared timestamp used.

## Summary

total: 11
passed: 0
issues: 0
pending: 11
skipped: 0
blocked: 0
