# Telemetron quickstart

Bring up the full Telemetron observability stack on a single Docker host
in one playbook run, then verify it with the included smoke test.

By the end of this walkthrough you will have:

- 12 healthy containers running on a `telemetron` Docker bridge network.
- Prometheus + Mimir for metrics, Loki for logs, Tempo for traces.
- Grafana on `:3000` with four provisioned datasources and a curated
  set of starter dashboards.
- Alertmanager + Karma reachable.
- A synthetic log + metric + trace pushed through the stack and visible
  in Grafana.

Estimated time: 15-20 minutes (most of it waiting for Docker pulls).

## Prerequisites

You need:

| Item | Version | How to check |
|------|---------|--------------|
| Ansible | 2.15 or later | `ansible --version` |
| `community.docker` collection | 4.x or later | `ansible-galaxy collection list community.docker` |
| Docker on the target host | 24+ recommended; 27+ for full feature parity | `ssh <target> docker version` |
| SSH key-based access to the target host | passwordless `sudo` if applicable | `ssh <target> hostname` |
| Free ports on the target host | 3000, 3100, 3200, 4317, 4318, 9000, 9001, 9009, 9090, 9093, 9100, 8081, 8082, 2020 | `ssh <target> ss -tln` |

If `community.docker` is not installed:

```bash
ansible-galaxy collection install community.docker
```

The example inventory ships configured to target the Ansible control
host itself via `ansible_connection: local`, so you can complete this
walkthrough without a remote SSH target if Docker is installed locally.

## Step 1 -- Clone

```bash
git clone https://github.com/rockdarko/telemetron.git
cd telemetron
```

## Step 2 -- Edit the example inventory

Open `inventory/example-homelab/hosts.yml`. By default it targets the
Ansible control host itself (`localhost`, `ansible_connection: local`).
To point at a remote Docker host, edit the `homelab` block:

```yaml
all:
  children:
    telemetron:
      hosts:
        homelab:
          ansible_host: my-docker-host.example.com   # was: localhost
          ansible_user: rock                          # was: $USER
          # remove `ansible_connection: local` to use SSH
```

Verify:

```bash
ansible -i inventory/example-homelab telemetron -m ping
```

Expected: one host line ending in `SUCCESS`.

If you need to override defaults (per-role tunables, host port publish
flags, MinIO retention, etc.), edit files under
`inventory/example-homelab/group_vars/all/`. See `docs/inventory.md` for
the full schema -- the "Building your own inventory" subsection below
covers the most common overrides.

## Step 3 -- Copy the secrets template

```bash
cp inventory/example-homelab/group_vars/all/secrets.yml.example \
   inventory/example-homelab/group_vars/all/secrets.yml
```

Open `secrets.yml` and replace every `CHANGE_ME` placeholder with a real
value. There are 9 keys; the first 8 reference each other so you only
need to set distinct values for three of them:

- `minio_root_user` (>= 3 chars)
- `minio_root_password` (>= 8 chars; recommend 32+)
- `grafana_admin_password` (any strong password)

The Loki / Tempo / Mimir S3 access keys default to the MinIO root
credentials -- no separate value needed for those.

`secrets.yml` is already in `.gitignore`; `secrets.yml.example` stays
committed with placeholders.

## Step 4 -- Optional: encrypt secrets with ansible-vault

If you want to use ansible-vault (one of several options -- sops,
env-var injection, external secret managers, and chmod 600 are also
valid):

```bash
ansible-vault encrypt inventory/example-homelab/group_vars/all/secrets.yml
```

You will be prompted for a vault password. Save it somewhere safe; you
will need it on every playbook run.

If you skip this step, drop `--ask-vault-pass` from the playbook
commands below.

## Step 5 -- Deploy

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml \
  --ask-vault-pass
```

This pulls all the Docker images on the first run (~3-5 minutes on a
typical home connection). Subsequent runs are much faster.

Expected last lines:

```
PLAY RECAP *********************************************************************
homelab      : ok=N  changed=N  failed=0  unreachable=0  skipped=N  rescued=0  ignored=0
```

`failed=0` is the gate. If anything failed, see the Troubleshooting
section below.

Run the playbook a SECOND time -- Telemetron is idempotent, so the
second run should report `changed=0`:

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml \
  --ask-vault-pass
```

Expected:

```
homelab      : ok=N  changed=0  failed=0  ...
```

To re-run a single role (faster than full deploy):

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml \
  --tags grafana --ask-vault-pass
```

Every role declares a tag matching its name.

## Step 6 -- Confirm containers are healthy

```bash
ssh <your-host> docker ps --filter name=telemetron- --format \
  'table {{.Names}}\t{{.Status}}'
```

(If you deployed to the control host via `ansible_connection: local`,
drop the `ssh <your-host>` prefix.)

Expected: 12 lines, all containing `Up ... (healthy)`. Telemetron
declares explicit HEALTHCHECKs on every container.

If `nfsd` was enabled via `enable_nfsd: true` in inventory, you also
see `systemctl is-active nfs-server.service` returning `active` on the
host (nfsd is a host-package, not a container).

## Step 7 -- Smoke test

```bash
ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml \
  --ask-vault-pass
```

This pushes a synthetic log + metric + trace via OTLP/HTTP to the OTel
Collector and verifies all four datasources (Loki, Prometheus, Mimir,
Tempo) return the data within a 60-second budget per signal.

Expected last lines:

```
TASK [Smoke summary -- all signals verified] ***********************************
ok: [homelab] => {
    "msg": [
        "Telemetron M1 smoke test PASSED",
        "trace_id: <hex>",
        "run_id:   <epoch>",
        "loki:     ok",
        "prom:     ok",
        "mimir:    ok",
        "tempo:    ok"
    ]
}
```

If any signal fails: see `playbooks/smoke_test/README.md` for a
troubleshooting table covering Loki / Prometheus / Mimir / Tempo
failure modes.

To exercise a single signal independently (useful when debugging a
specific data path):

```bash
ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml \
  --tags log    --ask-vault-pass
ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml \
  --tags metric --ask-vault-pass
ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml \
  --tags trace  --ask-vault-pass
```

The `metric` tag exercises both the Prometheus AND Mimir datasource
queries, validating the Prometheus-to-Mimir remote_write path.

## Step 8 -- Open Grafana

Open `http://<your-host>:3000` in a browser. Log in:

- Username: `admin`
- Password: the value you set for `grafana_admin_password` in Step 3.

Click **Dashboards** in the left sidebar. You should see a curated
starter set including:

- **Host health** -- node_exporter metrics (CPU, memory, disk, network).
- **Loki Explore landing** -- click a log line to drill into structured
  fields.
- **Tempo Explore landing** -- click a trace span; the "Logs for this
  span" link uses Tempo `tracesToLogsV2` to navigate to Loki with the
  `trace_id` pre-filtered.
- **OTel Collector self-metrics** -- pipeline health for the gateway.
- **Backend self-metrics** -- Loki / Mimir / Tempo internal health.

Click **Explore** in the left sidebar, select the **Loki** datasource,
and run the query `{service_name="telemetron-smoke"}`. The synthetic
smoke-test log from Step 7 should appear.

For alerts, open `http://<your-host>:8082` to see the Karma alert
triage UI. The default Alertmanager route uses a `null` receiver in M1,
so alerts are visible but not dispatched.

## Building your own inventory

The example inventory at `inventory/example-homelab/` is one worked
example. To target a different environment, copy or symlink your own
inventory directory under `inventory/` and run the playbook with
`-i inventory/<your-env>`. The full directory schema, group_vars
conventions, and the 9-key secrets contract are documented in
`docs/inventory.md`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ssh: Could not resolve hostname` during playbook run | Hostname in `hosts.yml` is wrong | Edit `inventory/example-homelab/hosts.yml`; verify with `ssh <host> hostname` |
| `Failed to connect to docker daemon` | Docker not installed on target | Install Docker (`curl -fsSL https://get.docker.com | sh` on the target) |
| `Bind for 0.0.0.0:3100 failed: port is already allocated` | Loki port collision | `ssh <host> ss -tlnp | grep 3100`; stop the conflicting service |
| Smoke test "Loki asserter exhausts retries" | OTel Collector not forwarding logs | `ssh <host> docker logs telemetron-opentelemetry` for export errors |
| Smoke test "Tempo asserter retries with 404" | Trace stuck in WAL or OTel trace export failing | `ssh <host> docker logs telemetron-tempo` for ingester errors |
| `vault password mismatch` | Wrong password supplied to `--ask-vault-pass` | Provide the password you used in Step 4 |
| Second `deploy_docker.yml` run shows `changed > 0` | Often a `community.docker` collection version older than 4.5.2 | Upgrade with `ansible-galaxy collection install -U community.docker` |
| `nfsd` role flagged but `enable_nfsd: false` | Role is task-level guarded; safe to ignore | No action needed; with `enable_nfsd: false` nfsd is a no-op |

## Production hardening (brief)

For homelab single-LAN deployments the defaults are reasonable. For
production-adjacent use cases, consider:

- **Reverse proxy + TLS termination in front of Grafana**: see the
  "Reverse proxy" section in `roles/grafana/README.md` for sample
  configurations (Nginx, Caddy, Traefik). Operators flip
  `grafana_publish_host: false` to keep Grafana on the telemetron
  bridge and proxy from the host network.
- **Anonymous viewer mode in Grafana**: disabled by default; enable
  via `grafana_anonymous_viewer: true` in inventory if you want
  unauthenticated read-only access (e.g. NOC TV dashboards).
- **Secrets rotation**: Grafana admin password is first-boot-only.
  After initial deploy, rotate via
  `docker exec telemetron-grafana grafana-cli admin reset-admin-password '<new>'`
  and update `secrets.yml` to match so subsequent deploys keep working.
- **Multi-host / HA deployment**: out of M1 scope; a future milestone
  ships distributed-mode role variants behind an HAProxy.

## Next steps

- `docs/architecture.md` -- component-level architecture reference.
- `docs/inventory.md` -- how to build your own inventory beyond the
  example.
- `roles/<name>/README.md` -- per-component documentation including
  tunables, modes, and secrets.
