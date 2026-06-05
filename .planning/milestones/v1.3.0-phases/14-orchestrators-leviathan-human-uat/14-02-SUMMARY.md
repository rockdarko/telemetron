---
phase: 14-orchestrators-leviathan-human-uat
plan: 02
subsystem: backup-orchestrator
tags: [backup, orchestrator, ansible, m1, v1.3.0]
requires:
  - 14-01 (per-role tasks/backup.yml accept backup_timestamp_override via set_fact -> backup_timestamp_effective)
  - inventory/example-homelab/group_vars/all/backup.yml (3 knobs: backup_dest_root, backup_stop_timeout, backup_continue_on_failure)
  - roles/garage/tasks/backup.yml, roles/prometheus/tasks/backup.yml, roles/grafana/tasks/backup.yml, roles/alertmanager/tasks/backup.yml (Phase 13)
provides:
  - playbooks/backup_docker.yml (single user-facing entry point for backups)
  - SC4 cross-cutting `--tags backup` selector (all 4 stateful role includes)
  - Per-role `--tags <role>` selector with always-tagged shared timestamp + banner pre_tasks
  - D-184 any_errors_fatal flip via backup_continue_on_failure knob
affects:
  - downstream Plan 14-03 (restore_docker.yml -- mirrors banner + include_role shape)
  - downstream Plan 14-04 (HUMAN-UAT scenarios 4a + 4d exercise the per-role and cross-cutting tag UX)
  - downstream Phase 15 (doc cascade: docs/quickstart.md ## Backup and restore section references this orchestrator)
tech-stack:
  added: []
  patterns:
    - Pattern A (Play scaffold) -- adapted from playbooks/undeploy_docker.yml
    - Pattern B (PLAY-start banner; tags: always) -- adapted from undeploy_docker.yml WARN banner shape
    - Pattern C (D-191 shared-timestamp set_fact in pre_tasks) -- hoisted from per-role tasks/backup.yml
    - Pattern D (Per-role include_role with `tags: [<role>, backup]`) -- D-149 + SC4 extension
    - Shared Pattern 1 (community.docker collection at play level)
    - Shared Pattern 4 (tags: always on banner + timestamp pre_tasks)
key-files:
  created:
    - playbooks/backup_docker.yml
  modified: []
decisions:
  - "Two-element tag list `[<role>, backup]` on each include_role: dynamic include_role resolves tags at include-task level BEFORE descending into the role body, so the include-task tag list is the ONLY mechanism that makes --tags backup cross-cutting work for dynamic includes; the per-role block-level tags inside each tasks/backup.yml are not visible at play-level tag-selection time."
  - "Banner uses literal `<role>/` token (not Jinja2 substitution) to enumerate the destination root shape (D-186 stability lock; banner is stable across future role additions)."
  - "FORWARD-deploy order (garage -> prometheus -> grafana -> alertmanager) NOT reverse-of-deploy: backup is content-dependency-ordered with Garage first (the only shared writer; Loki/Tempo/Mimir data lives in Garage)."
  - "any_errors_fatal Jinja2 inverts the knob (knob false -> any_errors_fatal true -> bail). default behaviour is fail-fast; --extra-vars backup_continue_on_failure=true opts into all-4-roles-attempt."
  - "Skipped post_tasks success summary (per CONTEXT.md Claude's Discretion): the per-role `state` task in each tasks/backup.yml already logs the tarball path; an orchestrator summary adds noise without value (mirrors undeploy_docker.yml convention)."
  - "Skipped any orchestrator-level block:/rescue:/always: -- per Phase 13 contract each per-role tasks/backup.yml owns its own restart guarantee inside its own block/always; orchestrator-level bail-out fires AFTER the failing role's always: ran (T-14-06 mitigation)."
metrics:
  duration: 8min
  completed: 2026-06-04T12:33:00Z
  tasks: 1
  files: 1
---

# Phase 14 Plan 02: M1 Backup Orchestrator (`playbooks/backup_docker.yml`) Summary

Shipped `playbooks/backup_docker.yml` -- the thin orchestrator that wires the 4 per-role `tasks/backup.yml` files (garage -> prometheus -> grafana -> alertmanager) under one shared ISO 8601 basic UTC timestamp, with D-186 PLAY-start banner, D-184 bail-out-vs-continue-on-failure semantics via `any_errors_fatal`, and full per-role + SC4 cross-cutting `--tags backup` UX.

## What Was Built

`playbooks/backup_docker.yml` (174 lines) — single user-facing entry point for backups (BACKUP-V13-05). Concentrates multi-role coordination (shared timestamp + bail-out policy + banner) and delegates everything else to the per-role tasks Phase 13 shipped. No other files changed.

### Structural anatomy (top to bottom)

1. **File header docstring (lines 1-67)** — describes orchestration model, ordering rationale (forward-deploy NOT reverse), shared-timestamp + override propagation, bail-out vs continue-on-failure knob, per-role + cross-cutting tag UX, and 4 explicit Usage block invocations: default full-run, `--tags <role>`, `--tags backup` cross-cutting, `--extra-vars backup_continue_on_failure=true`.

2. **Play header (lines 69-79)** — `hosts: telemetron`, `gather_facts: true`, `become: false`, `collections: [community.docker]`, plus the D-184 `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` Jinja2 inversion.

3. **`vars:` block (lines 81-84)** — `backup_continue_on_failure: false` default.

4. **`pre_tasks:` (lines 86-118; 3 tasks, all `tags: [always]`)**:
    - Banner (D-186): 4-line `msg: |` literal showing destination root + `<role>/` token, knob status + category description, and `backup_stop_timeout`.
    - `command: date -u +%Y%m%dT%H%M%SZ` registered as `backup_ts` (D-191).
    - `set_fact: backup_timestamp_shared: "{{ backup_ts.stdout }}"` (D-191).

5. **`tasks:` (lines 132-171; 4 include_role calls in forward-deploy order)** — each carries `tasks_from: backup`, `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }`, and `tags: [<role>, backup]` two-element list.

6. **No `post_tasks:`** (D-193 lock).

## How It Behaves

- **Default run** (no `--tags`): runs banner + timestamp pre_tasks, then all 4 role include_role calls in forward-deploy order; one shared filename suffix across all 4 tarballs; bails on first role's first task failure.
- **`--tags <role>`** (e.g. `--tags garage`): runs banner + timestamp pre_tasks (always-tagged) plus only that role's include_role; per-role timestamp suffix uses the orchestrator's shared timestamp.
- **`--tags backup`** (SC4 cross-cutting): selects all 4 role include_role calls plus the always-tagged pre_tasks; equivalent to default run.
- **`--tags <stateless-role>`** (loki/tempo/mimir/karma/fluentbit/opentelemetry/node_exporter/nfsd): matches no tasks; play exits 0 with empty plan (SC1).
- **`--extra-vars backup_continue_on_failure=true`**: flips `any_errors_fatal` to false; all 4 roles attempt their backup; failures aggregate in PLAY RECAP.

## Verification

All 21 verify-script checks PASS (see Task 1's `<verify>` block in 14-02-PLAN.md). Notable confirmations:

- `python3 -c "import yaml; yaml.safe_load(...)"` parses cleanly.
- `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0.
- `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` enumerates exactly 4 lines matching `Invoke (garage|prometheus|grafana|alertmanager) backup` (B-1 SC4 cross-cutting gate).
- Comment-stripped `^\s+-\s+always$` count = 3 (banner + 2 timestamp pre_tasks).
- Comment-stripped `^\s+-\s+backup\s*$` count = 4 (one per include_role).
- No `WARNING: irreversible` literal anywhere (backup is non-destructive; the locked D-187 destructive-action prefix is restore-only).
- Order: garage line (134) < prometheus (144) < grafana (154) < alertmanager (164).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Reworded the destructive-prefix anti-explanation comment to remove the literal `WARNING: irreversible --` substring**
- **Found during:** Task 1 verify-script run.
- **Issue:** The plan's header-comment block included the literal advisory "NO `WARNING: irreversible --` prefix -- backup is not destructive". The acceptance criterion enforces `if grep -q "WARNING: irreversible" playbooks/backup_docker.yml; then exit 1`, which fires even when the literal appears inside a YAML comment line.
- **Fix:** Reworded the comment from "NO `WARNING: irreversible --` prefix" to "NO destructive-action prefix" while preserving the D-187 reference. The semantic intent is identical; only the substring-matched literal is removed so the verify gate can distinguish "the banner does not say it" from "the file does not contain that substring anywhere".
- **Files modified:** `playbooks/backup_docker.yml` (one comment line in the banner-task block).
- **Commit:** Folded into the single-task commit `00a1eb7` (the plan ships one file in one task; the rewording happened pre-commit during the verify iteration).

No other deviations. Plan executed exactly as written.

## Threat Surface Scan

No new threats beyond the plan's 4-entry `<threat_model>`. The orchestrator:
- accepts ONE `--extra-vars` knob (`backup_continue_on_failure`) at a documented trust boundary -- T-14-04, T-14-05 dispositions remain `mitigate` via Plan 14-01's `default(backup_timestamp.stdout)` fallback (standalone callers do not need the override) and via the banner restating the knob status at play start.
- introduces no new network endpoints, no new auth paths, no file access patterns outside the per-role tasks (orchestrator is pure include + set_fact + debug).
- introduces no schema changes at trust boundaries.

## Known Stubs

None.

## Sub-Repo Routing

Single-repo project. Standard commit.

## Self-Check: PASSED

```
playbooks/backup_docker.yml -- FOUND (174 lines)
.planning/phases/14-orchestrators-leviathan-human-uat/14-02-SUMMARY.md -- FOUND
commit 00a1eb7 -- FOUND (git log -1)
```

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1    | Create playbooks/backup_docker.yml with vars + pre_tasks + 4 include_role calls | 00a1eb7 | playbooks/backup_docker.yml |
