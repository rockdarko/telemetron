# Requirements: Telemetron

**Milestone:** v1.2.0 — Operator Undeploy Path
**Defined:** 2026-05-28
**Core Value:** A homelab operator can clone the repo, edit one hostname in the example inventory, run a single Ansible playbook, and end up with a working observability plane on a single Docker host. **And** when they're done evaluating, can run a single symmetric playbook to cleanly remove it.

## v1.2.0 Requirements

Requirements for the v1.2.0 patch milestone. Each maps to roadmap phases.

### Orchestrator (UNDEPLOY)

- [x] **UNDEPLOY-01**: `playbooks/undeploy_docker.yml` exists at the repo root and runs successfully against both `inventory/example-homelab` and `inventory/leviathan`. Default run with no extra-vars stops + removes the 12 deployed containers (alertmanager, fluentbit, garage, grafana, karma, loki, mimir, node_exporter, opentelemetry, prometheus, tempo, plus `nfsd` only if `enable_nfsd: true` is set) and removes the `telemetron` Docker bridge network. Roles execute in reverse dependency order from `deploy_docker.yml`. Same `--ask-vault-pass` UX. Same `--tags <role>` targeted-re-run pattern (operator can undeploy a single role).

- [ ] **UNDEPLOY-02**: Every deploy role has a `tasks/uninstall.yml` (or equivalent removal task block) that stops + removes its container, removes any role-private files/directories it created during deploy (config dir under `/opt/telemetron/<role>/` if the role created one), and does NOT touch the named Docker volume by default. The contract is documented as a new gate in `roles/README.md` alongside the existing 8 cross-cutting gates: every deploy role MUST ship a tested uninstall path. `nfsd` follows the same contract for its host-package cleanup (only if it was installed by this role; do not auto-purge OS packages the operator may have had pre-existing).

### Safety + data preservation (PURGE)

- [x] **PURGE-01**: Conservative-by-default — the default `undeploy_docker.yml` run preserves all named Docker volumes (`telemetron_garage_data`, `telemetron_grafana_data`, `telemetron_loki_data`, `telemetron_tempo_data`, `telemetron_mimir_data`, `telemetron_alertmanager_data`, `telemetron_prometheus_data`, `telemetron_karma_data` if any, plus any other volumes the roles created), the `/opt/telemetron/` host directory tree, and the pinned Docker images. After a default undeploy, `docker volume ls | grep telemetron_` returns the same list as before.

- [x] **PURGE-02**: Opt-in irreversible flags — `telemetron_purge_data=true` removes every named Docker volume under the `telemetron_*` prefix; `telemetron_purge_host_dirs=true` removes the `/opt/telemetron/` tree on the host; `telemetron_purge_images=true` removes the pinned Docker images (only the exact pinned tags Telemetron deployed — not other tags of the same image that an operator may have pulled separately). Each flag is opt-in via `--extra-vars`; combining them is supported. Each flag emits a one-line "WARNING: irreversible" pre-task message before acting so operators see what they're about to lose. Garage S3 credential file at `{{ garage_config_dir }}/s3-credentials` is purged when `telemetron_purge_host_dirs=true` (the file lives under `/opt/telemetron/garage/`).

### Idempotency + recovery (OPS)

- [x] **OPS-01**: Back-to-back undeploy of an already-clean host produces `changed=0` in the PLAY RECAP — matches the v1.0/v1.1 idempotency quality bar for the deploy side. A re-run after a partial deploy (e.g. only garage + loki are up, the rest of the playbook failed mid-way) cleanly removes whatever is present and reports `failed=0`.

- [x] **OPS-02**: An undeploy followed by a fresh deploy successfully brings the stack back up — `playbook deploy_docker.yml` after `playbook undeploy_docker.yml` (default conservative purge) results in a healthy 12-container stack. If `telemetron_purge_data=true` was used, the re-deploy starts from scratch (Garage bootstrap creates a new S3 key, Loki/Tempo/Mimir start with empty buckets, Grafana SQLite is re-created, etc.).

### Documentation (DOCS)

- [x] **DOCS-01**: `docs/quickstart.md` gains a top-level `## Removing Telemetron` section placed after `## Upgrade notes` and before `## Building your own inventory`. Covers: (a) the default conservative-purge command line, (b) the three opt-in purge flags with examples, (c) order-of-operations expectation (containers come down before volumes can be purged), (d) the manual `docker volume rm` / `docker image rm` fallback for operators who'd rather not use the playbook. Tone matches existing operator-facing prose (factual, no marketing voice, no emojis).

- [x] **DOCS-02**: Root `README.md` Quick Start section gains a "When you're done evaluating" line linking to `docs/quickstart.md#removing-telemetron`. Each deployed role's `README.md` (12 + nfsd) gains a one-line "Uninstall: see `playbooks/undeploy_docker.yml --tags <role>`" in its Operator Surface section (or equivalent). `roles/README.md` documents the new "every deploy role ships a tested uninstall path" gate alongside the existing 8 gates.

## Future Requirements

Deferred to later milestones. Tracked but not in current roadmap.

### Preflight + validation (PREFLIGHT-V13-01..03)

- **PREFLIGHT-V13-01**: `playbooks/preflight_check.yml` — verifies Docker version, port availability, disk space, prior Telemetron state, and BYO-inventory wiring before a fresh deploy
- **PREFLIGHT-V13-02**: Doctor command — diagnostic output for a running stack (healthcheck status of every container, S3 reachability, Grafana datasource health)
- **PREFLIGHT-V13-03**: Inventory linter — fast pre-deploy sanity check on operator-supplied inventory (required keys present, syntactically valid)

### Backup + restore (BACKUP-V13-01..04)

- **BACKUP-V13-01**: Backup playbook — stops the stack, snapshots Garage S3 buckets via `mc cp` or `rclone sync`, exports Prometheus TSDB, Grafana SQLite, Alertmanager state, and restarts. Single tarball output to operator-specified path.
- **BACKUP-V13-02**: Restore playbook — inverse of BACKUP-V13-01 against a fresh host with the playbook already deployed
- **BACKUP-V13-03**: Per-component backup tasks reusable from operator-supplied wrappers
- **BACKUP-V13-04**: Documentation — recovery guide, disaster-recovery scenarios, what to back up vs what's regenerable

### Secrets rotation (SECRETS-V13-01..02)

- **SECRETS-V13-01**: Rotate Garage admin token, RPC secret, and S3 key without data loss
- **SECRETS-V13-02**: Rotate Grafana admin password, Prometheus bearer tokens (Garage scrape, future hook router)

### Carried forward from prior milestones

- **ALERT-V2-01..05** — Hook router (Alertmanager webhook → CI bridge)
- **DIST-01..03** — Multi-host distributed-mode Loki/Tempo/Mimir, HAProxy role, Kubernetes/OpenShift deployment path
- **ARCH-01..02** — arm64 / Pi 5 / Apple Silicon support, multi-arch CI matrix
- **DOCS-V2-01..07** — Alerts reference, retention deep-dive, FB timestamps deep-dive, hook router config, instrumentation guide, INSPQ migration guide, metrics reference

## Out of Scope

Explicitly excluded from v1.2.0. Documented to prevent scope creep.

| Feature | Reason |
|---|---|
| Backup + restore of stateful volumes | Deferred to v1.3.0 — BACKUP-V13-01..04. Bundling backup with undeploy would force decisions about backup format, storage location, and restore semantics that deserve their own milestone scope. The undeploy-with-purge irreversibility note in `docs/quickstart.md` will mention that backup is the operator's responsibility until then. |
| Preflight check playbook | Deferred to v1.3.0 — PREFLIGHT-V13-01..03. Preflight is the symmetric "before-deploy" hardening; logically pairs with deploy but doesn't gate the undeploy story. |
| Doctor / health-check diagnostic command | Deferred to v1.3.0 — PREFLIGHT-V13-02. Out-of-band live state inspection is independent of the deploy/undeploy lifecycle. |
| Secrets rotation playbook | Deferred to v1.3.0 — SECRETS-V13-01..02. Rotation tooling is orthogonal to undeploy. |
| Container-restart-as-a-feature (`telemetron_state: restarted`) | Out for v1.2.0. Operators restart containers today via `docker restart` or `ansible-playbook ... --tags <role>` which re-triggers the existing notify handlers. A dedicated restart playbook is operator convenience, not new capability. |
| Tearing down Telemetron on a host where it was deployed by a different inventory | Out — undeploy is scoped to "same inventory deployed it, same inventory removes it." Cross-inventory undeploy is undefined behavior; operators can use the manual `docker stop / rm` path documented as the fallback. |
| Kubernetes / OpenShift undeploy | Out — Telemetron has no K8s deployment path yet; undeploy follows whenever deploy lands. |
| arm64 / multi-arch validation of the undeploy path | Out — leviathan is amd64 (matches the deploy validation surface). |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| UNDEPLOY-01 | Phase 11 | Complete |
| UNDEPLOY-02 | Phase 10 | Pending |
| PURGE-01 | Phase 11 | Complete |
| PURGE-02 | Phase 11 | Complete |
| OPS-01 | Phase 11 | Complete |
| OPS-02 | Phase 11 | Complete |
| DOCS-01 | Phase 12 | Complete |
| DOCS-02 | Phase 12 | Complete |

**Coverage:**
- v1.2.0 requirements: 8 total
- Mapped to phases: 8 (roadmap complete)
- Unmapped: 0

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 — phase mapping complete (Phases 10, 11, 12).*
