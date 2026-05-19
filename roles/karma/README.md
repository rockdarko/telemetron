# roles/karma

Deploys [Karma](https://github.com/prymitive/karma) v0.130 -- the operator alert triage UI -- on the `telemetron` Docker bridge network. Karma reads evaluated alerts from the Phase-4 Alertmanager at `http://alertmanager:9093` (Docker bridge DNS -- NOT `localhost`) via the Alertmanager v2 API, and displays them in a grid view at `http://<host>:8082`.

Image pin: `ghcr.io/prymitive/karma:v0.130` -- the GHCR official image (NOT the `lmierzwa/karma` Docker Hub fork, which is an unofficial community image and should not be used). Ships UI-05 from `.planning/REQUIREMENTS.md`.

## Karma is the M1 alert UX

In M1, Karma is your primary alert interface. Phase 4 Alertmanager ships with a `null` default receiver (D-60), so alerts are visible-not-actioned by default. Until you wire a real Alertmanager receiver (via `alertmanager_extra_receivers` in `inventory/example-homelab/group_vars/all/alertmanager.yml` -- Slack, PagerDuty, email, custom webhook), Karma's silence/ack UX is how you interact with the alert plane.

## What this role does

1. Creates `/opt/telemetron/karma/` on the host (D-18 flat config layout).
2. Renders `/opt/telemetron/karma/karma.yaml` from `templates/karma.yaml.j2`. The default config points at `http://alertmanager:9093` (the Phase-4 Alertmanager on the telemetron bridge), enables alert acknowledgement, and surfaces UI refresh / theme / group-width knobs.
3. Pulls `ghcr.io/prymitive/karma:v0.130` (GHCR official).
4. Starts the `telemetron-karma` container with:
   - Explicit `HEALTHCHECK` (`wget --spider -q http://localhost:8080/health`) -- the image ships no built-in healthcheck (RESEARCH §2.2 confirmed).
   - `CONFIG_FILE: /etc/karma/karma.yaml` env var -- required because Karma searches for `karma.yaml` in its working directory (`/`) by default; the env var points it at the parent-dir-mounted config file.
   - Parent-directory bind mount: `/opt/telemetron/karma -> /etc/karma` (Gate 8 convention; avoids moby/moby#6011 stale-inode class).
   - `org.telemetron.service=telemetron` / `org.telemetron.job=karma` labels (Gate 7).
   - Host port 8082 published by default (D-82 inverts D-30 for UI plane).
   - `restart_policy: unless-stopped` (OPS-06).
5. Runs the verify suite (`tasks/verify.yml`) -- D-10a HEALTHCHECK poll, `/health` curl probe, root-path HTML smoke, and Alertmanager-connection assertion (Karma's `/alerts.json` response contains the configured alertmanager source name `telemetron`).

## Variables

See `defaults/main.yml` for the full list. Most operators only tune the UI knobs and acknowledgement duration.

| Variable | Default | Purpose |
|----------|---------|---------|
| `karma_image` | `ghcr.io/prymitive/karma` | Image (GHCR official; do not change) |
| `karma_image_tag` | `v0.130` | Pinned tag (OPS-01) |
| `karma_container_name` | `telemetron-karma` | DNS name on the `telemetron` network |
| `karma_publish_host` | `true` | D-82: UI plane publishes by default. `true`/`false`/`127.0.0.1` |
| `karma_bind_address` | `0.0.0.0` | D-83: bind address for published port |
| `karma_http_port` | `8082` | D-84 host-side port |
| `karma_container_port` | `8080` | Karma's internal listen port (fixed by the binary) |
| `karma_config_dir` | `/opt/telemetron/karma` | Host config directory (parent-dir bind source; Gate 8) |
| `karma_config_container_path` | `/etc/karma` | Container-side bind target (parent dir) |
| `karma_config_file_container_path` | `/etc/karma/karma.yaml` | Full path for `CONFIG_FILE` env (required) |
| `karma_alertmanager_name` | `telemetron` | Alertmanager source label in Karma UI (D-25 rename from upstream `alertmanager`) |
| `karma_alertmanager_host` | `alertmanager` | Docker bridge DNS for the Phase-4 AM container |
| `karma_alertmanager_port` | `9093` | Alertmanager HTTP port |
| `karma_alertmanager_proxy` | `true` | Karma proxies silence-add/del back to AM |
| `karma_ack_enabled` | `true` | Enable alert acknowledgement UI |
| `karma_ack_duration` | `1h` | Default silence duration for acks |
| `karma_ack_author` | `karma` | Default author for ack silences |
| `karma_ui_refresh` | `30s` | Karma UI alert refresh interval |
| `karma_ui_theme` | `auto` | `auto` / `light` / `dark` |
| `karma_ui_minimal_group_width` | `420` | Grid group min-width (pixels) |
| `karma_ui_collapse_groups` | `collapsedOnMobile` | Group collapse mode |
| `karma_default_filters` | `[]` | Default grid filter strings (sorted-keys per D-20) |
| `karma_labels_keep` | `[]` | Label names to display in grid view |
| `karma_extra_alertmanager_servers` | `[]` | Additional AM endpoints (multi-AM; v2) |
| `karma_healthcheck_*` | (see defaults) | Explicit healthcheck timing (image ships no default) |
| `karma_health_retries` | `30` | D-10a verify poll retries (2s delay; 60s budget) |
| `karma_restart_policy` | `unless-stopped` | Container restart policy (OPS-06) |
| `karma_memory_limit` | `128m` | Container memory limit |
| `karma_network` | `telemetron` | Docker network |
| `karma_tz` | `Etc/UTC` | Container timezone (Pitfall 6) |
| `karma_curl_image` | `curlimages/curl` | Curl image for verify one-shots |
| `karma_curl_image_tag` | `8.10.1` | Pinned curl image tag |

## Vault keys

None added in Phase 5 (D-66). Karma has no outbound auth -- it talks to Alertmanager on the trusted telemetron bridge network. Silence-add posts back to the AM API via the bridge; no operator credentials are needed for M1 single-host operation.

## Tags

- `karma` -- runs the whole role
- `karma-config` -- render config + restart on change
- `karma-container` -- container lifecycle
- `karma-verify` -- verify suite only

Example targeted run:

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags karma
```

## Modes

Single mode: stateless single-instance pointing at one Alertmanager (Phase-4 `alertmanager:9093`). Multi-AM is a v2 story -- use `karma_extra_alertmanager_servers` to wire additional endpoints.

## Volumes

None. Karma is stateless (in-memory alert cache). Container restart loses cache; Karma re-pulls from Alertmanager on next refresh cycle (30s by default). No named Docker volume, no host-path bind for data.

## Healthcheck

The `ghcr.io/prymitive/karma:v0.130` image ships **no default HEALTHCHECK** (confirmed via `docker inspect` -- RESEARCH §2.2). This role provides an explicit one:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --spider -q http://localhost:8080/health || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 5
  start_period: 30s
```

Verify with:

```bash
docker inspect telemetron-karma --format '{{.State.Health.Status}}'   # expects: healthy
```

In-network readiness probe (from another container on the `telemetron` bridge):

```bash
curl -fsS http://karma:8080/health   # expects: HTTP 200
```

## Network -- Host publishing

D-82 inverts D-30 for the UI plane: Karma publishes its port to the host by default (`karma_publish_host: true`). The port matrix (D-84):

| Traffic | Source | Destination |
|---------|--------|-------------|
| Operator browser | host :8082 | container :8080 |
| Karma -> Alertmanager | container (bridge) | alertmanager:9093 |
| Verify curl | curlimages/curl container | karma:8080 (bridge) |

## Network -- Bind address

D-83 defaults to `0.0.0.0` (all interfaces). Override to `127.0.0.1` to restrict to loopback only:

```yaml
# inventory/example-homelab/group_vars/all/karma.yml
karma_bind_address: "127.0.0.1"
```

Security trade-off: Karma is read-only by default (grid view, label filtering). Silence-add does POST back to Alertmanager via the bridge (no operator credentials required -- Karma handles the AM API call server-side). The single-host homelab trust model (D-26 / D-55) accepts `0.0.0.0` as the default since the host is typically behind the operator's own network boundary.

## Reverse proxy

The pattern is identical to `roles/grafana/README.md`'s reverse-proxy section; only the upstream port changes (`http://karma:8080` instead of `http://grafana:3000`). Use Caddy / Traefik / nginx pointed at the telemetron bridge:

```
# Caddy example (operator-supplied; not a Telemetron role)
karma.yourdomain.com {
    reverse_proxy karma:8080
}
```

Flip `karma_publish_host: false` if you terminate TLS at a reverse proxy -- this removes the direct host-port exposure and leaves only bridge-internal traffic.

## Configuration knobs

Most-likely-overridden knobs:

- `karma_ack_duration` -- how long a Karma silence lasts by default. `1h` is reasonable for homelab; bump to `4h` or `8h` for lower-churn environments.
- `karma_default_filters` -- pre-populate the grid's filter bar on load. Example: `["@alertmanager=telemetron"]` to show only alerts from the primary AM.
- `karma_labels_keep` -- which labels render in the grid cell. Example: `["instance", "job", "severity"]`.
- `karma_ui_theme` -- `auto` follows the OS preference; `dark` for low-light homelabs.

## Security

- Single-host bridge trust boundary (D-26 / D-55 / D-66). Karma is read-only by default -- grid view, label filtering, silence browsing do not require credentials against the AM API.
- Silence-add posts back to AM via the bridge (`karma_alertmanager_proxy: true`). No operator credentials needed for M1 single-host operation; Alertmanager in this stack has no inbound auth (same trust boundary).
- No TLS in-container. Operators who expose Karma externally are expected to terminate TLS at their reverse proxy and/or restrict access at the network level.

## Idempotency

Per OPS-04: running the playbook twice against an unchanged inventory reports `changed=0` in the PLAY RECAP. Verify:

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags karma
# first run: changed=N
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags karma
# second run: changed=0
```

Config-change restarts run via the `restart karma` handler (`docker restart {{ karma_container_name }}`).

## Per-role port-acceptance gates

This role passes Gates 1-8 documented in `roles/README.md`:

- **Gate 1 (grep gates):** `grep -riE 'inspq|qc.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/karma/` returns 0 matches. `grep -rPn '[^\x00-\x7F]' roles/karma/` returns 0 matches.
- **Gate 2 (image pin):** `ghcr.io/prymitive/karma:v0.130`; no `:latest` anywhere.
- **Gate 3 (vault discipline):** zero `{{ vault_* }}` references (D-66).
- **Gate 4 (idempotency):** see above.
- **Gate 5 (healthcheck + restart policy):** explicit `HEALTHCHECK` + `unless-stopped`.
- **Gate 6 (README schema):** this file.
- **Gate 7 (telemetron label stamp):** `org.telemetron.service: telemetron` + `org.telemetron.job: karma`.
- **Gate 8 (parent-directory bind mount):** `/opt/telemetron/karma -> /etc/karma` (directory bind; no single-file mounts).

Gate 9 is grafana-specific (datasources-resolve-real-data) and does NOT apply to this role.

## Deviations from upstream INSPQ

D-25 audit per RESEARCH §6.2 against `~/git/inspq/ansible/karma/`:

- **Alertmanager URL:** `http://localhost:9093` (upstream used host-network deploy) -> `http://alertmanager:9093` (Docker bridge DNS; D-25 fix). Without this change, Karma cannot reach Alertmanager inside the Docker bridge network.
- **Default alertmanager name:** `alertmanager` -> `telemetron` (clearer; less self-referential).
- **Image tag:** `v0.128` -> `v0.130` (latest stable as of 2026-05-16).
- **Host port:** `8080` -> `8082` (D-84; avoids common 8080 clash with other services).
- **Image source:** stays on `ghcr.io/prymitive/karma` -- this was already correct in the upstream INSPQ role. This is one INSPQ artifact that needed no change.
- **Dropped:** `application_web_docker` role dependency, `state: absent` cleanup logic, single-file bind-mount (Gate 8 violation, moby/moby#6011), latest-pull logic, French-language task names, INSPQ-internal Alertmanager hostname references.
- **Added:** explicit `HEALTHCHECK` (image ships none -- RESEARCH §2.2); `CONFIG_FILE` env var (required for non-CWD config location -- RESEARCH §2.2); `alertAcknowledgement` block; `karma_extra_alertmanager_servers` for future multi-AM ops; Gate 7 label stamp; parent-directory bind mount (Gate 8); D-10a HEALTHCHECK poll in verify.
