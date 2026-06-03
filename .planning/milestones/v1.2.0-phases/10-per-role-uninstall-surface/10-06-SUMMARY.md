---
phase: 10-per-role-uninstall-surface
plan: 06
subsystem: docs / gates
tags: [docs, roles-readme, gate-10, uninstall-contract, UNDEPLOY-02, D-148]
requires:
  - UNDEPLOY-02
provides:
  - "roles/README.md Gate 10 (Per-role uninstall contract) documenting the cross-cutting requirement that every deploy role ships a tested tasks/uninstall.yml"
affects:
  - "Future role additions inherit the per-role uninstall contract via documented gate; reviewers can grep for ^\\*\\*10\\. before merging a new role"
tech-stack:
  added: []
  patterns:
    - "Cross-cutting gate documentation in roles/README.md per-role port-acceptance gates section"
key-files:
  created: []
  modified:
    - roles/README.md
decisions:
  - "Gate 10 numbering (not Gate 9) preserves the existing Datasources gate added in Plan 05-01 / D-73; CONTEXT.md and ROADMAP.md were patched during planning to match"
  - "Gate 10 documents (a)..(e) as prose, not as a code block — matches Gate 4 / Gate 9 style; code blocks reserved for pattern visuals (Gate 7 / Gate 8)"
  - "nfsd host-package adaptation called out explicitly in Gate 10 body (D-136..D-140) so reviewers don't expect a uniform container-only contract"
  - "Phase 11 orchestrator behaviour scoped OUT of Gate 10; reserved as 'Gate 11 in Phase 11 if needed' to avoid prematurely locking Phase 11 design"
metrics:
  duration: ~6m
  completed: 2026-05-29
---

# Phase 10 Plan 06: Per-Role Uninstall Surface — Gate 10 Documentation Summary

Documented the Phase 10 per-role uninstall contract as Gate 10 in `roles/README.md`, ensuring every future role added to Telemetron inherits the requirement (UNDEPLOY-02; D-148).

## Gate 10 heading (verbatim)

```
**10. Per-role uninstall contract (UNDEPLOY-02; D-148):**
```

## Tasks Completed

| Task | Name                                                                              | Commit  | Files            |
| ---- | --------------------------------------------------------------------------------- | ------- | ---------------- |
| 1    | Insert Gate 10 (Per-role uninstall contract) into roles/README.md after Gate 9    | 59983fb | roles/README.md  |

## Verification — all plan acceptance criteria satisfied

Plan verification script output:
```
g9_line=91 g10_line=106 gate_count=10
OK
```

Per-criterion breakdown:
- [x] `roles/README.md` contains a line matching the regex `^\*\*10\. Per-role uninstall contract` (line 106).
- [x] Gate 10 block appears AFTER the existing Gate 9 heading (g9_line=91, g10_line=106).
- [x] Gate 10 body contains the literal phrase "Every deploy role MUST ship a tested uninstall path." (introductory sentence after the bold heading).
- [x] Gate 10 body contains all five contract item markers `(a)` through `(e)` (one per paragraph).
- [x] Gate 10 body references the literal substring `keep_volumes: true` (Gate 10 part (b)).
- [x] Gate 10 body references `telemetron_purge_data=true` (Gate 10 part (d) scope-out + closing paragraph).
- [x] Gate 10 body mentions `nfsd`, `/etc/exports`, and `exportfs -ra` (nfsd adaptation paragraph).
- [x] Gate 10 body mentions `Phase 11` (closing scope-out paragraph).
- [x] Gate 10 body does NOT mention `Gate 9` as the uninstall contract — uninstall is identified as Gate 10 throughout; Gate 9 references in the file remain confined to the pre-existing Datasources gate.
- [x] Existing Gates 1-9 unchanged. Total numbered-gate count in the per-role port-acceptance gates section = 10 (was 9 before the edit).
- [x] `ansible-playbook --syntax-check -i inventory/example-homelab/hosts.yml playbooks/deploy_docker.yml` still passes (only paramiko TripleDES deprecation warnings, no syntax errors). README-only edit cannot affect Ansible syntax; this is the plan's belt-and-braces sanity check.

## Positioning of Gate 10 (line numbers)

Before the edit:
- Gate 9 heading at line 91
- Gate 9 body ended at line 104 (last line of file)

After the edit:
- Gate 9 heading at line 91 (unchanged)
- Gate 9 body ends at line 104 (unchanged)
- Blank line at line 105
- Gate 10 heading at line 106
- Gate 10 body runs through line 122

`grep -nE '^\*\*[0-9]+\. ' roles/README.md` returns exactly 10 hits (Gates 1, 2, 3, 4, 5, 6, 7, 8, 9, 10) at lines 41, 51, 53, 55, 57, 59, 61, 71, 91, 106.

## No existing gate renumbered

Before the edit, `grep -E '^\*\*[1-9]\. '` returned 9 lines (Gates 1-9). After the edit, the same grep returns the same 9 lines byte-identical — no existing gate was modified, renumbered, or displaced. The new Gate 10 was appended, separated by one blank line from the closing "Auth:" paragraph of Gate 9.

## Deviations from Plan

None — plan executed exactly as written. The plan's pre-resolved gate-numbering decision (Gate 10, not Gate 9) was honored throughout. The Edit tool was used with Gate 9's existing closing "Auth: Basic Auth ..." sentence as the anchor, per the plan's explicit instruction to avoid Write.

## Authentication Gates

None — this plan is a documentation-only edit on a local file.

## Known Stubs

None — Gate 10 is a complete contract specification with all five required parts (a)..(e), the nfsd adaptation, and the Phase 11 scope-out.

## Self-Check: PASSED

- File modified: `roles/README.md` — FOUND.
- Commit: `59983fb` — FOUND in `git log` on `worktree-agent-af711b46c652a6e11`.
- Plan verification script (10-step assertion chain from `<verify><automated>`): PASSED.
- Gate count assertion (must equal 10): PASSED (was 9, now 10).
- "No `**9. .*uninstall` line" assertion (the gate-numbering anti-collision check): PASSED (uninstall gate is at `**10.`, not `**9.`).
- Plan output requirement: a-d (Gate 10 heading quoted verbatim, Gate 10 positioning confirmed with line numbers, total gate count = 10 confirmed, no existing gate renumbered confirmed) all addressed above.
