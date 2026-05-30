---
phase: 11-undeploy-orchestrator-safety-idempotency
plan: 03
subsystem: infra
tags: [ansible, ansible-role, docker, docker_volume, docker_image, purge, undeploy, garage, grafana, loki]

# Dependency graph
requires:
  - phase: 10-per-role-uninstall-surface
    provides: per-role tasks/uninstall.yml shape (D-132, D-133, D-141, D-142, D-145) — purge.yml extends the same conventions
  - phase: 08-garage-role-backend-retargeting
    provides: Garage two-volume layout + S3 credentials persistence model (garage_meta_volume, garage_data_volume, garage_s3_credentials_file)
provides:
  - roles/garage/tasks/purge.yml — two-volume loop + single primary image purge surface (D-152)
  - roles/grafana/tasks/purge.yml — single volume + two-image loop purge surface (grafana + curl)
  - roles/loki/tasks/purge.yml — single volume + two-image loop purge surface (loki + curl)
  - canonical "special-case" purge.yml shape that plans 11-01/11-02 follow as analog
affects: [11-04-undeploy-orchestrator-playbook, 11-05-uat-and-verification, 12-docs-cascade]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-volume `loop:` in docker_volume state=absent (D-152) — Garage-specific"
    - "Two-image `loop:` in docker_image state=absent with failed_when:false (D-154 + 11-CONTEXT.md task-count table) — grafana + loki only"
    - "Loop-register accessor: register: <role>_purge_image_results (plural) + .results | selectattr('failed', 'defined') | selectattr('failed') for post-skip WARN"
    - "D-159 single-line grep-friendly WARN format with comma-separated targets when N>1 (volumes or images)"

key-files:
  created:
    - roles/garage/tasks/purge.yml
    - roles/grafana/tasks/purge.yml
    - roles/loki/tasks/purge.yml
  modified: []

key-decisions:
  - "Loop indent uses canonical 2-space Ansible style (loop: as sibling of community.docker.docker_volume:); plan-verify regex `^    loop:` was a planner typo and was treated as documenting the intent (one loop per file) rather than the literal column."
  - "Documentation comments avoid mentioning literal forbidden tokens (garage_curl_image, ignore_errors:true, s3-credentials) so the plan-verify negative greps cleanly return 0 — meaning is preserved via paraphrased descriptions."
  - "Garage purge.yml deliberately omits the curl_image auxiliary per 11-PATTERNS.md `On the curl_image auxiliaries` — only grafana + loki are documented two-image-loop roles; Garage's shared curl image is operator-hygiene (`docker image prune`)."

patterns-established:
  - "Pattern A — Two-volume Garage loop: single docker_volume task with loop: over [{{ garage_meta_volume }}, {{ garage_data_volume }}], one warn task ahead of it that lists both names comma-separated in the msg"
  - "Pattern B — Two-image grafana/loki loop with shared-curl tolerance: failed_when:false on the docker_image loop + register: <role>_purge_image_results + post-skip WARN gated on `.results | selectattr('failed', 'defined') | selectattr('failed') | list | length > 0`"
  - "Pattern C — Single-tag discipline (D-133): every task carries ONLY the role tag (`garage`, `grafana`, `loki`); no sub-tags. Verified by negative grep on `tags:.*<role>-(purge|data|image|meta)`."
  - "Pattern D — Conservative-undeploy scope boundary: purge.yml does NOT re-touch paths Phase 10's uninstall.yml already removes (garage s3-credentials, role config_dir); per-role purge.yml stays strictly to volumes + images."

requirements-completed: [PURGE-01, PURGE-02]

# Metrics
duration: ~12 min
completed: 2026-05-30
---

# Phase 11 Plan 03: Special-case per-role purge.yml surfaces (garage two-volume, grafana/loki two-image) Summary

**Three special-case purge.yml task surfaces shipped: Garage's two-volume loop (meta + data) under a single docker_volume task, plus Grafana and Loki's two-image loops (role primary + shared curlimages/curl) with D-154 shared-curl tolerance via failed_when:false + post-skip WARN.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-30T01:52:00Z (approx)
- **Completed:** 2026-05-30T02:04:46Z (last commit)
- **Tasks:** 3 / 3 (auto)
- **Files created:** 3
- **Files modified:** 0

## Accomplishments

- Garage purge.yml carries the two-volume `loop:` over `{{ garage_meta_volume }}` + `{{ garage_data_volume }}` (D-152) — the unique multi-volume shape the rest of the role catalogue does not need. Pre-loop debug WARN lists BOTH volume names comma-separated so the operator sees the full destruction scope in PLAY OUTPUT.
- Grafana purge.yml carries the two-image `loop:` over `{{ grafana_image }}:{{ grafana_image_tag }}` + `{{ grafana_curl_image }}:{{ grafana_curl_image_tag }}`. `failed_when: false` on the docker_image loop handles the case where loki may already have removed `curlimages/curl` in a reverse-order orchestrator pass.
- Loki purge.yml mirrors Grafana shape verbatim with loki substitutions; same two-image loop, same `failed_when: false`, same `.results | selectattr('failed', 'defined') | selectattr('failed')` post-skip WARN gate.
- Established the loop-register-accessor pattern (`<role>_purge_image_results.results | selectattr('failed', 'defined') | selectattr('failed') | list | length > 0`) that Plan 11-04 can document in the orchestrator README and that any future "multi-target loop with skip-tolerance" surface can reuse.

## Task Commits

Each task was committed atomically:

1. **Task 1: roles/garage/tasks/purge.yml (TWO-volume loop + single image)** — `2d6c149` (feat)
2. **Task 2: roles/grafana/tasks/purge.yml (single volume + TWO-image loop)** — `9b13a98` (feat)
3. **Task 3: roles/loki/tasks/purge.yml (single volume + TWO-image loop)** — `1a5e3bc` (feat)

## Files Created/Modified

- `roles/garage/tasks/purge.yml` (NEW, 125 lines) — 5 tasks. Tasks A/B handle `telemetron_purge_data` (WARN + two-volume loop over meta+data); tasks C/D/E handle `telemetron_purge_images` (WARN + single docker_image + post-skip WARN). Single-image scope per 11-PATTERNS.md.
- `roles/grafana/tasks/purge.yml` (NEW, 114 lines) — 5 tasks. Tasks A/B handle `telemetron_purge_data` (WARN + single docker_volume); tasks C/D/E handle `telemetron_purge_images` (WARN + two-image loop with `failed_when: false` + post-skip WARN that walks `.results`).
- `roles/loki/tasks/purge.yml` (NEW, 114 lines) — 5 tasks. Same shape as grafana with loki substitutions throughout.

## Decisions Made

- **Canonical 2-space loop indent** — The plan-verify regex `^    loop:` (4 spaces) does not match canonical Ansible style. The PATTERNS.md "Special cases" example places `loop:` at 2-space indent (sibling of `community.docker.docker_volume:`), which is also what every existing role's tasks/*.yml uses. I followed PATTERNS.md and the canonical Ansible style and treated the regex as a planner typo. The verify intent — "exactly one `loop:` per file" — is fully satisfied (`grep -c '^  loop:'` returns 1 for each of grafana/loki and 1 for garage).
- **No literal forbidden tokens in header comments** — Initial draft of `roles/garage/tasks/purge.yml` mentioned `garage_curl_image`, `ignore_errors:true`, and `s3-credentials` in explanatory header comments. The plan-verify negative greps use the simple-grep idiom and would have flagged those mentions even though the file did not actually reference the tokens as Ansible code. Rephrased the comments to preserve meaning without using the literal tokens, so both the spirit (no actual usage) and the letter (no token anywhere in the file) of the negative greps are satisfied.
- **`failed_when: false` count > 1 in `grep -c`** — Plain `grep -c 'failed_when: false'` counts both the actual Ansible directive AND the explanatory header comments that name the pattern. The plan-verify uses `grep -q` (presence check, not count), so this is fine; for completeness, `grep -cE '^  failed_when: false'` (anchored at task-indent) returns exactly 1 in each file, confirming a single Ansible directive on the docker_image task.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed literal forbidden tokens from header comments in `roles/garage/tasks/purge.yml`**
- **Found during:** Task 1 (garage purge.yml) verification
- **Issue:** First draft of the file had explanatory header comments that mentioned `garage_curl_image`, `ignore_errors:true`, and `s3-credentials` as part of "why we do NOT reference these here" documentation. The plan-verify negative greps (`! grep -q "garage_curl_image"`, `! grep -q "ignore_errors"`, `! grep -q "s3-credentials"`) flag any occurrence anywhere in the file, including comments.
- **Fix:** Rephrased the comments to describe the intent without using the literal tokens (e.g., "Garage does NOT carry its auxiliary curl image var in this file" instead of "Garage exposes no `garage_curl_image`"). Meaning preserved; verify-greps now cleanly return 0.
- **Files modified:** `roles/garage/tasks/purge.yml`
- **Verification:** `grep -c 'garage_curl_image' roles/garage/tasks/purge.yml` returns 0; `grep -c 'ignore_errors' roles/garage/tasks/purge.yml` returns 0; `grep -c 's3-credentials' roles/garage/tasks/purge.yml` returns 0.
- **Committed in:** `2d6c149` (Task 1 commit; the rephrase happened before the commit was created)

**2. [Rule 1 - Bug, planner regex] Followed canonical Ansible 2-space indent for `loop:` instead of plan-verify's 4-space pattern**
- **Found during:** Task 1 (garage purge.yml) verification
- **Issue:** Plan-verify automated check uses `grep -q "^    loop:"` (4-space indent), but the canonical Ansible style — used by every existing `roles/*/tasks/*.yml` file in this repo AND by the PATTERNS.md "Special cases" example for this very plan — places `loop:` at 2-space indent (as a sibling of `community.docker.docker_volume:`).
- **Fix:** Followed PATTERNS.md and canonical Ansible style. The acceptance-criteria sentence "Contains exactly ONE `loop:` keyword" is the real check; the regex column count was a planner typo. Confirmed with `grep -c '^  loop:'` which returns 1 in each file.
- **Files modified:** All three purge.yml files
- **Verification:** `ansible-playbook playbooks/deploy_docker.yml --syntax-check --tags <role>` passes for garage, grafana, loki. Each file contains exactly one `loop:` keyword at canonical indent.
- **Committed in:** `2d6c149`, `9b13a98`, `1a5e3bc` (each task commit)

---

**Total deviations:** 2 auto-fixed (2 × Rule 1 — both were planner-side verification regex typos, not implementation bugs)
**Impact on plan:** No scope creep. Both fixes preserve the spirit of every acceptance criterion AND every `<threat_model>` mitigation. Verification intent is satisfied via the canonical-style anchored greps shown above; the spirit of "no literal forbidden tokens anywhere in the file" is now strictly satisfied (not just in Ansible code).

## Issues Encountered

- **Worktree did not contain phase 11 plan files at spawn time** — `.planning/` is gitignored at the repo root, so the worktree's per-worktree working tree started from an old `.planning/` snapshot that did not include phase 11. The orchestrator's main-repo working tree had the phase 11 files (`11-01-PLAN.md` ... `11-05-PLAN.md`, `11-CONTEXT.md`, `11-DISCUSSION-LOG.md`, `11-PATTERNS.md`) but they were not propagated to the worktree. **Resolution:** Copied the phase 11 directory from the main repo working tree (`/home/darko/git/rockdarko/telemetron/.planning/phases/11-undeploy-orchestrator-safety-idempotency/`) into the worktree path. This is a pre-execution working-tree shim and does NOT show up in git status (gitignored). No commit; this is environmental setup, not code change. **Future note:** the spawn-time prompt for executors in worktree mode should either (a) carry plan files inline OR (b) explicitly instruct the executor to copy from the main repo's `.planning/` tree before reading. Surfacing for the orchestrator: an alternative shape is to have the orchestrator pre-stage `.planning/phases/<phase>/` into the worktree before spawning. Not a blocker for this plan since the files were trivially copyable.

## Self-Check: PASSED

- **Files exist:**
  - `roles/garage/tasks/purge.yml` — present (`test -f` OK; 125 lines)
  - `roles/grafana/tasks/purge.yml` — present (`test -f` OK; 114 lines)
  - `roles/loki/tasks/purge.yml` — present (`test -f` OK; 114 lines)
- **Commits exist (verified via `git log --oneline`):**
  - `2d6c149` — feat(11-03): add garage purge.yml — two-volume loop + single image (D-152)
  - `9b13a98` — feat(11-03): add grafana purge.yml — single volume + two-image loop
  - `1a5e3bc` — feat(11-03): add loki purge.yml — single volume + two-image loop
- **Syntax-check (ansible-playbook --syntax-check --tags <role>):** PASSED for garage, grafana, loki — all three return `playbook: playbooks/deploy_docker.yml`.
- **Per-file task count = 5:** verified for all three files.
- **Negative greps (sub-tags, ignore_errors, notify, host_dirs, s3-credentials, curl_image-on-garage):** all return 0 across all three files.
- **D-159 WARN format prefixes present** in every file (`WARNING: irreversible -- <role> purge_<action>:`).
- **Loop count = 1** in each file (garage: docker_volume loop; grafana + loki: docker_image loop).
- **`failed_when: false` directive present** on the docker_image task in every file (anchored grep `^  failed_when: false` returns 1 per file).
- **`.results | selectattr('failed', 'defined') | selectattr('failed')` accessor** present in grafana + loki post-skip WARN gate.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 11-04 (orchestrator playbook) can now invoke `include_role: { name: garage, tasks_from: purge }`, `include_role: { name: grafana, tasks_from: purge }`, and `include_role: { name: loki, tasks_from: purge }` in the reverse-order task block. The garage two-volume + grafana/loki two-image loops are encapsulated entirely inside the per-role files — orchestrator does NOT need to know about the loops.
- D-146 garage recovery story is preserved: garage purge.yml only destroys the two named volumes + the primary image. Phase 10's garage uninstall.yml header (which Phase 11 plans do NOT modify) documents the recovery flow; after `telemetron_purge_data=true` removes meta + data, the next deploy regenerates S3 keys AND starts from empty buckets (the "fresh-start" leg of OPS-02 — UAT scenario #5 in Plan 11-05 proves it).
- Shared-curl edge case is contained inside grafana + loki via `failed_when: false`. Plan 11-04 orchestrator's `when:` gate (`telemetron_purge_data | default(false) | bool or telemetron_purge_images | default(false) | bool`) composes cleanly with the per-file belt-and-suspenders gates here.
- No blockers for Plan 11-04 or Plan 11-05 (UAT) — both can proceed once Plans 11-01 + 11-02 (sibling wave-1 plans) and this plan all merge back into main.

---
*Phase: 11-undeploy-orchestrator-safety-idempotency*
*Completed: 2026-05-30*
