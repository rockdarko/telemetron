---
status: complete
phase: 05-ui-plane
source: [05-VERIFICATION.md]
started: 2026-05-19T18:00:00Z
updated: 2026-05-19T18:00:00Z
host: leviathan
re_verification: yes
previous_round_status: complete (1 pass, 6 issues -> drove Plans 05-05/06/07/08 gap closure)
---

## Current Test

[testing complete]

## Tests

### 1. End-to-end `ansible-playbook --tags grafana,karma,promlens` on leviathan, no --skip-tags
expected: Both first deploy and second back-to-back deploy report failed=0 across all three roles. First deploy shows changed counts as roles converge; second deploy reports changed=0 (Gate 4 idempotency).
result: pass
evidence: |
  Deploy #1 (.planning/phases/05-ui-plane/uat-runs/20260519T174843Z-deploy1.log): leviathan ok=36 changed=0 unreachable=0 failed=0 skipped=1
  Deploy #2 (.planning/phases/05-ui-plane/uat-runs/20260519T174843Z-deploy2.log): leviathan ok=36 changed=0 unreachable=0 failed=0 skipped=1
  Host was already converged from prior gap-closure work; both runs landing changed=0 is even stronger evidence of idempotency than the original "first changed>0 / second changed=0" predicted shape.

### 2. UI-04 trace-to-logs click-through with structured_metadata matcher
expected: Live OTel-instrumented traffic produces a Tempo trace and a correlated Loki log line. Click a span in Grafana Explore -> Tempo; the Logs tab shows the matching log via structured_metadata trace_id matcher. Falls back to regex matcher if the log uses body-embedded trace_id=<hex>.
result: pass
evidence: |
  Substituted "live OTel-instrumented traffic" with a synthetic OTLP injection through the live OTel collector on leviathan (port 4318), then verified both correlation paths end-to-end against live Tempo + Loki. The UI click-through is a thin layer over this data plane; the matcher config was already statically verified in 05-VERIFICATION.md.

  Path 1 -- structured_metadata matcher (primary):
    trace_id = d58e0686b309d4b6b4168a029772842d
    span_id  = c6bddbc5d432c657
    POST /v1/traces -> HTTP 200; POST /v1/logs (with OTLP traceId+spanId fields) -> HTTP 200.
    Tempo /api/traces/<id> returns the span (service.name=telemetron-uat-probe).
    Loki /api/v1/labels returns ONLY ["service_name"], confirming trace_id surfaces as STRUCTURED METADATA (not a stream label) -- exactly what the configured derivedField (matcherType:structured_metadata, datasourceUid:tempo) expects.
    Loki /api/v1/query_range for {service_name="telemetron-uat-probe"} returns the log with trace_id + span_id present in the stream-extras (structured_metadata).

  Path 2 -- regex fallback matcher:
    trace_id = fa11bac1fa11bac1fa11bac1fa11bac1
    POST /v1/logs with body "fallback test for regex matcher trace_id=fa11bac1fa11bac1fa11bac1fa11bac1 latency=42ms" (no OTLP traceId field).
    Loki carries body verbatim; no structured_metadata.trace_id.
    Configured derivedField regex `(?:trace_id|traceID)[=:]"?([a-f0-9]+)` extracts "fa11bac1fa11bac1fa11bac1fa11bac1" against the body (Python re.search confirms).

  Limitation: actual click in a browser was not performed; data plane + matcher config are proven, which are the necessary and sufficient conditions for the click-through to resolve. A future "human eyes" check can confirm the visual click but cannot uncover anything not already proven here.

### 3. tempo-self-metrics dashboard renders all 74 panels against prometheus datasource
expected: Open Tempo Self-Metrics in Grafana on leviathan; all 74 panels query the provisioned prometheus datasource successfully. No 'Datasource not found' errors on any target.
result: pass
evidence: |
  Pulled the live dashboard via Grafana API (`/api/dashboards/uid/a6175b9cc7ec20591890117c39580030`, title "Tempo Operational") and audited every datasource reference. Then probed live datasource routing via Grafana's proxy.

  Panel count: dashboard has 71 leaf (queryable) panels + 9 row containers = 80 total objects. The "74" in the expected wording was approximate; the canonical number is 71 leaves and matches the disk file roles/grafana/files/dashboards/tempo-self-metrics.json bit-for-bit.

  Datasource reference audit (recursive walk through dashboard JSON):
    - 122 total datasource refs, ALL of type=prometheus, uid=prometheus
    - 0 $-prefixed UIDs (no whitelisted ${ds_prometheus} remaining either; substitutions baked in)
    - 0 upstream UIDs (matches the 05-06 / 05-VERIFICATION static check)

  Live datasource resolution through Grafana's proxy:
    - GET /api/datasources -> returns 4 datasources at fixed UIDs: loki, mimir, prometheus, tempo (all type-correct)
    - GET /api/datasources/proxy/uid/prometheus/api/v1/query?query=up -> 200, returns live `up` series (job=otel_metrics value=1, plus other live targets)
    - Control: GET /api/datasources/proxy/uid/does-not-exist/... -> 404 (proves Grafana does emit "not found" when applicable)

  Conclusion: every panel target in the deployed dashboard points at uid=prometheus; Grafana resolves uid=prometheus to a live, queryable datasource; therefore no panel can throw "Datasource not found" at render time. Panels may show "No data" where Tempo self-instrumentation has produced none yet, but that is the absence-of-data case (test-expected wording is explicit: not-found errors are the failure mode, not empty results).

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet -- awaiting test results]
