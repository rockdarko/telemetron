# Feature Landscape

**Domain:** Self-hosted observability stack (Ansible-deployed), homelab + small-deployment ops
**Researched:** 2026-05-17 (M1) / 2026-05-26 (v1.1.0 addendum)
**Confidence:** HIGH (Grafana ecosystem, Mimir/Tempo config), MEDIUM (Garage operator experience, FB timestamp fix)

---

## v1.1.0 Feature Research (primary focus for this pass)

This section covers the four features targeted in v1.1.0: Garage object store, Mimir retention fix,
Fluent Bit timestamp fallback fix, and Fluent Bit/OTel label reconciliation.

---

### Feature 1: Garage as Object Store

**What operators expect when MinIO is replaced with Garage**

#### What Garage actually is

Garage is an S3-compatible distributed object store maintained by Deuxfleurs (a French non-profit),
AGPL licensed, actively developed, designed explicitly for small/homelab/geo-distributed deployments.
Latest stable: `v2.3.0` (April 16, 2026, Forge Deuxfleurs). Docker image: `dxflrs/garage:v2.3.0`.
Image size ~26–27 MB compressed (vs. MinIO which ships a heavier binary).

v2.0 broke the admin API vs v1.x — the v2 admin API is not backward compatible with v1.x tooling.
v2.3.0 specifically added `--single-node` + `--default-bucket` auto-configuration flags, making
initial setup significantly easier.

#### Operator-facing setup flow (what they must do, not optional)

Unlike MinIO which starts accepting writes immediately, **Garage requires a mandatory cluster layout
initialization step** before it accepts any writes.

The required sequence after container start:

```
1. docker exec garage /garage status              # get node ID
2. docker exec garage /garage layout assign -z dc1 -c 1G <NODE_ID>
3. docker exec garage /garage layout apply --version 1
4. docker exec garage /garage bucket create loki-chunks
5. docker exec garage /garage key create telemetron-key
6. docker exec garage /garage bucket allow --read --write --owner loki-chunks --key telemetron-key
# (repeat bucket create + allow for all 5 buckets)
```

This is a fundamentally different bootstrap model from MinIO's `mc mb --ignore-existing`.
The Ansible role bootstrap task must replicate all of this; it cannot use a simple one-shot mc
container the way the minio role does.

#### Ports (different from MinIO)

| Port | Purpose | MinIO equivalent |
|------|---------|-----------------|
| 3900 | S3 API | 9000 |
| 3901 | RPC (internal, node-to-node) | N/A (MinIO doesn't expose this) |
| 3902 | S3 web hosting (static sites) | N/A |
| 3903 | Admin API | N/A |

All consumer roles (Loki/Tempo/Mimir) must have their S3 endpoint updated from
`minio:9000` to `garage:3900`.

#### Admin UI: what operators see

Garage itself has NO built-in web UI. Administration is CLI-only via the `garage` binary inside
the container. There is a community project `khairul169/garage-webui` (Docker:
`khairul169/garage-webui`, port 3909) that provides a GUI for bucket browsing, key management,
and object exploration. It requires Garage v2.0.0+ and the admin API enabled.

Comparison with what operators had in MinIO:
- MinIO Console (`:9001`) was a full-featured S3 browser, IAM manager, lifecycle policy UI
- Garage CLI provides: `bucket create`, `bucket list`, `key create`, `key list`, `bucket allow`
- Garage Admin API (`/metrics`, `/health`, `/v2/GetClusterHealth`) is Prometheus-scrapeable
- `garage-webui` provides bucket browsing and object listing — less capable than MinIO Console

**Operator experience gap:** MinIO Console was operator-friendly out of the box. Garage requires
either CLI fluency or deploying the separate `garage-webui` sidecar. For the Telemetron homelab
audience, this is a regression in discoverability. The `garage-webui` sidecar should be considered
as a default-on optional component of the `garage` role.

#### Monitoring

Garage exposes Prometheus metrics at `http://garage:3903/metrics` (admin API port, requires
`metrics_token` auth). This is a different pattern from MinIO's self-metrics (MinIO exposes
at `:9000/minio/v2/metrics/cluster`). OTel Collector or Prometheus must be reconfigured to
scrape the new endpoint and token.

#### Configuration shape (garage.toml)

```toml
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "sqlite"          # recommended for single-node
replication_factor = 1        # single-node: no redundancy (explicit tradeoff)
rpc_public_addr = "127.0.0.1:3901"

[s3_api]
s3_region = "garage"          # CRITICAL: rclone and S3 clients must use this exact region string
api_bind_addr = "0.0.0.0:3900"

[admin]
api_bind_addr = "0.0.0.0:3903"
admin_token = "<generated secret>"
metrics_token = "<generated secret>"
```

**Critical gotcha:** rclone (used for data migration) requires `region = garage` in its config.
Without it, rclone defaults to `us-east-1` and Garage rejects with `AuthorizationHeaderMalformed`.
The same applies to Loki/Mimir/Tempo S3 config — the region string must match what Garage expects.

#### Data migration path (MinIO → Garage)

The standard migration tool is rclone. The procedure:

1. Start Garage alongside MinIO on the same host (different ports; Garage on 3900)
2. Create matching buckets in Garage and generate access keys
3. Per bucket: `rclone sync minio:<bucket> garage:<bucket> --progress --transfers 8`
4. Stop applications (Loki/Tempo/Mimir)
5. Run a final incremental sync to catch late writes
6. Reconfigure backend roles to point at garage:3900 with Garage credentials
7. Restart backends

For Telemetron's homelab use case (low volume), existing data migration is optional — operators
with fresh installs can simply create empty Garage buckets (data in MinIO is lost, acceptable if
retention windows have not been exhausted). A migration guide should be shipped as
`docs/storage-migration.md`.

#### Table Stakes vs Differentiators for Garage

**Table stakes (Garage must provide these; it does):**
| Capability | Status | Notes |
|-----------|--------|-------|
| S3 API compatibility (Loki/Mimir/Tempo connect) | YES | All three work; region string must be set |
| Bucket create/list/allow via CLI | YES | `garage bucket create`, `garage key create` |
| Health endpoint for Ansible polling | YES | `GET /health` on admin port 3903 |
| Prometheus metrics endpoint | YES | `GET /metrics` on admin port 3903 |
| Actively maintained, security patches | YES | v2.3.0 released April 2026 |
| Single-node (no replication) mode | YES | `replication_factor = 1` |
| Idempotent bucket creation (no error if exists) | PARTIAL | CLI returns error if bucket exists; must check first |

**Differentiators (Garage does better than archived MinIO):**
| Capability | Notes |
|-----------|-------|
| Active maintenance with security patches | MinIO community archived; Garage is the point |
| Designed for homelab geo-distribution | Can grow to multi-node without replacing the tool |
| AGPL, non-commercial | No "we archived the community version" risk |
| Tiny image (~26 MB) | MinIO was heavier |

**Gaps vs MinIO (operator experience regressions):**
| Capability | MinIO had it | Garage |
|-----------|-------------|--------|
| Built-in web console | Yes (`:9001`) | No — requires `garage-webui` sidecar |
| IAM/per-bucket user policies | Rich policy model | Only key+bucket allow/deny |
| Lifecycle policies (auto-expire objects) | Yes | Not present — retention enforced by Loki/Mimir/Tempo compactors only |
| `mc` CLI (familiar from MinIO docs) | Yes | No — `garage` CLI is different UX |

**Anti-features to avoid:**
- Deploying Garage in `replication_factor = 3` on a single host (wastes disk, no benefit)
- Using `dxflrs/garage:latest` (floating tag — pin to `v2.3.0`)
- Setting region to anything other than `garage` in Loki/Mimir/Tempo S3 config without matching
  Garage's configured `s3_region` value

#### Dependencies on existing stack

- **Loki role:** S3 endpoint (`minio:9000` → `garage:3900`), region, access key/secret key vars must change
- **Mimir role:** Same S3 endpoint + credential change for all three buckets (blocks, ruler, alerts)
- **Tempo role:** Same S3 endpoint + credential change
- **OTel Collector/Prometheus:** Scrape config for Garage self-metrics changes endpoint + adds token auth
- **`minio` role:** Replaced by `garage` role; playbook ordering changes (`garage` takes `minio`'s slot)
- **Secrets:** New vars for Garage admin token, metrics token, access key ID, secret access key

#### Complexity assessment

**HIGH** — This is not a config variable change. It is:
- A new Ansible role replacing the existing `minio` role
- A fundamentally different bootstrap model (layout assign/apply before any write)
- New port map across all consumers
- New secrets surface (admin token, metrics token separate from S3 credentials)
- A migration doc for existing deployments
- Optional sidecar (`garage-webui`) for operator usability

The single hardest part is the bootstrap task: the `minio` role bootstrapped buckets by running a
one-shot `mc` container. Garage requires: (a) the container to be healthy, (b) layout to be
initialized (a two-step CLI operation), (c) buckets created, (d) keys created, (e) keys authorized
on each bucket. This is more orchestration than the `mc mb` one-liner.

---

### Feature 2: Mimir Retention Fix

**What operators expect vs what currently happens**

#### The bug (confirmed from codebase inspection)

`roles/mimir/defaults/main.yml` defines:
```yaml
mimir_compactor_blocks_retention_period: "{{ telemetron_default_metric_retention | default('30d') }}"
```

`roles/mimir/templates/mimir.yaml.j2` has this comment in the `compactor:` block:
```yaml
# Removed: blocks_retention_period -- field is not on compactor.Config in
# Mimir 3.0. The setting moved to per-tenant `limits:`. Default retention
# is 1 week, fine for M1.
```

And the `limits:` block in the template has only:
```yaml
limits:
  max_global_series_per_user: ...
  max_global_series_per_metric: ...
```

**The variable is declared but never used in the template.** The operator sets 30d retention in
inventory, runs the playbook, and gets Mimir's built-in default (which per Grafana docs is
"never delete" — not 1 week as the comment incorrectly states). The retention comment is doubly
wrong: the upstream default is unlimited retention, not 1 week.

#### What the correct configuration looks like

Per Grafana Mimir docs (HIGH confidence — official docs verified):

The retention setting belongs under `limits:` in the Mimir config YAML, not under `compactor:`:

```yaml
limits:
  compactor_blocks_retention_period: 30d   # this is the correct path
  max_global_series_per_user: ...
  max_global_series_per_metric: ...
```

There is no `compactor.blocks_retention_period` field in Mimir 3.x YAML — only
`limits.compactor_blocks_retention_period`. The compactor reads this from the limits layer, which
is why putting it under `compactor:` was silently ignored (Mimir would reject unknown fields in
newer versions or silently ignore them in others — Phase 2 UAT caught this and removed it, but
forgot to re-add it under `limits:`).

#### Operator experience when correctly configured

- Operator sets `telemetron_default_metric_retention: 30d` in `group_vars/all/telemetron.yml`
- Mimir config renders with `limits.compactor_blocks_retention_period: 30d`
- Compactor periodically deletes blocks older than 30d from the Mimir S3 bucket
- Operator can verify: Mimir exposes `cortex_compactor_blocks_cleaned_total` and
  `cortex_bucket_blocks_count` metrics scrapeable from `:9009/metrics`
- There is no UI — verification is metric-based or by checking bucket object count

#### Operator experience when broken (current state)

- Operator sets 30d retention and observes no block deletion
- S3 bucket (MinIO/Garage) grows without bound
- No error is surfaced — Mimir simply never enforces retention

#### Complexity assessment

**LOW** — One-line template fix: add `compactor_blocks_retention_period: {{ mimir_compactor_blocks_retention_period }}` to the `limits:` block in `mimir.yaml.j2`. The variable already exists in defaults. The fix is safe to ship without data loss risk (it starts enforcing retention going forward; blocks already stored are only deleted after the configured period elapses).

#### Table stakes

Operators who configure retention expect it to take effect. Silent non-enforcement is a critical
correctness bug, not a missing feature. This is firmly table stakes.

---

### Feature 3: Fluent Bit Timestamp Fallback

**What operators expect vs what currently happens**

#### The bug (confirmed from codebase inspection)

`roles/fluentbit/templates/fluent-bit.conf.j2` has this block commented out:

```
# DISABLED: Fluent Bit 4.x rejects `Add @timestamp ${ingest_time}` as
# "Invalid operation add : @timestamp". Likely cause: `${ingest_time}` is
# not a defined env var so the substitution leaves the value empty, AND/OR
# keys beginning with `@` need quoting in FB 4. Docker logs already include
# their own timestamp so this fallback is for edge cases only.
```

The intended behavior was: for log records that arrive without a timestamp (edge case for Docker
JSON logs, more likely for system logs via D-48 extension knobs), add a field `@timestamp` with
the ingest time so the record has a usable timestamp in Loki.

#### Why `${ingest_time}` doesn't work

`${ingest_time}` is not a Fluent Bit built-in environment variable. It was never a valid
variable reference in the modify filter. The modify filter's `Add` operation supports:
- Static literal values: `Add myfield staticvalue`
- Environment variable substitution via `${ENV_VAR_NAME}` — but only for variables that
  actually exist in the environment at runtime

`ingest_time` is not set in the Fluent Bit container's environment, so `${ingest_time}` expands
to empty string. Additionally, keys starting with `@` require quoting in Fluent Bit 4.x YAML
mode (less relevant here since the role uses classic INI config, but the `@timestamp` key name
is non-standard for the modify filter).

#### The correct approach (Lua filter)

The Lua filter can read the record's ingestion timestamp (which Fluent Bit always assigns from
system clock when no source timestamp is found) and write it to a record field:

```lua
function add_timestamp(tag, timestamp, record)
    -- timestamp is a float: seconds since epoch
    -- write it as ISO 8601 string to @timestamp field
    record["@timestamp"] = os.date("!%Y-%m-%dT%H:%M:%SZ", math.floor(timestamp))
    return 2, timestamp, record  -- return code 2: record modified, timestamp unchanged
end
```

The corresponding filter config:
```
[FILTER]
    Name    lua
    Match   *
    script  /fluent-bit/etc/timestamp_fallback.lua
    call    add_timestamp
```

Since the `enrich.lua` file already exists and is bind-mounted, the timestamp fallback function
can be added to `enrich.lua` itself (if the call pattern allows), or a second Lua file can be
shipped alongside it.

An alternative that doesn't require Lua: use the modify filter's `Set` operation with a hard-coded
value placeholder — but this cannot produce dynamic timestamps. Lua is the only correct path.

#### Operator experience when correctly configured

For Docker container logs (the default input): Docker JSON log records always include a `time`
field that FB's `docker` parser picks up as the record timestamp. The fallback is never triggered
for the happy-path use case. The fallback matters only when:
1. `fluentbit_tail_system_logs: true` (syslog/auth.log without a parsed timestamp)
2. `fluentbit_extra_tail_paths` pointing at app logs without a standard timestamp format
3. A container produces logs without the Docker JSON wrapper (unusual, but possible with
   `--log-driver=none` or custom loggers)

Correct behavior: records that would otherwise arrive in Loki with timestamp `1970-01-01T00:00:00Z`
(the Unix epoch, Loki's zero-timestamp) instead arrive with the ingest time as timestamp.

#### Complexity assessment

**LOW-MEDIUM** — The fix requires:
- Adding a timestamp function to the existing `enrich.lua` (or shipping a new `timestamp_fallback.lua`)
- Wiring the Lua filter call in `fluent-bit.conf.j2`
- Re-enabling the filter block (currently commented out with a different approach)

The tricky part is that `enrich.lua` is already doing per-container Docker label enrichment.
Adding timestamp fallback to the same Lua callback or adding a second callback in the same file
is technically straightforward but requires care about return codes (code 1 = modify timestamp
too, code 2 = modify record only). For timestamp fallback specifically, code 2 is correct (don't
override the source timestamp if FB already detected one; only add the `@timestamp` field to the
record metadata).

#### Table stakes

Timestamp correctness is table stakes for a log shipping solution. The current state (fallback
disabled, no substitute) is acceptable only because Docker logs have native timestamps. As soon
as operators enable `fluentbit_tail_system_logs` or `fluentbit_extra_tail_paths`, they hit the
zero-timestamp problem. The fix belongs in v1.1.0 to prevent silent data quality issues.

---

### Feature 4: Fluent Bit / OTel Label Naming Reconciliation

**What operators see in Loki and why it matters**

#### The divergence (confirmed from codebase inspection and Loki OTLP docs)

Telemetron's Fluent Bit label allowlist (D-47 in the existing role) defines these labels:
```
service    (from org.telemetron.service Docker label)
job        (from org.telemetron.job Docker label)
host       (static: ansible_hostname)
env        (static: telemetron_env)
level      (extracted from log line)
```

When Loki receives logs via OTLP (the default path: FB → OTel Collector → Loki via OTLP/HTTP),
the OTel semantic conventions apply. Per Loki's OTLP ingestion documentation (HIGH confidence —
Grafana official docs):

**OTel resource attributes use dot notation. Loki converts dots to underscores for index labels.**

So `service.name` (OTel attribute) becomes `service_name` (Loki label). The Fluent Bit Lua
enrichment sets `service` (no dot, no underscore suffix) in the record as a log field — not as
an OTel resource attribute.

The OTel Collector receives logs from Fluent Bit via OTLP/HTTP. At this point, the Fluent Bit
labels (`service`, `job`, `host`, `env`, `level`) are carried as log record attributes (not
resource attributes). Loki's OTLP ingestion path promotes resource attributes to index labels
by default; log record attributes become structured metadata.

#### What operators actually see in Loki (current state)

When querying logs in Grafana Explore (Loki datasource):
- Label `service_name` appears (from OTel's default resource attribute if any instrumented service
  sets `service.name`) — this is from OTLP-instrumented apps, not from Fluent Bit
- Labels from Fluent Bit (`service`, `job`, `host`, `env`, `level`) may appear as structured
  metadata or not at all as queryable index labels, depending on how the OTel Collector promotes them

The disconnect: the FB label spec says `service`, but OTel-aware operators writing LogQL queries
expect `service_name` (the OTel convention). This creates query divergence:
- `{service="telemetron"}` — works for FB-sourced logs (if FB labels make it to index)
- `{service_name="telemetron"}` — works for OTLP-instrumented app logs
- Neither query works for both, unless labels are explicitly reconciled

#### The three valid approaches and their operator experience

**Option A: Accept OTel convention — rename `service` → `service_name` in FB config**

FB label changes to emit `service_name` instead of `service`. All Loki queries use `service_name`.
Consistent with OTel-instrumented apps. Requires updating the Lua enrichment and the label
allowlist filter. Operators write `{service_name="myapp"}` for all log sources.

*Operator experience:* Clean, consistent with OTel ecosystem docs. The Grafana Loki Explore
panel's label autocomplete shows `service_name` for everything. Grafana 13's Explore Logs
feature expects `service_name` as a default label for service-level log browsing.

**Option B: Relabel at OTel Collector — rename `service` to `service_name` in the pipeline**

OTel Collector's `transform` processor or `attributes` processor renames the log record attribute
`service` to `service_name` before forwarding to Loki. FB config unchanged. Fragile: depends on
the attribute being in the right place (record vs resource attributes).

*Operator experience:* Invisible to the operator if it works, confusing to debug if it doesn't.
Adds config complexity to the OTel Collector.

**Option C: Overwrite at Loki — use `otlp_config` to promote `service` as an index label**

Loki's `limits_config.otlp_config` can specify that `service` is stored as an index label.
Requires Loki config change. Operators query `{service="myapp"}`.

*Operator experience:* Keeps the FB label spec unchanged but deviates from OTel defaults.
Operators migrating from OTel docs will expect `service_name`.

#### Recommended approach for Telemetron

**Option A** (rename in FB) is the correct long-term choice because:
- Grafana's Explore Logs feature treats `service_name` as a first-class concept for log browsing
- OTel-instrumented applications (the intended primary signal path) already emit `service_name`
- A user following any OTLP instrumentation guide will discover `service_name` naturally
- Keeping `service` as the FB label creates a permanent two-tier query experience

The rename is a breaking change for any existing Loki dashboards or alerts that query `{service=...}`.
For Telemetron v1.1.0 (still pre-1.0 community traction), this is the right time to break
compatibility in the correct direction.

#### Complexity assessment

**LOW** — The rename requires:
1. Update `enrich.lua` to set `record["service_name"]` instead of `record["service"]`
2. Update the modify filter in `fluent-bit.conf.j2` to use `service_name` in the allowlist
3. Update the label allowlist doc table in `roles/fluentbit/README.md`
4. Update any Grafana dashboard JSON files that query `{service=...}` — the curated dashboards
   may need a sweep (check all 7 dashboard files for `service` label references)
5. Update `docs/architecture.md` and `docs/quickstart.md` label references

The code change is small. The coordination cost (README, docs, dashboards) is the larger effort.

#### Table stakes

Consistent queryable label names are table stakes for an observability stack. Having two different
label names (`service` vs `service_name`) for the same concept depending on whether the log came
from Fluent Bit or an OTLP-instrumented app is a correctness failure. Users will file issues.

---

### Feature 5: Tempo compactor orphan variable cleanup

**What currently exists (confirmed from codebase inspection)**

`roles/tempo/defaults/main.yml` defines:
```yaml
tempo_compactor_block_ranges_period: 5m
```

`roles/tempo/templates/tempo.yaml.j2` has:
```yaml
# Removed: block_ranges_period -- the field does not exist in
# tempodb.CompactorConfig in Tempo 2.10. Caught Phase 2 UAT 2026-05-18
```

The variable is defined but never used. Per Grafana Tempo docs (HIGH confidence — official docs),
the correct compactor parameter for grouping blocks into compaction windows is `compaction_window`
under `compactor.compaction`, not `block_ranges_period`.

**Correct config shape:**
```yaml
compactor:
  compaction:
    block_retention: {{ tempo_block_retention }}
    compacted_block_retention: {{ tempo_compacted_block_retention }}
    compaction_window: {{ tempo_compactor_compaction_window | default('1h') }}
```

This is a dead variable cleanup + optional wire-in of the correct knob. The current retention
settings (`block_retention`, `compacted_block_retention`) are correctly placed and functioning.
The orphan is cosmetic pollution but should be cleaned to avoid confusing future operators who
see a variable that does nothing.

#### Complexity assessment

**LOW** — Either: (a) delete `tempo_compactor_block_ranges_period` from defaults and add a comment
explaining why it was removed, or (b) rename to `tempo_compactor_compaction_window`, wire it
into the template under `compactor.compaction.compaction_window`, and drop the orphan.

Option (b) is better — it turns dead code into functional config.

---

## v1.1.0 Feature Summary Table

| Feature | Category | Complexity | Breaking | Operator Impact |
|---------|----------|------------|----------|-----------------|
| Garage as object store | New feature (replaces minio role) | HIGH | YES — new role, new ports, new secrets | Security fix (no more archived MinIO) |
| Garage bucket bootstrap via CLI | Table stakes | HIGH (included in above) | — | Required for stack boot |
| Garage admin UI (garage-webui) | Differentiator | LOW (optional sidecar) | No | Restores MinIO Console–equivalent UX |
| Mimir retention fix | Bug fix | LOW | No | Retention actually enforced after fix |
| FB timestamp fallback (Lua) | Bug fix | LOW-MEDIUM | No | Log quality for non-Docker inputs |
| FB label rename (service → service_name) | Config fix | LOW | YES — existing LogQL queries | OTel ecosystem consistency |
| Tempo orphan var cleanup | Cleanup | LOW | No | Code hygiene |

---

## Feature Dependencies (v1.1.0)

```
[Garage role]
    └──requires──> [garage.toml template + rendered config]
    └──requires──> [Layout initialization bootstrap task]
                       └──requires──> [container healthy + CLI reachable]
    └──requires──> [Bucket create + key create + allow tasks per bucket]
    └──breaks──>   [minio role] (replaced; must be removed from play order)
    └──feeds──>    [Loki/Mimir/Tempo S3 config vars changed]

[Loki/Mimir/Tempo S3 retargeting]
    └──requires──> [Garage role ships first in playbook]
    └──requires──> [New S3 vars: endpoint=garage:3900, region=garage, new credentials]
    └──requires──> [Data migration doc if operator has existing MinIO data]

[Mimir retention fix]
    └──requires──> [Template: add limits.compactor_blocks_retention_period]
    └──independent of Garage migration] (can be applied against MinIO too)

[FB label rename: service → service_name]
    └──requires──> [enrich.lua update]
    └──requires──> [fluent-bit.conf.j2 allowlist filter update]
    └──requires──> [Dashboard JSON sweep: {service=...} → {service_name=...}]
    └──requires──> [Docs update: README, architecture.md, quickstart.md]

[FB timestamp fallback]
    └──requires──> [New Lua function (can be in enrich.lua or separate file)]
    └──requires──> [fluent-bit.conf.j2: new [FILTER] lua block replacing commented-out modify block]
    └──independent of label rename] (can be applied separately)

[Tempo orphan var cleanup]
    └──standalone] (no dependencies; optional wire-in of compaction_window)
```

---

## Anti-Features for v1.1.0

| Avoid | Why |
|-------|-----|
| Garage `replication_factor = 3` on single host | Wastes disk, no redundancy benefit without separate physical nodes |
| Keeping both `minio` and `garage` roles active simultaneously | Doubles the storage footprint, confuses consumers (which endpoint is canonical?) |
| Floating `dxflrs/garage:latest` tag | Garage releases regularly; pin to `v2.3.0` |
| Garage S3 region ≠ `garage` in consumer configs | Auth errors at runtime; hard to diagnose |
| Adding MinIO lifecycle policies as a workaround | Mimir/Loki/Tempo's compactors handle object deletion; MinIO lifecycle policies are redundant and can cause premature deletion |
| Renaming FB label to `service_name` but keeping old dashboards with `{service=...}` | Split-brain queries; worse than either consistent state |

---

## Sources

### Garage (HIGH confidence — official sources)
- [Garage releases — Forge Deuxfleurs](https://git.deuxfleurs.fr/Deuxfleurs/garage/releases) — v2.3.0 verified April 16, 2026
- [Garage quick start](https://garagehq.deuxfleurs.fr/documentation/quick-start/) — layout init workflow verified
- [Garage admin API — monitoring endpoints](https://garagehq.deuxfleurs.fr/documentation/reference-manual/admin-api/) — /metrics, /health, no web UI confirmed
- [dxflrs/garage Docker Hub](https://hub.docker.com/r/dxflrs/garage/tags) — v2.3.0 confirmed

### Garage operator experience (MEDIUM confidence — practitioner sources)
- [MinIO to Garage migration — Cloud Rumble](https://cloudrumble.net/blog/2025/12/22/minio-to-garage-migration/) — rclone workflow, region gotcha
- [Migrating from MinIO to Garage — sneekes.app](https://sneekes.app/posts/migrating-from-minio-to-garage/) — S3 compatibility confirmed, rclone sync procedure
- [Garage Docker compose example — portalZINE.DE](https://portalzine.de/day-38-garage-object-storage-the-self-hosted-s3-alternative-7-days-of-docker/) — full Docker compose + init sequence
- [khairul169/garage-webui GitHub](https://github.com/khairul169/garage-webui) — web UI requires Garage 2.0+, port 3909

### Mimir retention (HIGH confidence — official docs)
- [Configure Grafana Mimir retention — Grafana docs](https://grafana.com/docs/mimir/latest/configure/configure-metrics-storage-retention/) — limits.compactor_blocks_retention_period verified as correct YAML path
- [Mimir blocks retention discussion #3242 — GitHub](https://github.com/grafana/mimir/discussions/3242) — blocks_retention_period confirmed as a limits-layer setting

### Fluent Bit timestamp (MEDIUM confidence — docs + issue tracker)
- [Fluent Bit Lua filter docs](https://docs.fluentbit.io/manual/data-pipeline/filters/lua) — return codes 1/2 verified
- [Fluent Bit modify filter — copy timestamp issue #7054](https://github.com/fluent/fluent-bit/issues/7054) — modify filter cannot copy timestamps; Lua filter is the workaround
- [Fluent Bit modify filter docs](https://docs.fluentbit.io/manual/data-pipeline/filters/modify) — ${ingest_time} not documented as a variable

### OTel/Loki label naming (HIGH confidence — official docs)
- [Grafana Loki OTel ingestion docs](https://grafana.com/docs/loki/latest/send-data/otel/) — dots-to-underscores conversion confirmed; service.name → service_name verified
- [OTel Collector loki exporter issue #32497](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/32497) — service_name label generation from service.name + service.namespace confirmed

### Tempo compactor (HIGH confidence — official docs)
- [Grafana Tempo configuration reference](https://grafana.com/docs/tempo/latest/configuration/) — block_ranges_period not a valid field; compaction_window is the correct knob under compactor.compaction

---

## M1 Feature Landscape (carried forward, reference only)

The M1 feature landscape (table stakes, differentiators, anti-features for the original
port) is preserved in git history. Key decisions still relevant to v1.1.0:

- **MinIO bundled for S3-compatible storage** was listed as a differentiator in M1 with the
  note "M1 role exists. Differentiator is *defaults*: bucket pre-created, credentials in vault."
  The v1.1.0 Garage migration preserves this differentiator with a better underlying component.
- **Retention controls exposed as variables** was listed as a table-stakes feature with the
  note "Surface as group_vars. Planned docs/mimir-retention.md confirms intent." The Mimir
  retention fix completes this — the variable existed but was not wired.
- **PromLens** row in the competitor table is now moot (removed v1.0.1).
