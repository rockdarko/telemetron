---
phase: 10-per-role-uninstall-surface
plan: 01
subsystem: infra
tags: [ansible, docker, undeploy, lifecycle, role-task, uninstall]

# Dependency graph
requires:
  - phase: 02-telemetry-backends
    provides: loki/tempo/mimir deploy roles with named data volumes (telemetron_{loki,tempo,mimir}_data)
  - phase: 03-ingest-plane
    provides: prometheus deploy role with telemetron_prometheus_data volume
  - phase: 04-alert-plane
    provides: alertmanager deploy role with telemetron_alertmanager_data volume
  - phase: 05-ui-plane
    provides: grafana + karma deploy roles (grafana has telemetron_grafana_data; karma is stateless)
  - phase: 08-garage-role-backend-retargeting
    provides: telemetron_volume_prefix / telemetron_config_root default-naming patterns
provides:
  - "7 tasks/uninstall.yml files (alertmanager, grafana, karma, loki, mimir, prometheus, tempo)"
  - "Per-role surface that removes the container (state=absent, keep_volumes=true) and role-private /opt/telemetron/<role>/"
  - "Volume-preservation contract: named *_data_volume vars are NEVER touched by these files (UNDEPLOY-02)"
  - "Standard inversion shape ready for Phase 11 orchestrator (include_role: tasks_from: uninstall, D-132)"
affects: [10-02-fluentbit-opentelemetry, 10-03-garage-credentials, 10-04-node-exporter-edge-case, 10-05-nfsd-host-package, 10-06-gate10-readme, 11-undeploy-orchestrator, 12-doc-cascade]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-role uninstall.yml = inverse of tasks/main.yml (container absent + config_dir absent)"
    - "keep_volumes: true on every docker_container removal (UNDEPLOY-02 volume-preservation guard)"
    - "Role tag only on uninstall tasks (D-133); no <role>-uninstall sub-tag"
    - "No notify: in uninstall tasks (D-142); restart handlers stay deploy-only"
    - "References {{ <role>_container_name }} / {{ <role>_config_dir }} from role defaults (D-134)"

key-files:
  created:
    - "roles/alertmanager/tasks/uninstall.yml"
    - "roles/grafana/tasks/uninstall.yml"
    - "roles/karma/tasks/uninstall.yml"
    - "roles/loki/tasks/uninstall.yml"
    - "roles/mimir/tasks/uninstall.yml"
    - "roles/prometheus/tasks/uninstall.yml"
    - "roles/tempo/tasks/uninstall.yml"
  modified: []

key-decisions:
  - "Each uninstall.yml is exactly 2 tasks: docker_container state=absent (with keep_volumes: true), then file: state=absent on the role config dir -- no pre-checks, no verify, no handlers (D-135, D-141)"
  - "keep_volumes: true set even on karma (which has no named volume) for shape consistency across the 7-role set -- documented inline as a deliberate no-op"
  - "Grafana's single file: absent on grafana_config_dir relies on Ansible's recursive default to handle 5 nested provisioning subdirs (provisioning/datasources, provisioning/dashboards, ...) -- NO enumeration"
  - "Prometheus's single file: absent on prometheus_config_dir similarly handles the nested rules/ subdir recursively"

patterns-established:
  - "Uniform inversion contract: every container-based role's uninstall.yml is exactly container-absent + config-dir-absent (no docker_volume, no docker_image, no notify)"
  - "Volume-preservation grep gate: `grep -L 'keep_volumes: true'` across the 7-role set MUST return empty as a UNDEPLOY-02 enforcement check"
  - "Forbidden-construct grep gate: no `docker_volume|notify:|state: restarted|flush_handlers|<role>-uninstall` in uninstall.yml files"

requirements-completed: [UNDEPLOY-02]

# Metrics
duration: 8min
completed: 2026-05-29
---

# Phase 10 Plan 01: Uniform-shape uninstall surfaces (7 roles) Summary

**Per-role `tasks/uninstall.yml` for alertmanager, grafana, karma, loki, mimir, prometheus, tempo -- each file removes its container (state=absent, keep_volumes=true) and its role-private `/opt/telemetron/<role>/` config dir while preserving the named data volume.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-29T16:13Z
- **Completed:** 2026-05-29T16:17Z
- **Tasks:** 2 (both `type="auto"`)
- **Files created:** 7

## Accomplishments

- Shipped 7 of the 12 Phase-10 uninstall files (the uniform container+config_dir shape) -- the other 5 (fluentbit, garage, node_exporter, opentelemetry, nfsd) are wave-2 plans 10-02..10-05.
- Volume-preservation contract enforced everywhere: `keep_volumes: true` on every `docker_container` task; no `docker_volume` task in any of the 7 files. Named volumes (`telemetron_{alertmanager,grafana,loki,mimir,prometheus,tempo}_data`) are guaranteed untouched.
- Existing `playbooks/deploy_docker.yml` still syntax-checks clean -- the new files are loaded only via `include_role: tasks_from: uninstall` (Phase 11's path), so they cannot perturb the deploy path.
- Shape ready for Phase 11's orchestrator: every file uses role-namespaced variables from `defaults/main.yml` (no hardcoded paths), single role tag (no sub-tag), no `notify:` (no handler races on teardown).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create uninstall.yml for loki, tempo, mimir, prometheus** -- `6746966` (feat)
2. **Task 2: Create uninstall.yml for alertmanager, grafana, karma** -- `a083fe5` (feat)

_Plan metadata commit will be made by the orchestrator after wave-1 merges._

## Files Created/Modified

- `roles/alertmanager/tasks/uninstall.yml` -- container absent + alertmanager_config_dir absent; preserves telemetron_alertmanager_data
- `roles/grafana/tasks/uninstall.yml` -- container absent + grafana_config_dir absent (recursive -- 5 nested provisioning subdirs); preserves telemetron_grafana_data
- `roles/karma/tasks/uninstall.yml` -- container absent + karma_config_dir absent; no named volume (karma is stateless), keep_volumes: true set for shape consistency
- `roles/loki/tasks/uninstall.yml` -- container absent + loki_config_dir absent; preserves telemetron_loki_data (compactor markers per PITFALLS Pitfall 12)
- `roles/mimir/tasks/uninstall.yml` -- container absent + mimir_config_dir absent; preserves telemetron_mimir_data
- `roles/prometheus/tasks/uninstall.yml` -- container absent + prometheus_config_dir absent (recursive -- rules/ subdir); preserves telemetron_prometheus_data
- `roles/tempo/tasks/uninstall.yml` -- container absent + tempo_config_dir absent; preserves telemetron_tempo_data

## Decisions Made

- **Plain two-task shape** -- followed the plan verbatim. No pre-checks (`docker_container_info`/`stat`) per D-141; trust `state: absent` semantics for idempotency.
- **`keep_volumes: true` on karma anyway** -- karma has no named volume but the flag is set for shape uniformity across the 7-role set. Documented as a deliberate no-op in the inline header comment so future readers don't think it's a stray copy-paste.
- **No `meta: flush_handlers`** -- the deploy paths for prometheus and alertmanager use `meta: flush_handlers` before verify; uninstall doesn't need it because uninstall does not notify any handler (D-142). Plan called this out and it was honoured.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Absolute-path-to-main-repo silent write (worktree path safety)**

- **Encountered during:** Task 1 file writes
- **Symptom:** Initial `Write` calls used absolute paths under `/home/darko/git/rockdarko/telemetron/roles/...` rather than the worktree path under `/home/darko/git/rockdarko/telemetron/.claude/worktrees/agent-a6552a62d5af02ea2/roles/...`. The Write tool reported success, but the files landed in the main repo instead of the worktree (per the `worktree-path-safety` execution-context reference, issue #3099).
- **Resolution:** Detected via subsequent verification (`test -f roles/loki/tasks/uninstall.yml` failed). Removed the misplaced files from the main repo, re-wrote them using the worktree-absolute paths, and re-ran verification. No commits were affected (the issue was caught before staging).
- **Prevention:** Subsequent writes used the explicit worktree-absolute path. Worth surfacing in `references/worktree-path-safety.md` if not already covered.

No other problems during planned work.

## User Setup Required

None - no external service configuration required. These files are deploy-time artifacts only; Phase 11's orchestrator playbook (`playbooks/undeploy_docker.yml`) will invoke them.

## Next Phase Readiness

- 7 of 12 Phase-10 uninstall files shipped (uniform-shape set). Wave-2 plans 10-02..10-05 handle the differentiated roles: fluentbit+opentelemetry (10-02), garage with S3 credentials WARN (10-03), node_exporter container-only edge case (10-04), nfsd host-package variant (10-05). Plan 10-06 adds Gate 10 to `roles/README.md`.
- Phase 11's orchestrator can iterate these 7 roles uniformly: `include_role: { name: <role>, tasks_from: uninstall }` in reverse-deploy order (tempo -> mimir -> loki -> alertmanager -> grafana -> karma -> prometheus). The role tag flows through naturally for `--tags <role>` scoping.

## Self-Check: PASSED

- **roles/alertmanager/tasks/uninstall.yml** -- FOUND
- **roles/grafana/tasks/uninstall.yml** -- FOUND
- **roles/karma/tasks/uninstall.yml** -- FOUND
- **roles/loki/tasks/uninstall.yml** -- FOUND
- **roles/mimir/tasks/uninstall.yml** -- FOUND
- **roles/prometheus/tasks/uninstall.yml** -- FOUND
- **roles/tempo/tasks/uninstall.yml** -- FOUND
- **Commit 6746966 (Task 1)** -- FOUND in git log
- **Commit a083fe5 (Task 2)** -- FOUND in git log
- **ansible-playbook --syntax-check** -- PASS on playbooks/deploy_docker.yml
- **Volume-preservation grep gate** -- PASS (`grep -L 'keep_volumes: true'` returns empty across the 7-file set)
- **Forbidden-construct grep gate** -- PASS (no `docker_volume|notify:|state: restarted|flush_handlers|<role>-uninstall` in any of the 7 files)

---
*Phase: 10-per-role-uninstall-surface*
*Completed: 2026-05-29*
