---
phase: 13-per-role-backup-restore-tasks
reviewed: 2026-06-03T08:10:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - inventory/example-homelab/group_vars/all/backup.yml
  - roles/alertmanager/defaults/main.yml
  - roles/alertmanager/tasks/backup.yml
  - roles/alertmanager/tasks/restore.yml
  - roles/garage/defaults/main.yml
  - roles/garage/tasks/backup.yml
  - roles/garage/tasks/restore.yml
  - roles/grafana/defaults/main.yml
  - roles/grafana/tasks/backup.yml
  - roles/grafana/tasks/restore.yml
  - roles/prometheus/defaults/main.yml
  - roles/prometheus/tasks/backup.yml
  - roles/prometheus/tasks/restore.yml
findings:
  critical: 2
  warning: 6
  info: 7
  total: 15
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-06-03T08:10:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 13 ships per-role `backup.yml` / `restore.yml` task files for the four stateful roles (garage, prometheus, grafana, alertmanager). The architecture is sound: cold-quiesce via `docker stop` CLI (XP-1 compliant — does not invoke `community.docker.docker_container state: stopped`), per-role `block/always` wrappers around the destructive sequence with an always-restart `docker start` (AN-2 compliant), confirm-gate (`backup_restore_confirm=true`) inside each role-task (so `include_role: tasks_from=restore` from custom playbooks is also blocked), tar `--zstd` integrity check before any wipe step, and `find -mindepth 1 -delete` wipe pattern that preserves the volume mountpoint. The four pitfalls called out in the prompt are addressed: Prometheus PP-1 lock-file deletion is present at the correct place (after untar, before `docker start`), Alertmanager AP-1 fresh-deploy `data/` guard uses the stat-then-debug pattern, Garage 3-entry tarball (meta + data + s3-credentials) is correctly constructed and symmetrically extracted.

However, the implementation has **two BLOCKER findings** that affect correctness/security in realistic operator scenarios, plus six WARNINGs and seven INFO items.

The blockers are: (1) a TOCTOU window where the Garage backup tarball is written with the default root umask (0644) and only later chmod'd to 0600 — leaking the embedded `s3-credentials` secret to any local reader for the duration of the tar+chmod gap; (2) all backup/restore tasks hardcode `/var/lib/docker/volumes/` as the host path, silently breaking on any host whose Docker daemon is configured with a non-default `data-root` — the rest of the deploy uses `community.docker.docker_volume` which respects daemon config, so the inconsistency is invisible until a custom-data-root host actually runs backup.

The warnings cluster around: operator-interrupt windows in the destructive sequence (wipe completed but untar killed → empty volume + container restarted on empty data), `Ensure zstd is installed` running BEFORE the confirm-gate (mutates system state on a no-confirm run), `set -o pipefail` absence in latest-discovery shell pipelines, and `backup_restore_from` path-traversal interpolation (an operator-controlled string interpolated into tar paths and shell-rendered cmd: scalars without validation).

The info items are stylistic (naming inconsistency, Jinja `~` vs `+` concat split across files, deviation in defaults/main.yml between the trinary-default pattern and Grafana's hardcoded `true`).

The block/always restart guarantee (AN-2) is **correctly implemented in all 8 task files** — every destructive block has an `always:` clause that runs `docker start` even on prior task failure. The XP-1 contract (use `docker stop` CLI, not `community.docker.docker_container state: stopped`) is **honored everywhere**. None of the findings below contradict those core guarantees.

## Critical Issues

### CR-01: TOCTOU race exposes secrets in backup tarball before chmod

**File:** `roles/garage/tasks/backup.yml:139-162` (also affects `roles/grafana/tasks/backup.yml:106-124`, `roles/alertmanager/tasks/backup.yml:129-145`, `roles/prometheus/tasks/backup.yml:101-119`)
**Issue:** The tar task creates the output tarball as root with the inherited umask (typically `0022`, yielding mode `0644`). The subsequent `ansible.builtin.file: mode: "0600"` step runs as a **separate Ansible task** — Ansible writes to the file system between tasks, gather facts, etc. During the gap (potentially seconds for a large Prometheus TSDB or Garage data volume), any local user on the host can read the tarball.

For Garage, the tarball embeds the `s3-credentials` plaintext secret (D-176; this is the entire reason GP-3 mandates capturing it). For Grafana, the tarball embeds `grafana.db` containing the bcrypt admin-password hash, user accounts, and API tokens (file header explicitly notes this). For Alertmanager, the tarball may carry recipient addresses (file header XP-4 commentary). For Prometheus, the tarball carries scrape config in the data labels.

The destination directory is mode `0700` so root-only enumeration is blocked, but the directory mode does NOT propagate to files inside it (Linux directory mode bits gate `chdir`/`opendir`, not `open` of an absolute path the user already knows). Any process running on the host that knows the path can `open()` the tarball during the window.

The destination directory itself is created by the same Ansible run, so the path is predictable: `/opt/telemetron/backups/<role>/<role>-<UTC>.tar.zst` with a predictable ISO 8601 timestamp.

**Fix:** Set the umask BEFORE the tar command, or render the tarball to a temp path inside the same directory then atomically `chmod` + rename. Concrete fix using process-level umask in the command:

```yaml
- name: Create Garage backup tarball (meta + data + s3-credentials -- D-176, GP-2, GP-3)
  ansible.builtin.shell:
    cmd: >-
      umask 0177 &&
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
```

`umask 0177` ensures the new file is created with mode `0600` directly. The subsequent `ansible.builtin.file` `mode: "0600"` step then becomes a no-op idempotency check rather than a race-window narrower. Apply to all four backup files.

### CR-02: Hardcoded `/var/lib/docker/volumes/` breaks on non-default Docker `data-root`

**File:** `roles/garage/tasks/backup.yml:76,134,147,148,153,184,190`, `roles/garage/tasks/restore.yml:184,190,212,223`, `roles/alertmanager/tasks/backup.yml:76,134`, `roles/alertmanager/tasks/restore.yml:153,164`, `roles/grafana/tasks/backup.yml:111`, `roles/grafana/tasks/restore.yml:161,171`, `roles/prometheus/tasks/backup.yml:106`, `roles/prometheus/tasks/restore.yml:157,165,182,191`
**Issue:** Every backup/restore task that touches the volume contents references `/var/lib/docker/volumes/{{ <role>_<type>_volume }}/_data` as the host-side path. This is the Docker daemon default, but operators routinely override `data-root` in `/etc/docker/daemon.json` (e.g. `data-root: /data/docker` on hosts with the OS on a small SSD and a separate data disk).

The rest of the Telemetron deploy code is data-root-agnostic — it uses `community.docker.docker_volume` and named-volume mounts, which the Docker daemon resolves to wherever its `data-root` lives. The backup/restore code is the **only** place in the repo that hardcodes the path. The result: on any non-default-data-root host, backup tasks will fail with "No such file or directory" (the named volume exists, but not at the hardcoded path), and restore tasks would silently wipe a non-existent path (find returns no entries → wipe is a no-op), then untar into a non-existent `-C` target → fails. The deploy succeeds, but the entire Phase 13 surface is broken — and there is no automated discovery of the actual mountpoint.

**Fix:** Resolve the host mountpoint via `community.docker.docker_volume_info` at the start of each task file and use the registered `Mountpoint` field rather than the hardcoded path. Example for garage backup:

```yaml
- name: Resolve Garage meta volume mountpoint
  community.docker.docker_volume_info:
    name: "{{ garage_meta_volume }}"
  register: garage_meta_volume_info
  tags:
    - garage
    - backup

- name: Resolve Garage data volume mountpoint
  community.docker.docker_volume_info:
    name: "{{ garage_data_volume }}"
  register: garage_data_volume_info
  tags:
    - garage
    - backup

# then reference {{ garage_meta_volume_info.volume.Mountpoint }} instead of
# /var/lib/docker/volumes/{{ garage_meta_volume }}/_data
```

Apply to all 8 task files (backup + restore for each of the 4 roles). The `Mountpoint` field is the absolute path Docker resolves to and is data-root-agnostic.

## Warnings

### WR-01: Operator interrupt between wipe and untar leaves volume empty + container restarted on empty data

**File:** `roles/garage/tasks/restore.yml:182-226`, `roles/grafana/tasks/restore.yml:159-173`, `roles/alertmanager/tasks/restore.yml:151-166`, `roles/prometheus/tasks/restore.yml:155-167`
**Issue:** The destructive sequence is:
1. `docker stop` (cold quiesce)
2. `find -mindepth 1 -delete` (wipe volume)
3. `tar --zstd -xpf` (untar)
4. `always:` → `docker start` + verify

If the operator sends SIGINT (Ctrl-C) or `ansible-playbook` is killed between step 2 (wipe completes) and step 3 (untar finishes), the `always:` clause STILL FIRES — runs `docker start` against an empty (wiped) volume. For Prometheus, this means restarting on a TSDB with no blocks: Prometheus starts cleanly, all historical data gone. For Garage, the meta volume is empty → Garage fails its bootstrap-required layout check; data volume is empty → all stored chunks lost. The always-restart guarantee (AN-2) becomes a footgun in this specific failure mode: the operator was trying to restore data and instead got "restart container on wiped volume."

The integrity check before wipe (`tar --zstd -tf`) does not help here — it guards against a corrupt tarball, not against an interrupt mid-destructive-sequence.

**Fix:** Two reasonable mitigations, pick one:

(a) Untar into a temp staging dir under the same volume mount, then atomic rename — but a single named volume can't accommodate "old + new" simultaneously for large TSDBs.

(b) Detect "wipe ran but untar didn't" in the `always:` clause and refuse to restart (override AN-2 for this specific corner case):

```yaml
always:
  - name: Check whether untar completed before restart decision
    ansible.builtin.stat:
      path: "{{ tar_completion_sentinel }}"
    register: untar_sentinel

  - name: Restart container only if untar completed (or block did not destructively fail)
    ansible.builtin.command: "docker start {{ container_name }}"
    when: untar_sentinel.stat.exists or not wipe_completed_fact | default(false)
```

Where `wipe_completed_fact` is set after the find step and `tar_completion_sentinel` is touched after a successful untar. The fact-based detection is cleaner; the sentinel file requires writing into the volume itself which is fine because that's the destination of the untar.

The simpler intermediate fix is to document this clearly in the restore task header and in the Phase 15 README: "if you Ctrl-C this play between WIPE and UNTAR steps, the container will restart on an empty volume. Re-run the restore play to recover (it is idempotent at the file level)." Telemetron has accepted similar always-restart-even-on-half-state corners in the past, but the destructive sequence is severe enough that explicit documentation matters.

### WR-02: `Ensure zstd is installed` mutates system state before confirm-gate fires

**File:** `roles/garage/tasks/restore.yml:62-69`, `roles/grafana/tasks/restore.yml:61-68`, `roles/alertmanager/tasks/restore.yml:51-58`, `roles/prometheus/tasks/restore.yml:55-62`
**Issue:** The `Ensure zstd is installed` ansible.builtin.package task runs BEFORE the `Fail unless backup_restore_confirm is set` gate in all four restore files. On a no-confirm invocation (`ansible-playbook ... restore_docker.yml` without `--extra-vars backup_restore_confirm=true`), the gate fires and the play aborts — but only after zstd has been package-installed on the target host. This is a small system mutation, but it violates the spirit of the safety contract ("a misconfigured run fails fast without touching disk" — quoting the alertmanager restore.yml line 61 header comment, which is then contradicted by line 51's pre-gate package install).

**Fix:** Move the confirm-gate task to be the **first** task in each restore.yml. The zstd install moves AFTER the gate but BEFORE latest-discovery (which doesn't need zstd) and BEFORE integrity check (which does). Concrete reordering:

```yaml
# 1. Confirm gate FIRST
- name: Fail unless backup_restore_confirm is set
  ansible.builtin.fail:
    msg: "Restore is destructive. Set --extra-vars backup_restore_confirm=true to confirm."
  when: not (backup_restore_confirm | default(false) | bool)
  tags: [...]

# 2. THEN install zstd
- name: Ensure zstd is installed for tar --zstd decompression
  ansible.builtin.package:
    name: zstd
    state: present
  become: true
  tags: [...]

# ... rest of file unchanged
```

Apply to all four restore.yml files.

### WR-03: `backup_restore_from` is unvalidated user input interpolated into shell commands

**File:** `roles/garage/tasks/restore.yml:117`, `roles/grafana/tasks/restore.yml:104`, `roles/alertmanager/tasks/restore.yml:94`, `roles/prometheus/tasks/restore.yml:99`
**Issue:** Operator-supplied `backup_restore_from` (via `--extra-vars backup_restore_from=...`) is interpolated directly into `backup_src_path`:

```yaml
backup_src_path: "{{ backup_dest_root }}/garage/garage-{{ backup_restore_from }}.tar.zst"
```

Then `backup_src_path` is passed unquoted into `tar --zstd -tf {{ backup_src_path }}` and `tar --zstd -xpf {{ backup_src_path }}` in `ansible.builtin.command:` cmd: scalars. The ansible.builtin.command module does NOT invoke a shell (so classic shell injection like `; rm -rf /` is blocked), but it does word-split on whitespace and respects path traversal.

If an operator passes `backup_restore_from="../../../etc/passwd"`, the resulting path is `/opt/telemetron/backups/garage/garage-../../../etc/passwd.tar.zst`. The integrity check fails (no such file), so destructive steps don't run — but the operator has just been given an error message that incidentally confirms the existence/non-existence of arbitrary host paths via the `tar` error. Less severe than direct command injection, but still: this is operator-controlled input flowing unvalidated into privileged tar invocations.

The operator running this play has root-via-ansible anyway, so the attack surface is "operator who can edit `--extra-vars` but is not supposed to escape backup directory." That's a real threat model when restore is wired into a CI/CD pipeline where the timestamp comes from an automated source.

**Fix:** Add a validation task after the resolve-backup-src step:

```yaml
- name: Validate backup_restore_from matches expected format
  ansible.builtin.assert:
    that:
      - backup_restore_from | default('') | regex_search('^[0-9]{8}T[0-9]{6}Z$') is not none
        or backup_restore_from | default('') == ''
    fail_msg: "backup_restore_from must be an ISO 8601 basic UTC timestamp (YYYYMMDDTHHMMSSZ), got: {{ backup_restore_from }}"
  tags: [...]
```

Apply to all four restore.yml files.

### WR-04: Latest-discovery shell pipeline lacks `set -o pipefail`

**File:** `roles/garage/tasks/restore.yml:92-95`, `roles/grafana/tasks/restore.yml:85-88`, `roles/alertmanager/tasks/restore.yml:75-78`, `roles/prometheus/tasks/restore.yml:79-82`
**Issue:** The latest-discovery uses `find ... | sort -r | head -1`. Without `set -o pipefail`, the pipeline's exit status is `head`'s — which is always 0 even if `find` fails (e.g., the backup directory doesn't exist on a fresh host that never ran backup). The empty stdout is then caught by `failed_when: ..._latest_tarball.stdout == ""`, so the task does eventually fail — but it fails with the misleading message "discovery returned empty result" rather than "backup directory doesn't exist."

More concretely: on a host where `{{ backup_dest_root }}/garage/` doesn't exist, the shell pipeline emits `find: '/opt/telemetron/backups/garage/': No such file or directory` to stderr, `find` exits 1, `sort` and `head` exit 0, the pipeline exits 0, ansible doesn't fail on stderr, then failed_when fires on empty stdout. The operator sees "stdout was empty" rather than the actual root cause in stderr.

**Fix:** Add `set -o pipefail` to the shell invocations:

```yaml
- name: Discover latest Garage backup tarball (when backup_restore_from empty)
  ansible.builtin.shell:
    cmd: >-
      set -o pipefail;
      find {{ backup_dest_root }}/garage/ -name 'garage-*.tar.zst' -type f -printf '%f\n'
      | sort -r | head -1
  args:
    executable: /bin/bash
  register: garage_latest_tarball
  changed_when: false
  failed_when: garage_latest_tarball.rc != 0 or garage_latest_tarball.stdout == ""
  when: backup_restore_from | default("") == ""
  tags: [...]
```

The `executable: /bin/bash` is required because `pipefail` is a bash-ism not in POSIX sh.

### WR-05: Garage restore extracts `s3-credentials` into `garage_config_dir` without ensuring the directory exists

**File:** `roles/garage/tasks/restore.yml:234-241`
**Issue:** The task:
```yaml
- name: Extract s3-credentials entry of Garage tarball into garage config dir
  ansible.builtin.command:
    cmd: >-
      tar --zstd -xpf {{ backup_src_path }}
      -C {{ garage_config_dir }}
      s3-credentials
```

requires `{{ garage_config_dir }}` (`/opt/telemetron/garage`) to exist. On a true bare-metal restore (replacement host, no prior deploy), this directory does not exist — Telemetron's main.yml creates it as part of the deploy. tar with `-C` fails immediately if the target directory is missing:
```
tar: /opt/telemetron/garage: Cannot chdir: No such file or directory
```

The block fails. The `always:` clause runs `docker start` against a Garage container that doesn't yet exist (or against the old container whose state is now half-restored: meta + data volumes have content from the wipe+untar but s3-credentials is missing).

The Garage backup tasks/main.yml already creates `{{ garage_config_dir }}` at mode 0755, but restore.yml does NOT depend on having run main.yml first — and the Phase 14 orchestrator may run restore against fresh hosts.

**Fix:** Lazy-create the directory before extracting s3-credentials:

```yaml
- name: Ensure Garage config directory exists for s3-credentials extract
  ansible.builtin.file:
    path: "{{ garage_config_dir }}"
    state: directory
    mode: "0755"
    owner: root
    group: root
  become: true

- name: Extract s3-credentials entry of Garage tarball into garage config dir
  ansible.builtin.command:
    cmd: >-
      tar --zstd -xpf {{ backup_src_path }}
      -C {{ garage_config_dir }}
      s3-credentials
  become: true
  changed_when: true
```

### WR-06: `become: true` missing on Grafana latest-discovery (asymmetric with other roles)

**File:** `roles/grafana/tasks/restore.yml:84-96` vs `roles/prometheus/tasks/restore.yml:78-90`, `roles/alertmanager/tasks/restore.yml:74-85`, `roles/garage/tasks/restore.yml:91-102`
**Issue:** The four restore.yml files split on `become:` for the latest-discovery `find` shell task:
- **Grafana**: `become: true` (line 93)
- **Prometheus**: `become: true` (line 87)
- **Alertmanager**: NO `become:` (line 74-85)
- **Garage**: NO `become:` (line 91-102)

The `{{ backup_dest_root }}/<role>/` directory was created at mode `0700` and owner `root` by the backup.yml task (D-XP-4 hardening). A non-root ansible user cannot `chdir` into a `0700`-root-owned directory; `find` will fail with "Permission denied" stderr and an empty stdout pipeline.

For Alertmanager and Garage, the latest-discovery silently relies on the ansible user being root (which is true if the user runs `ansible-playbook -b` or uses an inventory that defaults ansible_user=root). But for any inventory using a non-root ansible_user (the common case for SSH-keyed homelab inventories), the alertmanager and garage latest-discovery tasks will fail with permission errors.

**Fix:** Add `become: true` to the alertmanager and garage latest-discovery tasks to match the grafana and prometheus pattern. Recommend also adding to the resolve-source-path set_fact tasks for consistency (set_fact doesn't need become, but tagging the whole flow as become-true clarifies the role-task's privilege model).

## Info

### IN-01: Self-referencing default in `<role>_publish_host` works but is brittle

**File:** `roles/alertmanager/defaults/main.yml:25`, `roles/prometheus/defaults/main.yml:21`
**Issue:** `alertmanager_publish_host: "{{ alertmanager_publish_host | default(false) }}"` and similar for prometheus. This is the standard Ansible self-referencing idiom that lets inventory group_vars override the value while preserving false as the fallback. It works because Ansible recursive resolution falls back to `default()` when the variable is undefined at the current scope. However, with `--extra-vars` setting an unrelated `publish_host` (no role prefix), the self-reference still resolves to false — so the operator might get confused.

**Fix:** Optional — the pattern is correct and used elsewhere in the codebase. If consistency matters, audit other phase roles for whether they use this pattern or a flatter `prometheus_publish_host: false` default. No code change required.

### IN-02: `am_data_dir_stat` variable name diverges from `alertmanager_*` prefix convention

**File:** `roles/alertmanager/tasks/backup.yml:77,86`
**Issue:** The stat register `am_data_dir_stat` uses `am_` prefix while the rest of the file consistently uses `alertmanager_*` prefix (e.g., `alertmanager_stopped_check` on line 115, `alertmanager_latest_tarball` in restore.yml). Trivial naming inconsistency.

**Fix:** Rename to `alertmanager_data_dir_stat` for consistency.

### IN-03: Jinja string-concatenation operator inconsistent across files

**File:** `roles/grafana/tasks/restore.yml:104-106` (uses `~`), `roles/alertmanager/tasks/restore.yml:93-97` (uses `+`)
**Issue:** Both `~` and `+` work for string concatenation in Jinja, but `~` is the Jinja-idiomatic operator (auto-coerces non-strings to str), while `+` requires both operands to be strings. Telemetron's restore.yml files split: grafana uses `~`, alertmanager and prometheus use `+`. Style only — no functional difference for the strings involved here.

**Fix:** Pick one (recommend `~`) and apply across all four restore.yml files. Optional, low priority.

### IN-04: `grafana_publish_host: true` (hardcoded) diverges from trinary-default pattern

**File:** `roles/grafana/defaults/main.yml:25`
**Issue:** Alertmanager uses `alertmanager_publish_host: "{{ alertmanager_publish_host | default(false) }}"` (self-referencing trinary-friendly default). Grafana hardcodes `true`. Per D-82, this divergence is intentional (UI plane must be browser-reachable without inventory edits), but the comment doesn't explicitly note the pattern departure from the other UI-adjacent roles. Phase 13 doesn't modify this default — I'm flagging because the file was in scope.

**Fix:** None required (intentional per D-82). Optional clarifying comment: "# NOTE: deviates from alertmanager/prometheus trinary-default pattern -- D-82 inverts D-30 for UI plane."

### IN-05: Backup destination directory not created with explicit `owner`/`group` consistency

**File:** All four backup.yml — directory creation tasks
**Issue:** All four backup.yml files explicitly set `owner: root` and `group: root` on the destination directory create AND on the chmod-tarball step. This is good defensive posture but is unusual relative to the rest of the codebase (which generally leaves `owner/group` implicit when running as root via `become: true`). No bug — just an observation.

**Fix:** None required.

### IN-06: `changed_when: true` on inherently non-idempotent backup tasks

**File:** All four backup.yml — tar tasks and docker stop/start tasks
**Issue:** Backup tasks are inherently non-idempotent (a new tarball is created on every run with a new timestamp), so `changed_when: true` is semantically accurate. However, this means `--check` mode dry-runs always report "would change" on every backup task, which is technically correct but reduces the signal value of `--check`. Not a defect — backups are not idempotent by design.

**Fix:** None required.

### IN-07: Path-style header comments reference `lines 21-35` of bootstrap.yml in multiple places

**File:** `roles/garage/tasks/backup.yml:104,174`, `roles/garage/tasks/restore.yml:163,263`, `roles/grafana/tasks/backup.yml:90`, `roles/grafana/tasks/restore.yml:141`
**Issue:** Multiple header comments reference `roles/garage/tasks/bootstrap.yml lines 21-35` as the source of the verbatim-shape healthy-poll pattern. If `bootstrap.yml` is ever edited (line numbers shift), these comments become stale. Minor maintainability concern.

**Fix:** Replace line-number references with task-name references: "verbatim shape from the `Wait for Garage container HEALTHCHECK to report healthy` task in bootstrap.yml" — survives line-number drift.

---

_Reviewed: 2026-06-03T08:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
