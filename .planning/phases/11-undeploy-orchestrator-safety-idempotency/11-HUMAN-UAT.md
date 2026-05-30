---
status: complete
phase: 11-undeploy-orchestrator-safety-idempotency
source: [11-VERIFICATION.md]
started: 2026-05-29T00:00:00Z
updated: 2026-05-30T12:25:00Z
---

## Current Test

[Round 2 complete 2026-05-30. All 7 scenarios pass on leviathan. G-01 + G-02 behaviourally closed via recovery branch (commits 5eb9833 + 319559f).]

## Tests

### 1. Conservative undeploy + redeploy (OPS-02 happy path; D-146 recovery proof; G-01 behavioural closure)
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` completes with `failed=0` and no purge flags set; named volumes `telemetron_*_data` survive -- `docker volume ls | grep telemetron_` shows all 11 telemetron-prefixed volumes intact (alertmanager, fluentbit_buffer, garage_meta + garage_data, grafana, loki, mimir, prometheus, tempo); immediate redeploy via `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml` succeeds WITHOUT the manual `garage key delete` workaround; `garage : Allow S3 key on Garage buckets` succeeds on all 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts); `ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml` round-trip passes within 60s; Grafana panels show OLD pre-undeploy log/metric/trace data (proves D-146 recovery: bootstrap.yml recovery branch reused the orphan key's secret via `garage key info --show-secret`, no duplicate key created)
result: pass
detail: PASSED 2026-05-30 round 2 (post-fix). Undeploy clean (ok=37 changed=23 failed=0). First redeploy attempt surfaced TWO downstream regressions caught only by live execution -- (a) unquoted "G-01:" colon in a task name broke YAML parsing of bootstrap.yml at include-role time (fixed in commit 2626989), (b) the `\S+`-widened regex matched the GK-prefixed ID but the real `garage key list` output has FOUR columns (ID, Created, Name, Expiration) not two, so the literal `telemetron` name in column 3 was never matched (fixed in commit 319559f -- regex now `^(\S+)\s+\S+\s+telemetron(?:\s|$)`). After the second deploy attempt the orphan-failure branch fired correctly (length>=2 because the first attempt had silently created a duplicate); the fail msg listed both key IDs and the verbatim workaround command. Applied workaround: deleted the bogus key + credentials file. Third deploy attempt fired the recovery branch (Read existing telemetron key info -> ok; Set ... credential facts -> ok; Persist recovered ... credentials -> changed) and completed with ok=142 changed=28 failed=0. Bucket allow succeeded on all 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts). Credentials file now points to GK18e062108528078b3e7ea4f6 (the OLD pre-undeploy key). Smoke test ok=9 failed=0. D-146 recovery proven end-to-end.

### 2. Back-to-back undeploy idempotency (OPS-01)
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` run twice in a row; second-run PLAY RECAP shows `changed=0` (every state=absent task already converged per D-141); `failed=0` in both runs
result: pass
detail: PASSED 2026-05-30 round 1. Run 1: ok=37 changed=23 failed=0. Run 2: ok=37 changed=0 failed=0. Perfect idempotency. No regression risk -- undeploy_docker.yml is unchanged by plan 11-06.

### 3. Partial-deploy idempotency simulation (D-164)
expected: with the stack running on leviathan, manually `ssh leviathan docker rm -f telemetron-fluentbit telemetron-opentelemetry telemetron-alertmanager`; then run `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml`; PLAY RECAP `failed=0`; pre-removed containers stay removed (no spurious `changed=true` on them since state=absent on a missing container is a no-op); remaining 9 containers (or 10 if nfsd enabled) cleanly removed
result: pass
detail: PASSED 2026-05-30 round 1. Setup: removed fluentbit + opentelemetry + alertmanager (stack went 11 -> 8). Undeploy: ok=37 changed=20 failed=0. changed=20 (vs 23 for full undeploy) -- exactly 3 fewer, matching the 3 pre-removed containers (state=absent no-op on missing). No regression risk -- undeploy_docker.yml unchanged by plan 11-06.

### 4a. telemetron_purge_data=true + redeploy
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --extra-vars "telemetron_purge_data=true"`; PLAY-start banner shows `telemetron_purge_data=True` with category description "all telemetron_* named Docker volumes will be removed" (D-160); PLAY OUTPUT shows `WARNING: irreversible -- <role> purge_data: <volume-name>` for every role with a volume (alertmanager, fluentbit, garage [comma-separated meta + data], grafana, loki, mimir, prometheus, tempo = 8 WARN lines); `docker volume ls | grep telemetron_` returns 0 telemetron-prefixed volumes after purge; redeploy via `playbooks/deploy_docker.yml` succeeds; `playbooks/smoke_test.yml` after redeploy shows EMPTY datasource panels (proves fresh-bucket state -- old data wiped); `failed=0` throughout
result: pass
detail: PASSED 2026-05-30 round 1. D-160 PLAY-start banner displays all 3 flag states with category descriptions verbatim. 8 WARN lines emitted (garage comma-joins meta+data on one line). Idempotency on second run: changed=0 failed=0. Post-purge: 0 telemetron_* volumes remain (only `telemetron_minio_data` v1.0.0 leftover, out of scope). Redeploy (fresh metadata = no orphan key issue): ok=148 changed=64 failed=0. Smoke test: ok=9 failed=0.

### 4b. telemetron_purge_host_dirs=true + redeploy (G-02 closure)
expected: `--extra-vars "telemetron_purge_host_dirs=true"`; PLAY OUTPUT shows `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)` (D-159 single-line); `ssh leviathan ls /opt/telemetron 2>&1` returns "No such file or directory" after purge (per D-155 parent-only rmdir at orchestrator post_tasks); redeploy recreates the tree from scratch (every role's config dir bind-mount re-renders Gate 8 parent-dir mount cleanly); Garage S3 credentials file at `/opt/telemetron/garage/s3-credentials` specifically destroyed (PURGE-02 SC-5 explicit requirement); bootstrap.yml recovery branch fires on redeploy (host file gone, one orphan key in preserved garage_meta volume); `bucket allow` succeeds on all 5 buckets; Grafana shows OLD data; `failed=0`
result: pass
detail: PASSED 2026-05-30 round 2 (post-fix). Undeploy with purge_host_dirs=true clean (ok=39 changed=24 failed=0; one more changed than scenario 1 because of the parent-tree removal). Post-undeploy: `/opt/telemetron` gone ("No such file or directory"); 9 telemetron_* volumes preserved (D-141 trust). Redeploy: recovery branch fired (Read existing telemetron key info -> ok; Set ... credential facts -> ok; Persist recovered ... -> changed); bucket allow ok on all 5 buckets; ok=148 changed=52 failed=0. Same OLD key (GK18e062108528078b3e7ea4f6) reused; same secret as scenario 1 (proves identical recovery path). 11 containers up. Smoke test ok=9 failed=0. G-02 closed transitively via the same G-01 fix.

### 4c. telemetron_purge_images=true + redeploy
expected: `--extra-vars "telemetron_purge_images=true"`; PLAY OUTPUT shows `WARNING: irreversible -- <role> purge_images: <image>:<tag>` per role (11 WARN lines -- every role except nfsd per D-156); `ssh leviathan docker images | grep -E "(grafana|prom|loki|tempo|mimir|otel|fluent|karma|alertmanager|garage|node-exporter)"` returns 0 rows for those exact pinned tags after purge; sibling-image edge case proof -- `curlimages/curl:8.10.1` should be gone after grafana OR loki's purge.yml runs and the other's `failed_when:false` skip-and-warn fires; redeploy re-pulls all images; `failed=0`
result: pass
detail: PASSED 2026-05-30 round 1 (with workaround). 11 WARN lines emitted (karma, grafana [grafana-oss + curl], alertmanager, fluentbit, prometheus, opentelemetry, node_exporter, mimir, tempo, loki [loki + curl], garage = 13 images across 11 WARN lines per role). All telemetron-pinned tags removed (only `curlimages/curl:latest` remains, not the pinned `:8.10.1`). Idempotency: second run changed=0 failed=0. Redeploy hit the G-01 bug; workaround applied; retry ok=144 changed=56 failed=0. Smoke test: ok=9 failed=0. G-01 fix means the workaround is no longer needed on re-run.

### 5. All 3 purge flags combined + redeploy (OPS-02 second clause: fresh-start)
expected: `--extra-vars "telemetron_purge_data=true telemetron_purge_host_dirs=true telemetron_purge_images=true"`; PLAY-start banner shows all three flags true with category descriptions (D-160); leviathan is rebuilt FROM SCRATCH on next deploy; new Garage S3 credentials auto-generated by bootstrap (Phase 8 D-112 first-run branch); empty buckets; `playbooks/smoke_test.yml` after fresh deploy passes within 60s budget; smoke_test.yml proves the WALK-IN-COLD recovery story: no /opt/telemetron, no images, no volumes, no orphan keys; `failed=0`
result: pass
detail: PASSED 2026-05-30 round 1. All-flags undeploy: ok=88 changed=43 failed=0. Post-purge state: 0 telemetron_* volumes (only minio leftover); /opt/telemetron entirely gone; 0 telemetron-pinned images. Walk-in-cold achieved. Fresh deploy (no orphan key because metadata + credentials + host tree all wiped): ok=148 changed=75 failed=0. Smoke test: ok=9 failed=0. Walk-in-cold recovery story PROVEN end-to-end.

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### G-01: Orphan S3 key on conservative undeploy + redeploy (Phase 8/10 cross-phase defect)
status: closed
manifests-in: scenarios 1, 4b
fix-commits: 5dc5fd5, 01399a0, 06047b8, 85a6de7, 5eb9833, 2626989, 319559f
fix-plan: 11-06-PLAN.md
fix-summary: Patched `roles/garage/tasks/bootstrap.yml` to add orphan-key discovery (`/garage key list` probe + `regex_findall` extracting keys matching the configured `garage_s3_key_name`), three mutually exclusive branches (length==0 first-run create, length==1 recovery via `garage key info --show-secret`, length>=2 `ansible.builtin.fail` with operator workaround in msg), `no_log: true` on the key-info exec. Required regex form is `^(\S+)\s+\S+\s+telemetron(?:\s|$)` -- the live `garage key list` output has 4 columns (ID, Created, Name, Expiration) so the Created column must be skipped. Validated end-to-end on leviathan 2026-05-30 round 2: orphan-failure branch fires correctly when 2 keys exist (msg lists both IDs + workaround); recovery branch fires correctly when 1 key exists (reuses OLD key's secret, persists to credentials file, bucket allow succeeds). D-146 recovery proven.

### G-02: Live-UAT scenario 4b not exercised
status: closed
manifests-in: scenario 4b
fix-commits: 5dc5fd5, 01399a0, 06047b8, 85a6de7, 5eb9833, 2626989, 319559f
fix-plan: 11-06-PLAN.md (G-01 fix is the same code path that closes 4b)
fix-summary: Scenario 4b validated end-to-end on leviathan 2026-05-30 round 2 -- same recovery branch as scenario 1 fires correctly when purge_host_dirs=true removes the credentials file but preserves the garage_meta volume. ok=148 changed=52 failed=0; smoke test ok=9 failed=0.
