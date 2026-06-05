# roles/opentelemetry

Deploys [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib)
0.152.0 as the OTLP ingest gateway for Telemetron. Receives OTLP/gRPC
on `:4317` and OTLP/HTTP on `:4318` from any producer (operator
applications, host-running services, future SDKs) and fans signals
out to the Phase-2 backends:

- **Traces** -> Tempo via OTLP gRPC at `tempo:14317` (Phase-2 D-29
  internal-only port; `tls.insecure: true` on the Docker bridge).
- **Logs** -> Loki via `otlphttp/loki` to `http://loki:3100/otlp`
  (D-44 AMENDED -- see "Loki exporter replaced by otlphttp" below).
- **Metrics** -> Prometheus pull-scrape on `:8889` by default
  (`telemetron_otel_metrics_path: prometheus`), or
  `prometheusremotewrite` direct-push to Mimir on the
  `remote_write` flip (D-43 forward-compat).

Also surfaces the `docker_stats` receiver which feeds the
`container_restarts_total` series consumed by Plan 03-03's
ContainerRestartLoop alert rule (D-51).

Mirrors the canonical role template established by `roles/garage`,
`roles/loki`, `roles/tempo`, `roles/mimir`, and `roles/node_exporter`
-- same defaults layout, same handler discipline (W6 single handler),
same in-network verify pattern (W8), same Docker HEALTHCHECK /
running-state pre-poll (D-10a), same OPS-03 README schema.

## What this role does

1. Renders `/opt/telemetron/opentelemetry/config.yaml` from
   `templates/config.yaml.j2` (production OTel config).
2. Renders `/opt/telemetron/opentelemetry/verify-config.yaml` from
   `templates/verify-config.yaml.j2` (verify-only config used by the
   D-54 approach (a) one-shot in `tasks/verify.yml`).
3. Detects the host's `docker` group GID via `ansible.builtin.getent`
   (D-52 / RESEARCH Q6 Approach A).
4. Pulls the pinned image and runs the `opentelemetry` container on
   the `telemetron` Docker bridge network with `groups: [<docker-gid>]`
   and a read-only Docker socket bind-mount at `/var/run/docker.sock`.
5. **As a blocking final task**, runs the verify suite: HEALTHCHECK or
   State.Running poll, OTLP HTTP probes against all three signal
   endpoints, static config grep + GOMEMLIMIT env check, then a D-54
   approach-(a) one-shot OTel container exercising
   `prometheusremotewrite` to Mimir.

## What metrics are collected

The OTel Collector forwards OTLP-pushed metrics from external
producers AND emits its own self-telemetry + Docker container
telemetry via the `docker_stats` receiver.

**Self-telemetry** (exposed on `:8888`; scraped by Prometheus as job
`otel_self` -- Plan 03-03):

- `otelcol_receiver_accepted_*` / `otelcol_receiver_refused_*` --
  per-receiver acceptance counters (Plan 03-03's
  OTelCollectorDroppingSignals alert consumes
  `otelcol_receiver_refused_spans|log_records|metric_points`).
- `otelcol_exporter_send_failed_*` -- per-exporter failure counters.
- `otelcol_processor_batch_*` -- batch processor throughput.
- `otelcol_process_*` -- process-level CPU / memory / GC.

**Docker container telemetry** (via `docker_stats` receiver; D-51 /
D-53; scope = ALL containers, no `excluded_images` filter):

- `container.cpu.usage.total`
- `container.memory.usage.total`
- `container.network.io.usage.tx.bytes` / `.rx.bytes`
- `container.uptime` -- **OPT-IN at the receiver level** per RESEARCH
  Finding 4 (default-disabled).
- `container.restarts` -- **OPT-IN at the receiver level** per
  RESEARCH Finding 4. After OTel-to-Prometheus translation the metric
  appears as `container_restarts_total` (Plan 03-03's
  ContainerRestartLoop alert rule expects this exact name).

**Application metrics** (received via OTLP; exposed on `:8889` when
`telemetron_otel_metrics_path: prometheus`; scraped by Prometheus as
job `otel_metrics`).

## Modes

D-43 forward-compat: the metrics pipeline can target either Prometheus
(via the pull `prometheus` exporter) or Mimir (via the push
`prometheusremotewrite` exporter). Both exporters are **declared
unconditionally** in `config.yaml.j2`; only the pipeline reference
flips via the inventory knob.

| `telemetron_otel_metrics_path` | Metrics pipeline exporter | Path | When |
|---|---|---|---|
| `prometheus` (default) | `prometheus` (pull on `:8889`) | OTel -> Prometheus scrape -> Prometheus remote_write -> Mimir | Default. Single ingest path into Mimir; everything that lands in Mimir came through Prometheus. Diagnostic-clarity bias. |
| `remote_write` | `prometheusremotewrite` (push) | OTel -> Mimir direct | Flip if Prometheus is removed/replaced or if you want to skip the scrape hop for OTLP-pushed metrics. No role rewrite required. |

The verify task always exercises the `prometheusremotewrite` path via
the D-54 approach-(a) one-shot, regardless of the production knob --
this proves the forward-compat exporter works end-to-end.

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `opentelemetry_image` | `otel/opentelemetry-collector-contrib` | Image (do not change -- Core lacks Loki + docker_stats) |
| `opentelemetry_image_tag` | `0.152.0` | Pinned tag |
| `opentelemetry_container_name` | `opentelemetry` | DNS name on the telemetron network |
| `opentelemetry_container_alias` | `otel` | Short DNS alias on the telemetron network |
| `opentelemetry_publish_otlp` | `true` | Publish `:4317` + `:4318` to host. Set false if all producers are on the Docker network |
| `opentelemetry_otlp_grpc_port` | `4317` | OTLP gRPC ingest |
| `opentelemetry_otlp_http_port` | `4318` | OTLP HTTP ingest |
| `opentelemetry_self_metrics_port` | `8888` | Self-metrics scrape target (`otel_self` job, D-42) |
| `opentelemetry_app_metrics_port` | `8889` | App-metrics scrape target (`otel_metrics` job, D-42) |
| `opentelemetry_config_dir` | `/opt/telemetron/opentelemetry` | Host config dir |
| `telemetron_otel_metrics_path` | `prometheus` | D-43 forward-compat -- `prometheus` (default) or `remote_write` |
| `opentelemetry_loki_endpoint` | `http://loki:3100/otlp` | D-44 AMENDED -- otlphttp endpoint |
| `opentelemetry_tempo_endpoint` | `tempo:14317` | D-29 internal-only OTLP gRPC port |
| `opentelemetry_mimir_endpoint` | `http://mimir:9009/api/v1/push` | Mimir push endpoint |
| `opentelemetry_memory_limit` | `512m` | Docker container hard limit |
| `opentelemetry_gomemlimit` | `400MiB` | D-45 ratio: 80% of mem_limit (Go runtime budget) |
| `opentelemetry_memory_limiter_limit_mib` | `260` | D-45 ratio: 65% of GOMEMLIMIT (Pitfall 5) |
| `opentelemetry_memory_limiter_spike_limit_mib` | `80` | D-45 ratio: 20% of GOMEMLIMIT (Pitfall 5) |
| `opentelemetry_memory_limiter_check_interval` | `1s` | memory_limiter poll interval |
| `opentelemetry_batch_timeout` | `10s` | batch processor max wait |
| `opentelemetry_batch_send_batch_size` | `1024` | batch target |
| `opentelemetry_batch_send_batch_max_size` | `2048` | batch hard cap |
| `opentelemetry_sending_queue_num_consumers` | `4` | D-45 per-exporter resilience |
| `opentelemetry_sending_queue_size` | `1000` | D-45 per-exporter resilience |
| `opentelemetry_retry_initial_interval` | `5s` | D-45 per-exporter resilience |
| `opentelemetry_retry_max_interval` | `30s` | D-45 per-exporter resilience |
| `opentelemetry_retry_max_elapsed_time` | `300s` | D-45 per-exporter resilience |
| `opentelemetry_docker_stats_endpoint` | `unix:///var/run/docker.sock` | docker_stats receiver socket |
| `opentelemetry_docker_stats_collection_interval` | `30s` | docker_stats poll |
| `opentelemetry_docker_stats_timeout` | `5s` | docker_stats timeout |
| `opentelemetry_docker_stats_api_version` | `1.25` | Docker Engine API version |
| `opentelemetry_docker_socket_host_path` | `/var/run/docker.sock` | Host-side socket for bind-mount |
| `opentelemetry_healthcheck_enabled` | `true` | Conditional HEALTHCHECK; flip false to fall back to State.Running |
| `opentelemetry_healthcheck_test` | `["CMD", "/otelcol-contrib", "--version"]` | Outcome B binary-alive proxy |
| `opentelemetry_restart_policy` | `unless-stopped` | OPS-06 |
| `opentelemetry_network` | `telemetron` | Docker network |
| `opentelemetry_tz` | `Etc/UTC` | Container timezone (Pitfall 6) |
| `opentelemetry_curl_image` | `curlimages/curl` | Verify probe image |
| `opentelemetry_curl_image_tag` | `8.10.1` | Pinned tag |

## Vault keys

None (Phase 3 D-55). The OTel Collector does not authenticate against
any Phase-2 backend in M1 (Loki `auth_enabled: false`, Mimir
`multitenancy_enabled: false`, Tempo single-tenant). Future hardening
that introduces backend auth would add a `vault_opentelemetry_*` key
surface.

## Tags

- `opentelemetry` -- runs the whole role (D-24 single tag per role)

## Volumes

None (OTel Collector is stateless). Two file bind-mounts and one
unix-socket bind-mount:

| Mount | Target | Mode | Purpose |
|-------|--------|------|---------|
| `/opt/telemetron/opentelemetry/config.yaml` | `/etc/otelcol-contrib/config.yaml` | ro | Production config (loaded via `--config=` command) |
| `/opt/telemetron/opentelemetry/verify-config.yaml` | `/etc/otelcol-contrib/verify-config.yaml` | ro | Verify-only config; never loaded by production container |
| `/var/run/docker.sock` | `/var/run/docker.sock` | ro | docker_stats receiver socket (D-52) |

## Backup

No operator state to preserve.

## Uninstall

```bash
ansible-playbook playbooks/undeploy_docker.yml --tags opentelemetry --ask-vault-pass
```

No named volume to preserve. To also remove this role's pinned Docker
image: `--extra-vars telemetron_purge_images=true` (irreversible).

See `docs/quickstart.md#removing-telemetron` for the full undeploy story
(purge flags, manual fallback, order-of-operations).

## Healthcheck

OTel Collector Contrib 0.152.0 is distroless. The default Docker
HEALTHCHECK uses `/otelcol-contrib --version` as a binary-alive proxy
(Outcome B per the canonical conditional-HEALTHCHECK pattern), and
the authoritative readiness gate is the verify task's in-network OTLP
HTTP probes (`/v1/traces`, `/v1/logs`, `/v1/metrics`).

Three possible outcomes (same shape as mimir/tempo/node_exporter):

1. **Outcome A -- native --health flag present:** set
   `opentelemetry_healthcheck_test: ["CMD", "/otelcol-contrib", "--health"]`.
2. **Outcome B -- only --version proxy (default):** Docker HEALTHCHECK
   uses `CMD ["/otelcol-contrib", "--version"]`.
3. **Outcome C -- no flag at all:** set
   `opentelemetry_healthcheck_enabled: false`. Docker HEALTHCHECK is
   omitted entirely; OPS-06 compliance via the verify task's
   `State.Running` poll + OTLP HTTP probes.

The plan that ports this role probes the image at execute time and
selects the actual shape. PITFALLS Pitfall B documents the distroless
trap.

## Operator access (no host publish by default per D-30, except OTLP)

OTLP ingest ports (`:4317` + `:4318`) ARE published to the host by
default (`opentelemetry_publish_otlp: true`) so external producers
can reach the collector without needing to join the telemetron
Docker network. The Prometheus scrape targets (`:8888` self-metrics
and `:8889` app-metrics) STAY INTERNAL ALWAYS -- Prometheus reaches
them via Docker DNS (D-42 / Plan 03-03 scrape configs).

For operator inspection of the internal-only ports, use SSH local-forward:

```bash
ssh -L 8888:localhost:8888 <homelab-host>
ssh -L 8889:localhost:8889 <homelab-host>
curl http://localhost:8888/metrics    # OTel self-telemetry
curl http://localhost:8889/metrics    # OTLP-pushed app metrics
```

## Security model

- **OTLP ports published; Prometheus scrape ports internal.** OTLP
  acceptance is the operator-facing surface; metrics are
  scraped-by-Prometheus-only.
- **Docker socket bind-mount is read-only.** Kernel-level write block
  on the host side of the bind.
- **Container joins host's docker group via group_add (Approach A).**
  Not root-as-OTel; not socket-proxy (deferred); least-privilege
  given the M1 fixed-component-list constraint.
- **No backend auth in M1.** All telemetron-bridge traffic is
  unauthenticated; trust boundary is the Docker network.

## Threat Model (D-52 Docker socket)

The Docker socket bind-mount is the load-bearing security
consideration for this role. Three threat-mitigation layers:

1. **Read-only at the kernel level.** The bind-mount has `:ro` so a
   compromised OTel container cannot write to the socket file itself
   -- kernel-level write block.
2. **API-layer access remains.** Docker uses HTTP-over-Unix-socket for
   its API; a compromised OTel binary that has the socket file open
   could still issue Docker API POST requests (start a privileged
   container, escalate to host root). The `:ro` bind-mount does NOT
   block this at the API layer.
3. **Acceptable for M1 homelab single-host.** The operator already
   owns the host; OTel runs Telemetron-published images; the trust
   boundary is the operator's choice of what to deploy on the host.

**Future hardening (deferred per CLAUDE.md fixed-component-list
constraint for M1):** drop a [Tecnativa
`docker-socket-proxy`](https://github.com/Tecnativa/docker-socket-proxy)
sidecar between OTel and the Docker socket. The proxy exposes only
the read-only subset of the Docker Engine API that `docker_stats`
needs (containers/json, containers/<id>/stats), blocking
container-create / exec / start API verbs at the API layer. This
collapses the threat model to the same level as a kernel-RO mount
PLUS API-layer least-privilege. Recommended for operators deploying
Telemetron alongside less-trusted workloads.

**Approach A vs. Approach B (RESEARCH Q6):** the role uses Approach
A (container joins host's docker group via `group_add`) rather than
Approach B (run as root). Approach A is least-privilege under the
fixed M1 component list; Approach B would have given the OTel
process full root inside the container, which is unnecessary for
docker_stats read-only operation.

## Idempotency

Per OPS-04: running the playbook twice in a row reports `changed=0`.

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags opentelemetry
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags opentelemetry
# ...second run: changed=0
```

Config changes notify a single `docker restart opentelemetry` handler
(W6); `state: restarted` is never used (Pitfall 8).

## Port-acceptance gates

All six pass on `roles/opentelemetry/` (with the grep gate scoped to
code/config files; this README's D-25 audit intentionally documents
the upstream-deviation history per the Phase-2 D-25 reinterpretation):

- **Image-pin (OPS-01):** zero floating-tag references.
- **Grep gate (Pitfall 9):** zero matches in code/config files for
  upstream-org leftovers.
- **Non-ASCII gate (OPS-05):** zero non-ASCII characters in the role.
- **Vault-discipline (OPS-02):** zero `{{ vault_* }}` references
  (D-55).
- **Idempotency (OPS-04):** twice-in-a-row run reports `changed=0`.
- **Healthcheck + restart-policy (OPS-06):** `docker inspect` returns
  `healthy` (Outcome A/B) or the verify task's State.Running + OTLP
  probe gate (Outcome C); restart policy `unless-stopped`.

## Deviations from upstream INSPQ (D-25)

Per CONTEXT.md D-25, each Phase-3 role port is an opinionated
improvement pass over the upstream INSPQ role -- not a mirror
translation. TL;DR audit (machine-greppable):

- Dropped: K8s branches, `:latest`, French strings, default OTLP
  loopback, Jaeger receivers, UFW tasks, parallel batch processors,
  `actuator` filter, `America/Toronto` TZ, force-recreate logic,
  verbose otel_telemetry_logs knobs.
- Replaced: `_internal: 8888` + `_external: 9464` -> D-42's `:8888`
  (self) + `:8889` (app metrics); `loki` exporter -> `otlphttp/loki`
  (see "Loki exporter replaced by otlphttp" below).
- Added: `memory_limiter` processor + `GOMEMLIMIT` env (Pitfall 5);
  `sending_queue` + `retry_on_failure` on every push exporter;
  `docker_stats` receiver with `container.restarts` opt-in (D-51);
  `prometheusremotewrite` exporter (D-43 forward-compat); Threat
  Model section (D-52); per-pipeline LOCKED processor order
  `[memory_limiter, batch]` (D-45).
- Kept: `otel/opentelemetry-collector-contrib` image (Contrib
  distribution explicit -- Core lacks Loki and docker_stats).

### Loki exporter replaced by otlphttp (upstream removal)

The upstream INSPQ role used the `loki` exporter pointing at Loki's
`/loki/api/v1/push` endpoint. The `loki` exporter was **deprecated
2024-07-09** and **removed from the OpenTelemetry Collector Contrib
distribution in v0.131.0**. Telemetron pins v0.152.0, which does NOT
ship the `loki` exporter at all -- attempting to declare it would
fail collector startup with `"unknown exporter type 'loki'"`.

The canonical OTLP replacement is the `otlphttp` exporter pointing at
Loki's native `/otlp` endpoint, available since Loki 3.0 and required
for OTel logs in Loki 3.7.2 (the Phase-2 pin). Loki accepts the OTLP
payload directly without translation; no `X-Scope-OrgID` header is
required because Phase-2 D-26 set Loki's `auth_enabled: false`.

The replacement is structurally simple: the receiver `otlp` and the
processor pipeline are unchanged; the only diff is the exporter block
in `config.yaml.j2`. See RESEARCH.md Finding 2 for the upstream
source confirming the removal (PR 33169 + the v0.131.0 release
notes).

### Dropped (upstream-isms beyond the grep gate)

- `:latest` image tag -- replaced with explicit pin `0.152.0` per
  OPS-01.
- K8s branches (`kubernetes.yml`, `kubernetes-helm.yml`,
  `helm_*`, `servicemonitor_*`, `networkpolicy_*`,
  `instrumentation_*`) -- dropped; M1 ships Docker only per
  CLAUDE.md.
- French task names and comment strings throughout -- replaced with
  English per CLAUDE.md.
- `container_restart_policy: always` -- replaced with
  `unless-stopped` per OPS-06.
- `TZ: America/Toronto` -- replaced with `Etc/UTC` per Pitfall 6.
- Default `otel_exporters_otlp` loopback (127.0.0.1) -- replaced
  with `0.0.0.0:4317/4318` so OTLP is reachable from other
  containers on the telemetron bridge.
- Parallel `batch_traces` / `batch_logs` / `batch_metrics` legacy
  processors -- dropped; single `batch` processor in every pipeline
  is the current canonical form.
- UFW host-firewall tasks -- dropped; Telemetron does not manage
  the host firewall.
- Jaeger receivers (`jaeger_grpc`, `thrift_compact`, `thrift_binary`,
  `thrift_http`) -- dropped; OTLP is the single ingest protocol per
  CLAUDE.md tech-stack.
- `actuator` path filter -- INSPQ-specific Spring Boot pattern;
  out of scope.
- `force-recreate-on-image-change` logic -- replaced with
  `recreate: false` + handler-driven restart (Pitfall 8).
- `otel_telemetry_logs_*` verbose self-log knobs -- dropped; the
  collector's stdout is already structured.

### Replaced

- `otel_port_prometheus_endpoint_internal: 8888` +
  `otel_port_prometheus_endpoint_external: 9464` -> D-42's `:8888`
  (self) + `:8889` (app metrics). The upstream `:9464` was
  INSPQ-specific.
- `loki` exporter -> `otlphttp/loki` (see subsection above).

### Added (Pitfall 5 mitigation pack)

- `memory_limiter` processor + `GOMEMLIMIT` env -- the upstream
  config had NEITHER, which is the single highest-impact
  reliability footgun for OTel Collector (Pitfall 5).
- `sending_queue` + `retry_on_failure` on every push exporter --
  the upstream config had neither; without them a transient backend
  hiccup loses data.
- `docker_stats` receiver with `container.restarts` AND
  `container.uptime` opt-in -- the upstream had no container-restart
  story (D-51).
- `prometheusremotewrite` exporter declared unconditionally (D-43
  forward-compat) -- the upstream metrics path was Prometheus-only.
- Threat Model section (D-52) -- the upstream documented nothing
  on Docker-socket security.
- Per-pipeline LOCKED processor order `[memory_limiter, batch]`
  (D-45) -- the upstream had no order discipline.

### Kept (got it right)

- `otel/opentelemetry-collector-contrib` image (Contrib explicit) --
  the Core distribution lacks the Loki and docker_stats components
  Telemetron needs.

## D-44 amendment note

The D-44 decision in `.planning/phases/03-ingest-plane/03-CONTEXT.md`
named the `loki` exporter as the OTel->Loki path. RESEARCH.md Finding
2 caught that the `loki` exporter has been removed from contrib in
v0.131.0 (Telemetron pins v0.152.0). This README's "Deviations"
section subheading "Loki exporter replaced by otlphttp (upstream
removal)" documents the amendment; the production config.yaml.j2
ships `otlphttp/loki -> http://loki:3100/otlp` with `D-44 AMENDED`
inline-cited in the file header.

## Deprecation notes

None for M1. Future hardening: drop a Tecnativa `docker-socket-proxy`
sidecar between OTel and the Docker socket (see Threat Model
section). The `loki` exporter is already gone from this role and
will not return.
