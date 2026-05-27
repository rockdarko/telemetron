# Telemetron

**Self-hosted observability in one playbook.** Bring up Prometheus + Loki +
Tempo + Grafana + Alertmanager on your own hardware with one Ansible
command. Single-host Docker. Homelab-friendly.

## Quick start

```bash
git clone https://github.com/rockdarko/telemetron.git && cd telemetron
# edit inventory/example-homelab/hosts.yml (one hostname + SSH user)
# copy + fill secrets.yml from inventory/example-homelab/group_vars/all/secrets.yml.example
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml \
  --ask-vault-pass
```

Full walkthrough with prerequisites, expected outputs, and troubleshooting:
[`docs/quickstart.md`](docs/quickstart.md).

After the deploy, validate with the included smoke test:

```bash
ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml \
  --ask-vault-pass
```

The smoke test pushes a synthetic log + metric + trace through the stack
and confirms visibility in Grafana within 60 seconds.

## What's included

| Component | Image | Purpose |
|-----------|-------|---------|
| OpenTelemetry Collector | `otel/opentelemetry-collector-contrib:0.152.0` | OTLP ingest and signal fan-out |
| Loki | `grafana/loki:3.7.2` | Log backend (monolithic mode) |
| Tempo | `grafana/tempo:2.10.5` | Trace backend (monolithic mode) |
| Mimir | `grafana/mimir:3.0.6` | Long-term metrics (monolithic mode) |
| Prometheus | `prom/prometheus:v3.11.3` | Short-term metrics + alert evaluation |
| node_exporter | `quay.io/prometheus/node-exporter:v1.11.1` | Host metrics |
| Fluent Bit | `fluent/fluent-bit:4.2.3` | Container log shipping |
| Garage | `dxflrs/garage:v2.3.0` | S3-compatible object storage |
| Alertmanager | `quay.io/prometheus/alertmanager:v0.32.1` | Alert routing (null receiver default) |
| Grafana | `grafana/grafana-oss:13.0.1` | Dashboards + Explore |
| Karma | `ghcr.io/prymitive/karma:v0.130` | Alert triage UI |
| nfsd (opt-in) | host package (`nfs-utils` / `nfs-kernel-server`) | Optional NFS server for legacy log ingestion |

Architecture detail: [`docs/architecture.md`](docs/architecture.md).

### Not in M1

- **PromLens** was bundled in v1.0.0 for upstream-INSPQ parity and removed in v1.0.1 after confirming the upstream repo has been Dependabot-only since December 2022. Prometheus 3.x's native UI at `http://prometheus:9090/graph` covers the PromQL tree-view and query-explorer use case.
- **Hook router** (Alertmanager -> CI/automation webhook bridge) is deferred to a future milestone. Alerts are visible in Karma but not auto-dispatched.
- **HAProxy** (load balancing for distributed-mode backends) is only useful when Loki / Mimir / Tempo run in microservices mode, which is a future-milestone deployment topology.
- **Kubernetes / OpenShift deployment path** is a future milestone; M1 ships the Docker path only.
- **Multi-host inventory** is a future milestone; M1 ships a single-host example.

## Requirements

- Ansible 2.15+
- `community.docker` collection 4.x+
- Docker 24+ on the target host (27+ recommended)
- SSH key-based access; passwordless `sudo` if applicable
- One Docker host (homelab box, VM, or bare metal)

## Layout

```
roles/        Ansible roles, one directory per component
playbooks/    deploy_docker.yml (orchestrator) + smoke_test.yml (acceptance)
inventory/    one subdirectory per environment; symlink yours in
docs/         architecture, quickstart, inventory model
```

## Inventory model

Each environment is a directory under `inventory/`. The shipped example
is `inventory/example-homelab/`. Build your own from scratch or symlink
an out-of-tree inventory in: see [`docs/inventory.md`](docs/inventory.md).

## Origin

Telemetron is a clean-slate fork of an internal observability stack
originally authored at INSPQ (Quebec public health institute). The fork
has been normalized to English, stripped of org-specific assumptions
(vault paths, internal domains, NFS share roots, cert chains), and
re-licensed MIT. The component selection, monolithic-mode deployment
shape, and Ansible-driven orchestration are inherited; the role
implementations are rewritten against current upstream image versions
and homelab-first defaults.

## License

MIT -- see [LICENSE](LICENSE).

## Author

Rock Martel-Langlois ([@rockdarko](https://github.com/rockdarko)).
