# Phase 7: Backlog Regression Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 07-backlog-regression-fixes
**Areas discussed:** Tempo variable rename, FB timestamp fallback scope, Verify approach

---

## Tempo variable rename

| Option | Description | Selected |
|--------|-------------|----------|
| Rename to tempo_compaction_window | Clean break — new var name matches the Tempo 2.10 config key `compaction_window`. Old var is orphaned anyway so no one is using it. Default changes from 5m to 1h. | ✓ |
| Keep tempo_compactor_block_ranges_period | Wire the existing var name to the new key. Avoids a rename for anyone who customized it in inventory, even though it was a no-op until now. | |
| You decide | Let Claude pick the cleanest approach based on codebase conventions. | |

**User's choice:** Rename to tempo_compaction_window
**Notes:** Clean break justified since the old variable was orphaned (mapped to nothing in the rendered template). No inventory backward compatibility concern.

---

## FB timestamp fallback scope

### Q1: Function placement

| Option | Description | Selected |
|--------|-------------|----------|
| Inside enrich() | Add the timestamp check at the top of the existing enrich() function — every record already passes through it. Name the helper `set_ingest_timestamp(record, timestamp)` so it grep-matches. | ✓ |
| Separate [FILTER] lua block | New [FILTER] lua with its own function and Match *. Runs on ALL records. More modular but adds a second Lua filter to the pipeline. | |
| You decide | Let the researcher/planner pick the cleanest approach. | |

**User's choice:** Inside enrich()
**Notes:** Single Lua filter pipeline, helper function for grep-matchability.

### Q2: Disabled [FILTER] modify cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it | The Lua function supersedes it completely. Leaving commented-out dead code violates the codebase convention of clean templates. Historical context preserved in git history and DISCUSSION-LOG. | ✓ |
| Keep as commented reference | Leave it commented out with a pointer to the Lua replacement. | |

**User's choice:** Remove it
**Notes:** Clean templates over inline historical comments.

### Q3: NFS path inclusion

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, apply to all paths | NFS logs from legacy hosts are MORE likely to lack proper timestamps than Docker JSON logs. The helper checks before writing so it's safe for both paths. | ✓ |
| Docker path only | Scope the fallback to docker.* tags only. NFS logs have their own enrichment branch and may need different timestamp handling. | |

**User's choice:** Yes, apply to all paths
**Notes:** NFS logs are the primary use case for this fallback; Docker JSON logs almost always have timestamps.

---

## Verify approach

### Q1: minio/mc in Mimir verify

| Option | Description | Selected |
|--------|-------------|----------|
| Leave for Phase 8 | Phase 7 is regression fixes only. The mc-based verify still works against the live MinIO and will be naturally replaced when Phase 8 rewrites the storage layer. | ✓ |
| Remove mc verify in Phase 7 | Get the MinIO dependency surface smaller before Phase 8. But this removes a working verification step without replacing it yet. | |

**User's choice:** Leave for Phase 8
**Notes:** Avoid scope creep; working verification is better than no verification.

### Q2: Plan shape

| Option | Description | Selected |
|--------|-------------|----------|
| One plan | Three small, independent template/Lua edits in three roles. No dependencies between them. A single plan with 3 tasks keeps the overhead low. | ✓ |
| Three separate plans | One plan per fix. Allows atomic verification of each regression independently. More overhead. | |
| Two plans: configs + Lua | Mimir + Tempo config fixes in one plan, FB Lua in a second. | |

**User's choice:** One plan
**Notes:** Matches the phase's "batch of config fixes" nature; low overhead.

---

## Claude's Discretion

No areas deferred to Claude's discretion.

## Deferred Ideas

None — discussion stayed within phase scope.
