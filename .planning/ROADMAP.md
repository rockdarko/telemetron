# Roadmap: Telemetron

## Milestones

- ✅ **v1.0.0 — M1 — LGTM observability plane on Docker** — Phases 1-6 (shipped 2026-05-19 on leviathan)
- ✅ **v1.1.0 — Garage migration + backlog sweep** — Phases 7-9 (shipped 2026-05-28 on leviathan)
- 📋 **v1.2.0 — TBD** (not yet started — run `/gsd-new-milestone` to define)

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

<details>
<summary>✅ v1.1.0 — Garage migration + backlog sweep (Phases 7-9) — SHIPPED 2026-05-28</summary>

- [x] **Phase 7: Backlog Regression Fixes** — Mimir retention re-wired under `limits:`, Tempo orphan var rebound to `compaction_window`, Fluent Bit timestamp fallback re-enabled via Lua (completed 2026-05-27; 1/1 plan)
- [x] **Phase 8: Garage Role + Backend Retargeting** — New `roles/garage/` replaces `roles/minio/`; Loki/Tempo/Mimir S3 configs retargeted to `garage:3900`; MinIO removed; Garage self-metrics scrape wired (completed 2026-05-27 + live UAT 2026-05-28; 3/3 plans)
- [x] **Phase 9: Label Reconciliation** — `service` → `service_name` across enrich.lua + dashboard verify-only audit; OTel Collector `transform/strip_namespace` processor on logs pipeline + quickstart Upgrade notes (completed 2026-05-28; 2/2 plans)

Full phase details: `.planning/milestones/v1.1.0-ROADMAP.md`
Phase artifacts (plans/summaries/UAT/verification): `.planning/phases/0[7-9]-*/` (not yet archived to `milestones/v1.1.0-phases/`)
Requirements outcomes (9/9 v1.1.0 reqs validated via live leviathan UAT): `.planning/milestones/v1.1.0-REQUIREMENTS.md`
Tag: `v1.1.0`

</details>

### 📋 v1.2.0 — TBD (not yet started)

Run `/gsd-new-milestone` to scope the next milestone. Candidate themes from CLAUDE.md + carried-forward requirements:
- Hook router (ALERT-V2-01..05) — Alertmanager webhook → CI bridge
- Distributed-mode (DIST-01..03) — multi-host Loki/Tempo/Mimir + HAProxy + Kubernetes/OpenShift path
- arm64 / multi-arch (ARCH-01..02)
- Documentation deep-dives (DOCS-V2-01..07)

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
| 7     | v1.1.0    | 1/1            | Complete    | 2026-05-27 |
| 8     | v1.1.0    | 3/3            | Complete    | 2026-05-27 |
| 9     | v1.1.0    | 2/2            | Complete    | 2026-05-28 |

## Backlog

Empty at v1.1.0 close. All four prior M1 backlog items (999.1–999.4) were absorbed into Phases 7 + 9 of v1.1.0 (see `.planning/milestones/v1.1.0-ROADMAP.md`).

New backlog items, if any, will be added under v1.2.0 scoping.
