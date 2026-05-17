# Roles

Ansible roles, one directory per component. These are forks of the upstream INSPQ roles, normalized to English and stripped of org-specific assumptions.

## Planned roles (port status)

| Role                     | Component                                         | Ported |
|--------------------------|---------------------------------------------------|:------:|
| `application_web_docker` | shared utility role used as a base                | ☐ |
| `alertmanager`           | alert routing                                     | ☐ |
| `fluentbit`              | log shipping                                      | ☐ |
| `grafana`                | dashboards, datasources, provisioning             | ☐ |
| `haproxy`                | distributed-mode load balancing                   | ☐ |
| `hook_router`            | Alertmanager → CI bridge (new — was inline upstream) | ☐ |
| `karma`                  | alert triage UI                                   | ☐ |
| `loki`                   | log backend (monolithic + distributed)            | ☐ |
| `mcp`                    | observability MCP server                          | ☐ |
| `mimir`                  | long-term metrics                                 | ☐ |
| `minio`                  | S3-compatible object storage                      | ☐ |
| `mongodb`                | dependency for some components                    | ☐ |
| `nfsd`                   | NFS for legacy log ingestion (optional)           | ☐ |
| `opentelemetry`          | OTel Collector                                    | ☐ |
| `postgres`               | Postgres (for Grafana, etc.)                      | ☐ |
| `prometheus`             | short-term metrics + alerting eval                | ☐ |
| `promlens`               | PromQL editor                                     | ☐ |
| `tempo`                  | trace backend (monolithic + distributed)          | ☐ |

**Dropped from upstream**: `graylog` (legacy aggregator no longer needed).

## Port process per role

1. Copy from upstream checkout (`~/git/inspq/ansible/<role>/` at time of fork).
2. Translate French → English (READMEs, comments, task `name:` strings, variable doc).
3. Strip INSPQ-isms (vault paths, internal domains, NFS share assumptions, Quebec-gov cert chains).
4. Apply locked naming normalizations (`alert_manager` → `alertmanager`, `postgresql-docker` → `postgres`).
5. Add a `roles/<role>/README.md` documenting variables, modes, defaults.
6. Wire into `playbooks/deploy_docker.yml` and/or `playbooks/deploy_kube.yml`.
7. Tick the box above.
