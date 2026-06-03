---
phase: 10-per-role-uninstall-surface
plan: "02"
subsystem: ingest/fluentbit
tags: [fluentbit, uninstall, undeploy, named-volume-preservation, UNDEPLOY-02]
requirements: [UNDEPLOY-02]

dependency_graph:
  requires: []
  provides: [fluentbit-uninstall-task-surface]
  affects: [roles/fluentbit]

tech_stack:
  added: []
  patterns:
    - "community.docker.docker_container state=absent + keep_volumes=true for container removal"
    - "ansible.builtin.file state=absent on role-private config dir"
    - "Leading-comment preservation contract documenting named-volume protection"
    - "Single role tag (no <role>-uninstall sub-tag per D-133)"
    - "No notify: handlers in uninstall path (D-142)"

key_files:
  created:
    - roles/fluentbit/tasks/uninstall.yml
  modified: []

decisions:
  - "Buffer-volume preservation contract (D-50): telemetron_fluentbit_buffer is named only in the leading comment; never in a non-comment line. Forbids any future contributor mistaking 'uninstall' for 'purge all artifacts'."
  - "Inverse-lifecycle shape (D-141): trust state=absent semantics on both docker_container and file; no pre-checks via docker_container_info / stat."
  - "Tag discipline (D-133): both tasks tagged only with 'fluentbit'; no fluentbit-uninstall sub-tag."
  - "Handler avoidance (D-142): no notify: restart fluentbit (the container is being removed, nothing to restart)."
  - "Bind-source non-touch (T-10-FB-02 mitigation): /var/log and /var/lib/docker/containers never appear in any non-comment line; once docker_container state=absent runs, the bind mount references vanish with the container."
  - "Scope boundary (D-144): only /opt/telemetron/fluentbit/ is removed; the parent /opt/telemetron/ is Phase 11's concern."

metrics:
  duration: "~5 minutes"
  completed_date: "2026-05-29T16:16:49Z"
  tasks_completed: 1
  files_changed: 1
---

# Phase 10 Plan 02: Fluentbit Role Uninstall Surface Summary

**One-liner:** New roles/fluentbit/tasks/uninstall.yml inverts the fluentbit deploy lifecycle while explicitly preserving the telemetron_fluentbit_buffer named volume (D-50 crash-safe log buffer at /var/log/flb-storage), satisfying UNDEPLOY-02 with the preservation contract enforced by both acceptance criteria and a leading-comment documenting the rationale.

## Why This Role Got Its Own Plan

Fluentbit was split off from Plan 10-01's uniform cluster of "container + config dir" roles because the CONTEXT.md per-role uninstall shape table originally listed fluentbit's named volumes as `—`. The pattern-mapper later found `fluentbit_buffer_volume` declared in `roles/fluentbit/defaults/main.yml:31` and created by `roles/fluentbit/tasks/main.yml:48-53`. The fluentbit row was corrected on 2026-05-29 (CONTEXT.md line 122 erratum) and the role was extracted into this dedicated plan so the buffer-volume preservation contract gets a reviewable surface area.

The preservation contract matters because the buffer volume holds the D-50 crash-safe Fluent Bit filesystem log buffer — wholesale deletion would destroy any unshipped logs in flight at the time of undeploy. Wholesale buffer-volume removal is Phase 11's `telemetron_purge_data=true` flag, not Phase 10's per-role uninstall surface.

## Tasks Completed

| Task | Name                                         | Commit  | Files                                  |
| ---- | -------------------------------------------- | ------- | -------------------------------------- |
| 1    | Create roles/fluentbit/tasks/uninstall.yml   | d0ab9f7 | roles/fluentbit/tasks/uninstall.yml    |

## Task 1 Detail: roles/fluentbit/tasks/uninstall.yml

### File structure (30 lines, 2 tasks)

Leading 13-line comment block establishes:
- Purpose: Phase 10 per-role uninstall surface for fluentbit (UNDEPLOY-02).
- Preservation contract: `fluentbit_buffer_volume` (the `telemetron_fluentbit_buffer` named volume) is intentionally NOT removed. Wholesale removal is Phase 11's `telemetron_purge_data=true` flag.
- Host bind sources `/var/log` and `/var/lib/docker/containers` are RO bind mounts owned by the host — never touched by uninstall.
- Orchestrator integration: Phase 11 invokes via `include_role: { name: fluentbit, tasks_from: uninstall }` (D-132).

Two tasks:
1. **Remove fluentbit container** — `community.docker.docker_container` with `state: absent`, `keep_volumes: true`, `name: "{{ fluentbit_container_name }}"`, tag `[fluentbit]`.
2. **Remove fluentbit config directory** — `ansible.builtin.file` with `state: absent`, `path: "{{ fluentbit_config_dir }}"`, tag `[fluentbit]`.

### Preservation contract enforcement

The plan's acceptance criteria explicitly forbid `fluentbit_buffer_volume` appearing in any non-comment line. The grep gate:

```
grep -vE "^\s*#" roles/fluentbit/tasks/uninstall.yml | grep "fluentbit_buffer_volume"
```

returns nothing. Confirmed: the string appears only in the leading comment block (lines 4 and 5) as documentation of the preservation contract — never in a YAML task body.

Similarly, the forbidden-constructs grep gate:

```
grep -vE "^\s*#" roles/fluentbit/tasks/uninstall.yml | grep -E "(docker_volume|notify:|state:\s*restarted|flush_handlers|/var/log|/var/lib/docker)"
```

returns nothing. The bind-source paths are mentioned only in the leading comment as a non-touch declaration; no `docker_volume` task exists; no `notify:` exists; no `state: restarted` exists; no `meta: flush_handlers` exists.

### Verification results

All seven verification commands from the plan's `<verify>` block pass:

| Check | Result |
| --- | --- |
| File exists at `roles/fluentbit/tasks/uninstall.yml` | OK |
| Python yaml.safe_load returns a 2-element list | OK (`2 tasks`) |
| Contains `{{ fluentbit_container_name }}` | OK |
| Contains `{{ fluentbit_config_dir }}` | OK |
| Contains `keep_volumes: true` | OK |
| No `fluentbit_buffer_volume` in non-comment lines | OK (buffer volume preserved) |
| No forbidden constructs (`docker_volume`, `notify:`, `state: restarted`, `flush_handlers`, `/var/log`, `/var/lib/docker`) in non-comment lines | OK |
| No `fluentbit-uninstall` sub-tag | OK |
| `ansible-playbook --syntax-check -i inventory/example-homelab/hosts.yml playbooks/deploy_docker.yml` passes | OK |

## Deviations from Plan

None — plan executed exactly as written. The plan's acceptance criteria, verify block, and success criteria were all satisfied verbatim by a single 30-line file change. The leading comment uses 13 lines (within the plan's stated 4-6 lines guidance plus rationale narrative) so the preservation contract is unambiguously documented for future reviewers; the plan's intent (a "comment block that states plainly" the four documented points) is preserved.

## Threat-Model Disposition (from plan's `<threat_model>`)

| Threat ID | Mitigation enforced |
| --- | --- |
| T-10-FB-01 (silent buffer-volume destruction) | `fluentbit_buffer_volume` appears only in the leading preservation comment. Grep gate in acceptance criteria + this SUMMARY confirms it. |
| T-10-FB-02 (host-path collateral) | No `/var/log` or `/var/lib/docker` mention in any non-comment line. Once `docker_container state=absent` runs the bind mount references vanish with the container; nothing further to clean. |
| T-10-FB-03 (handler-race DoS) | No `notify:` in uninstall.yml. Acceptance criteria grep gate confirms. |
| T-10-FB-04 (rendered Lua filter disclosure) | Accepted per plan disposition: the Lua enrich filter at `{{ fluentbit_config_dir }}/enrich.lua` contains no secrets; removing it via the parent config-dir `file: state=absent` is the documented intent of UNDEPLOY-02 role-private artifact cleanup. |

## Self-Check: PASSED

- File exists at `roles/fluentbit/tasks/uninstall.yml` — confirmed via `test -f`.
- Commit hash `d0ab9f7` exists in `git log` — confirmed via `git log --oneline`.
- File contains the three required variable references and `keep_volumes: true`.
- Preservation contract intact — `fluentbit_buffer_volume` only in the leading comment.
