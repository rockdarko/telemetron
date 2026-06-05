---
phase: 13-per-role-backup-restore-tasks
plan: 01
subsystem: backup-foundation
tags: [phase-13, backup, defaults, group_vars]
dependency_graph:
  requires:
    - inventory/example-homelab/group_vars/all/network.yml (analog)
    - inventory/example-homelab/group_vars/all/storage.yml (analog)
    - roles/garage/defaults/main.yml (existing health-poll block)
    - roles/prometheus/defaults/main.yml (existing health-poll block)
    - roles/grafana/defaults/main.yml (existing health-poll block)
    - roles/alertmanager/defaults/main.yml (existing health-poll block)
  provides:
    - backup_dest_root (operator-tunable root for all backup tarballs)
    - backup_stop_timeout (cold-quiesce SIGTERM->SIGKILL budget)
    - backup_continue_on_failure (bail-out vs continue gate)
    - backup_restore_confirm (destructive-restore confirmation gate)
    - backup_restore_from (explicit-timestamp vs latest-discovery selector)
    - garage_backup_stop_timeout (per-role override defaulting from shared knob)
    - prometheus_backup_stop_timeout (same)
    - grafana_backup_stop_timeout (same)
    - alertmanager_backup_stop_timeout (same)
  affects:
    - Plans 13-02..13-05 (per-role tasks/backup.yml + tasks/restore.yml will consume these vars)
    - Phase 14 orchestrators (playbooks/backup_docker.yml + playbooks/restore_docker.yml)
tech_stack:
  added: []
  patterns:
    - Shared `group_vars/all/<topic>.yml` file with top-of-file decision-ID-citing comment block + flat key:value lines (verbatim Pattern A from 13-PATTERNS.md lines 619-686)
    - Per-role `<role>_*_timeout` override pattern defaulting from a shared inventory-level knob via `{{ shared_var | default(N) }}` Jinja chain
key_files:
  created:
    - inventory/example-homelab/group_vars/all/backup.yml
  modified:
    - roles/garage/defaults/main.yml
    - roles/prometheus/defaults/main.yml
    - roles/grafana/defaults/main.yml
    - roles/alertmanager/defaults/main.yml
decisions:
  - D-176: backup_dest_root single root path; per-role subdirs lazy-created at mode 0700; tarballs mode 0600
  - D-177: shared backup_stop_timeout=60 default in group_vars/all/backup.yml with per-role <role>_backup_stop_timeout override defaulting from the shared knob
  - D-178: backup_continue_on_failure=false (bail-out default; v1.2.0 fail-fast carry-forward)
  - D-179: backup_restore_confirm=false hard-gate (destructive-restore confirmation); backup_restore_from="" empty default for latest-discovery via find|sort -r|head -1
metrics:
  duration: 2min
  completed_date: 2026-06-03
---

# Phase 13 Plan 01: Shared backup-vars foundation Summary

Ships the operator-tunable backup-knob foundation (5 shared vars in `inventory/example-homelab/group_vars/all/backup.yml` + 4 per-role `<role>_backup_stop_timeout` overrides) consumed by all 8 Phase 13 per-role backup/restore task files in plans 13-02..13-05.

## What Was Built

### 1. Shared backup vars file (Task 1)

Created `inventory/example-homelab/group_vars/all/backup.yml` (41 lines). Five flat scalars consumed by every per-role `tasks/backup.yml` + `tasks/restore.yml` (plans 13-02..13-05) and by the Phase 14 orchestrators:

| Key | Default | Source decision |
|-----|---------|-----------------|
| `backup_dest_root` | `/opt/telemetron/backups` | D-176 single-root destination |
| `backup_stop_timeout` | `60` | D-177 SIGTERM->SIGKILL budget (6x Docker default) |
| `backup_continue_on_failure` | `false` | D-178 bail-out-on-first-failure (v1.2.0 carry-forward) |
| `backup_restore_confirm` | `false` | D-179 destructive-restore confirmation gate (mirrors v1.2.0 D-159 telemetron_purge_data) |
| `backup_restore_from` | `""` | D-179 empty -> latest-discovery via find\|sort -r\|head -1 |

File header comment block cites Phase 13 + D-176..D-179. Per-knob inline comments cite the locked decision IDs plus the PITFALLS.md anchors (GP-1 LMDB clean-close, PP-1 Prometheus lock-file, XP-4 perms 0600/0700) that drove the defaults.

### 2. Per-role `<role>_backup_stop_timeout` overrides (Task 2)

Added one line per role to the 4 stateful role defaults files, placed adjacent to each role's existing `<role>_health_retries` / `<role>_health_delay` block so timing knobs stay cohesive in operator scanning:

- `roles/garage/defaults/main.yml`: `garage_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"` (6-line header citing GP-1 LMDB clean-close)
- `roles/prometheus/defaults/main.yml`: `prometheus_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"` (3-line header citing PP-1 SIGKILL-mid-checkpoint regression)
- `roles/grafana/defaults/main.yml`: `grafana_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"` (2-line header noting SQLite shutdown is fast)
- `roles/alertmanager/defaults/main.yml`: `alertmanager_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"` (2-line header noting SIGTERM final-flush is sub-second)

Every block opens with `# --- Backup stop-timeout (D-177; Phase 13) ---`. Verbatim copies of the PATTERNS.md lines 696-731 snippets.

## Verification Results

```
Foundation file:
  inventory/example-homelab/group_vars/all/backup.yml exists, YAML parses, all 5 expected keys present with locked defaults

Per-role chains:
  4/4 role defaults files contain `backup_stop_timeout | default(60)` Jinja chain
  4/4 files yaml.safe_load cleanly
  4/4 var lines match the exact pattern `^<role>_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"$`
  4/4 header comments matching `# --- Backup stop-timeout` present preceding the var

Playbook syntax:
  ansible-playbook playbooks/deploy_docker.yml --syntax-check exits 0
  (verified per Rock's memory note that --syntax-check skips role internals; supplemented with python3 yaml.safe_load per-file)

No decorative prefix:
  Zero occurrences of vault_(garage|prometheus|grafana|alertmanager)_backup* across roles/*/defaults/main.yml
```

## Deviations from Plan

None — plan executed exactly as written. The PATTERNS.md verbatim snippets for the per-role additions specify a 6-line comment block for Garage (vs. the action text's "4-line comment" estimate); I honored the PATTERNS.md verbatim content per the action instruction "copy each role's snippet exactly". The 7-line preceding-window check confirms every role's header comment is within reasonable proximity of its var line and the structural intent (header comment block precedes the var line) is met for all 4 roles.

## Authentication Gates

None encountered.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | feat(13-01): add shared backup vars file (D-176..D-179) | `1bce82f` |
| 2 | feat(13-01): add <role>_backup_stop_timeout to 4 stateful role defaults | `7c13b89` |

## Known Stubs

None. All vars resolve to concrete defaults; no placeholder values that block downstream plans.

## Threat Flags

None. The threat register in the plan's `<threat_model>` correctly classified every threat for this plan (T-13-01-01 through T-13-01-SC); no new threat surface introduced beyond the variables/files declared in scope.

## Downstream Consumers

Wave 2 plans (13-02..13-05) can now reference:

```jinja
{{ backup_dest_root }}                      # /opt/telemetron/backups
{{ backup_stop_timeout }}                   # 60
{{ backup_continue_on_failure }}            # false (orchestrator gate, Phase 14)
{{ backup_restore_confirm }}                # false (per-role + orchestrator gate)
{{ backup_restore_from }}                   # "" (empty -> latest-discovery)
{{ garage_backup_stop_timeout }}            # per-role override -> docker stop -t
{{ prometheus_backup_stop_timeout }}        # same
{{ grafana_backup_stop_timeout }}           # same
{{ alertmanager_backup_stop_timeout }}      # same
```

No additional plumbing is needed before plans 13-02..13-05 land their `tasks/backup.yml` + `tasks/restore.yml` files. Phase 14 orchestrators will additionally consume `backup_dest_root` (for latest-discovery globs) and `backup_continue_on_failure` (for ignore_errors orchestration).

## Self-Check: PASSED

- inventory/example-homelab/group_vars/all/backup.yml — FOUND
- roles/garage/defaults/main.yml — modified, contains `garage_backup_stop_timeout`
- roles/prometheus/defaults/main.yml — modified, contains `prometheus_backup_stop_timeout`
- roles/grafana/defaults/main.yml — modified, contains `grafana_backup_stop_timeout`
- roles/alertmanager/defaults/main.yml — modified, contains `alertmanager_backup_stop_timeout`
- Commit 1bce82f — FOUND in git log
- Commit 7c13b89 — FOUND in git log
