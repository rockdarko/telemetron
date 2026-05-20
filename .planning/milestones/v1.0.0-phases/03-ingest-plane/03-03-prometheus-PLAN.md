---
plan: 03-03-prometheus
phase: 03-ingest-plane
type: execute
wave: 3
depends_on: [03-01-node-exporter, 03-02-opentelemetry]
requirements: [INGEST-01, INGEST-02, INGEST-03]
files_modified:
  - roles/prometheus/defaults/main.yml
  - roles/prometheus/tasks/main.yml
  - roles/prometheus/tasks/verify.yml
  - roles/prometheus/handlers/main.yml
  - roles/prometheus/meta/main.yml
  - roles/prometheus/templates/prometheus.yml.j2
  - roles/prometheus/templates/rules-baseline.yml.j2
  - roles/prometheus/templates/rules-extras.yml.j2
  - roles/prometheus/README.md
  - inventory/example-homelab/group_vars/all/prometheus.yml
  - playbooks/deploy_docker.yml
  - roles/README.md
autonomous: true

must_haves:
  truths:
    - "In-network curl to http://prometheus:9090/-/ready returns 200 (ROADMAP SC1)."
    - "curl http://prometheus:9090/api/v1/targets shows three jobs all `up`: `otel_self` (targets otel:8888), `otel_metrics` (targets otel:8889), `node_exporter` (targets node-exporter:9100) (ROADMAP SC1 + INGEST-04 cross-plan confirmation)."
    - "curl http://prometheus:9090/api/v1/rules returns ALL FOUR baseline rule names: `HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals` (INGEST-03)."
    - "OTelCollectorDroppingSignals rule expression uses `otelcol_receiver_refused_*` prefix (NOT `otelcol_processor_refused_*`) -- RESEARCH correction #2."
    - "Prometheus remote_write target is `http://mimir:9009/api/v1/push` with NO X-Scope-OrgID header (INGEST-02 + Phase-2 D-26)."
    - "metric_relabel_configs ships default `labeldrop` regex `pod_uid|container_id|request_id|trace_id` AND catch-all `.*_id` (Pitfall 3 inline-cited)."
    - "prometheus_extra_rules inventory knob renders via sorted-keys Jinja into rules-extras.yml (operator-extensible per INGEST-03)."
    - "Re-running the playbook reports `changed=0` for the prometheus tag (OPS-04)."
    - "All six per-role port-acceptance gates pass on `roles/prometheus/`."
  artifacts:
    - path: roles/prometheus/defaults/main.yml
      provides: "Image pin prom/prometheus:v3.11.3, no-host-publish default, port :9090, retention 15d, scrape_interval 15s, named volume telemetron_prometheus_data, conditional HEALTHCHECK pattern, knob `prometheus_extra_rules: []` + `prometheus_extra_scrape_configs: []` + `prometheus_extra_relabel_configs: []`."
      contains: "v3.11.3"
    - path: roles/prometheus/templates/prometheus.yml.j2
      provides: "Production prometheus.yml: global scrape_interval 15s, three default scrape_configs (otel_self, otel_metrics, node_exporter), each with metric_relabel_configs labeldrop defaults, remote_write to mimir:9009, rule_files glob covering baseline + extras."
      contains: "remote_write"
    - path: roles/prometheus/templates/rules-baseline.yml.j2
      provides: "Four baseline alert rules in YAML group form: HostDown, FilesystemAlmostFull, ContainerRestartLoop, OTelCollectorDroppingSignals -- with the otelcol_receiver_refused_* prefix correction baked in."
      contains: "OTelCollectorDroppingSignals"
    - path: roles/prometheus/templates/rules-extras.yml.j2
      provides: "Sorted-keys Jinja iteration over prometheus_extra_rules; empty default renders an empty group (legal YAML)."
      contains: "prometheus_extra_rules"
    - path: roles/prometheus/tasks/main.yml
      provides: "Bootstrap: ensure config dir + rules subdir, ensure data volume, render three templates (notify), pull image, run container with --storage.tsdb.retention.time + --web.enable-lifecycle, include verify.yml."
      contains: "include_tasks: verify.yml"
    - path: roles/prometheus/tasks/verify.yml
      provides: "D-10a poll + /-/ready 200 probe + /api/v1/targets up-assertion (otel_self, otel_metrics, node_exporter) + /api/v1/rules four-rule-presence assertion."
      contains: "/api/v1/rules"
    - path: roles/prometheus/handlers/main.yml
      provides: "Single restart handler (W6) via docker restart."
      contains: "Docker restart prometheus"
    - path: roles/prometheus/README.md
      provides: "OPS-03 schema + D-25 audit + retention rationale + scrape-target rationale + 4-baseline-rules table + prometheus_extra_rules schema docs."
      contains: "## Deviations from upstream INSPQ"
    - path: inventory/example-homelab/group_vars/all/prometheus.yml
      provides: "Knobs: prometheus_publish_host: false, prometheus_retention_time: 15d, prometheus_extra_rules: [], prometheus_extra_scrape_configs: []."
      contains: "prometheus_retention_time"
    - path: playbooks/deploy_docker.yml
      provides: "prometheus role wired after opentelemetry."
      contains: "role: prometheus"
  key_links:
    - from: "roles/prometheus/templates/prometheus.yml.j2 remote_write block"
      to: "http://mimir:9009/api/v1/push"
      via: "Direct URL; no X-Scope-OrgID header (D-26)"
      pattern: "http://mimir:9009/api/v1/push"
    - from: "roles/prometheus/templates/prometheus.yml.j2 scrape_configs"
      to: "otel:8888 (job otel_self) AND otel:8889 (job otel_metrics) AND node-exporter:9100 (job node_exporter)"
      via: "Docker DNS over telemetron bridge -- D-42 + INGEST-04 + INGEST-08"
      pattern: "(otel:8888|otel:8889|node-exporter:9100)"
    - from: "roles/prometheus/templates/rules-baseline.yml.j2 OTelCollectorDroppingSignals"
      to: "otelcol_receiver_refused_{spans,log_records,metric_points}"
      via: "PromQL rate() sum over the three refused-* metrics -- RESEARCH correction #2"
      pattern: "otelcol_receiver_refused_(spans|log_records|metric_points)"
    - from: "roles/prometheus/templates/rules-baseline.yml.j2 ContainerRestartLoop"
      to: "container_restarts_total"
      via: "increase() over OTel docker_stats's container.restarts (translated to container_restarts_total)"
      pattern: "container_restarts_total"
    - from: "roles/prometheus/templates/prometheus.yml.j2 metric_relabel_configs"
      to: "labeldrop pod_uid|container_id|request_id|trace_id AND .*_id catch-all"
      via: "Pitfall 3 mitigation; inline-cited"
      pattern: "(labeldrop|pod_uid\\|container_id)"
---

<objective>
Port the `prometheus` role into `roles/prometheus/` mirroring the Phase-2 canonical role-template layout. Carries INGEST-02 (remote_write to Mimir) + INGEST-03 (four baseline alert rules + extras extension knob) + the OTelCollectorDroppingSignals PromQL `otelcol_receiver_refused_*` prefix correction (RESEARCH correction #2) + Pitfall 3 label-cardinality mitigation defaults. The verify task asserts both the Plan 03-01 (node_exporter) and Plan 03-02 (opentelemetry) targets are `up` and the four baseline rule names load.

Purpose: deliver INGEST-02 and INGEST-03; cross-confirm INGEST-01 (otel_self + otel_metrics scrape targets) and INGEST-08 (node_exporter scrape target).

Output: full canonical role layout under `roles/prometheus/` plus three Jinja templates (prometheus.yml + rules-baseline + rules-extras) plus inventory file plus playbook wiring plus roles/README.md status row tick. All six port-acceptance gates pass.
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
@roles/mimir/templates/mimir.yaml.j2
@inventory/example-homelab/group_vars/all/network.yml
@inventory/example-homelab/group_vars/all/storage.yml
@inventory/example-homelab/group_vars/all/mimir.yml
@playbooks/deploy_docker.yml
@.planning/phases/03-ingest-plane/03-01-node-exporter-PLAN.md
@.planning/phases/03-ingest-plane/03-02-opentelemetry-PLAN.md

<interfaces>
<!-- Phase-2 backends + Phase-3 plan 03-01 + 03-02 endpoints. -->

From Phase-2:
- Mimir HTTP push: http://mimir:9009/api/v1/push (D-26 no X-Scope-OrgID).

From Plan 03-01 (node-exporter):
- Scrape target: http://node-exporter:9100/metrics (single instance, single job `node_exporter`).

From Plan 03-02 (opentelemetry):
- OTel self-metrics: http://otel:8888/metrics  -> Prometheus job `otel_self`.
- OTel app-metrics (Prometheus-format exporter): http://otel:8889/metrics -> Prometheus job `otel_metrics`.
- The metric `container_restarts_total` arrives via OTel docker_stats + OTel `prometheus` exporter (D-51 opt-in, D-42 path).

RESEARCH correction #2 (CRITICAL):
- OTel self-metrics for refused records use prefix `otelcol_receiver_refused_*`, NOT `otelcol_processor_refused_*`.
- Concrete names: `otelcol_receiver_refused_spans`, `otelcol_receiver_refused_log_records`, `otelcol_receiver_refused_metric_points`.
- CONTEXT.md Claude-Discretion item that wrote `processor_refused_*` is SUPERSEDED.

RESEARCH Finding 4 (canonical prometheus.yml shape):
- global.scrape_interval: 15s, evaluation_interval: 15s
- global.external_labels: { cluster: telemetron-homelab, host: "{{ inventory_hostname }}" }
- rule_files: [/etc/prometheus/rules/baseline.yml, /etc/prometheus/rules/extra.yml]
- remote_write: [{ url: http://mimir:9009/api/v1/push, queue_config: { capacity 10000, max_samples_per_send 2000, batch_send_deadline 5s, min_shards 1, max_shards 5 } }]
- scrape_configs (three default jobs): otel_self, otel_metrics, node_exporter. EACH has metric_relabel_configs with labeldrop `pod_uid|container_id|request_id|trace_id` + labeldrop `.*_id`.

Command-line args (Prometheus 3.x):
- --config.file=/etc/prometheus/prometheus.yml
- --storage.tsdb.path=/prometheus
- --storage.tsdb.retention.time={{ prometheus_retention_time | default('15d') }}
- --web.enable-lifecycle
- --web.listen-address=0.0.0.0:9090
- (Do NOT add --web.enable-remote-write-receiver / --enable-feature=remote-write-receiver / --web.enable-otlp-receiver -- Prometheus WRITES remote_write to Mimir; does not RECEIVE it. Per D-25 audit.)

RESEARCH Finding 8 (final alert rule forms):

```yaml
groups:
  - name: telemetron.baseline
    interval: 30s
    rules:
      - alert: HostDown
        expr: up == 0
        for: 2m
        labels: { severity: critical, team: telemetron }
        annotations:
          summary: "Scrape target {{ '{{' }} $labels.instance {{ '}}' }} is unreachable"
          description: "{{ '{{' }} $labels.job {{ '}}' }} on {{ '{{' }} $labels.instance {{ '}}' }} has been unreachable for >2 minutes."

      - alert: FilesystemAlmostFull
        expr: (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"}) < 0.15
        for: 5m
        labels: { severity: warning, team: telemetron }
        annotations: { summary: ..., description: ... }

      - alert: ContainerRestartLoop
        # D-51 -- fed by OTel docker_stats container.restarts (opt-in via OTel config).
        # OTel->Prometheus translation: container_restarts_total.
        expr: increase(container_restarts_total[10m]) >= 3
        for: 0m
        labels: { severity: warning, team: telemetron }
        annotations: { summary: ..., description: ... }

      - alert: OTelCollectorDroppingSignals
        # RESEARCH correction #2: prefix is otelcol_receiver_refused_* (NOT processor_*).
        expr: |
          (
            rate(otelcol_receiver_refused_spans[5m])
            + rate(otelcol_receiver_refused_log_records[5m])
            + rate(otelcol_receiver_refused_metric_points[5m])
          ) > 0
        for: 5m
        labels: { severity: warning, team: telemetron }
        annotations: { summary: ..., description: ... }
```

Volume: `telemetron_prometheus_data` named Docker volume at `/prometheus` container path (Prometheus's default TSDB path).

INSPQ Deviation Audit (D-25) -- entries that MUST appear in README:
- Dropped: K8s branches (helm/operator), `:latest` tag, French strings, `America/Toronto`, restart_policy `always`, --web.enable-remote-write-receiver / --enable-feature=remote-write-receiver / --web.enable-otlp-receiver flags, prometheus_retention_size, URL-encoded alert rule format, `prometheus_alertmanager_alerting_rules` extension surface, UFW rules.
- Replaced: prometheus_retention_time 30d -> 15d (Claude Discretion); root_dir/data_dir/config_dir layout -> Phase-1 D-18 flat /opt/telemetron/prometheus/<file>.
- Added (Pitfall 3 mitigation pack + baseline rules + verify): metric_relabel_configs labeldrop defaults, baseline alert rule set (4 rules), default scrape jobs for OTel + node_exporter, remote_write to Mimir as default, in-network verify one-shot.

</interfaces>

<phase_decisions_inline>
- D-40: Plan 03-03 owns roles/prometheus/.
- D-41: Wave 3 -- depends_on: [03-01-node-exporter, 03-02-opentelemetry]. Both producers must exist before prometheus.yml can reference them.
- D-42: TWO OTel scrape jobs (otel_self :8888 + otel_metrics :8889). remote_write everything to Mimir.
- D-26 carry-forward: no X-Scope-OrgID header on remote_write.
- Pitfall 3: metric_relabel_configs labeldrop defaults; Mimir-side limits already shipped in Phase 2.
- D-19/W6: single docker restart handler.
- D-20: sorted-keys Jinja iteration on `prometheus_extra_rules`, `prometheus_extra_scrape_configs`, `prometheus_extra_relabel_configs`.
- D-30: prometheus_publish_host: false default.
- D-54: in-network verify one-shot -- curl /-/ready, /api/v1/targets, /api/v1/rules; assert specific patterns.
- D-55: no vault keys.
- RESEARCH correction #2: OTelCollectorDroppingSignals uses `otelcol_receiver_refused_*` prefix.
</phase_decisions_inline>
</context>

<tasks>

<task type="auto" id="03-03-01">
  <name>Task 1: Create prometheus role skeleton (full layout including templates/)</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/mimir/tasks/main.yml
    roles/mimir/handlers/main.yml
    roles/mimir/meta/main.yml
    roles/README.md
  </read_first>
  <action>
Create `roles/prometheus/{defaults,tasks,templates,handlers,meta}/`. Create skeleton files:
  - roles/prometheus/defaults/main.yml
  - roles/prometheus/tasks/main.yml
  - roles/prometheus/tasks/verify.yml
  - roles/prometheus/templates/prometheus.yml.j2
  - roles/prometheus/templates/rules-baseline.yml.j2
  - roles/prometheus/templates/rules-extras.yml.j2
  - roles/prometheus/handlers/main.yml
  - roles/prometheus/meta/main.yml (galaxy_info per mimir shape; description: "Deploys Prometheus 3.11.3 for Telemetron -- scrapes OTel Collector + node_exporter, remote_writes to Mimir, evaluates baseline alert rules."; galaxy_tags: metrics, prometheus, observability, telemetron)
  - roles/prometheus/README.md (skeleton)

Every YAML file starts with `---`.
  </action>
  <verify>
    <automated>test -d roles/prometheus/defaults &amp;&amp; test -d roles/prometheus/tasks &amp;&amp; test -d roles/prometheus/templates &amp;&amp; test -d roles/prometheus/handlers &amp;&amp; test -d roles/prometheus/meta &amp;&amp; test -f roles/prometheus/defaults/main.yml &amp;&amp; test -f roles/prometheus/tasks/main.yml &amp;&amp; test -f roles/prometheus/tasks/verify.yml &amp;&amp; test -f roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; test -f roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; test -f roles/prometheus/templates/rules-extras.yml.j2 &amp;&amp; test -f roles/prometheus/handlers/main.yml &amp;&amp; test -f roles/prometheus/meta/main.yml &amp;&amp; test -f roles/prometheus/README.md &amp;&amp; grep -q "^galaxy_info:" roles/prometheus/meta/main.yml &amp;&amp; grep -q "license: MIT" roles/prometheus/meta/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All five dirs exist.
    - [ ] All nine required files exist.
    - [ ] meta/main.yml has galaxy_info { role_name: prometheus, license: MIT, collections include community.docker + ansible.builtin }.
  </acceptance_criteria>
  <done>Skeleton matches Phase-2 canonical layout with three template files.</done>
</task>

<task type="auto" id="03-03-02" tdd="false">
  <name>Task 2: Populate defaults/main.yml with image pin, port, retention, volume, knobs (extra_rules, extra_scrape_configs, extra_relabel_configs)</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/prometheus/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/prometheus/defaults/main.yml`. Required keys (verbatim):

```yaml
# ---
# roles/prometheus/defaults/main.yml
# Prometheus role tunables. Override per-environment in
# inventory/<env>/group_vars/all/prometheus.yml.
#
# Prometheus 3.11.3 -- pull-scrape three default jobs (otel_self,
# otel_metrics, node_exporter) + remote_write to Mimir + evaluate four
# baseline alert rules + extensible via operator knobs.

# --- Image pin (OPS-01) ---
# See: https://github.com/prometheus/prometheus/releases/tag/v3.11.3
prometheus_image: prom/prometheus
prometheus_image_tag: "v3.11.3"

# --- Container identity ---
prometheus_container_name: prometheus

# --- Host port publishing (D-30) ---
# Default false. Operator UI access via SSH local-forward:
#   ssh -L 9090:localhost:9090 <host>
prometheus_publish_host: "{{ prometheus_publish_host | default(false) }}"

# --- Port matrix ---
prometheus_http_port: 9090

# --- Storage layout (D-16, D-17, D-18) ---
prometheus_data_volume: "{{ telemetron_volume_prefix | default('telemetron') }}_prometheus_data"
prometheus_data_path: /prometheus     # Prometheus image default TSDB path
prometheus_config_dir: "{{ telemetron_config_root | default('/opt/telemetron') }}/prometheus"

# --- Retention (Claude's Discretion -- 15d > Mimir's query_store_after 12h) ---
prometheus_retention_time: "{{ prometheus_retention_time | default('15d') }}"

# --- Scrape defaults ---
prometheus_global_scrape_interval: 15s
prometheus_global_evaluation_interval: 15s
prometheus_cluster_label: telemetron-homelab

# --- remote_write target (INGEST-02; Phase-2 D-26 no X-Scope-OrgID) ---
prometheus_remote_write_url: "http://mimir:9009/api/v1/push"
prometheus_remote_write_queue_capacity: 10000
prometheus_remote_write_max_samples_per_send: 2000
prometheus_remote_write_batch_send_deadline: 5s
prometheus_remote_write_min_shards: 1
prometheus_remote_write_max_shards: 5

# --- Default scrape targets (D-42 + INGEST-08) ---
prometheus_otel_self_target: "otel:8888"     # OTel self-metrics
prometheus_otel_metrics_target: "otel:8889"  # OTel app-metrics (Prometheus format)
prometheus_node_exporter_target: "node-exporter:9100"

# --- Pitfall 3 metric_relabel_configs defaults ---
# Always-applied set per scrape job. Operator extends via
# prometheus_extra_relabel_configs (list of dict per the
# metric_relabel_configs schema -- regex + action).
prometheus_default_relabel_drop_regex: "pod_uid|container_id|request_id|trace_id"
prometheus_default_relabel_id_catchall_regex: ".*_id"

# --- Operator extension knobs (INGEST-03 + D-20 sorted-keys) ---
prometheus_extra_scrape_configs: []
prometheus_extra_rules: []
prometheus_extra_relabel_configs: []

# --- Healthcheck approach (conditional; same pattern as Phase-2 roles) ---
# Prometheus 3.11.3 image is distroless; researcher most-likely Outcome B.
# /bin/prometheus --version is the binary-alive proxy. Image probe at
# execute time picks the actual outcome.
prometheus_healthcheck_enabled: true
prometheus_healthcheck_test: ["CMD", "/bin/prometheus", "--version"]
prometheus_healthcheck_interval: 15s
prometheus_healthcheck_timeout: 5s
prometheus_healthcheck_retries: 5
prometheus_healthcheck_start_period: 30s

# --- Verify pre-poll (D-10a) ---
prometheus_health_retries: 45
prometheus_health_delay: 2

# --- Restart policy (OPS-06) ---
prometheus_restart_policy: unless-stopped

# --- Resource limits ---
prometheus_memory_limit: 1g

# --- Network ---
prometheus_network: "{{ telemetron_network | default('telemetron') }}"

# --- Timezone (OPS-06; Pitfall 6) ---
prometheus_tz: "{{ telemetron_tz | default('Etc/UTC') }}"

# --- Curl image pin for verify (OPS-01) ---
prometheus_curl_image: curlimages/curl
prometheus_curl_image_tag: "8.10.1"
```

EXACT key names -- referenced by templates + tasks. Section order mirrors mimir.
  </action>
  <verify>
    <automated>grep -q '^prometheus_image: prom/prometheus$' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_image_tag: "v3.11.3"$' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_http_port: 9090$' roles/prometheus/defaults/main.yml &amp;&amp; grep -q 'prometheus_remote_write_url:.*mimir:9009/api/v1/push' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_otel_self_target: "otel:8888"$' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_otel_metrics_target: "otel:8889"$' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_node_exporter_target: "node-exporter:9100"$' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_extra_rules:' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_extra_scrape_configs:' roles/prometheus/defaults/main.yml &amp;&amp; grep -q '^prometheus_extra_relabel_configs:' roles/prometheus/defaults/main.yml &amp;&amp; grep -q "default('15d')" roles/prometheus/defaults/main.yml &amp;&amp; ! grep -qE ':\s*latest' roles/prometheus/defaults/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Image pin: `^prometheus_image: prom/prometheus$` AND `^prometheus_image_tag: "v3.11.3"$`
    - [ ] Port 9090 literal.
    - [ ] remote_write target: `prometheus_remote_write_url:.*mimir:9009/api/v1/push`
    - [ ] Three default scrape targets present (otel:8888, otel:8889, node-exporter:9100) as exact literals.
    - [ ] Retention default 15d: `grep -q "default('15d')"`
    - [ ] Extension knobs declared empty: `prometheus_extra_rules:`, `prometheus_extra_scrape_configs:`, `prometheus_extra_relabel_configs:`
    - [ ] Pitfall 3 relabel regex defaults declared.
    - [ ] Conditional HEALTHCHECK pattern.
    - [ ] No `:latest`.
  </acceptance_criteria>
  <done>defaults/main.yml has every literal the templates + tasks consume; all values match RESEARCH/CONTEXT.</done>
</task>

<task type="auto" id="03-03-03" tdd="false">
  <name>Task 3: Write templates/prometheus.yml.j2 -- three default scrape_configs with Pitfall 3 relabel defaults, remote_write to Mimir, rule_files glob, operator extension blocks</name>
  <read_first>
    roles/prometheus/defaults/main.yml
    roles/mimir/templates/mimir.yaml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/research/PITFALLS.md
  </read_first>
  <action>
Write `roles/prometheus/templates/prometheus.yml.j2` based on RESEARCH Finding 4. Use `{{ var }}` substitution where defaults vars exist. Inline-cite Pitfall 3.

Required content shape:

```yaml
# /opt/telemetron/prometheus/prometheus.yml
# {{ ansible_managed }}
# Prometheus 3.11.3 -- Telemetron-tuned.
# Pitfall 3 inline-cited; D-26 no X-Scope-OrgID on remote_write.

global:
  scrape_interval: {{ prometheus_global_scrape_interval }}
  evaluation_interval: {{ prometheus_global_evaluation_interval }}
  external_labels:
    cluster: {{ prometheus_cluster_label }}
    host: "{{ inventory_hostname }}"

rule_files:
  - /etc/prometheus/rules/baseline.yml
  - /etc/prometheus/rules/extra.yml

remote_write:
  - url: {{ prometheus_remote_write_url }}
    # D-26: no headers (Mimir multitenancy_enabled: false; tenant 'anonymous').
    queue_config:
      capacity: {{ prometheus_remote_write_queue_capacity }}
      max_samples_per_send: {{ prometheus_remote_write_max_samples_per_send }}
      batch_send_deadline: {{ prometheus_remote_write_batch_send_deadline }}
      min_shards: {{ prometheus_remote_write_min_shards }}
      max_shards: {{ prometheus_remote_write_max_shards }}

# Pitfall 3 source-side mitigation: labeldrop high-cardinality keys
# at scrape time so they never become active series.
scrape_configs:
  - job_name: otel_self
    # D-42: OTel Collector's INTERNAL/SELF metrics on :8888.
    # Source of otelcol_receiver_refused_* metrics consumed by the
    # OTelCollectorDroppingSignals alert rule.
    static_configs:
      - targets: ['{{ prometheus_otel_self_target }}']
        labels:
          service: opentelemetry-collector
    metric_relabel_configs:
      - regex: '{{ prometheus_default_relabel_drop_regex }}'
        action: labeldrop
      - regex: '{{ prometheus_default_relabel_id_catchall_regex }}'
        action: labeldrop

  - job_name: otel_metrics
    # D-42: OTLP-pushed app metrics in Prometheus format on :8889.
    # Source of container_restarts_total (from docker_stats opt-in).
    static_configs:
      - targets: ['{{ prometheus_otel_metrics_target }}']
        labels:
          service: opentelemetry-collector-app-metrics
    metric_relabel_configs:
      - regex: '{{ prometheus_default_relabel_drop_regex }}'
        action: labeldrop
      - regex: '{{ prometheus_default_relabel_id_catchall_regex }}'
        action: labeldrop

  - job_name: node_exporter
    # INGEST-08: host metrics scraped from Plan 03-01.
    static_configs:
      - targets: ['{{ prometheus_node_exporter_target }}']
        labels:
          service: node-exporter
    metric_relabel_configs:
      - regex: '{{ prometheus_default_relabel_drop_regex }}'
        action: labeldrop

  # Operator-extensible scrape jobs. Sorted-keys (D-20) for idempotency.
{% for job in prometheus_extra_scrape_configs | default([]) | sort(attribute='job_name') %}
  - job_name: {{ job.job_name }}
    static_configs: {{ job.static_configs }}
{% if job.metric_relabel_configs is defined %}
    metric_relabel_configs:
{% for rl in job.metric_relabel_configs %}
      - regex: '{{ rl.regex }}'
        action: {{ rl.action }}
{% endfor %}
{% endif %}
{% endfor %}
```

Use `{{ var }}` substitution everywhere a defaults key applies. All comments ENGLISH. ASCII only.
  </action>
  <verify>
    <automated>grep -q "global:" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "rule_files:" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "/etc/prometheus/rules/baseline.yml" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "/etc/prometheus/rules/extra.yml" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "remote_write:" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "prometheus_remote_write_url" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "job_name: otel_self" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "job_name: otel_metrics" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "job_name: node_exporter" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "metric_relabel_configs:" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "action: labeldrop" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "Pitfall 3" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; grep -q "sort(attribute" roles/prometheus/templates/prometheus.yml.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/prometheus/templates/prometheus.yml.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] global block present with scrape_interval var.
    - [ ] rule_files glob covers baseline + extra: `grep -q "baseline.yml"` AND `grep -q "extra.yml"`.
    - [ ] remote_write block targets Mimir: `grep -q "prometheus_remote_write_url"`.
    - [ ] Three default scrape jobs: `grep -q "job_name: otel_self"` AND `grep -q "job_name: otel_metrics"` AND `grep -q "job_name: node_exporter"`.
    - [ ] metric_relabel_configs with labeldrop appears at least 3 times (one per default job): `grep -c "action: labeldrop" roles/prometheus/templates/prometheus.yml.j2` returns >= 3.
    - [ ] Pitfall 3 cited inline: `grep -q "Pitfall 3"`.
    - [ ] D-20 sorted-keys iteration on extra scrape configs: `grep -q "sort(attribute"`.
    - [ ] NO X-Scope-OrgID header (D-26): `! grep -q "X-Scope-OrgID" roles/prometheus/templates/prometheus.yml.j2`.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>prometheus.yml.j2 has three default scrape jobs with Pitfall 3 relabel defaults, remote_write to Mimir, rule_files glob, operator-extensible block.</done>
</task>

<task type="auto" id="03-03-04" tdd="false">
  <name>Task 4: Write templates/rules-baseline.yml.j2 with FOUR alert rules, OTelCollectorDroppingSignals using otelcol_receiver_refused_* (RESEARCH correction #2)</name>
  <read_first>
    roles/prometheus/defaults/main.yml
    roles/prometheus/templates/prometheus.yml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/prometheus/templates/rules-baseline.yml.j2` using RESEARCH Finding 8 (Final form). The four rules:

```yaml
# /opt/telemetron/prometheus/rules/baseline.yml
# {{ ansible_managed }}
# INGEST-03 baseline alert rules. Operators extend via
# prometheus_extra_rules: [] in inventory.
#
# OTelCollectorDroppingSignals uses otelcol_receiver_refused_* prefix
# (RESEARCH correction #2 -- CONTEXT.md's processor_refused_* mention
# was wrong; receiver-side counters are the canonical names per the
# OpenTelemetry internal-telemetry docs).

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
        # Pitfall 3 -- exclude high-cardinality / ephemeral fstypes.
        expr: (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"}) < 0.15
        for: 5m
        labels:
          severity: warning
          team: telemetron
        annotations:
          summary: "Filesystem {{ '{{' }} $labels.mountpoint {{ '}}' }} on {{ '{{' }} $labels.instance {{ '}}' }} is <15% free"
          description: "Filesystem {{ '{{' }} $labels.mountpoint {{ '}}' }} ({{ '{{' }} $labels.fstype {{ '}}' }}) on {{ '{{' }} $labels.instance {{ '}}' }} has been below 15% available for >5 minutes."

      - alert: ContainerRestartLoop
        # D-51 -- fed by OTel docker_stats container.restarts (opt-in in OTel config).
        # OTel->Prometheus translation: container_restarts_total.
        expr: increase(container_restarts_total[10m]) >= 3
        for: 0m
        labels:
          severity: warning
          team: telemetron
        annotations:
          summary: "Container {{ '{{' }} $labels.container_name {{ '}}' }} restarted >=3 times in 10m"
          description: "Container {{ '{{' }} $labels.container_name {{ '}}' }} (image {{ '{{' }} $labels.container_image_name {{ '}}' }}) has restarted >=3 times in the last 10 minutes. Likely crash-looping."

      - alert: OTelCollectorDroppingSignals
        # RESEARCH correction #2: prefix is otelcol_receiver_refused_*
        # (NOT otelcol_processor_refused_*). When a downstream pipeline
        # rejects data (memory_limiter saturation, exporter retry exhaust,
        # batch overflow), the receiver-side counters increment.
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

Use `{{ '{{' }}` / `{{ '}}' }}` escapes to render literal `{{ ... }}` in the final YAML (so Prometheus's own templating in annotations survives Jinja rendering). ASCII only. NO `processor_refused_*` anywhere.
  </action>
  <verify>
    <automated>grep -q "alert: HostDown$" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "alert: FilesystemAlmostFull$" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "alert: ContainerRestartLoop$" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "alert: OTelCollectorDroppingSignals$" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "otelcol_receiver_refused_spans" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "otelcol_receiver_refused_log_records" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "otelcol_receiver_refused_metric_points" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; ! grep -q "otelcol_processor_refused" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "container_restarts_total" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "up == 0" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; grep -q "node_filesystem_avail_bytes" roles/prometheus/templates/rules-baseline.yml.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/prometheus/templates/rules-baseline.yml.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All FOUR alert names present (exact match): `alert: HostDown`, `alert: FilesystemAlmostFull`, `alert: ContainerRestartLoop`, `alert: OTelCollectorDroppingSignals`.
    - [ ] OTelCollectorDroppingSignals expression uses receiver prefix (RESEARCH correction #2): `grep -q "otelcol_receiver_refused_spans"` AND `grep -q "otelcol_receiver_refused_log_records"` AND `grep -q "otelcol_receiver_refused_metric_points"`.
    - [ ] Critically: NO `processor_refused_*` anywhere: `! grep -q "otelcol_processor_refused"`.
    - [ ] ContainerRestartLoop uses `container_restarts_total` (D-51 translated metric name): `grep -q "container_restarts_total"`.
    - [ ] HostDown expression `up == 0`: `grep -q "up == 0"`.
    - [ ] FilesystemAlmostFull uses node_exporter metric: `grep -q "node_filesystem_avail_bytes"`.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>rules-baseline.yml.j2 has all four rules; OTelCollectorDroppingSignals uses the CORRECTED prefix per RESEARCH; ContainerRestartLoop uses the OTel-translated metric name.</done>
</task>

<task type="auto" id="03-03-05" tdd="false">
  <name>Task 5: Write templates/rules-extras.yml.j2 -- sorted-keys Jinja iteration over prometheus_extra_rules (empty default renders empty group)</name>
  <read_first>
    roles/prometheus/defaults/main.yml
    roles/prometheus/templates/rules-baseline.yml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/prometheus/templates/rules-extras.yml.j2`. RESEARCH Finding 8 schema:

```jinja2
# /opt/telemetron/prometheus/rules/extra.yml
# {{ ansible_managed }}
# Operator-supplied alert rules (INGEST-03 extension).
# Define rules in inventory as prometheus_extra_rules: list-of-dict with
# keys: name, expr, for, labels (dict), annotations (dict).
# Sorted-keys (D-20) for idempotent rendering.

groups:
  - name: telemetron.operator-extras
    interval: 30s
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

When `prometheus_extra_rules` is empty (the default), the rendered file has:

```yaml
groups:
  - name: telemetron.operator-extras
    interval: 30s
    rules:
```

(a group with empty rules list -- legal YAML, Prometheus accepts.)

ASCII only. NO Jinja syntax errors.
  </action>
  <verify>
    <automated>grep -q "prometheus_extra_rules" roles/prometheus/templates/rules-extras.yml.j2 &amp;&amp; grep -q "sort(attribute='name')" roles/prometheus/templates/rules-extras.yml.j2 &amp;&amp; grep -q "keys() | sort" roles/prometheus/templates/rules-extras.yml.j2 &amp;&amp; grep -q "telemetron.operator-extras" roles/prometheus/templates/rules-extras.yml.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/prometheus/templates/rules-extras.yml.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] References prometheus_extra_rules: `grep -q "prometheus_extra_rules"`.
    - [ ] D-20 sorted-keys on the rule names: `grep -q "sort(attribute='name')"`.
    - [ ] D-20 sorted-keys on labels + annotations dicts: `grep -q "keys() | sort"`.
    - [ ] Group named `telemetron.operator-extras`: `grep -q "telemetron.operator-extras"`.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>rules-extras.yml.j2 has the operator-extras iterator; empty default renders empty group; sorted-keys discipline applied.</done>
</task>

<task type="auto" id="03-03-06" tdd="false">
  <name>Task 6: Write tasks/main.yml -- config dir + rules subdir, render 3 templates (notify), volume, pull, run container with retention/lifecycle flags, include verify</name>
  <read_first>
    roles/mimir/tasks/main.yml
    roles/prometheus/defaults/main.yml
    roles/prometheus/templates/prometheus.yml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/prometheus/tasks/main.yml`. Task sequence:

1. **Ensure config dir**: `ansible.builtin.file: path: "{{ prometheus_config_dir }}" state: directory mode: 0755`. Tags: [prometheus, prometheus-config].

2. **Ensure rules subdir**: `ansible.builtin.file: path: "{{ prometheus_config_dir }}/rules" state: directory mode: 0755`. Tags: [prometheus, prometheus-config].

3. **Render prometheus.yml**: `ansible.builtin.template: src: prometheus.yml.j2 dest: "{{ prometheus_config_dir }}/prometheus.yml" mode: 0640`. `notify: restart prometheus`. Tags: [prometheus, prometheus-config].

4. **Render rules-baseline**: `ansible.builtin.template: src: rules-baseline.yml.j2 dest: "{{ prometheus_config_dir }}/rules/baseline.yml" mode: 0640`. `notify: restart prometheus`. Tags: [prometheus, prometheus-config].

5. **Render rules-extras**: `ansible.builtin.template: src: rules-extras.yml.j2 dest: "{{ prometheus_config_dir }}/rules/extra.yml" mode: 0640`. `notify: restart prometheus`. Tags: [prometheus, prometheus-config].

6. **Ensure data volume**: `community.docker.docker_volume: name: "{{ prometheus_data_volume }}" state: present`. Tags: [prometheus].

7. **Pull image**: `community.docker.docker_image: name: "{{ prometheus_image }}:{{ prometheus_image_tag }}" source: pull force_source: false`. Tags: [prometheus].

8. **Run container** -- `community.docker.docker_container`:
   - `name`, `image`, `state: started`, `recreate: false`, `restart_policy`, `memory`
   - `command:` -- the explicit CLI args (NO `--web.enable-remote-write-receiver`, NO `--web.enable-otlp-receiver` per D-25 audit):
     ```
     - "--config.file=/etc/prometheus/prometheus.yml"
     - "--storage.tsdb.path=/prometheus"
     - "--storage.tsdb.retention.time={{ prometheus_retention_time }}"
     - "--web.enable-lifecycle"
     - "--web.listen-address=0.0.0.0:{{ prometheus_http_port }}"
     ```
   - `networks: [{ name: "{{ prometheus_network }}", aliases: ["{{ prometheus_container_name }}"] }]`
   - `published_ports:` -- triple-conditional Jinja per mimir pattern (`{{ prometheus_http_port }}`)
   - `mounts: [{ source: "{{ prometheus_data_volume }}", target: "{{ prometheus_data_path }}", type: volume }]`
   - `volumes:` -- THREE bind-mounts:
     - `"{{ prometheus_config_dir }}/prometheus.yml:/etc/prometheus/prometheus.yml:ro"`
     - `"{{ prometheus_config_dir }}/rules/baseline.yml:/etc/prometheus/rules/baseline.yml:ro"`
     - `"{{ prometheus_config_dir }}/rules/extra.yml:/etc/prometheus/rules/extra.yml:ro"`
   - `healthcheck:` -- conditional via vars-form mirroring mimir
   - `env: { TZ: "{{ prometheus_tz }}" }`
   - Tags: [prometheus, prometheus-container]

9. **Include verify** -- `ansible.builtin.include_tasks: verify.yml`. Tags: [prometheus, prometheus-verify].

All task names ENGLISH; no `state: restarted`; ASCII only.
  </action>
  <verify>
    <automated>grep -q "src: prometheus.yml.j2" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "src: rules-baseline.yml.j2" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "src: rules-extras.yml.j2" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "community.docker.docker_volume" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "community.docker.docker_image" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "community.docker.docker_container" roles/prometheus/tasks/main.yml &amp;&amp; grep -q -- "--storage.tsdb.retention.time" roles/prometheus/tasks/main.yml &amp;&amp; grep -q -- "--web.enable-lifecycle" roles/prometheus/tasks/main.yml &amp;&amp; ! grep -q -- "--web.enable-remote-write-receiver" roles/prometheus/tasks/main.yml &amp;&amp; ! grep -q -- "--web.enable-otlp-receiver" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "notify: restart prometheus" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "include_tasks: verify.yml" roles/prometheus/tasks/main.yml &amp;&amp; ! grep -qE "state:\s*restarted" roles/prometheus/tasks/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/prometheus/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All three template renders present (prometheus.yml.j2, rules-baseline.yml.j2, rules-extras.yml.j2).
    - [ ] All three renders notify the restart handler: `grep -c "notify: restart prometheus" roles/prometheus/tasks/main.yml` returns 3.
    - [ ] docker_volume + docker_image + docker_container all present.
    - [ ] CLI flags: `--storage.tsdb.retention.time` AND `--web.enable-lifecycle`.
    - [ ] D-25 audit enforced -- the FORBIDDEN flags are absent: `! grep -q -- "--web.enable-remote-write-receiver"` AND `! grep -q -- "--web.enable-otlp-receiver"`.
    - [ ] include_tasks final task.
    - [ ] No `state: restarted`.
    - [ ] ASCII-only.
    - [ ] Conditional HEALTHCHECK omit-magic-value pattern: `grep -q "if (prometheus_healthcheck_enabled | bool) else omit" roles/prometheus/tasks/main.yml`.
  </acceptance_criteria>
  <done>tasks/main.yml renders three configs, manages volume + container, includes verify, lacks the forbidden D-25 flags.</done>
</task>

<task type="auto" id="03-03-07" tdd="false">
  <name>Task 7: Write tasks/verify.yml -- D-10a poll + /-/ready 200 + /api/v1/targets up-assertion (otel_self, otel_metrics, node_exporter) + /api/v1/rules four-rule assertion</name>
  <read_first>
    roles/mimir/tasks/verify.yml
    roles/prometheus/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/prometheus/tasks/verify.yml`. Steps:

**Step 1a -- HEALTHCHECK poll** (when enabled): `community.docker.docker_container_info`, until State.Health.Status=='healthy', retries `prometheus_health_retries`, delay `prometheus_health_delay`, `when: prometheus_healthcheck_enabled | bool`.

**Step 1b -- State.Running fallback** (when disabled).

**Step 2 -- /-/ready 200 probe**: one-shot curlimages/curl on telemetron network. Shell loop:
```
i=0 ;
while [ $i -lt 30 ] ; do
  CODE=$(curl -sS -o /dev/null -w "%{http_code}" http://{{ prometheus_container_name }}:{{ prometheus_http_port }}/-/ready 2>/dev/null) ;
  if [ "$CODE" = "200" ] ; then echo "ready_ok=200" ; exit 0 ; fi ;
  i=$((i+1)) ;
  sleep 2 ;
done ;
echo "prometheus /-/ready never returned 200 within 60s" ;
exit 1
```
auto_remove: true, changed_when: false, failed_when on non-zero status.

**Step 3 -- /api/v1/targets assertion (otel_self + otel_metrics + node_exporter all up)**: one-shot curlimages/curl. Use `apk add --no-cache jq` or pipe through grep/awk. Simplest: curl returns JSON, grep the response for each job name AND `"health":"up"`:
```
BODY=$(curl -sS http://{{ prometheus_container_name }}:{{ prometheus_http_port }}/api/v1/targets 2>/dev/null) ;
echo "$BODY" | grep -q '"job":"otel_self"' || { echo "missing otel_self job" ; exit 1 ; } ;
echo "$BODY" | grep -q '"job":"otel_metrics"' || { echo "missing otel_metrics job" ; exit 1 ; } ;
echo "$BODY" | grep -q '"job":"node_exporter"' || { echo "missing node_exporter job" ; exit 1 ; } ;
echo "$BODY" | grep -q '"health":"up"' || { echo "no targets show health up" ; exit 1 ; } ;
echo "targets_ok"
```

NB: this verify runs IMMEDIATELY after the prometheus container starts; targets may not yet have completed a first scrape cycle. Recommendation: retry the assertion in a 60s window (similar to Step 2) -- wrap in a shell loop that retries until all assertions pass or times out.

**Step 4 -- /api/v1/rules assertion (four baseline rule names)**: one-shot curlimages/curl. Body must contain all four exact names:
```
BODY=$(curl -sS http://{{ prometheus_container_name }}:{{ prometheus_http_port }}/api/v1/rules 2>/dev/null) ;
echo "$BODY" | grep -q '"name":"HostDown"' || { echo "missing HostDown" ; exit 1 ; } ;
echo "$BODY" | grep -q '"name":"FilesystemAlmostFull"' || { echo "missing FilesystemAlmostFull" ; exit 1 ; } ;
echo "$BODY" | grep -q '"name":"ContainerRestartLoop"' || { echo "missing ContainerRestartLoop" ; exit 1 ; } ;
echo "$BODY" | grep -q '"name":"OTelCollectorDroppingSignals"' || { echo "missing OTelCollectorDroppingSignals" ; exit 1 ; } ;
echo "rules_ok=4"
```

All one-shots: `auto_remove: true`, `changed_when: false`, `failed_when` on non-zero status. ASCII English task names.
  </action>
  <verify>
    <automated>grep -q "community.docker.docker_container_info" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "State.Health.Status == 'healthy'" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "State.Running is true" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "/-/ready" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "/api/v1/targets" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "/api/v1/rules" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "otel_self" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "otel_metrics" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "node_exporter" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "HostDown" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "FilesystemAlmostFull" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "ContainerRestartLoop" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "OTelCollectorDroppingSignals" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "auto_remove: true" roles/prometheus/tasks/verify.yml &amp;&amp; grep -q "changed_when: false" roles/prometheus/tasks/verify.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/prometheus/tasks/verify.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Step 1a HEALTHCHECK poll + Step 1b Running fallback (mimir-pattern).
    - [ ] Step 2 `/-/ready` probe with 200 assertion.
    - [ ] Step 3 `/api/v1/targets` with all three job names asserted (`otel_self`, `otel_metrics`, `node_exporter`) + `health":"up"` check.
    - [ ] Step 4 `/api/v1/rules` with all FOUR rule names asserted (`HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals`).
    - [ ] All one-shots auto_remove + changed_when: false.
    - [ ] Attached to telemetron network.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>verify.yml exercises HEALTHCHECK/Running, /-/ready, /api/v1/targets, /api/v1/rules.</done>
</task>

<task type="auto" id="03-03-08" tdd="false">
  <name>Task 8: Write handlers/main.yml</name>
  <read_first>
    roles/mimir/handlers/main.yml
  </read_first>
  <action>
```yaml
# ---
# roles/prometheus/handlers/main.yml
# Per D-19 / Pitfall 8: container restarts on config change use
# `docker restart <name>`. Force-recreate is non-idempotent.
#
# All three template renders (prometheus.yml, rules/baseline.yml,
# rules/extra.yml) notify this handler. Prometheus reloads rule files
# on SIGHUP via --web.enable-lifecycle, but a `docker restart` is
# simpler and still idempotent at the W6 layer.

- name: Docker restart prometheus
  ansible.builtin.command:
    cmd: "docker restart {{ prometheus_container_name }}"
  changed_when: true
  listen: restart prometheus
```
  </action>
  <verify>
    <automated>grep -q "^- name: Docker restart prometheus$" roles/prometheus/handlers/main.yml &amp;&amp; grep -q "listen: restart prometheus" roles/prometheus/handlers/main.yml &amp;&amp; ! grep -q "state: restarted" roles/prometheus/handlers/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/prometheus/handlers/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Single handler.
    - [ ] listen: restart prometheus.
    - [ ] No state: restarted.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>handlers/main.yml has the canonical single handler.</done>
</task>

<task type="auto" id="03-03-09" tdd="false">
  <name>Task 9: Write README.md -- OPS-03 schema + D-25 audit + baseline rule table + retention rationale + prometheus_extra_rules schema docs</name>
  <read_first>
    roles/mimir/README.md
    roles/prometheus/defaults/main.yml
    roles/prometheus/templates/rules-baseline.yml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/prometheus/README.md` mirroring `roles/mimir/README.md` schema. Required H2 sections (in order):

1. `# roles/prometheus` -- overview.
2. `## What this role does` -- numbered list.
3. `## Default scrape targets` -- table:
   | Job | Target | Source |
   |-----|--------|--------|
   | `otel_self` | `otel:8888` | OTel Collector self-metrics (D-42; source of otelcol_receiver_refused_* signals consumed by OTelCollectorDroppingSignals alert) |
   | `otel_metrics` | `otel:8889` | OTel Collector Prometheus-format app metrics (D-42; source of container_restarts_total consumed by ContainerRestartLoop alert) |
   | `node_exporter` | `node-exporter:9100` | Host metrics from Plan 03-01 (INGEST-08) |
4. `## Baseline alert rules` -- table of four rules with expressions:
   | Alert | Expression | For | Severity |
   |-------|------------|-----|----------|
   | `HostDown` | `up == 0` | 2m | critical |
   | `FilesystemAlmostFull` | `(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"} / node_filesystem_size_bytes{...}) < 0.15` | 5m | warning |
   | `ContainerRestartLoop` | `increase(container_restarts_total[10m]) >= 3` | 0m | warning |
   | `OTelCollectorDroppingSignals` | `(rate(otelcol_receiver_refused_spans[5m]) + rate(otelcol_receiver_refused_log_records[5m]) + rate(otelcol_receiver_refused_metric_points[5m])) > 0` | 5m | warning |
   With a NOTE: the OTelCollectorDroppingSignals prefix is `otelcol_receiver_refused_*` (NOT `otelcol_processor_refused_*` -- the receiver-side counters increment when a downstream pipeline rejects data, per the OTel internal-telemetry docs; RESEARCH correction #2).
5. `## Operator-extensible alert rules (prometheus_extra_rules)` -- describe schema (list-of-dict: name, expr, for, labels dict, annotations dict). Show an example.
6. `## Variables` -- markdown table of every defaults/main.yml key.
7. `## Vault keys` -- "None (Phase 3 D-55)."
8. `## Tags` -- "- `prometheus`".
9. `## Modes` -- "Single mode. Distributed/federation is deferred."
10. `## Volumes` -- table: `telemetron_prometheus_data` (named, `/prometheus`) for TSDB; three bind-mounts for configs.
11. `## Retention` -- explain `prometheus_retention_time: 15d` (default) vs Mimir `query_store_after: 12h` -- 15d > 12h ensures Grafana queries against Prometheus for recent data while Mimir handles long-term.
12. `## Healthcheck` -- conditional pattern; image probe at execute time.
13. `## Operator access (no host publish by default per D-30)` -- SSH local-forward example.
14. `## Security model` -- short.
15. `## Idempotency` -- standard.
16. `## Port-acceptance gates` -- six gates.
17. `## Deviations from upstream INSPQ (D-25)` -- audit per RESEARCH:
    - **Dropped:** K8s helm/operator branches, French strings, restart_policy always, `America/Toronto`, `--web.enable-remote-write-receiver` flag, `--enable-feature=remote-write-receiver` flag, `--web.enable-otlp-receiver` flag (Telemetron's Prometheus WRITES remote_write, doesn't RECEIVE it), URL-encoded alert rule format, `prometheus_retention_size` size-based retention, UFW rules, `:latest` tag.
    - **Replaced:** retention 30d -> 15d (Claude's Discretion); root_dir/data_dir/config_dir layout -> Phase-1 D-18 flat layout.
    - **Added:** metric_relabel_configs labeldrop defaults (Pitfall 3 -- THE highest-leverage D-25 improvement); FOUR baseline alert rules (INGEST-03; upstream shipped empty `alerting_rules`); default scrape jobs for OTel + node_exporter; remote_write to Mimir as M1 default; in-network verify one-shot (D-54).
18. `## Deprecation notes` -- "None for M1."

ASCII-only outside the D-25 audit section.
  </action>
  <verify>
    <automated>grep -qE "^# roles/prometheus" roles/prometheus/README.md &amp;&amp; grep -q "^## What this role does" roles/prometheus/README.md &amp;&amp; grep -q "^## Default scrape targets" roles/prometheus/README.md &amp;&amp; grep -q "^## Baseline alert rules" roles/prometheus/README.md &amp;&amp; grep -q "^## Operator-extensible alert rules" roles/prometheus/README.md &amp;&amp; grep -q "^## Variables" roles/prometheus/README.md &amp;&amp; grep -q "^## Vault keys" roles/prometheus/README.md &amp;&amp; grep -q "^## Tags" roles/prometheus/README.md &amp;&amp; grep -q "^## Retention" roles/prometheus/README.md &amp;&amp; grep -q "^## Healthcheck" roles/prometheus/README.md &amp;&amp; grep -q "^## Deviations from upstream INSPQ" roles/prometheus/README.md &amp;&amp; grep -q "v3.11.3" roles/prometheus/README.md &amp;&amp; grep -q "otelcol_receiver_refused" roles/prometheus/README.md &amp;&amp; grep -q "container_restarts_total" roles/prometheus/README.md &amp;&amp; grep -q "metric_relabel_configs" roles/prometheus/README.md</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All 18 required H2 sections present (the grep set above covers the key ones).
    - [ ] Image pin documented: `grep -q "v3.11.3"`.
    - [ ] OTelCollectorDroppingSignals correction documented: `grep -q "otelcol_receiver_refused"` AND `grep -q "processor" roles/prometheus/README.md` AND a clear note that processor_refused is wrong.
    - [ ] D-25 audit has at least 3 bullet categories.
    - [ ] FOUR baseline rules table present (each name in the README).
    - [ ] container_restarts_total D-51 metric documented.
    - [ ] metric_relabel_configs Pitfall 3 highlighted.
    - [ ] Retention rationale (15d > Mimir's 12h) explained.
  </acceptance_criteria>
  <done>README has full OPS-03 schema + baseline-rules table + retention rationale + D-25 audit including the correction.</done>
</task>

<task type="auto" id="03-03-10" tdd="false">
  <name>Task 10: Create inventory/example-homelab/group_vars/all/prometheus.yml + wire role into playbooks/deploy_docker.yml after opentelemetry</name>
  <read_first>
    inventory/example-homelab/group_vars/all/mimir.yml
    playbooks/deploy_docker.yml
  </read_first>
  <action>
**Step A:** Create `inventory/example-homelab/group_vars/all/prometheus.yml`:

```yaml
# ---
# Telemetron -- prometheus operator knobs (Phase 3, D-30, INGEST-02, INGEST-03)
# Role-specific overrides for the `prometheus` role.
# See roles/prometheus/defaults/main.yml for the full default surface.

# Default: zero host port publish. Operator UI access via SSH:
#   ssh -L 9090:localhost:9090 <host>
prometheus_publish_host: false

# Local TSDB retention. 15d > Mimir's query_store_after (12h per
# Phase-2 D-36) so Grafana queries against Prometheus for recent data
# while Mimir handles long-term.
prometheus_retention_time: 15d

# Operator-extensible alert rules (INGEST-03 extension). Example:
#   prometheus_extra_rules:
#     - name: MyAppDown
#       expr: up{job="my-app"} == 0
#       for: 1m
#       labels: { severity: critical, team: ops }
#       annotations:
#         summary: "my-app is down"
prometheus_extra_rules: []

# Operator-extensible scrape jobs. Same shape as Prometheus scrape_config.
prometheus_extra_scrape_configs: []
```

**Step B:** Edit `playbooks/deploy_docker.yml`. Append `prometheus` after `opentelemetry`. Tag `prometheus`.

Run syntax check.
  </action>
  <verify>
    <automated>test -f inventory/example-homelab/group_vars/all/prometheus.yml &amp;&amp; grep -q "^prometheus_retention_time: 15d$" inventory/example-homelab/group_vars/all/prometheus.yml &amp;&amp; grep -q "^prometheus_extra_rules:" inventory/example-homelab/group_vars/all/prometheus.yml &amp;&amp; grep -q "    - role: prometheus$" playbooks/deploy_docker.yml &amp;&amp; awk '/- role: opentelemetry/{o=NR}/- role: prometheus/{p=NR}END{exit !(o&lt;p)}' playbooks/deploy_docker.yml &amp;&amp; ansible-playbook --syntax-check playbooks/deploy_docker.yml 2>&amp;1 | grep -q "playbook:.*deploy_docker.yml"</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Inventory file exists with expected knobs.
    - [ ] Playbook contains `role: prometheus`.
    - [ ] D-41 order: prometheus appears AFTER opentelemetry.
    - [ ] Syntax check exits 0.
    - [ ] ASCII-only on inventory file.
  </acceptance_criteria>
  <done>Inventory + playbook updates land in D-41 order.</done>
</task>

<task type="auto" id="03-03-11" tdd="false">
  <name>Task 11: Tick roles/README.md status row + run all six port-acceptance gates</name>
  <read_first>
    roles/README.md
    roles/prometheus/defaults/main.yml
    roles/prometheus/tasks/main.yml
    roles/prometheus/handlers/main.yml
    roles/prometheus/README.md
  </read_first>
  <action>
**Step A:** Update `roles/README.md` -- change the `prometheus` row's Ported column to `☑`.

**Step B:** Run the six port-acceptance gates:
1. Image-pin: `! grep -rE 'image:.*:latest' roles/prometheus/`
2. INSPQ grep (code/config): `! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/prometheus/ --include='*.yml' --include='*.yaml' --include='*.j2'`
3. Non-ASCII: `! grep -rPl '[^\x00-\x7F]' roles/prometheus/ --include='*.yml' --include='*.yaml' --include='*.j2'`
4. Vault gate (D-55): `! grep -rE '{{ *vault_' roles/prometheus/`
5. Idempotency: `! grep -rE 'state:\s*restarted' roles/prometheus/`
6. OPS-06: `grep -q "restart_policy:" roles/prometheus/tasks/main.yml` AND `grep -q "healthcheck:" roles/prometheus/tasks/main.yml`.
  </action>
  <verify>
    <automated>grep -qE "^\| \`prometheus\`\s*\|.*\|\s*☑\s*\|" roles/README.md &amp;&amp; ! grep -rE 'image:.*:latest' roles/prometheus/ &amp;&amp; ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/prometheus/ --include='*.yml' --include='*.yaml' --include='*.j2' &amp;&amp; ! grep -rPl '[^\x00-\x7F]' roles/prometheus/ --include='*.yml' --include='*.yaml' --include='*.j2' &amp;&amp; ! grep -rE '{{ *vault_' roles/prometheus/ &amp;&amp; ! grep -rE 'state:\s*restarted' roles/prometheus/ &amp;&amp; grep -q "restart_policy:" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "healthcheck:" roles/prometheus/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] roles/README.md prometheus row ticked.
    - [ ] All six gates pass (see verify command).
  </acceptance_criteria>
  <done>roles/README.md row `☑`; all six gates green.</done>
</task>

</tasks>

<verification>
**Static verification:**

1. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
2. All eleven task-level acceptance_criteria pass.
3. `find roles/prometheus -type f | sort` returns: defaults/main.yml, handlers/main.yml, meta/main.yml, tasks/main.yml, tasks/verify.yml, templates/prometheus.yml.j2, templates/rules-baseline.yml.j2, templates/rules-extras.yml.j2, README.md.
4. rules-baseline.yml.j2 contains all FOUR alert names AND uses `otelcol_receiver_refused_*` (NOT `processor_refused_*`).
5. rules-baseline.yml.j2 contains `container_restarts_total` (D-51 OTel-translated metric name).
6. prometheus.yml.j2 contains `remote_write` block targeting mimir:9009/api/v1/push.
7. roles/README.md row ticked.

**Live verification (deferred to Phase 3 verification stage):**

8. `ansible-playbook --tags prometheus` completes; Prometheus container healthy or running.
9. `curl http://prometheus:9090/-/ready` returns 200.
10. `curl http://prometheus:9090/api/v1/targets` shows otel_self, otel_metrics, node_exporter as `up`.
11. `curl http://prometheus:9090/api/v1/rules` returns all four baseline rule names.
12. Second back-to-back run reports `changed=0` for prometheus tag.

</verification>

<success_criteria>
- [ ] `roles/prometheus/` directory contains full canonical layout (defaults, tasks/main, tasks/verify, three templates, handlers, meta, README).
- [ ] All eleven task-level acceptance_criteria pass.
- [ ] All six per-role port-acceptance gates pass.
- [ ] roles/README.md status table row for prometheus shows `☑`.
- [ ] playbooks/deploy_docker.yml contains `role: prometheus` after `role: opentelemetry`.
- [ ] inventory/example-homelab/group_vars/all/prometheus.yml exists with operator knobs.
- [ ] `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
- [ ] RESEARCH correction #2 (`otelcol_receiver_refused_*` prefix) baked into rules-baseline.yml.j2 -- verified by grep.
- [ ] D-25 audit enforced -- forbidden Prometheus CLI flags absent from tasks/main.yml.
- [ ] INGEST-02 + INGEST-03 marked satisfied; live UAT deferred.
</success_criteria>

<output>
After completion, create `.planning/phases/03-ingest-plane/03-03-prometheus-SUMMARY.md` documenting: image probe outcome, the four baseline rules + extension knob shape, the OTelCollectorDroppingSignals prefix correction confirmation, D-25 deviation list, and execute-time surprises.
</output>
</content>
</invoke>