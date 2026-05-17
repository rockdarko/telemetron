# Roadmap: Telemetron

## Overview

Telemetron M1 — "Port to clean-slate, Docker, homelab-first" — ports 14 Ansible roles from an internal INSPQ stack into a clean-slate, English-only, MIT-licensed observability plane (Loki + Tempo + Mimir + Prometheus + OTel + Grafana + Alertmanager + Karma + PromLens + Fluent Bit + node_exporter + hook router) deployable against a single Docker host via one `ansible-playbook` command. The roadmap follows a validation-driven build order: foundation and storage land first (MinIO bucket bootstrap is the hard prerequisite gate that downstream backends depend on); the three monolithic telemetry backends ship in parallel once their object store is alive; the ingest plane (Prometheus, OTel Collector, Fluent Bit, node_exporter) wires the producers; the alert plane (Alertmanager + hook router) lands as a single unit because neither half validates alone; the UI plane (Grafana with explicit datasource UIDs, plus Karma and PromLens) closes out the deployment because Grafana's datasource provisioning is the de-facto end-to-end smoke test; and the final phase delivers the opt-in `nfsd` role, the full playbook orchestrator, the example inventory hostnames, three docs, and the M1 acceptance smoke test (synthetic log + metric + trace visible in Grafana within 60s).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Storage** - MinIO with bucket bootstrap gate (5 required buckets), `telemetron` Docker bridge network created in playbook pre_tasks, inventory `group_vars/all/` skeleton, vault discipline, grep + idempotency gates established (completed 2026-05-17)
- [ ] **Phase 2: Telemetry Backends** - Loki, Tempo, and Mimir running in monolithic mode against MinIO with correct retention defaults and Tempo's OTLP ports moved off the standard 4317/4318
- [ ] **Phase 3: Ingest Plane** - Prometheus scraping + remote_writing to Mimir with baseline alert rules, OTel Collector accepting OTLP on 4317/4318 and fanning out to all three backends, Fluent Bit shipping host logs through OTel to Loki, node_exporter exposing host metrics
- [ ] **Phase 4: Alert Plane** - Alertmanager configured with sane group/repeat intervals, hook router Flask source under `hooks/router/` with allowlist + rate limit + vault-supplied Jenkins token, sample Jenkinsfile runbooks under `hooks/jobs/`, `hook_router` role wiring the webhook
- [ ] **Phase 5: UI Plane** - Grafana provisioned with explicit datasource UIDs and a curated 5-10 dashboard set with trace-to-logs correlation, Karma over Alertmanager, PromLens marked as deprecation candidate
- [ ] **Phase 6: Opt-in, Orchestration, Docs & Smoke Test** - Opt-in `nfsd` role default-off, `playbooks/deploy_docker.yml` orchestrating all 14 roles in dependency order with per-role tags, example inventory hostnames wired so `ansible-playbook` runs end-to-end, three docs authored against a stack that actually booted, M1 acceptance smoke test (synthetic log + metric + trace in Grafana within 60s), top-level README updated

## Phase Details

### Phase 1: Foundation & Storage
**Goal**: Operator can run the foundation playbook against a fresh Docker host and have MinIO up with all five required buckets pre-created (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`), the `telemetron` Docker bridge network created, the `inventory/example-homelab/group_vars/all/` skeleton in place, and the cross-cutting gates (vault, idempotency, image-pin, healthcheck + `restart: unless-stopped`, INSPQ grep gate) established as port-acceptance criteria that every Phase 2-6 role port inherits.
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, INV-02, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06
**Success Criteria** (what must be TRUE):
  1. Operator runs `ansible-playbook playbooks/deploy_docker.yml --tags minio` against a fresh Docker host and `docker network ls` shows a `telemetron` user-defined bridge network with the MinIO container attached (`docker network inspect telemetron | jq -r '.[0].Containers | length'` returns at least 1).
  2. Operator runs `docker run --rm --network telemetron minio/mc:RELEASE.2025-04-22T16-23-26Z mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc ls local/` and sees all five required buckets exist: `loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts` — and bucket bootstrap completed successfully before the `minio` role exited (verifiable in the playbook output).
  3. Operator copies `inventory/example-homelab/group_vars/all/vault.yml.example` to `vault.yml`, fills in `vault_minio_root_user` and `vault_minio_root_password`, runs `ansible-vault encrypt inventory/example-homelab/group_vars/all/vault.yml`, and the playbook runs successfully reading the encrypted vault — no defaults, no placeholders consumed at runtime.
  4. Running the same playbook a second time on the converged host reports `changed=0` in the PLAY RECAP (idempotency gate); `grep -riE 'inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/minio/` returns zero matches and `grep -rPn '[^\x00-\x7F]' roles/minio/` returns zero matches (grep gate).
  5. `docker inspect telemetron-minio --format '{{.State.Health.Status}}'` returns `healthy`; `docker inspect telemetron-minio --format '{{.HostConfig.RestartPolicy.Name}}'` returns `unless-stopped`; image reference in `roles/minio/defaults/main.yml` is the explicit pinned tag `minio/minio:RELEASE.2025-04-22T22-12-26Z` with no `:latest` anywhere in `roles/minio/`.
**Plans**: 3 plans
Plans:
- [ ] 01-01-PLAN.md — Scope corrections and doc updates (PROJECT/REQUIREMENTS/ROADMAP/roles README) per D-01..D-05, D-21; removes FOUND-03
- [x] 01-02-PLAN.md — Inventory skeleton (`inventory/example-homelab/`) and `playbooks/deploy_docker.yml` with `telemetron` Docker network pre_task
- [ ] 01-03-PLAN.md — MinIO role port (`roles/minio/`) with bucket bootstrap (5 buckets) and wire into playbook

### Phase 2: Telemetry Backends
**Goal**: Operator can run the playbook and have Loki, Tempo, and Mimir running in monolithic mode against the MinIO buckets from Phase 1, each with the correct retention semantics for its storage model and Tempo's OTLP receivers moved off the standard ports to avoid clashing with the OTel Collector that lands in Phase 3.
**Depends on**: Phase 1
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, BACK-05
**Success Criteria** (what must be TRUE):
  1. Operator runs `ansible-playbook --tags loki,tempo,mimir` and `curl http://<host>:3100/ready`, `curl http://<host>:3200/ready`, `curl http://<host>:9009/ready` all return `ready` within 60s of role completion.
  2. Operator pushes a synthetic log to `:3100/loki/api/v1/push`, a synthetic trace to Tempo's internal-only `:14318` (via OTel later in Phase 3 — for Phase 2 the verification is direct OTLP HTTP to the alt port), and a synthetic metric series via `remote_write` to Mimir's `:9009/api/v1/push`, and `mc ls minio/loki-chunks`, `mc ls minio/tempo-traces`, and `mc ls minio/mimir-blocks` all show new objects landing.
  3. Operator changes `loki_retention_period` in `group_vars/` from the shipped default to a different value, re-runs the role, and `curl http://<host>:3100/config` reflects the new retention — same knob exists per-backend for Tempo (both `block_retention` and `compacted_block_retention`) and Mimir.
  4. Tempo's OTLP receivers bind to `:14317` (gRPC) and `:14318` (HTTP) — confirmed by `ss -tlnp` on the host — and the standard `:4317`/`:4318` ports are still free for the OTel Collector to claim in Phase 3.
  5. Per-role port-acceptance gates pass on each of Loki/Tempo/Mimir (idempotent re-run, grep clean, healthcheck green, image pinned).
**Plans**: TBD

### Phase 3: Ingest Plane
**Goal**: Operator can run the playbook and have Prometheus, OTel Collector, Fluent Bit, and node_exporter running — with Prometheus scraping the Collector's self-metrics and node_exporter, remote-writing to Mimir, and evaluating a baseline alert-rule set; the OTel Collector accepting OTLP on the standard ports and fanning out to all three backends; Fluent Bit tailing host logs through the Collector to Loki; and node_exporter exposing host metrics on `:9100`. The four pieces come up in their internal dependency order (Prometheus needs Mimir, OTel needs all three backends, Fluent Bit needs OTel).
**Depends on**: Phase 2
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, INGEST-08
**Success Criteria** (what must be TRUE):
  1. Operator runs `ansible-playbook --tags prometheus,opentelemetry,fluentbit,node_exporter` and `curl http://<host>:9090/-/ready`, `curl http://<host>:4318/v1/traces` (200 on POST), `curl http://<host>:2020/api/v1/health` (Fluent Bit), and `curl http://<host>:9100/metrics` all respond healthy; `curl http://<host>:9090/api/v1/targets` shows OTel Collector and node_exporter as `up`.
  2. Operator pushes a synthetic OTLP trace + log + metric to the Collector's `:4317`/`:4318` and within 30s the trace appears via Tempo's API, the log appears via Loki's API, and the metric appears in Prometheus (which has already remote-written it to Mimir, verifiable by querying both).
  3. Prometheus evaluates the baseline alert-rule set (`HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals`) — `curl http://<host>:9090/api/v1/rules` returns all four rule names; operators can add their own via `prometheus_extra_rules` in inventory.
  4. The OTel Collector pipeline order is `processors: [memory_limiter, batch, ...]` (verifiable in `/etc/telemetron/opentelemetry/config.yaml`); `GOMEMLIMIT` is set to ~80% of the container's memory limit; every exporter has `sending_queue: enabled` and `retry_on_failure` configured — and the container does not OOM under a 5-minute synthetic load test.
  5. Fluent Bit ships only the labels `{job, host, service, env, level}` to Loki (high-cardinality fields go to structured metadata) — verifiable by inspecting Loki streams via `/loki/api/v1/labels`; `Time_System_Timezone Etc/UTC` and `Multiline_Flush 5` are set in the rendered config.
**Plans**: TBD

### Phase 4: Alert Plane
**Goal**: Operator can run the playbook and have Alertmanager dispatching alerts from Prometheus to a Flask hook router (built locally from `hooks/router/` as a role artifact) that enforces an explicit per-rule allowlist + per-(alertname, job) rate limit and translates allowlisted alerts into Jenkins `buildWithParameters` calls with a vault-supplied token. Two to three sample Jenkinsfile runbooks ship under `hooks/jobs/` demonstrating non-trivial parameter substitution. No Jenkins token ever appears in alert payloads or container env logs.
**Depends on**: Phase 3
**Requirements**: ALERT-01, ALERT-02, ALERT-03, ALERT-04, ALERT-05, ALERT-06
**Success Criteria** (what must be TRUE):
  1. Operator runs `ansible-playbook --tags alertmanager,hook_router` and `curl http://<host>:9093/-/ready` and `curl http://<host>:5001/healthz` both return OK; the Alertmanager config shows `group_by: [alertname, cluster, service]`, `group_interval: 5m`, `repeat_interval: 4h`.
  2. Operator force-fires a test alert (`amtool alert add alertname=TestRestart instance=demo job=ops-jenkins`) that matches an allowlisted `(alertname, job)` mapping in `hooks/router/rules.yml`, and the hook router logs the receipt + `POST /job/<name>/buildWithParameters` to Jenkins with parameters substituted from labels (`instance=demo`).
  3. Operator force-fires an alert whose `alertname` is not on the allowlist — the hook router returns 4xx (not silently forwarded) and logs the rejection.
  4. Operator force-fires the same allowlisted alert 10 times in 60 seconds — the 7th through 10th attempts return HTTP 429 (rate limit default 6/hour per `(alertname, job)`) and the `hook_router_rate_limited_total` counter increments.
  5. Two to three sample `Jenkinsfile` runbooks exist under `hooks/jobs/` with non-trivial parameter substitution (e.g. `{instance}` → restart a specific container, `{filesystem}` → run a cleanup job); `grep -r 'Bearer\|api_token\|jenkins_token' hooks/router/` returns no string literal — token is loaded from env (sourced from vault) only.
**Plans**: TBD

### Phase 5: UI Plane
**Goal**: Operator can run the playbook and have Grafana running with datasources explicitly provisioned at stable UIDs (`prometheus`, `loki`, `tempo`, `mimir`), 5-10 curated starter dashboards rendering real data on a fresh deploy, trace-to-logs correlation wired through Tempo's `tracesToLogsV2` + a derived `trace_id` field on Loki — plus Karma running against Alertmanager and PromLens pinned to `v0.3.0` and marked deprecation-candidate in its role README. Grafana's datasource provisioning is the de-facto smoke test for everything that came before.
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06
**Success Criteria** (what must be TRUE):
  1. Operator runs `ansible-playbook --tags grafana,karma,promlens`, opens `http://<host>:3000`, logs in with the vault-supplied admin password, and the four provisioned datasources (Prometheus, Loki, Tempo, Mimir) appear with UIDs exactly `prometheus`, `loki`, `tempo`, `mimir` — `curl http://<host>:3000/api/datasources/uid/loki` returns 200.
  2. Operator opens any one of the bundled dashboards in a fresh browser session and every panel renders real data (host health from node_exporter, Loki Explore landing, Tempo Explore landing, OTel Collector self-metrics, backend health metrics) — no "Datasource not found" errors.
  3. Operator clicks a trace span in Grafana Explore and the "Logs for this span" link navigates to Loki Explore with a `trace_id` filter pre-applied; the corresponding log lines render — confirming `tracesToLogsV2` + Loki derived-field plumbing is wired correctly.
  4. Operator opens `http://<host>:8082` (Karma) and sees the M1 Alertmanager's current alerts in Karma's grid view; opens `http://<host>:8081` (PromLens) and gets a working PromQL editor pointed at Prometheus.
  5. `roles/promlens/README.md` explicitly marks PromLens as a deprecation candidate and notes Prometheus 3's UI absorbs the tree-view feature; Karma container image is `ghcr.io/prymitive/karma:v0.130` (the GHCR official, not `lmierzwa/karma` Docker Hub fork).
**Plans**: TBD
**UI hint**: yes

### Phase 6: Opt-in, Orchestration, Docs & Smoke Test
**Goal**: Operator can clone the repo, edit one hostname + SSH-user pair in `inventory/example-homelab/`, supply a vault password, run a single `ansible-playbook` command, and have the full M1 stack come up on a fresh Docker host — then push a synthetic log + metric + trace and see all three in Grafana within 60 seconds. The `nfsd` role exists for opt-in legacy NFS log ingestion (default-off), `playbooks/deploy_docker.yml` orchestrates all 14 roles in correct dependency order with per-role tags, three docs (`architecture.md`, `quickstart.md`, `inventory.md`) are authored against a stack that actually booted, and the top-level README reflects what shipped.
**Depends on**: Phase 5
**Requirements**: LEGACY-01, INV-01, INV-03, OPS-07, DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. Operator clones the repo, edits a single hostname + SSH-user in `inventory/example-homelab/example-homelab.hosts`, copies `vault.yml.example` to `vault.yml` and fills it in, then runs `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml` and the full 14-role stack comes up end-to-end on a fresh Docker host — every role's tag works for `--tags <role>` targeted re-runs.
  2. With `enable_nfsd: false` (the default in the example inventory), no `nfsd` container is created; flipping it to `true` and re-running the playbook deploys the NFS server container; `roles/nfsd/README.md` documents what it does and why most operators should ignore it.
  3. M1 acceptance smoke test: operator pushes a synthetic log (via Fluent Bit tail or direct OTLP), a synthetic metric (via OTel Collector OTLP), and a synthetic trace (via OTel Collector OTLP); within 60 seconds the log appears in Grafana Loki Explore using the bundled `loki` UID, the metric is queryable from both Prometheus (`uid: prometheus`) and Mimir (`uid: mimir`), and the trace appears in Grafana Tempo Explore using `uid: tempo`.
  4. `docs/architecture.md` (components, monolithic-mode tradeoffs, signal flow apps→OTel→backends→Grafana, port-allocation cheat sheet), `docs/quickstart.md` (zero-to-dashboards path verified by an operator running it verbatim on a fresh target), and `docs/inventory.md` (in-depth inventory model beyond the `inventory/README.md` stub) all exist and the quickstart works step-by-step on a clean host.
  5. Top-level `README.md` is updated post-M1 to reflect what's actually shipped (replacing "early" / "skeleton only" language) and links to `docs/quickstart.md`; the entire deploy is idempotent (a second back-to-back playbook run reports `changed=0`).
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Storage | 3/3 | Complete   | 2026-05-17 |
| 2. Telemetry Backends | 0/TBD | Not started | - |
| 3. Ingest Plane | 0/TBD | Not started | - |
| 4. Alert Plane | 0/TBD | Not started | - |
| 5. UI Plane | 0/TBD | Not started | - |
| 6. Opt-in, Orchestration, Docs & Smoke Test | 0/TBD | Not started | - |
