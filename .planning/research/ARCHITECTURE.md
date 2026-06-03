# Architecture: Backup & Restore Integration — Telemetron v1.3.0

**Domain:** Cold-quiesce backup + restore for the 4 stateful roles in an existing 12-role Ansible Docker stack
**Researched:** 2026-06-02
**Confidence:** HIGH — all findings derived from reading existing v1.2.0 source files directly

---

## 1. Per-Role `tasks/backup.yml` Shape

### Canonical task structure (all 4 stateful roles follow this pattern)

```
Task 1 — Pre-flight: assert destination directory exists (mode 0700)
Task 2 — Pre-flight: assert disk free space ≥ 1.5× current volume size
Task 3 — Pre-flight: record timestamp as set_fact
Task 4 — Quiesce: stop container (state: stopped, keep_volumes: true)
Task 5 — Snapshot: archive volume + config_dir into dated tarball
Task 6 — Restart: start container (state: started, no recreate)
Task 7 — Verify: include_tasks: verify.yml
```

**Why 1.5× safety factor, not 2×:** The backup destination is on the same host as the source volumes. Docker named volumes live at `/var/lib/docker/volumes/<name>/_data`; config bind-mounts live at `/opt/telemetron/<role>/`. Both are typically on the same filesystem as `/opt/telemetron/backups/`. 1.5× gives enough headroom for zstd streaming (which doesn't require a full uncompressed intermediate file) without needing 2× the data volume in free space simultaneously. For Garage specifically, a 2× factor should be documented as recommended for deployments with large S3 stores — but 1.5× is the shipped default.

**Disk pre-flight mechanism:** `ansible.builtin.shell` calling `df -k {{ backup_dest_dir }}` and parsing the `Available` column, compared against `du -sk /var/lib/docker/volumes/<meta_vol>/_data` + `du -sk /var/lib/docker/volumes/<data_vol>/_data`. Use `failed_when` on the arithmetic comparison. Do NOT use a separate pre-flight playbook (deferred to v1.4.0).

**Quiesce mechanism:** Reuse the exact same `community.docker.docker_container` call pattern as `uninstall.yml` — `state: stopped, keep_volumes: true`. This is not `state: absent`; the container definition stays, only the process stops. Restart is the symmetric `state: started` with `recreate: false` (critical — we do NOT want the module to re-create the container; we want to restart the existing stopped container).

**Snapshot task:** A single `ansible.builtin.shell` task running `tar --use-compress-program=zstd -cpf` against both the volume path and the config dir. The source paths are:
- Named volume contents: `/var/lib/docker/volumes/<role>_data_volume_name/_data` — accessible from the host without exec into the container because Docker volumes are host filesystem directories
- Config bind-mount: `{{ <role>_config_dir }}` (e.g., `/opt/telemetron/garage/`)

**Important: Garage requires backing up TWO named volumes plus the credentials file.** The meta volume (`telemetron_garage_meta`) holds Garage's lmdb metadata database. The data volume (`telemetron_garage_data`) holds the actual S3 object chunks. The credentials file (`{{ garage_s3_credentials_file }}` = `/opt/telemetron/garage/s3-credentials`) is inside `garage_config_dir`, so it gets captured in the config dir pass automatically — no separate step needed. The single tarball for garage includes all three: meta_vol + data_vol + config_dir.

**Restart behavior:** After `state: started`, do NOT use `recreate: true`. The existing container record must be restarted, not re-created from the module's perspective. `recreate: false` is the default but must be explicit in the task YAML as documentation intent.

**Verify step:** Call `include_tasks: verify.yml` directly (the same verify.yml that deploy uses). This is the exact same include_tasks pattern already used in `tasks/bootstrap.yml` (garage) and in `deploy_docker.yml` flows. No new wrapper needed.

### Tags

Each backup task carries TWO tags: the role tag and a `backup` tag. Pattern:

```yaml
tags:
  - garage
  - backup
```

This follows the existing sub-tag convention for cross-cutting operations. The deploy-side sub-tags (`garage-config`, `garage-container`, `garage-bootstrap`) demonstrate the pattern. The `backup` tag is the cross-cutting way for the orchestrator to scope all backup tasks in a single `--tags backup` run; the role tag allows `--tags garage` to pick up only Garage's backup task when iterating over a single role. Both together is correct per the D-133 spirit: a single role tag is the minimum; sub-tags serve specific cross-cut purposes.

**Contrast with Gate 10:** The uninstall pattern explicitly says "tasks carry the role tag only, no `<role>-uninstall` sub-tag (D-133)." Backup is different — `backup` is a legitimate cross-cutting sub-operation that the orchestrator needs to route by. D-133's prohibition was against `garage-uninstall` (operational-phase sub-tags that just duplicate the include-path context), not against functional sub-tags like `backup` that the operator would actually use standalone.

---

## 2. Per-Role `tasks/restore.yml` Shape

### Canonical task structure

```
Task 1 — Pre-flight: assert backup source path resolves (stat + fail)
Task 2 — Pre-flight: integrity-check the tarball (tar tf)
Task 3 — WARN: D-159 irreversible-pattern warning before any destructive step
Task 4 — Gate: fail unless backup_restore_confirm=true
Task 5 — Quiesce: stop container (state: stopped, keep_volumes: true)
Task 6 — Clear: wipe existing volume contents (shell: rm -rf /path/_data/*)
Task 7 — Restore: untar into volume paths
Task 8 — Restart: start container (state: started, recreate: false)
Task 9 — Verify: include_tasks: verify.yml
```

**Source path resolution:** The orchestrator passes `backup_restore_from` (a UTC timestamp string matching the tarball name pattern, e.g. `2026-06-02T14:30:00Z`) or `backup_restore_latest` (boolean, defaults true). When `backup_restore_latest=true`, the role finds the newest tarball in `{{ backup_dest_dir }}/<role>/` via `ansible.builtin.find` with `file_type: file`, sorting by `mtime`, and taking the first result. When `backup_restore_from` is set, the role constructs the expected path directly. The `stat` gate fails clearly if the file does not exist.

**Integrity check:** `ansible.builtin.command` running `tar tf <path>` (list-only, no extract). For `.tar.zst` this requires `--use-compress-program=zstd` or equivalently `zstdcat <path> | tar t`. The integrity check guards against partial tarballs from a failed backup run. `failed_when: rc != 0` on the command.

**D-159 WARN before destructive step:** Mirror the exact pattern from purge.yml:
```yaml
- name: WARN -- restore will overwrite existing <role> volume contents
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- <role> restore: existing volume data will be replaced from {{ backup_src_path }}"
```
This WARN task is separately named so it appears as its own line in PLAY OUTPUT — same contract as D-145/D-159.

**Confirm gate:** The confirm gate belongs IN the per-role restore.yml (not only in the orchestrator), so that `include_role: tasks_from=restore` called standalone also enforces the gate. Pattern:
```yaml
- name: Fail unless backup_restore_confirm is set
  ansible.builtin.fail:
    msg: "Restore is destructive. Set --extra-vars backup_restore_confirm=true to confirm."
  when: not (backup_restore_confirm | default(false) | bool)
```
The orchestrator additionally shows the D-160-style PLAY-start banner warning, but the per-role gate is the hard stop.

**Clear step:** `ansible.builtin.shell: rm -rf /var/lib/docker/volumes/<volume_name>/_data/*` for each named volume. This is "purge contents but keep the Docker volume object" — identical in intent to what `purge.yml` does, but scoped to the content only (the Docker volume record itself must persist, because `state: started` below re-attaches by name). Do NOT use `community.docker.docker_volume: state: absent` here — that would remove the volume record and force re-creation with a new volume ID, which may break Docker's mount table. Shell glob-clear is correct.

**Restore step:** `ansible.builtin.shell` running `tar --use-compress-program=zstd -xpf <tarball> -C /` (the tarball was created with absolute paths rooted at `/var/lib/docker/volumes/` and `/opt/telemetron/<role>/`). Alternatively the tarball can be created with relative paths and extracted with explicit `-C /var/lib/docker/volumes/<name>/_data` per-volume. The implementation must be consistent between backup.yml and restore.yml.

**Restart + verify:** Same as backup.yml — `state: started, recreate: false`, then `include_tasks: verify.yml`.

### Tags

Restore tasks carry the role tag and `restore`:
```yaml
tags:
  - garage
  - restore
```

---

## 3. Orchestrator Design — `playbooks/backup_docker.yml`

### Structure

Mirrors `deploy_docker.yml` shape exactly: one PLAY, `hosts: telemetron`, `gather_facts: true`, `become: false`, `collections: community.docker`. Pre-tasks banner; tasks block iterating the 4 stateful roles via `include_role: { tasks_from: backup }`; no post-tasks needed (no network to remove, unlike undeploy).

### Role ordering

**Any order is fine for backup** — each of the 4 stateful roles (garage, prometheus, grafana, alertmanager) is fully independent. Their volumes do not reference each other. Use the same forward deploy order for consistency: garage → prometheus → grafana → alertmanager. This matches the mental model operators already have from `deploy_docker.yml`.

Only include the 4 stateful roles in `backup_docker.yml`. The 8 stateless roles do NOT appear in the orchestrator. There are no no-op include_role calls for loki/tempo/mimir/etc.

### Serial vs parallel

Serial (one role at a time, no `serial:` directive which defaults to all hosts in sequence). Parallel within the host doesn't apply — we're operating on a single Docker host. The concern isn't Ansible's host parallelism but the serial role iteration. Run roles sequentially (the default `include_role` behavior in a `tasks:` block): stop garage, snapshot, restart, verify; then stop prometheus, snapshot, restart, verify; etc. Running all 4 stops simultaneously would maximize combined downtime (Grafana unusable for the whole backup window instead of just the 30-60s while Grafana itself is quiesced). Sequential is the right default.

### PLAY-start banner (pre_tasks)

D-160 style, `tags: always`. Content matches the backup-specific shape:

```yaml
- name: Backup status -- roles and destination
  ansible.builtin.debug:
    msg: |
      Telemetron backup starting -- 4 stateful roles
      Destination: {{ backup_dest_root | default('/opt/telemetron/backups') }}
      Continue on failure: {{ backup_continue_on_failure | default(false) }}
```

No list of role names in the message (per D-160 principle: category descriptions, not name enumeration, so the banner stays accurate if a role is skipped via `--tags`).

### Bail-out failure semantics

**Default:** bail on first role failure — Ansible's default `any_errors_fatal` behavior within a play is NOT the default, but `include_role` failure stops the play naturally. No extra mechanism needed for the default bail-out: if the backup task for garage fails, the tasks block for prometheus never starts.

**Override:** `backup_continue_on_failure=true` sets `ignore_errors: "{{ backup_continue_on_failure | default(false) | bool }}"` on each `include_role` call (or equivalently `failed_when: false` on the include). The flag belongs on each individual `include_role` call in the orchestrator, NOT inside the per-role backup.yml. This way the per-role task file fails correctly and surfaces error output; the orchestrator decides whether to continue.

```yaml
- name: Invoke garage backup
  ansible.builtin.include_role:
    name: garage
    tasks_from: backup
  ignore_errors: "{{ backup_continue_on_failure | default(false) | bool }}"
  tags:
    - garage
    - backup
```

### `--tags loki` on backup_docker.yml

Because loki does not appear in `backup_docker.yml` at all, `--tags loki` produces an empty play (no matching tasks). Ansible reports "PLAY RECAP: 0 tasks" — this is clean behavior, not a failure. The operator sees "skipped" in the sense that nothing ran. **No explicit no-op task needed.** Document this behavior in the playbook header comment.

---

## 4. Orchestrator Design — `playbooks/restore_docker.yml`

### Structure

Same pattern as `backup_docker.yml`. Single PLAY. `vars:` block declares the two operator-facing knobs:
```yaml
vars:
  backup_restore_confirm: false         # must be true for restore to proceed
  backup_restore_from: ""               # timestamp string or empty (uses latest)
  backup_continue_on_failure: false     # same opt-in as backup
```

### Role ordering

**Deploy order** (same as `deploy_docker.yml`): garage → prometheus → grafana → alertmanager. Rationale: Garage must be up and healthy before the stateless Loki/Tempo/Mimir roles can query it. Even though those roles are stateless from Telemetron's perspective, restoring Garage's S3 data first means that if the operator then runs `deploy_docker.yml` to re-deploy the stateless roles, they come up against the correct already-restored bucket contents. Order consistency with deploy is the conventional choice when the 4 roles are mutually independent — it prevents operator confusion.

### Post-restore re-deploy of stateless roles

**Not automatic.** After restoring Garage, the operator must manually re-run `deploy_docker.yml --tags loki,tempo,mimir` if the Garage S3 key changed (which it will have if the restore cycle included `undeploy --purge-data`). Document this explicitly in the playbook header and in the quickstart. The decision: Telemetron does one thing (restore state); chaining into deploy_docker.yml from within restore_docker.yml would create an implicit dependency between playbooks and make the restore playbook non-atomic. Operator-manual chaining is the right call.

**Garage credential recovery after restore:** If the restore includes the `s3-credentials` file (it does, since it's inside `garage_config_dir`), the restored credentials file is the one Loki/Tempo/Mimir were configured against at backup time. Bootstrap.yml's D-146 "length==1 orphan reuse" logic handles the case where the container has a new orphan key post-purge-data cycle — but after a restore, the credentials file is restored to its original state, so bootstrap should find the credential file and re-use those credentials. This means the post-restore Garage bootstrap path is: file exists → slurp existing key_id → verify key exists in `garage key list` → if found, reuse → bucket allow grants are idempotent. The logic is already in bootstrap.yml. No changes needed, but verify this during leviathan UAT.

### PLAY-start banner (pre_tasks)

This IS the destructive orchestrator — stronger banner than backup. Pattern mirrors D-160 but escalates the warning:

```yaml
- name: WARN -- restore will overwrite stateful role data
  ansible.builtin.debug:
    msg: |
      WARNING: restore is destructive -- existing volume contents for each
      restored role will be PERMANENTLY REPLACED with the backup tarball contents.
      backup_restore_confirm={{ backup_restore_confirm | default(false) }}
      {{ 'Restore will proceed.' if backup_restore_confirm | default(false) | bool else 'Set --extra-vars backup_restore_confirm=true to allow restore.' }}
  tags:
    - always
```

The per-role `tasks/restore.yml` also has its own `fail` gate (Task 4 in the restore shape above), so the banner alone is informational — the hard stop is in the role.

---

## 5. Per-Role Tag Inheritance

**Recommendation: role tag + `backup` or `restore` sub-tag. No `<role>-backup` sub-tag.**

Concretely: `tags: [garage, backup]` and `tags: [garage, restore]`.

The D-133 lesson (from Phase 10 undeploy) was that `garage-uninstall` as a sub-tag was wrong because it fragmented targeting without adding expressiveness — `--tags garage` already selected all garage tasks, and adding `-uninstall` was operational noise. The backup/restore case is different: `backup` and `restore` are **cross-role functional sub-tags** that the operator legitimately uses (`--tags backup` to run all 4 backups; `--tags restore` to run all 4 restores). These are analogous to `garage-bootstrap` and `garage-config` sub-tags that already exist — functional, not operational-phase naming.

`<role>-backup` (e.g. `garage-backup`) is wrong for the same D-133 reason: it adds per-role operational noise. The cross-cutting `backup` tag is what makes the tag useful.

---

## 6. Stateless Role Handling

**Recommendation: Option A — stateless roles ship nothing. The orchestrator iterates only the 4 stateful roles.**

Option B (no-op backup.yml for all roles) is rejected because it adds maintenance surface for no value. A no-op task file is still a file that can drift, break, accumulate YAML errors, and confuse contributors who wonder what it does. The "uniform contract" argument is appealing but Gate 11 can be expressed more honestly as "every STATEFUL role ships a tested backup + restore path" — stateless roles don't have a backup story and pretending they do via empty files is dishonest.

Option C (stateless roles get a README `## Backup` section saying "this role is stateless") is the right answer for DOCUMENTATION but does not require task files. The README section is cheap and adds real value (an operator who reads `roles/loki/README.md` and sees `## Backup: This role is stateless — no backup needed. Loki's data lives in Garage's S3 store.` understands the full story without confusion).

**Concrete Gate 11 formulation (for roles/README.md):**
> Every stateful role ships `tasks/backup.yml` and `tasks/restore.yml` with a tested leviathan round-trip. Every stateless role's README documents that it carries no operator state (and where that state actually lives if relevant). The 4 stateful roles are: garage, prometheus, grafana, alertmanager.

This is cleaner than a blanket "every role declares its backup story via a task file."

---

## 7. Verification Orchestration — Leviathan UAT

**Recommendation: HUMAN-UAT document (`14-HUMAN-UAT.md`), NOT an automated `backup_restore_uat.yml` playbook.**

Rationale: the v1.1.0 and v1.2.0 pattern is the established quality bar. Both milestones shipped a `*-HUMAN-UAT.md` that the operator (Rock) runs by hand on leviathan. An automated round-trip playbook (`backup_restore_uat.yml`) sounds attractive but introduces its own correctness surface: the UAT playbook would need to push synthetic OTLP signals, wait for Garage chunk landing, run backup, run undeploy, run deploy, run restore, then assert the signals are still queryable — which is essentially the entire smoke_test.yml wired into a new orchestrator. That's Phase 15 scope creep, and it would be the first playbook in the repo that calls other playbooks (not supported natively in Ansible; would require `delegate_to: localhost` + `ansible.builtin.command: ansible-playbook ...` antipattern).

**The correct leviathan UAT round-trip is:**
1. Deploy fresh stack: `deploy_docker.yml`
2. Run smoke_test.yml → record `smoke_trace_id` + `smoke_run_id` from summary output
3. Run `backup_docker.yml`
4. Run `undeploy_docker.yml --extra-vars telemetron_purge_data=true`
5. Run `deploy_docker.yml` (re-deploys fresh containers; Garage bootstrap creates new S3 key against empty volumes)
6. Run `restore_docker.yml --extra-vars backup_restore_confirm=true backup_restore_from=<timestamp>`
7. Run `smoke_test.yml` with the SAME `smoke_trace_id` + `smoke_run_id` → assert results are visible

Step 7 requires the smoke_test.yml to support querying by a known trace_id — it already does (`smoke_trace_id` is a var the operator can override). The operator records the values from step 2, plugs them into step 7.

**Trust signal:** The leviathan HUMAN-UAT document is the quality bar, matching v1.1.0/v1.2.0 precedent. The v1.1.0 lesson ("ansible deploy phases require a real live-deploy gate beyond the static verifier") applies directly: backup/restore involves volume manipulation that only a real Docker host surfaces correctly.

---

## 8. Storage Layout on Host

**Recommendation: per-role subdirectories. No manifest file.**

```
/opt/telemetron/backups/
  garage/
    garage-2026-06-02T14-30-00Z.tar.zst
    garage-2026-06-02T22-15-00Z.tar.zst
  prometheus/
    prometheus-2026-06-02T14-30-05Z.tar.zst
  grafana/
    grafana-2026-06-02T14-30-45Z.tar.zst
  alertmanager/
    alertmanager-2026-06-02T14-31-15Z.tar.zst
```

**Why per-role subdirs:** matches the per-role mental model operators already have from `/opt/telemetron/<role>/`. Per-role rsync (`rsync /opt/telemetron/backups/garage/ backup-host:`) works naturally. Flat layout makes per-role rsync and `backup_restore_latest` logic (find newest file for THIS role) more complex.

**Why no manifest.json:** overkill for a homelab single-host operator. A manifest adds a write path that can go stale, drift from actual files, and mislead. The operator can `ls -lt /opt/telemetron/backups/garage/` to see what's there. A manifest is only valuable when there are hundreds of backups across dozens of roles with complex dependencies — not this stack.

**Timestamp format in filename:** Use `%Y-%m-%dT%H-%M-%SZ` (hyphens in time component, not colons — colons are illegal in filenames on many filesystems and awkward in shell). The `ansible_date_time.iso8601` fact returns `2026-06-02T14:30:00Z`; replace colons via `| replace(':', '-')` in Jinja.

**Directory mode:** `mode: 0700` for `/opt/telemetron/backups/` and per-role subdirs. Tarballs written `mode: 0600`. Rationale: Garage's tarball contains the s3-credentials file (which includes the S3 secret key); Prometheus's TSDB may contain metric values the operator considers sensitive. 0700/0600 is the right default even though encryption is deferred.

---

## 9. Gate 11 Integration with Gate 10

Gate 10 (`roles/README.md`, Phase 10) codifies: "every deploy role ships a tested uninstall path."

Gate 11 should be scoped tightly: "every STATEFUL role ships tested `tasks/backup.yml` and `tasks/restore.yml`, proven on leviathan end-to-end. Stateless roles document their no-backup status in their role README."

Gate 11 does NOT need an "explicit enforcement" for stateless roles (no gating check, no empty task file). The distinction is:
- Gate 10 is uniform across ALL roles (every deploy role has an uninstall path — this was important because undeploy_docker.yml iterates ALL roles)
- Gate 11 is scoped to stateful roles only (backup_docker.yml iterates only 4 roles, so no role-completeness enforcement gap exists)

The Gate 11 paragraph in `roles/README.md` should list the 4 stateful roles explicitly so the gate is unambiguous, rather than leaving the determination of "which roles are stateful" as an exercise.

---

## 10. `secrets.yml` Integration

**The separation of concerns is clear and must be stated explicitly in documentation:**

Telemetron backs up **Telemetron-managed runtime state**. The operator backs up **everything else**.

What Telemetron's backup covers:
- Garage: lmdb metadata, S3 object data, the auto-generated s3-credentials file (D-112 host-file persistence pattern)
- Prometheus: TSDB time-series data
- Grafana: embedded SQLite (dashboards, users, org config, alert state, annotations)
- Alertmanager: silence registry and nflog

What Telemetron's backup explicitly does NOT cover:
- `inventory/<env>/group_vars/all/secrets.yml` — contains `garage_admin_token`, `garage_rpc_secret`, `grafana_admin_password`, `prometheus_bearer_token`, and future secrets. This is version-control or operator-encrypted inventory state, not runtime state.
- `ansible-vault` password — operator-managed
- The ansible inventory directory itself (`inventory/example-homelab/`)

**The operator story (to document in quickstart.md):**
> Telemetron's backup covers the runtime state that components generate during operation (databases, time-series, object storage). Your `inventory/` directory — including `secrets.yml` — is configuration state that you own and should version-control or back up separately. Without your inventory, a restore is incomplete: Telemetron would restore the data but wouldn't know how to reconnect the components to each other.

**Garage credential nuance:** The `s3-credentials` file IS backed up (it lives inside `garage_config_dir`). A full restore from backup restores the original S3 key pair, so Loki/Tempo/Mimir re-deploy after restore will find valid credentials matching the restored Garage state. This is the correct behavior and should be called out explicitly in the Garage role's backup documentation — it's different from the post-undeploy D-146 recovery story where credentials are regenerated.

---

## Component Map — New Files Introduced in v1.3.0

### Per-role additions (4 roles)

| File | Role | Notes |
|------|------|-------|
| `roles/garage/tasks/backup.yml` | garage | Two volumes (meta + data) + config dir including s3-credentials |
| `roles/garage/tasks/restore.yml` | garage | Must also trigger bootstrap sequence post-restart to verify key + buckets |
| `roles/prometheus/tasks/backup.yml` | prometheus | Single data volume + config dir |
| `roles/prometheus/tasks/restore.yml` | prometheus | |
| `roles/grafana/tasks/backup.yml` | grafana | Single data volume (SQLite) + config dir (provisioning) |
| `roles/grafana/tasks/restore.yml` | grafana | First-boot-only GF_SECURITY_ADMIN_PASSWORD env var means restored SQLite carries original admin password — document this |
| `roles/alertmanager/tasks/backup.yml` | alertmanager | Single data volume (silences/nflog) + config dir |
| `roles/alertmanager/tasks/restore.yml` | alertmanager | |

### New orchestrators

| File | Notes |
|------|-------|
| `playbooks/backup_docker.yml` | 4 stateful roles only; serial; bail-out default; D-160 banner |
| `playbooks/restore_docker.yml` | 4 stateful roles; deploy order; D-160 WARN banner; per-role confirm gate |

### New shared variables (inventory group_vars or playbook vars)

| Variable | Default | Notes |
|----------|---------|-------|
| `backup_dest_root` | `/opt/telemetron/backups` | Root directory for all backups |
| `backup_continue_on_failure` | `false` | Opt-in bail-out override |
| `backup_restore_confirm` | `false` | Must be true for restore to proceed |
| `backup_restore_from` | `""` (empty = latest) | Timestamp string for specific restore |
| `backup_space_factor` | `1.5` | Safety multiplier for pre-flight disk check |

---

## Build Order Implications

Phase 13 (per-role tasks) must complete before Phase 14 (orchestrators + UAT) because:
- The orchestrators call `include_role: tasks_from: backup` and `tasks_from: restore` — those files must exist for the orchestrator to run
- Leviathan UAT requires a real round-trip, which requires the per-role tasks to be correct end-to-end

Within Phase 13, the 4 roles are independent — garage, prometheus, grafana, alertmanager can be authored in any order and tested individually via `backup_docker.yml --tags <role>` once the orchestrator is a stub.

**Recommended sub-ordering within Phase 13:** garage first (most complex — two volumes + bootstrap interaction + credential file), then prometheus (simplest stateful role — single volume, no bootstrap), then grafana (SQLite + first-boot-password nuance), then alertmanager (simple single volume).

Phase 15 (docs + Gate 11) is purely additive and does not block Phase 14.

---

## Interaction with Existing v1.2.0 Contracts

| Contract | v1.3.0 Impact |
|----------|---------------|
| Gate 10 (every deploy role ships uninstall.yml) | No change — backup/restore are new task files alongside uninstall, not replacing it |
| D-133 (single role tag on tasks) | Extended: backup + restore tasks carry `[<role>, backup]` or `[<role>, restore]` — the cross-cutting sub-tag is justified because `--tags backup` is a legitimate operator command |
| D-148 (conservative default, opt-in for irreversible) | restore.yml mirrors this: default fail-unless-confirmed; operator passes `backup_restore_confirm=true` |
| D-159 (WARN prefix before destructive actions) | Applies to all restore clear-volume tasks: `WARNING: irreversible -- <role> restore: ...` |
| D-160 (PLAY-start banner) | Both playbooks ship a `tags: always` pre_tasks banner per this pattern |
| D-146 (Garage S3 credential recovery story) | A successful restore puts back the original credentials file, so D-146's "regenerate on missing file" branch is NOT triggered. Document this divergence explicitly. |
| uninstall.yml `state: absent, keep_volumes: true` pattern | backup.yml uses `state: stopped, keep_volumes: true` — different state, same volume-preservation intent |
| verify.yml call pattern (include_tasks) | backup.yml and restore.yml both call `include_tasks: verify.yml` after container restart, identical to how bootstrap.yml calls it in garage |
