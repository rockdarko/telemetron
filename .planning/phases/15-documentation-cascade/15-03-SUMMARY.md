---
phase: 15-documentation-cascade
plan: "03"
subsystem: documentation
tags: [documentation, root-readme, gate-11, cross-ref, DOCS-V13-01, DOCS-V13-02]
dependency_graph:
  requires: [13-per-role-backup-restore-tasks, 14-orchestrators-leviathan-human-uat]
  provides: [DOCS-V13-01, DOCS-V13-02-root-clause]
  affects: [README.md, roles/README.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - README.md
    - roles/README.md
decisions:
  - "D-206 honored: 'When something goes wrong,' lede + docs/quickstart.md#backup-and-restore link target + backup_restore_confirm=true knob name inserted verbatim into root README Quick start"
  - "D-207 honored: Gate 11 mirrors Gate 10 depth/voice/structure (bold lede with D-ID citation, contract statement, lettered sub-clauses, divergent paragraph, closing paragraph with future-role-additions closing line)"
  - "D-208 honored: Gate 11 closing paragraph distinguishes per-role in-gate scope from orchestrator-level out-of-gate concerns (backup_continue_on_failure, writer-quiesce, any_errors_fatal) + forward-points to docs/quickstart.md#backup-and-restore"
  - "Phase 12 D-174 ASCII '--' convention preserved in both edits (no em-dash characters introduced)"
  - "Pattern S3 asymmetry honored: D-IDs (D-176..D-179) cited in roles/README.md Gate 11 lede (contributor-facing, matches Gates 1-10); zero D-IDs in README.md (operator-facing)"
metrics:
  duration: "~6 minutes"
  completed: "2026-06-05T14:42:07Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 15 Plan 03: Root README cross-ref and Gate 11 Summary

Two surgical prose edits close DOCS-V13-01 (Gate 11 in `roles/README.md` codifying the per-role backup/restore contract that 4 stateful roles inherit) and the root-README clause of DOCS-V13-02 (the "When something goes wrong" cross-ref in `README.md` Quick start). Mirrors Phase 12 plan 12-03's shape one-to-one: one inserted cross-ref paragraph in the project root README plus one new gate entry in the contributor-facing `roles/README.md`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Insert "When something goes wrong" cross-ref paragraph into root README.md Quick start | 338bb8c | README.md |
| 2 | Insert Gate 11 (Per-role backup/restore contract) into roles/README.md Per-role port-acceptance gates | 5a1dba3 | roles/README.md |

## Changes Made

### Task 1 -- README.md

New paragraph inserted between the existing "When you're done evaluating" paragraph (Phase 12 plan 12-03 output, lines 30-33) and `## What's included` (was line 35, now line 41):

```
When something goes wrong,
[`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore)
covers the backup playbook (conservative by default -- local dated
tarballs; operator manages retention) and the restore workflow (with the
explicit `--extra-vars backup_restore_confirm=true` safety gate).
```

Net change: +6 lines (one blank separator + 5-line paragraph). Sits adjacent to and AFTER the existing Phase 12 "When you're done evaluating" sibling -- the two evaluation-exit cross-refs become natural reading siblings (the "what to do next" sequence: evaluate → done evaluating → something went wrong).

Locked elements per D-206 all present verbatim:
- Lede: `When something goes wrong,`
- Link target: `docs/quickstart.md#backup-and-restore`
- Knob name: `backup_restore_confirm=true`
- Framing phrase: `operator manages retention`
- Backup-by-default characterization: `conservative by default -- local dated tarballs`

ASCII `--` double-hyphen used in the parenthetical (Phase 12 D-174 + 12-VERIFICATION.md line 81: "double-hyphen used throughout per 12-03-PLAN explicit instruction matching README style"). Zero non-ASCII characters introduced. Zero D-XXX references (operator-facing -- Pattern S3).

### Task 2 -- roles/README.md

New Gate 11 entry inserted at lines 124-136, immediately after Gate 10's closing line (now line 122, unchanged). Gate 10's closing paragraph is preserved verbatim from Phase 12 plan 12-03's output (12-VERIFICATION.md line 100-109 records its finalized state).

Gate 11 structure mirrors Gate 10 element-by-element per D-207 + D-208:

| Element | Gate 11 content |
|---------|-----------------|
| Bold lede (cites D-IDs, contributor-facing per Pattern S3 exception) | `**11. Per-role backup/restore contract (BACKUP-V13-01..04 + RESTORE-V13-01..04; D-176..D-179):**` |
| Single-sentence contract + role enumeration | "Every stateful role MUST ship `tasks/backup.yml` and `tasks/restore.yml` proven on leviathan end-to-end. The 4 stateful roles are: `garage`, `prometheus`, `grafana`, `alertmanager`." |
| Sub-clause (a) | `tasks/backup.yml` cold-quiesce (docker stop, zstd tarball to `/opt/telemetron/backups/<role>/<role>-<UTC-ts>.tar.zst`, docker start, verify) wrapped in `block:/rescue:/always:` so the container is running at the end regardless of tar success/failure |
| Sub-clause (b) | `tasks/restore.yml` asserts `backup_restore_confirm == true` (fail-fast gate), runs `tar tf` integrity check, wipes `_data/`, untars, restarts, verifies |
| Sub-clause (c) | Both files start with idempotent `ansible.builtin.package: name: zstd state: present` pre-task |
| Divergent paragraph | Stateless roles document no-backup status in README only (no empty `tasks/backup.yml` no-op files). Names all 8: `loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`, `opentelemetry`, `nfsd`. Distinguishes Loki/Tempo/Mimir (data in Garage S3) from the 5 truly-stateless roles. |
| Closing paragraph | Names all 3 orchestrator-level out-of-gate concerns explicitly (`backup_continue_on_failure` knob, writer-quiesce on Garage restore, `any_errors_fatal: true` hardcode); forward-points to `docs/quickstart.md#backup-and-restore`; closes with the Gate-10-pattern line "Established in Phase 13-14 plans; future role additions inherit this contract." |

Net change: +14 lines (one blank separator + 13-line Gate 11 block).

ASCII `--` double-hyphen used in all em-dash positions, matching Gate 10's existing convention. Zero non-ASCII characters introduced in Gate 11. Pre-existing ☑ checkboxes in the port-status table at lines 9-21 are out-of-scope per Phase 12 12-VERIFICATION.md anti-patterns table.

## Deviations from Plan

### Minor stylistic adaptation (file-convention precedence)

**Gate 11 source-line count: 13 lines, plan budget 15-30 lines.**

The plan's stated body-length budget (15-30 lines) was derived from `15-CONTEXT.md`'s `<specifics>` worked example, which hard-wraps each paragraph at ~70 columns yielding ~25 source lines. The actual `roles/README.md` Gate 10 (the structural analog Gate 11 must mirror) uses no-wrap one-paragraph-per-source-line convention -- Gate 10 measures 17 lines, of which 5 are sub-clauses (a)-(e) plus a 1-line nfsd divergent paragraph plus closing paragraph plus blank separators.

Gate 11 has 3 sub-clauses (a)/(b)/(c) per the plan's structural spec (D-207 specifies 3 sub-clauses; the plan explicitly says "Planner MAY add a 4th sub-clause (d) only if a genuinely distinct contract element emerges; recommended to fold these into clauses (a)/(b) prose to keep the gate at 3 clauses matching the CONTEXT worked example"). With 3 sub-clauses + lede + contract statement + divergent paragraph + closing paragraph = 6 paragraphs + 5 blank-line separators + 1 lede + 1 contract = 13 source lines, matching the file's no-wrap convention.

The 15-30 budget reflects the worked example's line-wrapping; my output matches the actual file's existing convention (Gate 10 is one paragraph per source line). Rationale: file-convention precedence beats budget-derived-from-wrapped-example. All 17 acceptance-criteria gates pass at 13 lines.

### Pre-existing conditions (not introduced by this plan)

**Pre-existing non-ASCII characters in `roles/README.md`:** The ☑ checkboxes in the port-status table at lines 9-21 are Unicode (present before this plan). My Gate 11 edit (lines 124-136) introduces zero non-ASCII characters; verified via `awk '/^\*\*11\./{f=1} f{print; if(/Established in Phase 13-14/) f=0}' roles/README.md | grep -Pn '[^\x00-\x7F]'` returning empty. Out-of-scope per Phase 12 12-VERIFICATION.md anti-patterns table; logged here for traceability.

### Auto-fixed issues

None -- both tasks executed exactly as the plan prescribed.

## DOCS-V13-01 + DOCS-V13-02 Closure Statement

**DOCS-V13-01 met (in full):** `roles/README.md` Gate 11 inserted. Contains:
- Bold lede matching `^\*\*11\. ` with contract name "Per-role backup/restore contract" and D-IDs `D-176..D-179`.
- Contract-artifact file names verbatim: `tasks/backup.yml`, `tasks/restore.yml`.
- Acceptance heuristic phrase: `proven on leviathan`.
- All 4 stateful roles (`garage`, `prometheus`, `grafana`, `alertmanager`) and all 8 stateless roles (`loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`, `opentelemetry`, `nfsd`) named verbatim in backticks for grep-discoverability.
- 3 sub-clauses (a)/(b)/(c) covering cold-quiesce-with-block-rescue-always, confirm-gate + tar tf + wipe + untar + restart + verify, zstd pre-task idempotency.
- Closing paragraph with all 3 orchestrator-level concerns named (`backup_continue_on_failure`, writer-quiesce on Garage restore, `any_errors_fatal: true`), forward-pointer to `docs/quickstart.md#backup-and-restore`, closing-line pattern `future role additions inherit this contract`, Phase 13-14 origin attribution.
- Gate 10 unchanged (Phase 12 plan 12-03 output preserved); Gate 10 line-orders before Gate 11.

**DOCS-V13-02 met (root README clause):** `README.md` Quick start now contains the "When something goes wrong" paragraph linking to `docs/quickstart.md#backup-and-restore`. Sits AFTER the existing "When you're done evaluating" paragraph (sibling-paragraph ordering -- D-206) and BEFORE `## What's included`. All locked elements present verbatim. The H2 main clause of DOCS-V13-02 is closed by plan 15-01 in the same Wave 1.

## Known Stubs

None. Both edits are fully wired prose with concrete link targets. The `docs/quickstart.md#backup-and-restore` anchor is created by plan 15-01 (same Wave 1); the link is correct for post-merge state, consistent with the Phase 12 wave-1 precedent (12-03 forward-referenced an anchor created by 12-01).

## Threat Flags

None. Both edits are Markdown prose only; no code, config, secrets, or new network surface introduced. All STRIDE threats in the plan's `<threat_model>` (T-15-12 through T-15-17) are LOW severity doc-only concerns mitigated by:

- T-15-12 (link target stability): acceptance criterion asserts exact link target string `docs/quickstart.md#backup-and-restore` -- verified present in both files.
- T-15-13 (role-enumeration completeness): acceptance criterion enforced verbatim backtick-enclosed inline-code mentions of all 12 deployed role names -- all 12 verified present.
- T-15-14 (contract-sub-clause fidelity): acceptance criterion asserted key contract substrings (`tasks/backup.yml`, `tasks/restore.yml`, `proven on leviathan`) -- all 3 verified present.
- T-15-15 (in-gate/out-of-gate scope distinction): acceptance criterion asserted all 3 out-of-gate concerns named (`backup_continue_on_failure`, writer-quiesce, `any_errors_fatal`) -- all 3 verified present.
- T-15-16 (D-ID asymmetry contributor vs operator): Pattern S3 enforced -- `D-176..D-179` cited in `roles/README.md` Gate 11 lede; zero D-XXX references in `README.md`.
- T-15-17 (Gate 10 non-regression): Gate 10 lede `^\*\*10\. ` exists and line-orders before Gate 11; Gate 10 closing paragraph byte-for-byte identical to pre-edit state.

## Self-Check: PASSED

Files confirmed:
- `README.md` -- modified, contains "When something goes wrong" paragraph: FOUND
- `roles/README.md` -- modified, contains Gate 11 entry with all required substrings: FOUND
- `.planning/phases/15-documentation-cascade/15-03-SUMMARY.md` -- this file: FOUND

Commits confirmed:
- `338bb8c` (Task 1 -- README.md): FOUND
- `5a1dba3` (Task 2 -- roles/README.md): FOUND

Required-phrase gates confirmed (full re-run after both commits):
- README.md: `When something goes wrong` (lede), `docs/quickstart.md#backup-and-restore` (link target), `backup_restore_confirm=true` (knob name), `operator manages retention` (framing) -- all FOUND.
- roles/README.md: `**11. ` (Gate 11 lede), `tasks/backup.yml`, `tasks/restore.yml`, `proven on leviathan`, `docs/quickstart.md#backup-and-restore`, `future role additions inherit this contract`, `backup_continue_on_failure`, `any_errors_fatal` -- all FOUND.
- All 4 stateful + 8 stateless role names in backtick-delimited inline code in `roles/README.md`: all FOUND.

Structural gates confirmed:
- README.md line ordering: `## Quick start` → `When you're done evaluating` → `When something goes wrong` → `## What's included` -- VERIFIED in order.
- roles/README.md line ordering: Gate 10 (line 106) line-orders before Gate 11 (line 124) -- VERIFIED.
- Code-fence balance: README.md has 6 fences (even), roles/README.md has 8 fences (even) -- BOTH BALANCED.
- ASCII-only in new content: zero non-ASCII characters introduced in Task 1 or Task 2 edits -- VERIFIED.
- Gate 10 closing line byte-for-byte unchanged from pre-edit state -- VERIFIED via grep -F.
