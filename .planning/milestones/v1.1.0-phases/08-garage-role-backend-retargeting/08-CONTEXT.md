# Phase 8: Garage Role + Backend Retargeting - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace MinIO (archived community release) with Garage v2.3.0 as the S3-compatible object store. Build `roles/garage/` from scratch, retarget Loki/Tempo/Mimir S3 configs from `minio:9000` to `garage:3900`, remove `roles/minio/` and all MinIO-specific vars, and wire Garage self-metrics into Prometheus so storage health appears in Grafana.

</domain>

<decisions>
## Implementation Decisions

### Credential surface
- **D-110:** Garage admin token variable is `garage_admin_token`. Follows the no-decorative-prefix rule (D-90). Maps directly to the `GARAGE_ADMIN_TOKEN` env var that Garage reads at startup. Lives in `secrets.yml.example` as a CHANGE_ME placeholder.
- **D-111:** Single shared S3 API key for all three backends (Loki/Tempo/Mimir). Bootstrap creates ONE Garage key; per-backend keys deferred (same stance as D-27). Key vars: `garage_s3_access_key_id` and `garage_s3_secret_key`.
- **D-112:** Bootstrap generates the S3 key via `/garage key create` on first run. The key ID and secret are persisted to a host file (e.g., `/opt/telemetron/garage/s3-credentials`) so re-runs can read the existing key instead of regenerating. If the file already exists, bootstrap skips key creation and loads the persisted values.
- **D-113:** Per-backend S3 vars alias directly to Garage vars: `loki_s3_access_key` defaults to `{{ garage_s3_access_key_id }}`, etc. Same D-27 pattern with `garage_*` as the alias target instead of `minio_root_*`.

### Metrics scrape
- **D-114:** Garage metrics scraped by a 4th hardcoded Prometheus scrape job (alongside `otel_self`, `otel_metrics`, `node_exporter`). Always on, no toggle. Targets `garage:3903/metrics`.
- **D-115:** Bearer token (`garage_admin_token`) embedded inline in the rendered `prometheus.yml.j2` via `authorization.credentials`. No separate token file.
- **D-116:** No opt-out toggle for the Garage scrape job. Consistent with the existing three default jobs being unconditional.

### Backend verify migration
- **D-117:** Loki and Mimir S3 object verification migrated from `minio/mc` one-shot containers to `docker_container_exec` against the running Garage container, using `/garage bucket info <bucket>` with the admin token. Follows the Phase 4 canonical verify pattern.
- **D-118:** Tempo gets a new S3 bucket verify step (Loki and Mimir already had one; Tempo didn't). All three backends now have consistent Garage-backed bucket verification.

### Storage var naming
- **D-119:** Bucket list variable renamed from `telemetron_minio_buckets` to `telemetron_garage_buckets` in `inventory/example-homelab/group_vars/all/storage.yml`. Specific to Garage, not generic.
- **D-120:** Inventory file `group_vars/all/minio.yml` renamed to `group_vars/all/garage.yml`. Holds Garage-specific operator knobs (container name, publish host, ports).

### Claude's Discretion
- D-117 verify tool choice (docker_container_exec against Garage) was Claude's recommendation accepted via "You decide." Rationale: follows Phase 4 canonical pattern, uses already-available admin token, avoids fragile SigV4 curl signing, preserves per-role S3 assertion value.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Garage role (new)
- `roles/minio/tasks/main.yml` — Template for the replacement role's task structure (config dir, env render, volume, pull, container, bootstrap)
- `roles/minio/tasks/bootstrap.yml` — HEALTHCHECK poll → one-shot CLI → verify pattern to adapt for Garage's multi-step bootstrap (layout assign, layout apply, key create, bucket create, key allow)
- `roles/minio/defaults/main.yml` — Full MinIO default surface to translate to Garage equivalents
- `roles/minio/templates/minio.env.j2` — Env file template pattern (Garage uses TOML config + env overrides)

### Backend S3 retargeting
- `roles/loki/defaults/main.yml` — S3 endpoint default `http://minio:9000` → `http://garage:3900` (Loki uses http:// prefix)
- `roles/tempo/defaults/main.yml` — S3 endpoint default `minio:9000` → `garage:3900` (Tempo: no scheme prefix)
- `roles/mimir/defaults/main.yml` — S3 endpoint default `minio:9000` → `garage:3900` (Mimir: no scheme prefix); also `mimir_mc_image` var to remove
- `roles/loki/templates/loki.yaml.j2` — S3 config block (lines 50-62); Loki uses `object_store: aws` (defensive, not `s3`)
- `roles/tempo/templates/tempo.yaml.j2` — S3 config block (lines 35-43); key naming: `forcepathstyle` (single word)
- `roles/mimir/templates/mimir.yaml.j2` — S3 config block (lines 25-57); three distinct buckets (D-39/BACK-04/Pitfall G)

### Verify task migration
- `roles/loki/tasks/verify.yml` — Lines 63-80: mc-based S3 object check to replace with docker_container_exec
- `roles/mimir/tasks/verify.yml` — Lines 107-116: mc-based S3 object check to replace with docker_container_exec
- `roles/tempo/tasks/verify.yml` — No existing S3 check; D-118 adds one for consistency

### Metrics scrape
- `roles/prometheus/templates/prometheus.yml.j2` — Add 4th hardcoded scrape job targeting `garage:3903/metrics` with bearer auth

### Inventory and docs
- `inventory/example-homelab/group_vars/all/storage.yml` — `telemetron_minio_buckets` → `telemetron_garage_buckets`
- `inventory/example-homelab/group_vars/all/minio.yml` — Rename to `garage.yml`; translate operator knobs
- `playbooks/deploy_docker.yml` — Line 36: `role: minio` → `role: garage`
- `docs/architecture.md` — MinIO references in component table and dependency graph
- `docs/quickstart.md` — MinIO references in setup steps
- `docs/inventory.md` — MinIO operator knobs documentation
- `roles/README.md` — MinIO references in cross-cutting gates and component list

### Requirements
- `.planning/REQUIREMENTS.md` — STORE-01, STORE-02, STORE-03, OPS-01 requirement definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- MinIO role task structure (main.yml + bootstrap.yml + handlers + defaults + templates) — direct template for the Garage role, adapted for Garage's TOML config and multi-step bootstrap
- `docker_container_exec` verify pattern from Phase 4 Bug 1 fix — canonical pattern for all in-container verification
- Prometheus scrape job template pattern (existing three hardcoded jobs) — template for the Garage metrics job

### Established Patterns
- Bootstrap is the LAST blocking task in the storage role (D-08) — Garage bootstrap must follow the same ordering
- `changed_when: false` on idempotent verify/bootstrap tasks — Garage bootstrap must do the same for `changed=0` on re-runs
- Network alias pattern: container name + short alias (e.g., `telemetron-minio` + `minio`) — Garage should be `telemetron-garage` + `garage`
- Conditional host-port publish via `*_publish_host` knob — Garage gets `garage_publish_host` defaulting to `false`
- Gate 7 labels: `org.telemetron.service: telemetron`, `org.telemetron.job: garage`
- Gate 8: Parent-directory bind mounts only

### Integration Points
- `playbooks/deploy_docker.yml` role ordering: `garage → loki → tempo → mimir → ...` (same slot as MinIO)
- Backend S3 endpoint defaults change from `minio:9000` to `garage:3900` — Loki/Tempo/Mimir rendered configs point to the Garage container via Docker bridge DNS
- Prometheus rendered config gets a new scrape job section for Garage metrics
- `inventory/example-homelab/` file renames and var renames cascade to `secrets.yml.example` and all three backend defaults

</code_context>

<specifics>
## Specific Ideas

No specific requirements — the migration is well-defined by STORE-01/02/03 and OPS-01 with clear before/after states. Bootstrap credential persistence (D-112) to a host file is the main novel pattern not present in the MinIO role.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 8-Garage Role + Backend Retargeting*
*Context gathered: 2026-05-27*
