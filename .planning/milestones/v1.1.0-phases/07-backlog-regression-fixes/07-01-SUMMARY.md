---
phase: 07-backlog-regression-fixes
plan: "01"
subsystem: config-templates
tags: [mimir, tempo, fluentbit, retention, compaction, lua, regression-fix]
dependency_graph:
  requires: []
  provides: [mimir-retention-enforced, tempo-compaction-wired, fluentbit-timestamp-fallback]
  affects: [roles/mimir, roles/tempo, roles/fluentbit]
tech_stack:
  added: []
  patterns: [jinja-limits-block, lua-nil-or-empty-guard, orphan-var-rename]
key_files:
  created: []
  modified:
    - roles/mimir/templates/mimir.yaml.j2
    - roles/tempo/defaults/main.yml
    - roles/tempo/templates/tempo.yaml.j2
    - roles/fluentbit/files/enrich.lua
    - roles/fluentbit/templates/fluent-bit.conf.j2
decisions:
  - "D-101: compactor_blocks_retention_period belongs in limits: not compactor: in Mimir 3.0 (pre-existing var, no new var needed)"
  - "D-102/D-103: tempo_compaction_window replaces orphan tempo_compactor_block_ranges_period; 1h matches Tempo 2.10 upstream default"
  - "D-104/D-105: set_ingest_timestamp Lua helper fixes Pitfall 6 Mode 2 at the Lua layer; disabled [FILTER] modify block removed"
metrics:
  duration: "4 minutes"
  completed_date: "2026-05-27"
  tasks_completed: 3
  files_modified: 5
---

# Phase 7 Plan 01: Three Backlog Regression Fixes Summary

Three config regressions closed: Mimir retention wired to limits: block (was silently using 1-week default), Tempo compaction_window knob live-wired (replacing orphan block_ranges_period var), and Fluent Bit @timestamp fallback implemented in Lua (replacing the disabled [FILTER] modify block that FB 4.x rejected).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Wire Mimir retention to limits: block (CONFIG-01, D-101) | c7eed68 | roles/mimir/templates/mimir.yaml.j2 |
| 2 | Rebind Tempo compaction_window knob (CONFIG-02, D-102, D-103) | 30b1a92 | roles/tempo/defaults/main.yml, roles/tempo/templates/tempo.yaml.j2 |
| 3 | Lua timestamp fallback + remove disabled [FILTER] modify (INGEST-01, D-104, D-105) | c4c7b98 | roles/fluentbit/files/enrich.lua, roles/fluentbit/templates/fluent-bit.conf.j2 |

## What Was Built

### Task 1 — Mimir retention (CONFIG-01, D-101)

Added one line to the `limits:` block in `roles/mimir/templates/mimir.yaml.j2`:

```yaml
compactor_blocks_retention_period: {{ mimir_compactor_blocks_retention_period }} # CONTEXT.md D-101
```

The variable `mimir_compactor_blocks_retention_period` already existed in `defaults/main.yml` (line 63) defaulting to `30d` via `telemetron_default_metric_retention`. Without this line, Mimir 3.0 silently used its built-in 1-week retention regardless of operator configuration. The `defaults/main.yml` file was NOT modified.

### Task 2 — Tempo compaction_window (CONFIG-02, D-102, D-103)

Two surgical changes:
- `roles/tempo/defaults/main.yml`: Replaced the 4-line orphan section (`tempo_compactor_block_ranges_period: 5m`) with a D-102 section header + rationale comment + `tempo_compaction_window: 1h`. The old var referenced a field that does not exist in `tempodb.CompactorConfig` in Tempo 2.10.
- `roles/tempo/templates/tempo.yaml.j2`: Replaced the 3-line "Removed: block_ranges_period" comment with the live key `compaction_window: {{ tempo_compaction_window }}` (D-103 inline comment). The dual-knob `block_retention` + `compacted_block_retention` lines are unchanged (Pitfall 10 retention).

### Task 3 — Fluent Bit timestamp fallback (INGEST-01, D-104, D-105)

Two changes:
- `roles/fluentbit/files/enrich.lua`: Added `set_ingest_timestamp(record, timestamp)` helper after `hostname_from_nfs_tag`. Uses nil-or-empty guard `if not record["@timestamp"] or record["@timestamp"] == ""` — never overwrites a valid source timestamp. Called at all 5 `return 2, timestamp, record` sites in `enrich()` (NFS branch, no container_id fallback, cache hit, config read failed, normal success path).
- `roles/fluentbit/templates/fluent-bit.conf.j2`: Removed the 13-line disabled `[FILTER] modify` block (D-105). That block was the original Pitfall 6 Mode 2 mitigation attempt, rejected by Fluent Bit 4.x with "Invalid operation add : @timestamp". The Lua implementation supersedes it.

## Deviations from Plan

### Comment phrasing — D-102 rationale comment

**Found during:** Task 2 verify

**Issue:** The acceptance criteria required `! grep -q 'block_ranges_period' roles/tempo/defaults/main.yml`. The first draft of the D-102 rationale comment included the literal string "block_ranges_period" as part of the explanation. The grep would have caught this.

**Fix:** Rephrased the comment to describe the issue without using the exact field name string. The meaning is preserved; the orphan field context is documented. Same issue arose in the template inline comment — also rephrased.

**Rule:** Rule 1 (auto-fix) — the verify check was binding; the comment phrasing was not.

**Files modified:** roles/tempo/defaults/main.yml, roles/tempo/templates/tempo.yaml.j2

**Commit:** 30b1a92 (same task commit, not a separate fix)

## End-to-End Verification Results

| Check | Result |
|-------|--------|
| Ansible syntax-check | PASS |
| Mimir: `compactor_blocks_retention_period` in limits: block | PASS — 1 match |
| Tempo: `compaction_window` in compactor.compaction | PASS |
| Tempo: zero `block_ranges_period` references in roles/ | PASS |
| FB: `set_ingest_timestamp` function defined | PASS |
| FB: 6 total set_ingest_timestamp occurrences (1 def + 5 calls) | PASS |
| FB template: no `timestamp_fallback` or `ingest_time` | PASS |

## Known Stubs

None. All three fixes are complete wiring changes with no placeholder values.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are config template edits and a Lua filter modification. Threat model T-07-01 through T-07-03 dispositions are all `accept` per plan (no new mitigations required).

## Self-Check: PASSED

Files exist:
- roles/mimir/templates/mimir.yaml.j2: FOUND
- roles/tempo/defaults/main.yml: FOUND
- roles/tempo/templates/tempo.yaml.j2: FOUND
- roles/fluentbit/files/enrich.lua: FOUND
- roles/fluentbit/templates/fluent-bit.conf.j2: FOUND

Commits exist:
- c7eed68: FOUND
- 30b1a92: FOUND
- c4c7b98: FOUND
