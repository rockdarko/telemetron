# Phase 1: Foundation & Storage - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship the foundation layer for Telemetron M1: the MinIO object store (with five buckets bootstrapped before any backend can start) and the cross-cutting port-acceptance gates (vault discipline, image pinning, idempotency, healthchecks, INSPQ grep gate, `/opt/telemetron/` config layout, named-volume convention, `telemetron` Docker network, `inventory/example-homelab/group_vars/all/` skeleton) that every Phase 2-6 role port inherits.

Discussion in this phase clarified that two roles originally scoped into M1 — `application_web_docker` and `postgres` — have no consumer in the homelab single-host target and are being dropped, taking the M1 role count from 16 to 14.

</domain>

<decisions>
## Implementation Decisions

### Scope corrections (affect PROJECT.md + REQUIREMENTS.md + ROADMAP.md + roles/README.md)

- **D-01:** Drop the `application_web_docker` role from M1. Upstream INSPQ used it to pair each containerized REST service with an Apache vhost + external URL. That pattern binds operators to one reverse-proxy choice and is not how Rock runs his homelab (he uses Caddy). Telemetron is **reverse-proxy-agnostic** by design — quickstart shows operators reaching services via `http://host:<port>` and lets them slot Caddy/Traefik/nginx/Apache in front themselves.
- **D-02:** Drop the `postgres` role from M1. With Grafana as the only candidate consumer, and Grafana shipping with embedded SQLite that is fully sufficient for single-host homelab use, Postgres has no consumer in M1 (same shape as `mongodb` was dropped because Graylog left). FOUND-03 is **removed** from REQUIREMENTS.md. Grafana (Phase 5) uses SQLite on a persistent volume; Postgres returns as a v2 role only if HA Grafana lands.
- **D-03:** M1 role count is **14**, not 16: `alertmanager, fluentbit, grafana, hook_router, karma, loki, mimir, minio, nfsd, node_exporter, opentelemetry, prometheus, promlens, tempo`. `roles/README.md` table updated to drop `application_web_docker` and `postgres` rows. Add both to PROJECT.md "Out of Scope" with the same reasoning shape as the existing `mongodb` entry. Add "Reverse-proxy configuration / external URL exposure" to PROJECT.md "Out of Scope" so it doesn't sneak back.
- **D-04:** With `application_web_docker` dropped, the `telemetron` Docker bridge network is created in `playbooks/deploy_docker.yml` **pre_tasks** via `community.docker.docker_network` (state: present, idempotent). Roles assume the network exists.
- **D-05:** INV-03 dependency tree updates to drop `application_web_docker` and `postgres` from the role chain. New shape: `[pre_tasks: network] → (minio) → (loki, tempo, mimir) → (prometheus, opentelemetry, fluentbit, node_exporter) → (alertmanager, hook_router) → (grafana, karma, promlens) → nfsd (opt-in)`. Phase 1 ships only `minio` plus the cross-cutting plumbing.

### Shared utilities (replaces application_web_docker — see D-01)
- **D-06:** No shared base role. Each Phase 2-6 role is self-contained, writes its own `community.docker.docker_container` task, and references shared knobs from `inventory/example-homelab/group_vars/all/` (network name, restart policy, healthcheck timing defaults, TZ). Cross-cutting conventions enforced via per-role README schema (OPS-03), `ansible-lint`, and the grep/idempotency gates established in this phase.

### Bucket bootstrap pattern (FOUND-02)
- **D-07:** Bucket bootstrap is the **last task in the `minio` role**, using a one-shot ephemeral `minio/mc` container started via `community.docker.docker_container` with `detach: false, auto_remove: true`. Container joins the `telemetron` network, runs `mc alias set local http://minio:9000 ... && mc mb --ignore-existing local/loki-chunks local/tempo-traces local/mimir-blocks local/mimir-ruler local/mimir-alerts`, exits 0 on success. Non-zero exit fails the playbook.
- **D-08:** Downstream backend roles (Phase 2 `loki`/`tempo`/`mimir`) wait on **serial role ordering in `deploy_docker.yml`** — the `minio` role exits only after bootstrap returns 0. No async, no `meta: flush_handlers`, no extra polling. The playbook ordering IS the gate.
- **D-09:** Bootstrap container uses MinIO root credentials from vault: `vault_minio_root_user` + `vault_minio_root_password` (later renamed to `minio_root_user` / `minio_root_password` in Phase 4.1 / D-90) injected as env vars on the ephemeral container. Per-backend access-key topology is deferred (root creds are reused by Loki/Tempo/Mimir for now; can be split into per-backend users in a future hardening phase if blast-radius becomes a concern).
- **D-10:** Before the mc bootstrap fires, an `ansible.builtin.uri` pre-task polls `http://<host>:9000/minio/health/ready` with `until: result.status == 200, retries: 30, delay: 2` to guarantee MinIO is actually answering. Belt-and-suspenders relative to MinIO's own Docker HEALTHCHECK; cheap, kills startup race.
  - **D-10a (amended 2026-05-17, during Phase 1 plan-revision iteration 1):** Pre-poll implementation uses `community.docker.docker_container_info` reading the container's own `State.Health.Status` field (waiting for `healthy`) because D-13's no-host-publish model makes the original `ansible.builtin.uri` approach unreachable from the control host (port :9000 is not bound to any host interface). Same intent (don't fire mc until MinIO is actually ready), cleaner mechanism — and it leverages the Docker HEALTHCHECK that OPS-06 already mandates exist on every container. Implemented in `roles/minio/tasks/bootstrap.yml` Step 1.
- **D-11:** mc image pinned to `minio/mc:RELEASE.2025-04-22T16-23-26Z` paired with the MinIO server pin. Listed in `roles/minio/defaults/main.yml` alongside the server pin. OPS-01 image-pin discipline applies to both.

### Host binding & exposure (security model — propagates to Phase 2-5)
- **D-12:** **Default for every role: no host port publish.** Inter-component traffic happens over the `telemetron` Docker network via DNS (e.g. Loki reaches MinIO at `http://minio:9000`). Operator access is via SSH local-forward or `docker exec`.
- **D-13:** **MinIO specifically: zero host publish.** Neither `:9000` (S3 API) nor `:9001` (console) is published to the host. Console access via `ssh -L 9001:localhost:9001 host`. Eliminates the "anyone on the LAN can reach my S3" failure mode.
- **D-14:** Each role exposes a `<role>_publish_host` knob in `inventory/example-homelab/group_vars/all/<role>.yml` defaulting to `false` (or `127.0.0.1` for UIs like Grafana when their phase lands). Operator overrides per-service to publish; documented per role README. Pitfalls research lists default-`0.0.0.0` as the recurring security mistake; this convention inverts it.

### Inventory & volumes (INV-02 + Pitfall #12)
- **D-15:** `inventory/example-homelab/group_vars/all/` split by domain:
  - `network.yml` — `telemetron_network: telemetron`, `telemetron_publish_default: false`, `telemetron_tz: Etc/UTC`
  - `storage.yml` — `telemetron_volume_prefix: telemetron`, bucket names, retention defaults
  - `vault.yml.example` — every `vault_*` key (per OPS-02 naming) with `CHANGE_ME` placeholder + inline comment of which role consumes it  *(later renamed to `secrets.yml.example` with `vault_*` -> `<role>_*` keys in Phase 4.1 / D-90)*
  - `<role>.yml` per role — role-specific overrides (knobs operators commonly tune)
- **D-16:** Data volumes are **named Docker volumes** with `telemetron_` prefix: `telemetron_minio_data`, `telemetron_loki_data`, `telemetron_tempo_data`, `telemetron_mimir_data`, `telemetron_grafana_data`, `telemetron_prometheus_data`, `telemetron_alertmanager_data` (Karma uses BoltDB inside its own ephemeral volume; PromLens is stateless; node_exporter is stateless; Fluent Bit has a `telemetron_fluentbit_buffer` volume for its file buffer).
- **D-17:** Each component's volume covers the **full data root** of that component (not a subdir). For Loki specifically: one volume mounted at `/var/loki` covers wal + chunks + index + compactor markers — Pitfall #12 (marker-file loss on container recreate) is satisfied by-construction. Documented in each role's README under "Volumes".
- **D-18:** Rendered role configs (Jinja-templated YAML/JSON) bind-mounted from host at `/opt/telemetron/<role>/<file>` (**flat** layout, no nested `config/` subdir). Container mounts read-only at canonical path (e.g. host `/opt/telemetron/loki/loki.yaml` → container `/etc/loki/loki.yaml`). Operator does `cat /opt/telemetron/loki/loki.yaml` to debug, can diff after re-running the playbook. Single host-visible tree (`/opt/telemetron/`) for the whole stack.

### Cross-cutting plumbing (already locked upstream, restated for completeness)
- **D-19:** Container module: `community.docker.docker_container` for every role. Pitfall #8 (`state: restarted` non-idempotency) avoided — config-change restarts happen via handlers that `docker restart <name>` the running container, never via `state: restarted` or container recreation.
- **D-20:** Jinja templates iterate sorted dict keys (`{% for k in d.keys() | sort %}`) for deterministic output, per OPS-04.
- **D-21:** Grep gates established in this phase, enforced on every subsequent role port: `grep -riE 'inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/<name>/` and `grep -rPn '[^\x00-\x7F]' roles/<name>/` both return zero matches. Documented in `roles/README.md` "Port process".

### Claude's Discretion
- Exact `ansible-lint` ruleset/profile (start with `production` profile; tune as warnings surface).
- Per-role tagging granularity (start with one tag per role for `--tags <role>` — sub-tags for `<role>-config` vs `<role>-container` can be added per role if reload-without-restart becomes useful).
- Per-role healthcheck timing details (`interval`, `timeout`, `retries`) — defaults from upstream image conventions, tuned only if start-up races appear.
- Vault file split (single `vault.yml` per inventory vs per-role `vault_<role>.yml`) — start with single `vault.yml` since M1 has ~5-7 secrets total; revisit if it grows past 15.
- MinIO `MINIO_BROWSER_REDIRECT_URL` and similar UI knobs — defaults until an operator needs them.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project framing & scope
- `.planning/PROJECT.md` — Vision, constraints, locked tech stack, key decisions table. Update post-phase to add the dropped roles to "Out of Scope" and reflect the 14-role count.
- `.planning/REQUIREMENTS.md` — Phase 1 REQ-IDs (FOUND-01, FOUND-02, OPS-01..06, INV-02). **FOUND-03 to be removed** when this phase's plans land; traceability table updates accordingly.
- `.planning/ROADMAP.md` §"Phase 1: Foundation & Storage" — Goal, success criteria, role list. Update INV-03 dependency tree per D-05.

### Research backing for this phase
- `.planning/research/PITFALLS.md` §"Pitfall 1: MinIO bucket / Loki-Tempo-Mimir start-order race" — Direct backing for D-07..D-11 bucket bootstrap design.
- `.planning/research/PITFALLS.md` §"Pitfall 8: Ansible role idempotency cascades" — Backing for D-19 handler-not-restart convention; per-role `--check --diff` double-run gate.
- `.planning/research/PITFALLS.md` §"Pitfall 9: Fork-from-INSPQ leftovers" — Backing for D-21 grep gates.
- `.planning/research/PITFALLS.md` §"Pitfall 12: Loki compactor marker-file loss on container recreate" — Backing for D-17 "full data root, one volume" rule (consumed by Phase 2 Loki).
- `.planning/research/PITFALLS.md` §"Security Mistakes" — Backing for D-12..D-14 default-network-only exposure model.
- `.planning/research/STACK.md`, `.planning/research/FEATURES.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/SUMMARY.md` — Component pins, port allocation, signal-flow context.

### Upstream INSPQ source-of-truth (for porting)
- `~/git/inspq/ansible/minio/` (operator's workstation, **not** in repo) — Source role to port for Phase 1 (translation + INSPQ-stripping + naming normalization per `roles/README.md` port process).
- Note: `~/git/inspq/ansible/application_web_docker/` and `~/git/inspq/ansible/postgresql-docker/` are **NOT** ported — see D-01, D-02.

### Ansible module documentation
- [community.docker.docker_container module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_module.html) — Primary module for every role.
- [community.docker.docker_network module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_network_module.html) — Used by `deploy_docker.yml` pre_tasks for the `telemetron` network.

### Upstream specs for pinned images
- MinIO archived release `RELEASE.2025-04-22T22-12-26Z` — confirmed last community release.
- `minio/mc` release `RELEASE.2025-04-22T16-23-26Z` — paired bootstrap CLI pin.

### Locked naming normalizations
- git commit `ba836d2` — `alert_manager` → `alertmanager`, `postgresql-docker` → `postgres` (and other renames). Phase 1 sets the convention for vault keys (`vault_<role>_<purpose>` -- later changed to role-namespaced `<role>_<purpose>` in Phase 4.1 / D-90), volumes (`telemetron_<role>_data`), config dirs (`/opt/telemetron/<role>/`), tags (one per role).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- None yet — repo holds only scaffolding (`roles/README.md`, `inventory/README.md`, `playbooks/README.md`, `hooks/README.md`, top-level `README.md`, `LICENSE`, `.planning/`). Phase 1 lays the foundations every subsequent role consumes.

### Established patterns (to establish in this phase)
- **Role layout** — standard Ansible (`defaults/main.yml`, `tasks/main.yml`, `handlers/main.yml`, `templates/`, `meta/main.yml`, `README.md`). Set the pattern in the `minio` role; every subsequent role mirrors it.
- **Vault references** — `{{ vault_<role>_<purpose> }}` per OPS-02. `minio` role establishes `vault_minio_root_user`, `vault_minio_root_password`. *(Convention later changed to role-namespaced `<role>_<purpose>` in Phase 4.1 / D-90; this CONTEXT.md is preserved as institutional memory.)*
- **Volume references** — `{{ telemetron_volume_prefix }}_<role>_data` resolves to `telemetron_<role>_data` via `storage.yml`.
- **Config bind-mount** — host `/opt/telemetron/<role>/` → container canonical path.
- **Restart-by-handler** — handlers in `roles/<role>/handlers/main.yml` notify `docker restart <name>` (or `community.docker.docker_container_exec` for graceful reload where the binary supports it); never `state: restarted`.
- **Per-role README schema** — variables, modes, defaults, tags, volumes, healthcheck, deprecation notes (if any). `minio` README is the template; every subsequent role README follows the same schema. Documented in `roles/README.md`.
- **Image pin location** — every image+tag in `roles/<role>/defaults/main.yml` with a comment linking the upstream release notes.

### Integration points
- `playbooks/deploy_docker.yml` pre_tasks — `community.docker.docker_network` (telemetron). First non-fact-gathering task in any deploy.
- `inventory/example-homelab/group_vars/all/{network,storage,vault.example}.yml` + `<role>.yml` files — operator's API surface.
- `roles/minio/tasks/main.yml` final task — the bucket-bootstrap one-shot mc container. Serves as the hard gate Phase 2 backends depend on.

</code_context>

<specifics>
## Specific Ideas

- Rock runs his homelab with Caddy (not Apache); operators using Traefik/nginx/Apache are all first-class. Quickstart docs (Phase 6) demonstrate `http://host:3000` and explicitly say "operator's choice of reverse proxy goes here."
- `/opt/telemetron/` as the single host-visible tree (matches Rock's existing homelab convention; matches FHS spirit for add-on stacks; mirrors conventions like `/opt/gitea`, `/opt/portainer`).
- "Run twice in a row, second run is `changed=0`" — port-acceptance gate per role, written into `roles/README.md` port process. Established in Phase 1 on `minio`.
- "Open one Grafana dashboard in a fresh browser session — every panel must render real data" — final M1 smoke (Phase 6) but the pattern is set here: don't tick a role's box without one human-visible verification.
- INSPQ grep gate is non-negotiable per role port. The whole project literally cannot ship without it; the README promises a clean fork.

</specifics>

<deferred>
## Deferred Ideas

### Out of M1 (route to PROJECT.md "Out of Scope")
- **`application_web_docker` role** — INSPQ-specific Apache vhost pairing. Telemetron is reverse-proxy-agnostic.
- **`postgres` role** — No M1 consumer once Grafana uses SQLite. Returns as a v2 role only if HA Grafana lands (requires shared backing store across multiple Grafana instances).
- **Reverse-proxy configuration / external URL exposure** — Operator's choice; quickstart shows direct `http://host:<port>` and lets operators slot their own RP.

### Deferred within the project (future milestones / phases)
- **Per-backend MinIO access keys** — D-09 reuses root creds for Loki/Tempo/Mimir for now. Splitting into per-backend users with bucket-scoped policies reduces blast radius on cred leak. Hardening phase candidate.
- **MinIO replacement (Garage / SeaweedFS)** — Already in PROJECT.md Key Decisions; queued for a future milestone.
- **Backups** — Named volumes survive container lifecycle but no automated backup story in M1. `docker run --rm -v telemetron_<role>_data:/src ... tar` is the documented escape hatch.
- **HA Grafana + Postgres** — v2 territory.
- **Vault file split (per-role `vault_<role>.yml`)** — Reconsider if M1's ~5-7 secrets grow past 15. *(After Phase 4.1 / D-90, naming would be per-role `secrets_<role>.yml` if the split happens.)*
- **Sub-tags within roles (`<role>-config` vs `<role>-container`)** — Add per role only if reload-without-restart becomes useful.

### Reviewed Todos (not folded)
None — `gsd-tools todo match-phase 1` returned zero matches.

</deferred>

---

*Phase: 01-foundation-storage*
*Context gathered: 2026-05-17*
