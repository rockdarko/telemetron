# Roadmap: Telemetron

## Milestones

- ✅ **v1.0.0 — M1 — LGTM observability plane on Docker** — Phases 1-6 (shipped 2026-05-19 on leviathan)
- ✅ **v1.1.0 — Garage migration + backlog sweep** — Phases 7-9 (shipped 2026-05-28 on leviathan)
- 📋 **v1.2.0 — Operator Undeploy Path** — Phases 10-12 (in progress — started 2026-05-28)

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

### 📋 v1.2.0 — Operator Undeploy Path (Phases 10-12)

- [x] **Phase 10: Per-Role Uninstall Surface** — every deploy role gains `tasks/uninstall.yml`; container stop + removal, role-private config dir cleanup, named volumes preserved by default; `roles/README.md` Gate 10 documents the contract (TBD plans) (completed 2026-05-29)
- [ ] **Phase 11: Undeploy Orchestrator + Safety + Idempotency** — `playbooks/undeploy_docker.yml` reverse-order orchestrator; three opt-in purge flags (`telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images`); pre-task WARNING messages for irreversible ops; live UAT on leviathan (idempotency + full cycle); same `--ask-vault-pass` and `--tags <role>` UX as deploy (5 plans complete, gap closure pending for G-01 Garage orphan-key recovery defect)
- [ ] **Phase 12: Documentation Cascade** — `docs/quickstart.md` gains `## Removing Telemetron` section; root `README.md` gains "When you're done evaluating" link; all 12 deployed role READMEs + nfsd gain one-line Uninstall reference; `roles/README.md` Gate 10 wording finalized (TBD plans)

## Phase Details

### Phase 10: Per-Role Uninstall Surface

**Goal**: Every deploy role can cleanly remove its own container and config artifacts, leaving named Docker volumes untouched, so the Phase 11 orchestrator has a tested uninstall task to call for each role.
**Depends on**: Nothing — all changes are confined to individual role directories
**Requirements**: UNDEPLOY-02
**Success Criteria** (what must be TRUE):
  1. `roles/<name>/tasks/uninstall.yml` exists for all 12 deployed roles (alertmanager, fluentbit, garage, grafana, karma, loki, mimir, node_exporter, opentelemetry, prometheus, tempo) plus nfsd
  2. Running a role's uninstall task stops and removes its container; `docker ps -a | grep <role>` returns nothing afterward
  3. Running a role's uninstall task removes the role's config directory under `/opt/telemetron/<role>/`; `ls /opt/telemetron/<role>/` returns "no such file" afterward
  4. Running a role's uninstall task leaves its named Docker volume intact; `docker volume ls | grep telemetron_<role>` still returns the volume
  5. Re-running the uninstall task on an already-clean host (container absent, config dir absent) produces `changed=0` — uninstall is idempotent
  6. `roles/README.md` documents "every deploy role ships a tested uninstall path" as Gate 10 alongside the existing 9 gates (Gate 9 is the Grafana datasources-resolve-real-data gate added in Plan 05-01)
**Plans**: 6 plans
  - [x] 10-01-PLAN.md — uninstall.yml for 7 uniform backend roles (alertmanager, grafana, karma, loki, mimir, prometheus, tempo)
  - [x] 10-02-PLAN.md — uninstall.yml for fluentbit (preserves D-50 buffer volume)
  - [x] 10-03-PLAN.md — uninstall.yml for garage (4-task strict order: container -> WARN -> s3-credentials -> config dir; preserves both meta + data volumes)
  - [x] 10-04-PLAN.md — uninstall.yml for edge cases: node_exporter (container-only) + opentelemetry (no volume, no host-socket touch)
  - [x] 10-05-PLAN.md — uninstall.yml for nfsd (blockinfile state=absent with identical marker + exportfs -ra; no OS-package removal, no service stop, no share-root cleanup)
  - [x] 10-06-PLAN.md — Gate 10 documentation in roles/README.md (Per-role uninstall contract; D-148)

---

### Phase 11: Undeploy Orchestrator + Safety + Idempotency

**Goal**: Operators can run a single `ansible-playbook playbooks/undeploy_docker.yml` command against their inventory to cleanly remove the Telemetron stack from a Docker host, with conservative defaults that preserve data and opt-in flags for irreversible cleanup.
**Depends on**: Phase 10 (per-role uninstall tasks must exist before the orchestrator calls them)
**Requirements**: UNDEPLOY-01, PURGE-01, PURGE-02, OPS-01, OPS-02
**Success Criteria** (what must be TRUE):
  1. Running `ansible-playbook playbooks/undeploy_docker.yml` against `inventory/example-homelab` or `inventory/leviathan` removes all 12 deployed containers and the `telemetron` Docker bridge network; `docker ps -a | grep telemetron` and `docker network ls | grep telemetron` both return nothing afterward
  2. After a default (no extra-vars) undeploy run, all named Docker volumes under the `telemetron_*` prefix are still present; `docker volume ls | grep telemetron_` returns the same list as before
  3. Running the playbook twice in sequence on an already-clean host produces `changed=0` in the PLAY RECAP of the second run; running it after a partial deploy (some roles up, some not) removes whatever is present and reports `failed=0`
  4. Running with `--extra-vars "telemetron_purge_data=true"` removes all `telemetron_*` named Docker volumes; each irreversible flag emits a "WARNING: irreversible" pre-task message before acting
  5. Running `--extra-vars "telemetron_purge_host_dirs=true"` removes the `/opt/telemetron/` tree (including the Garage S3 credential file at `/opt/telemetron/garage/s3-credentials`); running `--extra-vars "telemetron_purge_images=true"` removes the exact pinned image tags Telemetron deployed without touching other tags on the host
  6. After a default undeploy, running `ansible-playbook playbooks/deploy_docker.yml` brings the full 12-container stack back up to healthy; after a purge-data undeploy, the re-deploy starts from scratch with new Garage S3 credentials and empty Loki/Tempo/Mimir buckets
**Plans**: 6 plans
  - [x] 11-01-PLAN.md — image-only purge.yml for karma + node_exporter + opentelemetry (3 roles, no volumes; D-154 failed_when:false; D-159 WARN template)
  - [x] 11-02-PLAN.md — single-volume + single-image purge.yml for alertmanager + fluentbit (buffer-volume) + mimir + prometheus + tempo (5 roles)
  - [x] 11-03-PLAN.md — special-case purge.yml for garage (2-volume loop) + grafana (2-image loop) + loki (2-image loop)
  - [x] 11-04-PLAN.md — playbooks/undeploy_docker.yml orchestrator (reverse-deploy order; D-160 banner; D-150 post_tasks network removal; D-155 parent host_dirs rmdir)
  - [x] 11-05-PLAN.md — 11-HUMAN-UAT.md 7-scenario checklist for live-leviathan UAT (D-161 + D-162 + D-163 + D-164)
  - [ ] 11-06-PLAN.md — gap-closure: patch roles/garage/tasks/bootstrap.yml to be S3-key-create idempotent against preserved metadata (closes G-01 orphan-key recovery defect + unblocks G-02 scenario 4b re-run)

---

### Phase 12: Documentation Cascade

**Goal**: Operators can find the complete undeploy story from first contact (root README) through to the reference details (quickstart.md) and per-role uninstall hints, without having to read source code or run `--help`.
**Depends on**: Phase 11 (final playbook flags and behavior must be settled before docs are written)
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. `docs/quickstart.md` contains a `## Removing Telemetron` section that covers the default conservative command line, all three opt-in purge flags with example invocations, the order-of-operations expectation (containers must come down before volumes can be purged), and the manual `docker volume rm` / `docker image rm` fallback
  2. Root `README.md` Quick Start section contains a "When you're done evaluating" line that links to `docs/quickstart.md#removing-telemetron`
  3. Every deployed role README (12 roles + nfsd) contains a one-line "Uninstall:" entry in its Operator Surface section pointing to `playbooks/undeploy_docker.yml --tags <role>`
  4. `roles/README.md` documents Gate 10 ("every deploy role ships a tested uninstall path") in the per-role port-acceptance gates section, in the same style and detail level as Gates 1-9
**Plans**: TBD

---

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
| 10    | v1.2.0    | 6/6 | Complete   | 2026-05-29 |
| 11    | v1.2.0    | 5/6 | Gap closure | 2026-05-30 |
| 12    | v1.2.0    | 0/?            | Not started | -          |

## Backlog

Empty at v1.1.0 close. All four prior M1 backlog items (999.1–999.4) were absorbed into Phases 7 + 9 of v1.1.0 (see `.planning/milestones/v1.1.0-ROADMAP.md`).

v1.2.0 scope is fully mapped across Phases 10-12 — no backlog items at milestone start.
