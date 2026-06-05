# Phase 14: Orchestrators + Leviathan HUMAN-UAT - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 14-orchestrators-leviathan-human-uat
**Areas discussed:** Writer quiesce, Bail-out / banner, Stateless-tag UX, Restore-from propagation, UAT scope, Layout

---

## Writer quiesce (Loki/Tempo/Mimir around Garage restore)

### Q1: Where should the stop/restart logic live?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in restore_docker.yml | Two task blocks; uses command:docker stop + docker_container_info poll (Phase 13 cold-quiesce shape). No new files in writer roles. | ✓ |
| New per-role tasks/quiesce.yml + tasks/resume.yml in loki, tempo, mimir | Each writer role grows two new task files. Cleaner separation but 6 new YAML files for a concern with one caller. | |
| Inline via community.docker.docker_container state:stopped/started | Ansible-native idiom. Rejected — XP-1 (state:stopped strips volume/mount specs). | |

**User's choice:** Inline in restore_docker.yml
**Notes:** D-180 — keep cross-role coordination in the orchestrator, not spread across writer roles.

### Q2: Sequential or parallel?

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential loop | command + loop over [loki, tempo, mimir]; ~3 × graceful-stop bounded by backup_stop_timeout. | ✓ |
| Parallel via async/poll | Saves a few seconds; adds error-aggregation complexity; no precedent in codebase. | |
| Bulk via single docker stop loki tempo mimir | Docker parallelizes internally; loses per-container granularity. | |

**User's choice:** Sequential loop
**Notes:** D-181 — every multi-container op in Telemetron is sequential; consistency wins.

### Q3: Stop timeout?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse backup_stop_timeout (60s) | One shared knob; overkill but harmless for stateless S3 clients. | ✓ |
| New shared writer_stop_timeout (15s) | Faster; second knob to document. | |
| Per-role <writer>_stop_timeout | Granular; 3 new vars nobody asked for. | |

**User's choice:** Reuse backup_stop_timeout
**Notes:** D-182 — no hidden capacity knobs.

### Q4: Restart mechanism?

| Option | Description | Selected |
|--------|-------------|----------|
| docker start + docker_container_info healthy poll | Symmetric with stop; fast. | ✓ |
| deploy_docker.yml --tags loki,tempo,mimir | Re-renders config (defensive); pulls in image-check + network-attach tasks unnecessarily. | |
| Just docker start, no health poll | Fire-and-forget; failure surfaces too late. | |

**User's choice:** docker start + healthy poll
**Notes:** D-183 — s3-credentials restored with Garage, so no config drift to defend against.

---

## Bail-out / banner

### Q5: backup_docker.yml bail-out mechanism?

| Option | Description | Selected |
|--------|-------------|----------|
| any_errors_fatal at play level | One-line idiomatic Ansible; per-role include_role calls unchanged. | ✓ |
| Explicit block/rescue per include_role + counter | 4× the YAML for native behaviour. | |
| failed_when:false + final assertion | Hides failures during run; bad bail-out UX. | |

**User's choice:** any_errors_fatal expression
**Notes:** D-184.

### Q6: Should restore_docker.yml honour backup_continue_on_failure?

| Option | Description | Selected |
|--------|-------------|----------|
| Restore always bails out (hardcoded any_errors_fatal: true) | Half-restored state is a footgun; forces operator attention. | ✓ |
| Restore honours backup_continue_on_failure symmetrically | Symmetric but enables footgun. | |
| New restore_continue_on_failure var | Second knob nobody touches. | |

**User's choice:** Restore always bails out
**Notes:** D-185 — backup_continue_on_failure applies to backup only.

### Q7: Backup PLAY-start banner format?

| Option | Description | Selected |
|--------|-------------|----------|
| Single multi-line debug, tags: always, D-160 shape | Mirrors undeploy_docker.yml WARN banner; stable across role additions. | ✓ |
| Single-line summary debug | Less helpful for PLAY OUTPUT grep. | |

**User's choice:** Multi-line debug, D-160 shape
**Notes:** D-186.

### Q8: Restore PLAY-start banner?

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-line WARN debug with 'WARNING: irreversible --' prefix + permanently-replace phrase + target timestamp + stop order | Single grep target; full operator context. | ✓ |
| Two separate WARN tasks (banner + confirm-gate echo) | Redundant with orchestrator-level confirm-gate. | |
| Single-line WARN | Loses stop-order context. | |

**User's choice:** Multi-line WARN
**Notes:** D-187. ROADMAP SC2 mandates escalated D-160 WARN.

---

## Stateless-tag UX

### Q9: restore_docker.yml --tags loki behaviour?

| Option | Description | Selected |
|--------|-------------|----------|
| Empty 0-task play, symmetric with backup | No tasks match; Ansible produces empty PLAY RECAP. | ✓ |
| Explicit fail with helpful message | Also fires on legitimate --tags backup/--tags restore. | |
| Loki-tag scope = stop+restart cycle on Loki only | Mixes restore with recycle; wrong playbook. | |

**User's choice:** Empty 0-task play
**Notes:** D-188.

### Q10: How are writer-stop/restart tasks tagged?

| Option | Description | Selected |
|--------|-------------|----------|
| Tag with 'garage' only | --tags garage runs stop-writers → garage restore → restart-writers as one unit. --tags loki = empty play. | ✓ |
| Tag with ['garage', 'writers'] | Adds cross-cutting --tags writers; overloads destructive playbook with non-destructive op. | |
| Tag with 'always' | Stop+restart fire even on --tags prometheus; pointless writer-cycling. | |

**User's choice:** Tag with 'garage' only
**Notes:** D-189 — writer-quiesce IS a Garage-restore prerequisite; tag accordingly.

---

## Restore-from propagation

### Q11: Pre-resolve backup_restore_from at orchestrator, or per-role?

| Option | Description | Selected |
|--------|-------------|----------|
| Let each role resolve independently | Loose coupling; per-role error if requested tarball missing. | ✓ |
| Orchestrator pre-resolves once | Complex find-shared-timestamp logic; might not exist across all 4 dirs. | |
| Per-role override map (backup_restore_from_<role>) | Overkill; out of v1.3.0 scope. | |

**User's choice:** Per-role independent
**Notes:** D-190.

### Q12: backup_docker.yml shared timestamp vs per-role?

| Option | Description | Selected |
|--------|-------------|----------|
| Orchestrator generates once, re-exports as backup_timestamp_override | All 4 tarballs share one timestamp; operator-friendly for explicit restores. Requires small Phase 13 amendment to tasks/backup.yml. | ✓ |
| Each role calls date independently (Phase 13 as-shipped) | No Phase 13 changes; timestamps drift ~10s across roles. | |
| Pre-round to minute granularity | Edge cases at minute boundaries; clever > useful. | |

**User's choice:** Orchestrator generates once
**Notes:** D-191.

### Q13: Phase 13 backup.yml amendment in scope?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Phase 14 plan includes 4 small tweaks | One plan task touches 4 files; Phase 13 remains source of truth for shape; Phase 14 owns the orchestrator-driven knob. | ✓ |
| Treat as out-of-scope; accept timestamp drift | Cleaner phase boundary; cosmetic-only cost on explicit-timestamp restores. | |
| set_fact + hostvars binding | Same scope as option 1, different mechanism. | |

**User's choice:** Yes — Phase 14 includes the 4 tweaks
**Notes:** D-191 — discrete plan task with file paths called out.

---

## UAT scope

### Q14: 14-HUMAN-UAT.md scope?

| Option | Description | Selected |
|--------|-------------|----------|
| Expanded: 7-step happy-path + 3-4 negative scenarios | Mirrors Phase 11 HUMAN-UAT; lives SC1, SC3, SC4, SC5 via live UAT, not just code review. | ✓ |
| Happy-path only | Smaller doc; re-introduces false-pass risk for confirm-gate/bail-out/tag-scoped SCs. | |
| Happy-path + confirm-gate proof only | Two scenarios; bail-out + tag-scoped left to code review. | |

**User's choice:** Expanded scope
**Notes:** D-192 — 4 scenarios: round-trip happy-path, confirm-gate (orchestrator + per-role), bail-out vs continue-on-failure, tag-scoped backup+restore.

---

## Layout

### Q15: Physical layout of restore_docker.yml?

| Option | Description | Selected |
|--------|-------------|----------|
| Single tasks: block (with pre_tasks for banner) | Matches undeploy_docker.yml shape; writer-restart inside tasks: keeps --tags garage symmetry. | ✓ |
| Explicit pre/tasks/post split | post_tasks runs regardless of --tags; would break --tags garage writer-restart symmetry. | |
| Single tasks: with section-banner comments | Cosmetic variant of option 1. | |

**User's choice:** Single tasks: block (pre_tasks for banner only)
**Notes:** D-193 — writer-restart MUST be in tasks: under the [garage] tag, not post_tasks.

---

## Claude's Discretion

- Pre-task `WARN -- writers will be stopped` debug before writer-stop loop (echo D-159 vs skip; default skip)
- Backup orchestrator success summary listing tarball paths (planner decides)
- Restore orchestrator success summary recommending smoke_test.yml (planner decides)
- 14-HUMAN-UAT.md `status:` frontmatter initial value (`in_progress` vs `pending`; prior phase convention)
- HUMAN-UAT doc ship timing — same plan as orchestrators with `result: not run` placeholders, or separate plan (planner decides)
- Phase 13 tasks/backup.yml amendment implementation pattern — `when: backup_timestamp_override is not defined` skip-date vs unconditional date + set_fact override (both work)
- Fault-injection mechanism for HUMAN-UAT scenario 3 — manual `chattr +i` instruction vs `playbooks/uat_inject_failure.yml` (default manual)

## Deferred Ideas

- `writer_stop_timeout` shared knob (capture if 60s reuse becomes ergonomically wrong)
- Per-role override map `backup_restore_from_<role>` (out of v1.3.0 scope; operators wrap with custom playbook + per-role tasks_from=restore)
- `restore_continue_on_failure` knob (footgun; not shipped)
- Async/parallel writer-quiesce (D-181 rejected; reconsider only if leviathan UAT shows sequential is annoying)
- Automated `playbooks/uat_inject_failure.yml` (Claude's Discretion; manual default)
- Cross-role pre-flight (each per-role task already lazy-creates destination subdir)
- Banner with role enumeration (D-186 explicitly avoids; stable across role additions)
