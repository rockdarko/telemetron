# Roles

Ansible roles, one directory per component. These are forks of the upstream INSPQ roles, normalized to English and stripped of org-specific assumptions.

## Planned roles (port status)

| Role                     | Component                                         | Ported |
|--------------------------|---------------------------------------------------|:------:|
| `alertmanager`           | alert routing                                     | ☑ |
| `fluentbit`              | log shipping                                      | ☑ |
| `grafana`                | dashboards, datasources, provisioning             | ☑ |
| `hook_router`            | Alertmanager -> generic CI/automation webhook bridge (deferred to a future milestone -- see REQUIREMENTS.md ALERT-V2-01..05) | — |
| `karma`                  | alert triage UI                                   | ☐ |
| `loki`                   | log backend (monolithic mode)                     | ☑ |
| `mimir`                  | long-term metrics (monolithic mode)               | ☑ |
| `minio`                  | S3-compatible object storage                      | ☑ |
| `nfsd`                   | NFS for legacy log ingestion (optional)           | ☐ |
| `node_exporter`          | host metrics exporter (CPU, memory, disk, network, FS) | ☑ |
| `opentelemetry`          | OTel Collector                                    | ☑ |
| `prometheus`             | short-term metrics + alerting eval                | ☑ |
| `promlens`               | PromQL editor                                     | ☐ |
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

Before ticking a role's box in the table above, every role port must pass the following checks. These gates were established in Phase 1 (`minio` role port) and apply to every Phase 2-6 role.

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

**6. Per-role README gate (OPS-03):** `roles/<name>/README.md` exists and documents (in order): variables (with defaults and purpose), modes (if the role supports any), tags (one per role minimum), volumes (with `telemetron_<role>_*` prefix), healthcheck details (port, interval, timeout, retries), and deprecation notes if applicable. The `roles/minio/README.md` written in Phase 1 plan 03 is the canonical template every subsequent role README mirrors.

**7. Telemetron label-stamp gate (Plan 03-05; INGEST-07):** every `community.docker.docker_container` task in a Telemetron role MUST include a `labels:` argument with the two key/value pairs:

```yaml
labels:
  org.telemetron.service: telemetron
  org.telemetron.job: <component>
```

`<component>` matches the role name (e.g. `prometheus`, `loki`, `node_exporter`) so that Fluent Bit's `[FILTER] lua` enrichment (`roles/fluentbit/files/enrich.lua`) picks them up from `/var/lib/docker/containers/<id>/config.v2.json` and ships them as the `service` + `job` Loki labels (INGEST-07 allowlist). Phase 4 (alertmanager) and Phase 5 (grafana, karma, promlens) role ports MUST stamp these labels. (The hook_router role is deferred to a future milestone -- see REQUIREMENTS.md ALERT-V2-01..05.) No Docker socket access is added; the Lua filter only reads the bind-mounted JSON files Fluent Bit already tails.

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
