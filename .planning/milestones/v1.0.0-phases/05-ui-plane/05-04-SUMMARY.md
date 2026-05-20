---
phase: 5
plan: 4
subsystem: ui-plane
tags: [gap-closure, non-ascii, dashboard-uids, gate-9.5, karma, promlens, grafana]
gap_closure: true

dependency_graph:
  requires: [05-01, 05-02, 05-03]
  provides: [Gate 1 clean for all three UI-plane roles, D-77 panel UIDs hardcoded in three dashboards, Gate 9.5 deploy-time regression guard]
  affects: [roles/karma, roles/promlens, roles/grafana/files/_rewrite_uids.py, roles/grafana/files/dashboards, roles/grafana/tasks/verify.yml]

tech_stack:
  added: []
  patterns: [Gate 9.5 host-side grep assertion pattern for provisioned JSON files]

key_files:
  modified:
    - roles/karma/defaults/main.yml
    - roles/karma/tasks/main.yml
    - roles/karma/tasks/verify.yml
    - roles/karma/templates/karma.yaml.j2
    - roles/promlens/defaults/main.yml
    - roles/promlens/tasks/main.yml
    - roles/promlens/tasks/verify.yml
    - roles/promlens/meta/main.yml
    - roles/grafana/files/_rewrite_uids.py
    - roles/grafana/files/dashboards/otel-collector-self-metrics.json
    - roles/grafana/files/dashboards/mimir-self-metrics.json
    - roles/grafana/files/dashboards/tempo-self-metrics.json
    - roles/grafana/tasks/verify.yml
    - .planning/ROADMAP.md
  created: []

decisions:
  - "[Rule 1 auto-fix] Gate 9.5 exception uses ${ds_prometheus} (lowercase) matching actual host-health.json panel content, not ${DS_PROMETHEUS} (uppercase) as specified in the plan; the plan had a case mismatch vs the actual JSON; fix applied inline without user consultation per Rule 1"

metrics:
  duration: ~12 minutes
  completed: "2026-05-19T15:01:19Z"
  tasks: 4
  files_modified: 14
  commits: 4
---

# Phase 5 Plan 4: Gap Closure (non-ASCII regression + dashboard uid rewrite bug + Gate 9.5) Summary

**One-liner:** Swept 25 U+00A7 section-sign violations from karma+promlens, fixed `_rewrite_uids.py` key-form mismatch resolving 207 broken panel datasource UIDs across three dashboards, and wired Gate 9.5 deploy-time regression guard.

## What Was Built

This gap-closure plan addressed two blockers identified by `/gsd:verify-work 5` after plans 05-01, 05-02, 05-03 shipped:

**Gap 1 — Non-ASCII Gate 1 regression:** 25 occurrences of U+00A7 `§` in 8 non-README files across `roles/karma/` and `roles/promlens/`. The identical fix (`§` -> `sec.`) had been applied to `roles/grafana/` by commit `d520359` but was not carried forward when karma and promlens were authored in plans 05-02 and 05-03. Replayed the UTF-8 byte-sequence sed (`\xc2\xa7` -> `sec.`) across all non-README `.yml`/`.yaml`/`.j2` files in both roles.

**Gap 2 — Dashboard UID rewrite incomplete:** `roles/grafana/files/_rewrite_uids.py` had a key-form mismatch in its `uid_refs` dict. Keys like `"${datasource}"` (curly-brace form) never matched actual Grafana panel JSON uids like `"$datasource"` (no-braces form). Step 1 of `rewrite_template_var()` correctly removed template vars from `.templating.list`; Step 2 (panel uid substitution via `walk()`) silently no-oped. Result: `otel-collector-self-metrics.json` (126 panels), `mimir-self-metrics.json` (7 panels), and `tempo-self-metrics.json` (74 panels) shipped with unresolved `$datasource`/`$ds`/`$logsds` panel refs. Fixed the three buggy keys, added an inline "Key form NOTE" comment documenting the two-form convention, then re-downloaded the three upstream sources and re-ran the script to regenerate all three dashboards with hardcoded `{type, uid: prometheus/loki}` dicts.

**Gate 9.5:** Added a new Step 10 task at the end of `roles/grafana/tasks/verify.yml`. At deploy time on the host, this task greps the provisioned dashboard tree for unresolved `"uid": "$..."` panel refs. The single legitimate exception (`${ds_prometheus}` in host-health.json, retained in `.templating.list` for Grafana runtime resolution) is explicitly allowlisted. The gate fails the play fast if any future dashboard regeneration reintroduces the bug.

## Per-Task Commits

| Task | Name | Commit | Files Modified |
|------|------|--------|----------------|
| 1 | Replay non-ASCII sed across karma + promlens | e97dbbd | 8 files (karma: defaults, tasks/main, tasks/verify, karma.yaml.j2; promlens: defaults, tasks/main, tasks/verify, meta) |
| 2 | Fix _rewrite_uids.py SUBSTITUTIONS key forms | c70a540 | 1 file (roles/grafana/files/_rewrite_uids.py) |
| 3 | Regenerate otel/mimir/tempo self-metrics dashboards | b096916 | 3 files (dashboard JSONs) |
| 4 | Gate 9.5 + ROADMAP update | 3c59b74 | 2 files (roles/grafana/tasks/verify.yml, .planning/ROADMAP.md) |

## Exact Counts

- `RESEARCH §` lines removed: 25 (across 8 non-README files in karma + promlens)
- `RESEARCH sec.` lines added: 25 (replacements are 1:1)
- Panel datasource uid refs resolved: 126 (otel-collector) + 7 (mimir) + 74 (tempo: 73 `$ds` + 1 `$logsds`) = **207 panels**
- Dashboard JSONs unchanged (regression guard): 2 (host-health.json, loki-self-metrics.json)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Gate 9.5 exception string uses actual case from host-health.json**

- **Found during:** Task 4 implementation
- **Issue:** The plan specified `${DS_PROMETHEUS}` as the exception to allowlist in Gate 9.5, but `host-health.json` actually contains `${ds_prometheus}` (all lowercase). Confirmed by reading the file: `python3 -c "import json; d=json.load(open('roles/grafana/files/dashboards/host-health.json')); ..."` shows all panel datasource uids are `${ds_prometheus}`, not `${DS_PROMETHEUS}`. The plan had a case mismatch against the actual JSON content.
- **Fix:** Used `${ds_prometheus}` (lowercase) in the Gate 9.5 `grep -vF` exception and in the task comment. The SUBSTITUTIONS dict in the script still correctly has `"${DS_PROMETHEUS}"` as the uid_refs key for the host-health entry (that key correctly does NOT match any panel uid in the JSON, leaving those panels to be resolved by Grafana at runtime via the retained `ds_prometheus` template var).
- **Files modified:** `roles/grafana/tasks/verify.yml` (Gate 9.5 exception string)
- **Commit:** 3c59b74

## Known Stubs

None. All three previously-broken dashboards now have hardcoded `{type, uid}` datasource dicts. Gate 9.5 would catch any new stubs at deploy time.

## Live-Host UAT (Post-Plan, leviathan)

Not yet run (gap-closure plans land static artifacts; UAT follows on the next playbook run):
- All 7 dashboards expected to open without "Template variable datasource does not exist" errors
- Gate 9.5 step expected to show `gate_9_5_ok` in the play recap
- Second back-to-back run expected to report `changed=0` (Gate 4 idempotency)
- `/gsd:verify-work 5` re-run expected to flip both gaps from `failed` to `verified` (score: 10/12 -> 12/12)

## Plan Handoff

No follow-up required. Phase 5 closes cleanly after 05-04. Phase 6 (orchestration + docs + smoke test) is the next milestone. The three previously-broken dashboards now satisfy D-77, and Gate 9.5 prevents regression at every future `--tags grafana` deploy.

## Self-Check: PASSED

- All 14 modified files exist on disk (confirmed by git diff counts in task verification)
- All 4 commits exist: e97dbbd, c70a540, b096916, 3c59b74 (git log --oneline -6 confirmed)
- Gate 1 non-ASCII scan: 0 matches (confirmed by grep returning empty)
- Panel walker: OK for all three regenerated dashboards (confirmed by python3 walker)
- Regression guard: host-health.json and loki-self-metrics.json unchanged (git diff --quiet exit 0)
- Gate 9.5 YAML valid (python3 -c 'import yaml; yaml.safe_load(...)' exit 0)
- ROADMAP.md: 05-04-PLAN.md entry present, 3/3 Complete unchanged
