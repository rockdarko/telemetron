# Roadmap: Telemetron

## Milestones

- ✅ **v1.0.0 — M1 — LGTM observability plane on Docker** — Phases 1-6 (shipped 2026-05-19 on leviathan)
- 📋 **v1.1.0 — Garage migration + backlog sweep** — Phases 7-9 (planning)

## Phases

<details>
<summary>✅ v1.0.0 — M1 (Phases 1-6) — SHIPPED 2026-05-19</summary>

- [x] **Phase 1: Foundation & Storage** — MinIO bucket bootstrap (5 buckets), `telemetron` Docker bridge network, `inventory/example-homelab/group_vars/all/` skeleton, 8 cross-cutting port-acceptance gates established in `roles/README.md` (3/3 plans)
- [x] **Phase 2: Telemetry Backends** — Loki 3.7.2 + Tempo 2.10.5 + Mimir 3.0.6 as monolithic-mode roles against MinIO; Tempo OTLP receivers moved to alt ports `:14317`/`:14318` so OTel Collector can claim the standard pair (3/3 plans)
- [x] **Phase 3: Ingest Plane** — Prometheus 3.11.3 + OTel Collector Contrib 0.152.0 + Fluent Bit 4.2.3 + node_exporter 1.11.1; Pitfall 5 OOM-resistance pack, 4 baseline alert rules + extras knob, FB Lua-enrichment promoting `org.telemetron.{service,job}` Docker labels to Loki labels (no Docker socket needed) (5/5 plans)
- [x] **Phase 4: Alert Plane** — Alertmanager v0.32.1 single-instance with null receiver, D-61 routing intervals, D-63 inhibit rule, persistent `telemetron_alertmanager_data` volume; Prometheus alerting block wired to it; Gate 8 added (parent-dir bind mounts) + auto_remove race fix in alertmanager verify (2/2 plans)
- [x] **Phase 04.1 (INSERTED): Drop vault_ prefix** — rename all `vault_*`-prefixed sensitive vars across 4 roles + `vault.yml.example` → `secrets.yml.example` + doc cascade. Reason: prefix added no value and implied tooling enforcement Ansible doesn't provide (D-90) (1/1 plan)
- [x] **Phase 5: UI Plane** — Grafana OSS 13.0.1 with 4-datasource provisioning at hardcoded UIDs + 7 curated dashboards + tracesToLogsV2/derivedFields trace-to-logs (UI-04), Karma v0.130 against Alertmanager via Docker bridge DNS (UI-05), PromLens v0.3.0 marked deprecation candidate (UI-06) (8/8 plans)
- [x] **Phase 6: Opt-in, Orchestration, Docs & Smoke Test** — nfsd opt-in role (default-off, 14th slot), `playbooks/smoke_test.yml` M1 acceptance probe (synthetic OTLP log+metric+trace in Grafana within 60s), three operator docs (`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`), README rewrite + idempotency revalidation (`changed=0` on second deploy of both default and 14-role shapes) (4/4 plans)

Full phase details: `.planning/milestones/v1.0.0-ROADMAP.md`
Phase artifacts (plans/summaries/UAT/verification): `.planning/milestones/v1.0.0-phases/`
Requirements outcomes (37/37 v1 reqs): `.planning/milestones/v1.0.0-REQUIREMENTS.md`
Tag: `v1.0.0`

</details>

### 📋 v1.1.0 — Garage migration + backlog sweep (planning)

- [x] **Phase 7: Backlog Regression Fixes** — Mimir retention re-wired under `limits:`, Tempo orphan var rebound to `compaction_window`, Fluent Bit timestamp fallback re-enabled via Lua (completed 2026-05-27)
- [ ] **Phase 8: Garage Role + Backend Retargeting** — New `roles/garage/` replaces `roles/minio/`; Loki/Tempo/Mimir S3 configs retargeted; MinIO removed; Garage self-metrics scrape wired
- [ ] **Phase 9: Label Reconciliation** — `service` → `service_name` across enrich.lua, dashboard JSONs, and OTel Collector namespace strip

## Phase Details

### Phase 7: Backlog Regression Fixes
**Goal**: Operator can run the playbook on leviathan, and the three live config regressions captured in the v1.0.0 backlog are resolved: Mimir enforces the configured 30-day retention period instead of silently defaulting to 1 week; Tempo exposes the `compaction_window` knob in its rendered config rather than carrying an orphan variable that maps to nothing; and Fluent Bit assigns an ingest-time `@timestamp` to logs that arrive without an embedded timestamp, using a Lua fallback that is compatible with Fluent Bit 4.2.3.
**Depends on**: Nothing — fixes are confined to existing roles and are self-contained template changes
**Requirements**: CONFIG-01, CONFIG-02, INGEST-01
**Success Criteria** (what must be TRUE):
  1. `docker exec telemetron_mimir grep -A1 'limits:' /etc/mimir/mimir.yaml` shows `compactor_blocks_retention_period: 30d` (or the operator-configured value) in the rendered config inside the running container
  2. `docker exec telemetron_tempo grep compaction_window /etc/tempo/tempo.yaml` returns the wired value (default `1h`); no orphan `block_ranges_period` key appears in the file
  3. `docker exec telemetron_fluentbit grep set_ingest_timestamp /fluent-bit/scripts/enrich.lua` returns a match, confirming the Lua fallback function is present; a synthetic log injected without a timestamp field lands in Loki with a valid `@timestamp` within 10 seconds
  4. Back-to-back deploy remains idempotent (`changed=0`) for all three affected roles (mimir, tempo, fluentbit)
**Plans**: 1 plan (07-01)

### Phase 8: Garage Role + Backend Retargeting
**Goal**: Operator can run the playbook on leviathan and have Garage v2.3.0 running in place of MinIO as the S3-compatible object store: the `garage` container is healthy on the `telemetron` bridge with S3 API on `:3900` and admin on `:3903`, single-node layout is assigned and applied, all five buckets (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`) are bootstrapped with a read/write/owner key, Loki and Tempo and Mimir all write through Garage's S3 API successfully, the `minio` role and all MinIO-specific vars are gone from the codebase, and Garage's self-metrics at `:3903/metrics` are scraped by Prometheus or OTel Collector so storage usage appears in Grafana.
**Depends on**: Phase 7 (regression fixes narrow Garage debugging blast radius)
**Requirements**: STORE-01, STORE-02, STORE-03, OPS-01
**Success Criteria** (what must be TRUE):
  1. `docker inspect telemetron_garage --format='{{.State.Health.Status}}'` returns `healthy`; `curl -s http://leviathan:3900/health` (or `curl -s http://leviathan:3903/health`) returns a 200 response confirming the S3 API is up
  2. `docker exec telemetron_garage /garage layout show` returns a layout with at least one node assigned and `replication_factor: 1` applied; `docker exec telemetron_garage /garage bucket list` shows all five buckets (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`)
  3. Running `playbooks/smoke_test.yml` completes with `failed=0` — synthetic OTLP log, metric, and trace data round-trips through Loki, Mimir, and Tempo respectively, all of which are now writing to and reading from Garage
  4. `grep -r 'minio' roles/ playbooks/ inventory/example-homelab/` returns zero matches (excluding inline comments that document the migration); `roles/minio/` directory does not exist; `docker ps` shows no `telemetron_minio` container
  5. `curl -s -H "Authorization: Bearer <garage_admin_token>" http://leviathan:3903/metrics` returns Prometheus-format text with at least one `garage_` metric; the Prometheus or OTel scrape config contains a job targeting `garage:3903`
**Plans**: 3 plans
Plans:
- [ ] 08-01-PLAN.md — Create roles/garage/ (defaults, tasks, template, handlers, meta, README)
- [ ] 08-02-PLAN.md — Retarget Loki/Tempo/Mimir S3 + verify migration + Prometheus Garage scrape + secrets
- [ ] 08-03-PLAN.md — Remove MinIO role + inventory renames + documentation updates + CLAUDE.md

### Phase 9: Label Reconciliation
**Goal**: Operator can query Loki in Grafana and find both Fluent Bit-originated and OTel Collector-originated logs under the single label `service_name` — there is no split between `service` (FB) and `service_name` (OTel) that forces different queries for the same logical service; all seven curated dashboards use `service_name=` in their LogQL matchers; and the OTel Collector strips the `service.namespace` resource attribute before forwarding to Loki, preventing the `namespace/service` concatenation corruption.
**Depends on**: Phase 8 (Garage must be verified stable before applying a breaking Loki label change that forces a re-query of stored data)
**Requirements**: INGEST-02, INGEST-03
**Success Criteria** (what must be TRUE):
  1. `docker exec telemetron_fluentbit grep 'service_name' /fluent-bit/scripts/enrich.lua` returns a match; `grep -r '"service"' roles/fluentbit/` returns zero matches on the Lua label-emit line (only comments or documentation references if any)
  2. Querying `{service_name="fluentbit"}` in Grafana's Loki Explore returns log lines from the Fluent Bit container without needing `{service="fluentbit"}`; querying `{service_name="opentelemetry"}` similarly returns OTel Collector logs, confirming both origins now use the same label key
  3. `grep -r '"service="' roles/grafana/files/dashboards/` returns zero matches; all seven dashboard JSONs use `service_name=` in their LogQL selectors
  4. `docker exec telemetron_opentelemetry grep -A5 'transform' /etc/otelcol/config.yaml` shows a `transform` processor configured to delete `service.namespace` from resource attributes before the `otlphttp/loki` exporter; no `namespace/` prefix appears in Loki log stream labels when queried via `{job="smoke_test"}`
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status      | Completed  |
|-------|-----------|----------------|-------------|------------|
| 1     | v1.0.0    | 3/3            | Complete    | 2026-05-17 |
| 2     | v1.0.0    | 3/3            | Complete    | 2026-05-17 |
| 3     | v1.0.0    | 5/5            | Complete    | 2026-05-18 |
| 4     | v1.0.0    | 2/2            | Complete    | 2026-05-19 |
| 04.1  | v1.0.0    | 1/1            | Complete    | 2026-05-19 |
| 5     | v1.0.0    | 8/8            | Complete    | 2026-05-19 |
| 6     | v1.0.0    | 4/4            | Complete    | 2026-05-19 |
| 7     | v1.1.0    | 1/1 | Complete   | 2026-05-27 |
| 8     | v1.1.0    | 0/3            | Planned    | —          |
| 9     | v1.1.0    | 0/?            | Not started | —          |

## Backlog

All four M1 backlog items (Phases 999.1-999.4) are addressed by v1.1.0 phases:

| Former backlog item | Addressed by |
|---------------------|--------------|
| 999.1: Mimir `blocks_retention_period` re-wire | Phase 7 — CONFIG-01 |
| 999.2: Tempo `block_ranges_period` cleanup | Phase 7 — CONFIG-02 |
| 999.3: Fluent Bit timestamp fallback (FB-4 syntax) | Phase 7 — INGEST-01 |
| 999.4: FB label-spec vs OTel-reality reconciliation | Phase 9 — INGEST-02 |

No open backlog items remain for v1.1.0.
