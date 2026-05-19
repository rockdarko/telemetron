# roles/promlens

## DEPRECATION CANDIDATE

PromLens (v0.3.0, last tagged 2022-12) is shipped for upstream-INSPQ parity. Prometheus 3.x's built-in UI absorbs PromLens's tree-view feature (CLAUDE.md "PromLens reality check"). New deployments should use Prometheus's native UI at `http://prometheus:9090/graph`. PromLens will likely be dropped in a future Telemetron milestone.

This role exists for upstream parity and is treated as a deprecate-in-place artifact. If you're evaluating Telemetron for a new homelab deployment, skip the `promlens` tag (`--skip-tags promlens`) -- nothing else in the stack depends on it.

---

Deploys PromLens `prom/promlens:v0.3.0` on the `telemetron` Docker bridge network. PromLens is a PromQL query editor with tree-view expression analysis that was pinned at host port `:8081` (UI-06). The role is **pure-CLI** -- no rendered config file is needed (PromLens v0.3.0 uses CLI flags via kingpin exclusively). No persistent volume is required (stateless).

## What this role does

1. Pulls `prom/promlens:v0.3.0`.
2. Runs the `telemetron-promlens` container on the `telemetron` bridge with:
   - Explicit HEALTHCHECK (image has none per RESEARCH §2.3) targeting root `/` (no `/health` endpoint in v0.3.0).
   - Gate-7 labels `org.telemetron.service: telemetron` / `org.telemetron.job: promlens`.
   - CLI flags `--web.default-prometheus-url={{ promlens_prometheus_url }}` and `--web.listen-address=:8080`.
   - Host port publish: `0.0.0.0:8081` → container `:8080` (D-82/D-83/D-84).
3. Runs the verify suite: HEALTHCHECK poll + root path probe + upstream Prometheus reachability cross-check.
4. Does **NOT** render any config file (PromLens is pure-CLI per RESEARCH §2.3).
5. Does **NOT** create any persistent volume (stateless).
6. Does **NOT** configure Grafana integration (D-25 audit per RESEARCH §6.3 dropped `--grafana.url` / `--grafana.api-token` for M1).

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `promlens_image` | `prom/promlens` | Container image repository |
| `promlens_image_tag` | `v0.3.0` | Image tag (pinned; OPS-01) |
| `promlens_container_name` | `telemetron-promlens` | Container name |
| `promlens_publish_host` | `true` | `true` = publish on `promlens_bind_address`; `"127.0.0.1"` = loopback only; `false` = no publish |
| `promlens_bind_address` | `0.0.0.0` | Host bind address for port publish (D-83) |
| `promlens_http_port` | `8081` | Host-side published port (D-84) |
| `promlens_container_port` | `8080` | Container listen port; matches `--web.listen-address` default |
| `promlens_prometheus_url` | `http://prometheus:9090` | Prometheus URL passed to `--web.default-prometheus-url` CLI flag |
| `promlens_healthcheck_enabled` | `true` | Toggle explicit HEALTHCHECK declaration |
| `promlens_healthcheck_test` | `wget --spider -q http://localhost:8080` | Healthcheck command (root path -- no /health endpoint in v0.3.0) |
| `promlens_healthcheck_interval` | `30s` | Healthcheck interval |
| `promlens_healthcheck_timeout` | `5s` | Healthcheck timeout |
| `promlens_healthcheck_retries` | `3` | Healthcheck retries before unhealthy |
| `promlens_healthcheck_start_period` | `15s` | Healthcheck grace period on container start |
| `promlens_health_retries` | `20` | Verify pre-poll retry count (D-10a) |
| `promlens_health_delay` | `2` | Verify pre-poll delay between retries (seconds) |
| `promlens_restart_policy` | `unless-stopped` | Container restart policy (OPS-06) |
| `promlens_memory_limit` | `128m` | Container memory limit |
| `promlens_network` | `{{ telemetron_network \| default('telemetron') }}` | Docker network name |
| `promlens_tz` | `{{ telemetron_tz \| default('Etc/UTC') }}` | Container timezone (Pitfall 6) |
| `promlens_curl_image` | `curlimages/curl` | Image for in-network curl verify one-shots |
| `promlens_curl_image_tag` | `8.10.1` | Pinned curl image tag (OPS-01) |

## Vault keys

None added in Phase 5. The dropped Grafana service-account integration (D-25 / RESEARCH §6.3) would have required a `promlens_grafana_api_token` key -- skipping it for M1. PromLens has no outbound auth in M1 (read-only PromQL editor; the Prometheus connection on the telemetron bridge needs no auth).

## Tags

| Tag | Runs |
|-----|------|
| `promlens` | Full role (pull + container + verify) |
| `promlens-container` | Container run task only |
| `promlens-verify` | Verify tasks only (flush_handlers + verify.yml) |

## Modes

**Single mode:** Stateless single-instance pointed at one Prometheus. SQL-based shared links (PromLens's `--shared-links.sql.driver=sqlite` feature) is **NOT** enabled in M1 (D-25 audit per RESEARCH §6.3).

**Deprecation track:** This role is on the deprecation track. Prometheus 3.x's native UI at `http://prometheus:9090/graph` absorbs PromLens's tree-view feature. See "Why PromLens is a deprecation candidate" below.

## Volumes

None. PromLens is stateless and has no config file. Gate 8 (parent-directory bind-mount convention) is vacuously satisfied -- there are no bind mounts to apply the convention to.

## Healthcheck

PromLens `v0.3.0` has **no built-in HEALTHCHECK** in the container image (RESEARCH §2.3). The role declares an explicit healthcheck:

```yaml
test: ["CMD-SHELL", "wget --spider -q http://localhost:{{ promlens_container_port }} || exit 1"]
interval: 30s
timeout: 5s
retries: 3
start_period: 15s
```

The probe targets root `/` because PromLens 0.3.0 has **no dedicated `/health` endpoint** (RESEARCH §2.3). The root path returns HTTP 200 + PromLens UI HTML, which is the correct readiness signal.

Disable with `promlens_healthcheck_enabled: false` (e.g. during development or if the container image changes in the future to ship its own HEALTHCHECK).

## Network -- Host publishing

D-82 inverts D-30 for the UI plane. PromLens is browser-accessible by default:

- Host `:8081` → container `:8080` (D-84)
- Bind address: `0.0.0.0` (D-83; all host interfaces)

To restrict to loopback (and reverse-proxy from the same host):

```yaml
promlens_publish_host: "127.0.0.1"
```

To disable host publishing entirely (access only via Docker exec or SSH tunnel):

```yaml
promlens_publish_host: false
```

## Network -- Bind address

Default `0.0.0.0` exposes PromLens on all host interfaces. The security trade-off is low for M1: PromLens is a read-only PromQL editor with no write surface. It queries Prometheus (internal bridge) and serves a static HTML/JS UI. No auth surface is added.

For a more restricted setup, bind to loopback and reverse-proxy:

```yaml
promlens_bind_address: "127.0.0.1"
promlens_publish_host: "127.0.0.1"
```

## Reverse proxy

The pattern from `roles/grafana/README.md` "Reverse proxy" section applies identically. Upstream target: `http://promlens:8080` (internal bridge) or `http://localhost:8081` (host loopback with `promlens_bind_address: "127.0.0.1"`). TLS termination and external URL are operator-supplied (D-85).

## Configuration knobs

The only meaningful operator knob is `promlens_prometheus_url` (default `http://prometheus:9090`). Override in `inventory/<env>/group_vars/all/promlens.yml` if Prometheus runs on a non-default container name or port.

**Do not** attempt to configure PromLens via environment variables. PromLens v0.3.0 uses CLI flags exclusively (via kingpin). The only env var PromLens recognizes is `PROMLENS_SHARED_LINKS_DSN` (SQL connection string for shared links -- M1 does not enable this feature). There is **no** `PROMLENS_DEFAULT_BACKEND_URL` env var -- this was a CONTEXT.md Claude's Discretion suggestion that RESEARCH §2.3 corrected.

## Image SHA pin recommendation

`prom/promlens:v0.3.0` was released 2022-12-05 and is still pullable from Docker Hub (RESEARCH §2.3, verified 2026-05). For true air-gap durability, capture the image SHA after first pull and pin in inventory:

```bash
docker inspect prom/promlens:v0.3.0 --format '{{.RepoDigests}}'
# -> [prom/promlens@sha256:<hash>]
```

Then override `promlens_image_tag` in your inventory to the `sha256:<hash>` form. This is operator hardening, not a Telemetron-shipped default -- aligns with the deprecation-track posture (you're carrying a frozen image; SHA pin at least guarantees the exact bits don't drift).

## Why PromLens is a deprecation candidate

- **Last tagged release:** v0.3.0 (2022-12-05). No subsequent functional releases. The upstream PromLens repo has only dependency-update commits since the v0.3.0 tag.
- **Prometheus 3.x absorption:** Prometheus 3's built-in Mantine-based UI at `http://prometheus:9090/graph` absorbs the PromQL tree-view feature that was PromLens's primary differentiator. New deployments should use the native Prometheus UI.
- **Parity only:** Telemetron ships PromLens for upstream-INSPQ parity (UI-06). It is not recommended for new homelab deployments starting from this repo.
- **Skip tag:** `--skip-tags promlens` -- nothing in the stack depends on PromLens; it can be omitted cleanly.

## Security

PromLens runs on the single-host telemetron bridge trust boundary. It makes outbound queries to Prometheus only (read-only PromQL; no write surface). No auth is configured on the bridge (D-26 / D-66 / D-90 unchanged from other Phase-5 roles). The security posture is identical to Grafana's datasource queries: trust the network segment, not the application layer, for homelab deployments.

## Idempotency

A second back-to-back `--tags promlens` run reports `changed=0`. PromLens's container spec is fully deterministic (no rendered config, no volume init tasks). Only `docker_image: force_source: false` and `docker_container: recreate: false` are needed to achieve idempotency.

## Per-role port-acceptance gates

Gates 1-8 apply:

1. **Grep gate (INSPQ / non-ASCII):** `grep -riE 'inspq|qc\.ca|montreal...' roles/promlens/` returns 0 matches.
2. **Image-pin gate:** `prom/promlens:v0.3.0` -- no `:latest`.
3. **Secrets-discipline gate:** No vault keys in Phase 5 for PromLens (D-66 rationale applies: null outbound, single-host bridge, deprecation candidate).
4. **Idempotency gate:** Second run `changed=0`.
5. **Healthcheck + restart-policy gate:** `docker inspect telemetron-promlens --format '{{.State.Health.Status}}'` returns `healthy`; restart policy `unless-stopped`.
6. **Per-role README gate:** This document.
7. **Telemetron label-stamp gate:** `labels: { org.telemetron.service: telemetron, org.telemetron.job: promlens }`.
8. **Parent-directory bind-mount convention:** Vacuously satisfied -- no bind mounts (PromLens has no config file).

Gate 9 (datasources-resolve-real-data) does NOT apply -- this is a grafana-specific gate.

## Deviations from upstream INSPQ

D-25 audit per RESEARCH §6.3. Headline changes vs. upstream INSPQ `promlens` role:

**Dropped from upstream:**

- **Grafana service-account integration** (`--grafana.url`, `--grafana.api-token`, `promlens_grafana_api_token_name`): Adds secrets surface for no M1 value on a deprecation-candidate role. D-25 audit decision per RESEARCH §6.3.
- **Shared-links SQLite** (`--shared-links.sql.driver=sqlite`): No persistent shared-link DB in M1. Stateless is simpler and correct for a deprecation candidate.
- **`templates/docker/promlens.yml.j2` upstream YAML config file**: PromLens v0.3.0 is pure-CLI; the upstream YAML was unused by the container entrypoint and served only as documentation of available flags. Removed entirely (no templates dir in this role).
- **`application_web_docker` role dependency**: Dropped from M1 project-wide (PROJECT.md Out of Scope).
- **`state: absent` cleanup logic**: Upstream had a pre-task that stopped and removed the old container before re-creating. Telemetron uses `recreate: false` for idempotency; the absent-task pattern was non-idempotent.
- **`:latest` image tag**: Upstream used `prom/promlens:latest`. Telemetron pins `v0.3.0` (OPS-01 image-pin gate).
- **Host port `8086` (upstream)**: Telemetron uses `:8081` (D-84 port matrix). `:8086` clashed with InfluxDB convention and was not in the Phase-5 port allocation.

**Added vs. upstream:**

- **Explicit HEALTHCHECK declaration** (image has none; upstream had none declared; silent unhealthy risk).
- **Gate 7 telemetron label stamp** (`org.telemetron.{service,job}` for Fluent Bit enrichment via INGEST-07 Lua filter).
- **Deprecation banner at top of this README** (per CONTEXT.md "Specific Ideas" and CLAUDE.md "PromLens reality check").
- **Image SHA pin recommendation** (RESEARCH §2.3 air-gap hardening note).

**Kept from upstream (already correct):**

- `promlens_prometheus_url` knob mapped to `--web.default-prometheus-url` CLI flag (correct in upstream; retained).
