---
gsd_state_version: 1.0
milestone: v1.3.0
milestone_name: — Backup & Restore
status: executing
stopped_at: Phase 14 context gathered
last_updated: "2026-06-05T02:55:29.194Z"
last_activity: 2026-06-05
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 14
  completed_plans: 14
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-02 after v1.3.0 milestone scoped)

**Core value:** A homelab operator can clone the repo, point the bundled example inventory at one of their own Docker hosts, run a single playbook, and end up with a working observability plane — Prometheus + Mimir for metrics, Loki for logs, Tempo for traces, Grafana on top, Alertmanager + Karma for alerts, all fed by OpenTelemetry Collector. **Shipped in v1.0.0. Extended in v1.3.0: when something goes wrong, the operator has a tested path to restore from a backup.**
**Current focus:** Phase 14 — orchestrators-leviathan-human-uat

## Current Position

Phase: 14 (orchestrators-leviathan-human-uat) — EXECUTING
Plan: 2 of 7
Status: Ready to execute
Last activity: 2026-06-05

```
[Phase 13] [ ] Per-Role Backup & Restore Tasks   (0/? plans)
[Phase 14] [ ] Orchestrators + Leviathan UAT      (0/? plans)
[Phase 15] [ ] Documentation Cascade              (0/? plans)
```

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 17
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 7     | TBD   | —     | —        |
| 8     | TBD   | —     | —        |
| 9     | TBD   | —     | —        |
| 08 | 3 | - | - |
| 11 | 6 | - | - |
| 12 | 3 | - | - |
| 13 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-foundation-storage P02 | 4 | 3 tasks | 8 files |
| Phase 01-foundation-storage P01 | 8min | 3 tasks | 4 files |
| Phase 01-foundation-storage P03 | 8min | 3 tasks | 9 files |
| Phase 02-telemetry-backends P01 | 7 min | 3 tasks | 12 files |
| Phase 02-telemetry-backends P02 | 8 min | 3 tasks | 11 files |
| Phase 02-telemetry-backends P03 | 7 min | 3 tasks | 11 files |
| Phase 03-ingest-plane P01 | 7min | 8 tasks | 9 files |
| Phase 03-ingest-plane P02-opentelemetry | 9 min | 10 tasks | 11 files |
| Phase 03-ingest-plane P03-prometheus | 9 min | 11 tasks | 12 files |
| Phase 03-ingest-plane P04-fluentbit | 8 min | 10 tasks | 9 files |
| Phase 03 P05 | 9 min | 10 tasks | 16 files |
| Phase 04-alert-plane P1 | 13min | 7 tasks tasks | 16 files files |
| Phase 04-alert-plane P02 | 13min | 7 tasks | 10 files |
| Phase 04.1-drop-vault-prefix P01 | 105 | 7 tasks | 20 files |
| Phase 05 P01 | 14 min | 3 tasks | 24 files |
| Phase 05 P02 | 7 | 2 tasks | 11 files |
| Phase 05 P03 | 8 | 2 tasks | 10 files |
| Phase 05 P04 | 12 | 4 tasks | 14 files |
| Phase 05-ui-plane P06 | 8min | 4 tasks | 3 files |
| Phase 05 P07 | 4 min | 4 tasks tasks | 3 files files |
| Phase 05-ui-plane P05 | 6min | 3 tasks tasks | 2 files files |
| Phase 05-ui-plane P08 | 8min | 5 tasks tasks | 5 files files |
| Phase 06 P01 | 24min | 4 tasks tasks | 12 files files |
| Phase 06-opt-in-orchestration-docs-smoke-test P02 | 12min | 4 tasks tasks | 5 files files |
| Phase 06-opt-in-orchestration-docs-smoke-test P03 | 10min | 4 tasks | 3 files |
| Phase 06-opt-in-orchestration-docs-smoke-test P04 | 28min | 4 tasks tasks | 6 files files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work (v1.3.0 — Backup & Restore):

- **Cold-quiesce model locked**: stop container → tar → restart. Hot snapshots (Garage `garage meta snapshot`, Prometheus `/api/v1/admin/tsdb/snapshot`, Grafana SQLite `.backup`) deferred. Brief downtime (~30-60s per role) is acceptable.
- **`docker stop` + `docker_container_info` poll, NOT `community.docker state: stopped`**: `state: stopped` strips volume/mount specs from the container record; subsequent `state: started` silently orphans data. Live-UAT-only catchable. Use native `docker stop` unconditionally.
- **Garage backup must include `s3-credentials` host file**: Without this file, a post-restore `deploy_docker.yml` regenerates a new S3 key that Loki/Tempo/Mimir don't know about, forcing a full re-bootstrap. The file lives inside `garage_config_dir` and is captured when the config dir is included in the tar.
- **Prometheus restore must delete `/prometheus/lock` after untar, before `docker start`**: The lock file is PID-based and left over from backup-time process; restored tarball carries the stale lock, causing `Locked by other process` startup failure.
- **Destination**: `/opt/telemetron/backups/<role>/<role>-YYYYMMDD-HHMMSS.tar.zst`, dir mode 0700, tarball mode 0600. Operator manages retention (find/rsync/restic/borg — Telemetron stays opinion-free).
- **`zstd` ensure-present task in every backup/restore task file**: Not pre-installed on Ubuntu 22.04, Debian 12, or RHEL 9. `ansible.builtin.package: name: zstd state: present become: true`.
- **`backup_restore_confirm=true` gate at both orchestrator AND per-role task level**: Mirrors v1.2.0 `telemetron_purge_data=true` safety contract. Gate in role task so standalone `include_role: tasks_from=restore` also enforces it.
- **`block`/`rescue`/`always` in every backup task**: Container is always restarted even on tar failure. Prevents half-state where a role is stopped but not restarted on bail-out.
- **Stop Loki/Tempo/Mimir before stopping Garage in `backup_docker.yml`**: These are Garage writers; crash-loop if Garage stops while they are writing (XP-2 pitfall mitigation).
- **3-phase shape mirrors v1.2.0**: Phase 13 (per-role tasks) → Phase 14 (orchestrators + live UAT) → Phase 15 (doc cascade + Gate 11). Same dependency shape as Phases 10 → 11 → 12.

### Roadmap Evolution

- Phase 04.1 inserted after Phase 4: Drop vault prefix (URGENT) -- 2026-05-19. Spec: `.planning/phases/05-ui-plane/05-CONTEXT.md` D-90. Drops the `vault_*` prefix from sensitive variables project-wide; renames 4 roles + 8 vault.yml.example keys + doc cascade. Hard precondition for Phase 5 plan 05-01.
- v1.1.0 roadmap created 2026-05-26: Phases 7-9 defined. Phase 7 (regression fixes), Phase 8 (Garage + storage migration), Phase 9 (label reconciliation). All 9 v1.1.0 requirements mapped; all 4 M1 backlog items (999.1-999.4) addressed.
- v1.3.0 roadmap created 2026-06-03: Phases 13-15 defined. Phase 13 (per-role backup + restore tasks), Phase 14 (orchestrators + leviathan HUMAN-UAT), Phase 15 (doc cascade + Gate 11). All 18 v1.3.0 requirements mapped.

### Pending Todos

None active. Begin with `/gsd:plan-phase 13`.

### Blockers/Concerns

None active.

### Known Debt (carried into v1.3.0+)

- **Hook router deferred** (ALERT-V2-01..05). Design preserved in `.planning/milestones/v1.0.0-phases/04-alert-plane/04-DISCUSSION-LOG.md`.
- **Single-host amd64 only** — distributed-mode + multi-host inventory + arm64 + Kube path all future candidates.
- **7 deferred docs** (alerts, retention, fluentbit-timestamps, hook-router, instrumentation-otel, migration-from-inspq, metrics) — tracked as DOCS-V2-01..07.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260519-sod | Remove PromLens from the Telemetron stack (v1.0.1 patch) | 2026-05-19 | d10005a | [260519-sod-remove-promlens-from-the-telemetron-stac](./quick/260519-sod-remove-promlens-from-the-telemetron-stac/) |

## Session Continuity

Last session: 2026-06-05T02:55:29.187Z
Stopped at: Phase 14 context gathered
Resume file: None

## Operator Next Steps

- Plan Phase 13 with `/gsd:plan-phase 13`

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-05-30:

| Category | Item | Status | Note |
|----------|------|--------|------|
| verification_gap | Phase 08 (`08-VERIFICATION.md`) | human_needed | v1.1.0 Garage migration; shipped successfully on leviathan 2026-05-28 (`5700393` chain); status field never bumped from `human_needed` to `passed`. Work is complete. |
| verification_gap | Phase 09 (`09-VERIFICATION.md`) | human_needed | v1.1.0 backlog sweep; shipped with v1.1.0; status drift only. Work is complete. |
| uat_gap | Phase 08 (`08-HUMAN-UAT.md`) | partial | 3 scenarios marked pending; superseded by the full leviathan UAT documented in v1.1.0 close (9/9 requirements validated, archived to `milestones/v1.1.0-REQUIREMENTS.md`). |
| quick_task | `260519-sod-remove-promlens-from-the-telemetron-stac` | missing | Orphaned quick-task descriptor from v1.0.1 patch (commit `d10005a` removed PromLens cleanly per `RETROSPECTIVE.md`). Housekeeping noise; the work shipped. |

These items are pre-existing drift from already-archived milestones (v1.0 / v1.1) and do not reflect outstanding v1.2.0 work. Recorded here for traceability; resolution is optional cleanup, not blocking.
