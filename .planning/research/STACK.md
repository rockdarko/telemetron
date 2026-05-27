# Technology Stack — v1.1.0 Delta

**Project:** Telemetron
**Milestone:** v1.1.0 — Garage migration + backlog sweep
**Researched:** 2026-05-26
**Scope:** NEW additions only. The 12 validated M1 roles (Loki 3.7.2, Tempo 2.10.5, Mimir 3.0.6, Prometheus 3.11.3, OTel Collector Contrib 0.152.0, Fluent Bit 4.2.3, Alertmanager v0.32.1, Grafana OSS 13.0.1, Karma v0.130, node_exporter v1.11.1, MinIO RELEASE.2025-04-22T22-12-26Z, nfsd opt-in) are NOT re-researched here.

---

## 1. Garage — MinIO Replacement

### Image Pin

| Image | Tag | Architecture | Confidence |
|-------|-----|--------------|:----------:|
| `dxflrs/garage` | `v2.3.0` | linux/amd64, linux/arm64 (multi-arch manifest) | HIGH |

**Why v2.3.0:** Latest stable as of 2026-04-16. The v2.x line is the current major; v1.3.1 is a maintenance branch. v2.3.0 adds auto-key and auto-bucket bootstrap via env vars (`GARAGE_DEFAULT_ACCESS_KEY`, `GARAGE_DEFAULT_SECRET_KEY`, `GARAGE_DEFAULT_BUCKET`), which eliminates the separate `mc` bootstrap container entirely — this is the key simplification over v2.2.0 and all v1.x releases. "No breaking changes when migrating from Garage v2.2.0."

Multi-arch confirmed via `docker manifest inspect dxflrs/garage:v2.3.0` — linux/amd64, linux/arm64, linux/386, linux/arm. M1 is amd64; arm64 for free when it lands.

### Port Map (replaces MinIO)

| Port | Service | Notes |
|------|---------|-------|
| 3900 | S3 API | The only port Loki/Tempo/Mimir need. Replaces MinIO's 9000. |
| 3901 | RPC | Cluster gossip. Needed even for single-node — Garage binds it. |
| 3902 | S3 web | Static website hosting. Not used by observability stack. |
| 3903 | Admin API | `garage` CLI and admin token calls reach here. |

**Host-publish default:** S3 API (3900) matches MinIO's pattern of internal-only access via Docker bridge. Admin API (3903) for CLI bootstrap. Console (3902) — default off, no observability consumer.

### S3 API Compatibility with Loki/Tempo/Mimir

Garage implements the full S3 operations the LGTM stack needs (HIGH confidence — verified against Garage's own S3 compatibility matrix):

| Operation | Status | Used by |
|-----------|--------|---------|
| PutObject / GetObject / DeleteObject | Implemented | All three |
| DeleteObjects (bulk) | Implemented | Compactor cleanup |
| CreateMultipartUpload / UploadPart / CompleteMultipartUpload / AbortMultipartUpload | Implemented | Mimir block uploads |
| ListObjects / ListObjectsV2 | Implemented | Querier block discovery |
| CreateBucket / HeadBucket | Implemented | Bucket bootstrap |
| Bucket versioning | NOT implemented | Not used by LGTM |
| ACL / Bucket policy endpoints | NOT implemented | Not used by LGTM |
| Server-side encryption | NOT implemented | Not used in this stack |
| Object tagging | NOT implemented | Not used by LGTM |

**Path-style requests:** Always enabled in Garage ("path-style requests are always enabled, whether or not vhost-style is configured"). This is what Loki (`s3forcepathstyle: true`), Tempo (`forcepathstyle: true`), and Mimir (`insecure: true` + no-scheme endpoint) require. No vhost DNS wildcard setup needed.

**AWS checksum header note:** One real-world migration (SendRec) had to set `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` and `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required` for their AWS SDK client. The Grafana LGTM stack uses Thanos/cortex-derived S3 clients, NOT the AWS SDK — this flag is not applicable. No equivalent flag in Loki/Tempo/Mimir config. This is a non-issue for the LGTM S3 client implementations.

### Endpoint Format in Loki/Tempo/Mimir Configs

The endpoint format does NOT change from MinIO — same pattern (host:port, no scheme, insecure flag signals HTTP):

```yaml
# Mimir (common.storage.s3.endpoint) -- was: minio:9000
endpoint: "garage:3900"
insecure: true

# Tempo (storage.trace.s3.endpoint) -- was: minio:9000
endpoint: "garage:3900"
insecure: true

# Loki (storage_config.aws.s3) -- Loki uses full URL form
s3: "http://garage:3900/loki-chunks"
```

Loki's S3 config uses a different format than Tempo/Mimir (full URL vs host:port). The container alias in the `telemetron` Docker bridge network becomes `garage` (replacing `minio`). All five bucket names remain the same (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`).

### Key Format

Garage auto-generates keys with a `GK` prefix (e.g., `GKabcdef...`). This is Garage's format — the LGTM stack S3 clients treat access key ID as an opaque string, so `GK`-prefixed keys work identically to MinIO-style alphanumeric keys. No config change in Loki/Tempo/Mimir is needed.

### Bucket Bootstrap Strategy — Replacing `mc`

**MinIO approach (M1):** `minio/mc` one-shot container. `mc alias set`, then `mc mb` for each bucket.

**Garage v2.3.0 approach:** No separate bootstrap container. Two options:

**Option A — `--single-node` + `--default-bucket` auto-init (v2.3.0+):**
Set `GARAGE_DEFAULT_ACCESS_KEY`, `GARAGE_DEFAULT_SECRET_KEY`, `GARAGE_DEFAULT_BUCKET` env vars and start with `garage server --single-node --default-bucket`. Creates layout + one default bucket automatically. Does NOT create all 5 buckets needed by the LGTM stack.

**Option B — `docker exec` bootstrap (recommended for multi-bucket setup):**
```bash
# Run inside container after startup:
docker exec telemetron-garage garage layout assign -z dc1 -c 10G <node-id>
docker exec telemetron-garage garage layout apply --version 1
docker exec telemetron-garage garage key create telemetron-key
docker exec telemetron-garage garage bucket create loki-chunks
# ... repeat for all 5 buckets
docker exec telemetron-garage garage bucket allow --read --write --owner loki-chunks --key <key-id>
```

**In Ansible:** Use `community.docker.docker_container_exec` (already used in `roles/alertmanager/tasks/verify.yml` and `roles/grafana/tasks/verify.yml` for UAT probes — same pattern). The bootstrap task runs after the container reaches healthy state, identical to the MinIO bootstrap pre-poll gate (D-10a pattern).

**Node ID retrieval:**
```bash
docker exec telemetron-garage garage status
# or: cat <data_dir>/meta/node_key.pub | xxd -p | tr -d '\n'
```

**No `mc` needed:** The `garage` binary ships inside `dxflrs/garage` — no separate client image required. This eliminates the `minio_mc_image` / `mimir_mc_image` pins entirely. Remove both.

### Garage Configuration File (TOML)

Garage requires a `garage.toml` (rendered by the role, bind-mounted). Minimum single-node shape:

```toml
metadata_dir = "/var/lib/garage/meta"
data_dir     = "/var/lib/garage/data"
db_engine    = "lmdb"          # recommended; sqlite also valid
replication_factor = 1

rpc_bind_addr    = "[::]:3901"
rpc_public_addr  = "127.0.0.1:3901"
rpc_secret       = "<openssl rand -hex 32>"  # 32-byte hex; unique per deploy

[s3_api]
s3_region    = "us-east-1"     # Must match what Loki/Tempo/Mimir send; they send "us-east-1"
api_bind_addr = "[::]:3900"
# root_domain intentionally omitted -- path-style always works, no vhost DNS needed

[admin]
api_bind_addr = "[::]:3903"
admin_token   = "<openssl rand -base64 32>"  # required for garage CLI calls to admin API
```

`s3_region` must match the `region:` field in Loki, Tempo, and Mimir S3 configs. All three currently use `us-east-1` (M1 defaults). Keep that value in Garage to avoid breaking region-mismatch errors.

`db_engine = "lmdb"` is the Garage-recommended engine ("use LMDB for production"). SQLite is valid for testing but has worse write performance under concurrent access.

### Healthcheck

Garage's S3 API does not expose a MinIO-style `/minio/health/ready` endpoint. The equivalent for Garage is:

```
GET http://127.0.0.1:3900/health
```

Garage returns HTTP 200 when healthy. Use `CMD-SHELL` healthcheck:
```
curl -sf http://127.0.0.1:3900/health || exit 1
```

Or probe the admin API: `GET http://127.0.0.1:3903/health` (requires no token for the health endpoint).

**Confidence:** MEDIUM — Garage docs confirm an HTTP health endpoint but the exact path for v2.3.0 should be verified at execute time (`docker run --rm dxflrs/garage:v2.3.0 /garage --help 2>&1` and inspect the admin API).

### What NOT to Add

- Do NOT add a separate S3 client image (no `garagehq/garage-mc` or `minio/mc`). The `garage` binary inside `dxflrs/garage` handles all bucket management via `docker exec`. Remove `minio_mc_image` and `mimir_mc_image` vars when replacing those roles.
- Do NOT add `awscli` or `s3cmd` — they're not needed for bucket bootstrapping via `docker exec`.
- Do NOT configure `root_domain` in `[s3_api]` — path-style always works; vhost-style requires wildcard DNS the homelab quickstart doesn't need.

---

## 2. Mimir — Retention Rewire Under `limits:`

### What Broke and Why

The M1 `mimir.yaml.j2` template removed `compactor.blocks_retention_period` when it was rejected by Mimir 3.0 (field moved from compactor config to per-tenant limits). The `mimir_compactor_blocks_retention_period` default var (`30d`) was wired nowhere — the template has no `compactor_blocks_retention_period` under `limits:`. Mimir silently used its built-in default (7 days).

### Fix

Add `compactor_blocks_retention_period` under the existing `limits:` block in `mimir.yaml.j2`. No new var needed — `mimir_compactor_blocks_retention_period` already exists in `defaults/main.yml` (line 63), set to `{{ telemetron_default_metric_retention | default('30d') }}`.

**Exact YAML change in template:**

```yaml
limits:
  max_global_series_per_user:   {{ mimir_max_global_series_per_user }}
  max_global_series_per_metric: {{ mimir_max_global_series_per_metric }}
  compactor_blocks_retention_period: {{ mimir_compactor_blocks_retention_period }}  # ADD THIS LINE
```

This is the correct location per Grafana docs: "For single-tenant anonymous deployments, simply place the configuration under `limits:` in your main config file without needing a separate runtime configuration." (HIGH confidence — verified against Grafana Mimir retention docs)

**Duration format note:** Mimir accepts `y` (years), `w` (weeks), `d` (days), `h` (hours). `30d` is valid. `m` is NOT valid for months (reserved for minutes). The default `30d` is correct.

**No runtime config file needed.** The runtime config (`-runtime-config.file`) is for per-tenant overrides in multi-tenant deployments. Single-tenant anonymous deployments put retention directly in `limits:` in the main config.

---

## 3. Tempo — `compaction_window` Wire-Up

### What the Backlog Item Actually Is

`roles/tempo/defaults/main.yml` line 82 defines `tempo_compactor_block_ranges_period: 5m`. This var was never used in the template (the field it was intended to map to, `block_ranges_period`, doesn't exist in Tempo 2.10's CompactorConfig and was removed at config-load time). The template comment documents this.

The actual Tempo 2.10 compaction config field is `compaction_window` (confirmed against Grafana Tempo configuration docs). Default is `1h`.

### Fix

Use Option B (full wire-up) over Option A (delete orphan var):

Rename the var `tempo_compactor_block_ranges_period` to `tempo_compactor_compaction_window`, default to `1h`, and add to the template:

```yaml
compactor:
  compaction:
    block_retention:           {{ tempo_block_retention }}
    compacted_block_retention: {{ tempo_compacted_block_retention }}
    compaction_window:         {{ tempo_compactor_compaction_window }}
```

This fulfills the original operator-control intent of the orphan var. The `1h` default matches Tempo's built-in default (so no behavior change on first deploy; operators can tune it in inventory).

**No new images or versions needed.**

---

## 4. Fluent Bit — `@timestamp` Fallback Fix

### Why `Add @timestamp ${ingest_time}` Fails in FB 4.2.3

Two confirmed reasons (HIGH confidence):

1. **`${ingest_time}` is not a Fluent Bit built-in variable.** It is not a defined env var. `${...}` in Fluent Bit classic config performs environment variable substitution — if the env var is unset, the value is empty or literal `${ingest_time}`. The `modify` filter's `Add` operation with an empty value is a no-op or produces an invalid field.

2. **The Modify filter has no dynamic time functions.** The Modify filter supports only literal string operations (`Add`, `Set`, `Remove`, `Rename`, `Copy`, etc.) — no dynamic time functions, no `${ingest_time}`, no `${now}`. Feature request (#7054 on fluent/fluent-bit) was filed and closed without implementation. This is a fundamental capability gap, not a syntax issue.

3. **`@` prefix in key names.** Keys beginning with `@` may trip the Modify filter's field-name validation in FB 4.x. This is secondary to reason 2 — even with a valid key name, the dynamic value source doesn't exist.

### Correct Fix for FB 4.2.3

Use the **Lua filter** — the existing `enrich.lua` already runs on `docker.*` records. Add timestamp injection there:

```lua
function enrich(tag, timestamp, record)
  -- ... existing enrichment logic ...
  -- Inject fallback @timestamp from Fluent Bit's ingest time.
  -- Conditional guard: don't overwrite a timestamp already in the record.
  -- os.date("!...") produces UTC ISO8601. Loki stores as structured metadata.
  -- Return code 2: preserves original event timestamp, updates record body.
  if not record["@timestamp"] then
    record["@timestamp"] = os.date("!%Y-%m-%dT%H:%M:%SZ", os.time())
  end
  return 2, timestamp, record
end
```

Return code `2`: keeps the original Fluent Bit event timestamp (which Loki uses for ingestion ordering), adds `@timestamp` field to the record body only if absent. The `if not record["@timestamp"]` guard avoids overwriting a timestamp already parsed from the log line.

**No new images, no new filters, no new Lua file.** The existing `enrich.lua` file already has the Lua function called on docker.* records. The fallback timestamp is added to the existing function body.

---

## 5. OTel Collector — `service.name` → `service_name` Label Resolution

### What Happens Today

Logs flowing through `otlphttp/loki` (the OTel Collector → Loki path used by Telemetron) arrive at Loki's native OTLP endpoint. Loki's OTLP ingestion path promotes 17 Resource Attributes to index labels by default. `service.name` is one of them. The promotion is automatic — Loki converts dots to underscores, so `service.name` becomes the Loki label `service_name`.

**This is not a bug — it is Loki's documented behavior** (HIGH confidence — verified against Grafana Loki OTLP docs): "Dots (.) are converted to underscores (_). Loki does not support `.` or any other special characters other than `_` in label names."

### The Conflict

The M1 Fluent Bit `enrich.lua` populates a `service` key in Loki records (from `org.telemetron.service` Docker label). This goes through the OTel Collector's logs pipeline as a log attribute (not a resource attribute). Separately, OTel SDK instrumented apps set `service.name` as a Resource Attribute, which Loki promotes to `service_name`.

Result: two coexisting Loki labels — `service` (from FB Lua enrichment via OTel body/attribute path) and `service_name` (from OTel Resource Attribute promotion). The M1 spec expected `service` to be the canonical label; OTel-instrumented apps produce `service_name`.

### Decision Point (Three Options)

| Option | What it means | Tradeoff |
|--------|---------------|---------|
| **A. Accept OTel convention** (`service_name`) | Change Grafana dashboard queries and Loki label filters to use `service_name`; rename the FB Lua `service` field to `service_name` for consistency | Breaking change to existing dashboard queries; aligns with OTel standard and future tooling |
| **B. Rename at OTel Collector** (transform `service.name` → `service`) | Add a `transform` processor in the OTel logs pipeline that copies resource attribute `service.name` to a log attribute named `service`; remove from resource so Loki doesn't promote it | Adds processor complexity; hides the OTel convention rather than embracing it |
| **C. Rename at Loki server** (otlp_config override) | Add `limits_config.otlp_config.resource_attributes:` in Loki config to store `service.name` as structured metadata instead of index label; rely on FB Lua's `service` label | Loki config change; `service_name` disappears from Loki's label set; more opaque |

**Recommendation: Option A.** Accept OTel convention. `service_name` is what OTel-aware tooling (Grafana Explore Logs, LogQL label selectors in dashboards) expects. Rename the Fluent Bit enrich Lua output key from `service` to `service_name` for parity. Update any Grafana dashboard queries that use `{service="..."}` to `{service_name="..."}`. This is a one-time 4-line change in `enrich.lua` + dashboard label filter update.

**Config changes required for Option A:**

1. `roles/fluentbit/files/enrich.lua`: rename `record["service"]` to `record["service_name"]` in the enrichment output
2. `roles/fluentbit/templates/fluent-bit.conf.j2`: update any allowlist filter `Add service` references if present
3. Grafana dashboards: any LogQL that uses `{service="..."}` becomes `{service_name="..."}`
4. No OTel Collector config change needed — `service.name` resource attribute flows naturally to `service_name` label in Loki via the OTLP ingestion path

**No new images, no new processors.** The `otlphttp/loki` exporter already does the right thing. The label normalization (`service.name` → `service_name`) is Loki-side automatic behavior on OTLP ingestion, not controllable from the OTel Collector side without adding a `transform` processor.

---

## Alternatives Considered

| Slot | Recommended | Alternative | Why Not |
|------|-------------|-------------|---------|
| S3 replacement | Garage v2.3.0 | SeaweedFS | Heavier; multi-protocol surface overkill for single-node homelab |
| S3 replacement | Garage v2.3.0 | RustFS | Newer project, less battle-tested integration with LGTM stack |
| S3 replacement | Garage v2.3.0 | Keep archived MinIO | Growing CVE surface; contradicts "maintainable homelab stack" pitch |
| FB timestamp | Lua extension in existing enrich.lua | New separate Lua file | Adds file count; existing enrich.lua already on the right Match path |
| FB timestamp | Lua `os.date` | record_accessor modifier | record_accessor doesn't support dynamic time functions in FB 4.x |
| Label fix | Rename FB output to `service_name` (Option A) | OTel Collector transform processor (Option B) | Adds pipeline complexity; hides the OTel convention rather than embracing it |
| Mimir retention | `limits:` block in main config | Runtime config file | Runtime config file is for multi-tenant per-tenant overrides; unnecessary for single-tenant anonymous |
| Tempo compaction | Rename var + wire to `compaction_window` | Delete orphan var | Deletion removes operator control knob; renaming preserves intent |

---

## Version Compatibility Check

| Pair | Status | Notes |
|------|--------|-------|
| Garage v2.3.0 ↔ Loki 3.7.2 | Expected PASS | Path-style S3, HTTP, no TLS — Garage supports all; Loki's `s3forcepathstyle` + `insecure` flags confirmed |
| Garage v2.3.0 ↔ Mimir 3.0.6 | Expected PASS | Endpoint format identical to MinIO; multipart upload supported; path-style always on |
| Garage v2.3.0 ↔ Tempo 2.10.5 | Expected PASS | `forcepathstyle: true` + `insecure: true` pattern; all required S3 ops implemented |
| Mimir 3.0.6 `limits.compactor_blocks_retention_period` | PASS (doc-confirmed) | Verified field name and YAML location per Grafana docs |
| Tempo 2.10.5 `compaction.compaction_window` | PASS (doc-confirmed) | Valid field in Tempo 2.10 CompactorConfig; default 1h |
| Fluent Bit 4.2.3 Lua `return 2` code | PASS | Preserves timestamp, updates record — correct for `@timestamp` injection |

**Caveat on Garage integration:** "Expected PASS" is based on S3 compatibility matrix analysis, not a documented tested combination with the LGTM stack. Verify at execute time by running `playbooks/smoke_test.yml` after the Garage role deploys.

---

## Sources

### HIGH Confidence (official docs / direct verification)
- [Garage releases (Forgejo)](https://git.deuxfleurs.fr/Deuxfleurs/garage/releases) — v2.3.0 released 2026-04-16, confirmed latest stable
- [dxflrs/garage Docker Hub](https://hub.docker.com/r/dxflrs/garage) — v2.3.0 tag confirmed; multi-arch via `docker manifest inspect` (amd64, arm64, 386, arm)
- [Garage S3 compatibility matrix](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/) — multipart, list, delete all implemented; versioning/ACL/SSE not implemented
- [Garage quick-start](https://garagehq.deuxfleurs.fr/documentation/quick-start/) — TOML format, ports, init commands, rpc_secret generation
- [Garage configuration reference](https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/) — path-style always enabled; db_engine options
- [Grafana Mimir retention config](https://grafana.com/docs/mimir/latest/configure/configure-metrics-storage-retention/) — `limits.compactor_blocks_retention_period` location confirmed; duration format
- [Tempo compactor config reference](https://grafana.com/docs/tempo/latest/configuration/) — `compaction.compaction_window` valid; `block_ranges_period` not present
- [Loki OTLP ingestion docs](https://grafana.com/docs/loki/latest/send-data/otel/) — `service.name` → `service_name` dot-to-underscore confirmed; 17 default promoted attributes listed
- [Fluent Bit Lua filter docs](https://docs.fluentbit.io/manual/data-pipeline/filters/lua) — return code 2 semantics; timestamp parameter format
- [Fluent Bit Modify filter docs](https://docs.fluentbit.io/manual/data-pipeline/filters/modify) — no dynamic time functions; only literal string operations

### MEDIUM Confidence (community-verified, single source)
- [How We Replaced MinIO with Garage — DEV Community](https://dev.to/alexneamtu/how-we-replaced-minio-with-garage-for-self-hosted-s3-storage-23f7) — AWS checksum flag note (non-issue for LGTM stack); GK key prefix; rclone migration pattern
- [Fluent Bit issue #7054](https://github.com/fluent/fluent-bit/issues/7054) — Modify filter timestamp feature request; closed without implementation

### LOW Confidence (verify at execute time)
- Garage health endpoint path (`GET /health` on port 3900) — stated in community guides; verify against `dxflrs/garage:v2.3.0` at execute time
