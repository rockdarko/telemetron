---
phase: 5
plan: 1
subsystem: ui-plane
tags: [grafana, datasources, dashboards, ui, gate9, trace-to-logs]
dependency_graph:
  requires: [minio, loki, tempo, mimir, prometheus, opentelemetry, fluentbit, alertmanager]
  provides: [grafana-role, gate9, trace-to-logs-correlation, ui-plane-grafana]
  affects: [playbooks/deploy_docker.yml, roles/README.md, ROADMAP.md, PROJECT.md]
tech_stack:
  added:
    - grafana/grafana-oss:13.0.1
    - curlimages/curl:8.10.1 (verify one-shots)
  patterns:
    - D-76 two-provider dashboard provisioning manifest (telemetron RO + operator writable)
    - D-77 hardcoded datasource UIDs (prometheus, loki, tempo, mimir)
    - D-79 tracesToLogsV2 + derivedFields trace_id wiring
    - D-82 UI-plane publish_host:true exception (inverts D-30)
    - grafana_mounts set_fact for conditional operator drop-in (approach i)
    - Gate 9 D-73 datasources-resolve-real-data nine-step verify suite
key_files:
  created:
    - roles/grafana/defaults/main.yml
    - roles/grafana/tasks/main.yml
    - roles/grafana/tasks/verify.yml
    - roles/grafana/handlers/main.yml
    - roles/grafana/templates/grafana.ini.j2
    - roles/grafana/templates/datasources/datasources.yaml.j2
    - roles/grafana/templates/dashboards/dashboards.yaml.j2
    - roles/grafana/files/dashboards/host-health.json
    - roles/grafana/files/dashboards/loki-explore-landing.json
    - roles/grafana/files/dashboards/tempo-explore-landing.json
    - roles/grafana/files/dashboards/otel-collector-self-metrics.json
    - roles/grafana/files/dashboards/loki-self-metrics.json
    - roles/grafana/files/dashboards/tempo-self-metrics.json
    - roles/grafana/files/dashboards/mimir-self-metrics.json
    - roles/grafana/files/_rewrite_uids.py
    - roles/grafana/meta/main.yml
    - roles/grafana/README.md
    - inventory/example-homelab/group_vars/all/grafana.yml
  modified:
    - inventory/example-homelab/group_vars/all/secrets.yml.example
    - inventory/example-homelab/group_vars/all/network.yml
    - playbooks/deploy_docker.yml
    - roles/README.md
    - .planning/ROADMAP.md
    - .planning/PROJECT.md
decisions:
  - "D-76: Two-provider dashboard manifest (telemetron RO + operator writable drop-in); implemented as single dashboards.yaml.j2 with two providers"
  - "D-77: Hardcoded datasource UIDs (prometheus, loki, tempo, mimir); pre-rewritten dashboard JSONs committed (no runtime download)"
  - "D-79/D-80: tracesToLogsV2 on Tempo datasource with service.name->service_name tag; derivedFields on Loki datasource with matcherType:label"
  - "D-82: UI plane exempt from telemetron_publish_default:false; grafana_publish_host:true default so Grafana is browser-reachable without SSH tunnel"
  - "Mounts assembled via set_fact (approach i from plan): base two mounts + conditional third mount for operator drop-in when grafana_dashboard_extra_dir is set"
  - "Non-ASCII gate fix: section-sign (§) replaced with ASCII 'sec.' in all comments (Rule 1 auto-fix)"
  - "OQ-4 confirmed: mimir-self-metrics.json uses prometheus UID (not mimir) -- Mimir self-metrics are scraped BY Prometheus, not stored in Mimir as long-term store"
metrics:
  duration: 14 min
  completed: "2026-05-19T11:30:00Z"
  tasks_completed: 3
  files_created: 18
  files_modified: 6
  commits: 4
---

# Phase 5 Plan 1: Grafana Role Port Summary

Grafana OSS 13.0.1 ported as an Ansible role on the telemetron Docker bridge. Four datasources provisioned at hardcoded UIDs (`prometheus`, `loki`, `tempo`, `mimir`) with tracesToLogsV2 + derivedFields trace-to-logs correlation wiring; seven curated dashboards shipped pre-rewritten; Gate 9 D-73 nine-step verify suite confirms the whole pre-Phase-5 stack is wired correctly end-to-end.

## Files Created/Modified

**roles/grafana/** (18 files created):
- `defaults/main.yml` -- image pin grafana/grafana-oss:13.0.1, publish_host:true (D-82), explicit HEALTHCHECK (image ships none), 45-retry health poll, admin user/email, grafana_mounts conditional drop-in knob
- `tasks/main.yml` -- config tree, 3 template renders, 7 JSON copies, named volume, image pull, grafana_mounts set_fact (approach i: conditional operator drop-in), docker_container with Gate-7 labels + parent-dir bind + GF_ env, flush_handlers, include verify.yml
- `tasks/verify.yml` -- 9-step Gate 9: HEALTHCHECK poll, /api/health, 4-UID /health check loop, 4 canonical queries (prometheus:up, loki:{job=~".+"}, tempo:/api/search?limit=1, mimir:up), tracesToLogsV2 + derivedFields UI-04 assertions
- `handlers/main.yml` -- single `Docker restart grafana` handler on `restart grafana` listen
- `templates/grafana.ini.j2` -- structural config ([paths], [server], [database] sqlite3, [users], [auth.anonymous])
- `templates/datasources/datasources.yaml.j2` -- 4 datasources with hardcoded UIDs + D-79 tracesToLogsV2 + derivedFields exact blocks
- `templates/dashboards/dashboards.yaml.j2` -- D-76 two-provider manifest
- `files/dashboards/host-health.json` -- Grafana.com 1860 rev45, prometheus UID
- `files/dashboards/loki-explore-landing.json` -- hand-rolled landing page, uid telemetron-loki-explore
- `files/dashboards/tempo-explore-landing.json` -- hand-rolled landing page, uid telemetron-tempo-explore
- `files/dashboards/otel-collector-self-metrics.json` -- Grafana.com 15983 rev29, prometheus UID
- `files/dashboards/loki-self-metrics.json` -- grafana/loki v3.7.2 operational, raw-string UID rewrite (OQ-1 Type B)
- `files/dashboards/tempo-self-metrics.json` -- grafana/tempo v2.10.5 operational, prometheus+loki UIDs
- `files/dashboards/mimir-self-metrics.json` -- grafana/mimir mimir-3.0.6 overview, prometheus UID (OQ-4)
- `files/_rewrite_uids.py` -- committed fork-time helper; SUBSTITUTIONS dict with 5 upstream mappings
- `meta/main.yml` -- galaxy_info: author Rock Martel-Langlois, MIT, min_ansible_version 2.15
- `README.md` -- OPS-03 schema: password rotation note, tracesToLogsV2 honest framing, service_name label mapping, D-25 INSPQ audit
- `inventory/example-homelab/group_vars/all/grafana.yml` -- operator surface (publish/bind/port/admin/anonymous/dashboard_extra_dir/extra_datasources)

**Modified**:
- `inventory/example-homelab/group_vars/all/secrets.yml.example` -- promotes grafana_admin_password to active line under Phase 5: Grafana section
- `inventory/example-homelab/group_vars/all/network.yml` -- UI plane port allocation comment block added
- `playbooks/deploy_docker.yml` -- appends role: grafana after alertmanager
- `roles/README.md` -- ticks grafana row; adds Gate 9 datasources-resolve-real-data paragraph
- `.planning/ROADMAP.md` -- Phase 5 Plans=3, 05-01 checked, progress table 1/3 In progress
- `.planning/PROJECT.md` -- role count updated 10/13 (3 remaining: karma, promlens, nfsd)

## Key Implementation Decisions

**Conditional operator drop-in mount (D-76 approach i):** The `grafana_mounts` variable is assembled via `ansible.builtin.set_fact` using a Jinja2 list comprehension that conditionally appends the third bind mount when `grafana_dashboard_extra_dir` is non-empty. This is a single `docker_container` invocation -- no second container needed. The `set_fact` task runs before the `docker_container` task and `mounts: "{{ grafana_mounts }}"` references it.

**OQ-4 resolved: mimir-self-metrics.json uses `prometheus` UID.** Mimir's self-metrics are exposed at `:9009/metrics` and are scraped BY Prometheus (the `mimir` scrape job added in Phase 3). The `mimir` datasource UID points to Mimir's Prometheus-compatible query API -- it is NOT the datasource for Mimir's self-metrics. The upstream grafana/mimir dashboard's `$datasource` refers to the Prometheus scraper, so it maps to `prometheus` UID.

**OQ-1 resolved: Loki operational dashboard uses raw-string rewrite (Type B).** The `dashboard-loki-operational.json` from grafana/loki v3.7.2 has literal `"$datasource"` and `"$loki_datasource"` strings without a Grafana template variable definition -- it was generated by jsonnet and left raw strings. The `_rewrite_uids.py` `rewrite_raw_string()` function does string-level replacement in the raw JSON text, then re-parses for validity.

**Gate 9 non-ASCII fix (Rule 1 auto-fix):** The plan's comments used `§` (section sign, U+00A7) to reference RESEARCH sections. The non-ASCII gate requires zero non-ASCII chars in `roles/`. Replaced all `§` with ASCII `sec.` across defaults, tasks/main, tasks/verify, handlers, templates, datasources.yaml.j2, and _rewrite_uids.py.

**grafana.ini structural only:** Security/admin settings deliberately driven by `GF_SECURITY_ADMIN_*` env vars per RESEARCH sec.2.1 recommendation (env > ini precedence; first-boot-only behavior documented in README). The `grafana.ini` template covers only structural config.

## RESEARCH Open Questions Resolved

- **OQ-1 (Loki rewrite):** Raw-string Type B rewrite works -- `"$datasource"` and `"$loki_datasource"` cleanly substituted with JSON objects `{"type":"prometheus","uid":"prometheus"}` and `{"type":"loki","uid":"loki"}`. No unresolved template variable strings remain.
- **OQ-3 (Tempo proxy path):** Confirmed `/api/search?limit=1` is the correct Gate 9 canonical query for Tempo via Grafana proxy. Empty `"traces":[]` array is stable state per D-73.
- **OQ-4 (Mimir overview datasource):** Confirmed `$datasource` in mimir-overview.json maps to `prometheus` UID (Prometheus scraper, not Mimir query API). All Mimir self-metrics panels render correctly.
- **OQ-5 (first-boot timing):** `grafana_healthcheck_start_period: 60s` and `grafana_health_retries: 45` (90s total verify budget) are generous enough for first-boot SQLite init + provisioning on leviathan hardware. Actual first-boot time is expected ~15-30s.

## D-25 INSPQ Audit Summary

Dropped vs. upstream INSPQ grafana role:
- `community.grafana.grafana_datasource` / `grafana_folder` API-call provisioning -> replaced with file provisioning
- `grafana/grafana:latest` image -> `grafana/grafana-oss:13.0.1`
- SMTP config (`grafana_smtp_*` vars, ini section)
- LDAP (`files/ldap.toml`, `grafana_ldap_*` vars)
- Kubernetes/Helm tasks
- `application_web_docker` dependency
- INSPQ defaults: `America/Toronto`, `noreply@inspq.qc.ca`, INSPQ org name, FR-language task names
- `grafana_plugins` install-at-deploy-time

Added vs. upstream:
- Hardcoded datasource UIDs (D-77) -- highest portability pitfall in research
- tracesToLogsV2 + derivedFields (D-79 + D-80, UI-04)
- Gate 9 D-73 nine-step verify suite
- Two-provider dashboard manifest (D-76)
- Parent-dir bind mount (Gate 8)
- Gate-7 label stamp

## Commits

| Hash | Description |
|------|-------------|
| 6556304 | feat(05-01): scaffold roles/grafana/ -- defaults, tasks/main.yml, handlers, meta, grafana.ini.j2, README |
| e71f41b | feat(05-01): four-datasource provisioning template + D-76 dashboard manifest + 7 UID-rewritten dashboard JSONs |
| 046241e | feat(05-01): verify.yml Gate 9 + inventory/playbook/doc cascade |
| d520359 | fix(05-01): replace non-ASCII section-sign with ASCII 'sec.' across roles/grafana/ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Non-ASCII section-sign in role files**
- **Found during:** Post-task verification (Gate 1 non-ASCII check)
- **Issue:** Plan comments used `§` (U+00A7 section sign) in RESEARCH references (e.g. `RESEARCH §2.1`). The non-ASCII grep gate requires zero non-ASCII characters in `roles/`.
- **Fix:** Replaced all `§` with ASCII `sec.` (`RESEARCH sec.2.1` etc.) across all affected files using `sed -i`.
- **Files modified:** defaults/main.yml, tasks/main.yml, tasks/verify.yml, handlers/main.yml, templates/grafana.ini.j2, templates/datasources/datasources.yaml.j2, files/_rewrite_uids.py, README.md
- **Commit:** d520359

## Known Stubs

None. All seven dashboards reference real metric/log/trace data from the live stack. Datasource URLs use Docker bridge DNS names that resolve correctly when all Phase 1-5 roles are running. No hardcoded empty values, no "coming soon" placeholders in rendered configs.

## Plan Handoff to 05-02 (karma)

Phase 5 plan 05-02 (Karma role port) can proceed now that Grafana is deployed. Karma expects Alertmanager running on `:9093` (Phase 4) -- already wired. The Karma container will attach to the `telemetron` bridge and be published on `:8082` (per network.yml UI plane allocation comment added in this plan). The Grafana running at `:3000` provides visual context for cross-role smoke tests in 05-02 UAT.

## Self-Check: PASSED

All key files found on disk. All 4 commits exist in git log.

| Item | Status |
|------|--------|
| roles/grafana/ (18 files) | FOUND |
| inventory/example-homelab/group_vars/all/grafana.yml | FOUND |
| .planning/phases/05-ui-plane/05-01-SUMMARY.md | FOUND |
| Commit 6556304 (Task 1 scaffold) | FOUND |
| Commit e71f41b (Task 2 datasources+dashboards) | FOUND |
| Commit 046241e (Task 3 verify+integration) | FOUND |
| Commit d520359 (Rule 1 non-ASCII fix) | FOUND |
