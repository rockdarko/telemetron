# roles/node_exporter

Deploys [Prometheus node_exporter](https://github.com/prometheus/node_exporter)
v1.11.1 on the `telemetron` Docker bridge network. Ships host metrics (CPU,
memory, disk, network, filesystem) on `:9100/metrics` for Phase 3 Prometheus
(Plan 03-03) to scrape at `http://node-exporter:9100/metrics`.

Mirrors the canonical role template established by `roles/garage`, `roles/loki`,
`roles/tempo`, and `roles/mimir` -- same defaults layout, same handler
discipline (W6 single handler), same in-network verify pattern, same Docker
HEALTHCHECK / running-state pre-poll (D-10a), same OPS-03 README schema.

Stateless: no rendered config (node_exporter is CLI-flag-driven), no Docker
volume, three RO bind-mounts from the host (`/proc`, `/sys`, `/`), and
`pid_mode: host`.

## What this role does

1. Pulls the pinned image `quay.io/prometheus/node-exporter:v1.11.1`.
2. Starts the `node-exporter` container on the `telemetron` Docker bridge with:
   - Three RO bind-mounts: `/proc -> /host/proc`, `/sys -> /host/sys`,
     `/ -> /host/root` (root with `propagation: rslave`).
   - `pid_mode: host` (required for some collectors per RESEARCH Finding 6).
   - Container hardening set (read-only rootfs, `cap_drop: [ALL]`, add
     `DAC_READ_SEARCH`, `no-new-privileges:true`, tmpfs `/tmp`,
     `pids_limit: 512`) guarded by `node_exporter_container_hardening_enabled`.
   - Conditional Docker HEALTHCHECK -- defaults to the `--version` binary-alive
     proxy; flippable to disabled.
3. **As a blocking final task**, polls readiness via
   `community.docker.docker_container_info` then runs a one-shot
   `curlimages/curl` container on the `telemetron` network curl-ing
   `http://node-exporter:9100/metrics` and asserts the body contains
   `node_cpu_seconds_total` (D-54 authoritative readiness gate).

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `node_exporter_image` | `quay.io/prometheus/node-exporter` | Image (do not change) |
| `node_exporter_image_tag` | `v1.11.1` | Pinned tag (OPS-01) |
| `node_exporter_container_name` | `node-exporter` | DNS name on the `telemetron` network |
| `node_exporter_publish_host` | `false` | Publish :9100 to host. `false`/`true`/`127.0.0.1` |
| `node_exporter_port` | `9100` | HTTP /metrics listen port |
| `node_exporter_network` | `telemetron` | Docker network |
| `node_exporter_tz` | `Etc/UTC` | Container timezone (Pitfall 6) |
| `node_exporter_restart_policy` | `unless-stopped` | OPS-06 |
| `node_exporter_memory_limit` | `128m` | Homelab-safe memory limit |
| `node_exporter_container_hardening_enabled` | `true` | Read-only / cap_drop / no-new-privileges / tmpfs / pids_limit |
| `node_exporter_healthcheck_enabled` | `true` | Conditional HEALTHCHECK pattern (Outcomes A/B/C) |
| `node_exporter_healthcheck_test` | `["CMD", "/bin/node_exporter", "--version"]` | Binary-alive proxy (Outcome B default) |
| `node_exporter_healthcheck_interval` | `15s` | |
| `node_exporter_healthcheck_timeout` | `5s` | |
| `node_exporter_healthcheck_retries` | `5` | |
| `node_exporter_healthcheck_start_period` | `10s` | |
| `node_exporter_health_retries` | `30` | Verify pre-poll retries |
| `node_exporter_health_delay` | `2` | Verify pre-poll delay seconds (60s total budget) |
| `node_exporter_curl_image` | `curlimages/curl` | Verify one-shot image |
| `node_exporter_curl_image_tag` | `8.10.1` | Pinned curl image tag (OPS-01) |

## Vault keys

None (per Phase 3 D-55). node_exporter has no auth surface.
`inventory/example-homelab/group_vars/all/vault.yml.example` is unchanged by
this role.

## Tags

- `node_exporter` -- runs the whole role (D-24 single tag per role)

## Modes

Single mode (containerized via Docker per CLAUDE.md). Stock collectors enabled;
`systemd` and `textfile` collectors are deferred opt-ins (see "Bring your own
collectors" below).

## Volumes

None (node_exporter is stateless).

Three host RO bind-mounts:

| Source | Target | Notes |
|--------|--------|-------|
| `/proc` | `/host/proc` (ro) | Required for the `cpu`/`meminfo`/`loadavg`/`netstat`/`stat` collectors |
| `/sys`  | `/host/sys`  (ro) | Required for the `diskstats`/`netdev`/`thermal_zone`/`hwmon` collectors |
| `/`     | `/host/root` (ro, `propagation: rslave`) | Required for the `filesystem` collector; `rslave` so the container sees post-startup bind-mount table changes |

## Uninstall

```bash
ansible-playbook playbooks/undeploy_docker.yml --tags node_exporter --ask-vault-pass
```

No named volume to preserve. To also remove this role's pinned Docker
image: `--extra-vars telemetron_purge_images=true` (irreversible).

See `docs/quickstart.md#removing-telemetron` for the full undeploy story
(purge flags, manual fallback, order-of-operations).

## Healthcheck

The image is built `FROM scratch` (no shell, no curl, no wget) and there is no
documented `--health` flag. Same approach as the Mimir / Tempo roles: a
binary-alive proxy (`/bin/node_exporter --version`) is used as the Docker
HEALTHCHECK to satisfy OPS-06 ("HEALTHCHECK is declared"), and the
authoritative readiness gate is the verify task's in-network curl to
`http://node-exporter:9100/metrics` asserting `node_cpu_seconds_total` in the
response body.

Three possible outcomes:

1. **Outcome A -- native `--health` flag present:** set
   `node_exporter_healthcheck_test: ["CMD", "/bin/node_exporter", "--health"]`.
   The role's verify task polls `State.Health.Status` until `healthy`.
2. **Outcome B -- only `--version` proxy (default):** Docker HEALTHCHECK uses
   `CMD ["/bin/node_exporter", "--version"]`. OPS-06 compliance via the
   binary-alive proxy + the verify task's authoritative `/metrics` curl probe.
3. **Outcome C -- no flag at all:** set
   `node_exporter_healthcheck_enabled: false`. Docker HEALTHCHECK is omitted
   entirely; OPS-06 compliance via the verify task's `State.Running` poll plus
   the in-network `/metrics` curl probe.

Probe the image at execute time:

```bash
docker run --rm quay.io/prometheus/node-exporter:v1.11.1 --help 2>&1 | grep -i health
```

PITFALLS Pitfall B documents the from-scratch trap.

## Operator access (no host publish by default per D-30)

Inter-component traffic on the `telemetron` bridge reaches node_exporter at
`http://node-exporter:9100` (Phase 3 Prometheus scrape target). Operator access
from a workstation:

```bash
ssh -L 9100:localhost:9100 <homelab-host>
curl http://localhost:9100/metrics | grep '^node_cpu_seconds_total' | head
```

Flip `node_exporter_publish_host: true` (or `'127.0.0.1'`) in inventory to
publish the port to the host. Default is `false` -- the SSH local-forward is
the homelab access pattern.

## Security model

- **Default: no host port publish.** Operator access via SSH local-forward;
  Prometheus scrape traffic stays on the `telemetron` bridge.
- **Container hardening enabled by default** (`node_exporter_container_hardening_enabled: true`):
  read-only rootfs, `cap_drop: [ALL]` + `capabilities: [DAC_READ_SEARCH]`,
  `security_opts: ['no-new-privileges:true']`, tmpfs `/tmp`, `pids_limit: 512`.
  Flip to `false` on hosts where SELinux or other layers interact poorly.
- **`pid_mode: host` is REQUIRED** for some node_exporter collectors (per
  RESEARCH Finding 6 and upstream node_exporter README). The kernel-level
  access is read-only via the `/host/{proc,sys,root}` bind-mounts -- the
  container has no write path to the host kernel state.
- **No vault keys** (D-55) -- node_exporter has no auth surface.

## Idempotency

Per OPS-04: running the playbook twice in a row reports `changed=0`.

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags node_exporter
# ...first run: changed=N
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml --tags node_exporter
# ...second run: changed=0
```

The single handler (`docker restart node_exporter`, W6) is unused in M1
(no rendered config, so no notify points exist) but lands per the canonical
role template. `state: restarted` is never used (Pitfall 8).

## Port-acceptance gates

All six pass on `roles/node_exporter/` (with the grep gate scoped to
code/config files; the role README intentionally documents the
upstream-deviation audit per D-25, which mentions the source-of-truth project
name):

- **Image-pin (OPS-01):** zero floating-tag references.
- **Grep gate (Pitfall 9):** zero matches in code/config files for
  upstream-org leftovers.
- **Non-ASCII gate (OPS-05):** zero non-ASCII characters in the role.
- **Vault-discipline (OPS-02 / D-55):** N/A -- node_exporter has no vault
  references.
- **Idempotency (OPS-04):** twice-in-a-row run reports `changed=0`.
- **Healthcheck + restart-policy (OPS-06):** `docker inspect` returns
  `healthy` (Outcome A/B) or the verify task's `State.Running` + `/metrics`
  probe gate (Outcome C); restart policy `unless-stopped`.

## Deviations from upstream INSPQ (D-25)

Per CONTEXT.md D-25, each Phase-3 role port is an opinionated improvement
pass over the upstream INSPQ role -- not a mirror translation. Items dropped,
replaced, or added vs. `~/git/inspq/ansible/node_exporter/`:

Audit categories (TL;DR):

- Dropped: native deployment, LVM, UFW, French names, host-publish default, textfile collector, `America/Toronto`, `:latest`, `node_explorer_*` typo variants
- Replaced: `--path.rootfs=/rootfs` -> `/host/root`; `prom/node-exporter` -> `quay.io/prometheus/node-exporter`
- Added: D-10a HEALTHCHECK + D-54 `/metrics` verify, `publish_host: false` default, pinned `v1.11.1`, conditional-HEALTHCHECK knob
- Kept: `pid_mode: host`, hardening set (read-only/cap_drop/no-new-privileges/tmpfs/pids_limit), `/host/{proc,sys,root}` bind-mount triple

**Dropped (upstream-isms beyond the grep gate):**

- `node_exporter_deployment_method: native` -- Docker-only per CLAUDE.md M1
  constraint.
- LVM tasks (`node_exporter_lvm`, `node_exporter_vg`) -- node_exporter is
  stateless; no storage volume needed.
- UFW rules -- Telemetron does not manage host firewall.
- French task names throughout -- replaced with English per CLAUDE.md.
- Default-on host publish -- replaced with `node_exporter_publish_host: false`
  default per D-30. Operator access via SSH local-forward.
- Textfile collector + LVM-on-textfile-collector assumption -- dropped; M1
  ships stock collectors only.
- `America/Toronto` TZ -- replaced with `Etc/UTC` per Pitfall 6 / D-06.
- `:latest` image tag -- replaced with explicit pin `v1.11.1` per OPS-01.
- `node_explorer_*` upstream typo variants (e.g.
  `node_explorer_docker_restart_policy`) -- renamed cleanly to
  `node_exporter_*`.

**Replaced:**

- `--path.rootfs=/rootfs` -> `--path.rootfs=/host/root` matching the current
  upstream node_exporter README example layout (all three `/host/*` paths
  consistent).
- `prom/node-exporter` Docker Hub -> `quay.io/prometheus/node-exporter` Quay
  registry. Matches the Phase-1 alertmanager registry choice and avoids
  Docker Hub rate-limit risk for unauth pulls.

**Added (missing in upstream):**

- D-10a HEALTHCHECK pre-poll + D-54 in-network `/metrics` verify asserting
  `node_cpu_seconds_total` in body -- upstream had no verify step.
- Conditional `node_exporter_publish_host: false` security default (upstream
  defaulted to host-published).
- Pinned image tag `v1.11.1` (upstream used `:latest`).
- Conditional HEALTHCHECK pattern + `node_exporter_healthcheck_enabled` knob
  so operators can flip to Outcome C without role restructure.

**Kept from upstream (got it right):**

- `pid_mode: host` -- required for some collectors.
- Container hardening set (`read_only: true`, `cap_drop: [ALL]`,
  `capabilities: [DAC_READ_SEARCH]`, `no-new-privileges:true`, tmpfs `/tmp`,
  `pids_limit: 512`) -- guarded by `node_exporter_container_hardening_enabled`
  knob so operators with SELinux quirks can flip off.
- Three RO bind-mount triple (`/proc`, `/sys`, `/`) with `rslave` propagation
  on the root mount.

## Bring your own collectors

Stock collectors only in M1. The default-enabled collector set in
node_exporter v1.11.1 covers CPU, memory, disk, network, filesystem, load
average, hwmon, and thermal zones -- enough for the homelab. The `systemd`
and `textfile` collectors and any per-collector `--collector.<name>` toggles
are deferred opt-ins. Operators can extend the `command:` flag list via a
future knob; tracked in CONTEXT.md Deferred Ideas. Filing-system mount-point
and FS-type exclusion regexes are already verbatim from the upstream
node_exporter README example -- override them with care.

## Deprecation notes

None.
