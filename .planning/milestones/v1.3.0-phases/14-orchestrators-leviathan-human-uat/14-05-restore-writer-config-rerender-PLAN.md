---
phase: 14-orchestrators-leviathan-human-uat
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - playbooks/restore_docker.yml
  - roles/garage/tasks/restore.yml
autonomous: true
gap_closure: true
requirements:
  - RESTORE-V13-05
  - UAT-V13-01
requirements_addressed:
  - UAT-V13-01
  - RESTORE-V13-05

must_haves:
  truths:
    - "G-01 closed: After `restore_docker.yml` runs end-to-end on leviathan via `14-HUMAN-UAT.md` scenario 1 step 6, Loki + Tempo + Mimir come back HEALTHY against the restored Garage `s3-credentials` key WITHOUT a manual `deploy_docker.yml --tags loki,tempo,mimir,garage` workaround."
    - "SC6 (ROADMAP.md Phase 14 #6) flips from FAILED to VERIFIED: `restore_docker.yml` step in the 7-step round-trip completes with `PLAY RECAP failed=0` and no manual intervention."
    - "Writer configs (`/opt/telemetron/{loki,tempo,mimir}/<role>.yaml`) on the host are re-rendered from the restored `{{ garage_s3_credentials_file }}` (so `access_key_id` / `access_key` matches the restored Garage DB) BEFORE the writers are unblocked."
    - "`include_role: name=loki tasks_from=main` (and tempo, mimir) is called between the Garage restore and the writer-restart step -- the role's `main.yml` template task re-renders writer config from `garage_s3_credentials_file` and the `notify: restart <writer>` handler is flushed via `meta: flush_handlers` immediately after so the writer picks up the fresh config before the subsequent healthy-poll."
    - "After Garage restore, `garage_s3_access_key_id` and `garage_s3_secret_key` are populated as facts so subsequent writer-config re-renders resolve `loki_s3_access_key` / `tempo_s3_access_key` / `mimir_s3_access_key` correctly. Without this fact-population step, the writer templates would fail with `AnsibleUndefinedVariable: 'garage_s3_access_key_id' is undefined` because `roles/garage/tasks/restore.yml` (pre-fix) restores the host credentials file but never slurp+set_fact's the in-memory facts that the writer templates lazy-resolve through `inventory/.../secrets.yml`. The canonical pattern lives at `roles/garage/tasks/bootstrap.yml:127-147` (Step 7b + 7c -- slurp `garage_s3_credentials_file`, then set_fact `garage_s3_access_key_id` and `garage_s3_secret_key` via the `(?m)^key_id=...` / `(?m)^secret=...` regex_search idiom). This plan adds the same pair of tasks to the END of `roles/garage/tasks/restore.yml` so they fire under both `--tags garage` and `--tags restore` AND benefit any future `include_role: name=garage tasks_from=restore` invocation (per-role-gate path), not just the orchestrator path."
    - "D-183's locked assumption -- `Garage S3 endpoint and credentials haven't changed [...] no config re-render needed` -- is REVERSED based on G-01 field evidence. The post-purge redeploy at step 5 of the round-trip re-runs Garage bootstrap which generates a NEW S3 key (because the host credentials file was removed by the purge); writer configs are templated against that NEW key; then `restore_docker.yml` overwrites the credentials file with the ORIGINAL pre-backup key but leaves writer configs holding the post-purge key. Result: writers crash-loop with `Forbidden: No such key:` against the restored Garage. The re-render step closes this drift. D-183's restart-via-`docker start` mechanism is PRESERVED; only the `no config re-render needed` assumption is reversed."
    - "Idempotency preserved: a second `restore_docker.yml` run against the same backup is a no-op for the writer-rerender step when configs already match (template task reports `changed=false`, no handler fires, no restart)."
    - "Tag UX preserved: the new writer-rerender tasks carry `tags: [garage, restore]` so they fire under `--tags garage` (per D-189 amended -- the writer-rerender is a Garage-restore prerequisite, same identity as writer-stop / writer-restart) AND under `--tags restore` cross-cutting (SC4). They do NOT fire under `--tags loki/tempo/mimir/prometheus/grafana/alertmanager`."
    - "The incorrect comment at lines 186-191 of `restore_docker.yml` is replaced with the correct rationale (writer configs must be re-rendered from the restored s3-credentials file BEFORE writers are started; the post-purge-redeploy left writer configs holding the wrong S3 key)."
    - "`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` exits 0. NOTE: `--syntax-check` is STRUCTURAL-ONLY -- it does NOT catch undefined-variable runtime failures (per MEMORY.md `feedback_ansible_syntax_check_role_gap.md`). Runtime correctness of the writer rerender is empirically verified by Plan 14-07 scenario 1 step 6 PLAY RECAP `failed=0` AND absence of `Forbidden: No such key:` errors in Loki/Tempo/Mimir container logs. This plan is structurally complete when the syntax check and the YAML-round-trip assertions pass; behavioral correctness is Plan 14-07's empirical gate."
  artifacts:
    - path: "playbooks/restore_docker.yml"
      provides: "Confirm-gated restore orchestrator with writer-quiesce + writer-config-rerender bracket around Garage restore."
      min_lines: 250
      contains: "include_role"
    - path: "roles/garage/tasks/restore.yml"
      provides: "Confirm-gated Garage restore with post-restore slurp + set_fact of garage_s3_access_key_id / garage_s3_secret_key so downstream writer templates resolve correctly."
      min_lines: 380
      contains: "set_fact"
  key_links:
    - from: "Garage `include_role: name=garage tasks_from=restore` (restores volumes + writes restored `s3-credentials` to host AND now slurp+set_fact's `garage_s3_access_key_id` + `garage_s3_secret_key` at the tail of the role-task)"
      to: "Writer rerender `include_role: name=<writer> tasks_from=main` for loki/tempo/mimir (whose templates lazy-resolve `loki_s3_access_key` / `tempo_s3_access_key` / `mimir_s3_access_key` -> `garage_s3_access_key_id` / `garage_s3_secret_key`)"
      via: "Sequential task ordering in the orchestrator -- Garage restore (including the new fact-population tail) completes BEFORE writer rerender begins; the facts are in scope when the writer templates render"
      pattern: "include_role"
    - from: "`roles/garage/tasks/restore.yml` tail (NEW: slurp `garage_s3_credentials_file` -> set_fact `garage_s3_access_key_id` + `garage_s3_secret_key`)"
      to: "Writer template render `roles/loki/templates/loki.yaml.j2:53-54` (reads `loki_s3_access_key` / `loki_s3_secret_key` which lazy-resolve via `inventory/.../secrets.yml` to `garage_s3_access_key_id` / `garage_s3_secret_key`)"
      via: "Ansible fact propagation across `include_role` boundary -- set_fact'd values are play-level facts, visible to all subsequent include_role invocations on the same host. Verbatim slurp+set_fact shape copied from `roles/garage/tasks/bootstrap.yml:127-147` (Step 7b + 7c)."
      pattern: "set_fact"
    - from: "Writer rerender include_role (notifies `restart <writer>` handler if config changes)"
      to: "`meta: flush_handlers` immediately after"
      via: "Ansible handler flush -- forces restart handlers to fire before the writer-restart healthy-poll runs against the (now correctly configured) container"
      pattern: "flush_handlers"
    - from: "Writer-restart loop (`docker start <writer>`)"
      to: "Writer healthy-poll (`State.Health.Status == 'healthy'`)"
      via: "Existing loop preserved -- handler may have already restarted the container, so `docker start` against an already-running container is acceptable (WR-03 known idempotency caveat preserved; out of scope for this gap-closure)"
      pattern: "docker start"
---

<objective>
G-01 closure. The 7-step round-trip on leviathan fails at step 6 (`restore_docker.yml`) because of a two-stage drift:

1. **Garage S3 key drift across purge+redeploy:** Step 5 of the round-trip (`deploy_docker.yml` after `undeploy_docker.yml --purge-data`) re-runs Garage bootstrap which generates a NEW S3 key (the purge removed the host credentials file). The post-step-5 writer configs on the host (`/opt/telemetron/{loki,tempo,mimir}/<role>.yaml`) are templated against that NEW key. Then step 6's `restore_docker.yml` runs `include_role: name=garage tasks_from=restore` which overwrites the host credentials file with the ORIGINAL pre-backup key -- but leaves the writer configs holding the post-purge key.

2. **In-memory fact drift inside the restore play:** `roles/garage/tasks/restore.yml` (pre-fix) restores the credentials FILE but never slurps+set_fact's the in-memory facts `garage_s3_access_key_id` / `garage_s3_secret_key`. A subsequent `include_role: name=loki tasks_from=main` inside the SAME play would render `loki.yaml.j2:53-54` which reads `loki_s3_access_key` -> (lazy Jinja via secrets.yml) -> `garage_s3_access_key_id`. That fact is UNDEFINED in the play context, so the template render explodes with `AnsibleUndefinedVariable`.

The 14-HUMAN-UAT.md scenario 1 workaround `deploy_docker.yml --tags loki,tempo,mimir,garage` worked because `--tags garage` runs `roles/garage/tasks/main.yml` -> `bootstrap.yml` which slurps the credentials file at lines 127-147 (Step 7b + 7c) and populates the facts as a side-effect; then loki/tempo/mimir templates render against the freshly-loaded facts. The fix must reproduce that side-effect inside the restore play.

This plan applies a TWO-PART fix:

- **Part 1 (`roles/garage/tasks/restore.yml`):** add a slurp + set_fact pair at the END of the role-task (after the existing healthy-poll in the `always:` clause) that populates `garage_s3_access_key_id` and `garage_s3_secret_key` from the just-restored `garage_s3_credentials_file`. VERBATIM shape from `roles/garage/tasks/bootstrap.yml:127-147`. Tagged `[garage, restore]` for consistency. This benefits BOTH the orchestrator path AND any future custom playbook that does `include_role: name=garage tasks_from=restore`.

- **Part 2 (`playbooks/restore_docker.yml`):** insert the writer-config-rerender step between the Garage restore (lines 178-184) and the writer-restart loop (lines 192-204): 3 `include_role: tasks_from=main` calls for loki/tempo/mimir (which re-render their templates against the now-populated facts) + `meta: flush_handlers` to force any notify-driven restarts to fire BEFORE the existing healthy-poll. Replace the misleading lines-186-191 comment block.

Purpose: SC6 flips from FAILED to VERIFIED. The 7-step round-trip completes on leviathan with no manual intervention; RESTORE-V13-05 acceptance criterion -- writers restart against restored Garage -- holds without operator-side post-restore actions.

Output: amended `playbooks/restore_docker.yml` AND `roles/garage/tasks/restore.yml`. No other files changed.
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

@playbooks/restore_docker.yml
@playbooks/deploy_docker.yml
@roles/garage/tasks/restore.yml
@roles/garage/tasks/bootstrap.yml
@roles/garage/defaults/main.yml
@roles/loki/tasks/main.yml
@roles/loki/templates/loki.yaml.j2
@roles/tempo/tasks/main.yml
@roles/mimir/tasks/main.yml
@roles/loki/handlers/main.yml
@roles/tempo/handlers/main.yml
@roles/mimir/handlers/main.yml
@inventory/example-homelab/group_vars/all/secrets.yml.example

<interfaces>
<!-- Variable resolution chain that drives the G-01 fix -->

The writer templates read these per-role vars:
  roles/loki/templates/loki.yaml.j2:53-54   -> loki_s3_access_key  / loki_s3_secret_key
  roles/tempo/templates/tempo.yaml.j2:*     -> tempo_s3_access_key / tempo_s3_secret_key
  roles/mimir/templates/mimir.yaml.j2:*     -> mimir_s3_access_key / mimir_s3_secret_key

Each per-role var is defined in inventory/example-homelab/group_vars/all/secrets.yml.example
lines 42-43 (loki), 48-49 (tempo), and analogous mimir lines as LAZY JINJA INDIRECTIONS:

  loki_s3_access_key:  "{{ garage_s3_access_key_id }}"
  loki_s3_secret_key:  "{{ garage_s3_secret_key }}"

The terminal facts `garage_s3_access_key_id` and `garage_s3_secret_key` are NOT operator-supplied
and NOT in secrets.yml.example (per roles/garage/defaults/main.yml:100-108 comment). They are
ONLY populated at runtime by `roles/garage/tasks/bootstrap.yml` via the slurp + set_fact pair at
lines 127-147 (Step 7b + 7c), with the SAME pattern repeated in the create branch (lines 206-213)
and recovery branch (lines 263-279). All three branches converge on the SAME set_fact shape:

  - name: Load existing Garage S3 credentials from host file
    ansible.builtin.slurp:
      src: "{{ garage_s3_credentials_file }}"
    register: garage_creds_raw
    when: garage_creds_file.stat.exists       # bootstrap-specific guard; restore.yml does NOT need it
    changed_when: false
    tags:
      - garage
      - garage-bootstrap                       # restore.yml uses [garage, restore]

  - name: Set Garage S3 credential facts from host file
    ansible.builtin.set_fact:
      garage_s3_access_key_id: "{{ (garage_creds_raw.content | b64decode) | regex_search('(?m)^key_id=(.+)$', '\\1') | first }}"
      garage_s3_secret_key:    "{{ (garage_creds_raw.content | b64decode) | regex_search('(?m)^secret=(.+)$', '\\1') | first }}"
    when: garage_creds_file.stat.exists       # bootstrap-specific guard; restore.yml does NOT need it
    tags:
      - garage
      - garage-bootstrap                       # restore.yml uses [garage, restore]

Credentials file format (defined by bootstrap.yml Step 7f, lines 215-227):
  key_id=<value>
  secret=<value>
mode 0600, owner root. Phase 13's restore.yml preserves the format (the s3-credentials entry
is extracted verbatim from the backup tarball + mode 0600 re-applied at lines 345-351).

<!-- Why restore.yml needs the slurp+set_fact AT ITS TAIL (not in bootstrap.yml's existing place) -->

bootstrap.yml is NOT called by restore_docker.yml. The orchestrator flow is:
  pre_tasks  -> confirm-gate + banner
  tasks      -> writer-stop loop -> writer-stop poll
             -> include_role: name=garage tasks_from=restore   <-- runs restore.yml, NOT main.yml
             -> [NEW] include_role: name=loki  tasks_from=main
             -> [NEW] include_role: name=tempo tasks_from=main
             -> [NEW] include_role: name=mimir tasks_from=main
             -> [NEW] meta: flush_handlers
             -> writer-restart loop (docker start)
             -> writer healthy-poll
             -> include_role: name=prometheus / grafana / alertmanager  (each tasks_from=restore)

restore.yml currently writes the credentials file but never set_fact's the in-memory facts.
The NEW tail of restore.yml (this fix) populates the facts so the subsequent writer
include_role calls render templates correctly.

<!-- Where the new tasks land in restore.yml -->

Append after the existing `always:` healthy-poll task (currently the last task in
roles/garage/tasks/restore.yml; the file ends at line 376 with `- garage` `- restore`).

The new tasks are OUTSIDE the existing `block: / always:` (they fire only after the
restore completed successfully -- if the block failed, the always: clause ran the
container restart + healthy-poll, but the slurp+set_fact should NOT run on a failed
restore because the file may be corrupt or missing).

Tagging: `[garage, restore]` matches the surrounding role-task convention.

<!-- Writer role surfaces consumed by the new restore_docker.yml rerender step -->

include_role: name=loki  tasks_from=main
  -- roles/loki/tasks/main.yml renders /opt/telemetron/loki/loki.yaml from loki.yaml.j2
     (which now resolves loki_s3_access_key -> garage_s3_access_key_id correctly because
     the new restore.yml tail populated that fact)
  -- `notify: restart loki` (handlers/main.yml: `docker restart {{ loki_container_name }}`)
     fires if template changed
  -- ALSO runs ensure-volume, pull-image, `community.docker.docker_container state=started
     recreate=false`, verify -- all idempotent against an already-deployed writer (writer is
     currently stopped by the writer-stop loop earlier in this play, so docker_container with
     state=started brings it back; verify polls until healthy)

include_role: name=tempo tasks_from=main   -- same shape; template renders /opt/telemetron/tempo/tempo.yaml; notify: restart tempo
include_role: name=mimir tasks_from=main   -- same shape; template renders /opt/telemetron/mimir/mimir.yaml; notify: restart mimir

meta: flush_handlers
  -- Forces queued `restart <writer>` handlers to fire NOW rather than at end-of-play. Critical because if the
     writer-restart loop later in this play sees an already-restarted container, that's fine, but if handlers
     are deferred until end-of-play, the writer-restart healthy-poll will run against a container holding stale
     config -- it will fail and the PLAY will end with the handler then firing too late.

<!-- Interaction with the existing writer-restart loop (lines 192-204 of restore_docker.yml) -->

The existing loop is preserved as-is. Justification:
  - The writer's role main.yml may NOT trigger the handler (if config files happen to match -- unlikely but possible
    on a same-host same-version re-restore). In that case the writers are still in the stopped state from the
    writer-stop loop earlier in this play; the existing `docker start` loop is the unconditional kick that brings
    them back up.
  - If the handler DID fire (the common case), `docker restart` against the now-running container is a no-op-ish
    operation (the existing `docker start` of an already-started container exits 0 on Docker 29 -- this is
    Docker 29's behavior on leviathan; older daemons may emit non-zero, but that's pre-existing WR-03 and out of
    scope for this gap-closure).
  - The healthy-poll after the `docker start` is the actual operational guarantee -- regardless of which path
    restarted the writer, the play waits until State.Health.Status == 'healthy' before continuing.

<!-- Tag inheritance: new tasks carry `tags: [garage, restore]` per D-189 amended -->

Writer rerender include_role + flush_handlers tags: [garage, restore]
  -- D-189 rationale extended: the writer-config-rerender is a Garage-restore PREREQUISITE (writer configs depend
     on Garage's restored s3-credentials), so it shares the same tag list as writer-stop / writer-restart.
  -- `--tags garage`  -> fires the rerender (correct -- garage restore needs writers re-rendered)
  -- `--tags restore` -> fires the rerender (correct -- SC4 cross-cutting)
  -- `--tags loki/tempo/mimir/prometheus/grafana/alertmanager` -> does NOT fire the rerender (correct -- rerender
     is a Garage-restore consequence, not a per-writer-role operation)

<!-- Var resolution gap: same as the existing writer-stop loop already navigates -->

The new include_role calls DO touch loki/tempo/mimir role defaults (unlike the existing inline `docker stop`
loop which hardcodes container names). The include_role itself loads the role's defaults/main.yml on
invocation -- that's an Ansible primitive guarantee. So `garage_s3_credentials_file` (referenced inside
loki.yaml.j2) and `loki_config_dir` etc. all resolve correctly because the include_role brings them into
scope. NO additional vars need to be passed via the orchestrator.

<!-- D-183 LOCKED-DECISION REVERSAL (cited in must_haves and the new comment in restore_docker.yml) -->

D-183 (CONTEXT.md) locked: "Garage S3 endpoint and credentials haven't changed (because Phase 13's Garage
restore restores the s3-credentials host file along with the meta+data volumes), so the writers come back
pointing at the same buckets they were configured for -- no config re-render needed."

REVERSED because the assumption "credentials haven't changed" is wrong in the 7-step round-trip context:
  - Step 5 (post-purge redeploy) regenerates a NEW Garage S3 key (garage bootstrap's first-run branch
    fires because the purge removed the credentials file).
  - Step 5's writer-config render uses that NEW key.
  - Step 6 (restore) overwrites the credentials file with the ORIGINAL pre-backup key.
  - Writer configs are still holding the step-5 key -> drift -> Forbidden: No such key.

D-183 still HOLDS for the same-deploy-no-purge case (restoring within a deploy that didn't bootstrap a new
key); the reversal is specifically for the post-purge-redeploy path the round-trip exercises. The fix is
unconditional (re-render always) because the cost is microseconds and the safety is non-negotiable.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Amend roles/garage/tasks/restore.yml -- slurp + set_fact garage_s3_access_key_id and garage_s3_secret_key after restore</name>
  <files>roles/garage/tasks/restore.yml</files>
  <read_first>
    - roles/garage/tasks/restore.yml (FULL file -- 377 lines; the new tasks land AFTER the closing `tags: - garage / - restore` of the `block:/always:` wrapper, as siblings at the same indentation as the wrapper itself)
    - roles/garage/tasks/bootstrap.yml lines 124-147 (Step 7b + Step 7c -- the CANONICAL slurp + set_fact shape; this task copies that shape verbatim, dropping the bootstrap-specific `when: garage_creds_file.stat.exists` guard because restore.yml just wrote the file unconditionally and the file MUST exist or the restore would have failed already)
    - roles/garage/defaults/main.yml:100-109 (the `garage_s3_credentials_file` definition and the comment block explaining that `garage_s3_access_key_id` + `garage_s3_secret_key` are NOT in secrets.yml and ARE set_fact'd at runtime)
    - inventory/example-homelab/group_vars/all/secrets.yml.example:38-49 (the lazy-Jinja indirection `loki_s3_access_key: "{{ garage_s3_access_key_id }}"` and the analogous tempo/mimir lines -- this is what the new set_fact populates the upstream of)
  </read_first>
  <action>
    Edit `roles/garage/tasks/restore.yml`. APPEND two new tasks to the END of the file (after the existing `always:` healthy-poll task that currently closes the `block:/always:` wrapper -- around line 376). The new tasks are OUTSIDE the `block:` (siblings of it at the same indentation), so they fire ONLY when the restore completed successfully (block + always both finished without raising).

    Verbatim shape from `roles/garage/tasks/bootstrap.yml:127-147` (Step 7b + Step 7c), with TWO changes:
      (a) DROP the `when: garage_creds_file.stat.exists` guard on BOTH tasks. The restore.yml `block:` just extracted the s3-credentials entry from the tarball and re-applied mode 0600; if any of those steps failed, the block raised and we are not in this code path. If we ARE in this code path, the file exists by construction.
      (b) Tag with `[garage, restore]` instead of `[garage, garage-bootstrap]` -- this matches the surrounding role-task convention (every other task in restore.yml carries `[garage, restore]`).

    Insert these exact two tasks at the end of the file:

      - name: Load restored Garage S3 credentials from host file (G-01 fact-population for writer-config re-render)
        ansible.builtin.slurp:
          src: "{{ garage_s3_credentials_file }}"
        register: garage_creds_raw
        changed_when: false
        tags:
          - garage
          - restore

      - name: Set Garage S3 credential facts from restored host file (G-01; mirrors bootstrap.yml:140-147)
        ansible.builtin.set_fact:
          garage_s3_access_key_id: "{{ (garage_creds_raw.content | b64decode) | regex_search('(?m)^key_id=(.+)$', '\\1') | first }}"
          garage_s3_secret_key: "{{ (garage_creds_raw.content | b64decode) | regex_search('(?m)^secret=(.+)$', '\\1') | first }}"
        tags:
          - garage
          - restore

    Add a 3-5 line comment block ABOVE the slurp task explaining: (a) G-01 closure -- writer templates downstream of this role-task lazy-resolve `loki_s3_access_key` / `tempo_s3_access_key` / `mimir_s3_access_key` to these two facts via `inventory/.../secrets.yml`; (b) without this set_fact, a subsequent `include_role: name=loki tasks_from=main` (e.g., from `playbooks/restore_docker.yml` G-01 fix) would fail with `AnsibleUndefinedVariable: 'garage_s3_access_key_id' is undefined`; (c) the slurp targets the file that the just-completed restore wrote at lines 332-339 of THIS file; (d) reference `roles/garage/tasks/bootstrap.yml:124-147` as the canonical shape and `14-HUMAN-UAT.md` G-01 for the field evidence.

    Constraints:
    - English-only.
    - The set_fact regex_search expressions must be COPIED VERBATIM from bootstrap.yml lines 142-143 (same `(?m)^key_id=(.+)$` / `(?m)^secret=(.+)$` pattern, same `(.content | b64decode) | regex_search(..., '\\1') | first` shape).
    - Both tasks carry `tags: [garage, restore]` exactly.
    - Both tasks are OUTSIDE (siblings of) the existing `block:/always:` wrapper -- NOT inside the `always:` clause (we do not want them to run on a failed restore).
    - DO NOT modify any pre-existing task in restore.yml.
    - DO NOT add a `when:` guard. The file existing is a postcondition of the block succeeding.
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=roles/garage/tasks/restore.yml
        test -s "$F"

        # YAML round-trip + structural assertions
        python3 -c "
import yaml
with open(\"$F\") as fh:
    tasks = yaml.safe_load(fh)
assert isinstance(tasks, list), \"restore.yml must be a task list\"
# Find the LAST two tasks at the top level
last_two = tasks[-2:]
assert len(last_two) == 2, \"expected at least 2 tasks at top level\"
slurp_task, setfact_task = last_two[0], last_two[1]
# Slurp task
slurp = slurp_task.get(\"ansible.builtin.slurp\") or slurp_task.get(\"slurp\")
assert slurp is not None, f\"second-to-last task must be a slurp, got keys: {list(slurp_task.keys())}\"
src = slurp.get(\"src\", \"\")
assert \"garage_s3_credentials_file\" in str(src), f\"slurp src must reference garage_s3_credentials_file, got {src!r}\"
assert slurp_task.get(\"register\") == \"garage_creds_raw\", \"slurp must register garage_creds_raw\"
assert slurp_task.get(\"changed_when\") is False, \"slurp must be changed_when: false\"
slurp_tags = set(slurp_task.get(\"tags\", []))
assert slurp_tags == {\"garage\", \"restore\"}, f\"slurp tags must be {{garage, restore}}, got {slurp_tags}\"
# Slurp must NOT have a when guard (file exists by construction)
assert \"when\" not in slurp_task, f\"slurp must not have when: guard, got {slurp_task.get(\\\"when\\\")!r}\"
# Set_fact task
sf = setfact_task.get(\"ansible.builtin.set_fact\") or setfact_task.get(\"set_fact\")
assert sf is not None, \"last task must be set_fact\"
assert \"garage_s3_access_key_id\" in sf, \"set_fact must define garage_s3_access_key_id\"
assert \"garage_s3_secret_key\" in sf, \"set_fact must define garage_s3_secret_key\"
# Regex pattern matches bootstrap.yml:142-143 shape
akid_expr = str(sf[\"garage_s3_access_key_id\"])
assert \"garage_creds_raw.content\" in akid_expr and \"b64decode\" in akid_expr and \"key_id=\" in akid_expr, f\"set_fact access_key expression off-shape: {akid_expr!r}\"
sk_expr = str(sf[\"garage_s3_secret_key\"])
assert \"garage_creds_raw.content\" in sk_expr and \"b64decode\" in sk_expr and \"secret=\" in sk_expr, f\"set_fact secret_key expression off-shape: {sk_expr!r}\"
sf_tags = set(setfact_task.get(\"tags\", []))
assert sf_tags == {\"garage\", \"restore\"}, f\"set_fact tags must be {{garage, restore}}, got {sf_tags}\"
assert \"when\" not in setfact_task, f\"set_fact must not have when: guard, got {setfact_task.get(\\\"when\\\")!r}\"
print(\"PASS: restore.yml tail slurp + set_fact landed correctly\")
"

        # G-01 audit reference present in restore.yml (the new comment block)
        grep -q "G-01" "$F"

        # The existing block/always wrapper is still present and unchanged in shape
        grep -q "block:" "$F"
        grep -q "always:" "$F"

        # Verify the orchestrator playbook still syntax-checks now that restore.yml has new tasks
        ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml

        echo "PASS: Task 1 -- garage/restore.yml tail fact-population landed"
      '
    </automated>
  </verify>
  <acceptance_criteria>
    - `roles/garage/tasks/restore.yml` ends with EXACTLY two new top-level tasks (siblings of the existing `block:/always:` wrapper, not inside it):
      1. `ansible.builtin.slurp` of `{{ garage_s3_credentials_file }}` -> `register: garage_creds_raw`, `changed_when: false`, `tags: [garage, restore]`, NO `when:` guard.
      2. `ansible.builtin.set_fact` assigning `garage_s3_access_key_id` and `garage_s3_secret_key` from the regex_search of `garage_creds_raw.content | b64decode` -- VERBATIM shape from `roles/garage/tasks/bootstrap.yml:142-143`. `tags: [garage, restore]`, NO `when:` guard.
    - A comment block ABOVE the new tasks cites G-01, references `roles/garage/tasks/bootstrap.yml:124-147` as the source pattern, and explains the downstream lazy-Jinja dependency (loki/tempo/mimir templates).
    - `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml` exits 0 (this also covers per-role syntax for `tasks_from=restore` inclusion).
    - The pre-existing `block:/always:` wrapper, all integrity-check tasks, the confirm-gate, the WARN banner, and the existing restore extraction tasks are unchanged.
    - NOTE for executor: `--syntax-check` is STRUCTURAL-ONLY. It cannot catch a misspelled fact name or a typo in the regex. Behavioral correctness (the fact value matches the file content) is empirically verified by Plan 14-07 scenario 1 step 6 PLAY RECAP `failed=0`.
  </acceptance_criteria>
  <done>
    `roles/garage/tasks/restore.yml` now slurp + set_fact's `garage_s3_access_key_id` and `garage_s3_secret_key` after a successful restore. Subsequent `include_role: name=loki/tempo/mimir tasks_from=main` (either from the orchestrator in Task 2 below OR from any custom playbook a future operator wires up) will see the facts populated and render templates against the restored Garage S3 key. Bootstrap.yml's behavior is unchanged (it still populates the same facts via the same shape on the deploy path).
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Insert writer-config-rerender step into restore_docker.yml between Garage restore and writer-restart loop</name>
  <files>playbooks/restore_docker.yml</files>
  <read_first>
    - playbooks/restore_docker.yml (full file -- understand current state: confirm-gate at lines 96-105, WARN banner at 110-117, writer-stop loop at 137-149, writer-stop poll at 154-173, Garage restore at 178-184, writer-restart loop at 192-204, writer healthy-poll at 210-230, prometheus/grafana/alertmanager restores at 235-257). The incorrect comment is at lines 186-191.
    - roles/garage/tasks/restore.yml POST-TASK-1 STATE (Task 1 added two tail tasks that populate `garage_s3_access_key_id` and `garage_s3_secret_key` facts -- these facts are in scope when the new include_role tasks in this Task 2 render their templates).
    - roles/loki/tasks/main.yml (confirm `tasks_from=main` re-renders /opt/telemetron/loki/loki.yaml -- the template task notifies `restart loki`)
    - roles/loki/templates/loki.yaml.j2 lines 53-54 (the template lines that consume `loki_s3_access_key` / `loki_s3_secret_key` which lazy-resolve via secrets.yml.example:42-43 to `garage_s3_access_key_id` / `garage_s3_secret_key`)
    - roles/tempo/tasks/main.yml (same structure -- template task with `notify: restart tempo`)
    - roles/mimir/tasks/main.yml (same structure -- template task with `notify: restart mimir`)
    - roles/loki/handlers/main.yml (handler runs `docker restart {{ loki_container_name }}`)
    - roles/tempo/handlers/main.yml, roles/mimir/handlers/main.yml (same shape)
    - inventory/example-homelab/group_vars/all/secrets.yml.example:42-43 (the lazy-Jinja indirection that closes the resolution chain)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-VERIFICATION.md gaps[0].missing (recommended remediation)
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md Gaps G-01 evidence section
    - .planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md D-181/D-183/D-189 (writer-quiesce design + tag-list rationale; D-183 is REVERSED by this fix -- cite the reversal in the new comment block)
    - playbooks/deploy_docker.yml (confirm how loki/tempo/mimir roles are normally invoked -- the `roles:` block. The new include_role calls in restore_docker.yml are functionally equivalent to a targeted re-deploy of just those three roles.)
  </read_first>
  <action>
    Edit `playbooks/restore_docker.yml` to insert a writer-config-rerender step between the Garage restore task (currently lines 178-184) and the writer-restart loop (currently lines 192-204). The incorrect comment at lines 186-191 must be REPLACED with the correct rationale.

    Sequence of edits (top to bottom in the file):

    1. **REPLACE the comment block at lines 186-191** -- the 5-line comment that begins `# D-183 + D-189 amended: restart the 3 Garage writers sequentially AFTER` and continues with the (incorrect) `# no config re-render needed.` line. Replace with a corrected rationale that explains:
       (a) D-183's locked assumption `Garage S3 endpoint and credentials haven't changed [...] no config re-render needed` is REVERSED by G-01 field evidence. The 7-step round-trip's step 5 (post-purge redeploy) generates a NEW S3 key; step 6 then restores the ORIGINAL pre-backup key BUT writer configs on the host still hold the step-5 key.
       (b) Garage restore overwrites `{{ garage_s3_credentials_file }}` with the ORIGINAL key from the tarball.
       (c) Writer configs (`/opt/telemetron/{loki,tempo,mimir}/<role>.yaml`) hold the NEW (wrong) post-purge key.
       (d) We MUST re-render writer configs from the restored s3-credentials before unblocking the writers.
       (e) `tasks_from=main` is the right hook because the role's main.yml template task re-reads `garage_s3_credentials_file` (indirectly via the lazy-Jinja `loki_s3_access_key` -> `garage_s3_access_key_id` chain) and notifies the restart handler.
       (f) `meta: flush_handlers` forces the restart to happen NOW rather than at end-of-play.
       (g) The new tail of `roles/garage/tasks/restore.yml` (Task 1) populates `garage_s3_access_key_id` and `garage_s3_secret_key` facts so the lazy-Jinja chain in (e) resolves cleanly -- without Task 1's set_fact, the template render in (e) would explode with `AnsibleUndefinedVariable`.
       (h) Reference G-01 from 14-HUMAN-UAT.md and the new must-have truth that captures the D-183 reversal.

    2. **INSERT new tasks BETWEEN the Garage restore (line 184 end) and the writer-restart loop (line 192 start)** -- in this order:

       (a) `include_role: name=loki  tasks_from=main` with `tags: [garage, restore]` and a `name:` field identifying it as the G-01 writer-rerender step (cite G-01 and D-183-reversal in the task name, e.g., `name: Re-render Loki config from restored Garage s3-credentials (G-01 fix; D-183 reversed)`).

       (b) `include_role: name=tempo tasks_from=main` with `tags: [garage, restore]`.

       (c) `include_role: name=mimir tasks_from=main` with `tags: [garage, restore]`.

       (d) `ansible.builtin.meta: flush_handlers` (no `tags:` field needed -- meta tasks inherit from the surrounding context). Use the bare `flush_handlers` meta name. The `name:` field should cite G-01.

    3. **DO NOT change** the existing writer-restart loop at lines 192-204 OR the writer healthy-poll at lines 210-230. They remain as-is. Rationale documented in the new comment block: the include_role may have triggered the restart handler (config changed -> notify fires); the existing `docker start` loop is the unconditional fallback for the case where the template happens to match (no handler fired, writer still in stopped state from the writer-stop loop earlier). The healthy-poll is the actual operational guarantee in either path.

    4. **DO NOT touch** the confirm-gate (lines 96-105), the WARN banner (lines 110-117), the writer-stop loop (lines 137-149), the writer-stop poll (lines 154-173), the Garage restore (lines 178-184), or the 3 trailing per-role restores (prometheus/grafana/alertmanager at lines 235-257).

    Per D-189 amended, the new include_role tasks must carry `tags: [garage, restore]` exactly -- `[garage]` so `--tags garage` runs the bracketed Garage unit; `[restore]` for SC4 cross-cutting `--tags restore`. They must NOT carry `[loki]`, `[tempo]`, `[mimir]`, `[writers]`, or `[always]` (per the original D-189 rationale preserved by the SC4 reconciliation).

    Constraints:
    - English-only.
    - Each new `name:` field cites G-01 explicitly.
    - The corrected comment block MUST cite `G-01`, `14-HUMAN-UAT.md`, AND `D-183 reversed` so future readers find the full audit trail.
    - The corrected comment block MUST NOT contain the phrase "no config re-render needed" -- that was the original incorrect assumption.
    - File header docstring (lines 1-69) does NOT need amendment -- the inline comment block from step 1 is the authoritative audit trail.
  </action>
  <verify>
    <automated>
      bash -c '
        set -e
        cd "$(git rev-parse --show-toplevel)"
        F=playbooks/restore_docker.yml
        test -s "$F"

        # Syntax-check passes (STRUCTURAL-ONLY -- per MEMORY.md feedback_ansible_syntax_check_role_gap.md,
        # this does NOT catch undefined-variable runtime failures. The G-01 fact-population in Task 1
        # is the runtime correctness guard; Plan 14-07 is the empirical proof.)
        ansible-playbook --syntax-check -i inventory/example-homelab "$F"

        # YAML round-trip validates the exact task sequence and tag sets
        python3 -c "
import yaml, sys
with open(\"$F\") as fh:
    docs = list(yaml.safe_load_all(fh))
play = docs[0][0]
tasks = play.get(\"tasks\", [])
writer_rerenders = []
for t in tasks:
    ir = t.get(\"ansible.builtin.include_role\") or t.get(\"include_role\")
    if ir and ir.get(\"tasks_from\") == \"main\" and ir.get(\"name\") in (\"loki\", \"tempo\", \"mimir\"):
        writer_rerenders.append((ir[\"name\"], t.get(\"tags\")))
names = [r[0] for r in writer_rerenders]
assert names == [\"loki\", \"tempo\", \"mimir\"], f\"expected [loki, tempo, mimir], got {names}\"
for name, tags in writer_rerenders:
    assert tags is not None, f\"{name} rerender missing tags\"
    assert set(tags) == {\"garage\", \"restore\"}, f\"{name} rerender tags must be [garage, restore], got {tags}\"
# Find meta: flush_handlers AFTER the 3 writer rerenders
meta_idx = None
loki_idx = None
restart_loop_idx = None
for i, t in enumerate(tasks):
    ir = t.get(\"ansible.builtin.include_role\") or t.get(\"include_role\")
    if ir and ir.get(\"name\") == \"loki\" and ir.get(\"tasks_from\") == \"main\":
        loki_idx = i
    meta_val = t.get(\"ansible.builtin.meta\") or t.get(\"meta\")
    if meta_val == \"flush_handlers\":
        meta_idx = i
    cmd_val = t.get(\"ansible.builtin.command\")
    if isinstance(cmd_val, str) and \"docker start\" in cmd_val and \"loop\" in str(t):
        restart_loop_idx = i
assert loki_idx is not None, \"loki rerender include_role not found\"
assert meta_idx is not None, \"meta: flush_handlers not found\"
assert restart_loop_idx is not None, \"writer-restart docker start loop not found\"
assert loki_idx < meta_idx, f\"flush_handlers must come AFTER loki rerender (loki@{loki_idx}, meta@{meta_idx})\"
assert meta_idx < restart_loop_idx, f\"flush_handlers must come BEFORE writer-restart loop (meta@{meta_idx}, restart@{restart_loop_idx})\"
garage_restore_idx = None
for i, t in enumerate(tasks):
    ir = t.get(\"ansible.builtin.include_role\") or t.get(\"include_role\")
    if ir and ir.get(\"name\") == \"garage\" and ir.get(\"tasks_from\") == \"restore\":
        garage_restore_idx = i
        break
assert garage_restore_idx is not None, \"Garage include_role tasks_from=restore not found\"
assert garage_restore_idx < loki_idx, f\"Garage restore must come BEFORE writer rerenders (garage@{garage_restore_idx}, loki@{loki_idx})\"
print(\"PASS: G-01 fix structure correct -- Garage restore -> [loki, tempo, mimir rerender] -> flush_handlers -> writer-restart loop\")
"

        # Incorrect old comment removed
        if grep -q "no config re-render needed" "$F"; then echo "FAIL: stale incorrect comment still present"; exit 1; fi
        # New rationale cites G-01, the audit doc, AND the D-183 reversal
        grep -q "G-01" "$F"
        grep -q "14-HUMAN-UAT.md" "$F"
        grep -q -E "D-183.*(revers|REVERS)" "$F"

        # Confirm-gate, WARN banner, writer-stop loop, writer-stop poll, Garage restore, and 3 trailing restores still present
        grep -q "ansible.builtin.fail:" "$F"
        grep -q "WARNING: irreversible --" "$F"
        grep -q "name=prometheus" "$F" || grep -q "name: prometheus" "$F"
        grep -q "name=grafana"    "$F" || grep -q "name: grafana"    "$F"
        grep -q "name=alertmanager" "$F" || grep -q "name: alertmanager" "$F"

        echo "PASS: Task 2 -- 14-05 G-01 fix landed in restore_docker.yml"
      '
    </automated>
  </verify>
  <note>
    `ansible-playbook --syntax-check` is structural-only (per MEMORY.md `feedback_ansible_syntax_check_role_gap.md`).
    It will NOT catch runtime failures from undefined variables in role internals, mismatched fact names,
    or regex parsing errors. Specifically: this Task's syntax-check passing does NOT prove that the
    `garage_s3_access_key_id` fact set in Task 1's `roles/garage/tasks/restore.yml` tail actually
    propagates correctly across the include_role boundary to the loki/tempo/mimir template renders.
    EXECUTORS MUST NOT mistake "Task 2 structurally complete" for "G-01 fixed." The empirical proof
    is Plan 14-07 scenario 1 step 6: PLAY RECAP `failed=0` AND absence of `Forbidden: No such key:`
    errors in Loki/Tempo/Mimir container logs after the unmodified-orchestrator run on leviathan.
    If Plan 14-07 surfaces a regression, this task's acceptance is rolled back and a follow-up plan
    addresses the actual runtime failure mode.
  </note>
  <acceptance_criteria>
    - `playbooks/restore_docker.yml` exists, non-empty, passes `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/restore_docker.yml`.
    - Three new `ansible.builtin.include_role` tasks exist with `name: loki`, `name: tempo`, `name: mimir` (in that order) and `tasks_from: main`. Each carries exactly `tags: [garage, restore]` (set equality; order does not matter).
    - One new `ansible.builtin.meta: flush_handlers` task exists IMMEDIATELY AFTER the 3 writer rerender include_role calls AND BEFORE the existing writer-restart `docker start` loop.
    - Task ordering in the `tasks:` block (verified by index): `... include_role:name=garage tasks_from=restore ... < include_role:name=loki tasks_from=main < include_role:name=tempo tasks_from=main < include_role:name=mimir tasks_from=main < meta:flush_handlers < command:"docker start ..." loop (writer-restart) ...`.
    - The exact phrase `no config re-render needed` does NOT appear anywhere in the file (the original incorrect comment is gone).
    - The new comment block cites `G-01`, `14-HUMAN-UAT.md`, AND `D-183 reversed` (or `D-183 REVERSED`) as the audit trail.
    - The existing confirm-gate, WARN banner, writer-stop loop, writer-stop poll, Garage restore, writer-restart loop, writer healthy-poll, and the 3 trailing restores (prometheus/grafana/alertmanager) are all still present and unchanged (their existing tag lists are intact).
  </acceptance_criteria>
  <done>
    `playbooks/restore_docker.yml` now contains the writer-config-rerender step. After Garage restore writes the restored s3-credentials AND populates `garage_s3_access_key_id` / `garage_s3_secret_key` as facts (via Task 1's restore.yml tail), the loki/tempo/mimir role main.yml fires (re-rendering writer configs against the just-populated facts), `meta: flush_handlers` forces the restart handlers to fire NOW (not deferred to end-of-play), and the existing writer-restart `docker start` + healthy-poll loop completes successfully because writers come back against the matching key. The incorrect "no config re-render needed" comment is replaced with the correct rationale citing G-01 and the D-183 reversal. Plan 14-07 (re-UAT) is the empirical proof that SC6 flips from FAILED to VERIFIED.
  </done>
</task>

</tasks>

<verification>
- Task 1 verification: YAML round-trip validates the two new tail tasks in `roles/garage/tasks/restore.yml` (slurp + set_fact) carry the right tags, no `when:` guard, and the regex_search shape matches bootstrap.yml verbatim.
- Task 2 verification: `ansible-playbook --syntax-check` exit 0, YAML round-trip validates the exact task sequence and tag sets in `playbooks/restore_docker.yml`, grep gates confirm the incorrect comment is removed and the G-01 + D-183-reversal audit reference is present.
- Empirical proof of SC6 closure is Plan 14-07's live re-UAT on leviathan. Both Task 1 + Task 2 are structurally complete when their acceptance criteria pass; behavioral correctness is the Plan 14-07 gate.
</verification>

<success_criteria>
- SC6 (ROADMAP.md Phase 14 #6) prerequisites in place: `restore_docker.yml` AND `roles/garage/tasks/restore.yml` are structurally capable of completing the 7-step round-trip without manual intervention. The remaining proof is empirical (Plan 14-07).
- RESTORE-V13-05 prerequisites in place: writers restart against restored Garage WITHOUT a manual config-rerender workaround.
- G-01 closure prerequisites in place: BOTH the missing in-memory fact population (Task 1, restore.yml tail) AND the missing writer-config-rerender step in the orchestrator (Task 2) exist in the correct positions with the correct tag lists and the supporting `meta: flush_handlers` task.
- Tag UX preserved: `--tags garage` and `--tags restore` both fire the writer-rerender (Task 2) AND the new restore.yml tail (Task 1); `--tags loki/tempo/mimir` do not.
- Idempotency preserved: a second restore against the same backup is a no-op for the rerender step (template reports `changed=false`); the slurp + set_fact in Task 1 is idempotent (the fact value just equals itself on re-run).
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Restored Garage `s3-credentials` host file -> writer config templates | The restored file is what the new restore.yml tail (Task 1) slurps and what bootstrap.yml's existing slurp targets. If Garage restore truncates or mis-writes this file, BOTH the new set_fact (Task 1) AND the subsequent writer config render (Task 2) fail. Mitigation: Phase 13's Garage restore already validates the restored file (tar --zstd -tf integrity check before any wipe; mode 0600 re-applied after extract). |
| `garage_creds_raw.content | b64decode | regex_search` parsing | If the credentials file format changes (e.g., bootstrap.yml ever switches from `key_id=<v>` / `secret=<v>` to JSON), both bootstrap.yml's slurp and restore.yml's new slurp need to track the change in lockstep. Mitigation: restore.yml's new slurp uses the EXACT same regex_search expressions as bootstrap.yml:142-143 (verbatim copy) -- one source of truth for the parsing shape. |
| Writer config templates -> writer container restart | The handler `docker restart <writer>` runs as the operator (typically via sudo). If the writer container is somehow missing (manually `docker rm`'d), the restart fails non-cleanly. Mitigation: this is operator-induced state outside Telemetron's contract; the existing `docker_container state=started recreate=false` in the role's main.yml will recreate if missing. |
| `meta: flush_handlers` timing | Handler must fire BEFORE the existing writer-restart `docker start` healthy-poll. If `flush_handlers` is misplaced, the writer restarts twice but eventually converges. No data loss. Mitigation: Task 2 acceptance_criteria asserts exact ordering. |
| Fact propagation across include_role boundary | Task 1's set_fact'd values must be visible to Task 2's include_role calls. Ansible facts are play-level by default. Mitigation: no `delegate_to:` or `delegate_facts:` weirdness in either task; standard fact propagation is the contract. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-14-G01-01 | Tampering | Writer config template re-render reads `garage_s3_credentials_file` indirectly via `garage_s3_access_key_id` fact -- if Garage restore wrote a corrupted file, Task 1's slurp parses garbage and set_fact's empty strings, writer configs render with bad credentials | mitigate | Phase 13's Garage restore tasks already integrity-check the tarball (`tar tf` returns 0) and post-restore verify task confirms Garage health. If Garage restore succeeds (i.e., we reach Task 1), the s3-credentials file is intact. Task 1's `regex_search ... | first` raises if the regex matches nothing, surfacing parse failures fast. |
| T-14-G01-02 | Denial of Service | `meta: flush_handlers` does not fire if a prior task in the play failed (Ansible handler semantics) -- on a partial restore where Garage succeeds but a later step crashes, writers may not get re-rendered configs | accept | `any_errors_fatal: true` is hardcoded in restore_docker.yml (D-185), so partial restores already abort the play. Operator re-runs restore from scratch after fixing the partial state -- standard restore-is-not-incremental contract. |
| T-14-G01-03 | Information Disclosure | Writer config files contain the Garage S3 access key in plaintext on the host (`/opt/telemetron/{loki,tempo,mimir}/<role>.yaml` mode 0600); set_fact'd facts are in Ansible's runtime context | accept | Pre-existing Phase 2 / Phase 8 contract -- mode 0600 + owner-only readability. Task 1's set_fact carries the same content bootstrap.yml already set_fact's. Same threat surface. |
| T-14-G01-04 | Tampering | An attacker with host access could replace `garage_s3_credentials_file` between Garage restore and Task 1's slurp, causing Task 1 to set_fact attacker's key | accept | Host-root attacker is out of v1.3.0 threat model; the restored s3-credentials are the legitimate value Garage just wrote. ASVS L1 boundary. |
| T-14-G01-05 | Repudiation | Task 1's set_fact silently shadows a `garage_s3_access_key_id` value that was already in scope (e.g., from a prior bootstrap.yml run in the same play, which cannot happen in restore_docker.yml because main.yml is not invoked there) | accept | restore_docker.yml does not invoke main.yml or bootstrap.yml. The fact is unset at play start; Task 1 is the first and only setter on the restore path. No shadow risk. |
</threat_model>

<output>
Create `.planning/phases/14-orchestrators-leviathan-human-uat/14-05-SUMMARY.md` when done. The SUMMARY captures:
- For Task 1: the exact 2 new tail tasks added to `roles/garage/tasks/restore.yml` (slurp + set_fact), their tags, and the canonical-shape reference to `roles/garage/tasks/bootstrap.yml:127-147`.
- For Task 2: the exact 4 new tasks inserted into `playbooks/restore_docker.yml` (3 include_role + 1 meta), their line numbers post-edit, the corrected comment block content (paraphrased, citing G-01 + D-183 reversal), and the syntax-check exit code.
- Reference G-01 from 14-HUMAN-UAT.md so future readers see the gap-closure audit trail.
- Explicit note that runtime correctness (no `Forbidden: No such key:` in writer logs post-restore) is empirically verified by Plan 14-07, not by this plan's structural verification.
</output>
</content>
</invoke>