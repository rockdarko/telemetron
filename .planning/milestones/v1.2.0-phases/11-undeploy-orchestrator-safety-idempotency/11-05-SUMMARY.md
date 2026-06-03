---
phase: 11-undeploy-orchestrator-safety-idempotency
plan: 05
subsystem: docs
tags: [uat, leviathan, undeploy, purge, idempotency, d-146, d-161, d-162, d-163, d-164]

# Dependency graph
requires:
  - phase: 11-undeploy-orchestrator-safety-idempotency
    provides: 11-01..11-04 (orchestrator wave, per-role purge.yml wave, undeploy_docker.yml playbook) -- these are the code Plans 11-05 will gate via UAT
  - phase: 08-garage-role-backend-retargeting
    provides: 08-HUMAN-UAT.md canonical UAT format (D-162 mirror source)
provides:
  - 11-HUMAN-UAT.md (7-scenario live-leviathan UAT checklist)
  - Sequential approval gating per D-163 (scenarios 1..5 top-to-bottom)
  - Scenario 1 D-146 recovery proof (old Grafana panels after default undeploy + redeploy)
  - Scenario 3 D-164 partial-deploy idempotency simulation method
  - Scenario 4b PURGE-02 SC-5 (Garage s3-credentials destruction)
affects: [11-VERIFICATION.md, future Phase 11 verifier run, post-leviathan-UAT gap-closure planning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-162 HUMAN-UAT.md mirror -- frontmatter (status/phase/source/started/updated) + ## Current Test + ## Tests + numbered scenarios + ## Summary tally + ## Gaps"
    - "D-25 ASCII-only enforcement -- `! grep -P '[^\\x00-\\x7F]'` gate catches em-dashes copied verbatim from PATTERNS.md"

key-files:
  created:
    - .planning/phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md
  modified: []

key-decisions:
  - "Replaced 4 em-dashes (U+2014) inherited from PATTERNS.md verbatim text with ASCII `--` to satisfy the D-25 grep gate before commit"
  - "Force-added 11-HUMAN-UAT.md via `git add -f` -- `.planning/` is gitignored but Phase 08 set precedent that HUMAN-UAT.md is the one deliverable in a planning subdir that ships in-tree (08-HUMAN-UAT.md is tracked)"
  - "Frontmatter `source: [11-VERIFICATION.md]` points forward to a file that does not exist yet -- D-162 convention is that VERIFICATION.md is generated later by the Phase 11 verifier, and HUMAN-UAT.md references it by name"

patterns-established:
  - "Plan-05 docs-only pattern -- pure markdown authoring, no code touched, validated via grep-only automated gates"
  - "Wave-2 independence -- plan files have no overlap with Plans 11-01..11-04 (only writes 11-HUMAN-UAT.md), enabling parallel-with-11-04 execution"

requirements-completed: [OPS-01, OPS-02]

# Metrics
duration: 2min
completed: 2026-05-30
---

# Phase 11 Plan 05: 11-HUMAN-UAT.md (7-scenario live-leviathan UAT checklist) Summary

**Phase 11 ships its 7-scenario live-leviathan UAT checklist mirroring 08-HUMAN-UAT.md (D-162): conservative undeploy + D-146 recovery proof, back-to-back idempotency (OPS-01), D-164 partial-deploy simulation, each purge flag individually (4a/4b/4c), and all-3-flags fresh-start (OPS-02 second clause).**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-30T02:00:28Z
- **Completed:** 2026-05-30T02:02:27Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- 11-HUMAN-UAT.md authored with the full 7-scenario D-161 matrix (1, 2, 3, 4a, 4b, 4c, 5) and 6-field summary tally (total: 7, passed: 0, issues: 0, pending: 7, skipped: 0, blocked: 0)
- Scenario 1 explicitly references D-146 recovery story (Grafana panels show OLD pre-undeploy data after default undeploy + redeploy, proving Garage regenerated S3 key on the orphan while Loki/Tempo/Mimir kept their old buckets via bootstrap.yml lines 188-223 bucket allow re-grant)
- Scenario 3 documents the D-164 partial-deploy simulation method (manually `docker rm -f` three containers, then run undeploy, expect `failed=0` and no spurious `changed=true` on pre-removed containers)
- Scenario 4b explicitly mentions `/opt/telemetron/garage/s3-credentials` destruction per PURGE-02 SC-5
- Scenarios 1, 4a, 4b, 4c, 5 all reference `smoke_test.yml` as the post-redeploy validation probe (OPS-07 acceptance)
- File passes every D-25 grep gate: ASCII-only, no INSPQ heritage references, no emojis

## Task Commits

Each task was committed atomically:

1. **Task 1: Create 11-HUMAN-UAT.md with frontmatter + 7-scenario checklist + summary** - `dd5474d` (docs)

## Files Created/Modified

- `.planning/phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` - 7-scenario live-leviathan UAT checklist with frontmatter, ## Current Test, ## Tests, scenarios 1/2/3/4a/4b/4c/5, ## Summary tally (total: 7, pending: 7), ## Gaps

## Decisions Made

- **Em-dash to ASCII `--` replacement:** PATTERNS.md lines 404-431 contained 4 em-dashes (U+2014, UTF-8 `e2 80 94`) in the verbatim scenario text. The plan's own automated verification gate `! grep -P "[^\x00-\x7F]"` (D-25 ASCII-only rule) would have failed if these were kept. Replaced with ASCII `--` in scenarios 1, 4a, 4c (twice). This is a faithful preservation of meaning (em-dash and `--` are interchangeable in technical prose) and satisfies the D-25 grep gate.
- **Force-add of gitignored file:** `.planning/` is gitignored via `.gitignore` line 25, but Phase 08 set the precedent that HUMAN-UAT.md ships in-tree (`08-HUMAN-UAT.md` is tracked). Used `git add -f` to follow that precedent for `11-HUMAN-UAT.md`.
- **`source: [11-VERIFICATION.md]` forward reference:** Frontmatter references `11-VERIFICATION.md` which does not yet exist. This follows the D-162 convention (08-HUMAN-UAT.md also references its 08-VERIFICATION.md by name even when that file is generated later by the verifier).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced em-dashes with ASCII `--` to satisfy D-25 grep gate**
- **Found during:** Task 1 (file creation; verification step)
- **Issue:** Verbatim copy of PATTERNS.md scenario text inherited 4 em-dashes (U+2014). The plan's own automated verification gate `! grep -P "[^\x00-\x7F]"` (D-25 ASCII-only rule per project convention) would have failed, blocking the commit.
- **Fix:** Replaced em-dashes with ASCII `--` in four locations (scenario 1 "_data` survive --", scenario 4a "fresh-bucket state -- old data wiped", scenario 4c "11 WARN lines -- every role except nfsd" and "sibling-image edge case proof --"). Meaning preserved.
- **Files modified:** .planning/phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md
- **Verification:** Re-ran the full automated gate block -- all 22 checks pass including `! grep -P "[^\x00-\x7F]"`.
- **Committed in:** dd5474d (Task 1 commit -- fix included in initial create)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Em-dash replacement was strictly required to pass the plan's own ASCII-only verification gate (D-25). No semantic change; no scope creep.

## Issues Encountered

- **Phase 11 directory absent from worktree:** The worktree base commit (`8dd06dd`) predates Phase 11 planning artifact creation, and `.planning/phases/11-...` files were untracked in the parent working directory. Copied the 8 planning files (`11-01..11-05-PLAN.md`, `11-CONTEXT.md`, `11-DISCUSSION-LOG.md`, `11-PATTERNS.md`) from the parent working directory into the worktree to read the plan; only the deliverable (`11-HUMAN-UAT.md`) was committed, matching Phase 10's pattern of committing only SUMMARY.md (not PLAN/CONTEXT/PATTERNS).
- **`.planning/` gitignored:** Required `git add -f` to stage the new file. Follows Phase 08 precedent (08-HUMAN-UAT.md is tracked via force-add).

## User Setup Required

None - no external service configuration required. The file is the input to manual UAT execution; the operator (Rock) will fill `result:` fields during live-leviathan testing per D-163 sequential approval pattern.

## Next Phase Readiness

- 11-HUMAN-UAT.md is ready for Rock's live-leviathan UAT execution per D-163 sequential approval gating
- Plans 11-01..11-04 (code-level orchestrator + per-role purge.yml wave) must be merged and deployed to leviathan before Rock can run the UAT
- Failed scenarios feed into 11-VERIFICATION.md gap list (generated by the Phase 11 verifier in a later step); gaps drive next round of planning per /gsd-verify-work convention

## Self-Check: PASSED

- File `.planning/phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md`: FOUND
- Commit `dd5474d`: FOUND (verified via `git log --oneline --all | grep dd5474d`)
- All 22 automated verification gates from `<verify><automated>` block: PASSED

---
*Phase: 11-undeploy-orchestrator-safety-idempotency*
*Completed: 2026-05-30*
