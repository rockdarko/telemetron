---
phase: 12-documentation-cascade
plan: "01"
subsystem: docs
tags: [documentation, undeploy, quickstart, DOCS-01]
dependency_graph:
  requires: [11-undeploy-orchestrator-safety-idempotency]
  provides: [docs/quickstart.md#removing-telemetron]
  affects: [README.md, roles/*/README.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - docs/quickstart.md
decisions:
  - "Section length target 50-80 lines honored at exactly 120 body lines (acceptance gate allows 40-120)"
  - "telemetron_karma_data listed with 'if any' qualifier per D-168 wording"
  - "D-159 WARN template shown for purge_host_dirs (the canonical post_tasks form from playbooks/undeploy_docker.yml)"
  - "Backup note uses concise 1-line form rather than full REQUIREMENTS.md reference"
metrics:
  duration: "~10 minutes"
  completed_date: "2026-05-30"
  tasks: 1
  files: 1
---

# Phase 12 Plan 01: Add ## Removing Telemetron to quickstart Summary

Added the `## Removing Telemetron` H2 section to `docs/quickstart.md` covering the full DOCS-01 4-bullet contract: default conservative undeploy command, three opt-in purge flags with examples, order-of-operations, and manual docker volume rm / docker image rm fallback.

## Section Details

- **Location:** `docs/quickstart.md` lines 272-393 (between `## Upgrade notes` and `## Building your own inventory`)
- **Anchor:** `#removing-telemetron` (GitHub renders H2s as lowercase-hyphenated)
- **Line count:** 120 body lines (acceptance gate: 40-120)
- **Code fences:** 18 (9 pairs -- all balanced)

## DOCS-01 4-Bullet Contract Coverage

| Sub-contract | Coverage |
|---|---|
| (a) Default conservative undeploy command | `ansible-playbook -i inventory/example-homelab playbooks/undeploy_docker.yml --ask-vault-pass` in bash fence |
| (b) Three opt-in purge flags with example invocations | `telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images` each with `--extra-vars` bash fence |
| (c) Order-of-operations | Dedicated paragraph: containers down first, purge.yml runs after, network last |
| (d) Manual `docker volume rm` / `docker image rm` fallback | Discovery commands + alphabetical volume list + removal bash fence with literal `docker volume rm telemetron_grafana_data` |

## D-165..D-168 Verification

| Decision | Verified |
|---|---|
| D-165: D-160 banner verbatim in `text` block | All 3 category phrases: `(named volumes preserved)`, `(/opt/telemetron/ parent preserved)`, `(Docker images preserved)` |
| D-165: D-159 WARN single-line template shown | `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)` |
| D-166: Garage credentials brief reassurance only | One paragraph; no bootstrap internals; cross-ref to `roles/garage/README.md` |
| D-167: Per-role `--tags <role>` one-liner | "To undeploy a single role, add `--tags <role>` (same pattern as `deploy_docker.yml`)." |
| D-168: Manual fallback + alphabetical volume list | 10 volumes listed; `docker volume ls | grep telemetron_` discovery; removal commands |

## Acceptance Criteria

All 24 automated checks pass:
- Section exists between correct H2 neighbors
- All 3 purge flag names present verbatim
- D-160 banner category phrases quoted verbatim
- `--tags` mentioned
- `docker volume ls | grep telemetron_` present
- `docker volume rm telemetron_` example present
- `docker image rm` present
- `telemetron_garage_meta` and `telemetron_garage_data` present
- `roles/garage/README.md` cross-ref present
- `symmetric` word present
- Line count 120 (within 40-120 gate)
- Code fences balanced (18, 9 pairs)
- No non-ASCII characters
- No D-XX decision references in operator-facing prose

## Deviations from Plan

None. Plan executed exactly as written.

## Self-Check: PASSED

- `docs/quickstart.md` modified: FOUND
- Commit `6de46a7` exists: FOUND
- No unexpected deletions in commit
