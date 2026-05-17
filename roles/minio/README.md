# roles/minio

Deploys [MinIO](https://github.com/minio/minio) -- S3-compatible object
storage -- on a single Docker host. MinIO is the backing store for
Telemetron's Loki (log chunks), Tempo (trace blocks), and Mimir
(metric blocks + ruler + alertmanager state).

This role is the **first role** ported in Telemetron M1 and the
canonical template every subsequent role mirrors.

## What this role does

1. Renders `/opt/telemetron/minio/minio.env` from `templates/minio.env.j2`
   with MinIO root credentials pulled from Ansible vault.
2. Ensures the named Docker volume `telemetron_minio_data` exists.
3. Starts the `minio` container on the `telemetron` Docker bridge
   network, with a Docker `HEALTHCHECK` and `restart: unless-stopped`.
   Container ports are NOT published to the host by default
   (`minio_publish_host: false`).
4. **As a blocking final task**, polls MinIO's Docker HEALTHCHECK
   via `community.docker.docker_container_info` until State.Health.Status
   reports `healthy`, then runs a one-shot `minio/mc` container that
   creates the five required buckets (`loki-chunks`, `tempo-traces`,
   `mimir-blocks`, `mimir-ruler`, `mimir-alerts`). Non-zero exit from
   the bootstrap container fails the playbook. **Downstream backends
   (Loki, Tempo, Mimir in Phase 2) depend on this -- they will not
   see a no-bucket MinIO.**

## Important: MinIO is archived upstream

The community MinIO project was archived in early 2026 -- the GitHub
repository is read-only and the community Docker images are no longer
being published. This role pins the last published community release
(`minio/minio:RELEASE.2025-04-22T22-12-26Z` and the paired
`minio/mc:RELEASE.2025-04-22T16-23-26Z`).

A future Telemetron milestone will evaluate
[Garage](https://garagehq.deuxfleurs.fr/) and SeaweedFS as
replacements. **Do not deploy this role for any workload where security
patching of the storage layer matters.**

## Variables

See `defaults/main.yml` for the full list. Most operators will only
touch `minio_publish_host` (default `false` -- see Security below).

| Variable | Default | Purpose |
|----------|---------|---------|
| `minio_image` | `minio/minio` | MinIO server image (do not change) |
| `minio_image_tag` | `RELEASE.2025-04-22T22-12-26Z` | Pinned tag (explicit, not floating) |
| `minio_mc_image` | `minio/mc` | mc CLI image for the bootstrap one-shot |
| `minio_mc_image_tag` | `RELEASE.2025-04-22T16-23-26Z` | Pinned tag |
| `minio_container_name` | `minio` | DNS name on the `telemetron` network |
| `minio_publish_host` | `false` | Publish :9000 and :9001 to the host. `false`/`true`/`127.0.0.1` |
| `minio_api_port` | `9000` | S3 API port |
| `minio_console_port` | `9001` | Web console port |
| `minio_data_volume` | `telemetron_minio_data` | Named Docker volume |
| `minio_data_path` | `/data` | In-container data path |
| `minio_config_dir` | `/opt/telemetron/minio` | Host config bind-mount source |
| `minio_buckets` | (5 buckets -- see defaults) | Buckets created by bootstrap |
| `minio_health_retries` | `30` | Pre-bootstrap Docker HEALTHCHECK polls |
| `minio_health_delay` | `2` | Seconds between polls |
| `minio_healthcheck_*` | (HEALTHCHECK config) | Docker HEALTHCHECK timing |
| `minio_restart_policy` | `unless-stopped` | Container restart policy |
| `minio_memory_limit` | `512m` | Container memory limit |
| `minio_network` | `telemetron` | Docker network (created by playbook pre_tasks) |
| `minio_tz` | `Etc/UTC` | Container timezone (Pitfall 6) |
| `minio_browser_redirect_url` | `""` | Empty disables console redirect |

## Vault keys

Required keys in `inventory/<env>/group_vars/all/vault.yml`:

| Key | Purpose |
|-----|---------|
| `vault_minio_root_user` | MinIO root username (>= 3 chars) |
| `vault_minio_root_password` | MinIO root password (>= 8 chars; 32+ recommended) |

Placeholders ship in `inventory/example-homelab/group_vars/all/vault.yml.example`.

## Tags

- `minio` -- runs the whole role
- `always` -- pre_tasks (network creation) -- set in `playbooks/deploy_docker.yml`

## Modes

Single mode only in M1: monolithic single-node. Distributed MinIO is a
later-milestone concern and is not part of the role's variable surface yet.

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `telemetron_minio_data` (named) | `/data` | MinIO data root -- covers all object storage. Persistent across container recreates. |
| `/opt/telemetron/minio/` (bind) | (env file mount path) | Rendered config; bind-mounted read-only. |

## Healthcheck

Docker HEALTHCHECK runs every 30s (`curl -sf http://127.0.0.1:9000/minio/health/ready`).
Verify with:

```bash
docker inspect minio --format '{{.State.Health.Status}}'   # expects: healthy
```

The bucket-bootstrap subtask polls this same HEALTHCHECK status via
`community.docker.docker_container_info` (reading
`result.container.State.Health.Status`) before firing the mc container,
so first-deploy timing races are eliminated without needing host port
publishing.

## Security model

- **Default: no host port publish.** Operator access via
  `ssh -L 9001:localhost:9001 <host>` and a web browser, or via
  `docker exec` on the host.
- **Root credentials from vault.** No `minioadmin/minioadmin` default
  anywhere; the role refuses to render the env file if vault keys
  are missing (Ansible errors out on the undefined vault variable).
- **Inter-component traffic on the `telemetron` Docker bridge network only.**
  Loki, Tempo, and Mimir (Phase 2) will reach MinIO at
  `http://minio:9000` over the bridge -- never via the host.
- **Per-backend access keys are deferred.** Phase 1 reuses MinIO root
  credentials for Loki/Tempo/Mimir; per-backend users with
  bucket-scoped IAM policies are a future hardening phase.
- **Bootstrap credential exposure (D-09 + I12).** The bucket-bootstrap
  one-shot mc container receives root creds via the
  `MC_HOST_<alias>=http://user:pw@host:port` env-var format that mc
  requires. This is technically visible in `docker inspect` for the
  lifetime of this container. `auto_remove: true` on the bootstrap
  container destroys it on exit (typically <5s), bounding the
  docker-inspect exposure window to the bootstrap run only. See
  `tasks/bootstrap.yml` inline comment.

## Idempotency

Per OPS-04: running the playbook twice in a row against an unchanged
inventory reports `changed=0` in the PLAY RECAP. Verify with:

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags minio \
                 --ask-vault-pass
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags minio \
                 --ask-vault-pass
# ...second run: changed=0
```

Container restarts on env-file change use a handler that runs
`docker restart minio` -- the module-level state parameter is never used
for restarts (force-recreate is non-idempotent per Pitfall 8).

## Port-acceptance gates

This role passes all five gates documented in `roles/README.md`:

- **Grep gates (Pitfall 9):**
  Fork-leftover grep gate (see `roles/README.md` port process for the full pattern) returns 0 matches against `roles/minio/`.
  Non-ASCII grep gate returns 0 matches against `roles/minio/`.
- **Image-pin gate:** zero floating-tag references in `roles/minio/` (all images pinned to explicit release tags).
- **Vault-discipline gate:** every `{{ vault_* }}` reference has a
  matching key in `vault.yml.example` with the consuming-role comment.
- **Idempotency gate:** twice-in-a-row playbook run reports `changed=0`.
- **Healthcheck + restart-policy gate:** `docker inspect` returns
  `healthy` and `unless-stopped`.

## Deprecation notes

The MinIO community version is archived upstream (see "Important" section
above). This role is a candidate for replacement with a Garage role in a
future milestone.

## Bring your own bucket names

Override `telemetron_minio_buckets` in
`inventory/<env>/group_vars/all/storage.yml` to add or rename buckets.
Renaming a bucket here MUST be paired with renaming in the consuming
backend role's S3 config (Phase 2 loki / tempo / mimir).
