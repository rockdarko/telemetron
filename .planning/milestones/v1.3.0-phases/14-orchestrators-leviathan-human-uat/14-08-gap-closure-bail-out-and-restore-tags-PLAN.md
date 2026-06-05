---
phase: 14-orchestrators-leviathan-human-uat
plan: "08"
type: execute
wave: 1
depends_on: []
files_modified:
  - playbooks/backup_docker.yml
  - playbooks/restore_docker.yml
autonomous: true
gap_closure: true
requirements:
  - BACKUP-V13-05
  - OPS-V13-02
  - RESTORE-V13-05
  - UAT-V13-01
tags: [gap-closure, G-03-addendum, G-04, ansible, backup, restore]

must_haves:
  truths:
    - "Under default mode (backup_continue_on_failure unset or false), the first stateful-role backup failure aborts backup_docker.yml -- subsequent role include_role calls do NOT run (G-03-addendum closure: rescue re-raises via explicit ansible.builtin.fail when the opt-in knob is off; any_errors_fatal then aborts the play)."
    - "Under opt-in mode (backup_continue_on_failure=true), the first failure does NOT abort -- subsequent role include_role calls still run (G-03 opt-in invariant from 14-06 preserved; the new fail task is when:-skipped, meta:clear_host_errors still fires)."
    - "When restore_docker.yml is invoked with `--tags restore`, the 3 writer-rerender include_role calls (loki, tempo, mimir) propagate the [garage, restore] tag list to the role body via `apply:`, so the inner role-body tasks (config render + handler chain) are NOT skipped (G-04 closure)."
    - "`ansible-playbook --syntax-check` exits 0 for both edited playbooks (no structural regression)."
    - "`ansible-playbook --list-tasks --tags backup` still enumerates all 4 `Invoke <role> backup` lines from backup_docker.yml (W-4 invariant from 14-06 preserved -- the new fail task is in the rescue block, not the main block, so it does NOT appear under --tags backup at include-task scope)."
    - "`ansible-playbook --list-tasks --tags restore` now enumerates the 3 writer-rerender include_role lines AND descendant role-body tasks from loki/tempo/mimir (G-04 empirical canary -- without `apply:`, descendants are filtered out)."
  artifacts:
    - path: "playbooks/backup_docker.yml"
      provides: "4 rescue blocks each carry an `ansible.builtin.fail` task (FIRST in the rescue, guarded by `when: not (backup_continue_on_failure | default(false) | bool)`) ahead of the existing `meta: clear_host_errors` task"
      contains: "G-03-addendum"
    - path: "playbooks/restore_docker.yml"
      provides: "3 writer-rerender include_role invocations (loki/tempo/mimir tasks_from=main) carry an `apply: tags: [garage, restore]` block in addition to their existing top-level `tags: [garage, restore]` field"
      contains: "G-04"
  key_links:
    - from: "playbooks/backup_docker.yml rescue blocks (G-03-addendum)"
      to: "play-level `any_errors_fatal: true` (line 106)"
      via: "explicit ansible.builtin.fail re-raises under default mode so Ansible increments the play-level failure counter; opt-in mode skips the fail and falls through to meta:clear_host_errors as before"
      pattern: "when: not \\(backup_continue_on_failure \\| default\\(false\\) \\| bool\\)"
    - from: "playbooks/restore_docker.yml writer-rerender include_role (G-04)"
      to: "loki/tempo/mimir role-body tasks under --tags restore"
      via: "Ansible `apply: tags:` keyword propagates the tag list to all tasks loaded by the dynamic include, making them selectable under --tags restore filtering"
      pattern: "apply:\\s*\\n\\s*tags:\\s*\\[garage,\\s*restore\\]"
---

<objective>
Close the two open gaps from the 14-07 round-2 leviathan UAT (recorded in `.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md`) with the minimum structural code changes: a re-raise task in each backup rescue block (G-03-addendum), and tag propagation on the 3 writer-rerender include_role calls in the restore orchestrator (G-04).

Purpose:
- G-03-addendum: Restore the default-mode bail-out contract advertised by the D-186 PLAY-start banner ("first role failure will abort the playbook"). The 14-06 block/rescue + meta:clear_host_errors mechanism delivered the opt-in contract (3 of 4 tarballs under backup_continue_on_failure=true) but introduced a regression where the rescue absorbs the failure even under default mode (rescued=1 failed=0 instead of failed=1). Adding an explicit re-fail in each rescue (skipped under opt-in via `when:`) restores `failed=1`, which `any_errors_fatal: true` then converts into the play-level abort the banner promises.
- G-04: Make `--tags restore` cross-cutting actually re-render writer configs after Garage restore. The dynamic include_role calls inserted by Plan 14-05 are correctly tagged at the include-task level (so they ARE selected under --tags restore), but Ansible applies the same tag filter to descendant role-body tasks loaded by the include -- and `loki/tempo/mimir/tasks/main.yml` body tasks do not carry [restore]. The `apply: tags:` keyword propagates the include-task tag list into the role body so the body tasks become selectable.

Output:
- Edited `playbooks/backup_docker.yml`: 4 new `ansible.builtin.fail` tasks (one per rescue block: garage, prometheus, grafana, alertmanager).
- Edited `playbooks/restore_docker.yml`: 3 new `apply:` blocks (one per writer-rerender include_role: loki, tempo, mimir).
- Approximately 30 lines of YAML across 2 files. No new files. No role-file edits. No handler edits.

Behavioral correctness is structurally verifiable here (syntax-check + YAML round-trip + --list-tasks enumeration). End-to-end behavioral proof (PLAY RECAP `failed=1` under default-mode 3a; no `Forbidden: No such key:` under `--tags restore`) is the empirical gate of the follow-up Plan 14-09 round-3 leviathan re-UAT.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-06-SUMMARY.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-05-SUMMARY.md
@playbooks/backup_docker.yml
@playbooks/restore_docker.yml
@./CLAUDE.md

<interfaces>
<!-- The two files this plan edits -- key structural cues extracted so the executor needs ZERO codebase exploration. -->

From playbooks/backup_docker.yml (post-14-06 state):
  - Play-level `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` at line 106. PRESERVED.
  - Play-level `vars: { backup_continue_on_failure: false }` at lines 108-111. PRESERVED.
  - Four block/rescue wrappers in `tasks:` (lines 178-252) in forward-deploy order:
      garage (178-195), prometheus (197-214), grafana (216-233), alertmanager (235-252).
  - Each block's outer task has `tags: [<role>, backup]` -- PRESERVED, do NOT touch.
  - Each block's `block:` contains exactly one task: `Invoke <role> backup` (an `ansible.builtin.include_role` with `tasks_from: backup`, `vars: backup_timestamp_override: ...`, and `tags: [<role>, backup]`). PRESERVED.
  - Each block's `rescue:` currently contains EXACTLY ONE task:
        - name: <Role> backup failed -- clear host errors so subsequent role backups still run (G-03; opt-in only)
          ansible.builtin.meta: clear_host_errors
          when: backup_continue_on_failure | default(false) | bool
    (no tags field -- inherits from the enclosing block).

  G-03-addendum fix shape: PREPEND a new task in each rescue, BEFORE the existing meta:clear_host_errors task. The new task is an `ansible.builtin.fail` with an inverted `when:` guard so default mode raises and opt-in mode skips. The existing clear_host_errors task is UNTOUCHED (same name, same module, same when-guard).

From playbooks/restore_docker.yml (post-14-05 state):
  - Play-level `any_errors_fatal: true` (HARDCODED at line 75). PRESERVED.
  - Orchestrator confirm-gate `ansible.builtin.fail` at lines 96-105 with `tags: [always]`. PRESERVED.
  - Three writer-rerender include_role tasks at lines 220-242, each shaped:
        - name: Re-render <Role> config from restored Garage s3-credentials (G-01 fix; D-183 reversed)
          ansible.builtin.include_role:
            name: <role>
            tasks_from: main
          tags:
            - garage
            - restore
  - Followed by `- name: Flush restart handlers now...` (lines 244-245) -- PRESERVED, unchanged.

  G-04 fix shape: insert an `apply:` key INSIDE the `ansible.builtin.include_role:` mapping (sibling of `name:` and `tasks_from:`), valued as a mapping `tags: [garage, restore]`. The outer task `tags:` list is UNTOUCHED.

From roles/loki/tasks/main.yml, roles/tempo/tasks/main.yml, roles/mimir/tasks/main.yml (reference -- DO NOT EDIT in this plan):
  - The body tasks (e.g. `Render Loki config`) carry per-role tags (e.g. [loki]) but NOT [restore]. That is by design; the `apply:` injection in the orchestrator is the canonical Ansible mechanism to propagate cross-cutting tags into a dynamic include's body without modifying the role.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Close G-03-addendum -- add re-fail task to each backup rescue block (default-mode bail-out restoration)</name>

  <files>playbooks/backup_docker.yml</files>

  <read_first>
    - playbooks/backup_docker.yml (FULL file -- understand the 4 block/rescue wrappers and the existing rescue task before editing)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md (G-03-addendum gap: the `truth:` and `reason:` fields are the authoritative gap description)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md (scenario 3a regression evidence + the proposed fix shape from "## New Gaps -> G-03-addendum -> Fix")
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-06-SUMMARY.md (the original G-03 opt-in closure that introduced the block/rescue structure -- the new fail task must NOT regress that closure)
    - ./CLAUDE.md (English-only `name:` strings, locked tech stack -- Ansible)
  </read_first>

  <action>
    Edit playbooks/backup_docker.yml. For EACH of the 4 rescue blocks (under the garage, prometheus, grafana, and alertmanager wrapper tasks), PREPEND a new `ansible.builtin.fail` task as the FIRST entry in the `rescue:` list, BEFORE the existing `ansible.builtin.meta: clear_host_errors` task. Do NOT remove or reorder the existing clear_host_errors task -- it remains the second (and last) task in each rescue. Do NOT touch any other section of the playbook (pre_tasks, vars, any_errors_fatal, the `block:` content, or the outer block tags).

    The new task has these EXACT properties:
      - name: "<Role> backup failed -- re-raise under default mode (G-03-addendum)"
        ansible.builtin.fail:
          msg: "<role> backup failed and backup_continue_on_failure is false -- aborting play (default-mode bail-out; set backup_continue_on_failure=true to opt into continue mode)"
        when: not (backup_continue_on_failure | default(false) | bool)

    Per-role substitutions (case-sensitive):
      - garage block (currently lines 192-195): name="Garage backup failed -- re-raise under default mode (G-03-addendum)"; msg starts with "garage backup failed and ..."
      - prometheus block (currently lines 211-214): name="Prometheus backup failed -- re-raise under default mode (G-03-addendum)"; msg starts with "prometheus backup failed and ..."
      - grafana block (currently lines 230-233): name="Grafana backup failed -- re-raise under default mode (G-03-addendum)"; msg starts with "grafana backup failed and ..."
      - alertmanager block (currently lines 249-252): name="Alertmanager backup failed -- re-raise under default mode (G-03-addendum)"; msg starts with "alertmanager backup failed and ..."

    Mechanics:
      - The new task carries NO `tags:` field (it inherits the outer block's `tags: [<role>, backup]` list, mirroring how the existing clear_host_errors task already works).
      - The `when:` guard is the EXACT logical negation of the existing clear_host_errors `when:` guard. Under default mode (`backup_continue_on_failure` unset or false) -> the new fail task RUNS, raises, Ansible increments the play-level failure counter, `any_errors_fatal: true` (computed at line 106) aborts the play before the next role's include_role can fire. Under opt-in mode (`backup_continue_on_failure=true`) -> the new fail task is when:-skipped, control falls through to the existing meta:clear_host_errors which fires as before, the host returns to the active set, and the next role's include_role runs -- preserving the 14-06 G-03 opt-in contract.

    Also add a short comment above the new fail task in EACH rescue (a single `# G-03-addendum:` line) so a future reader sees the rationale inline. Example for the garage rescue (the other 3 follow the same pattern with their role names substituted):

      rescue:
        # G-03-addendum: re-raise under default mode so any_errors_fatal aborts the play (the
        # rescue otherwise absorbs the failure -- rescued=1 failed=0 -- which makes the
        # banner's "first role failure will abort the playbook" claim untrue).
        - name: Garage backup failed -- re-raise under default mode (G-03-addendum)
          ansible.builtin.fail:
            msg: "garage backup failed and backup_continue_on_failure is false -- aborting play (default-mode bail-out; set backup_continue_on_failure=true to opt into continue mode)"
          when: not (backup_continue_on_failure | default(false) | bool)
        - name: Garage backup failed -- clear host errors so subsequent role backups still run (G-03; opt-in only)
          ansible.builtin.meta: clear_host_errors
          when: backup_continue_on_failure | default(false) | bool

    Anti-patterns to AVOID (these will break the contract or the verification):
      - Do NOT add `tags: [<role>, backup]` to the new fail task explicitly -- it would still inherit from the block, but adding the tags explicitly causes the task to appear in `--list-tasks --tags backup` output and would regress the 14-06 W-4 invariant (rescue tasks must not surface at include-task scope under --tags backup).
      - Do NOT change the existing clear_host_errors task `when:` guard. It stays `backup_continue_on_failure | default(false) | bool` -- it is the inverse of the new fail-task guard; both guards together are mutually exclusive.
      - Do NOT swap the order (clear_host_errors first, then fail). The fail MUST be first so that under default mode the play aborts at the fail before reaching clear_host_errors; under opt-in mode the fail when:-skips and clear_host_errors handles the recovery.
      - Do NOT touch any `vars:`, `pre_tasks:`, `any_errors_fatal`, the play-level header, or the `block:` content of any of the 4 wrappers. The only change is INSIDE each `rescue:` list.
      - No French in `name:` or `msg:` strings (CLAUDE.md English-only constraint).
  </action>

  <verify>
    <automated>
ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml &amp;&amp;
python3 -c "
import yaml, sys
with open('playbooks/backup_docker.yml') as f:
    data = yaml.safe_load(f)
assert isinstance(data, list) and len(data) == 1, 'expected one play'
play = data[0]
tasks = play.get('tasks', [])
assert len(tasks) == 4, f'expected 4 wrapper tasks, got {len(tasks)}'
expected_roles = ['garage', 'prometheus', 'grafana', 'alertmanager']
expected_role_titles = ['Garage', 'Prometheus', 'Grafana', 'Alertmanager']
for i, (t, role, title) in enumerate(zip(tasks, expected_roles, expected_role_titles)):
    rescue = t.get('rescue', [])
    assert len(rescue) == 2, f'rescue {i} ({role}): expected exactly 2 tasks, got {len(rescue)}'
    fail_task, clear_task = rescue[0], rescue[1]
    assert 'ansible.builtin.fail' in fail_task, f'rescue {i} ({role}): first task must be ansible.builtin.fail'
    assert 'msg' in fail_task['ansible.builtin.fail'], f'rescue {i} ({role}): fail task missing msg'
    assert role in fail_task['ansible.builtin.fail']['msg'], f'rescue {i} ({role}): msg must name role'
    assert fail_task.get('when', '').strip() == 'not (backup_continue_on_failure | default(false) | bool)', f'rescue {i} ({role}): fail task when-guard wrong: {fail_task.get(chr(34)+chr(119)+chr(104)+chr(101)+chr(110)+chr(34))!r}'
    assert 'G-03-addendum' in fail_task.get('name', ''), f'rescue {i} ({role}): fail task name must cite G-03-addendum'
    assert title in fail_task.get('name', ''), f'rescue {i} ({role}): fail task name must start with {title}'
    assert 'tags' not in fail_task, f'rescue {i} ({role}): fail task must NOT have explicit tags (inherits from block)'
    assert 'ansible.builtin.meta' in clear_task and clear_task['ansible.builtin.meta'] == 'clear_host_errors', f'rescue {i} ({role}): second task must be meta:clear_host_errors'
    assert clear_task.get('when', '').strip() == 'backup_continue_on_failure | default(false) | bool', f'rescue {i} ({role}): clear_host_errors when-guard regressed'
print('OK: 4 rescue blocks each have [fail, clear_host_errors] with correct guards')
" &amp;&amp;
grep -c 'G-03-addendum' playbooks/backup_docker.yml &amp;&amp;
test "$(grep -c 'G-03-addendum' playbooks/backup_docker.yml)" -ge 4 &amp;&amp;
ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml | grep -c 'Invoke .* backup' | grep -qE '^4$' &amp;&amp;
echo "OK: --list-tasks --tags backup still enumerates all 4 Invoke <role> backup lines (W-4 invariant preserved)"
    </automated>
  </verify>

  <acceptance_criteria>
    - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0.
    - YAML round-trip Python assertion passes:
        * Play has exactly 4 tasks in `tasks:` (one wrapper per stateful role).
        * Each wrapper's `rescue:` list has exactly 2 tasks in order: (1) `ansible.builtin.fail`, (2) `ansible.builtin.meta: clear_host_errors`.
        * Each fail task has `name:` containing "G-03-addendum" AND beginning with the role title (Garage/Prometheus/Grafana/Alertmanager), a non-empty `msg:` field that names the role (lowercase), `when: not (backup_continue_on_failure | default(false) | bool)`, and NO `tags:` field (inheritance only).
        * Each meta:clear_host_errors task still has `when: backup_continue_on_failure | default(false) | bool` (unchanged from 14-06).
    - The literal phrase `G-03-addendum` appears at least 4 times in playbooks/backup_docker.yml (one per rescue, ignoring optional comments).
    - `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` enumerates exactly 4 `Invoke <role> backup` lines (one per role) -- the 14-06 W-4 invariant.
    - No edits to any file other than playbooks/backup_docker.yml.
    - No French-language strings introduced.
  </acceptance_criteria>

  <done>
    playbooks/backup_docker.yml now has 4 rescue blocks, each containing [ansible.builtin.fail (when: NOT opt-in), ansible.builtin.meta:clear_host_errors (when: opt-in)] in that order. The two when-guards are mutually exclusive: default mode raises and aborts via any_errors_fatal; opt-in mode skips the fail and clears host errors as before. `ansible-playbook --syntax-check` passes; the W-4 `--list-tasks --tags backup` invariant still shows 4 Invoke <role> backup lines. G-03-addendum is structurally closed. (Behavioral confirmation -- PLAY RECAP `failed=1` under leviathan scenario 3a -- is Plan 14-09's gate.)
  </done>
</task>

<task type="auto">
  <name>Task 2: Close G-04 -- propagate [garage, restore] tags into writer-rerender role bodies via `apply:`</name>

  <files>playbooks/restore_docker.yml</files>

  <read_first>
    - playbooks/restore_docker.yml (FULL file -- understand the 3 writer-rerender include_role calls at lines 220-242 and the flush_handlers task that follows)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md (G-04 gap: the `truth:` and `reason:` fields are the authoritative gap description)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-07-SUMMARY.md (scenario 4d-restore FAIL evidence + the proposed fix shape from "## New Gaps -> G-04 -> Fix"; the included-but-empty subtask log block is the canonical symptom)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-05-SUMMARY.md (the G-01 closure that introduced these 3 include_role calls -- the existing top-level `tags: [garage, restore]` field must be preserved as-is; the new `apply:` is ADDITIVE)
    - roles/loki/tasks/main.yml (FIRST 30 LINES only -- confirm the body tasks do not carry [restore]; this confirms why `apply:` is required)
    - roles/tempo/tasks/main.yml (FIRST 30 LINES only -- same confirmation)
    - roles/mimir/tasks/main.yml (FIRST 30 LINES only -- same confirmation)
    - ./CLAUDE.md (English-only `name:` strings, Ansible-driven constraints)
  </read_first>

  <action>
    Edit playbooks/restore_docker.yml. For EACH of the 3 writer-rerender include_role tasks (loki at ~lines 220-226, tempo at ~lines 228-234, mimir at ~lines 236-242), add an `apply:` key INSIDE the `ansible.builtin.include_role:` mapping. The `apply:` value is a mapping with a single `tags:` key whose value is the YAML flow-style list `[garage, restore]`. The `apply:` key sits at the SAME indentation level as `name:` and `tasks_from:` within the include_role mapping.

    Do NOT remove or alter the existing top-level task `tags:` field (`tags: [garage, restore]` on each include_role) -- it remains as the include-task-scope selector. The new `apply:` block is the propagation mechanism into the role body and is ADDITIVE.

    Resulting shape for the loki entry (the tempo and mimir entries follow the same pattern with the role name substituted):

      - name: Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed; G-04 tag-propagation)
        ansible.builtin.include_role:
          name: loki
          tasks_from: main
          apply:
            tags:
              - garage
              - restore
        tags:
          - garage
          - restore

    Per-role substitutions (case-sensitive on the role name within the `name:` string):
      - loki entry: name string starts with "Re-render Loki config from restored ..."
      - tempo entry: name string starts with "Re-render Tempo config from restored ..."
      - mimir entry: name string starts with "Re-render Mimir config from restored ..."

    Also amend each of those 3 task `name:` strings to append "; G-04 tag-propagation" so the rationale is greppable in the file. The existing "(G-01 fix; D-183 reversed)" prefix from Plan 14-05 is preserved. Final name strings:
      - "Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed; G-04 tag-propagation)"
      - "Re-render Tempo config from restored Garage s3-credentials (G-01 fix; D-183 reversed; G-04 tag-propagation)"
      - "Re-render Mimir config from restored Garage s3-credentials (G-01 fix; D-183 reversed; G-04 tag-propagation)"

    Add a brief multi-line YAML comment ABOVE the loki include_role (so the rationale is documented once for the block of three) explaining the `apply:` mechanism. Example:

      # G-04 (14-VERIFICATION.md): dynamic `include_role` applies the parent task's
      # tag filter to descendant role-body tasks BEFORE inheritance. Without
      # `apply: tags: [garage, restore]`, an invocation with `--tags restore`
      # selects these include_role tasks but then skips every task loaded from
      # `roles/<writer>/tasks/main.yml` (none carry `restore`). The `apply:`
      # keyword propagates the listed tags onto each task loaded by the include,
      # making the writer config-render task selectable under `--tags restore`
      # so the config is re-rendered and the restart handler fires. The outer
      # task-level `tags: [garage, restore]` is preserved for include-task-scope
      # selection; the two are complementary, not redundant.

    Mechanics:
      - The `apply:` key is the canonical Ansible mechanism for propagating tags into a dynamic `include_role` body. Without it, Ansible only inspects the include-task-level `tags:` for selection AND then applies the SAME filter to the body, which means a role body task lacking the `restore` tag is skipped under `--tags restore`.
      - Do NOT add `[restore]` to any task tag inside `roles/loki/tasks/main.yml`, `roles/tempo/tasks/main.yml`, or `roles/mimir/tasks/main.yml`. The fix lives ONLY in the orchestrator. (Adding `[restore]` to render tasks in the role bodies would pollute the deploy-time tag surface; the orchestrator-side `apply:` is the surgical fix.)
      - Do NOT touch the `meta: flush_handlers` task at lines 244-245. Do NOT touch the writer-stop loop (lines 137-149), the writer-restart loop (lines 247-259), the healthy-poll (lines 265-285), the Garage restore include_role (lines 178-184), or any of the prometheus/grafana/alertmanager restore include_role calls (lines 290-312). The change surface is the 3 writer-rerender entries only.
      - No French in `name:` or comment strings (CLAUDE.md English-only constraint).
  </action>

  <verify>
    <automated>
ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml &amp;&amp;
python3 -c "
import yaml
with open('playbooks/restore_docker.yml') as f:
    data = yaml.safe_load(f)
play = data[0]
tasks = play.get('tasks', [])
# Find the 3 writer-rerender include_role tasks by name prefix
rerender = [t for t in tasks if 'include_role' in str(t.get('ansible.builtin.include_role', '')) or ('ansible.builtin.include_role' in t and isinstance(t['ansible.builtin.include_role'], dict) and t['ansible.builtin.include_role'].get('tasks_from') == 'main')]
# Filter to the writer-rerender names
writers = [t for t in rerender if t.get('name', '').startswith('Re-render ')]
assert len(writers) == 3, f'expected 3 writer-rerender include_role tasks, got {len(writers)}'
expected_roles = ['loki', 'tempo', 'mimir']
expected_titles = ['Loki', 'Tempo', 'Mimir']
for i, (t, role, title) in enumerate(zip(writers, expected_roles, expected_titles)):
    ir = t['ansible.builtin.include_role']
    assert ir.get('name') == role, f'writer {i}: expected name={role!r}, got {ir.get(chr(34)+chr(110)+chr(97)+chr(109)+chr(101)+chr(34))!r}'
    assert ir.get('tasks_from') == 'main', f'writer {i}: tasks_from must remain main'
    assert 'apply' in ir, f'writer {i} ({role}): include_role mapping missing apply: key'
    apply_block = ir['apply']
    assert isinstance(apply_block, dict), f'writer {i} ({role}): apply must be a mapping'
    apply_tags = apply_block.get('tags', [])
    assert set(apply_tags) == {'garage', 'restore'}, f'writer {i} ({role}): apply.tags must be {{garage, restore}}, got {apply_tags!r}'
    outer_tags = t.get('tags', [])
    assert set(outer_tags) == {'garage', 'restore'}, f'writer {i} ({role}): outer task tags must remain [garage, restore], got {outer_tags!r}'
    assert title in t.get('name', ''), f'writer {i} ({role}): name must reference {title}'
    assert 'G-04' in t.get('name', ''), f'writer {i} ({role}): name must cite G-04'
# Verify ordering: loki -> tempo -> mimir, then the flush_handlers meta task next
writer_indices = [tasks.index(w) for w in writers]
assert writer_indices == sorted(writer_indices), 'writer-rerender tasks must appear in source order'
assert writer_indices[0] < writer_indices[1] < writer_indices[2], 'order loki->tempo->mimir'
flush_idx = writer_indices[2] + 1
assert flush_idx < len(tasks), 'no task after mimir writer-rerender'
flush_task = tasks[flush_idx]
assert flush_task.get('ansible.builtin.meta') == 'flush_handlers', f'expected meta:flush_handlers immediately after mimir rerender, got {flush_task!r}'
print('OK: 3 writer-rerender include_role tasks have apply: tags: [garage, restore]; outer tags preserved; flush_handlers follows mimir')
" &amp;&amp;
grep -c 'G-04' playbooks/restore_docker.yml &amp;&amp;
test "$(grep -c 'G-04' playbooks/restore_docker.yml)" -ge 3 &amp;&amp;
LIST_OUTPUT=$(ansible-playbook --list-tasks --tags restore -i inventory/example-homelab playbooks/restore_docker.yml) &amp;&amp;
echo "$LIST_OUTPUT" | grep -c 'Re-render .* config from restored' | grep -qE '^3$' &amp;&amp;
(echo "$LIST_OUTPUT" | grep -qE '(Render Loki config|loki :)' &amp;&amp;
 echo "$LIST_OUTPUT" | grep -qE '(Render Tempo config|tempo :)' &amp;&amp;
 echo "$LIST_OUTPUT" | grep -qE '(Render Mimir config|mimir :)') &amp;&amp;
echo "OK: --list-tasks --tags restore enumerates the 3 writer-rerender lines AND descendant role-body tasks for loki/tempo/mimir (G-04 empirical canary)"
    </automated>
  </verify>

  <acceptance_criteria>
    - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` exits 0.
    - YAML round-trip Python assertion passes:
        * Exactly 3 tasks named `Re-render <Loki|Tempo|Mimir> config from restored ...` exist in `tasks:` in order loki -> tempo -> mimir.
        * Each is an `ansible.builtin.include_role` with `tasks_from: main` and an `apply:` block whose `tags:` list (as a Python set) equals `{garage, restore}`.
        * Each outer task `tags:` field (as a Python set) still equals `{garage, restore}` -- the existing top-level selector is preserved.
        * Each `name:` field contains the literal "G-04".
        * The very next task after the mimir rerender is `ansible.builtin.meta: flush_handlers` (unchanged).
    - The literal phrase `G-04` appears at least 3 times in playbooks/restore_docker.yml (once per rerender task name; the comment block above the loki entry adds extra occurrences but the threshold is the per-task name).
    - `ansible-playbook --list-tasks --tags restore -i inventory/example-homelab playbooks/restore_docker.yml`:
        * Lists all 3 `Re-render <Role> config from restored ...` lines.
        * Lists at least one descendant body task for each of loki, tempo, mimir (e.g. a "Render <Role> config" task surfaced under the include) -- this is the canary that proves tag propagation reaches the role body.
    - No edits to any file other than playbooks/restore_docker.yml. No edits to roles/loki, roles/tempo, roles/mimir.
    - No French-language strings introduced.
  </acceptance_criteria>

  <done>
    playbooks/restore_docker.yml's 3 writer-rerender include_role tasks now propagate `[garage, restore]` into their role bodies via `apply:`. The existing outer-task `tags: [garage, restore]` selector is preserved. `ansible-playbook --syntax-check` passes; `--list-tasks --tags restore` now enumerates not only the 3 include_role lines but also the descendant role-body tasks from each writer. G-04 is structurally closed. (Behavioral confirmation -- no `Forbidden: No such key:` and `failed=0` under leviathan scenario 4d-restore on a clean post-purge state -- is Plan 14-09's gate.)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator -> ansible control node | Operator supplies `--tags`, `--extra-vars backup_continue_on_failure`, and `--extra-vars backup_restore_confirm`. The orchestrator's safety contract relies on those untrusted inputs being honored by the play structure. |
| ansible control node -> leviathan (and other telemetron hosts) | Sequential `docker stop`/`docker start`, file-as-dir fault rendezvous, and tarball read/write paths. The two gap-closure edits do not introduce new cross-boundary traffic. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-08-01 | Tampering | playbooks/backup_docker.yml -- new fail task in each rescue could be mis-guarded (e.g. inverted condition) such that opt-in mode also aborts (regressing G-03 14-06 closure) or default mode silently continues (failing to close G-03-addendum) | mitigate | Mutually-exclusive when-guard pair (`not (knob)` on fail, `knob` on clear_host_errors). YAML round-trip Python assertion in Task 1 verifies BOTH guards on all 4 rescue blocks; `--list-tasks --tags backup` invariant confirms no regression to the 14-06 W-4 invariant. |
| T-14-08-02 | Denial-of-Service (against the operator's intent) | playbooks/restore_docker.yml -- omitting `apply:` on any one of the 3 writer-rerender include_role calls would leave that one writer crash-looping under --tags restore on a clean state (selective G-04 closure) | mitigate | YAML round-trip Python assertion in Task 2 iterates ALL 3 writer-rerender tasks and asserts the `apply.tags` set equals `{garage, restore}` for each. `--list-tasks --tags restore` enumeration asserts a descendant body task surfaces for each of loki, tempo, mimir. |
| T-14-08-03 | Information Disclosure | Neither edit changes log content, secret handling, or PII surfaces. `msg:` strings in the new fail tasks reference only the role name and the public knob name (`backup_continue_on_failure`). | accept | No secrets are interpolated into the new `msg:` strings; only Ansible Jinja already in the playbook's banner (which already names the same knob). Risk is low. |
| T-14-08-04 | Elevation of Privilege | Neither edit changes `become:` semantics. The new fail and apply blocks both run at the play scope already established (become: false at play header). | accept | No `become:` changes introduced. The rescue's existing meta:clear_host_errors and the include_role tasks already operate under the established privilege boundary. |
| T-14-08-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan (pure YAML edits on 2 existing files). Slopcheck not applicable. |
</threat_model>

<verification>
After both tasks complete, run the cross-task structural verification once at the playbook level:

1. Both playbooks syntax-check clean:
   - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0.
   - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` exits 0.

2. Tag UX invariants from prior phases still hold:
   - `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` shows exactly 4 `Invoke <role> backup` lines (W-4 from 14-06).
   - `ansible-playbook --list-tasks --tags garage -i inventory/example-homelab playbooks/backup_docker.yml` shows the garage block content (per-role selector unchanged).
   - `ansible-playbook --list-tasks --tags loki -i inventory/example-homelab playbooks/backup_docker.yml` produces an empty/zero-task selection (stateless-role tag unchanged from SC1).
   - `ansible-playbook --list-tasks --tags restore -i inventory/example-homelab playbooks/restore_docker.yml` now includes descendant body tasks under each of the 3 writer-rerender include_role calls (G-04 empirical canary).

3. The two gap citation strings appear at expected frequencies:
   - `grep -c 'G-03-addendum' playbooks/backup_docker.yml` returns at least 4 (one per rescue, plus the optional comments).
   - `grep -c 'G-04' playbooks/restore_docker.yml` returns at least 3 (one per writer-rerender task name, plus the optional comment block).

4. No edits leaked outside the two target files:
   - `git diff --name-only` lists exactly `playbooks/backup_docker.yml` and `playbooks/restore_docker.yml`.

Behavioral verification on leviathan (PLAY RECAP `failed=1` under default-mode 3a; PLAY RECAP `failed=0 rescued=1` under opt-in 3b unchanged; no `Forbidden: No such key:` and `failed=0` under `--tags restore` 4d-restore on a clean state) is OUT OF SCOPE for this plan and is the empirical gate of the follow-up Plan 14-09 round-3 leviathan re-UAT.
</verification>

<success_criteria>
- Both target playbooks pass `ansible-playbook --syntax-check`.
- YAML round-trip assertions in both tasks pass without `AssertionError`.
- `--list-tasks --tags backup` still enumerates exactly 4 `Invoke <role> backup` lines (W-4 invariant preserved).
- `--list-tasks --tags restore` now enumerates the 3 `Re-render <Role>` lines AND at least one descendant body task per writer (G-04 empirical canary).
- `G-03-addendum` literal appears in all 4 rescue blocks of `playbooks/backup_docker.yml`.
- `G-04` literal appears in all 3 writer-rerender task names of `playbooks/restore_docker.yml`.
- No file other than `playbooks/backup_docker.yml` and `playbooks/restore_docker.yml` is modified.
- No French-language artifacts introduced (CLAUDE.md English-only constraint).
</success_criteria>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-08-SUMMARY.md` when done. The summary MUST cite both G-03-addendum and G-04 in `decisions:` and include a short "Next" pointer to Plan 14-09 (round-3 leviathan re-UAT scenarios 3a + 4d-restore) as the behavioral closure gate.
</output>
