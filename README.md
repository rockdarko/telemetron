# Telemetron

**One-stop self-hosted observability stack** — driven by Ansible, targeting Docker/VM or Kubernetes/OpenShift.

Bring up a full observability plane on your own hardware in one playbook run:

- **OpenTelemetry Collector** — OTLP ingest and signal routing (traces, metrics, logs)
- **Loki** — log backend (monolithic or microservices mode)
- **Tempo** — distributed traces (monolithic or microservices mode)
- **Prometheus + Mimir** — short-term metrics + long-term retention
- **MinIO** — S3-compatible object storage for Loki / Tempo / Mimir
- **Grafana** — dashboards, exploration, alerting UI
- **Alertmanager + Karma + PromLens** — alert routing, triage UI, PromQL editor
- **Fluent Bit** — log shipping
- **HAProxy** — load balancing for distributed-mode components
- **Hook Router** — bridge from Alertmanager webhooks to your CI/CD for automated runbooks

> **Status: early.** This is a clean-slate fork of an internal Quebec-government deployment originally authored at INSPQ. It's being normalized to English and freed of org-specific assumptions. Don't expect a one-liner installer yet — see the milestone tracker in `docs/` for progress.

## Quick start

> Coming soon as roles land in `roles/`.

## Layout

```
roles/        ansible roles, one directory per component
playbooks/    top-level orchestration (deploy_docker.yml, deploy_kube.yml)
inventory/    one subdirectory per environment; symlink yours in
hooks/        hook router source + sample runbook job definitions
docs/         architecture, alerts catalog, retention strategy, etc.
```

## Inventory model

Each environment is a directory under `inventory/`. See [`inventory/README.md`](inventory/README.md) for the expected shape.

## License

MIT — see [LICENSE](LICENSE).

## Author

Rock Martel-Langlois ([@rockdarko](https://github.com/rockdarko)).
