---
phase: 10-per-role-uninstall-surface
plan: 05
subsystem: nfsd-uninstall
tags:
  - nfsd
  - uninstall
  - host-package
  - blockinfile
  - exportfs
dependency_graph:
  requires:
    - roles/nfsd/tasks/exports.yml  # source of blockinfile marker (must be byte-identical)
    - roles/nfsd/tasks/main.yml     # install-side counterpart
    - roles/nfsd/handlers/main.yml  # template for exportfs -ra invocation
  provides:
    - roles/nfsd/tasks/uninstall.yml  # Phase 11 orchestrator entrypoint via include_role tasks_from
  affects:
    - playbooks/undeploy_docker.yml  # Phase 11 will include this with `when: enable_nfsd | default(false) | bool` (D-140)
tech_stack:
  added: []
  patterns:
    - blockinfile-state-absent-with-byte-identical-marker
    - inline-exportfs-instead-of-handler-notify
    - gate-at-orchestrator-not-in-role-task
key_files:
  created:
    - roles/nfsd/tasks/uninstall.yml
  modified: []
decisions:
  - D-136: OS packages (nfs-kernel-server / nfs-utils) intentionally NOT removed
  - D-137: blockinfile marker is byte-identical to exports.yml install side
  - D-138: nfsd_share_root and per-remote-host subdirs intentionally NOT removed
  - D-139: nfs-server.service intentionally NOT stopped; exportfs -ra runs inline
  - D-140: enable_nfsd gate stays at Phase 11 orchestrator level, NOT inside uninstall.yml
  - D-141: blockinfile state=absent is idempotent no-op when marker missing
  - D-142: uninstall does NOT notify handlers (runs exportfs -ra inline instead)
metrics:
  duration: ~6 min
  tasks_completed: 1
  files_changed: 1
  commits: 1
  completed: 2026-05-29
---

# Phase 10 Plan 05: nfsd Per-Role Uninstall Surface Summary

## One-liner

Adds `roles/nfsd/tasks/uninstall.yml` — the only host-package uninstall in the M1 set — which removes the Telemetron-managed `/etc/exports` block via `blockinfile state=absent` (byte-identical marker to `exports.yml`) and re-exports via inline `exportfs -ra`, while intentionally preserving OS packages (D-136), the NFS service (D-139), and the share root (D-138).

## What Shipped

| Artifact | Description |
|----------|-------------|
| `roles/nfsd/tasks/uninstall.yml` | 2-task uninstall surface: blockinfile state=absent + `exportfs -ra` |

### Tasks 

| # | Module | Purpose |
|---|--------|---------|
| 1 | `ansible.builtin.blockinfile` (`state: absent`) | Removes the Telemetron-managed `/etc/exports` block using the byte-identical marker `"# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK"` from `roles/nfsd/tasks/exports.yml:10` (D-137) |
| 2 | `ansible.builtin.command` (`cmd: exportfs -ra`, `changed_when: false`) | Re-reads `/etc/exports` in the kernel so the just-removed exports stop being served (D-139, mirrors the `reload nfsd exports` handler's command) |

Both tasks `become: true`, tagged `[nfsd]` only — no `nfsd-uninstall` sub-tag (D-133).

## Byte-Identical Marker Verification

The install-side marker from `roles/nfsd/tasks/exports.yml:10`:

```
"# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK"
```

The uninstall-side marker from `roles/nfsd/tasks/uninstall.yml`:

```
"# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK"
```

Confirmed identical via:

```bash
diff \
  <(grep -E '^\s+marker:' roles/nfsd/tasks/exports.yml | head -1 | sed -E 's/^\s+//') \
  <(grep -E '^\s+marker:' roles/nfsd/tasks/uninstall.yml | head -1 | sed -E 's/^\s+//')
# (exit 0, no diff)
```

This guarantees `state: absent` actually matches the block written at install time — a one-byte drift would silently leave the export block in place AND append an orphan empty marker pair.

## D-136..D-140 Non-Removals (Enumerated)

The nfsd uninstall is conservative-by-default because nfsd is the only host-package role and may have been in use before Telemetron was deployed. The file intentionally does NOT do any of the following:

| Decision | What stays | Why |
|---|---|---|
| **D-136** | OS packages `nfs-kernel-server` (Debian) and `nfs-utils` (RedHat) | Operator may have had NFS running before deploying Telemetron; auto-purge would break unrelated workloads. The forbidden-constructs grep blocks `ansible.builtin.package`, `community.general.package`, `apt:`, `dnf:`, `yum:`. |
| **D-138** | `nfsd_share_root` (default `/srv/telemetron-nfs`) and per-remote-host subdirs (`nfsd_exports[*].path`) | These directories may hold log files arrived via NFS from external hosts — operator data, not role-private state. The forbidden-constructs grep blocks `nfsd_share_root` and `/srv/telemetron-nfs` in non-comment lines. |
| **D-139** | `nfs-server.service` running and enabled | Same as D-136 — the operator may have had it pre-existing. If Telemetron was the sole driver, the operator stops it manually. The forbidden-constructs grep blocks `ansible.builtin.service`. |
| **D-142** | No `notify:` on handlers | Uninstall paths do not trigger handlers; `exportfs -ra` runs as an inline task instead. The forbidden-constructs grep blocks `notify:`. |
| **D-133** | No `nfsd-uninstall` sub-tag | Primary role tag only — play context (deploy_docker vs undeploy_docker) disambiguates intent. |

## Gate Stays at Orchestrator Level (D-140)

The `when: enable_nfsd | default(false) | bool` clause is NOT inside `roles/nfsd/tasks/uninstall.yml`. This is symmetric with how the deploy-side gate lives in `playbooks/deploy_docker.yml` (line 72 region — `- role: nfsd ... when: enable_nfsd | default(false) | bool`), not inside `roles/nfsd/tasks/main.yml`.

Phase 11's `playbooks/undeploy_docker.yml` will wire this gate by wrapping the include like:

```yaml
- include_role:
    name: nfsd
    tasks_from: uninstall
  when: enable_nfsd | default(false) | bool
  tags: [nfsd]
```

The forbidden-constructs grep blocks `when:.*enable_nfsd` in this file to enforce the placement.

## Verification Results

All acceptance criteria pass:

- File `roles/nfsd/tasks/uninstall.yml` exists (51 lines).
- YAML parses cleanly (verified via `python3 -c "yaml.safe_load(...)"`).
- Exactly 2 tasks in correct order: `ansible.builtin.blockinfile` then `ansible.builtin.command`.
- Task 1: `state: absent`, `become: true`, `path: /etc/exports`, byte-identical marker, no `when:`, no `notify:`, `tags: [nfsd]`.
- Task 2: `cmd: exportfs -ra`, `changed_when: false`, `become: true`, `tags: [nfsd]`.
- Forbidden constructs grep PASS — none of `ansible.builtin.package`, `ansible.builtin.service`, `community.general.package`, `apt:`, `dnf:`, `yum:`, `nfsd_share_root`, `/srv/telemetron-nfs`, `when:.*enable_nfsd`, `notify:`, `nfsd-uninstall`, `flush_handlers` appears in any non-comment line.
- `ansible-playbook --syntax-check -i inventory/example-homelab/hosts.yml playbooks/deploy_docker.yml` still passes (existing deploy playbook unaffected).

## Deviations from Plan

None — plan executed exactly as written.

## Authentication Gates

None — pure file authoring against `roles/nfsd/`; no remote / credentialed operations involved.

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `d08dd16` | `feat(10-05): add nfsd uninstall surface (UNDEPLOY-02)` | `roles/nfsd/tasks/uninstall.yml` (+51) |

## Threat-Model Disposition

All six STRIDE rows from the plan's `<threat_model>` resolve to `mitigate` and are satisfied by acceptance-criteria checks already executed:

| Threat ID | Mitigation realised |
|---|---|
| T-10-NF-01 (orphan exports leak from marker drift) | Marker diff between exports.yml and uninstall.yml is empty — identical by byte. |
| T-10-NF-02 (DoS via OS-package removal) | `package` / `apt:` / `dnf:` / `yum:` / `community.general.package` grep PASS (absent). |
| T-10-NF-03 (DoS via service stop) | `ansible.builtin.service` grep PASS (absent). |
| T-10-NF-04 (operator log-file data loss) | `nfsd_share_root` / `/srv/telemetron-nfs` grep PASS (absent in non-comment lines). |
| T-10-NF-05 (gate-placement inconsistency) | `when:.*enable_nfsd` grep PASS (absent). |
| T-10-NF-06 (handler race) | `notify:` grep PASS (absent); `exportfs -ra` runs inline. |

No new threat flags surfaced — the uninstall surface is strictly narrower than the install surface it inverts.

## Self-Check: PASSED

- FOUND: `roles/nfsd/tasks/uninstall.yml` (file exists, 51 lines, contains literal marker string)
- FOUND: commit `d08dd16` in `git log --oneline` (`feat(10-05): add nfsd uninstall surface (UNDEPLOY-02)`)
- FOUND: byte-identical marker between `roles/nfsd/tasks/exports.yml:10` and `roles/nfsd/tasks/uninstall.yml` (diff returns no output)
- FOUND: existing `playbooks/deploy_docker.yml` still syntax-checks clean (no regressions)
