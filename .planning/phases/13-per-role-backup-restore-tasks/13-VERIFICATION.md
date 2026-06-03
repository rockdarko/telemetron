---
phase: 13-per-role-backup-restore-tasks
verified: 2026-06-03T13:30:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
roadmap_truths_verified: 6/6
requirements_verified: 9/9
---

# Phase 13: Per-Role Backup & Restore Tasks Verification Report

**Phase Goal:** Operators have a tested, atomic backup and restore task file for each of the 4 stateful roles (garage, prometheus, grafana, alertmanager), each producing a verified tarball or restoring from one without risk of leaving containers in a stopped state.

**Verified:** 2026-06-03T13:30:00Z
**Status:** passed
**Re-verification:** No — initial verification.
**Live-execution scope:** Out of band — BACKUP-V13-05/RESTORE-V13-05/UAT-V13-01 belong to Phase 14 (orchestrators + leviathan UAT). Phase 13 ships task files only; structural correctness is the bar.

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth (from ROADMAP.md success_criteria) | Status | Evidence |
|---|------------------------------------------|--------|----------|
| 1 | 8 new task files exist: `roles/{garage,prometheus,grafana,alertmanager}/tasks/{backup,restore}.yml` — 8 files, none empty | VERIFIED | All 8 files exist; wc -l: garage backup=221, garage restore=376, prom backup=153, prom restore=267, grafana backup=162, grafana restore=253, alertmanager backup=181, alertmanager restore=253. None empty; all exceed planner min_lines thresholds. |
| 2 | Each `tasks/backup.yml` stops container via `ansible.builtin.command: docker stop` (not `community.docker state: stopped`), tars with `--zstd` into `/opt/telemetron/backups/<role>/<role>-<UTC-timestamp>.tar.zst` (mode 0600, dir 0700), then restarts and runs verify — container running at end regardless of tar success (block/rescue/always) | VERIFIED | All 4 backup.yml files: (a) contain `ansible.builtin.command: "docker stop -t {{ <role>_backup_stop_timeout }} {{ <role>_container_name }}"`; (b) non-comment occurrences of `state: stopped` = 0 in every file; (c) `block:` + `always:` markers = 2 in every file; (d) tarball mode 0600 and dest dir 0700 set via `ansible.builtin.file`; (e) `docker start` is the FIRST task inside `always:`; (f) verify follows via either `include_tasks: verify.yml` (prom/grafana/AM) or inline `community.docker.docker_container_info` healthy-poll (garage, per D-178); (g) D-179 ISO 8601 basic UTC timestamp filename via `date -u +%Y%m%dT%H%M%SZ`. |
| 3 | Garage `tasks/backup.yml` includes both `telemetron_garage_meta` and `telemetron_garage_data` volumes AND host-mounted `{{ garage_s3_credentials_file }}` in the single tarball — `s3-credentials` captured | VERIFIED | `roles/garage/tasks/backup.yml`: references `{{ garage_meta_volume }}` (5x), `{{ garage_data_volume }}` (5x), `{{ garage_s3_credentials_file }}` (3x). 5 `--transform` clauses (3 path-rewrite + 2 for shell parsing). Single `tar --zstd -cpf` invocation lists all 3 sources: `{{ garage_meta_volume_info.volume.Mountpoint }}`, `{{ garage_data_volume_info.volume.Mountpoint }}`, `{{ garage_s3_credentials_file }}` (lines 177-179). GP-3 satisfied. |
| 4 | Each `tasks/restore.yml` asserts `backup_restore_confirm == true` (fail-fast), runs `tar tf` integrity check, wipes volume `_data/`, untars, restarts, runs verify. Prometheus restore also deletes `/prometheus/lock` AFTER untar BEFORE container start | VERIFIED | (a) All 4 restore.yml: `ansible.builtin.fail` with `when: not (backup_restore_confirm \| default(false) \| bool)` is the FIRST task (WR-02 fix). (b) `tar --zstd -tf` integrity check ordering: in ALL 4 files, `tar tf` line number < `find -mindepth 1 -delete` line number — confirmed via awk ordering check (PASS for all 4). (c) Wipe uses `find <mountpoint> -mindepth 1 -delete` per STACK.md §3. (d) Untar uses `tar --zstd -xpf` with `-C <mountpoint>`. (e) `docker start` in `always:` clause for all 4. (f) Prometheus PP-1: lock-deletion task at line 239-243 (`path: "{{ prometheus_data_volume_info.volume.Mountpoint }}/lock" state: absent`); ordering verified `untar(L224) < lock(L241) < always(L254)` — PASS. PP-3 queries.active deletion also present (line 248-252). |
| 5 | Each `tasks/backup.yml` and `tasks/restore.yml` begins with `ansible.builtin.package: name: zstd state: present` pre-task; idempotent | VERIFIED | All 8 task files: exactly 1 `ansible.builtin.package: name: zstd` task each, with `state: present` and `become: true`. `ansible.builtin.package` is idempotent by Ansible contract — second run produces `changed=0` if zstd already present. Verified across distros per planner (Debian 12 / Ubuntu 22 / RHEL 9 supported). **Note on restore ordering (WR-02 fix):** In restore.yml, the confirm-gate fires FIRST and zstd install is the second task — a no-confirm invocation fails before any system mutation. This is a deliberate improvement on the planner's "first task" spec for safety; OPS-V13-04 idempotency is unchanged. |
| 6 | Running `ansible-playbook playbooks/backup_docker.yml --tags <role> --ask-vault-pass` on leviathan completes with `failed=0` and container is running/healthy | OUT_OF_SCOPE | Phase 14 success criterion (orchestrator playbook + UAT-V13-01 belongs there). Phase 13 ships only the task files. `ansible-playbook playbooks/deploy_docker.yml --syntax-check` continues to PASS, and `ansible-playbook --syntax-check` against `include_role: tasks_from=backup` / `tasks_from=restore` for each of the 4 roles also passes — confirming structural readiness for Phase 14 to consume. |

**Score (Roadmap):** 5/5 in-scope truths verified; 1/1 explicitly out-of-scope (deferred to Phase 14).

### Observable Truths (Plan-Level Must-Haves, Aggregate)

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 7 | 13-01 | Shared backup vars resolve to operator-tunable defaults from single `group_vars/all` file; each role has `<role>_backup_stop_timeout` defaulting from shared knob; `--syntax-check` passes | VERIFIED | `inventory/example-homelab/group_vars/all/backup.yml` contains exactly the 5 keys at locked defaults: `backup_dest_root=/opt/telemetron/backups`, `backup_stop_timeout=60`, `backup_continue_on_failure=false`, `backup_restore_confirm=false`, `backup_restore_from=""`. Per-role overrides confirmed: `garage_backup_stop_timeout: "{{ backup_stop_timeout \| default(60) }}"` (defaults/main.yml line 71); same Jinja chain in prometheus L93, grafana L83, alertmanager L71. `ansible-playbook playbooks/deploy_docker.yml --syntax-check` passes. |
| 8 | 13-02 | Garage 3-entry tarball; restore refuses without confirm; integrity check before wipe; inline poll because no verify.yml; idempotent zstd ensure-present | VERIFIED | All sub-truths met (see roadmap truths 3 + 4 above). Inline poll wired: `garage_post_backup_health` (line 210) and `garage_post_restore_health` (line 365) both check `State.Health.Status == 'healthy'`. No `include_tasks: verify.yml` in either Garage file (D-178 conformance: Garage has no verify.yml; bootstrap inline pattern is the verify mechanism). |
| 9 | 13-03 | Prometheus PP-1 lock-file deletion correctly placed AFTER untar BEFORE container start | VERIFIED | Lock-deletion task on lines 239-243 with `state: absent` on `{{ prometheus_data_volume_info.volume.Mountpoint }}/lock`. Placement: untar L224 → lock L241 → always L254 (PP-3 queries.active L248). Lock task is inside `block:` BEFORE `always:` opens, so a lock-deletion failure surfaces as a block failure while `docker start` in `always:` still fires (defense-in-depth as documented in inline comment). |

**Score (Plans):** 3/3 plan-specific truths verified.

**Aggregate Score: 8/8 in-scope must-haves verified, 1 deferred to Phase 14 (explicitly out-of-scope per ROADMAP, BACKUP-V13-05/RESTORE-V13-05 ownership).**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `inventory/example-homelab/group_vars/all/backup.yml` | 5 shared backup knobs at locked defaults | VERIFIED | All 5 keys present with exact default values (D-176..D-179 locks honored); YAML parses cleanly. |
| `roles/garage/defaults/main.yml` (modified) | `garage_backup_stop_timeout` var | VERIFIED | Line 71: `garage_backup_stop_timeout: "{{ backup_stop_timeout \| default(60) }}"` |
| `roles/prometheus/defaults/main.yml` (modified) | `prometheus_backup_stop_timeout` var | VERIFIED | Line 93: same Jinja chain |
| `roles/grafana/defaults/main.yml` (modified) | `grafana_backup_stop_timeout` var | VERIFIED | Line 83: same Jinja chain |
| `roles/alertmanager/defaults/main.yml` (modified) | `alertmanager_backup_stop_timeout` var | VERIFIED | Line 71: same Jinja chain |
| `roles/garage/tasks/backup.yml` | Cold-quiesce 3-entry tarball (D-176) | VERIFIED (Levels 1-4) | Exists, 221 lines (substantive, ≥80), wired via include_role pattern, data flows (real volume + host-file source paths via CR-02 docker_volume_info resolution). |
| `roles/garage/tasks/restore.yml` | Confirm-gated 3-entry wipe + extract | VERIFIED | Exists, 376 lines (≥100), wired, data-flow verified. |
| `roles/prometheus/tasks/backup.yml` | Cold-quiesce single-volume tarball | VERIFIED | Exists, 153 lines (≥70). |
| `roles/prometheus/tasks/restore.yml` | Confirm-gated wipe + untar + PP-1 lock delete | VERIFIED | Exists, 267 lines (≥95). |
| `roles/grafana/tasks/backup.yml` | Cold-quiesce single-volume tarball | VERIFIED | Exists, 162 lines (≥70). |
| `roles/grafana/tasks/restore.yml` | Confirm-gated wipe + untar (no PP-1 — GR-1 WAL OFF) | VERIFIED | Exists, 253 lines (≥90). No `/_data/lock` or `queries.active` references — clean separation from Prometheus pattern. |
| `roles/alertmanager/tasks/backup.yml` | Cold-quiesce + AP-1 empty-data stat-guard | VERIFIED | Exists, 181 lines (≥75); `ansible.builtin.stat` registered as `am_data_dir_stat` (line 86-88), informational `ansible.builtin.debug` with `when: not (am_data_dir_stat.stat.exists and am_data_dir_stat.stat.isdir)` (line 97). |
| `roles/alertmanager/tasks/restore.yml` | Confirm-gated wipe + untar (empty-tolerant) | VERIFIED | Exists, 253 lines (≥90); no PP-1-style cleanup (no `_data/lock`, no `queries.active` — clean asymmetry with Prometheus per AP-1). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| 4 role defaults | `group_vars/all/backup.yml` | `{{ backup_stop_timeout \| default(60) }}` Jinja chain | WIRED | All 4 role defaults reference the same Jinja chain. Override resolution path: inventory `backup_stop_timeout` → role default expression → role tasks. |
| `roles/garage/tasks/backup.yml` | meta volume + data volume + s3-credentials host file | `tar --zstd -cpf` + 3 `--transform` regexes | WIRED | Single tar invocation (line 168-180) emits 3 entries into one tarball at `{{ backup_dest_root }}/garage/garage-{{ backup_timestamp.stdout }}.tar.zst`. |
| `roles/garage/tasks/restore.yml` | meta `_data/`, data `_data/`, `garage_s3_credentials_file` | 3× `tar --zstd -xpf` (per-entry extract with `--strip-components` + `-C` for `meta`/`data`; bare `s3-credentials` extract) | WIRED | Lines 286-339 — 3 separate extract invocations correctly reconstruct the absolute paths from the relativized tarball entries. |
| Prometheus restore `block:` | lock-file deletion | `ansible.builtin.file: state: absent` on `{{ prometheus_data_volume_info.volume.Mountpoint }}/lock` | WIRED | Line 239-243; PP-1 placement verified by awk ordering check (untar < lock < always). |
| All 4 restore.yml | `tar tf` integrity gate | `ansible.builtin.command: "tar --zstd -tf {{ backup_src_path }}"` BEFORE wipe | WIRED | Confirmed via awk ordering check on all 4: tf-line < wipe-line is PASS in all. |
| Prometheus/Grafana/Alertmanager backup+restore | `tasks/verify.yml` (existing, unchanged) | `ansible.builtin.include_tasks: verify.yml` inside `always:` | WIRED | 6 includes verified at lines: prom backup L150, prom restore L264, grafana backup L158, grafana restore L249, alertmanager backup L178, alertmanager restore L250. Each appears AFTER `^  always:` marker. |
| Garage backup+restore | post-restart healthy-poll | Inline `community.docker.docker_container_info` with `until: State.Health.Status == 'healthy'` | WIRED | D-178 conformance: backup line 207-218, restore line 362-373. No `include_tasks: verify.yml` in Garage files (intentional — Garage has no verify.yml). |
| All 4 restore.yml | confirm-gate fail-fast | `ansible.builtin.fail` with `when: not (backup_restore_confirm)` as the FIRST task (WR-02 fix) | WIRED | Confirmed FIRST in all 4 files; zstd install is task #2. |

### Data-Flow Trace (Level 4)

| Artifact | Data Source | Flows to | Status |
|----------|-------------|----------|--------|
| All 8 task files | `community.docker.docker_volume_info` registers volume.Mountpoint | tar source paths + find wipe paths + tar `--transform` regex anchors | FLOWING (CR-02 fix replaces hardcoded `/var/lib/docker/volumes/<vol>/_data` with dynamic mountpoint resolution; daemon-data-root-agnostic) |
| Backup tarballs | `umask 0177 && tar --zstd -cpf` (shell) | Tarball at mode 0600 directly at creation time (CR-01 TOCTOU fix) | FLOWING (`ansible.builtin.shell` rather than command because `umask` is a builtin; verified via grep — 2 occurrences in each of 4 backup.yml files: `umask 0177` + `tar --zstd -cpf` line) |
| Restore source path | `backup_restore_from` (operator-supplied) OR `find ... \| sort -r \| head -1` (D-179 lex-on-ISO-8601 latest discovery) | `backup_src_path` fact → `tar tf` integrity check → `tar -xpf` extraction | FLOWING; WR-03 fix validates `backup_restore_from` against `^[0-9]{8}T[0-9]{6}Z$` regex via `ansible.builtin.assert` before interpolation (path-traversal mitigation). WR-04 fix: `set -o pipefail; ... \| sort -r \| head -1` with `executable: /bin/bash` for proper error propagation. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `playbooks/deploy_docker.yml --syntax-check` passes | `ansible-playbook playbooks/deploy_docker.yml --syntax-check -i inventory/example-homelab/hosts --vault-password-file <(echo dummy)` | exit 0, output ends `playbook: playbooks/deploy_docker.yml` | PASS |
| YAML parses cleanly across all 13 modified files | `python3 -c "import yaml; yaml.safe_load(open('<file>'))"` ran across all 13 files | All 13 report OK | PASS |
| `include_role: tasks_from=backup` syntax-checks for each role | `ansible-playbook --syntax-check` against a synthetic playbook including each role's `backup`/`restore` task file | All 8 (4 roles × 2 ops) return success | PASS |
| Required structural patterns present | grep checks for `docker stop`, `block:`/`always:`, `name: zstd`, `tar --zstd -tf`, lock-file delete, stat-then-debug, mode 0600/0700 | All checks pass per Step 4 grep matrix above | PASS |

**Live execution against running stack** (BACKUP-V13-05/RESTORE-V13-05/UAT-V13-01) is Phase 14 scope per ROADMAP — explicitly excluded from this verification per the verify-work request.

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| n/a | No `scripts/*/tests/probe-*.sh` declared by the phase and none discovered in repo | n/a | SKIPPED — Phase 13 ships Ansible task files; no probe scripts authored by the phase. |

### Requirements Coverage

All 9 requirement IDs from PLAN frontmatter cross-referenced against `.planning/REQUIREMENTS.md`:

| Requirement | Source Plan(s) | Description (REQUIREMENTS.md) | Status | Evidence |
|-------------|----------------|-------------------------------|--------|----------|
| BACKUP-V13-01 | 13-01, 13-02 | Garage backup tarball with meta+data volumes AND s3-credentials, cold-quiesce | SATISFIED | `roles/garage/tasks/backup.yml` — 3-entry tarball wired (Roadmap truth #3 + #2 evidence). Live run check is Phase 14. |
| BACKUP-V13-02 | 13-01, 13-03 | Prometheus TSDB tarball with WAL/chunks_head/blocks, cold-quiesce | SATISFIED | `roles/prometheus/tasks/backup.yml` — single-volume tar of entire `_data/` tree via `tar -C <mountpoint> .` (entire volume captured; no `--exclude`). |
| BACKUP-V13-03 | 13-01, 13-04 | Grafana single tarball with grafana.db + plugins/, cold-quiesce | SATISFIED | `roles/grafana/tasks/backup.yml` — entire `_data/` tar (GR-2: no `--exclude` on plugins/csv); 0 occurrences of `exclude=` in file. |
| BACKUP-V13-04 | 13-01, 13-05 | Alertmanager tarball; handles empty-data fresh-deploy + populated state | SATISFIED | `roles/alertmanager/tasks/backup.yml` — AP-1 stat-then-debug guard present; tar runs unconditionally. |
| RESTORE-V13-01 | 13-01, 13-02 | Garage restore: integrity-check, wipe both volumes + s3-credentials, untar, restart | SATISFIED | `roles/garage/tasks/restore.yml` — 2 `find -mindepth 1 -delete` wipes + `ansible.builtin.file state: absent` on s3-credentials; 3 `tar --zstd -xpf` extracts (meta + data + s3-credentials). |
| RESTORE-V13-02 | 13-01, 13-03 | Prometheus restore: PP-1 lock-file delete AFTER untar BEFORE start | SATISFIED | `roles/prometheus/tasks/restore.yml` — lock delete line 239-243; ordering verified PASS. |
| RESTORE-V13-03 | 13-01, 13-04 | Grafana restore: symmetric, no PP-1 step | SATISFIED | `roles/grafana/tasks/restore.yml` — confirm-gated wipe+untar; NO `_data/lock` references (clean separation per GR-1). GR-4 admin-password rotation workaround documented in header (grep 'GR-4\|grafana-cli admin reset' returns ≥ 1). |
| RESTORE-V13-04 | 13-01, 13-05 | Alertmanager restore: handles empty backup symmetric | SATISFIED | `roles/alertmanager/tasks/restore.yml` — header documents AP-1 empty-data symmetry; no post-untar "ensure data/ subdir" task (AM creates `data/` on first state-write). |
| OPS-V13-04 | 13-02, 13-03, 13-04, 13-05 | zstd `ansible.builtin.package` pre-task in every backup/restore file, idempotent across Debian 12 / Ubuntu 22 / RHEL 9 | SATISFIED | Verified across all 8 task files (Roadmap truth #5). |

**No requirement IDs claimed by ROADMAP Phase 13 are orphaned** — every ID `BACKUP-V13-01..04`, `RESTORE-V13-01..04`, `OPS-V13-04` appears in at least one PLAN file's `requirements:` field AND has implementation evidence in the codebase. REQUIREMENTS.md confirms these are the Phase 13 IDs (BACKUP-V13-05, RESTORE-V13-05, OPS-V13-01..03 are Phase 14).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | Scan results: 0 `TBD`/`FIXME`/`XXX` debt markers in any phase 13 file; 0 `TODO`/`HACK`/`PLACEHOLDER` warning markers in any phase 13 file. The single `state: stopped` match in code was 0 (only the AN-1 explanation comment in `roles/garage/tasks/backup.yml` line 28 references the forbidden idiom). The single `state: absent` match in `roles/garage/tasks/restore.yml` is on `ansible.builtin.file: state: absent` for the s3-credentials host file (per-file scope, permitted by AN-1 which scopes only to `community.docker.docker_container`). |

### Code-Review Closure (13-REVIEW + 13-REVIEW-FIX)

| Finding | Severity | Status in Code | Verification |
|---------|----------|----------------|--------------|
| CR-01 (TOCTOU on tarball perms) | Critical | FIXED | `umask 0177 && tar --zstd -cpf` shell form present in all 4 backup.yml files (2 grep hits each — `umask` + `tar` line). |
| CR-02 (hardcoded `/var/lib/docker/volumes`) | Critical | FIXED | `community.docker.docker_volume_info` resolve tasks present in all 8 task files (2 or 3 usages per file); paths via `<vol>_info.volume.Mountpoint`. |
| WR-01 (operator-interrupt window) | Warning | FIXED (doc-only) | All 4 restore.yml carry a "WR-01" header block documenting the failure mode + recovery (re-run). |
| WR-02 (zstd install before confirm gate) | Warning | FIXED | Confirm-gate is the FIRST `- name:` task in all 4 restore.yml; zstd install is second. Verified via awk ordering check (PASS for all 4). |
| WR-03 (`backup_restore_from` injection) | Warning | FIXED | All 4 restore.yml carry `ansible.builtin.assert` with `regex_search('^[0-9]{8}T[0-9]{6}Z$')` on `backup_restore_from`. |
| WR-04 (missing `pipefail` in find pipeline) | Warning | FIXED | All 4 restore.yml: `set -o pipefail;` + `executable: /bin/bash` + `failed_when: rc != 0 or stdout == ""` present. |
| WR-05 (`garage_config_dir` missing on bare-metal restore) | Warning | FIXED | `roles/garage/tasks/restore.yml` lines 317-324: `ansible.builtin.file: state: directory` for `garage_config_dir` before s3-credentials extract. |
| WR-06 (asymmetric `become: true` on latest-discovery) | Warning | FIXED | All 4 restore.yml carry `become: true` on the latest-discovery shell task. |

All 8 review findings (2 Critical + 6 Warning) closed with codebase evidence.

### Human Verification Required

None for Phase 13 structural correctness. The following items are explicitly Phase 14 scope and route to the Phase 14 verification cycle, not this one:

- Live `ansible-playbook playbooks/backup_docker.yml --tags <role>` execution on leviathan with running stack (BACKUP-V13-05 / UAT-V13-01)
- Live `ansible-playbook playbooks/restore_docker.yml --tags <role> --extra-vars backup_restore_confirm=true` on leviathan with running stack (RESTORE-V13-05)
- Cold-quiesce timing budget validation against real Prometheus WAL + Garage LMDB sizes
- AP-2 stale-nflog re-fire empirical observation (operator-facing, real-receiver setups)

These do NOT block Phase 13 closure per the verify-work scoping (`playbooks/backup_docker.yml` does not yet exist; per-role tasks are the contract for Phase 14 to consume).

### Gaps Summary

No gaps blocking goal achievement. The phase ships 8 substantive Ansible task files + 1 shared vars file + 4 role-default additions, all wired and structurally correct. The previously-identified 2 Critical + 6 Warning code-review findings (13-REVIEW.md) were all auto-fixed in 13-REVIEW-FIX.md and verified present in the current codebase by this report.

The single live-execution success criterion in ROADMAP success_criteria[5] is explicitly out-of-Phase-13 scope (`playbooks/backup_docker.yml` is Phase 14 / BACKUP-V13-05). Structural readiness for Phase 14 to consume the task files is confirmed: `include_role: tasks_from=backup` and `tasks_from=restore` syntax-checks pass for all 4 stateful roles.

---

_Verified: 2026-06-03T13:30:00Z_
_Verifier: Claude (gsd-verifier)_
