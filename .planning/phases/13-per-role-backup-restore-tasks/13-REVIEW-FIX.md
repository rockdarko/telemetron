---
phase: 13-per-role-backup-restore-tasks
fixed_at: 2026-06-03T08:45:00Z
review_path: .planning/phases/13-per-role-backup-restore-tasks/13-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-06-03T08:45:00Z
**Source review:** .planning/phases/13-per-role-backup-restore-tasks/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (2 Critical + 6 Warning)
- Fixed: 8
- Skipped: 0

All Critical and Warning findings from REVIEW.md were applied. Info findings (IN-01..07) were out of scope (`fix_scope: critical_warning`) and intentionally not addressed.

Each fix was YAML-validated via `python3 -c "import yaml; yaml.safe_load(...)"` against every modified task file, and the final tree passed `ansible-playbook --syntax-check -i inventory/example-homelab/hosts.yml playbooks/deploy_docker.yml` (note: per `--syntax-check` does NOT recurse into role task files; YAML structural validation was the primary gate).

## Fixed Issues

### CR-01: TOCTOU race exposes secrets in backup tarball before chmod

**Files modified:** `roles/garage/tasks/backup.yml`, `roles/grafana/tasks/backup.yml`, `roles/alertmanager/tasks/backup.yml`, `roles/prometheus/tasks/backup.yml`
**Commit:** b514968
**Applied fix:** Switched tar invocation from `ansible.builtin.command` to `ansible.builtin.shell` with `umask 0177 && tar --zstd -cpf ...`. The new file is now created at mode 0600 directly, closing the window where the tarball was world-readable as 0644 between tar and the follow-up `ansible.builtin.file mode: "0600"` step. The subsequent file-mode task is retained as an idempotency guard.

### CR-02: Hardcoded `/var/lib/docker/volumes/` breaks on non-default Docker `data-root`

**Files modified:** `roles/garage/tasks/backup.yml`, `roles/garage/tasks/restore.yml`, `roles/grafana/tasks/backup.yml`, `roles/grafana/tasks/restore.yml`, `roles/alertmanager/tasks/backup.yml`, `roles/alertmanager/tasks/restore.yml`, `roles/prometheus/tasks/backup.yml`, `roles/prometheus/tasks/restore.yml`
**Commit:** 24235f6
**Applied fix:** Added `community.docker.docker_volume_info` resolve tasks at the start of each backup task file and after the source-path resolution in each restore task file. Replaced every hardcoded `/var/lib/docker/volumes/{{ <vol> }}/_data` reference with `{{ <vol>_info.volume.Mountpoint }}` across wipe `find`, tar `-C`, tar source paths, tar `--transform` regexes (with leading-slash stripped), and post-untar cleanup paths. The backup/restore surface is now consistent with the rest of the deploy code, which is already daemon-data-root-agnostic via `community.docker.docker_volume`.

### WR-01: Operator interrupt between wipe and untar leaves volume empty + container restarted on empty data

**Files modified:** `roles/garage/tasks/restore.yml`, `roles/grafana/tasks/restore.yml`, `roles/alertmanager/tasks/restore.yml`, `roles/prometheus/tasks/restore.yml`
**Commit:** 6020900
**Applied fix:** Per the review's simpler-intermediate-fix guidance, added a "WR-01 (operator-interrupt window -- documented corner case)" block to each restore.yml header describing the failure mode (per-role specifics: empty TSDB, lost silences, fresh-seeded grafana.db, broken Garage bootstrap), naming the AN-2 always-restart guarantee as the specific footgun, and pointing operators at the recovery path (re-run the restore play -- idempotent at the file level). Phase 15 will mirror this in the per-role READMEs.

**Logic-bug note:** The fix is documentation-only. The runtime behavior (sentinel/fact-based detection in `always:`) was the more complex alternative the review explicitly offered; the review's text "simpler intermediate fix is to document this clearly" is what was applied.

### WR-02: `Ensure zstd is installed` mutates system state before confirm-gate fires

**Files modified:** `roles/garage/tasks/restore.yml`, `roles/grafana/tasks/restore.yml`, `roles/alertmanager/tasks/restore.yml`, `roles/prometheus/tasks/restore.yml`
**Commit:** 6be9dd5
**Applied fix:** Reordered tasks so the confirm-gate (`Fail unless backup_restore_confirm is set`) is the FIRST task in each restore.yml file. The zstd install moves to second position -- still before latest-discovery and integrity check, both of which need zstd. A no-confirm invocation now fails before any system mutation. Added a WR-02 comment to each gate task explaining the ordering rationale.

### WR-03: `backup_restore_from` is unvalidated user input interpolated into shell commands

**Files modified:** `roles/garage/tasks/restore.yml`, `roles/grafana/tasks/restore.yml`, `roles/alertmanager/tasks/restore.yml`, `roles/prometheus/tasks/restore.yml`
**Commit:** 70f49b3
**Applied fix:** Added an `ansible.builtin.assert` task right after the confirm-gate in each restore.yml, validating that `backup_restore_from` matches `^[0-9]{8}T[0-9]{6}Z$` (ISO 8601 basic UTC -- the format `backup.yml` emits per D-179). Empty values are still allowed (latest-discovery path). The assertion fires before any tar interpolation or source-path resolution, so path-traversal payloads like `../../../etc/passwd` are rejected before they can reach a privileged tar invocation.

### WR-04: Latest-discovery shell pipeline lacks `set -o pipefail`

**Files modified:** `roles/garage/tasks/restore.yml`, `roles/grafana/tasks/restore.yml`, `roles/alertmanager/tasks/restore.yml`, `roles/prometheus/tasks/restore.yml`
**Commit:** 9f840e5
**Applied fix:** Added `set -o pipefail;` to each latest-discovery shell `cmd:` and `executable: /bin/bash` to `args:` (pipefail is a bash-ism not in POSIX sh). Also expanded `failed_when:` to include `rc != 0` so a non-empty stdout with a non-zero rc is still caught. Operators now see find's actual stderr on missing-directory errors rather than the misleading "stdout was empty".

### WR-05: Garage restore extracts `s3-credentials` into `garage_config_dir` without ensuring the directory exists

**Files modified:** `roles/garage/tasks/restore.yml`
**Commit:** 9626a39
**Applied fix:** Added an `ansible.builtin.file: state: directory` task immediately before the s3-credentials extract step in the restore block, lazy-creating `garage_config_dir` (mode 0755, owner+group root) to mirror the shape `main.yml` uses during deploy. The task is idempotent; on a host where deploy already created the directory, it's a no-op. On a true bare-metal restore-to-fresh-host scenario, tar with `-C` now finds a valid target directory rather than failing the block and leaving Garage in a half-restored state.

### WR-06: `become: true` missing on Grafana latest-discovery (asymmetric with other roles)

**Files modified:** `roles/alertmanager/tasks/restore.yml`, `roles/garage/tasks/restore.yml`
**Commit:** e47ce09
**Applied fix:** Added `become: true` to the latest-discovery `find` shell tasks in alertmanager and garage restore.yml files. (Note: REVIEW.md's title says "Grafana" but the body correctly identifies alertmanager and garage as the missing-become files -- grafana and prometheus already had become: true.) All four roles now use the same privilege model for the discovery shell step, which is required because `backup_dest_root/<role>/` is mode 0700 + owner root and a non-root ansible user cannot chdir into it.

---

_Fixed: 2026-06-03T08:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
