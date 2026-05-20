# Telemetron

## What This Is

Telemetron is a one-stop, self-hosted observability stack — driven by Ansible — that brings up a full OTel-fed observability plane (logs, metrics, traces, alerts) on hardware you control. Audience is homelab and small-deployment operators first, with a path to scaling/Kubernetes/OpenShift for bigger orgs later. It's a clean-slate fork of an internal Quebec-government (INSPQ) deployment, being normalized to English and freed of org-specific assumptions so anyone can clone and run it.

## Core Value

A homelab operator can clone the repo, point the bundled example inventory at one of their own Docker hosts, run a single playbook, and end up with a working observability plane — Prometheus + Mimir for metrics, Loki for logs, Tempo for traces, Grafana on top, Alertmanager + Karma for alerts, all fed by OpenTelemetry Collector. If everything else fails, that single-host Docker happy path must work.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- **Full M1 LGTM observability plane shipped via a single `ansible-playbook` against `inventory/example-homelab/`** — 13 roles deployed + nfsd as the 14th opt-in slot; full stack reaches healthy state on leviathan; synthetic OTLP log+metric+trace visible in Grafana within 60s; back-to-back deploy is `changed=0` for both the 13-role default and the 14-role `enable_nfsd: true` shape. **Validated in M1 close-out** (`.planning/milestones/v1.0.0-phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md`).
- Foundation + cross-cutting port-acceptance gates established — `inventory/example-homelab/` skeleton with domain-split group_vars, MinIO bucket bootstrap as a blocking step inside the `minio` role (5 buckets: loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts), `telemetron` Docker bridge network as a `playbooks/deploy_docker.yml` pre_task, and the 8 cross-cutting gates baked into `roles/README.md` (grep-clean / image-pin / secrets-discipline / idempotency / healthcheck+restart / README-schema / label-stamp / parent-dir bind-mount). **Validated in Phase 1: foundation-storage** — v1.0.0.
- Loki 3.7.2 / Tempo 2.10.5 / Mimir 3.0.6 ported as monolithic-mode Ansible roles against MinIO buckets bootstrapped in Phase 1; `playbooks/deploy_docker.yml` orchestrates `minio → loki → tempo → mimir` in order. **Validated in Phase 2: telemetry-backends** (BACK-01..BACK-05) — v1.0.0.
- Prometheus 3.11.3 + OpenTelemetry Collector Contrib 0.152.0 + Fluent Bit 4.2.3 + node_exporter 1.11.1 ported as monolithic-mode Ansible roles; `playbooks/deploy_docker.yml` extends to `… → node_exporter → opentelemetry → prometheus → fluentbit`. Pitfall 5 OOM-resistance pack (memory_limiter ratios + GOMEMLIMIT + sending_queue/retry_on_failure on every exporter), four baseline alert rules (HostDown / FilesystemAlmostFull / ContainerRestartLoop / OTelCollectorDroppingSignals) + extras knob, FB Lua-enrichment promotes `org.telemetron.{service,job}` Docker labels to first-class Loki labels (NO Docker socket — reads `/var/lib/docker/containers/<id>/config.v2.json`). Gate 7 in `roles/README.md` forces Phase 4/5 roles to inherit the label-stamp convention. **Validated in Phase 3: ingest-plane** (INGEST-01..INGEST-08, including INGEST-07 closed by gap-closure Plan 03-05) — v1.0.0.
- Alertmanager v0.32.1 ported as a single-instance monolithic Ansible role (`roles/alertmanager/`); gossip disabled (`--cluster.listen-address=""`), explicit busybox-wget HEALTHCHECK (image ships none), persistent `telemetron_alertmanager_data` volume on `/alertmanager`, route with single `null` receiver + D-61 intervals (`group_by [alertname, cluster, service]`, `group_wait 30s`, `group_interval 5m`, `repeat_interval 4h`), one D-63 inhibit rule using corrected `source_matchers:`/`target_matchers:` syntax (Research Q2 — deprecated `source_match:` form replaced). Prometheus extended with `alerting: alertmanagers:` block targeting `alertmanager:9093` (D-64); `playbooks/deploy_docker.yml` reaches `… → fluentbit → alertmanager`. Hook router (Flask + role + sample bundles + Jenkins `buildWithParameters` auth) deferred to v2 as ALERT-V2-01..05; 9-file doc cascade applied across PROJECT/REQUIREMENTS/ROADMAP/CLAUDE/hooks/README and research artifacts. Plan 04-02 gap closure (2026-05-19) closed two UAT bugs — Bug 1 (alertmanager verify auto_remove race rewritten with `community.docker.docker_container_exec` + Ansible `until:`/`retries:`/`delay:` polling) and Bug 2 (single-file rendered-config bind mounts replaced with parent-directory mounts across 7 roles, eliminating the moby/moby#6011 stale-inode class) — plus added Gate 8 to `roles/README.md` and ticked all 6 Phase 4 UAT tests `result: pass` on leviathan. **Validated in Phase 4: alert-plane** (ALERT-01 code-complete + UAT all-green) — v1.0.0.
- Grafana OSS 13.0.1 + Karma v0.130 + PromLens v0.3.0 ported as monolithic Ansible roles; `playbooks/deploy_docker.yml` extends to `… → alertmanager → grafana → karma → promlens`. Grafana provisions four datasources at hardcoded UIDs (`prometheus`, `loki`, `tempo`, `mimir`), seven curated dashboards (host-health, loki/tempo explore-landing, otel-collector / loki / tempo / mimir self-metrics) with `_rewrite_uids.py` collapsing upstream template-var refs to hardcoded UIDs (D-77), trace-to-logs correlation via Tempo `tracesToLogsV2` + Loki `derivedFields trace_id` (UI-04). Karma reads Alertmanager via Docker bridge DNS (`http://alertmanager:9093`). PromLens marked `## DEPRECATION CANDIDATE` in its README — Prometheus 3.x native UI absorbs the feature surface. Gap-closure plans 05-04 → 05-08 (2026-05-19) closed six live-UAT issues on leviathan: (a) 25 stray `§` chars swept from karma+promlens non-README files; (b) `_rewrite_uids.py` SUBSTITUTIONS dict key-form bug fixed and walker extended to recurse into `targets[*].datasource.uid` (51 target-level upstream-org UIDs in `tempo-self-metrics.json` normalized to `prometheus`); (c) Gate 9.5 in `roles/grafana/tasks/verify.yml` blocks unresolved `"uid": "$..."` panel refs at deploy time; (d) grafana `verify.yml` curl-probes rewritten from `community.docker.docker_container` (`auto_remove: true` + `detach: false` race per ansible/ansible#45272) to `community.docker.docker_container_exec` polling against the live container; (e) Loki `derivedFields` switched from `matcherType: label` (which never matched telemetron's actual stream labels) to `structured_metadata` primary + regex fallback for body-embedded trace_id; (f) Karma docker HEALTHCHECK flipped to opt-out (scratch image ships only the `/karma` binary, no `/bin/sh` for the wget probe) plus five latent auto_remove races dropped across karma+promlens `verify.yml`. **Validated in Phase 5: ui-plane** (UI-01..UI-06; 12/12 must-haves static-verified + live-stack UAT confirmed via M1 acceptance smoke test on leviathan) — v1.0.0. PromLens subsequently removed in v1.0.1 (see RETROSPECTIVE.md).

### Active

<!-- Awaiting v2 milestone scoping. M1 shipped 2026-05-19. -->

No active scope. Run `/gsd:new-milestone` to scope v2. Candidate themes from
M1's known debt:

- **Garage / SeaweedFS migration** off the archived MinIO community release
- **Hook router** (Flask app + role + sample bundles + Jenkins `buildWithParameters` auth) — preserved design in archived `04-DISCUSSION-LOG.md`, tracked as `ALERT-V2-01..05` in `.planning/milestones/v1.0.0-REQUIREMENTS.md`
- **Multi-host distributed inventory** + distributed-mode Loki/Tempo/Mimir + HAProxy in front
- **Kubernetes / OpenShift deployment path** (`playbooks/deploy_kube.yml`)
- **arm64 / multi-arch** support and testing surface
- **Backlog 999.x items** carried into v2: mimir blocks_retention re-wire under `limits:`, tempo `compactor.block_ranges_period` cleanup, fluentbit `timestamp_fallback` FB-4-compatible syntax, FB label-spec vs OTel-reality reconciliation (now in `.planning/milestones/v1.0.0-phases/999.x-*`)

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
- **PromLens (removed v1.0.1)** — shipped in v1.0.0 for upstream parity; removed post-ship after confirming upstream is functionally frozen since Dec 2022 (Dependabot-only commits, no tagged release in 3.5 years). Prometheus 3's native UI at `http://prometheus:9090/graph` covers the tree-view + query-explorer use case. Not coming back.

## Context

- **Origin:** Clean-slate fork of an INSPQ (Institut national de santé publique du Québec) Ansible observability stack. Rock authored the upstream and is now porting it for general use.
- **Upstream location:** `~/git/inspq/ansible/<role>/` on Rock's workstation — the source-of-truth checkout to copy roles from at fork time.
- **Stack shape:** OTel Collector for ingest/routing; Prometheus + Mimir (short-term + long-term metrics); Loki for logs; Tempo for traces; MinIO for S3-compatible object storage backing Loki/Tempo/Mimir; Grafana for UI; Alertmanager + Karma + PromLens for alerts; Fluent Bit for log shipping; hook router (Flask) bridging Alertmanager webhooks → Jenkins `buildWithParameters` for automated runbooks.
- **Naming normalization is already locked** (commit `ba836d2`): e.g. `alert_manager` → `alertmanager`, `postgresql-docker` → `postgres`. Subsequent role ports follow these names without re-litigating.
- **Test target for M1:** Rock's own homelab — SSH in, run the playbook, eyeball it. No reproducible CI/molecule harness required for milestone 1.
- **Audience layering:** Homelab and small deployments are the primary audience for M1. Bigger orgs (distributed mode + Kube/OpenShift) come in later milestones.
- **Motivation is layered** (all three apply): a portfolio artifact, a stack Rock actually wants to run, and a community contribution back from a previously-internal codebase.
- **Status:** v1.0.0 shipped 2026-05-19 on leviathan. Repo holds 13 working Ansible roles (alertmanager, fluentbit, grafana, karma, loki, mimir, minio, nfsd, node_exporter, opentelemetry, prometheus, promlens, tempo), a working `playbooks/deploy_docker.yml` orchestrator + `playbooks/smoke_test.yml` acceptance probe, a complete `inventory/example-homelab/` skeleton, and three operator docs (`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`). ~12,254 LOC across 139 files. Awaiting v2 scoping.

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
| Drop `application_web_docker` role from M1 | Upstream pattern binds operators to a single reverse-proxy choice (Apache vhost); Telemetron is reverse-proxy-agnostic. Cross-cutting Docker plumbing moves to shared `inventory/example-homelab/group_vars/all/` knobs + per-role README schema (OPS-03) + grep/idempotency gates (OPS-04, OPS-05) | ✓ Good (v1.0.0) |
| Drop `postgres` role from M1 | Grafana's embedded SQLite covers single-host homelab use; no other M1 component depends on Postgres. Postgres requirement removed from REQUIREMENTS.md; returns as a v2 role only if HA Grafana lands in a later milestone | ✓ Good (v1.0.0) |
| M1 ports 14 roles: drop `mcp`, `haproxy`, `mongodb`, `application_web_docker`, and `postgres` from the upstream set; add `node_exporter` | `mcp` non-core; `haproxy` is distributed-mode-only; `mongodb` was Graylog's metadata store; `application_web_docker` binds operators to a single reverse-proxy; `postgres` has no M1 consumer; `node_exporter` fills the gap of how the stack scrapes its own host | ✓ Good (v1.0.0 — 13 deployed + nfsd opt-in; hook_router deferred to v2) |
| Fluent Bit default log path: FB → OTel Collector → Loki | One ingress point (OTel) for all signals makes backend swaps cheap and matches the "OTel as gateway" architecture; FB → Loki direct is documented as escape hatch in `roles/fluentbit/README.md` | ✓ Good (v1.0.0 — D-49 default path proven in Plan 06-02 smoke test) |
| Resolve OTLP port clash: external OTLP terminates at OTel Collector on 4317/4318; Tempo's OTLP receivers bind to internal-only alt ports (14317/14318) | OTel Collector and Tempo both default to 4317/4318; without separation they collide on a single host. This is an architectural call, not a docs note | ✓ Good (shipped Phase 2 — Tempo role binds OTLP on 14317/14318, never host-published) |
| Ship M1 on archived MinIO (`RELEASE.2025-04-22T22-12-26Z`) with a loud README note; queue Garage migration for a future milestone | MinIO's community project was archived in early 2026. Adopting a replacement (Garage / SeaweedFS) inside M1 would blow up the port; deferring keeps M1 focused but accepts known software debt | ⚠️ Revisit (known debt; future milestone) |
| PromLens ships pinned to v0.3.0 and is marked deprecation-candidate in its role README | Project frozen since 2022; Prometheus 3 absorbed its tree-view feature. Shipped only for upstream parity | ✓ Resolved (removed in v1.0.1 — see RETROSPECTIVE.md) |
| M1 ships amd64-only; arm64 deferred to a later milestone | Rock's homelab is amd64; all chosen images publish arm64 but the testing surface is amd64. Avoids opening a multi-arch test matrix during the port | ✓ Good (v1.0.0 — leviathan is amd64; arm64 candidate for v2) |
| Grafana datasource UIDs are explicitly pinned (`uid: prometheus`, `uid: loki`, `uid: tempo`, `uid: mimir`) in provisioning | Auto-generated UIDs differ per deploy; without pinning, every bundled dashboard breaks on a fresh install. Top portability pitfall in the research | ✓ Good (v1.0.0 — D-77 `_rewrite_uids.py` walker normalizes upstream template-var refs to hardcoded UIDs; verified across 7 curated dashboards) |
| Hook router security model (label allowlist + per-(alertname,job) rate limit + vault-supplied Jenkins token) ships in the first cut of `hooks/router/` | Allowlist + rate-limit are inexpensive to design in on day one and very expensive to retrofit; token leakage via alert payloads is the headline security pitfall | Deferred to v2 (mid-M1 reshape, 2026-05-18 -- see Phase 4 CONTEXT.md D-56) |
| Monolithic mode only for Loki/Tempo/Mimir in M1 | Matches the homelab/small-deployment audience; smallest configuration surface to ship | ✓ Good (shipped Phase 2 — all three roles run `-target=all`) |
| Docker/VM deployment first; Kubernetes/OpenShift later | Tighter scope, faster to a credible "this works" demo; Kube path inherits a settled role surface | ✓ Good (v1.0.0 — Docker shipped; Kube path queued for v2) |
| Ship a single-node Docker example inventory in M1 (`inventory/example-homelab/`) | README already promises a quickstart; without a working inventory the quickstart is hypothetical | ✓ Good (v1.0.0 — INV-01 fresh-clone walkthrough PASS on leviathan in Plan 06-04) |
| Validate each role by booting on Rock's homelab — no molecule/CI harness in M1 | Avoids a parallel test-infrastructure project; trades reproducibility for speed-to-port | ✓ Good (v1.0.0 — leviathan UAT pattern proven; molecule/CI candidate for v2) |
| Write the hook router Flask source (`hooks/router/`) as part of M1, not just the deploy role | Upstream had it inline; without source the role has nothing to deploy | ⚠️ Revisit — deferred to v2 (mid-M1 reshape 2026-05-18, D-56; tracked as ALERT-V2-01..05) |
| M1 doc set is `architecture.md` + `quickstart.md` + `inventory.md` only | These three unblock evaluation and first-run; the other 7 planned docs (alerts, retention, fluentbit-timestamps, hook-router, instrumentation-otel, migration-from-inspq, metrics) can land alongside or after roles | ✓ Good (v1.0.0 — all three shipped via Plan 06-03; 7 deferred docs tracked as DOCS-V2-01..07 in archived v1.0.0-REQUIREMENTS.md) |
| Drop `graylog` from the upstream stack | OTel + Loki cover its role; legacy aggregator not needed | ✓ Good |
| Naming normalizations locked before role porting (commit `ba836d2`) | Renaming after porting would force every role to be revisited | ✓ Good |
| Drop the `vault_` prefix from all sensitive variables (D-90) | Prefix added no value beyond role-namespace + suffix; steered operators toward Ansible vault when sops/env/external managers are equally valid; implied tooling enforcement Ansible doesn't provide. Per [[feedback-no-decorative-convention-prefixes]] | ✓ Good (shipped Phase 4.1 — 8 keys renamed across 4 roles + `vault.yml.example` -> `secrets.yml.example` + doc cascade) |
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
*Last updated: 2026-05-19 after v1.0.0 milestone close — M1 SHIPPED on leviathan. Full LGTM observability plane (13 deployed roles + nfsd opt-in 14th slot) deployable via a single `ansible-playbook` against `inventory/example-homelab/`; synthetic OTLP log+metric+trace visible in Grafana within 60s (Plan 06-02 smoke test); back-to-back deploy idempotent (`changed=0`) for both the 13-role default and the 14-role `enable_nfsd: true` shape. 37/37 v1 requirements checked off and archived to `.planning/milestones/v1.0.0-REQUIREMENTS.md`. Awaiting v2 milestone scoping via `/gsd:new-milestone`.*
