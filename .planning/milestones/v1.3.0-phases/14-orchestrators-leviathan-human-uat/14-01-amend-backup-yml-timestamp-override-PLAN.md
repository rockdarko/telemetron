---
phase: 14-orchestrators-leviathan-human-uat
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - roles/garage/tasks/backup.yml
  - roles/prometheus/tasks/backup.yml
  - roles/grafana/tasks/backup.yml
  - roles/alertmanager/tasks/backup.yml
autonomous: true
requirements:
  - BACKUP-V13-05

must_haves:
  truths:
    - "All 4 stateful-role tasks/backup.yml files accept an orchestrator-supplied backup_timestamp_override variable."
    - "When backup_timestamp_override is undefined (standalone include_role invocation), the existing per-role inline `date -u +%Y%m%dT%H%M%SZ` value is used unchanged (zero behavior change for standalone callers)."
    - "When backup_timestamp_override is set (orchestrator invocation), every tarball filename in this role uses the override value."
    - "ansible-playbook --syntax-check on a wrapper that include_roles each of the 4 backup.yml files exits 0."
  artifacts:
    - path: "roles/garage/tasks/backup.yml"
      provides: "Garage backup tasks with backup_timestamp_effective set_fact + 2 filename consumer sites rewritten."
      contains: "backup_timestamp_override | default(backup_timestamp.stdout)"
    - path: "roles/prometheus/tasks/backup.yml"
      provides: "Prometheus backup tasks with backup_timestamp_effective set_fact + 2 filename consumer sites rewritten."
      contains: "backup_timestamp_override | default(backup_timestamp.stdout)"
    - path: "roles/grafana/tasks/backup.yml"
      provides: "Grafana backup tasks with backup_timestamp_effective set_fact + 2 filename consumer sites rewritten."
      contains: "backup_timestamp_override | default(backup_timestamp.stdout)"
    - path: "roles/alertmanager/tasks/backup.yml"
      provides: "Alertmanager backup tasks with backup_timestamp_effective set_fact + 2 filename consumer sites rewritten."
      contains: "backup_timestamp_override | default(backup_timestamp.stdout)"
  key_links:
    - from: "roles/<role>/tasks/backup.yml set_fact: backup_timestamp_effective"
      to: "filename construction lines (tar create dest + post-create stat path)"
      via: "Jinja2 variable substitution"
      pattern: "backup_timestamp_effective"
    - from: "playbooks/backup_docker.yml (Plan 02) include_role vars block"
      to: "roles/<role>/tasks/backup.yml backup_timestamp_override consumer"
      via: "include_role `vars:` keyword propagation"
      pattern: "backup_timestamp_override:"
---

<objective>
Amend the 4 stateful-role tasks/backup.yml files so each accepts an orchestrator-supplied `backup_timestamp_override` variable per D-191 while preserving standalone-call behavior. Insert a single `set_fact: backup_timestamp_effective: "{{ backup_timestamp_override | default(backup_timestamp.stdout) }}"` task after the existing `register: backup_timestamp` task and before the cold-quiesce `block:`; then rewrite the 2 filename consumer sites in each file from `backup_timestamp.stdout` to `backup_timestamp_effective`.

Purpose: this is the prerequisite for the shared-timestamp behavior `playbooks/backup_docker.yml` (Plan 02) introduces. Without it, the orchestrator's `vars: { backup_timestamp_override: ... }` propagation is a silent no-op and the 4 tarballs from a single backup run end up with 4 different timestamps (operator-hostile for `--from=<ts>` matching during restore).
Output: 4 amended files (3 new task entries per file -- the set_fact -- plus 2 in-place substitutions per file). No file added, none deleted.
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
@.planning/phases/13-per-role-backup-restore-tasks/13-CONTEXT.md

@roles/garage/tasks/backup.yml
@roles/prometheus/tasks/backup.yml
@roles/grafana/tasks/backup.yml
@roles/alertmanager/tasks/backup.yml

<interfaces>
<!-- The single new fact this plan creates is consumed by Plan 02 -->
<!-- (playbooks/backup_docker.yml). Plan 02 passes the override via the include_role -->
<!-- `vars:` block. Plan 03 (restore_docker.yml) does NOT use these tasks. -->

Variable contract for each amended tasks/backup.yml:

input  : backup_timestamp_override  (string, optional, default undefined)
                                    Set by orchestrator caller via include_role `vars:`.
                                    Format: ISO 8601 basic UTC YYYYMMDDTHHMMSSZ
                                    (matches `date -u +%Y%m%dT%H%M%SZ` output).

inline : backup_timestamp.stdout    (string, registered by existing `command: date`)
                                    Per-role per-invocation inline value.

derived: backup_timestamp_effective (string, set_fact)
                                    = backup_timestamp_override | default(backup_timestamp.stdout)
                                    Consumed by ALL filename construction sites in the file.

consumer: tar dest + post-create stat path
          `{{ backup_dest_root }}/<role>/<role>-{{ backup_timestamp_effective }}.tar.zst`
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Amend the 4 tasks/backup.yml files in lockstep -- insert set_fact and rewrite filename sites</name>
  <files>roles/garage/tasks/backup.yml, roles/prometheus/tasks/backup.yml, roles/grafana/tasks/backup.yml, roles/alertmanager/tasks/backup.yml</files>
  <read_first>
    - roles/garage/tasks/backup.yml (current shape; line 81 registers backup_timestamp; lines 173 + 188 are the two filename sites)
    - roles/prometheus/tasks/backup.yml (current shape; line 67 registers; lines 122 + 132 are filename sites)
    - roles/grafana/tasks/backup.yml (current shape; line 76 registers; lines 129 + 139 are filename sites)
    - roles/alertmanager/tasks/backup.yml (current shape; line 107 registers; lines 151 + 159 are filename sites)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-PATTERNS.md sections "3. roles/garage/tasks/backup.yml", "4. roles/prometheus/tasks/backup.yml", "5. roles/grafana/tasks/backup.yml", "6. roles/alertmanager/tasks/backup.yml" (Pattern K with verbatim BEFORE/AFTER excerpts)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md D-191 (the "Option B" path: always call date, then set_fact -- minimum-diff)
    - .planning/phases/13-per-role-backup-restore-tasks/13-CONTEXT.md (Phase 13 contract -- standalone include_role: tasks_from=backup must still work unchanged)
  </read_first>
  <action>
    Per D-191 (CONTEXT.md), implement Option B (always call date, then set_fact) for minimum diff. For EACH of the 4 files (garage, prometheus, grafana, alertmanager) apply the SAME 3-step recipe:

    Step A (insert one new task): IMMEDIATELY AFTER the existing `register: backup_timestamp` task (which keeps its current shape: `ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ`, `register: backup_timestamp`, `changed_when: false`, with its existing `tags: [<role>, backup]` block), insert a new task:

      - name: Resolve effective backup timestamp (D-191 orchestrator override or inline)
        ansible.builtin.set_fact:
          backup_timestamp_effective: "{{ backup_timestamp_override | default(backup_timestamp.stdout) }}"
        tags:
          - <role>
          - backup

    where <role> is the role name (garage / prometheus / grafana / alertmanager). Add a one-line comment above the task referencing D-191 and stating the standalone-default fallback.

    Step B (rewrite filename construction site #1 -- the `tar` create dest): replace the EXACT string `{{ backup_timestamp.stdout }}` with `{{ backup_timestamp_effective }}` at the lines listed below per file. The surrounding YAML structure (tar create task, dest path) is unchanged; only the variable name in the Jinja2 expression changes.

    Step C (rewrite filename construction site #2 -- the post-create stat path): same exact substitution at the second line listed per file.

    Per-file exact line numbers and exact strings:

    File: roles/garage/tasks/backup.yml
      - Set_fact insertion point: AFTER line 86 (current `tags: [garage, backup]` block close of the existing date task), BEFORE the cold-quiesce `block:` opener.
      - Filename site #1: line 173 -- replace `{{ backup_timestamp.stdout }}` with `{{ backup_timestamp_effective }}` (full surrounding context: `{{ backup_dest_root }}/garage/garage-{{ backup_timestamp.stdout }}.tar.zst` becomes `{{ backup_dest_root }}/garage/garage-{{ backup_timestamp_effective }}.tar.zst`).
      - Filename site #2: line 188 -- same substitution.
      - Tags on inserted task: `[garage, backup]`.

    File: roles/prometheus/tasks/backup.yml
      - Set_fact insertion point: AFTER line 71 (existing date task `tags: [prometheus, backup]` close), BEFORE the cold-quiesce `block:` opener at line 83.
      - Filename site #1: line 122 -- replace `{{ backup_timestamp.stdout }}` with `{{ backup_timestamp_effective }}`.
      - Filename site #2: line 132 -- same substitution.
      - Tags on inserted task: `[prometheus, backup]`.

    File: roles/grafana/tasks/backup.yml
      - Set_fact insertion point: AFTER line 80 (existing date task `tags: [grafana, backup]` close), BEFORE the cold-quiesce `block:` opener.
      - Filename site #1: line 129 -- replace `{{ backup_timestamp.stdout }}` with `{{ backup_timestamp_effective }}`.
      - Filename site #2: line 139 -- same substitution.
      - Tags on inserted task: `[grafana, backup]`.

    File: roles/alertmanager/tasks/backup.yml
      - Set_fact insertion point: AFTER line 111 (existing date task `tags: [alertmanager, backup]` close), BEFORE the cold-quiesce `block:` opener at line 116.
      - Filename site #1: line 151 -- replace `{{ backup_timestamp.stdout }}` with `{{ backup_timestamp_effective }}`.
      - Filename site #2: line 159 -- same substitution.
      - Tags on inserted task: `[alertmanager, backup]`.

    Constraints (do NOT change):
    - Do NOT change the existing `register: backup_timestamp` task -- it must stay so the fallback branch keeps working.
    - Do NOT delete `backup_timestamp.stdout` from the file -- it is referenced inside the new set_fact's default() call.
    - Do NOT add `backup_timestamp_override` to roles/<role>/defaults/main.yml. It is intentionally undefined-by-default; the `default(...)` filter handles the unset case. Adding a default to defaults/main.yml would invert the precedence and silently break orchestrator override propagation.
    - Do NOT modify roles/<role>/tasks/restore.yml in this plan -- restore reads `backup_restore_from`, not `backup_timestamp_override`, and is already correct per D-190.
    - English-only naming per CLAUDE.md.
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        # Each amended file must contain the literal set_fact expression
        for f in roles/garage/tasks/backup.yml roles/prometheus/tasks/backup.yml roles/grafana/tasks/backup.yml roles/alertmanager/tasks/backup.yml; do
          grep -q "backup_timestamp_override | default(backup_timestamp.stdout)" "$f" || { echo "MISS: $f missing set_fact"; exit 1; }
          # Each file must NO LONGER reference backup_timestamp.stdout in filename construction (only inside the default() call).
          # Filter that one allowed line, then assert no other occurrences in *-{{ backup_timestamp.stdout }}.tar.zst contexts.
          if grep -E "backup_timestamp\.stdout" "$f" | grep -E "\.tar\.zst" >/dev/null; then echo "FAIL: $f still has backup_timestamp.stdout in filename"; exit 1; fi
          # And each file must reference backup_timestamp_effective in BOTH filename sites (>=2 occurrences in .tar.zst context).
          n=$(grep -E "backup_timestamp_effective" "$f" | grep -cE "\.tar\.zst" || true)
          if [ "$n" -lt 2 ]; then echo "FAIL: $f has only $n filename references to backup_timestamp_effective (expected >= 2)"; exit 1; fi
        done
        # YAML lint each amended file (validates indentation of the inserted set_fact task)
        for f in roles/garage/tasks/backup.yml roles/prometheus/tasks/backup.yml roles/grafana/tasks/backup.yml roles/alertmanager/tasks/backup.yml; do
          python3 -c "import yaml,sys; yaml.safe_load(open(\"$f\"))" || { echo "FAIL: YAML parse on $f"; exit 1; }
        done
        echo "PASS: all 4 backup.yml files amended correctly"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - For each of {roles/garage/tasks/backup.yml, roles/prometheus/tasks/backup.yml, roles/grafana/tasks/backup.yml, roles/alertmanager/tasks/backup.yml}:
      - File contains the EXACT literal string `backup_timestamp_override | default(backup_timestamp.stdout)` (one occurrence per file, in the new set_fact task).
      - File contains AT LEAST TWO occurrences of `backup_timestamp_effective` in `.tar.zst` filename contexts (the rewritten tar-create dest + post-create stat path).
      - File contains ZERO occurrences of `backup_timestamp.stdout` in any `.tar.zst` filename context (the only remaining reference must be inside the new set_fact's `default(...)` call).
      - `python3 -c "import yaml; yaml.safe_load(open('<file>'))"` exits 0 (validates the inserted task's indentation is correct -- guarding against the `--syntax-check skips role internals` gap from MEMORY.md `feedback_ansible_syntax_check_role_gap.md`).
      - The new `set_fact` task carries `tags: [<role>, backup]` matching the role.
      - The existing `register: backup_timestamp` task is UNCHANGED (still calls `ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ`, still registers `backup_timestamp`, still `changed_when: false`, still tagged `[<role>, backup]`).
      - The cold-quiesce `block:` opener and its child tasks are UNCHANGED.
    - No new role defaults var added (verify `git diff roles/<role>/defaults/main.yml` shows no change for any of the 4 roles).
    - `git diff --stat` shows exactly 4 files modified and no files created or deleted.
  </acceptance_criteria>
  <done>
    All 4 stateful-role tasks/backup.yml files have a `backup_timestamp_effective` set_fact derived from `backup_timestamp_override | default(backup_timestamp.stdout)`; all filename construction sites use the new fact; standalone `include_role: name=<role> tasks_from=backup` (no orchestrator override) produces tarballs with the per-role inline timestamp exactly as before Phase 14; orchestrator `include_role` with `vars: { backup_timestamp_override: "<ts>" }` produces tarballs with the override timestamp. YAML loads cleanly in Python. No regression to Phase 13 standalone behavior.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| orchestrator caller -> role task scope | The orchestrator's `vars:` block on `include_role` crosses into role-task variable scope. Unchecked input here would let a caller inject arbitrary strings into filename construction. |
| role task -> host filesystem | Filename construction writes to `/opt/telemetron/backups/<role>/`. Tainted timestamps could path-traverse or overwrite unrelated tarballs. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-01 (T4) | Tampering | Standalone `include_role: tasks_from=backup` caller (custom playbook without orchestrator) | mitigate | `default(backup_timestamp.stdout)` fallback in the new `set_fact` -- the inline `date -u +%Y%m%dT%H%M%SZ` is always called and always usable. Standalone callers see ZERO behavior change. Acceptance criteria explicitly verifies no Phase 13 regression. |
| T-14-02 | Tampering | `backup_timestamp_override` value injection from a malicious orchestrator caller | accept | The orchestrator is in-tree code under repo review; no external/network-supplied path reaches this var. Format risk is bounded -- a malformed value just makes the filename ugly; it does not escape the `{{ backup_dest_root }}/<role>/<role>-` prefix because Ansible templating does not unescape backslashes / slashes in the Jinja2 expression context. ASVS L1 OK. |
| T-14-03 | Repudiation | Lost association between orchestrator run and per-role tarball | mitigate | The single shared timestamp Plan 02 generates becomes the filename suffix on ALL 4 tarballs in one run, so an operator can immediately identify "these 4 tarballs are from one orchestrator invocation" by `ls /opt/telemetron/backups/*/*.tar.zst | grep <ts>`. |
</threat_model>

<verification>
- `ansible-playbook` --syntax-check is INSUFFICIENT for role internals (MEMORY.md: `feedback_ansible_syntax_check_role_gap.md`). Verification uses `python3 -c "import yaml; yaml.safe_load(...)"` per amended file to catch indentation defects in the inserted set_fact.
- The Plan 02 orchestrator (next wave) will exercise the override path end-to-end; this plan's verification is the static-check / regression-guard layer.
- Phase 13 standalone-call regression guard: file contents must still produce a valid timestamp when `backup_timestamp_override` is unset -- the `default()` fallback covers this.
</verification>

<success_criteria>
- 4 files modified (no new files, no deletions).
- Each file has 1 new `set_fact: backup_timestamp_effective` task tagged `[<role>, backup]`.
- Each file has exactly 2 filename construction sites rewritten from `backup_timestamp.stdout` to `backup_timestamp_effective`.
- All 4 files parse as valid YAML via `python3 -c "import yaml; yaml.safe_load(...)"`.
- Phase 13 standalone-call behavior preserved: with `backup_timestamp_override` unset, the inline `backup_timestamp.stdout` is used (verified by inspection of the `default()` filter in the new set_fact).
- `git diff` is minimal: roughly 7 lines added per file (new set_fact task), 2 lines changed in-place per file (filename sites).
</success_criteria>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-01-SUMMARY.md` when done.
</output>
