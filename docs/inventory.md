# Telemetron inventory model

Telemetron is inventory-agnostic. Any environment can target any host;
the example inventory at `inventory/example-homelab/` is one worked
example. This document covers how to build your own.

For a quick start using the example inventory, see `inventory/README.md`
and the walkthrough in `docs/quickstart.md`. For per-component tunables,
see each role's README under `roles/<name>/README.md`.

## Directory shape

```
inventory/
  <env-name>/
    hosts.yml              # the inventory file (YAML; INI also supported)
    group_vars/
      all/
        network.yml          # telemetron_network, port publish defaults, TZ
        storage.yml          # volume prefix, MinIO bucket names, retention
        secrets.yml          # operator-supplied; .gitignored
        secrets.yml.example  # template; committed with CHANGE_ME placeholders
        nfsd.yml             # enable_nfsd opt-in knob (default off)
        minio.yml            # per-role tunables (one file per role)
        loki.yml
        tempo.yml
        mimir.yml
        prometheus.yml
        opentelemetry.yml
        fluentbit.yml
        node_exporter.yml
        alertmanager.yml
        grafana.yml
        karma.yml
    host_vars/
      <hostname>.yml         # optional per-host overrides
```

The example inventory uses `hosts.yml` in YAML format; Ansible also
accepts INI (`<env-name>.hosts`) if you prefer.

## group_vars/all conventions

Telemetron uses `group_vars/all/<role>.yml` rather than playbook-level
`vars:` so that operators override defaults without forking the role.
Every role's `defaults/main.yml` declares the tunables;
`group_vars/all/<role>.yml` in the operator's inventory wins.

Cross-cutting files (not tied to one role):

| File | Purpose | Key vars |
|------|---------|----------|
| `network.yml` | Docker bridge network + per-role host port publish defaults | `telemetron_network`, `telemetron_publish_default`, `telemetron_tz` |
| `storage.yml` | Volume prefix, MinIO bucket names, retention defaults | `telemetron_volume_prefix`, `telemetron_config_root`, `telemetron_minio_buckets` |
| `secrets.yml` | Sensitive variables (see Secrets contract below) | 9 keys |
| `nfsd.yml` | Opt-in NFS server | `enable_nfsd`, `nfsd_exports`, `nfsd_share_root` |

Per-role files (one per deployed role) follow the same convention:
declare overrides for any variable named in
`roles/<name>/defaults/main.yml`. Common per-role overrides include
host-port-publish flags (`<role>_publish_host`), retention windows,
log-level toggles, and resource limits.

## Secrets contract

The example secrets file (`secrets.yml.example`) declares the full set
of M1 sensitive variables. Operators copy it to `secrets.yml`, fill in
real values, and choose any protection mechanism (ansible-vault, sops,
external secret manager, or chmod 600 on a homelab).

| Key | Type | Consumed by | Notes |
|-----|------|-------------|-------|
| `minio_root_user` | string | roles/minio | MinIO root username (>= 3 chars) |
| `minio_root_password` | string | roles/minio | MinIO root password (>= 8 chars; recommend 32+) |
| `loki_s3_access_key` | string | roles/loki | Defaults to `{{ minio_root_user }}` |
| `loki_s3_secret_key` | string | roles/loki | Defaults to `{{ minio_root_password }}` |
| `tempo_s3_access_key` | string | roles/tempo | Defaults to `{{ minio_root_user }}` |
| `tempo_s3_secret_key` | string | roles/tempo | Defaults to `{{ minio_root_password }}` |
| `mimir_s3_access_key` | string | roles/mimir | Defaults to `{{ minio_root_user }}` |
| `mimir_s3_secret_key` | string | roles/mimir | Defaults to `{{ minio_root_password }}` |
| `grafana_admin_password` | string | roles/grafana | First-boot-only; rotate post-deploy via `grafana-cli admin reset-admin-password` |

Naming convention: `<role>_<purpose>`. No prefix decoration. Each
role's README "Secrets" section enumerates the keys it expects.

`secrets.yml` is in `.gitignore`; `secrets.yml.example` is committed
with `CHANGE_ME` placeholders. Telemetron documents keys, not
mechanism -- pick the protection tool that fits your environment.

A future hardening milestone will split MinIO into per-backend users
with bucket-scoped IAM policies. When that lands, only `secrets.yml`
changes (`loki_s3_access_key` stops aliasing `minio_root_user` and
gets its own distinct value); role templates do not.

## host_vars patterns

Use `host_vars/<hostname>.yml` for per-target overrides that should not
apply to the whole environment. Common patterns:

- Per-host port re-mapping when 2049 (NFS) collides on a target.
- Per-host disk paths when `telemetron_volume_prefix` or
  `telemetron_config_root` differs.
- Per-host SSH user when one target accepts a different account than
  the rest of the group.

`host_vars/` is optional; an inventory with a single host typically
keeps everything in `group_vars/all/`.

## Symlinking an out-of-tree inventory

If you maintain inventory elsewhere (a separate repo, a private fork,
a vaulted directory), symlink it in:

```bash
ln -s /path/to/your/inventory inventory/myenv
```

Then run playbooks with `-i inventory/myenv`. Add the symlink to
`.git/info/exclude` if you don't want it tracked locally:

```bash
echo inventory/myenv >> .git/info/exclude
```

This keeps your inventory cleanly separated from the upstream repo's
example inventory.

## Multi-host extension

The example inventory ships as a single-host shape -- one target host
under the `telemetron` group. Telemetron's M1 deploy is designed for
a single Docker host.

Multi-host (HA / federation) deployments require:

- Distributed-mode role variants for Loki / Tempo / Mimir
  (microservices target with separate ingester/querier/distributor
  containers).
- HAProxy in front of read/write paths.
- An inventory layout that splits backends across multiple hosts
  (different groups for `telemetron-ingest`, `telemetron-query`,
  `telemetron-storage`).

This is a future milestone, not part of M1.

## Validation

Once your inventory is in place, validate it without deploying:

```bash
ansible-playbook --syntax-check -i inventory/<your-env> \
  playbooks/deploy_docker.yml
ansible-inventory -i inventory/<your-env> --list
ansible -i inventory/<your-env> telemetron -m ping
```

- `--syntax-check` catches YAML/Ansible-syntax errors before any
  changes happen on the target.
- `ansible-inventory --list` prints the resolved host + group +
  variable graph so you can confirm overrides land where you expect.
- `ansible ... -m ping` confirms the Ansible control host can reach
  the target over the configured connection plugin.

## See also

- `inventory/README.md` -- top-level inventory orientation.
- `inventory/example-homelab/README.md` -- the worked example.
- `docs/quickstart.md` -- zero-to-dashboards walkthrough using the
  example inventory.
- `roles/<name>/README.md` -- per-role tunable documentation.
