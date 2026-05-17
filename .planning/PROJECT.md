# Telemetron

## What This Is

Telemetron is a one-stop, self-hosted observability stack — driven by Ansible — that brings up a full OTel-fed observability plane (logs, metrics, traces, alerts) on hardware you control. Audience is homelab and small-deployment operators first, with a path to scaling/Kubernetes/OpenShift for bigger orgs later. It's a clean-slate fork of an internal Quebec-government (INSPQ) deployment, being normalized to English and freed of org-specific assumptions so anyone can clone and run it.

## Core Value

A homelab operator can clone the repo, point the bundled example inventory at one of their own Docker hosts, run a single playbook, and end up with a working observability plane — Prometheus + Mimir for metrics, Loki for logs, Tempo for traces, Grafana on top, Alertmanager + Karma + hook-router for alerts, all fed by OpenTelemetry Collector. If everything else fails, that single-host Docker happy path must work.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- Loki 3.7.2 / Tempo 2.10.5 / Mimir 3.0.6 ported as monolithic-mode Ansible roles against MinIO buckets bootstrapped in Phase 1; `playbooks/deploy_docker.yml` orchestrates `minio → loki → tempo → mimir` in order. **Validated in Phase 2: telemetry-backends** (BACK-01..BACK-05; static gates green, live-Docker UAT tracked in `.planning/phases/02-telemetry-backends/02-HUMAN-UAT.md`).

### Active

<!-- Current scope — Milestone 1: "Port to clean-slate, Docker, homelab-first" -->

- [ ] Port 14 Ansible roles — translated (FR→EN), de-INSPQ'd, naming-normalized, each documented in `roles/<name>/README.md` and proven by booting on Rock's homelab Docker host
- [ ] Roles in scope: `alertmanager`, `fluentbit`, `grafana`, `hook_router`, `karma`, `loki`, `mimir`, `minio`, `nfsd`, `node_exporter`, `opentelemetry`, `prometheus`, `promlens`, `tempo` (14 total — `mongodb`, `application_web_docker`, and `postgres` dropped; `node_exporter` added so the stack can scrape the host it runs on)
- [ ] Loki, Tempo, and Mimir support monolithic mode only for M1 (distributed/microservices mode deferred)
- [ ] Write the hook router Flask app source under `hooks/router/` (was inline upstream) and ship sample Jenkinsfile runbooks under `hooks/jobs/`
- [ ] Ship a working `inventory/example-homelab/` covering a single-node Docker target — clone, edit a hostname, run the playbook
- [ ] Wire `playbooks/deploy_docker.yml` to orchestrate the 14 roles end-to-end
- [ ] Author `docs/architecture.md` — components, modes, signal flow
- [ ] Author `docs/quickstart.md` — zero-to-dashboards path against `inventory/example-homelab/`
- [ ] Author `docs/inventory.md` — inventory layout in depth (beyond the existing stub)

### Out of Scope

<!-- Explicit boundaries. Reasoning included to prevent re-adding. -->

- **`mcp` role (observability MCP server)** — Excluded from M1 entirely. Not core to the observability plane and not where homelab adoption is gated.
- **`haproxy` role** — Deferred. It exists to load-balance distributed-mode Loki/Tempo/Mimir; with monolithic-only run modes in M1, it has no job. Lands alongside distributed mode in a later milestone.
- **`application_web_docker` role** — Dropped from M1. Upstream INSPQ used it to pair each containerized REST service with an Apache vhost + external URL. That pattern binds operators to a single reverse-proxy choice; Telemetron is reverse-proxy-agnostic by design. Cross-cutting Docker plumbing (network, volume, restart-policy, healthcheck conventions) lives in shared `inventory/example-homelab/group_vars/all/` knobs and the per-role README schema instead.
- **`postgres` role** — Dropped from M1. With Grafana the only candidate consumer and Grafana's embedded SQLite fully sufficient for single-host homelab use, Postgres has no M1 consumer (same shape as `mongodb` losing Graylog). Returns as a v2 role only if HA Grafana lands, which would require a shared backing store across multiple Grafana instances.
- **Reverse-proxy configuration / external URL exposure** — Operator's choice. Quickstart shows direct `http://host:<port>` access patterns and lets operators slot Caddy / Traefik / nginx / Apache in front themselves. Telemetron ships no opinion on reverse-proxy layer or TLS termination; both are operator hardening steps documented in the quickstart, not pre-configured roles.
- **`mongodb` role** — Dropped from the upstream INSPQ stack. MongoDB was Graylog's metadata store; with Graylog dropped, no remaining M1 component depends on it. Karma uses BoltDB; PromLens has no datastore dependency. Confirmed during research synthesis.
- **`opensearch` (and any Elastic-family component)** — Out of scope entirely. Also a Graylog dependency; no role for it in the LGTM model Telemetron uses (Loki replaces Elastic for logs).
- **Multi-architecture (arm64) support and testing** — M1 is amd64-only. All chosen base images publish arm64, but Rock's homelab is amd64 and M1's bar is "boots on that host." Pi 5 / Apple Silicon support is a candidate for a later milestone.
- **Distributed / microservices mode for Loki, Tempo, Mimir** — Deferred. Monolithic mode covers homelab and small deployments. Distributed mode is a future milestone targeting bigger orgs.
- **Kubernetes / OpenShift deployment path (`playbooks/deploy_kube.yml`)** — Deferred. Docker/VM first for M1 to ship a focused, testable surface; Kube/OCP path is a later milestone.
- **`graylog` role** — Dropped from the upstream INSPQ stack. Legacy aggregator no longer needed; OTel + Loki cover its role.
- **CI test harness (molecule scenarios, ansible-test, Vagrant)** — Out for M1. Validation comes from booting roles on Rock's homelab. A reproducible test harness is a candidate for a later milestone.
- **`docs/migration-from-inspq.md`** — Deferred from M1's doc set. Useful for community signal but not blocking a homelab quickstart.
- **Multi-host distributed example inventory** — Deferred. M1 ships only the single-node Docker example; a distributed/HA inventory lands with distributed mode.
- **French-language docs / vars / role names** — Excluded. This fork is English-only by design.
- **INSPQ-specific vault paths, internal domains, NFS share assumptions, Quebec-gov cert chains** — Excluded. Stripped during the port; never re-added.

## Context

- **Origin:** Clean-slate fork of an INSPQ (Institut national de santé publique du Québec) Ansible observability stack. Rock authored the upstream and is now porting it for general use.
- **Upstream location:** `~/git/inspq/ansible/<role>/` on Rock's workstation — the source-of-truth checkout to copy roles from at fork time.
- **Stack shape:** OTel Collector for ingest/routing; Prometheus + Mimir (short-term + long-term metrics); Loki for logs; Tempo for traces; MinIO for S3-compatible object storage backing Loki/Tempo/Mimir; Grafana for UI; Alertmanager + Karma + PromLens for alerts; Fluent Bit for log shipping; hook router (Flask) bridging Alertmanager webhooks → Jenkins `buildWithParameters` for automated runbooks.
- **Naming normalization is already locked** (commit `ba836d2`): e.g. `alert_manager` → `alertmanager`, `postgresql-docker` → `postgres`. Subsequent role ports follow these names without re-litigating.
- **Test target for M1:** Rock's own homelab — SSH in, run the playbook, eyeball it. No reproducible CI/molecule harness required for milestone 1.
- **Audience layering:** Homelab and small deployments are the primary audience for M1. Bigger orgs (distributed mode + Kube/OpenShift) come in later milestones.
- **Motivation is layered** (all three apply): a portfolio artifact, a stack Rock actually wants to run, and a community contribution back from a previously-internal codebase.
- **Status:** Repo currently holds scaffolding only — top-level READMEs in `docs/`, `roles/`, `playbooks/`, `inventory/`, `hooks/`, plus `LICENSE` and the project `README.md`. No roles, playbooks, app source, or inventories committed yet.

## Constraints

- **Tech stack — Ansible**: Deployment is Ansible-driven. Not Terraform, not Pulumi, not raw scripts. M1 targets Docker via Ansible roles; Kube path uses Ansible too (later milestone).
- **Tech stack — Docker for M1**: Roles deploy via Docker on VMs/bare metal. Kubernetes deployment is a deferred milestone, not parallel work.
- **Tech stack — Components are fixed**: The component list (OTel, Prometheus/Mimir, Loki, Tempo, MinIO, Grafana, Alertmanager/Karma/PromLens, Fluent Bit, hook router) is decided. Swapping a backend (e.g. VictoriaMetrics in place of Mimir) is not part of M1.
- **Language — English only**: All vars, role names, READMEs, comments, and task `name:` strings must be English. No French-language artifacts.
- **Naming — Locked**: Naming normalizations decided in commit `ba836d2` are not re-litigated during M1 ports.
- **Test surface — Single host**: M1 quality bar is "boots on Rock's homelab Docker host." No molecule, no multi-host CI harness, no automated assertion suite — visual/manual verification is the bar.
- **Inventory portability — BYO supported but example shipped**: Inventory is symlinkable from outside the repo; M1 also ships one fully-worked single-node Docker example so a new user has a starting point.
- **License — MIT**: Already chosen and committed.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Drop `application_web_docker` role from M1 | Upstream pattern binds operators to a single reverse-proxy choice (Apache vhost); Telemetron is reverse-proxy-agnostic. Cross-cutting Docker plumbing moves to shared `inventory/example-homelab/group_vars/all/` knobs + per-role README schema (OPS-03) + grep/idempotency gates (OPS-04, OPS-05) | — Pending (M1) |
| Drop `postgres` role from M1 | Grafana's embedded SQLite covers single-host homelab use; no other M1 component depends on Postgres. Postgres requirement removed from REQUIREMENTS.md; returns as a v2 role only if HA Grafana lands in a later milestone | — Pending (M1) |
| M1 ports 14 roles: drop `mcp`, `haproxy`, `mongodb`, `application_web_docker`, and `postgres` from the upstream set; add `node_exporter` | `mcp` non-core; `haproxy` is distributed-mode-only; `mongodb` was Graylog's metadata store; `application_web_docker` binds operators to a single reverse-proxy; `postgres` has no M1 consumer; `node_exporter` fills the gap of how the stack scrapes its own host | — Pending (M1) |
| Fluent Bit default log path: FB → OTel Collector → Loki | One ingress point (OTel) for all signals makes backend swaps cheap and matches the "OTel as gateway" architecture; FB → Loki direct is documented as escape hatch in `roles/fluentbit/README.md` | — Pending (M1) |
| Resolve OTLP port clash: external OTLP terminates at OTel Collector on 4317/4318; Tempo's OTLP receivers bind to internal-only alt ports (14317/14318) | OTel Collector and Tempo both default to 4317/4318; without separation they collide on a single host. This is an architectural call, not a docs note | ✓ Good (shipped Phase 2 — Tempo role binds OTLP on 14317/14318, never host-published) |
| Ship M1 on archived MinIO (`RELEASE.2025-04-22T22-12-26Z`) with a loud README note; queue Garage migration for a future milestone | MinIO's community project was archived in early 2026. Adopting a replacement (Garage / SeaweedFS) inside M1 would blow up the port; deferring keeps M1 focused but accepts known software debt | ⚠️ Revisit (known debt; future milestone) |
| PromLens ships pinned to v0.3.0 and is marked deprecation-candidate in its role README | Project frozen since 2022; Prometheus 3 absorbed its tree-view feature. Shipped only for upstream parity | ⚠️ Revisit (known debt) |
| M1 ships amd64-only; arm64 deferred to a later milestone | Rock's homelab is amd64; all chosen images publish arm64 but the testing surface is amd64. Avoids opening a multi-arch test matrix during the port | — Pending (M1) |
| Grafana datasource UIDs are explicitly pinned (`uid: prometheus`, `uid: loki`, `uid: tempo`, `uid: mimir`) in provisioning | Auto-generated UIDs differ per deploy; without pinning, every bundled dashboard breaks on a fresh install. Top portability pitfall in the research | — Pending (M1) |
| Hook router security model (label allowlist + per-(alertname,job) rate limit + vault-supplied Jenkins token) ships in the first cut of `hooks/router/` | Allowlist + rate-limit are inexpensive to design in on day one and very expensive to retrofit; token leakage via alert payloads is the headline security pitfall | — Pending (M1) |
| Monolithic mode only for Loki/Tempo/Mimir in M1 | Matches the homelab/small-deployment audience; smallest configuration surface to ship | ✓ Good (shipped Phase 2 — all three roles run `-target=all`) |
| Docker/VM deployment first; Kubernetes/OpenShift later | Tighter scope, faster to a credible "this works" demo; Kube path inherits a settled role surface | — Pending (M1) |
| Ship a single-node Docker example inventory in M1 (`inventory/example-homelab/`) | README already promises a quickstart; without a working inventory the quickstart is hypothetical | — Pending (M1) |
| Validate each role by booting on Rock's homelab — no molecule/CI harness in M1 | Avoids a parallel test-infrastructure project; trades reproducibility for speed-to-port | — Pending (M1) |
| Write the hook router Flask source (`hooks/router/`) as part of M1, not just the deploy role | Upstream had it inline; without source the role has nothing to deploy | — Pending (M1) |
| M1 doc set is `architecture.md` + `quickstart.md` + `inventory.md` only | These three unblock evaluation and first-run; the other 7 planned docs (alerts, retention, fluentbit-timestamps, hook-router, instrumentation-otel, migration-from-inspq, metrics) can land alongside or after roles | — Pending (M1) |
| Drop `graylog` from the upstream stack | OTel + Loki cover its role; legacy aggregator not needed | ✓ Good |
| Naming normalizations locked before role porting (commit `ba836d2`) | Renaming after porting would force every role to be revisited | ✓ Good |
| English-only across all artifacts | Audience is global community + bigger orgs; FR-only would gate adoption | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-17 after Phase 2 (telemetry-backends) — Loki + Tempo + Mimir monolithic roles ported against MinIO; `playbooks/deploy_docker.yml` reaches `minio → loki → tempo → mimir`; canonical role pattern (defaults/meta/handlers/template/tasks/verify/README + inventory + vault aliases) proven on three backends*
