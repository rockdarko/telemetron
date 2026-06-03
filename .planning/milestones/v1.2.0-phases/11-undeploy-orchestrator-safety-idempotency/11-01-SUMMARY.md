---
phase: 11-undeploy-orchestrator-safety-idempotency
plan: 01
subsystem: infra
tags: [ansible, docker, undeploy, purge, irreversible, karma, node_exporter, opentelemetry]

# Dependency graph
requires:
  - phase: 10-per-role-uninstall-surface
    provides: "Per-role tasks/uninstall.yml + D-133 single-tag rule + sibling shape for purge.yml to mirror"
provides:
  - "roles/karma/tasks/purge.yml -- image-only purge surface"
  - "roles/node_exporter/tasks/purge.yml -- image-only purge surface"
  - "roles/opentelemetry/tasks/purge.yml -- image-only purge surface"
  - "Canonical 3-task D-159 WARN-before-destructive shape (image-only variant) for Plans 11-02 (volume-bearing roles) and 11-03 (two-image roles) to extend"
affects:
  - 11-02-PLAN.md  # 7 volume-bearing roles extend the canonical shape with telemetron_purge_data section
  - 11-03-PLAN.md  # grafana + loki two-image purge.yml extends with loop over [primary, curl] images
  - 11-04-PLAN.md  # playbooks/undeploy_docker.yml include_role: tasks_from: purge for each role

# Tech tracking
tech-stack:
  added: []  # No new tools; shape established with stock community.docker + ansible.builtin
  patterns:
    - "D-159 single-line grep-friendly WARN template (`WARNING: irreversible -- <role> <action>: <targets>`) applied to image-only purge"
    - "D-145 separately-named pre-action debug task + D-154 failed_when:false + register pattern (NOT ignore_errors) for non-fatal in-use detection"
    - "D-153 belt-and-suspenders when: gate on telemetron_purge_images at every task (in addition to the orchestrator's include-level gate)"

key-files:
  created:
    - roles/karma/tasks/purge.yml
    - roles/node_exporter/tasks/purge.yml
    - roles/opentelemetry/tasks/purge.yml
  modified: []

key-decisions:
  - "Image-only roles get a 3-task purge.yml (no telemetron_purge_data section) -- no synthetic placeholder for non-existent volumes"
  - "Shared curl_image (curlimages/curl:8.10.1) is NOT removed by any per-role purge.yml; documented as operator hygiene via `docker image prune` per Phase 11 PATTERNS.md"
  - "OTel Collector host docker socket bind-mount (D-52) is host-managed and explicitly NOT touched in purge -- bind reference vanishes with container removed by uninstall.yml"

patterns-established:
  - "Image-only purge.yml shape: 3 tasks (pre-WARN debug, docker_image state=absent with failed_when:false+register, post-skip WARN debug); single role tag per D-133; D-142 no notify; D-141 state=absent for idempotency trust"
  - "WARN message template literal: `WARNING: irreversible -- <role> purge_images: {{ <role>_image }}:{{ <role>_image_tag }}` -- operator can grep ^WARNING: in PLAY OUTPUT"
  - "Header comment block in every purge.yml documents: orchestrator include path (D-152), belt-and-suspenders rationale (D-153), tag-scoped composition (D-151), why this is image-only (no volume), and host-managed surfaces NOT touched (e.g. OTel docker.sock)"

requirements-completed: [PURGE-01, PURGE-02]

# Metrics
duration: 12min
completed: 2026-05-29
---

# Phase 11 Plan 01: Per-Role Image-Only Purge Surface Summary

**Image-only `tasks/purge.yml` for karma, node_exporter, and opentelemetry — establishes the canonical 3-task D-159 WARN-before-destructive purge shape that Plans 11-02 (volume-bearing roles) and 11-03 (two-image roles) extend.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-29 (worktree wave 1 execution)
- **Completed:** 2026-05-29
- **Tasks:** 3/3
- **Files created:** 3

## Accomplishments

- **3 per-role `purge.yml` files shipped** for the image-only roles (karma, node_exporter, opentelemetry). Each is a 3-task file: pre-action `debug` WARN + `community.docker.docker_image` `state: absent` (failed_when:false + register) + post-skip WARN.
- **D-159 grep-friendly WARN template applied** consistently — operators can `grep ^WARNING:` in PLAY OUTPUT to audit every irreversible action across the 3 roles before it fires.
- **PURGE-02 satisfied for the 3 image-only roles** — the opt-in `telemetron_purge_images=true` flag now has destination wiring for karma/node_exporter/opentelemetry; orchestrator (Plan 11-04) can `include_role: { name: <role>, tasks_from: purge }` for these 3 without "file not found" errors.
- **Conservative default preserved** — every task is gated on `telemetron_purge_images | default(false) | bool`, so the orchestrator including these files with no flag set produces `changed=0` (PURGE-01 conservative default).
- **D-133 single-tag rule honored** — each task carries ONLY its role tag (`karma`, `node_exporter`, `opentelemetry`), no `karma-purge` / `node_exporter-image` / etc. sub-tag. Avoids the regression mode from commit `8dd06dd` (the Phase 10 garage-uninstall sub-tag drop).

## Task Commits

Each task was committed atomically:

1. **Task 1: roles/karma/tasks/purge.yml** — `fc3741b` (feat)
2. **Task 2: roles/node_exporter/tasks/purge.yml** — `3378551` (feat)
3. **Task 3: roles/opentelemetry/tasks/purge.yml** — `c66855f` (feat)

## Files Created/Modified

- `roles/karma/tasks/purge.yml` — image-only purge: WARN → `docker_image state=absent` (failed_when:false, register) → post-skip WARN. Reads `karma_image`/`karma_image_tag` from auto-loaded defaults.
- `roles/node_exporter/tasks/purge.yml` — same 3-task shape; `node_exporter_image` / `node_exporter_image_tag`. Tag is underscore form (`node_exporter`), matching `playbooks/deploy_docker.yml` line 50.
- `roles/opentelemetry/tasks/purge.yml` — same 3-task shape; `opentelemetry_image` / `opentelemetry_image_tag`. Header comment explicitly documents that the D-52 host docker socket bind-mount is NOT touched here (host-managed; bind reference vanishes with the container).

## Decisions Made

- **Image-only shape is the canonical truncation of the two-section template** documented in `11-PATTERNS.md` (the `telemetron_purge_data` section is simply absent — no placeholder, no commented-out skeleton). Operators reading karma's purge.yml don't have to mentally subtract a non-existent volume section.
- **No `karma_curl_image` removal in karma's purge.yml.** Same call applies to node_exporter and opentelemetry. The `curlimages/curl:8.10.1` image is shared across multiple roles (used in `verify.yml` one-shots) — a per-role purge that removes it would race with sibling roles. Documented as `docker image prune` operator hygiene per Plan 11 PATTERNS.md.
- **`failed_when: false` (NOT `ignore_errors: true`) on `docker_image state=absent`** — D-154. `failed_when:false` returns the task as not-failed but still surfaces the result via `register:`, allowing the post-skip WARN debug task to inspect `<role>_purge_image_result.failed | default(false)` and fire a follow-up message. `ignore_errors:true` would swallow legitimate non-in-use errors (e.g. docker daemon unreachable).

## Deviations from Plan

None — plan executed exactly as written. The plan's `<action>` blocks were specific enough to produce 3 files that pass all 13 acceptance-criteria grep checks each on first write (after one comment-string edit on karma to avoid the `! grep telemetron_purge_data` negative test catching the literal word in a header comment — see Issues Encountered below).

## Issues Encountered

**1. Negative-grep tripwire on the literal token `telemetron_purge_data` in a header comment** — caught by the Task 1 verify automated check. The header comment originally read "NO telemetron_purge_data section exists in this file" as a documentation breadcrumb; the verify's `! grep -q "telemetron_purge_data"` (a Rule 1 *acceptance check*, not a *bug*) tripped on it.

- **Resolution:** Rephrased the comment to "This file therefore omits the data-purge section entirely -- there is no named volume to remove." Same intent communicated without the literal token. Applied to karma only; node_exporter and opentelemetry purge.yml were authored after this fix and never carried the literal token.
- **Lesson logged for Plans 11-02 / 11-03:** Comments that mention the canonical knob names (`telemetron_purge_data`, `telemetron_purge_images`) MUST live inside the section they enable, so the negative-grep tests don't trip on documentation prose.

**2. Worktree was branched from commit `8dd06dd`, which predates Phase 11 plan file creation.** The plan file (`.planning/phases/11-undeploy-orchestrator-safety-idempotency/11-01-PLAN.md`) does not exist in the worktree branch; it was read from the main repo checkout. The phase directory was created in the worktree (empty) so SUMMARY.md could be committed at the canonical path. The main-repo plan file will land in the worktree on merge via the orchestrator's normal flow.

## User Setup Required

None — no external service configuration required. All changes are Ansible role files and a planning summary doc.

## Next Phase Readiness

- **Plan 11-02 unblocked** — the canonical 3-task image-only shape established here is the truncation point of the full 5-task data+images shape that 11-02's 7 volume-bearing roles (alertmanager, fluentbit, garage, grafana, loki, mimir, prometheus — minus the two-image roles handled by 11-03) extend with their `telemetron_purge_data` section.
- **Plan 11-03 unblocked** — grafana and loki two-image purge.yml files will mirror the same WARN-template, failed_when:false, register, post-skip pattern but loop over `[primary_image, curl_image]`. The 3 files shipped here are the reference.
- **Plan 11-04 unblocked for these 3 roles** — `playbooks/undeploy_docker.yml` (Plan 11-04) can include karma/node_exporter/opentelemetry purge surfaces via `include_role: { name: <role>, tasks_from: purge }` without "file not found" errors. The remaining 8 roles depend on Plans 11-02 and 11-03 shipping.

## Self-Check: PASSED

- `roles/karma/tasks/purge.yml` — FOUND (commit `fc3741b`)
- `roles/node_exporter/tasks/purge.yml` — FOUND (commit `3378551`)
- `roles/opentelemetry/tasks/purge.yml` — FOUND (commit `c66855f`)
- Commit `fc3741b` — FOUND in worktree branch
- Commit `3378551` — FOUND in worktree branch
- Commit `c66855f` — FOUND in worktree branch
- `ansible-playbook playbooks/deploy_docker.yml --syntax-check` — PASSES (no role-graph integrity errors)

---
*Phase: 11-undeploy-orchestrator-safety-idempotency*
*Completed: 2026-05-29*
