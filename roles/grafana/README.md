# grafana

Deploys Grafana OSS 13.0.1 (`grafana/grafana-oss:13.0.1`) on the `telemetron` Docker bridge network, listening on port `:3000` (host-published by default -- D-82 inverts the `telemetron_publish_default:false` convention for the UI plane). The role ships four datasources provisioned at hardcoded UIDs (`prometheus`, `loki`, `tempo`, `mimir`) and seven curated starter dashboards under the `Telemetron` folder. Trace-to-logs correlation is wired via `tracesToLogsV2` on the Tempo datasource and a `derivedFields` trace_id link on the Loki datasource. Embedded SQLite on the `telemetron_grafana_data` persistent volume is the backing store (no Postgres needed for M1 single-host homelab use).

Requirements: UI-01 (persistent volume), UI-02 (datasource UIDs), UI-03 (curated dashboards), UI-04 (trace-to-logs correlation). Cross-linked to Phase 5 `karma` (plan 05-02) and `promlens` (plan 05-03 -- deprecation candidate) roles.

---

## What this role does

1. Ensures config tree on the host: `{{ grafana_config_dir }}/` with subdirs `provisioning/datasources/`, `provisioning/dashboards/`, `provisioning/dashboards/telemetron/`.
2. Renders `grafana.ini` from `templates/grafana.ini.j2` (structural config: paths, server bind, SQLite database, default theme, anonymous-viewer toggle). Changes notify the `restart grafana` handler.
3. Renders `provisioning/datasources/datasources.yaml` from `templates/datasources/datasources.yaml.j2` with four UID-pinned datasources + D-79 `tracesToLogsV2` (Tempo) and `derivedFields` (Loki). Hot-reloaded by Grafana without restart.
4. Renders `provisioning/dashboards/dashboards.yaml` from `templates/dashboards/dashboards.yaml.j2` with the D-76 two-provider manifest (read-only `Telemetron` folder + writable `Operator` drop-in). Hot-reloaded by Grafana.
5. Copies seven role-shipped dashboard JSONs to `provisioning/dashboards/telemetron/` (host-health, loki-explore-landing, tempo-explore-landing, otel-collector-self-metrics, loki-self-metrics, tempo-self-metrics, mimir-self-metrics).
6. Ensures the `telemetron_grafana_data` named volume (embedded SQLite store + sessions + plugin cache).
7. Pulls `grafana/grafana-oss:13.0.1`.
8. Assembles the `grafana_mounts` list (volume + parent-dir config bind + optional operator drop-in bind when `grafana_dashboard_extra_dir` is set).
9. Runs the `telemetron-grafana` container with: Gate-7 labels (`org.telemetron.service: telemetron`, `org.telemetron.job: grafana`), explicit `HEALTHCHECK` (image ships none -- RESEARCH Risk 3), `GF_SECURITY_ADMIN_*` env injection, and parent-dir bind mount of `{{ grafana_config_dir }}` to `/etc/grafana` (Gate 8).
10. Flushes handlers (so restart fires before verify).
11. Runs `tasks/verify.yml` -- D-10a HEALTHCHECK poll, `/api/health` probe, Gate 9 D-73 datasource health checks + canonical queries for all four UIDs, and UI-04 wiring assertions.

---

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `grafana_image` | `grafana/grafana-oss` | Container image (OSS; avoids Enterprise gates) |
| `grafana_image_tag` | `13.0.1` | Pinned tag (OPS-01) |
| `grafana_container_name` | `telemetron-grafana` | Docker container name and bridge DNS alias |
| `grafana_publish_host` | `true` | Publish port to host (D-82 UI plane exception). Trinary: `true` / `false` / `"127.0.0.1"` |
| `grafana_bind_address` | `0.0.0.0` | Host bind address (D-83). Set to `127.0.0.1` for ssh-tunnel-only access |
| `grafana_http_port` | `3000` | HTTP port (D-84) |
| `grafana_data_volume` | `telemetron_grafana_data` | Named volume for embedded SQLite + sessions + plugins |
| `grafana_data_path` | `/var/lib/grafana` | Container mount path for data volume |
| `grafana_config_dir` | `/opt/telemetron/grafana` | Host directory for rendered config tree |
| `grafana_config_container_path` | `/etc/grafana` | Container path for config bind mount |
| `grafana_admin_user` | `admin` | Grafana admin username (D-88) |
| `grafana_admin_email` | `admin@telemetron.local` | Grafana admin email (D-88) |
| `grafana_anonymous_enabled` | `false` | Enable anonymous viewer access (D-87); flip `true` for wall-display kiosk mode |
| `grafana_default_theme` | `dark` | Default UI theme (`dark` / `light`) |
| `grafana_prometheus_url` | `http://prometheus:9090` | Prometheus datasource URL (telemetron bridge DNS) |
| `grafana_loki_url` | `http://loki:3100` | Loki datasource URL |
| `grafana_tempo_url` | `http://tempo:3200` | Tempo datasource URL |
| `grafana_mimir_url` | `http://mimir:9009/prometheus` | Mimir datasource URL (Prometheus-compatible subpath; D-26) |
| `grafana_dashboard_extra_dir` | `""` | Host path for operator drop-in dashboards (D-76); empty = no third mount |
| `grafana_extra_datasources` | `[]` | Additional datasource objects to merge into `datasources.yaml` |
| `grafana_extra_env` | `{}` | Extra env vars on the container (GF_* escape hatch) |
| `grafana_healthcheck_enabled` | `true` | Enable explicit container HEALTHCHECK |
| `grafana_healthcheck_test` | `CMD-SHELL wget --spider ...` | Healthcheck command |
| `grafana_healthcheck_interval` | `15s` | Healthcheck interval |
| `grafana_healthcheck_timeout` | `5s` | Healthcheck timeout |
| `grafana_healthcheck_retries` | `5` | Healthcheck retries before unhealthy |
| `grafana_healthcheck_start_period` | `60s` | Start period (generous for first-boot SQLite init) |
| `grafana_health_retries` | `45` | Verify pre-poll retries (D-10a; 45 x 2s = 90s budget) |
| `grafana_health_delay` | `2` | Verify pre-poll delay in seconds |
| `grafana_restart_policy` | `unless-stopped` | Container restart policy (OPS-06) |
| `grafana_memory_limit` | `512m` | Container memory limit |
| `grafana_network` | `telemetron` | Docker bridge network name |
| `grafana_tz` | `Etc/UTC` | Container timezone (Pitfall 6 / OPS-06) |
| `grafana_curl_image` | `curlimages/curl` | Curl image for verify one-shots (OPS-01) |
| `grafana_curl_image_tag` | `8.10.1` | Pinned curl image tag |

### Secrets

`grafana_admin_password` must be defined in `inventory/example-homelab/group_vars/all/secrets.yml` (not tracked in git). See `inventory/example-homelab/group_vars/all/secrets.yml.example` for the placeholder.

> `grafana_admin_password` is consumed via the `GF_SECURITY_ADMIN_PASSWORD` env var. **Grafana sets the admin password when it initializes the database on first startup.** Subsequent restarts with a different env-var value do NOT update the stored password (this is documented Grafana behavior, not a Telemetron defect). To rotate the admin password after the initial deploy:
>
> ```bash
> docker exec telemetron-grafana grafana-cli admin reset-admin-password '<new-password>'
> ```
>
> Then update the inventory `grafana_admin_password` to match (so future fresh deploys + verify Gate 9 use the new password).

---

## Tags

| Tag | Runs |
|-----|------|
| `grafana` | All tasks (config + container + verify) |
| `grafana-config` | Config tree creation, template rendering, JSON copy |
| `grafana-container` | Volume, image pull, mounts assembly, container run |
| `grafana-verify` | Flush handlers + verify.yml (HEALTHCHECK poll + Gate 9) |

---

## Modes

Single mode: **embedded SQLite, single-instance**. Grafana manages its own dashboard metadata, alert rules, and sessions in an embedded SQLite database on the `telemetron_grafana_data` named volume.

Postgres-backed HA Grafana is deferred to a future milestone per PROJECT.md (no Postgres consumer in M1). Returning only if HA Grafana lands (multiple Grafana replicas behind a load balancer sharing a backing store).

---

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `telemetron_grafana_data` (named) | `/var/lib/grafana` | Embedded SQLite (dashboards SQLite, sessions, plugins cache). Persistent. |
| `/opt/telemetron/grafana` (bind, ro) | `/etc/grafana` | Rendered config tree: `grafana.ini`, `provisioning/datasources/datasources.yaml`, `provisioning/dashboards/dashboards.yaml`, `provisioning/dashboards/telemetron/*.json`. Parent-dir bind per Gate 8. |
| `{{ grafana_dashboard_extra_dir }}` (optional bind, ro) | `/etc/grafana/provisioning/dashboards/operator` | Operator drop-in dir (D-76). Only mounted when `grafana_dashboard_extra_dir` is non-empty. |

---

## Healthcheck

Image `grafana/grafana-oss:13.0.1` ships **no built-in HEALTHCHECK** (RESEARCH Risk 3). The role declares an explicit probe:

```yaml
grafana_healthcheck_test: ["CMD-SHELL", "wget --spider -q http://localhost:3000/api/health || exit 1"]
grafana_healthcheck_interval: 15s
grafana_healthcheck_timeout: 5s
grafana_healthcheck_retries: 5
grafana_healthcheck_start_period: 60s
```

Verify command after deploy:

```bash
docker inspect telemetron-grafana --format '{{.State.Health.Status}}'
# Expected: healthy
```

---

## Access model

- **Login required by default** (`grafana_anonymous_enabled: false`). Operator flips to `true` for wall-display / TV-mode kiosks (D-87).
- **Admin user**: `admin` + email `admin@telemetron.local` (D-88). Rotate post-deploy via `grafana-cli` (see Secrets section above).
- **Org**: stock `Main Org.` (D-89). Multi-org provisioning deferred.
- **SSO / LDAP**: deferred (post-M1 hardening). Grafana supports both but M1 is single-host homelab.

---

## Network -- Host publishing

D-82 inverts `telemetron_publish_default:false` for the UI plane. Grafana is published to the host on `:3000` by default so operators can open it in a browser without SSH tunneling.

Operators who want to run a reverse proxy can flip `grafana_publish_host: false` and proxy via the telemetron bridge (see Reverse proxy section below).

---

## Network -- Bind address

`grafana_bind_address: 0.0.0.0` (D-83) by default -- port `:3000` binds all host interfaces. Set to `127.0.0.1` for ssh-tunnel-only access (`ssh -L 3000:localhost:3000 <host>`).

---

## Reverse proxy

D-85: Telemetron ships no opinion on reverse proxy or TLS termination. Operator hardening pattern:

1. Set `grafana_publish_host: false` in inventory (stops host-port publishing).
2. Run Caddy / Traefik / nginx / Apache on the host (or a container on the `telemetron` bridge).
3. Proxy `https://grafana.example.com` -> `http://grafana:3000` (reachable via the bridge).

<!-- TODO Phase 6: docs/quickstart.md cross-link -->

---

## Datasources

Four datasources provisioned at hardcoded UIDs (D-77). UIDs are stable across redeploys and referenced by all seven role-shipped dashboard JSONs -- do not change without coordinating with `files/dashboards/*.json`.

| UID | Name | Type | URL |
|-----|------|------|-----|
| `prometheus` | Prometheus | `prometheus` | `http://prometheus:9090` |
| `loki` | Loki | `loki` | `http://loki:3100` |
| `tempo` | Tempo | `tempo` | `http://tempo:3200` |
| `mimir` | Mimir | `prometheus` | `http://mimir:9009/prometheus` |

**Mimir note**: Mimir type is `prometheus` (NOT `type: mimir`) pointed at the Prometheus-compatible `/prometheus` subpath. D-26 `multitenancy_enabled:false` means no `X-Scope-OrgID` header is needed.

---

## Dashboards

Seven role-shipped dashboards under the `Telemetron` Grafana folder (D-75). All UIDs pre-substituted; no runtime download (D-74):

| File | Source | UIDs used |
|------|--------|-----------|
| `host-health.json` | Grafana.com 1860 rev 45 (node_exporter full) | `prometheus` |
| `loki-explore-landing.json` | Hand-rolled Loki Explore landing page | `loki` |
| `tempo-explore-landing.json` | Hand-rolled Tempo Explore landing page | `tempo` |
| `otel-collector-self-metrics.json` | Grafana.com 15983 rev 29 (OTel Collector) | `prometheus` |
| `loki-self-metrics.json` | grafana/loki v3.7.2 `dashboard-loki-operational.json` | `prometheus`, `loki` |
| `tempo-self-metrics.json` | grafana/tempo v2.10.5 `tempo-operational.json` | `prometheus`, `loki` |
| `mimir-self-metrics.json` | grafana/mimir mimir-3.0.6 `mimir-overview.json` | `prometheus` (Mimir self-metrics scraped BY Prometheus) |

The `files/_rewrite_uids.py` helper documents the per-dashboard UID substitution map and was run once at fork time to produce the committed JSONs.

**Operator drop-in folder** (D-76): set `grafana_dashboard_extra_dir` to a host path containing `*.json` dashboards; they auto-load into the `Operator` Grafana folder. Empty string = no third mount (default).

---

## Trace-to-logs correlation

Telemetron wires bidirectional trace-to-logs correlation in Grafana.

### Tempo -> Loki (`tracesToLogsV2` on the Tempo datasource)

- Custom query: `{${__tags}} | trace_id="${__span.traceId}"`
- Tag forwarded: `service.name` -> `service_name` (D-80; minimal one-tag default).
- Effect: clicking a span in Tempo Explore opens Loki Explore with logs filtered to the same service AND the same `trace_id`.

### Loki -> Tempo (`derivedFields` on the Loki datasource)

Two matchers fire independently per log line. Whichever produces a hit shows a clickable **View in Tempo** button in the log detail panel. The pre-05-07 single-matcher form (`matcherType: label`) was incorrect because telemetron's live Loki labels are `{env, host, job, service_name}` -- no `trace_id` label exists. Plan 05-07 (gap closure) replaced it with the two-matcher form below.

1. **`structured_metadata` matcher (canonical, OTel-native)** -- matches log lines pushed via OTLP where the OTel SDK has attached `trace_id` as a structured-metadata field. This is the D-78 design contract: instrumented apps get reliable trace correlation. Loki 3.x stores OTel `trace_id` as structured metadata by default (not as a label, avoiding cardinality explosion).
2. **`regex` matcher (fallback, body-embedded)** -- matches when the log line body contains text like `trace_id=abc123def` or `traceID:abc123def`. Pattern: `(?:trace_id|traceID)[=:]"?([a-f0-9]+)`. Useful for legacy apps or hand-rolled instrumentation that embeds the id in the log body rather than as a structured field. Surfaces as the separate `trace_id_body` derived field so Grafana renders both links rather than deduplicating them.

### Label mapping note (D-81 / 999.4 backlog)

Live Loki labels in telemetron are `{env, host, job, service_name}` -- the OTel resource attribute `service.name` surfaces as `service_name` (OTel convention) rather than `service` (Phase 3 D-47 spec). Phase 5 accepts this per D-81 -- a future milestone may relabel via OTel exporter (option (c) in ROADMAP.md sec.999.4 backlog) to reconcile. Until then, all Grafana queries use `service_name` as the canonical service identifier.

### What this does NOT cover (M1 scope honesty)

E2E verification of the click-through requires:

- Either an OTel-instrumented app pushing traces+logs to telemetron's OTel Collector on `:4318` (OTLP HTTP) or `:4317` (OTLP gRPC), with both carrying the same `trace_id`;
- Or an uninstrumented app whose log lines contain `trace_id=<hex>` strings AND whose traces are independently pushed to Tempo (typical of homegrown Go services using a logging convention without full OTel SDK adoption).

Telemetron M1 ships no instrumented sample app. Operators verify the click-through by deploying their own instrumented service against the stack. The static wiring (derivedFields config -> Tempo datasourceUid linkage) is verified at deploy time by Gate 9 D-73 Step 9 (UI-04 -- assert Loki datasource derivedFields trace_id is wired).

---

## Label mapping

Live Loki labels are `{host, job, service_name}`. The Phase-3 spec'd `service` label is surfaced as `service_name` because the OTel Collector's `otlphttp/loki` exporter promotes the `service.name` resource attribute to `service_name` (Loki 3.x OTLP-native ingestion default). Telemetron M1 accepts this and standardises on `service_name`; D-80 forwards `service.name -> service_name` as the only `tracesToLogsV2` tag. A future post-M1 milestone may retrofit canonical `service` naming via an OTel exporter relabel rule -- see ROADMAP.md sec.999.4.

---

## Security

Single-host bridge trust boundary (D-26 / D-66 / D-90). All backend datasources (Loki, Tempo, Mimir, Prometheus) have auth disabled on the telemetron bridge -- they are not exposed to the host by default. Admin password is env-injected at first boot only (see Secrets section). No LDAP, no SSO in M1.

---

## Idempotency

Second back-to-back `ansible-playbook --tags grafana` run reports `changed=0` (OPS-04). Container restarts via the `restart grafana` handler triggered only when `grafana.ini` changes (rendered via `notify:`). Datasource and dashboard provisioning files hot-reload without restart. `state: restarted` is never used.

---

## Per-role port-acceptance gates

Gates 1-9 apply to this role. Gate 9 (D-73) is specific to the Grafana role (datasources-resolve-real-data) and is documented in `roles/README.md` under `## Per-role port-acceptance gates`.

---

## Deviations from upstream INSPQ

D-25 audit summary (RESEARCH sec.6.1):

- **File provisioning replaces API-call provisioning**: upstream used `community.grafana.grafana_datasource` / `grafana_folder` Ansible modules that call the Grafana HTTP API at playbook time. Replaced with Grafana's native file-provisioning (`/etc/grafana/provisioning/`). File provisioning is idempotent, works before Grafana is running, and survives `docker volume rm` + fresh deploy.
- **Image pin**: upstream used `grafana/grafana:latest`. Changed to `grafana/grafana-oss:13.0.1` (explicit OSS variant, pinned tag).
- **Dropped SMTP config**: upstream had `grafana_smtp_*` vars and a rendered SMTP section in `grafana.ini`. M1 Grafana has no outbound notification destination (alerting is Alertmanager's job).
- **Dropped LDAP**: upstream had `files/ldap.toml` and `grafana_ldap_*` vars. LDAP/SSO deferred to post-M1 hardening.
- **Dropped Kubernetes/Helm tasks**: upstream had optional Helm install path. Telemetron M1 is Docker-only.
- **Dropped `application_web_docker` dependency**: upstream paired each web service with an Apache vhost. Telemetron is reverse-proxy-agnostic (D-85); no role-level reverse proxy wiring.
- **Dropped INSPQ defaults**: `America/Toronto` timezone (replaced with `Etc/UTC`), `noreply@inspq.qc.ca` SMTP from, INSPQ org name, FR-language task names.
- **Dropped `grafana_plugins`**: upstream installed Grafana plugins at deploy time. Plugin management deferred; M1 stack uses only built-in panel types.
- **Hardcoded datasource UIDs**: upstream relied on auto-generated UIDs (highest portability pitfall). All four UIDs are explicitly pinned per D-77.
- **Trace-to-logs correlation added**: upstream had no `tracesToLogsV2` wiring. Telemetron adds D-79 + D-80 as M1 baseline (UI-04).
