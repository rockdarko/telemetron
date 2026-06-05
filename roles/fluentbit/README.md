# roles/fluentbit

Deploys [Fluent Bit](https://fluentbit.io/) 4.2.3 on a single Docker
host. Fluent Bit is Telemetron's log shipper: it tails the host's
Docker container JSON logs by default and ships through the OTel
Collector (Plan 03-02) to Loki for long-term storage.

Mirrors the canonical role template established by `roles/garage`,
`roles/loki`, `roles/tempo`, `roles/mimir`, `roles/node_exporter`,
`roles/opentelemetry`, and `roles/prometheus` -- same defaults layout,
same handler discipline (W6 single handler), same in-network verify
pattern (D-54), same conditional HEALTHCHECK / running-state pre-poll
(D-10a), same OPS-03 README schema.

## What this role does

1. Renders `/opt/telemetron/fluentbit/fluent-bit.conf` from
   `templates/fluent-bit.conf.j2` ([SERVICE] block with the Pitfall 6
   mitigation pack + [INPUT] tail of Docker container JSON logs + D-48
   conditional extension inputs + D-47 label allowlist filter chain +
   D-49 opentelemetry [OUTPUT]).
2. Renders `/opt/telemetron/fluentbit/parsers.conf` from
   `templates/parsers.conf.j2` (docker JSON parser + level_extractor
   regex parser).
3. Ensures the named Docker volume `telemetron_fluentbit_buffer` exists
   (D-50 filesystem buffer; Phase-1 D-16 volume-prefix scheme).
4. Starts the `fluentbit` container on the `telemetron` Docker bridge
   network. Container port `2020` (HTTP server) is NOT published to
   the host by default (`fluentbit_publish_host: false`). Two bind
   mounts attach: `/var/lib/docker/containers` (RO, the tail source
   per D-46) and the buffer volume at `/var/log/flb-storage`.
5. **As a blocking final task**, polls Fluent Bit readiness via
   `community.docker.docker_container_info` + an in-network curl
   one-shot probing `http://fluentbit:2020/api/v1/health` for HTTP 200
   (per RESEARCH Q9 simplification -- end-to-end FB->Loki smoke is
   deferred to Phase 6 OPS-07).

## Default tail path (D-46 role inversion)

By default, Fluent Bit tails
`/var/lib/docker/containers/*/*-json.log` -- the standard Docker JSON
file driver location -- on the same host that runs the Telemetron
stack. Records are parsed with Fluent Bit's built-in `docker` JSON
parser.

**This INVERTS the upstream role pattern.** Upstream, Fluent Bit ran on
legacy hosts that emitted app-specific log files (no native OTel /
shipper), and scooped those files to a central observability host.
The single-host colocated FB-with-workloads model is the Telemetron M1
default; the upstream legacy-host-scoop use case is preserved as an
opt-in via the D-48 extension knobs below. See the user memory note
`project_fluentbit_role_shift.md` for the full role-inversion narrative.

## Loki label allowlist (D-47)

Fluent Bit applies five static / extracted labels to every shipped
record. High-cardinality fields (container_id, image_id, image_name,
full image tag) are intentionally NOT promoted to labels -- they flow
through as structured metadata on the Loki side. This is the
source-side Pitfall 4 mitigation (label explosion).

| Label     | Source                                                                 |
|-----------|------------------------------------------------------------------------|
| `host`    | `{{ ansible_hostname }}` rendered at deploy time (static literal)      |
| `env`     | `{{ telemetron_env | default('homelab') }}` rendered at deploy time    |
| `service_name` | Docker label `org.telemetron.service` (M1 convention: `telemetron`); fallback `unlabeled` |
| `job`     | Docker label `org.telemetron.job` (M1 convention: per-component); fallback container_name from JSON `Name` field |
| `level`   | regex-extracted from log line via `level_extractor` parser; `info` default |

The `service_name` and `job` labels are populated at runtime by a `[FILTER] lua`
script (`roles/fluentbit/files/enrich.lua`) that reads each source container's
`/var/lib/docker/containers/<id>/config.v2.json` -- the sibling of the JSON
log file Fluent Bit already tails. The script extracts the two Docker labels
`org.telemetron.service` and `org.telemetron.job` (M1 convention: each
telemetron stack role stamps these on its `docker_container` at creation
time), caches results per container_id with a 300-second TTL, and falls
back to `service_name=unlabeled` + `job=<container_name>` when a container is
not stamped. NO Docker socket is mounted -- the Lua filter only reads the
on-disk JSON files Fluent Bit already has RO access to via the bind-mount
from Plan 03-04.

## Labeling operator apps

Operator workloads colocated on the Telemetron Docker host opt into the
Loki label scheme by stamping two Docker labels on their own
containers at creation time:

| Label key                  | Value                              | Purpose                              |
|----------------------------|------------------------------------|--------------------------------------|
| `org.telemetron.service`   | a stable service identifier        | populates Loki `service_name` label  |
| `org.telemetron.job`       | a per-component identifier         | populates Loki `job` label           |

The Fluent Bit Lua filter (`roles/fluentbit/files/enrich.lua`) picks
up these labels from the container's `config.v2.json` on the host and
applies them to every log line shipped to Loki. Unlabeled operator
containers still ship logs -- they just land with `service_name=unlabeled`
and `job=<container_name>` until the operator stamps the convention
labels.

Stamping pattern in docker run:

```bash
docker run -d \
  --network telemetron \
  --label org.telemetron.service=myapp \
  --label org.telemetron.job=myapp-web \
  myapp:1.2.3
```

In docker-compose:

```yaml
services:
  myapp-web:
    image: myapp:1.2.3
    networks: [telemetron]
    labels:
      org.telemetron.service: myapp
      org.telemetron.job: myapp-web
```

In an Ansible role using `community.docker.docker_container`:

```yaml
- community.docker.docker_container:
    name: myapp-web
    image: myapp:1.2.3
    networks:
      - name: telemetron
    labels:
      org.telemetron.service: myapp
      org.telemetron.job: myapp-web
```

The eight Phase-1..3 telemetron stack roles (garage, loki, tempo, mimir,
node_exporter, opentelemetry, prometheus, fluentbit) all stamp these
labels per Plan 03-05; Phase 4/5 role ports inherit the convention via
the per-role port-acceptance checklist in `roles/README.md`.

## Extension knobs (D-48, all default-off)

The role exposes three knobs that conditionally add extra inputs to
the rendered config. All three default to `false` / `[]`; flip
selectively per host.

| Knob | Default | Effect |
|------|---------|--------|
| `fluentbit_tail_system_logs` | `false` | Adds an `[INPUT] tail` for `/var/log/{syslog,auth.log,kern.log,messages}`. Requires those files to be readable inside the container (bind-mount needed for non-trivial setups). |
| `fluentbit_tail_journald` | `false` | Adds an `[INPUT] systemd` for `/run/log/journal`. Linux-with-systemd only; requires bind-mount of `/run/systemd/journal/socket` on the docker_container task (NOT wired by default -- flip the knob and add the mount in `roles/fluentbit/tasks/main.yml` if needed). |
| `fluentbit_extra_tail_paths` | `[]` | List of arbitrary file paths; each entry emits one `[INPUT] tail` section. Preserves the upstream legacy-host-scoop use case as opt-in -- operators with hosts that ship app-specific log files keep their wiring. |

The default-off shape keeps the M1 happy path narrow (Docker JSON
tail only) while leaving the upstream pattern available without a
fork or a role rewrite.

## Transport (D-49)

The role ships via Fluent Bit's `opentelemetry` output plugin to the
OTel Collector at `http://otel:4318/v1/logs` (Plan 03-02 owns the
OTel role; the `otel` DNS alias is registered on the `telemetron`
bridge). The Collector then forwards to Loki via its `otlphttp/loki`
exporter (Plan 03-02 D-44 AMENDED). Wire format: OTLP/HTTP.

### FB->Loki direct path (alternative; not default)

Per INGEST-06, operators who want to bypass the OTel Collector and
ship Fluent Bit directly to Loki can replace the `[OUTPUT]` block in
the rendered config with the `loki` output plugin pointing at
`http://loki:3100/loki/api/v1/push`:

```ini
[OUTPUT]
    Name              loki
    Match             *
    Host              loki
    Port              3100
    Uri               /loki/api/v1/push
    Labels            host=$host,env=$env,service_name=$service_name,job=$job,level=$level
    Auto_Kubernetes_Labels off
    Line_Format       json
```

This is NOT exposed as a knob in M1 -- editing the `[OUTPUT]` block
in `templates/fluent-bit.conf.j2` is the path. It is documented here
because INGEST-06 names the FB->Loki direct path as a documented
alternative, and so that operators know the option exists when
debugging Collector-side issues.

## Buffer + timestamp discipline (D-50; Pitfall 6 mitigation pack)

Fluent Bit's biggest operational footgun is timestamp drift -- this
role bakes in the documented mitigations explicitly. THE single most
impactful one-liner is `Time_System_Timezone Etc/UTC` (eliminates DST
landmines). The full pack:

| Knob | Value | Purpose |
|------|-------|---------|
| `storage.type filesystem` | per-INPUT | Filesystem buffer survives container restart without log loss. |
| `storage.path /var/log/flb-storage/` | [SERVICE] | Bind-mounted to the `telemetron_fluentbit_buffer` named volume. |
| `storage.max_chunks_up 128` | [SERVICE] | Homelab-sized in-flight chunk window. |
| `Time_System_Timezone Etc/UTC` | [SERVICE] | Pitfall 6 Mode 1 -- DST drift mitigation (THE biggest one). |
| `Multiline_Flush 5` | [SERVICE] | Pitfall 6 Mode 3 -- fail-fast multiline aggregation bound. |
| `Read_from_Head false` | per-INPUT | Pitfall 6 Mode 4 -- don't replay pre-deploy logs on first boot. |
| `[FILTER] modify Add @timestamp ${ingest_time}` | filter chain | Pitfall 6 Mode 2 -- fallback @timestamp when source line has none. |

Each mitigation is inline-cited in `templates/fluent-bit.conf.j2`.

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `fluentbit_image` | `fluent/fluent-bit` | Image (do not change) |
| `fluentbit_image_tag` | `4.2.3` | Pinned tag (OPS-01); 4.x M1-stable, 5.x too new |
| `fluentbit_container_name` | `fluentbit` | DNS name on the `telemetron` network |
| `fluentbit_publish_host` | `false` | Publish :2020 to host (`false` / `true` / `127.0.0.1`) |
| `fluentbit_http_port` | `2020` | HTTP server port (/api/v1/health, /api/v1/metrics) |
| `fluentbit_config_dir` | `/opt/telemetron/fluentbit` | Host config bind-mount source (D-18) |
| `fluentbit_buffer_volume` | `telemetron_fluentbit_buffer` | Named Docker volume (filesystem buffer) |
| `fluentbit_docker_logs_path` | `/var/lib/docker/containers` | Host directory bind-mounted RO into the container (D-46) |
| `telemetron_env` | `homelab` | Static `env` label applied to all FB-shipped logs |
| `fluentbit_tail_system_logs` | `false` | D-48 extension: tail `/var/log/syslog,auth.log,...` |
| `fluentbit_tail_journald` | `false` | D-48 extension: ingest journald (needs systemd-socket bind-mount) |
| `fluentbit_extra_tail_paths` | `[]` | D-48 extension: list of arbitrary tail paths |
| `fluentbit_otel_host` | `otel` | OTel Collector DNS alias on the telemetron bridge (D-49) |
| `fluentbit_otel_port` | `4318` | OTel Collector OTLP/HTTP port |
| `fluentbit_otel_logs_uri` | `/v1/logs` | OTel Collector OTLP/HTTP logs path |
| `fluentbit_system_timezone` | `Etc/UTC` | [SERVICE] Time_System_Timezone (Pitfall 6 Mode 1) |
| `fluentbit_multiline_flush` | `5` | [SERVICE] Multiline_Flush seconds (Pitfall 6 Mode 3) |
| `fluentbit_storage_max_chunks_up` | `128` | [SERVICE] storage.max_chunks_up |
| `fluentbit_storage_backlog_mem_limit` | `50M` | [SERVICE] storage.backlog.mem_limit |
| `fluentbit_flush_interval` | `5` | [SERVICE] Flush seconds |
| `fluentbit_enrich_lua_path` | `/fluent-bit/etc/enrich.lua` | In-container path of the Plan 03-05 Lua enrichment script |
| `fluentbit_enrich_docker_root` | `/var/lib/docker/containers` | Host directory of Docker container JSON config files (RO bind-mount source) |
| `fluentbit_enrich_cache_ttl_seconds` | `300` | Per-container_id cache TTL in the Lua filter |
| `fluentbit_unlabeled_service` | `unlabeled` | Fallback `service` label for containers without `org.telemetron.service` |
| `fluentbit_unlabeled_job` | `unknown` | Fallback `job` when no `org.telemetron.job` and no container_name available |
| `fluentbit_level_regex` | `(?i)\b(?<level>INFO\|WARN\|ERROR\|FATAL\|DEBUG\|TRACE)\b` | level_extractor regex |
| `fluentbit_default_level` | `info` | Default level when regex does not match |
| `fluentbit_healthcheck_enabled` | `true` | Override to false if image probe shows no useful flag |
| `fluentbit_healthcheck_test` | `["CMD", "/fluent-bit/bin/fluent-bit", "--version"]` | Default binary-alive proxy (Outcome B) |
| `fluentbit_restart_policy` | `unless-stopped` | Container restart policy |
| `fluentbit_memory_limit` | `256m` | Container memory limit |
| `fluentbit_network` | `telemetron` | Docker network |
| `fluentbit_tz` | `Etc/UTC` | Container timezone |
| `fluentbit_curl_image` / `_tag` | `curlimages/curl:8.10.1` | Verify one-shot image pin |

## Vault keys

None (Phase 3 D-55). Fluent Bit has no auth surface in M1; OTel
Collector receives logs without auth on the telemetron bridge.

## Tags

- `fluentbit` -- runs the whole role (D-24 single tag per role)

## Modes

Single mode -- monolithic Fluent Bit 4.2.3 single-instance. Distributed
modes (forward-protocol fan-in, multi-region) are deferred to a future
milestone.

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `telemetron_fluentbit_buffer` (named) | `/var/log/flb-storage` | Filesystem buffer (D-50). Survives container restart without log loss. |
| `/var/lib/docker/containers` (bind) | `/var/lib/docker/containers` (ro) | Tail source (D-46) -- host's Docker container JSON logs. Read-only. |
| `/opt/telemetron/fluentbit/fluent-bit.conf` (bind) | `/fluent-bit/etc/fluent-bit.conf` (ro) | Rendered main config |
| `/opt/telemetron/fluentbit/parsers.conf` (bind) | `/fluent-bit/etc/parsers.conf` (ro) | Rendered parsers config |

## Backup

No operator state to preserve.

## Uninstall

```bash
ansible-playbook playbooks/undeploy_docker.yml --tags fluentbit --ask-vault-pass
```

Named volume `telemetron_fluentbit_buffer` is preserved by default. To
also remove it: `--extra-vars telemetron_purge_data=true` (irreversible).

See `docs/quickstart.md#removing-telemetron` for the full undeploy story
(purge flags, manual fallback, order-of-operations).

## Healthcheck

Fluent Bit 4.2.3 is built on a distroless base by default -- no shell,
no curl, no wget, and no documented native `--health` binary flag.
Same approach as the Mimir, Tempo, node_exporter, opentelemetry, and
prometheus roles: the Docker HEALTHCHECK uses a binary-alive proxy
(`/fluent-bit/bin/fluent-bit --version`) to satisfy OPS-06, and the
authoritative readiness gate is the verify task's in-network curl to
`http://fluentbit:2020/api/v1/health` (returns 200 when the HTTP
server has bound and the engine reports healthy).

Three possible outcomes selectable at execute time:

1. **Outcome A -- native --health flag present:** set
   `fluentbit_healthcheck_test: ["CMD", "/fluent-bit/bin/fluent-bit", "--health"]`.
2. **Outcome B -- only --version proxy (default):** Docker HEALTHCHECK
   uses `CMD ["/fluent-bit/bin/fluent-bit", "--version"]`. OPS-06
   compliance via the binary-alive proxy + the verify task's
   authoritative `/api/v1/health` curl probe.
3. **Outcome C -- no flag at all:** set
   `fluentbit_healthcheck_enabled: false`. Docker HEALTHCHECK omitted
   entirely; OPS-06 compliance via the verify task's `State.Running`
   poll + the `/api/v1/health` curl probe.

The plan that ported this role selected Outcome B as the safe default;
the verify task's in-network `/api/v1/health` curl probe is the
authoritative readiness gate regardless of which Outcome is active.

## Operator access (no host publish by default per D-30)

Inter-component traffic on the `telemetron` bridge reaches Fluent Bit
at `http://fluentbit:2020`. Operator access from a workstation:

```bash
ssh -L 2020:localhost:2020 <homelab-host>
# In a browser:
#   http://localhost:2020/api/v1/health     -- 200 OK when healthy
#   http://localhost:2020/api/v1/metrics    -- Prometheus-format internal counters
#   http://localhost:2020/api/v1/uptime     -- uptime in milliseconds
#   http://localhost:2020/api/v1/storage    -- storage layer state
```

## Security model

- **Default: no host port publish.** Operator access via SSH local-forward.
- **No vault keys.** D-55 confirms no vault surface for Fluent Bit in M1.
- **Inter-component traffic on the `telemetron` bridge only.** Fluent
  Bit reaches the OTel Collector over Docker DNS (`otel:4318`); never
  via the host network.
- **`/var/lib/docker/containers` bind-mount is read-only.** Fluent Bit
  never writes to the host's Docker log dir.
- **`/var/run/docker.sock` is NOT bind-mounted.** The default tail
  parses on-disk JSON files; no Docker API access needed. The
  Labeling-operator-apps Lua-filter route would add a docker.sock RO
  bind-mount (mirror D-52 from Plan 03-02).
- **Rendered configs at mode 0640.** Operator-readable; container reads
  via UID-mapped bind-mount.

## Idempotency

Per OPS-04: running the playbook twice in a row reports `changed=0`.

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags fluentbit
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags fluentbit
# ...second run: changed=0
```

Config changes (either of the two rendered files) notify a single
docker-restart fluentbit handler (W6); the listen value is wired so
both renders share one restart per run. The module-level state
parameter is never used for restarts (Pitfall 8).

## Port-acceptance gates

All six pass on `roles/fluentbit/` (with the grep gate scoped to
code/config files; the role README intentionally documents the
upstream-deviation audit per D-25):

- **Image-pin (OPS-01):** zero floating-tag references.
- **Grep gate (Pitfall 9):** zero matches in code/config files.
- **Non-ASCII gate (OPS-05):** zero non-ASCII characters in the role.
- **Vault-discipline (OPS-02):** zero vault-prefixed references in
  code/config (none needed -- no auth surface).
- **Idempotency (OPS-04):** twice-in-a-row run reports `changed=0`.
- **Healthcheck + restart-policy (OPS-06):** `docker inspect` returns
  `healthy` (Outcome A/B) or the verify task's `State.Running` +
  `/api/v1/health` probe gate (Outcome C); restart policy
  `unless-stopped`.

## Verification scope

Per RESEARCH Open Question Q9 + Finding 9: end-to-end FB->Loki smoke
is deferred to Phase 6 OPS-07. A single-push bucket-landing assertion
is impractical for FB's chunk-buffered output -- the Phase 6 plan will
exercise the full pipeline with a synthetic log generator. The M1
acceptance gate is HTTP 200 on `:2020/api/v1/health`, which proves
the engine has started, the config parsed, and the [OUTPUT] plugin
loaded.

Plan 03-05 added two non-blocking verify-task assertions that confirm
the rendered `[FILTER] lua` block exists in the host-rendered config
and that `enrich.lua` is readable inside the container via the bind-
mount. The full Lua-under-load contract -- the SC4 retest (5-minute
synthetic load at >= 1k req/s without OOM, mirrored from
03-VERIFICATION.md's human_verification entry) -- is a UAT item: per-
log-line Lua execution shifts the FB CPU+memory budget, and if SC4
regresses under load, the Lua filter must be tuned (longer TTL, smaller
cache, simpler logic). The default TTL of 300 seconds + per-container
cache entry is sized to keep the per-log-line work to a cache lookup
plus two record-field assignments under steady state.

## Deviations from upstream INSPQ (D-25)

Per CONTEXT.md D-25, each role port is an opinionated improvement
pass -- not a mirror translation. The headline deviation is the role
inversion (D-46) below.

### Role inversion (D-46) -- the headline deviation

Upstream used Fluent Bit on legacy hosts to scoop app-specific log
files (no native OTel / shipper available) and ship them to a central
observability host. Telemetron M1 colocates Fluent Bit with workloads
on a single Docker host, tailing container JSON logs by default. The
`fluentbit_extra_tail_paths` knob (D-48) preserves the upstream
use case as opt-in. See user memory note
`project_fluentbit_role_shift.md` for the full inversion narrative.

### Dropped

- `:latest` image tag -- replaced with pinned `4.2.3` per OPS-01.
- K8s helm/operator branches -- dropped per M1 Docker-only scope.
- French task names ("gerer les mount points", "S'assurer que le
  repertoire", "gerer le lvm", "monter le lvm") -- replaced with
  English per CLAUDE.md.
- LVM tasks (manage LVM, mount LVM) -- dropped; Telemetron does not
  manage host LVM.
- `nfs.yml` + `fluentbit_nfs_mounts` -- dropped; NFS log ingestion is
  the deferred `nfsd` role's territory and isn't on the FB default
  path.
- `docker_cleanup.yml` -- dropped; not Fluent Bit's job to garbage-
  collect Docker artifacts.
- `restart_policy: always` -- replaced with `unless-stopped` per
  OPS-06.
- Default K8s tail path `/var/log/containers/*.log` -- replaced with
  the Docker JSON file driver path `/var/lib/docker/containers/*/*-json.log`
  per D-46.
- Default `kubernetes` filter -- replaced with the D-47 modify +
  parser + grep allowlist filter chain.
- Default `stdout` output -- replaced with the D-49 `opentelemetry`
  output to `otel:4318/v1/logs`.
- `fluentbit_namespace` + K8s helm vars + servicemonitor +
  openshift_scc -- dropped per M1 Docker-only scope.
- `fluentbit_kubernetes_*` host paths -- dropped per M1 Docker-only
  scope.
- `fluentbit_root_dir: /opt/fluentbit` -- replaced with the Phase-1
  D-18 flat layout (`/opt/telemetron/fluentbit/<file>`).
- `America/Toronto` timezone hardcode -- replaced with `Etc/UTC` per
  Pitfall 6 Mode 1 (DST avoidance).

### Replaced

- Tail path -- `/var/log/containers/*.log` (K8s) ->
  `/var/lib/docker/containers/*/*-json.log` (D-46 role inversion).
- Kubernetes filter -> D-47 modify + parser + grep allowlist filter
  chain.
- Stdout output -> D-49 opentelemetry output.
- Nested `root_dir/data_dir/config_dir` layout -> flat
  `/opt/telemetron/fluentbit/<file>` (Phase-1 D-18).

### Added (Pitfall 6 mitigation pack -- THE biggest D-25 improvement)

- **`Time_System_Timezone Etc/UTC`** -- THE single most impactful
  one-liner. Upstream had no `Time_System_Timezone` directive at all;
  records were timestamped in whatever the container's default TZ
  reported, which under DST shifts produced 1-hour skew twice a year.
- **`Multiline_Flush 5`** -- fail-fast aggregation bound (Pitfall 6
  Mode 3). Upstream had no `Multiline_Flush`, which produced
  multi-minute stalls when a multiline parser got stuck.
- **`Read_from_Head false`** -- per-INPUT (Pitfall 6 Mode 4). Upstream
  had no explicit setting; FB's default replays pre-deploy logs on
  first boot.
- **`storage.type filesystem` + `storage.max_chunks_up 128` + named
  buffer volume** -- per-INPUT (D-50). Upstream had `storage.path`
  commented out; on a slow OTel/Loki sink, in-memory chunks would
  back up until the engine dropped them.
- **Fallback `@timestamp` modify filter** -- (Pitfall 6 Mode 2
  mitigation). Upstream had no fallback when a source line lacked a
  date stamp; records would land in Loki without a usable timestamp.
- **D-47 label allowlist filter chain** -- modify (allowlist_static)
  + parser (extract_level) + modify (default_level). Upstream's
  kubernetes filter did different work (K8s pod metadata enrichment);
  the Telemetron filter chain promotes the five allowlist labels and
  drops everything else from Loki labels (high-cardinality kills via
  Pitfall 4 mitigation).
- **D-49 opentelemetry output** -- upstream used `stdout` (debugging
  only); Telemetron ships through the OTel Collector to Loki by
  default.
- **D-48 default-off extension knobs** -- `fluentbit_tail_system_logs`,
  `fluentbit_tail_journald`, `fluentbit_extra_tail_paths`. Preserves
  the upstream legacy-host-scoop use case as opt-in without making
  it the default.
- **Lua-filter Docker-label enrichment (Plan 03-05 D-47 amendment)** -- a
  `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) reads each
  source container's `/var/lib/docker/containers/<id>/config.v2.json`
  and extracts `org.telemetron.service` + `org.telemetron.job` Docker
  labels onto the record. M1 convention -- replaces an earlier
  container_name-default fallback for `service` and `job`. NO Docker
  socket mount; the Lua filter only reads the JSON files that Fluent
  Bit's tail already bind-mounts RO from /var/lib/docker/containers.

### Kept from upstream (got it right)

- Single Fluent Bit instance per host (vs. forward-protocol fan-in).
- Bind-mount on the host log directory (vs. shipping log files into
  the container).
- Tag-based filter dispatching (`Match docker.*` etc.).

## Deprecation notes

None for M1. Fluent Bit is the locked log shipper per CLAUDE.md
tech-stack constraints; Grafana Alloy / Vector / Promtail
alternatives are explicitly out of M1 scope.
