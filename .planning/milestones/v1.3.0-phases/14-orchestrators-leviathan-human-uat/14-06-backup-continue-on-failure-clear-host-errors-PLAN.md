---
phase: 14-orchestrators-leviathan-human-uat
plan: 06
type: execute
wave: 1
depends_on: []
files_modified:
  - playbooks/backup_docker.yml
autonomous: true
gap_closure: true
requirements:
  - BACKUP-V13-05
  - OPS-V13-02
requirements_addressed:
  - BACKUP-V13-05
  - OPS-V13-02

must_haves:
  truths:
    - "G-03 closed: With `backup_continue_on_failure=true` on a single-host inventory (leviathan, example-homelab) AND a Prometheus failure injected, the 3 remaining role tarballs (garage, grafana, alertmanager) are still produced at the run's shared timestamp -- not just the Garage tarball as the pre-fix behavior produced."
    - "SC5 (ROADMAP.md Phase 14 #5) flips from PARTIAL to VERIFIED: `backup_continue_on_failure=true` opt-in actually delivers the contract the PLAY-start banner promises (`(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)`)."
    - "Each of the 4 per-role `include_role` calls in `playbooks/backup_docker.yml` is wrapped in a `block:` with a matching `rescue:` that calls `ansible.builtin.meta: clear_host_errors`. The `rescue:` is GUARDED by `when: backup_continue_on_failure | default(false) | bool` so default-mode behavior (bail-out on first role failure) is unchanged -- under default mode the failed task aborts before the rescue is considered."
    - "Default-mode behavior is unchanged: `backup_continue_on_failure=false` (default) STILL bails out on first role failure. UAT scenario 3a behavior is preserved -- Prometheus failure aborts the play, Grafana + Alertmanager include_role calls do NOT run, only Garage tarball at run-ts."
    - "PLAY RECAP under opt-in mode shows `failed=1` (the one Prometheus failure) AND ok-count reflects Grafana + Alertmanager tasks attempted (they actually ran rather than being skipped due to host removal)."
    - "Banner alt-text contract is now honored: `(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)` is no longer a lie."
    - "D-184's locked decision -- `Explicit block/rescue around each include_role rejected -- 4x the YAML for behavior any_errors_fatal gives natively.` -- is REVERSED based on G-03 field evidence. Field reality (UAT scenario 3b on leviathan) shows that on a single-host inventory, `any_errors_fatal: false` alone does NOT keep the host in the active set across role failures -- Ansible's default error handling removes the failed host independently. The 4x YAML cost is real but unavoidable. `any_errors_fatal` is PRESERVED as complementary to the new rescue (it still gates play-level abort); the rescue handles the host-removal semantic that `any_errors_fatal` alone cannot."
    - "Tag UX preserved: each per-role `block:` carries `tags: [<role>, backup]` (matching the pre-fix tag list on the include_role itself). CRITICAL: the inner `include_role` task MUST ALSO retain its `tags: [<role>, backup]` (NOT removed when moving to block-level tags). Per the existing comment at `playbooks/backup_docker.yml:119-130`, dynamic `include_role` resolves tags at the include-task level BEFORE descending into the role body -- so the include-task tag list is what `--tags backup` actually filters on; block-level tags help with role-body visibility but cannot substitute for the include-task tag list. Keeping BOTH ensures `--tags backup`, `--tags <role>`, and `--list-tasks --tags backup` all behave identically to pre-fix."
    - "`any_errors_fatal: \"{{ not (backup_continue_on_failure | default(false) | bool) }}\"` (line 76) is PRESERVED -- the block/rescue change is complementary, not a replacement. `any_errors_fatal` still controls play-level abort for the default case; the new `rescue:` + `clear_host_errors` handles the host-removal-from-active-set semantic that `any_errors_fatal` alone cannot."
    - "`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0."
    - "`ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` still enumerates exactly the 4 role include_role lines (`Invoke garage backup`, `Invoke prometheus backup`, `Invoke grafana backup`, `Invoke alertmanager backup`) -- the block wrapper is transparent to --list-tasks AND the include_role-level tag retention guarantees `--tags backup` selects all 4. This is the execute-time canary that catches tag-leakage BEFORE the leviathan re-UAT runs."
  artifacts:
    - path: "playbooks/backup_docker.yml"
      provides: "Thin backup orchestrator with per-role block/rescue/clear_host_errors wrapping each include_role; opt-in continue-on-failure now actually keeps the host in the active set."
      min_lines: 110
      contains: "clear_host_errors"
  key_links:
    - from: "Per-role `block:` wrapping each `include_role` call (4 blocks: garage, prometheus, grafana, alertmanager)"
      to: "`rescue:` calling `ansible.builtin.meta: clear_host_errors`"
      via: "Ansible block/rescue/always control flow -- rescue fires ONLY on block failure"
      pattern: "rescue:"
    - from: "`rescue:` `when: backup_continue_on_failure | default(false) | bool`"
      to: "Default-mode preservation: under `backup_continue_on_failure=false` (default), the rescue is skipped, the failed task propagates, `any_errors_fatal: true` (from the inverted expression on line 76) aborts the play"
      via: "Ansible `when:` guard evaluation"
      pattern: "when: backup_continue_on_failure"
    - from: "`ansible.builtin.meta: clear_host_errors` inside rescue"
      to: "Host returns to the active set for subsequent role include_role calls"
      via: "Ansible meta task -- clears the host's failed state so the play continues against this host"
      pattern: "clear_host_errors"
    - from: "Block-level `tags: [<role>, backup]` AND retained include_role-level `tags: [<role>, backup]`"
      to: "Tag UX preserved -- `--tags <role>` selects exactly the per-role block; `--tags backup` cross-cutting selects all 4 blocks; `--list-tasks --tags backup` enumerates all 4 include_role invocations"
      via: "Ansible tag inheritance from block to inner tasks AND include-task-level tag filtering for dynamic include_role (per the existing comment at playbooks/backup_docker.yml:119-130)"
      pattern: "tags:\\s+-\\s+backup"
---

<objective>
G-03 closure. `playbooks/backup_docker.yml` line 76 sets `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"`, which correctly inverts the play-level abort knob: default-mode (`backup_continue_on_failure=false`) gives `any_errors_fatal=true` (bail-out on first role failure), opt-in (`backup_continue_on_failure=true`) gives `any_errors_fatal=false` (do not abort the play on a role failure).

BUT: Ansible's default error handling ALSO removes a failed host from subsequent task execution. On a single-host inventory (leviathan, example-homelab -- the only inventory shapes v1.3.0 targets), when Prometheus's `include_role: tasks_from=backup` fails, leviathan is removed from the host list. The Grafana and Alertmanager `include_role` calls then have NO host to run on. Result: only the Garage tarball is written under opt-in mode, not 3 of 4 as the banner alt-text promises.

This plan wraps each of the 4 per-role `include_role` calls in a `block:` with a `rescue:` that calls `ansible.builtin.meta: clear_host_errors`. The `rescue:` is guarded by `when: backup_continue_on_failure | default(false) | bool` so default-mode behavior is unchanged: under default mode the failed task propagates, `any_errors_fatal: true` aborts the play, the rescue never runs. Under opt-in mode, the rescue fires, clears the host's failed state, and the next role's include_role runs against the (now active again) host.

Purpose: SC5 flips from PARTIAL to VERIFIED. The banner alt-text contract `(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)` is now actually delivered on the inventory shape v1.3.0 targets. OPS-V13-02 opt-in contract is honored.
Output: amended `playbooks/backup_docker.yml`. No other files changed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-PATTERNS.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-REVIEW.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md

@playbooks/backup_docker.yml
@roles/garage/tasks/backup.yml
@roles/prometheus/tasks/backup.yml

<interfaces>
<!-- Ansible primitives the fix uses -->

block:                              -- groups N tasks; failure of any task triggers rescue
  rescue:                           -- runs ONLY on block failure
    when: <guard>                   -- evaluated at rescue time; if false, rescue is skipped and failure propagates
    - ansible.builtin.meta:         -- meta tasks are play-control primitives
        clear_host_errors           -- clears the host's failed state, restoring it to the active set for subsequent tasks

<!-- Existing per-role include_role structure (lines 132-170 of backup_docker.yml, BEFORE) -->

- name: Invoke <role> backup
  ansible.builtin.include_role:
    name: <role>
    tasks_from: backup
  vars:
    backup_timestamp_override: "{{ backup_timestamp_shared }}"
  tags:
    - <role>
    - backup

<!-- Target shape AFTER the fix (per per-role block) -->

- name: <role> backup (G-03: block/rescue allows continue-on-failure)
  tags:
    - <role>
    - backup
  block:
    - name: Invoke <role> backup
      ansible.builtin.include_role:
        name: <role>
        tasks_from: backup
      vars:
        backup_timestamp_override: "{{ backup_timestamp_shared }}"
      tags:
        - <role>
        - backup            # MANDATORY -- retained on the include_role (NOT removed when moving to block-level tags); per the existing comment at lines 119-130, dynamic include_role resolves tags at the include-task level BEFORE descending into the role body
  rescue:
    - name: Clear host errors so subsequent role backups still run (G-03; opt-in only)
      ansible.builtin.meta: clear_host_errors
      when: backup_continue_on_failure | default(false) | bool

<!-- Why the rescue's `when:` is critical -->

Default mode (`backup_continue_on_failure=false`):
  - role fails -> block fails -> rescue ENTERED
  - rescue evaluates `when: backup_continue_on_failure | default(false) | bool` -> false
  - clear_host_errors is SKIPPED
  - the host remains in the failed state
  - `any_errors_fatal: true` (from line 76 inversion) aborts the play
  - Net effect: identical to current behavior (UAT scenario 3a)

Opt-in mode (`backup_continue_on_failure=true`):
  - role fails -> block fails -> rescue ENTERED
  - rescue evaluates `when: backup_continue_on_failure | default(false) | bool` -> true
  - clear_host_errors RUNS -> host returns to active set
  - `any_errors_fatal: false` (from line 76 inversion) does NOT abort
  - Next role's block enters its include_role with the host active -- the role runs
  - Net effect: all 4 roles attempt their backup (G-03 fix delivers what the banner promised)

<!-- Tag inheritance: tags exist on BOTH the wrapping block AND the inner include_role -->

The pre-fix include_role carried `tags: [<role>, backup]`. The fix ADDS tags at the block level
BUT does NOT remove them from the include_role. Per the existing comment at lines 119-130 of
backup_docker.yml, dynamic `include_role` resolves tags at the include-task level BEFORE
descending into the role body -- so the include-task tag list is what `--tags backup` actually
filters on. Block-level tags propagate down to inner tasks for visibility/inheritance, but
they cannot substitute for the include-task tag list when `--tags <name>` is the selection
mechanism.

Empirical canary: `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab
playbooks/backup_docker.yml` MUST enumerate all 4 include_role invocations
(`Invoke garage backup`, `Invoke prometheus backup`, `Invoke grafana backup`,
`Invoke alertmanager backup`). If any include_role goes missing from that list, tag
inheritance has broken and `--tags backup` will silently skip that role at run time on
leviathan. This catches the bug at execute-time, NOT at run-time on the live host.

The rescue's clear_host_errors task carries NO additional tags (inherits from block) -- so under
`--tags <role>`, the rescue only fires if a failure occurs in that role's block, and the clear
is scoped to that block (it does not affect other roles' blocks).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Wrap each include_role in playbooks/backup_docker.yml with block/rescue/clear_host_errors guarded by backup_continue_on_failure</name>
  <files>playbooks/backup_docker.yml</files>
  <read_first>
    - playbooks/backup_docker.yml (full file -- understand current state: vars at lines 78-81, pre_tasks at 83-117 with banner + shared timestamp + set_fact, tasks at 131-170 with 4 include_role calls at lines 132-140, 142-150, 152-160, 162-170. Line 76 carries the `any_errors_fatal` Jinja expression that this plan PRESERVES. CRITICAL: re-read the comment at lines 119-130 -- it documents that dynamic include_role resolves tags at the include-task level BEFORE descending; that is why the inner include_role MUST retain its `tags:` even after moving tags to the block level.)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md gaps[1].missing (recommended remediation: wrap each per-role `include_role` in `block:`/`rescue:` where the rescue calls `meta: clear_host_errors`, optionally guarded by `when: backup_continue_on_failure | default(false) | bool`)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md Gaps G-03 evidence section (verbatim PLAY RECAP from scenario 3b proving only Garage tarball produced under opt-in mode, with root-cause analysis pointing at host-removal semantics)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md D-184 -- `any_errors_fatal` Jinja inversion. Explicit alternative considered: per-block `block`/`rescue` rejected as "4x the YAML for behavior `any_errors_fatal` gives natively." THIS PLAN REVERSES D-184's rejection because field evidence shows `any_errors_fatal` alone does not deliver the contract on single-host inventories. The 4x YAML cost is real but unavoidable. Document this reversal in the new comment block citing G-03.
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-REVIEW.md WR-01 (same finding from the review channel; reinforces the fix-plan)
    - roles/garage/tasks/backup.yml (verify per-role tasks/backup.yml already has its own block/rescue/always for the docker stop/tar/restart sequence -- the new orchestrator-level block/rescue is ADDITIVE; the per-role block is for "always-restart-container," the new orchestrator block is for "always-clear-host-errors-when-opt-in")
  </read_first>
  <action>
    Edit `playbooks/backup_docker.yml` to wrap each of the 4 per-role `ansible.builtin.include_role` tasks (currently at lines 132-140, 142-150, 152-160, 162-170) in a `block:` with a `rescue:` that calls `ansible.builtin.meta: clear_host_errors`, guarded by `when: backup_continue_on_failure | default(false) | bool`.

    Sequence of edits (top to bottom in the file):

    1. **PRESERVE line 76** -- the existing `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` is UNCHANGED. The G-03 fix is COMPLEMENTARY to the inversion expression, not a replacement.

    2. **PRESERVE the comment block at lines 119-130** that documents dynamic-include_role tag resolution -- this comment is the source of truth for why the inner include_role MUST keep its own `tags:` field even after the block-level tags are added. If anything, you may APPEND to this comment block citing G-03 closure as a concrete consequence; do not remove or rewrite it.

    3. **ADD a comment block** immediately before the `tasks:` keyword (currently at line 131) explaining the G-03 fix-plan: cite G-03 from `14-HUMAN-UAT.md`, document the host-removal semantics of Ansible (a failed host is removed from the active set independently of `any_errors_fatal`), reference CONTEXT.md D-184's original rejection of block/rescue ("4x the YAML for behavior `any_errors_fatal` gives natively") and explain why field evidence REVERSED that decision, name `meta: clear_host_errors` as the primitive that restores the host. This comment is the audit trail for future readers.

    4. **REPLACE the 4 existing include_role tasks** with 4 block/rescue wrappers. For each role (garage, prometheus, grafana, alertmanager) -- in that order, preserving forward-deploy ordering:

       Block-level `name:` field cites G-03 explicitly (e.g., `name: Garage backup (G-03: block/rescue allows continue-on-failure)`).
       Block-level `tags:` field is `[<role>, backup]` -- ADDED at the block level to keep the role-body visible under `--tags`.
       Block contents: ONE `ansible.builtin.include_role` task with the existing `name:` field (e.g., `Invoke garage backup`), `name: <role>`, `tasks_from: backup`, `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }`, **AND `tags: [<role>, backup]` retained on the include_role itself (MANDATORY -- do NOT remove the include_role-level tags when adding block-level tags).** The include-task tag list is what `--tags backup` and `--list-tasks --tags backup` actually filter on for dynamic include_role; removing it would break tag selection at execute-time (the existing comment at lines 119-130 is the authoritative source on this).
       Rescue contents: ONE `ansible.builtin.meta: clear_host_errors` task with a `name:` field citing G-03 (e.g., `name: <role> backup failed -- clear host errors so subsequent role backups still run (G-03; opt-in only)`) and a `when: backup_continue_on_failure | default(false) | bool` guard.

    5. **DO NOT change** the file header docstring (lines 1-62) -- it already documents the `any_errors_fatal` knob and the bail-out contract; a brief addendum after the existing "Bail-out vs continue-on-failure (D-184)" block citing G-03 closure is OK but not required (the inline comment from step 3 is the authoritative audit trail).

    6. **DO NOT change** the `vars:` block (lines 78-81), the `pre_tasks:` (banner at 89-97, timestamp commands at 104-117), the `any_errors_fatal:` expression (line 76), or any other surrounding structure.

    Constraints:
    - English-only.
    - Each block `name:` field cites G-03 explicitly.
    - Each rescue `name:` field cites G-03 explicitly.
    - The rescue's `when:` guard is the EXACT expression `backup_continue_on_failure | default(false) | bool` (matches the line-76 expression's idiom).
    - Forward-deploy role ordering preserved: garage -> prometheus -> grafana -> alertmanager.
    - File header docstring change (if any) does NOT remove the existing D-184 explanation -- only ADDS the G-03 closure note.
    - **The inner include_role MUST retain `tags: [<role>, backup]`. This is non-negotiable per the existing comment at lines 119-130. Removing the inner tags will silently break `--tags backup` on dynamic include_role at execute-time.**
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=playbooks/backup_docker.yml
        test -s "$F"

        # Syntax-check passes
        ansible-playbook --syntax-check -i inventory/example-homelab "$F"

        # NEW (W-4 mitigation): --list-tasks --tags backup must enumerate exactly the 4 role include_role
        # invocations. This catches tag-leakage at execute-time, BEFORE the leviathan re-UAT runs.
        # We assert the 4 expected include_role task names appear in the output (substring tokens).
        LIST_OUT=$(ansible-playbook --list-tasks --tags backup -i inventory/example-homelab "$F" 2>&1)
        echo "$LIST_OUT" | grep -q "Invoke garage backup"
        echo "$LIST_OUT" | grep -q "Invoke prometheus backup"
        echo "$LIST_OUT" | grep -q "Invoke grafana backup"
        echo "$LIST_OUT" | grep -q "Invoke alertmanager backup"
        # And no unexpected role-backup name appears (tag scope is correct)
        # (We do not assert "exactly 4" because pre_tasks banner with tags: always shows in --list-tasks; we
        #  assert the 4 role include_role tasks are present, which is the W-4 contract.)

        # Validate the block/rescue structure via YAML round-trip
        python3 -c "
import yaml
with open(\"$F\") as fh:
    docs = list(yaml.safe_load_all(fh))
play = docs[0][0]
# Preserve line-76 any_errors_fatal expression
aef = play.get(\"any_errors_fatal\")
assert aef is not None, \"any_errors_fatal removed -- must be preserved\"
assert \"backup_continue_on_failure\" in str(aef), f\"any_errors_fatal must reference backup_continue_on_failure, got {aef!r}\"
tasks = play.get(\"tasks\", [])
# Each of the 4 stateful roles must appear as a block with a rescue
expected_roles = [\"garage\", \"prometheus\", \"grafana\", \"alertmanager\"]
found_blocks = []
for t in tasks:
    blk = t.get(\"block\")
    if not blk:
        continue
    role = None
    for inner in blk:
        ir = inner.get(\"ansible.builtin.include_role\") or inner.get(\"include_role\")
        if ir and ir.get(\"name\") in expected_roles and ir.get(\"tasks_from\") == \"backup\":
            role = ir[\"name\"]
            break
    if role is None:
        continue
    found_blocks.append((role, t))
roles_found = [r for r, _ in found_blocks]
assert roles_found == expected_roles, f\"expected blocks in order {expected_roles}, got {roles_found}\"
# Each block must have a rescue with meta: clear_host_errors guarded by backup_continue_on_failure
for role, blk_task in found_blocks:
    rescue = blk_task.get(\"rescue\")
    assert rescue is not None and len(rescue) >= 1, f\"{role} block missing rescue\"
    rescue_task = rescue[0]
    meta_val = rescue_task.get(\"ansible.builtin.meta\") or rescue_task.get(\"meta\")
    assert meta_val == \"clear_host_errors\", f\"{role} rescue first task must be meta: clear_host_errors, got {meta_val!r}\"
    when_val = rescue_task.get(\"when\")
    assert when_val is not None and \"backup_continue_on_failure\" in str(when_val), f\"{role} rescue must be guarded by backup_continue_on_failure, got {when_val!r}\"
    # Block-level tags
    blk_tags = set(blk_task.get(\"tags\") or [])
    assert role in blk_tags, f\"{role} block tags must include {role!r}, got {blk_tags}\"
    assert \"backup\" in blk_tags, f\"{role} block tags must include backup, got {blk_tags}\"
    # CRITICAL W-4 ASSERTION: inner include_role MUST retain its own tags [<role>, backup]
    inner_ir_task = None
    for inner in blk_task[\"block\"]:
        ir = inner.get(\"ansible.builtin.include_role\") or inner.get(\"include_role\")
        if ir and ir.get(\"name\") == role:
            inner_ir_task = inner
            break
    assert inner_ir_task is not None, f\"{role}: inner include_role not found\"
    inner_tags = set(inner_ir_task.get(\"tags\") or [])
    assert role in inner_tags, f\"W-4: {role} include_role MUST retain its own tag {role!r} (got {inner_tags}). Per the existing comment at lines 119-130, dynamic include_role resolves tags at the include-task level BEFORE descending; removing the inner tag silently breaks --tags backup at execute-time.\"
    assert \"backup\" in inner_tags, f\"W-4: {role} include_role MUST retain its own tag backup (got {inner_tags}). See comment at lines 119-130.\"
print(\"PASS: G-03 fix structure correct -- 4 block/rescue wrappers with meta: clear_host_errors guarded by backup_continue_on_failure AND inner include_role retains its tags (W-4)\")
"

        # G-03 audit reference present
        grep -q "G-03" "$F"
        grep -q "clear_host_errors" "$F"
        # backup_continue_on_failure guard present in rescue
        grep -q "when: backup_continue_on_failure" "$F"

        # Default-mode invariants still present
        grep -q "any_errors_fatal:" "$F"

        # The 4 role include_role calls still in forward-deploy order via grep order check
        python3 -c "
import re
content = open(\"$F\").read()
roles = []
for m in re.finditer(r\"name:\\s*(garage|prometheus|grafana|alertmanager)\\b\", content):
    if m.group(1) not in roles:
        roles.append(m.group(1))
assert roles[:4] == [\"garage\", \"prometheus\", \"grafana\", \"alertmanager\"], f\"forward-deploy order broken: {roles[:4]}\"
"

        echo "PASS: 14-06 G-03 fix landed in backup_docker.yml (block/rescue + W-4 tag retention enforced)"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - `playbooks/backup_docker.yml` exists, non-empty, passes `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml`.
    - `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` enumerates all 4 include_role invocations by their `Invoke <role> backup` names (W-4 mitigation -- catches tag-leakage at execute-time).
    - Line-76 `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` is PRESERVED (not removed, not modified -- the Jinja expression on the play key is unchanged).
    - The `tasks:` block contains exactly 4 `block:` wrappers, in forward-deploy role order: garage -> prometheus -> grafana -> alertmanager.
    - Each block wraps exactly one `ansible.builtin.include_role` task whose `name:` matches the role (`garage` / `prometheus` / `grafana` / `alertmanager`) and `tasks_from:` is `backup`.
    - Each include_role inside its block still passes `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }`.
    - **CRITICAL (W-4):** Each include_role inside its block MUST retain its own `tags: [<role>, backup]` field (NOT removed when block-level tags were added). The YAML-round-trip assertion in the verify block enforces this -- removing the inner tags will fail the verify gate.
    - Block-level tags include both `<role>` and `backup` for each role.
    - Each block has a `rescue:` whose FIRST task is `ansible.builtin.meta: clear_host_errors`.
    - Each rescue task carries the EXACT `when:` guard `backup_continue_on_failure | default(false) | bool` (or `backup_continue_on_failure|default(false)|bool` -- whitespace tolerance OK; the underlying expression must reference `backup_continue_on_failure` and `default(false)` and `bool`).
    - The phrase `G-03` appears in the file (audit trail to `14-HUMAN-UAT.md`).
    - The string `clear_host_errors` appears at least once (in fact, exactly 4 times -- once per role rescue).
    - Existing pre_tasks (banner + timestamp set_fact) and `vars:` block are unchanged.
    - The existing tag-resolution comment block (lines 119-130 in pre-fix numbering) is preserved (may be appended to but not deleted).
  </acceptance_criteria>
  <done>
    `playbooks/backup_docker.yml` now wraps each per-role `include_role` in a `block:` with a `rescue:` that calls `meta: clear_host_errors` guarded by `when: backup_continue_on_failure | default(false) | bool`. The inner include_role retains its `tags: [<role>, backup]` field so `--tags backup` continues to enumerate all 4 invocations (W-4 mitigation -- verified by `--list-tasks --tags backup` at execute-time). Default mode (default `backup_continue_on_failure=false`) behavior is identical to pre-fix (UAT scenario 3a still passes); opt-in mode (`backup_continue_on_failure=true`) now actually keeps the host in the active set across role failures, so the remaining 3 roles' include_role calls run instead of being silently skipped. Plan 14-07 (re-UAT) is the empirical proof that SC5 flips from PARTIAL to VERIFIED and that scenario 3a (default bail-out) remains unaffected (no regression).
  </done>
</task>

</tasks>

<verification>
- Task 1 verification is fully automated: `ansible-playbook --syntax-check` exit 0, `ansible-playbook --list-tasks --tags backup` enumerates all 4 include_role invocations (W-4 mitigation), Python YAML round-trip validates the exact block/rescue/meta:clear_host_errors structure with the `when:` guard AND asserts the inner include_role tag retention, grep gates confirm the G-03 audit reference and the line-76 invariant are present.
- Empirical proof of SC5 closure (UAT scenario 3b passes) and no regression on scenario 3a (default bail-out) is Plan 14-07's live re-UAT on leviathan. This plan is structurally complete when Task 1 acceptance criteria all pass.
</verification>

<success_criteria>
- SC5 (ROADMAP.md Phase 14 #5) prerequisites in place: `backup_docker.yml` is structurally capable of running all 4 roles past a Prometheus failure under opt-in mode. The remaining proof is empirical (Plan 14-07).
- OPS-V13-02 prerequisites in place: opt-in `backup_continue_on_failure=true` opt-in contract is now actually deliverable on the inventory shape v1.3.0 targets.
- G-03 closure prerequisites in place: the missing `meta: clear_host_errors` rescue exists in the correct position with the correct `when:` guard for all 4 per-role include_role calls.
- W-4 mitigation in place: `--list-tasks --tags backup` empirically enumerates all 4 include_role invocations, proving the inner include_role tag retention is correct at execute-time.
- Default-mode invariant preserved: `backup_continue_on_failure=false` (default) still bails out on first role failure (`any_errors_fatal` expression on line 76 unchanged; rescue is `when:`-skipped under default mode).
- Tag UX preserved: `--tags garage`, `--tags backup` cross-cutting, and `--tags <stateless-role>` (empty 0-task play) all retain their pre-fix semantics.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator-supplied `backup_continue_on_failure=true` extra-var -> rescue `when:` guard | The guard is evaluated server-side; operator cannot bypass it. If the operator does NOT supply the flag, the rescue is skipped and default-mode (bail-out) holds. |
| `meta: clear_host_errors` privilege scope | This is a play-control primitive; it does not run shell or modify host state. No additional capabilities required. |
| Per-role tasks/backup.yml block/rescue/always (existing Phase 13 contract) -> orchestrator-level block/rescue (this fix) | The per-role block/rescue/always restarts the container even on tar failure. The orchestrator-level block/rescue handles the host-removal semantic. These are orthogonal concerns; the fix does not disturb the per-role guarantee. |
| Block-level tags vs include-task-level tags for dynamic include_role | Dynamic include_role resolves tags at the include-task level BEFORE descending into the role body (see comment at lines 119-130 of pre-fix backup_docker.yml). Block-level tags propagate down to inner tasks for inheritance but cannot substitute for the include-task tag list when `--tags <name>` is the selection mechanism. The W-4 mitigation enforces that the inner include_role retains its own `tags:` field. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-G03-01 | Tampering | Operator sets `backup_continue_on_failure=true` and a buggy role consumes excessive resources mid-failure | accept | The rescue only clears host errors; it does not re-invoke the failed task. A buggy role still fails fast on its first task. The opt-in contract is "attempt all 4 roles," not "infinite retry." |
| T-14-G03-02 | Denial of Service | Multiple consecutive role failures under opt-in mode -> PLAY RECAP shows `failed=N` for N up to 4 | accept | This is the documented contract -- failures are aggregated in PLAY RECAP. Operator addresses each failure individually. |
| T-14-G03-03 | Information Disclosure | Rescue task fires but does not change host state -- no new sensitive surface exposed | n/a | `meta: clear_host_errors` does not log secrets or modify files. |
| T-14-G03-04 | Repudiation | Default-mode regression: rescue accidentally fires under default mode and silently swallows a failure that should have aborted | mitigate | The `when: backup_continue_on_failure | default(false) | bool` guard prevents this. Acceptance criteria assert the guard expression verbatim. UAT scenario 3a (re-run in Plan 14-07) empirically confirms default-mode bail-out is unchanged. |
| T-14-G03-05 | Tampering | Rescue task tags inherit from block -- under `--tags garage` only the garage block's rescue fires on garage failure; other roles' rescues never fire because their blocks are skipped by the tag filter | accept | This is the correct per-role isolation. Cross-cutting `--tags backup` covers all 4 blocks. |
| T-14-G03-06 | Tampering | (W-4 threat:) Inner include_role tags are accidentally removed when block-level tags are added; `--tags backup` silently skips one or more roles at run time on leviathan | mitigate | `--list-tasks --tags backup` execute-time canary in the verify block enumerates all 4 include_role invocations. Removing inner tags fails the verify gate BEFORE the leviathan re-UAT runs. YAML-round-trip set-equality assertion is the deterministic structural enforcement. |
</threat_model>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-06-SUMMARY.md` when done. The SUMMARY captures: the 4 block/rescue wrappers inserted, the exact `when:` guard expression on each rescue, confirmation that line-76 `any_errors_fatal` is preserved, the W-4 mitigation (inner include_role tag retention + the `--list-tasks --tags backup` execute-time canary), and the syntax-check exit code. Reference G-03 from 14-HUMAN-UAT.md so future readers see the gap-closure audit trail.
</output>
</content>
</invoke>