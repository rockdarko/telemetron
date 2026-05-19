# Telemetron — Milestone 1 Requirements

**Milestone:** M1 — "Port to clean-slate, Docker, homelab-first"
**Target:** 14 Ansible roles ported and proven by booting on Rock's homelab Docker host, plus a single-node example inventory, the hook router source, and three docs.

REQ-IDs use the format `[CATEGORY]-[NUMBER]`. Categories:

- **FOUND** — Foundation: shared base role, object storage, state storage
- **BACK** — Telemetry backends (Loki, Tempo, Mimir)
- **INGEST** — Ingest plane (Prometheus, OTel Collector, Fluent Bit, node_exporter)
- **ALERT** — Alert plane (Alertmanager, hook router source + role + sample jobs)
- **UI** — Grafana + Karma + PromLens (UIs and provisioning)
- **LEGACY** — Optional opt-in roles (nfsd)
- **INV** — Example homelab inventory + playbook orchestration
- **OPS** — Cross-cutting operational requirements (secrets, idempotency, validation gates)
- **DOCS** — M1 documentation set

---

## v1 Requirements (Milestone 1)

### Foundation (FOUND)

- [x] **FOUND-01**: Operator can run the playbook against a target host and have a single user-defined Docker bridge network (`telemetron`) created with named volumes for every component that needs persistent state. The `telemetron` Docker bridge network is created in `playbooks/deploy_docker.yml` pre_tasks via `community.docker.docker_network`. No shared base role — each role is self-contained and joins the network in its own `docker_container` task.
- [x] **FOUND-02**: Operator can run the playbook and have a working MinIO server reachable on `:9000` (S3 API) and `:9001` (console), pinned to `minio/minio:RELEASE.2025-04-22T22-12-26Z`. MinIO is started with bucket bootstrap blocking on `mc mb --ignore-existing` for `loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, and `mimir-alerts`. Downstream roles do not start before bootstrap exits successfully.

### Backends (BACK)

- [x] **BACK-01**: Operator can run the playbook and have Loki running in monolithic mode (`-target=all`, `grafana/loki:3.7.2`), backed by the `loki-chunks` MinIO bucket, with its persistent volume covering `/loki/compactor/markers/` (marker-file persistence is required for cleanup).
- [x] **BACK-02**: Operator can configure Loki log retention via a single `group_vars/` variable (`loki_retention_period`). Default ships sane (e.g. 14d) and is documented in `roles/loki/README.md`.
- [x] **BACK-03**: Operator can run the playbook and have Tempo running in monolithic mode (`grafana/tempo:2.10.5`), backed by the `tempo-traces` MinIO bucket. Defaults set **both** `block_retention` and `compacted_block_retention` so retention actually takes effect (single-value retention silently fails).
- [x] **BACK-04**: Operator can run the playbook and have Mimir running in monolithic mode (`-target=all`, `grafana/mimir:3.0.6`), backed by **three distinct** MinIO buckets (`mimir-blocks`, `mimir-ruler`, `mimir-alerts`) — Mimir refuses to start when these share a bucket+prefix. Defaults include `max_global_series_per_user: 500000` and `query_store_after` tuned for a single-host monolithic run.
- [x] **BACK-05**: Tempo's OTLP receivers bind to internal-only alt ports (14317 gRPC / 14318 HTTP), not the standard 4317/4318. External OTLP traffic terminates at the OTel Collector. Documented in `roles/tempo/README.md`.

### Ingest plane (INGEST)

- [x] **INGEST-01**: Operator can run the playbook and have Prometheus running (`prom/prometheus:v3.11.3`) scraping the OTel Collector's `:8888/metrics`, node_exporter, and any additional targets defined in inventory. Default `metric_relabel_configs` drop known-bad-cardinality labels (`pod_uid`, `request_id`, `trace_id`).
- [x] **INGEST-02**: Operator can run the playbook and have Prometheus `remote_write` configured to push to Mimir at `http://mimir:9009/api/v1/push`.
- [x] **INGEST-03**: Prometheus ships a baseline alert-rule set out of the box: host down (>2m), filesystem >85% used, container restart loop (≥3 restarts in 10m), OTel Collector dropping signals (>0 for >5m). Operators can add their own rules via a `prometheus_extra_rules` inventory variable.
- [x] **INGEST-04**: Operator can run the playbook and have an OTel Collector instance (`otel/opentelemetry-collector-contrib:0.152.0` — **Contrib**, not Core) accepting OTLP on `:4317` (gRPC) and `:4318` (HTTP) and fanning out to Loki, Tempo, and Mimir/Prometheus.
- [x] **INGEST-05**: OTel Collector pipeline ships with `processors: [memory_limiter, batch, ...]` in that order (reversing OOMs the box). `GOMEMLIMIT` env var is set to ~80% of the container's Docker memory limit. Every exporter has `sending_queue` enabled and `retry_on_failure` configured.
- [x] **INGEST-06**: Operator can run the playbook and have Fluent Bit running (`fluent/fluent-bit:4.2.3`) tailing host logs and shipping them through the OTel Collector to Loki (default path). FB → Loki direct is documented as an alternative in `roles/fluentbit/README.md`. Fluent Bit's `Time_System_Timezone Etc/UTC` and `Multiline_Flush 5` are set by default to mitigate DST and multiline parsing pitfalls.
- [x] **INGEST-07**: Fluent Bit ships only a small allowlist of labels to Loki: `{job, host, service, env, level}`. `service` and `job` are populated at runtime by a `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) that reads each source container's `/var/lib/docker/containers/<id>/config.v2.json` and extracts the Docker labels `org.telemetron.service` and `org.telemetron.job` (each telemetron stack role stamps these on its container). High-cardinality fields go to Loki structured metadata, not labels. Allowlist documented in `roles/fluentbit/README.md`.
- [x] **INGEST-08**: Operator can run the playbook and have node_exporter running, scraped by Prometheus, exposing host metrics (CPU, memory, disk, network, filesystem) on `:9100/metrics`.

### Alert plane (ALERT)

- [x] **ALERT-01**: Operator can run the playbook and have Alertmanager running (`quay.io/prometheus/alertmanager:v0.32.1`) on `:9093`, configured with `group_by: [alertname, cluster, service]`, `group_interval: 5m`, `repeat_interval: 4h`.

> **ALERT-02..06 moved to v2 Requirements as ALERT-V2-01..05** during the Phase 4 scope reshape (CONTEXT.md D-56/D-57/D-58). The hook router (Flask app + `roles/hook_router/` + sample bundles + outbound auth) is deferred to a future milestone. M1 ships Alertmanager with a `null` default receiver; alerts are visible in Karma (Phase 5) but not dispatched automatically.

### UI plane (UI)

- [x] **UI-01**: Operator can run the playbook and have Grafana running (`grafana/grafana-oss:13.0.1` — the OSS variant, not the Enterprise variant) on `:3000`, using embedded SQLite on a persistent named volume (`telemetron_grafana_data`) as its backing store, with admin password supplied from Ansible vault.
- [x] **UI-02**: Grafana datasources are provisioned at boot with **explicit UIDs**: `uid: prometheus`, `uid: loki`, `uid: tempo`, `uid: mimir`. Bundled dashboards reference these UIDs; UIDs do not change between deploys.
- [x] **UI-03**: Grafana ships 5–10 curated starter dashboards out of the box: host health (node_exporter), Loki Explore landing dashboard, Tempo Explore landing dashboard, OTel Collector self-metrics, and backend self-metrics (Loki/Tempo/Mimir health). Dashboards open and render real data on a fresh deploy.
- [x] **UI-04**: Tempo datasource provisioning wires `tracesToLogsV2` (with `customQuery` referencing Loki's `uid: loki` and a labelled `trace_id` derived field), enabling trace ↔ log correlation in Grafana Explore.
- [ ] **UI-05**: Operator can run the playbook and have Karma running (`ghcr.io/prymitive/karma:v0.130` — **GHCR official**, not the `lmierzwa/karma` Docker Hub fork), configured to pull alerts from the M1 Alertmanager.
- [ ] **UI-06**: Operator can run the playbook and have PromLens running (`prom/promlens:v0.3.0`). The `roles/promlens/README.md` explicitly marks it as a deprecation-candidate, noting that Prometheus 3's UI absorbs its tree-view feature.

### Legacy / optional (LEGACY)

- [ ] **LEGACY-01**: The `nfsd` role exists for operators with a legacy NFS-based log ingestion path. Default `enable_nfsd: false` in the example inventory — it does not deploy unless an operator opts in. `roles/nfsd/README.md` documents what it does and why most operators should ignore it.

### Inventory and orchestration (INV)

- [ ] **INV-01**: Operator can clone the repo, edit a single hostname/SSH-user pair in `inventory/example-homelab/`, supply their own vault password, and run `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml` to bring up the full M1 stack on a target Docker host.
- [x] **INV-02**: `inventory/example-homelab/` ships a complete `group_vars/all/` layout covering `network.yml` (Docker network name, port assignments), `storage.yml` (named-volume mounts, MinIO bucket names, retention values), `secrets.yml.example` (placeholder secret names using role-namespaced `<role>_<purpose>` keys — the real `secrets.yml` is operator-supplied and never committed), plus per-component `group_vars/` files where the research recommends override knobs.
- [ ] **INV-03**: `playbooks/deploy_docker.yml` orchestrates the 14 roles in dependency order: `[pre_tasks: telemetron network]` → `minio` → (`loki`, `tempo`, `mimir`) → (`prometheus`, `opentelemetry`, `fluentbit`, `node_exporter`) → (`alertmanager`, `hook_router`) → (`grafana`, `karma`, `promlens`) → `nfsd` (opt-in). Every role has a tag so operators can run `--tags <role>` for targeted re-runs.

### Cross-cutting operational (OPS)

- [x] **OPS-01**: All container images are pinned to explicit tags — no `:latest` anywhere. Image references live in role `defaults/main.yml` and are documented per-role.
- [x] **OPS-02**: All sensitive variables (Grafana admin password, MinIO access key + secret, etc.) follow the role-namespaced naming convention `<role>_<purpose>` (no `vault_` prefix — see Phase 4.1 D-90). Each role's README "Secrets" section enumerates the keys it expects. The operator chooses the protection mechanism (ansible-vault, sops, env-var injection, external secret manager, or chmod 600 on a homelab); Telemetron documents keys, not mechanism. `.vault_pass` is in `.gitignore` if ansible-vault is used. `secrets.yml.example` lives in `inventory/example-homelab/` as a template (renamed from `vault.yml.example` by Phase 4.1).
- [x] **OPS-03**: Every role's tasks pass `ansible-lint` and yaml-syntax-checks. Each role README documents its variables, modes, defaults, and tags.
- [x] **OPS-04**: Running `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml` a second time on an already-converged host returns `changed=0`. Templates iterate sorted dict keys (`{% for k in d.keys() | sort %}`) to avoid non-deterministic ordering; container restarts use handlers, not `state: restarted`.
- [x] **OPS-05**: Every role passes a per-role port-acceptance grep gate: zero matches for the regex `inspq|qc\.ca|montreal|québec|vault_inspq_` (note: `vault_inspq_` here is the INSPQ-leftover historical key-name grep gate — distinct from, and unaffected by, the OPS-02 `vault_` prefix convention that D-90 retired) and zero non-ASCII characters in committed files. This gate is documented in `roles/README.md` as part of the port checklist.
- [x] **OPS-06**: Every component container has a Docker `HEALTHCHECK` and a `restart: unless-stopped` policy by default. Timezone defaults to `Etc/UTC` everywhere.
- [ ] **OPS-07**: M1 completion smoke test — push a synthetic log, push a synthetic metric, push a synthetic trace. Within 60 seconds, the log appears in Grafana Loki Explore, the metric is queryable from Prometheus and from Mimir, and the trace appears in Tempo Explore — all queried via the bundled datasource UIDs.

### Documentation (DOCS)

- [ ] **DOCS-01**: `docs/architecture.md` documents components, monolithic-mode tradeoffs, signal flow (apps → OTel → backends → Grafana), and a port-allocation cheat sheet. Distilled from `.planning/research/ARCHITECTURE.md`.
- [ ] **DOCS-02**: `docs/quickstart.md` documents the zero-to-dashboards path: prerequisites (Ansible version, Docker on the target host, SSH access), clone, edit `inventory/example-homelab/<hostname>.hosts`, supply `vault.yml`, run the playbook, open Grafana, click a bundled dashboard. The doc is verified by an operator running it verbatim on a fresh target.
- [ ] **DOCS-03**: `docs/inventory.md` documents the inventory model in depth beyond the existing `inventory/README.md` stub: the expected directory shape, `group_vars/` conventions, how to add an environment, how vault files relate, how to symlink an out-of-tree inventory.
- [ ] **DOCS-04**: Top-level `README.md` is updated post-M1 to reflect what's actually shipped (replacing the "early" / "skeleton only" language) and points at `docs/quickstart.md`.

---

## v2 Requirements (deferred — not in M1)

These are real requirements for the project but explicitly out of M1 scope. They land in a later milestone.

- **HA-01**: Distributed/microservices mode for Loki, Tempo, Mimir, with the `haproxy` role wired in front
- **HA-02**: Multi-host distributed example inventory (multiple target hosts under one playbook run)
- **K8S-01**: Kubernetes / OpenShift deployment path via `playbooks/deploy_kube.yml`
- **TEST-01**: Reproducible test harness (molecule scenarios, ansible-test, or Vagrantfile per role) so contributors can verify role behavior without Rock's homelab
- **STORAGE-01**: MinIO replacement (Garage / SeaweedFS evaluation and migration role)
- **ARCH-01**: Multi-architecture (arm64) testing and documented support — Pi 5 / Apple Silicon
- **DOCS-V2-01**: `docs/alerts.md` — bundled Prometheus alerts catalog
- **DOCS-V2-02**: `docs/mimir-retention.md` — two-tier retention strategy
- **DOCS-V2-03**: `docs/fluentbit-timestamps.md` — DST + timezone handling for log shipping
- **DOCS-V2-04**: `docs/hook-router.md` — full hook router architecture deep dive
- **DOCS-V2-05**: `docs/instrumentation-otel.md` — instrumenting applications for OTLP
- **DOCS-V2-06**: `docs/migration-from-inspq.md` — port notes for anyone forking the original INSPQ stack
- **DOCS-V2-07**: `docs/metrics.md` — health metrics catalog with thresholds
- **TEMPO-V2-01**: Tempo 3.x evaluation and upgrade when the release stabilizes
- **ALERT-V2-01**: Hook router Flask app under `hooks/router/` -- backend-agnostic webhook bridge (was M1 ALERT-02).
- **ALERT-V2-02**: Hook router enforces an explicit per-rule allowlist; unrecognized alerts return 4xx and are logged (was M1 ALERT-03).
- **ALERT-V2-03**: Per-`(alertname, backend)` rate limit, default 6 per hour, configurable; overflow returns 429 + counter (was M1 ALERT-04; "job" renamed to "backend" to match the backend-agnostic v2 design).
- **ALERT-V2-04**: `hooks/jobs/` sample bundles -- GitHub Actions repository_dispatch, Slack incoming webhook, generic curl, optionally Jenkinsfile for historical context (was M1 ALERT-05).
- **ALERT-V2-05**: `roles/hook_router/` Ansible role that builds the Flask image locally + wires Alertmanager `webhook_configs` receiver + injects shared-secret + outbound token from vault (was M1 ALERT-06).

---

## Out of Scope (explicit exclusions)

- **`mcp` role (observability MCP server)** — Excluded entirely. Not core to the observability plane.
- **`mongodb` role** — Excluded. Was Graylog's metadata store; with Graylog dropped, no M1 consumer.
- **`opensearch` / Elastic-family** — Excluded entirely. Also a Graylog dependency; Loki replaces Elastic for logs in the LGTM model.
- **`graylog` role** — Dropped from the upstream INSPQ stack. OTel + Loki cover its role.
- **Dashboard "marketplace" / catalog ingestion** — M1 ships a small curated set; no UI for browsing community dashboards.
- **ML-driven anomaly detection** — Out of scope. Token alert rules cover M1; ML detection is a different product.
- **eBPF auto-instrumentation** — Out of scope. Operators instrument via OTel SDKs.
- **Web-UI configuration editor** — Telemetron is IaC; configuration is files-in-git, not a browser form.
- **Hosted SaaS variant** — Telemetron is self-hosted by definition.
- **GUI installer / one-command tarball** — The Ansible playbook is the installer.
- **French-language docs / variables / role names** — Excluded by constraint; English-only.
- **INSPQ-specific vault paths, internal domains, NFS shares, Quebec-gov cert chains** — Stripped during port; never re-added.

---

## Traceability

<!-- Filled by the roadmapper agent when phases are created. Each row maps a REQ-ID to the phase that delivers it. -->

| REQ-ID | Phase |
|--------|-------|
| FOUND-01 | Phase 1 — Foundation & Storage |
| FOUND-02 | Phase 1 — Foundation & Storage |
| BACK-01 | Phase 2 — Telemetry Backends |
| BACK-02 | Phase 2 — Telemetry Backends |
| BACK-03 | Phase 2 — Telemetry Backends |
| BACK-04 | Phase 2 — Telemetry Backends |
| BACK-05 | Phase 2 — Telemetry Backends |
| INGEST-01 | Phase 3 — Ingest Plane |
| INGEST-02 | Phase 3 — Ingest Plane |
| INGEST-03 | Phase 3 — Ingest Plane |
| INGEST-04 | Phase 3 — Ingest Plane |
| INGEST-05 | Phase 3 — Ingest Plane |
| INGEST-06 | Phase 3 — Ingest Plane |
| INGEST-07 | Phase 3 — Ingest Plane |
| INGEST-08 | Phase 3 — Ingest Plane |
| ALERT-01 | Phase 4 — Alert Plane |
| UI-01 | Phase 5 — UI Plane |
| UI-02 | Phase 5 — UI Plane |
| UI-03 | Phase 5 — UI Plane |
| UI-04 | Phase 5 — UI Plane |
| UI-05 | Phase 5 — UI Plane |
| UI-06 | Phase 5 — UI Plane |
| LEGACY-01 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| INV-01 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| INV-02 | Phase 1 — Foundation & Storage |
| INV-03 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| OPS-01 | Phase 1 — Foundation & Storage |
| OPS-02 | Phase 1 — Foundation & Storage |
| OPS-03 | Phase 1 — Foundation & Storage |
| OPS-04 | Phase 1 — Foundation & Storage |
| OPS-05 | Phase 1 — Foundation & Storage |
| OPS-06 | Phase 1 — Foundation & Storage |
| OPS-07 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| DOCS-01 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| DOCS-02 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| DOCS-03 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
| DOCS-04 | Phase 6 — Opt-in, Orchestration, Docs & Smoke Test |
