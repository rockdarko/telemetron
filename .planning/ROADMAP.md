# Roadmap: Telemetron

## Milestones

- ✅ **v1.0.0 — M1 — LGTM observability plane on Docker** — Phases 1-6 (shipped 2026-05-19 on leviathan)
- 📋 **v2 (TBD)** — scoping awaits `/gsd:new-milestone`. Candidates: Garage migration, hook router, distributed/Kube path, arm64, multi-host inventory.

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

### 📋 v2 (planning)

No active phases. Scope via `/gsd:new-milestone`.

## Progress

| Phase | Milestone | Plans Complete | Status   | Completed  |
|-------|-----------|----------------|----------|------------|
| 1     | v1.0.0    | 3/3            | Complete | 2026-05-17 |
| 2     | v1.0.0    | 3/3            | Complete | 2026-05-17 |
| 3     | v1.0.0    | 5/5            | Complete | 2026-05-18 |
| 4     | v1.0.0    | 2/2            | Complete | 2026-05-19 |
| 04.1  | v1.0.0    | 1/1            | Complete | 2026-05-19 |
| 5     | v1.0.0    | 8/8            | Complete | 2026-05-19 |
| 6     | v1.0.0    | 4/4            | Complete | 2026-05-19 |

## Backlog

Captured during M1 execution. Promoted backlog phases live under
`.planning/milestones/v1.0.0-phases/999.x-*/` as raw notes; promote with
`/gsd:review-backlog` when triaging v2 scope.

### Phase 999.1: Mimir blocks_retention_period — re-wire under per-tenant `limits:` (BACKLOG)

**Goal:** [Captured for future planning]

Context:
- Phase 2 UAT removed `compactor.blocks_retention_period` from `mimir.yaml.j2` because Mimir 3.0 moved it out of `compactor.Config`. Mimir crashed at parse with "field blocks_retention_period not found in type compactor.Config".
- The intended value (`telemetron_default_metric_retention`, default 30d) is now silently dropped — Mimir falls back to its built-in default of 1 week.
- `mimir_compactor_blocks_retention_period` var still defined in `roles/mimir/defaults/main.yml` but no template references it (orphan dead code).
- Right home in Mimir 3.0 is the per-tenant `limits:` block: `limits.compactor_blocks_retention_period`.

### Phase 999.2: Tempo compactor.block_ranges_period — clean up or re-wire (BACKLOG)

**Goal:** [Captured for future planning]

Context:
- Phase 2 UAT removed `compactor.compaction.block_ranges_period` from `tempo.yaml.j2` because Tempo 2.10 dropped the field from `tempodb.CompactorConfig`.
- `tempo_compactor_block_ranges_period: 5m` var still exists in `roles/tempo/defaults/main.yml` but is no longer referenced (orphan dead code).
- Either delete the var (cosmetic cleanup) OR re-wire to the actual Tempo 2.10 knob `-compactor.compaction.compaction-window` (controls compaction time-range; default 1h0m).

### Phase 999.3: Fluent Bit timestamp_fallback — re-enable with FB-4-compatible syntax (BACKLOG)

**Goal:** [Captured for future planning]

Context:
- Phase 3 UAT disabled the `[FILTER] modify` block that added `@timestamp ${ingest_time}` because FB 4.2.3 rejected it with "Invalid operation add : @timestamp in configuration". Suspected causes: (a) `${ingest_time}` isn't a defined env var so substitution leaves value empty, (b) keys starting with `@` may need quoting in FB 4.
- Currently commented out in `roles/fluentbit/templates/fluent-bit.conf.j2`. Docker logs include their own timestamp so the fallback is a no-op for the homelab Docker-tail path — but PITFALLS.md Pitfall 6 Mode 2 says this is the defensive safety net for log sources without timestamps.
- Right fix: either inject `ingest_time` as a real FB env var (e.g. via the `record_modifier` filter using `Record ingest_time ${HOSTNAME}` style), or switch to FB's native `Time_Key` / `Time_Format` mechanism for the fallback.

### Phase 999.4: Reconcile FB 5-label spec with OTel-first ingest reality (BACKLOG)

**Goal:** [Captured for future planning]

Context:
- Phase 3 SC5 spec calls for Loki labels exactly `{host, env, service, job, level}`. Live Loki labels on leviathan are `{host, job, service_name}` — `service_name` is OTel's resource-attribute convention (`service.name` → `service_name`) surfaced by the OTel Collector's `otlphttp/loki` exporter, not FB's intended `service` label.
- The high-cardinality leak gate IS working (no `container_id`/`image_id` leaks); this is a naming-convention drift, not a correctness bug.
- Three resolution paths: (a) accept that OTel-pushed logs surface OTel attribute names; rewrite the SC5 spec accordingly. (b) Wire FB's enriched labels to overwrite OTel attributes on the Loki side. (c) Move canonical naming to a relabel rule on the OTel Collector's `loki` exporter side (cleanest — single place owns the label contract).
