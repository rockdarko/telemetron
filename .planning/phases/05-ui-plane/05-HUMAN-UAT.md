---
status: complete
phase: 05-ui-plane
source: [05-VERIFICATION.md]
started: 2026-05-19T16:35:00Z
updated: 2026-05-19T17:35:00Z
host: leviathan
---

## Current Test

[testing complete]

## Tests

### 1. Grafana up and datasource health checks pass
expected: ansible-playbook --tags grafana on leviathan; `docker inspect telemetron-grafana` returns healthy; `GET /api/datasources/uid/{prometheus,loki,tempo,mimir}/health` all return `{"status":"OK"}`
result: issue
reported: "Grafana container itself is healthy and all 4 datasource /health endpoints return status:OK. BUT the role's verify task `Curl-probe /api/health in-network` uses `auto_remove: true` + `detach: false` on the one-shot curl container — incompatible combo: ansible can't fetch the result once auto-remove triggers. Playbook fails with `Cannot retrieve result as auto_remove is enabled` even though Grafana itself is healthy. Re-running with --skip-tags grafana-verify works."
severity: major

### 2. Dashboard panels render real data -- especially tempo-self-metrics upstream UID issue
expected: All 7 dashboards open. otel-collector and mimir-self-metrics fully render with prometheus data. tempo-self-metrics: 23 panels with prometheus/loki hardcoded UIDs render correctly; 51 panels with upstream org UIDs (`mimir-ops-03`, `cortex-ops-01`, `P666011C0B63BDCA4`, `P1809F7CD0C75ACF3` -- all prometheus-type) either fall back to the provisioned prometheus datasource or show "Datasource not found". If fallback works, note it as a warning; if panels error, document that tempo-self-metrics requires an additional uid_refs pass for upstream org UIDs.
result: issue
reported: "All 7 dashboards provisioned (verified via /api/search). Panel-level datasources in tempo-self-metrics.json are normalized to `prometheus` (71 panels). But TARGET-level datasources still reference upstream UIDs: 22 mimir-ops-03, 22 cortex-ops-01, 6 P666011C0B63BDCA4, 1 P1809F7CD0C75ACF3 (51 total). All 4 UIDs return 404 from /api/datasources/uid/{uid} and /api/ds/query — Grafana does NOT fall back to the panel datasource for target-level UIDs. 51 target queries will error in the UI. Phase 05-04 uid_refs normalization needs a second pass that covers `targets[*].datasource.uid`, not just `panels[*].datasource.uid`."
severity: major

### 3. Trace-to-logs correlation in Grafana Explore (UI-04)
expected: Open a Tempo trace in Explore; click a span; Logs tab shows correlated Loki logs via tracesToLogsV2 + derivedFields trace_id
result: issue
reported: "Wiring is correct on both sides: Tempo datasource has tracesToLogsV2 with datasourceUid=loki and customQuery template; Loki datasource has derivedFields with name=trace_id, matcherType=label, matcherRegex=trace_id, datasourceUid=tempo. BUT cannot validate E2E: (a) Tempo has 0 traces (search start=-1h returned empty), (b) Loki labels are {env, host, job, service_name} — NO `trace_id` label, so the label-typed derivedField has nothing to match. Either the OTel Collector loki exporter isn't promoting trace_id to a Loki label, or the derivedField matcherType should be `structured_metadata` (Grafana 11+) instead of `label`. Also: Loki derivedField has `url: \"\"` (relies on datasourceUid linkage — fine in Grafana 8+ but worth flagging). Loki tracesToLogsV2 custom query `{} | trace_id=\"\"` has empty `{}` selector — likely depends on template var substitution at click time."
severity: major

### 4. Karma visible at host:8082 showing Alertmanager's alerts (UI-05)
expected: `docker inspect telemetron-karma` shows healthy; `http://<leviathan>:8082` loads Karma grid; Karma API response includes `telemetron` as alertmanager source
result: issue
reported: "Karma serves traffic correctly: GET /health returns 200 'Pong', POST /alerts.json returns upstream=[{name: 'telemetron', version: '0.32.1', uri: ./proxy/alertmanager/telemetron, error: ''}]. BUT `docker inspect` reports unhealthy with FailingStreak=4. Cause: ghcr.io/prymitive/karma:v0.130 is a distroless/scratch image with no `/bin/sh` and no `wget`. The role's default healthcheck `[\"CMD-SHELL\", \"wget --spider -q http://localhost:8080/health || exit 1\"]` (roles/karma/defaults/main.yml:59) fails with `OCI runtime exec failed: exec: \"/bin/sh\": stat /bin/sh: no such file or directory`. Fix: either set `karma_healthcheck_enabled: false` and rely on external probe, or use `CMD` (no shell) with a static binary the image actually contains. Karma image ships only the `/karma` binary itself; common pattern is to disable the healthcheck and use the Ansible verify probe."
severity: major

### 5. PromLens accessible at host:8081 with Prometheus tree view (UI-06)
expected: `docker inspect telemetron-promlens` shows healthy; `http://<leviathan>:8081` loads PromLens UI; PromQL expression tree renders against `prometheus:9090`
result: pass

### 6. Gate 4 idempotency for grafana, karma, promlens
expected: Second back-to-back `ansible-playbook --tags grafana,karma,promlens` run reports `changed=0` for all three roles
result: issue
reported: "Idempotency itself is fine — when verify tasks are skipped, `--tags grafana,karma,promlens --skip-tags grafana-verify,karma-verify` returns ok=21 changed=0 failed=0 on a second back-to-back run. But the AS-WRITTEN default run (no skip-tags) FAILS on first deploy at grafana-verify (auto_remove bug, test 1) AND at karma-verify (distroless healthcheck, test 4), so 'second back-to-back run' never gets reached cleanly through the default invocation. Strict reading: idempotency PASSES; deploy-as-shipped fails before idempotency can even be tested."
severity: major

### 7. Gate 9.5 fires correctly on leviathan
expected: `gate_9_5_ok` appears in task output; task does not fail on any provisioned dashboard JSON
result: issue
reported: "Gate 9.5 detection logic is CORRECT: ran the shell snippet directly against `/opt/telemetron/grafana/provisioning/dashboards/telemetron/` and it returned `gate_9_5_ok`. BUT during the normal `ansible-playbook --tags grafana` run, Gate 9.5 (verify.yml:246) is never reached — the playbook fails at step 2 (verify.yml:33, the Curl-probe /api/health task with the auto_remove bug). Gate 9.5 is gated behind the same `grafana-verify` tag as the broken upstream task. So Gate 9.5 works when invoked manually or when the auto_remove bug is fixed, but cannot be reached via the default deploy."
severity: major

## Summary

total: 7
passed: 1
issues: 6
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "ansible-playbook --tags grafana completes without failure when Grafana itself is healthy"
  status: failed
  reason: "User reported: grafana role's verify.yml:33 Curl-probe /api/health uses community.docker.docker_container with auto_remove:true + detach:false — module docs say this combo is invalid (cannot fetch result post-removal). Playbook fails with 'Cannot retrieve result as auto_remove is enabled' on first deploy even when Grafana datasources all report OK."
  severity: major
  test: 1
  artifacts: ["roles/grafana/tasks/verify.yml:33-53"]
  missing: ["set auto_remove:false + explicit cleanup, OR run curl via raw shell/command module, OR use a known-good pattern from another working role"]

- truth: "tempo-self-metrics dashboard's 51 upstream-UID panel TARGETS render against the provisioned prometheus datasource"
  status: failed
  reason: "User reported: tempo-self-metrics.json has 51 target[*].datasource.uid refs still pointing at upstream org UIDs (22 mimir-ops-03, 22 cortex-ops-01, 6 P666011C0B63BDCA4, 1 P1809F7CD0C75ACF3). All 4 UIDs 404 from Grafana. Grafana does NOT fall back to panel-level datasource for target-level UID mismatches — /api/ds/query returns 404. Phase 05-04 uid_refs normalization only fixed panel-level datasources."
  severity: major
  test: 2
  artifacts: ["roles/grafana/files/dashboards/tempo-self-metrics.json"]
  missing: ["uid_refs pass that walks targets[*].datasource.uid in every dashboard JSON and rewrites unknown UIDs to the inherited panel datasource"]

- truth: "trace-to-logs correlation produces results when clicking a Tempo span in Grafana Explore"
  status: failed
  reason: "User reported: cannot E2E-test (Tempo has 0 traces, Loki has no trace_id label). Configuration is also suspect — Loki derivedField uses matcherType:label requiring trace_id as a Loki label, but Loki labels are {env, host, job, service_name}. For OTel logs the modern path is structured_metadata, not a label."
  severity: major
  test: 3
  artifacts: ["roles/grafana/templates/datasources.yaml.j2 (Loki derivedFields + Tempo tracesToLogsV2)"]
  missing: ["either: (a) configure OTel Collector loki exporter to promote trace_id to a Loki label via resource attribute hint, OR (b) change Loki derivedField matcherType to `structured_metadata` if Grafana version supports it, OR (c) add a regex-typed derivedField that extracts trace_id from the log line body as fallback; AND a synthetic trace+log producer so this can be verified without an external instrumented service"]

- truth: "telemetron-karma container reports healthy on `docker inspect`"
  status: failed
  reason: "User reported: ghcr.io/prymitive/karma:v0.130 is FROM scratch — no /bin/sh, no wget. Role's default healthcheck karma_healthcheck_test = CMD-SHELL + wget at roles/karma/defaults/main.yml:59 fails every time with 'exec: /bin/sh: stat /bin/sh: no such file or directory'. Karma functionally works (GET /health returns 200, alertmanager linkage OK), but inspect shows unhealthy and the role's verify task hangs waiting for healthy."
  severity: major
  test: 4
  artifacts: ["roles/karma/defaults/main.yml:59", "roles/karma/tasks/main.yml:71-85"]
  missing: ["replace healthcheck with one that doesn't require /bin/sh — options: (a) disable healthcheck entirely (`karma_healthcheck_enabled: false` as default) and rely on the in-network curl probe in verify.yml, (b) use `CMD ['/karma', '--check-config']` if karma has a self-check subcommand, or (c) add a curl binary via volume-mount (not preferred)"]

- truth: "default `--tags grafana,karma,promlens` run on a fresh host completes without failure on first deploy"
  status: failed
  reason: "User reported: blocked by gaps from tests 1 and 4. With verify tasks skipped, three roles are perfectly idempotent (ok=21 changed=0 on second run). But the as-shipped default invocation never completes a clean first deploy."
  severity: major
  test: 6
  artifacts: ["roles/grafana/tasks/verify.yml:33-53", "roles/karma/defaults/main.yml:59"]
  missing: ["fixes for the two gating bugs above; once fixed, idempotency itself is already proven"]

- truth: "Gate 9.5 task runs and prints gate_9_5_ok during the normal --tags grafana playbook run"
  status: failed
  reason: "User reported: Gate 9.5 logic is correct (verified by running the shell snippet directly on leviathan — prints gate_9_5_ok). But it's gated behind the `grafana-verify` tag along with the broken auto_remove task, which fails earlier and aborts the verify block. Gate 9.5 task is never reached during a normal deploy."
  severity: major
  test: 7
  artifacts: ["roles/grafana/tasks/verify.yml:246-263"]
  missing: ["fix for test 1's auto_remove bug — then Gate 9.5 runs naturally as part of the verify block"]
