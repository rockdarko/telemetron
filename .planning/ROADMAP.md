# Roadmap: Telemetron

## Milestones

- ✅ **v1.0.0 — M1 — LGTM observability plane on Docker** — Phases 1-6 (shipped 2026-05-19 on leviathan)
- ✅ **v1.1.0 — Garage migration + backlog sweep** — Phases 7-9 (shipped 2026-05-28 on leviathan)
- ✅ **v1.2.0 — Operator Undeploy Path** — Phases 10-12 (shipped 2026-05-30 on leviathan)
- ✅ **v1.3.0 — Backup & Restore** — Phases 13-15 (shipped 2026-06-05 on leviathan)

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

<details>
<summary>✅ v1.2.0 — Operator Undeploy Path (Phases 10-12) — SHIPPED 2026-05-30</summary>

- [x] **Phase 10: Per-Role Uninstall Surface** — every deploy role gains `tasks/uninstall.yml` (alertmanager, fluentbit, garage, grafana, karma, loki, mimir, node_exporter, opentelemetry, prometheus, tempo + opt-in nfsd); container stop + removal, role-private config dir cleanup, named volumes preserved by default; `roles/README.md` Gate 10 documents the contract (6/6 plans, completed 2026-05-29)
- [x] **Phase 11: Undeploy Orchestrator + Safety + Idempotency** — `playbooks/undeploy_docker.yml` reverse-order orchestrator with D-160 PLAY-start banner; three opt-in purge flags (`telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images`); D-159 per-action WARNING template; live leviathan UAT (7 scenarios incl. G-01 orphan-key self-recovery + G-02 back-to-back idempotency) (6/6 plans, completed 2026-05-30)
- [x] **Phase 12: Documentation Cascade** — `docs/quickstart.md` `## Removing Telemetron` section (120 lines, all 4 DOCS-01 sub-contracts incl. manual `docker volume rm`/`docker image rm` fallback); root README "When you're done evaluating" cross-ref (D-174); 12 role READMEs gain `## Uninstall` H2 sections (11 uniform per D-170 + nfsd divergent per D-172); `roles/README.md` Gate 10 finalization per D-175 (3/3 plans, completed 2026-05-30)

Full phase details: `.planning/milestones/v1.2.0-ROADMAP.md`
Phase artifacts (plans/summaries/UAT/verification): `.planning/phases/1[0-2]-*/` (not yet archived to `milestones/v1.2.0-phases/`)
Requirements outcomes (8/8 v1.2.0 reqs validated via live leviathan UAT): `.planning/milestones/v1.2.0-REQUIREMENTS.md`
Tag: `v1.2.0`

</details>

<details>
<summary>✅ v1.3.0 — Backup & Restore (Phases 13-15) — SHIPPED 2026-06-05</summary>

- [x] **Phase 13: Per-Role Backup & Restore Tasks** — `tasks/backup.yml` + `tasks/restore.yml` for the 4 stateful roles (garage, prometheus, grafana, alertmanager); cold-quiesce model (`docker stop` + `docker_container_info` poll, not `state: stopped`); zstd tarballs at `/opt/telemetron/backups/<role>/<role>-<UTC>.tar.zst`; Garage tarball captures `s3-credentials` host file (D-176); Prometheus restore deletes `/prometheus/lock` after untar; `block:`/`rescue:`/`always:` container-restart guarantee on every backup task (5/5 plans, completed 2026-06-03)
- [x] **Phase 14: Orchestrators + Leviathan HUMAN-UAT** — `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` symmetric orchestrators with the same `--ask-vault-pass` + `--tags <role>` UX as deploy/undeploy; `backup_restore_confirm=true` gate at both orchestrator and per-role level (mirrors v1.2.0 `telemetron_purge_data=true`); restore stops Loki/Tempo/Mimir (Garage writers) before Garage restore + restarts after; bail-out default with `backup_continue_on_failure=true` opt-in; D-160-style PLAY-start banner + D-191 timestamp override. 7-step leviathan UAT round-trip (deploy → smoke → backup → purge-data undeploy → deploy → restore → re-smoke with same `smoke_trace_id`/`smoke_run_id`) verified 6/6 must-haves across 3 rounds with G-01/G-03/G-03-addendum/G-04 closed (9/9 plans, completed 2026-06-05)
- [x] **Phase 15: Documentation Cascade** — Gate 11 in `roles/README.md` codifies "every stateful role ships a tested `tasks/backup.yml` + `tasks/restore.yml` proven on leviathan"; `docs/quickstart.md` `## Backup and restore` H2 with 5 H3s in D-202 order (Backup → Restore → Stop order during Garage restore → Retention → Manual fallback); root README "When something goes wrong" Quick Start cross-ref; 4 stateful role READMEs (garage, prometheus, grafana, alertmanager) gain `## Backup` H2 with full 5-part skeleton; 8 stateless role READMEs (loki, tempo, mimir, fluentbit, karma, node_exporter, opentelemetry, nfsd) gain two-template one-liner (3/3 plans, completed 2026-06-05)

Full phase details: `.planning/milestones/v1.3.0-ROADMAP.md`
Phase artifacts (plans/summaries/UAT/verification): `.planning/milestones/v1.3.0-phases/`
Requirements outcomes (18/18 v1.3.0 reqs validated): `.planning/milestones/v1.3.0-REQUIREMENTS.md`
Tag: `v1.3.0`

</details>

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
| 10    | v1.2.0    | 6/6            | Complete    | 2026-05-29 |
| 11    | v1.2.0    | 6/6            | Complete    | 2026-05-30 |
| 12    | v1.2.0    | 3/3            | Complete    | 2026-05-30 |
| 13    | v1.3.0    | 5/5            | Complete    | 2026-06-03 |
| 14    | v1.3.0    | 9/9            | Complete    | 2026-06-05 |
| 15    | v1.3.0    | 3/3            | Complete    | 2026-06-05 |

## Backlog

Empty. All four prior M1 backlog items (999.1–999.4) were absorbed into Phases 7 + 9 of v1.1.0 (see `.planning/milestones/v1.1.0-ROADMAP.md`).
