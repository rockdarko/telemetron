---
status: partial
phase: 05-ui-plane
source: [05-VERIFICATION.md]
started: 2026-05-19T16:35:00Z
updated: 2026-05-19T16:35:00Z
---

## Current Test

[awaiting human testing on leviathan]

## Tests

### 1. Grafana up and datasource health checks pass
expected: ansible-playbook --tags grafana on leviathan; `docker inspect telemetron-grafana` returns healthy; `GET /api/datasources/uid/{prometheus,loki,tempo,mimir}/health` all return `{"status":"OK"}`
result: [pending]

### 2. Dashboard panels render real data -- especially tempo-self-metrics upstream UID issue
expected: All 7 dashboards open. otel-collector and mimir-self-metrics fully render with prometheus data. tempo-self-metrics: 23 panels with prometheus/loki hardcoded UIDs render correctly; 51 panels with upstream org UIDs (`mimir-ops-03`, `cortex-ops-01`, `P666011C0B63BDCA4`, `P1809F7CD0C75ACF3` -- all prometheus-type) either fall back to the provisioned prometheus datasource or show "Datasource not found". If fallback works, note it as a warning; if panels error, document that tempo-self-metrics requires an additional uid_refs pass for upstream org UIDs.
result: [pending]

### 3. Trace-to-logs correlation in Grafana Explore (UI-04)
expected: Open a Tempo trace in Explore; click a span; Logs tab shows correlated Loki logs via tracesToLogsV2 + derivedFields trace_id
result: [pending]

### 4. Karma visible at host:8082 showing Alertmanager's alerts (UI-05)
expected: `docker inspect telemetron-karma` shows healthy; `http://<leviathan>:8082` loads Karma grid; Karma API response includes `telemetron` as alertmanager source
result: [pending]

### 5. PromLens accessible at host:8081 with Prometheus tree view (UI-06)
expected: `docker inspect telemetron-promlens` shows healthy; `http://<leviathan>:8081` loads PromLens UI; PromQL expression tree renders against `prometheus:9090`
result: [pending]

### 6. Gate 4 idempotency for grafana, karma, promlens
expected: Second back-to-back `ansible-playbook --tags grafana,karma,promlens` run reports `changed=0` for all three roles
result: [pending]

### 7. Gate 9.5 fires correctly on leviathan
expected: `gate_9_5_ok` appears in task output; task does not fail on any provisioned dashboard JSON
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
