# Telemetron architecture

Telemetron is a single-host Docker observability stack deployed via
Ansible. It runs Prometheus + Mimir for metrics, Loki for logs, Tempo for
traces, Grafana for visualization, Alertmanager + Karma for alerts, and
Fluent Bit + OTel Collector for ingestion. The stack is a clean-slate
fork of an internal Quebec-government deployment, normalized to English
and stripped of org-specific assumptions.

## Overview

Single-host Docker deployment. All components run as containers on one
user-defined bridge network (`telemetron`). The OTel Collector is the
single ingress for new instrumentation; Prometheus retains its scrape
model for infrastructure and self-metrics. The three Grafana-stack
backends (Loki, Mimir, Tempo) run in monolithic mode against a single
MinIO S3-compatible object store. Grafana is provisioned with explicit
datasource UIDs (`prometheus`, `loki`, `tempo`, `mimir`) and a curated
set of starter dashboards.

A 13th role (`nfsd`) is shipped as an opt-in host-package NFSv4 server
for operators who need to ingest logs from legacy hosts that cannot run
an OTel SDK or a Fluent Bit agent locally. Default off; flipping a
single inventory knob (`enable_nfsd: true`) wires both the NFS server
and a conditional Fluent Bit tail input over the share root.

## Signal Flow

```
                EXTERNAL: instrumented apps, hosts, browsers
                                |
                                | OTLP gRPC :4317 / OTLP HTTP :4318
                                v
+-----------------------------------------------------------------+
|                          INGEST EDGE                            |
|                                                                 |
|  +---------------+     fwd / OTLP HTTP       +---------------+  |
|  |  Fluent Bit   |--------------------------->| OTel Collector|  |
|  |  tail Docker  |                            |  :4317 gRPC   |  |
|  |  containers + |                            |  :4318 HTTP   |  |
|  |  NFS (opt-in) |                            |  :8888 self   |  |
|  +---------------+                            |  :8889 app    |  |
|                                               +---+---+---+---+  |
|                                                   |   |   |      |
|     +------- Prometheus :9090 --scrape-+          |   |   |      |
|     |  (node_exporter :9100,           |          |   |   |      |
|     |   OTel :8888, OTel :8889)        |          |   |   |      |
|     |                                  |          |   |   |      |
|     |  --remote_write :9009--+         |          |logs|trc|met  |
|     v                        v         |          v   v   v      |
|  +----------+       +---------------+  |   +------+-------+----+ |
|  |  Alert-  |       |     Mimir     |<-+   | Loki | Tempo |Mim.| |
|  | manager  |       |     :9009     |      |:3100 |:3200  |:9009| |
|  |  :9093   |       | (monolithic)  |      |(mono)|(mono) |(mono)| |
|  +----+-----+       +-------+-------+      +--+---+---+---+--+--+ |
|       |                     |                 |       |     |    |
|       | (null)              |                 v       v     v    |
|       v                     |              +---------------------+ |
|     [Karma :8082]           +------------->|       MinIO         | |
|                                            |   S3 API :9000      | |
|                                            |   Console :9001     | |
|                                            |   buckets:          | |
|                                            |     loki-chunks     | |
|                                            |     tempo-traces    | |
|                                            |     mimir-blocks    | |
|                                            |     mimir-ruler     | |
|                                            |     mimir-alerts    | |
|                                            +---------------------+ |
+-----------------------------------------------------------------+
                                ^
                                | HTTP datasource queries
                                | LogQL / TraceQL / PromQL
                                |
+-----------------------------------------------------------------+
|                            UI PLANE                              |
|                                                                  |
|  +-------------+   +----------+   +-----------+                  |
|  |  Grafana    |   |  Karma   |   | MinIO     |                  |
|  |  :3000      |   |  :8082   |   | console   |                  |
|  | (admin/UI)  |   | -> AM    |   |  :9001    |                  |
|  +-------------+   +----------+   +-----------+                  |
+-----------------------------------------------------------------+

Opt-in (default off, enable_nfsd: true):
    [remote host] --writes-to--> /srv/telemetron-nfs/<host>/*.log
        --> Fluent Bit tail input --> OTel Collector --> Loki
```

## Components

| Component | Image | Port (host) | Mode | Purpose |
|-----------|-------|------------:|------|---------|
| MinIO | minio/minio:RELEASE.2025-04-22T22-12-26Z | 9000 / 9001 | single-node | S3-compatible object storage for Loki/Tempo/Mimir |
| Loki | grafana/loki:3.7.2 | 3100 | monolithic (-target=all) | Log backend |
| Tempo | grafana/tempo:2.10.5 | 3200 (HTTP) / 14317-14318 (OTLP internal) | monolithic (-target=all) | Trace backend |
| Mimir | grafana/mimir:3.0.6 | 9009 | monolithic (-target=all) | Long-term metrics |
| OTel Collector | otel/opentelemetry-collector-contrib:0.152.0 | 4317 / 4318 | gateway | OTLP ingest + fan-out |
| Prometheus | prom/prometheus:v3.11.3 | 9090 | scrape + remote_write | Short-term metrics + alerting eval |
| node_exporter | quay.io/prometheus/node-exporter:v1.11.1 | 9100 | host exporter | Host CPU/mem/disk/net/FS |
| Fluent Bit | fluent/fluent-bit:4.2.3 | 2020 (HTTP API) | tail | Docker container log shipping |
| Alertmanager | quay.io/prometheus/alertmanager:v0.32.1 | 9093 | single | Alert routing (null receiver default) |
| Grafana | grafana/grafana-oss:13.0.1 | 3000 | OSS | Dashboards + Explore |
| Karma | ghcr.io/prymitive/karma:v0.130 | 8082 | UI | Alert triage UI |
| nfsd | host package (`nfs-utils` / `nfs-kernel-server`) | 2049 (opt-in) | systemd | Optional NFS server for legacy log ingestion |

## Port Allocation

| Service | Container Port | Host Port |
|---------|---------------:|----------:|
| Grafana | 3000 | 3000 |
| Loki HTTP | 3100 | 3100 |
| Tempo HTTP | 3200 | 3200 |
| OTel OTLP gRPC | 4317 | 4317 |
| OTel OTLP HTTP | 4318 | 4318 |
| Tempo OTLP gRPC (internal) | 14317 | none |
| Tempo OTLP HTTP (internal) | 14318 | none |
| Prometheus | 9090 | 9090 |
| Alertmanager | 9093 | 9093 |
| Karma | 8080 | 8082 |
| Mimir | 9009 | 9009 |
| MinIO API | 9000 | 9000 |
| MinIO Console | 9001 | 9001 |
| node_exporter | 9100 | 9100 |
| Fluent Bit HTTP | 2020 | none (bridge only) |
| NFS (if enabled) | 2049 | 2049 |

Loki, Tempo, and Mimir also expose gRPC ports on the bridge network
(9095, 9096, 9097 respectively) for inter-component traffic; these are
not published to the host.

## Monolithic Mode

The three Grafana-stack backends run as single binaries with `-target=all`:

- **Loki**: distributor, ingester, querier, query-frontend, ruler,
  compactor, and index-gateway in one process; TSDB schema v13; S3
  backend via the MinIO `loki-chunks` bucket. Single replica; no
  memberlist gossip cluster.
- **Tempo**: distributor, ingester, querier, and compactor in one
  process; OTLP receivers bound to internal-only ports (14317/14318) to
  avoid clashing with the OTel Collector's published OTLP ports; S3
  backend via the MinIO `tempo-traces` bucket. Metrics-generator persists
  to a local WAL at `/var/tempo/generator/wal`.
- **Mimir**: distributor, ingester, querier, compactor, ruler, and
  alertmanager-store in one process; multitenancy disabled (single
  anonymous tenant -- no `X-Scope-OrgID` header needed); THREE distinct
  S3 buckets (`mimir-blocks`, `mimir-ruler`, `mimir-alerts`). Mimir
  refuses to start if these stores share a bucket+prefix.

Monolithic mode trades horizontal scalability for operational
simplicity. HA / distributed mode (HAProxy in front of multiple replicas)
is a future-milestone item.

## Storage Dependencies

| Backend | Object store | Bucket(s) | On-disk state |
|---------|--------------|-----------|---------------|
| Loki | MinIO | loki-chunks | `/loki/compactor/markers/` (marker-file persistence) |
| Tempo | MinIO | tempo-traces | `/var/tempo/generator/wal` (metrics-generator WAL) |
| Mimir | MinIO | mimir-blocks, mimir-ruler, mimir-alerts | ingester memory only |
| Prometheus | n/a (TSDB local) | n/a | `/prometheus/data` (15-day retention) |
| Grafana | embedded SQLite | n/a | `telemetron_grafana_data` volume |
| Alertmanager | n/a | n/a | `telemetron_alertmanager_data` volume |
| MinIO | itself | (server) | `telemetron_minio_data` volume |

Named volumes are prefixed `telemetron_<role>_data` to avoid clashes
with other Docker stacks on the same host. Rendered configs live on the
host filesystem at `/opt/telemetron/<role>/` and are bind-mounted
read-only into the corresponding container.

## Known Debt

- **MinIO community edition is archived.** The pinned tag
  (`RELEASE.2025-04-22T22-12-26Z`) is the last published community
  release. A future milestone replaces MinIO with Garage or SeaweedFS.
  Loki, Tempo, and Mimir configurations all target the S3 API, so the
  replacement is contained to the `minio` role.
- **PromLens was removed in v1.0.1.** The bundled Prometheus 3.x UI at
  `http://prometheus:9090/graph` covers the tree-view and query-explorer
  use case that PromLens served in v1.0.0. Upstream had not shipped a
  real release since v0.3.0 (Dec 2022).
- **Hook router is deferred.** The Alertmanager-to-CI webhook bridge is
  a future-milestone item. M1 ships Alertmanager with a `null` default
  receiver; alerts are visible in Karma but not dispatched automatically.
- **MongoDB is dropped.** Was Graylog's metadata store; Graylog is not
  in scope for Telemetron.

## Further reading

- `docs/quickstart.md` -- zero-to-dashboards walkthrough.
- `docs/inventory.md` -- inventory model in depth.
- `roles/<name>/README.md` -- per-component documentation.
