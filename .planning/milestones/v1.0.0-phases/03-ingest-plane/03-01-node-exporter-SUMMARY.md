---
phase: 03-ingest-plane
plan: 01-node-exporter
subsystem: infra
tags: [ansible, docker, prometheus, node-exporter, host-metrics, observability, monolithic, telemetron]

# Dependency graph
requires:
  - phase: 01-foundation-storage
    provides: telemetron Docker bridge network (pre_tasks), inventory group_vars skeleton, port-acceptance gate framework
  - phase: 02-telemetry-backends
    provides: canonical role template (defaults/tasks/verify/handlers/meta/README) proven across loki/tempo/mimir; conditional-HEALTHCHECK pattern; D-10a poll discipline
provides:
  - node_exporter role on roles/node_exporter/ shipping host metrics at http://node-exporter:9100/metrics on the telemetron bridge
  - pinned image quay.io/prometheus/node-exporter:v1.11.1
  - three RO bind-mount triple (/proc, /sys, /) with pid_mode host
  - hardened container default (read-only rootfs, cap_drop ALL + DAC_READ_SEARCH, no-new-privileges, tmpfs /tmp, pids_limit 512) guarded by an inventory knob
  - in-network /metrics curl asserting node_cpu_seconds_total body match (D-54 authoritative readiness gate)
  - playbooks/deploy_docker.yml extended to minio -> loki -> tempo -> mimir -> node_exporter
affects: [03-02-opentelemetry, 03-03-prometheus, 03-04-fluentbit, 05-grafana, 06-orchestration-docs]

# Tech tracking
tech-stack:
  added: [node_exporter v1.11.1 (quay.io/prometheus/node-exporter)]
  patterns:
    - "Phase-3-role canonical shape proven: no-rendered-config role (CLI-flag-driven), conditional-HEALTHCHECK omit-magic-value, in-network /metrics curl verify -- inherited template for opentelemetry/prometheus/fluentbit"
    - "Container hardening knob (`<role>_container_hardening_enabled`) with all six security fields collapsing to `omit` when false -- introduced here, available for any future container-hardened role"
    - "D-25 audit TL;DR bullet block at top of Deviations section -- machine-greppable `- (Dropped|Replaced|Added|Kept):` lines preserved alongside the detailed `**Dropped:**` paragraphs"

key-files:
  created:
    - roles/node_exporter/defaults/main.yml
    - roles/node_exporter/tasks/main.yml
    - roles/node_exporter/tasks/verify.yml
    - roles/node_exporter/handlers/main.yml
    - roles/node_exporter/meta/main.yml
    - roles/node_exporter/README.md
    - inventory/example-homelab/group_vars/all/node_exporter.yml
  modified:
    - playbooks/deploy_docker.yml
    - roles/README.md

key-decisions:
  - "Image registry: Quay (quay.io/prometheus/node-exporter) over Docker Hub (prom/node-exporter) -- matches Phase-1 alertmanager registry choice and avoids Docker Hub rate-limit risk for unauth pulls"
  - "Image tag: v1.11.1 (RESEARCH.md Finding 6, 2026-04-07 release) -- supersedes CONTEXT.md's stale v1.8.x mention"
  - "Healthcheck Outcome B selected as default: --version binary-alive proxy; --health flag is not documented in node_exporter v1.11.1 CLI surface -- authoritative readiness gate is the verify task's in-network /metrics curl asserting node_cpu_seconds_total"
  - "Container hardening kept from upstream but guarded by inventory knob (node_exporter_container_hardening_enabled, default true) so RHEL/SELinux operators can flip off without role restructure"
  - "Inventory file ships three operator knobs (publish_host, container_hardening_enabled, healthcheck_enabled) -- high-signal surface; all other defaults stay in roles/node_exporter/defaults/main.yml"

patterns-established:
  - "No-rendered-config role pattern: skip 'ensure config dir' and 'render template' tasks entirely when the component is CLI-flag-driven; handler still exists for future-compat with command-flag knobs"
  - "Three-bind-mount triple (/proc, /sys, /) with rslave on root -- canonical shape for any host-metrics exporter that lands in future milestones"
  - "Audit TL;DR pattern: short `- Dropped:` / `- Replaced:` / `- Added:` / `- Kept:` bullets at the top of the README Deviations section + detailed `**Dropped:**` paragraphs below"

requirements-completed: [INGEST-08]

# Metrics
duration: 7 min
completed: 2026-05-18
---

# Phase 03 Plan 01: node-exporter Summary

**node_exporter v1.11.1 ported as Telemetron's Wave-1 Phase-3 role: hardened single-binary on quay.io/prometheus/node-exporter, three RO host bind-mounts + pid_mode host, conditional-HEALTHCHECK pattern, in-network /metrics curl asserting node_cpu_seconds_total**

## Performance

- **Duration:** ~7 min (398 seconds wall)
- **Started:** 2026-05-18T13:26:43Z
- **Completed:** 2026-05-18T13:33:21Z
- **Tasks:** 8
- **Files created:** 7
- **Files modified:** 2

## Accomplishments

- Canonical six-file role layout (defaults/tasks/verify/handlers/meta/README) on disk at roles/node_exporter/ mirroring roles/mimir/ exactly modulo node_exporter-specifics (no rendered config, no Docker volume, three RO bind-mounts, pid_mode host)
- Pinned image quay.io/prometheus/node-exporter:v1.11.1 -- supersedes CONTEXT.md's stale v1.8.x mention with RESEARCH.md Finding 6 verified release (2026-04-07)
- Conditional-HEALTHCHECK pattern reused verbatim from Phase-2 mimir/tempo precedent: Outcome B (--version binary-alive proxy) default; Outcome C (disabled, fall back to State.Running) one knob-flip away
- Container hardening default-enabled (read-only rootfs, cap_drop ALL, add DAC_READ_SEARCH, no-new-privileges, tmpfs /tmp, pids_limit 512), guarded by node_exporter_container_hardening_enabled knob -- collapses cleanly to Ansible `omit` when flipped off
- Verify task: D-10a docker_container_info poll (HEALTHCHECK or State.Running) followed by curlimages/curl:8.10.1 one-shot asserting HTTP 200 AND body match for node_cpu_seconds_total over the telemetron bridge -- 60s total budget
- playbooks/deploy_docker.yml role list grew from 4 to 5 entries in D-41 order (minio -> loki -> tempo -> mimir -> node_exporter); ansible-playbook --syntax-check exits 0
- All six per-role port-acceptance gates pass on roles/node_exporter/

## Task Commits

Each task was committed atomically:

1. **Task 1: scaffold role skeleton** - `f78c22f` (feat)
2. **Task 2: populate defaults with v1.11.1 pin and hardening knobs** - `26d09e7` (feat)
3. **Task 3: write tasks/main.yml -- pull, run with bind-mounts and pid_mode host, include verify** - `82d2dd2` (feat)
4. **Task 4: write tasks/verify.yml -- D-10a poll + in-network /metrics assertion** - `6b9e45a` (feat)
5. **Task 5: add single restart handler (W6 / Pitfall 8)** - `e38d1cf` (feat)
6. **Task 6: write README with OPS-03 schema + D-25 deviations audit** - `02b86e4` (feat; also tightens INSPQ-in-comments in defaults/tasks per Phase-2 D-25 reinterpretation)
7. **Task 7: wire into example inventory + deploy_docker playbook (D-41 order)** - `589aad2` (feat)
8. **Task 8: tick roles/README.md row + confirm six port-acceptance gates** - `2f74afa` (feat)

**Plan metadata commit:** appended after self-check (docs)

## Files Created/Modified

### Created

- `roles/node_exporter/defaults/main.yml` - Role tunables: image pin v1.11.1, container identity, port 9100, no-host-publish default, conditional-HEALTHCHECK trio of knobs, hardening knob, curl pin
- `roles/node_exporter/tasks/main.yml` - Pull + run docker_container with three RO bind-mounts, pid_mode host, six hardening fields collapsing on omit, D-30 triple-conditional published_ports, verbatim command flags from RESEARCH Finding 6, conditional healthcheck, final include_tasks verify.yml
- `roles/node_exporter/tasks/verify.yml` - D-10a HEALTHCHECK or State.Running poll (conditional on knob) + in-network curlimages/curl:8.10.1 one-shot asserting /metrics 200 with node_cpu_seconds_total in body, 60s budget
- `roles/node_exporter/handlers/main.yml` - Single 'Docker restart node_exporter' handler (W6 / Pitfall 8); unused in M1 (no notify points since no rendered config) but lands per canonical template
- `roles/node_exporter/meta/main.yml` - galaxy_info { role_name, MIT license, Ubuntu jammy/noble + Debian bookworm platforms, metrics/node-exporter/observability/telemetron tags }, dependencies [], collections [community.docker, ansible.builtin]
- `roles/node_exporter/README.md` - 13-section OPS-03 schema doc with Variables table, Conditional-HEALTHCHECK Outcomes A/B/C, SSH local-forward operator access pattern, three-bind-mount table, D-25 Deviations audit
- `inventory/example-homelab/group_vars/all/node_exporter.yml` - Three operator knobs (publish_host false, hardening_enabled true, healthcheck_enabled true)

### Modified

- `playbooks/deploy_docker.yml` - Appended 'role: node_exporter' entry after mimir per D-41 order with tag node_exporter; updated trailing comment block to reflect new state (Phase 3 still needs opentelemetry/prometheus/fluentbit)
- `roles/README.md` - Ticked node_exporter row from ☐ to ☑ in the planned-roles table

## Decisions Made

- **Image registry choice (Quay > Docker Hub):** quay.io/prometheus/node-exporter matches the Phase-1 alertmanager precedent and avoids Docker Hub unauth-pull rate-limit risk for homelab operators. Both registries publish the same official Prometheus-org image.
- **Image tag v1.11.1 (research-corrected):** CONTEXT.md cited v1.8.x as the current line; RESEARCH.md Finding 6 verified v1.11.1 as the actual current release (2026-04-07). Plan executor used the corrected pin.
- **Conditional-HEALTHCHECK Outcome B as default:** node_exporter is built FROM scratch -- no shell, no curl, and no documented native --health flag in the v1.11.1 CLI surface. `--version` exits 0 with a banner, making it a valid binary-alive proxy. The authoritative readiness gate is delegated to the verify task's in-network /metrics curl. This mirrors the Phase-2 mimir/tempo pattern verbatim.
- **Container hardening guarded by knob:** Kept the upstream hardening set (read-only, cap_drop ALL, DAC_READ_SEARCH, no-new-privileges, tmpfs /tmp, pids_limit 512) AND added `node_exporter_container_hardening_enabled` knob so RHEL/SELinux operators can flip off without role restructure. Default true.
- **D-25 audit TL;DR pattern:** Plan acceptance criterion required `- (Dropped:|Replaced:|Added:|Kept)` bullet lines (which canonical Phase-2 mimir/tempo READMEs technically don't satisfy literally -- they use `**Dropped:**` bold paragraphs). Resolved by shipping BOTH: short greppable TL;DR bullets at the top of the Deviations section + detailed `**Dropped:**` paragraphs below. Forward-compat for the Phase-3+ acceptance regex.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] INSPQ string in YAML-file comments would have failed the Phase-2 D-25 reinterpretation grep gate**

- **Found during:** Task 6 (README + cross-cutting INSPQ-grep audit on YAML files)
- **Issue:** Initial Task 2 (defaults/main.yml) and Task 3 (tasks/main.yml) outputs included comments referring to "upstream INSPQ security hardening set" and "kept from upstream INSPQ". Phase 2 established that the OPS-05 grep gate, when scoped to YAML/J2 files, must be clean -- the upstream-org name is allowed ONLY in the README's documented Deviations section. Sibling roles (roles/mimir/, roles/tempo/) ship with zero INSPQ matches in their YAML files.
- **Fix:** Rewrote the affected comments to refer to "upstream" or "kept-and-improved security set" with a back-reference to the README's Deviations section for the full audit. README content unchanged -- the audit narrative is still authoritative.
- **Files modified:** roles/node_exporter/defaults/main.yml, roles/node_exporter/tasks/main.yml
- **Verification:** `grep -riE 'inspq|...' roles/node_exporter/ --include='*.yml' --include='*.yaml' --include='*.j2'` returns zero matches.
- **Committed in:** `02b86e4` (Task 6 commit -- bundled with the README write since the README is the source-of-truth for the audit narrative)

**2. [Rule 1 - Bug] D-25 audit bullets missing in plan-required `- (Dropped|Replaced|Added|Kept):` form**

- **Found during:** Task 6 (README acceptance regex check)
- **Issue:** Plan Task 6 acceptance criterion required `grep -cE "^- (Dropped:|Replaced:|Added:|Kept)" roles/node_exporter/README.md` to return >= 3. The README initially used the canonical Phase-2 `**Dropped:**` bold-paragraph form (matching mimir/tempo precedent exactly), which doesn't satisfy the regex literally.
- **Fix:** Added a four-line TL;DR bullet block (`- Dropped: ...`, `- Replaced: ...`, `- Added: ...`, `- Kept: ...`) at the top of the Deviations section, preserving the detailed `**Dropped:**` paragraphs below. The bullets are machine-greppable and the paragraphs remain human-friendly.
- **Files modified:** roles/node_exporter/README.md
- **Verification:** `grep -cE "^- (Dropped:|Replaced:|Added:|Kept)" roles/node_exporter/README.md` returns 4.
- **Committed in:** `02b86e4` (Task 6 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1)
**Impact on plan:** Both fixes are alignment to existing Phase-2 standards (D-25 reinterpretation in YAML files; acceptance-criteria literal regex). No scope creep, no architectural change.

## Issues Encountered

- **`ugrep` regex error on `{{ *vault_` pattern:** The vault-discipline grep gate uses a regex that ugrep (the default `grep` binary on this host) interprets as an empty subexpression. Verified the intent (zero `{{ vault_` references) via a plain-text `grep -F` test instead. No vault references exist in roles/node_exporter/. Not a code defect; just a grep-tool quirk.
- **`grep -rE 'state:\s*restarted' roles/node_exporter/` (no file-type scope) trips on README documentation:** The README's Idempotency section contains the documented don't-do-this phrase ``state: restarted` is never used (Pitfall 8)`` -- same wording shipped in roles/mimir/README.md and roles/tempo/README.md in Phase 2. Re-scoped Gate 5 to YAML/J2 files to match the Phase-2 precedent; the README phrase is documentation, not code.

## Image-probe outcome (Conditional HEALTHCHECK selection)

The plan asked the executor to probe the image at execute time:

```
docker run --rm quay.io/prometheus/node-exporter:v1.11.1 --help | grep -i health
```

This was NOT actually executed (live Docker not available in this environment). The conditional-HEALTHCHECK default ships as **Outcome B** (`--version` binary-alive proxy) which is the safe default given:

1. The from-scratch image has no shell, no curl, no wget (so CMD-SHELL probes are off the table).
2. Public node_exporter v1.11.1 CLI documentation lists no `--health` flag.
3. The verify task's in-network /metrics curl asserting `node_cpu_seconds_total` is the authoritative readiness gate either way.

If a future UAT pass discovers `--health` actually works (Outcome A), flipping `node_exporter_healthcheck_test: ["CMD", "/bin/node_exporter", "--health"]` in inventory is a one-line operator change with no role restructure. If `--version` also doesn't work as a HEALTHCHECK (Outcome C), `node_exporter_healthcheck_enabled: false` flips the role to State.Running mode with the same one-line operator change.

## User Setup Required

None -- node_exporter has no auth surface, no vault keys (D-55), and no rendered config. Operator only needs the existing Phase-1 inventory and a Docker host.

## Next Phase Readiness

- node_exporter is in place for Plan 03-03 (Prometheus) to scrape at `http://node-exporter:9100/metrics` over the telemetron bridge -- the scrape config in Plan 03-03 will reference this hostname:port pair.
- The Phase-3 canonical role shape is now proven on a stateless, no-config role: subsequent Phase-3 plans (03-02 opentelemetry, 03-03 prometheus, 03-04 fluentbit) inherit the conditional-HEALTHCHECK omit-magic-value pattern, the D-10a poll + in-network verify combo, and the D-25-clean audit narrative.
- **Live UAT proof (deferred):** A fresh-from-Phase-2 homelab boot of `ansible-playbook --tags node_exporter` plus the two-back-to-back-runs `changed=0` idempotency check are documented in the success criteria but deferred to the Phase 3 verification stage (consistent with Phase 2 precedent).

## Self-Check: PASSED

**Files (7 created + 2 modified):**
- FOUND: roles/node_exporter/defaults/main.yml
- FOUND: roles/node_exporter/tasks/main.yml
- FOUND: roles/node_exporter/tasks/verify.yml
- FOUND: roles/node_exporter/handlers/main.yml
- FOUND: roles/node_exporter/meta/main.yml
- FOUND: roles/node_exporter/README.md
- FOUND: inventory/example-homelab/group_vars/all/node_exporter.yml
- FOUND: playbooks/deploy_docker.yml (node_exporter wired)
- FOUND: roles/README.md (node_exporter row ticked)
- FOUND: .planning/phases/03-ingest-plane/03-01-node-exporter-SUMMARY.md

**Commits (8 task commits):**
- FOUND: f78c22f (Task 1 scaffold)
- FOUND: 26d09e7 (Task 2 defaults)
- FOUND: 82d2dd2 (Task 3 tasks/main.yml)
- FOUND: 6b9e45a (Task 4 tasks/verify.yml)
- FOUND: e38d1cf (Task 5 handlers/main.yml)
- FOUND: 02b86e4 (Task 6 README + INSPQ-grep cleanup)
- FOUND: 589aad2 (Task 7 inventory + playbook wiring)
- FOUND: 2f74afa (Task 8 roles/README.md tick + gates)

**Plan metadata commit:** appended next.

---
*Phase: 03-ingest-plane*
*Completed: 2026-05-18*
