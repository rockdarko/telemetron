# Requirements: Telemetron

**Milestone:** v1.1.0 — Garage migration + backlog sweep
**Defined:** 2026-05-26
**Core Value:** A homelab operator can clone the repo, edit one hostname in the example inventory, run a single Ansible playbook, and end up with a working observability plane on a single Docker host.

## v1.1.0 Requirements

Requirements for the v1.1.0 patch milestone. Each maps to roadmap phases.

### Storage migration (STORE)

- [ ] **STORE-01**: Operator can run the playbook and have Garage (`dxflrs/garage:v2.3.0`) running on the `telemetron` Docker bridge with S3 API on `:3900`, admin on `:3903`, single-node layout assigned+applied, and all 5 buckets (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`) bootstrapped with a key that has read/write/owner permissions — using the `docker_container_exec` bootstrap pattern established in M1.
- [ ] **STORE-02**: Loki, Tempo, and Mimir S3 configs are retargeted from `minio:9000` to `garage:3900`; all three backends successfully read and write objects through Garage's S3 API. Loki uses `object_store: aws` (defensive G-6 mitigation). Credential vars renamed from `minio_root_*` to `garage_*` across defaults, inventory, and `secrets.yml.example`.
- [ ] **STORE-03**: The `roles/minio/` directory, `minio/mc` image references, and all MinIO-specific vars (`minio_*`, `mimir_mc_image`) are removed from the codebase. `playbooks/deploy_docker.yml` shows `garage` in the storage slot. Documentation (architecture, README, inventory, roles/README, CLAUDE.md) reflects Garage replacing MinIO with updated port tables.

### Backend config regressions (CONFIG)

- [ ] **CONFIG-01**: Mimir retention is enforced — `limits.compactor_blocks_retention_period` is wired in `mimir.yaml.j2` with the operator-configured value (default `30d` via `mimir_compactor_blocks_retention_period`). Blocks older than the retention period are compacted away on the next compactor cycle.
- [ ] **CONFIG-02**: Tempo orphan var `tempo_compactor_block_ranges_period` is re-wired to `compactor.compaction.compaction_window` in `tempo.yaml.j2` (default `1h`), giving operators the compaction-range knob that was silently dropped when Tempo 2.10 removed the old field name.

### Ingest pipeline fixes (INGEST)

- [ ] **INGEST-01**: Fluent Bit logs without embedded timestamps receive an ingest-time `@timestamp` fallback via a Lua function in `enrich.lua` (replaces the disabled `[FILTER] modify` block that used the invalid `${ingest_time}` substitution). The fallback only writes `@timestamp` when absent — it never overwrites a valid source timestamp.
- [ ] **INGEST-02**: Loki labels unify on `service_name` (OTel convention) — `enrich.lua` emits `record["service_name"]` instead of `record["service"]`, the allowlist filter references are updated, and all 7 curated Grafana dashboard JSONs are swept for `{service=` → `{service_name=` so that FB-originated and OTLP-originated logs share one queryable label.
- [ ] **INGEST-03**: OTel Collector adds a `transform` processor before the `otlphttp/loki` exporter that strips the `service.namespace` resource attribute, preventing the `namespace/service` concatenation corruption documented in upstream issue #32497.

### Operational (OPS)

- [ ] **OPS-01**: Garage self-metrics at `:3903/metrics` are scraped (via Prometheus scrape config or OTel Collector) with `metrics_token` bearer auth, so operators can see Garage S3 request counts, object counts, and storage usage in Grafana.

## Future Requirements

Deferred to later milestones. Tracked but not in current roadmap.

### Hook router (ALERT-V2-01..05)

- **ALERT-V2-01**: Alertmanager webhook receiver dispatches to a configurable CI/automation endpoint
- **ALERT-V2-02**: Per-rule label allowlist gates which alerts trigger automation
- **ALERT-V2-03**: Per-(alertname, job) rate limiting prevents CI flooding
- **ALERT-V2-04**: Jenkins `buildWithParameters` auth token sourced from vault
- **ALERT-V2-05**: Sample runbook bundles ship for common alert→job mappings

### Distributed / scale-out

- **DIST-01**: Multi-host example inventory with distributed-mode Loki/Tempo/Mimir
- **DIST-02**: HAProxy role for load-balancing distributed backends
- **DIST-03**: Kubernetes / OpenShift deployment path (`playbooks/deploy_kube.yml`)

### Multi-arch

- **ARCH-01**: arm64 support tested on Pi 5 / Apple Silicon
- **ARCH-02**: Multi-arch CI matrix

### Documentation (DOCS-V2-01..07)

- **DOCS-V2-01**: `docs/alerts.md` — alert-rules reference + runbook patterns
- **DOCS-V2-02**: `docs/retention.md` — per-backend retention knobs + lifecycle
- **DOCS-V2-03**: `docs/fluentbit-timestamps.md` — timestamp handling deep-dive
- **DOCS-V2-04**: `docs/hook-router.md` — webhook bridge config + sample bundles
- **DOCS-V2-05**: `docs/instrumentation-otel.md` — instrumenting apps to feed Telemetron
- **DOCS-V2-06**: `docs/migration-from-inspq.md` — porting guide for existing INSPQ users
- **DOCS-V2-07**: `docs/metrics.md` — metrics naming, cardinality, Mimir tuning

## Out of Scope

Explicitly excluded from v1.1.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Data migration tooling (rclone automation) | Leviathan is fresh-start; production operators can use rclone manually per the Garage role README. Automating the stop-sync-start procedure is v2+ scope. |
| `garage-webui` sidecar | Adds a container to the default footprint for a UI that most homelab operators won't need. Defer until user demand emerges. |
| Garage multi-node / replication_factor > 1 | Single-host Docker only in v1.1.0. Multi-node Garage lands alongside the distributed-mode milestone. |
| Fluent Bit 5.x upgrade | v5.0 GA May 2026 — too new; stay on 4.2.3 until shaken out. |
| Component version bumps (Loki, Tempo, Mimir, etc.) | v1.1.0 is a storage migration + config fix milestone, not a version-bump cycle. Bump separately via the quarterly-bump strategy. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONFIG-01 | Phase 7 | Pending |
| CONFIG-02 | Phase 7 | Pending |
| INGEST-01 | Phase 7 | Pending |
| STORE-01 | Phase 8 | Pending |
| STORE-02 | Phase 8 | Pending |
| STORE-03 | Phase 8 | Pending |
| OPS-01 | Phase 8 | Pending |
| INGEST-02 | Phase 9 | Pending |
| INGEST-03 | Phase 9 | Pending |

**Coverage:**
- v1.1.0 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-05-26*
*Last updated: 2026-05-26 after roadmap creation (phases 7-9 assigned)*
