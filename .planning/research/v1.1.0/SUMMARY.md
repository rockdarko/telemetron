# Project Research Summary — Telemetron v1.1.0

**Domain:** Self-hosted Ansible-deployed LGTM observability stack — Garage migration + backlog sweep
**Researched:** 2026-05-26
**Confidence:** HIGH

## Executive Summary

v1.1.0 is a focused milestone: replace the archived MinIO community edition with Garage v2.3.0 as the S3-compatible object store, and close four M1 backlog config regressions. The Garage migration touches five roles (new `garage` role replaces `minio`, plus endpoint updates in `loki`, `tempo`, `mimir`). The backlog fixes are self-contained one-to-three-file changes per role. All work stays on the existing single-host Docker stack.

**Priority order:** Fix Mimir retention first (live production regression — no retention enforcement at all), then ship Garage role and retarget backends, then apply Fluent Bit fixes and label reconciliation last.

## Stack Additions/Changes

| Component | Current | New | Why |
|-----------|---------|-----|-----|
| Object storage | `minio/minio:RELEASE.2025-04-22T22-12-26Z` (archived) | `dxflrs/garage:v2.3.0` (AGPL, active) | MinIO community archived early 2026; Garage is actively maintained, designed for homelab |
| Bootstrap CLI | `minio/mc` one-shot container | `garage` binary inside the image via `docker_container_exec` | Net simplification — no separate mc image needed |
| S3 API port | `:9000` | `:3900` | No conflict with existing allocation |
| Admin port | `:9001` (MinIO Console) | `:3903` (Garage Admin API) | No browser console; CLI-first admin |
| Volumes | 1 (`telemetron_minio_data`) | 2 (`telemetron_garage_meta` + `telemetron_garage_data`) | Garage separates metadata DB from object blobs |

**No version bumps** for any other component. All 11 remaining roles stay at M1 pins.

## Critical Pitfalls

| ID | Pitfall | Severity | Prevention |
|----|---------|----------|------------|
| G-1 | Garage layout must be assigned before any S3 write; writes silently fail otherwise | HIGH | Bootstrap: start → poll health → layout assign → layout apply → key create → bucket create × 5 → bucket allow × 5 |
| M-1 | Mimir retention not enforced at all (live regression) — blocks accumulate forever | HIGH | Fix first, before any other v1.1.0 work |
| G-2 | Endpoint format asymmetry: Loki needs `http://garage:3900`; Mimir/Tempo need bare `garage:3900` | MEDIUM | Scheme-free base var; Loki template adds `http://` |
| G-6 | Loki `object_store: s3` may not work with Garage (community reports GET-only) | MEDIUM | Set `object_store: aws` defensively; verify with PutObject metric |
| O-1 | `service` vs `service_name` label split breaks cross-signal correlation | MEDIUM | Rename everywhere in one phase; sweep dashboards |
| G-5 | Data migration while backends run corrupts TSDB index | HIGH | Stop-window: stop FB → stop backends → rclone → start Garage → restart. Homelab: fresh-start. |

## Suggested Build Order (3 phases)

### Phase 1: Backlog Regression Fixes
Fix live production bugs before adding new infrastructure — narrows Garage debugging blast radius.
- Mimir: add `compactor_blocks_retention_period` under `limits:` (one-line template fix)
- Tempo: rename orphan var → `tempo_compactor_compaction_window: 1h`; wire into template
- FB: add Lua `set_ingest_timestamp` to `enrich.lua`; replace disabled Modify filter with Lua call

### Phase 2: Garage Role + Backend Retargeting
New `roles/garage/` + S3 endpoint retarget across 3 backend roles.
- New role: `garage.toml.j2`, `tasks/bootstrap.yml` (layout → key → buckets via `docker_container_exec`), healthcheck on `:3903`
- Loki/Tempo/Mimir: endpoint `minio:9000` → `garage:3900`; credential vars `minio_root_*` → `garage_*`
- Loki: set `object_store: aws` defensively
- Remove `minio_mc_image` / `mimir_mc_image` vars; swap `minio` → `garage` in `deploy_docker.yml`
- Inventory updates: `secrets.yml.example` adds `garage_rpc_secret`, `garage_admin_token`
- Docs: port table, data migration guide (stop-sync-start + fresh-start paths)

### Phase 3: Label Reconciliation + Scrape Config
Breaking query change isolated from storage migration risk.
- `enrich.lua`: `record["service"]` → `record["service_name"]`
- Grafana dashboard JSON sweep: `{service=` → `{service_name=`
- Optional: Garage admin metrics scrape at `:3903/metrics`
- Optional: OTel Collector `transform` processor to strip `service.namespace`

## Open Questions (verify at execute time)

1. Garage health endpoint — `GET /health` on S3 port `:3900` or only admin `:3903`?
2. `garage key import` — can credentials be pre-generated in `secrets.yml` and imported?
3. `--single-node` flag — does it skip the layout-assign step?
4. `object_store: aws` in Loki — confirm with PutObject metric after first Garage deploy

---
*Research completed: 2026-05-26 — Ready for requirements definition*
