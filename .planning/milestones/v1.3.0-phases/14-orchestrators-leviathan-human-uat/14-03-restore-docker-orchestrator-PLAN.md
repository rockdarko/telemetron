---
phase: 14-orchestrators-leviathan-human-uat
plan: 03
type: execute
wave: 2
depends_on: []
files_modified:
  - playbooks/restore_docker.yml
autonomous: true
requirements:
  - RESTORE-V13-05
  - OPS-V13-01
  - OPS-V13-03

must_haves:
  truths:
    - "`playbooks/restore_docker.yml` exists and refuses to run without `--extra-vars backup_restore_confirm=true` -- the orchestrator-level `fail:` gate is tagged `[always]` so it fires on ANY invocation of restore_docker.yml regardless of `--tags` (this is the playbook's identity-level safety: the playbook NAME signals destructive intent, so the confirm flag is required for any restore_docker.yml invocation, including stateless-tag invocations). Per-role gate in each tasks/restore.yml (Phase 13) is the defence-in-depth layer for custom-playbook callers that bypass restore_docker.yml entirely."
    - "A D-187 `WARNING: irreversible --` PLAY-start banner (`tags: always`) is the second pre_task, with the verbatim 3-line message (headline + Target timestamp + Restore order)."
    - "Garage writers (Loki, Tempo, Mimir) are stopped sequentially BEFORE the Garage `include_role: tasks_from=restore` and restarted sequentially AFTER -- all tagged `[garage, restore]` (D-189 amended by SC4 reconciliation; see truth #4 for the tag rationale) so `--tags garage` runs the whole stop -> restore -> restart unit AND `--tags restore` cross-cutting also runs the bracketed unit."
    - "Per-role restore order matches backup order (forward, NOT reverse): garage -> prometheus -> grafana -> alertmanager."
    - "`any_errors_fatal: true` is HARDCODED at play level (D-185) -- no operator opt-in. Restore is destructive; partial restore is worse than no restore."
    - "`restore_docker.yml --tags <stateless-role> --extra-vars backup_restore_confirm=true` produces an empty 0-task play and exits 0 (D-188 amended by SC4 reconciliation: confirm flag is REQUIRED for ANY restore_docker.yml invocation including stateless-tag invocations, because the playbook's identity is destructive even when no tag selects any role). Without the confirm flag, ANY restore_docker.yml invocation fails at the orchestrator-level gate before tag-filtering, regardless of `--tags`."
    - "D-189 rationale preserved: writer-stop tag list is `[garage, restore]`, NOT `[loki]/[tempo]/[mimir]/[writers]/[always]` -- prevents `--tags loki/tempo/mimir/writers` from firing the writer-stop. The `[restore]` element is the cross-cutting tag SC4 requires; `[garage]` preserves the original `--tags garage` runs the whole bracketed unit semantic. `[restore]` is also the cross-cutting tag the orchestrator-level identity demands."
    - "`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` exits 0."
    - "`ansible-playbook --list-tasks --tags restore -i inventory/example-homelab playbooks/restore_docker.yml` enumerates exactly the 4 role include_role lines (garage, prometheus, grafana, alertmanager) plus the 4 writer-quiesce tasks (writer-stop loop, writer-stop poll, writer-restart loop, writer-restart poll) -- proving SC4 cross-cutting `--tags restore` covers the full destructive surface."
  artifacts:
    - path: "playbooks/restore_docker.yml"
      provides: "Confirm-gated restore orchestrator with writer-quiesce around Garage."
      min_lines: 130
      contains: "WARNING: irreversible --"
  key_links:
    - from: "playbooks/restore_docker.yml pre_task `fail:`"
      to: "OPS-V13-01 orchestrator-level confirm gate (per-role gate is the defence-in-depth layer per D-185)"
      via: "`when: not (backup_restore_confirm | default(false) | bool)` on a fail task tagged `[always]`"
      pattern: "ansible.builtin.fail"
    - from: "writer-stop loop `docker stop -t {{ backup_stop_timeout }} <container>`"
      to: "writer-stop poll `docker_container_info` until `State.Running == false`"
      via: "sequential `loop:` over [loki, tempo, mimir]"
      pattern: "loop:"
    - from: "writer-restart loop `docker start <container>`"
      to: "writer-restart poll `docker_container_info` until `State.Health.Status == 'healthy'`"
      via: "sequential `loop:` over [loki, tempo, mimir]"
      pattern: "State.Health.Status"
    - from: "writer-stop/restart loop `tags: [garage, restore]`"
      to: "D-189 amended contract: `--tags garage` runs the whole stop -> restore -> restart unit; `--tags restore` ALSO runs the bracketed unit (SC4 cross-cutting); `--tags loki/tempo/mimir/writers` matches nothing in the bracket (D-189 original rationale preserved)"
      via: "Ansible tag inheritance"
      pattern: "tags:\\s+-\\s+restore"
    - from: "Each include_role `tags: [<role>, restore]`"
      to: "SC4 cross-cutting `--tags restore` covers all 4 role include_role calls"
      via: "Ansible tag selection at include-task level (D-149 explicit-include precedent; dynamic include_role does not propagate inner tags up to the play-level tag resolver)"
      pattern: "tags:\\s+-\\s+restore"
---

<objective>
Ship `playbooks/restore_docker.yml` -- the confirm-gated restore orchestrator. It runs the 4 per-role `tasks/restore.yml` files (garage -> prometheus -> grafana -> alertmanager, forward order matching backup) with one cross-role concern: stop the 3 Garage writers (Loki, Tempo, Mimir) BEFORE the Garage restore and restart them AFTER, all tagged `[garage, restore]` per D-189 (amended for SC4 reconciliation) so `--tags garage` runs the entire bracketed unit AND `--tags restore` cross-cutting runs the bracketed unit + the other 3 roles.

Purpose: this is the single user-facing entry point for restores (RESTORE-V13-05). Destructive operations are gated behind `backup_restore_confirm=true` (OPS-V13-01) at BOTH orchestrator and per-role layers (defence-in-depth from D-185). The orchestrator-level gate is tagged `[always]` so it fires on ANY restore_docker.yml invocation -- including stateless-tag invocations -- because the playbook's IDENTITY is destructive. `any_errors_fatal: true` is hardcoded -- partial restore is worse than no restore.
Output: one new playbook file at `playbooks/restore_docker.yml`. No other files changed.
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

@playbooks/undeploy_docker.yml
@playbooks/deploy_docker.yml
@roles/garage/tasks/backup.yml
@roles/grafana/tasks/restore.yml
@roles/grafana/tasks/verify.yml
@inventory/example-homelab/group_vars/all/backup.yml

<interfaces>
<!-- Knobs the orchestrator references (already defined in group_vars/all/backup.yml; Phase 13) -->

backup_restore_confirm   : bool   (default false; operator MUST set to true via --extra-vars for ANY restore_docker.yml invocation, including --tags <stateless-role> invocations -- the gate is the identity-level safety)
backup_restore_from      : str    (default "" -- per-role tasks resolve "latest per role" via find|sort -r|head -1)
backup_stop_timeout      : int    (default 60; reused for writer-stop -- single knob serves backup AND restore per group_vars comment)

<!-- Writer container names -- HARDCODED inline in the loop list-of-dicts per "Landmines" Mitigation Option 1 -->
<!-- in 14-PATTERNS.md. Rationale: no include_role for loki/tempo/mimir means their defaults/main.yml is not loaded; -->
<!-- hardcoding avoids that resolution gap and matches Rock's preference for explicit values. -->
<!-- Operator override surface: `--extra-vars loki_container_name=...` still works because we use the var inside the loop dict. -->

loki_container_name      : default "telemetron-loki"   (roles/loki/defaults/main.yml:20)
tempo_container_name     : default "telemetron-tempo"  (roles/tempo/defaults/main.yml:22)
mimir_container_name     : default "telemetron-mimir"  (roles/mimir/defaults/main.yml:20)

<!-- Per-role include_role surface (Phase 13 -- each tasks/restore.yml already gates on backup_restore_confirm) -->

include_role: name=<role> tasks_from=restore
  tags: [<role>, restore]
  -- consumes: backup_restore_confirm, backup_restore_from
  -- per-role gate is the defence-in-depth layer (D-185 acknowledges this)
  -- defence-in-depth confirmed: roles/grafana/tasks/restore.yml carries its own backup_restore_confirm gate
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create playbooks/restore_docker.yml -- confirm gate, WARN banner, writer-stop, 4 role restores, writer-restart</name>
  <files>playbooks/restore_docker.yml</files>
  <read_first>
    - playbooks/undeploy_docker.yml (structural analog: vars + pre_tasks banner + include_role list)
    - roles/garage/tasks/backup.yml lines 122-142 (verbatim writer-stop pattern -- docker stop + docker_container_info poll until State.Running == false; PATTERNS.md Pattern H)
    - roles/garage/tasks/backup.yml lines 197-218 (verbatim restart pattern -- docker start + docker_container_info poll until State.Health.Status == 'healthy'; PATTERNS.md Pattern I)
    - roles/grafana/tasks/restore.yml (defence-in-depth per-role confirm gate -- already exists per Phase 13)
    - roles/grafana/tasks/verify.yml lines 21-32 (canonical healthy-poll shape -- cross-reference for Pattern I)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-PATTERNS.md Pattern F (WARN banner with `WARNING: irreversible --` prefix), Pattern G (confirm-gate fail), Pattern H (writer-stop loop), Pattern I (writer-restart loop), Pattern J (any_errors_fatal true hardcoded), Shared Patterns 1 + 2 + 3 + 4 + 5
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md D-180 (writer-quiesce lives inline in restore_docker.yml), D-181 (sequential loop over [loki, tempo, mimir]), D-182 (reuse backup_stop_timeout), D-183 (writer restart via docker start + healthy-poll), D-185 (any_errors_fatal hardcoded true), D-187 (WARN banner content -- exact 3 lines), D-188 (stateless tag -> empty play; AMENDED by SC4 reconciliation -- confirm flag required for any restore_docker.yml invocation), D-189 (writer-stop/restart tagged [garage, restore] per the SC4 reconciliation; original ban on [writers]/[always] preserved), D-193 (physical layout: pre_tasks for confirm-gate + banner; tasks for writer-stop -> include_role -> writer-restart -> other 3 roles; NO post_tasks)
    - inventory/example-homelab/group_vars/all/backup.yml (knobs: backup_restore_confirm, backup_restore_from, backup_stop_timeout; line 20-22 comment confirms backup_stop_timeout serves both backup AND restore)
    - PATTERNS.md "Landmines" section "Writer container name defaults" (the hardcode-in-loop-dicts mitigation -- Option 1, recommended)
  </read_first>
  <action>
    Create `playbooks/restore_docker.yml` from scratch.

    1. File header (comments lines 1-N):
       - `---` YAML doc start.
       - Comment block describing: M1 restore orchestrator (Docker target); DESTRUCTIVE -- requires `--extra-vars backup_restore_confirm=true` for ANY invocation (including stateless-tag invocations like `--tags loki` -- the orchestrator-level gate is the playbook-identity-level safety per D-188 amended by SC4 reconciliation); calls 4 per-role tasks/restore.yml in forward order (garage -> prometheus -> grafana -> alertmanager), brackets the Garage restore with writer-stop (Loki, Tempo, Mimir) BEFORE and writer-restart AFTER (D-180); writer-stop/restart tasks tagged `[garage, restore]` (D-189 amended by SC4 reconciliation: `--tags garage` runs the whole bracketed unit AND `--tags restore` cross-cutting also runs it; `[writers]`/`[always]` still banned so `--tags loki/tempo/mimir` matches nothing in the bracket); `any_errors_fatal: true` hardcoded (D-185 -- `backup_continue_on_failure` does NOT apply to restore). Include 4-line Usage block: (a) default `ansible-playbook -i inventory/example-homelab playbooks/restore_docker.yml --ask-vault-pass --extra-vars "backup_restore_confirm=true"`; (b) explicit timestamp `... --extra-vars "backup_restore_confirm=true backup_restore_from=YYYYMMDDTHHMMSSZ"`; (c) per-role `--tags <role> --extra-vars "backup_restore_confirm=true"`; (d) cross-cutting `--tags restore --extra-vars "backup_restore_confirm=true"`.

    2. Play header:
       - `- name: Telemetron -- restore Docker host stateful roles from backups (DESTRUCTIVE)`
       - `hosts: telemetron`
       - `gather_facts: true`
       - `become: false`
       - `collections: [community.docker]`  (Shared Pattern 1 -- writer-stop/restart polls use docker_container_info)
       - `any_errors_fatal: true`  (D-185 -- VERBATIM, hardcoded, no Jinja2 expression)

    3. `vars:` block:
       - `backup_restore_confirm: false`  (D-185 default; operator MUST opt in via `--extra-vars`)
       - `backup_restore_from: ""`  (default empty string -- per-role tasks resolve "latest per role"; per D-190 the orchestrator does NOT pre-resolve)

    4. `pre_tasks:` (2 tasks, in this order):

       Task 4a -- the confirm gate (OPS-V13-01; PATTERNS.md Pattern G) -- FIRST so operator does not see the banner if the gate fires:
         `- name: Refuse to run restore without explicit confirm-gate (OPS-V13-01; identity-level safety per D-188 amended)`
         `  ansible.builtin.fail:`
         `    msg: |`
                  Restore refused.
                  Pass --extra-vars backup_restore_confirm=true to proceed.
                  This flag is required for ANY restore_docker.yml invocation including --tags <stateless-role> invocations -- the playbook's identity is destructive.
                  See docs/quickstart.md#backup-and-restore for the operator opt-in contract.
         `  when: not (backup_restore_confirm | default(false) | bool)`
         `  tags: [always]`
         Note: `tags: [always]` is intentional and is the play's IDENTITY-LEVEL safety. The gate fires on ANY restore_docker.yml invocation -- including invocations with `--tags <stateless-role>` that would otherwise produce a 0-task play -- because the playbook's destructive identity does not depend on which tag is selected. This is the D-188-amended-by-SC4 reconciliation: operators always supply the confirm flag for any restore_docker.yml run; the stateless-tag empty-play behavior is verified ONLY when the confirm flag IS supplied (then no role include_role matches and the play exits 0).

       Task 4b -- the WARN banner (D-187; PATTERNS.md Pattern F):
         `- name: WARN -- restore will permanently replace volume contents (D-187)`
         `  ansible.builtin.debug:`
         `    msg: |`
                  WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)
                  Target timestamp: {{ backup_restore_from | default('<latest per role>') }}
                  Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir
         `  tags: [always]`
         Verbatim `WARNING: irreversible --` prefix on line 1 (D-159 grep target).

    5. `tasks:` block in this EXACT order:

       Task 5a -- writer-stop loop (D-181, D-189-amended; PATTERNS.md Pattern H + Shared Pattern 2):
         `- name: Stop Garage writers (Loki/Tempo/Mimir) before Garage restore (D-181, D-189)`
         `  ansible.builtin.command: "docker stop -t {{ backup_stop_timeout }} {{ item.container_name }}"`
         `  loop:`
                  - { role: loki,  container_name: "{{ loki_container_name  | default('telemetron-loki') }}" }
                  - { role: tempo, container_name: "{{ tempo_container_name | default('telemetron-tempo') }}" }
                  - { role: mimir, container_name: "{{ mimir_container_name | default('telemetron-mimir') }}" }
         `  loop_control:`
         `    label: "{{ item.role }}"`
         `  changed_when: true`
         `  become: true`  (Shared Pattern 5 -- become true on host-side commands)
         `  tags:`
         `    - garage`
         `    - restore`

       Task 5b -- writer-stop healthy-poll (PATTERNS.md Pattern H):
         `- name: Wait for Garage writers to reach stopped state`
         `  community.docker.docker_container_info:`
         `    name: "{{ item.container_name }}"`
         `  register: writer_stopped_check`
         `  until: >-`
         `    writer_stopped_check.container is defined`
         `    and writer_stopped_check.container.State is defined`
         `    and writer_stopped_check.container.State.Running == false`
         `  retries: 30`
         `  delay: 2`
         `  changed_when: false`
         `  loop:` (SAME 3-entry list as 5a; hardcoded again -- DO NOT use `loop: "{{ ansible_loop_var ... }}"` indirection)
                  - { role: loki,  container_name: "{{ loki_container_name  | default('telemetron-loki') }}" }
                  - { role: tempo, container_name: "{{ tempo_container_name | default('telemetron-tempo') }}" }
                  - { role: mimir, container_name: "{{ mimir_container_name | default('telemetron-mimir') }}" }
         `  loop_control:`
         `    label: "{{ item.role }}"`
         `  tags:`
         `    - garage`
         `    - restore`

       Task 5c -- Garage restore (tagged `[garage, restore]`):
         `- name: Invoke garage restore`
         `  ansible.builtin.include_role:`
         `    name: garage`
         `    tasks_from: restore`
         `  tags:`
         `    - garage`
         `    - restore`

       Task 5d -- writer-restart loop (D-183, D-189-amended; PATTERNS.md Pattern I + Shared Pattern 3):
         `- name: Start Garage writers (Loki/Tempo/Mimir) after Garage restore (D-183, D-189)`
         `  ansible.builtin.command: "docker start {{ item.container_name }}"`
         `  loop:` (SAME 3-entry hardcoded list)
                  - { role: loki,  container_name: "{{ loki_container_name  | default('telemetron-loki') }}" }
                  - { role: tempo, container_name: "{{ tempo_container_name | default('telemetron-tempo') }}" }
                  - { role: mimir, container_name: "{{ mimir_container_name | default('telemetron-mimir') }}" }
         `  loop_control:`
         `    label: "{{ item.role }}"`
         `  changed_when: true`
         `  become: true`
         `  tags:`
         `    - garage`
         `    - restore`

       Task 5e -- writer-restart healthy-poll (PATTERNS.md Pattern I + Shared Pattern 3):
         `- name: Wait for Garage writers to report healthy`
         `  community.docker.docker_container_info:`
         `    name: "{{ item.container_name }}"`
         `  register: writer_healthy_check`
         `  until: >-`
         `    writer_healthy_check.container is defined`
         `    and writer_healthy_check.container.State is defined`
         `    and writer_healthy_check.container.State.Health is defined`
         `    and writer_healthy_check.container.State.Health.Status == 'healthy'`
         `  retries: 30`
         `  delay: 2`
         `  changed_when: false`
         `  loop:` (SAME 3-entry hardcoded list)
                  - { role: loki,  container_name: "{{ loki_container_name  | default('telemetron-loki') }}" }
                  - { role: tempo, container_name: "{{ tempo_container_name | default('telemetron-tempo') }}" }
                  - { role: mimir, container_name: "{{ mimir_container_name | default('telemetron-mimir') }}" }
         `  loop_control:`
         `    label: "{{ item.role }}"`
         `  tags:`
         `    - garage`
         `    - restore`

       Tasks 5f, 5g, 5h -- the other 3 role restores (each tagged with its role name AND `restore` for SC4 cross-cutting):

         Task 5f:
           `- name: Invoke prometheus restore`
           `  ansible.builtin.include_role:`
           `    name: prometheus`
           `    tasks_from: restore`
           `  tags:`
           `    - prometheus`
           `    - restore`

         Task 5g:
           `- name: Invoke grafana restore`
           `  ansible.builtin.include_role:`
           `    name: grafana`
           `    tasks_from: restore`
           `  tags:`
           `    - grafana`
           `    - restore`

         Task 5h:
           `- name: Invoke alertmanager restore`
           `  ansible.builtin.include_role:`
           `    name: alertmanager`
           `    tasks_from: restore`
           `  tags:`
           `    - alertmanager`
           `    - restore`

    6. NO `post_tasks:` block (D-193 -- writer-restart MUST live inside `tasks:` so it fires under `--tags garage` AND `--tags restore`; placing it in post_tasks would break the tag-scoped UX because post_tasks runs regardless of `--tags` and writer-stop would NOT fire under non-garage tag selections).

    Constraints:
    - English-only.
    - HARDCODE the container names inline in each `loop:` dict per PATTERNS.md "Landmines" Mitigation Option 1. Rationale: no `include_role: name=loki` (or tempo/mimir) anywhere in this playbook, so role defaults are NOT loaded -- a bare `{{ loki_container_name }}` reference would fail or fall back to undefined. The `| default('telemetron-<role>')` filter mirrors the role's defaults/main.yml value. Operators can still override via `--extra-vars loki_container_name=...`.
    - DO NOT add any `community.docker` `state: stopped`/`state: started` tasks -- use the `command: docker stop`/`command: docker start` shape per Phase 13 standard (matches roles/garage/tasks/backup.yml verbatim; community.docker state: stopped is documented in 13-CONTEXT.md and PROJECT.md as STRICTLY FORBIDDEN because it strips volume specs).
    - DO NOT pre-resolve `backup_restore_from` at orchestrator level (D-190 -- each role resolves independently).
    - DO NOT introduce `restore_continue_on_failure` (D-185 footgun lock; out of scope).
    - DO NOT add writer-stop/restart tasks to roles/loki, roles/tempo, or roles/mimir tasks/ directories (D-180 -- writer-quiesce lives inline in this orchestrator, not as new per-role tasks).
    - DO NOT tag writer-stop/restart with `[writers]` or `[always]` (D-189 original rationale preserved: `--tags loki/tempo/mimir/writers` must NOT fire the writer-stop). The `[garage, restore]` two-element list is the SC4 reconciliation.
    - DO NOT enumerate role names in the WARN banner -- D-186/D-187 explicitly bans enumeration so banner is stable across role additions. The banner DOES name the 4 stateful roles on the headline line per D-187's verbatim content, which is acceptable because that line is the locked content of the decision.
    - DO NOT change the `tags: [always]` on the confirm-gate fail task. This is intentional: the gate is the playbook's identity-level safety per the D-188 amendment. Operators always supply the confirm flag for any restore_docker.yml invocation.

    Per Claude's Discretion (CONTEXT.md):
    - SKIP the optional pre-stop `WARN -- writers will be stopped` debug (the top-level WARN banner already names the stop order on line 3).
    - SKIP the optional success summary recommending smoke_test.yml (the human-UAT doc in Plan 04 prescribes the smoke-test step explicitly; orchestrator summary would be noise).
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        # File exists and parses
        test -s playbooks/restore_docker.yml
        python3 -c "import yaml; yaml.safe_load(open(\"playbooks/restore_docker.yml\"))"
        # Required structural elements
        grep -q "hosts: telemetron" playbooks/restore_docker.yml
        grep -q "any_errors_fatal: true" playbooks/restore_docker.yml
        grep -q "WARNING: irreversible --" playbooks/restore_docker.yml
        grep -q "ansible.builtin.fail" playbooks/restore_docker.yml
        grep -q "backup_restore_confirm" playbooks/restore_docker.yml
        # Writer-stop + writer-restart loops
        test "$(grep -c "docker stop -t" playbooks/restore_docker.yml)" -ge 1
        test "$(grep -c "docker start " playbooks/restore_docker.yml)" -ge 1
        # 3 writers referenced in each of the 4 docker_container_info loops -- minimum 4 occurrences of loki/tempo/mimir keys collectively in loops
        test "$(grep -cE "role:\\s+loki" playbooks/restore_docker.yml)" -ge 4
        test "$(grep -cE "role:\\s+tempo" playbooks/restore_docker.yml)" -ge 4
        test "$(grep -cE "role:\\s+mimir" playbooks/restore_docker.yml)" -ge 4
        # docker_container_info called for both stopped-check and healthy-check
        test "$(grep -c "community.docker.docker_container_info" playbooks/restore_docker.yml)" -ge 2
        # 4 include_role calls -- one per stateful role
        test "$(grep -c "tasks_from: restore" playbooks/restore_docker.yml)" -eq 4
        grep -q "name: garage" playbooks/restore_docker.yml
        grep -q "name: prometheus" playbooks/restore_docker.yml
        grep -q "name: grafana" playbooks/restore_docker.yml
        grep -q "name: alertmanager" playbooks/restore_docker.yml
        # Order check: writer-stop docker_container_info < garage include_role < writer-restart docker_container_info < prometheus include_role
        ws=$(grep -n "writer_stopped_check" playbooks/restore_docker.yml | head -1 | cut -d: -f1)
        gr=$(grep -n "name: garage" playbooks/restore_docker.yml | head -1 | cut -d: -f1)
        wh=$(grep -n "writer_healthy_check" playbooks/restore_docker.yml | head -1 | cut -d: -f1)
        pr=$(grep -n "name: prometheus" playbooks/restore_docker.yml | head -1 | cut -d: -f1)
        test "$ws" -lt "$gr" && test "$gr" -lt "$wh" && test "$wh" -lt "$pr"
        # Tag enforcement: writer-stop/restart tasks MUST be tagged with both garage AND restore, NOT loki/tempo/mimir/writers/always.
        # Heuristic: between the writer-stop label and the prometheus include_role, neither [loki], [tempo], [mimir], [writers], nor [always] appears as a tag value (after stripping comment lines).
        awk -v s="$ws" -v e="$pr" "NR>=s && NR<=e" playbooks/restore_docker.yml | grep -v "^[[:space:]]*#" > /tmp/restore-quiesce-block.yml
        if grep -E "^\\s+-\\s+(loki|tempo|mimir|writers|always)\\b" /tmp/restore-quiesce-block.yml; then echo "FAIL: writer-quiesce block has forbidden tag (D-189 ban)"; exit 1; fi
        # Confirm the writer-quiesce block carries both garage and restore tag entries
        if ! grep -E "^\\s+-\\s+garage\\b" /tmp/restore-quiesce-block.yml; then echo "FAIL: writer-quiesce block missing garage tag"; exit 1; fi
        if ! grep -E "^\\s+-\\s+restore\\b" /tmp/restore-quiesce-block.yml; then echo "FAIL: writer-quiesce block missing restore tag (SC4 cross-cutting)"; exit 1; fi
        # NO state: stopped or state: started anywhere
        if grep -E "state:\\s+(stopped|started)" playbooks/restore_docker.yml; then echo "FAIL: must use docker stop/start, not community.docker state:"; exit 1; fi
        # NO post_tasks
        if grep -E "^\\s*post_tasks:" playbooks/restore_docker.yml; then echo "FAIL: D-193 forbids post_tasks"; exit 1; fi
        # become: true on host commands (writer-stop + writer-restart), become: false at play level
        test "$(grep -c "become: true" playbooks/restore_docker.yml)" -ge 2
        # SC4 cross-cutting `restore` tag appears AT LEAST 8 times (4 include_role + 4 writer-quiesce tasks 5a/5b/5d/5e) -- comment-stripped
        nr=$(grep -v "^[[:space:]]*#" playbooks/restore_docker.yml | grep -E "^\\s+-\\s+restore\\s*$" | wc -l)
        test "$nr" -ge 8 || { echo "FAIL: --tags restore cross-cutting requires >= 8 [restore] tag occurrences (got $nr)"; exit 1; }
        # Syntax-check
        ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml
        # SC4 cross-cutting tag enumeration: --list-tasks --tags restore must enumerate the 4 include_role lines + 4 writer-quiesce tasks
        # The confirm-gate (tagged [always]) ALWAYS appears under any tag filter, so we must not require its absence;
        # we DO require the 4 invoke-<role>-restore lines and the 4 writer-quiesce task names appear.
        listout=$(ansible-playbook --list-tasks --tags restore -i inventory/example-homelab playbooks/restore_docker.yml)
        echo "$listout" | grep -cE "Invoke (garage|prometheus|grafana|alertmanager) restore" | xargs -I{} test {} -eq 4 || { echo "FAIL: --tags restore did not enumerate all 4 role include lines"; exit 1; }
        echo "$listout" | grep -q "Stop Garage writers" || { echo "FAIL: --tags restore did not enumerate writer-stop loop"; exit 1; }
        echo "$listout" | grep -q "Start Garage writers" || { echo "FAIL: --tags restore did not enumerate writer-restart loop"; exit 1; }
        echo "$listout" | grep -q "Wait for Garage writers to reach stopped state" || { echo "FAIL: --tags restore did not enumerate writer-stop poll"; exit 1; }
        echo "$listout" | grep -q "Wait for Garage writers to report healthy" || { echo "FAIL: --tags restore did not enumerate writer-restart poll"; exit 1; }
        echo "PASS: restore_docker.yml structurally and syntactically valid; SC4 cross-cutting tag verified"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - `playbooks/restore_docker.yml` exists, is non-empty, parses as YAML via `python3 -c "import yaml; yaml.safe_load(...)"`.
    - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` exits 0.
    - Play declares `hosts: telemetron`, `gather_facts: true`, `become: false`, `collections: [community.docker]`, `any_errors_fatal: true` (literal `true`, NOT a Jinja2 expression -- D-185).
    - `vars:` block contains `backup_restore_confirm: false` and `backup_restore_from: ""`.
    - `pre_tasks:` contains EXACTLY 2 tasks in this order: (a) `ansible.builtin.fail` with `when: not (backup_restore_confirm | default(false) | bool)` and `tags: [always]` (the gate's `[always]` tag is INTENTIONAL and is the playbook's identity-level safety per D-188 amended by SC4 reconciliation); (b) `ansible.builtin.debug` banner with `tags: [always]` whose `msg:` begins (line 1) with the verbatim string `WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)`.
    - `tasks:` contains EXACTLY 8 tasks in this order: writer-stop loop (docker stop), writer-stop poll (docker_container_info until State.Running == false), `include_role: name=garage tasks_from=restore`, writer-restart loop (docker start), writer-restart poll (docker_container_info until State.Health.Status == 'healthy'), `include_role: name=prometheus tasks_from=restore`, `include_role: name=grafana tasks_from=restore`, `include_role: name=alertmanager tasks_from=restore`.
    - The 5 garage-bracket tasks (writer-stop loop, writer-stop poll, garage include_role, writer-restart loop, writer-restart poll) ALL carry `tags: [garage, restore]` (two-element list per D-189 amended by SC4 reconciliation). The grep-filtered tag-value scan between the writer-stop label and the prometheus include_role asserts that `garage` AND `restore` BOTH appear and that `loki`, `tempo`, `mimir`, `writers`, and `always` do NOT appear (D-189 original rationale preserved).
    - The other 3 include_role calls each carry `tags: [<role>, restore]` (two-element list per SC4 cross-cutting).
    - The comment-stripped count of `- restore` tag entries is >= 8 (4 include_role + 4 writer-quiesce tasks); the grep guard strips `#`-prefixed lines.
    - `ansible-playbook --list-tasks --tags restore -i inventory/example-homelab playbooks/restore_docker.yml` enumerates exactly the 4 `Invoke <role> restore` lines and all 4 writer-quiesce task names (Stop Garage writers, Wait for Garage writers to reach stopped state, Start Garage writers, Wait for Garage writers to report healthy) -- B-1 SC4 cross-cutting gate.
    - Each writer-stop/restart `loop:` contains a 3-entry list-of-dicts hardcoding `{role: loki, container_name: "{{ loki_container_name | default('telemetron-loki') }}" }`, same for tempo and mimir, in that order.
    - Each docker_container_info poll uses `retries: 30, delay: 2, changed_when: false` and a loop-scoped `register:` (`writer_stopped_check` for stop-poll; `writer_healthy_check` for restart-poll).
    - `community.docker.docker_container_info` appears at least 2 times (stop-poll + restart-poll).
    - `docker stop -t` appears at least 1 time; `docker start ` appears at least 1 time.
    - NO `state: stopped` or `state: started` anywhere (community.docker landmine).
    - NO `post_tasks:` block (D-193).
    - NO `block:` at play level.
    - NO `roles:` block (D-149).
    - NO `WARNING: irreversible --` prefix on the backup orchestrator (Plan 02 already enforced this).
    - `become: true` appears at least on the writer-stop command task and the writer-restart command task; `become: false` declared at play level.
    - File header has Usage block showing 4 invocation forms: default (with confirm flag), explicit timestamp, per-role `--tags <role>` (with confirm flag), and cross-cutting `--tags restore` (with confirm flag). The Usage block MUST state that `backup_restore_confirm=true` is required for ANY invocation including `--tags <stateless-role>` invocations (D-188 amended by SC4 reconciliation).
    - `git diff --stat` shows exactly 1 new file `playbooks/restore_docker.yml` and no other changes.
  </acceptance_criteria>
  <done>
    `playbooks/restore_docker.yml` ships as the M1 restore orchestrator. An invocation WITHOUT `backup_restore_confirm=true` fails at the orchestrator-level pre_task gate before the WARN banner prints, REGARDLESS of `--tags` (the gate is tagged `[always]` per the D-188 SC4 amendment because the playbook's identity is destructive). An invocation WITH `backup_restore_confirm=true`: prints the WARN banner (verbatim 3-line shape including `WARNING: irreversible --` prefix); stops Loki/Tempo/Mimir sequentially; polls until each is stopped; runs the Garage restore (which Phase 13's per-role gate ALSO re-validates against `backup_restore_confirm` -- defence-in-depth, confirmed via roles/grafana/tasks/restore.yml's own gate); starts Loki/Tempo/Mimir; polls until each is healthy; then runs prometheus/grafana/alertmanager restores in that order. `any_errors_fatal: true` aborts the play on the first role's failure with no operator opt-out. `--tags garage` runs only the bracketed Garage unit (stop -> restore -> restart) plus pre_tasks. `--tags restore` cross-cutting (SC4) runs the bracketed Garage unit AND the other 3 role restores. `--tags prometheus` (or grafana or alertmanager) restores only that role; writers stay running. `--tags loki --extra-vars backup_restore_confirm=true` (or any other stateless role with the confirm flag) matches nothing on the role side and exits 0 (D-188 amended); without the confirm flag the same invocation fails at the orchestrator gate.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Ansible CLI `--extra-vars` -> play vars scope | `backup_restore_confirm` flips a DESTRUCTIVE operation; without the orchestrator-level gate, an unrelated typo (`backup_restore_conform=true`) would let the play proceed silently. |
| Orchestrator -> per-role tasks/restore.yml | Per-role gate provides defence-in-depth (D-185 acknowledgement). A custom playbook calling `include_role: tasks_from=restore` directly STILL hits the per-role gate (the orchestrator-level one is in pre_tasks, which custom playbooks don't share). Verified: roles/grafana/tasks/restore.yml carries its own confirm gate. |
| `docker stop`/`docker start` host commands | Tampering here (e.g., race between stop and restore-start) would corrupt Garage LMDB. Mitigated by docker_container_info poll until `State.Running == false` BEFORE the restore touches the volume. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-08 (T1) | Tampering | Restore orchestrator invocation without confirm flag (operator typo, accidental rerun, CI script bug) | mitigate | Orchestrator-level `ansible.builtin.fail` pre_task tagged `[always]` with `when: not (backup_restore_confirm | default(false) | bool)` fires BEFORE any destructive action AND fires under ANY `--tags` filter (identity-level safety per D-188 amendment). Per-role gate in each tasks/restore.yml (Phase 13 contract; confirmed in roles/grafana/tasks/restore.yml) is the defence-in-depth layer when a custom playbook bypasses the orchestrator. Both layers exist by design (D-185). |
| T-14-09 (T2) | Tampering | Half-restored stack when a later role's restore fails (e.g., Prometheus disk full after Garage restore succeeded) | mitigate | `any_errors_fatal: true` HARDCODED -- play aborts on the first failure with no opt-out (D-185). Operator sees PLAY RECAP immediately and knows which role was the failure point. Documented in file header that `backup_continue_on_failure` does NOT apply here. |
| T-14-10 (T3) | Tampering | Race between writer-stop and Garage restore -- Loki commits a chunk during the window where writers think Garage is healthy but Garage is being restored | mitigate | `docker_container_info` poll with `until: State.Running == false` and `retries: 30, delay: 2` -- the include_role for Garage restore does NOT begin until each writer has been observed `Running == false`. The 60s budget (30 * 2s) matches `backup_stop_timeout` (D-181 + D-182). Sequential ordering ensures all 3 writers are confirmed stopped before any restore touches the Garage volume. |
| T-14-11 (related to T2) | Information Disclosure | `ansible.builtin.fail`'s `msg:` echoes the operator-facing instruction including the `--extra-vars` form -- could be construed as making the bypass too obvious | accept | The bypass IS the legitimate path. ASVS L1; not security-sensitive information. The msg directs operators to docs/quickstart.md for the full contract -- right thing to do. |
| T-14-12 (T5) | Denial of Service | Writers' restart-poll never reaches healthy (HEALTHCHECK fails) -- play hangs for 60s before timing out | mitigate | `retries: 30, delay: 2 -> 60s ceiling` matches writer-stop budget. `any_errors_fatal: true` ensures the timeout fails the play loudly rather than hanging indefinitely. Phase 13 contract ensures writer HEALTHCHECK exists (Gate 7). |
</threat_model>

<verification>
- Static structural + syntax check only in this plan. Live UAT for the round-trip happy path AND the confirm-gate proof lives in Plan 04 (14-HUMAN-UAT.md scenarios 1 + 2).
- The verify script grep gates use `grep -v '^[[:space:]]*#'` semantics (the writer-quiesce tag-content check + the `- restore` count) so comments cannot mask a forbidden tag value or inflate the cross-cutting tag count.
- `ansible-playbook --syntax-check` is INSUFFICIENT for role-internal tasks (MEMORY.md `feedback_ansible_syntax_check_role_gap.md`); it does catch play-level structural defects, which is what this plan ships.
- The `--list-tasks --tags restore` static check is the SC4 cross-cutting gate -- proves the `[garage, restore]` and `[<role>, restore]` tag lists actually expose all 8 destructive tasks under `--tags restore` WITHOUT requiring a live host.
</verification>

<success_criteria>
- RESTORE-V13-05: `restore_docker.yml` exists with the 4 stateful roles in forward-deploy order, the writer-stop -> Garage restore -> writer-restart bracket, and the D-187 banner.
- OPS-V13-01 (orchestrator side): pre_task `ansible.builtin.fail` gate tagged `[always]` refuses to run without `backup_restore_confirm=true` on ANY invocation (D-188 amended by SC4 reconciliation: identity-level safety). The per-role gate (Phase 13) is the defence-in-depth layer for custom-playbook callers.
- OPS-V13-03 (restore side): per-role `tags: [<role>, restore]` on each include_role; banner + confirm-gate tagged `[always]`; writer-stop/restart tagged `[garage, restore]` (D-189 amended) so `--tags garage` runs the bracketed unit, `--tags restore` cross-cutting (SC4) runs the bracketed unit AND the other 3 roles, and `--tags loki/tempo/mimir/writers/always` matches nothing in the bracket.
- SC4 cross-cutting: `--tags restore` selects all 4 role include_role calls + the 4 writer-quiesce tasks (proven by the `--list-tasks --tags restore` verify gate).
</success_criteria>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-03-SUMMARY.md` when done.
</output>
