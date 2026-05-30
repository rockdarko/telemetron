---
status: partial
phase: 11-undeploy-orchestrator-safety-idempotency
source: [11-VERIFICATION.md]
started: 2026-05-29T00:00:00Z
updated: 2026-05-30T03:35:00Z
---

## Current Test

[all scenarios executed; results below]

## Tests

### 1. Conservative undeploy + redeploy (OPS-02 happy path; D-146 recovery proof)
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` completes with `failed=0` and no purge flags set; named volumes `telemetron_*_data` survive -- `docker volume ls | grep telemetron_` shows all 11 telemetron-prefixed volumes intact (alertmanager, fluentbit_buffer, garage_meta + garage_data, grafana, loki, mimir, prometheus, tempo); immediate redeploy via `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml` succeeds; `ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml` round-trip passes within 60s (OPS-07 acceptance); Grafana panels show OLD pre-undeploy log/metric/trace data (proves D-146 recovery: Garage regenerated S3 key on the orphan, Loki/Tempo/Mimir kept their old buckets via bucket allow re-grant in bootstrap.yml lines 188-223)
result: fail
detail: Undeploy itself succeeds cleanly (ok=37 changed=23 failed=0; containers and network gone; 9 telemetron_* named volumes preserved). Redeploy aborts at `garage : Allow S3 key on Garage buckets` with `Error: GetKeyInfo returned InvalidRequest (400): Bad request: 2 matching keys`. Root cause: garage uninstall.yml removes `/opt/telemetron/garage/s3-credentials` (as designed), but the `telemetron_garage_meta` volume is preserved (also as designed by D-141). On redeploy, bootstrap.yml creates a NEW `telemetron` key without checking whether one already exists in the preserved metadata, producing two keys with the same name -- `key info telemetron` becomes ambiguous. Workaround for UAT: `docker exec telemetron-garage /garage key delete --yes <OLD_KEY_ID>` then re-run deploy. NOT a Phase 11 defect (orchestrator just invokes the existing Phase 10 garage uninstall.yml). See ## Gaps for the cross-phase fix recommendation.

### 2. Back-to-back undeploy idempotency (OPS-01)
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` run twice in a row; second-run PLAY RECAP shows `changed=0` (every state=absent task already converged per D-141); `failed=0` in both runs
result: pass
detail: Run 1: ok=37 changed=23 failed=0. Run 2: ok=37 changed=0 failed=0. Perfect idempotency.

### 3. Partial-deploy idempotency simulation (D-164)
expected: with the stack running on leviathan, manually `ssh leviathan docker rm -f telemetron-fluentbit telemetron-opentelemetry telemetron-alertmanager`; then run `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml`; PLAY RECAP `failed=0`; pre-removed containers stay removed (no spurious `changed=true` on them since state=absent on a missing container is a no-op); remaining 9 containers (or 10 if nfsd enabled) cleanly removed; tests Ansible state=absent idempotency against arbitrary host state, not just clean or fully-deployed
result: pass
detail: Setup: removed fluentbit + opentelemetry + alertmanager (stack went 11 -> 8). Undeploy: ok=37 changed=20 failed=0. changed=20 (vs 23 for full undeploy) -- exactly 3 fewer, matching the 3 pre-removed containers (state=absent no-op on missing).

### 4a. telemetron_purge_data=true + redeploy
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --extra-vars "telemetron_purge_data=true"`; PLAY-start banner shows `telemetron_purge_data=True` with category description "all telemetron_* named Docker volumes will be removed" (D-160); PLAY OUTPUT shows `WARNING: irreversible -- <role> purge_data: <volume-name>` for every role with a volume (alertmanager, fluentbit, garage [comma-separated meta + data], grafana, loki, mimir, prometheus, tempo = 8 WARN lines); `docker volume ls | grep telemetron_` returns 0 telemetron-prefixed volumes after purge; redeploy via `playbooks/deploy_docker.yml` succeeds; `playbooks/smoke_test.yml` after redeploy shows EMPTY datasource panels (proves fresh-bucket state -- old data wiped); `failed=0` throughout
result: pass
detail: D-160 PLAY-start banner displays all 3 flag states with category descriptions verbatim. 8 WARN lines emitted (garage comma-joins meta+data on one line). Idempotency on second run: changed=0 failed=0. Post-purge: 0 telemetron_* volumes remain (only `telemetron_minio_data` v1.0.0 leftover, out of scope). Redeploy (fresh metadata = no orphan key issue): ok=148 changed=64 failed=0. Smoke test: ok=9 failed=0.

### 4b. telemetron_purge_host_dirs=true + redeploy
expected: `--extra-vars "telemetron_purge_host_dirs=true"`; PLAY OUTPUT shows `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)` (D-159 single-line); `ssh leviathan ls /opt/telemetron 2>&1` returns "No such file or directory" after purge (per D-155 parent-only rmdir at orchestrator post_tasks); redeploy recreates the tree from scratch (every role's config dir bind-mount re-renders Gate 8 parent-dir mount cleanly); Garage S3 credentials file at `/opt/telemetron/garage/s3-credentials` specifically destroyed (PURGE-02 SC-5 explicit requirement); `failed=0`
result: skipped
detail: Skipped per user choice -- would hit same recovery bug as scenario 1 (host_dirs purge removes credentials file; metadata volume preserved; redeploy creates orphan key). Will pass once the cross-phase recovery fix (see Gaps) lands.

### 4c. telemetron_purge_images=true + redeploy
expected: `--extra-vars "telemetron_purge_images=true"`; PLAY OUTPUT shows `WARNING: irreversible -- <role> purge_images: <image>:<tag>` per role (11 WARN lines -- every role except nfsd per D-156); `ssh leviathan docker images | grep -E "(grafana|prom|loki|tempo|mimir|otel|fluent|karma|alertmanager|garage|node-exporter)"` returns 0 rows for those exact pinned tags after purge; sibling-image edge case proof -- `curlimages/curl:8.10.1` should be gone after grafana OR loki's purge.yml runs and the other's `failed_when:false` skip-and-warn fires (post-skip WARN visible in OUTPUT); redeploy re-pulls all images (first-time runtime is longer); `failed=0`
result: pass
detail: 11 WARN lines emitted (karma, grafana [grafana-oss + curl], alertmanager, fluentbit, prometheus, opentelemetry, node_exporter, mimir, tempo, loki [loki + curl], garage = 13 images across 11 WARN lines per role). All telemetron-pinned tags removed (only `curlimages/curl:latest` remains, not the pinned `:8.10.1`). Idempotency: second run changed=0 failed=0. Volumes + /opt/telemetron tree preserved per spec. Redeploy hit the same orphan-key recovery bug; workaround applied (delete OLD key); retry redeploy: ok=144 changed=56 failed=0. Smoke test: ok=9 failed=0.

### 5. All 3 purge flags combined + redeploy (OPS-02 second clause: fresh-start)
expected: `--extra-vars "telemetron_purge_data=true telemetron_purge_host_dirs=true telemetron_purge_images=true"`; PLAY-start banner shows all three flags true with category descriptions (D-160); leviathan is rebuilt FROM SCRATCH on next deploy; new Garage S3 credentials auto-generated by bootstrap (Phase 8 D-112 first-run branch); empty buckets; `playbooks/smoke_test.yml` after fresh deploy passes within 60s budget; smoke_test.yml proves the WALK-IN-COLD recovery story: no /opt/telemetron, no images, no volumes, no orphan keys; `failed=0`
result: pass
detail: All-flags undeploy: ok=88 changed=43 failed=0. Post-purge state: 0 telemetron_* volumes (only minio leftover); /opt/telemetron entirely gone; 0 telemetron-pinned images. Walk-in-cold achieved. Fresh deploy (no orphan key because metadata + credentials + host tree all wiped): ok=148 changed=75 failed=0. Smoke test: ok=9 failed=0. Walk-in-cold recovery story PROVEN end-to-end.

## Summary

total: 7
passed: 5
issues: 1
pending: 0
skipped: 1
blocked: 0

## Gaps

### G-01: Orphan S3 key on conservative undeploy + redeploy (Phase 8/10 cross-phase defect)
manifests-in: scenarios 1, 4b (also surfaced during the recovery between scenarios 3 and 4a/4c)
phase-affected: 8 (Garage bootstrap.yml) AND 10 (garage uninstall.yml)
phase-11-impact: none (orchestrator + per-role purge surfaces are correct; this is a pre-existing recovery defect that scenario 1 surfaced)
root-cause: `roles/garage/tasks/uninstall.yml` (Phase 10) unconditionally removes `/opt/telemetron/garage/s3-credentials`. The `telemetron_garage_meta` Docker volume is preserved (correct per D-141). On redeploy, `roles/garage/tasks/bootstrap.yml` (Phase 8) checks "does the credentials file exist?" -- no -- and creates a NEW key named `telemetron` without checking whether a key with that name already exists in the preserved metadata volume. Result: two keys named `telemetron` in Garage's metadata. The subsequent `garage : Allow S3 key on Garage buckets` task filters by key NAME (not ID) via `garage bucket allow --key telemetron --read --write <bucket>`, which fails on the ambiguity with `Error: GetKeyInfo returned InvalidRequest (400): Bad request: 2 matching keys`. Affected buckets: loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts.
workaround-during-uat: `NEW_KEY=$(ssh leviathan 'sudo cat /opt/telemetron/garage/s3-credentials' | grep key_id | cut -d= -f2); OLD_KEY=$(ssh leviathan "docker exec telemetron-garage /garage key list | grep telemetron | awk '{print \$1}' | grep -v $NEW_KEY"); ssh leviathan "docker exec telemetron-garage /garage key delete --yes $OLD_KEY"`; then re-run `ansible-playbook playbooks/deploy_docker.yml`.
recommended-fix: Two options:
  (a) [bootstrap-side, RECOMMENDED] Patch `roles/garage/tasks/bootstrap.yml` to be key-create idempotent -- before creating a new `telemetron` key, run `docker exec telemetron-garage /garage key list` and check for existing keys with that name. If exactly one exists, reuse its ID + secret (extract via `key info <ID>`). If zero exist, create as today. If two or more exist, fail loudly with a clear "orphan key cleanup needed" message.
  (b) [uninstall-side] Patch `roles/garage/tasks/uninstall.yml` to ALSO delete the `telemetron` key from Garage metadata before removing the credentials file. Cleaner but loses the operator's ability to recover OLD bucket data on redeploy.
trigger-for-fix: This defect blocks the D-146 "data recovery on conservative undeploy" story that Phase 11's success criterion 1 explicitly requires. It should be filed as a fix-up plan in a new Phase 8 or Phase 10 gap-closure cycle, OR as Phase 11.1 if we want to keep all M1.2 undeploy work together.

### G-02: Live-UAT scenario 4b not exercised
manifests-in: scenario 4b (skipped during this UAT run)
reason: Skipped per user decision to avoid hitting the G-01 recovery bug twice. Will pass once G-01 is fixed -- the test logic itself is sound.
recommended: Re-run scenario 4b after G-01 fix lands. Expected result: post-purge `/opt/telemetron` gone, `/opt/telemetron/garage/s3-credentials` gone, redeploy clean (no orphan key once G-01 fix is in), `failed=0`.
