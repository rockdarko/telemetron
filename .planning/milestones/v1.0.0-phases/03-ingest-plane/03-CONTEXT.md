# Phase 3: Ingest Plane - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Port the four producer/collector roles that feed the Phase-2 telemetry backends with real signal — **`node_exporter`**, **`opentelemetry`** (OTel Collector Contrib), **`prometheus`**, and **`fluentbit`** — each as an Ansible role deployed via Docker on the single homelab host. node_exporter exposes host metrics on `:9100`; the OTel Collector accepts OTLP on the standard `:4317`/`:4318` ports (claimable because Phase-2 D-29 moved Tempo's OTLP receivers off the standard pair to `:14317`/`:14318`); Prometheus scrapes pull-targets (node_exporter, OTel's `:8888`/`:8889`, inventory-defined targets) and remote_writes everything to Mimir; Fluent Bit tails Docker container logs on the host and ships them through OTel to Loki.

Each role mirrors the canonical patterns established by Phases 1 and 2: D-10a HEALTHCHECK poll before any downstream task, W6 single-handler restart, W7 `changed_when: false` on verify tasks, W8 in-network verify step, OPS-03 README schema, D-25 opinionated improvement (not mechanical translation) over upstream INSPQ. Four role ports + four playbook wirings + cross-cutting Phase-1+2-pattern carry-forward. Alertmanager + hook router are Phase 4; Grafana + datasource provisioning is Phase 5; Phase 3 stops at "producers are alive, scrape/push paths are wired end-to-end, baseline alert rules evaluate, and a synthetic log+metric+trace pushed through OTel lands in the right backends — all queried via the `telemetron` Docker network, no host port publishes required."

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues from Phase 2 (last decision was D-39). Phase 3 introduces D-40 through D-55.

### Plan structure & dependency order (D-40, D-41)

- **D-40:** **Four plans, one per role, in dependency-true order.** `03-01-PLAN.md` ports `roles/node_exporter/`; `03-02-PLAN.md` ports `roles/opentelemetry/`; `03-03-PLAN.md` ports `roles/prometheus/`; `03-04-PLAN.md` ports `roles/fluentbit/`. Mirrors the Phase-2 D-22 "one plan per role" shape. Each plan is end-to-end shippable in isolation (Phase-2 D-23 carry-forward — each plan wires its own role into `playbooks/deploy_docker.yml` as its final task; the playbook stays runnable at every commit). One tag per role per Phase-2 D-24.

- **D-41:** **Inter-plan order is dependency-true, NOT roadmap-textual.** node_exporter (zero deps — host-metrics-only) → opentelemetry (uses Phase-2 Loki/Tempo/Mimir endpoints; works standalone before Prometheus exists) → prometheus (needs node_exporter + OTel alive to scrape them, needs Mimir alive for `remote_write`) → fluentbit (needs OTel alive — default ship path is FB → OTel → Loki). Each plan's verify step (D-54) is satisfiable at plan-completion time without "waiting for the next plan to land." Playbook role order after Phase 3: `pre_tasks: [network] → minio → loki → tempo → mimir → node_exporter → opentelemetry → prometheus → fluentbit`. The ROADMAP's textual order `(prometheus, opentelemetry, fluentbit, node_exporter)` was a sibling-listing within Phase 3's goal paragraph, not a dependency assertion — D-41 supersedes it for execution order.

### OTel Collector fanout topology (D-42, D-43, D-44, D-45)

- **D-42:** **OTLP-pushed metrics route through Prometheus, NOT direct to Mimir.** OTel Collector exposes a `prometheus` exporter on `:8889` (separate from `:8888` which is OTel's *self*-metrics endpoint). Prometheus scrape config declares **two distinct jobs against the OTel container**: `otel_self` targeting `otel:8888` (collector internal health metrics — refused records, queue depth, exporter retries — Pitfall 5 surfaces) and `otel_metrics` targeting `otel:8889` (the Prometheus-formatted output of all OTLP-pushed app metrics). Prometheus then `remote_write`s **both** sets of series (plus node_exporter and inventory targets) to Mimir at `http://mimir:9009/api/v1/push`. **Single ingest path into Mimir** for diagnostic clarity at the cost of OTLP-native metric semantics (delta→cumulative coercion, OTLP attribute→Prometheus label mapping, exemplar fidelity reduction in transit). Cardinality concentration risk on Prometheus is mitigated by D-36 Mimir limits (back-pressure if Prometheus over-writes) plus the D-43 `metric_relabel_configs` defaults.

- **D-43:** **Forward-compat knob: OTel config ships BOTH exporters declared.** `roles/opentelemetry/templates/config.yaml.j2` declares `prometheus` (on `:8889`, in the metrics pipeline by default) AND `prometheusremotewrite` (pointing at `http://mimir:9009/api/v1/push`, declared-but-not-in-pipeline). Inventory knob `telemetron_otel_metrics_path: prometheus | remote_write` (default `prometheus`) selects which exporter the `metrics` pipeline references via Jinja conditional. Flipping the knob switches architectures without role rewrite — same shape pattern as Phase-2 D-27 vault-key aliases. Documented in `roles/opentelemetry/README.md` "Modes" section.

- **D-44:** **Loki and Tempo legs are unambiguous and locked.** Loki: OTel uses the `loki` exporter pointed at `http://loki:3100` (Loki HTTP push API). Tempo: OTel uses an `otlp` exporter (gRPC) pointed at the internal-only `tempo:14317` (locked by Phase-2 D-29). Neither leg has a forward-compat knob — single config shape per signal. Both endpoints are container-network-only; no host publish required (D-30).

- **D-45:** **OTel pipeline shape per Pitfall 5 + INGEST-05, all explicit in the template:**
  - `processors: [memory_limiter, batch, ...]` — order locked; `memory_limiter` MUST be first (Pitfall 5 reverse-order OOM mode). Inline-cited in the template with the PITFALLS § reference.
  - `GOMEMLIMIT` env var on the OTel container = **80%** of the container's Docker `mem_limit` (e.g. `mem_limit: 512m` → `GOMEMLIMIT=400MiB`).
  - `memory_limiter.limit_mib` = **65%** of GOMEMLIMIT; `spike_limit_mib` = **20%** of GOMEMLIMIT (so soft/hard limiter sits below where Go's GC has time to free, refusing data before the kernel OOM-kills).
  - **Every exporter** (loki, otlp/tempo, prometheus, prometheusremotewrite-when-active) declares `sending_queue: {enabled: true, num_consumers: 4, queue_size: 1000}` and `retry_on_failure: {enabled: true, initial_interval: 5s, max_interval: 30s, max_elapsed_time: 300s}`. Defaults are homelab-tuned (PITFALLS guidance).

### Fluent Bit (D-46, D-47, D-48, D-49, D-50)

- **D-46:** **FB default tail = Docker container logs at `/var/lib/docker/containers/*/*-json.log`** (read-only bind-mount), parsed with the `docker` JSON parser. Captures all containerized workloads on the host — Telemetron stack itself (loki, mimir, tempo, prometheus, otel, node_exporter, fluentbit own logs via Docker's json-file driver) AND operator-deployed apps colocated on the host. **This inverts the upstream INSPQ pattern.** Upstream INSPQ used FB on legacy hosts scooping app-specific log files to ship to a central observability host; Telemetron M1 colocates FB with the workloads it observes, on a single Docker host. Documented as a D-25 "Deviations from upstream INSPQ" entry in `roles/fluentbit/README.md`. (See memory: `project_fluentbit_role_shift.md`.)

- **D-47:** **FB → Loki label mapping within D-37's allowlist `{job, host, service, env, level}`:**
  - **`host`** — `{{ ansible_hostname }}` statically templated at deploy time.
  - **`service`** — Docker label `com.telemetron.service` if present on the source container; otherwise `container_name` stripped of leading `/`.
  - **`env`** — Docker label `com.telemetron.env` if present; otherwise inventory var `telemetron_env` (default `homelab`).
  - **`job`** — Docker label `com.telemetron.job` if present; otherwise `container_name` (same fallback as `service` but operators can override independently).
  - **`level`** — parsed from log line content via FB grep filter (regex `(?i)\b(INFO|WARN|ERROR|FATAL|DEBUG|TRACE)\b`); default `info` when no match.
  - **High-cardinality Docker metadata** (`container_id`, `image_id`, `image_name`, full image tag) → Loki **structured metadata**, NOT labels — per Pitfall 4 + D-37. Every Telemetron-managed container (every role's `docker_container` task) sets the three `com.telemetron.{service,env,job}` Docker labels automatically. Operator apps document the convention via `roles/fluentbit/README.md` "Labeling operator apps" section.

- **D-48:** **FB extension knobs (all default-off, conditionally emitted via Jinja):**
  - `fluentbit_tail_system_logs: false` — when `true`, adds `[INPUT]` sections for `/var/log/{syslog,auth.log,kern.log,messages}` (distro-agnostic via glob).
  - `fluentbit_tail_journald: false` — when `true`, adds a `[INPUT]` for systemd journal (requires bind-mount `/run/systemd/journal/socket` on the FB container; doc'd as a Linux-with-systemd-only knob).
  - `fluentbit_extra_tail_paths: []` — operator-supplied list of arbitrary tail paths. **Preserves the upstream-INSPQ legacy-host-scoop use-case** (FB on a host slot next to a non-instrumentable legacy app) without making it the default. Each entry emits one `[INPUT] Name tail / Path <entry>` Jinja-templated section.

- **D-49:** **FB → OTel transport: `opentelemetry` output plugin (OTLP/HTTP to `http://otel:4318/v1/logs`).** Cleanest mapping — preserves OTLP semantics end-to-end through the pipeline; FB 4.2.3 supports this natively. Rejected alternatives: `forward` protocol (would require OTel's `fluentforward` receiver — adds a receiver type and bypasses OTLP normalization), `http` raw-JSON output (mapping fragility; brittle parsing on the OTel side). FB → Loki **direct** is documented as an alternative path in `roles/fluentbit/README.md` per INGEST-06 (escape hatch when OTel is down or operator wants to bypass the OTel layer).

- **D-50:** **FB buffer & timestamp discipline:**
  - `storage.type filesystem` writing to `telemetron_fluentbit_buffer` Docker volume (mounted at `/var/log/flb-storage/` — already declared in Phase-1 D-16). Survives container restart without log loss.
  - `storage.max_chunks_up: 128` (homelab-sized memory cap on the in-flight chunk window).
  - `Time_System_Timezone Etc/UTC` (Pitfall 6 single-most-impactful one-liner — no DST drift).
  - `Multiline_Flush 5` (fail-fast on misparsed multiline events rather than aggregate forever — Pitfall 6).
  - `Read_from_Head: false` (start at tail, don't replay pre-deploy logs on first boot).
  - `[FILTER] modify` asserting `@timestamp` exists, falling back to ingest time when absent (Pitfall 6 three-failure-modes mitigation).

### ContainerRestartLoop alert source + Docker socket security (D-51, D-52, D-53)

- **D-51:** **OTel Collector's `docker_stats` receiver provides the ContainerRestartLoop signal.** Receiver scrapes the Docker socket (bind-mounted into the OTel container) and emits `container.uptime`, `container.cpu.usage.total`, `container.memory.usage.total`, `container.network.io.usage.{tx,rx}.bytes`, etc. as OTLP metrics. **The restart count comes from `container.restarts`** (cumulative since container creation — OTel converts to cumulative Prometheus series via the D-42 OTel→Prometheus→Mimir path). Restart-loop alert PromQL: `increase(container_restarts_total[10m]) >= 3`. Satisfies INGEST-03 success criterion 3. `collection_interval: 30s` (matches Prometheus scrape; minimizes Docker daemon load).

- **D-52:** **Docker socket security: direct bind-mount `/var/run/docker.sock:/var/run/docker.sock:ro` on the OTel container.** Acknowledged threat-model limitation: the `:ro` modifier is a kernel-level write block but Docker API operations use POST-over-HTTP-over-socket — a compromised OTel container could still issue Docker API calls (start privileged containers, escalate to host) **at the API layer**. **Acceptable for M1 homelab single-host threat model** — the operator already owns the host and trusts Telemetron images. Documented as a **Security Model + Threat Caveat** section in `roles/opentelemetry/README.md` so future-Rock or operators deploying Telemetron next to less-trusted workloads can opt into a Tecnativa-style `docker-socket-proxy` sidecar in a hardening phase. Adding the proxy is deferred (CLAUDE.md component list is fixed for M1; adding a sidecar is out of scope here).

- **D-53:** **`docker_stats` scope: ALL containers the Docker daemon sees, no name filter.** Captures operator workloads (the high-value catchment for ContainerRestartLoop — most homelab operators want the alert to fire on *their* app flapping, not just the Telemetron stack). Cardinality bounded by typical container count (`<30` on a homelab) so no Pitfall 3 risk. Documented in `roles/opentelemetry/README.md` "What metrics are collected" section.

### Verify steps + vault surface (D-54, D-55)

- **D-54:** **Per-role in-network verify (mirrors Phase-2 D-32, one-shot container on the `telemetron` bridge):**
  - **node_exporter** (`03-01`): one-shot `curlimages/curl` container curls `http://node-exporter:9100/metrics`; assert non-empty body containing `node_cpu_seconds_total`.
  - **opentelemetry** (`03-02`): one-shot `otel/opentelemetry-collector-contrib` client container configured to push a synthetic OTLP trace + log + metric to `otel:4317`; sequential mc-ls assertions across `mimir-blocks` / `loki-chunks` / `tempo-traces` to confirm objects landed. (NB: this verify runs BEFORE prometheus plan exists, so the metrics-arrival assertion is on the Mimir bucket directly — exporter pipeline reaches Mimir even without Prometheus, via the D-43 forward-compat path: for verify purposes, plan 03-02 temporarily flips the OTel metrics pipeline to use `prometheusremotewrite` so the metric makes it to Mimir; plan 03-03 reverts to the `prometheus` exporter when Prometheus is wired. Alternative: skip the metric assertion in 03-02's verify and pick it up in 03-03's verify. **Planner picks one approach** based on which is cleaner in research.)
  - **prometheus** (`03-03`): one-shot `curlimages/curl` curls `http://prometheus:9090/api/v1/targets` and asserts both `otel_self` (`:8888`) and `otel_metrics` (`:8889`) jobs report `up`; curls `/api/v1/rules` and asserts the four baseline rule names are loaded (`HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals`); curls `/api/v1/query?query=up{job=~"otel_.*|node_exporter"}` and asserts non-zero result count.
  - **fluentbit** (`03-04`): bind-mount a synthetic log path into FB (e.g. `/tmp/flb-test/`), write a uniquely-tagged synthetic log line, wait `Multiline_Flush + scrape_interval ≈ 10s`, then one-shot `curlimages/curl` queries `http://loki:3100/loki/api/v1/query_range?query={service="flb-test"}` and asserts the synthetic line is returned. All one-shot containers use `auto_remove: true` (W7) and `changed_when: false` (W7) per Phase-1 conventions.

- **D-55:** **Vault key surface for Phase 3: NONE added.** All four Phase 3 components operate on the `telemetron` Docker network with no outbound credentials needed: node_exporter has no auth, OTel Collector accepts unauth OTLP (M1 single-host design where producer trust is bounded by network membership), Prometheus has no auth surface in the M1 config (Mimir's remote_write endpoint accepts unauth — D-26 multitenancy-off), Fluent Bit ships logs OTLP-unauth. `inventory/example-homelab/group_vars/all/vault.yml.example` does NOT grow in Phase 3. **Future hardening phase** can layer bearer tokens / mTLS at all four boundaries (queued as a deferred idea below).

### Claude's Discretion (research-bounded — planner picks defaults, planner's call within these bounds)

- **Prometheus local retention** — `--storage.tsdb.retention.time` default **15d** (upstream Prometheus default; comfortably > Mimir's `query_store_after: 12h` per Phase-2 D-36). Knob `prometheus_retention_time` surfaced in `roles/prometheus/defaults/main.yml` for operator override.
- **node_exporter collectors enabled** — stock defaults (upstream image's enabled-by-default set); explicit allowlist *not* applied in M1. Bind-mounts: `/proc → /host/proc:ro`, `/sys → /host/sys:ro`, `/ → /rootfs:ro` with corresponding `--path.{procfs,sysfs,rootfs}` args. Standard pattern.
- **Prometheus `metric_relabel_configs` defaults** — drop labels matching `pod_uid`, `container_id`, `request_id`, `trace_id`, plus any label name ending in `_id` that has UUID-shaped values. Inline-comment-cite Pitfall 3 + INGEST-01. Knob `prometheus_extra_relabel_configs` surfaces operator extensions.
- **3 non-restart-loop alert rule PromQL shapes** (planner finalizes during plan-phase research):
  - `HostDown`: `up == 0 for 2m` (INGEST-03 spec)
  - `FilesystemAlmostFull`: `(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes) < 0.15 for 5m` (>85% used per INGEST-03)
  - `OTelCollectorDroppingSignals`: `(rate(otelcol_processor_refused_spans[5m]) + rate(otelcol_processor_refused_log_records[5m]) + rate(otelcol_processor_refused_metric_points[5m])) > 0 for 5m` (INGEST-03 + Pitfall 5 warning signs)
- **`prometheus_extra_rules` shape** — list-of-dicts inventory var (each dict: `name`, `expr`, `for`, `labels`, `annotations`); Jinja iterates with `| sort(attribute='name')` per D-20 sorted-keys discipline. Default `[]`.
- **OTel `mem_limit`** — `512m` container default; operator-overridable. With GOMEMLIMIT 400MiB / memory_limiter 320MiB soft / 384MiB hard (D-45 ratios).
- **FB Loki output `LogLevel` field mapping** — defer to OTel Collector's `loki` exporter handling once OTLP-wrapped; FB does not write directly to Loki on the default path.
- **D-25 "Deviations from upstream INSPQ" README section per role** — list shape proposed by planner after researcher's audit pass. Known entries the audit should surface: FB role inversion (D-46), OTel docker_stats addition (was inline `docker` Ansible facts in INSPQ, replaced with collector-native), Prometheus `metric_relabel_configs` defaults (INSPQ relied on operator-tuned configs), `node_exporter`'s textfile-collector escape hatch (whether to expose by default).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project framing & scope
- `.planning/PROJECT.md` — Vision, constraints, Tech Stack section (CLAUDE.md mirrors and includes the full per-component pin table: Prometheus `v3.11.3`, OTel Collector Contrib `0.152.0`, Fluent Bit `4.2.3`, node_exporter latest stable).
- `.planning/REQUIREMENTS.md` §"Ingest plane (INGEST)" — Phase 3 REQ-IDs INGEST-01..INGEST-08 with full acceptance text.
- `.planning/ROADMAP.md` §"Phase 3: Ingest Plane" — Goal, 5 success criteria, requirement mapping.

### Phase 1 + 2 decisions that propagate forward (read in full before Phase 3 planning)
- `.planning/phases/01-foundation-storage/01-CONTEXT.md` — D-04 (network in pre_tasks), D-06 (no shared base role), D-10a (HEALTHCHECK poll), D-12..D-14 (no host publish), D-15..D-18 (inventory + volumes + config layout), D-19..D-21 (handler restart, sorted-keys Jinja, grep gates).
- `.planning/phases/02-telemetry-backends/02-CONTEXT.md` — D-22 (one plan per role), D-23 (each plan wires its own role), D-24 (one tag per role), D-25 (opinionated improvement over upstream), D-26 (multitenancy off — no `X-Scope-OrgID` on remote_write), D-27 (per-backend vault key aliases — pattern reused for Phase 3 *if* any vault keys land, which D-55 says they don't), D-28 (gRPC port pinning: Loki 9095 / Tempo 9096 / Mimir 9097 — Prometheus scrapes Mimir on HTTP `:9009` not gRPC), D-29 (Tempo OTLP on internal `:14317`/`:14318` — unlocks `:4317`/`:4318` for OTel Collector), D-30 (no host publish default), D-31 (full Phase-2 port matrix), D-32 (in-network verify one-shot — pattern reused as D-54), D-36 (Mimir limits — Phase 3 Prometheus relabels stay within), D-37 (Loki label discipline — FB allowlist `{job, host, service, env, level}` lands in Phase 3).
- `roles/minio/`, `roles/loki/`, `roles/tempo/`, `roles/mimir/` (entire roles) — canonical role-port templates. Every Phase 3 role layout, README schema, defaults file, handlers shape, verify-task pattern mirrors these.
- `roles/README.md` §"Port process" + §"Per-role port-acceptance gates" — grep gates, image-pin gate, vault gate, idempotency gate, healthcheck+restart gate, README gate. Every Phase 3 role passes all six.

### Research backing for this phase
- `.planning/research/PITFALLS.md` §"Pitfall 3: High-cardinality label explosion in Prometheus/Mimir" — Backing for D-42 cardinality-on-Prometheus mitigation + D-43 forward-compat knob + `metric_relabel_configs` defaults (Claude's discretion section).
- `.planning/research/PITFALLS.md` §"Pitfall 4: Loki label discipline" — Backing for D-47 label allowlist mapping + structured-metadata channeling for high-cardinality fields.
- `.planning/research/PITFALLS.md` §"Pitfall 5: OTel Collector pipeline misconfiguration" — Backing for D-45 pipeline shape, GOMEMLIMIT/memory_limiter/sending_queue/retry_on_failure defaults, processor order.
- `.planning/research/PITFALLS.md` §"Pitfall 6: Fluent Bit timestamp drift" — Backing for D-50 (UTC, multiline_flush, fallback @timestamp filter).
- `.planning/research/PITFALLS.md` §"Pitfall 8: Ansible role idempotency cascades" — Backing for handler-restart-not-state-restarted across all four Phase 3 roles.
- `.planning/research/PITFALLS.md` §"Pitfall 9: Fork-from-INSPQ leftovers" — Backing for grep gates per role (D-21 carry-forward).
- `.planning/research/PITFALLS.md` §"Pitfall-to-Phase Mapping" — Confirms Pitfalls 3, 4, 5, 6 land specifically in Phase 3 role ports.
- `.planning/research/PITFALLS.md` §"Performance Traps" + §""Looks Done But Isn't" Checklist" — Per-role acceptance items (Prometheus head-series stable, FB timestamp correctness, OTel queue not saturated).
- `.planning/research/STACK.md` — Image pin sources (Prometheus 3.11.3, OTel Collector Contrib 0.152.0, Fluent Bit 4.2.3, node_exporter); component port matrix.
- `.planning/research/FEATURES.md` — OTel Collector receivers/exporters/processors catalog (informs D-51 docker_stats receiver pick, D-44 loki/otlp exporter picks).
- `.planning/research/ARCHITECTURE.md` — Signal-flow apps → OTel → backends; the "OTel as gateway" stance.

### Upstream INSPQ source-of-truth (for porting + D-25 improvement audit)
- `~/git/inspq/ansible/node_exporter/` (operator workstation) — Source role for `03-01-PLAN.md`.
- `~/git/inspq/ansible/opentelemetry/` — Source role for `03-02-PLAN.md`. D-25 audit MUST surface: hardcoded INSPQ-internal OTLP endpoints, French-locale processor names, any Quebec-gov cert chains in receivers, missing `memory_limiter` + `GOMEMLIMIT` discipline (Pitfall 5).
- `~/git/inspq/ansible/prometheus/` — Source role for `03-03-PLAN.md`. D-25 audit MUST surface: hardcoded INSPQ scrape targets, missing high-cardinality relabel defaults (Pitfall 3), French-only rule annotations.
- `~/git/inspq/ansible/fluentbit/` — Source role for `03-04-PLAN.md`. D-25 audit MUST surface: legacy-host-scoop assumptions in the input section (per the D-46 role inversion), `America/Montreal` or similar DST-observing TZ in `Time_System_Timezone` (Pitfall 6), missing UTF-8 forced encoding, any French-language parsers.

### Ansible module & collection documentation
- [community.docker.docker_container module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_module.html) — Primary module per role.
- [community.docker.docker_container_info module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_info_module.html) — D-10a HEALTHCHECK poll pattern (carries to all four Phase 3 roles).
- [community.docker.docker_volume module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_volume_module.html) — Per-role `telemetron_<role>_data` + `telemetron_fluentbit_buffer` volumes.

### Upstream component docs (consulted by research per D-54 verify shapes + D-49 transport pick + D-51 receiver pick)
- [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/) — scrape_configs, remote_write, metric_relabel_configs syntax.
- [Prometheus remote_write to Mimir](https://grafana.com/docs/mimir/latest/configure/configure-prometheus-remote-write/) — Endpoint shape, header requirements (per D-26 no `X-Scope-OrgID` needed).
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) — Rule file format, `for:` semantics, label/annotation conventions.
- [OpenTelemetry Collector configuration](https://opentelemetry.io/docs/collector/configuration/) — Receiver/processor/exporter/pipeline shape.
- [OTel Collector `prometheus` exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusexporter) — Backing for D-42 `:8889` shape.
- [OTel Collector `prometheusremotewrite` exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusremotewriteexporter) — Backing for D-43 forward-compat declaration.
- [OTel Collector `loki` exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/lokiexporter) — Backing for D-44 Loki leg.
- [OTel Collector `docker_stats` receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/dockerstatsreceiver) — Backing for D-51 + D-53 (scope, collection_interval).
- [OTel Collector `memory_limiter` processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/memorylimiterprocessor) — Backing for D-45 GOMEMLIMIT/limit_mib/spike_limit_mib ratios.
- [OTel Collector `sending_queue` + `retry_on_failure`](https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md) — Backing for D-45 per-exporter resilience defaults.
- [Fluent Bit `tail` input plugin](https://docs.fluentbit.io/manual/pipeline/inputs/tail) — Backing for D-46 Docker-logs default + D-48 extra-paths knob shape.
- [Fluent Bit `docker` parser](https://docs.fluentbit.io/manual/pipeline/parsers/json) — JSON parser for Docker's `*-json.log` format.
- [Fluent Bit `opentelemetry` output plugin](https://docs.fluentbit.io/manual/pipeline/outputs/opentelemetry) — Backing for D-49 transport pick.
- [Fluent Bit `storage` configuration](https://docs.fluentbit.io/manual/administration/buffering-and-storage) — Backing for D-50 filesystem buffer.
- [node_exporter README](https://github.com/prometheus/node_exporter) — Standard collectors, recommended bind-mounts (`--path.{procfs,sysfs,rootfs}`).

### Locked naming normalizations (Phase 1 baseline, carried forward)
- git commit `ba836d2` — naming locked.
- Phase 1 conventions: vault keys `vault_<role>_<purpose>` (none added in Phase 3 per D-55), volumes `telemetron_<role>_data` + `telemetron_fluentbit_buffer`, config dirs `/opt/telemetron/<role>/`, tags one-per-role.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`roles/minio/`, `roles/loki/`, `roles/tempo/`, `roles/mimir/`** — Four canonical role templates established in Phases 1 + 2. Every layout choice (directory shape, defaults file structure, handler convention, README schema, verify-via-one-shot-container pattern, D-10a HEALTHCHECK poll, D-32 in-network verify) propagates verbatim to the four Phase 3 roles. Researcher AND planner should read all four roles before producing the Phase 3 plan family.
- **`roles/minio/tasks/bootstrap.yml`** — D-10a `docker_container_info` HEALTHCHECK poll pattern. Each Phase 3 role mirrors this shape for "wait for the container to be ready before pushing the verify payload."
- **`roles/tempo/`** — Especially relevant for Phase 3 OTel decisions: Tempo binds OTLP on internal-only `:14317`/`:14318` per D-29, so the OTel Collector role can claim `:4317`/`:4318` without clash. The OTel Tempo-leg exporter (D-44) points at `tempo:14317`.
- **`roles/mimir/`** — Relevant for D-42 Prometheus → Mimir remote_write: Mimir's HTTP `:9009/api/v1/push` is unauth (D-26 multitenancy off) and accepts the Prometheus remote_write protocol natively (no extra config needed on the Prometheus side beyond the URL).
- **`roles/loki/`** — Relevant for D-44 OTel → Loki: Loki's HTTP `:3100` push API is unauth (`auth_enabled: false` per D-26) and accepts the OTel `loki` exporter's payload format natively.
- **`inventory/example-homelab/group_vars/all/storage.yml`** — `telemetron_volume_prefix`, `telemetron_config_root`, `telemetron_default_log_retention` (referenced by D-50 FB buffer + INGEST-06 timestamp discipline). Phase 3 adds per-role files: `node_exporter.yml`, `opentelemetry.yml`, `prometheus.yml`, `fluentbit.yml`.
- **`inventory/example-homelab/group_vars/all/network.yml`** — `telemetron_network`, `telemetron_publish_default: false`, `telemetron_tz: Etc/UTC` (the latter especially relevant for D-50 FB timestamp discipline). Phase 3 roles consume all three.
- **`inventory/example-homelab/group_vars/all/vault.yml.example`** — Phase 3 does NOT extend this file (D-55).
- **`playbooks/deploy_docker.yml`** — Has the pre_task creating the `telemetron` network and the role list ending at `mimir`. Phase 3 plans append four role entries below `role: mimir` per D-41 order.

### Established patterns (mirrored from Phases 1 + 2; planner enforces in Phase 3)
- **Role layout** — `defaults/main.yml`, `tasks/main.yml`, `tasks/<verify_step>.yml`, `handlers/main.yml`, `templates/<file>.j2`, `meta/main.yml`, `vars/` (where needed), `README.md`.
- **Image pin discipline (OPS-01)** — `prom/prometheus:v3.11.3`, `otel/opentelemetry-collector-contrib:0.152.0`, `fluent/fluent-bit:4.2.3`, `prom/node-exporter:<latest stable pin>` (planner picks specific tag during research — `v1.8.x` line per upstream conventions).
- **Volume naming (D-16)** — `telemetron_prometheus_data` (for TSDB), `telemetron_fluentbit_buffer` (FB filesystem storage). node_exporter and OTel Collector are stateless.
- **Config bind-mount (D-18)** — Host `/opt/telemetron/{prometheus,opentelemetry,fluentbit,node_exporter}/<file>` → container canonical path read-only.
- **Restart-by-handler (D-19, W6)** — One handler per role, `docker restart <name>` on config change; never `state: restarted`.
- **Sorted-keys Jinja iteration (D-20)** — `{% for k in d.keys() | sort %}` in every templated config.
- **In-network verify one-shot (D-32 → D-54)** — Final task is a one-shot container on the `telemetron` network that pushes/queries and asserts.
- **Grep gates per role (D-21)** — INSPQ-noise + non-ASCII gates per role port.
- **No-host-publish default (D-12..D-14, D-30)** — `<role>_publish_host: false` per role.

### Integration points
- **`playbooks/deploy_docker.yml`** — Each Phase 3 plan appends one role entry per D-41 order. Final shape after Phase 3: `pre_tasks: [network] → minio → loki → tempo → mimir → node_exporter → opentelemetry → prometheus → fluentbit`. Subsequent phases (Alertmanager, hook router, Grafana, Karma, PromLens, nfsd) append on top.
- **`inventory/example-homelab/group_vars/all/`** — Phase 3 adds four per-role files: `node_exporter.yml`, `opentelemetry.yml`, `prometheus.yml`, `fluentbit.yml`. Vault file UNCHANGED (D-55).
- **`roles/README.md`** — Update the role-status table (rows for node_exporter / opentelemetry / prometheus / fluentbit) as each plan completes — port-acceptance gates each role passes.
- **`/opt/telemetron/{node_exporter,opentelemetry,prometheus,fluentbit}/`** — Four new host-side config trees created by each role's first task.
- **`telemetron` bridge network** — All four Phase 3 containers attach. Producers (node_exporter, OTel via `:8888`/`:8889`) become scrape targets for Prometheus; collectors (OTel, FB) reach the Phase-2 backends by Docker DNS (`loki:3100`, `tempo:14317`, `mimir:9009`).
- **Docker socket** — Mounted RO into the OTel container only (D-52), exclusively for the `docker_stats` receiver (D-51). No other Phase 3 role binds the socket.

</code_context>

<specifics>
## Specific Ideas

- **Opinionated improvement audit per D-25 is non-negotiable** — every Phase 3 role plan's "Deviations from upstream INSPQ" README section MUST surface: hardcoded INSPQ paths/hostnames, missing pitfall guards (Pitfalls 3/4/5/6 specifically — these are Phase-3-coded in PITFALLS.md), French-locale defaults (DST-observing TZ, FR rule annotations, FR comments), and any defaults that only made sense in a Quebec-gov-scale multi-host deploy vs a single-host homelab.
- **The OTel docker_stats receiver is the cleanest cross-cutting addition.** It replaces what would otherwise be a separate cAdvisor role (out of scope per CLAUDE.md fixed component list) and provides container restart/CPU/memory/network signals that node_exporter cannot. Documented as a D-25 improvement entry in `roles/opentelemetry/README.md`.
- **FB role inversion vs upstream (D-46)** — INSPQ used FB on legacy hosts to scoop logs from non-instrumentable apps. Telemetron M1 colocates FB with workloads on a single Docker host, tailing container logs by default. The `fluentbit_extra_tail_paths` knob (D-48) preserves the upstream-INSPQ use-case without making it the default.
- **Single ingest path into Mimir (D-42)** — Rock's explicit pick. Sacrifices OTLP-native metric semantics in transit for diagnostic clarity ("everything that lands in Mimir came through Prometheus" is a load-bearing mental model). D-43 forward-compat knob keeps the door open to flip later without rewriting the role.
- **OTel collector and Prometheus share an architectural responsibility split: OTel owns push (OTLP), Prometheus owns pull (scrape).** Both write to Mimir, but they don't compete for the same signals. node_exporter's metrics never touch OTel; OTLP-instrumented app metrics never touch Prometheus's pull path (they enter via OTel's `:8889` exporter, which Prometheus *scrapes* but as a single scrape target, not as N pulled targets).
- **Docker socket security tradeoff (D-52)** — `:ro` is a kernel-level write-block that doesn't fully restrict Docker's HTTP-API-over-socket. Accepted for M1 homelab single-host where the operator trusts their images and host. Future hardening: Tecnativa docker-socket-proxy as a sidecar — documented in `roles/opentelemetry/README.md` "Threat model" section so operators considering broader deployments have the path.
- **"Single host where the operator owns it" is a load-bearing assumption** for the FB Docker-logs default (D-46), the docker_stats Docker-socket mount (D-52), and the unauth OTLP/Prometheus/Mimir wire format (D-55). When Telemetron eventually targets multi-host or less-trusted deployments, all three reverse simultaneously — and that's a hardening-milestone trigger, not an M1 patch.

</specifics>

<deferred>
## Deferred Ideas

### Out of Phase 3 (lands in later Phases / future milestones)

- **Per-component bearer/mTLS auth on OTel/Prometheus/FB ingress** — M1 single-host design assumes `telemetron`-network membership as the trust boundary (D-55). Layering auth at all four boundaries is a hardening-milestone candidate.
- **Tecnativa-style docker-socket-proxy sidecar** — Defense in depth for the D-52 Docker socket mount. CLAUDE.md component list is fixed for M1 (adding a sidecar is out of scope here). Future-Rock can layer it in a hardening phase; D-52 README documents the path.
- **Prometheus federation** — Multi-host metric aggregation. M1 is single-host; deferred until distributed-mode milestone.
- **Prometheus recording rules** — Pre-aggregated PromQL queries materialized as new series. Phase 3 ships alert rules only; recording rules can land alongside dashboard work (Phase 5 or post-M1).
- **OTel Collector → Mimir direct push** — D-43 forward-compat knob exists; flipping `telemetron_otel_metrics_path: remote_write` switches to direct push. Defer the flip until there's a reason (e.g. OTLP-native semantics matter for a specific app).
- **OTel Collector `service-graph` connector → Tempo metrics-generator integration** — Phase-2 D-38 picked local-WAL-only for Tempo's metrics-generator; OTel's service-graph connector is the alternative path. Lands when (if) Rock wants Grafana's service-graph view post-M1.
- **node_exporter `systemd` collector** — Requires D-Bus bind-mount; not enabled by default in M1 (stock collectors only). Operator can opt-in via a knob in a future iteration.
- **node_exporter `textfile` collector escape hatch** — Operators sometimes ship custom metrics by writing `.prom` files to a directory the exporter watches. Not enabled by default; could surface as a knob if requested.
- **FB → Loki direct path enablement** — INGEST-06 mandates the path be documented as an alternative in `roles/fluentbit/README.md`. The role can implement it as a knob (`fluentbit_loki_direct: false` default; flipping bypasses OTel) — planner decides whether to ship the knob in Phase 3 or defer to operator-fork.
- **PromQL retention auto-tuning** — Currently 15d static; could auto-derive from `Mimir's query_store_after × safety_margin`. Defer to ops-tooling pass post-M1.
- **Comprehensive alert rule library** — INGEST-03 ships 4 baseline rules. A broader library (10-30 rules covering Loki/Mimir/Tempo/Karma health, common app patterns) could ship as `prometheus_extra_rules` content or as a separate `roles/prometheus_alert_library/` role. Future phase or post-M1.
- **OTel Collector `host_metrics` receiver** — Alternative path to node_exporter (OTel-native host metrics). Currently kept separate because node_exporter is on the M1 fixed component list and replacing it would be an architectural change. If node_exporter is ever dropped, OTel `host_metrics` is the natural replacement.

### Already deferred from earlier phases (still applicable)

- **MinIO replacement (Garage / SeaweedFS)** — Already deferred from M1.
- **Multi-tenant Loki/Mimir** — D-26 disables. Adding tenants in v2 requires flipping the flag + every Phase 3 producer needs the `X-Scope-OrgID` header.
- **Distributed/scalable-single-binary modes** — Loki/Tempo/Mimir all support beyond-monolithic.
- **HAProxy in front of distributed backends** — Already deferred per PROJECT.md.

### Out of Phase 3 (lands in Phase 4+)
- **Alertmanager + hook router (`hooks/router/` Flask app, alert routing, allowlist, rate limit, vault-supplied Jenkins token)** — Phase 4.
- **Sample Jenkinsfile runbooks under `hooks/jobs/`** — Phase 4.
- **Grafana datasource provisioning with explicit UIDs (`prometheus`, `loki`, `tempo`, `mimir`)** — Phase 5.
- **Bundled 5-10 starter dashboards (host health, Loki/Tempo/Mimir Explore, OTel self-metrics, backend health)** — Phase 5.
- **Trace-to-logs correlation (`tracesToLogsV2` + derived `trace_id` field)** — Phase 5.
- **Karma + PromLens** — Phase 5.
- **`nfsd` opt-in role** — Phase 6.
- **M1 acceptance smoke test** (synthetic log + metric + trace in Grafana within 60s) — Phase 6 (OPS-07).
- **`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`** — Phase 6.

### Reviewed Todos (not folded)
None — `gsd-tools todo match-phase 3` returned zero matches.

</deferred>

---

*Phase: 03-ingest-plane*
*Context gathered: 2026-05-18*
