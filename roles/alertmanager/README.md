# roles/alertmanager

Deploys [Prometheus Alertmanager](https://github.com/prometheus/alertmanager) v0.32.1 -- single-instance monolithic mode -- on the `telemetron` Docker bridge network. Receives evaluated alerts from Prometheus (`alerting:` block wired by `roles/prometheus/` in this phase) and dispatches them according to its `route` / `receivers` / `inhibit_rules` config.

This role ships ALERT-01 from `.planning/REQUIREMENTS.md`. ALERT-02..06 (the hook router Flask app + sample bundles + outbound auth) were deferred to a future milestone during the Phase 4 scope reshape; see `.planning/REQUIREMENTS.md` `## v2 Requirements` `ALERT-V2-01..05` for the planned shape.

## What this role does

1. Creates `/opt/telemetron/alertmanager/` on the host (D-18 flat config layout).
2. Renders `/opt/telemetron/alertmanager/alertmanager.yml` from `templates/alertmanager.yml.j2`. The default config has:
   - A single `route` with `receiver: 'null'`, `group_by: [alertname, cluster, service]`, `group_wait: 30s`, `group_interval: 5m`, `repeat_interval: 4h` (ALERT-01 + D-61).
   - One `inhibit_rules` entry: `source_matchers: [severity = "critical"]` -> `target_matchers: [severity = "warning"]`, `equal: [instance]` (D-63; new `source_matchers` syntax -- the old `source_match` is deprecated in v0.32.1).
   - A single `receivers` entry named `null` (the deliberate D-60 default -- see Security model below).
3. Ensures the `telemetron_alertmanager_data` named Docker volume exists (D-16).
4. Starts the `telemetron-alertmanager` container with:
   - Image pin `quay.io/prometheus/alertmanager:v0.32.1` (OPS-01 / D-59).
   - Explicit `HEALTHCHECK` (`wget --spider -q http://localhost:9093/-/healthy`) -- the image has no built-in healthcheck (confirmed via `docker inspect`).
   - `restart_policy: unless-stopped` (OPS-06).
   - `--cluster.listen-address=""` to disable gossip cluster (single-instance M1; HA mode is a future milestone).
   - `org.telemetron.service=telemetron` / `org.telemetron.job=alertmanager` labels (Gate 7).
   - Persistent named volume `telemetron_alertmanager_data` mounted at `/alertmanager` for silences + nflog.
5. Runs the verify suite (`tasks/verify.yml`) -- D-10a HEALTHCHECK poll, `/-/ready` + `/-/healthy` curl probes, `/api/v2/receivers` null-receiver assertion, `/api/v2/status` config-grep for route knobs, Prometheus alertmanagers API round-trip, and `amtool` synthetic alert add / query + silence add / query.

## Default receiver is `null` -- read this

Default receiver is `null`. Alerts are visible in the Alertmanager UI (port 9093) and in Karma (Phase 5) but are **not dispatched to anything automatically**. Add a real receiver before you rely on this stack to wake you up.

The reason this exists: M1 ships the observability plane plus alerting visibility, but the original M1 plan for routing alerts to Jenkins via a Flask hook router was deferred to a future milestone. Operators wire their own receivers via `alertmanager_extra_receivers` (and corresponding routes via `alertmanager_extra_routes`) in their inventory -- Slack, PagerDuty, email, or a custom webhook target.

## Variables

See `defaults/main.yml` for the full list. Most operators only touch the routing intervals (if their alert volume is different) and `alertmanager_extra_receivers` to wire a real notification target.

| Variable | Default | Purpose |
|----------|---------|---------|
| `alertmanager_image` | `quay.io/prometheus/alertmanager` | Image (do not change) |
| `alertmanager_image_tag` | `v0.32.1` | Pinned tag (OPS-01) |
| `alertmanager_container_name` | `telemetron-alertmanager` | DNS name on the `telemetron` network |
| `alertmanager_publish_host` | `false` | Publish :9093 to the host. `false`/`true`/`127.0.0.1` |
| `alertmanager_http_port` | `9093` | HTTP API + UI port |
| `alertmanager_data_volume` | `telemetron_alertmanager_data` | Named Docker volume for silences + nflog |
| `alertmanager_data_path` | `/alertmanager` | In-container data path (matches image VOLUME) |
| `alertmanager_config_dir` | `/opt/telemetron/alertmanager` | Host config bind-mount source |
| `alertmanager_group_by` | `[alertname, cluster, service]` | ALERT-01 / D-61 |
| `alertmanager_group_wait` | `30s` | AM default; explicit for documentation discipline |
| `alertmanager_group_interval` | `5m` | ALERT-01 / D-61 |
| `alertmanager_repeat_interval` | `4h` | ALERT-01 / D-61 |
| `alertmanager_log_level` | `info` | `--log.level` (Claude's discretion default) |
| `alertmanager_extra_receivers` | `[]` | Operator-defined receivers (sorted-keys per D-20) |
| `alertmanager_extra_routes` | `[]` | Operator-defined sub-routes |
| `alertmanager_extra_inhibit_rules` | `[]` | Operator-defined inhibit rules |
| `alertmanager_extra_time_intervals` | `[]` | Operator-defined time-of-day windows |
| `alertmanager_extra_mute_time_intervals` | `[]` | Operator-defined mute windows |
| `alertmanager_healthcheck_*` | (see defaults) | Explicit healthcheck timing (image ships no default) |
| `alertmanager_restart_policy` | `unless-stopped` | Container restart policy |
| `alertmanager_memory_limit` | `256m` | Container memory limit |
| `alertmanager_network` | `telemetron` | Docker network |
| `alertmanager_tz` | `Etc/UTC` | Container timezone (Pitfall 6) |

## Vault keys

None added in Phase 4 (D-66). Alertmanager has no outbound auth in M1 (null receiver = no destination = no credentials) and no inbound auth either (single-host bridge network -- D-26 / D-55 / D-66 trust boundary).

## Tags

- `alertmanager` -- runs the whole role
- `alertmanager-config` -- render config + restart on change
- `alertmanager-container` -- container lifecycle
- `alertmanager-verify` -- verify suite only

## Modes

Single mode: single-instance monolithic (`--cluster.listen-address=""`). HA cluster mode is deferred to a future milestone alongside HAProxy and distributed-mode backends.

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `telemetron_alertmanager_data` (named) | `/alertmanager` | Silences + notification log (nflog) + active-alert state. Persistent -- losing this volume loses silences and dedup memory across restart (Pitfall 7 replay-storm risk). |
| `/opt/telemetron/alertmanager/alertmanager.yml` (bind, ro) | `/etc/alertmanager/alertmanager.yml` | Rendered config |

## Healthcheck

The `quay.io/prometheus/alertmanager:v0.32.1` image ships **no default HEALTHCHECK** (confirmed via `docker inspect`). This role provides an explicit one:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --spider -q http://localhost:9093/-/healthy || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 5
  start_period: 30s
```

`busybox` base means `wget` is available (no distroless concern, unlike Tempo / Mimir / OTel). Verify with:

```bash
docker inspect telemetron-alertmanager --format '{{.State.Health.Status}}'   # expects: healthy
```

## Security model

- **Default: no host port publish** (`alertmanager_publish_host: false`). Operator UI access via `ssh -L 9093:localhost:9093 <host>`. Prometheus reaches AM at `http://alertmanager:9093` over the bridge.
- **No outbound credentials in M1.** The null receiver has no destination. Operators who add a real receiver via `alertmanager_extra_receivers` are responsible for vault-storing any outbound tokens.
- **No inbound auth.** Single-host trust boundary (D-26 / D-55 / D-66). When operators wire a real notification destination, inbound auth from upstream callers (e.g. a webhook receiver behind it) is the operator's responsibility.

## Deviations from upstream INSPQ

The upstream `~/git/inspq/ansible/alert_manager/` role embeds the upstream on-call topology: time-window vocabulary in the upstream language (evening / night / weekday / weekend / release-window), multi-team routing, SMTP receivers, the local timezone, kubernetes/Helm task paths, and an `alert_manager_*` var prefix. This role's port (D-68 audit):

- **Removed:** all time-window vars, all team-routing vars, all SMTP knobs (`alert_manager_smtp_*`, `alert_manager_email_config_send_resolve`), all k8s/Helm/OpenShift task paths, `alert_manager_kubernetes_*`, `alert_manager_helm_*`, `alert_manager_namespace`, `alert_manager_storage_class`, `alert_manager_persistence_enabled`, `alert_manager_pod_security_context`, `alert_manager_openshift_*`, `alert_manager_include_alertnames`, `alert_manager_external_url` (templated FQDN form), `alert_manager_state`, `alert_manager_container_recreate`, and the misspelled `alert_amanger_weekend_jours`.
- **Translated:** SMTP from-address removed; timezone defaults to `Etc/UTC` (consumes `telemetron_tz` from `group_vars/all/network.yml`); inline comments stripped.
- **Renamed:** `alert_manager_*` prefix -> `alertmanager_*` (locked naming normalization `ba836d2`).
- **Re-defaulted:** `alert_manager_docker_image_version: latest` -> `v0.32.1` (D-59 / OPS-01); `alert_manager_docker_restart_policy: always` -> `unless-stopped` (OPS-06).
- **Re-shaped:** `alert_manager_route: {}` + `alert_manager_receivers: []` -> explicit D-60/D-61/D-63 structure with operator extension lists.
- **Added:** `--cluster.listen-address=""` (single-instance gossip-disable, Research Q4); explicit HEALTHCHECK via wget (image has none, Research Q1); Gate 7 telemetron labels; `org.telemetron.*` label stamping for Fluent Bit Lua-enrichment (INGEST-07).

## Idempotency

Per OPS-04: running the playbook twice in a row against an unchanged inventory reports `changed=0` in the PLAY RECAP. Verify with:

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags alertmanager
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags alertmanager
# ...second run: changed=0
```

Config-change restarts run via the `restart alertmanager` handler (`docker restart {{ alertmanager_container_name }}`) -- never `state: restarted`.

## Port-acceptance gates

This role passes all seven gates documented in `roles/README.md`:

- **Gate 1 (grep gates):** `grep -riE 'inspq|qc.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq|soir|nuit|mep_|noreply@inspq' roles/alertmanager/` returns 0 matches. `grep -rPn '[^\x00-\x7F]' roles/alertmanager/` returns 0 matches (non-ASCII).
- **Gate 2 (image pin):** `quay.io/prometheus/alertmanager:v0.32.1`; no `:latest` anywhere.
- **Gate 3 (vault discipline):** zero `{{ vault_* }}` references (D-66).
- **Gate 4 (idempotency):** see above.
- **Gate 5 (healthcheck + restart policy):** explicit HEALTHCHECK + `unless-stopped`.
- **Gate 6 (README schema):** this file.
- **Gate 7 (telemetron label stamp):** `org.telemetron.service: telemetron` + `org.telemetron.job: alertmanager`.

## Deprecation notes

None. Alertmanager v0.32.1 is current stable as of 2026-04-29.

## Bring your own receivers

The default `null` receiver is intentional -- M1 ships alerting visibility, not auto-dispatch. To wire a real notification target (Slack, PagerDuty, email, custom webhook), set `alertmanager_extra_receivers` and `alertmanager_extra_routes` in `inventory/<env>/group_vars/all/alertmanager.yml`:

```yaml
alertmanager_extra_receivers:
  - name: slack-ops
    webhook_configs:
      - url: "{{ vault_slack_webhook_url }}"
        send_resolved: true

alertmanager_extra_routes:
  - receiver: slack-ops
    matchers:
      - 'severity="critical"'
    continue: false
```

(Operators who add a vault-supplied URL must also extend `inventory/example-homelab/group_vars/all/vault.yml.example` with the placeholder.)
