---
phase: 14-orchestrators-leviathan-human-uat
reviewed: 2026-06-04T18:30:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - playbooks/backup_docker.yml
  - playbooks/restore_docker.yml
  - roles/garage/tasks/backup.yml
  - roles/prometheus/tasks/backup.yml
  - roles/grafana/tasks/backup.yml
  - roles/alertmanager/tasks/backup.yml
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-06-04T18:30:00Z
**Depth:** standard (Ansible-aware)
**Files Reviewed:** 6 (1 modified set of 4 `roles/*/tasks/backup.yml` + 2 new orchestrators)
**Status:** issues_found

## Summary

Phase 14 ships the v1.3.0 backup/restore orchestration layer. Two new playbooks (`backup_docker.yml`, `restore_docker.yml`) wrap the Phase 13 per-role tasks, plus a `set_fact backup_timestamp_effective` insertion was made into each of the 4 stateful roles' `tasks/backup.yml` to wire up the D-191 shared-timestamp override.

Code quality is high — the modifications are surgical (each backup.yml change is ~10 lines), tag selection is explicit and consistent with D-149/D-188/D-189, the `block/always` restart guarantee from Phase 13 is preserved without disturbance, and the orchestrators are richly commented with D-ID and SC-ID provenance. The D-191 timestamp-override fallback (`default(backup_timestamp.stdout)`) is correct: standalone `include_role: tasks_from=backup` callers see zero behavior change.

That said, two real defects shipped, both already caught by the live UAT on leviathan (`14-HUMAN-UAT.md`):

- **CR-01 (Critical, restore_docker.yml)** — `restore_docker.yml` does NOT re-render Loki/Tempo/Mimir configs after Garage restore. Restored S3-credentials drift from writer configs on host; writers crash-loop with `Forbidden: No such key`. This is the same defect tracked as Gap **G-01** in `14-HUMAN-UAT.md`. The fix is in flight as a Phase 14.1 amendment per the documented fix-plan. Re-flagged here so it appears in the review-artifact channel.

- **WR-01 (Warning, backup_docker.yml)** — `backup_continue_on_failure=true` is functionally a no-op on single-host inventories. `any_errors_fatal: false` controls play-abort but Ansible still removes failed hosts from subsequent task execution, so Grafana/Alertmanager include_role calls have no host to run on. Tracked as **G-03** in `14-HUMAN-UAT.md`. Missing `meta: clear_host_errors` in a rescue path.

Both pre-existing G-01 / G-03 items are credited as caught-by-UAT (not regressions hidden from testing) and are re-flagged below without re-stating their fix-plans (already on the gaps list in `14-HUMAN-UAT.md`).

Beyond those two, this review surfaces additional issues spanning correctness, idempotency, and consistency. Summary table below.

## Findings Summary

| ID | Severity | File:Line | Issue |
|----|----------|-----------|-------|
| CR-01 | Critical | `playbooks/restore_docker.yml:186-230` | Garage restore does not re-render Loki/Tempo/Mimir configs; writers crash-loop on stale S3 key (pre-existing UAT G-01) |
| WR-01 | Warning | `playbooks/backup_docker.yml:76` | `backup_continue_on_failure=true` is functionally a no-op on single-host inventories; missing `meta: clear_host_errors` (pre-existing UAT G-03) |
| WR-02 | Warning | `playbooks/restore_docker.yml:137-149` | Writer-stop `docker stop` is non-idempotent: a re-run after a partial failure will trigger an Ansible-level failure if a writer is already stopped (or wedged) — there is no `failed_when:` or `ignore_errors:` guard |
| WR-03 | Warning | `playbooks/restore_docker.yml:192-204` | Writer-restart `docker start` against an already-running container exits non-zero on some Docker versions; same idempotency gap as WR-02 |
| WR-04 | Warning | `playbooks/backup_docker.yml:93` and `playbooks/restore_docker.yml:114` | Banner uses bare `{{ backup_continue_on_failure }}` / `{{ backup_restore_from }}` without `\| default(...)`; if an operator strips the inventory file or overrides incorrectly, the banner will fail with `AnsibleUndefinedVariable` BEFORE the safety gate fires |
| WR-05 | Warning | `playbooks/restore_docker.yml:138, 193` | Writer-quiesce tasks use `become: true` but the surrounding play has `become: false`; per-task escalation is fine, but the writer-restart `docker start` is missing a healthcheck-poll grace for the "container was already running before docker start" Docker daemon quirk (exits 0 on some daemons, non-zero on others) |
| IN-01 | Info | `playbooks/backup_docker.yml:93` | Banner emits `backup_continue_on_failure={{ ... \| default(false) }}` but the same expression elsewhere reads the raw var — minor inconsistency; the raw var is already defaulted at the `vars:` block, so the filter is redundant |
| IN-02 | Info | `roles/garage/tasks/backup.yml:91-96`, `roles/prometheus/tasks/backup.yml:77-82`, `roles/grafana/tasks/backup.yml:86-91`, `roles/alertmanager/tasks/backup.yml:117-122` | The new `set_fact backup_timestamp_effective` is duplicated verbatim across 4 files. Standard Ansible practice is fine, but a `vars:` mapping at include_role time would also work; current shape is explicit and consistent — kept-as-is is defensible |
| IN-03 | Info | `playbooks/backup_docker.yml:104-117` | The `command: date -u +%Y%m%dT%H%M%SZ` + `set_fact` two-step could be a single `set_fact: backup_timestamp_shared: "{{ '%Y%m%dT%H%M%SZ' \| strftime(ansible_date_time.epoch) }}"` (zero shell-out) — Ansible-idiomatic and gather_facts is already true |
| IN-04 | Info | `playbooks/restore_docker.yml:110-117` | The WARN banner enumerates "garage, prometheus, grafana, alertmanager" inline — contradicts the explicit D-186 stability principle the backup-banner correctly follows ("no role enumeration so banner stays stable across role additions"). Acceptable for the destructive identity-banner case, but worth noting the inconsistency in rationale |

## Critical Issues

### CR-01: restore_docker.yml does not re-render Loki/Tempo/Mimir configs after Garage restore (pre-existing UAT G-01)

**File:** `playbooks/restore_docker.yml:186-230`
**Pre-existing:** Yes — caught by Phase 14 HUMAN-UAT scenario 1 step 6 on leviathan and tracked as Gap **G-01** in `14-HUMAN-UAT.md`. Fix-plan already on the gaps list. Re-flagged here for review-artifact visibility.

**Issue:** After Garage's `tasks_from=restore` runs, the restored `/opt/telemetron/garage/s3-credentials` host file contains the ORIGINAL Garage S3 key (e.g. `GK18e0...`). However, the writer config files on the host (`/opt/telemetron/loki/loki.yaml`, `tempo.yaml`, `mimir.yaml`) still contain the POST-PURGE-REDEPLOY S3 key (e.g. `GKf41a...`). When the orchestrator's writer-restart loop fires `docker start telemetron-loki`, Loki reads the stale config, presents the wrong key to Garage, and crash-loops with:

```
level=error caller=log.go:223 msg="error running loki" err="init compactor: failed to init delete store: operation error S3: DeleteObject ... AccessDenied: Forbidden: No such key: GKf41a2c5494e088bfda8b3a0d"
```

Same crash pattern for Tempo and Mimir. The `community.docker.docker_container_info` healthy-poll then times out (30 retries × 2s = 60s) and the play fails. Stack is left in a half-restored state requiring manual intervention.

Workaround applied during UAT (works around but does not fix the orchestrator):
```bash
ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags loki,tempo,mimir,garage
```

The comment at lines 186-191 of `restore_docker.yml` makes the wrong assumption explicit:
```yaml
# Garage S3 endpoint and credentials haven't changed
# (Phase 13's Garage restore restores the s3-credentials host file), so
# the writers come back pointing at the same buckets they were
# configured for -- no config re-render needed.
```
This is true for the credentials file but ignores the fact that writer configs (rendered at deploy time from `garage_s3_credentials_file`) were re-rendered at the post-purge redeploy and now hold the wrong key.

**Fix (from G-01 fix-plan):** Add `include_role: name=<writer> tasks_from=main` for loki/tempo/mimir AFTER the Garage restore and BEFORE the writer-restart loop (or replace the writer-restart loop with the include_role calls — they handle start + healthcheck). The fix-plan recommends Option (1): idempotent re-deploy of the 3 writer roles re-reads `garage_s3_credentials_file` and re-renders configs. See `14-HUMAN-UAT.md` G-01 for the full options analysis.

## Warnings

### WR-01: backup_continue_on_failure=true is a no-op on single-host inventories (pre-existing UAT G-03)

**File:** `playbooks/backup_docker.yml:76`
**Pre-existing:** Yes — caught by Phase 14 HUMAN-UAT scenario 3b on leviathan and tracked as Gap **G-03** in `14-HUMAN-UAT.md`. Fix-plan already documented. Re-flagged here for review-artifact visibility.

**Issue:** Line 76:
```yaml
any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"
```
This correctly inverts the knob for the play-level abort decision, but it is insufficient on its own. Ansible's default error handling removes a failed host from subsequent task execution regardless of `any_errors_fatal`. On a single-host inventory (the entire v1.3.0 surface — leviathan, example-homelab), if Prometheus's `include_role: tasks_from=backup` fails, the only host (leviathan) is removed from the play and the Grafana + Alertmanager `include_role` calls have no host to run against. Result: only 1 of 4 tarballs gets written, not the documented 3 of 4.

The PLAY-start banner correctly fires its alt-text ("all 4 roles will attempt their backup; failures aggregated in PLAY RECAP"), so the operator is told a contract that the orchestrator does not actually deliver — worse than no opt-in flag at all.

**Fix (from G-03 fix-plan):** Wrap each per-role `include_role` in `block: / rescue:` where the rescue calls `meta: clear_host_errors` to put the host back in the active set. Optionally guard the rescue with `when: backup_continue_on_failure | default(false) | bool` so default-mode behavior is unchanged. See `14-HUMAN-UAT.md` G-03 for the full options analysis.

### WR-02: Writer-stop `docker stop` is non-idempotent against partial-failure retry

**File:** `playbooks/restore_docker.yml:137-149`
**Issue:** The writer-stop loop:
```yaml
- name: Stop Garage writers (Loki/Tempo/Mimir) before Garage restore (D-181, D-189)
  ansible.builtin.command: "docker stop -t {{ backup_stop_timeout }} {{ item.container_name }}"
  loop:
    - { role: loki,  container_name: "..." }
    - { role: tempo, container_name: "..." }
    - { role: mimir, container_name: "..." }
  loop_control:
    label: "{{ item.role }}"
  changed_when: true
  become: true
```
has no `failed_when:` or `ignore_errors:` guard. `docker stop <container>` on a container that does not exist (e.g., Phase 14.x will land scenarios where the operator re-runs restore after a partial deploy where a writer was never started, or where a writer was removed via `--tags loki` undeploy) exits non-zero with:
```
Error response from daemon: No such container: telemetron-loki
```
This causes the loop to fail on the FIRST writer-stop attempt of the restore — before any tarball is read, before Garage is touched. The play aborts with a confusing error pointing at a writer-stop, not the missing container.

The writer-restart loop has the symmetric issue (WR-03) — `docker start` against a missing container also fails.

**Fix:** Add a tolerance guard. Two options:

Option A (use `community.docker.docker_container` with `state: stopped` + `ignore_errors`-style tolerance — but per XP-1 that strips volume specs, so NOT applicable here).

Option B (canonical):
```yaml
- name: Stop Garage writers (Loki/Tempo/Mimir) before Garage restore
  ansible.builtin.command: "docker stop -t {{ backup_stop_timeout }} {{ item.container_name }}"
  loop: [...]
  loop_control:
    label: "{{ item.role }}"
  register: writer_stop_result
  failed_when: >-
    writer_stop_result.rc != 0
    and 'No such container' not in writer_stop_result.stderr
  changed_when: writer_stop_result.rc == 0
  become: true
```

### WR-03: Writer-restart `docker start` has the same idempotency gap as WR-02

**File:** `playbooks/restore_docker.yml:192-204`
**Issue:** Symmetric with WR-02 — `docker start` against a non-existent container fails with `No such container`. Additionally, on some Docker daemon versions, `docker start <already-running-container>` exits 0 but other versions exit non-zero. The current task has no tolerance for either case.

**Fix:** Apply the same `failed_when: 'No such container' not in stderr` guard as WR-02, and consider adding `ignore_errors: true` plus an explicit "is it running?" probe via `docker_container_info` if hardening matters. The writer-restart-then-poll-healthy pattern (lines 210-230) already does the healthy-poll, so the actual operational guarantee is the poll — the `docker start` is just the kick. A graceful `failed_when:` is the lowest-risk hardening.

### WR-04: PLAY-start banners reference vars without `| default(...)` filter

**File:** `playbooks/backup_docker.yml:93` and `playbooks/restore_docker.yml:114`
**Issue:** Both banner debugs read shared knobs without a defensive default:

Backup banner line 93:
```yaml
backup_continue_on_failure={{ backup_continue_on_failure | default(false) }}
```
This is defended (good).

But line 95 reads `backup_stop_timeout` raw:
```yaml
backup_stop_timeout={{ backup_stop_timeout }}s
```

And restore banner line 114:
```yaml
Target timestamp: {{ backup_restore_from | default('<latest per role>') }}
```
is defended.

But the `pre_tasks:` use `backup_dest_root` (backup line 92) and `backup_stop_timeout` (line 95) raw. If a user invokes the orchestrator against an inventory that does not include `inventory/example-homelab/group_vars/all/backup.yml` (e.g., a BYO inventory missing this group_var file), the banner fires `AnsibleUndefinedVariable` BEFORE the confirm-gate or any safety gate. The banner is `tags: always` and runs first, so a missing `backup_dest_root` aborts the play with an unhelpful Jinja undefined-var error.

The orchestrator's quickstart README is supposed to walk new operators through BYO inventory; a missing group_var should produce a clear "please define backup_dest_root in your inventory" message, not a Jinja stacktrace.

**Fix:** Either (a) wrap every var reference in the two banners with `| default(...)` (lowest-risk) or (b) add a pre_tasks `assert:` step before the banner validating that the 5 shared knobs are defined, with a `msg:` pointing to the canonical inventory location.

### WR-05: become semantics on writer-stop/restart loops

**File:** `playbooks/restore_docker.yml:138, 193`
**Issue:** The play header at line 74 sets `become: false` (correct for an orchestrator that delegates `become` to per-task escalations). Both the writer-stop (line 138) and writer-restart (line 193) tasks set `become: true` to run `docker stop`/`docker start` as root.

The actual concern is subtler: these loops run `ansible.builtin.command` (not `community.docker.docker_container_exec` against the Docker socket) and rely on the controller user being able to `sudo docker`. On the leviathan UAT host this works (Rock's profile is in the docker + sudo groups), but on a BYO Docker host where the operator user can talk to Docker via socket group membership but NOT sudo, the `become: true` will fail at the sudoers gate. The per-role `tasks/backup.yml` files have the same pattern — accepted there because Phase 13 documented "Docker requires either docker group membership OR sudo." That documentation does not exist for `restore_docker.yml`.

**Fix:** Document the assumption in the playbook's header comment ("Operator user MUST have `sudo docker` or be in the docker group; if the latter, override become: false in the writer-quiesce loop via --extra-vars"). Lowest-risk fix is a doc-only note. Phase 15's doc cascade may already cover this — verify.

## Info

### IN-01: Redundant `| default(false)` filter on already-defaulted var

**File:** `playbooks/backup_docker.yml:93`
**Issue:** Line 93: `backup_continue_on_failure={{ backup_continue_on_failure | default(false) }}` — the var is already defaulted at the `vars:` block (line 81: `backup_continue_on_failure: false`), so the filter is harmless but redundant. Same at line 94 in the Jinja `if` expression.
**Fix:** Cosmetic only. Either remove the filter (relying on the `vars:` default) or keep it (defense-in-depth against `--extra-vars backup_continue_on_failure=` unset by some wrapper script). Current shape is defensible.

### IN-02: D-191 set_fact insertion duplicated across 4 files

**File:** `roles/garage/tasks/backup.yml:91-96`, `roles/prometheus/tasks/backup.yml:77-82`, `roles/grafana/tasks/backup.yml:86-91`, `roles/alertmanager/tasks/backup.yml:117-122`
**Issue:** The same 6-line `set_fact backup_timestamp_effective` block is duplicated verbatim in each of the 4 backup.yml files. The plan deliberately chose this shape (per D-191 Option B) over a `vars:` mapping at include_role time. Current shape is explicit and consistent — IN-01 quality-only flag.
**Fix:** None required. Documented as an info-only because future readers may wonder if this could DRY. Answer: it could, but the explicit shape preserves "standalone include_role: tasks_from=backup just works" — alternative would require either a wrapper role or a coupling to orchestrator-side vars. Current shape is the right tradeoff for the project's Ansible-conventions audience.

### IN-03: Shared-timestamp generation uses shell-out instead of ansible_date_time

**File:** `playbooks/backup_docker.yml:104-117`
**Issue:** Lines 104-117 use a two-task pattern (`command: date -u +%Y%m%dT%H%M%SZ` + register + `set_fact`) when a single `set_fact` could compute the same value from `ansible_date_time` (already populated by `gather_facts: true` at line 66):
```yaml
- set_fact:
    backup_timestamp_shared: "{{ '%Y%m%dT%H%M%SZ' | strftime(ansible_date_time.epoch | int) }}"
```
The shell-out is harmless (microseconds), but the Ansible-idiomatic shape is one task with zero subprocess invocations.
**Fix:** Cosmetic. Worth keeping a note here because the per-role `tasks/backup.yml` files use the same shell-out pattern for the per-role timestamp — possibly worth a follow-up sweep across all 4 to unify.

### IN-04: Restore banner enumerates role names; backup banner deliberately does not

**File:** `playbooks/restore_docker.yml:110-117`
**Issue:** The backup-banner header comment at line 84-88 explicitly cites D-186 stability ("Category descriptions, no role-name enumeration so the banner is stable across future role additions"). The restore-banner at lines 110-117 enumerates role names:
```yaml
WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)
...
Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir
```
A future 5th stateful role addition will silently make this banner lie. The decision was deliberate (D-187 specifies the verbatim 3-line shape), but it's inconsistent with D-186's stability principle.
**Fix:** None required (D-187 locks the verbatim shape). Worth noting because Phase 15's doc cascade may want to call out the maintenance contract ("when you add a 5th stateful role, update this banner").

## Pre-existing items credited to UAT

Both **CR-01 (G-01)** and **WR-01 (G-03)** were caught by the live Phase 14 HUMAN-UAT on leviathan (`14-HUMAN-UAT.md`), with fix-plans already documented under `## Gaps`. They are NOT regressions hidden from testing — they are exactly the kind of behavioral defect the UAT layer is designed to surface (the v1.1.0 / v1.2.0 lesson Rock has called out before: live-deploy is the only gate that catches output-format and host-handling assumptions).

This review re-flags them in the review-artifact channel for visibility but does not re-state their fix-plans. The Phase 14.1 amendment (or follow-up plan) targets both.

## Cross-cutting notes

- **English-only naming:** All artifacts pass (no French strings).
- **Idempotency:** Backup tasks are idempotent for the normal-path case (block/always restart guarantee preserved from Phase 13). Restore writer-quiesce loops have idempotency gaps on retry (WR-02 / WR-03).
- **Confirm-gate identity-level safety:** Correctly tagged `[always]` per D-188 amended; UAT scenarios 2a/2b/2c prove the contract holds.
- **Tag selection:** Correct per D-149 (per-role + cross-cutting `[<role>, backup]` and `[<role>, restore]`) and D-189 (writer-quiesce `[garage, restore]` only). UAT scenarios 4a-4d-restore prove the tag matrix empirically.
- **Secrets handling:** Tarballs are mode 0600, dest dirs 0700, umask 0177 before tar to close the TOCTOU window (CR-01 from Phase 13, retained). Garage tarball captures s3-credentials in plaintext — perm contract correctly enforced.
- **Block/rescue/always shape:** Backup tasks correctly wrap stop + tar in `block:` with `always:` restart + verify. Phase 14's amendments do not disturb this.

---

_Reviewed: 2026-06-04T18:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (Ansible-aware)_
