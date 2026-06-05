# Phase 13: Per-Role Backup & Restore Tasks - Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 8 new task files + 1 new shared vars file + 4 in-place `defaults/main.yml` additions
**Analogs found:** 9 / 9 (every file has at least a structural analog; some patterns are NEW)

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `roles/garage/tasks/backup.yml` | Ansible task (backup) | file-I/O + container quiesce | `roles/garage/tasks/uninstall.yml` (header + `become:` + multi-volume), `roles/garage/tasks/bootstrap.yml` (inline `docker_container_info` poll) | role-match (no existing backup task in repo) |
| `roles/garage/tasks/restore.yml` | Ansible task (restore) | file-I/O + container quiesce + destructive | `roles/garage/tasks/uninstall.yml` (D-145 WARN shape), `roles/garage/tasks/purge.yml` (D-159 WARN + gate idiom), `roles/garage/tasks/bootstrap.yml` (inline poll) | role-match |
| `roles/prometheus/tasks/backup.yml` | Ansible task (backup) | file-I/O + container quiesce | `roles/prometheus/tasks/uninstall.yml` (per-role uninstall shape), `roles/prometheus/tasks/verify.yml` (include target) | role-match |
| `roles/prometheus/tasks/restore.yml` | Ansible task (restore) | file-I/O + container quiesce + destructive | `roles/prometheus/tasks/uninstall.yml`, `roles/garage/tasks/purge.yml` (D-159 WARN + `when:` gate) | role-match |
| `roles/grafana/tasks/backup.yml` | Ansible task (backup) | file-I/O + container quiesce | `roles/grafana/tasks/uninstall.yml`, `roles/grafana/tasks/verify.yml` (include target) | role-match |
| `roles/grafana/tasks/restore.yml` | Ansible task (restore) | file-I/O + container quiesce + destructive | `roles/grafana/tasks/uninstall.yml`, `roles/garage/tasks/purge.yml` | role-match |
| `roles/alertmanager/tasks/backup.yml` | Ansible task (backup) | file-I/O + container quiesce + stat-guard | `roles/alertmanager/tasks/uninstall.yml`, `roles/alertmanager/tasks/verify.yml` (include target) | role-match |
| `roles/alertmanager/tasks/restore.yml` | Ansible task (restore) | file-I/O + container quiesce + destructive | `roles/alertmanager/tasks/uninstall.yml`, `roles/garage/tasks/purge.yml` | role-match |
| `inventory/example-homelab/group_vars/all/backup.yml` | Ansible vars file | static config | `inventory/example-homelab/group_vars/all/network.yml`, `.../storage.yml` | exact (shared `telemetron_*` knob pattern) |
| `roles/{garage,prometheus,grafana,alertmanager}/defaults/main.yml` (in-place additions) | Ansible defaults | static config | existing role-defaults lines (e.g. `garage_health_retries: 30`) | exact |

---

## Pattern Assignments

### `roles/garage/tasks/backup.yml` (NEW; container quiesce + multi-source tar)

**Primary analog:** `roles/garage/tasks/uninstall.yml` (header shape, three-entry awareness — meta + data + s3-credentials).
**Secondary analog:** `roles/garage/tasks/bootstrap.yml` lines 17-35 (the inline `docker_container_info` healthy poll — Garage ships NO `tasks/verify.yml`).
**No analog for:** the actual stop-tar-restart `block:`/`always:` skeleton (NEW pattern in repo; cite ARCHITECTURE.md §1 and PITFALLS.md AN-2).

**Pitfall references:** GP-1 (cold-quiesce required for LMDB), GP-2 (tar full meta + data volumes), GP-3 (must include `s3-credentials`), XP-1 (use `docker stop` not `state: stopped`), XP-4 (mode 0600 tarballs), XP-5 (host `_data/` path access), AN-1 (no `state: absent`), AN-2 (`always:` restart guarantee).

#### Header comment shape — verbatim model

Copy the docstring-style header from `roles/garage/tasks/uninstall.yml` lines 1-55 (the D-145/D-146/D-147 reference structure). Replace the uninstall narrative with backup narrative. Specifically the three-bullet "what gets included" preamble:

```yaml
---
# roles/garage/tasks/backup.yml
# Cold-quiesce backup for the Garage role (D-176 single-tarball decision).
#
# Stops the Garage container (cold-quiesce per GP-1: LMDB cannot be tarred
# while Garage is writing -- see .planning/research/PITFALLS.md GP-1) and
# produces ONE tarball at:
#   {{ backup_dest_root }}/garage/garage-<UTC>.tar.zst   (mode 0600)
#
# Three top-level entries inside the tarball (D-176):
#   meta/            -> contents of {{ garage_meta_volume }} (_data dir)
#                       holds LMDB db.lmdb/ -- node id, layout, buckets,
#                       keys, ACLs. ALL Telemetron-specific identity.
#   data/            -> contents of {{ garage_data_volume }} (_data dir)
#                       holds the actual S3 object chunks (Loki, Tempo,
#                       Mimir blocks).
#   s3-credentials   -> the file at {{ garage_s3_credentials_file }}.
#                       Without this, post-restore deploy hits the D-146
#                       recovery branch (regenerates key) -- see GP-3.
#
# Container is ALWAYS restarted (block/rescue/always per AN-2) even on
# tar failure. Verify is inline because Garage has NO tasks/verify.yml
# (verification is in tasks/main.yml + tasks/bootstrap.yml).
#
# Tags: [garage, backup] -- D-133 + ARCHITECTURE.md §5 cross-cutting subtag.
```

(Mirror lines 1-55 of `roles/garage/tasks/uninstall.yml` for tone.)

#### Tag pattern (verbatim from uninstall.yml lines 66-67)

Every task in this file carries:

```yaml
  tags:
    - garage
    - backup
```

Note: `uninstall.yml` lines 66-67 show the single-tag convention (`tags: [garage]`). Backup files extend to two tags per ARCHITECTURE.md §5 (D-133 spirit — `backup` is a legitimate cross-cutting functional tag, not an operational-phase tag).

#### `zstd` ensure-present pre-task — analog: `roles/nfsd/tasks/install_debian.yml` lines 5-11

The only existing `ansible.builtin.package:` precedent in the repo (the rest of nfsd is the only place packages get installed; tar is always pre-installed). Copy the exact shape:

```yaml
- name: Install nfs-kernel-server
  ansible.builtin.package:
    name: nfs-kernel-server
    state: present
    update_cache: true
    cache_valid_time: 3600
  become: true
```

Adapt for backup tasks (drop `update_cache` for idempotency — zstd is a tiny universal package; the cache is irrelevant):

```yaml
- name: Ensure zstd is installed for tar --zstd compression
  ansible.builtin.package:
    name: zstd
    state: present
  become: true
  tags:
    - garage
    - backup
```

#### Destination-dir create — analog: `roles/garage/tasks/main.yml` lines 7-14

The deploy task creates `garage_config_dir` mode 0755 with `ansible.builtin.file: state: directory`. Backup destination uses mode 0700 (XP-4 — tarballs may contain s3-credentials secret + Prometheus metric values):

```yaml
# Pattern from roles/garage/tasks/main.yml lines 7-14 (file: state: directory):
- name: Ensure Garage config directory exists on host
  ansible.builtin.file:
    path: "{{ garage_config_dir }}"
    state: directory
    mode: "0755"
  tags:
    - garage
    - garage-config
```

Adapt for backup destination:

```yaml
- name: Ensure Garage backup destination directory exists
  ansible.builtin.file:
    path: "{{ backup_dest_root }}/garage"
    state: directory
    mode: "0700"
    owner: root
    group: root
  become: true
  tags:
    - garage
    - backup
```

#### Timestamp recording

No existing precedent; ARCHITECTURE.md + CONTEXT.md D-179 specify:

```yaml
- name: Record UTC timestamp for backup filename (D-179 ISO 8601 basic)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - garage
    - backup
```

#### Cold-quiesce stop + healthy-stopped poll — analog: `roles/garage/tasks/bootstrap.yml` lines 21-35 (INVERTED — wait for `Running == false`)

**No `docker stop` shell command exists yet in the repo** (XP-1 — this is the new contract). The polling pattern is verbatim from bootstrap.yml's "wait for healthy" shape, with two changes: `command: docker stop` precedes the poll, and the `until:` flips to `Running == false`.

Copy lines 21-35 of `roles/garage/tasks/bootstrap.yml` for the poll structure:

```yaml
- name: Wait for Garage container HEALTHCHECK to report healthy
  community.docker.docker_container_info:
    name: "{{ garage_container_name }}"
  register: garage_health_check
  until: >-
    garage_health_check.container is defined
    and garage_health_check.container.State is defined
    and garage_health_check.container.State.Health is defined
    and garage_health_check.container.State.Health.Status == 'healthy'
  retries: "{{ garage_health_retries }}"
  delay: "{{ garage_health_delay }}"
  changed_when: false
  tags:
    - garage
    - garage-bootstrap
```

Adapt for stop-quiesce. The `block:` opens here:

```yaml
- name: Cold-quiesce backup -- block wraps stop + tar (AN-2 restart guarantee)
  block:
    # XP-1: docker stop, NOT community.docker state=stopped.
    - name: Stop Garage container for cold-quiesce backup (XP-1; PITFALLS GP-1)
      ansible.builtin.command: "docker stop -t {{ garage_backup_stop_timeout }} {{ garage_container_name }}"
      changed_when: true
      become: true

    # Verbatim shape from bootstrap.yml lines 21-35, flipped to Running == false.
    - name: Wait for Garage container to reach stopped state
      community.docker.docker_container_info:
        name: "{{ garage_container_name }}"
      register: garage_stopped_check
      until: >-
        garage_stopped_check.container is defined
        and garage_stopped_check.container.State is defined
        and garage_stopped_check.container.State.Running == false
      retries: 30
      delay: 2
      changed_when: false
```

#### Tar three-entry archive — NEW pattern, no analog (cite ARCHITECTURE.md §1 + STACK.md §1)

For Garage's three-entry layout, the simplest reliable approach is `tar --zstd -cpf <dest>` with three `--transform`/`-C` invocations, OR `tar` with explicit absolute paths and renaming via `--transform`. Recommended:

```yaml
    # D-176: single tarball, three top-level entries. STACK.md §1 + §4.
    - name: Create Garage backup tarball (meta + data + s3-credentials)
      ansible.builtin.command:
        cmd: >-
          tar --zstd -cpf
          {{ backup_dest_root }}/garage/garage-{{ backup_timestamp.stdout }}.tar.zst
          --transform 's,^var/lib/docker/volumes/{{ garage_meta_volume }}/_data,meta,'
          --transform 's,^var/lib/docker/volumes/{{ garage_data_volume }}/_data,data,'
          --transform 's,^{{ garage_s3_credentials_file | regex_replace("^/", "") }}$,s3-credentials,'
          /var/lib/docker/volumes/{{ garage_meta_volume }}/_data
          /var/lib/docker/volumes/{{ garage_data_volume }}/_data
          {{ garage_s3_credentials_file }}
      become: true
      changed_when: true

    - name: Set tarball permissions (XP-4 mode 0600)
      ansible.builtin.file:
        path: "{{ backup_dest_root }}/garage/garage-{{ backup_timestamp.stdout }}.tar.zst"
        mode: "0600"
        owner: root
        group: root
      become: true
```

#### `always:` block — restart + inline verify (AN-2)

```yaml
  always:
    - name: Restart Garage container after backup (AN-2 always-restart guarantee)
      ansible.builtin.command: "docker start {{ garage_container_name }}"
      changed_when: true
      become: true

    # Garage has NO tasks/verify.yml -- inline healthy-poll per CONTEXT D-178.
    # Verbatim shape from bootstrap.yml lines 21-35.
    - name: Wait for Garage container HEALTHCHECK to report healthy post-backup
      community.docker.docker_container_info:
        name: "{{ garage_container_name }}"
      register: garage_post_backup_health
      until: >-
        garage_post_backup_health.container is defined
        and garage_post_backup_health.container.State is defined
        and garage_post_backup_health.container.State.Health is defined
        and garage_post_backup_health.container.State.Health.Status == 'healthy'
      retries: "{{ garage_health_retries }}"
      delay: "{{ garage_health_delay }}"
      changed_when: false
```

---

### `roles/garage/tasks/restore.yml` (NEW; destructive — wipe + untar)

**Primary analog:** `roles/garage/tasks/purge.yml` lines 60-72 (D-159 WARN + `when:` gate pattern).
**Secondary analog:** `roles/garage/tasks/uninstall.yml` (D-145 WARN-before-destructive shape).
**Same inline-poll requirement as `backup.yml`** (Garage lacks `verify.yml`).

**Pitfall references:** GP-1 (cold-quiesce), GP-2 (restore both volumes), GP-3 (must restore s3-credentials BEFORE container start — the whole point), XP-1 (`docker stop`), AN-1 (no `state: absent`), AN-2 (`always:` restart), AN-3 (vault token rotation breaks bootstrap if `garage_admin_token` changed between backup and restore).

#### Gate task — `backup_restore_confirm` (mirrors `telemetron_purge_data` gate)

Pattern from `roles/garage/tasks/purge.yml` line 69 (`when: telemetron_purge_data | default(false) | bool`):

```yaml
- name: Fail unless backup_restore_confirm is set
  ansible.builtin.fail:
    msg: "Restore is destructive. Set --extra-vars backup_restore_confirm=true to confirm."
  when: not (backup_restore_confirm | default(false) | bool)
  tags:
    - garage
    - restore
```

#### D-159 WARN task — verbatim shape from `purge.yml` lines 66-72

```yaml
# Original purge.yml lines 66-72:
- name: WARN -- garage purge_data is about to remove named volumes
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- garage purge_data: {{ garage_meta_volume }}, {{ garage_data_volume }}"
  when: telemetron_purge_data | default(false) | bool
  tags:
    - garage
```

Adapt for restore (D-159 WARN format from CONTEXT.md):

```yaml
- name: WARN -- garage restore will overwrite existing volume contents
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- garage restore: {{ garage_meta_volume }}, {{ garage_data_volume }}, {{ garage_s3_credentials_file }} from {{ backup_src_path }}"
  tags:
    - garage
    - restore
```

#### Latest-tarball discovery (when `backup_restore_from` empty)

No existing analog; CONTEXT.md D-179 specifies `find ... | sort -r | head -1`:

```yaml
- name: Discover latest Garage backup tarball (when backup_restore_from empty)
  ansible.builtin.shell:
    cmd: >-
      find {{ backup_dest_root }}/garage/ -name 'garage-*.tar.zst' -type f -printf '%f\n'
      | sort -r | head -1
  register: garage_latest_tarball
  changed_when: false
  failed_when: garage_latest_tarball.stdout == ""
  when: backup_restore_from | default("") == ""
  tags:
    - garage
    - restore
```

#### Integrity check (`tar tf`)

```yaml
- name: Integrity-check Garage backup tarball
  ansible.builtin.command:
    cmd: "tar --zstd -tf {{ backup_src_path }}"
  changed_when: false
  become: true
  tags:
    - garage
    - restore
```

#### Wipe pattern — `find -mindepth 1 -delete` (no precedent in repo; STACK.md §3)

```yaml
- name: Wipe existing Garage meta volume contents (PITFALLS XP-5)
  ansible.builtin.command:
    cmd: "find /var/lib/docker/volumes/{{ garage_meta_volume }}/_data -mindepth 1 -delete"
  become: true
  changed_when: true

- name: Wipe existing Garage data volume contents
  ansible.builtin.command:
    cmd: "find /var/lib/docker/volumes/{{ garage_data_volume }}/_data -mindepth 1 -delete"
  become: true
  changed_when: true

- name: Remove existing s3-credentials file before restore
  ansible.builtin.file:
    path: "{{ garage_s3_credentials_file }}"
    state: absent
  become: true
```

#### Untar + restart — same `block:`/`always:` skeleton as backup.yml

The container must be stopped before untar (mirrors backup.yml block). On `always:`, restart + inline healthy poll.

---

### `roles/prometheus/tasks/backup.yml` (NEW)

**Primary analog:** `roles/prometheus/tasks/uninstall.yml` (full file, 27 lines — the uniform per-role uninstall shape).
**Verify include target:** `roles/prometheus/tasks/verify.yml` (exists, used as-is).

**Pitfall references:** PP-1 (lock file — restore only), PP-2 (WAL gap — document only), PP-3 (queries.active — harmless), PP-4 (.tmp dirs — cold quiesce handles), XP-1, AN-1, AN-2.

#### Header — adopt the uninstall.yml docstring style (lines 1-12)

```yaml
# Original uninstall.yml lines 1-12 for reference shape:
---
# roles/prometheus/tasks/uninstall.yml
# Per-role uninstall surface for Prometheus (Phase 10 / UNDEPLOY-02).
# Named volume {{ prometheus_data_volume }} (default: telemetron_prometheus_data)
# is intentionally PRESERVED -- volume removal is Phase 11's concern (driven
# by telemetron_purge_data=true). Phase 11's playbooks/undeploy_docker.yml
# invokes this file via `include_role: { name: prometheus, tasks_from: uninstall }`
# (D-132). Inverts the deploy sequence in tasks/main.yml minus volume +
# image removal; the single `file: state=absent` on prometheus_config_dir
# is recursive by Ansible default and handles the nested rules/ subdir.
# Carries no notify: (D-142) and only the role tag (D-133).
```

Adapt:

```yaml
---
# roles/prometheus/tasks/backup.yml
# Cold-quiesce backup for Prometheus TSDB (BACKUP-V13-02).
#
# Stops the Prometheus container (cold-quiesce via `docker stop` + poll --
# NOT community.docker state: stopped per XP-1), then tars the named volume
# {{ prometheus_data_volume }} into a single zstd tarball at:
#   {{ backup_dest_root }}/prometheus/prometheus-<UTC>.tar.zst   (mode 0600)
#
# Tarball contents: full /prometheus/ tree -- WAL, chunks_head/, compacted
# blocks (ULID dirs), queries.active, lock file. The clean SIGTERM from
# docker stop flushes the WAL; the 0-2h head gap is documented (PP-2;
# Mimir's remote_write covers it). queries.active is harmless on restart
# (PP-3); .tmp dirs are absent on clean stop (PP-4).
#
# Lock file is INCLUDED in the backup but DELETED on restore (PP-1).
# Backup task does not need to delete it -- the running container holds
# the lock by PID; after `docker stop` the lock file is stale-on-disk and
# safe to tar (Prometheus 3.x replaces stale locks on startup).
#
# Block/rescue/always: container ALWAYS restarts even on tar failure (AN-2).
# Verify post-restart includes tasks/verify.yml (D-178; the same file
# tasks/main.yml uses post-deploy).
#
# Tags: [prometheus, backup] (D-133 + ARCHITECTURE.md §5).
```

#### Stop + poll + tar + restart skeleton

Same shape as Garage's `block:`/`always:`. Single source path (one named volume), single tarball:

```yaml
- name: Cold-quiesce Prometheus backup -- block (AN-2)
  block:
    - name: Stop Prometheus container for cold-quiesce backup (XP-1)
      ansible.builtin.command: "docker stop -t {{ prometheus_backup_stop_timeout }} {{ prometheus_container_name }}"
      changed_when: true
      become: true

    - name: Wait for Prometheus container to reach stopped state
      community.docker.docker_container_info:
        name: "{{ prometheus_container_name }}"
      register: prometheus_stopped_check
      until: >-
        prometheus_stopped_check.container is defined
        and prometheus_stopped_check.container.State is defined
        and prometheus_stopped_check.container.State.Running == false
      retries: 30
      delay: 2
      changed_when: false

    - name: Create Prometheus TSDB backup tarball
      ansible.builtin.command:
        cmd: >-
          tar --zstd -cpf
          {{ backup_dest_root }}/prometheus/prometheus-{{ backup_timestamp.stdout }}.tar.zst
          -C /var/lib/docker/volumes/{{ prometheus_data_volume }}/_data
          .
      become: true
      changed_when: true

    - name: Set tarball permissions
      ansible.builtin.file:
        path: "{{ backup_dest_root }}/prometheus/prometheus-{{ backup_timestamp.stdout }}.tar.zst"
        mode: "0600"
        owner: root
        group: root
      become: true

  always:
    - name: Restart Prometheus container after backup (AN-2)
      ansible.builtin.command: "docker start {{ prometheus_container_name }}"
      changed_when: true
      become: true

    # D-178: verify.yml is reused as-is.
    - name: Verify Prometheus post-backup
      ansible.builtin.include_tasks: verify.yml
  tags:
    - prometheus
    - backup
```

The `include_tasks: verify.yml` inside `always:` is the D-178 contract. `tasks/verify.yml` already exists (lines 1-152) and includes the in-network /-/ready + targets + rules assertions — no changes needed.

---

### `roles/prometheus/tasks/restore.yml` (NEW)

**Primary analog:** `roles/garage/tasks/purge.yml` (D-159 WARN + gate idiom).
**Pitfall references:** PP-1 (CRITICAL — delete `/prometheus/lock` after untar, before docker start), PP-3 (optionally delete `queries.active`), XP-1, AN-1, AN-2.

#### PP-1 lock-file deletion task — UNIQUE TO PROMETHEUS

CRITICAL: No current task in the codebase deletes the Prometheus lock file. This is a new pattern, single concrete line:

```yaml
- name: Delete Prometheus lock file after restore (PITFALLS PP-1)
  ansible.builtin.file:
    path: "/var/lib/docker/volumes/{{ prometheus_data_volume }}/_data/lock"
    state: absent
  become: true
```

Placement: AFTER untar, BEFORE the `docker start` line in `always:`. The task is unconditional and idempotent (`state: absent` is a no-op if the file doesn't exist — no `ignore_errors:` needed).

Optional PP-3 (silence the harmless "queries didn't finish" startup log noise):

```yaml
- name: Delete Prometheus queries.active after restore (PP-3, optional log noise suppression)
  ansible.builtin.file:
    path: "/var/lib/docker/volumes/{{ prometheus_data_volume }}/_data/queries.active"
    state: absent
  become: true
```

CONTEXT.md specifically calls out PP-1 as locked-in (the planner picks whether to add PP-3 — recommend YES for cleanliness).

#### Wipe + untar + lock-delete + restart skeleton

Same as Garage restore skeleton but with the PP-1 lock-file deletion injected between untar and `docker start`. Verify post-restart via `include_tasks: verify.yml`.

---

### `roles/grafana/tasks/backup.yml` (NEW)

**Primary analog:** `roles/grafana/tasks/uninstall.yml` (full file).
**Verify include target:** `roles/grafana/tasks/verify.yml` (exists; complex 268-line file with Gate 9 + Gate 9.5 — used as-is via `include_tasks`).

**Pitfall references:** GR-1 (WAL off by default; no -wal/-shm worry), GR-2 (tar entire volume — captures plugins/), GR-4 (admin password reverts — docs only), XP-1, AN-1, AN-2.

#### Header docstring

Adapt the uninstall.yml lines 1-13 shape:

```yaml
---
# roles/grafana/tasks/backup.yml
# Cold-quiesce backup for Grafana embedded SQLite (BACKUP-V13-03).
#
# Stops the Grafana container (cold-quiesce via `docker stop` + poll;
# Grafana docs require shutdown before SQLite backup -- GR-1) then tars
# the named volume {{ grafana_data_volume }} into a single zstd tarball:
#   {{ backup_dest_root }}/grafana/grafana-<UTC>.tar.zst   (mode 0600)
#
# Tarball contents: full /var/lib/grafana/ tree -- grafana.db (SQLite
# rollback-journal mode, NO -wal/-shm sidecars on clean stop), plugins/
# (operator-installed plugin binaries -- GR-2), csv/ if present, session
# state. WAL mode is OFF by default in Grafana 13.0.1 (defaults.ini
# wal=false; verified in research).
#
# Provisioning configs in {{ grafana_config_dir }}/provisioning/ are NOT
# in the volume backup -- they live in the host bind-mount and are
# re-applied by deploy_docker.yml. Restored grafana.db carries operator
# UI state only; provisioning re-overrides on next start (GR-3).
#
# Admin password caveat (GR-4): grafana.db carries the password hash from
# backup time. If GF_SECURITY_ADMIN_PASSWORD is rotated between backup
# and restore, restore reverts the in-DB hash. Re-rotate post-restore via
# grafana-cli admin reset-admin-password.
#
# Block/rescue/always: container ALWAYS restarts (AN-2). Verify via
# include_tasks: verify.yml (D-178; the same 9-step verify the deploy uses).
#
# Tags: [grafana, backup].
```

#### Skeleton

Identical to Prometheus skeleton — single volume, single tarball, `verify.yml` in `always:`.

---

### `roles/grafana/tasks/restore.yml` (NEW)

**Same skeleton as Prometheus restore minus the lock-file deletion.**
**Pitfall references:** GR-1, GR-2, GR-4 (post-restore password rotation), AN-1, AN-2, XP-1.

No special post-untar cleanup needed (no analog to Prometheus `/prometheus/lock`). The plain wipe + untar + restart + verify pattern is sufficient.

---

### `roles/alertmanager/tasks/backup.yml` (NEW)

**Primary analog:** `roles/alertmanager/tasks/uninstall.yml` (full file).
**Verify include target:** `roles/alertmanager/tasks/verify.yml` (exists; 202-line file — used as-is).

**Pitfall references:** AP-1 (protobuf files, not BoltDB), AP-2 (stale nflog re-fires — docs only), AP-3 (single-instance, no cluster state), XP-1, AN-1, AN-2.

**SPECIAL: empty `data/` directory guard** (STACK.md open question 2; CONTEXT.md Claude's-Discretion item).

#### Empty data dir stat guard — recommended default

CONTEXT.md leaves the guard pattern to planner discretion with the recommendation: `stat`-then-skip-with-debug. Recommended pattern (no existing repo analog; reads naturally as Ansible-idiomatic):

```yaml
- name: Check whether Alertmanager has any persisted state
  ansible.builtin.stat:
    path: "/var/lib/docker/volumes/{{ alertmanager_data_volume }}/_data/data"
  register: am_data_dir_stat
  become: true
  tags:
    - alertmanager
    - backup

- name: Note empty Alertmanager data directory (fresh-deploy state)
  ansible.builtin.debug:
    msg: "Alertmanager data directory does not exist yet (no silences or nflog persisted). Backup will still tar the volume (empty payload)."
  when: not (am_data_dir_stat.stat.exists and am_data_dir_stat.stat.isdir)
  tags:
    - alertmanager
    - backup
```

Then the tar step runs unconditionally — tarring an "empty" volume still produces a valid (small) tarball with whatever bookkeeping files exist at `_data/` root. Restore symmetric: untar always runs; if the tarball captured no `data/` subdir, Alertmanager will create one on first state-write.

#### Skeleton

Same shape as Grafana — single volume, single tarball, `include_tasks: verify.yml` in `always:`.

---

### `roles/alertmanager/tasks/restore.yml` (NEW)

**Same skeleton as Grafana restore.** Symmetric to backup: untar may restore an empty `data/` state — that's fine (AP-1: AM creates files when state-write happens).

---

### `inventory/example-homelab/group_vars/all/backup.yml` (NEW vars file)

**Primary analog:** `inventory/example-homelab/group_vars/all/network.yml` (lines 1-30) AND `inventory/example-homelab/group_vars/all/storage.yml` (lines 1-37).

Pattern: top-of-file comment block citing the phase + decisions, then flat `key: value` lines for each shared knob.

```yaml
# Original network.yml lines 1-20:
---
# Telemetron -- shared network knobs (Phase 1, D-04, D-12, D-14, D-15)
# Consumed by playbooks/deploy_docker.yml pre_tasks and every role's
# community.docker.docker_container task.

# Single user-defined Docker bridge network. Every component container
# attaches to this network and discovers peers by container name (DNS).
# Created by playbooks/deploy_docker.yml pre_tasks; never by any role.
telemetron_network: telemetron

# Default for every role: do NOT publish container ports to the host.
# Inter-component traffic happens over the telemetron bridge network.
# Operator access is via `ssh -L <port>:localhost:<port> <host>` or `docker exec`.
# Each role exposes its own <role>_publish_host knob to override per-service.
telemetron_publish_default: false
```

Adapt for backup vars (cite Phase 13 + D-176..D-179):

```yaml
---
# Telemetron -- shared backup knobs (Phase 13, D-176..D-179)
# Consumed by per-role tasks/backup.yml + tasks/restore.yml and by
# playbooks/backup_docker.yml + playbooks/restore_docker.yml (Phase 14).
#
# All knobs are operator-tunable. Per-role overrides live in each role's
# defaults/main.yml as <role>_backup_stop_timeout (default-from
# {{ backup_stop_timeout }}).

# Root destination for all backup tarballs. Per-role subdirs are auto-created
# by each tasks/backup.yml at mode 0700. Tarballs are written mode 0600.
# (ARCHITECTURE.md §8; PITFALLS.md XP-4)
backup_dest_root: /opt/telemetron/backups

# Seconds to wait between SIGTERM and SIGKILL when stopping a container for
# cold-quiesce backup or restore. 60s default gives Prometheus WAL flush
# and Garage LMDB clean-close ~6x the Docker default (10s). Per-role
# overrides via <role>_backup_stop_timeout in each role's defaults/main.yml.
# (D-177; PITFALLS.md GP-1, PP-1)
backup_stop_timeout: 60

# Default false: bail out on first role failure. Operator opt-in to "continue
# all 4 roles even if one fails" via --extra-vars backup_continue_on_failure=true.
# (CONTEXT.md "Carrying forward from v1.0-v1.2"; PROJECT.md locked decision)
backup_continue_on_failure: false

# Default false: restore refuses to run. Operator opt-in confirmation:
#   --extra-vars backup_restore_confirm=true
# Required at BOTH orchestrator-level (Phase 14) AND per-role tasks/restore.yml
# (so include_role: tasks_from=restore is safe from custom playbooks too).
# Mirrors v1.2.0 D-159 telemetron_purge_data=true safety contract.
backup_restore_confirm: false

# Default "" -> per-role tasks/restore.yml resolves the latest tarball
# matching <role>-*.tar.zst via `find ... | sort -r | head -1`. Lexicographic
# sort is chronological because filenames use ISO 8601 basic UTC
# (D-179: YYYYMMDDTHHMMSSZ).
# Set to a specific UTC timestamp string (e.g. 20260603T143012Z) to restore
# that exact backup across all roles.
backup_restore_from: ""
```

---

### Per-role `defaults/main.yml` additions (4 in-place edits)

**Analog:** existing one-line variable definitions in each role's defaults file (e.g. `roles/garage/defaults/main.yml` line 62 `garage_health_retries: 30`).

Pattern: add a single var per role, with a short comment block referencing D-177, defaulting from the shared `backup_stop_timeout`.

For `roles/garage/defaults/main.yml`, add (place near the existing `garage_health_retries: 30` block):

```yaml
# --- Backup stop-timeout (D-177; Phase 13) ---
# Seconds to wait between SIGTERM and SIGKILL when stopping the Garage
# container for cold-quiesce backup or restore. Defaults from the shared
# {{ backup_stop_timeout }} in inventory/<env>/group_vars/all/backup.yml.
# Override per-role for environments with very large LMDB metadata.
# (PITFALLS.md GP-1: LMDB clean-close required.)
garage_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"
```

For `roles/prometheus/defaults/main.yml`:

```yaml
# --- Backup stop-timeout (D-177; Phase 13) ---
# Override default 60s for very large TSDB (WAL flush latency).
# PITFALLS.md PP-1: SIGKILL mid-checkpoint reintroduces lock-file regression.
prometheus_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"
```

For `roles/grafana/defaults/main.yml`:

```yaml
# --- Backup stop-timeout (D-177; Phase 13) ---
# SQLite checkpoint on shutdown is fast; default 60s is generous.
grafana_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"
```

For `roles/alertmanager/defaults/main.yml`:

```yaml
# --- Backup stop-timeout (D-177; Phase 13) ---
# Final maintenance snapshot on SIGTERM is sub-second; default 60s is generous.
alertmanager_backup_stop_timeout: "{{ backup_stop_timeout | default(60) }}"
```

---

## Shared Patterns

### Pattern A — `block:` / `rescue:` / `always:` restart guarantee

**Source:** NEW PATTERN — no precedent in the current `roles/` or `playbooks/` trees (Bash grep confirms only `nfsd/tasks/exports.yml` uses `block:` and that's `blockinfile:` content, not Ansible's flow-control `block:`).

**Apply to:** All 8 new task files.

**Shape (locked in CONTEXT.md):**

```yaml
- name: Cold-quiesce backup -- block wraps stop + tar (AN-2 restart guarantee)
  block:
    - name: Stop {{ role }} container ...
    - name: Wait for stopped state ...
    - name: Create tarball ...
    - name: Set tarball permissions ...
  always:
    - name: Restart {{ role }} container (ALWAYS runs, even on tar failure)
    - name: Verify {{ role }} post-restart
      ansible.builtin.include_tasks: verify.yml   # or inline poll for Garage
  tags:
    - {{ role }}
    - backup    # or `restore`
```

No `rescue:` body beyond a single debug-WARN (the `always:` clause is the operational guarantee — `rescue:` would be redundant for the bail-out propagation; ARCHITECTURE.md §3 says orchestrator-level `ignore_errors` handles continue-on-failure).

### Pattern B — `docker stop` + `docker_container_info` poll (XP-1)

**Source:** Polling shape verbatim from `roles/garage/tasks/bootstrap.yml` lines 21-35.
**`docker stop` shell command itself:** NEW — no existing precedent.

**Apply to:** All 8 new task files. Backup wraps inside `block:`; restore wraps inside `block:` similarly.

```yaml
# XP-1 critical: NEVER community.docker.docker_container state=stopped.
# That defect (issue #791) strips volume + mount + network specs from the
# container; restart silently loses mounts.
- name: Stop {{ role_container_name }} for cold-quiesce backup
  ansible.builtin.command: "docker stop -t {{ <role>_backup_stop_timeout }} {{ <role>_container_name }}"
  changed_when: true
  become: true

# Verbatim shape from roles/garage/tasks/bootstrap.yml lines 21-35,
# inverted: until Running == false (not Health.Status == healthy).
- name: Wait for {{ role }} container to reach stopped state
  community.docker.docker_container_info:
    name: "{{ <role>_container_name }}"
  register: <role>_stopped_check
  until: >-
    <role>_stopped_check.container is defined
    and <role>_stopped_check.container.State is defined
    and <role>_stopped_check.container.State.Running == false
  retries: 30
  delay: 2
  changed_when: false
```

Restart uses `ansible.builtin.command: docker start <name>` (no native `community.docker` analog; the pattern symmetry is intentional).

### Pattern C — `zstd` ensure-present pre-task

**Source:** `roles/nfsd/tasks/install_debian.yml` lines 5-11 (the only existing `ansible.builtin.package:` precedent — minus `update_cache` for zstd's tiny universal nature).

**Apply to:** All 8 new task files (Phase 13 cannot assume zstd is pre-installed on Ubuntu 22 / Debian 12 / RHEL 9 — STACK.md §1 table).

```yaml
- name: Ensure zstd is installed for tar --zstd compression
  ansible.builtin.package:
    name: zstd
    state: present
  become: true
  tags:
    - {{ role }}
    - backup   # or `restore`
```

Place as the very first task in each backup.yml and restore.yml (idempotent — Ansible package module is a no-op when state matches).

### Pattern D — Destination-dir create (mode 0700)

**Source:** `roles/garage/tasks/main.yml` lines 7-14 (`ansible.builtin.file: state: directory`).

**Apply to:** All 4 backup.yml files (lazy idempotent per-role; D-176 destination layout).

```yaml
- name: Ensure {{ role }} backup destination directory exists
  ansible.builtin.file:
    path: "{{ backup_dest_root }}/{{ role }}"
    state: directory
    mode: "0700"
    owner: root
    group: root
  become: true
  tags:
    - {{ role }}
    - backup
```

### Pattern E — D-159 destructive WARN

**Source:** `roles/garage/tasks/purge.yml` lines 66-72 (WARN-before-destruction with the `WARNING: irreversible --` prefix).

**Apply to:** All 4 restore.yml files (NOT backup.yml — backup is non-destructive).

```yaml
# Pattern from purge.yml lines 66-72:
- name: WARN -- garage purge_data is about to remove named volumes
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- garage purge_data: {{ garage_meta_volume }}, {{ garage_data_volume }}"
  when: telemetron_purge_data | default(false) | bool
  tags:
    - garage
```

Adapt for restore (use the `restore` action verb in the WARN message per CONTEXT.md "D-159 WARN format"):

```yaml
- name: WARN -- {{ role }} restore will overwrite volume contents
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- {{ role }} restore: {{ <role>_data_volume }} from {{ backup_src_path }}"
  tags:
    - {{ role }}
    - restore
```

### Pattern F — `verify.yml` include in `always:` (D-178)

**Source:** `roles/garage/tasks/main.yml` lines 118-122 (`ansible.builtin.include_tasks: bootstrap.yml`) — verify.yml inclusion follows the same shape as bootstrap.yml inclusion.

**Apply to:** Prometheus / Grafana / Alertmanager backup + restore (6 files).

```yaml
# Same shape as roles/garage/tasks/main.yml lines 118-122:
- name: Bootstrap Garage layout, S3 key, and buckets (blocking)
  ansible.builtin.include_tasks: bootstrap.yml
  tags:
    - garage
    - garage-bootstrap
```

Adapt:

```yaml
    - name: Verify {{ role }} post-restart
      ansible.builtin.include_tasks: verify.yml
```

Placed inside the `always:` block of the backup/restore wrapper. **Do NOT carry sub-tags inside this include** — the role + action tag is on the `block:` parent.

**Garage divergence:** Garage has NO `tasks/verify.yml`. Use inline `community.docker.docker_container_info` healthy poll instead (copied verbatim from `bootstrap.yml` lines 21-35).

### Pattern G — Tarball latest-discovery + `tar tf` integrity-check

**Source:** NEW PATTERN — no precedent. Cite ARCHITECTURE.md §2 + CONTEXT.md D-179.

Lexicographic sort is chronological because filenames are ISO 8601 basic UTC (`YYYYMMDDTHHMMSSZ`).

```yaml
- name: Discover latest {{ role }} backup tarball
  ansible.builtin.shell:
    cmd: >-
      find {{ backup_dest_root }}/{{ role }}/ -name '{{ role }}-*.tar.zst' -type f -printf '%f\n'
      | sort -r | head -1
  register: <role>_latest_tarball
  changed_when: false
  failed_when: <role>_latest_tarball.stdout == ""
  when: backup_restore_from | default("") == ""

- name: Integrity-check {{ role }} backup tarball
  ansible.builtin.command:
    cmd: "tar --zstd -tf {{ backup_src_path }}"
  changed_when: false
  become: true
```

### Pattern H — Wipe `_data/` contents in-place (STACK.md §3)

**Source:** NEW PATTERN — no precedent. The closest existing wipe-style operation is `purge.yml`'s `community.docker.docker_volume: state: absent`, which is the WRONG approach (STACK.md §3 explicitly rejects `state: absent` for restore — recreating the volume changes its ID and may break Docker's mount table).

```yaml
- name: Wipe existing {{ role }} volume contents
  ansible.builtin.command:
    cmd: "find /var/lib/docker/volumes/{{ <role>_data_volume }}/_data -mindepth 1 -delete"
  become: true
  changed_when: true
```

### Pattern I — `backup_restore_confirm` hard-gate

**Source:** `roles/garage/tasks/purge.yml` line 69 (`when: telemetron_purge_data | default(false) | bool`) — the gate idiom for irreversible operations.

**Apply to:** All 4 restore.yml files (the gate must fire in the role-task itself, NOT just the orchestrator — per CONTEXT.md "Carrying forward").

```yaml
- name: Fail unless backup_restore_confirm is set
  ansible.builtin.fail:
    msg: "Restore is destructive. Set --extra-vars backup_restore_confirm=true to confirm."
  when: not (backup_restore_confirm | default(false) | bool)
  tags:
    - {{ role }}
    - restore
```

Placed BEFORE the D-159 WARN (gate first, then warn what's about to happen, then the actual destruction).

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File / Pattern | Reason | Planner Reference |
|----------------|--------|-------------------|
| `block:` / `rescue:` / `always:` flow control | No precedent in repo (grep confirms only `blockinfile:` content blocks exist) | ARCHITECTURE.md §1; PITFALLS.md AN-2 |
| `ansible.builtin.command: docker stop` shell-out | First Telemetron use case for stop-then-restart (uninstall uses `state: absent`, never `docker stop`) | PITFALLS.md XP-1 |
| `tar --zstd -cpf` invocation | No prior tar usage; community.general.archive explicitly excluded | STACK.md §1 |
| `find -mindepth 1 -delete` wipe | No restore precedent; closest is purge.yml's `docker_volume state=absent` (wrong for restore — see STACK.md §3) | STACK.md §3 |
| `tar --transform` with three-source single-tarball | Garage-specific D-176; no analog | ARCHITECTURE.md §1 + STACK.md §4 |
| `find \| sort -r \| head -1` lexicographic-latest discovery | No prior latest-tarball pattern | CONTEXT.md D-179 |
| `tar tf` integrity check before restore | No prior content-list precedent | ARCHITECTURE.md §2 |
| `ansible.builtin.fail` with `when: not (var \| default(false) \| bool)` gate | Same idiom as `purge.yml`'s `when:` gates but using `fail:` instead of skipping — first use in role tasks | ARCHITECTURE.md §2 |

---

## Cross-File Pitfall Checklist (for planner / executor verification)

| Pitfall | Role File(s) Affected | Concrete Line to Add |
|---------|----------------------|----------------------|
| GP-1 (LMDB cold-copy) | garage/{backup,restore} | `docker stop` + `Running == false` poll BEFORE any tar/untar |
| GP-2 (full meta + data tar) | garage/backup | `--transform` of BOTH volumes in single `tar` invocation |
| GP-3 (s3-credentials in tarball) | garage/{backup,restore} | Include `{{ garage_s3_credentials_file }}` as third source; restore writes back before `docker start` |
| GP-4 (key list regex) | garage/{backup,restore} | Phase 13 does NOT parse `garage key list`. If a future plan adds it, copy regex verbatim from `bootstrap.yml` line 185 (`'(?m)^(\\S+)\\s+\\S+\\s+' ~ garage_s3_key_name ~ '(?:\\s|$)'`) |
| PP-1 (lock file) | prometheus/restore | `ansible.builtin.file: path=.../_data/lock state=absent` AFTER untar, BEFORE `docker start` |
| PP-3 (queries.active) | prometheus/restore | Optional `state: absent` on `queries.active` AFTER untar (log noise suppression) |
| GR-1 (no -wal/-shm) | grafana/backup | No action needed; default Grafana 13 ships `wal=false`. Document in header. |
| GR-2 (tar full volume incl. plugins/) | grafana/backup | Tar `_data/` root recursively (not just `grafana.db`) |
| AP-1 (protobuf state) | alertmanager/backup | Tar `_data/` root recursively (`data/nflog`, `data/silences` if present) |
| AP-3 (no cluster state) | alertmanager/{backup,restore} | No special handling; document `--cluster.listen-address=""` in header |
| XP-1 (docker stop not state: stopped) | ALL 8 files | Use `ansible.builtin.command: docker stop` + poll — never `community.docker.docker_container state: stopped` |
| XP-4 (perms 0700/0600) | ALL 4 backup files | `file: mode: "0700"` for dir; `file: mode: "0600"` for tarball after creation |
| XP-5 (host `_data/` path) | ALL 8 files | Direct `/var/lib/docker/volumes/<vol>/_data` access; `become: true` required |
| XP-6 (symlinks) | ALL 4 backup files | Use plain `tar`, no `--dereference` flag |
| AN-1 (no state: absent) | ALL 8 files | Code review: grep each file for `state: absent` on `community.docker.docker_container` -- should match ZERO times |
| AN-2 (always restart) | ALL 8 files | `always:` clause with `docker start` is mandatory |
| AN-3 (vault token rotation) | garage/restore + Phase 15 docs | Document in restore.yml header; no code change |

---

## Metadata

**Analog search scope:**
- `roles/**/tasks/*.yml` (12 roles, ~40 task files scanned)
- `inventory/example-homelab/group_vars/all/*.yml` (15 vars files scanned)
- `playbooks/*.yml` (3 playbooks scanned — `deploy_docker.yml`, `undeploy_docker.yml`, `smoke_test.yml`)
- Grep for `block:` / `rescue:` / `always:` / `docker stop` / `command:.*tar` (all returned empty for Ansible flow-control / direct shell-out patterns)

**Files scanned:** ~60

**Strongest analogs (5 high-value):**
1. `roles/garage/tasks/uninstall.yml` — D-145/D-146/D-147 header narrative + 4-task structural shape
2. `roles/garage/tasks/purge.yml` — D-159 WARN + `when:` gate idiom
3. `roles/garage/tasks/bootstrap.yml` lines 21-35 — `docker_container_info` healthy-poll (and the GP-4 regex on line 185)
4. `roles/{prometheus,grafana,alertmanager}/tasks/verify.yml` — verbatim-included by 6 of 8 new files
5. `inventory/example-homelab/group_vars/all/network.yml` — shared-vars file shape

**Pattern extraction date:** 2026-06-03
