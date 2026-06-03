---
status: partial
phase: 08-garage-role-backend-retargeting
source: [08-VERIFICATION.md]
started: 2026-05-27T17:30:00Z
updated: 2026-05-27T17:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Smoke test round-trip through Garage
expected: `ansible-playbook playbooks/smoke_test.yml` completes with `failed=0`; synthetic OTLP log, metric, and trace data round-trips through Loki, Mimir, and Tempo respectively, all writing to and reading from Garage
result: [pending]

### 2. Container health + bootstrap verification
expected: `docker inspect telemetron-garage --format='{{.State.Health.Status}}'` returns `healthy`; `docker exec telemetron-garage /garage layout show` shows assigned node with `replication_factor: 1`; `docker exec telemetron-garage /garage bucket list` shows all 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts); `/opt/telemetron/garage/s3-credentials` exists with mode 0600 containing key_id and secret lines
result: [pending]

### 3. Prometheus Garage scrape UP
expected: Prometheus targets page shows `garage` job as UP; `curl -s -H "Authorization: Bearer <garage_admin_token>" http://leviathan:3903/metrics` returns Prometheus-format text with at least one `garage_` metric
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
