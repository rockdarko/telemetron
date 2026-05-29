---
phase: 10-per-role-uninstall-surface
plan: 04
subsystem: infra
tags: [ansible, docker, uninstall, undeploy, node_exporter, opentelemetry, gate-10, edge-case]

# Dependency graph
requires:
  - phase: 03-ingest-plane
    provides: roles/node_exporter and roles/opentelemetry deploy surface (tasks/main.yml, defaults/main.yml)
provides:
  - "roles/node_exporter/tasks/uninstall.yml (single docker_container state=absent task; D-143 edge case)"
  - "roles/opentelemetry/tasks/uninstall.yml (docker_container state=absent + file state=absent on opentelemetry_config_dir)"
  - "Gate 10 uniformity for the two ingest-plane edge cases (container-only role + container+config_dir-no-volume role)"
affects: [phase-10-other-uninstall-plans, phase-11-undeploy-orchestrator, phase-12-docs-cascade]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-task uninstall.yml (container-only edge case) -- ship file for Gate 10 uniformity even when only the container exists, so the Phase 11 orchestrator iterates roles without per-role conditional logic (D-143)"
    - "Two-task uninstall.yml (container + config_dir, no named volume) -- mirror of Plan 10-01 karma shape applied to opentelemetry"
    - "Host-path safety contract documented in leading comment block: name every RO bind source the deploy container touches (/proc, /sys, / for node_exporter; /var/run/docker.sock for opentelemetry) and explicitly state uninstall MUST NEVER `file: state=absent` them"

key-files:
  created:
    - roles/node_exporter/tasks/uninstall.yml
    - roles/opentelemetry/tasks/uninstall.yml
  modified: []

key-decisions:
  - "node_exporter ships tasks/uninstall.yml as a single docker_container state=absent task per D-143 -- preserves Gate 10 uniformity (every deploy role has an uninstall path so Phase 11 orchestrator iterates without conditional logic) even though no config_dir and no named volume exist."
  - "Both files set keep_volumes:true on the docker_container state=absent task even where no named volume exists -- semantic no-op, documents the UNDEPLOY-02 preservation intent uniformly across the Phase 10 surface."
  - "Leading comment block in each file enumerates the host RO bind sources the deploy container touches and explicitly forbids uninstall from removing them (node_exporter: /proc /sys /; opentelemetry: /var/run/docker.sock). T-10-NE-01 and T-10-OT-01 STRIDE mitigations are encoded in the file itself, not just in the plan."

patterns-established:
  - "Edge-case uniformity: Gate 10 forbids per-role conditional logic in the Phase 11 orchestrator -- single-task uninstall.yml is the design answer for stateless container-only roles"
  - "Host RO bind sources are never uninstall targets -- the container removal implicitly drops the bind references; uninstall scope is role-private artifacts only (UNDEPLOY-02)"

requirements-completed: [UNDEPLOY-02]

# Metrics
duration: ~2min
completed: 2026-05-29
---

# Phase 10 Plan 04: Edge-Case Uninstall Surfaces (node_exporter, opentelemetry) Summary

**Two `tasks/uninstall.yml` files added for the Phase 3 ingest-plane edge cases: node_exporter as a one-task container-only file (D-143 Gate 10 uniformity) and opentelemetry as a two-task container+config_dir file (no named volume).**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-29T16:15:34Z
- **Completed:** 2026-05-29T16:16:52Z
- **Tasks:** 2 / 2
- **Files modified:** 2 (both created)

## Accomplishments

- `roles/node_exporter/tasks/uninstall.yml`: single `community.docker.docker_container state=absent` task with `keep_volumes: true`, role tag only, no notify. NO `ansible.builtin.file` task because the role has no config_dir and no named volume. Header documents that `/proc`, `/sys`, `/` are kernel-managed RO bind sources the uninstall MUST NEVER `file: state=absent`.
- `roles/opentelemetry/tasks/uninstall.yml`: two-task file -- `docker_container state=absent` (keep_volumes:true) followed by `ansible.builtin.file state=absent` on `{{ opentelemetry_config_dir }}`. Header documents that `/var/run/docker.sock` is RO-bind-mounted by the deploy container for the `docker_stats` receiver and the uninstall MUST NEVER touch it.
- Gate 10 contract (every deploy role ships a tested uninstall path) is preserved uniformly for these two edge-case shapes -- Phase 11's orchestrator can call `include_role: { name: node_exporter, tasks_from: uninstall }` and `include_role: { name: opentelemetry, tasks_from: uninstall }` without any per-role conditional.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create roles/node_exporter/tasks/uninstall.yml (single-task, container-only)** -- `9e5bc90` (feat)
2. **Task 2: Create roles/opentelemetry/tasks/uninstall.yml (container + config_dir, no volume)** -- `a2899ac` (feat)

## Files Created/Modified

- `roles/node_exporter/tasks/uninstall.yml` (created) -- single-task container-only uninstall, Gate 10 uniformity per D-143; host-path safety contract documented in leading comment block.
- `roles/opentelemetry/tasks/uninstall.yml` (created) -- two-task container + config_dir uninstall (no named volume), mirrors Plan 10-01 karma shape; docker-socket safety contract documented in leading comment block.

## Shape Confirmation

Single-task vs two-task shapes as required by the plan:

- **node_exporter**: **1 task** -- `docker_container state=absent` only. Verified by `python3 -c "import yaml; d=yaml.safe_load(open('roles/node_exporter/tasks/uninstall.yml')); assert len(d)==1"`. No `ansible.builtin.file` task in the file (no config_dir to remove). `grep -vE '^\s*#' roles/node_exporter/tasks/uninstall.yml | grep -E '(/proc|/sys|/var/run)'` returns nothing.
- **opentelemetry**: **2 tasks** -- `docker_container state=absent` then `file state=absent` on `{{ opentelemetry_config_dir }}`. Verified by `python3 -c "import yaml; d=yaml.safe_load(open('roles/opentelemetry/tasks/uninstall.yml')); assert len(d)==2"`. `grep -vE '^\s*#' roles/opentelemetry/tasks/uninstall.yml | grep -E '/var/run/docker\.sock'` returns nothing.

## Host-Path Safety Contracts Enforced

- **node_exporter (T-10-NE-01)**: deploy container RO-bind-mounts `/proc -> /host/proc`, `/sys -> /host/sys`, `/ -> /host/root` (with `propagation: rslave`). Uninstall.yml's leading comment block explicitly names these as kernel-managed real filesystems and forbids `file: state=absent` against them. The file contains no `ansible.builtin.file` task, no `docker_volume` task, no `notify:`, no `state: restarted`, and no sub-tag -- structurally cannot regress.
- **opentelemetry (T-10-OT-01)**: deploy container RO-bind-mounts `/var/run/docker.sock` (host docker socket, for `docker_stats` receiver per D-52). Uninstall.yml's leading comment block explicitly forbids touching the socket. The `file: state=absent` task targets `{{ opentelemetry_config_dir }}` only; `grep -vE '^\s*#' ... | grep -E '/var/run/docker\.sock'` returns nothing.

## D-143 Gate 10 Uniformity Preserved

D-143 mandates that node_exporter ship `tasks/uninstall.yml` even though it has no config_dir and no named volume -- the rationale is that the Phase 11 orchestrator must iterate all deploy roles via `include_role: { name: <role>, tasks_from: uninstall }` without any per-role conditional logic. This plan delivers that file as a one-task `docker_container state=absent` (with `keep_volumes: true` set for shape consistency with the rest of the Phase 10 surface, semantically a no-op). Gate 10's contract holds uniformly across the two edge cases shipped here.

## Decisions Made

- **D-143 enforced literally**: node_exporter uninstall is a single-task file with no `file:` module at all. The temptation to add a no-op `file: state=absent` for symmetry was explicitly rejected: there is no host artifact to remove, and adding a placeholder would obscure the genuine D-143 edge-case shape from review.
- **`keep_volumes: true` set uniformly even on roles with no named volume**: documents UNDEPLOY-02 preservation intent and matches Plan 10-01 / 10-02 / 10-03 shape so the Phase 11 orchestrator's per-role include never has to reason about "does this role have a volume."

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None -- this plan ships role-internal files only. No external service configuration, no inventory variable changes, no operator action required. Phase 11 will wire these into the orchestrator playbook.

## Next Phase Readiness

- Two of the twelve `tasks/uninstall.yml` files in Phase 10 scope are now shipped (the two ingest-plane edge cases). The remaining ten roles (alertmanager, fluentbit, garage, grafana, karma, loki, mimir, prometheus, tempo, nfsd) are addressed by Plan 10-01 through Plan 10-03 and 10-05.
- Phase 11's `playbooks/undeploy_docker.yml` orchestrator can now safely call `include_role: { name: node_exporter, tasks_from: uninstall }` and `include_role: { name: opentelemetry, tasks_from: uninstall }` once it lands.
- No blockers.

## Self-Check: PASSED

- `roles/node_exporter/tasks/uninstall.yml` exists: FOUND
- `roles/opentelemetry/tasks/uninstall.yml` exists: FOUND
- Commit `9e5bc90` (Task 1) present in git log: FOUND
- Commit `a2899ac` (Task 2) present in git log: FOUND
- `ansible-playbook --syntax-check -i inventory/example-homelab/hosts.yml playbooks/deploy_docker.yml` exits 0: PASS

---
*Phase: 10-per-role-uninstall-surface*
*Completed: 2026-05-29*
