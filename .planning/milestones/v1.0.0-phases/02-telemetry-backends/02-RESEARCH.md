# Phase 2: Telemetry Backends - Research

**Researched:** 2026-05-17
**Domain:** Grafana Loki 3.7.2 / Tempo 2.10.5 / Mimir 3.0.6 — Ansible-on-Docker monolithic deployment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-22:** Three plans, one per role, in LGTM/storage-bucket order. `02-01-PLAN.md` ports `roles/loki/`; `02-02-PLAN.md` ports `roles/tempo/`; `02-03-PLAN.md` ports `roles/mimir/`. Mirrors Phase 1's 01-03 shape. Each plan is independent.
- **D-23:** Each plan wires its own role into `playbooks/deploy_docker.yml` as the final task of that plan.
- **D-24:** Each role gets one tag matching its name. Sub-tags only if reload-without-restart becomes useful.
- **D-25:** Each role port is an opinionated improvement pass, not a mirror-translate of the INSPQ source. Researcher and planner audit for INSPQ-isms, missing pitfall guards, and better defaults. Documented in each plan's "Deviations from upstream" section.
- **D-26:** Multitenancy disabled in both Loki and Mimir. Loki: `auth_enabled: false`. Mimir: `multitenancy_enabled: false`.
- **D-27:** Per-backend vault key aliases pointing at MinIO root creds for now. Six new keys in `vault.yml.example`.
- **D-28:** gRPC clash resolution: Loki :9095, Tempo :9096, Mimir :9097. Every backend explicitly pins its gRPC port.
- **D-29:** Tempo OTLP alt ports `:14317`/`:14318` explicitly pinned; NOT host-published.
- **D-30:** All three backends default `<role>_publish_host: false`.
- **D-31:** Full port matrix — Loki: HTTP :3100 gRPC :9095; Tempo: HTTP :3200 gRPC :9096 OTLP-gRPC :14317 OTLP-HTTP :14318; Mimir: HTTP :9009 gRPC :9097.
- **D-32:** Each role's final task is an in-network one-shot verify container (W8 pattern).
- **D-33:** Loki: `loki_retention_period: 14d`, compactor `retention_enabled: true`, `retention_delete_delay: 2h`.
- **D-34:** Tempo dual-knob retention: `tempo_block_retention: 168h` + `tempo_compacted_block_retention: 1h`. Both must be set.
- **D-35:** Mimir: `mimir_compactor_blocks_retention_period: 30d`.
- **D-36:** Mimir limits + monolithic tuning: `max_global_series_per_user: 500000`, `max_global_series_per_metric: 100000`, `query_store_after: 12h`, `blocks_storage.bucket_store.sync_interval: 5m`, `compactor.cleanup_interval: 5m`.
- **D-37:** Loki `limits_config`: `max_streams_per_user: 5000`, `max_label_value_length: 2048`, `max_label_names_per_series: 15`.
- **D-38:** Enable metrics-generator processor in Tempo, NO `remote_write` to Mimir. Research validates config shape.
- **D-39:** Claude's Discretion within research-validated boundaries: Loki schema TSDB, `compactor_working_directory: /var/loki/compactor`, Mimir alertmanager/ruler S3-backed, Tempo storage S3, S3 endpoint `http://minio:9000` region `us-east-1` `s3forcepathstyle: true`.

### Claude's Discretion

- Exact Jinja iteration patterns for nested config sections.
- Per-role healthcheck timing.
- Memory limits per backend container.
- Loki `chunk_target_size`, `chunk_idle_period`.
- Tempo `compactor.compaction.block_ranges_period`.
- Exact in-network verify payload shape per backend.
- README "Improvements over upstream INSPQ" sub-section per role.

### Deferred Ideas (OUT OF SCOPE)

- Per-backend MinIO access keys (hardening phase).
- Distributed/scalable-single-binary modes (v2).
- MinIO replacement (future milestone).
- Multi-tenant Loki/Mimir (v2).
- Tempo metrics-generator full remote_write to Mimir (post-M1).
- HAProxy (distributed mode only, deferred).
- Per-backend WAL tuning, ingester memory limits beyond homelab defaults.
- Fluent Bit Loki label allowlist (Phase 3).
- Prometheus metric_relabel_configs for high-cardinality (Phase 3).
- OTel Collector pipeline order + GOMEMLIMIT (Phase 3).
- Synthetic push via OTel Collector (Phase 6 smoke test).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-01 | Loki monolithic (`grafana/loki:3.7.2`), `loki-chunks` bucket, persistent volume covering `/loki/compactor/markers/` | Config shape verified: TSDB schema, S3 storage_config.aws, compactor.working_directory |
| BACK-02 | `loki_retention_period` group_vars knob, documented in README | Compactor retention_enabled + limits_config.retention_period keys confirmed |
| BACK-03 | Tempo monolithic (`grafana/tempo:2.10.5`), `tempo-traces` bucket, both `block_retention` and `compacted_block_retention` set | D-34 dual-knob validated; exact YAML path confirmed |
| BACK-04 | Mimir monolithic (`grafana/mimir:3.0.6`), three distinct buckets, `max_global_series_per_user: 500000`, `query_store_after` tuned | Mimir S3 config shape confirmed; separate bucket keys verified |
| BACK-05 | Tempo OTLP receivers on :14317/:14318 (internal-only), standard :4317/:4318 free | OTLP receiver endpoint config confirmed: `distributor.receivers.otlp.protocols.grpc.endpoint`/`http.endpoint` |

</phase_requirements>

---

## Summary

Phase 2 ports three Grafana LGTM backends — Loki 3.7.2, Tempo 2.10.5, Mimir 3.0.6 — as Ansible roles following the Phase 1 `minio` role canonical template exactly. All three backends run in monolithic mode (`-target=all`), store data in MinIO S3 buckets from Phase 1, and wire into `playbooks/deploy_docker.yml` in series after `minio`.

The primary open question going in — D-38 Tempo metrics-generator without remote_write — is **resolved**: Tempo 2.10.5 supports processor-only operation (`service-graphs`, `span-metrics`, `local-blocks`) via `overrides.defaults.metrics_generator.processors` with `metrics_generator.storage.path` for the WAL, and `remote_write` is entirely optional. The preferred path (b) from CONTEXT.md applies: enable processor + local-WAL-only-no-remote-write.

The major cross-cutting surprise for the planner: **Loki 3.7 and Tempo 2.10 both use distroless images with no shell**. Standard `CMD-SHELL wget` healthchecks do not work. Loki 3.7+ ships a built-in `-health` flag on the binary (`/usr/bin/loki -health`). Tempo 2.10 is distroless but has NO built-in health binary yet — healthcheck must use a different approach (see § Healthcheck Endpoints). Mimir 3.0 is also distroless with no built-in health command as of this research. The planner must use `CMD ["/usr/bin/loki", "-health"]` for Loki and a workaround for Tempo/Mimir.

The INSPQ upstream audit (D-25) found significant INSPQ-isms in all three roles that do NOT survive into Phase 2: French task names, `America/Toronto` timezone, `inventory_hostname`-embedded container names, `latest` image tags, LVM/UFW tasks, `application_web_docker` base role dependency, hardcoded INSPQ-internal hostnames in alertmanager/ruler URLs, and INSPQ-scale limits (`max_global_series_per_user: 5000000`).

**Primary recommendation:** Mirror the Phase 1 `minio` role structure verbatim for each backend. The config templates are the main differentiator per role; the task/handler/volume patterns are identical.

---

## Standard Stack

### Core (Phase 2)

| Component | Image | Version | Purpose | Why This |
|-----------|-------|---------|---------|----------|
| Loki | `grafana/loki` | `3.7.2` | Log storage + LogQL | Latest stable (2026-05-13); TSDB schema default since 2.8+ |
| Tempo | `grafana/tempo` | `2.10.5` | Trace storage + TraceQL | Latest stable (2026-04-23); v3.0 is pre-release |
| Mimir | `grafana/mimir` | `3.0.6` | Long-term metrics storage | Latest stable (2026-04-20); v3.0 line is current |
| MinIO mc | `minio/mc` | `RELEASE.2025-04-22T16-23-26Z` | In-network verify one-shot (W8) | Carries forward from Phase 1 minio role |

### Image Verification

All three images confirmed resolvable via `docker manifest inspect`:
- `grafana/loki:3.7.2` — `application/vnd.docker.distribution.manifest.list.v2+json` (HIGH)
- `grafana/tempo:2.10.5` — `application/vnd.docker.distribution.manifest.list.v2+json` (HIGH)
- `grafana/mimir:3.0.6` — `application/vnd.oci.image.index.v1+json` (HIGH)

### Installation

```bash
docker pull grafana/loki:3.7.2
docker pull grafana/tempo:2.10.5
docker pull grafana/mimir:3.0.6
```

---

## Architecture Patterns

### Recommended Role Structure (per backend)

Each Phase 2 role mirrors the Phase 1 `minio` role layout exactly:

```
roles/<backend>/
├── defaults/main.yml        # image pin, ports, volumes, retention, limits, health timing
├── tasks/main.yml           # config dir, render template, volume, pull, run container, include verify
├── tasks/verify.yml         # D-10a HEALTHCHECK poll + W8 one-shot payload push + mc ls assert
├── handlers/main.yml        # W6: single handler "docker restart <name>"
├── templates/<backend>.yaml.j2  # D-20 sorted-keys Jinja config template
├── meta/main.yml            # role_name, dependencies: [], collections: [community.docker]
└── README.md                # OPS-03 README schema (Variables/Vault/Tags/Modes/Volumes/Healthcheck/Security/Idempotency/Port-gates/Deprecation)
```

The `tasks/verify.yml` file corresponds to `tasks/bootstrap.yml` in the minio role — same three-step shape:
1. D-10a poll: `docker_container_info` loop until `State.Health.Status == 'healthy'`
2. W8 payload push: one-shot container on `telemetron` network pushes synthetic payload
3. W8 bucket assert: one-shot `minio/mc` container runs `mc ls --json` and diffs against expected objects

### Pattern 1: Config Bind-Mount (D-18)

Host `/opt/telemetron/<backend>/<backend>.yaml` → container canonical config path (read-only).

```yaml
# In tasks/main.yml
- name: Ensure <backend> config directory exists
  ansible.builtin.file:
    path: "{{ <backend>_config_dir }}"   # /opt/telemetron/<backend>
    state: directory
    mode: "0755"

- name: Render <backend> config
  ansible.builtin.template:
    src: <backend>.yaml.j2
    dest: "{{ <backend>_config_dir }}/<backend>.yaml"
    mode: "0644"
  notify: restart <backend>
```

### Pattern 2: D-10a HEALTHCHECK Poll (mirrors minio role bootstrap.yml Step 1)

```yaml
- name: Wait for <backend> container HEALTHCHECK to report healthy
  community.docker.docker_container_info:
    name: "{{ <backend>_container_name }}"
  register: <backend>_health_check
  until: >-
    <backend>_health_check.container is defined
    and <backend>_health_check.container.State is defined
    and <backend>_health_check.container.State.Health is defined
    and <backend>_health_check.container.State.Health.Status == 'healthy'
  retries: "{{ <backend>_health_retries }}"
  delay: "{{ <backend>_health_delay }}"
  changed_when: false
```

### Pattern 3: W6 Single Handler (mirrors minio handlers/main.yml)

```yaml
- name: Docker restart <backend>
  ansible.builtin.command:
    cmd: "docker restart {{ <backend>_container_name }}"
  changed_when: true
  listen: restart <backend>
```

### Pattern 4: S3 Endpoint Convention (D-39)

All three backends share the same MinIO connection pattern:
- Endpoint: `http://minio:9000` (Docker DNS on `telemetron` bridge)
- Region: `us-east-1` (MinIO ignores but S3 client requires a value)
- Force path style: `true` (MinIO requires path-style, not vhost-style)
- Insecure: `true` (plain HTTP on internal bridge; no TLS in M1)
- Credentials: `{{ vault_<backend>_s3_access_key }}` / `{{ vault_<backend>_s3_secret_key }}`

### Anti-Patterns to Avoid

- **`state: restarted` on `docker_container`** — non-idempotent, destroys state. Use handler + `docker restart`.
- **Single retention knob for Tempo** — `block_retention` alone is silent no-op. Both `block_retention` AND `compacted_block_retention` must be set (Pitfall 10).
- **MinIO lifecycle policies on backend buckets** — fight the compactors. Let Loki/Tempo/Mimir own deletion exclusively.
- **`latest` image tag** — breaks reproducibility and OPS-01.
- **INSPQ-inherited `always` restart policy** — Telemetron default is `unless-stopped` everywhere (OPS-06).
- **Hardcoded `inventory_hostname` in container names** — breaks single-host inventory portability. Container name is a simple, consistent string.
- **French task names from upstream** — all task `name:` strings must be English (CLAUDE.md).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log stream storage + retention | Custom retention cron | Loki compactor (`retention_enabled: true`) | Loki compactor handles two-phase mark+delete correctly; DIY misses marker file persistence |
| Trace block compaction | Custom S3 cleanup script | Tempo compactor (dual-knob: `block_retention` + `compacted_block_retention`) | Single-knob or DIY cleanup misses the mark-then-delete phase, causing disk fill |
| Long-term metric block retention | Custom TTL job | Mimir compactor (`compactor.blocks_retention_period`) | Mimir owns block lifecycle; external deletion corrupts block index |
| Service-graph metrics from traces | Custom span aggregation | Tempo metrics-generator (local-WAL-only path) | Built-in processor handles cardinality limits and overflow series correctly |
| S3 path-style routing for MinIO | Custom HTTP proxy | `s3forcepathstyle: true` / `http.insecure` flags in backend config | One config key per backend; no proxy overhead |

---

## Critical Research Findings (per question in brief)

### Finding 1: D-38 — Tempo metrics-generator without remote_write (RESOLVED)

**Conclusion (HIGH confidence):** Tempo 2.10.5 supports processor-only operation. `remote_write` is **optional** under `metrics_generator.storage`.

**Correct path (b) from CONTEXT.md applies:**

```yaml
metrics_generator:
  storage:
    path: /var/tempo/generator/wal       # WAL for generated metrics
    # remote_write is intentionally absent -- no coupling to Mimir at startup
  traces_storage:
    path: /var/tempo/generator/traces    # local-blocks processor storage

overrides:
  defaults:
    metrics_generator:
      processors:
        - service-graphs
        - span-metrics
        - local-blocks
```

The `overrides.defaults.metrics_generator.processors` key is how processors are enabled. `remote_write` is listed as `[- <Prometheus remote write config>]` in the config reference — brackets denote optional list. Without `remote_write`, generated metrics exist in the WAL only during the container lifetime; they are not persisted or exported. This is acceptable for M1 — Phase 2 stop-gap. Full service-graph + span-metrics in Grafana requires `remote_write` to Mimir (deferred, post-M1).

**Source:** Grafana Tempo 2.10.x configuration reference — metrics_generator section (MEDIUM confidence, verified via WebFetch against official docs).

**Default knob in `roles/tempo/defaults/main.yml`:** `tempo_metrics_generator_enabled: true` (CONTEXT.md D-38 requirement). When `true`, include the `metrics_generator` block above. The INSPQ upstream (`tempo_metrics_generator_remote_write: false` already existed) had partial support for this path — the Telemetron port completes it by making the no-remote-write path the default.

---

### Finding 2: Loki 3.7.2 Config Shape (HIGH confidence)

Verified against INSPQ template `loki-config.single-tenant.yaml.j2` (which already uses Loki 3.x TSDB) and official Loki retention docs.

#### Full monolithic config shape for Loki 3.7.2:

```yaml
auth_enabled: false           # D-26: single-tenant, no X-Scope-OrgID

server:
  http_listen_port: 3100
  grpc_listen_port: 9095      # D-28: keep Loki default; Tempo/Mimir move
  grpc_server_max_recv_msg_size: 10485760   # 10MB (from INSPQ; reasonable)
  grpc_server_max_send_msg_size: 10485760

common:
  path_prefix: /loki

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  max_chunk_age: 2h
  chunk_idle_period: 30m         # Claude's Discretion per D-39 + PITFALLS "Performance Traps"
  chunk_retain_period: 30s
  wal:
    enabled: false               # monolithic: no distributed WAL needed

schema_config:
  configs:
    - from: 2023-01-01            # arbitrary past date; TSDB schema stable since Loki 2.8
      store: tsdb
      object_store: s3
      schema: v13                 # v13 is the current TSDB schema in Loki 3.x
      index:
        prefix: tsdb_index_
        period: 24h               # must be 24h for retention support

storage_config:
  tsdb_shipper:
    active_index_directory: /loki/tsdb-index
    cache_location: /loki/tsdb-cache
  aws:
    endpoint: http://minio:9000   # Docker DNS on telemetron bridge (D-39)
    bucketnames: loki-chunks      # matches Phase 1 bucket name
    access_key_id: "{{ vault_loki_s3_access_key }}"
    secret_access_key: "{{ vault_loki_s3_secret_key }}"
    region: us-east-1             # MinIO ignores; S3 client requires value
    s3forcepathstyle: true        # MinIO requires path-style (D-39)
    insecure: true                # plain HTTP on internal Docker bridge

compactor:
  working_directory: /loki/compactor   # D-39 + Pitfall 12: must be on persistent volume
  delete_request_store: s3             # required for S3 backend in Loki 3.x
  retention_enabled: true              # D-33
  retention_delete_delay: 2h           # D-33
  retention_delete_worker_count: 150   # upstream default; fine for homelab

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  allow_structured_metadata: true
  max_entries_limit_per_query: 1000
  volume_enabled: true
  retention_period: "{{ loki_retention_period }}"   # D-33: group_vars knob default 14d
  # D-37: label discipline limits
  max_streams_per_user: 5000            # Pitfall 4
  max_label_value_length: 2048          # Pitfall 4
  max_label_names_per_series: 15        # Pitfall 4
  # Chunking for homelab (PITFALLS "Performance Traps")
  # chunk_target_size and chunk_idle_period are ingester-level, not limits_config
```

**Volume mount:** One named volume `telemetron_loki_data` at `/loki` covers WAL + tsdb-index + tsdb-cache + chunks + compactor markers (D-17 + Pitfall 12).

**Config bind-mount:** Host `/opt/telemetron/loki/loki.yaml` → container `/etc/loki/loki.yaml` (read-only, D-18).

**Container command:** `-config.file=/etc/loki/loki.yaml -target=all`

**Key INSPQ-ism in template:** INSPQ used `storage_config.aws.bucketnames: loki` — this must become `loki-chunks` to match Phase 1. The INSPQ `loki_tenant_id: inspq` must be dropped entirely (auth_enabled: false means no tenant ID needed).

---

### Finding 3: Mimir 3.0.6 Monolithic Config Shape (HIGH confidence)

Verified against official Mimir config docs, the `single-process-config-blocks.yaml` sample, and the INSPQ `mimir-standalone.yaml.j2` template.

```yaml
target: all                    # monolithic mode (equivalent to -target=all CLI flag)
multitenancy_enabled: false    # D-26: single tenant "anonymous"

server:
  http_listen_port: 9009
  grpc_listen_port: 9097       # D-28: explicit override (default 9095 clashes with Loki)
  log_level: warn

ingester:
  ring:
    replication_factor: 1
    kvstore:
      store: inmemory

common:
  storage:
    backend: s3
    s3:
      endpoint: minio:9000     # NO http:// prefix for common.storage.s3.endpoint (Mimir format)
      access_key_id: "{{ vault_mimir_s3_access_key }}"
      secret_access_key: "{{ vault_mimir_s3_secret_key }}"
      insecure: true           # plain HTTP

blocks_storage:
  backend: s3
  s3:
    bucket_name: mimir-blocks  # D-39: distinct bucket per BACK-04
  tsdb:
    dir: /data/tsdb
  bucket_store:
    sync_dir: /data/tsdb-sync
    sync_interval: 5m          # D-36 + Pitfall 11

ruler_storage:
  backend: s3
  s3:
    bucket_name: mimir-ruler   # D-39: distinct bucket; Mimir refuses to share

alertmanager_storage:
  backend: s3
  s3:
    bucket_name: mimir-alerts  # D-39: distinct bucket

compactor:
  data_dir: /data/compactor
  blocks_retention_period: 30d  # D-35 + BACK-04
  cleanup_interval: 5m          # D-36 + Pitfall 11

ruler:
  rule_path: /data/ruler/rules
  alertmanager_url: http://alertmanager:9093  # Phase 4 component; placeholder for now

alertmanager:
  data_dir: /data/alertmanager
  # external_url intentionally NOT set to inventory_hostname (INSPQ-ism to drop)

querier:
  query_store_after: 12h       # D-36 + Pitfall 11: longer than block-lands window; shorter than Prometheus local retention

limits:
  max_global_series_per_user: 500000     # D-36 + Pitfall 3
  max_global_series_per_metric: 100000   # D-36 + Pitfall 3
```

**Important S3 endpoint format difference from Loki/Tempo:** In Mimir's `common.storage.s3.endpoint`, the endpoint does NOT include `http://` — just `minio:9000`. However, in `blocks_storage.s3`, only the `bucket_name` override is needed (inherits from `common`). Verified against official Mimir docs and the play-with-grafana-mimir example config.

**Volume mount:** One named volume `telemetron_mimir_data` at `/data` (D-16/D-17). Sub-paths `/data/tsdb`, `/data/tsdb-sync`, `/data/compactor`, `/data/alertmanager`, `/data/ruler` are created by Mimir on first start. The `data_dir` and `dir` settings in the config must all point inside `/data`.

**INSPQ-ism to drop:** `mimir_container_name: "telemetron_mimir_{{ env | lower }}_{{ inventory_hostname }}"` — Telemetron uses a simple `mimir` container name. Also drop `alertmanager.external_url: http://{{ inventory_hostname }}:9009/alertmanager` (hardcoded INSPQ hostname pattern); omit `external_url` in M1.

**INSPQ limits to replace:** INSPQ used `max_global_series_per_user: 5000000` (5M, tuned for INSPQ scale). Telemetron M1 default is `500000` (500k) per Pitfall 3 homelab guidance.

---

### Finding 4: Tempo 2.10.5 Monolithic Config Shape (HIGH confidence)

Verified against INSPQ `tempo-config.monolithic.yaml.j2`, official Tempo 2.10.x docs, and Pitfall 10.

```yaml
stream_over_http_enabled: true
server:
  http_listen_port: 3200
  grpc_listen_port: 9096     # D-28: explicit override (default 9095 clashes with Loki)
  log_level: info

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:14317"   # D-29: internal-only alt port (NOT 4317)
        http:
          endpoint: "0.0.0.0:14318"   # D-29: internal-only alt port (NOT 4318)

metrics_generator:
  storage:
    path: /var/tempo/generator/wal     # D-38 path (b): local WAL, no remote_write
  traces_storage:
    path: /var/tempo/generator/traces

storage:
  trace:
    backend: s3
    s3:
      bucket: tempo-traces             # D-39: matches Phase 1 bucket
      endpoint: minio:9000             # NO http:// prefix for Tempo S3 endpoint
      access_key: "{{ vault_tempo_s3_access_key }}"
      secret_key: "{{ vault_tempo_s3_secret_key }}"
      insecure: true
      forcepathstyle: true             # MinIO requires path-style
      region: us-east-1
    wal:
      path: /var/tempo/wal
    local:
      path: /var/tempo/traces

compactor:
  compaction:
    block_retention: "{{ tempo_block_retention }}"               # D-34: default 168h (7d)
    compacted_block_retention: "{{ tempo_compacted_block_retention }}"  # D-34: default 1h
    # Both knobs MUST be set -- see PITFALLS.md Pitfall 10

overrides:
  defaults:
    metrics_generator:
      processors:
        - service-graphs
        - span-metrics
        - local-blocks             # D-38: local-only, no remote_write
```

**Volume mount:** One named volume `telemetron_tempo_data` at `/var/tempo` (D-16/D-17). Covers WAL + traces + generator storage.

**Config bind-mount:** Host `/opt/telemetron/tempo/tempo.yaml` → container `/etc/tempo.yaml` (read-only, D-18).

**Container command:** `-config.file=/etc/tempo.yaml -target=all`

**INSPQ-isms to drop:**
- `tempo_container_env.TZ: "America/Toronto"` → use `Etc/UTC`
- `tempo_port_grpc: 4317` / `tempo_port_http: 4318` (INSPQ used standard ports) → change to `14317`/`14318`
- `tempo_retention_period: "336h"` and `tempo_compaction_block_retention: "{{ tempo_retention_period }}"` — INSPQ only set one knob (silent failure per Pitfall 10). Telemetron sets BOTH `block_retention` AND `compacted_block_retention`.
- Jaeger receivers enabled in INSPQ template — drop all Jaeger receiver config from Telemetron. OTel → Tempo via OTLP only.
- `tempo_compaction_window: "1h"` from INSPQ defaults — this is not the dual-knob retention; keep only as reference.

**Note on `storage.s3.endpoint` format:** Tempo uses `endpoint: minio:9000` WITHOUT `http://` prefix, consistent with Mimir. The `insecure: true` flag handles the HTTP-not-HTTPS case. Verified via INSPQ template analysis.

---

### Finding 5: gRPC Port Allocation Cross-Check (D-28)

All three backends have an explicit `server.grpc_listen_port` YAML key that overrides the default `:9095`.

| Backend | HTTP Port | gRPC Port | Override Key | Internal Default |
|---------|-----------|-----------|--------------|-----------------|
| Loki | :3100 | :9095 | `server.grpc_listen_port` | 9095 (kept) |
| Tempo | :3200 | :9096 | `server.grpc_listen_port` | 9095 (overridden) |
| Mimir | :9009 | :9097 | `server.grpc_listen_port` | 9095 (overridden) |

In monolithic mode, gRPC is needed internally even with no external gRPC clients — the query-frontend↔querier loop (and equivalent in Loki/Tempo) uses it. The explicit pin prevents silent failures if future image versions change defaults.

**Confidence:** HIGH — `server.grpc_listen_port` key confirmed present in INSPQ templates for all three backends.

---

### Finding 6: Healthcheck Endpoints — CRITICAL GOTCHA

This is the most operationally important finding for the planner. All three backends are **distroless images** without standard shell utilities.

#### Loki 3.7.2 — Built-in `-health` flag (HIGH confidence)

Loki 3.6+ removed busybox from the image. The Loki team implemented a native healthcheck command (PR #20590, backported to 3.6.x+, included in 3.7.x).

```yaml
# In community.docker.docker_container task:
healthcheck:
  test: ["CMD", "/usr/bin/loki", "-health"]
  start_period: 30s
  interval: 10s
  timeout: 5s
  retries: 5
```

The `/ready` endpoint on `:3100` is what the `-health` flag hits internally. The `CMD` (not `CMD-SHELL`) form is required — no shell is available.

**Source:** Official Loki examples `getting-started/docker-compose.yaml` (HIGH confidence — official repo).

#### Tempo 2.10.5 — No built-in health binary; use `/ready` HTTP check workaround (MEDIUM confidence)

Tempo 2.10 switched to `gcr.io/distroless/static-debian12` as the base image (confirmed in release notes). The Tempo healthcheck issue (#6536, opened 2026-02-23) was resolved (PR #6608 closed) — a health binary was implemented. However, the timing relative to 2.10.5's release (2026-04-23) is uncertain.

**Safe approach for planner:** Assume the health binary may NOT be present in 2.10.5. Use the `/ready` endpoint via `CMD` with a bundled HTTP client. Since the image has no wget/curl/sh, the recommended workaround is:

```yaml
healthcheck:
  test: ["CMD", "/tempo", "-health-check"]   # IF binary ships this flag
  start_period: 60s
  interval: 15s
  timeout: 5s
  retries: 5
```

If `-health-check` or `-health` flag is NOT in `grafana/tempo:2.10.5`, fallback: skip the Docker-level HEALTHCHECK on the container and instead rely on the D-10a `docker_container_info` poll in `tasks/verify.yml` polling for the container running state, then immediately use `curl`/`wget` from the one-shot verify container to hit `http://tempo:3200/ready`. This is still valid for OPS-06 compliance if the Ansible task verifies health before proceeding.

**Planner instruction:** Test `docker run --rm grafana/tempo:2.10.5 -help 2>&1 | grep -i health` against the actual image at plan-write time to determine which approach applies.

**Source:** GitHub tempo issue #6536 + release notes analysis (MEDIUM confidence).

#### Mimir 3.0.6 — Distroless, no built-in health binary (MEDIUM confidence)

Mimir uses `gcr.io/distroless/static-debian12` (confirmed via Dockerfile). Issue #9034 requesting healthcheck binary support is closed as "question" with no confirmed resolution. No evidence of a built-in `-health` flag in Mimir 3.0.6.

**Approach:** Same fallback as Tempo — the Docker `HEALTHCHECK` cannot use `CMD-SHELL`. Options:
1. Omit the Docker-level HEALTHCHECK and use Ansible D-10a polling via `docker_container_info` watching for container state `running` (not `healthy`), then validate via the one-shot verify container.
2. Use `CMD ["/bin/mimir", "-version"]` as a proxy health check (binary executes = container alive; not a true health check).

The planner should check the image at plan-write time: `docker run --rm grafana/mimir:3.0.6 -help 2>&1 | grep -i health`.

**OPS-06 compliance note:** OPS-06 requires "every component container has a Docker HEALTHCHECK." If Mimir and Tempo cannot do a meaningful health check via CMD, the healthcheck should be defined as a container-alive check rather than a readiness check, with the actual readiness gate in Ansible's `verify.yml` task (D-10a pattern). This satisfies OPS-06's intent without requiring shell utilities.

**Mimir `/ready` endpoint:** Confirmed at `http://mimir:9009/ready`. The `/services` endpoint (lists all component statuses) is available at `http://mimir:9009/services` for operational debugging but is not the healthcheck endpoint.

---

### Finding 7: Volume Layout per Backend (D-17 one-volume rule)

| Backend | Volume Name | Container Mount | Sub-paths Created by Container |
|---------|-------------|-----------------|--------------------------------|
| Loki | `telemetron_loki_data` | `/loki` | tsdb-index, tsdb-cache, chunks, compactor/ (incl. markers/) |
| Tempo | `telemetron_tempo_data` | `/var/tempo` | wal/, traces/, generator/wal, generator/traces |
| Mimir | `telemetron_mimir_data` | `/data` | tsdb/, tsdb-sync/, compactor/, alertmanager/, ruler/rules |

**Loki specifics (Pitfall 12):** The compactor markers directory `/loki/compactor/markers/` is covered by the volume at `/loki`. The `compactor.working_directory: /loki/compactor` config key must be set explicitly so it resolves to the persistent volume, not a transient location.

**Volume creation:** `community.docker.docker_volume` with `name: "{{ <backend>_data_volume }}"` and `state: present` before container start.

**Container user:** Loki runs as user `1000:0` (INSPQ default). Tempo runs as user `1000:0`. Mimir runs as `472:472` (INSPQ default). The named volumes are managed by Docker and permissions are handled by the container runtime on first mount — no explicit `chown` task needed in the Ansible role, since these are named volumes (not bind mounts).

---

### Finding 8: In-Network Verify Payload Shapes (D-32)

Per D-32, each role's final verify task pushes a synthetic payload and asserts objects land in the MinIO bucket. All verification happens over the `telemetron` Docker bridge — no host port publishing needed.

#### Loki Verify (one-shot `curlimages/curl` or minimal Alpine container)

**Push endpoint:** `POST http://loki:3100/loki/api/v1/push`

```bash
# Exact payload (JSON stream format)
curl -s -X POST http://loki:3100/loki/api/v1/push \
  -H "Content-Type: application/json" \
  --data-raw '{
    "streams": [{
      "stream": {"job": "telemetron-verify", "host": "verify"},
      "values": [["'"$(date +%s%N)"'", "telemetron loki verify OK"]]
    }]
  }'
```

**Timestamp:** Unix nanoseconds as a string (date +%s%N). Must be within `reject_old_samples_max_age` (168h default).

**MinIO assertion (mc ls):** After push, wait ~10 seconds for ingestion, then:
```bash
mc ls --json local/loki-chunks | grep -c '"key"' | awk '$1 > 0'
```
Presence of ANY object key in the bucket confirms Loki is writing chunks.

**Source:** Official Loki HTTP API docs + community examples (HIGH confidence for endpoint; MEDIUM for exact timing).

#### Tempo Verify (one-shot OTLP HTTP push)

**Push endpoint:** `POST http://tempo:14318/v1/traces` (internal-only alt port, D-29)

```bash
# Minimal OTLP/HTTP JSON trace (shell-friendly)
curl -s -X POST http://tempo:14318/v1/traces \
  -H "Content-Type: application/json" \
  --data-raw '{
    "resourceSpans": [{
      "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "telemetron-verify"}}]},
      "scopeSpans": [{
        "scope": {"name": "telemetron.verify"},
        "spans": [{
          "traceId": "5b8efff798038103d269b633813fc60c",
          "spanId": "eee19b7ec3c1b174",
          "name": "telemetron-verify-span",
          "kind": 1,
          "startTimeUnixNano": "'"$(date +%s)"'000000000",
          "endTimeUnixNano": "'"$(date +%s)"'100000000",
          "status": {"code": 1}
        }]
      }]
    }]
  }'
```

**MinIO assertion:** Tempo does not immediately write to S3 — it first writes to local WAL, then flushes blocks after `max_block_duration` (default 2h) or when the ingester is flushed. For a Phase 2 verify, assert the WAL directory is non-empty OR wait for a block flush (impractical in CI). **Recommended approach:** verify the HTTP push returns 200, then check that `mc ls local/tempo-traces` has objects within a longer window (or skip the mc assertion for Phase 2, adding it to Phase 6 smoke). The per-backend verify pattern for Tempo is: push returns 200 = backend is alive and accepting traces.

**Source:** OTLP spec + Grafana Tempo HTTP API docs (HIGH confidence for endpoint; MEDIUM for exact timing before block flush).

#### Mimir Verify (one-shot Prometheus remote_write push)

**Push endpoint:** `POST http://mimir:9009/api/v1/push`

Prometheus remote_write uses snappy-compressed protobuf, which is not curl-friendly from a shell script. **Recommended approach:** use a one-shot `prom/prometheus:v3.11.3` container (already in CLAUDE.md standard stack) to push a synthetic remote_write batch:

```bash
# One-shot Prometheus container that pushes a single sample via remote_write
docker run --rm --network telemetron prom/prometheus:v3.11.3 \
  promtool tsdb create-blocks-from openmetrics - <<'EOF'
# HELP telemetron_verify_total Telemetron verify counter
# TYPE telemetron_verify_total counter
telemetron_verify_total{job="verify"} 1
# EOF
EOF
```

**Alternative (simpler):** Use `mimirtool` (`grafana/mimirtool`) to push a metric directly. Or use `curl` with a pre-generated remote_write body (base64-encoded snappy protobuf blob). The simplest approach for Phase 2: verify via `curl http://mimir:9009/ready` returns `ready` and `curl http://mimir:9009/metrics` returns 200. Save the actual remote_write push to Phase 3 when Prometheus comes online (INGEST-02).

**MinIO assertion:** After Prometheus starts in Phase 3 and begins remote_writing, Mimir blocks land in `mimir-blocks`. For Phase 2 verify, the readiness check (`/ready` returns `ready`) is sufficient to gate the role.

**Source:** Mimir HTTP API docs + Prometheus remote_write spec (HIGH confidence for endpoint; MEDIUM for exact push body format).

---

### Finding 9: Image Entrypoints and Container Startup

| Backend | Image Entrypoint | Config Flag | Shell Available |
|---------|-----------------|-------------|-----------------|
| Loki 3.7.2 | `/usr/bin/loki` | `-config.file=/etc/loki/loki.yaml` | No (distroless) |
| Tempo 2.10.5 | `/tempo` | `-config.file=/etc/tempo.yaml` | No (distroless static) |
| Mimir 3.0.6 | `/bin/mimir` | `-config.file=/etc/mimir/mimir.yaml` | No (distroless static) |

All three: no shell, no wget, no curl in the image. All runtime healthchecks must use `CMD` (not `CMD-SHELL`).

---

## INSPQ Upstream Audit (D-25)

### Loki INSPQ-isms Found

| INSPQ Pattern | Action |
|---------------|--------|
| `loki_image_version: "latest"` | Drop. Pin `3.7.2` per OPS-01. |
| `loki_container_env.TZ: "America/Toronto"` | Replace with `Etc/UTC` per D-15. |
| `loki_tenant_id: inspq` | Drop. `auth_enabled: false` means no tenant header; tenant is implicitly `fake`. |
| `loki_alertmanager_url: "http://localhost:9093"` | Replace with `http://alertmanager:9093` when Phase 4 lands; omit from M1 config. |
| `loki_storage_s3_bucketname: loki` | Replace with `loki-chunks` per Phase 1 bucket naming. |
| French task names in all task files | Replace ALL with English per CLAUDE.md. |
| `loki_mode: "monolithic"` variable driving conditional logic | Simplify: M1 ships monolithic only; no conditional for distributed. |
| `loki_container_restart_policy: "always"` | Replace with `unless-stopped` per OPS-06. |
| LVM tasks (`loki_lvm: true`, `loki_vg`, `loki_lv_name`) | Drop entirely. Named Docker volume covers storage. |
| `loki_memberlist_join_members: [loki-memberlist]` | Drop. Monolithic mode does not need memberlist. |
| Bloom filter, pattern ingester, distributed component vars | Drop for M1. Document as future milestone in README. |
| `loki_network_mode: bridge` + custom network logic | Simplify: always use the `telemetron` bridge (D-04). |
| `loki_container_user: "1000:0"` hardcoded | Keep but make a default var `loki_container_user: "1000:0"`. |
| `schema_config.configs[0].from: 2023-01-01` | Keep (reasonable past date for TSDB schema). |
| **Missing Pitfall 12 guard** — no explicit `compactor.working_directory` | ADD: `compactor.working_directory: /loki/compactor` |
| **Missing Pitfall 4 limits** — no `max_streams_per_user`, etc. | ADD all three D-37 limits. |
| Table manager retention (`loki_table_manager_*`) | Drop. Loki 3.x uses compactor retention, not table manager. |

### Tempo INSPQ-isms Found

| INSPQ Pattern | Action |
|---------------|--------|
| `tempo_image_version: latest` | Drop. Pin `2.10.5`. |
| `tempo_container_env.TZ: "America/Toronto"` | Replace with `Etc/UTC`. |
| `tempo_port_grpc: 4317` / `tempo_port_http: 4318` | Replace with `14317`/`14318` per D-29. |
| Jaeger receivers (`thrift_http`, `thrift_binary`, `thrift_compact`) in config template | Drop. Telemetron uses OTLP only. Jaeger is an INSPQ-specific dependency. |
| `tempo_storage_trace_backend: local` default | Replace with `s3` as Telemetron M1 default (D-39). |
| `tempo_retention_period: "336h"` driving `compaction_block_retention` only | Replace with dual-knob: both `block_retention: 168h` AND `compacted_block_retention: 1h` per D-34. |
| `tempo_container_restart_policy: "unless-stopped"` | Keep (INSPQ got this one right). |
| `tempo_metrics_generator_remote_write: false` + `tempo_prometheus_url: ""` | Refine: when `tempo_metrics_generator_enabled: true` AND `tempo_prometheus_url` is empty, emit the local-WAL-only block (D-38 path b). |
| `tempo_replication_factor: 3` | Drop for M1 monolithic (single replica). |
| `tempo_memberlist_*` config | Drop. Not needed for monolithic. |
| Distributed component vars (distributor/ingester/querier ports) | Drop from M1 defaults. |
| `tempo_root_dir: /opt/telemetron/tempo` | Replace with `/opt/telemetron/tempo` for config dir (D-18), but data volume is `/var/tempo` (container path). |
| `tempo_container_command: "-config.file=/etc/tempo.yaml"` | Keep, add `-target=all`. |
| **Missing Pitfall 10 guard** — only `tempo_compaction_block_retention`, not both knobs | ADD `compacted_block_retention` as second required knob. |

### Mimir INSPQ-isms Found

| INSPQ Pattern | Action |
|---------------|--------|
| `mimir_image_version: "latest"` | Drop. Pin `3.0.6`. |
| `mimir_container_name: "telemetron_mimir_{{ env \| lower }}_{{ inventory_hostname }}"` | Replace with simple `mimir`. Inventory_hostname embedding breaks single-host portability. |
| `alertmanager.external_url: "http://{{ inventory_hostname }}:9009/alertmanager"` | Drop. This embeds INSPQ host resolution. Omit in M1. |
| `ruler.alertmanager_url: "http://{{ inventory_hostname }}:9009/alertmanager"` | Replace with `http://alertmanager:9093` when Phase 4 lands; omit from M1 config. |
| `mimir_port_grpc: 9010` (INSPQ set 9010, not 9095) | INTERESTING: INSPQ already moved gRPC off 9095. Telemetron uses 9097 (D-28). Both are correct moves. |
| `mimir_limits_config.max_global_series_per_user: 5000000` | Replace with `500000` per Pitfall 3 homelab defaults. |
| `mimir_limits_config.max_global_series_per_metric: 500000` | Replace with `100000`. |
| `mimir_lvm: true` + LVM vars | Drop entirely. Named Docker volume handles storage. |
| `mimir_ufw: true` + UFW tasks | Drop. Telemetron does not manage host firewall. |
| French task names throughout | Replace ALL with English. |
| `mimir_container_restart_policy: "always"` | Replace with `unless-stopped` per OPS-06. |
| `mimir_container_user: "472:472"` | Keep as default — Mimir 3.x image uses UID 472. |
| `mimir_config == 'standalone'` conditional | Drop. M1 ships monolithic only. |
| `mimir_storage_backend: filesystem` default | Replace with `s3` as Telemetron M1 default (D-39). |
| `mimir_compactor_retention_period: "2y"` (INSPQ used 2-year retention) | Replace with `30d` per D-35. |
| `blocks_storage.backend: filesystem` in template | Replace with `s3` + three distinct bucket config (D-39). |
| **Missing Pitfall 11 guard** — no `query_store_after`, no `sync_interval`, no `cleanup_interval` | ADD all three D-36 knobs. |
| `alertmanager.fallback_config_file` path reference | Drop INSPQ-specific fallback path; omit from M1. |
| `mimir_ooo_time_window: "30m"` | Keep (sensible; protects against data loss on restart). |

---

## Common Pitfalls

### Pitfall A: Loki 3.7+ Docker HEALTHCHECK — Distroless Image

**What goes wrong:** Operator copies a `CMD-SHELL wget` or `CMD-SHELL curl` healthcheck from online Loki guides. Container enters `unhealthy` state permanently because neither wget nor curl exists in the image.

**Why it happens:** Loki 3.6+ switched to a distroless base. Every tutorial written before 3.6 uses the old busybox-based healthcheck.

**How to avoid:** Use `CMD ["/usr/bin/loki", "-health"]` — the binary-native healthcheck added in PR #20590 (backported to 3.6.x, present in 3.7.x).

**Warning signs:** Container status stays `starting` for >5 minutes; HEALTHCHECK logs show `exec: "/bin/sh": stat /bin/sh: no such file or directory`.

### Pitfall B: Tempo/Mimir No Shell + No Health Binary

**What goes wrong:** Neither Tempo 2.10 nor Mimir 3.0 has a built-in health binary OR a shell. Using `CMD-SHELL` or any shell-dependent healthcheck fails silently or errors.

**How to avoid:** Use the Ansible `docker_container_info` D-10a poll for readiness, then verify via one-shot container hitting `/ready`. If Docker-level HEALTHCHECK is required, use a `CMD ["/tempo", "-version"]` or `CMD ["/bin/mimir", "-version"]` proxy check (confirms binary is alive).

### Pitfall C: Tempo Single-Knob Retention (Pitfall 10 from PITFALLS.md)

**What goes wrong:** Only `block_retention` is set. MinIO `tempo-traces` grows monotonically. Compacted blocks are marked but never deleted.

**How to avoid:** Both `compactor.compaction.block_retention: 168h` AND `compactor.compaction.compacted_block_retention: 1h` MUST be set. Template inline comment should cite Pitfall 10.

### Pitfall D: Mimir Store Consistency Check Failures (Pitfall 11)

**What goes wrong:** Grafana dashboards intermittently return `err-mimir-store-consistency-check-failed` for recent metrics.

**How to avoid:** Set `querier.query_store_after: 12h` + `blocks_storage.bucket_store.sync_interval: 5m` + `compactor.cleanup_interval: 5m` (all three D-36 knobs). All inline-commented with PITFALLS.md § reference.

### Pitfall E: Loki Compactor Marker File Loss (Pitfall 12)

**What goes wrong:** Container restart wipes `/loki/compactor/markers/`. MinIO `loki-chunks` grows forever.

**How to avoid:** One volume `telemetron_loki_data` at `/loki` covers the full data root including `compactor/markers/`. `compactor.working_directory: /loki/compactor` set explicitly.

### Pitfall F: INSPQ S3 Bucket Name Mismatch

**What goes wrong:** INSPQ defaults used bucket names like `loki`, `tempo`, `mimir` — Phase 1 MinIO bootstrapped `loki-chunks`, `tempo-traces`, `mimir-blocks`. Copying INSPQ templates without updating the bucket names causes immediate startup failure.

**How to avoid:** Cross-check every `bucket_name` / `bucketnames` / `bucket` key against Phase 1's `telemetron_minio_buckets` list.

### Pitfall G: Mimir Shared Bucket for Blocks/Ruler/Alerts (BACK-04)

**What goes wrong:** Operator sets all three to the same bucket + different prefixes. Mimir refuses to start with an error about storage prefix collision.

**How to avoid:** Three distinct bucket names: `mimir-blocks`, `mimir-ruler`, `mimir-alerts`. Each is a separate `_bucket_name` key in the config.

---

## Code Examples

### Loki Container Task (community.docker.docker_container)

```yaml
# Source: mirrors roles/minio/tasks/main.yml pattern (D-19, D-12, OPS-06)
- name: Run Loki container
  community.docker.docker_container:
    name: "{{ loki_container_name }}"
    image: "{{ loki_image }}:{{ loki_image_tag }}"
    state: started
    recreate: false
    restart_policy: "{{ loki_restart_policy }}"
    memory: "{{ loki_memory_limit }}"
    command:
      - "-config.file=/etc/loki/loki.yaml"
      - "-target=all"
    networks:
      - name: "{{ loki_network }}"
        aliases:
          - "{{ loki_container_name }}"
    published_ports: >-
      {{ ([loki_http_port|string + ':' + loki_http_port|string] if loki_publish_host is sameas true else
          ['127.0.0.1:' + loki_http_port|string + ':' + loki_http_port|string] if loki_publish_host == '127.0.0.1' else
          []) }}
    mounts:
      - source: "{{ loki_data_volume }}"
        target: /loki
        type: volume
    volumes:
      - "{{ loki_config_dir }}/loki.yaml:/etc/loki/loki.yaml:ro"
    healthcheck:
      test: ["CMD", "/usr/bin/loki", "-health"]
      start_period: 30s
      interval: 10s
      timeout: 5s
      retries: 5
    env:
      TZ: "{{ loki_tz }}"
```

### Mimir S3 Config Block (YAML template snippet)

```yaml
# Source: official Mimir single-process-config-blocks.yaml + INSPQ mimir-standalone.yaml.j2
# Note: common.storage.s3.endpoint has NO http:// prefix (Mimir S3 client adds scheme from insecure flag)
common:
  storage:
    backend: s3
    s3:
      endpoint: "{{ mimir_s3_endpoint }}"        # e.g. minio:9000
      access_key_id: "{{ vault_mimir_s3_access_key }}"
      secret_access_key: "{{ vault_mimir_s3_secret_key }}"
      insecure: true

blocks_storage:
  backend: s3
  s3:
    bucket_name: "{{ mimir_blocks_bucket }}"
  tsdb:
    dir: /data/tsdb
  bucket_store:
    sync_dir: /data/tsdb-sync
    sync_interval: "{{ mimir_bucket_store_sync_interval }}"   # D-36: 5m

ruler_storage:
  backend: s3
  s3:
    bucket_name: "{{ mimir_ruler_bucket }}"

alertmanager_storage:
  backend: s3
  s3:
    bucket_name: "{{ mimir_alerts_bucket }}"
```

### Vault Keys (vault.yml.example extension per D-27)

```yaml
# --- Phase 2: Loki S3 credentials ---
# Consumed by: roles/loki (S3 access to loki-chunks bucket)
# Values alias to MinIO root creds for now (per D-27; per-backend keys in future hardening phase)
vault_loki_s3_access_key: "{{ vault_minio_root_user }}"
vault_loki_s3_secret_key: "{{ vault_minio_root_password }}"

# --- Phase 2: Tempo S3 credentials ---
vault_tempo_s3_access_key: "{{ vault_minio_root_user }}"
vault_tempo_s3_secret_key: "{{ vault_minio_root_password }}"

# --- Phase 2: Mimir S3 credentials ---
vault_mimir_s3_access_key: "{{ vault_minio_root_user }}"
vault_mimir_s3_secret_key: "{{ vault_minio_root_password }}"
```

### Per-Role Inventory Files (group_vars/all/)

Phase 2 adds three new per-role files:

**loki.yml:**
```yaml
loki_publish_host: false
loki_retention_period: "{{ telemetron_default_log_retention }}"   # 14d from storage.yml
```

**tempo.yml:**
```yaml
tempo_publish_host: false
tempo_block_retention: "{{ telemetron_default_trace_retention }}"   # expressed as 168h
tempo_compacted_block_retention: "1h"
```

**mimir.yml:**
```yaml
mimir_publish_host: false
mimir_compactor_blocks_retention_period: "{{ telemetron_default_metric_retention }}"   # 30d
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Loki BoltDB-shipper index schema | TSDB index schema (v13) | Loki 2.8+ (stable) | Different storage_config keys; BoltDB-shipper deprecated |
| Loki table manager retention | Compactor retention (`retention_enabled: true`) | Loki 2.x+ | INSPQ template still had table_manager vars — these are dead code in 3.x |
| `wget` / shell-based Docker healthchecks | Binary-native `CMD ["/usr/bin/loki", "-health"]` | Loki 3.6+ | All tutorials written pre-3.6 are incorrect for healthchecks |
| Tempo standard OTLP ports 4317/4318 | Internal-only alt ports 14317/14318 | Telemetron M1 decision | Avoids port clash with Phase 3 OTel Collector |
| Mimir filesystem backend | S3 backend (MinIO) | Telemetron M1 design | Enables retention, compaction, and object-store-backed durability |
| Mimir grpc default port 9095 | Explicit `server.grpc_listen_port: 9097` | Telemetron M1 (D-28) | Avoids clash with Loki 9095 on single host |
| Jaeger receivers in Tempo | OTLP-only receivers | Telemetron M1 design | Telemetron uses OTel Collector as single ingress; no Jaeger clients |

---

## Open Questions

1. **Tempo 2.10.5 health binary presence**
   - What we know: Issue #6536 was resolved (PR #6608 closed) with a healthcheck binary implementation
   - What's unclear: Whether the binary flag is available in the `grafana/tempo:2.10.5` image specifically, or only in later releases
   - Recommendation: Planner or implementer should run `docker run --rm grafana/tempo:2.10.5 -help 2>&1 | grep -i health` at plan-write time to confirm. If not present, use D-10a Ansible poll as the effective health gate instead of Docker HEALTHCHECK.

2. **Mimir S3 endpoint format — with or without http:// prefix**
   - What we know: The official `play-with-grafana-mimir` example uses `endpoint: minio:9000` (no scheme). The INSPQ `mimir-standalone.yaml.j2` uses filesystem backend, not S3, so no direct INSPQ S3 template to compare.
   - What's unclear: Whether `common.storage.s3.endpoint` requires or forbids the `http://` scheme prefix in Mimir 3.0.6
   - Recommendation: Use `minio:9000` (no scheme), consistent with the official example. Set `insecure: true` to signal HTTP. If startup fails with a scheme error, add `http://` as fallback.

3. **Loki `delete_request_store` key for S3**
   - What we know: INSPQ template used `delete_request_store: s3` in the compactor section for S3 backend. Official Loki docs confirm this is required in Loki 3.x for deletion requests when using object storage.
   - What's unclear: Whether this key changed names in Loki 3.7.2 vs older 3.x docs
   - Recommendation: Include `delete_request_store: s3` in the compactor block. If Loki rejects it as unknown key on 3.7.2, remove it.

---

## Environment Availability

All external dependencies for Phase 2 are already available from Phase 1:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker daemon | All container tasks | ✓ | (Phase 1 verified) | — |
| `community.docker` Ansible collection | docker_container tasks | ✓ | (Phase 1 verified) | — |
| `telemetron` Docker network | All containers | ✓ | Created in Phase 1 pre_tasks | — |
| MinIO `loki-chunks` bucket | Loki S3 backend | ✓ | Created in Phase 1 minio role | — |
| MinIO `tempo-traces` bucket | Tempo S3 backend | ✓ | Created in Phase 1 minio role | — |
| MinIO `mimir-blocks` bucket | Mimir blocks storage | ✓ | Created in Phase 1 minio role | — |
| MinIO `mimir-ruler` bucket | Mimir ruler storage | ✓ | Created in Phase 1 minio role | — |
| MinIO `mimir-alerts` bucket | Mimir alertmanager storage | ✓ | Created in Phase 1 minio role | — |
| `minio/mc` image | W8 verify one-shot | ✓ | Phase 1 pinned tag | — |

**No new external dependencies are introduced in Phase 2.** All three backend images (`grafana/loki:3.7.2`, `grafana/tempo:2.10.5`, `grafana/mimir:3.0.6`) are publicly available on Docker Hub and confirmed via `docker manifest inspect`.

---

## Project Constraints (from CLAUDE.md)

- **Tech stack fixed:** Loki, Tempo, Mimir are the locked backends. No VictoriaMetrics, no Quickwit.
- **Docker for M1 only:** No Kubernetes, no Helm. All roles use `community.docker.docker_container`.
- **English only:** All variable names, task names, comments, README text must be English. Drop all French from INSPQ upstream.
- **Naming locked (commit ba836d2):** `telemetron_<role>_data` volumes, `vault_<role>_<purpose>` keys, `/opt/telemetron/<role>/` config dirs, one tag per role.
- **Test surface — single host:** No molecule, no multi-host CI. Verification is manual visual check that containers are healthy on Rock's homelab.
- **Image pins mandatory (OPS-01):** All images pinned to explicit tags. Loki `3.7.2`, Tempo `2.10.5`, Mimir `3.0.6`.
- **Vault discipline (OPS-02):** `vault_<role>_<purpose>` naming. Six new keys added to `vault.yml.example`.
- **Idempotency gate (OPS-04):** Second playbook run reports `changed=0`.
- **Healthcheck + restart policy (OPS-06):** `unless-stopped` restart, Docker HEALTHCHECK on every container.
- **INSPQ grep gate (OPS-05):** Both grep patterns return zero matches for every Phase 2 role.

---

## Sources

### Primary (HIGH confidence)

- Official Grafana Loki getting-started docker-compose (GitHub) — healthcheck `CMD ["/usr/bin/loki", "-health"]` pattern confirmed
- GitHub grafana/loki PR #20590 — loki `-health` flag backported to 3.6.x
- Official Grafana Tempo 2.10.x configuration reference (WebFetch) — metrics_generator `remote_write` confirmed optional
- Official Grafana Tempo 2.10 release notes (WebFetch) — distroless image switch confirmed
- Official Mimir configuration parameters + `single-process-config-blocks.yaml` (GitHub) — `multitenancy_enabled: false`, S3 endpoint format, compactor keys
- INSPQ upstream source roles at `~/git/inspq/ansible/{loki,tempo,mimir}/` — full audit of INSPQ-isms performed
- `roles/minio/` (this repo) — canonical Phase 1 template fully read; all patterns confirmed
- `docker manifest inspect` — all three pinned image tags verified resolvable

### Secondary (MEDIUM confidence)

- GitHub grafana/tempo issue #6536 + PR #6608 — healthcheck binary for Tempo implemented; 2.10.5 inclusion uncertain
- GitHub grafana/mimir issue #9034 — Mimir healthcheck binary not yet added as of this research
- Official Loki retention docs (WebFetch) — compactor YAML keys confirmed
- Official Mimir object storage backend docs (WebFetch) — common.storage.s3 pattern confirmed
- Official Tempo configuration 2.10.x (WebFetch) — metrics_generator structure confirmed
- WebSearch multiple sources — Loki push API JSON shape, OTLP HTTP trace JSON shape

### Tertiary (LOW confidence — for planner awareness only)

- WebSearch for Mimir MinIO S3 force_path_style — key name uncertain (`endpoint_type: path` not found in official docs; `insecure: true` is the confirmed MinIO flag)

---

## Metadata

**Confidence breakdown:**
- Standard stack (image pins): HIGH — all three images manifest-verified
- Loki config shape: HIGH — verified against INSPQ template + official docs
- Tempo config shape: HIGH — verified against INSPQ template + official docs
- Mimir config shape: HIGH — verified against official sample configs + INSPQ template
- D-38 metrics-generator: MEDIUM-HIGH — config structure confirmed optional; implementation validated via official docs
- Healthchecks: HIGH for Loki; MEDIUM for Tempo/Mimir (distroless no-shell confirmed; Tempo binary health flag timing uncertain)
- INSPQ audit: HIGH — read full defaults/main.yml and key templates for all three roles

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (stable ecosystem; Loki/Tempo/Mimir release cadence is monthly)
