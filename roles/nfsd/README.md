# nfsd

Opt-in, default-off host-package NFSv4 server for legacy log ingestion. Lands logs from remote hosts that cannot run an OTel SDK or a Fluent Bit agent locally into `/srv/telemetron-nfs/<remote-host>/` where Fluent Bit on the Telemetron host tails them and ships them to Loki via the OTel Collector.

## When to use this role

**Most operators do NOT need this role.** It defaults to off (`enable_nfsd: false`) and exists only as a last-resort fallback. Skip it unless you have a specific legacy-host log-ingestion problem this solves.

The preferred shipping paths, in order of preference:

1. **OTel SDK direct from the application.** If the workload can be instrumented, point its OTLP exporter at the Telemetron OTel Collector at `:4317` / `:4318`. This is the modern path and what the rest of Telemetron is built around.
2. **Fluent Bit on the source host.** If the source host runs Linux and can install packages, ship a small Fluent Bit agent locally and forward to the Telemetron OTel Collector. The `roles/fluentbit/` role on the Telemetron side already accepts forwarded records.
3. **rsyslog / syslog-ng to OTel.** If the source host already speaks syslog, send the syslog stream to the OTel Collector's syslog receiver (operator-supplied receiver config; not pre-rendered in M1).

**Use `nfsd` only when:** the source host is a legacy box, an appliance, or an embedded device that cannot run any of the above but CAN write its logs to a file. The remote host writes log files to an NFS-mounted directory exported by this role; Fluent Bit on the Telemetron host tails those files. This is the "legacy escape hatch" -- not a preferred path.

## What this role does

1. Installs the OS-appropriate NFS server package (`nfs-utils` on RedHat family; `nfs-kernel-server` on Debian family).
2. Enables and starts `nfs-server.service` via systemd.
3. Creates the share root directory `/srv/telemetron-nfs/` (mode `0755`).
4. Creates per-remote-host sub-directories listed in `nfsd_exports` (e.g. `/srv/telemetron-nfs/oldbox/`).
5. Manages `/etc/exports` content via `ansible.builtin.blockinfile` with a stable marker block:

   ```
   # BEGIN TELEMETRON NFSD ANSIBLE MANAGED BLOCK
   /srv/telemetron-nfs/oldbox 10.0.0.42(rw,sync,root_squash,no_subtree_check)
   # END TELEMETRON NFSD ANSIBLE MANAGED BLOCK
   ```

6. Triggers `exportfs -ra` via a handler whenever the marker block content changes.

When `enable_nfsd: false` (default), the role does NOT run at all (gated by `when: enable_nfsd | default(false) | bool` at the play level in `playbooks/deploy_docker.yml`).

When `enable_nfsd: true` but `nfsd_exports: []` (default empty), the NFS server is installed and started but the `/etc/exports` management task is skipped entirely. No exports are exposed until the operator explicitly names a remote host. This is the fail-safe default.

## Inventory knobs

| Variable | Default | Purpose |
|----------|---------|---------|
| `enable_nfsd` | `false` | Master opt-in. When `false`, neither this role NOR the conditional Fluent Bit NFS tail-input runs. |
| `nfsd_share_root` | `/srv/telemetron-nfs` | Root directory for per-remote-host export sub-dirs. Changing this requires a matching change to `roles/fluentbit/files/enrich.lua` (see "How this integrates with Fluent Bit"). |
| `nfsd_exports` | `[]` | List of `{path, allow}` dicts. Each entry is rendered into `/etc/exports`. Default empty = fail-safe (server runs, no exports rendered). |
| `nfsd_protocol` | `nfsv4` | Documentary only. Modern Linux defaults to v4; the role does not explicitly configure protocol versions. |
| `nfsd_service_name` | `nfs-server.service` | Systemd unit name. Same on both RedHat and Debian families. |

## Example: enabling for a single remote host

In `inventory/<your-env>/group_vars/all/nfsd.yml`:

```yaml
enable_nfsd: true
nfsd_exports:
  - path: /srv/telemetron-nfs/oldbox
    allow: "10.0.0.42(rw,sync,root_squash,no_subtree_check)"
```

Then run the deploy playbook with the `nfsd` tag (or the full playbook):

```bash
ansible-playbook -i inventory/<your-env> playbooks/deploy_docker.yml --tags nfsd
```

On the remote host (`10.0.0.42` in this example), mount the export and write logs there:

```bash
sudo mount -t nfs telemetron-host:/srv/telemetron-nfs/oldbox /var/log/forward
# Your legacy app or syslog forwarder writes log files into /var/log/forward/
```

## How this integrates with Fluent Bit

The single `enable_nfsd` knob in inventory flips BOTH this role AND a conditional `[INPUT] tail` block inside `roles/fluentbit/templates/fluent-bit.conf.j2`. When `enable_nfsd: true`:

- Fluent Bit gains an additional `[INPUT] tail` matching `/srv/telemetron-nfs/*/*.log` with `Tag nfs.*`.
- Fluent Bit gains a sibling `[FILTER] lua` block with `Match nfs.*` calling the same `enrich()` function in `roles/fluentbit/files/enrich.lua`.

The Fluent Bit tag-asterisk expansion produces tags like `nfs.srv.telemetron-nfs.oldbox.auth.log` for a file at `/srv/telemetron-nfs/oldbox/auth.log`. The Lua filter splits the tag on `.`:

- `parts[1] = "nfs"`
- `parts[2] = "srv"`
- `parts[3] = "telemetron-nfs"`
- `parts[4] = "oldbox"` (the hostname)
- `parts[5..]` = filename components

The Lua filter extracts `parts[4]` as the `host` Loki label and hardcodes `service_name = "remote"` and `job = "remote-syslog"`. This is the path-derived-label trick: the deterministic share-root depth lets us recover the hostname without parsing the log content.

**Important caveat:** If you change `nfsd_share_root` to a different path depth, you MUST also update the segment index in `roles/fluentbit/files/enrich.lua` (the `parts[4]` constant). This is documented inline in `enrich.lua`. Acceptable for M1; a more robust extraction is a v2 enhancement.

## Supported distros

- RedHat family: RHEL 8+, Rocky Linux 8+, AlmaLinux 8+, CentOS Stream 8+.
- Debian family: Ubuntu 22.04+ (jammy, noble), Debian 11+ (bullseye, bookworm).

**EL7 is intentionally NOT supported.** The upstream port's `yum`-binary workaround for OracleLinux 7 + custom Python install is dropped. Telemetron targets EL8+ throughout.

Other OS families fail fast at the `assert` task with a clear error message.

## Firewall

This role does NOT configure firewalls -- consistent with every other Telemetron role in M1. Firewall policy is the operator's domain.

Required ports:

- TCP `2049` -- NFSv4 server. This is the ONLY port that needs to be reachable from remote hosts. NFSv4 does not require portmapper / rpcbind external exposure.

If your firewall is `firewalld`:

```bash
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --reload
```

If your firewall is `ufw`:

```bash
sudo ufw allow from 10.0.0.0/24 to any port 2049 proto tcp
```

Adjust the source CIDR to match your remote-host subnet.

## Security posture

- **Protocol:** NFSv4 only. NFSv3 (which required rpcbind and an open portmapper) is not used.
- **Auth:** `AUTH_SYS` (Unix UID/GID matching) plus IP allow-list via the `allow` field in each export.
- **No Kerberos.** Kerberos NFS hardening (KDC, service principal, realm) is a v2 milestone item.
- **Acceptable for single-LAN homelab.** This is a deliberate scoping decision: NFSv4 + AUTH_SYS + IP allow-list is reasonable on a trusted LAN with a small number of legacy hosts. It is NOT acceptable on an untrusted network. If your environment requires stronger auth, defer enabling this role until Kerberos lands in a future milestone.

Default mount-option recommendations for the `allow` field of each export entry:

- `rw` -- remote host writes log files into the export.
- `sync` -- writes are durable before the server acknowledges them.
- `root_squash` -- remote root is mapped to nobody; remote root cannot write as local root.
- `no_subtree_check` -- avoids spurious "stale file handle" errors when files are renamed; recommended by Linux NFS docs for modern setups.

## Timezone guidance

Remote hosts SHOULD log in UTC (`Etc/UTC`). Non-UTC timestamps from remote hosts arriving over NFS are a known caveat:

- Fluent Bit's `Time_System_Timezone Etc/UTC` setting governs Fluent Bit's own internal time interpretation, not parsed log-line timestamps.
- If a remote host logs in a DST-observing timezone, log timestamps may shift by an hour across DST boundaries and lose their correct ordering in Loki.

M1 does NOT solve this. If your remote hosts cannot be set to UTC, document the timezone offset and consider whether the legacy-log ingestion is worth the loss of timestamp fidelity. Future hardening (timestamp normalization at the Lua filter) is a v2 candidate.

## Deviations from upstream

This role is a clean-slate port from the upstream Ansible nfsd role that ships with the broader observability stack Telemetron forks. It deviates from that upstream port in several ways, all documented here for transparency:

1. **Host-package, not container (D-91).** This is the ONLY host-package role in Telemetron M1. The obvious container path uses `erichough/nfs-server`, but that image was archived in 2022, requires `--privileged` or `CAP_SYS_ADMIN`, and depends on host kernel NFS modules being loadable from inside the container. Kernel NFS via systemd on the host is simpler, more reliable, and the proven approach upstream relied on as well. This deviation from the "every role is a docker_container" convention is the single biggest M1 deviation and is documented in `meta/main.yml` and here.
2. **EL7 yum-binary workaround dropped.** The upstream `nfs_centos7.yml` contained a `yum`-binary install workaround for OracleLinux 7 with a custom Python install. Telemetron targets EL8+ only, where the standard `ansible.builtin.package` module works without any workaround. EL7 is intentionally unsupported.
3. **Firewall management dropped.** The upstream role manages `firewalld` (on EL) and `ufw` (on Debian) tasks. Telemetron does not -- consistent with every Phase 1-5 role. Firewall is the operator's domain.
4. **`nfs_shares` renamed to `nfsd_exports`.** The upstream variable name lacked a role-namespace prefix. Telemetron uses the role-namespace convention (`nfsd_exports`) so the variable is discoverable from the variable name alone.
5. **Org-specific share root replaced with `/srv/telemetron-nfs`.** Upstream used an organization-prefixed share root inherited from its original deployment. Telemetron uses a brand-neutral root that operators recognize as belonging to this project.
6. **Non-English task names translated to English.** The upstream task `name:` strings were not in English. All task names in this role port are in English, consistent with the project's English-only constraint.

## Gates (Phase 1-5 port acceptance)

The standard Phase 1-5 port-acceptance gates (defined in `roles/README.md` "Per-role port-acceptance gates") apply selectively to this role because it is a host-package role, not a container role:

| Gate | Applies? | Note |
|------|----------|------|
| Gate 1 (upstream-fork-leftover grep + non-ASCII) | YES | Hard zero-match gate. All upstream non-English names translated; org-specific share root replaced. |
| Gate 2 (image pin) | N/A | Host-package, no container image. |
| Gate 3 (secrets discipline) | N/A | No secrets in this role. |
| Gate 4 (idempotency) | YES | `package`, `systemd`, `blockinfile`, `file` chain. Handler-driven `exportfs -ra` with `changed_when: false`. |
| Gate 5 (healthcheck + restart-policy) | N/A as container; YES as systemd | Equivalent contract is `enabled: true, state: started` on `nfs-server.service`. |
| Gate 6 (README schema) | YES | This document. |
| Gate 7 (label-stamp) | N/A | No container, no Docker labels. |
| Gate 8 (parent-dir bind-mount) | N/A | No bind-mounts. |
| Gate 9 (datasources-resolve) | N/A | Not a UI role. |

## Verification

To confirm the role deployed correctly:

```bash
# Service is running
systemctl is-active nfs-server.service
# Expected: active

# Exports are declared (if nfsd_exports is non-empty)
showmount -e localhost
# Expected: list of paths matching nfsd_exports

# /etc/exports contains the marker block
cat /etc/exports
# Expected: BEGIN TELEMETRON NFSD ANSIBLE MANAGED BLOCK ... END ... lines
```

If you set `enable_nfsd: true` but `nfsd_exports: []`, `showmount -e` returns an empty list and `/etc/exports` does not contain the marker block (the export-management task is skipped). This is the fail-safe state -- the NFS server is running but exposing nothing.

## Backup

No operator state to preserve.

## Uninstall

```bash
ansible-playbook playbooks/undeploy_docker.yml --tags nfsd --ask-vault-pass
```

Removes only the `TELEMETRON NFSD ANSIBLE MANAGED BLOCK` from
`/etc/exports` and re-runs `exportfs -ra`. Does NOT:

- remove OS packages (`nfs-kernel-server` on Debian/Ubuntu, `nfs-utils`
  on EL); operators may have installed these before deploying nfsd.
- stop or disable `nfs-server.service`; another service on the host
  may rely on it.
- touch `/srv/telemetron-nfs/` (the share root) or per-remote-host
  subdirectories beneath it; those may hold operator log data that
  arrived via NFS from external hosts.

No purge flag affects nfsd -- it has no container, no Docker volume,
and no Docker image, so `telemetron_purge_data`, `telemetron_purge_images`,
and `telemetron_purge_host_dirs` are all no-ops for this role.

See `docs/quickstart.md#removing-telemetron` for the full undeploy story.
