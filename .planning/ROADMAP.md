# Roadmap: Telemetron

## Milestones

- ✅ **v1.0.0 — M1 — LGTM observability plane on Docker** — Phases 1-6 (shipped 2026-05-19 on leviathan)
- ✅ **v1.1.0 — Garage migration + backlog sweep** — Phases 7-9 (shipped 2026-05-28 on leviathan)
- ✅ **v1.2.0 — Operator Undeploy Path** — Phases 10-12 (shipped 2026-05-30 on leviathan)
- 🚧 **v1.3.0 — Backup & Restore** — Phases 13-15 (in progress)

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

### 🚧 v1.3.0 — Backup & Restore (In Progress)

- [x] **Phase 13: Per-Role Backup & Restore Tasks** — `tasks/backup.yml` + `tasks/restore.yml` for the 4 stateful roles (garage, prometheus, grafana, alertmanager); cold-quiesce model; zstd tarballs at `/opt/telemetron/backups/<role>/`; block/rescue/always container-restart guarantee (9 requirements: BACKUP-V13-01..04, RESTORE-V13-01..04, OPS-V13-04) (completed 2026-06-03)
- [x] **Phase 14: Orchestrators + Leviathan HUMAN-UAT** — `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml`; confirm-gate, bail-out, and `--tags` cross-cutting UX; live 7-step backup → purge-data undeploy → redeploy → restore → re-smoke round-trip on leviathan (6 requirements: BACKUP-V13-05, RESTORE-V13-05, OPS-V13-01..03, UAT-V13-01) (completed 2026-06-04)
- [ ] **Phase 15: Documentation Cascade** — Gate 11 in `roles/README.md`; `docs/quickstart.md` `## Backup and restore` section + root README cross-ref; per-stateful-role README `## Backup` H2 sections; stateless role README one-liners (3 requirements: DOCS-V13-01..03)

## Phase Details

### Phase 13: Per-Role Backup & Restore Tasks
**Goal**: Operators have a tested, atomic backup and restore task file for each of the 4 stateful roles, each producing a verified tarball or restoring from one without risk of leaving containers in a stopped state.
**Depends on**: Nothing (per-role task files are confined to individual role directories and can be written independently of the orchestrators)
**Requirements**: BACKUP-V13-01, BACKUP-V13-02, BACKUP-V13-03, BACKUP-V13-04, RESTORE-V13-01, RESTORE-V13-02, RESTORE-V13-03, RESTORE-V13-04, OPS-V13-04
**Success Criteria** (what must be TRUE):
  1. Eight new task files exist: `roles/{garage,prometheus,grafana,alertmanager}/tasks/{backup,restore}.yml` — 8 files, none empty.
  2. Each `tasks/backup.yml` stops its container via `ansible.builtin.command: docker stop` (not `community.docker state: stopped`), tars the relevant Docker volume `_data/` path(s) with `--zstd` compression into `/opt/telemetron/backups/<role>/<role>-<UTC-timestamp>.tar.zst` (mode 0600, dest dir mode 0700), then restarts and runs verify — the container is running at the end regardless of tar success or failure (block/rescue/always).
  3. The Garage `tasks/backup.yml` includes both `telemetron_garage_meta` and `telemetron_garage_data` volumes AND the host-mounted `{{ garage_s3_credentials_file }}` in the single tarball — the `s3-credentials` file is captured.
  4. Each `tasks/restore.yml` asserts `backup_restore_confirm == true` (fail-fast gate), runs `tar tf` integrity check on the source tarball, wipes volume `_data/` contents, untars, restarts, and runs verify. The Prometheus `tasks/restore.yml` also deletes the `/prometheus/lock` file after untar and before container start.
  5. Each `tasks/backup.yml` and `tasks/restore.yml` begins with an `ansible.builtin.package: name: zstd state: present` pre-task; a second run on a host that already has `zstd` produces `changed=0` for that task.
  6. Running `ansible-playbook playbooks/backup_docker.yml --tags garage --ask-vault-pass` (substituting any of the 4 role names) on leviathan completes with `failed=0` and the role's container is in a running/healthy state afterward.
**Plans**: 5 plans
- [x] 13-01-PLAN.md — Shared backup vars file + 4 role defaults additions (foundation; wave 1)
- [x] 13-02-PLAN.md — Garage backup.yml + restore.yml (3-entry tarball: meta + data + s3-credentials per D-176)
- [x] 13-03-PLAN.md — Prometheus backup.yml + restore.yml (PP-1 lock-file deletion on restore)
- [x] 13-04-PLAN.md — Grafana backup.yml + restore.yml (entire-volume tar per GR-2; GR-4 password rotation documented)
- [x] 13-05-PLAN.md — Alertmanager backup.yml + restore.yml (empty-data stat-guard per AP-1)

### Phase 14: Orchestrators + Leviathan HUMAN-UAT
**Goal**: Operators have two symmetric orchestrator playbooks (`backup_docker.yml` and `restore_docker.yml`) with the same `--tags <role>`, `--ask-vault-pass`, and UX conventions as `deploy_docker.yml` and `undeploy_docker.yml`, proven end-to-end on leviathan via the full backup → purge-data undeploy → redeploy → restore → re-smoke round-trip.
**Depends on**: Phase 13 (the orchestrators call `include_role: tasks_from=backup` and `tasks_from=restore`, which must exist before the orchestrators can run)
**Requirements**: BACKUP-V13-05, RESTORE-V13-05, OPS-V13-01, OPS-V13-02, OPS-V13-03, UAT-V13-01
**Success Criteria** (what must be TRUE):
  1. `playbooks/backup_docker.yml` exists and includes the 4 stateful roles in forward-deploy order (garage → prometheus → grafana → alertmanager), serial, with a D-160-style PLAY-start banner (`tags: always`) that states the target directory and `backup_continue_on_failure` status without enumerating role names. Stateless-role tag invocations produce an empty 0-task play, not a failure.
  2. `playbooks/restore_docker.yml` stops the Garage writers (Loki, Tempo, Mimir) before restoring Garage, then restores in garage → prometheus → grafana → alertmanager order, then restarts the writers. Its PLAY-start banner is an escalated D-160 WARN explicitly stating that restore will permanently replace volume contents.
  3. `playbooks/restore_docker.yml` refuses to run without `--extra-vars backup_restore_confirm=true` — the gate fires at both orchestrator level and inside each per-role `tasks/restore.yml`, so a standalone `include_role: tasks_from=restore` from a custom playbook also enforces the gate.
  4. Both playbooks honour `--tags <role>` for any of the 4 stateful roles using the same tagging convention as `deploy_docker.yml`; `--tags backup` and `--tags restore` are also valid cross-cutting commands that operate on all 4 roles.
  5. `playbooks/backup_docker.yml` defaults to bail-out on the first role's failure; `--extra-vars backup_continue_on_failure=true` opts into continuing past failed roles.
  6. The `14-HUMAN-UAT.md` 7-step round-trip on leviathan completes with no manual intervention: (1) `deploy_docker.yml`, (2) `smoke_test.yml` records `smoke_trace_id` + `smoke_run_id`, (3) `backup_docker.yml`, (4) `undeploy_docker.yml --extra-vars telemetron_purge_data=true`, (5) `deploy_docker.yml`, (6) `restore_docker.yml --extra-vars backup_restore_confirm=true backup_restore_from=<timestamp>`, (7) `smoke_test.yml` with the same `smoke_trace_id` + `smoke_run_id` asserts the same synthetic OTLP signals are visible in Grafana — the milestone acceptance gate passes.
**Plans**: 4 plans
- [x] 14-01-amend-backup-yml-timestamp-override-PLAN.md — D-191 timestamp_override amendment to 4 backup.yml files (wave 1)
- [x] 14-02-backup-docker-orchestrator-PLAN.md — backup_docker.yml thin orchestrator with shared timestamp + bail-out knob (wave 2)
- [x] 14-03-restore-docker-orchestrator-PLAN.md — restore_docker.yml confirm-gated orchestrator with writer-quiesce around Garage (wave 2)
- [x] 14-04-human-uat-PLAN.md — 14-HUMAN-UAT.md skeleton + live leviathan UAT round-trip (wave 3)

### Phase 15: Documentation Cascade
**Goal**: Operators can discover the backup and restore story entirely through documentation — from root README to quickstart to per-role README — without reading source code, and Gate 11 codifies the stateful-role contract for future contributors.
**Depends on**: Phase 14 (the doc cascade references final playbook flags and the operator UX surface, which must be settled before docs are written — mirrors the v1.2.0 Phase 12 → Phase 11 dependency shape)
**Requirements**: DOCS-V13-01, DOCS-V13-02, DOCS-V13-03
**Success Criteria** (what must be TRUE):
  1. `roles/README.md` documents Gate 11 ("every stateful role ships `tasks/backup.yml` and `tasks/restore.yml` with a tested leviathan round-trip; every stateless role's README documents that it carries no operator state; the 4 stateful roles are: garage, prometheus, grafana, alertmanager") in the same style and detail level as Gates 1-10.
  2. `docs/quickstart.md` contains a `## Backup and restore` section covering: the default backup command line, the restore workflow including the `backup_restore_confirm=true` gate, the stop-order expectation (Loki/Tempo/Mimir stop before Garage restore), the local-disk destination and retention model (Telemetron writes dated tarballs; operator manages retention), and the manual tarball-extraction fallback. The root README Quick Start section contains a "When something goes wrong" line linking to `docs/quickstart.md#backup-and-restore`.
  3. All 4 stateful role READMEs (garage, prometheus, grafana, alertmanager) contain a new `## Backup` H2 section documenting what is and is not captured in the tarball (e.g., Garage `s3-credentials` IS captured; Grafana provisioning is NOT because it re-renders from version-controlled config) and the per-role tag invocation.
  4. All 8 stateless role READMEs (loki, tempo, mimir, fluentbit, karma, node_exporter, opentelemetry, nfsd) contain a one-line note in the vicinity of their `## Uninstall` section explaining why the role has no `tasks/backup.yml` (e.g., "Loki data lives in Garage S3 buckets — backed up via the garage role"; "Karma is stateless — no operator state to preserve").
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
| 7     | v1.1.0    | 1/1            | Complete    | 2026-05-27 |
| 8     | v1.1.0    | 3/3            | Complete    | 2026-05-27 |
| 9     | v1.1.0    | 2/2            | Complete    | 2026-05-28 |
| 10    | v1.2.0    | 6/6            | Complete    | 2026-05-29 |
| 11    | v1.2.0    | 6/6            | Complete    | 2026-05-30 |
| 12    | v1.2.0    | 3/3            | Complete    | 2026-05-30 |
| 13    | v1.3.0    | 5/5 | Complete    | 2026-06-03 |
| 14    | v1.3.0    | 6/7 | In Progress|  |
| 15    | v1.3.0    | 0/?            | Not started | -          |

## Backlog

Empty. All four prior M1 backlog items (999.1–999.4) were absorbed into Phases 7 + 9 of v1.1.0 (see `.planning/milestones/v1.1.0-ROADMAP.md`).
