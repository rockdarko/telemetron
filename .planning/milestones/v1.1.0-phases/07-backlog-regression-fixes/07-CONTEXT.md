# Phase 7: Backlog Regression Fixes - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three live config regressions captured in the v1.0.0 backlog: Mimir retention not enforced, Tempo compaction knob orphaned, Fluent Bit timestamp fallback disabled. All three are self-contained template or Lua edits in existing roles with no cross-role dependencies.

</domain>

<decisions>
## Implementation Decisions

### Mimir retention (CONFIG-01)
- **D-101:** Add `compactor_blocks_retention_period: {{ mimir_compactor_blocks_retention_period }}` to the `limits:` block in `roles/mimir/templates/mimir.yaml.j2`. The variable already exists in `defaults/main.yml:63` with default `30d`. The `compactor:` section comment documenting the removal stays as-is (it explains why the key moved). No new variables needed.

### Tempo compaction window (CONFIG-02)
- **D-102:** Rename `tempo_compactor_block_ranges_period` to `tempo_compaction_window` in `roles/tempo/defaults/main.yml`. Default changes from `5m` to `1h` to match the Tempo 2.10 `compaction_window` upstream default.
- **D-103:** Wire the new variable to `compactor.compaction.compaction_window: {{ tempo_compaction_window }}` in `roles/tempo/templates/tempo.yaml.j2`, replacing the "Removed" comment block. Update the defaults comment to reference the new key name.

### Fluent Bit timestamp fallback (INGEST-01)
- **D-104:** Implement `set_ingest_timestamp(record, timestamp)` as a helper function in `roles/fluentbit/files/enrich.lua`. Called from inside the existing `enrich()` function for both Docker and NFS code paths. Sets `@timestamp` from the FB-provided `timestamp` argument only when the record lacks an embedded timestamp field. Never overwrites a valid source timestamp.
- **D-105:** Remove the disabled `[FILTER] modify` block at `roles/fluentbit/templates/fluent-bit.conf.j2:154-166`. The Lua approach supersedes it; historical context preserved in git history and this CONTEXT.md.

### Plan shape
- **D-106:** All three fixes ship in a single plan. Three independent tasks (one per role), no dependencies between them. Matches the phase's "batch of config fixes" nature.

### Verify scope
- **D-107:** Leave `minio/mc` bucket verification in `roles/mimir/tasks/verify.yml` untouched. Phase 8 (Garage migration) will naturally replace it when it rewrites the storage layer. No scope creep in Phase 7.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Mimir retention regression
- `roles/mimir/templates/mimir.yaml.j2` — Current rendered config; `compactor:` section comment documents why `blocks_retention_period` was removed (moved to `limits:`)
- `roles/mimir/defaults/main.yml` — `mimir_compactor_blocks_retention_period` var at line 63 (already exists, default `30d`)

### Tempo compaction regression
- `roles/tempo/templates/tempo.yaml.j2` — Current rendered config; `compactor:compaction:` section has the "Removed: block_ranges_period" comment at line 56
- `roles/tempo/defaults/main.yml` — Orphan var `tempo_compactor_block_ranges_period` at line 82 (to be renamed)

### Fluent Bit timestamp regression
- `roles/fluentbit/files/enrich.lua` — Existing Lua enrichment function; timestamp fallback will be added here
- `roles/fluentbit/templates/fluent-bit.conf.j2` — Disabled `[FILTER] modify` block at lines 154-166 (to be removed)

### Requirements
- `.planning/REQUIREMENTS.md` — CONFIG-01, CONFIG-02, INGEST-01 requirement definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `enrich.lua` enrichment pattern: tag-based dispatch (`docker.*` vs `nfs.*`), per-container cache with TTL, `return 2, timestamp, record` convention for modified records. New `set_ingest_timestamp` follows the same return convention.
- Mimir `limits:` section in `mimir.yaml.j2` already exists (lines 82-84) with two monolithic-tuning knobs — retention joins them naturally.

### Established Patterns
- Template comments cite decision IDs (e.g., `# CONTEXT.md D-36`) — new lines should cite D-101/D-102/D-103.
- Defaults comments reference PITFALLS, RESEARCH findings, and decision IDs — maintain for the new/renamed vars.
- Jinja variable references use `{{ var | string | lower }}` for booleans, plain `{{ var }}` for strings/durations.

### Integration Points
- `playbooks/deploy_docker.yml` orchestration order unchanged — all three roles are already in the pipeline.
- Phase 7 success criteria reference `docker exec` commands on running containers — verify tasks may need minor updates to check the new config keys.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — the fixes are well-defined regressions with clear before/after states documented in the Phase 2 and Phase 3 UAT gaps.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 7-Backlog Regression Fixes*
*Context gathered: 2026-05-27*
