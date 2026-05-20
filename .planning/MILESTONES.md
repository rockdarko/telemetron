# Milestones

## v1.0.0 — M1 — LGTM observability plane on Docker

**Shipped:** 2026-05-19 (on `leviathan` — Ubuntu 24.04, Docker 29.1.3)
**Phases:** 7 active (1, 2, 3, 4, 04.1, 5, 6) + 4 backlog (999.x deferred to v2)
**Plans:** 26 plans, 110 tasks
**Codebase:** ~12,254 LOC across 139 files in `roles/` + `playbooks/` + `inventory/` + `docs/`
**Commits:** 171 (from `05ef1f8` to `b5eccb3`)
**Timeline:** 2026-05-16 → 2026-05-19 (4 days)

### What shipped

A homelab operator can clone the repo, edit one hostname + SSH-user in
`inventory/example-homelab/`, supply a vault password, run a single
`ansible-playbook` command, and have a complete LGTM observability plane
(Loki + Grafana + Tempo + Mimir + Prometheus + OTel Collector + Fluent Bit +
node_exporter + Alertmanager + Karma + PromLens + MinIO + optional nfsd) come
up on a single Docker host. A synthetic OTLP log + metric + trace pushed to
`:4318` is visible in Grafana within 60 seconds. The full deploy is idempotent
(`changed=0` on the second back-to-back run, both for the 13-role default and
the 14-role `enable_nfsd: true` shape).

### Key accomplishments

- **13 Ansible roles ported + 1 opt-in (nfsd as 14th slot)** from the upstream
  INSPQ stack to clean-slate, English-only, MIT-licensed code — every role
  passes the 8 cross-cutting port-acceptance gates (`roles/README.md`).
- **Three monolithic backends ported** with explicit S3 wiring to MinIO:
  Loki 3.7.2 (`loki-chunks`), Tempo 2.10.5 (`tempo-traces`), Mimir 3.0.6 (the
  trinity `mimir-blocks` / `mimir-ruler` / `mimir-alerts`). All three use
  `-target=all` and the conditional-HEALTHCHECK `-version` pattern.
- **OTel Collector Contrib 0.152.0 as the single ingest gateway** —
  OTLP gRPC `:4317` + HTTP `:4318` fanning to Loki (otlphttp), Tempo (otlp gRPC),
  and Prometheus-or-Mimir; Tempo's native OTLP receivers moved to internal-only
  alt ports `:14317`/`:14318` to avoid the port clash.
- **Grafana 13.0.1 OSS with 4 hardcoded-UID datasources** (`prometheus`,
  `loki`, `tempo`, `mimir`) and 7 curated dashboards covering host-health,
  explore landings, and stack self-metrics; trace ↔ log correlation wired via
  Tempo `tracesToLogsV2` + Loki `derivedFields` on `trace_id`.
- **`playbooks/smoke_test.yml` as the M1 acceptance probe** — synthetic OTLP
  log + metric + trace asserted through Grafana's datasource-proxy within a
  60s budget per signal; passes on leviathan including loud-failure mode and
  tag-scoped single-signal runs.
- **Three operator docs authored against the booted stack** —
  `docs/architecture.md` (component reference + signal flow + 17-row port
  table), `docs/quickstart.md` (zero-to-dashboards walkthrough proven verbatim
  on a fresh host), `docs/inventory.md` (9-key secrets contract + symlink
  pattern + multi-host v2 callout).
- **Two famous bugs caught and fixed in live UAT, encoded as gates**:
  (1) docker_container `auto_remove:true + detach:false` race (ansible/ansible#45272)
      → rewired to `docker_container_exec` polling across 9+ verify.yml files;
  (2) moby/moby#6011 single-file rendered-config bind-mount stale-inode
      → 12 surfaces collapsed to 7 parent-directory mounts; Gate 8 added to
      `roles/README.md` so future ports inherit the convention.

### Known debt at ship (tracked for v2)

- **MinIO** pinned to the archived community release `RELEASE.2025-04-22T22-12-26Z`
  with a loud README note. Garage migration queued as a v2 milestone.
- **Hook router** (Flask + per-rule allowlist + per-tuple rate limit + Jenkins
  buildWithParameters auth) deferred to v2 — tracked as `ALERT-V2-01..05` in
  the archived `v1.0.0-REQUIREMENTS.md`. Phase 4 design preserved in the
  archived `04-DISCUSSION-LOG.md`.
- **PromLens** ships pinned at `v0.3.0` and marked deprecation-candidate in
  its role README — Prometheus 3 absorbs its tree-view surface.
- **amd64-only**; arm64 + Apple Silicon support is a candidate for a later
  milestone (all chosen base images publish arm64 but the testing surface
  was amd64 on leviathan).
- **Monolithic-mode only** for Loki/Tempo/Mimir; distributed mode + HAProxy
  + multi-host inventory are deferred to a later milestone.
- **Backlog 999.x phases** (4 items: mimir blocks_retention re-wire, tempo
  block_ranges_period cleanup, fluentbit timestamp_fallback FB-4 syntax,
  fluentbit label-spec-vs-OTel-reality alignment) — captured during M1
  execution for v2 picking.

### Decimal phase

- **Phase 04.1 (INSERTED)**: rename every `vault_*`-prefixed sensitive variable
  to its role-namespaced unprefixed form across 4 roles + `secrets.yml.example`
  rename + doc cascade. Reason: the prefix added no value and implied tooling
  enforcement Ansible doesn't provide (D-90 in Phase 5 CONTEXT).

### Archived artifacts

- `.planning/milestones/v1.0.0-ROADMAP.md` — full phase details + plan list
- `.planning/milestones/v1.0.0-REQUIREMENTS.md` — all 37 v1 requirements with outcomes
- `.planning/milestones/v1.0.0-phases/` — every shipped phase's plans/summaries/UAT/verification

---
