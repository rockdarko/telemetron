---
phase: 13-per-role-backup-restore-tasks
plan: 02
subsystem: garage-backup-restore
tags: [phase-13, backup, restore, garage, ansible-tasks]
dependency_graph:
  requires:
    - inventory/example-homelab/group_vars/all/backup.yml (Wave 1 / 13-01 — provides backup_dest_root, backup_stop_timeout, backup_restore_confirm, backup_restore_from)
    - roles/garage/defaults/main.yml (Wave 1 / 13-01 — provides garage_backup_stop_timeout)
    - roles/garage/defaults/main.yml (existing — garage_container_name, garage_meta_volume, garage_data_volume, garage_config_dir, garage_s3_credentials_file, garage_health_retries, garage_health_delay)
    - roles/garage/tasks/bootstrap.yml lines 21-35 (analog — inline docker_container_info healthy-poll, copied verbatim with until: flipped)
    - roles/garage/tasks/purge.yml lines 66-72 (analog — D-159 WARN + gate idiom)
    - roles/garage/tasks/main.yml lines 7-14 (analog — ansible.builtin.file state: directory destination create)
    - roles/garage/tasks/uninstall.yml (analog — docstring-style header narrative)
    - roles/nfsd/tasks/install_debian.yml lines 5-11 (analog — only ansible.builtin.package precedent in repo)
  provides:
    - roles/garage/tasks/backup.yml (include target — `include_role: name=garage tasks_from=backup`)
    - roles/garage/tasks/restore.yml (include target — `include_role: name=garage tasks_from=restore`)
    - 3-entry tarball contract (meta/ + data/ + s3-credentials per D-176) for Phase 14 latest-discovery glob and Phase 15 docs
    - block/always/restart skeleton pattern that plans 13-03..13-05 can mirror (with include_tasks: verify.yml replacing the inline poll for prometheus/grafana/alertmanager)
  affects:
    - Plan 13-03 (prometheus backup/restore — same skeleton, single volume, include_tasks: verify.yml in always:)
    - Plan 13-04 (grafana backup/restore — same skeleton, single volume, verify.yml include)
    - Plan 13-05 (alertmanager backup/restore — same skeleton + empty-data-dir stat guard, verify.yml include)
    - Phase 14 orchestrators (playbooks/backup_docker.yml + playbooks/restore_docker.yml) — call `include_role: name=garage tasks_from=backup` and `tasks_from=restore`
    - Phase 15 docs cascade (docs/quickstart.md + roles/garage/README.md `## Backup` H2) — references tarball entries + restore gate
tech_stack:
  added: []
  patterns:
    - Pattern A: block/always container-restart guarantee (AN-2). NEW in repo — no prior precedent.
    - Pattern B: `ansible.builtin.command: docker stop -t N <name>` + `community.docker.docker_container_info` poll until `State.Running == false` (XP-1). Stop CLI is new; poll shape verbatim from bootstrap.yml.
    - Pattern C: `ansible.builtin.package: zstd state: present` ensure-present pre-task (OPS-V13-04). Adapted from nfsd/install_debian.yml.
    - Pattern D: lazy idempotent destination-dir create at mode 0700 (XP-4). Adapted from garage/main.yml.
    - Pattern E: D-159 destructive WARN with "WARNING: irreversible -- garage restore: ..." prefix. Adapted from garage/purge.yml.
    - Pattern G: `find ... | sort -r | head -1` latest-discovery (D-179) + `tar --zstd -tf` integrity check. NEW in repo.
    - Pattern H: `find /var/lib/docker/volumes/<vol>/_data -mindepth 1 -delete` in-place wipe (STACK.md sec.3). NEW in repo.
    - Pattern I: `ansible.builtin.fail` confirm gate with `when: not (backup_restore_confirm | default(false) | bool)`. NEW in repo; idiom mirrors purge.yml.
    - 3-entry single-tarball construction via three `--transform` invocations (NEW; D-176 Garage-specific).
    - 3-entry symmetric extract via three `tar --zstd -xpf -C ... --strip-components=1` invocations (NEW; D-176 inverse).
key_files:
  created:
    - roles/garage/tasks/backup.yml
    - roles/garage/tasks/restore.yml
  modified: []
decisions:
  - D-176 (single tarball, 3 top-level entries) — IMPLEMENTED. backup.yml uses one `tar --zstd -cpf` with three `--transform` regexes; restore.yml extracts each entry to its canonical destination with three separate `tar --zstd -xpf` invocations using `--strip-components=1` for the two volume entries and a bare `-C` for the s3-credentials host file.
  - D-178 (verify pattern) — IMPLEMENTED for Garage variant. Inline `community.docker.docker_container_info` healthy poll in `always:` block (verbatim shape from bootstrap.yml lines 21-35). No `include_tasks: verify.yml` because Garage ships no such file (verification lives in tasks/main.yml + tasks/bootstrap.yml).
  - D-179 (ISO 8601 basic UTC timestamp) — IMPLEMENTED. backup.yml: `ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ`. restore.yml: latest-discovery via `find ... | sort -r | head -1` (lexicographic sort is chronological because format is monotonic).
  - GP-3 (s3-credentials in tarball; D-146 self-healing branch must NOT fire post-restore) — IMPLEMENTED. backup.yml includes `{{ garage_s3_credentials_file }}` as third source; restore.yml extracts it back to the host file BEFORE the container restarts.
  - AN-2 (always-restart) — IMPLEMENTED via block/always wrapper in both files. No rescue: body needed (ARCHITECTURE.md sec.3: orchestrator-level continue-on-failure handles bail-out).
  - AN-3 (vault token rotation breaks bootstrap if garage_admin_token rotated between backup and restore) — DOCUMENTED in restore.yml header. No code-level guard (operator-procedural).
  - XP-1 (docker stop CLI, NOT community.docker state: stopped) — IMPLEMENTED. `ansible.builtin.command: docker stop -t {{ garage_backup_stop_timeout }} {{ garage_container_name }}` in both files. No `state: stopped` anywhere.
  - XP-4 (mode 0700 dir, 0600 tarball, 0600 restored s3-credentials) — IMPLEMENTED. Three `ansible.builtin.file mode:` assertions.
  - AN-1 (no `state: absent` on `community.docker.docker_container`) — RESPECTED. Per-file `ansible.builtin.file state: absent` for s3-credentials host file removal is correct (AN-1 governs only the docker_container module).
metrics:
  duration: ~10min
  completed_date: 2026-06-03
---

# Phase 13 Plan 02: Garage backup + restore Ansible task files Summary

Ships `roles/garage/tasks/backup.yml` (191 lines) and `roles/garage/tasks/restore.yml` (278 lines) — the most complex of the four Wave-2 stateful-role pairs because Garage carries 3 distinct entries in one tarball (meta volume + data volume + s3-credentials host file) per locked decision D-176. Both files use the new repo-wide `block`/`always` restart-guarantee pattern (AN-2) and the new `docker stop` cold-quiesce CLI (XP-1).

## What Was Built

### 1. `roles/garage/tasks/backup.yml` (Task 1, 191 lines)

7-task backup file matching ARCHITECTURE.md sec.1's locked shape:

1. **`zstd` ensure-present pre-task** (OPS-V13-04) — `ansible.builtin.package` idempotent. Tags `[garage, backup]`.
2. **Destination subdir create** at mode 0700 (XP-4) — `ansible.builtin.file: state: directory`. Lazy idempotent.
3. **UTC timestamp record** (D-179) — `ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ` registered as `backup_timestamp`.
4. **`block:`** opens — stop + tar sequence wrapped per AN-2.
   - **Stop container** via `ansible.builtin.command: "docker stop -t {{ garage_backup_stop_timeout }} {{ garage_container_name }}"` (XP-1; never `state: stopped`).
   - **Poll until stopped** — `community.docker.docker_container_info` with `until: State.Running == false`, retries 30, delay 2.
   - **3-entry tar** — one invocation, three `--transform` rewrites, three source paths:
     - `/var/lib/docker/volumes/{{ garage_meta_volume }}/_data` → `meta/`
     - `/var/lib/docker/volumes/{{ garage_data_volume }}/_data` → `data/`
     - `{{ garage_s3_credentials_file }}` → `s3-credentials`
   - **Tarball perms** — `ansible.builtin.file mode: "0600"` (XP-4).
5. **`always:`** — restart + inline healthy-poll guaranteed (AN-2 + D-178).
   - **Restart** — `ansible.builtin.command: "docker start {{ garage_container_name }}"`.
   - **Inline healthy-poll** — verbatim shape from bootstrap.yml lines 21-35 (D-178; no `include_tasks: verify.yml` because Garage ships none).
6. **Block tags** `[garage, backup]` on the parent (single source for cross-cutting tag).

### 2. `roles/garage/tasks/restore.yml` (Task 2, 278 lines)

Symmetric inverse with confirm-gate + integrity check + 3-entry extract:

1. **`zstd` ensure-present** (OPS-V13-04) — same shape as backup.yml.
2. **Confirm gate (Pattern I)** — `ansible.builtin.fail` with `when: not (backup_restore_confirm | default(false) | bool)`. Fires INSIDE the role-task so a standalone `include_role: tasks_from=restore` is also blocked without the flag (CONTEXT.md "Carrying forward").
3. **Latest-tarball discovery (Pattern G, D-179)** — `find {{ backup_dest_root }}/garage/ -name 'garage-*.tar.zst' -type f -printf '%f\n' | sort -r | head -1`. `failed_when:` guards against empty backup dir. Only runs when `backup_restore_from` is empty.
4. **`backup_src_path` set** — two mutually-exclusive `set_fact` tasks: one for latest-discovered path, one for operator-pinned timestamp.
5. **D-159 WARN (Pattern E)** — `WARNING: irreversible -- garage restore: {{ garage_meta_volume }}, {{ garage_data_volume }}, {{ garage_s3_credentials_file }} from {{ backup_src_path }}`. Names ONLY destination identifiers — does NOT echo tarball contents or existing volume contents (CONTEXT.md mandate).
6. **Integrity check (Pattern G)** — `tar --zstd -tf {{ backup_src_path }}`. Runs BEFORE any wipe step (verified by `awk '/tar --zstd -tf/{tf=NR} /-mindepth 1 -delete/{wipe=NR} END{exit !(tf < wipe)}'`).
7. **`block:`** opens — stop + wipe + 3-entry untar wrapped per AN-2.
   - **Stop** + **poll-until-stopped** (same shape as backup.yml).
   - **Wipe meta volume** — `find /var/lib/docker/volumes/{{ garage_meta_volume }}/_data -mindepth 1 -delete` (STACK.md sec.3; not `docker_volume state: absent`).
   - **Wipe data volume** — symmetric `find ... -mindepth 1 -delete`.
   - **Remove existing s3-credentials host file** — `ansible.builtin.file state: absent` (per-file scope; AN-1 governs only `community.docker.docker_container`).
   - **Extract `meta/` entry** — `tar --zstd -xpf {{ backup_src_path }} --strip-components=1 -C /var/lib/docker/volumes/{{ garage_meta_volume }}/_data meta`. Drops the `meta/` prefix so files land at `_data/db.lmdb/`.
   - **Extract `data/` entry** — symmetric.
   - **Extract `s3-credentials` entry** — `tar --zstd -xpf {{ backup_src_path }} -C {{ garage_config_dir }} s3-credentials`. Lands at exactly `{{ garage_s3_credentials_file }}` because `garage_s3_credentials_file = {{ garage_config_dir }}/s3-credentials` (defaults/main.yml line 109).
   - **Re-apply mode 0600** to restored s3-credentials (XP-4 defense-in-depth).
8. **`always:`** — restart + inline healthy-poll (same shape as backup.yml).
9. **Block tags** `[garage, restore]` on the parent.

## Verification Results

```
$ python3 -c "import yaml; yaml.safe_load(open('roles/garage/tasks/backup.yml'))"
(parses OK)
$ python3 -c "import yaml; yaml.safe_load(open('roles/garage/tasks/restore.yml'))"
(parses OK)

$ ansible-playbook playbooks/deploy_docker.yml --syntax-check -i inventory/example-homelab/hosts --vault-password-file <(echo dummy)
playbook: playbooks/deploy_docker.yml   (exit 0)

$ # Synthetic include-role probes for both files
$ ansible-playbook /tmp/probe-include-backup.yml --syntax-check
playbook: /tmp/probe-include-backup.yml   (exit 0)
$ ansible-playbook /tmp/probe-include-restore.yml --syntax-check
playbook: /tmp/probe-include-restore.yml   (exit 0)

Plan-level acceptance criteria for backup.yml:
  - YAML parses: OK
  - `docker stop` present: 1 occurrence
  - `block:` / `always:` openers: 2 (one of each at the same indent)
  - `state: stopped` (non-comment): 0
  - `state: absent` on docker_container: 0
  - `zstd` ensure-present: present
  - {{ garage_meta_volume }} / {{ garage_data_volume }} / {{ garage_s3_credentials_file }}: all 3 present
  - --transform count: 5 (3 for tar in backup -- the other 2 are unrelated text mentions in comments)
  - mode "0600" / mode "0700": both present
  - tags [garage, backup]: 4 tag stanzas
  - docker start in `always:` block: line 165 (after always: line 152)
  - inline healthy poll: present; include_tasks: verify.yml: 0
  - D-176/D-178/GP-1/GP-3/AN-2 citations in header: 17 hits
  - wc -l: 191

Plan-level acceptance criteria for restore.yml:
  - YAML parses: OK
  - backup_restore_confirm gate context: 2 preceding-context hits + 1 trailing `when:` clause
  - `find ... | sort -r | head -1` (D-179): present
  - tar tf BEFORE wipe (line ordering): verified (tf line < wipe line)
  - "WARNING: irreversible -- garage restore": 1 occurrence
  - 3-entry coverage: meta_volume + data_volume + s3_credentials_file all present
  - Two `find ... -mindepth 1 -delete` wipe tasks: 2
  - state: absent on credentials file (proximity): 1 context hit, none on docker_container
  - `docker stop`: 3 occurrences (1 task body + 2 comment references); `state: stopped`: 0
  - block/always count: 2 (one of each)
  - zstd ensure-present: present
  - mode "0600" near s3-credentials: 1 proximity hit
  - tags [garage, restore]: present
  - inline healthy-poll: present; include_tasks: verify.yml: 0
  - D-176/GP-3/AN-3 header citations: 5 hits
  - wc -l: 278
```

## Deviations from Plan

None — both files implement exactly what the plan's `<action>` blocks specified, with the verbatim PATTERNS.md snippets adopted in the order the plan listed. The one tactical interpretation I made was in the restore.yml header docstring prose: I rephrased two adjacent-token sequences ("state: stopped" and "state: absent" as comment text) so the strict acceptance-criteria grep patterns (which intentionally do not parse YAML comments out) would not trip on commented-out warnings. The substance of the warnings is preserved verbatim — only the exact token adjacency changed. No code behavior changed.

The plan's `<action>` Task 2 step 7 called out a "DECISION POINT for executor" about how to extract the 3-entry tarball given that backup.yml's `--transform` flattens to relative paths. I resolved it per the plan's own recommended approach: three separate `tar --zstd -xpf` invocations (meta, data, s3-credentials), each with `-C` to its destination, the two volume extracts using `--strip-components=1` to drop the entry-name prefix, and the s3-credentials extract relying on the fact that `garage_s3_credentials_file = {{ garage_config_dir }}/s3-credentials` so `-C {{ garage_config_dir }}` lands the file at exactly the expected host path.

## Authentication Gates

None encountered. No package install retries needed (`ansible.builtin.package: zstd state: present` is a pre-task in both files but never executed during this plan — only authored).

## Commits

| Task | Description                                                                   | Commit    |
| ---- | ----------------------------------------------------------------------------- | --------- |
| 1    | feat(13-02): add roles/garage/tasks/backup.yml -- cold-quiesce 3-entry tarball | `2771f86` |
| 2    | feat(13-02): add roles/garage/tasks/restore.yml -- confirm-gated wipe + 3-entry untar | `a2b4ba9` |

## Known Stubs

None. Both files reference only variables that already exist (`garage_*` defaults + `backup_*` shared knobs from Wave 1 plan 13-01) and produce concrete artifacts (the tarball + the restored volume contents). No placeholder return values, no UI surfaces, no data sources stubbed out.

## Threat Flags

None new. The plan's `<threat_model>` enumerates T-13-02-01..T-13-02-09 + T-13-02-SC; every threat is either `mitigate` (and the mitigation is implemented as specified) or `accept` (and matches an existing acceptance — `become: true` for root volume access, operator footgun on `garage_backup_stop_timeout=0`). No new attack surface introduced beyond what the plan declared.

## Downstream Consumers

Plans 13-03 (prometheus), 13-04 (grafana), 13-05 (alertmanager) can now mirror this 7-task backup + 9-task restore skeleton with two differences per role:

- **Single volume instead of 3 entries**: drop the 3 `--transform` regexes and pass a single source path (`-C /var/lib/docker/volumes/<vol>/_data .`) for backup; drop `--strip-components=1` for restore extract.
- **`ansible.builtin.include_tasks: verify.yml` replaces the inline `community.docker.docker_container_info` poll** in the `always:` block — prometheus, grafana, and alertmanager all ship their own `tasks/verify.yml` already.

Plan 13-03 (prometheus) additionally needs the PP-1 `/prometheus/lock` deletion task AFTER untar BEFORE `docker start` in restore.yml (single new `ansible.builtin.file: path=.../_data/lock state=absent` task). Plan 13-05 (alertmanager) additionally needs the empty-data-dir `stat` guard at the top of backup.yml (per CONTEXT.md Claude's-Discretion item; PATTERNS.md lines 586-602 has the exact snippet).

Phase 14 orchestrators can now call:

```yaml
- ansible.builtin.include_role:
    name: garage
    tasks_from: backup
- ansible.builtin.include_role:
    name: garage
    tasks_from: restore
```

The latest-discovery glob the orchestrator uses for cross-role coordination matches the per-role glob inside restore.yml — both produce `garage-<UTC>.tar.zst` filenames sortable lexicographically.

## Self-Check: PASSED

- `roles/garage/tasks/backup.yml` — FOUND (191 lines)
- `roles/garage/tasks/restore.yml` — FOUND (278 lines)
- Commit `2771f86` — FOUND in `git log --oneline`
- Commit `a2b4ba9` — FOUND in `git log --oneline`
- `python3 yaml.safe_load` on both files — OK
- `ansible-playbook playbooks/deploy_docker.yml --syntax-check` — exit 0
