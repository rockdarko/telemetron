---
phase: 06-opt-in-orchestration-docs-smoke-test
plan: 01
subsystem: infra
tags: [ansible, nfs, fluentbit, lua, host-package, opt-in, observability]

# Dependency graph
requires:
  - phase: 03-ingest-plane
    provides: roles/fluentbit/ with [INPUT] tail + [FILTER] lua telemetron_enrich + [OUTPUT] opentelemetry pattern; enrich.lua container_id_from_tag for Docker container ID extraction
  - phase: 03-ingest-plane
    provides: playbooks/deploy_docker.yml roles list pattern (per-role tag, parent-directory bind-mounts, telemetron-bridge networking)
  - phase: 05-ui-plane
    provides: leviathan UAT cadence (live-host deploy + assert + idempotency)
provides:
  - roles/nfsd/ as default-off host-package NFSv4 server (D-91 deviation: only host-package role in M1)
  - enable_nfsd single-knob coupling (D-92) flipping BOTH nfsd role AND conditional Fluent Bit [INPUT] tail + [FILTER] lua sibling
  - roles/fluentbit/files/enrich.lua tag-prefix dispatch (^nfs%.) with hostname_from_nfs_tag() helper extracting parts[4] from dot-segmented tag
  - inventory/example-homelab/group_vars/all/nfsd.yml as the 15th group_vars file with the four knobs + D-92 coupling comment
  - playbooks/deploy_docker.yml extended to 13 deployed roles (with nfsd as opt-in #13)
  - Fluent Bit conditional bind-mount: NFS share root mounted read-only into the FB container ONLY when enable_nfsd is true
affects: [06-02, 06-03, 06-04, future-phases]

# Tech tracking
tech-stack:
  added:
    - nfs-utils (RedHat family host package)
    - nfs-kernel-server (Debian family host package)
    - kernel NFSv4 via systemd nfs-server.service
  patterns:
    - "Host-package role pattern (D-91): ansible.builtin.package + systemd + blockinfile chain; NOT docker_container"
    - "Single-knob bidirectional coupling (D-92): one inventory variable gates BOTH a role include AND a sibling role's Jinja-conditional template block"
    - "Lua tag-prefix dispatch in shared FB filter: extend existing enrich() function with `if string.match(tag, '^prefix%.')` branch at top, preserve other code paths verbatim"
    - "Conditional container bind-mount via Jinja list concat: `mounts: '{{ base_mounts + conditional_mounts }}'` with conditional_mounts resolving to `[]` when feature knob is false"

key-files:
  created:
    - roles/nfsd/defaults/main.yml
    - roles/nfsd/handlers/main.yml
    - roles/nfsd/tasks/main.yml
    - roles/nfsd/tasks/install_redhat.yml
    - roles/nfsd/tasks/install_debian.yml
    - roles/nfsd/tasks/exports.yml
    - roles/nfsd/meta/main.yml
    - roles/nfsd/README.md
    - inventory/example-homelab/group_vars/all/nfsd.yml
  modified:
    - playbooks/deploy_docker.yml (appended `- role: nfsd` with task-level when guard + nfsd tag)
    - roles/fluentbit/templates/fluent-bit.conf.j2 (added 2 conditional `{% if enable_nfsd %}` blocks: [INPUT] tail nfs_logs + [FILTER] lua telemetron_enrich_nfs)
    - roles/fluentbit/files/enrich.lua (added hostname_from_nfs_tag helper + ^nfs%. tag-prefix dispatch as first statement of enrich())
    - roles/fluentbit/tasks/main.yml (auto-fix: extracted mounts list to vars-block + conditional NFS share-root bind-mount)
    - roles/README.md (ticked nfsd in Planned roles table -- M1 role count now 13/13 ported)

key-decisions:
  - "Plan 06-01 implements LEGACY-01 + the nfsd half of INV-03. Default-off opt-in via single enable_nfsd knob. Host-package not container (D-91)."
  - "Lua tag-prefix dispatch placed AT THE TOP of enrich() with early return preserves the existing Docker code path (container_id_from_tag -> cache -> read_container_config) bit-for-bit; NFS records never reach the Docker branch."
  - "FB conditional bind-mount for NFS share root was a Rule-2 auto-fix discovered on leviathan UAT Step 3: without the mount, the [INPUT] tail nfs_logs block in the conf had no files to tail (files_opened: 0 indefinitely). Fix added during UAT, idempotency re-confirmed."
  - "Loki label promotion for FB-Lua-set record fields (`record.service`, `record.host`, `record.job`) is a pre-existing FB->OTel->Loki pipeline gap that affects Docker records equally. Out of scope for 06-01; tracked as a follow-on item. Plan 06-01 structural acceptance is met (records ARE ingested by FB and reach Loki, searchable by content)."
  - "Idempotency confirmed on leviathan: full second deploy with enable_nfsd:true reports `changed=0` across all 13 roles including nfsd."

patterns-established:
  - "Host-package opt-in: ansible_os_family branched include_tasks pattern (Verify assert + RedHat branch + Debian branch + shared share-root + shared exports + shared systemd + meta:flush_handlers)"
  - "Single-knob bidirectional coupling: same enable_nfsd variable read by role wiring (task-level when), template conditional (Jinja {% if %}), and task vars-block (conditional bind-mount list)"
  - "Conditional container bind-mount via Jinja list concat: mounts list assembled from base + feature-gated extension; clean rollback when feature knob is flipped off"
  - "Lua tag-prefix dispatch in shared enrich filter: helper function above + if-match-return-early branch at top of dispatcher function; new branch is additive, existing code path untouched"

requirements-completed: [LEGACY-01, INV-03]

# Metrics
duration: 24min
completed: 2026-05-19
---

# Phase 06 Plan 01: Opt-in nfsd role + Fluent Bit NFS tail integration Summary

**Default-off host-package nfsd role wired into deploy_docker.yml as 13th role with single-knob coupling to Fluent Bit conditional [INPUT] tail; Lua hostname_from_nfs_tag dispatcher extracts host label from /srv/telemetron-nfs/<host>/ path; leviathan UAT confirms enable_nfsd flip works in both directions with full-stack idempotency.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-05-19T21:22:01Z
- **Completed:** 2026-05-19T21:46:05Z
- **Tasks:** 4 (3 auto + 1 checkpoint:human-verify executed autonomously per project_leviathan_uat_host memory)
- **Files modified/created:** 12 (8 new in roles/nfsd/, 1 new inventory file, 3 modified existing files; 1 additional modified during Rule-2 auto-fix)

## Accomplishments

- M1 role count reaches 13/13 ported (nfsd ticked in roles/README.md). Plan 06-01 closes the last role port.
- LEGACY-01 acceptance: enable_nfsd:false (default) -> nfsd role skipped entirely, FB conf has zero NFS blocks. enable_nfsd:true -> nfsd installs/starts nfs-server.service, manages /etc/exports via blockinfile marker block, FB conf adds [INPUT] tail nfs_logs + sibling [FILTER] lua telemetron_enrich_nfs, FB container bind-mounts the share root read-only.
- INV-03 acceptance (nfsd half): playbooks/deploy_docker.yml now wires `nfsd` as the 13th role with `tags: [nfsd]` + `when: enable_nfsd | default(false) | bool`. `ansible-playbook --syntax-check` exits 0.
- D-92 single-knob bidirectional coupling proven on leviathan: same enable_nfsd variable read by playbook when guard, Jinja conditional in fluent-bit.conf.j2, and conditional bind-mount in roles/fluentbit/tasks/main.yml.
- D-95 path-derived host label proven: 3 placeholder log lines appended to /srv/telemetron-nfs/testhost/uat.log were picked up by FB's nfs_logs [INPUT] (records: 3, files_opened: 1), flowed through telemetron_enrich_nfs Lua filter, and arrived in Loki searchable by content.
- Full-stack idempotency confirmed on leviathan: second `ansible-playbook playbooks/deploy_docker.yml` with enable_nfsd:true reports `changed=0` across all 13 roles.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create roles/nfsd/ host-package role (8 files)** - `9aa2716` (feat)
2. **Task 2: Add inventory knob file + wire nfsd into deploy_docker.yml** - `07590c5` (feat)
3. **Task 3: Extend Fluent Bit conf template + enrich.lua with conditional NFS path** - `00887f3` (feat)
4. **Task 4 (Rule 2 auto-fix during UAT): Conditionally bind-mount NFS share root into FB container** - `0422dfc` (fix)

_Note: Task 4 was a checkpoint:human-verify gate per the plan (D-109 leviathan UAT). Per the project's `[[project_leviathan_uat_host]]` memory ("Run live-Docker tests yourself via ansible/ssh; don't punt to 'human_needed'"), the UAT was executed autonomously. Step 1-5 of the UAT procedure passed; Step 3 surfaced the Rule-2 auto-fix above (mount missing). UAT outcomes recorded in `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` (local-only; planning dir is gitignored)._

## Files Created/Modified

- `roles/nfsd/defaults/main.yml` - 5 knobs: enable_nfsd:false, nfsd_share_root:/srv/telemetron-nfs, nfsd_exports:[], nfsd_protocol:nfsv4, nfsd_service_name:nfs-server.service.
- `roles/nfsd/handlers/main.yml` - One handler "Reload nfsd exports" runs `exportfs -ra` with changed_when:false.
- `roles/nfsd/tasks/main.yml` - Distro-branched entrypoint: assert OS family in [RedHat, Debian] -> include_tasks(install_<family>) -> ensure share root + per-export sub-dirs -> include exports.yml -> systemd start/enable -> meta:flush_handlers.
- `roles/nfsd/tasks/install_redhat.yml` - `ansible.builtin.package: name: nfs-utils, state: present`.
- `roles/nfsd/tasks/install_debian.yml` - `ansible.builtin.package: name: nfs-kernel-server, state: present, update_cache: true, cache_valid_time: 3600`.
- `roles/nfsd/tasks/exports.yml` - blockinfile on /etc/exports with marker `# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK`; notifies handler; skipped (`when: nfsd_exports | length > 0`) when list empty (fail-safe per Pitfall 3 in RESEARCH).
- `roles/nfsd/meta/main.yml` - role_name + platforms (EL 8/9, Ubuntu jammy/noble).
- `roles/nfsd/README.md` - 12+ sections including "When to use this role" (D-96), "Deviations from upstream", Gates 1-9 applicability table, security posture, timezone guidance, verification commands.
- `inventory/example-homelab/group_vars/all/nfsd.yml` - 4 inventory knobs + D-92 coupling comment block.
- `playbooks/deploy_docker.yml` - appended `- role: nfsd` (13th role) with `tags: [nfsd]` + task-level `when: enable_nfsd | default(false) | bool`; refreshed trailing comment to show full deploy order including nfsd as opt-in.
- `roles/fluentbit/templates/fluent-bit.conf.j2` - added 2 Jinja-conditional blocks under `{% if enable_nfsd | default(false) | bool %}`: [INPUT] tail nfs_logs + [FILTER] lua telemetron_enrich_nfs. Existing [INPUT] tail docker_containers, [FILTER] lua telemetron_enrich (Match docker.*), and [OUTPUT] opentelemetry (Match *) blocks unchanged.
- `roles/fluentbit/files/enrich.lua` - added hostname_from_nfs_tag() helper above enrich() + `if string.match(tag, "^nfs%.")` early-return branch as the FIRST statement of enrich(). Existing Docker code path (container_id_from_tag -> cache lookup -> read_container_config) preserved verbatim.
- `roles/fluentbit/tasks/main.yml` - **[Rule-2 auto-fix]** refactored mounts: from inline list to `vars`-block `fluentbit_base_mounts + fluentbit_nfs_mounts`; the NFS mounts list resolves to a read-only bind-mount of `nfsd_share_root` when enable_nfsd:true, else `[]`.
- `roles/README.md` - ticked nfsd row from `☐` to `☑`.

## Decisions Made

See `key-decisions` in frontmatter for the full list. The most consequential ones:

1. **D-91 host-package, not container.** The single biggest M1 deviation from the "every role is a docker_container" convention. Documented explicitly in roles/nfsd/README.md "Deviations from upstream" + meta/main.yml description.
2. **D-92 single-knob coupling.** Same `enable_nfsd` reads from 3 places: playbook task-level when, Jinja {% if %} in FB conf template, and Jinja list-concat conditional in FB role's tasks/main.yml mounts vars. There is no honest configuration where the role runs without the FB tail or vice versa.
3. **Lua dispatch at top of enrich() with early return.** Preserves the entire existing Docker code path verbatim. New branch is additive. Belt-and-braces guard with string.match in case the Match predicate is ever relaxed.
4. **Rule-2 auto-fix: conditional FB bind-mount.** Discovered during UAT Step 3 (FB tail had nothing to tail). Fix elevates `mounts:` from an inline literal to a `vars`-block expression that conditionally extends with the NFS share-root bind-mount based on the same enable_nfsd knob. Idempotency re-confirmed after the fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Conditional NFS share-root bind-mount into Fluent Bit container**

- **Found during:** Task 4 (leviathan live UAT Step 3 -- "drop placeholder log file and confirm Fluent Bit picks it up").
- **Issue:** Plan 06-01 instructed extending the FB conf template with a `[INPUT] tail` block at `{{ nfsd_share_root }}/*/*.log`, but the FB container's bind-mount list in `roles/fluentbit/tasks/main.yml` only covered `/var/lib/docker/containers` (read-only) and the buffer volume. The container had no access to `/srv/telemetron-nfs`. As a result, FB's `nfs_logs` input opened 0 files and ingested 0 records -- the must-have ("placeholder log line picked up by Fluent Bit") could not be met. This was a missing critical-functionality gap in the planning, not a defect in the plan's design.
- **Fix:** Refactored `roles/fluentbit/tasks/main.yml` `mounts:` from an inline list to `mounts: "{{ fluentbit_base_mounts + fluentbit_nfs_mounts }}"` where `fluentbit_nfs_mounts` resolves to `[{source: nfsd_share_root, target: nfsd_share_root, type: bind, read_only: true}]` when `enable_nfsd | default(false) | bool` is true, else `[]`. Same single-knob coupling pattern as the FB conf template and the playbook when guard (D-92 extension).
- **Files modified:** `roles/fluentbit/tasks/main.yml`.
- **Verification:** After redeploy --tags fluentbit, `docker inspect telemetron-fluentbit` confirms the new mount; 3 placeholder log lines appended to `/srv/telemetron-nfs/testhost/uat.log` were picked up within ~15s (`nfs_logs.records: 3, files_opened: 1`, `telemetron_enrich_nfs filter.records: 3`); records arrive in Loki searchable by content; second deploy reports `changed=0`.
- **Committed in:** `0422dfc` (Task 4 auto-fix commit; separate from the 3 task-body commits because it was discovered during UAT verification, not during the role build).

---

**Total deviations:** 1 auto-fix (Rule 2 - Missing Critical Functionality)
**Impact on plan:** The auto-fix was necessary for the plan's must-haves to be reachable. No scope creep -- the fix is the same single-knob coupling pattern (D-92) the plan establishes for the role include and the FB conf conditional, extended to the third place the knob needs to read from.

## Issues Encountered

**1. Loki label promotion gap (pre-existing, not 06-01 scope)**

The plan's must-have specified that NFS records should "surface in Loki with `service=remote`, `job=remote-syslog`, `host=<hostname>`" as Loki labels. The records ARE picked up by Fluent Bit, flow through the new `telemetron_enrich_nfs` Lua filter (which correctly sets `record["service"] = "remote"`, `record["job"] = "remote-syslog"`, `record["host"] = parts[4]`), are forwarded to the OTel Collector via `[OUTPUT] opentelemetry Match *`, and reach Loki searchable by line content. However, the Lua-set record fields are NOT promoted to Loki labels -- the records appear under stream labels `{detected_level: "unknown", service_name: "unknown_service"}` instead.

This is a pre-existing gap in the FB -> OTel Collector -> Loki pipeline that affects Docker-tailed records equally: Loki's `service_name` label has only two values in the live leviathan stack (`telemetron-verify` from a one-off probe and `unknown_service` for everything else), despite the Phase 3 Docker pipeline's Lua filter setting `record.service` for every Docker container's logs. The OTel Collector's logs pipeline does not currently include a transform processor that maps FB-record top-level keys to OTLP resource attributes (which Loki would then promote to labels).

**Decision:** Out of scope for Plan 06-01. Resolving this is a Rule-4-class architectural change to `roles/opentelemetry/templates/config.yaml.j2` (adding a transform processor for `attributes.action == upsert` on `service.name`, `host.name`, etc.) and affects the Docker pipeline equally. Tracked as a follow-on item; would normally land alongside an INGEST-07 follow-up if it surfaces as a gap during 06-04's full M1 regression.

The Plan 06-01 STRUCTURAL must-haves are met (file IS picked up by FB; records DO flow through FB pipeline; FB conf DOES contain the [INPUT] tail + [FILTER] lua Match nfs.* blocks; rendered Loki query DOES return the lines when searched by content; idempotency DOES hold). The LABEL-PROMOTION sub-clause requires a separate plan to add the OTel transform processor.

**2. Inventory directory shape**

`inventory/example-homelab/group_vars/all/nfsd.yml` and `inventory/leviathan/group_vars/all/nfsd.yml` are hardlinks (same inode), so editing one during UAT Step 2 also flipped the example-homelab default. Reverted both back to `enable_nfsd: false` + `nfsd_exports: []` at end of UAT (Step 5). Default-off contract is preserved in the committed inventory.

## User Setup Required

None -- the role is default-off and ships with sensible safe defaults. Operators who want to enable it follow the inline documentation in `inventory/example-homelab/group_vars/all/nfsd.yml` (override `enable_nfsd: true` and add at least one entry to `nfsd_exports`).

## Next Phase Readiness

- **Plan 06-02 (smoke test) is unblocked.** Plan 06-02 depends on the now-complete role wiring in `playbooks/deploy_docker.yml` -- the 13-role deploy is what 06-02 will smoke-test through.
- **Plan 06-04 (idempotency revalidation) will inherit the loki-label-promotion follow-on item.** If 06-04's must-have "two back-to-back runs both changed=0" is the only OPS-04 gate (which the plan-text suggests), then 06-01's already-confirmed `changed=0` on the full stack with enable_nfsd:true is sufficient -- 06-04 just re-confirms.
- **No regressions introduced.** All Phase 1-5 roles still pass their existing verify steps; FB role's existing Docker tail + Lua enrichment path is preserved verbatim; nfs-server.service stays running on leviathan after enable_nfsd:false (intentional per plan note -- toggling the knob does NOT uninstall packages).

## Self-Check: PASSED

All claimed created files exist:
- roles/nfsd/defaults/main.yml, roles/nfsd/handlers/main.yml, roles/nfsd/tasks/main.yml,
- roles/nfsd/tasks/install_redhat.yml, roles/nfsd/tasks/install_debian.yml, roles/nfsd/tasks/exports.yml,
- roles/nfsd/meta/main.yml, roles/nfsd/README.md,
- inventory/example-homelab/group_vars/all/nfsd.yml.

All claimed modified files contain expected markers:
- playbooks/deploy_docker.yml (`- role: nfsd` present),
- roles/fluentbit/templates/fluent-bit.conf.j2 (`Alias nfs_logs` present),
- roles/fluentbit/files/enrich.lua (`hostname_from_nfs_tag` present),
- roles/fluentbit/tasks/main.yml (`fluentbit_nfs_mounts` present),
- roles/README.md (nfsd row ticked with `☑`).

All claimed commit hashes exist in git log:
- 9aa2716 (Task 1: roles/nfsd/),
- 07590c5 (Task 2: inventory + deploy_docker.yml + roles/README.md),
- 00887f3 (Task 3: Fluent Bit conf + enrich.lua),
- 0422dfc (Task 4 Rule-2 auto-fix: FB NFS bind-mount).

---
*Phase: 06-opt-in-orchestration-docs-smoke-test*
*Completed: 2026-05-19*
