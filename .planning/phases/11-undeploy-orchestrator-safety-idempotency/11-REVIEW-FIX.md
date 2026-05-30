---
phase: 11-undeploy-orchestrator-safety-idempotency
fixed_at: 2026-05-29T00:00:00Z
review_path: .planning/phases/11-undeploy-orchestrator-safety-idempotency/11-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-05-29
**Source review:** `.planning/phases/11-undeploy-orchestrator-safety-idempotency/11-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope: 2 (Critical only -- `--fix` without `--all`)
- Fixed: 2
- Skipped: 0 (4 warnings + 3 info findings are out of scope; not attempted)

Both BLOCKER findings address the same defect class: `tags: always` on
post_tasks that should only run on a full unscoped undeploy. Targeted
`--tags <role>` invocations were silently destroying shared infra (bridge
network, /opt/telemetron parent tree) outside the tagged role's scope,
breaking the "Tag-scoped purge composition (D-151)" contract advertised in
the orchestrator header.

A third commit (`docs(11):`) adds a short caveat sentence to the orchestrator
header so operators know `--tags <role>` no longer reaches those post_tasks
and that `telemetron_purge_host_dirs=true` is intended for a full-stack
undeploy.

Syntax verified after each commit:

```
ansible-playbook playbooks/undeploy_docker.yml --syntax-check
# -> playbook: playbooks/undeploy_docker.yml  (no errors)
```

## Fixed Issues

### CR-01: Targeted `--tags <role>` purge tears down the shared bridge network

**Files modified:** `playbooks/undeploy_docker.yml`
**Commit:** `cf3a511`
**Applied fix:** Removed `tags: always` from the `Remove the telemetron Docker
bridge network` post_task. The task now carries `tags: [network]` only.
Ansible's normal tag filtering ensures it runs only on (a) an unscoped
invocation, or (b) when `--tags network` is explicitly given -- matching the
intended behaviour per the orchestrator header.

Pre-fix snippet:

```yaml
- name: Remove the telemetron Docker bridge network
  community.docker.docker_network:
    name: "{{ telemetron_network }}"
    state: absent
  tags:
    - always
    - network
```

Post-fix snippet:

```yaml
- name: Remove the telemetron Docker bridge network
  community.docker.docker_network:
    name: "{{ telemetron_network }}"
    state: absent
  tags:
    - network
```

### CR-02: Targeted `--tags <role>` purge with `telemetron_purge_host_dirs=true` nukes every other role's host config

**Files modified:** `playbooks/undeploy_docker.yml`
**Commit:** `ddad530`
**Applied fix:** Removed `tags: always` from BOTH the `WARN -- /opt/telemetron
host tree will be removed` debug task AND the destructive `Remove
/opt/telemetron parent host tree` `ansible.builtin.file: state=absent` task.
Both tasks now have no `tags:` line at all (simplest option per the review's
recommendation, matching the rest of the role-scoped purge surfaces). The
`when: telemetron_purge_host_dirs | default(false) | bool` gate is preserved
on both tasks.

Pre-fix snippet:

```yaml
- name: WARN -- /opt/telemetron host tree will be removed
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)"
  when: telemetron_purge_host_dirs | default(false) | bool
  tags:
    - always

- name: Remove /opt/telemetron parent host tree
  ansible.builtin.file:
    path: "{{ telemetron_config_root | default('/opt/telemetron') }}"
    state: absent
  when: telemetron_purge_host_dirs | default(false) | bool
  tags:
    - always
```

Post-fix snippet:

```yaml
- name: WARN -- /opt/telemetron host tree will be removed
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)"
  when: telemetron_purge_host_dirs | default(false) | bool

- name: Remove /opt/telemetron parent host tree
  ansible.builtin.file:
    path: "{{ telemetron_config_root | default('/opt/telemetron') }}"
    state: absent
  when: telemetron_purge_host_dirs | default(false) | bool
```

### Header clarification (follow-on to CR-01 + CR-02)

**Files modified:** `playbooks/undeploy_docker.yml`
**Commit:** `52dba59`
**Applied fix:** Added a short caveat to the existing "Tag-scoped purge
composition (D-151)" comment block (lines 22-24) explaining that:

1. `--tags <role>` does NOT remove the shared telemetron Docker bridge
   network (now tagged `network`, not `always`).
2. The `telemetron_purge_host_dirs=true` /opt/telemetron parent-tree removal
   is untagged and runs only on a full unscoped undeploy.
3. Both are now safe under targeted re-runs; `telemetron_purge_host_dirs=true`
   should be used on a full-stack undeploy.

The header structure was preserved (no restructure), only a clarifying
sentence appended after the existing D-151 paragraph, per the user's
instruction.

## Skipped Issues

None. All in-scope (Critical / BLOCKER) findings were fixed.

The following out-of-scope findings were NOT attempted (would require
`--fix --all`):

- WR-01: header "12 / 23 include_role calls" vs `enable_nfsd` default-off
  precision
- WR-02: `garage` purge_data WARN templating risk on undefined volume vars
- WR-03: no post-play summary of which roles' purge sections executed
- WR-04: `become: false` + `state=absent` on `/opt/telemetron` perms failure
  mode
- IN-01: duplicated 30-40 line header comment blocks across 5 role purges
- IN-02: `_result` vs `_results` register naming (already correct; noted for
  reader)
- IN-03: `nfsd` has no `purge.yml` (intentional per D-156; optional README
  note)

## Verification

- Tier 1 (mandatory): re-read modified file sections after each Edit;
  confirmed fix text present, surrounding code intact.
- Tier 2 (preferred): `ansible-playbook playbooks/undeploy_docker.yml
  --syntax-check` run after CR-01, CR-02, and the header docs commit -- all
  three runs report `playbook: playbooks/undeploy_docker.yml` (parse OK).
  Inventory-matching warnings are expected (the worktree had no inventory
  attached); no YAML/Jinja errors.
- Tier 3: n/a.

## Notes for the Verifier Phase

Both CR-01 and CR-02 fixes are syntactic + tag-config changes; no runtime
logic was modified. Verification should include:

1. Targeted re-run safety: `ansible-playbook playbooks/undeploy_docker.yml
   --tags garage` (with the rest of the stack still running on `leviathan`)
   should NOT remove the bridge network and should NOT touch
   `/opt/telemetron/{loki,grafana,...}/`. This is the regression the fix
   targets.
2. Full unscoped undeploy: `ansible-playbook playbooks/undeploy_docker.yml`
   should still remove the bridge network and (if
   `telemetron_purge_host_dirs=true`) remove the parent tree.
3. Explicit network tag: `ansible-playbook playbooks/undeploy_docker.yml
   --tags network` should remove ONLY the bridge network (after every
   container is already down, otherwise Docker will refuse / force-detach).

---

_Fixed: 2026-05-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
