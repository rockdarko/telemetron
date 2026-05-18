---
gsd_state_version: 1.0
milestone: v1.11.1
milestone_name: milestone
status: executing
stopped_at: Completed 03-01-node-exporter-PLAN.md
last_updated: "2026-05-18T13:35:32.987Z"
last_activity: 2026-05-18
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 10
  completed_plans: 7
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-17)

**Core value:** A homelab operator can clone the repo, edit one hostname in the example inventory, run a single Ansible playbook, and end up with a working LGTM + Alertmanager + hook-router observability plane on a single Docker host.
**Current focus:** Phase 03 — ingest-plane

## Current Position

Phase: 03 (ingest-plane) — EXECUTING
Plan: 2 of 4
Status: Ready to execute
Last activity: 2026-05-18

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-foundation-storage P02 | 4 | 3 tasks | 8 files |
| Phase 01-foundation-storage P01 | 8min | 3 tasks | 4 files |
| Phase 01-foundation-storage P03 | 8min | 3 tasks | 9 files |
| Phase 02-telemetry-backends P01 | 7 min | 3 tasks | 12 files |
| Phase 02-telemetry-backends P02 | 8 min | 3 tasks | 11 files |
| Phase 02-telemetry-backends P03 | 7 min | 3 tasks | 11 files |
| Phase 03-ingest-plane P01 | 7min | 8 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work (Phase 1):

- MinIO bucket bootstrap is a blocking step inside the `minio` role — downstream backends do not start until `mc mb --ignore-existing` exits for all five buckets (highest-impact M1 pitfall).
- Pinned MinIO `RELEASE.2025-04-22T22-12-26Z` with loud README note; Garage migration queued for a future milestone.
- All vault references use `vault_<role>_<purpose>` naming; `.vault_pass` in `.gitignore`; `vault.yml.example` ships in `inventory/example-homelab/`.
- INSPQ grep gate (`inspq|qc\.ca|montreal|québec|vault_inspq_` + non-ASCII check) is established in Phase 1 and enforced on every role port from Phase 2 onward.
- [Phase 01-foundation-storage]: telemetron Docker bridge network created in playbook pre_tasks tagged [always, network], not in any role (D-04)
- [Phase 01-foundation-storage]: Five MinIO buckets in storage.yml (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts) consumed by Phase 2 roles
- [Phase 01-foundation-storage]: vault_<role>_<purpose> naming pattern established; vault.yml gitignored; vault.yml.example committed with CHANGE_ME placeholders
- [Phase 01-foundation-storage]: Drop application_web_docker from M1: reverse-proxy-agnostic design; network plumbing moves to playbook pre_tasks (D-01, D-04)
- [Phase 01-foundation-storage]: Drop postgres from M1: Grafana uses embedded SQLite; FOUND-03 removed from REQUIREMENTS.md (D-02)
- [Phase 01-foundation-storage]: M1 role count is 14: alertmanager, fluentbit, grafana, hook_router, karma, loki, mimir, minio, nfsd, node_exporter, opentelemetry, prometheus, promlens, tempo (D-03)
- [Phase 01-foundation-storage]: Per-role port-acceptance gates established in Phase 1 (D-21): grep, image-pin, vault, idempotency, healthcheck+restart, README schema — canonical reference in roles/README.md
- [Phase 01-foundation-storage]: ansible.cfg with roles_path=roles is required at project root for ansible-playbook to find roles/ from any working directory -- established in Plan 03 (confirmed by syntax-check failure without it)
- [Phase 01-foundation-storage]: minio role canonical patterns established (D-10a docker_container_info HEALTHCHECK poll, W6 single-handler, W7 changed_when:false for mc tasks, W8 mc ls --json verify, OPS-03 README schema) -- Phase 2-6 roles mirror this template
- [Phase 02-telemetry-backends]: Loki image pinned to grafana/loki:3.7.2 with TSDB schema v13 and -target=all monolithic CLI; auth_enabled:false (D-26); explicit gRPC port pin 9095 (D-28)
- [Phase 02-telemetry-backends]: D-27 per-backend vault key surface established: vault_loki_s3_access_key / vault_loki_s3_secret_key alias to vault_minio_root_user / vault_minio_root_password -- cheap forward-compat for the deferred per-backend MinIO IAM hardening
- [Phase 02-telemetry-backends]: D-25 INSPQ grep gate is interpreted as code/config-only (excluding README documentation) so the D-25-mandated 'Deviations from upstream INSPQ' README section can document the audit without tripping the gate
- [Phase 02-telemetry-backends]: Tempo image pinned to grafana/tempo:2.10.5 with -target=all monolithic CLI; D-29/BACK-05 OTLP receivers on internal-only :14317/:14318; D-28 gRPC port pin 9096
- [Phase 02-telemetry-backends]: D-34 dual-knob retention -- BOTH block_retention 168h AND compacted_block_retention 1h in rendered config with inline Pitfall 10 citation; single-knob silently fails (highest-impact M1 Tempo pitfall)
- [Phase 02-telemetry-backends]: D-38 resolved to path (b) -- metrics-generator [service-graphs, span-metrics, local-blocks] persists to local WAL at /var/tempo/generator/wal; zero remote_write in rendered config (Tempo startup decoupled from Mimir)
- [Phase 02-telemetry-backends]: Conditional Docker HEALTHCHECK pattern via tempo_healthcheck_enabled + Ansible omit magic value -- handles RESEARCH Finding 6 MEDIUM-confidence distroless health-binary uncertainty; image probe confirmed Outcome B (-version proxy) for Tempo 2.10.5
- [Phase 02-telemetry-backends]: Mimir image pinned to grafana/mimir:3.0.6 with -target=all monolithic CLI; D-28 gRPC port 9097 (completes no-clash port trinity: Loki 9095 / Tempo 9096 / Mimir 9097)
- [Phase 02-telemetry-backends]: D-26 multitenancy_enabled:false in Mimir -- single-tenant anonymous; Phase 3 Prometheus remote_write needs no X-Scope-OrgID header
- [Phase 02-telemetry-backends]: D-36 / Pitfall 11 + Pitfall 3 five-knob monolithic tuning in Mimir (max_global_series_per_user 500000, max_global_series_per_metric 100000, query_store_after 12h, bucket_store.sync_interval 5m, compactor.cleanup_interval 5m) -- all five inline-cited in rendered config; upstream had ZERO of these guards (highest-impact D-25 improvement)
- [Phase 02-telemetry-backends]: D-39 / BACK-04 / Pitfall G three-distinct-bucket S3 trinity in Mimir -- blocks_storage.s3.bucket_name=mimir-blocks, ruler_storage.s3.bucket_name=mimir-ruler, alertmanager_storage.s3.bucket_name=mimir-alerts; Mimir refuses to start sharing bucket+prefix across stores
- [Phase 02-telemetry-backends]: Mimir image probe confirmed Outcome B: no native -health flag in grafana/mimir:3.0.6; default mimir_healthcheck_test=[CMD,/bin/mimir,-version] binary-alive proxy; authoritative readiness gate is verify task's /ready curl probe -- reuses Plan 02-02 Tempo conditional-healthcheck pattern verbatim
- [Phase 02-telemetry-backends]: Phase 2 FEATURE-COMPLETE: deploy_docker.yml roles list is minio -> loki -> tempo -> mimir in dependency order; D-27 vault alias surface complete (six keys: 2x Loki + 2x Tempo + 2x Mimir aliasing to MinIO root creds); canonical role template proven across four roles
- [Phase 03-ingest-plane]: Image registry: Quay (quay.io/prometheus/node-exporter) over Docker Hub matches Phase-1 alertmanager registry choice and avoids Docker Hub rate-limit risk
- [Phase 03-ingest-plane]: node_exporter pinned to v1.11.1 (RESEARCH Finding 6, 2026-04-07 release) -- corrects CONTEXT.md's stale v1.8.x mention
- [Phase 03-ingest-plane]: Conditional-HEALTHCHECK Outcome B (--version binary-alive proxy) is the safe default for from-scratch node_exporter image; authoritative readiness gate is verify task's in-network /metrics curl asserting node_cpu_seconds_total
- [Phase 03-ingest-plane]: Container hardening (read-only/cap_drop/no-new-privileges/tmpfs/pids_limit) kept from upstream but guarded by node_exporter_container_hardening_enabled knob -- six fields collapse to omit when false for RHEL/SELinux flexibility
- [Phase 03-ingest-plane]: Phase-3 canonical role shape (Wave 1) proven on a stateless no-config role: no rendered config dir, no Docker volume, three RO bind-mounts (/proc /sys /), pid_mode host -- template for subsequent Phase-3 plans

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-05-18T13:35:21.926Z
Stopped at: Completed 03-01-node-exporter-PLAN.md
Resume file: None
