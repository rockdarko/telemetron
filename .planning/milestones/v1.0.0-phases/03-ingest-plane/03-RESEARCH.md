# Phase 3: Ingest Plane - Research

**Researched:** 2026-05-18
**Domain:** Ansible-deployed observability ingest plane on Docker (node_exporter, OTel Collector Contrib 0.152.0, Prometheus 3.11.3, Fluent Bit 4.2.3) producing data into the Phase-2 monolithic Loki/Tempo/Mimir backends
**Confidence:** HIGH for stack pins, config shapes, OTel metric names and Prometheus syntax (verified against official sources / repo contents at v0.152.0). MEDIUM for the Tempo OTLP-port-collision side of D-44's `otlphttp`-to-Loki replacement (logically sound, needs hands-on confirmation at execute time). LOW where flagged inline.

## Summary

Phase 3 ports four Ansible roles in dependency order (`node_exporter → opentelemetry → prometheus → fluentbit` per D-41) that mirror the canonical role-template Phase 1+2 established on `roles/minio/`, `roles/loki/`, `roles/tempo/`, and `roles/mimir/`. The OTel Collector terminates external OTLP on `:4317`/`:4318` (unlocked by Phase-2 D-29 moving Tempo OTLP to `:14317`/`:14318`) and fans out to Loki, Tempo, and Prometheus-or-Mimir; Prometheus owns the single ingest path into Mimir (D-42); Fluent Bit tails Docker container logs by default (D-46 inversion vs INSPQ) and ships through OTel (D-49); node_exporter is host-bind-mounted and scraped by Prometheus (INGEST-08).

**Two load-bearing research corrections the planner MUST surface before plan-phase:**

1. **D-44 is broken at the pinned tag.** The `loki` exporter was deprecated 2024-07-09 and **removed from `opentelemetry-collector-contrib` in v0.131.0**. The Phase-3 pin `otel/opentelemetry-collector-contrib:0.152.0` does NOT ship a `loki` exporter — verified via `gh api repos/open-telemetry/opentelemetry-collector-contrib/contents/exporter?ref=v0.152.0` (no `lokiexporter` entry). The current canonical OTel→Loki path is the `otlphttp` exporter targeting Loki's `/otlp` endpoint (`http://loki:3100/otlp`). Loki 3.7.2 natively supports OTLP/HTTP ingestion. **D-44 needs amendment** (or the planner picks the substitution and documents it as a D-25 deviation).

2. **D-45's `OTelCollectorDroppingSignals` PromQL metric prefix is wrong.** Collector self-metrics for refused-by-pipeline counters live under `otelcol_receiver_refused_*`, NOT `otelcol_processor_refused_*`. The `processor_*` prefix exists but counts items passing through processors, not refused data. The CONTEXT.md alert-rule discretion item must use `otelcol_receiver_refused_{spans,log_records,metric_points}`.

**Primary recommendation:** Plan 03-02 (opentelemetry) carries the heaviest research-derived deviation surface — both corrections above land there. Plans 03-01, 03-03, 03-04 are mechanical ports with PITFALL-aligned defaults baked in. The four plans together append 4 role entries to `playbooks/deploy_docker.yml`, 4 inventory `<role>.yml` files, 0 vault keys (D-55), and bring the role-status table to 7-of-14 ported.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Plan structure & dependency order:**
- **D-40:** Four plans, one per role. `03-01-PLAN.md` ports `roles/node_exporter/`; `03-02-PLAN.md` ports `roles/opentelemetry/`; `03-03-PLAN.md` ports `roles/prometheus/`; `03-04-PLAN.md` ports `roles/fluentbit/`.
- **D-41:** Inter-plan order is dependency-true: `node_exporter → opentelemetry → prometheus → fluentbit`. Playbook role order after Phase 3: `pre_tasks: [network] → minio → loki → tempo → mimir → node_exporter → opentelemetry → prometheus → fluentbit`.

**OTel Collector fanout topology:**
- **D-42:** OTLP-pushed metrics route through Prometheus, NOT direct to Mimir. OTel exposes `:8889` Prometheus-format exporter (separate from `:8888` self-metrics). Prometheus declares TWO scrape jobs (`otel_self` → `otel:8888`, `otel_metrics` → `otel:8889`) and remote_writes both to Mimir.
- **D-43:** OTel config ships BOTH exporters declared (`prometheus` AND `prometheusremotewrite`). Jinja knob `telemetron_otel_metrics_path: prometheus | remote_write` (default `prometheus`) selects.
- **D-44:** Loki and Tempo legs locked: Loki via `loki` exporter at `http://loki:3100`; Tempo via OTLP gRPC at `tempo:14317`. **NOTE: see Summary correction #1 — `loki` exporter is removed from v0.152.0.**
- **D-45:** Pipeline shape `processors: [memory_limiter, batch, ...]` order locked; `GOMEMLIMIT` = 80% mem_limit; `memory_limiter.limit_mib` = 65% GOMEMLIMIT; `spike_limit_mib` = 20% GOMEMLIMIT; every exporter declares `sending_queue: {enabled: true, num_consumers: 4, queue_size: 1000}` + `retry_on_failure: {enabled: true, initial_interval: 5s, max_interval: 30s, max_elapsed_time: 300s}`.

**Fluent Bit:**
- **D-46:** FB default tail = `/var/lib/docker/containers/*/*-json.log` (read-only bind-mount), parsed with the `docker` JSON parser. Role inversion vs INSPQ.
- **D-47:** FB→Loki label allowlist `{job, host, service, env, level}` mapped from Docker labels `com.telemetron.{service,env,job}` with container-name and regex fallbacks; high-cardinality fields go to Loki structured metadata.
- **D-48:** Extension knobs `fluentbit_tail_system_logs`, `fluentbit_tail_journald`, `fluentbit_extra_tail_paths` all default-off.
- **D-49:** FB→OTel transport via `opentelemetry` output plugin (OTLP/HTTP to `http://otel:4318/v1/logs`).
- **D-50:** Buffer `storage.type filesystem` on `telemetron_fluentbit_buffer` volume; `storage.max_chunks_up 128`; `Time_System_Timezone Etc/UTC`; `Multiline_Flush 5`; `Read_from_Head: false`; `[FILTER] modify` fallback for missing `@timestamp`.

**ContainerRestartLoop signal + Docker socket security:**
- **D-51:** OTel Collector `docker_stats` receiver provides the signal. PromQL: `increase(container_restarts_total[10m]) >= 3`. `collection_interval: 30s`.
- **D-52:** Docker socket direct bind-mount `/var/run/docker.sock:/var/run/docker.sock:ro` on the OTel container. Documented Threat Model section in README.
- **D-53:** `docker_stats` scope: ALL containers, no name filter.

**Verify steps + vault surface:**
- **D-54:** Per-role in-network verify one-shot containers (D-32 pattern carry-forward). Plan 03-02's metric-arrival verify uses approach (a) — temporarily flip OTel metrics pipeline to `prometheusremotewrite` for the verify step so the metric reaches Mimir before Prometheus is wired in 03-03 (researcher recommends; see "Plan 03-02 verify topology" below).
- **D-55:** NO vault keys added in Phase 3. `inventory/example-homelab/group_vars/all/vault.yml.example` does NOT grow.

### Claude's Discretion

- **node_exporter image tag** — propose `quay.io/prometheus/node-exporter:v1.11.1` (verified latest stable, 2026-04-07 release).
- **Prometheus retention** — propose `--storage.tsdb.retention.time=15d` (>>Mimir `query_store_after: 12h` per Phase-2 D-36).
- **`metric_relabel_configs` cardinality drops** — propose concrete regex set targeting `pod_uid`, `container_id`, `request_id`, `trace_id`, and UUID-shaped `*_id` labels. See "Prometheus relabel defaults" finding below.
- **3 non-restart-loop alert rule PromQL shapes** — `HostDown`, `FilesystemAlmostFull`, `OTelCollectorDroppingSignals` final form proposed below. Restart-loop rule uses D-51.
- **`prometheus_extra_rules` schema** — list-of-dicts with `name`, `expr`, `for`, `labels`, `annotations`; Jinja iterates `| sort(attribute='name')`.
- **OTel container `mem_limit`** — `512m` default. Derived ratios: GOMEMLIMIT=400MiB, memory_limiter.limit_mib=260MiB (65% of 400), spike_limit_mib=80MiB (20% of 400).
- **D-54 plan 03-02 verify approach** — researcher recommends approach (a) (temporarily flip to `prometheusremotewrite` for verify-time then revert). Rationale below.
- **INSPQ source-role audit per D-25** — full surface enumerated in "INSPQ deviation audit" section below.

### Deferred Ideas (OUT OF SCOPE)

- Per-component bearer/mTLS auth on OTel/Prometheus/FB ingress (M1 single-host design assumes `telemetron`-network membership as the trust boundary per D-55).
- Tecnativa-style docker-socket-proxy sidecar (CLAUDE.md component list is fixed for M1).
- Prometheus federation; Prometheus recording rules; FB→Loki direct path enablement (documented as alternative in README).
- OTel `host_metrics` receiver (alternative to node_exporter); OTel `service-graph` connector → Tempo metrics-generator integration.
- node_exporter `systemd` and `textfile` collectors (defaults-only in M1).
- PromQL retention auto-tuning; comprehensive alert rule library beyond INGEST-03 baseline four.
- Multi-tenant Loki/Mimir (D-26 disables; Phase 3 producers send no `X-Scope-OrgID`).
- Alertmanager + hook router (Phase 4); Grafana datasource provisioning (Phase 5); `nfsd` opt-in role + smoke test (Phase 6).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGEST-01 | Prometheus 3.11.3 scraping OTel `:8888`, node_exporter, inventory targets; default `metric_relabel_configs` drop `pod_uid`/`request_id`/`trace_id` | Finding 4 (Prometheus config), Finding 7 (relabel syntax) |
| INGEST-02 | Prometheus `remote_write` to `http://mimir:9009/api/v1/push` (no X-Scope-OrgID per Phase-2 D-26) | Finding 5 (Mimir remote_write target) |
| INGEST-03 | Four baseline alert rules: `HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals`; `prometheus_extra_rules` extension knob | Finding 8 (alert PromQL final forms; CORRECTED metric prefix `otelcol_receiver_refused_*`) |
| INGEST-04 | OTel Collector Contrib 0.152.0 accepting OTLP on `:4317`/`:4318`, fanning out to Loki/Tempo/Mimir-or-Prometheus | Finding 1 (OTel config), Finding 2 (Loki exporter REMOVED — use `otlphttp`), Finding 3 (Tempo OTLP exporter shape) |
| INGEST-05 | Pipeline shape `[memory_limiter, batch, ...]`; `GOMEMLIMIT` ≈ 80% mem_limit; per-exporter `sending_queue` + `retry_on_failure`; container doesn't OOM under 5-min synthetic load | Finding 1 (memory_limiter + exporterhelper) |
| INGEST-06 | Fluent Bit 4.2.3 tailing host logs and shipping through OTel to Loki; FB→Loki direct documented as alternative; `Time_System_Timezone Etc/UTC` and `Multiline_Flush 5` set | Finding 9 (FB tail + opentelemetry output + parsers) |
| INGEST-07 | FB ships only `{job, host, service, env, level}` labels to Loki; high-cardinality fields → Loki structured metadata; allowlist documented in README | Finding 9 (D-47 mapping in FB filter form) |
| INGEST-08 | node_exporter running, scraped by Prometheus, exposing host metrics on `:9100/metrics` | Finding 6 (containerized node_exporter shape) |

## Standard Stack

### Core (image pins — all verified, no `:latest` anywhere)

| Component | Image | Tag (pinned) | Purpose | Verification |
|-----------|-------|--------------|---------|--------------|
| node_exporter | `quay.io/prometheus/node-exporter` | `v1.11.1` | Host metrics on `:9100/metrics` | Verified 2026-04-07 release via WebFetch; canonical registry is `quay.io/prometheus/*` (matches Alertmanager pin) |
| OpenTelemetry Collector | `otel/opentelemetry-collector-contrib` | `0.152.0` | OTLP ingest + fanout (Contrib distro, NOT Core — Contrib has `docker_stats` receiver, `prometheus`/`prometheusremotewrite` exporters; Core does not) | Verified by `gh api repos/open-telemetry/opentelemetry-collector-contrib/releases/tags/v0.152.0` returns release body |
| Prometheus | `prom/prometheus` | `v3.11.3` | Pull-scrape + alerting + remote_write to Mimir | Pin per CLAUDE.md authoritative table; v3.11.3 is latest stable (v3.5.1 LTS available as operator override) |
| Fluent Bit | `fluent/fluent-bit` | `4.2.3` | Tail Docker container logs + ship via OTel `opentelemetry` output plugin | Pin per CLAUDE.md; 4.x line is M1-stable (5.0 released May 2026, too new) |

### Supporting (already-pinned canon from Phase 1)

| Image | Tag | Purpose |
|-------|-----|---------|
| `minio/mc` | `RELEASE.2025-04-22T16-23-26Z` | mc client for verify one-shots (carryover from Phase 1+2) |
| `curlimages/curl` | `8.10.1` | Curl one-shots for synthetic push + scrape-target verification |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `quay.io/prometheus/node-exporter` | `prom/node-exporter` (Docker Hub) | Both registries publish identical images. Quay matches the Alertmanager pin pattern (`quay.io/prometheus/alertmanager:v0.32.1`) and avoids Docker Hub rate-limit risk for unauth pulls. **Recommend Quay.** |
| OTel `prometheus` exporter (pull) | OTel `prometheusremotewrite` exporter (push direct to Mimir) | D-42 picks scrape-via-Prometheus for diagnostic clarity. D-43 keeps both declared in the template so the knob can flip later. |
| `otlphttp` exporter to Loki `/otlp` | (Removed) `loki` exporter to `/loki/api/v1/push` | D-44 says `loki` exporter, but Finding 2 confirms the `loki` exporter was REMOVED from contrib in v0.131.0 — not available at the pinned v0.152.0. **`otlphttp` is the only viable path.** |
| OTel `docker_stats` receiver | Separate cAdvisor container OR Docker Engine's `:9323` Prometheus endpoint | CLAUDE.md fixed component list precludes cAdvisor. Docker Engine's metrics endpoint exposes daemon metrics (operations counter), not per-container restart counts — wrong shape. `docker_stats` is the only path that emits per-container `container.restarts`. |
| FB `opentelemetry` output → OTel → Loki | FB `loki` output → Loki direct | D-49 picks the OTel path (cleanest mapping, preserves OTLP semantics). FB→Loki direct documented as alternative in README per INGEST-06. |

### Installation

No new container images are pulled by Ansible (all images are pulled per-role via `community.docker.docker_image` as they're already wired into Phase 1+2). The four Phase 3 roles add the following pulls:

```bash
# Pre-pull for offline-friendly cache (operator's discretion)
docker pull quay.io/prometheus/node-exporter:v1.11.1
docker pull otel/opentelemetry-collector-contrib:0.152.0
docker pull prom/prometheus:v3.11.3
docker pull fluent/fluent-bit:4.2.3
```

### Version verification

| Package | Verified Tag | Method | Date |
|---------|--------------|--------|------|
| `quay.io/prometheus/node-exporter` | `v1.11.1` | WebFetch github.com/prometheus/node_exporter/releases | 2026-04-07 |
| `otel/opentelemetry-collector-contrib` | `0.152.0` | `gh api .../releases/tags/v0.152.0` returned 200 | 2026-05-12 (per STACK.md) |
| `prom/prometheus` | `v3.11.3` | CLAUDE.md authoritative pin; latest stable per STACK.md | 2026-04-27 |
| `fluent/fluent-bit` | `4.2.3` | CLAUDE.md authoritative pin; latest 4.x stable | 2026-02 (per STACK.md) |

## Architecture Patterns

### Recommended Role Structure (mirrors Phase 1+2 canonical template)

Each Phase 3 role follows the EXACT shape established by `roles/{minio,loki,tempo,mimir}`:

```
roles/<role>/
├── defaults/main.yml        # Image pin (OPS-01), container identity, port matrix, healthcheck timing,
│                            # restart policy (D-19/W6), memory limit, network/TZ refs to inventory,
│                            # mc + curl image pins for verify one-shots
├── handlers/main.yml        # ONE handler "Docker restart <role>" → `docker restart {{ <role>_container_name }}`
│                            # (D-19 / Pitfall 8: never `state: restarted`)
├── meta/main.yml            # galaxy_info (license: MIT, English-only, platforms Ubuntu/Debian),
│                            # dependencies: [], collections: [community.docker, ansible.builtin]
├── tasks/main.yml           # 1. Ensure config dir exists
│                            # 2. Render config from Jinja template (notifies handler)
│                            # 3. Ensure data volume exists (if stateful)
│                            # 4. Pull image
│                            # 5. Run container with HEALTHCHECK + restart_policy + memory limit
│                            # 6. include_tasks: verify.yml  (D-32 / D-54)
├── tasks/verify.yml         # 1a. docker_container_info poll for healthy (D-10a)
│                            # 1b. Optional: poll State.Running for distroless-no-health images
│                            # 1c. In-network curl probe of HTTP /ready or /metrics
│                            # 2.  Synthetic-payload push or scrape-target assertion
│                            # All one-shots: auto_remove: true, changed_when: false, failed_when: status!=0
├── templates/<file>.j2      # Jinja config; sorted-keys iteration (D-20); inline PITFALL §
│                            # comments are load-bearing documentation
├── vars/                    # (empty / unused in M1)
└── README.md                # OPS-03 schema: Variables / Vault keys / Tags / Modes / Volumes /
                             # Healthcheck / Operator access (SSH local-forward) / Security model /
                             # Idempotency / Port-acceptance gates / Deviations from upstream INSPQ /
                             # Bring your own X / Deprecation notes
```

### Pattern 1: HEALTHCHECK pre-poll + in-network verify one-shots (D-10a + D-32 + D-54)

**What:** Final task of every role's `tasks/main.yml` is `include_tasks: verify.yml`. The verify task first polls `community.docker.docker_container_info` for `State.Health.Status == 'healthy'` (with retries/delay), then runs one-shot containers (`detach: false`, `auto_remove: true`) on the `telemetron` network that push a synthetic payload or assert a scrape target is `up`. Failure of any step fails the playbook.

**When to use:** Every Phase 3 role (mirrors Phase 1+2 minio/loki/tempo/mimir pattern exactly).

**Example:** See `roles/loki/tasks/verify.yml` lines 13–98 (full canonical reference). Phase 3 roles use the same module call sequence with substituted endpoints/payloads.

**Conditional-healthcheck branch (distroless images):** If the upstream image lacks a shell AND lacks a `-health` binary flag (e.g., the Tempo/Mimir image probe outcomes documented in Phase 2 RESEARCH.md), the role surfaces `<role>_healthcheck_enabled: true` knob; `tasks/main.yml` uses `healthcheck: "{{ container_healthcheck if enabled else omit }}"` magic value; verify.yml's Step 1a runs when enabled, Step 1b polls `State.Running` when disabled. node_exporter, OTel Collector, Prometheus, and Fluent Bit are all distroless or near-distroless — confirm at execute time which outcome applies per image probe.

### Pattern 2: One handler, `docker restart`-by-handler (D-19 / Pitfall 8)

**What:** Each role has exactly one handler. Config-template changes `notify: restart <role>`. Handler runs `docker restart {{ <role>_container_name }}` via `ansible.builtin.command` with `changed_when: true`. `community.docker.docker_container` never uses `state: restarted` for restarts.

**Why:** `state: restarted` non-idempotently force-recreates the container; cascades break OPS-04 second-run-changed=0 gate.

### Pattern 3: Sorted-keys Jinja iteration (D-20 / OPS-04)

**What:** Every Jinja template iterates dicts as `{% for k in d.keys() | sort %}` for deterministic output. Lists with operator-supplied entries (e.g., `prometheus_scrape_configs`, `prometheus_extra_rules`) iterate via `| sort(attribute='name')` or `| sort` depending on shape.

**Why:** Python dict ordering is insertion-order since 3.7+, but the merged dict-from-multiple-source-files has non-deterministic order. Sorting at render time fixes the idempotency cascade.

### Pattern 4: No host port publish by default (D-12, D-14, D-30 carry-forward)

**What:** Each Phase 3 role's `<role>_publish_host` defaults to `false`. Container ports are reachable only on the `telemetron` Docker bridge by container DNS name. Operator access is via `ssh -L <port>:localhost:<port> <host>`. **node_exporter is the ONE exception that warrants discussion** — see Finding 6 below; node_exporter publishing :9100 to the host is the upstream default and matches how non-containerized monitoring tools may want to scrape it. **Recommendation:** keep `node_exporter_publish_host: false` for M1 default (Prometheus on the `telemetron` network reaches `http://node-exporter:9100/metrics` by DNS). Operators publish per `<role>_publish_host: true | 127.0.0.1` override.

### Anti-Patterns to Avoid

- **`state: restarted` on `docker_container`** — non-idempotent; force-recreates the container; cascades through handlers and breaks OPS-04. Use `state: started` + `recreate: false` and one-handler-per-role pattern (D-19).
- **Hardcoded localhost endpoints in templates** — break the "no host publish" model. Templates reference Docker DNS names (`loki:3100`, `tempo:14317`, `mimir:9009`, `otel:4317`, `node-exporter:9100`) — never `localhost` or the operator's hostname.
- **`memory_limiter` after `batch` in OTel pipeline order** — Pitfall 5 mode. `batch` accumulates before `memory_limiter` can refuse; OTel OOMs. Phase 3 D-45 locks order `[memory_limiter, batch, ...]`.
- **Setting `Time_System_Timezone America/Montreal`** (or any DST-observing TZ) in Fluent Bit — Pitfall 6 mode. UTC everywhere (D-50).
- **Promoting trace_id / pod_uid / container_id / request_id to Loki labels** — Pitfall 4 (label cardinality explosion). D-47 allowlist mapping channels them to structured metadata.
- **Adding `:latest` anywhere in role defaults** — OPS-01 gate. Every image+tag pinned with inline comment linking the upstream release notes.
- **`state: present` on container module without explicit restart_policy** — leaves restart behavior ambiguous; OPS-06 requires `unless-stopped`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container restart-count detection | Custom Ansible task polling `docker inspect ... RestartCount` and exporting to a textfile collector | OTel Collector `docker_stats` receiver with `container.restarts` metric enabled (D-51 + Finding 1) | docker_stats does the polling, label-mapping, OTLP transport, and Prometheus-format export for all containers in one config block. Replaces what would be a separate cAdvisor-style role (out of scope per CLAUDE.md). |
| OTel pipeline OOM resilience | Custom resource-limit scripts + manual GC tuning | `memory_limiter` processor + `GOMEMLIMIT` env var (D-45 + Finding 1) | The processor talks to Go's runtime memory stats; manual scripts can't see them in time. Pitfall 5 is the entire failure mode. |
| OTel exporter retry on transient backend failure | Custom retry loop in receiver code | Built-in `sending_queue` + `retry_on_failure` in every Contrib exporter (D-45 + Finding 1 `exporterhelper`) | Native exponential backoff, configurable consumer count, persistent queue option. Replaces what would be a custom Python sidecar. |
| FB→OTel log shipping format normalization | Custom Lua scripts in FB to transform records into OTLP | FB `opentelemetry` output plugin (D-49 + Finding 9) | Native OTLP/HTTP encoding. Removes a layer of fragile Lua. |
| Loki label allowlist enforcement at FB-source | Custom Lua filter | Pair of `[FILTER] modify` (set well-known keys) + `[FILTER] grep` (extract level) + `[FILTER] nest` (move non-allowlist into structured metadata) (D-47 + Finding 9) | Native FB filters; sorted-keys; idempotent rendering. |
| Prometheus high-cardinality label cleanup | Custom recording rules to aggregate | `metric_relabel_configs` with `labeldrop` action at scrape time (Finding 7) | Drops at ingest, not aggregate-after-the-fact. Active series never created. |
| Multi-line stack-trace parsing in FB | Custom regex aggregation | FB built-in `multiline.parser` (e.g., `docker, cri, java, python`) (Finding 9 + Pitfall 6) | Standard, well-tested; `Multiline_Flush 5` (D-50) bounds aggregation window. |
| Synthetic OTLP push for verify | Custom Python client | One-shot `curlimages/curl` container posting OTLP/HTTP JSON to `:4318/v1/{traces,logs,metrics}` | Mirrors Phase-2 tempo verify pattern; no new image pin. Trace ID strings can be fixed for idempotent push payloads. |

**Key insight:** Every "Don't Hand-Roll" entry above leverages a built-in capability of an already-pinned image. Phase 3 introduces zero net-new tools, zero new vault keys (D-55), zero new image pulls beyond the four ports — the platform component capabilities cover all four roles' needs.

## Runtime State Inventory

Phase 3 is a **greenfield phase** (4 new roles, no rename/refactor/migration). State inventory is not applicable in the traditional rename/refactor sense — but the phase DOES touch one runtime-state surface worth surfacing explicitly:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — all four roles start with empty state on first deploy (Prometheus TSDB grows during runtime; FB filesystem buffer is empty at first start; node_exporter and OTel are stateless) | None |
| Live service config | None — no existing pre-Phase-3 service config to migrate | None |
| OS-registered state | None — no systemd / Task Scheduler / launchd registrations; all four roles deploy as Docker containers only | None |
| Secrets/env vars | None added (D-55 — vault.yml.example does NOT grow) | None |
| Build artifacts | None — no compiled artifacts or installed packages; all four roles pull pre-built upstream images | None |
| **Pre-existing per-role host directories** (cross-cutting) | `/opt/telemetron/{node_exporter,opentelemetry,prometheus,fluentbit}/` will be created by each role's first task. None exist pre-Phase-3 — confirm via `ls /opt/telemetron/` after Phase 2 (only `loki/`, `tempo/`, `mimir/`, `minio/` exist). | None — fresh creation |
| **Pre-existing named Docker volumes** | `telemetron_prometheus_data` (Prometheus TSDB), `telemetron_fluentbit_buffer` (FB filesystem buffer). Both fresh-created by each role's `docker_volume` task. node_exporter and OTel are stateless — no volume. | None — fresh creation |

**Conclusion:** No runtime-state inventory remediation is required. Phase 3 is purely additive over a settled Phase 2.

## Common Pitfalls

Phase 3 lands Pitfalls 3, 4, 5, 6 from `.planning/research/PITFALLS.md` (per PITFALL-to-Phase mapping). Inline-cited in templates. Summarized below as planner-facing per-role mitigations.

### Pitfall 3: High-cardinality label explosion in Prometheus/Mimir

**Where it lands:** `roles/prometheus/templates/prometheus.yml.j2` `metric_relabel_configs` + `roles/mimir/defaults/main.yml` `max_global_series_*` (Phase 2 D-36 — safety net already in place).

**Mitigation (Prometheus side, Phase 3 plan 03-03):**
```yaml
# Inline-cite PITFALLS §"Pitfall 3" in the template.
metric_relabel_configs:
  - regex: 'pod_uid|container_id|request_id|trace_id'
    action: labeldrop
  - regex: '.*_id'
    action: labeldrop
    # Drops any label name ending in _id when value looks UUID-shaped.
    # Bounded by the explicit names above + this catch-all.
```

**Per scrape job** vs **global** — `metric_relabel_configs` is per-scrape_config block. Default ships under both `otel_self` and `otel_metrics` jobs in the role template; operator extension via `prometheus_extra_relabel_configs: []` (list of dict, merged in).

**Warning signs:** `prometheus_tsdb_head_series` growing linearly past 100k on a homelab; Mimir's `cortex_ingester_memory_series_in_progress` climbing; queries slow.

### Pitfall 4: Loki label discipline — unbounded labels and high churn

**Where it lands:** `roles/fluentbit/templates/fluent-bit.conf.j2` allowlist filter (D-47). Loki-side limits already shipped in Phase 2 D-37 (`max_streams_per_user: 5000`).

**Mitigation (FB side, Phase 3 plan 03-04):** D-47 allowlist + structured-metadata channeling. See Finding 9 below for exact filter stanzas.

### Pitfall 5: OTel Collector pipeline misconfiguration — wrong processor order, no memory limiter

**Where it lands:** `roles/opentelemetry/templates/config.yaml.j2` (D-45 pipeline order + GOMEMLIMIT + per-exporter sending_queue/retry_on_failure).

**Mitigation (Phase 3 plan 03-02):** D-45 defaults; inline PITFALLS §"Pitfall 5" citation in the template. Full config shape: Finding 1 below.

**Warning signs:** Container restarts with exit 137 (OOMKilled); `otelcol_receiver_refused_*` > 0 (NOT `processor_refused_*` — see Summary correction #2); `otelcol_exporter_queue_size` near `otelcol_exporter_queue_capacity`.

### Pitfall 6: Fluent Bit timestamp drift — DST, missing dates, multiline parsers

**Where it lands:** `roles/fluentbit/templates/fluent-bit.conf.j2` (D-50 `Time_System_Timezone Etc/UTC`, `Multiline_Flush 5`, `Read_from_Head: false`, fallback `@timestamp` modify filter).

**Mitigation (Phase 3 plan 03-04):** D-50 defaults; inline PITFALLS §"Pitfall 6" citation.

### Pitfall 8: Ansible role idempotency cascades

**Where it lands:** All four Phase 3 roles. OPS-04 gate enforced via:
- `state: started, recreate: false`
- Handler-driven restarts (one-handler-per-role pattern)
- `changed_when: false` on all verify tasks
- Sorted-keys Jinja iteration (D-20)

**Verification:** Second-in-a-row playbook run reports `changed=0` per role's tag.

### Pitfall 9: Fork-from-INSPQ leftovers

**Where it lands:** Per-role grep gates (D-21 carry-forward):
```bash
grep -riE 'inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/<name>/   # zero matches
grep -rPn '[^\x00-\x7F]' roles/<name>/                                                              # zero matches
```

INSPQ source has French task `name:` strings, `America/Toronto` TZ, and references to internal Kubernetes namespaces — all stripped. See "INSPQ deviation audit" section below.

### Phase-3-specific gotcha: Docker socket permissions on OTel container

The OTel `docker_stats` receiver requires read access to `/var/run/docker.sock`. Since OTel Collector Contrib v0.40+ images run as a non-root user. Two approaches at the role layer:

**Approach A (recommended for M1):** Pass `group_add` with the host's `docker` group GID:
```yaml
# roles/opentelemetry/tasks/main.yml
- name: Detect docker group GID on the target host
  ansible.builtin.getent:
    database: group
    key: docker
  register: docker_group_info

- name: Run OTel Collector container
  community.docker.docker_container:
    ...
    groups:
      - "{{ docker_group_info.ansible_facts.getent_group.docker[1] }}"
    ...
```

**Approach B (simpler but less secure):** Run OTel as root (`user: "0"`). **Rejected for M1** — adds unnecessary attack surface.

**Approach C (production-grade, deferred):** Tecnativa docker-socket-proxy sidecar. Out of M1 scope per D-52 and CLAUDE.md fixed component list.

**Researcher recommendation: Approach A**, with `roles/opentelemetry/README.md` Security Model section documenting the `:ro` mount + the API-layer caveat (a compromised OTel container could still issue Docker API calls).

## Code Examples

Verified patterns from official sources. All snippets are starting points; planner specifies the full template shape in plans.

### Finding 1: OTel Collector 0.152.0 config shape

**Source:** [opentelemetry-collector memorylimiterprocessor README](https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md) (verified via `gh api`), [opentelemetry-collector exporterhelper README](https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md), [otelcol docker_stats receiver README](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/dockerstatsreceiver) (verified via `gh api`).

**Canonical Phase-3 config template shape** (planner extends with sorted-keys Jinja for operator-extensible sections):

```yaml
# /opt/telemetron/opentelemetry/config.yaml
# {{ ansible_managed }}
# OTel Collector Contrib 0.152.0 — pipeline shape locked per CONTEXT.md D-45.
# Pitfall 5 inline-cited; comments are load-bearing documentation.

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  docker_stats:
    endpoint: unix:///var/run/docker.sock
    collection_interval: 30s   # D-51 — matches Prometheus default scrape; minimizes daemon load
    timeout: 5s
    api_version: "1.25"
    # D-53: ALL containers; no excluded_images filter.
    # Default metrics: cpu/memory/network/blockio subset.
    # OPT-IN metrics required for restart-loop alert (D-51):
    metrics:
      container.restarts:
        enabled: true     # OFF by default; D-51 needs this for ContainerRestartLoop
      container.uptime:
        enabled: true     # complementary "container alive for N seconds" signal

processors:
  # D-45: memory_limiter MUST be FIRST. Pitfall 5 inline-cite.
  memory_limiter:
    check_interval: 1s     # upstream recommendation
    limit_mib: 260         # 65% of GOMEMLIMIT (400MiB) per D-45 ratio
    spike_limit_mib: 80    # 20% of GOMEMLIMIT (400MiB) per D-45 ratio

  batch:
    timeout: 10s
    send_batch_size: 1024
    send_batch_max_size: 2048

exporters:
  # OTel → Loki via OTLP/HTTP (Loki 3.7 native OTLP — see Finding 2).
  # NOTE: D-44 specifies `loki` exporter but that exporter is REMOVED from v0.152.0.
  # The current canonical path is otlphttp to Loki's /otlp endpoint.
  otlphttp/loki:
    endpoint: http://loki:3100/otlp
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 1000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

  # OTel → Tempo via OTLP gRPC on Phase-2 D-29 internal-only port.
  otlp/tempo:
    endpoint: tempo:14317
    tls:
      insecure: true
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 1000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

  # D-42 + D-43: metrics path via Prometheus scrape on :8889.
  # `prometheus` exporter is pull-style; no sending_queue/retry_on_failure (those are
  # push-exporter concepts; pull is Prometheus's responsibility).
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: ""            # no prefix
    send_timestamps: true
    metric_expiration: 5m
    enable_open_metrics: true

  # D-43 forward-compat: declared but not in pipeline by default.
  # Jinja conditional includes this in the metrics pipeline ONLY when
  # telemetron_otel_metrics_path == 'remote_write'.
  prometheusremotewrite:
    endpoint: http://mimir:9009/api/v1/push
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 1000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

service:
  telemetry:
    metrics:
      # Self-metrics on :8888 — Prometheus job `otel_self` scrapes this.
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888

  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/loki]   # was D-44's loki exporter; see Finding 2

    metrics:
      receivers: [otlp, docker_stats]   # docker_stats feeds restart-loop signal
      processors: [memory_limiter, batch]
      # D-43 Jinja conditional:
      #   {% if telemetron_otel_metrics_path == 'remote_write' %}
      #   exporters: [prometheusremotewrite]
      #   {% else %}
      #   exporters: [prometheus]
      #   {% endif %}
      exporters: [prometheus]
```

**Environment variables (set on the OTel container):**
```yaml
env:
  GOMEMLIMIT: "400MiB"   # 80% of mem_limit 512m per D-45
  TZ: "{{ telemetron_tz | default('Etc/UTC') }}"
```

**Memory ratios cross-check (D-45):**
- `mem_limit`: 512MiB (operator-overridable via `opentelemetry_memory_limit`)
- `GOMEMLIMIT`: 400MiB (80% of 512)
- `memory_limiter.limit_mib`: 260MiB (65% of 400) — hard limit
- `memory_limiter.spike_limit_mib`: 80MiB (20% of 400) — soft limit gap
- Effective soft limit: 260 - 80 = **180MiB**
- Soft <= hard <= GOMEMLIMIT <= container mem_limit ✓

### Finding 2: OTel → Loki path — `loki` exporter REMOVED; use `otlphttp`

**Source:** [otelcol-contrib release v0.131.0 release notes](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/38374) confirms `loki` exporter removal; [`gh api repos/.../contents/exporter?ref=v0.152.0`](#) confirms absence at v0.152.0; [Grafana Loki OTLP docs](https://grafana.com/docs/loki/latest/send-data/otel/) confirms `otlphttp` is the official replacement.

**Status:** `loki` exporter was deprecated 2024-07-09; removed from contrib in v0.131.0. v0.152.0 (Phase 3 pin) does NOT ship it. Verified by listing the `exporter/` directory contents at the v0.152.0 tag — no `lokiexporter` entry.

**D-44 conflict:** CONTEXT.md says "OTel→Loki uses `loki` exporter at `http://loki:3100`". This is not feasible at the pinned tag.

**Researcher recommendation:** Planner amends D-44 to read "OTel→Loki uses `otlphttp` exporter at `http://loki:3100/otlp`" and documents this as a D-25 deviation in `roles/opentelemetry/README.md`. The Loki side is already compatible: Loki 3.7.2 with `auth_enabled: false` (Phase-2 D-26) accepts OTLP/HTTP on its `/otlp` endpoint with no `X-Scope-OrgID` header required.

**Config shape (replaces D-44 Loki leg):**
```yaml
exporters:
  otlphttp/loki:
    endpoint: http://loki:3100/otlp
    # No headers needed when Loki auth_enabled: false.
    # When multitenancy lands in v2: headers: {X-Scope-OrgID: <tenant>}.
    sending_queue: {enabled: true, num_consumers: 4, queue_size: 1000}
    retry_on_failure: {enabled: true, initial_interval: 5s, max_interval: 30s, max_elapsed_time: 300s}
```

**Tradeoff:** OTLP/HTTP wire format vs. the older Loki push format. `otlphttp` is semantically richer (preserves resource attributes, scope info, trace_id correlation natively); Loki 3.7 handles this cleanly. No behavioral regression.

### Finding 3: OTel → Tempo OTLP gRPC exporter shape (D-44 Tempo leg — confirmed)

**Source:** Verified against Phase-2 `roles/tempo/templates/tempo.yaml.j2` lines 17–23 — Tempo's OTLP receivers bind to `0.0.0.0:14317` (gRPC) and `0.0.0.0:14318` (HTTP) per D-29.

**Status:** D-44's Tempo leg is unchanged. OTel `otlp` exporter (NOT `otlphttp`) sends to `tempo:14317` over the `telemetron` bridge.

**Config shape:**
```yaml
exporters:
  otlp/tempo:
    endpoint: tempo:14317    # gRPC; Tempo accepts on :14317 internal-only (Phase-2 D-29)
    tls:
      insecure: true         # plain HTTP/2 on the telemetron bridge
    sending_queue: {enabled: true, num_consumers: 4, queue_size: 1000}
    retry_on_failure: {enabled: true, initial_interval: 5s, max_interval: 30s, max_elapsed_time: 300s}
```

**Note:** `otlp` exporter (gRPC) ≠ `otlphttp` exporter (HTTP). Both are first-class in Contrib. Tempo gRPC has lower overhead and preserves full OTLP semantics; sticking with gRPC for the Tempo leg matches Phase-2 D-29's port allocation.

### Finding 4: Prometheus 3.x scrape_config + remote_write to Mimir

**Source:** [Prometheus configuration reference](https://prometheus.io/docs/prometheus/latest/configuration/configuration/), [Mimir remote_write docs](https://grafana.com/docs/mimir/latest/configure/configure-prometheus-remote-write/). Mimir 3.0.6 with `multitenancy_enabled: false` (Phase-2 D-26) requires no `X-Scope-OrgID` header.

**Canonical Phase-3 prometheus.yml shape** (planner extends sorted-keys for operator scrape_configs / extra_rules):

```yaml
# /opt/telemetron/prometheus/prometheus.yml
# {{ ansible_managed }}
# Prometheus 3.11.3 — scrape config + remote_write to Mimir + relabel cardinality defaults.
# Pitfall 3 inline-cited; D-26 no X-Scope-OrgID needed.

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: telemetron-homelab
    host: "{{ inventory_hostname }}"

rule_files:
  - /etc/prometheus/rules/baseline.yml      # D-43 four-rule baseline
  - /etc/prometheus/rules/extra.yml         # operator extras from prometheus_extra_rules

remote_write:
  - url: http://mimir:9009/api/v1/push
    # D-26: no headers (Mimir multitenancy_enabled: false; tenant 'anonymous').
    # When multitenancy lands in v2, add: headers: {X-Scope-OrgID: <tenant>}.
    queue_config:
      capacity: 10000
      max_samples_per_send: 2000
      batch_send_deadline: 5s
      min_shards: 1
      max_shards: 5

# Phase-2 D-36 Mimir limits are the safety net (max_global_series_per_user: 500000).
# Pitfall 3 source-side mitigation here:
scrape_configs:
  - job_name: otel_self
    # D-42: OTel Collector's INTERNAL/SELF metrics on :8888 (refused records, queue depth).
    static_configs:
      - targets: ['otel:8888']
        labels:
          service: opentelemetry-collector
    metric_relabel_configs:
      - regex: 'pod_uid|container_id|request_id|trace_id'
        action: labeldrop
      - regex: '.*_id'
        action: labeldrop

  - job_name: otel_metrics
    # D-42: OTLP-pushed app metrics exported in Prometheus format on :8889.
    static_configs:
      - targets: ['otel:8889']
        labels:
          service: opentelemetry-collector-app-metrics
    metric_relabel_configs:
      - regex: 'pod_uid|container_id|request_id|trace_id'
        action: labeldrop
      - regex: '.*_id'
        action: labeldrop

  - job_name: node_exporter
    static_configs:
      - targets: ['node-exporter:9100']
        labels:
          service: node-exporter
    # node_exporter labels are well-behaved (no UUID-shaped *_id by default),
    # but ship the relabel anyway as a consistent default + operator extension point.
    metric_relabel_configs:
      - regex: 'pod_uid|container_id|request_id|trace_id'
        action: labeldrop

  # Operator-extensible scrape jobs via prometheus_extra_scrape_configs: []
  {% for job in prometheus_extra_scrape_configs | default([]) | sort(attribute='job_name') %}
  - job_name: {{ job.job_name }}
    static_configs: {{ job.static_configs }}
  {% endfor %}
```

**Container command-line args (in `roles/prometheus/tasks/main.yml` `docker_container.command`):**
```yaml
command:
  - "--config.file=/etc/prometheus/prometheus.yml"
  - "--storage.tsdb.path=/prometheus"
  - "--storage.tsdb.retention.time={{ prometheus_retention_time | default('15d') }}"
  - "--web.enable-lifecycle"      # for SIGHUP-style reload (not used by handler-restart pattern but useful for operators)
  - "--web.enable-admin-api"      # for /api/v1/admin/* endpoints (operator-facing)
  - "--web.listen-address=0.0.0.0:9090"
```

**Retention rationale:** 15d local retention > Mimir's `query_store_after: 12h` (Phase-2 D-36) ensures Grafana queries against Prometheus for recent data while Mimir handles long-term. 15d is upstream-default-ish for Prometheus 3.x homelab.

### Finding 5: Mimir remote_write target shape (confirmed, no header changes)

**Source:** Phase-2 `roles/mimir/templates/mimir.yaml.j2` line 10 (`multitenancy_enabled: false`); Mimir 3.0 architecture overview.

**Status:** Phase-2 D-26 / D-29 / D-31 already settled the target. Prometheus → Mimir `http://mimir:9009/api/v1/push`. No `X-Scope-OrgID` header. No extra config beyond URL + queue tuning.

**Path:** `/api/v1/push` (Mimir compatibility endpoint that accepts Prometheus remote_write v2 protobuf natively).

### Finding 6: Containerized node_exporter v1.11.1 — flags + bind mounts

**Source:** [prometheus/node_exporter README](https://github.com/prometheus/node_exporter) + [release v1.11.1 notes](https://github.com/prometheus/node_exporter/releases/tag/v1.11.1) (verified 2026-04-07).

**Canonical containerized invocation (mirrors upstream README "Docker" section):**

```yaml
# roles/node_exporter/tasks/main.yml — container run task
- name: Run node_exporter container
  community.docker.docker_container:
    name: "{{ node_exporter_container_name }}"          # default 'node-exporter'
    image: "{{ node_exporter_image }}:{{ node_exporter_image_tag }}"   # quay.io/prometheus/node-exporter:v1.11.1
    state: started
    recreate: false
    restart_policy: "{{ node_exporter_restart_policy }}"   # unless-stopped
    pid_mode: host        # node_exporter needs host PID namespace for some collectors
    networks:
      - name: "{{ node_exporter_network }}"
        aliases:
          - "{{ node_exporter_container_name }}"
    # D-30: zero host publish by default; Prometheus reaches via Docker DNS.
    published_ports: >-
      {{
        (
          [ node_exporter_port | string + ':' + node_exporter_port | string ]
          if node_exporter_publish_host is sameas true else
          [ '127.0.0.1:' + node_exporter_port | string + ':' + node_exporter_port | string ]
          if node_exporter_publish_host == '127.0.0.1' else
          []
        )
      }}
    command:
      - "--path.procfs=/host/proc"
      - "--path.sysfs=/host/sys"
      - "--path.rootfs=/host/root"
      - "--collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+|var/lib/kubelet/.+)($|/)"
      - "--collector.filesystem.fs-types-exclude=^(autofs|binfmt_misc|bpf|cgroup2?|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|iso9660|mqueue|nsfs|overlay|proc|procfs|pstore|rpc_pipefs|securityfs|selinuxfs|squashfs|sysfs|tracefs)$"
      - "--web.listen-address=0.0.0.0:{{ node_exporter_port }}"
    mounts:
      - source: /proc
        target: /host/proc
        type: bind
        read_only: true
      - source: /sys
        target: /host/sys
        type: bind
        read_only: true
      - source: /
        target: /host/root
        type: bind
        read_only: true
        propagation: rslave
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:{{ node_exporter_port }}/metrics"]
      # NOTE: node_exporter image is from-scratch; wget may not be present.
      # Recommend executor probe at execute time; fall back to:
      #   ["CMD-SHELL", "/bin/node_exporter --version || exit 1"] (binary-alive proxy)
      # or omit healthcheck entirely with omit-magic and rely on State.Running poll.
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    env:
      TZ: "{{ node_exporter_tz }}"
```

**Verify task shape:**
- Step 1: `docker_container_info` poll for State.Health.Status healthy OR State.Running (per conditional-healthcheck pattern).
- Step 2: one-shot `curlimages/curl` on the `telemetron` network curls `http://node-exporter:9100/metrics`; assert HTTP 200 and body contains `node_cpu_seconds_total`.

**Collectors default-enabled set (stock M1, per Claude's Discretion):** cpu, diskstats, filesystem, loadavg, meminfo, netdev, time, uname, vmstat, stat, ... (all stock defaults; no explicit `--collector.<name>` flags added beyond the path/exclude args above).

**Deferred opt-in collectors:**
- `systemd` collector — requires D-Bus bind-mount; not enabled by default.
- `textfile` collector — operators sometimes write custom metrics; not enabled by default.

### Finding 7: Prometheus `metric_relabel_configs` syntax + cardinality regex defaults

**Source:** [Prometheus configuration reference §relabel_config](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config), WebFetch query confirms `labeldrop` action drops matching labels while preserving the metric stream.

**Action semantics:**
- `labeldrop`: drops labels matching `regex`; metric stream stays. **This is what we want for cardinality drops.**
- `drop`: drops entire samples where `source_labels` match `regex`. Use for blanking known-bad metric names entirely.
- `labelmap`: copies/renames labels; not relevant here.

**Concrete default regex set (proposed for `roles/prometheus/templates/prometheus.yml.j2`):**

```yaml
metric_relabel_configs:
  # Pitfall 3 explicit-name drops:
  - regex: 'pod_uid|container_id|request_id|trace_id'
    action: labeldrop
  # Pitfall 3 *_id catch-all (UUID-shaped *_id values):
  - regex: '.*_id'
    action: labeldrop
```

**Why two stanzas instead of one combined regex:** The explicit-name stanza makes the operator-visible intent obvious (these are the load-bearing four labels Pitfall 3 calls out). The `.*_id` stanza is the catch-all safety net. Two stanzas also make `prometheus_extra_relabel_configs: []` extension semantics cleaner (operator-appended entries land AFTER the defaults).

**Per-job vs global:** `metric_relabel_configs` is per-scrape_config. Both `otel_self`, `otel_metrics`, `node_exporter` ship this set. Operator extension via `prometheus_extra_scrape_configs` items can include their own `metric_relabel_configs` lists.

**Operator override knob:** `prometheus_extra_relabel_configs: []` in `inventory/example-homelab/group_vars/all/prometheus.yml` — list of dict merged in.

### Finding 8: Four baseline alert rule PromQL final forms

**Source:** [Prometheus alerting_rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/); OTel self-metrics naming confirmed via [opentelemetry.io internal-telemetry docs](https://opentelemetry.io/docs/collector/internal-telemetry/) — **prefix is `otelcol_receiver_*`, NOT `otelcol_processor_*`**.

**Final form for `roles/prometheus/templates/rules-baseline.yml.j2`:**

```yaml
# /opt/telemetron/prometheus/rules/baseline.yml
# {{ ansible_managed }}
# INGEST-03 baseline alert rules. Operator extends via prometheus_extra_rules: []
# (list of dict with name/expr/for/labels/annotations).

groups:
  - name: telemetron.baseline
    interval: 30s
    rules:
      - alert: HostDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
          team: telemetron
        annotations:
          summary: "Scrape target {{ '{{' }} $labels.instance {{ '}}' }} is unreachable"
          description: "{{ '{{' }} $labels.job {{ '}}' }} on {{ '{{' }} $labels.instance {{ '}}' }} has been unreachable for >2 minutes."

      - alert: FilesystemAlmostFull
        # Pitfall 3 — exclude high-cardinality fstypes (tmpfs/overlay) that flap.
        expr: (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"}) < 0.15
        for: 5m
        labels:
          severity: warning
          team: telemetron
        annotations:
          summary: "Filesystem {{ '{{' }} $labels.mountpoint {{ '}}' }} on {{ '{{' }} $labels.instance {{ '}}' }} is <15% free"
          description: "Filesystem {{ '{{' }} $labels.mountpoint {{ '}}' }} ({{ '{{' }} $labels.fstype {{ '}}' }}) on {{ '{{' }} $labels.instance {{ '}}' }} has been below 15% available for >5 minutes."

      - alert: ContainerRestartLoop
        # D-51 — fed by OTel docker_stats receiver's container.restarts metric.
        # The Prometheus-format name (after OTel→Prometheus translation):
        #   container_restarts_total (UnderscoreEscapingWithSuffixes default).
        expr: increase(container_restarts_total[10m]) >= 3
        for: 0m   # fire immediately when condition holds
        labels:
          severity: warning
          team: telemetron
        annotations:
          summary: "Container {{ '{{' }} $labels.container_name {{ '}}' }} restarted ≥3 times in 10m"
          description: "Container {{ '{{' }} $labels.container_name {{ '}}' }} (image {{ '{{' }} $labels.container_image_name {{ '}}' }}) has restarted ≥3 times in the last 10 minutes. Likely crash-looping."

      - alert: OTelCollectorDroppingSignals
        # CORRECTED prefix: otelcol_receiver_refused_* (NOT otelcol_processor_refused_*).
        # When a downstream pipeline rejects data (memory_limiter, exporter retry exhaust,
        # batch overflow), the receiver counts as "refused".
        expr: |
          (
            rate(otelcol_receiver_refused_spans[5m])
            + rate(otelcol_receiver_refused_log_records[5m])
            + rate(otelcol_receiver_refused_metric_points[5m])
          ) > 0
        for: 5m
        labels:
          severity: warning
          team: telemetron
        annotations:
          summary: "OTel Collector is refusing signals"
          description: "OTel Collector on {{ '{{' }} $labels.instance {{ '}}' }} has been refusing one or more signal types for >5 minutes. Check memory_limiter saturation, exporter queue depth, and backend availability."
```

**Operator extension knob shape (proposed `prometheus_extra_rules`):**

```yaml
# inventory/example-homelab/group_vars/all/prometheus.yml
prometheus_extra_rules:
  - name: MyAppDown
    expr: up{job="my-app"} == 0
    for: 1m
    labels:
      severity: critical
      team: ops
    annotations:
      summary: "my-app is down"
      description: "Description here."
```

**Template rendering (sorted-keys per D-20):**

```jinja2
# /opt/telemetron/prometheus/rules/extra.yml
groups:
  - name: telemetron.operator-extras
    rules:
{% for rule in prometheus_extra_rules | default([]) | sort(attribute='name') %}
      - alert: {{ rule.name }}
        expr: {{ rule.expr | to_json }}
        for: {{ rule.for | default('0m') }}
        labels:
{% for k in (rule.labels | default({})).keys() | sort %}
          {{ k }}: {{ rule.labels[k] }}
{% endfor %}
        annotations:
{% for k in (rule.annotations | default({})).keys() | sort %}
          {{ k }}: {{ rule.annotations[k] }}
{% endfor %}
{% endfor %}
```

**Cross-check D-51 metric name:**
- OTel docker_stats `container.restarts` (Sum, monotonic) → Prometheus exporter translates with default `UnderscoreEscapingWithSuffixes` → emitted as `container_restarts_total` (the `_total` suffix is added by Prometheus translator for Sum metric type per OpenMetrics convention). Label set includes `container_name`, `container_image_name`, `container_id` — but `container_id` is dropped by our `metric_relabel_configs` (Finding 7), which is correct (cardinality bound). `container_name` stays.

**Critical: `container.restarts` is OPT-IN.** The metric is declared as Default-disabled in the receiver's `documentation.md` (Stability: Development). The OTel config MUST explicitly enable it (`metrics: {container.restarts: {enabled: true}}`) — see Finding 1.

### Finding 9: Fluent Bit 4.2.3 config shape — tail + parser + filter + opentelemetry output

**Source:** [Fluent Bit tail input docs](https://docs.fluentbit.io/manual/pipeline/inputs/tail), [opentelemetry output plugin](https://docs.fluentbit.io/manual/data-pipeline/outputs/opentelemetry) (verified via WebFetch), [Fluent Bit storage docs](https://docs.fluentbit.io/manual/administration/buffering-and-storage).

**Canonical fluent-bit.conf shape** (D-46, D-47, D-48, D-49, D-50 all baked in):

```ini
# /opt/telemetron/fluentbit/fluent-bit.conf
# {{ ansible_managed }}
# Fluent Bit 4.2.3 — Telemetron-tuned. Pitfall 6 inline-cited; D-50 buffer/timezone discipline.

[SERVICE]
    Parsers_File              parsers.conf
    Log_Level                 info
    Flush                     5
    HTTP_Server               On
    HTTP_Listen               0.0.0.0
    HTTP_Port                 2020
    Health_Check              On
    HC_Error_Count            5
    HTTP_Metrics              On
    # D-50: filesystem buffer survives container restart without log loss.
    storage.path              /var/log/flb-storage/
    storage.sync              normal
    storage.checksum          off
    storage.backlog.mem_limit 50M
    storage.max_chunks_up     128
    # Pitfall 6 — UTC everywhere; never DST-observing TZ.

# D-46: Docker container logs default tail.
[INPUT]
    Name              tail
    Alias             docker_containers
    Path              /var/lib/docker/containers/*/*-json.log
    Parser            docker
    Tag               docker.<container_id>
    Tag_Regex         (?<container_id>[^/]+)\.log$
    Refresh_Interval  5
    Read_from_Head    false                  # D-50 — start at tail
    Mem_Buf_Limit     10MB
    Skip_Long_Lines   On
    storage.type      filesystem             # D-50 — buffered to disk
    Buffer_Max_Size   1MB
    Buffer_Chunk_Size 32KB

# D-48: extension knobs all default-off.
{% if fluentbit_tail_system_logs | default(false) %}
[INPUT]
    Name              tail
    Alias             system_logs
    Path              /var/log/syslog,/var/log/auth.log,/var/log/kern.log,/var/log/messages
    Tag               system.*
    Refresh_Interval  10
    Read_from_Head    false
    Skip_Long_Lines   On
    storage.type      filesystem
{% endif %}

{% if fluentbit_tail_journald | default(false) %}
[INPUT]
    Name              systemd
    Alias             journald
    Path              /run/log/journal     # requires bind-mount of /run/systemd/journal/socket too
    Tag               journald.*
    Read_From_Tail    on
    Strip_Underscores on
{% endif %}

{% for entry in fluentbit_extra_tail_paths | default([]) | sort %}
[INPUT]
    Name              tail
    Alias             extra_{{ loop.index }}
    Path              {{ entry }}
    Tag               extra.{{ loop.index }}.*
    Refresh_Interval  10
    Read_from_Head    false
    storage.type      filesystem
{% endfor %}

# D-47: label allowlist mapping.
# Step 1: parse Docker JSON log entries (container_name, container_id, image_name come from the docker parser).
[FILTER]
    Name              modify
    Alias             allowlist_static
    Match             docker.*
    # Static labels (D-47):
    Add               host {{ ansible_hostname }}
    Add               env {{ telemetron_env | default('homelab') }}
    # job + service fallback assignments — operator-set container Docker labels
    # com.telemetron.{service,env,job} take precedence at the FB filter layer via lua or
    # the `parser` filter for extracting via attribute. For M1 default, the simplest:
    # use container_name as both job and service if no Docker labels are extracted.
    # See "Open Questions" — Docker label extraction in FB 4.2 tail needs verification.

# D-47: level extraction via grep-style match (parses log line content).
[FILTER]
    Name              parser
    Alias             extract_level
    Match             docker.*
    Key_Name          log
    Parser            level_extractor
    Reserve_Data      On
    Preserve_Key      On
# Default level when no match (D-47):
[FILTER]
    Name              modify
    Alias             default_level
    Match             docker.*
    Add               level info     # only added if `level` key doesn't already exist (modify Add is non-destructive)

# Pitfall 6 timestamp fallback (D-50 three-failure-mode mitigation):
[FILTER]
    Name              modify
    Alias             timestamp_fallback
    Match             *
    # `modify` Add operates only when key is missing.
    Add               @timestamp ${ingest_time}

# D-49: ship to OTel Collector via OTLP/HTTP.
[OUTPUT]
    Name                 opentelemetry
    Alias                otel_logs
    Match                *
    Host                 otel
    Port                 4318
    Logs_uri             /v1/logs
    log_response_payload false
    Tls                  Off
    # Note: fb opentelemetry output sends logs in OTLP format; resource and scope
    # attributes are derived from record keys. D-47 allowlist controls what becomes
    # a Loki label after OTel→Loki via otlphttp (Finding 2); FB's job here is to
    # produce a well-shaped OTLP record with stable resource attributes.
```

**parsers.conf:**

```ini
# /opt/telemetron/fluentbit/parsers.conf
# {{ ansible_managed }}

[PARSER]
    Name        docker
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%LZ
    Time_Keep   On

[PARSER]
    Name        level_extractor
    Format      regex
    Regex       (?i)\b(?<level>INFO|WARN|ERROR|FATAL|DEBUG|TRACE)\b
```

**Multiline parser (Pitfall 6 mitigation):**

```ini
# Stack traces in Java / Python logs are multi-line; default Docker JSON parser
# treats each line as one event. M1 default: don't aggregate (multiline.parser is
# opt-in per-input). When operator enables, ship a `Multiline_Flush 5` to bound.
# Reference: https://docs.fluentbit.io/manual/data-pipeline/parsers/multiline-parsing
```

**Container run task (mirrors Phase-2 pattern):**

```yaml
- name: Run Fluent Bit container
  community.docker.docker_container:
    name: "{{ fluentbit_container_name }}"
    image: "{{ fluentbit_image }}:{{ fluentbit_image_tag }}"
    state: started
    recreate: false
    restart_policy: "{{ fluentbit_restart_policy }}"
    memory: "{{ fluentbit_memory_limit | default('256m') }}"
    networks:
      - name: "{{ fluentbit_network }}"
        aliases:
          - "{{ fluentbit_container_name }}"
    published_ports: >-
      {{
        ([fluentbit_http_port | string + ':' + fluentbit_http_port | string]
          if fluentbit_publish_host is sameas true else
          ['127.0.0.1:' + fluentbit_http_port | string + ':' + fluentbit_http_port | string]
          if fluentbit_publish_host == '127.0.0.1' else
          [])
      }}
    mounts:
      - source: "{{ fluentbit_buffer_volume }}"
        target: /var/log/flb-storage
        type: volume
      - source: /var/lib/docker/containers
        target: /var/lib/docker/containers
        type: bind
        read_only: true
    volumes:
      - "{{ fluentbit_config_dir }}/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro"
      - "{{ fluentbit_config_dir }}/parsers.conf:/fluent-bit/etc/parsers.conf:ro"
    healthcheck:
      test: ["CMD-SHELL", "wget --quiet --tries=1 --spider http://localhost:2020/api/v1/health || exit 1"]
      # Fluent Bit image has busybox shell; wget may need verification at execute time.
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s
    env:
      TZ: "{{ fluentbit_tz }}"
```

**Verify task shape:**
- Step 1: poll HEALTHCHECK or `State.Running`.
- Step 2: one-shot `curlimages/curl` curls `http://fluentbit:2020/api/v1/health` and asserts HTTP 200.
- Step 3: write a synthetic uniquely-tagged log line to a bind-mounted test path (e.g., `/tmp/flb-test/synthetic.log` mounted via `fluentbit_extra_tail_paths: ['/tmp/flb-test/*.log']` for the verify run), wait `Multiline_Flush + scrape_interval ≈ 10s`, then one-shot curl `http://loki:3100/loki/api/v1/query_range?query={service="flb-test"}` and assert the synthetic line is returned.
- **Simplification for M1:** Step 3 may be challenging because Loki's structured-metadata-via-OTLP path is new in 3.7. Researcher recommendation: Step 3 omitted in plan 03-04; FB-to-Loki end-to-end smoke moves to Phase 6 OPS-07. Step 2's `/api/v1/health` 200 is the M1 acceptance gate for the FB role.

## INSPQ Source-Role Deviation Audit (D-25)

Per D-25, each Phase-3 role port is an opinionated improvement pass — not a mirror translate. The audit below surfaces per-role concrete deviation candidates the plan-level "Deviations from upstream INSPQ" README section will document.

### roles/node_exporter (plan 03-01)

INSPQ source: `~/git/inspq/ansible/node_exporter/` (verified directory listing + `defaults/main.yml` + `tasks/docker.yml` read).

**Dropped (INSPQ-isms beyond grep gate):**
- `node_exporter_deployment_method: native` — DROP. Telemetron is Docker-only per CLAUDE.md.
- All `native.yml` / `native.yml.1` tasks — DROP.
- `node_exporter_image_version: latest` — REPLACE with `v1.11.1` pin (OPS-01).
- `node_exporter_container_env: TZ: "America/Toronto"` — REPLACE with `Etc/UTC` per OPS-06 + Pitfall 6.
- `node_explorer_docker_restart_policy: always` (note INSPQ typo — `explorer` not `exporter`) — REPLACE with `unless-stopped` per OPS-06.
- `node_exporter_textfile_dir: /opt/node-exporter/textfile-collector` + `--collector.textfile.directory=/textfile-collector` — DROP for M1 default (textfile collector opt-in, deferred per CONTEXT.md).
- `node_exporter_lvm` LVM tasks (`community.general.lvol`, `ansible.builtin.filesystem`, `ansible.builtin.mount`) — DROP entirely. INSPQ's LVM-on-textfile assumption is Quebec-gov-host-specific.
- `community.general.ufw` UFW firewall rules — DROP. Telemetron uses no-host-publish default (D-30) so no firewall hole needed.
- French task names ("Vérifier...", "Supprimer...", "Permettre...", "gérer le lvm...") — REPLACE with English (Pitfall 9 + CLAUDE.md).
- `published_ports: [{{ node_exporter_port }}:9100]` (default-on host publish) — REPLACE with conditional Jinja per Phase-2 pattern (D-30 default `node_exporter_publish_host: false`).
- Container hardening (`read_only`, `cap_drop: [ALL]`, `capabilities: [DAC_READ_SEARCH]`, `security_opts: [no-new-privileges:true]`, `tmpfs: [...]`, `pids_limit: 512`) — **KEEP IN MODIFIED FORM**. These are good security defaults; carry forward but guard with `node_exporter_container_hardening_enabled: true` so operators can disable per environment. Document the hardening set in README.

**Replaced with better defaults:**
- INSPQ's `--path.rootfs=/rootfs` and `mounts: /:/rootfs:ro` — keep but mount at `/host/root` to match the upstream README's current canonical form (see Finding 6).
- INSPQ's `pid_mode: host` — KEEP. Needed for some collectors.

**Added (missing pitfall guards in upstream):**
- Pre-poll on HEALTHCHECK + in-network /metrics verify (D-10a + D-32 + D-54) — INSPQ has no verify step.
- Conditional `node_exporter_publish_host` default-false (Pitfall: Security Mistakes "Prometheus /metrics exposed to internet" — INSPQ defaulted to host publish).
- Pinned image tag (OPS-01).
- Image registry pin from `prom/node-exporter` → `quay.io/prometheus/node-exporter` (Pitfall: alignment with Alertmanager registry choice).

### roles/opentelemetry (plan 03-02)

INSPQ source: `~/git/inspq/ansible/opentelemetry/` (verified `defaults/main.yml` + `tasks/docker.yml` + `templates/common/collector-config.yaml.j2` partial read).

**Dropped (INSPQ-isms beyond grep gate):**
- `otel_image_version: latest` — REPLACE with `0.152.0` pin (OPS-01).
- `otel_deployment_method: docker` + Kubernetes branch tasks (`kubernetes.yml`, `kubernetes-helm.yml`) — DROP K8s branches for M1 (Telemetron is Docker-only per CLAUDE.md).
- All `otel_kubernetes_*`, `otel_servicemonitor_*`, `otel_networkpolicy_enabled`, `otel_instrumentation_*` vars + tasks — DROP entirely (K8s-only surface).
- `otel_image_pull: True` + force-recreate-on-image-change logic — REPLACE with handler-driven restart pattern (D-19) + `force_source: false`.
- French task names ("Déployer OTEL en docker...", "Gérer le conteneur...", "Faire le mapping des ports...", "S'assurer que le répertoire parent telemetron existe...") — REPLACE with English (Pitfall 9 + CLAUDE.md).
- French log/comment strings throughout `collector-config.yaml.j2` — REPLACE with English (`Supervision Prometheus Operator - Métriques internes`, etc.).
- `container_restart_policy: always` (default) — REPLACE with `unless-stopped`.
- Default `TZ: "America/Toronto"` — REPLACE with `Etc/UTC`.
- Default `otel_exporters_otlp: [{endpoint: {{ ansible_fqdn }}:4317, tls: false}]` — DROP entirely. Telemetron's exporters are Loki/Tempo/Mimir (D-44 amended per Finding 2), not a generic OTLP loopback.
- `otel_processors_batch` (legacy single-batch) AND `otel_processors_batch_traces/logs/metrics` (three-batch) parallel defaults — REPLACE with single `batch` processor per D-45 (no signal-type-split needed at M1 scale).
- UFW firewall rules — DROP per D-30 / D-52 / no-host-publish-except-:4317/:4318.
- `otel_jaeger_*` receivers (Jaeger gRPC, thrift_compact, thrift_binary, thrift_http) — DROP entirely. M1 ingest is OTLP-only (FEATURES.md / ARCHITECTURE.md).
- `otel_telemetry_logs_*` verbose self-log knobs — DROP defaults; keep simple `log_level: info`.
- `otel_processors_filter_drop_actuator` + actuator-path filtering logic — DROP. INSPQ-specific (Spring Boot Actuator paths); operator can re-add via `prometheus_extra_*` style extension if needed.

**Replaced with better defaults:**
- INSPQ's `otel_port_prometheus_endpoint_internal: 8888` + `otel_port_prometheus_endpoint_external: 9464` — REPLACE with D-42's `:8888` (self-metrics) + `:8889` (app-metrics Prometheus export). The `:9464` choice was INSPQ-specific; D-42's `:8889` is cleaner adjacent-to-:8888.

**Added (missing pitfall guards in upstream — the BIG list for OTel):**
- **`memory_limiter` processor + `GOMEMLIMIT` env var (Pitfall 5)** — INSPQ has NEITHER. This is the headline D-25 improvement for the OTel role. Without these, OTel OOMs on any sustained load.
- **`sending_queue` + `retry_on_failure` on every exporter (Pitfall 5)** — INSPQ has neither. Without these, transient backend unavailability becomes data loss.
- **`docker_stats` receiver (D-51 ContainerRestartLoop signal)** — Not in INSPQ. INSPQ has no container-restart story.
- **OTLP→Loki via `otlphttp`** (Finding 2 correction to D-44) — INSPQ has no Loki exporter at all (their stack used `otel_exporters_otlp` pointing at `ansible_fqdn:4317` — single-hop loopback).
- **D-43 forward-compat dual-exporter declaration** — INSPQ has no equivalent.
- **D-52 Docker socket Threat Model section in README** — INSPQ docs have nothing on the security implications.
- Per-pipeline processor order locked `[memory_limiter, batch]` — INSPQ has no explicit order discipline.
- Image registry pin already correct (`otel/opentelemetry-collector-contrib` — Contrib explicit) — KEEP, just pin version.

### roles/prometheus (plan 03-03)

INSPQ source: `~/git/inspq/ansible/prometheus/` (verified `defaults/main.yml` + `tasks/main.yml` + `templates/docker/prometheus.yml.j2` partial read).

**Dropped (INSPQ-isms beyond grep gate):**
- `prometheus_image_version: latest` — REPLACE with `v3.11.3` pin (OPS-01).
- `prometheus_deployment_type: docker` + Kubernetes branch tasks — DROP K8s (`kubernetes-helm.yml`, `kubernetes-operator.yml`) for M1.
- All `prometheus_namespace`, `prometheus_kubernetes_mode`, `prometheus_kubeconfig_file`, `prometheus_helm_*`, `prometheus_kube_*`, `prometheus_operator_*` vars + tasks — DROP entirely (K8s-only surface).
- French task names ("Déployer Prometheus sous Docker..." etc.) — REPLACE with English.
- `prometheus_container_env: TZ: "America/Toronto"` — REPLACE with `Etc/UTC`.
- `container_restart_policy: always` — REPLACE with `unless-stopped`.
- `prometheus_root_dir: /opt/prometheus` + `prometheus_data_dir: {{ prometheus_root_dir }}/data` + `prometheus_config_dir: {{ prometheus_root_dir }}/config` — REPLACE with Phase-1 D-18 flat layout: `/opt/telemetron/prometheus/<file>` for configs + named Docker volume `telemetron_prometheus_data` for TSDB.
- INSPQ's `prometheus_container_command` includes `--web.enable-remote-write-receiver` + `--enable-feature=remote-write-receiver` + `--enable-feature=remote-read-receiver` — DROP these flags. Telemetron's Prometheus is the WRITER of remote_write to Mimir, not a remote_write RECEIVER (D-42). Also DROP `--web.enable-otlp-receiver` for the same reason (OTel goes through OTel Collector, not directly into Prometheus).
- INSPQ's `prometheus_retention_size: 4GB` — DROP for M1 default. Time-based retention (`prometheus_retention_time: 15d`) is sufficient; size-based is an operator opt-in.
- INSPQ's URL-encoded alert rule format (`{{ %20 }}` etc.) — DROP. Replace with plain YAML alert rules; readable, no double-escape.
- `prometheus_alertmanager_alerting_rules` + `prometheus_alertmanager_recording_rules` operator-extension surfaces — REPLACE with simpler `prometheus_extra_rules: []` (list-of-dict) per Claude's Discretion.

**Replaced with better defaults:**
- INSPQ `prometheus_retention_time: 30d` — REPLACE with `15d` (Phase-3 Claude's Discretion: 15d > Mimir `query_store_after: 12h`; conservative for homelab disk budget).

**Added (missing pitfall guards in upstream):**
- **`metric_relabel_configs` cardinality defaults (Pitfall 3)** — INSPQ has none. Adding the default `pod_uid|container_id|request_id|trace_id` + `.*_id` `labeldrop` set is THE highest-leverage D-25 improvement for this role.
- **Baseline alert rule set (INGEST-03 four rules)** — INSPQ ships `prometheus_alertmanager_alerting_rules: []` empty default. Adding `HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals` makes the role useful out of the box.
- **Default scrape jobs for OTel `:8888` + `:8889` + node_exporter** — INSPQ has no default targets (`prometheus_alertmanager_servers: []` and nothing for scrape).
- **`remote_write` to Mimir as a default** — INSPQ has `prometheus_remote_write` as conditional/empty; Telemetron makes it the default M1 path (D-42 / INGEST-02).
- **In-network verify one-shot** (D-32 / D-54) — INSPQ has none.

### roles/fluentbit (plan 03-04)

INSPQ source: `~/git/inspq/ansible/fluentbit/` (verified `defaults/main.yml` + `tasks/docker.yml` + `templates/fluent-bit.conf.j2` + `templates/parsers.conf.j2`).

**Dropped (INSPQ-isms beyond grep gate):**
- `fluentbit_image_version: latest` — REPLACE with `4.2.3` pin (OPS-01).
- `fluentbit_deployment_type: docker` + K8s branch (`kubernetes_helm.yml`) — DROP K8s for M1.
- `fluentbit_namespace: telemetron`, `fluentbit_helm_*`, `fluentbit_service_account`, `fluentbit_openshift_scc_*`, `fluentbit_servicemonitor_enabled` — DROP entirely (K8s-only surface).
- `fluentbit_kubernetes_kind: DaemonSet`, `fluentbit_kubernetes_host_log_path: /var/log`, `fluentbit_kubernetes_containers_log_path: /var/log/containers`, `fluentbit_kubernetes_collect_host_logs`, `fluentbit_kubernetes_collect_container_logs` — DROP.
- French task names ("gérer les mount points nfs...", "S'assurer que le répertoire parent telemetron existe...", "gérer le lvm pour le stockage fluentbit...", "créer un filesystem xfs...", "monter le lvm...", "créer le répertoire de stockage fluentbit...", "set fact pour les répertoires fluentbit...", "créer les sous-répertoires...") — REPLACE with English.
- LVM tasks (`community.general.lvol`, `ansible.builtin.filesystem`, `ansible.builtin.mount`) — DROP entirely. Same INSPQ-internal-host assumption as node_exporter.
- `nfs.yml` and `fluentbit_nfs_mounts` — DROP. Phase 6's optional `nfsd` role handles legacy NFS; FB doesn't mount NFS shares.
- `docker_cleanup.yml` — DROP. Phase-1 D-19 handler-pattern + named-volume convention handles cleanup.
- `fluentbit_root_dir: /opt/fluentbit` — REPLACE with Phase-1 D-18 layout: `/opt/telemetron/fluentbit/` (configs) + `telemetron_fluentbit_buffer` volume.
- INSPQ default `fluentbit_inputs: [{type: tail, path: /var/log/containers/*.log, tag: kube.*, options: {Mem_Buf_Limit: 10MB, Skip_Long_Lines: On, Refresh_Interval: 5, Exclude_Path: /var/log/containers/fluentbit-*.log}}]` — REPLACE with D-46's Docker JSON tail `/var/lib/docker/containers/*/*-json.log` (k8s vs Docker host log layout difference; FB **role inversion** vs INSPQ documented in `project_fluentbit_role_shift.md` memory).
- INSPQ default `fluentbit_filters: [{type: kubernetes, match: kube.*, options: {Kube_Tag_Prefix: kube.var.log.containers., Merge_Log: On, Keep_Log: Off, K8S-Logging.Parser: On, K8S-Logging.Exclude: Off}}]` — DROP entirely (k8s-specific kubernetes filter). REPLACE with D-47 allowlist filter set (modify Add + parser regex level extraction + structured-metadata channeling).
- INSPQ default `fluentbit_outputs: [{type: stdout, match: *}]` — REPLACE with D-49 `opentelemetry` output to `otel:4318`.
- `fluentbit_restart_policy: always` — REPLACE with `unless-stopped`.
- `fluentbit_container_command: "/fluent-bit/bin/fluent-bit -c /fluent-bit/etc/fluent-bit.conf"` — KEEP (verbatim from upstream image; no Telemetron-specific override needed).
- No `Time_System_Timezone` set in INSPQ `[SERVICE]` block — **ADD `Etc/UTC` per D-50 / Pitfall 6** (this is the single most-impactful one-liner per Pitfall 6).
- No `Multiline_Flush` set — **ADD `5` per D-50 / Pitfall 6**.
- No `Read_from_Head` set — **ADD `false` per D-50**.

**Replaced with better defaults:**
- INSPQ's `fluentbit_health_check: On` + `fluentbit_hc_error_count: 5` — KEEP verbatim.
- INSPQ's `fluentbit_http_metrics: On` — KEEP (operator can scrape `:2020/api/v1/metrics/prometheus` later if needed).
- INSPQ's `fluentbit_http_port: 2020` — KEEP (canonical FB port).

**Added (missing pitfall guards in upstream):**
- **`Time_System_Timezone Etc/UTC` + `Multiline_Flush 5` + `Read_from_Head: false` (D-50 / Pitfall 6)** — INSPQ has none of these. Headline D-25 improvement for FB.
- **`storage.type filesystem` + `storage.max_chunks_up 128` + filesystem-buffer named volume (D-50)** — INSPQ has `# storage.path /fluent-bit/logs` commented out. Adding makes restart-survivable.
- **Fallback `@timestamp` modify filter (Pitfall 6 mode 2 mitigation)** — INSPQ has nothing.
- **D-47 label allowlist filter chain** — INSPQ has K8s filter doing different label mapping. The Telemetron filter chain is a clean rewrite.
- **D-49 `opentelemetry` output plugin** — INSPQ uses stdout default (debugging only). Adding the OTel target is the role's actual M1 purpose.
- **D-48 default-off extension knobs** (system_logs, journald, extra_tail_paths) — INSPQ has only the K8s tail; preserving the legacy-host-scoop use case via `fluentbit_extra_tail_paths` is a Telemetron-specific addition.

## Plan 03-02 Verify Topology (D-54 Decision Point)

CONTEXT.md D-54 asks the planner to pick between:
- **(a)** Plan 03-02's verify temporarily flips OTel metrics pipeline to `prometheusremotewrite` so a synthetic OTLP metric reaches Mimir before Prometheus exists.
- **(b)** Defer the metric-arrival assertion to 03-03's verify (when Prometheus is wired).

**Researcher recommendation: (a), with refinements.**

**Rationale:**
- **(a) is cleaner per-plan responsibility.** Plan 03-02 owns the OTel role; "the role is doing what it claims" deserves a positive smoke test in its OWN verify, not a deferred-to-next-plan assertion.
- **(a) exercises D-43's forward-compat knob.** The whole point of D-43 declaring BOTH exporters is to make the flip cheap. Plan 03-02's verify is the first natural test of that machinery.
- **(b) creates a verify-coverage gap.** If 03-02 only asserts `/health` 200 and OTLP-receiver-accepting, a broken `prometheusremotewrite` exporter wouldn't be caught until 03-03 runs — and 03-03's actual focus is Prometheus scraping, not OTel exporter health.

**Concrete shape of approach (a):**

```yaml
# roles/opentelemetry/tasks/verify.yml
# Step 1: poll HEALTHCHECK / State.Running.
# Step 2: in-network curl probes of :4318/v1/{traces,logs,metrics} return 200 on POST.
# Step 3: bucket-trinity assertion — synthetic OTLP trace lands in tempo-traces;
#         synthetic OTLP log lands in loki-chunks.
# Step 4 (NEW — approach (a)): flip metrics-pipeline exporter via Jinja conditional
#         at verify-time only, push synthetic OTLP metric to :4318/v1/metrics,
#         assert it lands in mimir-blocks bucket via mc ls.
#
# Implementation: roles/opentelemetry/tasks/verify.yml has its OWN config render
# (writes a verify-config.yaml to /opt/telemetron/opentelemetry/verify-config.yaml
# with telemetron_otel_metrics_path set to 'remote_write' regardless of the role
# default), runs a one-shot otel-collector-contrib container loaded with that
# config (not the production container — separate container_name), pushes synthetic
# metric, asserts bucket, removes the one-shot container, leaves the production
# container untouched.
```

**Alternative refinement:** Run the verify metric push against the production container after temporarily swapping its config and restarting it. **Researcher rejects this** — it touches production state mid-verify which violates Phase-2 D-32 idempotency posture.

**Plan 03-03 reverts nothing.** Because the production container's config (the rendered `/opt/telemetron/opentelemetry/config.yaml`) was never touched, plan 03-03's prometheus role port just appends `role: prometheus` to the playbook and runs end-to-end with the production OTel config (using `prometheus` exporter on `:8889`).

**Tempo bucket assertion subtlety (from Phase-2 Tempo verify):** Per Phase-2 `roles/tempo/tasks/verify.yml` lines 136–144, Tempo does NOT flush blocks to S3 on a single synthetic push (max_block_duration defaults to 2h). The same caveat applies to Mimir on a single synthetic remote_write push. **Recommendation:** Plan 03-02 Step 4 asserts the HTTP push returned 200/202/204 — bucket-landing assertion is impractical at single-push granularity. The end-to-end bucket-landing smoke moves to Phase 6 OPS-07 (longer running window).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OTel `loki` exporter to `/loki/api/v1/push` | OTel `otlphttp` exporter to Loki's `/otlp` endpoint | Deprecated 2024-07-09; removed from contrib in v0.131.0 | **CONTEXT.md D-44 needs amendment.** Loki 3.7 natively supports OTLP/HTTP. |
| Prometheus `<2.x` rule files + monolithic config | Prometheus 3.x with separated rule_files + `--web.enable-lifecycle` reload | Prometheus 3.0 release 2024-11 | Phase 3 uses 3.x form; rule files in `/opt/telemetron/prometheus/rules/` |
| Fluent Bit `4.x` stable | Fluent Bit `5.x` released May 2026 | Too new for M1 (pin 4.2.3 per STACK.md) | Stay on 4.x for M1; 5.x is a future hardening candidate |
| node_exporter `--path.rootfs=/rootfs` | node_exporter `--path.rootfs=/host/root` | Recent upstream README change | Use `/host/root` to match current upstream docs |
| OTel `processor_refused_*` metrics | OTel `receiver_refused_*` metrics | Naming-convention clarification in OTel internal telemetry docs | **CONTEXT.md Claude's-Discretion alert rule needs prefix correction.** |
| FB `K8S-Logging.Parser: On` for k8s container logs | FB `tail` direct on Docker JSON file paths | Telemetron isn't k8s; D-46 inverts the upstream | Role inversion vs INSPQ documented as D-25 deviation |

**Deprecated/outdated (relative to INSPQ source):**
- `:latest` image tags — replaced with explicit pins (OPS-01).
- French task names + comments — replaced with English (Pitfall 9 + CLAUDE.md).
- LVM-on-textfile / LVM-on-buffer assumptions — replaced with named Docker volumes.
- K8s Helm/ServiceMonitor branches — dropped entirely for M1 (Docker-only per CLAUDE.md).
- UFW firewall rules — dropped per D-30 no-host-publish model.

## Open Questions

These are gaps the planner should close during plan-phase, with researcher's recommended defaults.

### Q1: `loki` exporter replacement — `otlphttp` confirmed; does the planner amend D-44 or document deviation?

**What we know:** `loki` exporter removed from contrib in v0.131.0; Loki 3.7 supports OTLP/HTTP at `/otlp`; `otlphttp` exporter is the canonical replacement.

**What's unclear:** Whether the planner has authority to amend D-44 (a locked decision) or must document the change as a D-25 deviation in `roles/opentelemetry/README.md` and surface for operator visibility.

**Recommendation:** Plan 03-02 documents the change as a D-25 deviation entry in the role README and adds a note to CONTEXT.md's decision log (postface) noting D-44 is amended. The planner does NOT relitigate the intent (OTel→Loki transport) — just selects the only feasible implementation at the pinned tag.

### Q2: OTel self-metrics prefix correction — confirmed `otelcol_receiver_refused_*`

**What we know:** WebFetch of OTel internal-telemetry docs confirms `otelcol_receiver_refused_log_records`, `otelcol_receiver_refused_metric_points`, `otelcol_receiver_refused_spans` are the canonical names. CONTEXT.md's Claude's Discretion section for the alert rule writes `otelcol_processor_refused_*`.

**What's unclear:** Whether `otelcol_processor_refused_*` is a legacy name that was renamed (in which case both might work at v0.152.0) or whether it never existed.

**Recommendation:** Plan 03-03 uses `otelcol_receiver_refused_*` in the alert rule expression. The planner adds a small note explaining the correction. Researcher's WebFetch evidence is sufficient.

### Q3: Docker labels in FB tail — does FB 4.2 extract container Docker labels at tail-input time?

**What we know:** FB `tail` input parses the Docker JSON log entries (which contain `container_id`, `log`, `stream`, `time`, `attrs`); container Docker labels (`com.telemetron.{service,env,job}`) live in the Docker container's metadata, NOT in the JSON log entry.

**What's unclear:** Whether FB 4.2's tail input can enrich records with container labels (similar to how the k8s `kubernetes` filter enriches with pod labels), or whether the role needs a separate filter (e.g., `lua` or `record_modifier` filter) to look up labels via the Docker API at read time.

**Recommendation:** Plan 03-04 ships D-47 with a **simpler fallback**: use `container_name` (extracted from the file path via `Tag_Regex` capture group) as both `job` and `service` defaults. Operator-set Docker labels promotion to record fields is deferred to a Phase-3-followup or a `[FILTER] lua` script extension. Document the fallback semantics in `roles/fluentbit/README.md` "Labeling operator apps" section: "Operators who want container-Docker-label-driven labeling will need to add a `[FILTER] lua` script — researcher recommendation for v2."

### Q4: node_exporter HEALTHCHECK — does the image support `wget`?

**What we know:** `quay.io/prometheus/node-exporter:v1.11.1` is a from-scratch image (no shell, no `wget`).

**What's unclear:** Whether the image ships any binary capable of self-health-checking (similar to `loki -health` in Phase 2 Loki).

**Recommendation:** Plan 03-01 does an image probe at execute time (similar to Phase-2 Tempo/Mimir probes):
```bash
docker run --rm quay.io/prometheus/node-exporter:v1.11.1 --version
docker run --rm quay.io/prometheus/node-exporter:v1.11.1 --help | grep -i health
```
- Outcome A: native `--health` flag exists → use it.
- Outcome B: only `--version` (binary-alive proxy) → use `["CMD", "/bin/node_exporter", "--version"]`.
- Outcome C: nothing available → set `node_exporter_healthcheck_enabled: false` and use State.Running poll + in-network curl probe.

Plan 03-01 ships the role with the conditional pattern Phase-2 Tempo/Mimir already established.

### Q5: Fluent Bit HEALTHCHECK — does the image ship `wget`?

**What we know:** FB image `fluent/fluent-bit:4.2.3` is distroless (`docker run --rm fluent/fluent-bit:4.2.3 --version` works; shell may or may not).

**What's unclear:** Confirmed via image probe at execute time. Same conditional-healthcheck pattern.

**Recommendation:** Plan 03-04 does the same image-probe-and-fallback dance. Most-likely outcome: `["CMD", "/fluent-bit/bin/fluent-bit", "--version"]` (binary-alive proxy) is safe.

### Q6: OTel docker socket — Approach A (group_add) vs Approach B (run-as-root)

**What we know:** OTel Collector v0.40+ images run as non-root; reading `/var/run/docker.sock` requires either group membership in the host's `docker` group OR running as root.

**Recommendation (researcher):** Approach A (group_add) — see "Phase-3-specific gotcha" section above. Plan 03-02 surfaces `opentelemetry_docker_group_gid: "{{ docker_group_gid | default(omit) }}"` and uses `ansible.builtin.getent` to look up the local docker GID at deploy time. README documents the alternative (Approach B) for operators on systems where group_add doesn't work cleanly.

### Q7: Loki `/otlp` endpoint authentication / X-Scope-OrgID header

**What we know:** Loki 3.7 with `auth_enabled: false` (Phase-2 D-26) accepts OTLP/HTTP on `/otlp` without `X-Scope-OrgID`. The Grafana docs confirm this for `otlphttp` exporter pointed at `http://loki:3100/otlp`.

**What's unclear:** Whether Loki's `/otlp` endpoint behavior under `auth_enabled: false` precisely matches the `/loki/api/v1/push` behavior (i.e., assigns to tenant `fake`).

**Recommendation:** Trust the official Grafana docs that single-tenant single-user mode works on both endpoints. Plan 03-02 verify Step 3 (Loki bucket assertion via mc ls — if implemented; researcher recommends skipping per Q9 below) provides ground-truth verification.

### Q8: Prometheus `:9090` HTTP/metrics — host publish or not?

**What we know:** Phase-2 backends all default `<role>_publish_host: false`. Prometheus's `:9090` UI is operator-facing (queries, target health, rule status). Future Grafana datasource will scrape Prometheus on the `telemetron` network, not the host.

**Recommendation:** Plan 03-03 sets `prometheus_publish_host: false` per D-30 default. Operator accesses Prometheus UI via `ssh -L 9090:localhost:9090 host`. README documents.

### Q9: Verify-step depth — push synthetic data through OTel and assert MinIO bucket landing?

**What we know:** Phase-2 Tempo and Mimir verify steps explicitly OMITTED bucket-landing assertions because single-trace/single-metric pushes don't trigger S3 flush (block-duration > test window). Loki's verify DID assert bucket landing because Loki flushes on chunk_idle_period (30m) AND on close, and `loki_chunk_target_size` is small enough that the synthetic push triggers a flush within ~20s.

**Recommendation:**
- Plan 03-02 (OTel) verify: HTTP push to `:4318/v1/traces`, `:4318/v1/logs`, `:4318/v1/metrics` → assert 200/202/204 from each endpoint. DO NOT assert MinIO bucket landing per Tempo's Phase-2 verify rationale. Step 4 (D-54 approach (a)) is the metric-arrival via `prometheusremotewrite` — bucket-landing assertion is impractical for the same reason.
- Plan 03-03 (Prometheus) verify: curl `/api/v1/targets` and assert `otel_self`, `otel_metrics`, `node_exporter` all show `up`; curl `/api/v1/rules` and assert four baseline rule names loaded; curl `/api/v1/query?query=up{job=~"otel_.*|node_exporter"}` and assert result count ≥ 2.
- Plan 03-04 (FB) verify: `/api/v1/health` returns 200. End-to-end FB→Loki smoke deferred to Phase 6 OPS-07.

## Sources

### Primary (HIGH confidence)

- [OpenTelemetry Collector Contrib v0.152.0 release](https://github.com/open-telemetry/opentelemetry-collector-contrib/releases/tag/v0.152.0) — Confirmed release date 2026-05-12 and that loki exporter was removed pre-v0.152.0.
- [OpenTelemetry Collector Contrib exporter directory @ v0.152.0](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.152.0/exporter) — Verified via `gh api repos/.../contents/exporter?ref=v0.152.0`; no `lokiexporter` entry.
- [OpenTelemetry Collector memorylimiterprocessor README](https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md) — Fetched via `gh api`. Confirmed `check_interval` default 0s (recommend 1s), `limit_mib`/`spike_limit_mib` semantics, GOMEMLIMIT-at-80% recommendation, MUST-be-first-in-pipeline guidance.
- [OpenTelemetry Collector exporterhelper README](https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md) — Fetched via `gh api`. Confirmed `sending_queue` + `retry_on_failure` field names, defaults, semantics.
- [OpenTelemetry Collector docker_stats receiver README](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/dockerstatsreceiver) — Fetched via `gh api`. Confirmed config fields (`endpoint`, `collection_interval`, `excluded_images`, `metrics.<name>.enabled`), Docker socket permission caveats.
- [OpenTelemetry Collector docker_stats receiver documentation.md (full metric catalog)](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/dockerstatsreceiver/documentation.md) — Fetched via `gh api`. Confirmed `container.restarts` and `container.uptime` are OPTIONAL metrics (opt-in via `enabled: true`).
- [OpenTelemetry Collector prometheusexporter README](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusexporter) — Fetched via `gh api`. Confirmed `endpoint`, `metric_expiration`, `enable_open_metrics`, `translation_strategy` defaults.
- [OpenTelemetry internal-telemetry docs](https://opentelemetry.io/docs/collector/internal-telemetry/) — Confirmed self-metric naming prefix `otelcol_receiver_refused_*` (NOT `otelcol_processor_refused_*`); default port :8888.
- [Fluent Bit opentelemetry output plugin docs](https://docs.fluentbit.io/manual/data-pipeline/outputs/opentelemetry) — Confirmed config fields (`host`, `port`, `logs_uri`, `metrics_uri`, `traces_uri`, `tls`, `log_response_payload`); default endpoints `/v1/{logs,metrics,traces}`.
- [Prometheus configuration reference](https://prometheus.io/docs/prometheus/latest/configuration/configuration/) — Confirmed `metric_relabel_configs` syntax, `labeldrop` action semantics.
- [Grafana Loki OTLP ingestion docs](https://grafana.com/docs/loki/latest/send-data/otel/) — Confirmed Loki 3.x supports `otlphttp` exporter at `/otlp` endpoint, no header needed when `auth_enabled: false`.
- [node_exporter v1.11.1 release](https://github.com/prometheus/node_exporter/releases/tag/v1.11.1) — Verified release date 2026-04-07; current stable.
- [node_exporter README — containerized deployment](https://github.com/prometheus/node_exporter) — Confirmed canonical container bind-mount pattern (`/host/root` + `--path.rootfs`).
- [Phase 1 + 2 RESEARCH.md + CONTEXT.md + canonical roles] — Full canonical role-template authority on Telemetron's deploy patterns (D-10a, D-19, D-20, D-32, etc.).
- [CLAUDE.md project instructions](#) — Per-component pin authority, English-only constraint, MIT license, Docker-only M1.

### Secondary (MEDIUM confidence)

- [Loki exporter deprecation discussion — opentelemetry-collector-contrib#33916](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/33916) — Confirmed deprecation timeline (2024-07-09).
- [Loki exporter removal discussion — opentelemetry-collector-contrib#38374](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/38374) — Confirmed removal in v0.131.0.
- INSPQ source roles under `~/git/inspq/ansible/{node_exporter,opentelemetry,prometheus,fluentbit}/` — Local-filesystem read; informs D-25 deviation audit.

### Tertiary (LOW confidence — flagged for hands-on verification at execute time)

- node_exporter image HEALTHCHECK shape (wget availability) — image probe at plan 03-01 execute time.
- FB image HEALTHCHECK shape (shell availability) — image probe at plan 03-04 execute time.
- OTel image's Docker socket access via group_add Approach A — hands-on verification on Rock's homelab.
- Loki `/otlp` endpoint behavior under `auth_enabled: false` specifically vs `/loki/api/v1/push` — verified by docs but not by Telemetron's own stack until plan 03-02 verify lands.

## Validation Architecture

> Phase 3 uses the same Ansible-driven per-role validation pattern Phase 1+2 established. Telemetron's M1 has no separate test framework (CLAUDE.md "test surface — single host" constraint); validation is per-role idempotent playbook runs + in-network verify one-shot containers (D-54).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Ansible playbook + `community.docker.docker_container` one-shot containers (D-32 / D-54 pattern from Phase 1+2) |
| Config file | Each role's `tasks/verify.yml` (included from `tasks/main.yml`) |
| Quick run command | `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags <role> --ask-vault-pass` |
| Full suite command | `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --ask-vault-pass` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Verify Task Step |
|--------|----------|-----------|-------------------|------------------|
| INGEST-01 | Prometheus scraping OTel `:8888`/`:8889` + node_exporter | integration | `--tags prometheus` | 03-03 verify Step 2: curl `/api/v1/targets` → assert `otel_self`, `otel_metrics`, `node_exporter` all `up` |
| INGEST-01 | `metric_relabel_configs` drop high-cardinality | static | `--tags prometheus` rendered config + grep | 03-03 verify Step 1 (rendered config grep for `labeldrop` action) |
| INGEST-02 | remote_write to Mimir | integration | `--tags prometheus` | 03-03 verify Step 3: curl `prometheus_remote_storage_samples_in_total` query > 0 |
| INGEST-03 | Four baseline rules loaded | static | `--tags prometheus` | 03-03 verify Step 4: curl `/api/v1/rules` → assert four rule names |
| INGEST-03 | `prometheus_extra_rules` extension | static | rendered-config grep | 03-03 verify Step 5 (idempotency double-run) |
| INGEST-04 | OTel accepts OTLP on `:4317`/`:4318` | integration | `--tags opentelemetry` | 03-02 verify Step 2: curl-POST synthetic OTLP trace/log/metric to `:4318` → assert 200/202/204 |
| INGEST-04 | OTel fans out to Loki/Tempo/Mimir | integration | `--tags opentelemetry` | 03-02 verify Step 3 (Loki bucket assertion if feasible — Pitfall: tempo/mimir bucket assertions deferred per Phase-2 pattern) |
| INGEST-05 | Pipeline order `[memory_limiter, batch, ...]` | static | rendered-config grep | 03-02 verify Step 1: grep `/opt/telemetron/opentelemetry/config.yaml` for processor order |
| INGEST-05 | GOMEMLIMIT ~80% mem_limit | static | `docker inspect` env | 03-02 verify Step 1.5: `docker inspect telemetron-otel --format '{{.Config.Env}}'` contains `GOMEMLIMIT=400MiB` |
| INGEST-05 | per-exporter sending_queue + retry_on_failure | static | rendered-config grep | 03-02 verify Step 1: grep config.yaml for `sending_queue: enabled: true` AND `retry_on_failure: enabled: true` |
| INGEST-05 | Container doesn't OOM under 5-min synthetic load | manual-only | (M1 manual smoke; out of automated suite) | Phase 6 OPS-07 |
| INGEST-06 | FB tails Docker logs, ships through OTel to Loki | integration | `--tags fluentbit` | 03-04 verify Step 2: curl FB `:2020/api/v1/health` → 200; end-to-end FB→Loki deferred to Phase 6 OPS-07 |
| INGEST-06 | `Time_System_Timezone Etc/UTC` + `Multiline_Flush 5` | static | rendered-config grep | 03-04 verify Step 1: grep `/opt/telemetron/fluentbit/fluent-bit.conf` |
| INGEST-07 | FB ships only allowlist labels | integration | `--tags fluentbit` | 03-04 verify Step 3 (deferred): query Loki `/loki/api/v1/labels` → assert label set ⊆ `{job, host, service, env, level}`. Deferred to Phase 6 OPS-07. |
| INGEST-08 | node_exporter on `:9100/metrics` scraped by Prometheus | integration | `--tags node_exporter` | 03-01 verify Step 2: curl `http://node-exporter:9100/metrics` → 200 + body contains `node_cpu_seconds_total` |

### Sampling Rate

- **Per task commit:** `ansible-playbook ... --tags <role> --check --diff` (idempotency dry-run) — sanity check before commit.
- **Per wave merge:** Full role's playbook run; verify task asserts pass.
- **Phase gate:** All four roles green; second back-to-back run reports `changed=0` per OPS-04; grep gates clean per OPS-05; `gsd-tools verify-work` confirms.

### Wave 0 Gaps

- [ ] `roles/node_exporter/{defaults,tasks,handlers,meta,templates}/main.{yml,j2}` — full role layout (mirror Phase 2 minio/loki/tempo/mimir shape).
- [ ] `roles/node_exporter/README.md` — OPS-03 schema.
- [ ] `roles/opentelemetry/{defaults,tasks,handlers,meta,templates}/main.{yml,j2}` — full role layout.
- [ ] `roles/opentelemetry/README.md` — OPS-03 schema + Threat Model section (D-52) + Modes section (D-43 knob).
- [ ] `roles/prometheus/{defaults,tasks,handlers,meta,templates}/main.{yml,j2}` — full role layout.
- [ ] `roles/prometheus/README.md` — OPS-03 schema.
- [ ] `roles/prometheus/templates/rules-baseline.yml.j2` — four baseline alert rules.
- [ ] `roles/prometheus/templates/rules-extras.yml.j2` — operator extras renderer.
- [ ] `roles/fluentbit/{defaults,tasks,handlers,meta,templates}/main.{yml,j2}` — full role layout.
- [ ] `roles/fluentbit/templates/parsers.conf.j2` — docker JSON parser + level_extractor regex.
- [ ] `roles/fluentbit/README.md` — OPS-03 schema + Labeling operator apps section (D-47) + FB→Loki direct alternative.
- [ ] `inventory/example-homelab/group_vars/all/{node_exporter,opentelemetry,prometheus,fluentbit}.yml` — operator-facing tunable surface per role.
- [ ] `playbooks/deploy_docker.yml` — append four role entries in D-41 order.
- [ ] `roles/README.md` — tick the four port-status rows.

## Metadata

**Confidence breakdown:**
- Standard stack (image pins, versions): HIGH — every pin verified via gh api or WebFetch against the upstream registry/release notes.
- Architecture patterns (role layout, verify shape, D-19/D-20/D-32 carry-forward): HIGH — directly mirrors Phase 1+2 canonical roles in the same repo.
- OTel Collector config shape (memory_limiter ratios, sending_queue defaults, docker_stats config, OTLP receivers/exporters): HIGH — every field verified against the official README in the OTel repos at the appropriate version.
- D-44 amendment (`loki` exporter → `otlphttp`): HIGH — verified by listing `exporter/` directory at `ref=v0.152.0` shows no `lokiexporter`.
- OTel self-metric prefix correction (`processor_*` → `receiver_*`): HIGH — verified against opentelemetry.io official docs.
- INSPQ deviation audit: MEDIUM — based on local-filesystem read of all four INSPQ source roles; subjective judgment on what counts as "improvement" vs "mechanical translation."
- Fluent Bit Docker-label-extraction in tail input (Q3): LOW — needs hands-on verification at plan 03-04 execute time; researcher recommends fallback (container_name as job/service).
- HEALTHCHECK shape per image (node_exporter, OTel, FB): LOW — needs image probe at execute time per Phase-2 Tempo/Mimir pattern.

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (30 days — stack pins are stable; OTel ecosystem changes monthly so re-verify Loki exporter status and OTel internal-metric naming if research is re-used past this window).
