---
phase: 01-foundation-storage
plan: 01
subsystem: infra
tags: [ansible, documentation, planning, scope-corrections]

# Dependency graph
requires: []
provides:
  - "PROJECT.md Out of Scope updated: application_web_docker, postgres, reverse-proxy dropped with rationale"
  - "REQUIREMENTS.md: FOUND-03 removed, FOUND-01 rewritten to new network model, preamble updated to 14 roles"
  - "ROADMAP.md: Phase 1 goal/criteria/requirements corrected; Phase 6 role count corrected; all 16-role phrasings purged"
  - "roles/README.md: 14-role table (dropped 5, added node_exporter); port-acceptance gates section added"
affects:
  - "02-foundation-storage"
  - "03-foundation-storage"
  - "All Phase 2-6 plans that read roles/README.md port-process gates"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-role port-acceptance gates: grep (INSPQ + non-ASCII), image-pin, vault-discipline, idempotency, healthcheck+restart, README schema"
    - "telemetron Docker bridge network created in playbook pre_tasks, not a shared base role"
    - "vault_<role>_<purpose> naming convention established"

key-files:
  created: []
  modified:
    - ".planning/REQUIREMENTS.md"
    - ".planning/PROJECT.md"
    - ".planning/ROADMAP.md"
    - "roles/README.md"

key-decisions:
  - "Drop application_web_docker from M1: reverse-proxy-agnostic design; network plumbing moves to playbook pre_tasks (D-01, D-04)"
  - "Drop postgres from M1: Grafana uses embedded SQLite; FOUND-03 removed from REQUIREMENTS.md (D-02)"
  - "M1 role count is 14, not 16: alertmanager, fluentbit, grafana, hook_router, karma, loki, mimir, minio, nfsd, node_exporter, opentelemetry, prometheus, promlens, tempo (D-03)"
  - "Per-role port-acceptance gates established in Phase 1 (D-21): grep, image-pin, vault, idempotency, healthcheck+restart, README schema"

patterns-established:
  - "Port-acceptance gate: grep -riE 'inspq|qc.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/<name>/ returns 0"
  - "Port-acceptance gate: grep -rPn '[^\\x00-\\x7F]' roles/<name>/ returns 0"
  - "Port-acceptance gate: changed=0 on second playbook run"
  - "Port-acceptance gate: docker inspect shows healthy + unless-stopped"

requirements-completed: [OPS-03, OPS-04, OPS-05]

# Metrics
duration: 7min
completed: 2026-05-17
---

# Phase 1 Plan 01: Scope corrections and doc updates

**Planning doc baseline aligned to 14-role M1 scope: FOUND-03 removed, FOUND-01 rewritten to playbook-pre_task network model, all 16-role phrasings purged, port-acceptance gates canonicalized in roles/README.md**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-17T14:02:33Z
- **Completed:** 2026-05-17T14:09:53Z
- **Tasks:** 3 of 3
- **Files modified:** 4

## Accomplishments

- Removed FOUND-03 (Postgres) from REQUIREMENTS.md (both Foundation section and traceability table), rewritten FOUND-01 to reflect playbook pre_task network-creation model, updated preamble to "14 Ansible roles"
- Updated PROJECT.md with three Out of Scope entries (application_web_docker, postgres, reverse-proxy/external URL), two Key Decisions rows, corrected role count and role list to 14 total
- Updated ROADMAP.md: purged all "16 role/Ansible" phrasings across Phase 1, Phase 6, and overview; rewrote Phase 1 goal and success criteria to drop postgres/application_web_docker; FOUND-03 removed from Requirements line
- Updated roles/README.md: 14-row role table (removed 5 rows, added node_exporter), expanded Dropped/Added paragraphs, added Per-role port-acceptance gates section with 6 concrete gate commands

## Task Commits

1. **Task 1: Update REQUIREMENTS.md** — planning file (gitignored, local only)
2. **Task 2: Update PROJECT.md** — planning file (gitignored, local only)
3. **Task 3: Update ROADMAP.md + roles/README.md** — `8aab3e5` (chore)

Note: `.planning/` is in `.gitignore` per project config (`commit_docs: false`). Only `roles/README.md` is tracked in git.

## Files Created/Modified

- `.planning/REQUIREMENTS.md` — preamble "14 Ansible roles"; FOUND-01 rewritten (playbook pre_task network model, no application_web_docker); FOUND-03 removed from Foundation section and traceability table; UI-01 updated (SQLite not Postgres); INV-03 updated (14-role chain, drop application_web_docker/postgres); OPS-02 updated (no Postgres password)
- `.planning/PROJECT.md` — role count 16→14 in Active section; three Out of Scope entries added; two Key Decisions rows added; existing Key Decisions row updated (16→14 count)
- `.planning/ROADMAP.md` — Overview: "ports 14 Ansible roles"; Phase 1 goal rewritten; Phase 1 Requirements line drops FOUND-03; Phase 1 Success Criteria rewritten (MinIO-only foundation); Phase 6 goal and SC#1: "14-role stack" not "16-role"; Phase overview summary line updated; catch-all `16[- ]?(role|Ansible)` returns 0
- `roles/README.md` — 14-row role table; Dropped from upstream paragraph expanded (6 dropped roles with rationale); Added vs upstream paragraph; Per-role port-acceptance gates section (6 gates)

## Decisions Made

- FOUND-03 removal documented in PROJECT.md Key Decisions and Out of Scope rather than in REQUIREMENTS.md body — REQUIREMENTS.md is for active requirements only; rationale lives in PROJECT.md and CONTEXT.md (D-02)
- INV-03 in REQUIREMENTS.md updated alongside the FOUND changes (not just FOUND section) — the acceptance criterion required 0 `application_web_docker` references which INV-03 previously contained
- UI-01 in REQUIREMENTS.md updated to reference SQLite not Postgres — FOUND-03 removal makes the Postgres backing store reference stale/broken

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated INV-03, UI-01, and OPS-02 in REQUIREMENTS.md**
- **Found during:** Task 1 verification
- **Issue:** Acceptance criterion required `grep -c 'application_web_docker' .planning/REQUIREMENTS.md` = 0, but INV-03 referenced `application_web_docker` in the dependency chain. UI-01 still referenced "Postgres database from FOUND-03". OPS-02 still listed "Postgres password".
- **Fix:** Rewrote INV-03 dependency chain to 14-role model (D-05), rewrote UI-01 backing store from Postgres to SQLite, removed "Postgres password" from OPS-02 secrets list
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Verification:** All acceptance criteria grep counts pass

**2. [Rule 1 - Bug] Updated Key Decisions row in PROJECT.md**
- **Found during:** Task 2 verification
- **Issue:** Acceptance criterion `grep -cE '16[- ]?(role|Ansible)' .planning/PROJECT.md` = 0 failed because the existing Key Decisions row said "M1 ports 16 roles"
- **Fix:** Updated Key Decisions row to "M1 ports 14 roles" with updated dropped role list
- **Files modified:** `.planning/PROJECT.md`
- **Verification:** grep count = 0

**3. [Rule 1 - Bug] Removed FOUND-03 reference from PROJECT.md Key Decisions**
- **Found during:** Cross-file verification
- **Issue:** Cross-file acceptance criterion `grep -c 'FOUND-03' .planning/PROJECT.md` = 0 failed because the newly added "Drop postgres role from M1" Key Decision row said "Removes FOUND-03 from REQUIREMENTS.md"
- **Fix:** Rephrased to "Postgres requirement removed from REQUIREMENTS.md"
- **Files modified:** `.planning/PROJECT.md`
- **Verification:** grep count = 0

**4. [Rule 1 - Bug] Fixed Phase 1 summary line in ROADMAP.md Phases overview**
- **Found during:** Task 3 execution
- **Issue:** The Phase 1 summary line in the `## Phases` overview section still mentioned `application_web_docker` and Postgres
- **Fix:** Rewrote Phase 1 summary line to reflect the corrected MinIO-only foundation scope
- **Files modified:** `.planning/ROADMAP.md`
- **Verification:** No application_web_docker/Postgres references remain in non-"Dropped"/"Out of Scope" contexts

---

**Total deviations:** 4 auto-fixed (all Rule 1 — bugs found during verification; acceptance criteria drove fixes)
**Impact on plan:** All auto-fixes necessary for acceptance criteria compliance. No scope creep.

## Issues Encountered

The `.planning/` directory is gitignored (per `.gitignore` and `commit_docs: false` in config.json), so REQUIREMENTS.md, PROJECT.md, and ROADMAP.md changes are local-only planning artifacts. Only `roles/README.md` is tracked in git. This is expected per project design and does not affect plan completion.

## Known Stubs

None — this is a documentation-only plan. No code stubs.

## Next Phase Readiness

- Plan 01-02 can proceed: planning docs are now internally consistent with D-01..D-05, D-21
- Plan 01-02 will create `inventory/example-homelab/` skeleton and `playbooks/deploy_docker.yml` with the `telemetron` network pre_task — per the updated ROADMAP.md and REQUIREMENTS.md it now reads
- Plan 01-03 can reference `roles/README.md` port-acceptance gates section as the single canonical place for gate documentation

---
*Phase: 01-foundation-storage*
*Completed: 2026-05-17*
