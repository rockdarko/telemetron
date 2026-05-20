---
phase: 05-ui-plane
plan: "03"
subsystem: ui
tags: [promlens, promql, deprecation, ansible, docker, telemetron]

# Dependency graph
requires:
  - phase: 05-01-grafana
    provides: Grafana role port, Gate 9 datasource verification pattern, D-82 UI plane publish-default exemption
  - phase: 05-02-karma
    provides: karma role pattern for stateless CLI-flag container, roles/README.md karma row, playbook karma entry
provides:
  - roles/promlens/ (6 files): pure-CLI stateless PromLens v0.3.0 Ansible role
  - inventory/example-homelab/group_vars/all/promlens.yml: operator tunable surface
  - Phase 5 UI Plane completion (3/3 plans; UI-01..UI-06 all delivered)
affects: [06-orchestration-docs, nfsd, quickstart-doc]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-CLI role pattern: no templates/ dir, no config file, no bind mounts -- PromLens configured entirely via docker_container command: list (kingpin flags)"
    - "Explicit HEALTHCHECK on root / path for images with no /health endpoint and no built-in HEALTHCHECK (prom/promlens:v0.3.0)"
    - "Deprecation-candidate role: DEPRECATION CANDIDATE banner at top of README, --skip-tags guidance, role still ships for upstream parity"

key-files:
  created:
    - roles/promlens/defaults/main.yml
    - roles/promlens/tasks/main.yml
    - roles/promlens/tasks/verify.yml
    - roles/promlens/handlers/main.yml
    - roles/promlens/meta/main.yml
    - roles/promlens/README.md
    - inventory/example-homelab/group_vars/all/promlens.yml
  modified:
    - inventory/example-homelab/group_vars/all/network.yml
    - playbooks/deploy_docker.yml
    - roles/README.md
    - .planning/ROADMAP.md

key-decisions:
  - "PromLens uses CLI flags only (kingpin) -- no PROMLENS_DEFAULT_BACKEND_URL env var (RESEARCH §2.3 correction over CONTEXT.md Claude's Discretion line 152)"
  - "Explicit HEALTHCHECK required: prom/promlens:v0.3.0 image has no built-in HEALTHCHECK; probe uses wget --spider on root / (no /health endpoint per RESEARCH §2.3)"
  - "D-25 audit: Grafana service-account integration dropped entirely from M1 (no --grafana.url / --grafana.api-token); adds secrets surface for no M1 value on a deprecation-candidate role"
  - "Stateless: no templates/ dir, no files/ dir, no volume, no bind mounts -- pure CLI flags at docker_container command: time"
  - "Deprecation-candidate posture: README opens with DEPRECATION CANDIDATE banner; --skip-tags promlens guidance provided; nothing in stack depends on PromLens"

patterns-established:
  - "Pure-CLI role pattern: useful for any future role that uses an image configured entirely by CLI flags (no config file to render)"

requirements-completed: [UI-06]

# Metrics
duration: 8min
completed: 2026-05-19
---

# Phase 5 Plan 3: PromLens Role Port Summary

**PromLens v0.3.0 Ansible role (pure-CLI, stateless, deprecation-candidate) on host :8081 -> container :8080, pointed at Prometheus via `--web.default-prometheus-url` CLI flag (RESEARCH §2.3 correction -- no env var)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-19T11:35:00Z
- **Completed:** 2026-05-19T11:43:00Z
- **Tasks:** 2 (Task 1: role scaffold; Task 2: inventory + cascade)
- **Files modified:** 10

## Accomplishments

- Delivered Phase 5 plan 3: PromLens v0.3.0 role port with explicit deprecation-candidate posture
- Corrected CONTEXT.md's "Claude's Discretion" env-var suggestion: PromLens uses `--web.default-prometheus-url` CLI flag exclusively (RESEARCH §2.3) -- no `PROMLENS_DEFAULT_BACKEND_URL` env var exists in v0.3.0
- Phase 5 UI Plane complete: 3/3 plans delivered, all six UI requirements (UI-01..UI-06) covered across grafana + karma + promlens
- D-25 audit applied: Grafana service-account integration dropped (no `--grafana.url` / `--grafana.api-token`), shared-links SQLite dropped, upstream YAML config file dropped (PromLens is pure-CLI)

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold roles/promlens/ (6 files, pure-CLI)** - `a6a9bae` (feat)
2. **Task 2: Inventory + network.yml + roles/README.md + ROADMAP cascade** - `7b38ca8` (feat)

## Files Created/Modified

- `roles/promlens/defaults/main.yml` - Image pin prom/promlens:v0.3.0, port matrix (host :8081 -> container :8080), prometheus URL knob, explicit HEALTHCHECK on root /, D-82 publish_host:true
- `roles/promlens/tasks/main.yml` - Pull image + run container with CLI flags (--web.default-prometheus-url, --web.listen-address), Gate-7 labels, no bind mount, flush_handlers + include verify.yml
- `roles/promlens/tasks/verify.yml` - D-10a HEALTHCHECK poll + root path curl probe + upstream Prometheus reachability cross-check via curlimages/curl one-shots
- `roles/promlens/handlers/main.yml` - Single `Docker restart promlens` handler (OPS-03 schema consistency; not triggered in M1 since no config file)
- `roles/promlens/meta/main.yml` - license MIT, author Rock Martel-Langlois, min_ansible_version 2.15, DEPRECATION CANDIDATE in description
- `roles/promlens/README.md` - DEPRECATION CANDIDATE banner at top, all OPS-03 sections, D-25 deviations audit, --skip-tags guidance, SHA pin recommendation, CLI-flag-only config note
- `inventory/example-homelab/group_vars/all/promlens.yml` - Operator-tunable knobs (publish_host, bind_address, ports, prometheus_url)
- `inventory/example-homelab/group_vars/all/network.yml` - PromLens :8081 DEPRECATION CANDIDATE callout added to UI plane port-allocation comment block
- `playbooks/deploy_docker.yml` - promlens role entry after karma (already present via 05-02 cascade; Phase 5 FEATURE-COMPLETE comment updated)
- `roles/README.md` - promlens row ticked (☑) with "(deprecation candidate)" annotation

## Decisions Made

- **RESEARCH §2.3 correction over CONTEXT.md:** PromLens v0.3.0 has NO `PROMLENS_DEFAULT_BACKEND_URL` env var. The correct configuration mechanism is the CLI flag `--web.default-prometheus-url=<url>`. CONTEXT.md line 152 "Claude's Discretion" paragraph suggested env-var configuration -- RESEARCH refuted this. CLI flag is the only correct approach.
- **D-25 audit per RESEARCH §6.3:** Dropped Grafana service-account integration (`--grafana.url`, `--grafana.api-token`), shared-links SQLite (`--shared-links.sql.driver=sqlite`), upstream YAML config file (`templates/docker/promlens.yml.j2` was unused by the container entrypoint). Port 8086 (upstream) -> 8081 (D-84).
- **Pure-CLI pattern:** No `templates/` dir, no `files/` dir, no volume, no bind mounts. PromLens is configured entirely at container-create time via the `command:` list. This establishes the pure-CLI role pattern for future similar roles.
- **Explicit HEALTHCHECK:** `prom/promlens:v0.3.0` has no built-in HEALTHCHECK (RESEARCH §2.3). Added `wget --spider -q http://localhost:8080` targeting root `/` (no `/health` endpoint in v0.3.0).

## Deviations from Plan

### INSPQ grep gate adjustment

**[Rule 1 - Convention application] D-25 README exemption applied to INSPQ grep gate**
- **Found during:** Task 1 verification
- **Issue:** Plan's verify script ran `grep -riE 'inspq...' roles/promlens/` which flagged README.md and meta/main.yml (both legitimately contain "INSPQ" in deviation-audit documentation context). Phase 2 D-25 decision established that the INSPQ grep gate is code/config-only (excluding README documentation).
- **Fix:** Applied D-25: removed "INSPQ" mention from `meta/main.yml` description (used "upstream parity" instead), kept README's "Deviations from upstream INSPQ" section (documentation context, permitted). Removed `PROMLENS_DEFAULT_BACKEND_URL` literal from code comments in defaults/main.yml and tasks/main.yml, keeping it only in README.md (required by acceptance criteria).
- **Files modified:** roles/promlens/meta/main.yml, roles/promlens/defaults/main.yml, roles/promlens/tasks/main.yml
- **Committed in:** a6a9bae (Task 1 commit)

None - plan executed as specified beyond the above gate adjustment.

## Phase 5 Completion Summary

Phase 5 UI Plane is **feature-complete**: all 3 plans delivered (05-01 Grafana, 05-02 Karma, 05-03 PromLens).

All six UI requirements covered:
- UI-01: Grafana datasource UIDs pinned (prometheus, loki, tempo, mimir)
- UI-02: Datasources resolve real data (Gate 9 verification)
- UI-03: Curated dashboards rendering real data
- UI-04: Trace-to-logs correlation (tracesToLogsV2 + Loki derivedFields)
- UI-05: Karma over Alertmanager on host :8082
- UI-06: PromLens v0.3.0 on host :8081, pointed at prometheus:9090

## D-25 Audit Summary (upstream INSPQ promlens role)

| Item | Upstream had | Telemetron M1 | Reason |
|------|-------------|--------------|--------|
| Grafana SA integration | `--grafana.url` + `--grafana.api-token` | DROPPED | Secrets surface, no M1 value, deprecation candidate |
| Shared-links SQLite | `--shared-links.sql.driver=sqlite` | DROPPED | Stateless simpler, correct for deprecation candidate |
| YAML config file | `templates/docker/promlens.yml.j2` | DROPPED | Unused by container entrypoint; PromLens is pure-CLI |
| `application_web_docker` dep | Role dependency | DROPPED | Dropped project-wide (PROJECT.md Out of Scope) |
| `state: absent` pre-task | Non-idempotent cleanup | DROPPED | docker_container recreate:false is idempotent |
| Image tag | `:latest` | `v0.3.0` (pinned) | OPS-01 image-pin gate |
| Host port | `8086` | `8081` | D-84 port matrix |
| HEALTHCHECK | None | Explicit wget --spider | Image has no built-in HEALTHCHECK |
| Gate-7 labels | None | org.telemetron.{service,job} | INGEST-07 Fluent Bit enrichment |
| Deprecation banner | None | README opens with banner | CLAUDE.md + CONTEXT.md "Specific Ideas" |

## Issues Encountered

- deploy_docker.yml edit conflict: The 05-02 parallel agent had already committed promlens to the playbook as part of its cascade. Python-based edit resolved to the correct content (idempotent operation).

## Next Phase Readiness

Phase 5 is complete. Phase 6 (Opt-in, Orchestration, Docs & Smoke Test) can begin:
- `nfsd` role (opt-in via `enable_nfsd: false` default)
- Full `playbooks/deploy_docker.yml` orchestration review and docs
- Three docs: `docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`
- M1 acceptance smoke test (synthetic log + metric + trace in Grafana within 60s)

---
*Phase: 05-ui-plane*
*Completed: 2026-05-19*
