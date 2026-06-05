---
phase: 14-orchestrators-leviathan-human-uat
plan: 02
type: execute
wave: 2
depends_on:
  - 14-01
files_modified:
  - playbooks/backup_docker.yml
autonomous: true
requirements:
  - BACKUP-V13-05
  - OPS-V13-02
  - OPS-V13-03

must_haves:
  truths:
    - "`playbooks/backup_docker.yml` exists and includes the 4 stateful roles (garage -> prometheus -> grafana -> alertmanager, in forward-deploy order)."
    - "A D-186 PLAY-start banner (`tags: always`) displays the backup destination root, the `backup_continue_on_failure` knob status with category description, and the `backup_stop_timeout` value -- without enumerating role names (D-186 stability)."
    - "A single shared ISO 8601 basic UTC timestamp is generated once in `pre_tasks:` and passed to all 4 role include_role calls via `vars: { backup_timestamp_override: ... }` so all 4 tarballs in one run share one filename suffix (D-191)."
    - "`any_errors_fatal: '{{ not (backup_continue_on_failure | default(false) | bool) }}'` is set at play level (D-184): default behavior aborts the play on the first role failure; `--extra-vars backup_continue_on_failure=true` opts into running all 4 roles past failures."
    - "Each role's include_role call is tagged with the role name AND the cross-cutting `backup` tag (`tags: [<role>, backup]`); `--tags <role>` selects only that role; `--tags backup` cross-cutting selects all 4 role include_role calls (SC4 cross-cutting contract); `--tags <stateless-role>` (loki/tempo/mimir/karma/fluentbit/opentelemetry/node_exporter/nfsd) produces an empty 0-task play and exits 0 (SC1)."
    - "`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0."
    - "`ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` enumerates exactly the 4 role include_role lines (garage, prometheus, grafana, alertmanager) -- proving the `[backup]` cross-cutting tag covers all 4 roles."
  artifacts:
    - path: "playbooks/backup_docker.yml"
      provides: "Thin orchestrator: pre_tasks banner + shared timestamp + 4 role-tagged include_role calls."
      min_lines: 80
      contains: "include_role"
  key_links:
    - from: "playbooks/backup_docker.yml pre_tasks set_fact: backup_timestamp_shared"
      to: "include_role vars: backup_timestamp_override"
      via: "Jinja2 variable propagation across 4 include_role calls"
      pattern: "backup_timestamp_override: \"{{ backup_timestamp_shared }}\""
    - from: "playbooks/backup_docker.yml play-level any_errors_fatal"
      to: "Ansible play-execution control"
      via: "play-level keyword evaluated once at play start"
      pattern: "any_errors_fatal:"
    - from: "Banner pre_task `tags: [always]`"
      to: "Banner visible under --tags <role> targeted runs"
      via: "Ansible tag inheritance"
      pattern: "tags:\\s+-\\s+always"
    - from: "Each include_role `tags: [<role>, backup]`"
      to: "SC4 cross-cutting `--tags backup` covers all 4 role include_role calls"
      via: "Ansible tag selection at include-task level (D-149 explicit-include precedent)"
      pattern: "tags:\\s+-\\s+backup"
---

<objective>
Ship `playbooks/backup_docker.yml` -- a thin orchestrator that runs the 4 per-role `tasks/backup.yml` files (garage -> prometheus -> grafana -> alertmanager) under a single shared ISO 8601 basic UTC timestamp, with a D-186 PLAY-start banner, configurable bail-out vs continue-on-failure semantics, and full `--tags <role>` + `--tags backup` cross-cutting UX (SC4).

Purpose: this is the single user-facing entry point for backups (BACKUP-V13-05). The orchestrator concentrates the multi-role coordination (shared timestamp, bail-out policy, banner) and delegates everything else to the per-role tasks Phase 13 shipped.
Output: one new playbook file at `playbooks/backup_docker.yml`. No other files changed.
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
@.planning/phases/14-orchestrators-leviathan-human-uat/14-01-amend-backup-yml-timestamp-override-PLAN.md
@.planning/phases/14-orchestrators-leviathan-human-uat/14-01-SUMMARY.md

@playbooks/undeploy_docker.yml
@playbooks/deploy_docker.yml
@inventory/example-homelab/group_vars/all/backup.yml

<interfaces>
<!-- Knobs the orchestrator must reference (already defined in group_vars/all/backup.yml; Phase 13) -->

backup_dest_root              : str   (default "/opt/telemetron/backups")
backup_stop_timeout           : int   (default 60)
backup_continue_on_failure    : bool  (default false; orchestrator overrides via play-level vars)

<!-- Variable the orchestrator must DEFINE inside pre_tasks via set_fact -->

backup_timestamp_shared       : str   (set_fact value from `date -u +%Y%m%dT%H%M%SZ`; ISO 8601 basic UTC)

<!-- Variable the orchestrator must PASS to each include_role via vars: -->

backup_timestamp_override     : str   (= backup_timestamp_shared; consumed by Plan 01's set_fact in each tasks/backup.yml)

<!-- Role-side surface (from Phase 13 + Plan 01) -->

include_role: name=<role> tasks_from=backup
  vars:
    backup_timestamp_override: "<shared ts>"

  -- produces: /opt/telemetron/backups/<role>/<role>-<shared-ts>.tar.zst
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create playbooks/backup_docker.yml with vars + pre_tasks (banner + shared-timestamp) and the 4 include_role calls</name>
  <files>playbooks/backup_docker.yml</files>
  <read_first>
    - playbooks/undeploy_docker.yml (the structural analog: vars, pre_tasks banner, include_role bodies, post_tasks shape -- adapt forward-deploy order and DROP destructive guard)
    - playbooks/deploy_docker.yml (cross-check the per-role `tags: <role>` convention from SC4)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-PATTERNS.md Pattern A (Play scaffold), Pattern B (PLAY-start banner), Pattern C (D-191 shared-timestamp set_fact), Pattern D (Per-role include_role with `tags: [<role>]`), Pattern E (per-role tag for SC4), Shared Patterns 1 + 4 + 5
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md D-184 (any_errors_fatal one-liner), D-186 (banner shape -- exact 3-line content), D-191 (shared-timestamp + override propagation), D-193 (physical layout)
    - inventory/example-homelab/group_vars/all/backup.yml (the 3 knobs already defined: backup_dest_root, backup_stop_timeout, backup_continue_on_failure)
    - The just-shipped Plan 01 amended roles/<role>/tasks/backup.yml files (verify the `backup_timestamp_override` consumer is in place before wiring this orchestrator)
  </read_first>
  <action>
    Create `playbooks/backup_docker.yml` from scratch with the following exact structure (no `roles:` block -- explicit `include_role` per D-149 + D-193).

    1. File header (comments lines 1-N):
       - `---` YAML doc start.
       - Comment block describing: M1 backup orchestrator (Docker target); calls 4 per-role tasks/backup.yml files in forward-deploy order (garage -> prometheus -> grafana -> alertmanager, NOT reverse -- different from undeploy_docker.yml because backup is content-dependency-ordered: storage first); uses `include_role` not `roles:` block (D-149); `tags: always` on banner + timestamp pre_tasks so they fire under `--tags <role>` (D-186, D-191, Shared Pattern 4); single shared timestamp per D-191; bail-out vs continue-on-failure via `any_errors_fatal` per D-184. Include 4-line Usage block showing: (a) the default full-run `ansible-playbook -i inventory/example-homelab playbooks/backup_docker.yml --ask-vault-pass`; (b) per-role `--tags <role>` (e.g. `--tags garage`); (c) cross-cutting `--tags backup` (selects all 4 role include_role calls via the per-include `[<role>, backup]` tag list -- the SC4 cross-cutting invocation form); (d) opt-in continue-on-failure `--extra-vars backup_continue_on_failure=true`.

    2. Play header:
       - `- name: Telemetron -- back up Docker host stateful roles`
       - `hosts: telemetron`
       - `gather_facts: true`  (needed for `ansible_date_time` fallbacks downstream; matches deploy/undeploy)
       - `become: false`  (per-task `become: true` on host commands; play-level false matches undeploy/deploy)
       - `collections: [community.docker]`  (Shared Pattern 1; not strictly required here since orchestrator does not call docker_container_info directly, but kept for style consistency with deploy/undeploy/smoke_test)
       - `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"`  (D-184 -- VERBATIM this Jinja2 expression)

    3. `vars:` block:
       - `backup_continue_on_failure: false`  (D-184 default; operator opts in via `--extra-vars`; comment cites D-184)

    4. `pre_tasks:` (3 tasks, all with `tags: [always]` per Shared Pattern 4):

       Task 4a -- the banner (D-186; mirror Pattern B from PATTERNS.md):
         `- name: Banner -- backup invocation context (D-186; tags: always for --tags <role> visibility)`
         `  ansible.builtin.debug:`
         `    msg: |`
                  Backup destination: {{ backup_dest_root }}/<role>/
                  backup_continue_on_failure={{ backup_continue_on_failure | default(false) }}
                    {{ '(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)' if (backup_continue_on_failure | default(false) | bool) else '(first role failure will abort the playbook)' }}
                  backup_stop_timeout={{ backup_stop_timeout }}s
         `  tags: [always]`
         Note: the `<role>` token in line 1 is the literal four-char string `<role>` (not a Jinja2 substitution) -- D-186 explicitly avoids enumerating role names so the banner is stable across role additions. Operators read it as "one tarball per role under that root".

       Task 4b -- generate the shared timestamp once (D-191; Pattern C):
         `- name: Generate shared backup timestamp (D-191 ISO 8601 basic UTC)`
         `  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ`
         `  register: backup_ts`
         `  changed_when: false`
         `  tags: [always]`

       Task 4c -- promote to set_fact (D-191; Pattern C):
         `- name: Publish shared timestamp as backup_timestamp_shared fact`
         `  ansible.builtin.set_fact:`
         `    backup_timestamp_shared: "{{ backup_ts.stdout }}"`
         `  tags: [always]`

    5. `tasks:` block -- 4 include_role calls in forward-deploy order (per ROADMAP SC1 and PATTERNS.md "Established Patterns" note that backup order is content-dependency-driven, NOT reverse-of-deploy). For EACH role in [garage, prometheus, grafana, alertmanager]:

       `- name: Invoke <role> backup`
       `  ansible.builtin.include_role:`
       `    name: <role>`
       `    tasks_from: backup`
       `  vars:`
       `    backup_timestamp_override: "{{ backup_timestamp_shared }}"`
       `  tags:`
       `    - <role>`
       `    - backup`

       Use the TWO-element tag list `[<role>, backup]` on every include_role per SC4. Rationale: with dynamic `include_role`, Ansible resolves tags at the include-task level BEFORE descending into the role body, so the included `tasks/backup.yml`'s own block-level `[<role>, backup]` tags are NOT visible at play-level tag-selection time. Adding `backup` to the include-task tag list is the ONLY mechanism that makes `--tags backup` cross-cutting work for dynamic includes. The per-role `<role>` tag still works for `--tags <role>` single-role invocations.

    6. NO `post_tasks:` block (D-193 -- backup orchestrator does not need shared-resource cleanup; per-role tasks own their own restart guarantee via block/rescue/always).

    Constraints:
    - English-only per CLAUDE.md.
    - NO `WARNING: irreversible --` prefix (backup is not destructive -- D-187 prefix is restore-only).
    - NO role enumeration in the banner -- this is a locked decision (D-186) so banner stays stable when future roles are added.
    - NO `restore_continue_on_failure` knob (out of scope; restore is destructive and bails out unconditionally per D-185).
    - NO `block:` at orchestrator level (PATTERNS.md "No existing block:/rescue:/always: precedent at orchestrator level").
    - NO `set_fact` to `backup_timestamp_effective` at play level -- that fact is intentionally per-role (the override-vs-inline-default resolution happens inside each role's tasks/backup.yml via Plan 01).
    - The `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }` MUST be present on EACH of the 4 include_role calls (do not move to play-level vars -- that would also affect the include_role's nested scope but is less explicit and brittle).

    Per Claude's Discretion (CONTEXT.md "Claude's Discretion"):
    - SKIP the backup-orchestrator success summary (the per-role `state` task in each tasks/backup.yml already logs the tarball path; an orchestrator summary adds noise without value -- mirror the undeploy_docker.yml convention which also has no success summary).
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        # File exists and is non-empty
        test -s playbooks/backup_docker.yml
        # YAML parses (catches indentation errors syntax-check misses)
        python3 -c "import yaml; yaml.safe_load(open(\"playbooks/backup_docker.yml\"))"
        # Required structural elements -- each must appear at least once
        grep -q "hosts: telemetron" playbooks/backup_docker.yml
        # any_errors_fatal one-liner: content match (W-2 -- loosen from quote-exact to content match)
        grep -E "any_errors_fatal.*not.*backup_continue_on_failure" playbooks/backup_docker.yml
        # Parallel semantic YAML check for the same Jinja2 expression
        python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(\"playbooks/backup_docker.yml\")))
play = docs[0][0]
expr = play.get(\"any_errors_fatal\",\"\")
assert \"not\" in expr and \"backup_continue_on_failure\" in expr, f\"any_errors_fatal expr unexpected: {expr!r}\"
"
        grep -q "backup_continue_on_failure: false" playbooks/backup_docker.yml
        grep -q "command: date -u +%Y%m%dT%H%M%SZ" playbooks/backup_docker.yml
        grep -q "backup_timestamp_shared:" playbooks/backup_docker.yml
        # All 4 include_role calls present, in forward order
        grep -E "name:\\s+(garage|prometheus|grafana|alertmanager)" playbooks/backup_docker.yml | wc -l | xargs -I{} test {} -ge 4
        # Each include_role carries the override vars
        grep -c "backup_timestamp_override:" playbooks/backup_docker.yml | xargs -I{} test {} -ge 4
        # tasks_from: backup appears 4 times
        test "$(grep -c "tasks_from: backup" playbooks/backup_docker.yml)" -eq 4
        # Order check: garage line < prometheus line < grafana line < alertmanager line for the include_role name keys
        g=$(grep -n "name: garage" playbooks/backup_docker.yml | head -1 | cut -d: -f1)
        p=$(grep -n "name: prometheus" playbooks/backup_docker.yml | head -1 | cut -d: -f1)
        r=$(grep -n "name: grafana" playbooks/backup_docker.yml | head -1 | cut -d: -f1)
        a=$(grep -n "name: alertmanager" playbooks/backup_docker.yml | head -1 | cut -d: -f1)
        test "$g" -lt "$p" && test "$p" -lt "$r" && test "$r" -lt "$a"
        # tags: always appears on banner + 2 timestamp pre_tasks (>=3 occurrences) -- W-3 strip comments first
        n=$(grep -v "^[[:space:]]*#" playbooks/backup_docker.yml | grep -E "^\\s+-\\s+always" | wc -l)
        test "$n" -ge 3
        # SC4 cross-cutting `backup` tag appears AT LEAST 4 times (once per include_role) -- comment-stripped
        nb=$(grep -v "^[[:space:]]*#" playbooks/backup_docker.yml | grep -E "^\\s+-\\s+backup\\s*$" | wc -l)
        test "$nb" -ge 4
        # NO destructive prefix
        if grep -q "WARNING: irreversible" playbooks/backup_docker.yml; then echo "FAIL: backup orchestrator must not use destructive prefix"; exit 1; fi
        # Syntax-check against the shipped example inventory (which IS in-repo)
        ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml
        # SC4 cross-cutting tag enumeration: --list-tasks --tags backup must enumerate all 4 role include_role lines
        # Match the include_role task name line ("Invoke <role> backup") -- safer than matching the internal "include_role" string Ansible may render differently
        nlist=$(ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml | grep -cE "Invoke (garage|prometheus|grafana|alertmanager) backup")
        test "$nlist" -eq 4 || { echo "FAIL: --tags backup did not enumerate all 4 role include lines (got $nlist)"; exit 1; }
        echo "PASS: backup_docker.yml structurally and syntactically valid; SC4 cross-cutting tag verified"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - `playbooks/backup_docker.yml` exists, is non-empty, and parses as valid YAML via `python3 -c "import yaml; yaml.safe_load(open('playbooks/backup_docker.yml'))"`.
    - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/backup_docker.yml` exits 0 (NOTE: this only validates the play-level structure, not role internals -- per MEMORY.md `feedback_ansible_syntax_check_role_gap.md`).
    - Play declares `hosts: telemetron`, `gather_facts: true`, `become: false`, `collections: [community.docker]`.
    - Play declares an `any_errors_fatal:` Jinja2 expression whose content includes both `not` and `backup_continue_on_failure` (W-2: content match, not quote-style-exact -- D-184 semantic intent preserved even if executor uses single quotes or different whitespace).
    - The same expression loads cleanly via PyYAML and its value contains the two semantic markers.
    - `vars:` block contains `backup_continue_on_failure: false`.
    - `pre_tasks:` contains: (a) banner debug task with `tags: [always]` and the literal 3-line message including `Backup destination:`, `backup_continue_on_failure=`, and `backup_stop_timeout=`; (b) `command: date -u +%Y%m%dT%H%M%SZ` task tagged `[always]`, registered as `backup_ts`; (c) `set_fact: backup_timestamp_shared: "{{ backup_ts.stdout }}"` task tagged `[always]`.
    - `tasks:` contains EXACTLY 4 `include_role` calls -- one each for garage, prometheus, grafana, alertmanager -- in that LITERAL order (forward-deploy order; verified by line-number comparison in the verify script).
    - Each include_role has `tasks_from: backup`, a `vars:` block setting `backup_timestamp_override: "{{ backup_timestamp_shared }}"`, and a `tags: [<role>, backup]` two-element list (`<role>` for `--tags <role>` per-role invocation; `backup` for SC4 cross-cutting `--tags backup` invocation).
    - The comment-stripped count of `- always` tag entries is >= 3 (banner + 2 timestamp pre_tasks), and the comment-stripped count of `- backup` tag entries is >= 4 (one per include_role); both grep guards strip `#`-prefixed lines so trailing comments cannot inflate or hide the count (W-3 mitigation).
    - `ansible-playbook --list-tasks --tags backup -i inventory/example-homelab playbooks/backup_docker.yml` enumerates exactly 4 lines matching `Invoke (garage|prometheus|grafana|alertmanager) backup` (B-1 SC4 cross-cutting gate).
    - NO `post_tasks:` block (D-193 -- backup orchestrator does not need one).
    - NO occurrence of `WARNING: irreversible --` (backup is not destructive; D-187 prefix is restore-only).
    - NO occurrence of `block:` at orchestrator level.
    - NO occurrence of `roles:` block (D-149 lock: include_role only).
    - File header includes a Usage block showing the `--ask-vault-pass`, `--tags <role>`, `--tags backup` (cross-cutting), and `--extra-vars backup_continue_on_failure=true` invocation forms.
    - `git diff --stat` shows exactly 1 new file `playbooks/backup_docker.yml` and no other changes.
  </acceptance_criteria>
  <done>
    `playbooks/backup_docker.yml` is the M1 backup orchestrator. A `ansible-playbook -i inventory/example-homelab playbooks/backup_docker.yml --ask-vault-pass` invocation would (against a live host): print the D-186 banner, generate one shared timestamp, run garage/prometheus/grafana/alertmanager tasks/backup.yml in that order with all 4 tarball filenames carrying the shared timestamp, and abort the play on the first role's failure unless `backup_continue_on_failure=true` is supplied. `--tags garage` (or any of the other 3) runs only that role plus the always-tagged pre_tasks. `--tags backup` (SC4 cross-cutting) runs all 4 roles plus the always-tagged pre_tasks. `--tags loki` (or any other stateless role) matches nothing and exits 0 (SC1).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Ansible CLI `--extra-vars` -> play vars scope | Operator-supplied `backup_continue_on_failure` flips the destructive vs safe-default behavior of multi-role coordination. Misuse leaves an operator believing backups succeeded when they partially failed. |
| Play scope -> role task scope | The `vars:` block on each include_role propagates `backup_timestamp_override` into the role; tampering here would let one role's tarball carry a different timestamp than the other 3 (defeating the shared-timestamp UX). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-04 (T4) | Tampering | Standalone `include_role: name=<role> tasks_from=backup` from a custom playbook | mitigate | Plan 01's `default(backup_timestamp.stdout)` fallback in each tasks/backup.yml. Standalone caller does not need to pass `backup_timestamp_override`; per-role inline date still works. Acceptance for Plan 01 enforces this. |
| T-14-05 | Repudiation | Bail-out under default (`backup_continue_on_failure=false`) -- operator unaware which roles ran | mitigate | `any_errors_fatal` causes Ansible's PLAY RECAP to surface the exact failing role inline. Banner restates the knob status at play start so the operator sees "(first role failure will abort the playbook)" before any role runs. |
| T-14-06 (related to T2) | Denial of Service | Per-role tasks/backup.yml stops the container; on bail-out the per-role `block:`/`rescue:`/`always:` from Phase 13 restarts the container before the play aborts | mitigate | This plan does NOT introduce new failure paths -- Phase 13's per-role `always:` block owns container-restart guarantee. Orchestrator-level bail-out is on a role boundary, AFTER that role's always: fires. |
| T-14-07 | Information Disclosure | Banner echoes the destination path -- if `backup_dest_root` were set to a world-readable location like `/tmp/` by a careless operator, banner would advertise it | accept | `backup_dest_root` defaults to `/opt/telemetron/backups` per group_vars and the per-role tasks set the dir mode to 0700 (Phase 13 contract). ASVS L1. |
</threat_model>

<verification>
- Static checks only in this plan (no live UAT here -- live UAT lives in Plan 04 / 14-HUMAN-UAT.md).
- Plan 04's scenario 4a (`--tags garage`) exercises the per-role tag selection and shared-timestamp propagation against leviathan.
- Plan 04's scenario 4d (`--tags backup` cross-cutting) exercises the SC4 cross-cutting tag against leviathan.
- Plan 04's scenario 3 (fault-injection) exercises both `any_errors_fatal` paths (default-bail and `backup_continue_on_failure=true`).
- The orchestrator does NOT have its own `tasks/verify.yml`-style automated check; the included roles each ship a verify step inside their tasks/backup.yml block.
- `--list-tasks --tags backup` static-check is the play-level gate proving SC4 cross-cutting works WITHOUT requiring a live host.
</verification>

<success_criteria>
- BACKUP-V13-05: `backup_docker.yml` exists with the 4 stateful roles in forward-deploy order and the D-186 banner.
- OPS-V13-02: `any_errors_fatal` Jinja2 expression at play level provides default-bail + opt-in continue-on-failure.
- OPS-V13-03 (backup side): per-role `tags: [<role>, backup]` on each include_role; banner + timestamp pre_tasks tagged `[always]` so they fire under `--tags <role>` invocations; stateless-tag invocation produces empty 0-task play.
- SC4 cross-cutting: `--tags backup` selects all 4 role include_role calls (proven by the `--list-tasks --tags backup` verify gate).
</success_criteria>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-02-SUMMARY.md` when done.
</output>
