# Documentation

Reference docs for Telemetron M1.

## Shipped (M1)

| File | Content |
|---|---|
| [`architecture.md`](architecture.md) | Components, monolithic-mode tradeoffs, signal flow, port matrix |
| [`quickstart.md`](quickstart.md) | Zero-to-dashboards walkthrough with prerequisites, expected outputs, troubleshooting |
| [`inventory.md`](inventory.md) | Inventory model, group_vars schema, secrets contract, multi-host extension preview |

See also the per-component documentation under
[`roles/<name>/README.md`](../roles/) and the smoke-test operator notes
at [`playbooks/smoke_test/README.md`](../playbooks/smoke_test/README.md).

## Deferred (v2)

The following docs are deferred to a future milestone. Tracked in
`.planning/REQUIREMENTS.md` under DOCS-V2-01..07.

| File | Content | Status |
|---|---|---|
| `alerts.md` | Bundled Prometheus alerts catalog | v2 (DOCS-V2-01) |
| `mimir-retention.md` | Two-tier retention strategy | v2 (DOCS-V2-02) |
| `fluentbit-timestamps.md` | DST + timezone handling for log shipping | v2 (DOCS-V2-03) |
| `hook-router.md` | Alertmanager -> CI bridge architecture (hook router itself is deferred -- see ALERT-V2-01..05) | v2 (DOCS-V2-04) |
| `instrumentation-otel.md` | Instrumenting your apps for OTLP | v2 (DOCS-V2-05) |
| `migration-from-inspq.md` | Port notes for anyone forking the original INSPQ stack | v2 (DOCS-V2-06) |
| `metrics.md` | Health metrics catalog with thresholds | v2 (DOCS-V2-07) |
