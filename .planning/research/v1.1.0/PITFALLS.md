# Pitfalls Research — v1.1.0 Supplement

**Domain:** Garage migration + backlog config fixes in an existing Ansible-Docker LGTM stack (Telemetron v1.0.1)
**Researched:** 2026-05-26
**Confidence:** HIGH for Garage S3 compatibility gaps (verified against official Garage docs + Mimir/Loki/Tempo GitHub issues). HIGH for Mimir retention field location (official docs + KnownFields strict parsing confirmed). MEDIUM for FB timestamp_fallback fix (no authoritative upstream issue found; analysis from FB docs + UAT evidence). HIGH for OTel→Loki service_name transformation (official Loki docs, upstream OTel collector-contrib issue #32497).

This file supplements the base PITFALLS.md from 2026-05-17. That file covers M1 pitfalls (bucket bootstrap race, Grafana UID provisioning, cardinality, idempotency, etc.). This file covers only the v1.1.0 migration-specific pitfalls — Garage replacement of MinIO, four M1 backlog config items, and integration hazards that surface when you change the object storage backend on a live stack.

---

## Critical Pitfalls — Garage Migration

### Pitfall G-1: Garage requires a layout assignment before S3 API calls work

**What goes wrong:**
The Garage bootstrap sequence is four steps, not one. Operators who come from MinIO assume "container up → `mc mb` → done" will translate to "container up → `garage bucket create` → done." It does not. Without a `garage layout assign` + `garage layout apply` cycle, S3 API calls — including bucket creation and `PutObject` — fail or silently return no data because no node in the cluster has been assigned a storage role. The S3 endpoint responds (the API port is open) but requests fail with opaque errors or 500s.

**Why it happens:**
Garage is designed as a distributed system first; even single-node deployments must go through the layout-assignment dance. The layout defines which node stores which data and at what capacity. MinIO doesn't have this concept — the server owns its own directory unconditionally. The Garage docs bury this step under "Setting up the cluster," which reads like a distributed-mode concern; single-node operators skip it and hit a wall.

**Consequences:**
- Loki/Tempo/Mimir start, connect to Garage's S3 endpoint, fail to `PutObject` blocks, and crash-loop or degrade silently without the layout step
- The `garage bucket create` command itself succeeds (it's an admin-API call, not S3), but writes to the bucket via S3 fail
- The `garage status` output shows the node as "NO ROLE ASSIGNED" — if bootstrap automation doesn't inspect this, it will report success

**Prevention:**
The Garage Ansible role must run this exact sequence before any S3 client (Loki/Tempo/Mimir) can use it:
1. Start Garage container
2. Poll admin API readiness (not just S3 port — different port, different health signal)
3. `garage layout assign -z garage1 -c <capacity> <node_id>` — capacity in bytes or SI units
4. `garage layout apply --version 1`
5. `garage key create <key-name>` — note the returned `access_key_id` / `secret_access_key`
6. `garage bucket create <bucket-name>` — once per bucket (5 for Telemetron: loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts)
7. `garage bucket allow --read --write --owner <bucket-name> --key <key-name>` — once per bucket per key

The `community.docker.docker_container_exec` polling pattern from M1 (gate from RETROSPECTIVE.md) applies here: do not assume the Garage container is ready just because Docker reports "started." Poll the admin API endpoint (`http://garage:3903/health`) before running layout steps.

**Alternative — `garage-single-node` image:**
The `bikeshedder/garage-single-node` wrapper image handles steps 2–7 automatically on startup via env vars (`GARAGE_ACCESS_KEY_ID`, `GARAGE_SECRET_ACCESS_KEY`, `GARAGE_BUCKETS`). This is the recommended approach for Telemetron's single-host homelab target. The Garage role bootstrap task becomes: start container → poll healthcheck → done. Bucket creation is declarative via env var.

**Detection:**
- `garage status` shows node with empty capacity or "NO ROLE ASSIGNED" after container start
- Loki/Tempo/Mimir logs show `S3 API error: 500` or `NoSuchBucket` immediately after start (even though bucket was created via admin API)
- `garage bucket list` shows buckets but `mc ls garage/bucket/` returns empty or errors

**Phase to address:** Garage role port — first task after container start is the layout/key/bucket sequence (or hand it to garage-single-node). This is the **exact analog of Pitfall 1 (bucket bootstrap race)** from M1, but with more steps.

---

### Pitfall G-2: Endpoint format mismatch — Loki uses `http://` prefix, Mimir/Tempo do not

**What goes wrong:**
Loki's S3 storage_config requires the endpoint WITH the `http://` prefix (e.g., `http://garage:3900`). Mimir's `common.storage.s3.endpoint` and Tempo's `storage.trace.s3.endpoint` require the endpoint WITHOUT the scheme prefix (e.g., `garage:3900`), signaling HTTP vs HTTPS via an `insecure: true` flag. This is already the case in M1 with MinIO — the pattern is identical with Garage. Swapping `minio:9000` for `garage:3900` in all three templates is mechanical but asymmetric. Any copy-paste between the role templates will produce a broken config that fails silently with TLS errors or connection-refused at the wrong port.

**Consequences:**
- Loki with `endpoint: garage:3900` (missing `http://`) fails SSL handshake against an HTTP-only endpoint, logs TLS errors, and cannot persist chunks
- Mimir/Tempo with `endpoint: http://garage:3900` fail at config parsing because the scheme is embedded in the endpoint string AND `insecure: true` — the combination is treated as an https URL, then a TLS handshake fails

**Prevention:**
- Loki template: `endpoint: "http://{{ garage_s3_host }}:{{ garage_s3_port }}"` (scheme required, same as current Loki template for MinIO)
- Mimir template: `endpoint: "{{ garage_s3_host }}:{{ garage_s3_port }}"` (no scheme, same as current Mimir template)
- Tempo template: `endpoint: "{{ garage_s3_host }}:{{ garage_s3_port }}"` (no scheme, same as current Tempo template)
- The existing vars can stay scheme-aware if the role owns the scheme prefix (Loki adds it in template; Mimir/Tempo get the bare host:port)
- Add a comment next to each endpoint var noting the scheme expectation

**Detection:**
- Loki logs: `msg="failed to put object" err="Put \"garage:3900/loki-chunks/...\": unsupported protocol scheme"` (missing http://)
- Mimir/Tempo logs: TLS errors or connection reset against port 3900 if scheme is accidentally included

**Phase to address:** Garage role port + all three backend role template updates. A single inventory var `garage_s3_endpoint_base` (scheme-free) plus role-specific templating that adds the scheme only where required is the cleanest approach.

---

### Pitfall G-3: Garage does not support object tagging — Loki compactor delete path may break

**What goes wrong:**
Garage's S3 API does not implement `PutObjectTagging` or `GetObjectTagging` (both listed as "❌ Missing" in the official Garage S3 compatibility matrix). Loki's TSDB compactor marks chunks for deletion by writing marker files; it does NOT use S3 tagging for this. However, some Loki configurations or third-party tooling attempt to use object tags for lifecycle management. More importantly: if any future Loki, Tempo, or Mimir version adds tagging to their compaction/deletion workflow, Garage will return a 501 Not Implemented, which may silently drop the request and leave objects undeleted.

**Current risk for v1.1.0:** LOW. Loki 3.7.2, Tempo 2.10.5, and Mimir 3.0.6 do NOT use S3 object tagging in their standard compaction flows. The risk is forward-looking, not immediate.

**Prevention:**
- Do not set any MinIO lifecycle policies on Garage buckets (lifecycle = versioning/tagging dependency)
- When upgrading Loki/Tempo/Mimir beyond v1.1.0 pinned versions, scan changelogs for any mention of S3 tagging or lifecycle policy integration before bumping
- Do not use the Garage bucket's built-in expiry (if supported) — let Loki/Tempo/Mimir compactors own deletion exclusively

**Phase to address:** Document in Garage role README + note in the post-upgrade checklist. Not a blocker for v1.1.0 given pinned versions.

---

### Pitfall G-4: Garage port numbers differ from MinIO — three ports, not two

**What goes wrong:**
MinIO exposes two ports: API (9000) and console (9001). Garage exposes three: S3 API (3900 by default), admin API (3903), and web console (optional, 3902). The bootstrap logic — specifically the "wait for S3 to be ready" health poll — must target port 3900, not 3903 (admin) or 3902 (console). The Garage admin API has its own healthcheck path (`/health`); the S3 port has no `/minio/health/ready` analog — S3 readiness must be inferred from a successful S3 ListBuckets call or from the admin health endpoint.

**Why it matters for Telemetron's existing bootstrap pattern:**
The MinIO bootstrap.yml polls `minio_healthcheck_test` via `docker_container_info` (which reads Docker's own HEALTHCHECK status, not a port check). Garage's container HEALTHCHECK must be configured to probe a meaningful port. The `dxflrs/garage` official image does not ship a built-in HEALTHCHECK. It must be added in the Ansible role's `container:` definition.

**Prevention:**
- In the Garage role's `docker_container` task, declare an explicit `healthcheck:` that probes the admin health endpoint: `test: ["CMD", "/usr/bin/garage", "status"]` — or an HTTP probe against `http://127.0.0.1:3903/health` if curl is available in the image
- Set `loki_s3_endpoint`, `tempo_s3_endpoint`, and `mimir_s3_endpoint` to `:3900` (not 9000)
- Keep port 3900 on the Docker bridge network only (D-13 pattern: no host publish by default); admin port 3903 on bridge-only too
- Update the port snapshot in `CLAUDE.md` (and `docs/architecture.md`) to reflect the three Garage ports

**Detection:**
- Health poll times out waiting for `healthy` if the HEALTHCHECK probes the wrong port
- Loki/Tempo/Mimir logs show `connection refused` against port 9000 (old MinIO port not updated in vars)

**Phase to address:** Garage role port. Port update is mechanical but touches the inventory var defaults for all three backend roles.

---

### Pitfall G-5: Data migration from MinIO to Garage — stopping services is mandatory; rclone sync alone is not enough

**What goes wrong:**
The appealing migration path is: start Garage alongside MinIO, `rclone sync minio:bucket garage:bucket`, update configs, restart backends. The risk: Loki/Tempo/Mimir are still writing to MinIO during the rclone sync. Any block that is partially written (WAL flush in progress, multipart upload not yet completed) and then synced to Garage may arrive in a corrupt or incomplete state. Worse: Loki's TSDB index and chunk objects have referential integrity — if the index is synced first and references chunks that haven't been synced yet, queries against the migrated store will fail or panic.

**Additional rclone gotcha:** Rclone signed-request encoding mismatch. When syncing from MinIO to Garage, adding `--s3-sign-accept-encoding=false` to the rclone command avoids `SignatureDoesNotMatch` errors caused by different content-encoding header expectations between MinIO and Garage.

**What the actual safe procedure looks like:**
1. Stop Fluent Bit (no new log ingest)
2. Stop Prometheus remote_write to Mimir (or pause scraping)
3. Let Loki/Tempo/Mimir flush their WALs (wait for their health endpoints to stabilize)
4. Stop Loki, Tempo, Mimir
5. `rclone sync` each bucket from MinIO to Garage (per-bucket, with `--progress`)
6. Start Garage, verify bucket contents
7. Update inventory vars to point at Garage endpoint
8. Start Loki, Tempo, Mimir, Fluent Bit, Prometheus

**Acceptable-loss alternative for homelab:** Accept that historical data is not migrated. Start Garage with empty buckets. Existing MinIO data becomes inaccessible (old dashboards show gaps before migration date). For a homelab this is often acceptable and eliminates the entire migration risk surface.

**Silent failure mode:** If you run `rclone sync` while Loki is still writing, the Loki TSDB index objects will reference chunks that may not yet be in Garage after the sync (if the chunk write landed after the corresponding index entry was synced). Loki will query against Garage, see the index entry, fetch the chunk URL, get a 404 from Garage, and log an error but not crash. The user sees gaps in Grafana log queries with no obvious error surfaced at the dashboard level — the error is buried in Loki's own logs.

**Phase to address:** Garage role port — the role README must document both paths (full migration with downtime vs fresh-start). The playbook migration path must be stop-sync-start, not live-sync.

---

### Pitfall G-6: Loki `object_store: aws` versus `object_store: s3` — Garage requires the `aws` provider

**What goes wrong:**
Telemetron's current `loki.yaml.j2` uses `object_store: s3` in the `schema_config`. Community forum posts and at least one reproducible issue report (Grafana community forums, 2025) describe Loki making only GET requests to Garage — no writes — when `object_store: s3` is used. Switching to `object_store: aws` (which causes Loki to use the `storage_config.aws` stanza for the S3 backend) resolved the issue. The `s3` value in `object_store` is a shorthand that may resolve to a different code path than the explicit `aws` S3 storage driver.

**Confidence:** MEDIUM. The community forum thread did not confirm whether the `aws` change alone was the fix, and the thread is unresolved. However, the safe default is `aws` — it is what all Grafana example configs for S3-compatible storage use, and the MinIO integration in M1 may have worked by accident because MinIO is more permissive about S3 wire format.

**Prevention:**
- In `loki.yaml.j2` `schema_config.configs[].object_store`: use `aws` not `s3`
- In `storage_config`: ensure the `aws:` stanza is present and populated
- After deploying Loki against Garage, immediately verify with a `curl -s http://loki:3100/metrics | grep loki_boltdb_shipper_compact` — if chunks are landing in Garage, this counter moves; if they are not, it stays at 0 while Loki appears healthy

**Phase to address:** Loki role template update alongside the Garage migration.

---

## Critical Pitfalls — Mimir Retention Config

### Pitfall M-1: `limits.compactor_blocks_retention_period` vs the orphan `mimir_compactor_blocks_retention_period` default var

**What goes wrong:**
The v1.0.1 `mimir.yaml.j2` template removed `compactor.blocks_retention_period` (which was the wrong location — caught in Phase 2 UAT, noted in the template comment "Removed: blocks_retention_period -- field is not on compactor.Config in Mimir 3.0"). However, `roles/mimir/defaults/main.yml` STILL defines `mimir_compactor_blocks_retention_period: "{{ telemetron_default_metric_retention | default('30d') }}"`. This var is set, has a sensible value, but is **never rendered into `mimir.yaml.j2`** because the template's `compactor:` block doesn't reference it and the var has not yet been wired into the `limits:` block. The net effect: Mimir runs with the built-in default retention (0 = no retention / keep forever) rather than the 30d the operator configured.

**Why it happens:**
The Phase 2 UAT correctly removed the field from the wrong location but did not wire it into the right location. The task was recorded as a config-parse fix ("Mimir refused to start"), not a retention-behavior fix. No one verified that 30d retention was actually being applied post-fix — only that Mimir started successfully.

**Consequences:**
The `mimir-blocks` bucket grows without bound. The compactor runs, compacts blocks, but never deletes them because `compactor_blocks_retention_period` is either 0 (unlimited) or absent from `limits:`. This is silent: Mimir logs nothing unusual; dashboards show data normally; MinIO (and after migration, Garage) silently accumulates blocks forever. The only observable signal is the bucket size metric from MinIO/Garage.

**The correct config (Mimir 3.x):**
```yaml
limits:
  compactor_blocks_retention_period: "{{ mimir_compactor_blocks_retention_period }}"
```
NOT under `compactor:`. The `limits:` placement is the only documented location in the official Grafana Mimir docs. CLI flag: `-compactor.blocks-retention-period`.

**Important: Mimir uses `KnownFields(true)` — unknown fields fail startup.** If `blocks_retention_period` appears under `compactor:` in the rendered YAML, Mimir will refuse to start with a field-not-found error (this is why Phase 2 UAT caught it). If it appears nowhere, Mimir starts normally but retention silently does nothing. Both are bugs; only the second is silent.

**Prevention:**
- Add `limits.compactor_blocks_retention_period: {{ mimir_compactor_blocks_retention_period }}` to `mimir.yaml.j2`
- Keep `mimir_compactor_blocks_retention_period` in defaults/main.yml as-is (already defined correctly)
- After deploy, verify: `mimir_compactor_blocks_deletion_marks_total` metric must be non-zero after one compaction cycle (typically within 2× the block duration, ~4h on homelab ingest rates)
- Ship a "Mimir retention is working" section in the smoke test: check bucket size stabilizes after 30d of data is present

**Phase to address:** First task in v1.1.0. This is existing behavior regression, not a new feature.

---

## Moderate Pitfalls — Tempo Compactor Orphan Var

### Pitfall T-1: `block_ranges_period` is not a field in Tempo 2.x — it was never silently applied

**What goes wrong:**
The current `tempo.yaml.j2` correctly removes `block_ranges_period` with the comment "field does not exist in tempodb.CompactorConfig in Tempo 2.10." The M1 backlog item is to "clean up or re-wire" this orphan. The cleanup is: the field simply does not exist. The closest equivalent in Tempo 2.x is `compaction_window` (the time window for grouping blocks in compaction, default 1h). It is not the same concept as what `block_ranges_period` was in earlier versions.

**Risk of blindly adding `compaction_window`:** Setting `compaction_window` too large (e.g., 24h) means blocks that arrive within that window are compacted together into very large blocks, increasing compaction I/O. On a homelab with low trace volume, the default 1h is fine. Setting it too small (e.g., 5m) causes too many small blocks and excessive compaction cycles.

**What the backlog item actually needs:**
1. Confirm `compaction_window` is intentionally absent (default 1h is fine for homelab Tempo)
2. Delete the var `tempo_block_ranges_period` from `roles/tempo/defaults/main.yml` if it exists there
3. Add `compaction_window` to `roles/tempo/defaults/main.yml` with a comment if the operator wants to tune it (optional)
4. Update the comment in `tempo.yaml.j2` from "Removed: block_ranges_period" to note what the equivalent is

**Silent failure mode:** There is none for this specific item — the field was removed from the template in M1, so Tempo is already running without it. The backlog item is a hygiene/documentation task, not a behavior fix.

**Phase to address:** v1.1.0 backlog sweep. Low-risk, small scope.

---

## Moderate Pitfalls — Fluent Bit Timestamp Fallback

### Pitfall F-1: `@timestamp` key with env-var value in `[FILTER] modify` — two distinct bugs conflated

**What goes wrong:**
The disabled `timestamp_fallback` block in `fluent-bit.conf.j2` has this comment: "DISABLED: Fluent Bit 4.x rejects `Add @timestamp ${ingest_time}` as 'Invalid operation add : @timestamp'. Likely cause: `${ingest_time}` is not a defined env var..." This conflates two separate bugs:

**Bug 1: `${ingest_time}` is not an FB built-in variable.** Fluent Bit's `[FILTER] modify` supports `${ENV_VAR}` substitution for OS environment variables. `ingest_time` is not an environment variable and is never populated by Fluent Bit automatically. This means the substituted value is always empty string, which causes the key to be set to an empty string — not the current time.

**Bug 2: `@` prefix in key names in `[FILTER] modify`.** The `@` character in key names is valid in Fluent Bit's INI-format config (the docs use emoji as evidence of special-character flexibility), but the Modify filter's `Add` operation may reject empty-string values even if the key name is valid. The rejection message "Invalid operation add : @timestamp" is most likely triggered by the empty value (from the failed `${ingest_time}` substitution) rather than the `@` character itself.

**The correct solution for FB 4.2.3:** Use a Lua filter, not Modify, to inject a fallback timestamp:
```lua
function add_timestamp_fallback(tag, timestamp, record)
    if record["time"] == nil or record["time"] == "" then
        record["@timestamp"] = os.date("!%Y-%m-%dT%H:%M:%SZ")
    end
    return 1, timestamp, record
end
```
Lua filters have direct access to the event timestamp (`timestamp`) and can set any key (including `@timestamp`) without the restriction that Modify filter imposes on values derived from undefined env vars.

**What is NOT broken:** Docker logs already include their own timestamp in the JSON log line (`time` field from Docker's json-file driver). The `docker` parser in FB extracts this. The `timestamp_fallback` was defensive code for log sources without embedded timestamps (custom apps, some NFS logs). For the main Docker container tail path, it is rarely triggered.

**Risk of leaving it disabled:** Logs from services that emit no timestamp (or emit unparseable timestamps) will inherit Fluent Bit's "agent start time" as the event time. These arrive in Loki with a stale timestamp; Loki may reject them with "entry too far behind." For the homelab default (all sources are Docker containers with json-file timestamps), this is low-risk. The opt-in NFS tail path is higher risk.

**Phase to address:** v1.1.0 backlog. Replace the disabled Modify block with a Lua `timestamp_fallback` function in `enrich.lua` (already mounted). Do not try to fix the Modify syntax — the Lua path is cleaner and sidesteps both bugs.

---

## Moderate Pitfalls — OTel→Loki Label Mapping

### Pitfall O-1: `service.name` becomes `service_name` in Loki — the spec vs the label allowlist are misaligned

**What goes wrong:**
The Telemetron label spec (established in Phase 3, coded in the FB Lua `enrich.lua` filter) produces a Loki stream label named `service` (from `org.telemetron.service` Docker label). OTel Collector sends logs to Loki via OTLP/HTTP; Loki's OTLP receiver converts the OTel resource attribute `service.name` → `service_name` (dot-to-underscore, documented in Loki 3.x OTLP ingestion docs). The result is that Telemetron has **two different label names for the same concept** depending on the ingest path:

- Docker logs via Fluent Bit → OTel → Loki: stream label is `service` (set by enrich.lua)
- App-instrumented OTLP logs sent directly to OTel Collector → Loki: stream label is `service_name` (set by Loki's OTLP receiver from `service.name` resource attribute)

This means a LogQL query like `{service="my-app"}` misses all OTLP-originated logs; `{service_name="my-app"}` misses all FB-originated logs. Cross-signal correlation in Grafana (trace → logs) is broken for the OTLP ingest path because Tempo's service graph uses `service.name` and the Loki derivedFields `trace_id` lookup assumes the user knows which label to filter on.

**Why it happens:**
Loki's OTLP receiver applies dot-to-underscore transformation to ALL resource attribute names, then maps 17 selected attributes (including `service.name` → `service_name`) to index labels. This happens inside Loki, not the OTel Collector. The OTel Collector's `otlphttp/loki` exporter passes the OTLP payload through verbatim; the transformation is entirely on Loki's side.

**Available resolutions:**
Option A — Accept `service_name` as the canonical label. Rename the FB Lua `service` output to `service_name` in `enrich.lua`. All queries use `service_name`. OTel path and FB path are aligned.
Option B — Override Loki's OTLP default label set. Under `distributor.otlp_config.default_resource_attributes_as_index_labels`, remove `service.name` from the default list, then add a transform that emits it as `service` instead. Requires per-tenant config.
Option C — Transform at OTel Collector. Add a `transform` processor in the OTel logs pipeline that renames `service.name` resource attribute to `service` before sending to Loki. Loki's OTLP receiver will then convert `service` → `service` (no dots, no transformation). Downstream: `{service="my-app"}` works for OTLP-originated logs.

**Recommended for v1.1.0:** Option A — rename `service` to `service_name` in `enrich.lua`. It is the smallest change and aligns Telemetron with the OTel semantic convention. Update Loki derivedFields in the Grafana role to use `service_name`, and update any alert rules that filter on `{service="..."}`.

**Secondary issue: `service.namespace` corruption.** OTel Collector Contrib issue #32497 (open as of 2026-05): when both `service.name` and `service.namespace` are present in a resource, Loki's OTLP receiver generates `service_name = "namespace/service"` (slash-concatenated) instead of just the service name. This produces malformed `service_name` labels that break LogQL equality filters. Mitigation: strip `service.namespace` at the OTel Collector using a `transform` processor before sending to Loki, or ensure instrumented apps do not set `service.namespace`.

**Phase to address:** v1.1.0 backlog sweep. Label rename in `enrich.lua` + update Grafana datasource derivedFields + update any alert rule that references `{service=...}`. Small but touches multiple roles.

---

## Integration Pitfalls Specific to the MinIO→Garage Switch

### Pitfall I-1: Backend roles reference `minio` as DNS hostname — six places to update

**What goes wrong:**
Every backend role's S3 endpoint var defaults to `minio:9000` (or `http://minio:9000` for Loki). This hostname resolves to the MinIO container via Docker bridge DNS using the container alias set in the MinIO role (`aliases: [minio]`). After replacing the MinIO role with a Garage role, the DNS alias changes. If the three backend roles still reference `minio:9000` and the Garage role does not provide a `minio` alias, all three backends fail to connect to object storage on first boot after migration.

**Specific locations in the current codebase:**
- `roles/loki/defaults/main.yml`: `loki_s3_endpoint` → `http://minio:9000`
- `roles/mimir/defaults/main.yml`: `mimir_s3_endpoint` → `minio:9000`
- `roles/tempo/defaults/main.yml` (not read but assumed same pattern): `tempo_s3_endpoint` → `minio:9000`
- `playbooks/deploy_docker.yml`: role ordering references `minio` before `loki`, `tempo`, `mimir`

**Prevention:**
- Use an abstract inventory var `telemetron_s3_host` (default `garage` after migration) that all three backend roles reference. Default it to `garage` in the inventory after migration
- The Garage role's container aliases should include `garage` (matches the new var)
- Do NOT add a `minio` alias to the Garage container — it would paper over the config and prevent detecting broken references

**Detection:**
- Loki/Tempo/Mimir logs immediately show `connection refused` or `DNS lookup failed` against `minio:9000` if the alias wasn't updated

**Phase to address:** Garage role port. Update all three backend role defaults at the same time.

---

### Pitfall I-2: Five buckets must exist before Loki/Tempo/Mimir start — same race as M1, different CLI

**What goes wrong:**
M1's Pitfall 1 (bucket bootstrap race) is fully solved for MinIO: `tasks/bootstrap.yml` uses `minio/mc` to create all 5 buckets and verify they exist before the playbook continues. With Garage, `minio/mc` still works against Garage's S3 API, but the layout must be applied first (Pitfall G-1). Using `mc` against Garage requires an `mc alias set` pointing at `garage:3900`. This adds a dependency: the `mc` bootstrap container (or equivalent) cannot run until after Garage's layout is applied AND its S3 port is ready.

**Risk of re-using the `mc` approach against Garage:** Functional, but `minio/mc` is an archived project. If Telemetron ships Garage as a replacement for archived MinIO, using `minio/mc` for bucket bootstrap sends a mixed signal. Prefer the `garage` CLI or `awscli` for bucket management.

**Better alternative:** Use `awscli` (or `garage bucket create` via `docker_container_exec`) for the Garage bootstrap:
```bash
docker exec telemetron-garage /usr/bin/garage bucket create loki-chunks
docker exec telemetron-garage /usr/bin/garage bucket allow --read --write --owner loki-chunks --key telemetron
```
This can be encoded as `community.docker.docker_container_exec` tasks in Ansible (same pattern as the existing verify tasks in M1 roles).

**Phase to address:** Garage role port, `tasks/bootstrap.yml` rewrite. Highest-priority task within the role.

---

### Pitfall I-3: Rolling the storage backend on a running stack — Loki ingester WAL flush window

**What goes wrong:**
Loki's ingester holds unflushed chunks in memory (WAL) for `max_chunk_age` (default in Telemetron: `loki_max_chunk_age`). When Loki is stopped for the storage migration, any chunks not yet flushed to MinIO are in the WAL at `loki_data_path/wal/`. If the WAL is on a Docker named volume (as it is in Telemetron — one volume covers the full Loki data root), the WAL survives the container stop. When Loki restarts against Garage, it replays the WAL and writes the unflushed chunks to Garage. This is fine as long as the MinIO-side data that WAS flushed is also migrated to Garage. If you skip MinIO→Garage data migration and start Loki fresh against empty Garage buckets, the WAL replay will try to link WAL chunks to index entries that exist in the (now-inaccessible) MinIO store, causing query errors and compaction confusion.

**Safe procedure:**
- If doing a clean-break migration (no data migration): wipe the Loki WAL volume entirely before restarting against Garage. Accept data loss.
- If doing a full migration: stop Loki → rclone sync → start Loki against Garage (WAL replays against migrated data on Garage).

**Phase to address:** Data migration guide in Garage role README. The playbook does not handle this automatically; it must be documented as a manual step.

---

## Minor Pitfalls — Housekeeping

### Pitfall H-1: Garage admin API needs a separate token from the S3 access key

**What goes wrong:**
Garage's admin API (port 3903) uses a Bearer token (`garage_admin_token`), completely separate from the S3 access key/secret pair used by Loki/Tempo/Mimir. The bootstrap automation needs the admin token to run `garage layout assign`, `garage key create`, and `garage bucket create`. The S3 credentials only work against the S3 API (port 3900). Operators who try to authenticate the bootstrap with S3 credentials against port 3903 get 401 Unauthorized and conclude bootstrap is broken.

**Prevention:** Ship two separate secrets in the Garage inventory vars: `garage_admin_token` (used only by the bootstrap task via `docker_container_exec`) and `garage_access_key`/`garage_secret_key` (used by Loki/Tempo/Mimir S3 configs). Never cross-use.

### Pitfall H-2: Volume rename — `telemetron_minio_data` → `telemetron_garage_data`

**What goes wrong:**
If the Garage role reuses the old `telemetron_minio_data` volume name (to "preserve data"), Garage will try to read data in MinIO's on-disk format, which is incompatible with Garage's internal format. MinIO stores object data in its own chunk format with MinIO-specific metadata. Garage cannot read it. The result is either a startup error or silent data corruption as Garage ignores the incompatible files.

**Prevention:** The Garage role must create a **new named volume** (`telemetron_garage_data` or similar). The MinIO volume is left untouched (as a safety net during migration) and can be manually pruned after the migration is confirmed working.

### Pitfall H-3: Mimir retention time format — `m` means minutes not months

**What goes wrong:**
The Mimir docs note that retention periods cannot use `m` to mean "months" — `m` is minutes. A retention of `30d` is correct for 30 days. A naive attempt to set `1m` for "one month" configures 1-minute retention, which causes Mimir to delete almost all blocks on every compaction cycle. Symptoms: Mimir queries return no data; `mimir_compactor_blocks_deletion_marks_total` spikes; bucket empties out quickly.

**Prevention:** Only use `d`, `w`, `y` for retention periods. The current default `30d` is correct.

---

## Pitfall-to-Phase Mapping (v1.1.0)

| Pitfall | Phase | Verification |
|---------|-------|--------------|
| G-1: Garage layout required before S3 works | Garage role port — first task | `garage status` shows node with capacity assigned; S3 ListBuckets succeeds |
| G-2: Endpoint format (http:// vs bare host) | Garage role + backend template updates | Loki/Tempo/Mimir logs show no TLS errors; first PutObject succeeds |
| G-3: No object tagging | Document in Garage role README | — |
| G-4: Garage port matrix | Garage role port + HEALTHCHECK | Port snapshot in docs updated; health poll targets :3903 |
| G-5: Data migration stop-sync-start | Migration guide in Garage role README | Smoke test passes against migrated buckets |
| G-6: Loki `object_store: aws` | Loki template update | Loki `loki_boltdb_shipper_compact` metric increases |
| M-1: Mimir retention not wired to `limits:` | Mimir role template update | `mimir_compactor_blocks_deletion_marks_total` > 0 after compaction cycle |
| T-1: `block_ranges_period` orphan | Tempo role defaults cleanup | Template renders without unknown-field comment; no orphan vars |
| F-1: FB timestamp_fallback — Lua fix | FB role `enrich.lua` update | Docker log arrives in Loki with timestamp within 30s of wall-clock, not agent-start time |
| O-1: `service` vs `service_name` label split | FB enrich.lua + Grafana + alert rules | Single LogQL query `{service_name="my-app"}` returns both FB-originated and OTLP-originated logs |
| I-1: DNS hostname references to `minio` | Garage role + backend role defaults | No "DNS lookup failed for minio" in any backend log after migration |
| I-2: Bucket bootstrap with Garage CLI | Garage role `tasks/bootstrap.yml` | All 5 buckets exist; backends start without NoSuchBucket errors |
| I-3: WAL flush on storage switch | Migration guide | No query errors for recently-flushed chunks after migration |
| H-1: Admin token vs S3 credentials | Garage role secrets discipline | Bootstrap task succeeds; S3 creds never sent to :3903 |
| H-2: Volume rename | Garage role defaults | No attempt to read MinIO data directory with Garage |
| H-3: Mimir `m` = minutes | Mimir retention docs + comment | `mimir_compactor_blocks_retention_period` value validated at deploy time |

---

## Biggest Risk for v1.1.0

**Mimir retention (Pitfall M-1)** is the only silent behavior regression already present in production (v1.0.1). Every day on leviathan, Mimir accumulates blocks it will never delete until this is fixed. Fix it first.

**Garage bootstrap sequence (Pitfall G-1)** is the highest-complexity new pitfall. The layout-assign step has no MinIO analog and the bootstrap task must be written from scratch.

**Label split (Pitfall O-1)** is the highest UX-impact bug — it silently breaks cross-signal correlation for all OTLP-instrumented apps. The fix touches three roles (fluentbit, grafana, possibly alert rules).

---

## Sources

- [Garage S3 Compatibility Matrix](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/) — verified tagging ❌ Missing, path-style ✅, multipart ✅
- [Garage Quick Start documentation](https://garagehq.deuxfleurs.fr/documentation/quick-start/) — verified layout-assign bootstrap sequence
- [bikeshedder/garage-single-node (GitHub)](https://github.com/bikeshedder/garage-single-node) — single-node bootstrap automation via env vars
- [Grafana community: Loki does not ship logs to external S3 storage (Garage)](https://community.grafana.com/t/loki-does-not-ship-logs-to-external-s3-storage-garage/159780) — `object_store: aws` workaround (MEDIUM confidence, thread unresolved)
- [Migrating from MinIO to Garage (Matt Gerega, 2025-12-10)](https://www.mattgerega.com/2025/12/10/migrating-from-minio-to-garage-when-open-source-isnt-so-open-anymore/) — Loki/Tempo/Mimir endpoint-only config update confirmed working in practice
- [Migrating from MinIO to Garage (Sander Sneekes)](https://sneekes.app/posts/migrating-from-minio-to-garage/) — rclone sync approach; RPC stability notes
- [Use Rclone to migrate Minio to Garage](https://exia.dev/blog/2025-12-06/Use-Rclone-to-migrate-Minio-to-Garage/) — `--s3-sign-accept-encoding=false` flag for SignatureDoesNotMatch
- [Configure Grafana Mimir metrics storage retention](https://grafana.com/docs/mimir/latest/configure/configure-metrics-storage-retention/) — `limits.compactor_blocks_retention_period` is the only documented location; HIGH confidence
- [DeepWiki: Mimir configuration](https://deepwiki.com/grafana/mimir/4-configuration) — `KnownFields(true)` strict parsing confirmed; unknown fields fail startup
- [Grafana Tempo configuration reference](https://grafana.com/docs/tempo/latest/configuration/) — `compaction_window` is the current field; `block_ranges_period` does not exist in 2.x schema
- [Ingesting logs to Loki using OpenTelemetry Collector](https://grafana.com/docs/loki/latest/send-data/otel/) — `service.name` → `service_name` dot-to-underscore transformation documented; `default_resource_attributes_as_index_labels` controllable
- [OTel Collector Contrib issue #32497: invalid service_name when service.namespace defined](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/32497) — `service_name = "namespace/service"` corruption confirmed
- [Fluent Bit Modify filter documentation](https://docs.fluentbit.io/manual/data-pipeline/filters/modify) — no restriction on `@` prefix keys; empty-value `Add` is the rejection trigger
- [Tempo issue #431: S3ForcePathStyle](https://github.com/grafana/tempo/issues/431) — `forcepathstyle` key confirmed for Tempo S3 config
- [Loki issue #823: s3forcepathstyle field](https://github.com/grafana/loki/issues/823) — `s3forcepathstyle` key confirmed for Loki S3 config
- Telemetron codebase (verified against live files):
  - `roles/mimir/templates/mimir.yaml.j2` — retention field removed but not re-wired
  - `roles/mimir/defaults/main.yml` — `mimir_compactor_blocks_retention_period` defined but unused
  - `roles/tempo/templates/tempo.yaml.j2` — `block_ranges_period` removed, `compaction_window` absent
  - `roles/fluentbit/templates/fluent-bit.conf.j2` — `timestamp_fallback` block disabled
  - `roles/opentelemetry/templates/config.yaml.j2` — `otlphttp/loki` exporter passes OTLP verbatim
  - `roles/minio/tasks/bootstrap.yml` — bootstrap pattern to replicate for Garage

---
*v1.1.0 pitfalls supplement. Covers Garage migration + backlog config items only. For M1 pitfalls (cardinality, Grafana UID provisioning, OTel pipeline order, Ansible idempotency, etc.), see the 2026-05-17 base PITFALLS.md.*
