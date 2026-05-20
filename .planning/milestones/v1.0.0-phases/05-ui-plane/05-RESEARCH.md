# Phase 5: UI Plane - Research

**Researched:** 2026-05-19
**Domain:** Grafana provisioning (datasources + dashboards + tracesToLogsV2), Karma configuration, PromLens deployment, upstream INSPQ audit
**Confidence:** HIGH (Grafana provisioning schema, Karma config, PromLens flags confirmed from source). MEDIUM (tracesToLogsV2 exact query syntax per D-79 confirmed from Grafana devenv; Loki structured-metadata trace_id behavior confirmed from multiple docs sources). LOW on mixin dashboard UID-substitution specifics (runtime behavior not testable without a live Grafana instance).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-70:** Three plans, one per role. 05-01-PLAN.md = grafana, 05-02-PLAN.md = karma, 05-03-PLAN.md = promlens. Each plan is end-to-end shippable in isolation.
- **D-71:** Dependency-true order: grafana → karma → promlens. No plan depends on a later plan's output.
- **D-72:** Per-role light doc cascade in each plan (roles/README.md tick, role README, ROADMAP.md mark, PROJECT.md Active line).
- **D-73:** Gate 9 — datasources-resolve-real-data verify gate added to roles/README.md by plan 05-01. Curl /api/datasources/uid/<uid>/health for each of 4 UIDs + one canonical query per datasource.
- **D-74:** Hybrid source strategy: official upstream mixin JSONs + hand-rolled landing pages. All 7 JSONs committed at fork time. No runtime download.
- **D-75:** Exactly 7 dashboards: host-health.json, loki-explore-landing.json, tempo-explore-landing.json, otel-collector-self-metrics.json, loki-self-metrics.json, tempo-self-metrics.json, mimir-self-metrics.json.
- **D-76:** File-based provisioning + operator drop-in dir. Two providers in dashboards.yml.j2: `telemetron` folder (role-shipped) and `operator` folder (operator drop-in). Conditional bind-mount for operator dir.
- **D-77:** Hardcoded datasource UIDs in dashboard JSONs — `prometheus`, `loki`, `tempo`, `mimir`. No Jinja-templating of JSON files.
- **D-78:** Realistic correlation scope: OTLP-pushed app logs only. FB-tailed stdout/stderr logs do NOT carry trace_id unless app embeds it.
- **D-79:** tracesToLogsV2 customQuery on Tempo datasource locked to `{${__tags}} | trace_id="${__span.traceId}"`. Includes full YAML block.
- **D-80:** Forwarded tags: `service.name` → `service_name` only (single tag).
- **D-81:** Accept FB-vs-OTel Loki label drift (999.4 backlog). Ship with `service_name` as canonical. Phase 5 does NOT fix the ingest plane.
- **D-82:** UI plane is exempt from D-30's default-off host publishing. `grafana_publish_host: true`, `karma_publish_host: true`, `promlens_publish_host: true`.
- **D-83:** Bind address `0.0.0.0` default. Per-role `<role>_bind_address` knob exposed.
- **D-84:** Port matrix unchanged: Grafana host :3000, Karma host :8082, PromLens host :8081. Inventory-overrideable.
- **D-85:** Reverse-proxy/TLS recipe in roles/grafana/README.md only. Phase 5 leaves `<!-- TODO Phase 6 -->` marker.
- **D-86:** Vault key naming: `grafana_admin_password` (no `vault_` prefix per D-90).
- **D-87:** Anonymous viewer: default off. `grafana_anonymous_enabled: false` knob exposed.
- **D-88:** Admin user: username `admin`, email `admin@telemetron.local`. SSO is post-M1.
- **D-89:** Stock `Main Org.` — no org provisioning.
- **D-90:** Drop `vault_` prefix. Phase 4.1 must land before Phase 5 plan 05-01.

### Claude's Discretion
- Grafana container args (GF_ env vs grafana.ini sections)
- Karma config shape (which additional knobs to expose as inventory vars)
- PromLens config shape (env vars vs CLI flags)
- Healthcheck details per role (Grafana ships NO HEALTHCHECK, Karma ships NO HEALTHCHECK, PromLens ships NO HEALTHCHECK — all three need explicit declarations)
- Plan task order per role

### Deferred Ideas (OUT OF SCOPE)
- Project-wide vault_* rename (Phase 4.1 precondition — must land first)
- OPS-07 smoke test (Phase 6)
- docs/architecture.md, quickstart.md, inventory.md (Phase 6)
- nfsd opt-in role (Phase 6)
- 999.4 fix — option (c) OTel-side Loki label relabel (post-M1)
- SSO/LDAP/OAuth on Grafana (post-M1)
- Multi-org Grafana provisioning (post-M1)
- Grafana Enterprise features (never for M1)
- TLS/reverse proxy role (operator-supplied)
- Trace-to-logs body-regex extraction (post-M1)
- Karma silence-import API (post-M1)
- Mimir per-tenant datasource with X-Scope-OrgID (post-M1)
- PromLens replacement/removal (future milestone)
- MinIO replacement (future milestone)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Grafana OSS 13.0.1 on :3000, embedded SQLite on telemetron_grafana_data volume, admin password from inventory secret | §Grafana env injection, §SQLite default, §container UID (472:0) |
| UI-02 | Grafana datasources provisioned with explicit UIDs: prometheus, loki, tempo, mimir | §Datasource provisioning YAML schema, §canonical examples |
| UI-03 | 5-10 curated dashboards rendering real data on fresh deploy | §Dashboard sourcing inventory, §UID substitution approach |
| UI-04 | tracesToLogsV2 wired on Tempo datasource + trace_id derived field on Loki | §tracesToLogsV2 exact YAML, §derivedFields exact YAML, §structured metadata confirmation |
| UI-05 | Karma on :8082 (GHCR official) against M1 Alertmanager | §Karma config schema, §HEALTHCHECK, §image verification |
| UI-06 | PromLens on :8081 (v0.3.0) with deprecation banner in README | §PromLens flags, §deprecation note |
</phase_requirements>

---

## 1. Executive Summary

Five things the planner most needs to know:

1. **None of the three Phase-5 images ship a Docker HEALTHCHECK.** Grafana OSS 13.0.1 (confirmed from Dockerfile), Karma v0.130 (confirmed from Dockerfile), and PromLens v0.3.0 (confirmed from Dockerfile) all need explicit `healthcheck:` declarations in their `docker_container` tasks. For Grafana, use `CMD-SHELL wget --spider -q http://localhost:3000/api/health`. For Karma, use `CMD-SHELL wget --spider -q http://localhost:8080/health`. For PromLens, use `CMD-SHELL wget --spider -q http://localhost:8080`. All three are busybox-based or include wget.

2. **Mimir's mixin dashboard ships as pre-compiled JSON at `operations/mimir-mixin-compiled/dashboards/mimir-overview.json` at tag `mimir-3.0.6`.** Loki and Tempo ship actual JSON files at their version tags. The Grafana.com community dashboard 15983 (OTel) and 1860 (node_exporter) are downloadable at specific revisions. Dashboard JSON files from upstream mixins contain datasource template variables (`$datasource`, `$ds`, `$ds_prometheus`) that must be replaced with hardcoded UIDs per D-77 before committing.

3. **`GF_SECURITY_ADMIN_PASSWORD` is a first-boot-only setting.** Grafana sets the admin password when it initializes the database on first startup; subsequent environment-variable changes do NOT update the stored password. This is the key operator-communication point: "to rotate the admin password after first boot, use the Grafana UI or CLI, not the env var." The `grafana_admin_password` inventory variable is injected via `GF_SECURITY_ADMIN_PASSWORD` env on the container; it works correctly on fresh deploys.

4. **Grafana container runs as UID 472 (GF_UID).** The `telemetron_grafana_data` volume at `/var/lib/grafana` gets initialized with UID 472 ownership. Passing a different `user:` in `docker_container` causes "permission denied" at startup (same footgun as Loki/Tempo's 10001:10001 UID). Do NOT specify a custom user — inherit the image default (472:0, confirmed from Dockerfile).

5. **The trace-to-logs path is real and wired.** Phase 3's OTel config already pushes logs to Loki via `otlphttp/loki` to `http://loki:3100/otlp`. Loki 3.7.2's native OTLP ingestion stores `trace_id` (and `span_id`, `trace_flags`) as structured metadata — NOT as stream labels. The `derivedFields` `matcherType: label` in Grafana's Loki datasource works for structured metadata fields (confirmed: Grafana docs state label type works for "any type of label - indexed, parsed or structured metadata"). D-79's YAML is correct as written.

---

## 2. Per-Role Technical Details

### 2.1 Grafana (`grafana/grafana-oss:13.0.1`)

#### Container Identity and UID
- Container runs as `GF_UID=472` (declared in Dockerfile ARG; group 0). Do NOT specify `user:` in `docker_container` — inherit image default.
- Entrypoint: `/run.sh`
- Exposes: 3000

#### Image HEALTHCHECK
**CONFIRMED: grafana/grafana-oss:13.0.1 Dockerfile has NO HEALTHCHECK directive.**
The role must declare an explicit healthcheck:

```yaml
# In defaults/main.yml
grafana_healthcheck_enabled: true
grafana_healthcheck_test: ["CMD-SHELL", "wget --spider -q http://localhost:3000/api/health || exit 1"]
grafana_healthcheck_interval: 15s
grafana_healthcheck_timeout: 5s
grafana_healthcheck_retries: 5
grafana_healthcheck_start_period: 60s
```

The `/api/health` endpoint returns HTTP 200 with JSON `{"commit":"...","database":"ok","version":"13.0.1"}` when Grafana is ready. First-boot typically 10-30s. Start_period 60s gives buffer for DB initialization.

#### Environment Variables (Grafana reads GF_ env > grafana.ini > defaults.ini)
```yaml
env:
  GF_SECURITY_ADMIN_USER: "{{ grafana_admin_user | default('admin') }}"
  GF_SECURITY_ADMIN_PASSWORD: "{{ grafana_admin_password }}"
  GF_SECURITY_ADMIN_EMAIL: "{{ grafana_admin_email | default('admin@telemetron.local') }}"
  GF_AUTH_ANONYMOUS_ENABLED: "{{ grafana_anonymous_enabled | default('false') | string | lower }}"
  GF_AUTH_ANONYMOUS_ORG_ROLE: "Viewer"
  GF_AUTH_ANONYMOUS_ORG_NAME: "Main Org."
  TZ: "{{ grafana_tz }}"
```

**CRITICAL: GF_SECURITY_ADMIN_PASSWORD is first-boot-only.** Grafana docs state: "Set once on first-run." The env var initializes the SQLite database admin row on first start. Subsequent restarts with a different value do NOT update the stored password. Operator password rotation after first boot requires: Grafana UI profile settings, or `grafana-cli admin reset-admin-password <newpass>` inside the container.

Document this in `roles/grafana/README.md` "Secrets" section: "Changing `grafana_admin_password` in inventory after a successful first deploy will NOT take effect until you reset the password via UI or CLI."

#### SQLite Backing Store (UI-01)
Grafana 13 defaults to SQLite at `/var/lib/grafana/grafana.db` when no database section is configured. The `telemetron_grafana_data` volume mounted at `/var/lib/grafana` is sufficient — no `GF_DATABASE_TYPE` or connection string needed. Confirmed from `conf/defaults.ini`: `type = sqlite3`, `path = grafana.db`.

#### Anonymous Viewer (D-87)
```ini
[auth.anonymous]
enabled = true
org_role = Viewer
org_name = Main Org.
```
Via env: `GF_AUTH_ANONYMOUS_ENABLED=true`, `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`, `GF_AUTH_ANONYMOUS_ORG_NAME=Main Org.` Anonymous viewers can access dashboards in provisioned folders (Telemetron, Operator) without explicit folder permission grants — Viewer role grants read access to all dashboards in the default org.

#### Datasource Provisioning Schema (UI-02)

**File location in container:** `/etc/grafana/provisioning/datasources/datasources.yaml`
**File location on host (Gate 8 parent-dir mount):** `/opt/telemetron/grafana/provisioning/datasources/datasources.yaml`
**Mount pattern:** `source: /opt/telemetron/grafana/provisioning → target: /etc/grafana/provisioning, type: bind, read_only: true`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    url: http://prometheus:9090
    access: proxy
    isDefault: false
    editable: false
    jsonData:
      prometheusType: Prometheus
      prometheusVersion: "3.11.3"

  - name: Loki
    type: loki
    uid: loki
    url: http://loki:3100
    access: proxy
    editable: false
    jsonData:
      derivedFields:
        - name: trace_id
          matcherType: label
          matcherRegex: trace_id
          url: '${__value.raw}'
          datasourceUid: tempo
          urlDisplayLabel: 'View in Tempo'

  - name: Tempo
    type: tempo
    uid: tempo
    url: http://tempo:3200
    access: proxy
    editable: false
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: '-1h'
        spanEndTimeShift: '1h'
        tags:
          - key: 'service.name'
            value: 'service_name'
        filterByTraceID: false
        filterBySpanID: false
        customQuery: true
        query: '{${__tags}} | trace_id="${__span.traceId}"'
      serviceMap:
        datasourceUid: prometheus
      nodeGraph:
        enabled: true

  - name: Mimir
    type: prometheus
    uid: mimir
    url: http://mimir:9009/prometheus
    access: proxy
    isDefault: false
    editable: false
    jsonData:
      prometheusType: Mimir
```

**Key notes:**
- Mimir datasource type is `prometheus` (not `mimir`), pointed at `http://mimir:9009/prometheus` — Mimir exposes a Prometheus-compatible API at that subpath. No `X-Scope-OrgID` header needed (D-26: multitenancy off).
- No `basicAuth` fields needed for any datasource — all backends are auth-disabled on the `telemetron` bridge network.
- `editable: false` prevents operators from accidentally breaking provisioned datasources via UI.

**CONFIRMED from Grafana devenv datasources.yaml (official source):** The `tracesToLogsV2` block lives under `jsonData:` (not top-level). The `tags` array uses `{ key, value }` objects where `key` is the OTel span attribute name and `value` is the Loki label name. The `query` field uses `${__tags}` and `${__span.traceId}` substitution markers.

#### Dashboard Provisioning Schema (UI-03)

**File location in container:** `/etc/grafana/provisioning/dashboards/dashboards.yaml`
**Template name:** `roles/grafana/templates/dashboards.yml.j2`

```yaml
apiVersion: 1

providers:
  - name: telemetron
    type: file
    folder: Telemetron
    disableDeletion: true
    updateIntervalSeconds: 30
    allowUiUpdates: false
    options:
      path: /etc/grafana/provisioning/dashboards/telemetron

  - name: operator
    type: file
    folder: Operator
    disableDeletion: false
    updateIntervalSeconds: 60
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/operator
```

**Behavior notes:**
- `updateIntervalSeconds: 30` means Grafana polls the directory every 30s and hot-reloads JSON changes without restart.
- `disableDeletion: true` on the `telemetron` provider prevents accidental panel deletion from being written back to the provisioned JSON.
- `allowUiUpdates: false` on `telemetron` prevents UI edits from persisting; the JSON files are authoritative.
- `allowUiUpdates: true` on `operator` lets operators iterate on their own dashboards via UI and then save the JSON back out.
- Both providers use **file** type (not `file` type with `foldersFromFilesStructure` — that would create subfolders from subdirectories, which we don't want).
- Grafana creates the folders (`Telemetron`, `Operator`) automatically from the `folder:` key; no API call or pre-creation needed.

#### Grafana grafana.ini Template
The role uses Jinja template `templates/grafana.ini.j2`. Minimal sections needed:

```ini
[paths]
data = /var/lib/grafana
logs = /var/log/grafana
plugins = /var/lib/grafana/plugins
provisioning = /etc/grafana/provisioning

[server]
http_port = 3000
http_addr = 0.0.0.0

[database]
type = sqlite3
path = grafana.db

[security]
; admin_user, admin_password, admin_email set via GF_ env vars at first boot

[users]
default_theme = dark

[auth.anonymous]
enabled = {{ grafana_anonymous_enabled | default(false) | string | lower }}
org_role = Viewer
org_name = Main Org.
```

**Recommendation:** Use env vars for security settings (GF_SECURITY_*) rather than ini — env vars are the Grafana-documented approach for container deployments and avoid the "ini file vs env var precedence confusion" surface. The ini file covers structural config (paths, ports, database type, anonymous auth).

---

### 2.2 Karma (`ghcr.io/prymitive/karma:v0.130`)

#### Container Identity
- Internal port: **8080** (Karma config `listen.port: 8080` default, confirmed from CONFIGURATION.md)
- Host port: 8082 (per D-84)
- Entrypoint: `/karma` (binary, confirmed from Dockerfile)
- No CMD — binary runs directly from ENTRYPOINT

#### Image HEALTHCHECK
**CONFIRMED: Karma v0.130 Dockerfile has NO HEALTHCHECK directive.**

```yaml
# In defaults/main.yml
karma_healthcheck_enabled: true
karma_healthcheck_test: ["CMD-SHELL", "wget --spider -q http://localhost:8080/health || exit 1"]
karma_healthcheck_interval: 15s
karma_healthcheck_timeout: 5s
karma_healthcheck_retries: 5
karma_healthcheck_start_period: 30s
```

**CONFIRMED: Karma exposes `/health` endpoint** (confirmed from source: `router.Get(getViewURL("/health"), pong)`). Returns HTTP 200 when ready.

#### Config File Location
Karma reads config from (in priority order):
1. `--config.file` CLI flag
2. `CONFIG_FILE` environment variable
3. `karma.yaml` in current working directory (CWD = `/` in distroless-like image)

**Recommendation:** Use `CONFIG_FILE` env var to point at `/etc/karma/karma.yaml`. This matches the upstream INSPQ pattern and avoids needing to know the binary's working directory.

```yaml
env:
  TZ: "{{ karma_tz }}"
  CONFIG_FILE: /etc/karma/karma.yaml
```

#### karma.yaml Schema (minimum + recommended knobs)
```yaml
alertmanager:
  servers:
    - name: "{{ karma_alertmanager_name | default('telemetron') }}"
      uri: "http://alertmanager:{{ karma_alertmanager_port | default(9093) }}"
      proxy: true

alertAcknowledgement:
  enabled: true
  duration: "{{ karma_ack_duration | default('1h') }}"
  author: "{{ karma_ack_author | default('karma') }}"
  comment: "Acknowledged via Karma [%NOW%]"

ui:
  refresh: "{{ karma_ui_refresh | default('30s') }}"
  minimalGroupWidth: 420
  collapseGroups: collapsedOnMobile
  theme: auto

{% if karma_default_filters | length > 0 %}
filters:
  default:
{% for f in karma_default_filters | sort %}
    - "{{ f }}"
{% endfor %}
{% endif %}
```

**Inventory-exposed knobs (planner decides exact list):**
- `karma_alertmanager_name` (default: `telemetron`)
- `karma_alertmanager_port` (default: `9093`)
- `karma_ack_duration` (default: `1h`)
- `karma_ack_author` (default: `karma`)
- `karma_ui_refresh` (default: `30s`)
- `karma_default_filters` (default: `[]`)
- `karma_labels_keep` (default: `[]`)

**`external_uri` note:** Karma 0.130 supports `external_uri` in the alertmanager server block for when a reverse proxy changes the visible URL. Surface as `karma_alertmanager_external_uri` with empty default — omit from rendered YAML if empty (Jinja conditional).

**Alertmanager v2 API compatibility:** Karma 0.130 + Alertmanager 0.32.1 — confirmed compatible. Karma autodetects the Alertmanager API version. No explicit version pin needed in karma.yaml.

#### Gate 8 / bind-mount pattern for Karma
```yaml
mounts:
  - source: "{{ karma_config_dir }}"   # /opt/telemetron/karma
    target: /etc/karma
    type: bind
    read_only: true
```
Host `/opt/telemetron/karma/karma.yaml` → container `/etc/karma/karma.yaml`. CONFIG_FILE env var set to `/etc/karma/karma.yaml`.

---

### 2.3 PromLens (`prom/promlens:v0.3.0`)

#### Container Identity
- Internal port: **8080** (EXPOSE 8080 in Dockerfile, confirmed)
- Host port: 8081 (per D-84)
- Entrypoint: `/bin/promlens`
- Base: busybox-based, runs as user `nobody` (confirmed from Dockerfile analysis)

#### Image HEALTHCHECK
**CONFIRMED: prom/promlens:v0.3.0 Dockerfile has NO HEALTHCHECK directive.**

```yaml
# In defaults/main.yml
promlens_healthcheck_enabled: true
promlens_healthcheck_test: ["CMD-SHELL", "wget --spider -q http://localhost:8080 || exit 1"]
promlens_healthcheck_interval: 30s
promlens_healthcheck_timeout: 5s
promlens_healthcheck_retries: 3
promlens_healthcheck_start_period: 15s
```

The `/` root path returns the PromLens UI (HTTP 200). No dedicated `/health` endpoint confirmed; root is the readiness signal.

#### CLI Flags Only (no env var support for most settings)
PromLens v0.3.0 uses CLI flags via kingpin. **No `PROMLENS_DEFAULT_BACKEND_URL` env var exists** — the flag is `--web.default-prometheus-url`. The only env var confirmed is `PROMLENS_SHARED_LINKS_DSN` (for SQL link sharing, irrelevant for M1).

```yaml
# Correct approach: use command: flags, not env vars
command:
  - "--web.default-prometheus-url=http://prometheus:{{ prometheus_http_port | default(9090) }}"
  - "--web.listen-address=:8080"
  # Optional: Grafana integration (omit for M1 minimal config)
  # - "--grafana.url=http://grafana:3000"
  # - "--grafana.api-token={{ grafana_api_token }}"
```

**`PROMLENS_GRAFANA_URL` does not exist as an env var** — the Grafana integration uses `--grafana.url` CLI flag and `--grafana.api-token` (or `--grafana.api-token-file`). For M1, skip Grafana integration in PromLens — it requires a Grafana service account token that adds complexity for a deprecation-candidate role.

**Knobs to expose:**
- `promlens_prometheus_url` (default: `http://prometheus:9090`)

**No volume needed** — PromLens is stateless for M1 (no shared links SQLite configured).

**No config dir needed** — PromLens reads only CLI flags. `/opt/telemetron/promlens/` directory can be created (for Gate 8 compliance and future config), but no bind-mount is needed unless shared-links SQLite is enabled.

#### Image pull durability
`prom/promlens:v0.3.0` was released 2022-12-05. The image is still pullable from Docker Hub as of research date (2026-05-19). For true air-gap durability, document the image SHA in the role README and recommend `docker pull` + local registry mirroring. The image may eventually be archived — this is part of the deprecation story.

---

## 3. Dashboard Sourcing Inventory

All 7 dashboards for `roles/grafana/files/dashboards/`. D-74: no runtime download; all committed at fork time.

| # | Target filename | Source | Tag/Revision | Raw URL for fork-time download | UID substitution needed |
|---|----------------|--------|-------------|-------------------------------|------------------------|
| 1 | `host-health.json` | Grafana.com community ID 1860, revision 45 | Rev 45 (2026-05-19 latest) | `https://grafana.com/api/dashboards/1860/revisions/45/download` | Replace `${ds_prometheus}` template var → hardcoded `prometheus` UID |
| 2 | `loki-explore-landing.json` | Hand-rolled stub | n/a — create from scratch | n/a | n/a — hand-written with `loki` UID directly |
| 3 | `tempo-explore-landing.json` | Hand-rolled stub | n/a — create from scratch | n/a | n/a — hand-written with `tempo` UID directly |
| 4 | `otel-collector-self-metrics.json` | Grafana.com community ID 15983, revision 29 | Rev 29 (downloads: 2.75M, confirmed current) | `https://grafana.com/api/dashboards/15983/revisions/29/download` | Replace `${datasource}` template var → hardcoded `prometheus` UID |
| 5 | `loki-self-metrics.json` | grafana/loki repo, `production/loki-mixin/dashboards/dashboard-loki-operational.json` | tag `v3.7.2` | `https://raw.githubusercontent.com/grafana/loki/v3.7.2/production/loki-mixin/dashboards/dashboard-loki-operational.json` | Replace string `"$datasource"` → `{"type":"prometheus","uid":"prometheus"}` AND `"$loki_datasource"` → `{"type":"loki","uid":"loki"}` (sed replacement — NO template vars exist in this file) |
| 6 | `tempo-self-metrics.json` | grafana/tempo repo, `operations/tempo-mixin/dashboards/tempo-operational.json` | tag `v2.10.5` | `https://raw.githubusercontent.com/grafana/tempo/v2.10.5/operations/tempo-mixin/dashboards/tempo-operational.json` | Replace template var `$ds` → `{"type":"prometheus","uid":"prometheus"}` AND `$logsds` → `{"type":"loki","uid":"loki"}` (proper Grafana template vars — replace both in `templating.list` and in all panel `datasource.uid` references) |
| 7 | `mimir-self-metrics.json` | grafana/mimir repo, `operations/mimir-mixin-compiled/dashboards/mimir-overview.json` | tag `mimir-3.0.6` | `https://raw.githubusercontent.com/grafana/mimir/mimir-3.0.6/operations/mimir-mixin-compiled/dashboards/mimir-overview.json` | Replace template var `$datasource` → `{"type":"prometheus","uid":"mimir"}` — Mimir's own metrics are queried via Prometheus protocol against Mimir's `/prometheus` path. Grafana datasource UID `mimir` points there. |

### UID Substitution Procedure Per Dashboard Type

**Type A — Template variable datasources (node-exporter, otel, tempo, mimir):**
These dashboards have proper Grafana templating variables (`type: datasource`). To hardcode:
1. Remove the datasource variable from `templating.list`
2. Replace `{"uid": "${ds_prometheus}"}` (or `${datasource}`, `${ds}`) in every panel target/datasource with `{"type": "prometheus", "uid": "prometheus"}` (or `"mimir"` for Mimir dashboards)

**Type B — Raw string references (loki-operational):**
The Loki operational dashboard was generated from jsonnet with string substitution, leaving literal `"$datasource"` and `"$loki_datasource"` strings (no templating vars defined). Sed-replace these strings directly:
```bash
# During fork-time preparation (document in plan task)
sed -e 's/"$datasource"/{"type":"prometheus","uid":"prometheus"}/g' \
    -e 's/"$loki_datasource"/{"type":"loki","uid":"loki"}/g' \
    dashboard-loki-operational.json > loki-self-metrics.json
```

### Hand-Rolled Landing Page Shape (for loki-explore-landing.json, tempo-explore-landing.json)

Minimal JSON structure for a text-panel nav dashboard in Grafana 13:

```json
{
  "title": "Loki — Explore Landing",
  "uid": "telemetron-loki-explore",
  "schemaVersion": 39,
  "version": 1,
  "panels": [
    {
      "type": "text",
      "title": "Quick Links",
      "gridPos": { "h": 8, "w": 24, "x": 0, "y": 0 },
      "datasource": { "type": "datasource", "uid": "-- Grafana --" },
      "options": {
        "mode": "markdown",
        "content": "## Log Explorer\n\n[Open Loki Explore](/explore?orgId=1&left=%7B%22datasource%22%3A%22loki%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22expr%22%3A%22%7Bservice_name%3D~%22.%2B%22%7D%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%22now-1h%22%2C%22to%22%3A%22now%22%7D%7D)\n\nFilters for common streams:\n- `{service_name=\"telemetron-grafana\"}`\n- `{service_name=\"telemetron-loki\"}`\n- `{job=\"telemetron\"}`"
      }
    }
  ],
  "templating": { "list": [] },
  "time": { "from": "now-1h", "to": "now" },
  "timepicker": {},
  "refresh": "",
  "timezone": "browser",
  "tags": ["telemetron"]
}
```

The Explore link URL-encodes a Grafana Explore state. For Tempo landing, replace datasource with `tempo` and query with a Tempo search.

---

## 4. Trace-to-Logs Deep Dive

### Confirmed: trace_id lands as structured metadata via OTLP path

**The pipeline:** App → OTel SDK → OTel Collector `:4318` → `otlphttp/loki` exporter → `http://loki:3100/otlp`

**What Loki 3.7.2 does with OTLP LogRecords:**
- `LogRecord.Body` → log line content
- `LogRecord.TimeUnixNano` / `LogRecord.ObservedTimestamp` → timestamp
- **Everything else** (including `trace_id`, `span_id`, `trace_flags`, all LogRecord attributes) → **structured metadata**
- Resource attributes → stream labels (17 default resource attributes promoted to labels, configurable via `distributor.otlp_config.default_resource_attributes_as_index_labels`); `service.name` → `service_name` label

**Confirmed from Loki docs:** "The log fields SpanID and TraceId are stored as `metadata[span_id]` and `metadata[trace_id]`." This means trace_id is available as structured metadata under the key `trace_id`.

**CONFIRMED: Phase 3 OTel config already wires this path** (`opentelemetry_loki_endpoint: "http://loki:3100/otlp"`). No changes needed to the OTel config for trace correlation to work.

### tracesToLogsV2 YAML (Tempo datasource jsonData — D-79 verbatim, confirmed correct)

```yaml
# In roles/grafana/templates/datasources/tempo.yaml.j2
jsonData:
  tracesToLogsV2:
    datasourceUid: loki
    spanStartTimeShift: '-1h'
    spanEndTimeShift: '1h'
    tags:
      - key: 'service.name'
        value: 'service_name'
    filterByTraceID: false
    filterBySpanID: false
    customQuery: true
    query: '{${__tags}} | trace_id="${__span.traceId}"'
```

**Confirmed from Grafana devenv official datasources.yaml:** The block lives under `jsonData:`. The `customQuery: true` + `query:` pattern confirmed. `${__tags}` expands to the stream label filter derived from the `tags` array (e.g., `{service_name="myapp"}`). `${__span.traceId}` is substituted with the actual trace ID from the clicked span.

**The query this generates at click-time:** `{service_name="myapp"} | trace_id="abc123def456..."`

### derivedFields YAML (Loki datasource jsonData — D-79 verbatim, confirmed correct)

```yaml
# In roles/grafana/templates/datasources/loki.yaml.j2
jsonData:
  derivedFields:
    - name: trace_id
      matcherType: label
      matcherRegex: trace_id
      url: '${__value.raw}'
      datasourceUid: tempo
      urlDisplayLabel: 'View in Tempo'
```

**matcherType: label with structured metadata:** CONFIRMED. Grafana's Loki documentation explicitly states: "A label from the selected log line. This can be any type of label - indexed, parsed or **structured metadata**." The `matcherType: label` matches against Loki's unified label surface which includes structured metadata fields. For `matcherType: label`, `matcherRegex` holds the exact field name (not a regex — the naming is misleading in the TypeScript type definition).

**url: `${__value.raw}`:** When an internal link is configured (`datasourceUid: tempo`), this value is the trace ID extracted from the structured metadata field, passed as a Tempo query parameter. Grafana constructs the Tempo Explore URL with the trace ID.

### Live path verification status
- **OTel → Loki via otlphttp/loki:** WIRED (Phase 3, confirmed from roles/opentelemetry/defaults/main.yml)
- **trace_id in structured metadata:** CONFIRMED (Loki 3.x OTLP native ingestion, multiple sources)
- **matcherType: label for structured metadata:** CONFIRMED (Grafana docs explicit statement)
- **D-79 query syntax:** CONFIRMED (Grafana official devenv example uses identical customQuery pattern)

**Caveat (D-78):** Fluent Bit-tailed Docker stdout/stderr logs do NOT carry trace_id. FB logs land on Loki via `otlphttp/loki` too (same path), but the log records don't carry OTLP trace context because FB doesn't extract it from stdout text. Only logs from OTel-SDK-instrumented apps that push OTLP-native logs will have trace_id in structured metadata.

---

## 5. Gate 9 Verify Implementation

Gate 9 (D-73): datasources-resolve-real-data. Added to `roles/README.md` by plan 05-01.

### Step pattern: in-network curlimages/curl one-shot per assertion

**Auth:** Grafana API requires Basic Auth with admin credentials. The verify container uses `{{ grafana_admin_password }}` from inventory. Use `-u admin:{{ grafana_admin_password }}` in curl commands. Note: since GF_SECURITY_ADMIN_PASSWORD is first-boot-only, the password stored in Grafana's SQLite matches whatever was set on first boot.

### Datasource health checks (Step 1 — structural)

```bash
# For each UID: prometheus, loki, tempo, mimir
curl -fsS -u admin:{{ grafana_admin_password }} \
  http://grafana:3000/api/datasources/uid/prometheus/health
# Returns: {"message":"Data source connected and labels found.","status":"OK"}
# or similar 200 JSON with "status":"OK"

# Repeat for loki, tempo, mimir
```

The `/api/datasources/uid/<uid>/health` endpoint was introduced in Grafana 9. It makes a test query against the backend and returns the backend's health status. Returns HTTP 200 + JSON `{"status":"OK"}` on success, 400/500 on failure.

### Canonical queries (Step 2 — data present)

**Prometheus (UID: prometheus):**
```bash
curl -fsS -u admin:{{ grafana_admin_password }} \
  'http://grafana:3000/api/datasources/proxy/uid/prometheus/api/v1/query?query=up' \
  | grep -q '"result":\[{' || { echo "prometheus no data"; exit 1; }
```
Expects: JSON with non-empty `data.result` array.

**Loki (UID: loki):**
```bash
curl -fsS -u admin:{{ grafana_admin_password }} \
  'http://grafana:3000/api/datasources/proxy/uid/loki/loki/api/v1/query?query=%7Bjob%3D~%22.%2B%22%7D' \
  | grep -q '"status":"success"' || { echo "loki no data"; exit 1; }
```
Query is URL-encoded `{job=~".+"}`. Even with no log streams yet, status:"success" with empty streams is acceptable — the proxy successfully reached Loki. For a stronger assertion, check `result` is non-empty.

**Tempo (UID: tempo):**
```bash
curl -fsS -u admin:{{ grafana_admin_password }} \
  'http://grafana:3000/api/datasources/proxy/uid/tempo/api/search?limit=1' \
  | grep -qE '"traces":\[|"results":\[' || { echo "tempo no data"; exit 1; }
```
Tempo's `/api/search` returns `{"traces":[], ...}` or `{"results":[], ...}` even with no traces. A 200 response confirms the proxy reaches Tempo. For fresh deploys with no synthetic traces yet, an empty array is acceptable per D-73 ("expect at least one trace OR explicit 'no traces yet' stable state").

**Mimir (UID: mimir):**
```bash
curl -fsS -u admin:{{ grafana_admin_password }} \
  'http://grafana:3000/api/datasources/proxy/uid/mimir/prometheus/api/v1/query?query=up' \
  | grep -q '"result":\[{' || { echo "mimir no data"; exit 1; }
```
Same pattern as Prometheus; proxy path routes through Mimir datasource to `mimir:9009/prometheus/api/v1/query`.

### In-network container pattern (reusing D-54/D-69 shape)

```yaml
- name: Gate 9 — datasource health check ({{ item }})
  community.docker.docker_container:
    name: "telemetron-grafana-verify-{{ item }}"
    image: "{{ grafana_curl_image }}:{{ grafana_curl_image_tag }}"
    state: started
    detach: false
    auto_remove: true
    recreate: true
    cleanup: true
    networks:
      - name: "{{ grafana_network }}"
    entrypoint: ["/bin/sh", "-c"]
    command:
      - >-
        curl -fsS -u admin:{{ grafana_admin_password }}
        http://telemetron-grafana:3000/api/datasources/uid/{{ item }}/health
        | grep -q '"status":"OK"'
        || { echo "datasource {{ item }} health FAIL"; exit 1; }
  changed_when: false
  loop:
    - prometheus
    - loki
    - tempo
    - mimir
```

---

## 6. INSPQ Upstream Audit

### 6.1 roles/grafana (INSPQ source: ~/git/inspq/ansible/grafana/)

**FR-language artifacts — ALL task `name:` strings must be replaced:**
- `"Déployer Grafana en docker"` → `"Deploy Grafana container"`
- `"Gérer les répertoire de données et de configuration"` → `"Ensure Grafana config and data directories exist"`
- `"Créer le fichier de config grafana vierge"` → `"Initialize grafana.ini config file"`
- `"Ajouter la config de SMTP dans le grafana.ini"` → (DROP — no SMTP in M1)
- `"Configurer le thème et le nom d'organisation dans le grafana.ini"` → handled by GF_ env vars
- `"Ajouter les datasources prometheus sans headers à grafana"` → (DROP — replaced by file provisioning)
- `"Ajouter les tableaux de bord à grafana"` → (DROP — replaced by file provisioning)
- `"Attendre que Grafana soit disponible"` → (DROP — replaced by HEALTHCHECK poll D-10a)
- All other French task names → translate to English

**INSPQ-specific artifacts to DROP entirely:**

| Artifact | Location | Treatment |
|----------|----------|-----------|
| `grafana_timezone: America/Toronto` | defaults/main.yml | DROP — use `Etc/UTC` via `telemetron_tz` |
| SMTP configuration (`from_address: {{ ansible_hostname }}@inspq.qc.ca`) | tasks/docker.yml line 33 | DROP entirely — no SMTP in M1 |
| `grafana_smtp_server` / `grafana_smtp_port` / `grafana_smtp_from` vars | defaults | DROP |
| LDAP configuration block | tasks/docker.yml | DROP entire block |
| `files/ldap.toml` | files/ | DROP — contains `host = "inspq.qc.ca"`, `dc=inspq,dc=qc,dc=ca`, INSPQ AD group DNs |
| `grafana_ldap_enabled: false` default | defaults | DROP — LDAP is post-M1 per D-88 |
| `grafana_ldap_server`, `grafana_ldap_port`, `grafana_ldap_bind_*`, `grafana_ldap_search_filter`, `grafana_ldap_base_dns` vars | defaults | DROP |
| `community.grafana.grafana_datasource` module usage | tasks/grafana_datasources.yml | DROP — replaced by file provisioning |
| `community.grafana.grafana_folder` module usage | tasks/grafana_dashboards.yml | DROP — replaced by file provisioning |
| `grafana_dashboard_tmp_dest_dir: "/tmp/grafana-dashboards"` | defaults | DROP |
| `grafana_datasources_prometheus`, `grafana_datasources_loki`, `grafana_datasources_tempo`, `grafana_datasources_alertmanager` vars | defaults | DROP — replaced by static provisioning |
| `grafana_dashboards: []` var | defaults | DROP — replaced by static provisioning |
| `application_web_docker` role dependency | tasks/docker.yml | DROP — Telemetron dropped this shared role per D-01 |
| `grafana_docker_image_name: "grafana/grafana"` (without -oss) | defaults | REPLACE with `grafana/grafana-oss:13.0.1` |
| `grafana_docker_image_version: "latest"` | defaults | REPLACE with pinned `13.0.1` |
| `grafana_docker_restart_policy: always` | defaults | REPLACE with `unless-stopped` |
| Kubernetes/Helm deployment tasks | tasks/ | DROP entirely |
| `grafana_plugins: ["grafana-lokiexplore-app@1.0.41"]` | defaults | DROP — no plugin installation in M1 |
| `grafana_plugins_tls_skip_verify: true` | defaults | DROP |
| Helm chart vars (`grafana_helm_chart_*`) | defaults | DROP |
| `GF_AUTH_LDAP_ENABLED` env var injection | vars/main.yml | DROP |
| `GF_PLUGINS_PREINSTALL` env var injection | vars/main.yml | DROP |

**Features worth preserving (normalized):**
- `grafana_admin_user` / `grafana_admin_password` knobs → keep, rename per D-86/D-88 naming
- `grafana_default_theme: dark` → keep as `grafana_default_theme: dark` (GF_USERS_DEFAULT_THEME env)
- General container env var injection pattern → keep, cleaned up

**D-25 headline deviation:** Upstream used `community.grafana.grafana_datasource` API calls + `community.grafana.grafana_folder` for dashboard management, making provisioning dependent on a running Grafana API. Telemetron replaces this with **file-based provisioning** (datasources.yaml + dashboards.yaml under `/etc/grafana/provisioning/`) — simpler, idempotent, no race condition with Grafana startup, survives `docker volume rm`. This is the most significant D-25 improvement for this role.

---

### 6.2 roles/karma (INSPQ source: ~/git/inspq/ansible/karma/)

**FR-language artifacts:**
- `karma_container_env: {TZ: "America/Toronto"}` → REPLACE with `Etc/UTC`
- README.md line 33: `TZ: "America/Toronto"` → replace in ported README
- README.md line 45: `karma_alertmanager_uri: "https://alertmanager.inspq.qc.ca"` → replace with `http://alertmanager:9093`
- Task names (partial FR): `"Assurer que le repertoire..."` → `"Ensure karma config directory exists"`, `"Faire le menage si demande"` → DROP (no state=absent in M1)
- `"Telecharger le latest si specifie"` → DROP (pinned tag, not latest)
- `"Televerser le template de configuration karma"` → `"Render karma.yaml config"`
- `"Regler la variable image_updated si latest"` → DROP

**INSPQ-specific artifacts to DROP:**
- `karma_alertmanager_uri: "http://localhost:9093"` → REPLACE with `http://alertmanager:9093` (Docker bridge DNS)
- `karma_alertmanager_name: "alertmanager"` → REPLACE with `telemetron` (clearer)
- `karma_image_version: "v0.128"` → REPLACE with `v0.130`
- `karma_image_name: "ghcr.io/prymitive/karma"` → KEEP (correct GHCR image, not the Docker Hub fork) — this is the one INSPQ artifact that's already correct
- `karma_port: 8080` (external port) → REPLACE with `8082` per D-84
- `application_web_docker` role dependency → DROP
- `application_web_docker_apache_enabled: false` → DROP
- `application_web_docker_otel_sdk_disabled: true` → DROP
- Single-file bind-mount `"{{ karma_config_dir }}/karma.yaml:/etc/karma/karma.yaml"` → REPLACE with parent-directory mount per Gate 8
- `karma_state: present` / `docker_cleanup.yml` / `state: absent` pattern → DROP
- `karma_image_pull: default(True)` + latest-pull logic → DROP (pinned tag)

**Features worth preserving:**
- `karma.yaml.j2` template structure → keep and extend (it's clean; the Jinja is already English)
- `alertAcknowledgement` block → keep (genuinely useful for homelab alert management)
- `karma_default_filters`, `karma_labels_keep` knobs → keep (filtered via `|sort` per D-20)
- `karma_ack_duration`, `karma_ack_author` knobs → keep

**D-25 headline deviation:** Upstream had `karma_alertmanager_uri: "http://localhost:9093"` (localhost reference — requires the Karma container to be on host network). Telemetron uses Docker bridge DNS: `http://alertmanager:9093`. Also: upstream used `application_web_docker` shared role abstraction; Telemetron uses `community.docker.docker_container` directly (D-01 / D-06).

---

### 6.3 roles/promlens (INSPQ source: ~/git/inspq/ansible/promlens/)

**FR-language artifacts:**
- `promlens_container_env: {TZ: "America/Toronto"}` → REPLACE with `Etc/UTC`
- Task names: `"Configurer le service account Grafana"` → DROP (Grafana service account for PromLens link-sharing not in M1), `"Déployer Promlens en docker"` → `"Deploy PromLens container"`, `"Configurer les commandes du conteneur"` → handled inline in docker_container task, `"Téléverser le template"` → DROP (no config file needed for M1), `"Télécharger le latest..."` → DROP, `"Regler la variable image_updated..."` → DROP
- Kubernetes task comments (FR) → DROP

**INSPQ-specific artifacts to DROP:**
- `promlens_image_version: "latest"` → REPLACE with `v0.3.0`
- `promlens_port: 8086` (INSPQ used 8086) → REPLACE with `8081` per D-84
- `promlens_grafana_api_token_name: "promlens"` + Grafana service account setup → DROP (complexity not worth it for a deprecation-candidate)
- `promlens_grafana_url` / `promlens_grafana_admin_username` / `promlens_grafana_admin_password` → DROP
- `templates/docker/promlens.yml.j2` (YAML config for link sharing SQLite) → DROP (no shared links in M1)
- `application_web_docker` role dependency → DROP
- `state: absent` / cleanup logic → DROP
- `--shared-links.sql.driver=sqlite` + `--grafana.url` + `--grafana.api-token` CLI flags in upstream command → DROP

**Features worth preserving:**
- `promlens_prometheus_url` var → keep (maps to `--web.default-prometheus-url` CLI flag)

**D-25 headline deviation:** Upstream set up a Grafana service account to enable cross-linking from PromLens back to Grafana. Telemetron drops this — PromLens is a deprecation candidate; the Grafana integration requires a service account token that adds secrets surface for no M1 value. The M1 PromLens role is purely the Prometheus URL endpoint with a deprecation banner.

---

## 7. Pitfalls and Risks

### Top-3 Risks for Phase 5

**Risk 1 (HIGHEST): Dashboard datasource UID template-variable substitution in upstream mixin JSONs**

What can go wrong: The planner commits dashboard JSONs with `$datasource`, `$ds`, or template variables still intact. On a fresh Grafana install, dashboards render empty panels with "Datasource not found" errors. This is Pitfall 2 from PITFALLS.md — the exact failure mode this phase must prevent.

The challenge: Each upstream dashboard has a DIFFERENT substitution approach:
- Loki operational: raw string `"$datasource"` (no template vars — sed-replace required)
- Tempo operational: proper template vars `$ds` / `$logsds` (remove from templating.list, replace uid refs)
- Mimir overview: proper template var `$datasource` (remove from templating.list, replace uid refs)
- Node exporter: proper template var `$ds_prometheus` (remove from templating.list, replace uid refs)
- OTel collector: proper template var `${datasource}` (remove from templating.list, replace uid refs)

The planner must explicitly task the preparation of each JSON file, not just "copy from upstream."

**Risk 2 (HIGH): GF_SECURITY_ADMIN_PASSWORD first-boot-only behavior misunderstood**

What can go wrong: Operator assumes they can rotate `grafana_admin_password` in inventory, re-run the playbook, and the password updates in Grafana. It doesn't — Grafana ignores the env var on subsequent boots (password is in SQLite). The operator is then locked out if they change the inventory value without updating Grafana's stored password.

Mitigation: Explicitly document in `roles/grafana/README.md` "Secrets" section: "Grafana reads `GF_SECURITY_ADMIN_PASSWORD` on first boot only. To reset the password after initial deploy: `docker exec telemetron-grafana grafana-cli admin reset-admin-password <newpass>`"

**Risk 3 (MEDIUM): No HEALTHCHECK in any Phase-5 image — easy to accidentally omit**

Grafana, Karma, and PromLens all ship without a Docker HEALTHCHECK. All three require explicit `healthcheck:` declarations in their `docker_container` tasks. If the planner forgets even one (easy to do since Phase 1-4 roles sometimes used image-native healthchecks), Gate 5 will fail. The planner should treat "explicit HEALTHCHECK required" as a checklist item for all three roles.

### Additional Pitfalls (from question 13)

**Hardcoded UIDs in dashboard JSON (D-77 — already covered above):**
The gotcha is that upstream mixin dashboards use variable datasource references — the variable name/style differs per dashboard. The find-and-replace pattern is not uniform. Validate each dashboard loads in Grafana after substitution.

**Datasource provisioning order:** Grafana provisions datasources before dashboards (alphabetically within `/etc/grafana/provisioning/datasources/`, then `/etc/grafana/provisioning/dashboards/`). In practice, since both happen before serving traffic, this is not a race issue. Confirmed: datasources are loaded at startup before the HTTP server opens for dashboard API requests.

**Anonymous viewer + dashboards in folders:** `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer` grants read-only access to all resources in the default org, including dashboards in provisioned folders (Telemetron, Operator). No explicit folder permission grants needed. Confirmed from Grafana auth docs.

**PromLens CLI flag (not env var) for Prometheus URL:** The INSPQ upstream used CLI command args (`--web.default-prometheus-url`); `PROMLENS_DEFAULT_BACKEND_URL` does NOT exist. The planner must use `command:` in the `docker_container` task, not `env:`. Confirmed from source code analysis of v0.3.0 `cmd/promlens/main.go`.

**Karma CONFIG_FILE env var required:** Karma's default config search path is `karma.yaml` in the working directory. The container's working directory is `/` (distroless-like). Since we mount config at `/etc/karma/karma.yaml` (parent-dir mount per Gate 8), we MUST set `CONFIG_FILE=/etc/karma/karma.yaml` in the container environment. Without this, Karma won't find the config and will start with empty defaults (no alertmanager configured).

**Grafana container UID — do NOT set `user:`:** Grafana OSS 13.0.1 runs as UID 472 (the `GF_UID` build arg). Setting `user: "472:472"` in `docker_container` would work, but explicitly setting a different UID causes "permission denied" on `/var/lib/grafana`. Best practice: omit `user:` entirely and let the image default apply (same pattern as Mimir runs as 0:0, Loki/Tempo run as 10001:10001 — each image has its own expected UID).

**PromLens image SHA pin for air-gap:** `prom/promlens:v0.3.0` is currently pullable but may eventually be archived. Document SHA in README: `prom/promlens@sha256:<hash>` for operators running air-gapped. The plan should note this as a README documentation task.

**Karma alertmanager hostname:** INSPQ used `http://localhost:9093` (host-network deployment). Telemetron uses Docker bridge DNS: `http://alertmanager:9093`. This is a critical fix in D-25 audit — the Karma container cannot reach `localhost:9093` if it's on the bridge network.

---

## 8. Recommended Wave Assignment

**Recommendation: Wave 1 = grafana only; Wave 2 = karma + promlens (parallel)**

Rationale matching D-71:

- **Wave 1: plan 05-01 (grafana)** — Grafana is the de-facto end-to-end smoke test (ROADMAP.md Phase-5 goal). It needs to be running and datasources verified (Gate 9) before anything else is claimed "working." Grafana also introduces the only secret in Phase 5 (`grafana_admin_password`) and the only named volume (`telemetron_grafana_data`). Its verify step (Gate 9) validates that all prior phases (1-4) wired correctly. Time cost: ~2-3x longer than karma or promlens due to datasource provisioning + dashboard preparation + Gate 9 multi-step verify.

- **Wave 2: plans 05-02 (karma) + 05-03 (promlens) in parallel** — Both are simple container deployments with minimal config. Neither depends on Grafana being up (Karma reads from Alertmanager, PromLens reads from Prometheus). They can be planned, implemented, and committed in parallel. Combined they're roughly one Grafana-sized effort.

This is option (b) from the objective: Wave 1 = grafana, Wave 2 = karma + promlens (parallel). It matches D-71's "dependency-true order" while parallelizing the two low-stakes roles. Option (c) — sequential for all three — is unnecessary since Karma and PromLens genuinely have no inter-dependency.

**Playbook extension order (D-71):**
- After 05-01: `… → alertmanager → grafana`
- After 05-02: `… → alertmanager → grafana → karma`
- After 05-03: `… → alertmanager → grafana → karma → promlens`

---

## 9. Open Questions

**OQ-1: Loki operational dashboard datasource substitution — validate sed approach before committing**

The Loki operational dashboard uses raw string `"$datasource"` and `"$loki_datasource"` (confirmed: no template vars defined, no JSON objects). The sed replacement turns these strings into JSON objects inline. This is technically non-standard (replacing a string value with an object). The correct approach is to fully parse and rewrite the JSON:

```python
# Recommended: Python-based substitution rather than sed
import json, sys
d = json.load(open('dashboard-loki-operational.json'))
content = json.dumps(d)
content = content.replace('"$datasource"', '{"type":"prometheus","uid":"prometheus"}')
content = content.replace('"$loki_datasource"', '{"type":"loki","uid":"loki"}')
d = json.loads(content)
json.dump(d, open('loki-self-metrics.json', 'w'), indent=2)
```

**The planner should include an explicit task for JSON transformation** rather than expecting a simple file copy. The Loki dashboard is the most fragile of the 5 non-hand-rolled dashboards.

**OQ-2: Grafana `/api/datasources/uid/<uid>/health` exact response format per backend**

The research confirms this endpoint returns HTTP 200 + JSON with `"status":"OK"` on success. However, the exact message field varies by datasource type (Prometheus returns "Data source connected...", Loki returns "Data source connected and labels found.", Tempo may return differently, Mimir as Prometheus type returns the same as Prometheus). The Gate 9 verify should assert on `"status":"OK"` only (not message content) for robustness.

**OQ-3: Tempo `/api/search` proxy path through Grafana — confirm exact proxy URL**

The research suggests `http://grafana:3000/api/datasources/proxy/uid/tempo/api/search?limit=1`. However, Tempo's query API may have version-specific path differences. Planner should verify the proxy path during execution by checking the Grafana API documentation for the proxy endpoint format — it's consistently `POST /api/datasources/proxy/uid/<uid>/<backend-path>`. For Tempo's search, the backend path is `api/search`.

**OQ-4: Mimir overview dashboard — does `$datasource` template var reference `mimir` UID or `prometheus` UID?**

The Mimir overview dashboard uses Prometheus-type queries against Mimir's self-metrics (which it exposes at `:9009/metrics` as Prometheus format). The `$datasource` template variable queries against a Prometheus datasource. For Telemetron, Mimir's own metrics are scraped by Prometheus (via `prometheus_extra_scrape_configs` or direct scrape job). The Mimir overview dashboard should reference the `prometheus` UID (the Prometheus scraper that collects Mimir's self-metrics), NOT the `mimir` UID (the long-term metrics store). **Planner must verify this** by checking whether Prometheus already scrapes Mimir's `:9009/metrics` and whether the relevant Mimir metrics exist in the `prometheus` datasource.

**OQ-5: Grafana health verify timing — first-boot DB initialization**

The start_period of 60s should be sufficient, but on a fresh host where Grafana has never run, the SQLite database initialization adds a few seconds. The D-10a poll (30 retries × 2s = 60s total budget post-start_period) provides adequate buffer. However, if leviathan UAT shows first-boot takes longer than expected, the planner should bump `grafana_health_retries` to 45 (90s budget) to match the Mimir/Tempo pattern.

---

## Standard Stack (Phase 5 specific)

### Core Phase-5 Images
| Role | Image | Tag | Container Port | Host Port |
|------|-------|-----|---------------|-----------|
| grafana | `grafana/grafana-oss` | `13.0.1` | 3000 | 3000 |
| karma | `ghcr.io/prymitive/karma` | `v0.130` | 8080 | 8082 |
| promlens | `prom/promlens` | `v0.3.0` | 8080 | 8081 |

### Supporting Images (one-shot verify)
| Purpose | Image | Tag |
|---------|-------|-----|
| Gate 9 verify | `curlimages/curl` | `8.10.1` |

### Key Confirmed Facts

| Item | Finding | Confidence |
|------|---------|-----------|
| Grafana HEALTHCHECK | NOT in image — explicit required | HIGH (Dockerfile confirmed) |
| Karma HEALTHCHECK | NOT in image — explicit required | HIGH (Dockerfile confirmed) |
| PromLens HEALTHCHECK | NOT in image — explicit required | HIGH (Dockerfile confirmed) |
| Grafana container UID | 472 (GF_UID, group 0) — do not override | HIGH (Dockerfile confirmed) |
| GF_SECURITY_ADMIN_PASSWORD | First-boot only — does NOT update on restart | HIGH (docs + community confirmed) |
| Karma /health endpoint | EXISTS at :8080/health | HIGH (source confirmed) |
| Karma CONFIG_FILE env var | Required when config not at CWD | HIGH (source confirmed) |
| PromLens CLI flags only | `--web.default-prometheus-url` — no env var equivalent | HIGH (source confirmed) |
| trace_id in structured metadata | YES via Loki 3.x OTLP native ingestion | HIGH (multiple docs sources) |
| matcherType: label for structured metadata | YES — Grafana docs explicit | HIGH (docs confirmed) |
| Mimir pre-compiled JSON | YES at `mimir-mixin-compiled/dashboards/` at tag `mimir-3.0.6` | HIGH (verified via GitHub API) |
| Loki operational dashboard datasource vars | Raw strings "$datasource", "$loki_datasource" — Python rewrite needed | HIGH (parsed JSON confirmed) |
| Tempo operational dashboard datasource vars | Proper template vars `$ds`, `$logsds` — standard substitution | HIGH (parsed JSON confirmed) |

---

## Environment Availability

Phase 5 has no new external dependencies beyond Docker and Ansible (already available from Phases 1-4). The Phase-5 images are public Docker Hub / GHCR images. Verified on leviathan:

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|---------|
| Docker 29 | All containers | ✓ (leviathan, confirmed) | — |
| Ansible | Playbook | ✓ (leviathan, confirmed) | — |
| `grafana/grafana-oss:13.0.1` | UI-01 | Pull-on-deploy | — |
| `ghcr.io/prymitive/karma:v0.130` | UI-05 | Pull-on-deploy | — |
| `prom/promlens:v0.3.0` | UI-06 | Pull-on-deploy | — |
| `curlimages/curl:8.10.1` | Gate 9 verify | Already used in earlier phases | — |

---

## Validation Architecture

**Nyquist validation is disabled for this project** (`nyquist_validation_enabled` absent from config, treated as disabled per project convention). **Gate 9 (D-73) IS the Phase-5 dimension-8 acceptance evidence.** The planner should ensure plan 05-01 includes Gate 9 as its final verify step, covering all 4 datasource UIDs with the curl commands documented in §5 above.

The standard Gates 1-8 apply to all three roles (grafana, karma, promlens). Gate 9 applies to grafana only.

---

## Sources

### Primary (HIGH confidence)
- Grafana v13.0.1 Dockerfile — confirmed no HEALTHCHECK, UID 472, entrypoint /run.sh
  `https://github.com/grafana/grafana/blob/v13.0.1/Dockerfile`
- Grafana devenv datasources.yaml — confirmed tracesToLogsV2 schema under jsonData
  `https://raw.githubusercontent.com/grafana/grafana/refs/heads/main/devenv/datasources.yaml`
- Grafana defaults.ini v13.0.1 — confirmed SQLite default, admin_password "set once on first-run"
  `https://raw.githubusercontent.com/grafana/grafana/v13.0.1/conf/defaults.ini`
- Grafana Loki datasource TypeScript types — confirmed DerivedFieldConfig field names including matcherType
  `https://raw.githubusercontent.com/grafana/grafana/v13.0.1/public/app/plugins/datasource/loki/types.ts`
- Karma v0.130 config.go — confirmed CONFIG_FILE env var, karma.yaml default search path
  `https://raw.githubusercontent.com/prymitive/karma/v0.130/internal/config/config.go`
- Karma v0.130 main.go — confirmed /health endpoint, listen address pattern
  `https://raw.githubusercontent.com/prymitive/karma/v0.130/cmd/karma/main.go`
- Karma v0.130 Dockerfile — confirmed NO HEALTHCHECK, distroless-like image
- PromLens v0.3.0 cmd/promlens/main.go — confirmed CLI flags (`--web.default-prometheus-url`), NO PROMLENS_DEFAULT_BACKEND_URL env var, only PROMLENS_SHARED_LINKS_DSN
- PromLens Dockerfile — confirmed NO HEALTHCHECK, port 8080, entrypoint /bin/promlens
- GitHub API: grafana/loki v3.7.2 dashboard directory — confirms `dashboard-loki-operational.json` exists as pre-built JSON
- GitHub API: grafana/tempo v2.10.5 dashboard directory — confirms `tempo-operational.json` exists as pre-built JSON
- GitHub API: grafana/mimir mimir-3.0.6 — confirms `operations/mimir-mixin-compiled/dashboards/mimir-overview.json` exists at tag
- Grafana.com API: dashboard 1860 revision 45, dashboard 15983 revision 29 — confirmed current revisions

### Secondary (MEDIUM confidence)
- Grafana Loki docs: derivedFields label type works for structured metadata — "any type of label - indexed, parsed or structured metadata"
  `https://grafana.com/docs/grafana/latest/datasources/loki/configure-loki-data-source/`
- Multiple community sources confirming GF_SECURITY_ADMIN_PASSWORD is first-boot-only
  `https://community.grafana.com/t/admin-password-reset/19455`
- Grafana.com dashboard provisioning docs — updateIntervalSeconds behavior confirmed
  `https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards`
- Karma CONFIGURATION.md — alertmanager.servers schema, ui settings, /health endpoint docs
  `https://github.com/prymitive/karma/blob/main/docs/CONFIGURATION.md`
- Loki docs: trace_id and span_id stored as structured metadata[trace_id] and metadata[span_id]
  `https://grafana.com/docs/loki/latest/send-data/otel/`
- INSPQ grafana/karma/promlens role audit — direct code inspection (~/git/inspq/ansible/)
- Telemetron Phase 3 OTel config: `opentelemetry_loki_endpoint: "http://loki:3100/otlp"` confirmed from roles/opentelemetry/defaults/main.yml

### Tertiary (LOW confidence)
- Grafana anonymous viewer behavior with custom provisioned folders — not explicitly documented; inferred from standard Viewer role permissions model
- Exact Tempo proxy path format via Grafana API (`/api/datasources/proxy/uid/tempo/api/search`) — follows documented pattern but not tested against live Grafana 13

---

## Metadata

**Confidence breakdown:**
- Grafana provisioning schema: HIGH — confirmed from official devenv datasources.yaml
- HEALTHCHECK findings: HIGH — confirmed from Dockerfiles for all 3 images
- tracesToLogsV2 + derivedFields: HIGH — confirmed from devenv YAML + TypeScript types + Loki docs
- Karma config schema: HIGH — confirmed from CONFIGURATION.md + source code
- PromLens CLI flags: HIGH — confirmed from v0.3.0 source
- Dashboard sourcing: HIGH (sources exist at claimed paths) / MEDIUM (UID substitution behavior)
- INSPQ audit: HIGH — direct code inspection

**Research date:** 2026-05-19
**Valid until:** 2026-08-19 (stable ecosystem; 90-day window reasonable for these components)
