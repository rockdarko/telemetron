---
status: partial
phase: 03-ingest-plane
source: [03-VERIFICATION.md]
started: 2026-05-18T17:05:00Z
updated: 2026-05-18T22:30:00Z
---

## Current Test

[awaiting human testing on homelab Docker host]

## Tests

### 1. Live boot SC1 — playbook converges + all four readiness probes green
expected: |
  Run `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags prometheus,opentelemetry,fluentbit,node_exporter --ask-vault-pass` against the fresh-from-Phase-2 homelab host.
  All four containers come up healthy in dependency order (node_exporter → opentelemetry → prometheus → fluentbit). On the host:
  - `curl http://<host>:9090/-/ready` returns "Prometheus Server is Ready."
  - `curl -X POST http://<host>:4318/v1/traces -H 'content-type: application/json' -d '{}'` returns 200/202
  - `curl http://<host>:2020/api/v1/health` returns 200
  - `curl http://<host>:9100/metrics` returns 200 with body containing `node_cpu_seconds_total`
  - `curl http://<host>:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'` shows `otel_self`, `otel_metrics`, `node_exporter` all reporting `up`
result: [pending]

### 2. Live boot SC2 — synthetic OTLP signals fan out to all three backends
expected: |
  After convergence, push synthetic OTLP signals to the Collector:
  - Trace pushed to `:4318/v1/traces` appears via Tempo's API within 30s
  - Log pushed to `:4318/v1/logs` appears via Loki's `/loki/api/v1/query` within 30s
  - Metric pushed to `:4318/v1/metrics` is queryable both at `:9090/api/v1/query` (Prometheus scrape) AND at `:9009/prometheus/api/v1/query` (after remote_write to Mimir)
result: [pending]

### 3. Live boot SC3 — four baseline alert rules load + extras knob renders
expected: |
  - `curl http://<host>:9090/api/v1/rules | jq -r '.data.groups[].rules[].name' | sort` returns exactly: `ContainerRestartLoop`, `FilesystemAlmostFull`, `HostDown`, `OTelCollectorDroppingSignals`
  - Adding a single rule via `prometheus_extra_rules` in inventory and re-running the playbook causes the new rule to appear in the same query output without re-deploying the role
result: [pending]

### 4. Live boot SC4 — pipeline ordering, GOMEMLIMIT, OOM resistance under 5-min load
expected: |
  - `docker exec telemetron-otel cat /etc/telemetron/opentelemetry/config.yaml | grep -A1 'pipelines:' | grep 'processors'` shows `processors: [memory_limiter, batch]` in every pipeline
  - `docker inspect telemetron-otel --format '{{json .Config.Env}}' | jq -r '.[]' | grep GOMEMLIMIT` returns `GOMEMLIMIT=400MiB`
  - 5-min synthetic load (e.g. otelgen) against `:4318/v1/metrics` at ≥1k req/s does NOT OOM the container (`docker inspect telemetron-otel --format '{{.State.OOMKilled}}'` stays `false`)
result: [pending]

### 5. Live boot SC5 — Fluent Bit ships only the 5-label allowlist (incl. Lua-enriched service/job)
expected: |
  After FB has tailed at least one container log line on the host:
  - `curl 'http://<host>:3100/loki/api/v1/labels'` returns a `data` array containing AT MOST: `host`, `env`, `service`, `job`, `level`
  - High-cardinality keys (`container_id`, `image_id`, etc.) MUST NOT appear
  - `Time_System_Timezone Etc/UTC` and `Multiline_Flush 5` literals are visible in the rendered `/opt/telemetron/fluentbit/fluent-bit.conf` on the host

  INGEST-07 enrichment (Plan 03-05 — now SATISFIED in code, awaiting live boot):
  - For a STACK container (e.g. `telemetron-prometheus`), Loki streams must show `service="telemetron"` + `job="prometheus"` (the `org.telemetron.service` / `org.telemetron.job` Docker labels stamped by every Phase-1..3 role)
  - For an UNLABELED container (e.g. `docker run --rm hello-world`), the Lua filter falls back to `service="unlabeled"` (from `fluentbit_unlabeled_service`) + `job=<container_name>` (from `fluentbit_unlabeled_job`) — `curl 'http://<host>:3100/loki/api/v1/label/service/values'` should return both `telemetron` and `unlabeled`
  - SC4 OOM re-test: the Lua filter adds a per-log-line disk read against `/var/lib/docker/containers/<id>/config.v2.json` with a 300s TTL cache. Re-run the 5-min 1k-req/s synthetic load test against the FB pipeline (not just OTel) and confirm `docker inspect telemetron-fluentbit --format '{{.State.OOMKilled}}'` stays `false`.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

- ingest-07-service-job-labels:
    description: |
      INGEST-07 PARTIAL -- `roles/fluentbit/templates/fluent-bit.conf.j2` originally Add'd only `host`/`env`/`level` via `[FILTER] modify`. The required `service` and `job` labels were documented in the README allowlist table as "default to container_name via Q3 fallback", but no rendered filter actually promoted them.
    status: resolved
    resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md
    severity: minor
    resolution: |
      Plan 03-05 adds a `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) that reads `/var/lib/docker/containers/<id>/config.v2.json` (already bind-mounted RO from Plan 03-04 -- no Docker socket) and extracts the Docker labels `org.telemetron.service` and `org.telemetron.job`. All eight Phase-1..3 telemetron stack roles stamp these labels on their `docker_container` task; Phase 4/5 role ports inherit the convention via Gate 7 in `roles/README.md`. The Lua filter caches per-container lookups with a 300s TTL; SC4 (5-min 1k-req/s OOM resistance) re-tested as a UAT item per the README Verification scope section.
