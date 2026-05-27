# roles/prometheus

Deploys [Prometheus](https://prometheus.io/) 3.11.3 on a single Docker
host. Prometheus is Telemetron's short-term metrics + alerting-eval
plane; it scrapes the OTel Collector (self-metrics + app-metrics) and
node_exporter, evaluates baseline alert rules, and `remote_write`s
everything to Mimir for long-term retention.

Mirrors the canonical role template established by `roles/garage`,
`roles/loki`, `roles/tempo`, `roles/mimir`, `roles/node_exporter`, and
`roles/opentelemetry` -- same defaults layout, same handler discipline
(W6 single handler), same in-network verify pattern (D-54), same
conditional HEALTHCHECK / running-state pre-poll (D-10a), same OPS-03
README schema.

## What this role does

1. Renders `/opt/telemetron/prometheus/prometheus.yml` from
   `templates/prometheus.yml.j2` (global + rule_files + remote_write +
   three default scrape jobs + operator extension block).
2. Renders `/opt/telemetron/prometheus/rules/baseline.yml` from
   `templates/rules-baseline.yml.j2` (four baseline alert rules).
3. Renders `/opt/telemetron/prometheus/rules/extra.yml` from
   `templates/rules-extras.yml.j2` (operator-supplied rules; empty by
   default).
4. Ensures the named Docker volume `telemetron_prometheus_data` exists.
5. Starts the `prometheus` container on the `telemetron` Docker bridge
   network. Container port `9090` is NOT published to the host by
   default (`prometheus_publish_host: false`).
6. **As a blocking final task**, polls Prometheus readiness via
   `community.docker.docker_container_info` + an in-network curl to
   `/-/ready`, then asserts the three default scrape jobs are reporting
   targets `up`, and finally asserts all four baseline alert rule
   names are loaded.

## Default scrape targets

| Job | Target | Source |
|-----|--------|--------|
| `otel_self` | `otel:8888` | OTel Collector self-metrics (D-42; source of `otelcol_receiver_refused_*` signals consumed by the `OTelCollectorDroppingSignals` alert) |
| `otel_metrics` | `otel:8889` | OTel Collector Prometheus-format app metrics (D-42; source of `container_restarts_total` consumed by the `ContainerRestartLoop` alert) |
| `node_exporter` | `node-exporter:9100` | Host metrics from Plan 03-01 (INGEST-08) |

Each default scrape job applies a `metric_relabel_configs` block with
the Pitfall 3 mitigation set: drop `pod_uid|container_id|request_id|trace_id`
and the catch-all `.*_id` regex. Operators extend the relabel set per
job by editing the template directly, or add full extra scrape jobs
via `prometheus_extra_scrape_configs` in inventory.

## Baseline alert rules

The role ships four baseline alert rules in
`templates/rules-baseline.yml.j2` (group name `telemetron.baseline`,
evaluation interval 30s):

| Alert | Expression | For | Severity |
|-------|------------|-----|----------|
| `HostDown` | `up == 0` | 2m | critical |
| `FilesystemAlmostFull` | `(node_filesystem_avail_bytes{fstype!~"tmpfs\|overlay\|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs\|overlay\|squashfs"}) < 0.15` | 5m | warning |
| `ContainerRestartLoop` | `increase(container_restarts_total[10m]) >= 3` | 0m | warning |
| `OTelCollectorDroppingSignals` | `(rate(otelcol_receiver_refused_spans[5m]) + rate(otelcol_receiver_refused_log_records[5m]) + rate(otelcol_receiver_refused_metric_points[5m])) > 0` | 5m | warning |

**Note on OTelCollectorDroppingSignals (RESEARCH correction #2):** the
metric prefix is `otelcol_receiver_refused_*`, NOT
`otelcol_processor_refused_*`. The receiver-side counters increment
when a downstream pipeline rejects data (memory_limiter saturation,
exporter retry exhaust, batch overflow), per the OpenTelemetry
internal-telemetry docs. Any guidance saying `processor_refused_*` is
the canonical name is wrong and would result in a permanently-firing
zero-rate alert (or, more likely, no firing at all).

**Note on ContainerRestartLoop (D-51):** the `container_restarts_total`
metric is the OTel-to-Prometheus translation of the
`container.restarts` resource attribute emitted by the OTel docker_stats
receiver -- which Plan 03-02 ships with `container.restarts.enabled:
true` opt-in. Without that opt-in, the metric never appears and the
alert silently does nothing.

## Operator-extensible alert rules (prometheus_extra_rules)

Define operator-specific alert rules in inventory as a list of dicts
keyed by `name`, `expr`, `for`, `labels` (dict), `annotations` (dict).
They render into `rules/extra.yml` under the
`telemetron.operator-extras` group (interval 30s) with sorted-keys
discipline (D-20) for idempotent renders.

Example:

```yaml
prometheus_extra_rules:
  - name: MyAppDown
    expr: up{job="my-app"} == 0
    for: 1m
    labels:
      severity: critical
      team: ops
    annotations:
      summary: "my-app is down"
      description: "The my-app instance has been unreachable for >1 minute."
  - name: MyAppHighLatency
    expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="my-app"}[5m])) by (le)) > 1.0
    for: 5m
    labels:
      severity: warning
      team: ops
    annotations:
      summary: "my-app p99 latency > 1s"
```

When `prometheus_extra_rules` is `[]` (the default), the rendered
`rules/extra.yml` contains a group with an empty rules list -- legal
YAML, accepted by Prometheus, zero alerts evaluated.

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `prometheus_image` | `prom/prometheus` | Image (do not change) |
| `prometheus_image_tag` | `v3.11.3` | Pinned tag (OPS-01) |
| `prometheus_container_name` | `prometheus` | DNS name on the `telemetron` network |
| `prometheus_publish_host` | `false` | Publish :9090 to host (`false` / `true` / `127.0.0.1`) |
| `prometheus_http_port` | `9090` | HTTP API port |
| `prometheus_data_volume` | `telemetron_prometheus_data` | Named Docker volume (TSDB) |
| `prometheus_data_path` | `/prometheus` | In-container TSDB path (image default) |
| `prometheus_config_dir` | `/opt/telemetron/prometheus` | Host config bind-mount source (D-18) |
| `prometheus_retention_time` | `15d` | TSDB retention (Claude's Discretion: 15d > Mimir's 12h query_store_after) |
| `prometheus_global_scrape_interval` | `15s` | Global scrape interval |
| `prometheus_global_evaluation_interval` | `15s` | Rule evaluation interval |
| `prometheus_cluster_label` | `telemetron-homelab` | external_labels.cluster value |
| `prometheus_remote_write_url` | `http://mimir:9009/api/v1/push` | Mimir push endpoint (INGEST-02) |
| `prometheus_remote_write_queue_capacity` | `10000` | remote_write queue capacity |
| `prometheus_remote_write_max_samples_per_send` | `2000` | Max samples per batch |
| `prometheus_remote_write_batch_send_deadline` | `5s` | Max batch latency |
| `prometheus_remote_write_min_shards` | `1` | Min concurrent send shards |
| `prometheus_remote_write_max_shards` | `5` | Max concurrent send shards |
| `prometheus_otel_self_target` | `otel:8888` | OTel self-metrics scrape target |
| `prometheus_otel_metrics_target` | `otel:8889` | OTel app-metrics scrape target |
| `prometheus_node_exporter_target` | `node-exporter:9100` | node_exporter scrape target |
| `prometheus_default_relabel_drop_regex` | `pod_uid\|container_id\|request_id\|trace_id` | Per-job labeldrop (Pitfall 3) |
| `prometheus_default_relabel_id_catchall_regex` | `.*_id` | Per-job catch-all labeldrop (Pitfall 3) |
| `prometheus_extra_scrape_configs` | `[]` | Operator-extensible scrape jobs |
| `prometheus_extra_rules` | `[]` | Operator-extensible alert rules (INGEST-03) |
| `prometheus_extra_relabel_configs` | `[]` | Operator-extensible relabel block (reserved) |
| `prometheus_healthcheck_enabled` | `true` | Override to false if image probe shows no useful flag |
| `prometheus_healthcheck_test` | `["CMD", "/bin/prometheus", "--version"]` | Default binary-alive proxy (Outcome B) |
| `prometheus_restart_policy` | `unless-stopped` | Container restart policy |
| `prometheus_memory_limit` | `1g` | Container memory limit |
| `prometheus_network` | `telemetron` | Docker network |
| `prometheus_tz` | `Etc/UTC` | Container timezone |
| `prometheus_curl_image` / `_tag` | `curlimages/curl:8.10.1` | Verify one-shot image pin |

## Vault keys

None (Phase 3 D-55). Prometheus has no auth surface in M1; Mimir's
single-tenant `anonymous` (D-26) means no remote_write credentials.

## Tags

- `prometheus` -- runs the whole role (D-24 single tag per role)

## Modes

Single mode -- monolithic Prometheus 3.11.3 single-server. Distributed
modes (federation, hierarchical) are deferred to a future milestone.

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `telemetron_prometheus_data` (named) | `/prometheus` | TSDB data root. Persistent across recreates. |
| `/opt/telemetron/prometheus/prometheus.yml` (bind) | `/etc/prometheus/prometheus.yml` (ro) | Rendered config |
| `/opt/telemetron/prometheus/rules/baseline.yml` (bind) | `/etc/prometheus/rules/baseline.yml` (ro) | Rendered baseline rule group |
| `/opt/telemetron/prometheus/rules/extra.yml` (bind) | `/etc/prometheus/rules/extra.yml` (ro) | Rendered operator-extras rule group |

## Retention

`prometheus_retention_time: 15d` (default). Sized deliberately:

- **15d > Mimir's `query_store_after: 12h`** (Phase-2 D-36). Grafana's
  Prometheus datasource path resolves recent queries (<= 12h) against
  Prometheus's local TSDB; older queries fall back to Mimir via
  remote_read. The 15-day local window ensures any recent query that
  Mimir hasn't fully synced yet still has a local answer.
- **Override path:** edit `inventory/example-homelab/group_vars/all/prometheus.yml`
  and set `prometheus_retention_time: 30d` (or `7d`, etc.). No role
  change needed.
- **Size-based retention is intentionally not exposed** (D-25:
  upstream INSPQ used `prometheus_retention_size`; Telemetron drops it
  because mixed time+size retention has surprising eviction order on
  small homelab disks).

## Healthcheck

Prometheus 3.11.3 is built on a distroless base -- no shell, no curl,
no wget, and no documented native `--health` binary flag as of
research. Same approach as the Mimir, Tempo, and node_exporter roles:
the Docker HEALTHCHECK uses a binary-alive proxy
(`/bin/prometheus --version`) to satisfy OPS-06, and the authoritative
readiness gate is the verify task's in-network curl to
`http://prometheus:9090/-/ready` (returns 200 with body `Prometheus
Server is Ready.` when fully started).

Three possible outcomes selectable at execute time:

1. **Outcome A -- native --health flag present:** set
   `prometheus_healthcheck_test: ["CMD", "/bin/prometheus", "--health"]`.
2. **Outcome B -- only --version proxy (default):** Docker HEALTHCHECK
   uses `CMD ["/bin/prometheus", "--version"]`. OPS-06 compliance via
   the binary-alive proxy + the verify task's authoritative `/-/ready`
   curl probe.
3. **Outcome C -- no flag at all:** set
   `prometheus_healthcheck_enabled: false`. Docker HEALTHCHECK omitted
   entirely; OPS-06 compliance via the verify task's `State.Running`
   poll + the `/-/ready` curl probe.

The plan that ported this role selected Outcome B as the safe default;
the verify task's in-network `/-/ready` + `/api/v1/targets` +
`/api/v1/rules` chain is the authoritative readiness gate regardless
of which Outcome is active.

## Operator access (no host publish by default per D-30)

Inter-component traffic on the `telemetron` bridge reaches Prometheus
at `http://prometheus:9090`. Operator UI access from a workstation:

```bash
ssh -L 9090:localhost:9090 <homelab-host>
# In a browser:
#   http://localhost:9090/      -- Prometheus UI (graph, targets, alerts, rules)
#   http://localhost:9090/-/ready -- 200 OK when fully started
curl http://localhost:9090/api/v1/targets   # JSON: scrape target states
curl http://localhost:9090/api/v1/rules     # JSON: loaded rule groups
```

## Security model

- **Default: no host port publish.** Operator access via SSH local-forward.
- **No vault keys.** D-26 single-tenant Mimir means no credentials on
  remote_write; D-55 confirms no vault surface for Prometheus in M1.
- **Inter-component traffic on the `telemetron` bridge only.** Prometheus
  reaches OTel + node_exporter + Mimir over Docker DNS; never via the
  host network.
- **Rendered configs at mode 0640.** Operator-readable; container reads
  via UID-mapped bind-mount.
- **`--web.enable-lifecycle` is enabled** for SIGHUP-style runtime
  reload, but the role uses `docker restart` via the handler instead
  (simpler, OPS-04-clean).

## Idempotency

Per OPS-04: running the playbook twice in a row reports `changed=0`.

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags prometheus
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags prometheus
# ...second run: changed=0
```

Config changes notify a single `docker restart prometheus` handler
(W6); `state: restarted` is never used (Pitfall 8).

## Port-acceptance gates

All six pass on `roles/prometheus/` (with the grep gate scoped to
code/config files; the role README intentionally documents the
upstream-deviation audit per D-25):

- **Image-pin (OPS-01):** zero floating-tag references.
- **Grep gate (Pitfall 9):** zero matches in code/config files.
- **Non-ASCII gate (OPS-05):** zero non-ASCII characters in the role.
- **Vault-discipline (OPS-02):** zero `{{ vault_* }}` references in
  code/config (none needed -- single-tenant Mimir).
- **Idempotency (OPS-04):** twice-in-a-row run reports `changed=0`.
- **Healthcheck + restart-policy (OPS-06):** `docker inspect` returns
  `healthy` (Outcome A/B) or the verify task's `State.Running` +
  `/-/ready` probe gate (Outcome C); restart policy `unless-stopped`.

## Deviations from upstream INSPQ (D-25)

Per CONTEXT.md D-25, each role port is an opinionated improvement
pass -- not a mirror translation. The full audit:

- Dropped: K8s helm/operator branches, French strings, restart_policy `always`, `America/Toronto`, remote-write-receiver feature flag, otlp-receiver feature flag, URL-encoded alert rule format, `prometheus_retention_size`, `prometheus_alertmanager_alerting_rules` extension surface, UFW rules, `:latest` tag.
- Replaced: retention `30d` -> `15d` (Claude's Discretion).
- Replaced: nested `root_dir/data_dir/config_dir` layout -> flat `/opt/telemetron/prometheus/<file>` (Phase-1 D-18).
- Added: metric_relabel_configs labeldrop defaults per scrape job (Pitfall 3 mitigation pack).
- Added: four baseline alert rules (INGEST-03; upstream shipped empty `alerting_rules`).
- Added: default scrape jobs for OTel self/app metrics + node_exporter (D-42 + INGEST-08).
- Added: remote_write to Mimir as the M1 default (INGEST-02).
- Added: in-network verify one-shot (D-54) asserting /-/ready + targets + rules.
- Kept: single-server monolithic Prometheus.

**Dropped (upstream-isms beyond the grep gate):**

- `prometheus_image_version: "latest"` -- replaced with explicit pin
  `v3.11.3` per OPS-01.
- K8s deployment branches (helm chart, operator) -- dropped per M1
  Docker-only scope.
- `--web.enable-remote-write-receiver` flag and the
  `--enable-feature=remote-write-receiver` legacy variant -- dropped.
  Telemetron's Prometheus WRITES `remote_write` to Mimir; it does not
  RECEIVE remote_write traffic. Phase-2 Mimir already owns that role.
- `--web.enable-otlp-receiver` flag -- dropped for the same reason
  (Prometheus is not the OTLP ingress; the OTel Collector is, per
  Plan 03-02).
- `prometheus_retention_size` size-based retention -- dropped. Mixed
  time + size retention has surprising eviction order on small
  homelab disks; time-only retention is more predictable.
- `prometheus_alertmanager_alerting_rules` upstream extension surface
  -- replaced with the `prometheus_extra_rules` knob whose schema is
  documented above.
- URL-encoded alert rule format that the upstream used -- replaced
  with the canonical Prometheus YAML group form per RESEARCH Finding 8.
- UFW host firewall tasks -- dropped; Telemetron does not manage host
  firewall.
- `prometheus_container_restart_policy: "always"` -- replaced with
  `unless-stopped` per OPS-06.
- `America/Toronto` timezone hardcode -- replaced with `Etc/UTC` per
  Pitfall 6.
- French task names and var doc throughout -- replaced with English
  per CLAUDE.md.

**Replaced:**

- Retention default `30d` (upstream) -> `15d` (Telemetron M1). 15d is
  comfortably longer than Mimir's `query_store_after: 12h` so Grafana
  resolves recent queries against Prometheus while Mimir handles
  long-term retention. Claude's Discretion per D-35.
- `root_dir` / `data_dir` / `config_dir` nested layout (upstream)
  -> flat `/opt/telemetron/prometheus/<file>` (Phase-1 D-18).

**Added (missing pitfall guards in upstream):**

- **Pitfall 3 metric_relabel_configs labeldrop defaults** -- THE
  highest-leverage D-25 improvement. Every default scrape job ships
  with two `labeldrop` rules: the explicit
  `pod_uid|container_id|request_id|trace_id` set plus the
  catch-all `.*_id` regex. High-cardinality keys die at scrape time
  and never become active series. Upstream shipped zero of these.
- **Four baseline alert rules (INGEST-03)** -- upstream shipped an
  empty `alerting_rules` extension surface; Telemetron baselines:
  HostDown, FilesystemAlmostFull, ContainerRestartLoop,
  OTelCollectorDroppingSignals.
- **Default scrape jobs for OTel + node_exporter** -- upstream shipped
  an empty `prometheus_scrape_configs` list; Telemetron baselines
  three default jobs (otel_self, otel_metrics, node_exporter).
- **remote_write to Mimir as M1 default** (INGEST-02) -- upstream
  shipped without a remote_write block; Telemetron always remote_writes
  to `http://mimir:9009/api/v1/push` (no X-Scope-OrgID header per D-26).
- **In-network verify one-shot** (D-54) -- upstream shipped no
  post-deploy verification; Telemetron asserts /-/ready + /api/v1/targets
  + /api/v1/rules + four baseline rule names load before the role
  task completes.

**Kept from upstream (got it right):**

- Single-server monolithic Prometheus (vs. federation / Thanos / Cortex).
- 15s `scrape_interval` (homelab-sensible default).
- Named Docker volume for the TSDB (vs. host bind-mount).

## Deprecation notes

None for M1. Prometheus is the locked short-term metrics + alerting-eval
backend per CLAUDE.md tech-stack constraints; VictoriaMetrics
alternative is explicitly out of M1 scope.
