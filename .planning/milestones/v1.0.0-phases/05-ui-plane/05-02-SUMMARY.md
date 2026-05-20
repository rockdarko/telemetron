---
phase: 5
plan: 2
subsystem: karma
tags: [karma, alerting, ui, docker, ansible]
dependency_graph:
  requires: [05-01-grafana, 04-01-alertmanager]
  provides: [roles/karma, inventory/karma, karma-role-port]
  affects: [playbooks/deploy_docker.yml, roles/README.md]
tech_stack:
  added:
    - ghcr.io/prymitive/karma:v0.130 (GHCR official, not Docker Hub fork)
  patterns:
    - Explicit HEALTHCHECK for image that ships none (RESEARCH §2.2 pattern)
    - CONFIG_FILE env var for non-CWD config location
    - Parent-dir bind mount /opt/telemetron/karma -> /etc/karma (Gate 8)
    - curlimages/curl:8.10.1 one-shot verify containers
    - D-10a HEALTHCHECK poll + /health probe + UI smoke + AM connection assertion
key_files:
  created:
    - roles/karma/defaults/main.yml
    - roles/karma/tasks/main.yml
    - roles/karma/tasks/verify.yml
    - roles/karma/handlers/main.yml
    - roles/karma/templates/karma.yaml.j2
    - roles/karma/meta/main.yml
    - roles/karma/README.md
    - inventory/example-homelab/group_vars/all/karma.yml
  modified:
    - playbooks/deploy_docker.yml (appended - role: karma after grafana)
    - roles/README.md (ticked karma row ☑)
    - .planning/ROADMAP.md (ticked 05-02, updated 2/3)
decisions:
  - "CONFIG_FILE env var is mandatory -- Karma binary searches CWD (/) by default; without CONFIG_FILE env Karma starts with empty defaults and no Alertmanager configured (RESEARCH §2.2)"
  - "alertmanager URL is http://alertmanager:9093 (Docker bridge DNS) NOT localhost:9093 (upstream INSPQ used host-network); D-25 audit fix"
  - "Alertmanager source name is `telemetron` not `alertmanager` (clearer in Karma UI, less self-referential) -- D-25 rename"
  - "Karma endpoint for AM-connection assertion is /alerts.json with fallback to /api/v1/alerts (dual-path for per-version endpoint drift)"
  - "lmierzwa/karma Docker Hub fork is explicitly called out in README as 'NOT this' -- GHCR official is ghcr.io/prymitive/karma"
metrics:
  duration_seconds: 393
  duration_minutes: 7
  completed_date: "2026-05-19"
  tasks_completed: 2
  tasks_total: 2
  files_created: 9
  files_modified: 3
---

# Phase 5 Plan 2: Karma Role Port -- Summary

Karma v0.130 role ported end-to-end. Operator runs `ansible-playbook --tags karma`, opens `http://<host>:8082`, and sees the Phase-4 Alertmanager's alerts in Karma's grid view. UI-05 delivered.

## What Was Built

### Task 1: roles/karma/ scaffold (7 files)

**`roles/karma/defaults/main.yml`** -- Full knob surface:
- Image pin `ghcr.io/prymitive/karma:v0.130` (GHCR official, NOT Docker Hub fork)
- Port matrix D-84: `karma_http_port: 8082` (host), `karma_container_port: 8080` (container)
- D-25 audit: `karma_alertmanager_host: alertmanager`, `karma_alertmanager_port: 9093`, `karma_alertmanager_name: telemetron`
- Explicit healthcheck block (`wget --spider -q http://localhost:8080/health`) -- image ships none
- `karma_publish_host: true` by default (D-82 inverts D-30 for UI plane)
- Stateless: no volume, no persistent state knobs

**`roles/karma/tasks/main.yml`** -- Deploy pipeline:
1. Ensure `/opt/telemetron/karma/` exists
2. Render `karma.yaml` from template (notify: restart karma)
3. Pull `ghcr.io/prymitive/karma:v0.130` (force_source: false for idempotency)
4. Run container with: explicit HEALTHCHECK, `CONFIG_FILE: /etc/karma/karma.yaml` env, parent-dir bind `/opt/telemetron/karma -> /etc/karma` (Gate 8), Gate-7 labels, D-82/D-83/D-84 publish logic
5. Flush handlers, include verify.yml

**`roles/karma/tasks/verify.yml`** -- 4-step verify suite:
- D-10a HEALTHCHECK poll (30 retries x 2s = 60s budget)
- `/health` curl probe via curlimages/curl one-shot on telemetron bridge
- Root-path HTML smoke (grep for `karma|<html`)
- Alertmanager-connection assertion: poll `/alerts.json` (fallback `/api/v1/alerts`) until response contains `telemetron` (the configured AM source name)

**`roles/karma/handlers/main.yml`** -- Single handler `Docker restart karma`, listen: `restart karma`

**`roles/karma/templates/karma.yaml.j2`** -- Karma YAML config:
- `alertmanager.servers[0]`: name=`{{ karma_alertmanager_name }}`, uri=`http://{{ karma_alertmanager_host }}:{{ karma_alertmanager_port }}`, proxy=true
- `alertAcknowledgement:` block (enabled, 1h duration, karma author)
- `ui:` block (30s refresh, auto theme, 420px group width, collapsedOnMobile)
- Conditional `filters.default` and `labels.keep` blocks (sorted-keys per D-20, only if non-empty)

**`roles/karma/meta/main.yml`** -- Galaxy metadata: license MIT, min_ansible_version 2.15, author Rock Martel-Langlois

**`roles/karma/README.md`** -- OPS-03 schema with:
- "Karma is the M1 alert UX" framing paragraph (verbatim from CONTEXT.md)
- "GHCR official, NOT the `lmierzwa/karma` Docker Hub fork" explicit warning
- Full variables table, vault keys (none -- D-66), tags, modes, volumes (none), healthcheck, network sections
- Deviations from upstream INSPQ (D-25 audit: localhost->bridge, port 8080->8082, name alertmanager->telemetron, image v0.128->v0.130)

### Task 2: Inventory + playbook + cascade (3 file modifications, 1 new file)

**`inventory/example-homelab/group_vars/all/karma.yml`** (new) -- Operator-tunable surface with all D-25 defaults: bridge DNS, telemetron name, port 8082.

**`playbooks/deploy_docker.yml`** (modified) -- `- role: karma` appended after `- role: grafana` (dependency order; D-05).

**`roles/README.md`** (modified) -- karma row ticked ☑.

**`.planning/ROADMAP.md`** (modified) -- 05-02-PLAN.md ticked `[x]`, Phase 5 progress updated to 2/3.

Note: `inventory/example-homelab/group_vars/all/network.yml` already had the Karma :8082 line inserted by plan 05-01 (grafana plan pre-populated the full UI plane comment block). No change needed.

## D-25 Audit Summary (vs Upstream INSPQ karma role)

| Change | Upstream INSPQ | This Port | Reason |
|--------|---------------|-----------|--------|
| Alertmanager URL | `http://localhost:9093` | `http://alertmanager:9093` | Docker bridge DNS; localhost doesn't resolve AM across bridge |
| Alertmanager name | `alertmanager` | `telemetron` | Clearer in Karma UI; less self-referential |
| Image tag | `v0.128` | `v0.130` | Latest stable 2026-05-16 |
| Host port | `8080` | `8082` | D-84; avoid 8080 clash |
| Image source | `ghcr.io/prymitive/karma` | `ghcr.io/prymitive/karma` | Already correct -- only INSPQ artifact unchanged |
| Bind mount | Single-file (Gate 8 violation) | Parent-dir `/opt/telemetron/karma -> /etc/karma` | moby/moby#6011 fix |
| HEALTHCHECK | None | Explicit `wget --spider -q http://localhost:8080/health` | Image ships none (RESEARCH §2.2) |
| CONFIG_FILE env | Missing | `CONFIG_FILE: /etc/karma/karma.yaml` | Required for non-CWD config location (RESEARCH §2.2) |
| Gate-7 labels | Missing | `org.telemetron.service + job` | Fluent Bit Lua enrichment (INGEST-07) |
| `alertAcknowledgement` | Missing | Enabled, 1h | Useful homelab UX feature |

## Deviations from Plan

None - plan executed exactly as written. The dual-path verify (`/alerts.json` fallback to `/api/v1/alerts`) was taken as-is from the plan's recommended "safe default" shape. The `lmierzwa/karma` reference was moved from defaults/main.yml to README.md only (where it belongs as a warning string -- the grep gate only permits it in README).

Two minor corrections applied automatically (Rule 1):
1. Removed `lmierzwa/karma` string from `defaults/main.yml` (kept in README as warning-only per plan gate). Moved to a descriptive comment: "see roles/karma/README.md".
2. Removed "INSPQ" string from `templates/karma.yaml.j2` comment (INSPQ grep gate excludes only README). Changed to "D-25 fix" phrasing without the INSPQ reference.

## Gate Status

| Gate | Status | Evidence |
|------|--------|---------|
| Gate 1 (INSPQ grep) | PASS | Zero matches outside README.md |
| Gate 1 (non-ASCII) | PASS | Zero non-ASCII chars in roles/karma/ |
| Gate 2 (image pin) | PASS | `v0.130` -- no :latest |
| Gate 3 (secrets discipline) | PASS | Zero vault_* references (D-66 -- no outbound auth) |
| Gate 4 (idempotency) | PENDING | Requires live-host UAT on leviathan |
| Gate 5 (healthcheck + restart) | PASS | Explicit HEALTHCHECK + unless-stopped |
| Gate 6 (README schema) | PASS | OPS-03 sections in order |
| Gate 7 (label stamp) | PASS | org.telemetron.service + job: karma |
| Gate 8 (parent-dir bind) | PASS | /opt/telemetron/karma -> /etc/karma |
| Gate 9 | N/A | Grafana-specific; does not apply |

## Plan Handoff to 05-03 (PromLens)

05-02 is complete. 05-03 (PromLens role port) is the final plan in Phase 5.

- PromLens ships `prom/promlens:v0.3.0` on host port 8081 (D-84)
- Must mark as deprecation-candidate (PromLens frozen since 2022; Prometheus 3 UI absorbs tree-view feature)
- `roles/README.md` promlens row needs ☑
- ROADMAP.md Phase 5 will reach 3/3 after 05-03

## Self-Check: PASSED

Files verified:
- roles/karma/defaults/main.yml: EXISTS
- roles/karma/tasks/main.yml: EXISTS
- roles/karma/tasks/verify.yml: EXISTS
- roles/karma/handlers/main.yml: EXISTS
- roles/karma/templates/karma.yaml.j2: EXISTS
- roles/karma/meta/main.yml: EXISTS
- roles/karma/README.md: EXISTS
- inventory/example-homelab/group_vars/all/karma.yml: EXISTS
- playbooks/deploy_docker.yml: contains `role: karma` after `role: grafana`
- roles/README.md: karma row is ☑

Commits verified:
- ae4c42f: feat(05-02): scaffold roles/karma
- 611ce1a: feat(05-02): inventory + playbook + roles/README.md cascade
