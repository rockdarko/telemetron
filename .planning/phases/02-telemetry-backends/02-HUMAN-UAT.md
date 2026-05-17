---
status: partial
phase: 02-telemetry-backends
source: [02-VERIFICATION.md]
started: 2026-05-17T00:00:00Z
updated: 2026-05-17T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end playbook run lights up all three backends

expected: All three containers (loki, tempo, mimir) reach healthy/running state within ~90s; `verify.yml` in-network curl probes succeed inside each role; a second playbook run reports `changed=0` in the PLAY RECAP.

command: `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags loki,tempo,mimir --ask-vault-pass`

prereqs: Live Docker daemon on the target host, SSH-reachable, MinIO already up from Phase 1, populated `inventory/example-homelab/group_vars/all/vault.yml` (decrypted via `ansible-vault edit`) with `vault_minio_root_user` / `vault_minio_root_password` AND the D-27 aliases `vault_loki_s3_access_key`/`_secret_key`, `vault_tempo_s3_access_key`/`_secret_key`, `vault_mimir_s3_access_key`/`_secret_key`.

result: [pending]

### 2. Loki write path lands chunks in MinIO

expected: HTTP 204 from Loki on the synthetic push; a fresh object key visible under `loki-chunks` bucket within ~10s.

command (inside the telemetron Docker network — Loki's `verify.yml` already runs this as a one-shot curlimages/curl container during the playbook):

```sh
curl -sv -XPOST -H 'Content-Type: application/json' \
  -d '{"streams":[{"stream":{"job":"uat"},"values":[["'"$(date +%s%N)"'","hello loki"]]}]}' \
  http://loki:3100/loki/api/v1/push
mc ls --json local/loki-chunks | head
```

result: [pending]

### 3. Tempo OTLP/HTTP push reaches WAL

expected: Tempo returns HTTP 200 on the synthetic OTLP/HTTP POST; trace lands in the WAL within seconds. (Single-trace block flush is non-deterministic per Phase 2 RESEARCH Finding 8 — visible-in-Grafana check is deferred to Phase 4.)

command (inside the telemetron Docker network — Tempo's `verify.yml` already runs this):

```sh
curl -sv -XPOST -H 'Content-Type: application/json' \
  -d '<minimal-otlp-trace-json>' \
  http://tempo:14318/v1/traces
```

result: [pending]

### 4. Standard OTLP ports :4317 / :4318 are FREE on the host (BACK-05 intent)

expected: `ss -tlnp` shows only Loki HTTP (:3100), Tempo HTTP (:3200), Mimir HTTP (:9009) — and only when the corresponding `*_publish_host: true` override is set. Tempo's OTLP receivers are on `:14317`/`:14318` inside the Docker network and MUST NOT be bound to the host, leaving the standard OTLP pair free for the Phase 3 OTel Collector.

command:

```sh
ss -tlnp | grep -E ':(4317|4318|14317|14318|3100|3200|9009)\b'
```

result: [pending]

### 5. Idempotent second run reports changed=0

expected: PLAY RECAP shows `changed=0` for all three roles on the second consecutive run against the converged host. Verifies the W6 single-handler pattern + `state: started + recreate: false` + handler-only restarts work end-to-end.

command:

```sh
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags loki,tempo,mimir --ask-vault-pass
# re-run immediately:
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags loki,tempo,mimir --ask-vault-pass
```

result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
