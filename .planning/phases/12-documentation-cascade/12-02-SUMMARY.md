---
phase: 12-documentation-cascade
plan: "02"
subsystem: docs
tags: [documentation, uninstall, operator-surface, role-readmes]
dependency_graph:
  requires: [phases/11-undeploy-orchestrator-safety-idempotency]
  provides: [per-role-uninstall-sections, DOCS-02-second-clause, SC-3]
  affects: [roles/*/README.md]
tech_stack:
  added: []
  patterns: [uniform-uninstall-H2-between-volumes-and-healthcheck, divergent-nfsd-uninstall-block]
key_files:
  created: []
  modified:
    - roles/alertmanager/README.md
    - roles/fluentbit/README.md
    - roles/garage/README.md
    - roles/grafana/README.md
    - roles/karma/README.md
    - roles/loki/README.md
    - roles/mimir/README.md
    - roles/nfsd/README.md
    - roles/node_exporter/README.md
    - roles/opentelemetry/README.md
    - roles/prometheus/README.md
    - roles/tempo/README.md
decisions:
  - "Uniform placement: ## Uninstall between ## Volumes and ## Healthcheck for all 11 uniform roles (D-171); no fallback branch needed since both karma and node_exporter have ## Volumes on-disk"
  - "Stateless roles (karma, node_exporter, opentelemetry) use purge_images variant; stateful roles use purge_data variant"
  - "nfsd ## Uninstall appended as final section after ## Verification (D-172)"
  - "Pre-existing § non-ASCII in roles/karma/README.md (lines 17, 237, 245) not introduced by this plan -- out of scope per deviation rules boundary"
metrics:
  duration: "3m 49s"
  completed: "2026-05-30T18:53:05Z"
  tasks: 3
  files_modified: 12
---

# Phase 12 Plan 02: Per-Role Uninstall Sections Summary

Added `## Uninstall` H2 sections to all 12 deployed-role READMEs -- 11 uniform template
sections (garage, alertmanager, fluentbit, grafana, karma, loki, mimir, node_exporter,
opentelemetry, prometheus, tempo) and one divergent nfsd section -- closing DOCS-02 second
clause and ROADMAP SC-3.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add ## Uninstall to roles/garage/README.md (canonical template anchor) | c504259 | roles/garage/README.md |
| 2 | Add ## Uninstall to 10 remaining uniform-role READMEs | 05815de | roles/alertmanager/README.md, roles/fluentbit/README.md, roles/grafana/README.md, roles/karma/README.md, roles/loki/README.md, roles/mimir/README.md, roles/node_exporter/README.md, roles/opentelemetry/README.md, roles/prometheus/README.md, roles/tempo/README.md |
| 3 | Add divergent ## Uninstall to roles/nfsd/README.md | da57607 | roles/nfsd/README.md |

## Files Modified and Uninstall Section Details

| Role | Volume(s) Named | Purge Flag | Placement |
|------|-----------------|------------|-----------|
| alertmanager | `telemetron_alertmanager_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| fluentbit | `telemetron_fluentbit_buffer` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| garage | `telemetron_garage_meta`, `telemetron_garage_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| grafana | `telemetron_grafana_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| karma | (none -- stateless) | `telemetron_purge_images=true` | between ## Volumes and ## Healthcheck (D-171) |
| loki | `telemetron_loki_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| mimir | `telemetron_mimir_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| nfsd | (divergent -- no Docker volume) | no purge flags apply | after ## Verification, final section (D-172) |
| node_exporter | (none -- stateless) | `telemetron_purge_images=true` | between ## Volumes and ## Healthcheck (D-171) |
| opentelemetry | (none -- stateless) | `telemetron_purge_images=true` | between ## Volumes and ## Healthcheck (D-171) |
| prometheus | `telemetron_prometheus_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |
| tempo | `telemetron_tempo_data` | `telemetron_purge_data=true` | between ## Volumes and ## Healthcheck (D-171) |

## SC-3 Status

SC-3 is closed: every deployed role README (12 roles including nfsd) now contains a
`## Uninstall` section with tag-scoped `playbooks/undeploy_docker.yml --tags <role>` invocation.

## Cross-Reference Verification

All 12 role READMEs cross-ref `docs/quickstart.md#removing-telemetron`. All 11 uniform
role sections use abbreviated playbook form (no `-i inventory/...`) consistent with each
role's existing `## Tags` section convention.

## nfsd Divergence (D-172) Faithfulness

The nfsd section explicitly lists all 4 things the uninstall does NOT remove:
- OS packages (`nfs-kernel-server` on Debian/Ubuntu, `nfs-utils` on EL)
- `nfs-server.service` (not stopped/disabled)
- `/srv/telemetron-nfs/` share root and per-remote-host subdirectories
- No purge flags apply (`telemetron_purge_data`, `telemetron_purge_images`, `telemetron_purge_host_dirs` are all no-ops)

The `TELEMETRON NFSD ANSIBLE MANAGED BLOCK` literal marker string is quoted verbatim.

## Deviations from Plan

### Pre-existing Condition (not a deviation from my changes)

**Pre-existing `§` characters in roles/karma/README.md (lines 17, 237, 245)**
- Found during: Task 2 post-edit AC check
- Issue: `grep -qP "[^\x00-\x7F]"` returns non-zero for karma README due to 3 pre-existing `§` section-reference characters
- My changes: purely additive; the diff contains zero non-ASCII characters
- Status: Out of scope per deviation rules boundary (pre-existing issue, not caused by current task)
- Note: Phase 5 gap-closure plans 05-04 swept `§` from karma non-README files; the README itself was not swept. Logged to deferred-items.

## Decisions Made

- D-171 fallback branch ("after `## Tags`" for roles without `## Volumes`) was not needed; both karma and node_exporter have `## Volumes` on-disk today. All 11 uniform roles use the primary placement rule.
- prometheus has `## Retention` between `## Volumes` and `## Healthcheck`; `## Uninstall` was inserted between `## Volumes` and `## Retention` (still satisfies "between ## Volumes and ## Healthcheck" D-171 constraint).
- grafana README uses `---` separators between H2 sections; `## Uninstall` placed after the `---` separator following `## Volumes` table for visual consistency.

## Self-Check: PASSED

Files created/modified exist:

- roles/garage/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/alertmanager/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/fluentbit/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/grafana/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/karma/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/loki/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/mimir/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/node_exporter/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/opentelemetry/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/prometheus/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/tempo/README.md -- contains `## Uninstall` between `## Volumes` and `## Healthcheck`
- roles/nfsd/README.md -- contains divergent `## Uninstall` after `## Verification`

Commits exist:
- c504259: docs(12-02): add ## Uninstall section to roles/garage/README.md
- 05815de: docs(12-02): add ## Uninstall section to 10 uniform-role READMEs
- da57607: docs(12-02): add divergent ## Uninstall section to roles/nfsd/README.md
