---
phase: 11-undeploy-orchestrator-safety-idempotency
plan: 04
subsystem: ansible-playbook
tags: [undeploy, orchestrator, safety, idempotency, purge-flags, reverse-deploy]
requires:
  - playbooks/deploy_docker.yml (literal inverse — D-149)
  - inventory/example-homelab/group_vars/all/network.yml (telemetron_network)
  - inventory/example-homelab/group_vars/all/storage.yml (telemetron_config_root)
  - 12 per-role tasks/uninstall.yml (Phase 10 — 11-01, 10-XX)
  - 11 per-role tasks/purge.yml (Phase 11 wave 1 — 11-01, 11-02, 11-03)
provides:
  - playbooks/undeploy_docker.yml (M1 undeploy orchestrator; user-facing)
  - Reverse-deploy traversal: nfsd -> karma -> grafana -> alertmanager -> fluentbit -> prometheus -> opentelemetry -> node_exporter -> mimir -> tempo -> loki -> garage
  - 3 opt-in irreversible purge flags (telemetron_purge_data, telemetron_purge_host_dirs, telemetron_purge_images)
  - D-160 PLAY-start category banner; D-159 grep-friendly per-action WARN lines
affects:
  - UNDEPLOY-01 (operator undeploy entry point)
  - PURGE-01 (default conservative — volumes preserved)
  - PURGE-02 (3-flag opt-in irreversible purge surface)
  - OPS-01 (back-to-back undeploy idempotency)
  - OPS-02 (redeploy after undeploy round-trip)
tech-stack:
  added: []
  patterns:
    - ansible.builtin.include_role + tasks_from (D-132 pattern)
    - YAML folded scalar (>-) for multi-line OR-gated when:
    - Single role tag (D-133) — no <role>-uninstall sub-tag
    - state: absent idempotency trust (D-141) — no precondition *_info lookups
    - separately-named debug WARN BEFORE destructive task (D-145)
key-files:
  created:
    - playbooks/undeploy_docker.yml
  modified: []
decisions:
  - D-149 reverse-deploy order is HARDCODED in tasks: block (not loop:) so --tags <role> scoping works
  - D-150 telemetron Docker bridge network removal lives in post_tasks (mirrors deploy pre_tasks)
  - D-153 all 3 purge flags default to false in vars: block (single discovery point)
  - D-155 host_dirs purge is parent-only at orchestrator post_tasks (per-role purge.yml has NO host_dirs section)
  - D-156 nfsd has uninstall-only (NO purge.yml); orchestrator does NOT include_role tasks_from: purge for nfsd
  - D-157 + D-160 PLAY-start banner with category descriptions (not counts/names) — stable across role additions
  - D-158 no ansible.builtin.pause — typing --extra-vars is the confirmation; scripted teardowns must work without TTY
  - D-159 single-line grep-friendly WARN prefix `WARNING: irreversible -- ...`
  - Folded-scalar OR-gate on purge includes: `telemetron_purge_data | bool or telemetron_purge_images | bool`
  - failed_when:false safety (D-154) lives in per-role purge.yml, NOT orchestrator
metrics:
  duration_min: 3
  tasks: 3
  files: 1
  lines_added: 301
  completed_date: "2026-05-30"
---

# Phase 11 Plan 04: Undeploy Orchestrator Summary

**One-liner:** Wired the M1 undeploy orchestrator `playbooks/undeploy_docker.yml` — a reverse-deploy traversal of the 12 stack roles with a 3-flag opt-in purge surface, PLAY-start safety banner, and post-task network + host_dirs parent removal.

## What Was Built

`playbooks/undeploy_docker.yml` (301 lines, 1 new file at repo root, same level as `deploy_docker.yml`):

1. **Header comment block** citing D-149/D-150/D-151/D-153/D-154/D-155/D-156/D-157/D-159/D-160 + `--extra-vars` examples for each of the 3 purge flags + per-role `--tags <role>` re-run pattern + `--ask-vault-pass` UX parity with deploy.

2. **Play frame** mirroring `deploy_docker.yml` verbatim (`hosts: telemetron`, `gather_facts: true`, `become: false`, `collections: community.docker`) so the same inventory invocation works.

3. **`vars:` block** — D-153 single discovery point declaring all 3 purge flags = `false`:
   - `telemetron_purge_data: false`
   - `telemetron_purge_host_dirs: false`
   - `telemetron_purge_images: false`

4. **`pre_tasks:`** — D-160 PLAY-start banner: a single `ansible.builtin.debug` task with `msg: |` block scalar listing each flag's current value plus a category description (preserved when false, destroyed when true). Tagged `always` so the banner displays even under `--tags <role>` targeted runs (Pattern 8).

5. **`tasks:`** — D-149 reverse-deploy traversal. 23 total `ansible.builtin.include_role` tasks in literal inverse of `deploy_docker.yml`'s roles: block:
   - **nfsd** (FIRST — was last in deploy): single `tasks_from: uninstall` include, gated by `when: enable_nfsd | default(false) | bool` (D-156 symmetric with deploy line 72). NO purge include for nfsd (D-156).
   - **11 uninstall+purge pairs** for karma → garage: `tasks_from: uninstall` (unconditional, tagged single role), then `tasks_from: purge` (OR-gated on `telemetron_purge_data | bool or telemetron_purge_images | bool` via YAML folded scalar). Per-role purge.yml internally gates each section on its specific flag (D-153 belt-and-suspenders).

6. **`post_tasks:`** — 3 final teardown tasks:
   - **Task A**: `community.docker.docker_network: state=absent` on `{{ telemetron_network }}`, tagged `[always, network]`. Inverts deploy's pre_tasks network-create (D-150). Unconditional — state=absent on missing network is a no-op (D-141).
   - **Task B**: D-145 + D-159 WARN debug emitting grep-friendly `"WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)"`. Gated on `telemetron_purge_host_dirs`.
   - **Task C**: `ansible.builtin.file: state=absent` on `{{ telemetron_config_root | default('/opt/telemetron') }}` (inventory-tunable, NOT hardcoded). Gated on `telemetron_purge_host_dirs`. D-155 parent-only — Phase 10 uninstall.yml already removes each role's `/opt/telemetron/<role>/` subdir under conservative undeploy.

## How It Works

Operator UX after this plan ships:

```bash
# Conservative (default): containers + bridge network + role-private subdirs removed.
# Named volumes, /opt/telemetron parent, and images PRESERVED.
ansible-playbook -i inventory/example-homelab playbooks/undeploy_docker.yml --ask-vault-pass

# Per-role targeted re-run (D-151 tag-scoped — single role tag per task means
# --tags garage runs ONLY the 2 garage include_role calls + post_tasks/always):
ansible-playbook -i inventory/example-homelab playbooks/undeploy_docker.yml --tags garage

# Irreversible purge — remove all named volumes (telemetron_*):
ansible-playbook -i inventory/example-homelab playbooks/undeploy_docker.yml \
    --extra-vars "telemetron_purge_data=true"

# All 3 flags = scorched-earth (rebuild from scratch on next deploy):
ansible-playbook -i inventory/example-homelab playbooks/undeploy_docker.yml \
    --extra-vars "telemetron_purge_data=true \
                  telemetron_purge_host_dirs=true \
                  telemetron_purge_images=true"
```

The PLAY-start banner displays first (always tag), then teardown proceeds top-down through the tasks: block in reverse-deploy order, then post_tasks: removes network + (optionally) the `/opt/telemetron/` parent tree.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `playbooks/undeploy_docker.yml` | 301 | M1 undeploy orchestrator — user-facing single entry point. Inverse of `deploy_docker.yml`. |

## Verification

`ansible-playbook playbooks/undeploy_docker.yml --syntax-check` → `playbook: playbooks/undeploy_docker.yml` (parses cleanly).

`ansible-playbook playbooks/undeploy_docker.yml --list-tasks` → confirms full 26-task linear program in expected order:
1. WARN -- irreversible purge flags status [always]
2. Invoke nfsd uninstall [nfsd]
3-24. 11 uninstall+purge pairs (karma → garage)
25. Remove the telemetron Docker bridge network [always, network]
26. WARN -- /opt/telemetron host tree will be removed [always]
27. Remove /opt/telemetron parent host tree [always]

(Pre_tasks shown first by `--list-tasks` as a single task; post_tasks shown last.)

**Verify-block invariants:**
- 12 `tasks_from: uninstall` references (one per role including nfsd)
- 11 `tasks_from: purge` references (every role except nfsd — D-156)
- python3 regex assertion: role include order = literal reverse of deploy_docker.yml
- All 23 `include_role` invocations use FQCN `ansible.builtin.include_role`
- Negative grep on `tags:.*-(uninstall|purge|data|image)$` → no matches (D-133 single role tag)
- 3 occurrences of `telemetron_purge_host_dirs | default(false) | bool` (post_tasks WARN + post_tasks file; D-153 belt-and-suspenders elsewhere via per-role purge.yml)
- Header cites D-149, D-150, D-155, D-156, D-159, D-160 by ID for downstream auditing

## Deviations from Plan

None — plan executed exactly as written. Pattern map (`11-PATTERNS.md` lines 28-193) was followed verbatim for the header, banner, per-role include pair shape, and post_tasks structure.

## Decisions Made

(Inherited from CONTEXT.md; the orchestrator plan codified these as wire shapes, but the calls were already settled.)

- **D-149 hardcoded order, not loop:** A `loop: roles_in_reverse` over a single include_role pattern would break `--tags <role>` scoping because Ansible applies tags to the loop task as a whole, not per-iteration. The literal 23-task expansion is the only shape that lets `--tags garage` scope to garage's pair.
- **D-150 network removal in post_tasks:** Deploy creates network first (pre_tasks); undeploy removes last (post_tasks) — symmetric lifecycle. state=absent on missing network is a no-op (D-141), so back-to-back run is changed=0.
- **D-156 nfsd uninstall-only:** nfsd has NO purge.yml because Phase 10 D-136..D-140 rule that the OS package, the systemd service, and the share root all stay. The host_dirs flag doesn't affect nfsd either (no `/opt/telemetron/nfsd/` subdir). Orchestrator must NOT write `include_role tasks_from: purge` for nfsd.
- **Banner uses category descriptions, not enumeration:** Listing each volume/image by name would force banner edits every time a new role joins the stack. Category-level ("all telemetron_* named Docker volumes") is stable across role additions (D-160).

## Threat Mitigations Applied

| Threat ID | Mitigation Shipped In This Plan |
|-----------|---------------------------------|
| T-11-04-01 (operator typo on `-i inventory/...`) | D-160 PLAY-start banner is the FIRST thing in PLAY OUTPUT, listing all 3 flags with category description. Operator has visual notice before destruction. |
| T-11-04-02 (host_dirs overreach into operator data) | D-155 parent-only `ansible.builtin.file state=absent` at orchestrator post_tasks. Per-role purge.yml has NO host_dirs section (Plans 11-01/02/03 enforced by negative grep). |
| T-11-04-03 (image collateral damage) | Per-role purge.yml uses `failed_when: false` on docker_image state=absent (Plans 11-01/02/03 — not changed by this plan, but the orchestrator's OR-gate `include_role tasks_from: purge` is what surfaces it). |
| T-11-04-04 (nfsd OS-level divergence) | D-156 — orchestrator wraps ONLY `tasks_from: uninstall` for nfsd in `when: enable_nfsd`. NO purge include for nfsd. Verify enforces by counting `tasks_from: purge` = exactly 11. |
| T-11-04-05 (silent destruction) | D-160 PLAY-start banner + D-159 per-action WARN (host_dirs Task B) + D-145 separately-named debug task pattern. `WARNING: irreversible --` grep-friendly. |
| T-11-04-06 (missing per-role purge.yml) | `depends_on: [11-01, 11-02, 11-03]` enforced sequencing — wave 1 wrote all 11 purge.yml files before this plan executed. Confirmed via filesystem check at plan start. |
| T-11-04-07 (sub-tag scoping break) | Negative grep on `tags:.*-(uninstall|purge|data|image)$` → no matches. Every task has single role tag only (D-133). |
| T-11-04-08 (secrets in PLAY OUTPUT) | Accepted — undeploy doesn't actually need vault decryption; `--ask-vault-pass` is muscle-memory UX parity only. |
| T-11-04-SC (package installs) | Accepted — pure YAML authoring; no npm/pip/cargo. |

## Known Stubs

None. All 23 include_role calls reference real existing tasks_from targets (verified at plan start — 12 uninstall.yml + 11 purge.yml files present from Phase 10 + Phase 11 wave 1).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | c2297a7 | Scaffold header + frame + vars + pre_tasks banner |
| 2 | 93df6a1 | Add 23 include_role tasks in reverse-deploy order (D-149) |
| 3 | a99c4a0 | Add post_tasks block — network removal + host_dirs parent rmdir |

## Self-Check: PASSED

- `playbooks/undeploy_docker.yml` exists at repo root: FOUND
- Commit c2297a7: FOUND in git log
- Commit 93df6a1: FOUND in git log
- Commit a99c4a0: FOUND in git log
- ansible-playbook --syntax-check: PASSES
- ansible-playbook --list-tasks: emits expected 26-task linear program

## Next Step

Plan 11-05 picks up the live-leviathan UAT (`11-HUMAN-UAT.md` already written in wave 1) — runs the 7-test acceptance matrix (conservative undeploy + redeploy, back-to-back idempotency, partial-deploy simulation, each of the 3 purge flags individually, all 3 combined). Acceptance gate for UNDEPLOY-01 + PURGE-01 + PURGE-02 + OPS-01 + OPS-02.
