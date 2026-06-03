---
phase: 10-per-role-uninstall-surface
plan: 03
subsystem: infra
tags: [ansible, garage, undeploy, uninstall, s3, docker]

# Dependency graph
requires:
  - phase: 08-garage-role-backend-retargeting
    provides: roles/garage with bootstrap.yml (auto-generated S3 key persisted at garage_s3_credentials_file) and named volumes telemetron_garage_meta + telemetron_garage_data
provides:
  - roles/garage/tasks/uninstall.yml — default-conservative undeploy that stops the container and removes ephemeral host-side state (config dir + S3 credentials file) while preserving named volumes (logs, metrics, traces data survive)
  - D-146 recovery contract proven by code: next deploy_docker.yml run regenerates an S3 key via bootstrap.yml first-run branch and re-grants it on the existing buckets via the idempotent `bucket allow` loop (bootstrap.yml lines 188-223)
  - D-147 explicit non-cleanup of orphan keys, documented in the uninstall header as operator hygiene (not Phase 10 scope)
affects: [10-04, 10-05, 10-06, undeploy_docker.yml, operator-undeploy-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-role default-conservative undeploy: container down + ephemeral state purged, named volumes preserved"
    - "Separately-named WARN debug task immediately before destructive `file: state=absent` so the message appears in PLAY OUTPUT instead of as a silent side effect"
    - "Header-comment documentation of recovery flow with explicit upstream-task line citations (bootstrap.yml lines 188-223 for the bucket re-grant cycle)"

key-files:
  created:
    - "roles/garage/tasks/uninstall.yml — 4-task default-conservative undeploy in strict D-145 order"
    - ".planning/phases/10-per-role-uninstall-surface/ (new phase directory)"
  modified: []

key-decisions:
  - "Strict D-145 4-task order: stop container (keep_volumes:true) -> WARN debug -> remove garage_s3_credentials_file -> remove garage_config_dir. Order is load-bearing; the WARN debug exists because it must precede the destructive file: tasks so operators see it in PLAY OUTPUT."
  - "Named volumes telemetron_garage_meta and telemetron_garage_data are deliberately PRESERVED by the default undeploy. Removing operator data (logs, metrics, traces objects) is a separate operator decision, out of Phase 10 scope."
  - "D-147 chosen: no docker_container_exec orphan-key delete. Stopping Garage before reading its key list creates a half-completed-delete failure mode worse than a clean orphan in the registry. Operator hygiene is the right home for that, not the uninstall path."

patterns-established:
  - "Per-role uninstall.yml lives at roles/<role>/tasks/uninstall.yml and is invoked via include_tasks from a top-level undeploy playbook (consumed by Plan 10-04+)."
  - "Recovery-after-undeploy semantics are documented inline in the role's uninstall.yml header with explicit citations to the bootstrap.yml line ranges that perform the recovery — so the next operator reading the file can trace the round-trip without leaving the file."
  - "Destructive `file: state=absent` tasks are preceded by their own named `debug:` WARN task with the literal message text inline, ensuring operator visibility in PLAY OUTPUT."

requirements-completed: []

# Metrics
duration: ~2 min
completed: 2026-05-29
---

# Phase 10 Plan 03: Garage Role Uninstall Surface Summary

**Default-conservative Garage undeploy: container + ephemeral config + credentials file removed; named volumes (Mimir/Loki/Tempo S3 data) preserved; recovery via S3-key auto-regeneration documented inline.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-29T16:15:24Z
- **Completed:** 2026-05-29T16:17:04Z
- **Tasks:** 1 (single-file role addition)
- **Files modified:** 1 created, 0 modified

## Accomplishments

- `roles/garage/tasks/uninstall.yml` shipped with strict D-145 4-task order (container absent + keep_volumes:true; separately-named WARN debug; credentials file absent; config dir absent).
- D-146 recovery flow documented in the header with explicit line-range citation of `bootstrap.yml:188-223` (the bucket create + idempotent `bucket allow` loop that re-grants the freshly auto-generated S3 key on the surviving buckets).
- D-147 orphan-key non-cleanup decision documented inline so the next operator/maintainer reading the role can immediately see why no `docker_container_exec /garage key delete` task exists.
- `ansible-lint --profile production` passes on the new file.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add garage role uninstall.yml** — `9f90cbb` (feat)

**Plan metadata:** to be added in final commit below (this SUMMARY.md).

## Files Created/Modified

- `roles/garage/tasks/uninstall.yml` (CREATED, 100 lines) — Default-conservative Garage undeploy: 4 Ansible tasks in strict D-145 order with a 53-line header documenting D-146 recovery and D-147 non-cleanup decisions.
- `.planning/phases/10-per-role-uninstall-surface/10-03-SUMMARY.md` (CREATED, this file).

## Decisions Made

- **Single-commit task split:** The plan describes 4 Ansible tasks inside a single small role file. Splitting that into 4 separate git commits would have produced 3 intermediate states that fail lint (a debug WARN without the destructive task it warns about; a destructive task without the WARN that should precede it). The atomic 4-task addition is the smallest reviewable unit that is internally consistent. Committed as one `feat(10-03)` commit.
- **D-145 task order preserved verbatim:** Container `state: absent` with `keep_volumes: true` is task 1; the WARN debug is task 2; `file: state=absent` for credentials is task 3; `file: state=absent` for config dir is task 4. The order is documented as load-bearing in the header comment so future contributors don't reorder for "cleanliness."
- **Header comment cites BOTH a narrow line range (211-223 for `bucket allow`) AND a broader range (188-223 for bucket create + allow) per the success criterion.** Both ranges describe the same recovery, just at different granularity; the broader range matches the success criterion text and the narrower line callout helps a reader find the exact `allow` loop quickly.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- The `.planning/phases/10-per-role-uninstall-surface/` directory did not exist at the worktree's spawn-time HEAD (`b3b7b3e`). Resolution: created the directory as part of writing this SUMMARY.md. This is a planning-state artifact (Phase 10 only had its `STATE.md` cursor advanced in the prior commit; per-phase directory creation is the executor's job on first plan in a phase).
- Pre-existing modification to `.planning/STATE.md` was carried in by the worktree spawn-time checkout. Per the `<parallel_execution>` directive, I do NOT modify STATE.md; the orchestrator owns that write.

## User Setup Required

None — Ansible role change only, no external services or secrets involved. The `uninstall.yml` will be wired into a top-level `undeploy_docker.yml` playbook by a later Phase 10 plan (Plan 10-04 or later).

## Next Phase Readiness

- `roles/garage/tasks/uninstall.yml` is invoke-ready via `include_tasks: roles/garage/tasks/uninstall.yml` from a future top-level undeploy playbook.
- Same per-role uninstall.yml pattern (header comment + strict task order + separately-named WARN debug + preserve-named-volumes-by-default) is now established for the rest of Phase 10's stateful-role plans (loki, tempo, mimir uninstalls).
- No blockers carried forward.

## Self-Check: PASSED

- FOUND: `roles/garage/tasks/uninstall.yml`
- FOUND: `.planning/phases/10-per-role-uninstall-surface/10-03-SUMMARY.md`
- FOUND commit `9f90cbb` in `git log --oneline --all`

---
*Phase: 10-per-role-uninstall-surface*
*Completed: 2026-05-29*
