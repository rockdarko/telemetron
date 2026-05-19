---
phase: 05-ui-plane
verified: 2026-05-19T16:30:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 10/12
  gaps_closed:
    - "Gate 1 non-ASCII gate passes for all three UI-plane roles (25 § chars removed from 8 non-README files in karma + promlens)"
    - "Dashboard JSONs have hardcoded telemetron datasource UIDs per D-77 -- _rewrite_uids.py key-form bug fixed, 207 previously-broken panel uid refs resolved, Gate 9.5 deployed"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Grafana up and datasource health checks pass"
    expected: "ansible-playbook --tags grafana on leviathan; docker inspect telemetron-grafana returns healthy; GET /api/datasources/uid/{prometheus,loki,tempo,mimir}/health all return {\"status\":\"OK\"}"
    why_human: "Requires live container; HEALTHCHECK timing and SQLite first-boot initialization cannot be verified statically"
  - test: "Dashboard panels render real data -- especially tempo-self-metrics upstream UID issue"
    expected: "All 7 dashboards open. otel-collector and mimir-self-metrics fully render with prometheus data. tempo-self-metrics: 23 panels with prometheus/loki hardcoded UIDs render correctly; 51 panels with upstream org UIDs (mimir-ops-03, cortex-ops-01, P666011C0B63BDCA4, P1809F7CD0C75ACF3 -- all prometheus-type) either fall back to the provisioned prometheus datasource or show 'Datasource not found'. If fallback works, note it as a warning; if panels error, document that tempo-self-metrics requires an additional uid_refs pass for upstream org UIDs."
    why_human: "Grafana runtime behavior for an unknown datasource UID (non-$ hardcoded random string) cannot be verified statically. The 51 panels are a pre-existing upstream issue not introduced by 05-04."
  - test: "Trace-to-logs correlation in Grafana Explore (UI-04)"
    expected: "Open a Tempo trace in Explore; click a span; Logs tab shows correlated Loki logs via tracesToLogsV2 + derivedFields trace_id"
    why_human: "Requires live OTel-instrumented traffic and a running trace to click through"
  - test: "Karma visible at host:8082 showing Alertmanager's alerts (UI-05)"
    expected: "docker inspect telemetron-karma shows healthy; http://<leviathan>:8082 loads Karma grid; Karma API response includes 'telemetron' as alertmanager source"
    why_human: "Requires live container; alert grid state is runtime-only"
  - test: "PromLens accessible at host:8081 with Prometheus tree view (UI-06)"
    expected: "docker inspect telemetron-promlens shows healthy; http://<leviathan>:8081 loads PromLens UI; PromQL expression tree renders against prometheus:9090"
    why_human: "Requires live container"
  - test: "Gate 4 idempotency for grafana, karma, promlens"
    expected: "Second back-to-back ansible-playbook --tags grafana,karma,promlens run reports changed=0 for all three roles"
    why_human: "Requires live host; cannot verify idempotency statically"
  - test: "Gate 9.5 fires correctly on leviathan"
    expected: "gate_9_5_ok appears in task output; task does not fail on any provisioned dashboard JSON"
    why_human: "Gate runs on the remote host against provisioned files; cannot verify without live container"
---

# Phase 5: UI Plane Verification Report

**Phase Goal:** Operator can run the playbook and have Grafana running with datasources explicitly provisioned at stable UIDs (`prometheus`, `loki`, `tempo`, `mimir`), 5-10 curated starter dashboards rendering real data on a fresh deploy, trace-to-logs correlation wired through Tempo's `tracesToLogsV2` + a derived `trace_id` field on Loki -- plus Karma running against Alertmanager and PromLens pinned to `v0.3.0` and marked deprecation-candidate in its role README. Grafana's datasource provisioning is the de-facto smoke test for everything that came before.
**Verified:** 2026-05-19T16:30:00Z
**Status:** human_needed
**Re-verification:** Yes -- after gap closure via 05-04 (non-ASCII regression + dashboard uid rewrite bug + Gate 9.5)

## Goal Achievement

Both gaps from the prior VERIFICATION.md are resolved in the codebase. All 12 must-haves verify statically. The remaining open items are runtime behaviors that require the live leviathan stack, plus one pre-existing upstream issue in `tempo-self-metrics.json` that needs UAT to classify.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Grafana OSS 13.0.1 is the pinned image | VERIFIED | `roles/grafana/defaults/main.yml`: `grafana_image_tag: "13.0.1"`, `grafana_image: grafana/grafana-oss` |
| 2 | Grafana admin password is vault-supplied, no default | VERIFIED | `defaults/main.yml` has no default for `grafana_admin_password`; `secrets.yml.example` has `grafana_admin_password: CHANGE_ME`; no `vault_` prefix (D-90 clean) |
| 3 | Grafana on named volume `telemetron_grafana_data` | VERIFIED | `grafana_data_volume: "{{ telemetron_volume_prefix }}_grafana_data"` in defaults; `docker_volume` task creates it |
| 4 | Four datasources provisioned at hardcoded UIDs | VERIFIED | `datasources.yaml.j2` has `uid: prometheus`, `uid: loki`, `uid: tempo`, `uid: mimir` explicitly at lines 12, 23, 42, 68 |
| 5 | Seven curated dashboards copied at deploy time | VERIFIED | `tasks/main.yml` copies all 7 JSON files; all 7 files confirmed on disk |
| 6 | Dashboard JSONs have hardcoded UIDs (D-77) | VERIFIED | `_rewrite_uids.py` key-form mismatch fixed (commit c70a540); 207 panels regenerated with hardcoded `{type,uid}` dicts (commit b096916); zero `$`-prefixed panel uid refs in all 7 dashboards confirmed by walker |
| 7 | tracesToLogsV2 + derivedFields wired (UI-04) | VERIFIED | `datasources.yaml.j2` line 50: `tracesToLogsV2:` block with `datasourceUid: loki`, `customQuery: true`; Loki datasource line 32: `derivedFields:` with `name: trace_id`, `datasourceUid: tempo` |
| 8 | Gate 1 non-ASCII passes for all three roles | VERIFIED | `LC_ALL=C grep -rPn '[^\x00-\x7F]' roles/karma roles/promlens roles/grafana --include='*.yml' ...` returns empty (exit 1); Python character scan confirms 0 § in all 8 non-README files (commit e97dbbd) |
| 9 | Karma image is ghcr.io/prymitive/karma:v0.130 | VERIFIED | `roles/karma/defaults/main.yml`: `karma_image: ghcr.io/prymitive/karma`, `karma_image_tag: "v0.130"` |
| 10 | Karma reads Alertmanager via Docker bridge DNS | VERIFIED | `templates/karma.yaml.j2` line 10: `uri: "http://{{ karma_alertmanager_host }}:{{ karma_alertmanager_port }}"` with `karma_alertmanager_host: alertmanager` |
| 11 | PromLens image is prom/promlens:v0.3.0 | VERIFIED | `roles/promlens/defaults/main.yml`: `promlens_image: prom/promlens`, `promlens_image_tag: "v0.3.0"` |
| 12 | PromLens README has deprecation banner | VERIFIED | `roles/promlens/README.md` line 3: `## DEPRECATION CANDIDATE`; `roles/README.md` shows `(deprecation candidate)` annotation |

**Score: 12/12 truths verified**

---

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `roles/grafana/defaults/main.yml` | VERIFIED | Image pin, publish_host:true, named volume, healthcheck, datasource URLs |
| `roles/grafana/tasks/main.yml` | VERIFIED | Config tree, 7 dashboard copies, named volume, set_fact mounts, docker_container, flush_handlers |
| `roles/grafana/tasks/verify.yml` | VERIFIED | Gates 1-9 plus Gate 9.5 (Step 10) added in commit 3c59b74; YAML valid |
| `roles/grafana/templates/datasources/datasources.yaml.j2` | VERIFIED | 4 UIDs hardcoded, tracesToLogsV2 block, derivedFields block, extra_datasources extension |
| `roles/grafana/templates/dashboards/dashboards.yaml.j2` | VERIFIED | Two-provider manifest (telemetron RO + operator writable) |
| `roles/grafana/files/dashboards/` (7 files) | VERIFIED | All 7 JSON files valid (python3 json.load passes); zero `$`-prefixed panel uid refs confirmed; see note on tempo-self-metrics upstream UIDs below |
| `roles/grafana/files/_rewrite_uids.py` | VERIFIED | Key-form bug fixed: `"$datasource"` (no braces), `"$ds"`, `"$logsds"` are correct forms; inline "Key form NOTE" comment documents the two-form convention |
| `roles/grafana/README.md` | VERIFIED | OPS-03 schema, tracesToLogsV2 framing |
| `inventory/example-homelab/group_vars/all/grafana.yml` | VERIFIED | publish_host, port, datasource URL knobs |
| `roles/karma/defaults/main.yml` | VERIFIED | Image pin correct, alertmanager bridge DNS vars, zero § chars |
| `roles/karma/tasks/main.yml` | VERIFIED | Docker container task, CONFIG_FILE env, zero § chars; YAML valid |
| `roles/karma/tasks/verify.yml` | VERIFIED | Gate tasks present, zero § chars; YAML valid |
| `roles/karma/templates/karma.yaml.j2` | VERIFIED | Alertmanager URI uses bridge DNS, zero § chars |
| `roles/karma/README.md` | VERIFIED | M1 alert UX framing, GHCR warning |
| `inventory/example-homelab/group_vars/all/karma.yml` | VERIFIED | karma_publish_host:true, alertmanager bridge DNS |
| `roles/promlens/defaults/main.yml` | VERIFIED | Image pin v0.3.0, prometheus_url, zero § chars |
| `roles/promlens/tasks/main.yml` | VERIFIED | `--web.default-prometheus-url` CLI flag present, zero § chars; YAML valid |
| `roles/promlens/tasks/verify.yml` | VERIFIED | Gate tasks present, zero § chars; YAML valid |
| `roles/promlens/meta/main.yml` | VERIFIED | Galaxy metadata, zero § chars |
| `roles/promlens/README.md` | VERIFIED | `## DEPRECATION CANDIDATE` at line 3, CLI-flag-only note |
| `inventory/example-homelab/group_vars/all/promlens.yml` | VERIFIED | promlens_publish_host:true, prometheus_url http://prometheus:9090 |
| `playbooks/deploy_docker.yml` | VERIFIED | grafana (line 63) -> karma (line 66) -> promlens (line 69) in correct order after alertmanager |
| `roles/README.md` | VERIFIED | grafana, karma, promlens all ticked with deprecation annotation on promlens |
| `.planning/ROADMAP.md` | VERIFIED | Phase 5 marked complete; 05-04-PLAN.md entry present with 4 plan commits |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `playbooks/deploy_docker.yml` | `roles/grafana/tasks/main.yml` | `- role: grafana` | WIRED | Line 63 |
| `playbooks/deploy_docker.yml` | `roles/karma/tasks/main.yml` | `- role: karma` | WIRED | Line 66 |
| `playbooks/deploy_docker.yml` | `roles/promlens/tasks/main.yml` | `- role: promlens` | WIRED | Line 69 |
| `datasources.yaml.j2` -> Tempo datasource | tracesToLogsV2 -> Loki | `datasourceUid: loki`, `customQuery: true` | WIRED | Lines 50-60 confirmed |
| `datasources.yaml.j2` -> Loki datasource | derivedFields -> Tempo | `datasourceUid: tempo`, `matcherType: label`, `name: trace_id` | WIRED | Lines 27-36 confirmed |
| `karma/templates/karma.yaml.j2` | `alertmanager:9093` | `uri: "http://{{ karma_alertmanager_host }}:{{ karma_alertmanager_port }}"` | WIRED | Line 10; bridge DNS not localhost |
| `karma/tasks/main.yml` | `/etc/karma/karma.yaml` | `CONFIG_FILE` env var | WIRED | `CONFIG_FILE: "{{ karma_config_container_path }}"` present |
| `promlens/tasks/main.yml` | `prometheus:9090` | `--web.default-prometheus-url` CLI flag | WIRED | Line 53: `"--web.default-prometheus-url={{ promlens_prometheus_url }}"` |
| `_rewrite_uids.py` uid_refs keys | panel datasource uid substitution | `"$datasource"`, `"$ds"`, `"$logsds"` without braces | WIRED | Commit c70a540 fixed key forms; commit b096916 verified 0 $ refs in all 3 regenerated dashboards |
| `roles/grafana/tasks/verify.yml` | Gate 9.5 regression guard | `grep -rE '"uid".*"\$[^"]+"'` on provisioned dashboards | WIRED | Step 10 added in commit 3c59b74; YAML valid |

---

### Data-Flow Trace (Level 4)

All data sources in this phase are Grafana provisioning files (static YAML/JSON read at container startup) and Ansible roles (pure declarative). No runtime data-fetching artifacts to trace. Gate 9.5 is the deploy-time regression guard -- its output can only be verified on leviathan.

---

### Behavioral Spot-Checks

Step 7b: SKIPPED -- no runnable entry points in this repo. Ansible roles execute on a remote host. Gate 9.5 (`roles/grafana/tasks/verify.yml` Step 10) is the behavioral check for the D-77 fix and runs automatically on leviathan during playbook execution.

YAML validation (static proxy for syntax correctness):
- `roles/grafana/tasks/verify.yml`: VALID
- `roles/karma/tasks/main.yml`: VALID
- `roles/karma/tasks/verify.yml`: VALID
- `roles/promlens/tasks/main.yml`: VALID
- `roles/promlens/tasks/verify.yml`: VALID

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| UI-01 | 05-01 | Grafana OSS 13.0.1 on :3000, SQLite on named volume, admin password from vault | SATISFIED | Image pin, named volume, GF_SECURITY_ADMIN_PASSWORD env, no default for grafana_admin_password |
| UI-02 | 05-01 | Datasources at explicit UIDs: prometheus, loki, tempo, mimir | SATISFIED | `datasources.yaml.j2` hardcoded UIDs at lines 12, 23, 42, 68 |
| UI-03 | 05-01 | 5-10 curated starter dashboards rendering real data | SATISFIED (static) | 7 dashboards present, all valid JSON, zero $-prefixed panel uid refs; runtime rendering pending UAT (see tempo-self-metrics upstream UID note) |
| UI-04 | 05-01 | tracesToLogsV2 on Tempo + derived trace_id field on Loki | SATISFIED | Template has full tracesToLogsV2 + Loki derivedFields; verify.yml steps 8-9 assert wiring at deploy time |
| UI-05 | 05-02 | Karma ghcr.io/prymitive/karma:v0.130 reading Alertmanager | SATISFIED (static) | Image pin correct, alertmanager bridge DNS wired, CONFIG_FILE env present; live verification pending |
| UI-06 | 05-03 | PromLens prom/promlens:v0.3.0, README deprecation banner | SATISFIED | Image pin correct, CLI flag wired, README line 3 is `## DEPRECATION CANDIDATE` |

All 6 requirement IDs (UI-01 through UI-06) are accounted for. No orphaned requirements.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `roles/grafana/files/dashboards/tempo-self-metrics.json` | 51 timeseries panels reference upstream org UIDs (`mimir-ops-03`, `cortex-ops-01`, `P666011C0B63BDCA4`, `P1809F7CD0C75ACF3`) -- all prometheus-type; UIDs don't exist in telemetron's provisioned datasources | WARNING | Pre-existing upstream issue in grafana/tempo v2.10.5's `tempo-operational.json` mixin; NOT introduced by 05-04. The SUBSTITUTIONS script handles template vars ($ds, $logsds) but not upstream hardcoded org UIDs. At runtime Grafana may fall back to the first prometheus-type datasource or show "Datasource not found" on those 51 panels. Requires UAT to classify as blocker vs. acceptable (51 of 74 panels). Gate 9.5 does not catch these because they are not $-prefixed. |

**Blocker count: 0 (both prior blockers resolved)**
**Warning count: 1 (tempo-self-metrics upstream UID issue -- pre-existing, not introduced by 05-04)**

---

### 05-04 Gap Closure Confirmation

**Gap 1 (non-ASCII Gate 1):** CLOSED.
- Commit e97dbbd replayed `§` -> `sec.` across all 8 non-README files in roles/karma/ and roles/promlens/
- Confirmed: `LC_ALL=C grep -rPn '[^\x00-\x7F]' roles/karma roles/promlens roles/grafana ...` returns empty (exit code 1)
- Python character scan: 0 § in all 8 files

**Gap 2 (dashboard uid rewrite bug):** CLOSED for its defined scope (template variable refs).
- Commit c70a540 fixed `_rewrite_uids.py` SUBSTITUTIONS keys from `${VAR}` to `$VAR` form
- Commit b096916 regenerated three dashboard JSONs; walker confirms 0 `$`-prefixed panel uid refs
- Commit 3c59b74 added Gate 9.5 to `roles/grafana/tasks/verify.yml` as a regression guard
- New finding: 51 panels in `tempo-self-metrics.json` reference upstream org UIDs -- pre-existing in the upstream source, out of scope for 05-04, requires UAT to determine runtime impact

---

### Human Verification Required

### 1. Grafana Datasource Health (Gate 9 Step 3)

**Test:** Run `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags grafana` on leviathan. After completion check `docker inspect telemetron-grafana --format '{{.State.Health.Status}}'` returns `healthy`. Then: `curl -su admin:$PASS http://leviathan:3000/api/datasources/uid/prometheus/health` (and same for loki, tempo, mimir).
**Expected:** All four return `{"message":"OK","status":"OK"}`.
**Why human:** Requires live container and actual backend services running.

### 2. Dashboard Panel Rendering -- tempo-self-metrics upstream UID issue

**Test:** Open Grafana at `http://leviathan:3000`. Navigate to the Telemetron dashboards folder. Open `Tempo Self-Metrics`. Check which panels render and which error.
**Expected:** 23 panels with `prometheus` and `loki` UIDs render correctly. For the 51 panels with upstream org UIDs (`mimir-ops-03`, `cortex-ops-01`, `P666011C0B63BDCA4`, `P1809F7CD0C75ACF3` -- all prometheus-type): either they fall back to the provisioned `prometheus` datasource and render data (acceptable workaround), or they show "Datasource not found" (requires adding these 4 UIDs as additional `uid_refs` entries in `_rewrite_uids.py` and regenerating the dashboard). Also check `OTel Collector Self-Metrics` and `Mimir Self-Metrics` -- both should render fully with prometheus data.
**Why human:** Grafana's runtime behavior for an unknown non-variable datasource UID cannot be determined statically.

### 3. Gate 9.5 Fires Correctly

**Test:** During the grafana playbook run, watch the task output for Step 10 `Gate 9.5 -- assert no provisioned dashboard has unresolved $datasource panel refs`.
**Expected:** Task completes with `gate_9_5_ok` in the output and `changed=false`. Task does NOT fail.
**Why human:** Gate runs on the remote host against provisioned files in the container's volume mount; cannot verify without live execution.

### 4. Trace-to-Logs Correlation (UI-04)

**Test:** Open Grafana Explore -> Tempo datasource -> run a trace search. Click a trace -> click a span -> check the `Logs` tab.
**Expected:** Loki logs correlated by `trace_id` appear in the Logs tab (confirming tracesToLogsV2 + derivedFields wiring is live).
**Why human:** Requires live OTel-instrumented traffic generating traces with trace_id labels.

### 5. Karma Alert Grid (UI-05)

**Test:** Open `http://leviathan:8082` in a browser. Also run `docker inspect telemetron-karma --format '{{.State.Health.Status}}'`.
**Expected:** Karma loads its grid UI. `docker inspect` returns `healthy`. Karma's `/alerts.json` response body contains the string `telemetron` (the configured alertmanager source name).
**Why human:** Requires live container; alert presence depends on stack state.

### 6. PromLens Query Editor (UI-06)

**Test:** Open `http://leviathan:8081` in a browser.
**Expected:** PromLens PromQL editor loads with Prometheus at `http://prometheus:9090` pre-configured as the default backend. Enter `up` and check the expression tree renders.
**Why human:** Requires live container; CLI flag `--web.default-prometheus-url` requires a reachable Prometheus.

### 7. Gate 4 Idempotency

**Test:** Run `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags grafana,karma,promlens` twice back-to-back.
**Expected:** Second run reports `changed=0` for all three roles.
**Why human:** Requires live host.

---

### Gaps Summary

No unresolved static gaps. Both prior blockers are closed:

- Gap 1 (non-ASCII § in karma + promlens): 25 occurrences removed across 8 files in commit e97dbbd. Gate 1 scan returns empty.
- Gap 2 (dashboard uid rewrite key-form bug): `_rewrite_uids.py` SUBSTITUTIONS keys corrected in commit c70a540. Three dashboards regenerated in commit b096916 with 207 previously-broken panel uid refs now hardcoded. Gate 9.5 regression guard wired in commit 3c59b74.

One pre-existing upstream issue identified (not a regression from 05-04):
- `tempo-self-metrics.json` contains 51 timeseries panels with hardcoded org-specific UIDs from the grafana/tempo v2.10.5 mixin that will not match telemetron's provisioned datasources at runtime. All 51 are prometheus-type. Runtime behavior (fallback vs. error) requires UAT on leviathan. If panels error: add the 4 UIDs to `_rewrite_uids.py` SUBSTITUTIONS for tempo and regenerate. If panels fall back to the provisioned `prometheus` datasource: document as acceptable upstream limitation. This is flagged as a WARNING, not a blocker, because the D-77 and Gate 9.5 scope was specifically `$`-prefixed variable refs.

Phase 5 static verification is complete. Proceed with UAT on leviathan to close the human_needed items above.

---

_Verified: 2026-05-19T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
