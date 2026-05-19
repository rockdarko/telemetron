# roles/mimir

Deploys [Grafana Mimir](https://github.com/grafana/mimir) 3.0.6 in
monolithic mode (`-target=all`) on a single Docker host. Mimir is
the long-term metrics backend for Telemetron's observability plane;
metrics land via Prometheus `remote_write` (Phase 3) and are queried
via Grafana (Phase 5).

Storage backend: MinIO S3 with **three distinct buckets** -- Mimir
refuses to start with shared prefixes (Pitfall G + BACK-04).

Mirrors the canonical role template established by `roles/minio`,
`roles/loki`, and `roles/tempo` -- same defaults layout, same handler
discipline (W6 single handler), same in-network verify pattern (W8),
same Docker HEALTHCHECK / running-state pre-poll (D-10a), same OPS-03
README schema.

## What this role does

1. Renders `/opt/telemetron/mimir/mimir.yaml` from `templates/mimir.yaml.j2`
   with MinIO S3 credentials from Ansible vault.
2. Ensures the named Docker volume `telemetron_mimir_data` exists.
3. Starts the `mimir` container on the `telemetron` Docker bridge
   network. Container port `9009` is NOT published to the host by
   default (`mimir_publish_host: false`).
4. **As a blocking final task**, polls Mimir readiness via
   `community.docker.docker_container_info` plus an in-network curl
   to `/ready`, then asserts all three required buckets (`mimir-blocks`,
   `mimir-ruler`, `mimir-alerts`) are reachable via a one-shot `mc`
   container.

## Three distinct buckets (BACK-04)

Mimir's three storage stores -- blocks, ruler, alertmanager -- MUST
use distinct buckets. Sharing a bucket (even with different prefixes)
causes Mimir to refuse startup with a storage prefix collision error.

| Store | Bucket |
|-------|--------|
| `blocks_storage` | `mimir-blocks` |
| `ruler_storage` | `mimir-ruler` |
| `alertmanager_storage` | `mimir-alerts` |

The Phase 1 minio role bootstrap creates all three buckets; this role
references them by name. Renaming any bucket here MUST be paired with
renaming in `roles/minio/defaults/main.yml` or the
`telemetron_minio_buckets` list in `storage.yml`.

## Monolithic tuning (BACK-04 / D-36 / Pitfall 11)

Five knobs are explicitly set to avoid known monolithic-mode footguns
on a single homelab host:

| Knob | Default | Why |
|------|---------|-----|
| `limits.max_global_series_per_user` | `500000` | Pitfall 3 -- homelab limit (upstream INSPQ used 5M for multi-host scale) |
| `limits.max_global_series_per_metric` | `100000` | Pitfall 3 -- secondary high-cardinality guard |
| `querier.query_store_after` | `12h` | Pitfall 11 -- longer than block-lands window; shorter than Prometheus local retention |
| `blocks_storage.bucket_store.sync_interval` | `5m` | Pitfall 11 -- ingester/compactor consistency on single host |
| `compactor.cleanup_interval` | `5m` | Pitfall 11 -- consistent with sync_interval |

All five are inline-commented in `templates/mimir.yaml.j2` with their
PITFALLS.md references.

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `mimir_image` | `grafana/mimir` | Image (do not change) |
| `mimir_image_tag` | `3.0.6` | Pinned tag |
| `mimir_container_name` | `mimir` | DNS name on the `telemetron` network |
| `mimir_publish_host` | `false` | Publish :9009 to host. `false`/`true`/`127.0.0.1` |
| `mimir_http_port` | `9009` | HTTP API port (metrics push + /ready) |
| `mimir_grpc_port` | `9097` | gRPC port (D-28 -- moved off 9095/9096 to avoid clashes) |
| `mimir_data_volume` | `telemetron_mimir_data` | Named Docker volume |
| `mimir_data_path` | `/data` | In-container data root |
| `mimir_config_dir` | `/opt/telemetron/mimir` | Host config bind-mount source |
| `mimir_s3_endpoint` | `minio:9000` | **NO** http:// prefix (Mimir/Tempo format); insecure flag signals HTTP |
| `mimir_blocks_bucket` | `mimir-blocks` | TSDB blocks bucket |
| `mimir_ruler_bucket` | `mimir-ruler` | Recording rule state |
| `mimir_alerts_bucket` | `mimir-alerts` | Alertmanager state (in case multi-AM ring is enabled later) |
| `mimir_compactor_blocks_retention_period` | `30d` | **BACK-04** retention knob |
| `mimir_max_global_series_per_user` | `500000` | D-36 / Pitfall 3 |
| `mimir_max_global_series_per_metric` | `100000` | D-36 / Pitfall 3 |
| `mimir_query_store_after` | `12h` | D-36 / Pitfall 11 |
| `mimir_bucket_store_sync_interval` | `5m` | D-36 / Pitfall 11 |
| `mimir_compactor_cleanup_interval` | `5m` | D-36 / Pitfall 11 |
| `mimir_multitenancy_enabled` | `false` | D-26 -- single-tenant `anonymous` |
| `mimir_healthcheck_enabled` | `true` | Override to false if image probe shows no useful flag |
| `mimir_healthcheck_test` | `["CMD", "/bin/mimir", "-version"]` | Default binary-alive proxy (Outcome B) |
| `mimir_restart_policy` | `unless-stopped` | Container restart policy |
| `mimir_memory_limit` | `2g` | Container memory limit (ingester is the memory hog) |
| `mimir_container_user` | `472:472` | Mimir image default UID |
| `mimir_network` | `telemetron` | Docker network |
| `mimir_tz` | `Etc/UTC` | Container timezone |

## Secrets

Required keys in `inventory/<env>/group_vars/all/secrets.yml`:

| Key | Purpose |
|-----|---------|
| `mimir_s3_access_key` | MinIO access key for all three mimir-* buckets |
| `mimir_s3_secret_key` | MinIO secret key for all three mimir-* buckets |

Per CONTEXT.md D-27 (superseded by D-90 naming), both alias to
`minio_root_user` / `minio_root_password` in `secrets.yml.example`.
Future hardening milestone splits MinIO into per-backend users (secret
values change; role templates do not). Cheap forward-compat per D-27.

## Tags

- `mimir` -- runs the whole role (D-24 single tag per role)

## Modes

Monolithic only (`-target=all`). Single-tenant
(`multitenancy_enabled: false` per D-26). Distributed Mimir
(microservices mode) is deferred to a future milestone.

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `telemetron_mimir_data` (named) | `/data` | Mimir data root -- covers tsdb/, tsdb-sync/, compactor/, alertmanager/, ruler/. Persistent across recreates. |
| `/opt/telemetron/mimir/mimir.yaml` (bind) | `/etc/mimir/mimir.yaml` (ro) | Rendered config |

## Healthcheck

Mimir 3.0.6 is built on `gcr.io/distroless/static-debian12` -- no
shell, no curl, no wget, and no native `-health` binary flag as of
research (issue #9034 closed unresolved). Same approach as the Tempo
role: a binary-alive proxy (`/bin/mimir -version`) is used as the
Docker HEALTHCHECK to satisfy OPS-06 ("HEALTHCHECK is declared"),
and the authoritative readiness gate is the verify task's
in-network curl to `http://mimir:9009/ready` (returns 200 with body
`ready` when fully started).

Three possible outcomes:

1. **Outcome A -- native -health flag present:** set
   `mimir_healthcheck_test: ["CMD", "/bin/mimir", "-health"]`. The
   role's verify task polls `State.Health.Status` until `healthy`.
2. **Outcome B -- only -version proxy (default):** Docker HEALTHCHECK
   uses `CMD ["/bin/mimir", "-version"]`. OPS-06 compliance via the
   binary-alive proxy + the verify task's authoritative /ready curl
   probe.
3. **Outcome C -- no flag at all:** set
   `mimir_healthcheck_enabled: false`. Docker HEALTHCHECK is omitted
   entirely; OPS-06 compliance via the verify task's `State.Running`
   poll plus the in-network `/ready` curl probe.

The plan that ports this role probes the image at execute time
(`docker run --rm grafana/mimir:3.0.6 -help 2>&1 | grep -i health`)
and selects the actual shape. PITFALLS Pitfall B documents the
distroless trap.

## Operator access (no host publish by default per D-30)

Inter-component traffic on the `telemetron` bridge reaches Mimir at
`http://mimir:9009` (Phase 3 Prometheus remote_write target; Phase 5
Grafana datasource path). Operator access from a workstation:

```bash
ssh -L 9009:localhost:9009 <homelab-host>
curl http://localhost:9009/ready      # expects: ready
curl http://localhost:9009/services   # operational debug -- shows component states
```

## Security model

- **Default: no host port publish.** Operator access via SSH local-forward.
- **S3 credentials from operator-supplied secrets.** Rendered config at mode `0600`.
- **Inter-component traffic on the `telemetron` bridge only.** Mimir
  reaches MinIO at `minio:9000` over the bridge; never via the host.
- **Multitenancy off** -- all data lives in tenant `anonymous`.
  Flipping to true requires every Phase-3 producer to send
  `X-Scope-OrgID`. Document the path in Phase 6 `docs/architecture.md`
  for future-Rock.

## Idempotency

Per OPS-04: running the playbook twice in a row reports `changed=0`.

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags mimir --ask-vault-pass
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags mimir --ask-vault-pass
# ...second run: changed=0
```

Config changes notify a single `docker restart mimir` handler (W6);
`state: restarted` is never used (Pitfall 8).

## Port-acceptance gates

All five pass on `roles/mimir/` (with the grep gate scoped to
code/config files; the role README intentionally documents the
upstream-deviation audit per D-25, which mentions the source-of-truth
project name):

- **Image-pin (OPS-01):** zero floating-tag references.
- **Grep gate (Pitfall 9):** zero matches in code/config files for
  upstream-org leftovers.
- **Non-ASCII gate (OPS-05):** zero non-ASCII characters in the role.
- **Secrets-discipline (OPS-02):** every sensitive `{{ <role>_<purpose> }}`
  reference has a matching key in `secrets.yml.example`.
- **Idempotency (OPS-04):** twice-in-a-row run reports `changed=0`.
- **Healthcheck + restart-policy (OPS-06):** `docker inspect` returns
  `healthy` (Outcome A/B) or the verify task's `State.Running` + `/ready`
  probe gate (Outcome C); restart policy `unless-stopped`.

## Deviations from upstream INSPQ (D-25)

Per CONTEXT.md D-25, each Phase-2 role port is an opinionated
improvement pass over the upstream INSPQ role -- not a mirror
translation. Items dropped, replaced, or added vs.
`~/git/inspq/ansible/mimir/`:

**Dropped (upstream-isms beyond the grep gate):**

- `mimir_image_version: "latest"` -- replaced with explicit pin
  `3.0.6` per OPS-01.
- `mimir_container_name: "telemetron_mimir_{{ env | lower }}_{{ inventory_hostname }}"` --
  replaced with simple `mimir`. inventory_hostname-embedded names
  break single-host portability and the Docker DNS contract assumed
  by other Phase-2/3 roles.
- `alertmanager.external_url: "http://{{ inventory_hostname }}:9009/alertmanager"` --
  dropped. Upstream hostname pattern.
- `ruler.alertmanager_url: "http://{{ inventory_hostname }}:9009/alertmanager"` --
  omitted from M1; Phase 4 lands the alertmanager URL once the
  alertmanager role is ported.
- Upstream `max_global_series_per_user: 5000000` (5M, multi-host
  scale) -- replaced with homelab `500000` per Pitfall 3.
- Upstream `max_global_series_per_metric: 500000` -- replaced with
  `100000`.
- LVM tasks (`mimir_lvm`, `mimir_vg`) -- dropped; named Docker volume
  covers storage.
- UFW tasks -- dropped; Telemetron does not manage host firewall.
- `mimir_container_restart_policy: "always"` -- replaced with
  `unless-stopped` per OPS-06.
- `mimir_config == 'standalone'` conditional -- dropped; M1 ships
  monolithic only.
- `mimir_storage_backend: filesystem` -- replaced with `s3` (MinIO)
  per D-39.
- `mimir_compactor_retention_period: "2y"` -- replaced with `30d`
  per D-35.
- `blocks_storage.backend: filesystem` template branch -- replaced
  with `s3` + three distinct bucket config per D-39 + Pitfall G.
- `alertmanager.fallback_config_file` upstream-specific path --
  omitted.
- French task names throughout -- replaced with English per CLAUDE.md.

**Kept from upstream (got it right):**

- `mimir_container_user: "472:472"` -- Mimir image default UID.
- `mimir_ooo_time_window: "30m"` -- sensible homelab default.
- Upstream already moved gRPC off 9095 (used 9010); Telemetron uses
  9097 per D-28 (different value, same rationale).

**Added (missing pitfall guards in upstream):**

- **D-36 / Pitfall 11 monolithic tuning** -- the upstream template
  had NONE of: `query_store_after`, `sync_interval`,
  `cleanup_interval`. All three added per Pitfall 11 guidance.
- **D-36 / Pitfall 3 limits** -- both `max_global_series_per_user`
  AND `max_global_series_per_metric` set to homelab-appropriate
  values.
- **D-28 explicit gRPC port pin** -- `server.grpc_listen_port: 9097`
  (avoids 9095 clash with Loki and 9096 clash with Tempo on single
  host).
- **D-39 / Pitfall G three-bucket S3** -- the upstream default was
  filesystem; switching to S3 required validating three-distinct-bucket
  configuration that the upstream never had.

## Bring your own bucket names

Override `mimir_blocks_bucket` / `mimir_ruler_bucket` /
`mimir_alerts_bucket` individually, or rename the
`telemetron_minio_buckets` list entries in `storage.yml`. All three
MUST remain distinct (Pitfall G).

## Deprecation notes

None. Mimir is the locked long-term metrics backend per CLAUDE.md
tech-stack constraints; VictoriaMetrics / Thanos alternatives are
explicitly out of M1 scope.
