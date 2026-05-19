# Telemetron smoke test

Acceptance smoke test for the Telemetron M1 data plane. Pushes a synthetic
log + metric + trace through the OTel Collector and asserts visibility in
Grafana via datasource-proxy queries within a 60-second budget.

## What it proves

1. The OTel Collector OTLP/HTTP receiver on `:4318` accepts the three signal types.
2. Loki ingests the log and exposes it via `service_name="telemetron-smoke"`.
3. Prometheus scrapes the metric from the OTel Collector's `prometheus` exporter.
4. Prometheus remote_writes the metric to Mimir (both datasources return the series).
5. Tempo receives the trace and makes it queryable by `traceId`.
6. Grafana's four datasource UIDs (`loki`, `prometheus`, `mimir`, `tempo`) all resolve.

If all 4 assertions pass, the data plane is end-to-end healthy.

## Prerequisites

- `playbooks/deploy_docker.yml` has run to convergence on the target host.
- `grafana_admin_password` is set in `inventory/<env>/group_vars/all/secrets.yml`.

## Run

Full smoke (all three signals):

```bash
ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml \
  --ask-vault-pass
```

Single signal (debug a specific data path):

```bash
ansible-playbook ... playbooks/smoke_test.yml --tags log
ansible-playbook ... playbooks/smoke_test.yml --tags metric
ansible-playbook ... playbooks/smoke_test.yml --tags trace
```

## Budget

Each assertion task retries 12 times with 5-second delays -- 60 seconds
total per signal. The smoke test fails LOUDLY (non-zero playbook exit) if
any assertion exhausts its retry budget. This is OPS-07 / ROADMAP SC3
expressed as a verifiable Ansible assertion.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Producer task fails with `Connection refused` on `:4318` | OTel Collector not running, or OTLP/HTTP receiver disabled | `docker ps -f name=telemetron-opentelemetry`; check `opentelemetry_publish_otlp` is `true` |
| Loki asserter exhausts retries | OTel Collector failing to forward logs to Loki, OR Loki ingester not flushing | Check `docker logs telemetron-opentelemetry` for export errors; check `docker logs telemetron-loki` for ingester errors |
| Prometheus asserter passes, Mimir asserter fails | Prometheus -> Mimir remote_write broken | Check `curl http://localhost:9090/api/v1/alertmanagers` and Prometheus's `remote_storage_*` metrics |
| Tempo asserter exhausts retries with 404 | Trace stuck in WAL or OTel Collector trace export failing | Check `docker logs telemetron-tempo` for ingester errors; verify OTel Collector's trace pipeline is healthy |
| Mimir asserter fails with 404 on URL | Mimir datasource URL path mismatch | Compare path in playbook (`/api/datasources/proxy/uid/mimir/api/v1/query`) with `roles/grafana/templates/datasources.yml.j2` |

## Idempotency

The smoke test is read-mostly (3 POSTs to OTel + 4 queries). Running it
multiple times back-to-back produces fresh trace_id / run_id values on
each run; back-to-back runs do not pollute each other.

## Source of truth

- OTLP/HTTP payload spec: opentelemetry-proto/examples (verified against 0.152.0 OTel Collector Contrib).
- Assertion pattern: mirrored from `roles/grafana/tasks/verify.yml` (proven on leviathan 2026-05-19).
- 60s budget: D-99 / OPS-07 (see `.planning/REQUIREMENTS.md`).
