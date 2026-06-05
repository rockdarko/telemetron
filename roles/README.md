# Roles

Ansible roles, one directory per component. These are forks of the upstream INSPQ roles, normalized to English and stripped of org-specific assumptions.

## Planned roles (port status)

| Role                     | Component                                         | Ported |
|--------------------------|---------------------------------------------------|:------:|
| `alertmanager`           | alert routing                                     | ☑ |
| `fluentbit`              | log shipping                                      | ☑ |
| `grafana`                | dashboards, datasources, provisioning             | ☑ |
| `hook_router`            | Alertmanager -> generic CI/automation webhook bridge (deferred to a future milestone -- see REQUIREMENTS.md ALERT-V2-01..05) | — |
| `karma`                  | alert triage UI                                   | ☑ |
| `loki`                   | log backend (monolithic mode)                     | ☑ |
| `mimir`                  | long-term metrics (monolithic mode)               | ☑ |
| `garage`                 | S3-compatible object storage (Garage v2.3.0)      | ☑ |
| `nfsd`                   | NFS for legacy log ingestion (optional)           | ☑ |
| `node_exporter`          | host metrics exporter (CPU, memory, disk, network, FS) | ☑ |
| `opentelemetry`          | OTel Collector                                    | ☑ |
| `prometheus`             | short-term metrics + alerting eval                | ☑ |
| `tempo`                  | trace backend (monolithic mode)                   | ☑ |

**Dropped from upstream**: `graylog` (legacy aggregator no longer needed), `mongodb` (Graylog's metadata store; no remaining consumer), `mcp` (observability MCP server; not core to the plane), `haproxy` (only useful in distributed mode, which is deferred to a future milestone), `application_web_docker` (Apache vhost pairing binds operators to a single reverse-proxy choice; Telemetron is reverse-proxy-agnostic), and `postgres` (Grafana uses embedded SQLite on a persistent volume for single-host homelab use; Postgres returns only if HA Grafana lands in a later milestone).

**Added vs. upstream**: `node_exporter` (so the stack has a story for scraping the host it runs on), `hook_router` (Alertmanager -> generic CI/automation webhook bridge; was inline upstream; planned for a future milestone, see REQUIREMENTS.md ALERT-V2-01..05).

## Port process per role

1. Copy from upstream checkout (`~/git/inspq/ansible/<role>/` at time of fork).
2. Translate French → English (READMEs, comments, task `name:` strings, variable doc).
3. Strip INSPQ-isms (vault paths, internal domains, NFS share assumptions, Quebec-gov cert chains).
4. Apply locked naming normalizations (`alert_manager` → `alertmanager`, `postgresql-docker` → `postgres`).
5. Add a `roles/<role>/README.md` documenting variables, modes, defaults.
6. Wire into `playbooks/deploy_docker.yml` and/or `playbooks/deploy_kube.yml`.
7. Tick the box above.

## Per-role port-acceptance gates

Before ticking a role's box in the table above, every role port must pass the following checks. These gates were established in Phase 1 (storage role port) and apply to every subsequent role.

**1. Grep gates (zero tolerance — Pitfall 9 from `.planning/research/PITFALLS.md`):**

```bash
# INSPQ fork-leftover gate — must return zero matches
grep -riE 'inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/<name>/

# Non-ASCII character gate — must return zero matches (catches missed translations and accented characters that survived the FR→EN pass)
grep -rPn '[^\x00-\x7F]' roles/<name>/
```

**2. Image-pin gate (OPS-01):** `grep -rE 'image:.*:latest' roles/<name>/` returns zero matches. Every image reference uses an explicit pinned tag.

**3. Secrets-discipline gate (OPS-02):** every sensitive `{{ <role>_<purpose> }}` reference in the role has a matching key declared in `inventory/example-homelab/group_vars/all/secrets.yml.example` with a `CHANGE_ME` placeholder and a comment naming the consuming role. The naming convention is role-namespaced — `<role>_<purpose>` (no `vault_` prefix); per D-90 the prefix added no value and implied tooling enforcement Ansible doesn't provide. The protection mechanism is the operator's choice (ansible-vault, sops, env-var injection, external secret manager, or chmod 600 on a homelab); Telemetron documents keys, not mechanism.

**4. Idempotency gate (OPS-04 + Pitfall 8 from PITFALLS.md):** run the playbook twice in a row against the same target host. The second run's PLAY RECAP must report `changed=0`. Container restarts on config change use handlers (`docker restart <name>` via `community.docker.docker_container_exec` or notify-handler), never `state: restarted`.

**5. Healthcheck + restart-policy gate (OPS-06):** `docker inspect <container> --format '{{.State.Health.Status}}'` returns `healthy`; `docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}'` returns `unless-stopped`. Healthcheck is declared on the container (either via Docker image default or explicit in the role's `community.docker.docker_container` task).

**6. Per-role README gate (OPS-03):** `roles/<name>/README.md` exists and documents (in order): variables (with defaults and purpose), modes (if the role supports any), tags (one per role minimum), volumes (with `telemetron_<role>_*` prefix), healthcheck details (port, interval, timeout, retries), and deprecation notes if applicable. The `roles/garage/README.md` is the canonical template every subsequent role README mirrors.

**7. Telemetron label-stamp gate (Plan 03-05; INGEST-07):** every `community.docker.docker_container` task in a Telemetron role MUST include a `labels:` argument with the two key/value pairs:

```yaml
labels:
  org.telemetron.service: telemetron
  org.telemetron.job: <component>
```

`<component>` matches the role name (e.g. `prometheus`, `loki`, `node_exporter`) so that Fluent Bit's `[FILTER] lua` enrichment (`roles/fluentbit/files/enrich.lua`) picks them up from `/var/lib/docker/containers/<id>/config.v2.json` and ships them as the `service` + `job` Loki labels (INGEST-07 allowlist). Phase 4 (alertmanager) and Phase 5 (grafana, karma) role ports MUST stamp these labels. (The hook_router role is deferred to a future milestone -- see REQUIREMENTS.md ALERT-V2-01..05.) No Docker socket access is added; the Lua filter only reads the bind-mounted JSON files Fluent Bit already tails.

**8. Parent-directory bind-mount convention (Bug-fix 04-02; moby/moby#6011):**

When bind-mounting rendered config files into a container, mount the PARENT DIRECTORY, not individual files. Ansible `template:` / `copy:` modules atomic-rename new inodes into place; Docker's single-file bind pins to the original inode at container start (kernel-fd; see moby/moby#6011, WONTFIX since 2014). Result: host sees new content, container reads old until restart re-binds. Parent-directory mounts resolve the directory entry on every open(), so post-rename inodes are picked up immediately.

Anti-pattern (do NOT use):

```yaml
volumes:
  - "{{ role_config_dir }}/config.yaml:/etc/role/config.yaml:ro"   # bug
```

Convention (use):

```yaml
volumes:
  - "{{ role_config_dir }}:/etc/role:ro"   # parent-directory mount
```

Established in Phase 4 plan 04-02 (see `.planning/debug/prometheus-template-rename-bind-mount-stale-inode.md` for the diagnosis). The 7 afflicted roles (alertmanager, fluentbit, loki, mimir, opentelemetry, prometheus, tempo) were converted in that plan; future role ports inherit this convention.

**9. Datasources-resolve-real-data gate (Plan 05-01; D-73; UI-02 / UI-03 / Gate 9):**

Applies to the `roles/grafana/` role specifically (the only role with cross-component datasource provisioning). The role's verify step MUST:

1. Issue `curl http://grafana:3000/api/datasources/uid/<uid>/health` for each of the four UIDs (`prometheus`, `loki`, `tempo`, `mimir`) and assert HTTP 200 + body containing `"status":"OK"`.
2. Issue one canonical query against each datasource:
   - `prometheus`: `/api/v1/query?query=up` -- expect non-empty `result[]`.
   - `loki`: `/loki/api/v1/query?query={job=~".+"}` -- expect `"status":"success"`.
   - `tempo`: `/api/search?limit=1` -- expect 200 with `"traces":[` or `"results":[` (empty array acceptable as stable state).
   - `mimir`: `/api/v1/query?query=up` (proxied through the mimir datasource which prepends `/prometheus`) -- expect `"status":"success"`.
3. Assert that `/api/datasources/uid/tempo` returns a JSON body containing `tracesToLogsV2` and `trace_id` (UI-04 wiring).
4. Assert that `/api/datasources/uid/loki` returns a JSON body containing `derivedFields` and `"datasourceUid":"tempo"` (UI-04 wiring).

Auth: Basic Auth with admin + `grafana_admin_password`. In-network via `curlimages/curl:8.10.1` one-shot containers on the `telemetron` bridge (D-54 / D-69 pattern). This is THE M1 acceptance heuristic for "everything wired correctly" -- if Grafana boots and Gate 9 passes, the whole pre-Phase-5 stack is validated end-to-end.

**10. Per-role uninstall contract (UNDEPLOY-02; D-148):**

Every deploy role MUST ship a tested uninstall path. The contract has five parts:

(a) `tasks/uninstall.yml` exists in the role and is invocable by the orchestrator via `include_role: { name: <role>, tasks_from: uninstall }` (D-132). The file references role variables from the role's own `defaults/main.yml` directly (D-134) -- no hardcoded container names, no hardcoded paths.

(b) Stops and removes the role's container via `community.docker.docker_container` with `state: absent` and `keep_volumes: true`. The `keep_volumes: true` argument is the explicit mechanism that prevents the docker module from touching the named Docker volume(s) the container is attached to -- the volume is preserved by default per UNDEPLOY-02.

(c) Removes role-private host artifacts under `/opt/telemetron/<role>/` (the role's `<role>_config_dir`) via `ansible.builtin.file` with `state: absent`. Removal is scoped to the role's own subdirectory only; the parent `/opt/telemetron/` is the orchestrator's concern, not the role's (D-144).

(d) Does NOT touch named Docker volumes. The volume-preservation default is the most operator-protective posture for a homelab: an accidental `undeploy` followed by `deploy` re-bootstraps cleanly against surviving data. Wholesale named-volume removal is reserved for Phase 11's `telemetron_purge_data=true` flag, not anything a per-role `uninstall.yml` does.

(e) Idempotent: re-running the uninstall against an already-clean host (container absent, config directory absent) produces `changed=0` in the PLAY RECAP. The mechanism is to trust `state: absent` semantics on the underlying modules (`community.docker.docker_container`, `ansible.builtin.file`, `ansible.builtin.blockinfile`) -- all return `changed: false` when the target is already gone. No `docker_container_info` / `stat` pre-checks (D-141). No `notify:` handlers (D-142) -- the container is being removed, there is nothing to restart. Tasks carry the role tag only, no `<role>-uninstall` sub-tag (D-133).

`nfsd` follows the same contract with its host-package adaptation -- it removes only the Telemetron-managed `/etc/exports` block via `ansible.builtin.blockinfile` with `state: absent` and the IDENTICAL marker string (`# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK`) used by `roles/nfsd/tasks/exports.yml`, then runs `exportfs -ra` so the kernel re-reads its export table. It does NOT remove OS packages (`nfs-kernel-server` / `nfs-utils`), does NOT stop or disable `nfs-server.service`, and does NOT touch `nfsd_share_root` (`/srv/telemetron-nfs/`) or per-remote-host subdirs -- those may hold operator log data that arrived via NFS from external hosts (D-136..D-140).

Orchestrator behaviour -- purge flags (`telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images`), reverse-order role iteration in `playbooks/undeploy_docker.yml`, WARNING messages for irreversible operations -- is out of Gate 10 scope. Phase 11 shipped these as playbook-level concerns and did NOT add a Gate 11; the per-role contract above is sufficient. See `docs/quickstart.md#removing-telemetron` for the operator-facing story. Established in Phase 10 plans 10-01 through 10-05; future role additions inherit this contract.

**11. Per-role backup/restore contract (BACKUP-V13-01..04 + RESTORE-V13-01..04; D-176..D-179):**

Every stateful role MUST ship `tasks/backup.yml` and `tasks/restore.yml` proven on leviathan end-to-end. The 4 stateful roles are: `garage`, `prometheus`, `grafana`, `alertmanager`.

(a) `tasks/backup.yml` performs a cold-quiesce backup: `docker stop` the role's container, write a `zstd`-compressed tarball of the role's named volume(s) into `/opt/telemetron/backups/<role>/<role>-<UTC-ts>.tar.zst`, `docker start` the container, and verify the resulting archive. The stop/tar/start sequence is wrapped in `block:/rescue:/always:` so the container is running at the end regardless of tar success or failure -- a failed backup never leaves a stateful role offline.

(b) `tasks/restore.yml` asserts `backup_restore_confirm == true` as a fail-fast confirm-gate, then runs `tar tf` against the chosen archive for an integrity check, wipes the volume's `_data/` directory, untars the archive in place, restarts the container, and verifies the role is healthy. Every step is bail-out-on-failure; the operator chooses the archive, the role does the rest.

(c) Both `tasks/backup.yml` and `tasks/restore.yml` start with an idempotent `ansible.builtin.package: name: zstd state: present` pre-task so hosts without `zstd` are auto-provisioned on first use and hosts that already have it report `changed: false`.

Stateless roles document their no-backup status in the role's README only -- they do NOT ship empty `tasks/backup.yml` no-op files. The 8 stateless roles are: `loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`, `opentelemetry`, `nfsd`. Of these, `loki` / `tempo` / `mimir` keep their durable data in Garage S3 buckets (covered by the `garage` role's backup); the remaining 5 carry no operator state worth restoring (config is regenerated from inventory on every deploy).

Orchestrator behaviour -- the `backup_continue_on_failure` knob, writer-quiesce on Garage restore (Loki/Tempo/Mimir stop before, restart after), and restore's hardcoded bail-out (`any_errors_fatal: true`) -- is out of Gate 11 scope. Phase 14 shipped these as `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` concerns; the per-role contract above is sufficient. See `docs/quickstart.md#backup-and-restore` for the operator-facing story. Established in Phase 13-14 plans; future role additions inherit this contract.
