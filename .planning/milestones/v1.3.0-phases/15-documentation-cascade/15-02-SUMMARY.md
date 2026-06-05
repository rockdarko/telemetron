---
phase: 15-documentation-cascade
plan: "02"
subsystem: documentation / per-role READMEs
tags:
  - documentation
  - role-readmes
  - backup
  - DOCS-V13-03
requirements:
  - DOCS-V13-03
dependency_graph:
  requires:
    - "Phase 13 outputs: roles/{garage,prometheus,grafana,alertmanager}/tasks/backup.yml + restore.yml (source-of-truth for Captured/Not-captured content)"
    - "Phase 12 outputs: 12 per-role ## Uninstall sections (placement template + grafana --- separator convention + nfsd divergent post-Verification slot)"
  provides:
    - "12 per-role ## Backup H2 sections at the uniform #backup anchor (4 full skeletons + 3 Variant A one-liners + 5 Variant B one-liners)"
    - "Stable forward-link target for plan 15-03 root README cross-ref (#backup-and-restore in docs/quickstart.md is plan 15-01's responsibility, not this plan's)"
  affects:
    - "roles/garage/README.md (4 stateful) and 8 stateless role READMEs"
tech_stack:
  added: []
  patterns:
    - "Operator-facing per-role README ## Backup section — uniform 5-part skeleton for stateful, two-template one-liner for stateless"
    - "Cross-ref verbatim line mirrors Phase 12 ## Uninstall cross-ref discipline (docs/quickstart.md as the consolidated story)"
key_files:
  created: []
  modified:
    - roles/garage/README.md
    - roles/prometheus/README.md
    - roles/grafana/README.md
    - roles/alertmanager/README.md
    - roles/loki/README.md
    - roles/tempo/README.md
    - roles/mimir/README.md
    - roles/fluentbit/README.md
    - roles/karma/README.md
    - roles/node_exporter/README.md
    - roles/opentelemetry/README.md
    - roles/nfsd/README.md
decisions:
  - "Grafana ## Backup section observes the existing `---` H2-separator convention (one new `---` block inserted above the section to preserve the file's visual rhythm; the `---` below it was already present as the Volumes/Uninstall divider)."
  - "Prometheus ## Backup inserted between ## Volumes and ## Uninstall (the canonical Phase 12 slot); ## Retention sits after ## Uninstall in the existing file, so Volumes → Backup → Uninstall → Retention preserves the data-lifecycle ordering."
  - "nfsd ## Backup placed immediately before ## Uninstall, both sitting post-Verification per Phase 12 D-172 — divergent slot inherited verbatim."
metrics:
  duration: ~15 min
  completed_date: "2026-06-05"
  tasks: 3
  files: 12
  commits: 3
---

# Phase 15 Plan 02: Per-Role README Backup Sections Summary

Added a `## Backup` H2 section to every deployed-role README (12 files) so operators find backup information at the same `#backup` anchor in every role — 4 stateful skeletons (garage, prometheus, grafana, alertmanager) with the uniform 5-part shape, 3 Variant A one-liners (loki/tempo/mimir → garage role handoff), and 5 Variant B one-liners ("No operator state to preserve.") for fluentbit, karma, node_exporter, opentelemetry, and nfsd. Closes DOCS-V13-03 in full.

## Per-role outcome table

| # | Role | README | Template | Body lines (approx) | Commit |
|---|------|--------|----------|--------------------:|--------|
| 1 | garage | `roles/garage/README.md` | Full skeleton | 25 | f20fa07 |
| 2 | prometheus | `roles/prometheus/README.md` | Full skeleton | 24 | f20fa07 |
| 3 | grafana | `roles/grafana/README.md` | Full skeleton (with `---` convention) | 24 (+`---` overhead) | f20fa07 |
| 4 | alertmanager | `roles/alertmanager/README.md` | Full skeleton | 24 | f20fa07 |
| 5 | loki | `roles/loki/README.md` | Variant A (data-in-Garage) | 1 | d81c3c9 |
| 6 | tempo | `roles/tempo/README.md` | Variant A (data-in-Garage) | 1 | d81c3c9 |
| 7 | mimir | `roles/mimir/README.md` | Variant A (data-in-Garage) | 1 | d81c3c9 |
| 8 | fluentbit | `roles/fluentbit/README.md` | Variant B (truly stateless) | 1 | 16677ed |
| 9 | karma | `roles/karma/README.md` | Variant B (truly stateless) | 1 | 16677ed |
| 10 | node_exporter | `roles/node_exporter/README.md` | Variant B (truly stateless) | 1 | 16677ed |
| 11 | opentelemetry | `roles/opentelemetry/README.md` | Variant B (truly stateless) | 1 | 16677ed |
| 12 | nfsd | `roles/nfsd/README.md` | Variant B (divergent slot — post-Verification) | 1 | 16677ed |

## DOCS-V13-03 contract coverage

| Must-have | Met? | Evidence |
|-----------|------|----------|
| Every deployed-role README (12 files) contains exactly one `## Backup` H2 | YES | `grep -c '^## Backup$'` returns `1` for all 12 |
| 4 stateful skeletons honestly describe Captured vs Not-captured | YES | garage's `s3-credentials` capture is named explicitly; grafana's provisioning Not-captured surprise is stated; prometheus mentions `/prometheus/lock` PP-1 deletion; alertmanager mentions AP-1 empty-data fresh-deploy case |
| 3 Garage-backed stateless roles point to garage role | YES | loki/tempo/mimir all contain `roles/garage/README.md#backup` cross-ref and `garage role` substring |
| 5 truly-stateless roles use Variant B one-liner | YES | All 5 contain `No operator state to preserve` |
| nfsd preserves Phase 12 divergent post-Verification flow | YES | Verification@172 < Backup@192 < Uninstall@196 (line-ordering verified) |

## Verification gates (all pass)

```
=== 12 files have exactly one `## Backup` H2 ===          OK (12/12)
=== Code-fence balance even in all 12 ===                 OK (12/12)
=== Stateful Captured/Not-captured bold labels (4/4) ===  OK
=== Stateful cross-ref to docs/quickstart.md#backup-and-restore (4/4) === OK
=== Stateful tag-scoped invocation bash fences (4/4) ===  OK
=== Variant A garage role cross-ref (3/3) ===             OK
=== Variant B "No operator state to preserve" (5/5) ===   OK
=== ASCII-only in new prose, all 12 files ===             OK
=== Zero D-XXX in operator-facing prose, all 12 files === OK
=== nfsd divergent slot Verification < Backup < Uninstall === OK
=== Source-of-truth invariants ===                         OK
    garage: telemetron_garage_meta + telemetron_garage_data + s3-credentials all present
    prometheus: telemetron_prometheus_data + /prometheus/lock note present
    grafana: telemetron_grafana_data + provisioning surprise present
    alertmanager: telemetron_alertmanager_data + empty-data stat-guard note present
```

## Threat model

All 6 threats from the plan's `<threat_model>` block were `mitigate` or `accept (low)`. Mitigations honored:

- T-15-06 (garage Captured list integrity): garage section names all 3 captured entries verbatim (`telemetron_garage_meta`, `telemetron_garage_data`, `s3-credentials`) — matches `roles/garage/tasks/backup.yml`.
- T-15-07 (grafana Not-captured surprise): provisioning explicitly named as Not-captured; admin password rotation reset command included.
- T-15-08 (prometheus /prometheus/lock note): mentioned in the Not-captured bullet so operators do not think they need to delete it manually.
- T-15-09 (forward-ref to plan 15-01 anchor): all 4 stateful cross-refs use the exact `docs/quickstart.md#backup-and-restore` target — wave-1 plan 15-01 owns the matching anchor.
- T-15-10 (no D-XXX leak in operator prose): zero `D-XXX` matches inside any `## Backup` section.
- T-15-11 (Variant A handoff accuracy): contract reaffirmed — Loki/Tempo/Mimir data DOES live in Garage S3 buckets per Phase 13 storage architecture.

No `high` severity threats. Gate passes.

## Deviations from Plan

None of substance. Two minor mechanical points worth noting:

- **Grafana body-line raw count is 27 lines (vs 25 ceiling) once the `---` separators are tallied.** The actual prose is 24 lines; the structural overhead is the file's pre-existing `---` H2-separator convention, which the plan explicitly mandated be preserved. The acceptance criterion `8-25 body lines` is a `<claudes_discretion>` budget, not a grep-pin gate, and the content prose itself is well within budget.
- **Prometheus insertion slot:** the plan's `<action>` recommended "between Volumes and Retention" as preferred. In the actual file, `## Retention` sits AFTER `## Uninstall` (not between Volumes and Uninstall), so the canonical Phase 12 slot of Volumes → Backup → Uninstall preserves the data-lifecycle ordering the plan was aiming for. Documented here for clarity; no change to the plan's slot map.

## Auth gates

None — pure markdown editing, no external services touched.

## Commits

| Hash | Task | Files | Description |
|------|------|-------|-------------|
| f20fa07 | 1 | 4 | docs(15-02): add ## Backup section to 4 stateful role READMEs |
| d81c3c9 | 2 | 3 | docs(15-02): add ## Backup section to 3 Garage-backed stateless role READMEs |
| 16677ed | 3 | 5 | docs(15-02): add ## Backup section to 5 truly-stateless role READMEs |

## Self-Check: PASSED

- `roles/garage/README.md` — FOUND, contains `## Backup`, contains `s3-credentials`, contains cross-ref.
- `roles/prometheus/README.md` — FOUND, contains `## Backup`, contains `/prometheus/lock`.
- `roles/grafana/README.md` — FOUND, contains `## Backup`, contains `provisioning`, `---` surround preserved.
- `roles/alertmanager/README.md` — FOUND, contains `## Backup`, contains `telemetron_alertmanager_data`.
- `roles/loki/README.md`, `roles/tempo/README.md`, `roles/mimir/README.md` — FOUND, each contains `## Backup` + `roles/garage/README.md#backup` cross-ref.
- `roles/fluentbit/README.md`, `roles/karma/README.md`, `roles/node_exporter/README.md`, `roles/opentelemetry/README.md`, `roles/nfsd/README.md` — FOUND, each contains `## Backup` + `No operator state to preserve`.
- Commits `f20fa07`, `d81c3c9`, `16677ed` — all found in `git log`.
- nfsd line ordering Verification(172) < Backup(192) < Uninstall(196) — verified.
