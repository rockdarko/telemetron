# Phase 3: Ingest Plane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `03-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 03-ingest-plane
**Areas discussed:** Plan/role order, OTel fanout, FB log sources, Restart-loop rule

---

## Areas Selected

User selected ALL four offered gray areas: Plan/role order, OTel fanout, FB log sources, Restart-loop rule.

Areas NOT presented (settled by prior phases or research):
- Pipeline order (memory_limiter → batch) — locked by Pitfall 5 + INGEST-05
- Multitenancy / X-Scope-OrgID header — locked by Phase-2 D-26
- Tempo OTLP port assignment — locked by Phase-2 D-29
- gRPC port allocation — locked by Phase-2 D-28
- Per-role tag granularity — locked by Phase-2 D-24
- INSPQ grep gate enforcement — locked by Phase-1 D-21
- No-host-publish default — locked by Phase-1 D-12..D-14, Phase-2 D-30

---

## Plan/role order

### Q1: Dependency order for the 4 plans

| Option | Description | Selected |
|--------|-------------|----------|
| `node_exp → otel → prom → fb` | Dependency-true: zero-dep first; OTel uses Phase-2 backends; Prometheus needs producers alive; FB needs OTel alive. | ✓ |
| `prom → otel → fb → node_exp` | ROADMAP textual order; violates dependency order for OTel and FB. | |
| OTel first (`otel → node_exp → prom → fb`) | Central piece first; reshuffle of recommended. | |

**User's choice:** Dependency-true order. → D-41

**Notes:** Plan-to-role mapping cascades automatically (`03-01` node_exporter, `03-02` opentelemetry, `03-03` prometheus, `03-04` fluentbit); one-tag-per-role (Phase-1 D-24) preserved.

### Q2: More questions about Plan/role order, or move on?

| Option | Description | Selected |
|--------|-------------|----------|
| Next area | Order locked; remaining sub-details cascade. | ✓ |
| More questions | Verify-step shape per role, sub-tags, Phase-3 meta-check. | |

**User's choice:** Next area.

---

## OTel fanout

### Q1: Where should OTel route metrics?

| Option | Description | Selected |
|--------|-------------|----------|
| OTel → Mimir direct | OTel `prometheusremotewrite` exporter → Mimir; Prometheus only scrapes pull-targets. Preserves OTLP semantics. | |
| OTel → Prom → Mimir | OTel exposes Prometheus exporter; Prometheus scrapes + remote_writes. Single ingest path. | ✓ (after clarification) |
| Both paths | Direct + scrape; double-write. Diagnostic but wasteful. | |

**User's first response:** "But things like node exporter don't send to otel, otel would need to scrape them? We need to clarify that piece. I might be misunderstanding otel capacities."

**Claude clarification:** Explained the two orthogonal ingest paths: Prometheus owns pull-scrape (node_exporter, OTel's self-metrics on `:8888`, inventory targets) and OTel owns push (OTLP from instrumented apps). The fanout question was *only* about where OTLP-pushed metrics from instrumented apps should land. node_exporter goes through Prometheus regardless.

**User's choice after clarification:** OTel → Prom → Mimir. → D-42

### Q2: Prometheus scrape config shape for OTel's two endpoints

| Option | Description | Selected |
|--------|-------------|----------|
| `:8889 + :8888` two jobs | OTel exposes Prom exporter on `:8889`; self-metrics on `:8888`. Prometheus has two distinct jobs (`otel_self` and `otel_metrics`). | ✓ |
| Single `:8889` only | Skip self-metrics; lose Pitfall-5 visibility into OTel health. | |
| Merge to `:8888` | Single endpoint serves both. Tangled namespaces. | |

**User's choice:** `:8889 + :8888` two jobs. → D-42 (Prometheus scrape config side)

### Q3: Forward-compat knob for switching to direct push later

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, knob — default off | Both exporters declared; `telemetron_otel_metrics_path` selects which is in the pipeline. Forward-compat shape like Phase-2 D-27. | ✓ |
| No, single path only | Ship Prometheus exporter only; rewrite role later if direction changes. Pure YAGNI. | |

**User's choice:** Yes, knob — default off. → D-43

### Q4: More questions about OTel fanout, or move on?

| Option | Description | Selected |
|--------|-------------|----------|
| Next area | Topology + scrape shape + forward-compat knob settled. | ✓ |
| More questions | Loki exporter native-vs-OTLP-HTTP, per-signal queue tuning, etc. | |

**User's choice:** Next area.

---

## FB log sources

### Q1: What should FB tail by default?

| Option | Description | Selected |
|--------|-------------|----------|
| Docker container logs | Tail `/var/lib/docker/containers/*/*-json.log`. Highest signal for Docker-host stack. | ✓ |
| Docker + system logs | Above + `/var/log/{syslog,auth.log,kern.log,messages}`. | |
| systemd journal | journald via FB systemd input; requires journald logging driver. | |
| Everything | Docker + system + journal. Maximum coverage; maximum surface. | |

**User's choice:** Docker container logs. → D-46

### Q2: Docker → Loki label mapping (within D-37 allowlist)

| Option | Description | Selected |
|--------|-------------|----------|
| Docker labels first | Operator tags containers with `com.telemetron.{service,env,job}`; falls back to container_name. Level parsed from line content. High-cardinality → structured metadata. | ✓ |
| Container name only | `job` and `service` both = container_name; env from inventory; level parsed. Simpler, less semantic. | |
| Image-based | service = image basename; job = container_name. Image-name stable but brittle for forks. | |

**User's choice:** Docker labels first. → D-47

### Q3: Extension knobs for system-log / journald

| Option | Description | Selected |
|--------|-------------|----------|
| Knobs shipped, off | `fluentbit_tail_system_logs`, `fluentbit_tail_journald` both default false, Jinja-conditional. | ✓ |
| Docker only, hard-coded | Pure YAGNI; rewrite role later if asked. | |

**User's choice:** Knobs shipped, off. → D-48

### Q4: More questions about FB, or move on?

User's response was free text (not a label match): *"I just want to precise something. In telemetron, fluentbit was used mainly to scoop logs from legacy products that couldn't be instrumented with otel. Picking up the telemetron components logs is something I never thought about. That was a good catch by you."*

**Interpretation:** Not a request to move on yet — flagging a perspective shift. Claude:
1. Acknowledged the inversion (FB role shift from upstream INSPQ pattern to Telemetron M1 pattern).
2. Saved a project memory: `project_fluentbit_role_shift.md`.
3. Offered a follow-up question covering the legacy-host-scoop use-case via an `extra_tail_paths` knob.

### Q5 (follow-up): Add an `extra_tail_paths` knob to preserve the upstream-INSPQ legacy-host-scoop use-case?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes: extra_tail_paths knob | `fluentbit_extra_tail_paths: []` default; operator supplies list for legacy paths. | ✓ |
| No, defer | Ship Docker-only + the two knobs from Q3. | |

**User's choice:** Yes: extra_tail_paths knob. → D-48 (extended)

---

## Restart-loop rule

### Q1: How should ContainerRestartLoop get its data?

| Option | Description | Selected |
|--------|-------------|----------|
| OTel docker_stats | Receiver scrapes Docker socket; emits container.restarts. Reuses existing component. | ✓ |
| Up-transition proxy | `changes(up{}[10m]) > 3`. Zero new components; weaker signal; misses non-Prom-scraped containers. | |
| Defer the rule | Drop from M1 baseline; amend INGEST-03. | |

**User's choice:** OTel docker_stats. → D-51

### Q2: Docker socket security shape

| Option | Description | Selected |
|--------|-------------|----------|
| Direct mount, RO | `/var/run/docker.sock:ro` direct. `:ro` is kernel-write-block; doesn't restrict Docker API write surface. Accepted for single-host homelab. | ✓ |
| Socket proxy | Tecnativa-style sidecar; defense in depth; adds a component not on CLAUDE.md fixed list. | |
| Off-by-default | Receiver wired-but-disabled; operator opts in. Violates INGEST-03 default-on. | |

**User's choice:** Direct mount, RO. → D-52

### Q3: docker_stats receiver scope

| Option | Description | Selected |
|--------|-------------|----------|
| All containers | Telemetron stack + operator apps; bounded cardinality. | ✓ |
| Telemetron only | Name-filter to `telemetron-*`; smaller scope; misses operator workloads. | |

**User's choice:** All containers. → D-53

### Q4: Anything else still unclear?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | Decisions cover all 4 selected gray areas plus follow-ups. Remaining specifics are Claude's-discretion-within-research-bounds. | ✓ |
| More gray areas | Prometheus retention, alert PromQL shapes, node_exporter collector allowlist, etc. | |

**User's choice:** I'm ready for context.

---

## Claude's Discretion

Areas the user explicitly delegated to Claude (planner finalizes during plan-phase research):
- Prometheus local retention default (planner picks 15d unless research surfaces a reason to deviate)
- 3 non-restart alert rule PromQL shapes (`HostDown`, `FilesystemAlmostFull`, `OTelCollectorDroppingSignals`)
- node_exporter collector allowlist + bind-mount specifics
- `prometheus_extra_rules` schema shape
- OTel `mem_limit` / `GOMEMLIMIT` / `memory_limiter` exact ratios (within Pitfall-5 guidance)
- FB buffer sizing (`storage.max_chunks_up`)
- Verify-payload shapes per role (D-54 documents the broad shape; planner specifies exact synthetic-line content)
- D-25 "Deviations from upstream INSPQ" README section content per role

---

## Deferred Ideas Captured During Discussion

- Tecnativa docker-socket-proxy sidecar (hardening phase)
- Per-component bearer/mTLS auth at OTel/Prometheus/FB ingress (hardening phase)
- node_exporter `systemd` collector + `textfile` collector escape hatch (operator-knob; future iteration)
- FB → Loki direct path enablement as a knob (vs operator-fork)
- Comprehensive alert rule library (`prometheus_extra_rules` content or separate role; post-M1)
- OTel `host_metrics` receiver as a node_exporter replacement path (if node_exporter ever drops)
- Prometheus federation (multi-host milestone)
- Prometheus recording rules (post-M1 or alongside Phase 5 dashboards)
- Switching to OTel → Mimir direct push (D-43 forward-compat knob exists; flip when warranted)

All recorded in `03-CONTEXT.md` `<deferred>` section.
