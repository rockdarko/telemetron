---
plan: 03-02-opentelemetry
phase: 03-ingest-plane
type: execute
wave: 2
depends_on: [03-01-node-exporter]
requirements: [INGEST-04, INGEST-05]
files_modified:
  - roles/opentelemetry/defaults/main.yml
  - roles/opentelemetry/tasks/main.yml
  - roles/opentelemetry/tasks/verify.yml
  - roles/opentelemetry/handlers/main.yml
  - roles/opentelemetry/meta/main.yml
  - roles/opentelemetry/templates/config.yaml.j2
  - roles/opentelemetry/templates/verify-config.yaml.j2
  - roles/opentelemetry/README.md
  - inventory/example-homelab/group_vars/all/opentelemetry.yml
  - playbooks/deploy_docker.yml
  - roles/README.md
autonomous: true

must_haves:
  truths:
    - "In-network POSTs to http://otel:4318/v1/{traces,logs,metrics} return HTTP 200/202/204 (ROADMAP SC1 + INGEST-04 partial; full bucket-landing deferred per Phase-2 pattern)."
    - "Rendered /opt/telemetron/opentelemetry/config.yaml has `processors: [memory_limiter, batch, ...]` in that exact order in every pipeline (ROADMAP SC4 / INGEST-05 / Pitfall 5)."
    - "Rendered config.yaml declares BOTH `prometheus` AND `prometheusremotewrite` exporters (D-43 forward-compat)."
    - "OTel container has `GOMEMLIMIT=400MiB` env (80% of 512m mem_limit) -- visible via `docker inspect telemetron-otel --format '{{.Config.Env}}'`."
    - "Every exporter in config.yaml has `sending_queue: enabled: true` AND `retry_on_failure: enabled: true` blocks (INGEST-05)."
    - "OTel→Loki uses `otlphttp` exporter at `http://loki:3100/otlp` (D-44 AMENDED per RESEARCH Finding 2 -- loki exporter removed in v0.131.0)."
    - "OTel→Tempo uses `otlp` exporter (gRPC) at `tempo:14317` with `tls.insecure: true` (D-44 Tempo leg confirmed; Phase-2 D-29 internal-only port)."
    - "OTel `docker_stats` receiver enabled with `metrics.container.restarts.enabled: true` AND `metrics.container.uptime.enabled: true` (RESEARCH correction #4; D-51 ContainerRestartLoop signal source)."
    - "Docker socket bind-mounted RO at `/var/run/docker.sock:/var/run/docker.sock:ro` (D-52); Approach A (group_add with host's docker GID) applied per RESEARCH Q6."
    - "README documents D-44 amendment + D-52 Threat Model + D-43 Modes + D-51 docker_stats catchment + D-25 deviation audit."
    - "Verify task (D-54 approach a) spawns a SEPARATE one-shot OTel-Collector-Contrib container loaded with verify-config.yaml.j2 (using prometheusremotewrite exporter), pushes synthetic OTLP metric to mimir:9009, queries http://mimir:9009/api/v1/query, asserts presence -- production container untouched."
    - "Re-running the playbook reports `changed=0` for the opentelemetry tag (OPS-04)."
    - "All six per-role port-acceptance gates pass on `roles/opentelemetry/`."
  artifacts:
    - path: roles/opentelemetry/defaults/main.yml
      provides: "Image pin otel/opentelemetry-collector-contrib:0.152.0, port matrix (4317/4318/8888/8889), mem_limit 512m, GOMEMLIMIT 400MiB, memory_limiter ratios (260/80), no-host-publish-except-OTLP triple-conditional, docker_stats endpoint, telemetron_otel_metrics_path knob default 'prometheus', conditional-HEALTHCHECK pattern."
      contains: "0.152.0"
    - path: roles/opentelemetry/templates/config.yaml.j2
      provides: "Production OTel config with receivers (otlp + docker_stats with container.restarts opt-in), processors [memory_limiter, batch], exporters (otlphttp/loki + otlp/tempo + prometheus + prometheusremotewrite declared-but-conditional), pipelines (traces/logs/metrics with Jinja conditional on telemetron_otel_metrics_path)."
      contains: "memory_limiter"
    - path: roles/opentelemetry/templates/verify-config.yaml.j2
      provides: "Verify-only OTel config used by tasks/verify.yml Step 4 (D-54 approach a) -- same receivers/processors but metrics pipeline EXPLICITLY uses prometheusremotewrite exporter regardless of inventory knob. Loaded into a one-shot container, never overwrites production config."
      contains: "prometheusremotewrite"
    - path: roles/opentelemetry/tasks/main.yml
      provides: "Bootstrap: ensure config dir, render production config (notify restart), getent docker group GID (Approach A), pull image, run container with Docker socket RO + group_add + OTLP/Prometheus published_ports conditional + conditional HEALTHCHECK, include verify.yml."
      contains: "include_tasks: verify.yml"
    - path: roles/opentelemetry/tasks/verify.yml
      provides: "D-10a poll + Step 2 OTLP /v1/{traces,logs,metrics} 200 probes + Step 3 config grep assertions (memory_limiter first, GOMEMLIMIT env, sending_queue/retry_on_failure on every exporter) + Step 4 verify-config one-shot push to mimir + assert Mimir query."
      contains: "verify-config"
    - path: roles/opentelemetry/handlers/main.yml
      provides: "Single restart handler (W6) via docker restart -- never state: restarted (Pitfall 8)."
      contains: "Docker restart opentelemetry"
    - path: roles/opentelemetry/README.md
      provides: "OPS-03 schema + Modes (D-43 dual-exporter knob) + Threat Model (D-52) + D-25 audit including D-44 amendment + D-51 docker_stats catchment list + 'What metrics are collected' section."
      contains: "## Threat Model"
    - path: inventory/example-homelab/group_vars/all/opentelemetry.yml
      provides: "Operator knobs: telemetron_otel_metrics_path: prometheus (D-43), opentelemetry_publish_otlp: true (allow OTLP host publish for external producers), opentelemetry_memory_limit: 512m, opentelemetry_docker_group_gid lookup."
      contains: "telemetron_otel_metrics_path"
    - path: playbooks/deploy_docker.yml
      provides: "opentelemetry role wired in D-41 order: after node_exporter, before prometheus."
      contains: "role: opentelemetry"
  key_links:
    - from: "roles/opentelemetry/templates/config.yaml.j2 service.pipelines"
      to: "config.yaml.j2 processors block"
      via: "Hardcoded list `[memory_limiter, batch]` -- Pitfall 5 inline-cited in the template comment"
      pattern: "processors:\\s*\\[memory_limiter,\\s*batch"
    - from: "roles/opentelemetry/tasks/main.yml docker_container env"
      to: "GOMEMLIMIT=400MiB"
      via: "Hardcoded env var; ratio to mem_limit documented in defaults/main.yml comment"
      pattern: "GOMEMLIMIT.*400MiB"
    - from: "roles/opentelemetry/templates/config.yaml.j2 exporters.otlphttp/loki"
      to: "http://loki:3100/otlp"
      via: "OTLP/HTTP exporter -- D-44 AMENDMENT per Finding 2 (loki exporter removed)"
      pattern: "http://loki:3100/otlp"
    - from: "roles/opentelemetry/templates/config.yaml.j2 exporters.otlp/tempo"
      to: "tempo:14317"
      via: "OTLP gRPC; Phase-2 D-29 internal-only port"
      pattern: "endpoint:\\s*tempo:14317"
    - from: "roles/opentelemetry/templates/config.yaml.j2 receivers.docker_stats"
      to: "/var/run/docker.sock"
      via: "endpoint: unix:///var/run/docker.sock; bind-mounted RO by tasks/main.yml"
      pattern: "unix:///var/run/docker.sock"
    - from: "roles/opentelemetry/tasks/verify.yml Step 4"
      to: "roles/opentelemetry/templates/verify-config.yaml.j2"
      via: "Rendered to /opt/telemetron/opentelemetry/verify-config.yaml; loaded into a one-shot otel-collector-contrib container with prometheusremotewrite exporter (D-54 approach a)"
      pattern: "verify-config\\.yaml"
    - from: "roles/opentelemetry/tasks/main.yml"
      to: "host docker group GID"
      via: "ansible.builtin.getent database=group key=docker -> register -> group_add (RESEARCH gotcha Approach A)"
      pattern: "getent.*docker"
---

<objective>
Port the `opentelemetry` role into `roles/opentelemetry/` mirroring the Phase-2 canonical role-template layout. This is the heaviest Phase-3 plan -- it carries the two MANDATORY research corrections (D-44 amendment + alert-metric prefix surfaces here via README documentation), the Pitfall 5 mitigation pack (memory_limiter ratios, GOMEMLIMIT, sending_queue/retry_on_failure on every exporter), the D-43 dual-exporter forward-compat knob, the D-51 docker_stats receiver for ContainerRestartLoop, the D-52 Docker socket security model, and the D-54 approach (a) verify topology that exercises the prometheusremotewrite exporter via a one-shot container.

Purpose: deliver INGEST-01 (OTel as OTLP ingest on :4317/:4318 fanning out to Loki/Tempo/Mimir), INGEST-05 (pipeline shape + memory/queues), INGEST-07 (Docker socket + docker_stats receiver for restart-loop signal), INGEST-08 (signal fanout to all three backends). Establishes the verify topology that exercises D-43 forward-compat without polluting the production config.

Output: full canonical role layout under `roles/opentelemetry/` plus two Jinja templates (config + verify-config) plus inventory file plus playbook wiring plus roles/README.md status row tick. All six port-acceptance gates pass.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/03-ingest-plane/03-CONTEXT.md
@.planning/phases/03-ingest-plane/03-RESEARCH.md
@.planning/research/PITFALLS.md
@CLAUDE.md
@roles/README.md
@roles/mimir/defaults/main.yml
@roles/mimir/tasks/main.yml
@roles/mimir/tasks/verify.yml
@roles/mimir/handlers/main.yml
@roles/mimir/meta/main.yml
@roles/mimir/README.md
@roles/loki/templates/loki.yaml.j2
@roles/loki/tasks/verify.yml
@inventory/example-homelab/group_vars/all/network.yml
@inventory/example-homelab/group_vars/all/storage.yml
@inventory/example-homelab/group_vars/all/mimir.yml
@playbooks/deploy_docker.yml
@.planning/phases/03-ingest-plane/03-01-node-exporter-PLAN.md

<interfaces>
<!-- Phase-2 backends and conventions this role wires into. -->

From inventory/example-homelab/group_vars/all/network.yml:
- telemetron_network: telemetron
- telemetron_publish_default: false
- telemetron_tz: Etc/UTC

From inventory/example-homelab/group_vars/all/storage.yml:
- telemetron_volume_prefix: telemetron      # OTel is STATELESS -- no data volume
- telemetron_config_root: /opt/telemetron   # config dir at /opt/telemetron/opentelemetry/

Phase-2 backend DNS endpoints (already wired and verified):
- Loki: http://loki:3100  (Phase-2 D-26 auth_enabled: false; native /otlp endpoint accepts OTLP/HTTP -- Finding 2)
- Tempo: tempo:14317 (gRPC, Phase-2 D-29 internal-only OTLP port; tls.insecure: true)
- Mimir: http://mimir:9009/api/v1/push (Phase-2 D-26 multitenancy_enabled: false -- no X-Scope-OrgID needed)

RESEARCH corrections that LAND in this plan (verbatim from RESEARCH.md Findings):

**Correction #1 (D-44 amendment, CRITICAL):** loki exporter REMOVED from contrib in v0.131.0; v0.152.0 does NOT ship it. Use `otlphttp/loki` exporter to `http://loki:3100/otlp`. Document as D-25 deviation in README with subheading "Loki exporter replaced by otlphttp (upstream removal)".

**Correction #4 (container.restarts opt-in):** The `dockerstatsreceiver` ships `container.restarts` DISABLED by default. Config MUST include:
```yaml
receivers:
  docker_stats:
    metrics:
      container.restarts:
        enabled: true
      container.uptime:
        enabled: true
```
After OTel→Prometheus translation, the metric appears as `container_restarts_total` (Plan 03-03 alert rule expects this exact name).

**D-45 ratios (Pitfall 5, locked):**
- `mem_limit`: 512m
- `GOMEMLIMIT`: 400MiB (80% of 512m)
- `memory_limiter.limit_mib`: 260 (65% of 400)
- `memory_limiter.spike_limit_mib`: 80 (20% of 400)
- Effective soft limit: 180MiB

**D-45 per-exporter resilience (every exporter):**
```yaml
sending_queue:
  enabled: true
  num_consumers: 4
  queue_size: 1000
retry_on_failure:
  enabled: true
  initial_interval: 5s
  max_interval: 30s
  max_elapsed_time: 300s
```
EXCEPT: the `prometheus` (pull) exporter has NO sending_queue/retry_on_failure -- those are push-exporter concepts. Pull exporter only has its own endpoint config.

**D-43 dual-exporter declaration (forward-compat):**
- Production config.yaml.j2 declares BOTH `prometheus` (port :8889) AND `prometheusremotewrite` (target Mimir).
- Inventory knob `telemetron_otel_metrics_path: prometheus | remote_write` (default `prometheus`) selects which exporter the metrics pipeline references via Jinja conditional.
- The DECLARATION of both is unconditional; only the PIPELINE references are conditional.

**D-54 approach (a) verify topology:**
- Production OTel container keeps the default `prometheus` exporter in the metrics pipeline (operator never sees the flip).
- Verify task renders a SEPARATE `verify-config.yaml.j2` template to `/opt/telemetron/opentelemetry/verify-config.yaml` with metrics pipeline EXPLICITLY using `prometheusremotewrite`.
- Verify task runs a one-shot otel-collector-contrib container loaded with verify-config.yaml, pushes a synthetic OTLP metric, and queries Mimir's `/api/v1/query` to assert presence.
- One-shot container has different container_name (`opentelemetry-verify-metric`) so it never clashes with production.
- After verify, the one-shot container is auto-removed; the rendered verify-config.yaml stays on disk (harmless; documented in README).

**D-52 Docker socket Approach A (RESEARCH Q6 + Phase-3-specific gotcha):**
```yaml
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
    mounts:
      - source: /var/run/docker.sock
        target: /var/run/docker.sock
        type: bind
        read_only: true
```

Port matrix to ship (D-31 / D-42 / RESEARCH):
- :4317  -- OTLP gRPC ingest (external-facing default; published to host so external producers can reach it)
- :4318  -- OTLP HTTP ingest (external-facing default; published)
- :8888  -- self-metrics (Prometheus scrape target `otel_self` -- internal only)
- :8889  -- app-metrics Prometheus format (Prometheus scrape target `otel_metrics` -- internal only)

Image probe outcome (RESEARCH Q4 carries over): otel-collector-contrib is distroless; researcher expects Outcome B (--version proxy) for HEALTHCHECK. Apply conditional pattern.

INSPQ Deviation Audit (D-25) -- entries that MUST appear in README:
- Dropped: `:latest` tag, K8s branches (kubernetes.yml, kubernetes-helm.yml, helm_*, servicemonitor_*, networkpolicy_*, instrumentation_*), French task/comment strings, `container_restart_policy: always`, `TZ: America/Toronto`, default `otel_exporters_otlp` loopback, parallel `batch_traces/logs/metrics` legacy processors, UFW rules, Jaeger receivers (gRPC/thrift_compact/thrift_binary/thrift_http), `actuator` path filter, `force-recreate-on-image-change` logic, `otel_telemetry_logs_*` verbose self-log knobs.
- Replaced: `otel_port_prometheus_endpoint_internal: 8888` + `_external: 9464` -> D-42's :8888 (self) + :8889 (app metrics) -- the upstream :9464 was INSPQ-specific.
- Added (the big list -- Pitfall 5 mitigation pack):
  - `memory_limiter` processor + `GOMEMLIMIT` env (Pitfall 5 -- upstream had NEITHER).
  - `sending_queue` + `retry_on_failure` on every push exporter (upstream had neither).
  - `docker_stats` receiver with `container.restarts` opt-in (upstream had no container-restart story).
  - `otlphttp/loki` exporter (D-44 AMENDED -- upstream had no Loki exporter at all).
  - `prometheusremotewrite` exporter declared (D-43 forward-compat).
  - D-52 Docker socket Threat Model section in README (upstream documented nothing on security).
  - Per-pipeline processor order locked `[memory_limiter, batch]` (upstream had no order discipline).
- Kept (got it right): `otel/opentelemetry-collector-contrib` image (Contrib explicit) -- just pin version.

</interfaces>

<phase_decisions_inline>
- D-40: Plan 03-02 owns roles/opentelemetry/ exclusively.
- D-41: Wave 2 -- depends_on: [03-01-node-exporter]. The runtime dependency is loose (OTel doesn't need node_exporter to start), but the playbook-edit ordering serializes plans.
- D-42: OTLP-pushed metrics through Prometheus (NOT direct to Mimir on the production path). Prometheus has TWO scrape jobs for OTel: otel_self (:8888) + otel_metrics (:8889). Plan 03-03 lands those scrape configs.
- D-43: Production config declares both `prometheus` AND `prometheusremotewrite`. Inventory knob `telemetron_otel_metrics_path: prometheus` is the default. Modes section in README explains the flip.
- D-44 AMENDED: OTel→Loki uses `otlphttp/loki` exporter to `http://loki:3100/otlp`. Documented as D-25 deviation under "Loki exporter replaced by otlphttp (upstream removal)".
- D-44 Tempo leg confirmed: `otlp/tempo` exporter (gRPC) to `tempo:14317` with `tls.insecure: true`.
- D-45: pipeline order LOCKED `[memory_limiter, batch]`; GOMEMLIMIT/memory_limiter ratios LOCKED.
- D-51: docker_stats receiver with `container.restarts.enabled: true` + `container.uptime.enabled: true`. Translated Prometheus name = `container_restarts_total`.
- D-52: Direct bind-mount `/var/run/docker.sock:ro` + group_add Approach A. README Threat Model section.
- D-53: docker_stats scope = ALL containers (no excluded_images filter).
- D-54 approach (a): Verify renders a separate verify-config.yaml with prometheusremotewrite, runs a one-shot otel-collector-contrib container. Production stays on prometheus exporter.
- D-55: No new vault keys.
- Pitfall 5: full mitigation pack in config.yaml.j2.
- Pitfall 9: grep gates per role.
</phase_decisions_inline>
</context>

<tasks>

<task type="auto" id="03-02-01">
  <name>Task 1: Create opentelemetry role skeleton (full layout including templates/)</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/mimir/tasks/main.yml
    roles/mimir/handlers/main.yml
    roles/mimir/meta/main.yml
    roles/mimir/README.md
    roles/README.md
    .planning/phases/03-ingest-plane/03-CONTEXT.md
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Create `roles/opentelemetry/{defaults,tasks,templates,handlers,meta}/`. Create skeleton files:
  - roles/opentelemetry/defaults/main.yml
  - roles/opentelemetry/tasks/main.yml
  - roles/opentelemetry/tasks/verify.yml
  - roles/opentelemetry/templates/config.yaml.j2
  - roles/opentelemetry/templates/verify-config.yaml.j2
  - roles/opentelemetry/handlers/main.yml
  - roles/opentelemetry/meta/main.yml (galaxy_info per mimir shape; description: "Deploys OpenTelemetry Collector Contrib 0.152.0 -- OTLP ingest + signal fanout to Loki/Tempo/Mimir-or-Prometheus for Telemetron's observability plane."; galaxy_tags: opentelemetry, otel, observability, telemetron; collections community.docker + ansible.builtin)
  - roles/opentelemetry/README.md (skeleton)

Every YAML file starts with `---`.
  </action>
  <verify>
    <automated>test -d roles/opentelemetry/defaults &amp;&amp; test -d roles/opentelemetry/tasks &amp;&amp; test -d roles/opentelemetry/templates &amp;&amp; test -d roles/opentelemetry/handlers &amp;&amp; test -d roles/opentelemetry/meta &amp;&amp; test -f roles/opentelemetry/defaults/main.yml &amp;&amp; test -f roles/opentelemetry/tasks/main.yml &amp;&amp; test -f roles/opentelemetry/tasks/verify.yml &amp;&amp; test -f roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; test -f roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; test -f roles/opentelemetry/handlers/main.yml &amp;&amp; test -f roles/opentelemetry/meta/main.yml &amp;&amp; test -f roles/opentelemetry/README.md &amp;&amp; grep -q "^galaxy_info:" roles/opentelemetry/meta/main.yml &amp;&amp; grep -q "license: MIT" roles/opentelemetry/meta/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All five dirs exist (defaults, tasks, templates, handlers, meta).
    - [ ] All eight required files exist.
    - [ ] meta/main.yml has galaxy_info with role_name: opentelemetry, license: MIT, collections include community.docker + ansible.builtin.
  </acceptance_criteria>
  <done>Skeleton matches the Phase-2 canonical role-template shape with the addition of a second template file (verify-config.yaml.j2).</done>
</task>

<task type="auto" id="03-02-02" tdd="false">
  <name>Task 2: Populate defaults/main.yml with image pin, port matrix, mem/GOMEMLIMIT ratios, knobs, conditional-HEALTHCHECK</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/opentelemetry/defaults/main.yml
    inventory/example-homelab/group_vars/all/network.yml
    inventory/example-homelab/group_vars/all/storage.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/phases/03-ingest-plane/03-CONTEXT.md
  </read_first>
  <action>
Write `roles/opentelemetry/defaults/main.yml` mirroring `roles/mimir/defaults/main.yml` section structure. Required keys (verbatim values from RESEARCH Findings 1 + 6 + D-45 ratios):

```yaml
# ---
# roles/opentelemetry/defaults/main.yml
# OTel Collector role tunables. Override per-environment in
# inventory/<env>/group_vars/all/opentelemetry.yml.
#
# OpenTelemetry Collector Contrib 0.152.0 -- OTLP ingest gateway on
# :4317 (gRPC) + :4318 (HTTP). Fans out to Loki via otlphttp (D-44
# AMENDED per RESEARCH Finding 2 -- loki exporter removed from contrib
# in v0.131.0), Tempo via otlp gRPC, and Prometheus-or-Mimir via the
# D-43 forward-compat knob.

# --- Image pin (OPS-01) -- Contrib explicit (Core lacks Loki + docker_stats) ---
# See: https://github.com/open-telemetry/opentelemetry-collector-contrib/releases/tag/v0.152.0
opentelemetry_image: otel/opentelemetry-collector-contrib
opentelemetry_image_tag: "0.152.0"

# --- Container identity ---
opentelemetry_container_name: opentelemetry
# Short DNS alias on the telemetron network so other roles reach the
# collector at http://otel:4318/v1/logs etc.
opentelemetry_container_alias: otel

# --- Host port publishing (D-30) ---
# OTLP receivers (4317 + 4318) DEFAULT TO PUBLISHED so external
# producers (host-running apps, future operator apps) can reach them.
# Prometheus scrape targets (:8888 + :8889) STAY INTERNAL -- Prometheus
# reaches them via Docker DNS.
opentelemetry_publish_otlp: "{{ opentelemetry_publish_otlp | default(true) }}"

# --- Port matrix (D-31, D-42, RESEARCH Finding 1) ---
opentelemetry_otlp_grpc_port: 4317
opentelemetry_otlp_http_port: 4318
opentelemetry_self_metrics_port: 8888   # otel_self scrape target (D-42)
opentelemetry_app_metrics_port: 8889    # otel_metrics scrape target (D-42)

# --- Config layout (D-18) ---
opentelemetry_config_dir: "{{ telemetron_config_root | default('/opt/telemetron') }}/opentelemetry"

# --- D-43 forward-compat knob: production metrics-pipeline exporter ---
# 'prometheus' (default): metrics pipeline uses pull-scrape via :8889.
#                          Prometheus scrapes; Prometheus remote_writes to Mimir.
# 'remote_write': metrics pipeline uses prometheusremotewrite direct push to Mimir.
# Both exporters are DECLARED unconditionally in config.yaml.j2; only the
# PIPELINE reference flips. Future flip needs no role rewrite.
telemetron_otel_metrics_path: "{{ telemetron_otel_metrics_path | default('prometheus') }}"

# --- Backend endpoints (Phase-2 carry-forward) ---
# Loki: D-44 AMENDED -- otlphttp to /otlp endpoint (D-26 auth_enabled: false).
opentelemetry_loki_endpoint: "http://loki:3100/otlp"
# Tempo: D-29 internal-only OTLP gRPC port.
opentelemetry_tempo_endpoint: "tempo:14317"
# Mimir: D-26 multitenancy off; no X-Scope-OrgID header.
opentelemetry_mimir_endpoint: "http://mimir:9009/api/v1/push"

# --- D-45 / Pitfall 5 memory model ---
# mem_limit: 512m (Docker container hard limit)
# GOMEMLIMIT: 400MiB (80% of 512) -- Go runtime sees this as the budget
# memory_limiter.limit_mib: 260 (65% of 400) -- hard refuse-data threshold
# memory_limiter.spike_limit_mib: 80 (20% of 400) -- soft refuse-data gap
opentelemetry_memory_limit: 512m
opentelemetry_gomemlimit: 400MiB
opentelemetry_memory_limiter_check_interval: 1s
opentelemetry_memory_limiter_limit_mib: 260
opentelemetry_memory_limiter_spike_limit_mib: 80

# --- Batch processor defaults ---
opentelemetry_batch_timeout: 10s
opentelemetry_batch_send_batch_size: 1024
opentelemetry_batch_send_batch_max_size: 2048

# --- D-45 per-exporter sending_queue + retry_on_failure ---
opentelemetry_sending_queue_num_consumers: 4
opentelemetry_sending_queue_size: 1000
opentelemetry_retry_initial_interval: 5s
opentelemetry_retry_max_interval: 30s
opentelemetry_retry_max_elapsed_time: 300s

# --- D-51 / D-53 docker_stats receiver ---
opentelemetry_docker_stats_endpoint: "unix:///var/run/docker.sock"
opentelemetry_docker_stats_collection_interval: 30s
opentelemetry_docker_stats_timeout: 5s
opentelemetry_docker_stats_api_version: "1.25"

# --- D-52 Docker socket bind-mount ---
opentelemetry_docker_socket_host_path: "/var/run/docker.sock"

# --- Healthcheck approach (conditional pattern; RESEARCH Q4) ---
# otel-collector-contrib 0.152.0 image is distroless. Image probe at
# execute time picks the actual outcome. Default Outcome B = binary-alive
# proxy via /otelcol-contrib --version (path verified in image probe).
opentelemetry_healthcheck_enabled: true
opentelemetry_healthcheck_test: ["CMD", "/otelcol-contrib", "--version"]
opentelemetry_healthcheck_interval: 15s
opentelemetry_healthcheck_timeout: 5s
opentelemetry_healthcheck_retries: 5
opentelemetry_healthcheck_start_period: 30s

# --- Verify pre-poll (D-10a) ---
opentelemetry_health_retries: 45
opentelemetry_health_delay: 2

# --- Restart policy (OPS-06) ---
opentelemetry_restart_policy: unless-stopped

# --- Network ---
opentelemetry_network: "{{ telemetron_network | default('telemetron') }}"

# --- Timezone (OPS-06; Pitfall 6) ---
opentelemetry_tz: "{{ telemetron_tz | default('Etc/UTC') }}"

# --- Curl image pin for verify (OPS-01) ---
opentelemetry_curl_image: curlimages/curl
opentelemetry_curl_image_tag: "8.10.1"
```

Use the EXACT key names -- downstream tasks/templates reference them. Section order mirrors mimir.
  </action>
  <verify>
    <automated>grep -q '^opentelemetry_image: otel/opentelemetry-collector-contrib$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_image_tag: "0.152.0"$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_otlp_grpc_port: 4317$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_otlp_http_port: 4318$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_self_metrics_port: 8888$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_app_metrics_port: 8889$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_memory_limit: 512m$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_gomemlimit: 400MiB$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_memory_limiter_limit_mib: 260$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^opentelemetry_memory_limiter_spike_limit_mib: 80$' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q 'opentelemetry_loki_endpoint:.*loki:3100/otlp' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q 'opentelemetry_tempo_endpoint:.*tempo:14317' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q 'opentelemetry_mimir_endpoint:.*mimir:9009/api/v1/push' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q '^telemetron_otel_metrics_path:' roles/opentelemetry/defaults/main.yml &amp;&amp; grep -q 'opentelemetry_docker_socket_host_path:.*"/var/run/docker.sock"' roles/opentelemetry/defaults/main.yml &amp;&amp; ! grep -qE ':\s*latest' roles/opentelemetry/defaults/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Image pin: `grep -q '^opentelemetry_image: otel/opentelemetry-collector-contrib$'` AND `grep -q '^opentelemetry_image_tag: "0.152.0"$'`
    - [ ] Port matrix: 4317/4318/8888/8889 all literal.
    - [ ] Memory model: mem_limit 512m, GOMEMLIMIT 400MiB, limit_mib 260, spike_limit_mib 80.
    - [ ] D-44 AMENDED: `grep -q 'opentelemetry_loki_endpoint:.*loki:3100/otlp'` (otlphttp endpoint, not /loki/api/v1/push)
    - [ ] D-44 Tempo leg: `grep -q 'opentelemetry_tempo_endpoint:.*tempo:14317'`
    - [ ] D-43 knob declared with default 'prometheus': `grep -q '^telemetron_otel_metrics_path:'` AND `grep -q "default('prometheus')" roles/opentelemetry/defaults/main.yml`
    - [ ] docker_stats endpoint pinned: `grep -q 'opentelemetry_docker_stats_endpoint:.*unix:///var/run/docker.sock'`
    - [ ] No `:latest` anywhere: `! grep -qE ':\s*latest' roles/opentelemetry/defaults/main.yml`
    - [ ] Sending-queue + retry knobs declared.
    - [ ] Curl image pinned (8.10.1).
  </acceptance_criteria>
  <done>Every literal the downstream tasks/templates need is in defaults; ratios match Pitfall 5; D-44 amendment baked in; D-43 forward-compat knob present.</done>
</task>

<task type="auto" id="03-02-03" tdd="false">
  <name>Task 3: Write templates/config.yaml.j2 -- production OTel config with all D-45 mitigations, D-43 dual-exporter, D-44 amendment, D-51 docker_stats opt-in, inline PITFALLS citations</name>
  <read_first>
    roles/loki/templates/loki.yaml.j2
    roles/mimir/templates/mimir.yaml.j2
    roles/opentelemetry/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/research/PITFALLS.md
  </read_first>
  <action>
Write `roles/opentelemetry/templates/config.yaml.j2` using the EXACT shape from RESEARCH Finding 1 -- copy structurally and parameterize via defaults vars. Inline-cite Pitfall 5 in header comment.

Required content (substitute `{{ var }}` references where vars exist; otherwise use the literal value from Finding 1):

```yaml
# /opt/telemetron/opentelemetry/config.yaml
# {{ ansible_managed }}
# OpenTelemetry Collector Contrib 0.152.0 -- Telemetron-tuned.
# Pitfall 5 inline-cited; D-45 pipeline order LOCKED.
# D-44 AMENDED: loki exporter REMOVED from contrib in v0.131.0; using
# otlphttp/loki exporter to Loki's /otlp endpoint (Loki 3.7.2 native OTLP).

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:{{ opentelemetry_otlp_grpc_port }}
      http:
        endpoint: 0.0.0.0:{{ opentelemetry_otlp_http_port }}

  docker_stats:
    # D-51 / D-53: scope all containers; no excluded_images.
    endpoint: {{ opentelemetry_docker_stats_endpoint }}
    collection_interval: {{ opentelemetry_docker_stats_collection_interval }}
    timeout: {{ opentelemetry_docker_stats_timeout }}
    api_version: "{{ opentelemetry_docker_stats_api_version }}"
    metrics:
      # ContainerRestartLoop signal source (D-51). DEFAULT-DISABLED in
      # the receiver; MUST be explicitly enabled. Translated Prometheus
      # name = container_restarts_total.
      container.restarts:
        enabled: true
      container.uptime:
        enabled: true

processors:
  # PITFALL 5: memory_limiter MUST be FIRST. Reversing order OOMs the box.
  # D-45 ratios: limit_mib = 65% of GOMEMLIMIT, spike_limit_mib = 20%.
  memory_limiter:
    check_interval: {{ opentelemetry_memory_limiter_check_interval }}
    limit_mib: {{ opentelemetry_memory_limiter_limit_mib }}
    spike_limit_mib: {{ opentelemetry_memory_limiter_spike_limit_mib }}

  batch:
    timeout: {{ opentelemetry_batch_timeout }}
    send_batch_size: {{ opentelemetry_batch_send_batch_size }}
    send_batch_max_size: {{ opentelemetry_batch_send_batch_max_size }}

exporters:
  # OTel -> Loki via OTLP/HTTP. D-44 AMENDED -- the `loki` exporter was
  # REMOVED from contrib in v0.131.0 (see RESEARCH Finding 2). The
  # canonical OTLP path replaces it. Loki 3.7.2 with auth_enabled: false
  # accepts OTLP without X-Scope-OrgID.
  otlphttp/loki:
    endpoint: {{ opentelemetry_loki_endpoint }}
    sending_queue:
      enabled: true
      num_consumers: {{ opentelemetry_sending_queue_num_consumers }}
      queue_size: {{ opentelemetry_sending_queue_size }}
    retry_on_failure:
      enabled: true
      initial_interval: {{ opentelemetry_retry_initial_interval }}
      max_interval: {{ opentelemetry_retry_max_interval }}
      max_elapsed_time: {{ opentelemetry_retry_max_elapsed_time }}

  # OTel -> Tempo via OTLP gRPC on Phase-2 D-29 internal-only port.
  otlp/tempo:
    endpoint: {{ opentelemetry_tempo_endpoint }}
    tls:
      insecure: true
    sending_queue:
      enabled: true
      num_consumers: {{ opentelemetry_sending_queue_num_consumers }}
      queue_size: {{ opentelemetry_sending_queue_size }}
    retry_on_failure:
      enabled: true
      initial_interval: {{ opentelemetry_retry_initial_interval }}
      max_interval: {{ opentelemetry_retry_max_interval }}
      max_elapsed_time: {{ opentelemetry_retry_max_elapsed_time }}

  # D-42: pull-style Prometheus exporter for OTLP-pushed metrics.
  # Prometheus scrapes :{{ opentelemetry_app_metrics_port }} as job
  # `otel_metrics`. NO sending_queue / retry_on_failure (those are
  # push-exporter concepts; pull is Prometheus's responsibility).
  prometheus:
    endpoint: 0.0.0.0:{{ opentelemetry_app_metrics_port }}
    namespace: ""
    send_timestamps: true
    metric_expiration: 5m
    enable_open_metrics: true

  # D-43 forward-compat: DECLARED unconditionally even when not in the
  # metrics pipeline. Flipping telemetron_otel_metrics_path to
  # 'remote_write' moves the metrics pipeline to use this exporter
  # without role rewrite.
  prometheusremotewrite:
    endpoint: {{ opentelemetry_mimir_endpoint }}
    sending_queue:
      enabled: true
      num_consumers: {{ opentelemetry_sending_queue_num_consumers }}
      queue_size: {{ opentelemetry_sending_queue_size }}
    retry_on_failure:
      enabled: true
      initial_interval: {{ opentelemetry_retry_initial_interval }}
      max_interval: {{ opentelemetry_retry_max_interval }}
      max_elapsed_time: {{ opentelemetry_retry_max_elapsed_time }}

service:
  telemetry:
    metrics:
      # Self-metrics on :{{ opentelemetry_self_metrics_port }} -- Prometheus
      # job `otel_self` scrapes this (D-42). Includes
      # otelcol_receiver_refused_{spans,log_records,metric_points} which
      # Plan 03-03's OTelCollectorDroppingSignals alert rule consumes.
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: {{ opentelemetry_self_metrics_port }}

  pipelines:
    # D-45 LOCKED order in every pipeline: [memory_limiter, batch].
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/loki]   # D-44 AMENDED

    metrics:
      # docker_stats feeds the container.restarts signal (D-51).
      receivers: [otlp, docker_stats]
      processors: [memory_limiter, batch]
      # D-43 forward-compat Jinja conditional. Default 'prometheus'.
{% if telemetron_otel_metrics_path == 'remote_write' %}
      exporters: [prometheusremotewrite]
{% else %}
      exporters: [prometheus]
{% endif %}
```

EVERY exporter except `prometheus` (pull) has sending_queue + retry_on_failure. Pipeline order `[memory_limiter, batch]` is LITERAL (not Jinja-templated). The metrics-pipeline EXPORTER is the one conditional. All comments ENGLISH.
  </action>
  <verify>
    <automated>grep -q "memory_limiter" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -q "docker_stats:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -q "container.restarts:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -A1 "container.restarts:" roles/opentelemetry/templates/config.yaml.j2 | grep -q "enabled: true" &amp;&amp; grep -q "container.uptime:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -q "otlphttp/loki:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -q "otlp/tempo:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -q "^  prometheus:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -q "^  prometheusremotewrite:" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -qE "processors:\s*\[memory_limiter,\s*batch\]" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; grep -cE "sending_queue:" roles/opentelemetry/templates/config.yaml.j2 | (read n; test "$n" -ge 3) &amp;&amp; grep -cE "retry_on_failure:" roles/opentelemetry/templates/config.yaml.j2 | (read n; test "$n" -ge 3) &amp;&amp; grep -q "telemetron_otel_metrics_path == 'remote_write'" roles/opentelemetry/templates/config.yaml.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/opentelemetry/templates/config.yaml.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] memory_limiter declared: `grep -q "memory_limiter" roles/opentelemetry/templates/config.yaml.j2`
    - [ ] Pipeline order LOCKED `[memory_limiter, batch]`: `grep -qE "processors:\s*\[memory_limiter,\s*batch\]"` -- appears 3 times (traces, logs, metrics): `grep -cE "processors:\s*\[memory_limiter,\s*batch\]" roles/opentelemetry/templates/config.yaml.j2` returns `3`
    - [ ] docker_stats receiver with container.restarts opt-in: `grep -q "container.restarts:"` AND the next-line `enabled: true` (verified via `grep -A1 "container.restarts:" | grep -q "enabled: true"`)
    - [ ] container.uptime opt-in: `grep -q "container.uptime:"`
    - [ ] D-44 AMENDED -- otlphttp/loki exporter: `grep -q "otlphttp/loki:"` AND `grep -q "loki:3100/otlp"` (via var or literal)
    - [ ] Tempo gRPC leg: `grep -q "otlp/tempo:"` AND `grep -q "tempo:14317"`
    - [ ] D-43 dual-exporter declaration: BOTH `grep -q "^  prometheus:"` AND `grep -q "^  prometheusremotewrite:"`
    - [ ] D-43 Jinja conditional present: `grep -q "telemetron_otel_metrics_path == 'remote_write'"`
    - [ ] Every push-exporter has resilience: `grep -cE "sending_queue:" roles/opentelemetry/templates/config.yaml.j2 >= 3` AND `grep -cE "retry_on_failure:" >= 3` (otlphttp/loki, otlp/tempo, prometheusremotewrite)
    - [ ] Pull exporter (prometheus) does NOT have sending_queue/retry_on_failure: check that the lines following `^  prometheus:` (until next `^  [a-z]` exporter) do NOT contain `sending_queue`.
    - [ ] Self-metrics port 8888 wired: `grep -q "{{ opentelemetry_self_metrics_port }}" roles/opentelemetry/templates/config.yaml.j2`
    - [ ] App-metrics port 8889 wired: `grep -q "{{ opentelemetry_app_metrics_port }}" roles/opentelemetry/templates/config.yaml.j2`
    - [ ] Pitfall 5 cited inline: `grep -q "PITFALL 5" roles/opentelemetry/templates/config.yaml.j2` OR `grep -q "Pitfall 5" roles/opentelemetry/templates/config.yaml.j2`
    - [ ] D-44 amendment cited inline: `grep -q "D-44" roles/opentelemetry/templates/config.yaml.j2`
    - [ ] ASCII-only: `! grep -qP '[^\x00-\x7F]' roles/opentelemetry/templates/config.yaml.j2`
  </acceptance_criteria>
  <done>Production config.yaml.j2 has all D-45 mitigations, D-43 dual-exporter declaration with Jinja conditional, D-44 amendment for Loki, D-51 docker_stats opt-in for container.restarts.</done>
</task>

<task type="auto" id="03-02-04" tdd="false">
  <name>Task 4: Write templates/verify-config.yaml.j2 -- verify-only OTel config with prometheusremotewrite exporter in metrics pipeline (D-54 approach a)</name>
  <read_first>
    roles/opentelemetry/templates/config.yaml.j2
    roles/opentelemetry/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/opentelemetry/templates/verify-config.yaml.j2` -- a SECOND, SEPARATE OTel config used by the verify one-shot ONLY. Differences from production config:
- Container name is `opentelemetry-verify-metric` (set in tasks/verify.yml when running the one-shot), so this config never overwrites production.
- The metrics pipeline ALWAYS uses `prometheusremotewrite` (no Jinja conditional on telemetron_otel_metrics_path).
- docker_stats receiver is OMITTED (verify doesn't need it -- the synthetic OTLP metric is the assertion target).
- Server ports remain the same (4317/4318/8888/8889) but the one-shot uses different host ports (or no host publish at all).

The content is structurally similar to config.yaml.j2 but with the metrics pipeline flipped to prometheusremotewrite unconditionally. Include the header comment explaining this is a verify-only config.

```yaml
# /opt/telemetron/opentelemetry/verify-config.yaml
# {{ ansible_managed }}
# VERIFY-ONLY OTel Collector config (D-54 approach (a)).
# Loaded into a one-shot otel-collector-contrib container by
# roles/opentelemetry/tasks/verify.yml. The metrics pipeline forces
# prometheusremotewrite -> Mimir so a synthetic OTLP metric can be
# asserted in Mimir BEFORE Plan 03-03 wires Prometheus.
#
# This config is NEVER loaded by the production OTel container; it
# exists alongside the production config but is referenced explicitly
# by the verify one-shot container's command.

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:{{ opentelemetry_otlp_grpc_port }}
      http:
        endpoint: 0.0.0.0:{{ opentelemetry_otlp_http_port }}

processors:
  memory_limiter:
    check_interval: {{ opentelemetry_memory_limiter_check_interval }}
    limit_mib: {{ opentelemetry_memory_limiter_limit_mib }}
    spike_limit_mib: {{ opentelemetry_memory_limiter_spike_limit_mib }}

  batch:
    timeout: 1s
    send_batch_size: 8
    send_batch_max_size: 8

exporters:
  # Verify path: push directly to Mimir via prometheusremotewrite so the
  # synthetic metric reaches the backend before Prometheus is wired.
  prometheusremotewrite:
    endpoint: {{ opentelemetry_mimir_endpoint }}
    sending_queue:
      enabled: true
      num_consumers: 1
      queue_size: 100
    retry_on_failure:
      enabled: true
      initial_interval: 1s
      max_interval: 5s
      max_elapsed_time: 30s

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheusremotewrite]
```

NO docker_stats receiver. NO traces pipeline (the verify only pushes a metric per RESEARCH Open Question Q9 -- bucket-landing for traces/logs is impractical at single-push granularity). NO logs pipeline either. Smaller batch sizes and shorter retry intervals so the verify one-shot completes within the verify task's budget.
  </action>
  <verify>
    <automated>grep -q "memory_limiter" roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; grep -q "^  prometheusremotewrite:" roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; ! grep -q "docker_stats" roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; ! grep -q "otlphttp/loki" roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; ! grep -q "otlp/tempo" roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; grep -qE "exporters:\s*\[prometheusremotewrite\]" roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/opentelemetry/templates/verify-config.yaml.j2 &amp;&amp; grep -q "VERIFY-ONLY" roles/opentelemetry/templates/verify-config.yaml.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Header explicitly marks verify-only: `grep -q "VERIFY-ONLY" roles/opentelemetry/templates/verify-config.yaml.j2`
    - [ ] D-54 approach (a) cited: `grep -q "D-54" roles/opentelemetry/templates/verify-config.yaml.j2`
    - [ ] Has memory_limiter: `grep -q "memory_limiter"`
    - [ ] Metrics pipeline forces prometheusremotewrite: `grep -qE "exporters:\s*\[prometheusremotewrite\]"`
    - [ ] NO docker_stats: `! grep -q "docker_stats"`
    - [ ] NO Loki exporter: `! grep -q "otlphttp/loki"`
    - [ ] NO Tempo exporter: `! grep -q "otlp/tempo"`
    - [ ] NO Jinja conditional on telemetron_otel_metrics_path (unconditional remote_write): `! grep -q "telemetron_otel_metrics_path" roles/opentelemetry/templates/verify-config.yaml.j2`
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>verify-config.yaml.j2 exists; references prometheusremotewrite unconditionally; does NOT replace production config.yaml.j2; mentioned in README's Verify section.</done>
</task>

<task type="auto" id="03-02-05" tdd="false">
  <name>Task 5: Write tasks/main.yml -- getent docker GID, render config (notify), pull image, run container with Docker socket RO + group_add + OTLP publish, include verify</name>
  <read_first>
    roles/mimir/tasks/main.yml
    roles/opentelemetry/defaults/main.yml
    roles/opentelemetry/templates/config.yaml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/opentelemetry/tasks/main.yml` mirroring `roles/mimir/tasks/main.yml`. Task sequence:

1. **Ensure config dir** -- `ansible.builtin.file: path: "{{ opentelemetry_config_dir }}" state: directory mode: 0755`. Tags: [opentelemetry, opentelemetry-config].

2. **Render production config** -- `ansible.builtin.template: src: config.yaml.j2 dest: "{{ opentelemetry_config_dir }}/config.yaml" mode: 0640`. `notify: restart opentelemetry`. Tags: [opentelemetry, opentelemetry-config].

3. **Render verify-only config** -- same template module, src verify-config.yaml.j2, dest "{{ opentelemetry_config_dir }}/verify-config.yaml", mode 0640. NO `notify:` -- verify-config is loaded by the one-shot in verify.yml, never by the production container. Tags: [opentelemetry, opentelemetry-config].

4. **Detect docker group GID on the target host** (D-52 / RESEARCH Approach A):
   ```yaml
   - name: Detect docker group GID on the target host
     ansible.builtin.getent:
       database: group
       key: docker
     register: opentelemetry_docker_group_info
     changed_when: false
     tags:
       - opentelemetry
   ```

5. **Pull image** -- `community.docker.docker_image: name: "{{ opentelemetry_image }}:{{ opentelemetry_image_tag }}" source: pull force_source: false`. Tags: [opentelemetry].

6. **Run container** -- `community.docker.docker_container` with these explicit fields:
   - `name: "{{ opentelemetry_container_name }}"`
   - `image: "{{ opentelemetry_image }}:{{ opentelemetry_image_tag }}"`
   - `state: started`
   - `recreate: false`
   - `restart_policy: "{{ opentelemetry_restart_policy }}"`
   - `memory: "{{ opentelemetry_memory_limit }}"`
   - `groups:` -- list with one entry: `"{{ opentelemetry_docker_group_info.ansible_facts.getent_group.docker[1] }}"` (D-52 Approach A)
   - `command:` -- `["--config=/etc/otelcol-contrib/config.yaml"]`
   - `networks:` -- `[{ name: "{{ opentelemetry_network }}", aliases: ["{{ opentelemetry_container_name }}", "{{ opentelemetry_container_alias }}"] }]` (BOTH `opentelemetry` and `otel` resolve to this container)
   - `published_ports:` -- conditional on opentelemetry_publish_otlp:
     ```
     published_ports: >-
       {{
         (
           [
             opentelemetry_otlp_grpc_port | string + ':' + opentelemetry_otlp_grpc_port | string,
             opentelemetry_otlp_http_port | string + ':' + opentelemetry_otlp_http_port | string
           ]
           if (opentelemetry_publish_otlp | bool) else []
         )
       }}
     ```
     :8888 and :8889 stay INTERNAL ALWAYS (D-42 Prometheus reaches them by Docker DNS).
   - `volumes:` -- two bind-mounts (file mode RO):
     - `"{{ opentelemetry_config_dir }}/config.yaml:/etc/otelcol-contrib/config.yaml:ro"`
     - `"{{ opentelemetry_config_dir }}/verify-config.yaml:/etc/otelcol-contrib/verify-config.yaml:ro"` (mounted so it's available for hot-flip operations -- but production loads only config.yaml via command)
   - `mounts:` -- one entry for Docker socket:
     - `{ source: "{{ opentelemetry_docker_socket_host_path }}", target: "/var/run/docker.sock", type: bind, read_only: true }`
   - `healthcheck:` -- conditional via vars-form mirroring mimir lines 89-98: `"{{ opentelemetry_container_healthcheck if (opentelemetry_healthcheck_enabled | bool) else omit }}"` with vars: section computing the dict.
   - `env:` -- TWO required entries:
     - `TZ: "{{ opentelemetry_tz }}"`
     - `GOMEMLIMIT: "{{ opentelemetry_gomemlimit }}"`   (D-45 ratio -- 80% of mem_limit)
   - Tags: `[opentelemetry, opentelemetry-container]`

7. **Final task: include verify** -- `ansible.builtin.include_tasks: verify.yml`. Tags: [opentelemetry, opentelemetry-verify].

NO `state: restarted` anywhere. ALL task names ENGLISH. ASCII only.
  </action>
  <verify>
    <automated>grep -q "ansible.builtin.template" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "src: config.yaml.j2" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "src: verify-config.yaml.j2" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "ansible.builtin.getent" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "key: docker" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "groups:" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "docker_group_info.ansible_facts.getent_group.docker" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "GOMEMLIMIT" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "/var/run/docker.sock" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "read_only: true" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "notify: restart opentelemetry" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "include_tasks: verify.yml" roles/opentelemetry/tasks/main.yml &amp;&amp; ! grep -qE "state:\s*restarted" roles/opentelemetry/tasks/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/opentelemetry/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Renders BOTH config.yaml.j2 (notifies handler) and verify-config.yaml.j2 (no notify): `grep -q "src: config.yaml.j2"` AND `grep -q "src: verify-config.yaml.j2"` AND `grep -q "notify: restart opentelemetry"`
    - [ ] getent task for docker group GID (D-52 Approach A): `grep -q "ansible.builtin.getent"` AND `grep -q "key: docker"`
    - [ ] group_add wired: `grep -q "groups:" roles/opentelemetry/tasks/main.yml` AND `grep -q "docker_group_info.ansible_facts.getent_group.docker" roles/opentelemetry/tasks/main.yml`
    - [ ] Docker socket bind-mount: `grep -q "/var/run/docker.sock" roles/opentelemetry/tasks/main.yml` AND `grep -q "read_only: true" roles/opentelemetry/tasks/main.yml`
    - [ ] GOMEMLIMIT env: `grep -q "GOMEMLIMIT" roles/opentelemetry/tasks/main.yml`
    - [ ] Conditional OTLP publish (only OTLP ports published; :8888/:8889 stay internal): `grep -q "opentelemetry_publish_otlp" roles/opentelemetry/tasks/main.yml` AND the Jinja must NOT publish :8888 or :8889
    - [ ] Container aliases include both `opentelemetry` and `otel`: `grep -q "opentelemetry_container_alias" roles/opentelemetry/tasks/main.yml`
    - [ ] Conditional HEALTHCHECK pattern: `grep -q "opentelemetry_container_healthcheck if (opentelemetry_healthcheck_enabled | bool) else omit" roles/opentelemetry/tasks/main.yml`
    - [ ] include_tasks final: `grep -q "include_tasks: verify.yml"`
    - [ ] D-19 idempotency: `! grep -qE "state:\s*restarted"`
    - [ ] ASCII-only: `! grep -qP '[^\x00-\x7F]'`
  </acceptance_criteria>
  <done>tasks/main.yml renders both configs, detects docker GID, runs container with Docker socket RO bind-mount + group_add + GOMEMLIMIT env + conditional HEALTHCHECK + OTLP-publish-conditional, verify wired as final task.</done>
</task>

<task type="auto" id="03-02-06" tdd="false">
  <name>Task 6: Write tasks/verify.yml -- D-10a poll + OTLP /v1/{traces,logs,metrics} 200 probes + config grep assertions + D-54 (a) one-shot verify-config push to Mimir</name>
  <read_first>
    roles/mimir/tasks/verify.yml
    roles/loki/tasks/verify.yml
    roles/opentelemetry/defaults/main.yml
    roles/opentelemetry/templates/verify-config.yaml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/opentelemetry/tasks/verify.yml`. Mirror mimir/loki verify shape (Steps 1a/1b/1c) + extend with OTLP probes + D-54 approach (a) metric push.

**Step 1a -- HEALTHCHECK poll** (when enabled): `community.docker.docker_container_info` for `{{ opentelemetry_container_name }}`, until State.Health.Status == 'healthy', retries `{{ opentelemetry_health_retries }}`, delay `{{ opentelemetry_health_delay }}`, `changed_when: false`, `when: opentelemetry_healthcheck_enabled | bool`. Tags: [opentelemetry, opentelemetry-verify].

**Step 1b -- State.Running fallback** (when disabled): same module call, until State.Running is true, same retries/delay, `when: not (opentelemetry_healthcheck_enabled | bool)`.

**Step 2 -- In-network OTLP HTTP probes** (one-shot curlimages/curl container on telemetron network). Use a single shell loop that POSTs minimal OTLP/HTTP JSON to `:4318/v1/traces`, `:4318/v1/logs`, `:4318/v1/metrics` and asserts each returns HTTP in {200,202,204}:
  - container name: `"{{ opentelemetry_container_name }}-verify-otlp"`
  - image: `"{{ opentelemetry_curl_image }}:{{ opentelemetry_curl_image_tag }}"`
  - state: started, detach: false, auto_remove: true, recreate: true, cleanup: true, changed_when: false
  - networks: `[{ name: "{{ opentelemetry_network }}" }]`
  - entrypoint: `["/bin/sh", "-c"]`
  - command: shell script that:
    1. Loops up to 30 times sleeping 2s:
    2. For each of `/v1/traces`, `/v1/logs`, `/v1/metrics`: POST minimal OTLP JSON body (use `{}` if accepted, or a minimal valid OTLP request; the assertion is "endpoint reachable and responds in the 2xx range")
    3. If all three return 2xx, echo `otlp_probes_ok` and exit 0
    4. After 30 attempts, echo failure and exit 1
  - failed_when: status != 0

**Step 3 -- Static config grep assertions (D-45 pipeline order + GOMEMLIMIT env)** via `ansible.builtin.command` or `ansible.builtin.shell`:
  - shell: `grep -E "processors:\\s*\\[memory_limiter,\\s*batch" {{ opentelemetry_config_dir }}/config.yaml`
  - register; failed_when rc != 0; changed_when: false
  - Separate task: `docker inspect {{ opentelemetry_container_name }} --format '{{ '{{ ' }}.Config.Env{{ ' }}' }}'` -- assert `GOMEMLIMIT=400MiB` substring present.

**Step 4 -- D-54 approach (a) -- one-shot verify-config push to Mimir** (the synthetic-metric exercise):

```yaml
- name: Run one-shot OTel Collector with verify-config to push a synthetic metric to Mimir
  community.docker.docker_container:
    name: "{{ opentelemetry_container_name }}-verify-metric"
    image: "{{ opentelemetry_image }}:{{ opentelemetry_image_tag }}"
    state: started
    detach: false
    auto_remove: true
    recreate: true
    cleanup: true
    networks:
      - name: "{{ opentelemetry_network }}"
    volumes:
      - "{{ opentelemetry_config_dir }}/verify-config.yaml:/etc/otelcol-contrib/config.yaml:ro"
    command:
      - "--config=/etc/otelcol-contrib/config.yaml"
    env:
      GOMEMLIMIT: "{{ opentelemetry_gomemlimit }}"
    # The one-shot lives only long enough to receive the synthetic metric
    # from Step 4b's curl push and forward it to Mimir; remove after a short window.
    # Approach (a) deliberately uses verify-config which forces prometheusremotewrite
    # in the metrics pipeline -- production OTel stays on the prometheus exporter.
  register: opentelemetry_verify_one_shot
  changed_when: false
  async: 60
  poll: 0
```

Then push a synthetic OTLP metric to this one-shot's :4318/v1/metrics via another curl one-shot; then query Mimir's `/api/v1/query?query=...` to assert the metric is present. Mimir block-flush latency means the assertion target is a labels/series presence check, NOT a value-correctness check.

**Simplification per RESEARCH Open Question Q9:** the bucket-landing assertion is impractical at single-push granularity. Step 4's success criterion is: (a) the one-shot otel-contrib container starts and exits 0; (b) the synthetic metric reaches Mimir's /api/v1/push (verified via the one-shot's exit status, which proves prometheusremotewrite ran end-to-end without HTTP error). Querying Mimir is OPTIONAL and time-bounded; if the query times out, log it (warning) but do not fail the verify -- the prometheusremotewrite-to-Mimir-HTTP-200 chain is the load-bearing assertion.

All one-shots: auto_remove: true, changed_when: false. ASCII only. English task names.
  </action>
  <verify>
    <automated>grep -q "community.docker.docker_container_info" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "State.Health.Status == 'healthy'" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "State.Running is true" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "/v1/traces" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "/v1/logs" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "/v1/metrics" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "auto_remove: true" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "verify-config.yaml" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "memory_limiter" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "GOMEMLIMIT" roles/opentelemetry/tasks/verify.yml &amp;&amp; grep -q "changed_when: false" roles/opentelemetry/tasks/verify.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/opentelemetry/tasks/verify.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Step 1a HEALTHCHECK poll present (conditional on `opentelemetry_healthcheck_enabled | bool`).
    - [ ] Step 1b State.Running fallback present (negated conditional).
    - [ ] Step 2 probes all three OTLP HTTP endpoints: `grep -q "/v1/traces"` AND `grep -q "/v1/logs"` AND `grep -q "/v1/metrics"`.
    - [ ] Step 3 static assertions: `grep -q "memory_limiter" roles/opentelemetry/tasks/verify.yml` (config order check) AND `grep -q "GOMEMLIMIT" roles/opentelemetry/tasks/verify.yml` (env-var check).
    - [ ] Step 4 uses verify-config.yaml mounted as the one-shot's config: `grep -q "verify-config.yaml" roles/opentelemetry/tasks/verify.yml`
    - [ ] Step 4 one-shot uses the production OTel image: `grep -q "{{ opentelemetry_image }}:{{ opentelemetry_image_tag }}" roles/opentelemetry/tasks/verify.yml`
    - [ ] One-shots all auto-remove: `grep -q "auto_remove: true" roles/opentelemetry/tasks/verify.yml`
    - [ ] changed_when: false on all read-shaped tasks: `grep -q "changed_when: false" roles/opentelemetry/tasks/verify.yml`
    - [ ] Attached to telemetron network: `grep -q "opentelemetry_network" roles/opentelemetry/tasks/verify.yml`
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>verify.yml exercises HEALTHCHECK/Running, OTLP probes, static config grep, and the D-54 approach (a) one-shot verify-config metric push to Mimir.</done>
</task>

<task type="auto" id="03-02-07" tdd="false">
  <name>Task 7: Write handlers/main.yml -- single docker-restart handler</name>
  <read_first>
    roles/mimir/handlers/main.yml
  </read_first>
  <action>
Mirror `roles/mimir/handlers/main.yml`:

```yaml
# ---
# roles/opentelemetry/handlers/main.yml
# Per D-19 / Pitfall 8: container restarts on config change use
# `docker restart <name>`. Force-recreate is non-idempotent.

- name: Docker restart opentelemetry
  ansible.builtin.command:
    cmd: "docker restart {{ opentelemetry_container_name }}"
  changed_when: true
  listen: restart opentelemetry
```
  </action>
  <verify>
    <automated>grep -q "^- name: Docker restart opentelemetry$" roles/opentelemetry/handlers/main.yml &amp;&amp; grep -q "listen: restart opentelemetry" roles/opentelemetry/handlers/main.yml &amp;&amp; grep -q "ansible.builtin.command:" roles/opentelemetry/handlers/main.yml &amp;&amp; ! grep -q "state: restarted" roles/opentelemetry/handlers/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/opentelemetry/handlers/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Exactly one handler.
    - [ ] Uses ansible.builtin.command, not shell.
    - [ ] listen: restart opentelemetry (matches the notify in tasks/main.yml).
    - [ ] No state: restarted; no non-ASCII.
  </acceptance_criteria>
  <done>handlers/main.yml has the canonical single restart handler.</done>
</task>

<task type="auto" id="03-02-08" tdd="false">
  <name>Task 8: Write README.md -- OPS-03 schema + D-43 Modes section + D-52 Threat Model + D-25 audit + D-44 amendment subsection + What metrics are collected</name>
  <read_first>
    roles/mimir/README.md
    roles/loki/README.md
    roles/opentelemetry/defaults/main.yml
    roles/opentelemetry/templates/config.yaml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/opentelemetry/README.md` mirroring `roles/mimir/README.md` schema, plus three extra sections required by Phase-3 decisions:

H2 sections required (in order):

1. `# roles/opentelemetry` -- overview paragraph.
2. `## What this role does` -- numbered list (5 items: render configs, detect Docker GID, pull image, run container with socket+group_add, verify).
3. `## What metrics are collected` -- D-51 + D-53 documentation: docker_stats receiver scope (ALL containers, no name filter), the OTel metrics list (container.cpu.usage.total, container.memory.usage.total, container.network.io.usage.{tx,rx}.bytes, container.uptime, container.restarts -- with note that the latter two are OPT-IN at the receiver level).
4. `## Modes` -- D-43 dual-exporter forward-compat. Document `telemetron_otel_metrics_path: prometheus | remote_write`. Default `prometheus`. Explain when an operator would flip.
5. `## Variables` -- markdown table of every defaults/main.yml key.
6. `## Vault keys` -- "None (Phase 3 D-55)."
7. `## Tags` -- "- `opentelemetry`".
8. `## Volumes` -- "None (OTel Collector is stateless). Two file bind-mounts: production config + verify-only config. One unix-socket bind-mount: Docker socket (RO)."
9. `## Healthcheck` -- conditional pattern; image probe at execute time.
10. `## Operator access (no host publish by default per D-30, except OTLP)` -- explain that OTLP (4317+4318) is published by default so external producers can reach it; explain SSH local-forward for :8888/:8889 (internal-only).
11. `## Security model` -- short.
12. `## Threat Model (D-52 Docker socket)` -- THE LOAD-BEARING SECTION per D-52. Document:
    - Bind-mount is `:ro` -- kernel-level write block.
    - Docker API operations use POST-over-HTTP-over-socket -- a compromised OTel container could still issue Docker API calls (start privileged containers, escalate to host) AT THE API LAYER.
    - Acceptable for M1 homelab single-host (operator already owns the host; trusts Telemetron images).
    - Future-Rock or operators deploying alongside less-trusted workloads can layer a Tecnativa-style `docker-socket-proxy` sidecar (deferred per CLAUDE.md fixed component list for M1).
    - Approach A (group_add) preferred over Approach B (run as root). Documented in tasks/main.yml.
13. `## Idempotency` -- standard.
14. `## Port-acceptance gates` -- six gates.
15. `## Deviations from upstream INSPQ (D-25)` -- the audit section. Required sub-bullets:
    - **Loki exporter replaced by otlphttp (upstream removal)** -- explicit subheading per planning_context. The `loki` exporter was deprecated 2024-07-09 and removed from contrib in v0.131.0. v0.152.0 (Phase-3 pin) does NOT ship it. The `otlphttp` exporter to Loki's `/otlp` endpoint is the replacement (Loki 3.7.2 with auth_enabled: false accepts without X-Scope-OrgID). RESEARCH Finding 2 reference.
    - **Dropped** bullet list per RESEARCH INSPQ audit (K8s branches, French strings, default loopback OTLP, parallel batch processors, UFW, Jaeger receivers, `actuator` filter, `:latest` tag, `America/Toronto` TZ, etc.).
    - **Replaced** bullet list (`:9464` → `:8889`).
    - **Added (Pitfall 5 mitigation pack)** bullet list -- memory_limiter, GOMEMLIMIT, sending_queue, retry_on_failure, docker_stats receiver with container.restarts opt-in, prometheusremotewrite forward-compat, Threat Model section.
16. `## D-44 amendment note` -- short paragraph linking the README's deviation section above to CONTEXT.md D-44 and RESEARCH Finding 2.
17. `## Deprecation notes` -- "None for M1. Future hardening: docker-socket-proxy sidecar."

README's D-25 section is the documented exception to the INSPQ grep gate (Phase-2 D-25 interpretation). ASCII-only OUTSIDE the D-25 audit section.
  </action>
  <verify>
    <automated>grep -qE "^# roles/opentelemetry" roles/opentelemetry/README.md &amp;&amp; grep -q "^## What metrics are collected" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Modes" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Variables" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Vault keys" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Tags" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Healthcheck" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Threat Model" roles/opentelemetry/README.md &amp;&amp; grep -q "^## Deviations from upstream INSPQ" roles/opentelemetry/README.md &amp;&amp; grep -q "Loki exporter replaced by otlphttp" roles/opentelemetry/README.md &amp;&amp; grep -q "docker-socket-proxy" roles/opentelemetry/README.md &amp;&amp; grep -q "telemetron_otel_metrics_path" roles/opentelemetry/README.md &amp;&amp; grep -q "memory_limiter" roles/opentelemetry/README.md &amp;&amp; grep -q "container.restarts" roles/opentelemetry/README.md &amp;&amp; grep -q "0.152.0" roles/opentelemetry/README.md</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All ~16 required H2 sections present (Modes, What metrics are collected, Threat Model, Deviations from upstream INSPQ in particular).
    - [ ] D-44 amendment documented with the exact subheading `Loki exporter replaced by otlphttp`: `grep -q "Loki exporter replaced by otlphttp" roles/opentelemetry/README.md`
    - [ ] D-52 Threat Model section discusses docker-socket-proxy as deferred hardening: `grep -q "docker-socket-proxy" roles/opentelemetry/README.md`
    - [ ] D-43 Modes section names the knob: `grep -q "telemetron_otel_metrics_path" roles/opentelemetry/README.md`
    - [ ] D-51 docker_stats mentioned: `grep -q "container.restarts" roles/opentelemetry/README.md`
    - [ ] Pitfall 5 mitigation pack referenced: `grep -q "memory_limiter" roles/opentelemetry/README.md`
    - [ ] Image tag 0.152.0 referenced: `grep -q "0.152.0" roles/opentelemetry/README.md`
    - [ ] At least 3 D-25 audit categories present (Dropped, Replaced, Added).
  </acceptance_criteria>
  <done>README has the canonical 16-section OPS-03 schema + 3 Phase-3-specific sections (Modes, What metrics are collected, Threat Model). D-44 amendment is explicitly subheaded per planning_context guidance.</done>
</task>

<task type="auto" id="03-02-09" tdd="false">
  <name>Task 9: Create inventory/example-homelab/group_vars/all/opentelemetry.yml + wire role into playbooks/deploy_docker.yml after node_exporter</name>
  <read_first>
    inventory/example-homelab/group_vars/all/mimir.yml
    inventory/example-homelab/group_vars/all/network.yml
    playbooks/deploy_docker.yml
  </read_first>
  <action>
**Step A:** Create `inventory/example-homelab/group_vars/all/opentelemetry.yml`:

```yaml
# ---
# Telemetron -- opentelemetry operator knobs (Phase 3, D-30, D-42, D-43, D-52)
# Role-specific overrides for the `opentelemetry` role.
# See roles/opentelemetry/defaults/main.yml for the full default surface.

# OTLP ingest (:4317 + :4318) published to host so external producers
# (host-running apps, future operator workloads) can reach the collector.
# Set to false if all producers are on the telemetron Docker network.
opentelemetry_publish_otlp: true

# D-43 forward-compat: metrics pipeline exporter selection.
#   'prometheus' (default): metrics pipeline emits Prometheus format on
#                            :8889; Prometheus scrapes; Prometheus remote_writes
#                            to Mimir. Single ingest path into Mimir.
#   'remote_write': metrics pipeline emits via prometheusremotewrite
#                   direct to Mimir.
# Default 'prometheus' for diagnostic clarity (everything that lands in
# Mimir came through Prometheus -- load-bearing mental model).
telemetron_otel_metrics_path: prometheus

# OTel container memory limit. D-45 ratios: GOMEMLIMIT = 80% of this;
# memory_limiter.limit_mib = 65% of GOMEMLIMIT; spike_limit_mib = 20%.
# Overriding requires updating the matching ratio knobs in defaults.
opentelemetry_memory_limit: 512m

# Conditional HEALTHCHECK. Outcome B default (--version proxy).
opentelemetry_healthcheck_enabled: true
```

**Step B:** Edit `playbooks/deploy_docker.yml`. Append `opentelemetry` role entry AFTER `node_exporter` (D-41 order). The role list after this plan: minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry. Update the trailing comment block.

Run `ansible-playbook --syntax-check playbooks/deploy_docker.yml`.
  </action>
  <verify>
    <automated>test -f inventory/example-homelab/group_vars/all/opentelemetry.yml &amp;&amp; grep -q "^telemetron_otel_metrics_path: prometheus$" inventory/example-homelab/group_vars/all/opentelemetry.yml &amp;&amp; grep -q "^opentelemetry_publish_otlp: true$" inventory/example-homelab/group_vars/all/opentelemetry.yml &amp;&amp; grep -q "    - role: opentelemetry$" playbooks/deploy_docker.yml &amp;&amp; grep -qE "^\s*- opentelemetry\s*$" playbooks/deploy_docker.yml &amp;&amp; awk '/- role: node_exporter/{n=NR}/- role: opentelemetry/{o=NR}END{exit !(n&lt;o)}' playbooks/deploy_docker.yml &amp;&amp; ansible-playbook --syntax-check playbooks/deploy_docker.yml 2>&amp;1 | grep -q "playbook:.*deploy_docker.yml"</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Inventory file exists with `telemetron_otel_metrics_path: prometheus`, `opentelemetry_publish_otlp: true`.
    - [ ] Playbook references `role: opentelemetry`.
    - [ ] D-41 order: opentelemetry appears AFTER node_exporter (awk check above).
    - [ ] Single-tag declaration (D-24).
    - [ ] Syntax check exits 0.
    - [ ] ASCII-only on the inventory file.
  </acceptance_criteria>
  <done>Inventory file lands at canonical location; playbook role list grows by one in D-41 order; syntax check passes.</done>
</task>

<task type="auto" id="03-02-10" tdd="false">
  <name>Task 10: Tick roles/README.md status row + run all six port-acceptance gates</name>
  <read_first>
    roles/README.md
    roles/opentelemetry/defaults/main.yml
    roles/opentelemetry/tasks/main.yml
    roles/opentelemetry/handlers/main.yml
    roles/opentelemetry/README.md
    roles/opentelemetry/templates/config.yaml.j2
    roles/opentelemetry/templates/verify-config.yaml.j2
  </read_first>
  <action>
**Step A:** Update `roles/README.md` -- change the `opentelemetry` row's Ported column from `☐` to `☑`. Touch nothing else.

**Step B:** Run the six port-acceptance gates on `roles/opentelemetry/`:
1. **Image-pin (OPS-01):** `! grep -rE 'image:.*:latest' roles/opentelemetry/`
2. **INSPQ grep gate (code/config only):** `! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/opentelemetry/ --include='*.yml' --include='*.yaml' --include='*.j2'`. README D-25 audit explicitly allowed to mention upstream project per Phase-2 D-25 reinterpretation.
3. **Non-ASCII gate (OPS-05):** `! grep -rPl '[^\x00-\x7F]' roles/opentelemetry/ --include='*.yml' --include='*.yaml' --include='*.j2'`.
4. **Vault gate (D-55):** `! grep -rE '{{ *vault_' roles/opentelemetry/` (zero refs).
5. **Idempotency (D-19/Pitfall 8):** `! grep -rE 'state:\s*restarted' roles/opentelemetry/`.
6. **Healthcheck + restart-policy (OPS-06):** `grep -q "restart_policy:" roles/opentelemetry/tasks/main.yml` AND `grep -q "healthcheck:" roles/opentelemetry/tasks/main.yml`.

Fix in prior task's file if any gate fails -- do not paper over.
  </action>
  <verify>
    <automated>grep -qE "^\| \`opentelemetry\`\s*\|.*\|\s*☑\s*\|" roles/README.md &amp;&amp; ! grep -rE 'image:.*:latest' roles/opentelemetry/ &amp;&amp; ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/opentelemetry/ --include='*.yml' --include='*.yaml' --include='*.j2' &amp;&amp; ! grep -rPl '[^\x00-\x7F]' roles/opentelemetry/ --include='*.yml' --include='*.yaml' --include='*.j2' &amp;&amp; ! grep -rE '{{ *vault_' roles/opentelemetry/ &amp;&amp; ! grep -rE 'state:\s*restarted' roles/opentelemetry/ &amp;&amp; grep -q "restart_policy:" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "healthcheck:" roles/opentelemetry/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] roles/README.md `opentelemetry` row ticked.
    - [ ] Image-pin gate passes (no `:latest`).
    - [ ] INSPQ grep gate passes on code/config files (README D-25 audit exempt).
    - [ ] Non-ASCII gate passes on code/config files.
    - [ ] Vault gate passes (zero `{{ vault_...` refs per D-55).
    - [ ] Idempotency gate passes (no `state: restarted`).
    - [ ] OPS-06 gate passes (restart_policy + healthcheck declared).
  </acceptance_criteria>
  <done>roles/README.md row ticked; all six gates green; plan M1-ready; live UAT proof deferred to Phase 3 verification.</done>
</task>

</tasks>

<verification>
**Static verification:**

1. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
2. All ten task-level acceptance_criteria pass.
3. `find roles/opentelemetry -type f | sort` returns: defaults/main.yml, handlers/main.yml, meta/main.yml, tasks/main.yml, tasks/verify.yml, templates/config.yaml.j2, templates/verify-config.yaml.j2, README.md.
4. `grep -c "include_tasks: verify.yml" roles/opentelemetry/tasks/main.yml` returns `1`.
5. config.yaml.j2 has `[memory_limiter, batch]` in all three pipelines (3x grep match).
6. config.yaml.j2 declares BOTH `^  prometheus:` AND `^  prometheusremotewrite:` exporter blocks.
7. config.yaml.j2 has container.restarts opt-in (grep -A1 confirms `enabled: true`).
8. roles/README.md row ticked.

**Live verification (deferred to Phase 3 verification stage):**

9. `ansible-playbook --tags opentelemetry` completes; `docker inspect telemetron-opentelemetry --format '{{.State.Health.Status}}'` returns `healthy` or `State.Running: true`.
10. `docker inspect telemetron-opentelemetry --format '{{.Config.Env}}'` contains `GOMEMLIMIT=400MiB`.
11. `docker inspect telemetron-opentelemetry --format '{{.HostConfig.Mounts}}'` contains the docker.sock bind-mount with `read_only: true`.
12. The verify task's Step 4 one-shot exits 0 (prometheusremotewrite -> Mimir end-to-end succeeded).
13. Second back-to-back run reports `changed=0` for the opentelemetry tag.

</verification>

<success_criteria>
- [ ] `roles/opentelemetry/` directory contains full canonical layout (defaults, tasks/main, tasks/verify, two templates, handlers, meta, README).
- [ ] All ten task-level acceptance_criteria pass.
- [ ] All six per-role port-acceptance gates pass.
- [ ] roles/README.md status table row for opentelemetry shows `☑`.
- [ ] playbooks/deploy_docker.yml contains `role: opentelemetry` after `role: node_exporter`.
- [ ] inventory/example-homelab/group_vars/all/opentelemetry.yml exists with the four operator knobs (publish_otlp, telemetron_otel_metrics_path, memory_limit, healthcheck_enabled).
- [ ] `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
- [ ] RESEARCH correction #1 (D-44 amendment) documented in README under "Loki exporter replaced by otlphttp" subheading and inline in config.yaml.j2 comments.
- [ ] RESEARCH correction #4 (container.restarts opt-in) baked into config.yaml.j2 (verified by grep -A1).
- [ ] INGEST-01, INGEST-05, INGEST-07, INGEST-08 marked satisfied in this plan's `requirements` field; live UAT proof deferred to Phase 3 verification.
</success_criteria>

<output>
After completion, create `.planning/phases/03-ingest-plane/03-02-opentelemetry-SUMMARY.md` documenting: image probe outcome (HEALTHCHECK shape), D-44 amendment implementation, D-43 dual-exporter knob, D-51 docker_stats + container.restarts opt-in, D-52 Approach A (group_add GID detection), D-54 approach (a) verify topology, D-25 deviations list, and execute-time surprises.
</output>
</content>
</invoke>