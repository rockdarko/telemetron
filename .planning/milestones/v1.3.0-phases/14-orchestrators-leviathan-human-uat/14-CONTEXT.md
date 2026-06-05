# Phase 14: Orchestrators + Leviathan HUMAN-UAT - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 ships two thin orchestrator playbooks (`playbooks/backup_docker.yml` and `playbooks/restore_docker.yml`) that wrap the per-role `tasks/backup.yml` / `tasks/restore.yml` files Phase 13 already shipped for the 4 stateful roles (garage, prometheus, grafana, alertmanager). It also ships `14-HUMAN-UAT.md` — the live audit document proving the 7-step backup → undeploy-with-purge → redeploy → restore → re-smoke round-trip on leviathan, plus 3 negative scenarios (confirm-gate proof, bail-out vs continue-on-failure proof, tag-scoped run proof).

The orchestrators introduce one cross-cutting concern Phase 13 deliberately deferred: stopping the 3 Garage writers (Loki, Tempo, Mimir) before `tasks_from=restore` runs on Garage, then restarting them after. This is the only cross-role coordination the orchestrators add — everything else delegates to the per-role tasks.

Phase 14 covers 6 of the 18 v1.3.0 requirements: BACKUP-V13-05, RESTORE-V13-05, OPS-V13-01..03, UAT-V13-01.

Out of scope for Phase 14 (lives in Phase 15): the doc cascade (root README cross-ref, `docs/quickstart.md ## Backup and restore`, per-role README `## Backup` H2, Gate 11 in `roles/README.md`).

</domain>

<decisions>
## Implementation Decisions

### Writer quiesce around Garage restore (D-180..D-183)

- **D-180: Writer quiesce lives inline in `playbooks/restore_docker.yml`, not as new per-role tasks.** Two task blocks in the orchestrator: "stop Garage writers" before the Garage `include_role` and "restart Garage writers" after. No new files in `roles/loki/tasks/`, `roles/tempo/tasks/`, `roles/mimir/tasks/`. Rationale: the writer-quiesce concern is specifically a Garage-restore prerequisite, not a per-writer-role concern. Keeps the writers' role surface unchanged; concentrates the cross-role coordination in the one place where it matters (the orchestrator). Alternative (`tasks/quiesce.yml + tasks/resume.yml` in each of the 3 writer roles) rejected — 6 new YAML files for a concern that has exactly one caller.

- **D-181: Stop writers via sequential loop over `[loki, tempo, mimir]` using `ansible.builtin.command: docker stop -t {{ backup_stop_timeout }} {{ <writer>_container_name }}` + `community.docker.docker_container_info` healthy-poll (mirrors the cold-quiesce pattern Phase 13 standardized).** Loop body issues `docker stop`, registers result, then polls `docker_container_info` for `State.Status == exited` via `until:` + `retries:` + `delay:`. Same shape used inside Garage/Prometheus/Grafana/Alertmanager `tasks/backup.yml`. Sequential (not async) — total stop time ≈ 3 × graceful-stop ≤ 3 × backup_stop_timeout (60s ceiling). The extra ~5–15s of sequential vs parallel stopping is invisible compared to the Garage restore window. Async + bulk `docker stop loki tempo mimir` alternatives rejected — async adds error-aggregation complexity for no real-world win; bulk loses per-container changed_when/failed_when granularity.

- **D-182: Stop timeout for the 3 writers reuses the existing `backup_stop_timeout` (60s).** Loki/Tempo/Mimir are S3 clients with write-ahead buffers — 60s is generous but harmless. One shared knob. No new `writer_stop_timeout` introduced. Matches the v1.3.0 "no hidden capacity knobs" precedent.

- **D-183: Restart writers via `ansible.builtin.command: docker start {{ <writer>_container_name }}` + `community.docker.docker_container_info` poll for `State.Health.Status == healthy`.** Symmetric with the stop step (same loop shape, opposite verb). Garage S3 endpoint and credentials haven't changed (because Phase 13's Garage restore restores the `s3-credentials` host file along with the meta+data volumes), so the writers come back pointing at the same buckets they were configured for — no config re-render needed. Alternative (`deploy_docker.yml --tags loki,tempo,mimir`) rejected — pulls in image-check + network-attach + config-render tasks that aren't needed for a restart, and runs slower.

### Bail-out vs continue-past-failure (D-184..D-187)

- **D-184: `backup_docker.yml` uses `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` at the play level.** One-line, idiomatic Ansible. The 4 `include_role` calls remain unchanged; Ansible itself decides whether a role failure aborts the play based on the operator's flag. When `backup_continue_on_failure=true`, every role attempts its backup; PLAY RECAP shows `failed=N` at the end. Explicit `block`/`rescue` around each `include_role` rejected — 4× the YAML for behavior `any_errors_fatal` gives natively. `failed_when:false` + final assertion rejected — hides failures during the run, bad UX for the bail-out case where the operator needs immediate visibility.

- **D-185: `restore_docker.yml` hardcodes `any_errors_fatal: true` — restore ALWAYS bails out on the first role's failure.** Restore is destructive; once Garage's volumes are wiped, a downstream failure (e.g., Prometheus restore aborts) leaves the stack in a half-restored state where the operator must manually figure out which roles got their data back. Bail-out forces operator attention immediately. Document explicitly that `backup_continue_on_failure` applies to backup only, not restore. Symmetric-honor and new-`restore_continue_on_failure`-knob alternatives rejected — both enable a footgun that 99% of operators should never opt into.

- **D-186: Backup PLAY-start banner — single `ansible.builtin.debug` task with multi-line `msg:`, `tags: always`, D-160 shape mirroring `undeploy_docker.yml`'s irreversible-purge banner.** Banner lines (no role enumeration — stable across role additions): `Backup destination: {{ backup_dest_root }}/<role>/`, `backup_continue_on_failure={{ backup_continue_on_failure }}` with category description (`(first role failure will abort the playbook)` if false, `(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)` if true), `backup_stop_timeout={{ backup_stop_timeout }}s`. `tags: always` so the banner displays on `--tags <role>` targeted runs. Single-line summary rejected — multi-line shape lets the operator scan each knob independently in PLAY OUTPUT.

- **D-187: Restore PLAY-start banner — multi-line `ansible.builtin.debug` debug with `WARNING: irreversible --` grep-friendly prefix on the headline line, `tags: always`, escalated D-160 WARN.** Banner content: line 1 `WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)`; line 2 `Target timestamp: {{ backup_restore_from | default('<latest per role>') }}`; line 3 `Restore order: stop Loki/Tempo/Mimir → garage → prometheus → grafana → alertmanager → restart Loki/Tempo/Mimir`. Uses the same `WARNING: irreversible --` prefix as `undeploy_docker.yml` (D-159) — same grep target. Single-line WARN rejected — loses the stop-order context which is the genuinely useful operator info.

### Stateless-tag UX (D-188..D-189)

- **D-188: `restore_docker.yml --tags <stateless-role>` produces an empty 0-task play (symmetric with `backup_docker.yml`'s SC1 contract).** Loki/Tempo/Mimir/Karma/FluentBit/OpenTelemetry/node_exporter/nfsd have no `tasks/restore.yml` in their roles, AND the writer-quiesce tasks at orchestrator level are not tagged with their role names — so `--tags loki` matches nothing in the play and Ansible produces an empty PLAY RECAP. Explicit fail rejected — would also fire on legitimate `--tags backup`/`--tags restore` cross-cutting invocations because those don't include `loki`. Loki-tag-as-recycle-cycle rejected — mixes restore concerns with debug concerns; wrong playbook for the operation.

- **D-189: Writer-stop and writer-restart tasks in `restore_docker.yml` are tagged `[garage]` only — not `[writers]`, not `[always]`.** Effect: `--tags garage` runs `stop-writers → include_role: name=garage tasks_from=restore → restart-writers` as one logical unit. `--tags loki/tempo/mimir` runs nothing. `--tags prometheus/grafana/alertmanager` restores just that role; writers stay running because their data is in Prometheus's local TSDB / Grafana's SQLite / Alertmanager's silences — none of which touches Garage. `[writers]` cross-cutting tag rejected — overloads a destructive playbook with a non-destructive operation. `[always]` rejected — would stop writers on every targeted run, even when restoring Prometheus only.

### `backup_restore_from` propagation (D-190..D-191)

- **D-190: `restore_docker.yml` lets each role's `tasks/restore.yml` resolve `backup_restore_from` independently — no orchestrator pre-resolution.** Pass the variable through unchanged. Each role does its own `find /opt/telemetron/backups/<role>/ -name '<role>-*.tar.zst' | sort -r | head -1` when `backup_restore_from=''` (default), else uses the explicit timestamp. Loose coupling — if a role's tarball with the requested timestamp is missing, that role's restore fails with a clear per-role error and the operator knows immediately which role is the problem. Orchestrator pre-resolve (parse latest-shared-timestamp across all 4 dirs) rejected — complex parsing for a timestamp that might not exist in all 4 dirs if any role's backup failed. Per-role override map rejected — out of scope for v1.3.0.

- **D-191: `backup_docker.yml` generates ONE shared ISO 8601 basic UTC timestamp at play start (`ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ`, registered as `set_fact: backup_timestamp_shared`) and re-exports it to each of the 4 role `include_role` calls via `vars: { backup_timestamp_override: '{{ backup_timestamp_shared }}' }`.** All 4 tarballs in a single backup run share one timestamp — operator-friendly for matching explicit restores. **Phase 14 includes a small amendment to each of the 4 `tasks/backup.yml` files Phase 13 shipped:** change the filename generation to use `backup_timestamp_override | default(<existing inline date call>)`. This is the only Phase-13 code Phase 14 modifies; planner must include this as a discrete plan task with the 4 file paths called out. Standalone `include_role: tasks_from=backup` (without the orchestrator) still works because the `default(<inline date>)` branch fires when `backup_timestamp_override` is unset.

### 14-HUMAN-UAT.md scope (D-192)

- **D-192: `14-HUMAN-UAT.md` ships with the 7-step happy-path round-trip (UAT-V13-01) AND 3 negative scenarios** following the shape of `.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` (YAML frontmatter `status`/`phase`/`source`/`started`/`updated`; `## Current Test`; `## Tests` with numbered scenarios using `expected:` / `result:` / `detail:`). Required scenarios:
  - **Scenario 1: 7-step round-trip happy-path** — deploy → smoke (records `smoke_trace_id` + `smoke_run_id`) → backup → undeploy --purge-data → deploy → restore --confirm --from=<timestamp> → smoke with the recorded trace_id+run_id asserts the same OTLP signals visible in Grafana (UAT-V13-01).
  - **Scenario 2: confirm-gate proof** — `restore_docker.yml` without `backup_restore_confirm=true` MUST fail at the orchestrator-level gate; standalone `include_role: tasks_from=restore` (custom playbook) MUST also fail at the per-role gate (OPS-V13-01). Two sub-tests: (a) orchestrator-level fail, (b) custom-playbook include_role-level fail.
  - **Scenario 3: bail-out vs continue-on-failure proof** — simulate a failing tar (e.g., `chattr +i` an existing tarball, or `chmod 000` the destination subdir before run) on Prometheus's backup. Sub-test (a): default run aborts at Prometheus; Garage's tarball exists, Grafana+Alertmanager are NOT attempted (proves bail-out, OPS-V13-02 default). Sub-test (b): rerun with `--extra-vars backup_continue_on_failure=true`; Garage+Grafana+Alertmanager all succeed, Prometheus fails; PLAY RECAP shows `failed=1` for Prometheus (proves opt-in, OPS-V13-02 opt-in).
  - **Scenario 4: tag-scoped backup + restore proof** — `backup_docker.yml --tags garage` produces only `garage-*.tar.zst`, no other role's tarball touched. `backup_docker.yml --tags loki` produces empty 0-task play, exits 0 (SC1). `restore_docker.yml --tags grafana --extra-vars backup_restore_confirm=true backup_restore_from=<ts>` restores only Grafana; writers stay running (because `--tags grafana` doesn't match the `[garage]`-tagged writer-quiesce tasks); other roles untouched (OPS-V13-03).

Single doc, single audit trail. Mirrors Phase 11's HUMAN-UAT format exactly — proven workflow.

### Layout of orchestrators (D-193)

- **D-193: Both `backup_docker.yml` and `restore_docker.yml` use the same physical layout as `undeploy_docker.yml`:** `vars:` (knob defaults), `pre_tasks:` (confirm-gate + PLAY-start banner, both `tags: always`), `tasks:` (writer-stop if applicable → 4 `include_role` calls in role order → writer-restart if applicable), no `post_tasks` for restore (the writer-restart is in `tasks` to keep it inside the tag-scoped run for `--tags garage`). Comments at task-block boundaries reference the relevant D-IDs and ROADMAP SC IDs. No `roles:` block — every per-role call is an `include_role` so tag handling is explicit (matches `undeploy_docker.yml`'s D-149 precedent). Split pre/tasks/post layout rejected — would put writer-restart in `post_tasks`, but `post_tasks` runs after the play body regardless of `--tags`, breaking the `--tags garage` symmetry (writers would NOT restart in a tag-scoped Garage-only restore run because writer-stop wouldn't have fired either — both must be in `tasks` to fire together under `[garage]` tag).

### Claude's Discretion (left to planner with safe defaults)

- **Pre-task `WARN -- writers will be stopped` debug** before the writer-stop loop in `restore_docker.yml`. Planner decides whether to emit (echoing D-159 pattern) or skip (the top-level banner already states the stop order). Default if planner is silent: skip — the play-start banner already names the stop order.
- **Backup orchestrator success summary** at end of play: ansible.builtin.debug listing the 4 tarball paths just written. Useful but not required. Planner decides.
- **Restore orchestrator success summary** at end of play: ansible.builtin.debug stating "restore complete — recommend running playbooks/smoke_test.yml to verify". Useful for the human; planner decides.
- **`14-HUMAN-UAT.md` `status:` frontmatter starting value**: prior phase used `in_progress` at create time, flipped to `complete` after the round-trip passes. Same convention here.
- **`14-HUMAN-UAT.md` initial commit timing**: planner can ship the doc with `status: pending`/`result: not run` placeholders for every scenario in the same plan that ships the orchestrators (audit trail is the doc), then the live UAT run flips them to `pass`. Or the doc gets a separate plan. Planner's call.
- **leviathan `inventory/leviathan/` path** is already gitignored and present on Rock's workstation per memory `project_leviathan_uat_host.md`. The HUMAN-UAT round-trip is run by Rock (or by Claude on Rock's behalf using passwordless SSH) — both modes valid. Plans should reference `inventory/leviathan` in example commands but not check for its existence on `ansible-playbook --syntax-check` runs (it's not in the repo).
- **Pre-flight check for live UAT scenario 3** (the `chattr +i` or `chmod 000` setup): planner decides how to script the "fault-injection" step — could be a manual instruction in the HUMAN-UAT doc, or an automated `pre_tasks` setup in a throwaway `playbooks/uat_inject_failure.yml`. Default if planner is silent: manual instruction documented inline in the HUMAN-UAT scenario.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements (locked)
- `.planning/PROJECT.md` § Current Milestone v1.3.0 — locked design decisions (cold-quiesce, destination, retention, encryption, failure-mode, quality-bar, size)
- `.planning/PROJECT.md` § Key Decisions — D-145..D-179 (v1.2.0 uninstall + Gate 10 patterns Phase 14 inherits; D-146 self-healing context; D-159/D-160 banner pattern Phase 14 mirrors)
- `.planning/REQUIREMENTS.md` § v1.3.0 — BACKUP-V13-05, RESTORE-V13-05, OPS-V13-01..03, UAT-V13-01 (the 6 Phase 14 requirements)
- `.planning/ROADMAP.md` § Phase 14 — goal + 6 success criteria (SC1..6)
- `.planning/STATE.md` § Decisions — v1.3.0 locked-decision list
- `.planning/phases/13-per-role-backup-restore-tasks/13-CONTEXT.md` — Phase 13 locked decisions (D-176..D-179) the orchestrators must respect

### Reference playbooks (Phase 14 mirrors these exactly — same shape, opposite verb)
- `playbooks/deploy_docker.yml` — sets the per-role `--tags <role>` precedent the orchestrators must honour (SC4)
- `playbooks/undeploy_docker.yml` — D-149 (reverse-order include_role list), D-150 (pre/post_tasks for network), D-157+D-160 (WARN banner format with `tags: always`), D-159 (`WARNING: irreversible --` grep-friendly prefix), D-151 (tag-scoped purge composition). The single closest analog to Phase 14's two orchestrators in shape.
- `playbooks/smoke_test.yml` — exact smoke command + per-run `smoke_trace_id` + `smoke_run_id` mechanics used by 14-HUMAN-UAT scenario 1 steps 2 and 7

### Phase 13 task files (orchestrators delegate to these via include_role)
- `roles/garage/tasks/backup.yml` — receives `backup_timestamp_override` per D-191
- `roles/garage/tasks/restore.yml` — already gates on `backup_restore_confirm` (OPS-V13-01 partial); already resolves `backup_restore_from` independently (D-190)
- `roles/prometheus/tasks/backup.yml`, `roles/prometheus/tasks/restore.yml`
- `roles/grafana/tasks/backup.yml`, `roles/grafana/tasks/restore.yml`
- `roles/alertmanager/tasks/backup.yml`, `roles/alertmanager/tasks/restore.yml`

### Shared variables + per-role container names
- `inventory/example-homelab/group_vars/all/backup.yml` — `backup_dest_root`, `backup_stop_timeout`, `backup_continue_on_failure`, `backup_restore_confirm`, `backup_restore_from` (all 5 knobs the orchestrators reference)
- `roles/loki/defaults/main.yml` — `loki_container_name` (writer-quiesce target)
- `roles/tempo/defaults/main.yml` — `tempo_container_name` (writer-quiesce target)
- `roles/mimir/defaults/main.yml` — `mimir_container_name` (writer-quiesce target)
- `roles/garage/defaults/main.yml` — `garage_container_name` (reference for writer-restart ordering)

### HUMAN-UAT reference format (mirror exactly)
- `.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` — frontmatter shape, `## Current Test` + `## Tests` + numbered scenarios with `expected:` / `result:` / `detail:`. Phase 14 uses the same exact format.
- `.planning/milestones/v1.0.0-phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` — earlier example of the same format

### Pattern references (cold-quiesce, healthy-poll, block/rescue/always)
- `roles/garage/tasks/backup.yml` lines around the `docker_container_info` poll — exact loop shape `restore_docker.yml`'s writer-quiesce mirrors
- `roles/grafana/tasks/verify.yml` — the canonical `docker_container_info` healthy-poll pattern (`until:` + `retries:` + `delay:`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`undeploy_docker.yml`**: closest structural analog for both new orchestrators. The `vars:` knob block, `pre_tasks:` WARN banner with `tags: always`, `tasks:` block of 12 `include_role` calls, and `post_tasks:` for shared-resource cleanup are all directly applicable. `backup_docker.yml` simplifies (no destructive guard, just the banner + 4 include_role calls); `restore_docker.yml` extends (adds writer-stop and writer-restart task blocks bracketing the Garage include_role).
- **`smoke_test.yml`**: directly invoked by 14-HUMAN-UAT scenario 1 steps 2 and 7. The `smoke_trace_id` + `smoke_run_id` mechanics (per-run hex via `lookup('password', '/dev/null')` and epoch) are exactly what scenario 1 records and re-uses. No changes to `smoke_test.yml` needed — Phase 14 just consumes it.
- **Phase 13 task files**: 8 `tasks/backup.yml` + `tasks/restore.yml` ship the per-role surface. Orchestrators just `include_role: name=<role> tasks_from=backup` (or `restore`). One small amendment per D-191: each `tasks/backup.yml` must accept `backup_timestamp_override`.
- **`group_vars/all/backup.yml`**: all 5 knobs already defined in Phase 13. Orchestrators just reference them.
- **`docker_container_info` healthy-poll pattern**: documented in 13-CONTEXT.md as Phase 13's standard. Same pattern used in `roles/grafana/tasks/verify.yml`. Writer-quiesce loop in `restore_docker.yml` reuses this verbatim.

### Established Patterns
- **`tags: always` on WARN banners**: D-157 + D-160 from undeploy_docker.yml. Both new orchestrators' banners use this so the banner displays even on `--tags <role>` runs.
- **`include_role` (not `roles:` block) for per-role tag handling**: D-149 precedent. The roles directive applies tags broadly; explicit include_role lets each call carry its own tag set and ordering. Phase 14 follows this.
- **`WARNING: irreversible --` grep-friendly prefix**: D-159. Restore PLAY-start banner uses it; backup banner does NOT (backup is not destructive).
- **Forward-deploy order = backup order; restore order = same as backup, NOT reversed**: ROADMAP SC1 (backup) and SC2 (restore) both specify garage → prometheus → grafana → alertmanager. Restore is NOT the reverse of deploy (which would be alertmanager-first); restore preserves the storage-dependency-first ordering established by backup. Pattern note: this is different from undeploy's literal-reverse-of-deploy (D-149) pattern. Backup/restore order is content-dependency-driven (Garage = storage backend, must be present first); undeploy is dependency-removal-driven (clients first, then servers).
- **`any_errors_fatal` at play level (not block-level)**: idiomatic Ansible. Telemetron uses it elsewhere; no precedent issue.
- **No async/parallel in writer-quiesce**: every multi-container op in Telemetron is sequential — see undeploy_docker.yml's 12 sequential include_role calls. Writer-quiesce stays consistent.

### Integration Points
- **Phase 13 → Phase 14**: Phase 14 modifies 4 Phase-13 files (each role's `tasks/backup.yml` accepts `backup_timestamp_override`). Phase 14 does NOT modify any Phase-13 `tasks/restore.yml` — those already resolve `backup_restore_from` independently (D-190).
- **Phase 14 → Phase 15**: Phase 15 doc cascade references the final command lines (`ansible-playbook -i inventory/example-homelab playbooks/backup_docker.yml --ask-vault-pass`), the `--extra-vars backup_restore_confirm=true` gate, and the tag-scoped invocations. Phase 14 must finalize these surfaces; Phase 15 documents them.
- **leviathan inventory**: `inventory/leviathan/` is gitignored and present on Rock's workstation (per memory). HUMAN-UAT scenarios use it. Plans don't ship a `inventory/leviathan/` template — operator inventory is BYO.
- **`smoke_test.yml`**: read-only consumer in HUMAN-UAT scenario 1. No changes required.

</code_context>

<specifics>
## Specific Ideas

- **Writer container names referenced inline**: `loki_container_name` (default `telemetron-loki`), `tempo_container_name` (default `telemetron-tempo`), `mimir_container_name` (default `telemetron-mimir`). Writer-quiesce loop reads these from the writer roles' `defaults/main.yml`. Orchestrator loop variable `writer_item` with role+container_name dict.
- **Backup orchestrator structure (per D-186, D-191, D-193)**:
  ```yaml
  vars:
    backup_continue_on_failure: false  # operator opt-in (D-184)
  pre_tasks:
    - debug: PLAY-start banner (D-186)  # tags: always
    - command: date -u +%Y%m%dT%H%M%SZ  # D-191 single timestamp
      register: backup_ts
    - set_fact:
        backup_timestamp_shared: "{{ backup_ts.stdout }}"
  tasks:
    - include_role: name=garage tasks_from=backup
      vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }
      tags: garage
    # ... same shape for prometheus, grafana, alertmanager
  ```
  `any_errors_fatal` at play level (D-184).
- **Restore orchestrator structure (per D-180, D-187, D-189, D-193)**:
  ```yaml
  pre_tasks:
    - fail: confirm gate (mirrors per-role gate)  # tags: always
      when: not backup_restore_confirm
    - debug: WARN banner (D-187)  # tags: always
  tasks:
    - command: docker stop ... (loki, tempo, mimir loop)
      tags: garage  # D-189: tagged garage, fires under --tags garage
    - poll docker_container_info until State.Status==exited
      tags: garage
    - include_role: name=garage tasks_from=restore
      tags: garage
    - command: docker start ... (loki, tempo, mimir loop)
      tags: garage
    - poll docker_container_info until State.Health.Status==healthy
      tags: garage
    - include_role: name=prometheus tasks_from=restore
      tags: prometheus
    - include_role: name=grafana tasks_from=restore
      tags: grafana
    - include_role: name=alertmanager tasks_from=restore
      tags: alertmanager
  ```
  `any_errors_fatal: true` hardcoded (D-185).
- **Phase 13 backup.yml amendment (per D-191)**: each `roles/<role>/tasks/backup.yml` filename-generation task changes from
  ```yaml
  - command: date -u +%Y%m%dT%H%M%SZ
    register: backup_timestamp
  ```
  to using `backup_timestamp_override | default(<call date>)`. Implementation pattern (planner picks one):
  - **Option A**: Add `when: backup_timestamp_override is not defined` to the existing date command, then `set_fact: backup_timestamp_effective: "{{ backup_timestamp_override | default(backup_timestamp.stdout) }}"` and use `backup_timestamp_effective` in the filename.
  - **Option B**: Always call `date`, then `set_fact: backup_timestamp_effective: "{{ backup_timestamp_override | default(backup_timestamp.stdout) }}"`. Simpler — one extra `date` call per role, but the call is microseconds.
  Either works. Planner's call.
- **14-HUMAN-UAT.md frontmatter** (exact format from prior phase):
  ```yaml
  ---
  status: in_progress  # or pending until plans ship
  phase: 14-orchestrators-leviathan-human-uat
  source: [14-VERIFICATION.md]  # if Phase 14 ships VERIFICATION.md, else omit
  started: 2026-XX-XXT...
  updated: 2026-XX-XXT...
  ---
  ```

</specifics>

<deferred>
## Deferred Ideas

- **`writer_stop_timeout` shared knob** — Could be added if 60s reuse becomes ergonomically wrong in practice. v1.3.0 ships single-knob. Capture if operator feedback surfaces.
- **`backup_docker.yml` success summary listing the 4 tarball paths** — Claude's Discretion; planner decides whether to ship.
- **`restore_docker.yml` success summary recommending smoke_test.yml** — Claude's Discretion; planner decides.
- **Per-role override map `backup_restore_from_<role>`** — Out of scope for v1.3.0. Operator who needs per-role timestamp selection wraps the per-role `tasks_from=restore` include_role from a custom playbook (already supported via per-role `backup_restore_from` resolution).
- **`restore_continue_on_failure` knob** — Footgun. Not shipped.
- **Async/parallel writer-quiesce** — D-181 rejected. Could be reconsidered if leviathan UAT shows the sequential time is annoying (it won't be — 3 × <10s stops in a 60-90s window is invisible).
- **Automated fault-injection playbook (`playbooks/uat_inject_failure.yml`)** — Claude's Discretion; HUMAN-UAT scenario 3 can document the manual `chattr +i` instead.
- **Cross-role pre-flight (e.g., "do all 4 backup destination subdirs exist?")** — Each per-role task already lazy-creates its destination subdir at mode 0700 (Phase 13 contract). No orchestrator-level pre-flight needed.
- **Banner with role enumeration** — D-186 explicitly avoids enumerating role names so the banner is stable across role additions. Future additions don't require a banner update.

</deferred>

---

*Phase: 14-orchestrators-leviathan-human-uat*
*Context gathered: 2026-06-03*
