# Roles

Ansible roles, one directory per component. These are forks of the upstream INSPQ roles, normalized to English and stripped of org-specific assumptions.

## Planned roles (port status)

| Role                     | Component                                         | Ported |
|--------------------------|---------------------------------------------------|:------:|
| `alertmanager`           | alert routing                                     | ☐ |
| `fluentbit`              | log shipping                                      | ☐ |
| `grafana`                | dashboards, datasources, provisioning             | ☐ |
| `hook_router`            | Alertmanager → CI bridge (new — was inline upstream) | ☐ |
| `karma`                  | alert triage UI                                   | ☐ |
| `loki`                   | log backend (monolithic mode)                     | ☑ |
| `mimir`                  | long-term metrics (monolithic mode)               | ☐ |
| `minio`                  | S3-compatible object storage                      | ☑ |
| `nfsd`                   | NFS for legacy log ingestion (optional)           | ☐ |
| `node_exporter`          | host metrics exporter (CPU, memory, disk, network, FS) | ☐ |
| `opentelemetry`          | OTel Collector                                    | ☐ |
| `prometheus`             | short-term metrics + alerting eval                | ☐ |
| `promlens`               | PromQL editor                                     | ☐ |
| `tempo`                  | trace backend (monolithic mode)                   | ☑ |

**Dropped from upstream**: `graylog` (legacy aggregator no longer needed), `mongodb` (Graylog's metadata store; no remaining consumer), `mcp` (observability MCP server; not core to the plane), `haproxy` (only useful in distributed mode, which is deferred to a future milestone), `application_web_docker` (Apache vhost pairing binds operators to a single reverse-proxy choice; Telemetron is reverse-proxy-agnostic), and `postgres` (Grafana uses embedded SQLite on a persistent volume for single-host homelab use; Postgres returns only if HA Grafana lands in a later milestone).

**Added vs. upstream**: `node_exporter` (so the stack has a story for scraping the host it runs on), `hook_router` (Alertmanager → CI bridge; was inline upstream).

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

**3. Vault-discipline gate (OPS-02):** every `{{ vault_* }}` reference in the role has a matching key declared in `inventory/example-homelab/group_vars/all/vault.yml.example` with a `CHANGE_ME` placeholder and a comment naming the consuming role. The vault naming convention is `vault_<role>_<purpose>`.

**4. Idempotency gate (OPS-04 + Pitfall 8 from PITFALLS.md):** run the playbook twice in a row against the same target host. The second run's PLAY RECAP must report `changed=0`. Container restarts on config change use handlers (`docker restart <name>` via `community.docker.docker_container_exec` or notify-handler), never `state: restarted`.

**5. Healthcheck + restart-policy gate (OPS-06):** `docker inspect <container> --format '{{.State.Health.Status}}'` returns `healthy`; `docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}'` returns `unless-stopped`. Healthcheck is declared on the container (either via Docker image default or explicit in the role's `community.docker.docker_container` task).

**6. Per-role README gate (OPS-03):** `roles/<name>/README.md` exists and documents (in order): variables (with defaults and purpose), modes (if the role supports any), tags (one per role minimum), volumes (with `telemetron_<role>_*` prefix), healthcheck details (port, interval, timeout, retries), and deprecation notes if applicable. The `roles/minio/README.md` written in Phase 1 plan 03 is the canonical template every subsequent role README mirrors.
