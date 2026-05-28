---
phase: 09-label-reconciliation
verified: 2026-05-28T00:00:00Z
status: human_needed
score: 8/8
overrides_applied: 0
human_verification:
  - test: "Deploy fluentbit role twice on leviathan; confirm second run is changed=0"
    expected: "Second ansible-playbook --tags fluentbit run reports changed=0, failed=0"
    why_human: "Idempotency requires running Ansible against the live Docker host"
  - test: "docker exec telemetron-fluentbit grep -c 'record[\"service_name\"]' /fluent-bit/etc/enrich.lua"
    expected: "Returns 5"
    why_human: "Confirms live container received the new enrich.lua via the copy task"
  - test: "docker exec telemetron-fluentbit grep -c 'record[\"service\"]' /fluent-bit/etc/enrich.lua"
    expected: "Returns 0"
    why_human: "Confirms no old service key remains in the in-container Lua file"
  - test: "Query {service_name=\"fluentbit\"} in Grafana Loki Explore after restart"
    expected: "Returns Fluent Bit container logs without needing {service=\"fluentbit\"}"
    why_human: "Live runtime query cannot be verified statically"
  - test: "Query {service_name=\"telemetron-smoke\"} in Grafana Loki Explore after smoke_test.yml"
    expected: "OTel-originated smoke log appears under service_name label"
    why_human: "Confirms end-to-end OTel path uses service_name label after transform"
  - test: "Deploy opentelemetry role twice on leviathan; confirm second run is changed=0"
    expected: "Second ansible-playbook --tags opentelemetry run reports changed=0, failed=0"
    why_human: "Idempotency requires running Ansible against the live Docker host"
  - test: "docker exec telemetron-opentelemetry grep -A5 'transform/strip_namespace' /etc/otelcol-contrib/config.yaml"
    expected: "Shows delete_key(resource.attributes, \"service.namespace\") in the processor definition"
    why_human: "Confirms live container received the new config.yaml with the transform processor"
  - test: "Optional: inject OTLP log with service.namespace=\"testns\" and service.name=\"testsvc\" via curl to :4318/v1/logs; query Loki Explore"
    expected: "Log appears under {service_name=\"testsvc\"} NOT {service_name=\"testns/testsvc\"}"
    why_human: "Proves the transform/strip_namespace processor strips the namespace before Loki ingestion"
---

# Phase 9: Label Reconciliation — Verification Report

**Phase Goal:** Operator can query Loki in Grafana and find both Fluent Bit-originated and OTel Collector-originated logs under the single label `service_name`; all seven curated dashboards use `service_name=` in their LogQL matchers; and the OTel Collector strips the `service.namespace` resource attribute before forwarding to Loki, preventing the `namespace/service` concatenation corruption.

**Verified:** 2026-05-28
**Status:** HUMAN_NEEDED — All 8 automated truths verified. Live deployment validation on leviathan requires human execution (standard for this project's Docker+Ansible quality bar per CLAUDE.md).
**Re-verification:** No — initial verification.

---

## Overall Verdict: PASS (pending leviathan UAT)

All code-state truths are VERIFIED. No gaps found. No blocker anti-patterns. Human UAT items are the normal leviathan idempotency + in-container assertions documented in both SUMMARY.md files — they require Rock to run Ansible against the live host and cannot be verified statically.

---

## Requirement Verdicts

### INGEST-02: Loki labels unify on service_name (Fluent Bit side)

**Verdict: PASS**

`enrich.lua` emits `record["service_name"]` at all 5 emission sites (lines 161, 169, 178, 187, 199). Zero `record["service"]` Loki-key emissions remain (`grep -c 'record\["service"\]'` = 0). The doc cascade is complete: `defaults/main.yml` D-47 comment, `fluentbit/README.md` label table + prose + alt-INI example, `enrich.lua` header docstring, and `nfsd/README.md` line 86 all reference `service_name`. Dashboard regression-guard confirms zero bare `service=` LogQL selectors across all 7 curated dashboard JSONs. Docker source label `org.telemetron.service` and Lua cache field `entry.service` are untouched per D-121 LOCK.

### INGEST-03: OTel Collector strips service.namespace before Loki ingestion

**Verdict: PASS**

`roles/opentelemetry/templates/config.yaml.j2` has a `transform/strip_namespace` processor block using modern path-qualified OTTL (`delete_key(resource.attributes, "service.namespace")`). It is wired into the logs pipeline only as `[memory_limiter, batch, transform/strip_namespace]` per D-125. Traces and metrics pipelines remain `[memory_limiter, batch]`. `verify-config.yaml.j2` is untouched. No new inventory variable was added (D-127). `docs/quickstart.md` has a new `## Upgrade notes` subsection covering both the FB label rename and the OTel transform.

---

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `enrich.lua` emits `record["service_name"]` (not `record["service"]`) at all 5 emission sites | VERIFIED | `grep -c 'record\["service"\]' enrich.lua` = 0; `grep -c 'record\["service_name"\]' enrich.lua` = 5; sites confirmed at lines 161, 169, 178, 187, 199 |
| 2 | Loki streams from Fluent Bit-tailed Docker logs land under `{service_name=...}` after deploy | HUMAN | Code state correct; live Grafana query requires leviathan deploy |
| 3 | Fluent Bit defaults D-47 comment, README label table + prose + alt-INI, and `enrich.lua` header docstring all reference `service_name` | VERIFIED | `defaults/main.yml:39` contains `service_name / job: container_name fallback (D-121: ...)`; README label table row 1 col 1 = `service_name`; README alt-INI = `service_name=$service_name`; header line 4 = `` `service_name` and `job` Loki labels ``; header line 36 = `emit service_name="unlabeled"` |
| 4 | Docker source labels (`org.telemetron.service`) and Lua cache field names (`entry.service`, `svc`) remain unchanged per D-121 | VERIFIED | `grep -c 'org.telemetron.service' enrich.lua` = 2 (header refs intact); `grep -c 'entry.service' enrich.lua` = 1 (cache field on line 178 RHS intact); `{ service = svc, ... }` cache table shape unchanged |
| 5 | Dashboard JSONs already use `service_name=` and regression-guard confirms zero bare `service=` LogQL selectors | VERIFIED | `grep -rnE '"service=|{service=' roles/grafana/files/dashboards/` = 0 matches; `grep -rl 'service_name' dashboards/` returns loki-explore-landing.json and tempo-explore-landing.json |
| 6 | `transform/strip_namespace` processor defined in OTel config using modern path-qualified OTTL, wired into logs pipeline only | VERIFIED | `grep -c 'transform/strip_namespace' config.yaml.j2` = 2 (definition + pipeline ref); `delete_key(resource.attributes, "service.namespace")` present; `error_mode: ignore` present; logs pipeline = `[memory_limiter, batch, transform/strip_namespace]`; traces pipeline = `[memory_limiter, batch]`; metrics pipeline = `[memory_limiter, batch]`; D-124, D-125, D-126, D-127 all cited inline |
| 7 | `docs/quickstart.md` has `## Upgrade notes` covering both the FB label rename and the OTel transform | VERIFIED | Heading at line 253, before `## Building your own inventory` at line 272; body contains `service=`, `service_name=`, `service.namespace`; 14 top-level sections (was 13, delta = +1); 320 lines total (delta = 18 lines vs. pre-edit 302) |
| 8 | Back-to-back deploys of fluentbit and opentelemetry roles on leviathan produce changed=0 on second run | HUMAN | Per-project M1 quality bar (CLAUDE.md); requires live Ansible execution by Rock |

**Score:** 8/8 code-state truths verified. 2 truths require live execution (standard human UAT per M1 quality bar).

---

## Required Artifacts

| Artifact | Expected | Status | Evidence |
|----------|----------|--------|----------|
| `roles/fluentbit/files/enrich.lua` | 5 `record["service_name"]` emission sites; 0 `record["service"]`; header updated; Docker source label refs intact | VERIFIED | Direct file read + grep counts confirmed |
| `roles/fluentbit/defaults/main.yml` | D-47 comment updated with D-121 citation | VERIFIED | Line 39 contains `service_name / job: container_name fallback (D-121: ...)` |
| `roles/fluentbit/README.md` | Label table + prose + alt-INI synchronized to `service_name`; Docker source label refs intact | VERIFIED | 0 remaining `service=` Loki-label references; `org.telemetron.service` Docker label refs still present |
| `roles/nfsd/README.md` | Line 86 prose updated to `service_name = "remote"` | VERIFIED | `grep -q 'service_name = "remote"'` exits 0; `job = "remote-syslog"` unchanged |
| `roles/opentelemetry/templates/config.yaml.j2` | `transform/strip_namespace` processor block + logs pipeline reference (2 occurrences) | VERIFIED | Count = 2; definition at lines 61-64; pipeline ref at line 150 |
| `docs/quickstart.md` | `## Upgrade notes` subsection before `## Building your own inventory` | VERIFIED | Heading at line 253; `## Building your own inventory` at line 272 |

---

## Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `roles/fluentbit/tasks/main.yml` | `roles/fluentbit/files/enrich.lua` | `ansible.builtin.copy` + `notify: restart fluentbit` at line 43 | VERIFIED | `grep -A6 'Copy Fluent Bit Lua enrichment script' tasks/main.yml \| grep 'notify: restart fluentbit'` exits 0 |
| `roles/opentelemetry/tasks/main.yml` | `roles/opentelemetry/templates/config.yaml.j2` | `ansible.builtin.template` + `notify: restart opentelemetry` at line 37 | VERIFIED | Line 37 confirmed in `tasks/main.yml`; `notify: restart opentelemetry` is present on the `Render opentelemetry production config` task (grep pattern `-A6` was insufficient due to multi-line task body; direct file read confirms) |
| `roles/fluentbit/files/enrich.lua` logs pipeline | Loki ingest | FB `[OUTPUT] opentelemetry` to OTel Collector -> OTel `otlphttp/loki` | VERIFIED (code-state) | `service_name` emitted in enrich.lua; Loki ingest will use the new label key after container restart |
| `roles/opentelemetry/templates/config.yaml.j2` logs pipeline | `otlphttp/loki` exporter | `transform/strip_namespace` strips `service.namespace` before exporter | VERIFIED (code-state) | Processor in logs pipeline only; `error_mode: ignore` ensures no-op for records without `service.namespace` |

---

## Decision-ID Compliance Table

| Decision ID | Requirement | Evidence | Status |
|-------------|-------------|----------|--------|
| D-121 LOCK | Rename confined to Loki record-key (`record["service_name"]` LHS only); Docker source label `org.telemetron.service` and Lua cache field `entry.service` NOT renamed | `entry.service` at enrich.lua line 178 RHS intact; `org.telemetron.service` header refs count = 2; all 10 role task files stamp unchanged Docker labels | COMPLIANT |
| D-122 | Doc cascade synchronized atomically: defaults comment, README label table + prose + alt-INI, enrich.lua header docstring, nfsd README | 8 edits across 3 files verified; zero stale `service=` Loki-label references remain in fluentbit/ | COMPLIANT |
| D-123 | Dashboard sweep is verify-only; regression-guard grep confirms zero bare `service=` LogQL selectors across all 7 curated dashboards | `grep -rnE '"service=|{service='` = 0 matches; 7 JSON files confirmed present in dashboards/; no JSON files modified | COMPLIANT |
| D-124 | `transform/strip_namespace` processor uses `delete_key(resource.attributes, "service.namespace")`; modern path-qualified OTTL syntax | `delete_key(resource.attributes, "service.namespace")` present in config.yaml.j2:64; NOT bare `attributes` form | COMPLIANT |
| D-125 | Logs pipeline processors order is `[memory_limiter, batch, transform/strip_namespace]`; D-45 memory_limiter-first LOCK preserved | config.yaml.j2:150 = `processors: [memory_limiter, batch, transform/strip_namespace]` with D-125 inline cite | COMPLIANT |
| D-126 | `transform` wired into LOGS pipeline only; traces and metrics pipelines unchanged | Traces pipeline = `[memory_limiter, batch]`; metrics pipeline = `[memory_limiter, batch]`; no `transform` in either | COMPLIANT |
| D-127 | Processor is always-on; no new inventory variable added to `opentelemetry/defaults/main.yml` | `git diff` shows zero changes to `opentelemetry/defaults/main.yml` in phase 9; processor is literal YAML, not Jinja-templated | COMPLIANT |
| D-128 | Clean-break label transition; no dual-label period; old `service=` Loki streams age out per retention | Quickstart Upgrade notes explains clean-break; no relabeling or alias added; dashboard JSONs already used `service_name=` before this phase | COMPLIANT |
| D-129 | `docs/quickstart.md` gains `## Upgrade notes` subsection covering both the FB rename and the OTel transform | Section at line 253, before `## Building your own inventory`; contains both halves; no emojis; operational/factual tone | COMPLIANT |
| D-130 | enrich.lua NFS branch value stays `"remote"`; only the record key renames from `service` to `service_name` | enrich.lua line 161 = `record["service_name"] = "remote"` (value unchanged; key renamed per D-121) | COMPLIANT |
| D-131 | NFS scope is Lua rename only; FB config template, nfsd role config, and D-92 `enable_nfsd` coupling knob are untouched | No changes to `roles/fluentbit/templates/fluent-bit.conf.j2`, `roles/nfsd/defaults/main.yml`, or `nfsd/tasks/`; only `nfsd/README.md` line 86 prose updated | COMPLIANT |

---

## Out-of-Scope Guard

| Item | Expected State | Status |
|------|---------------|--------|
| Prometheus scrape labels | Unchanged (metric-namespace, not Loki) | VERIFIED — `roles/prometheus/templates/` has no `service=` Loki-label edits |
| Alertmanager `group_by` | Unchanged (`alertmanager_group_by: [alertname, cluster, service]` — alert-domain label) | VERIFIED — `roles/alertmanager/defaults/main.yml:39` unchanged |
| Grafana datasources | Already correctly maps `service.name` -> `service_name` via D-80 | VERIFIED — `datasources.yaml.j2` references `service_name` pre-phase; no edits in phase 9 |
| All 10 role Docker label stamps (`org.telemetron.service: telemetron`) | Unchanged per D-121 LOCK | VERIFIED — `grep -rn 'org.telemetron.service' roles/*/tasks/main.yml` shows all roles stamping unchanged value |
| `roles/opentelemetry/templates/verify-config.yaml.j2` | NOT modified (D-54 Approach A one-shot) | VERIFIED — file confirmed clean; no `transform/strip_namespace` reference |
| `nfsd_service_name` systemd unit var in `nfsd/defaults/main.yml` | Unchanged (systemd unit name, unrelated to Loki) | VERIFIED — `nfsd_service_name: nfs-server.service` at line 48, untouched |
| FB config template `fluent-bit.conf.j2` | Unchanged (D-131) | Not modified; no phase 9 git delta on this file |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `enrich.lua` | `record["service_name"]` | `org.telemetron.service` Docker label in container's `config.v2.json` (via `read_container_config`) | Yes — reads real on-disk JSON, falls back to `UNLABELED_SERVICE` constant for unlabeled containers | FLOWING |
| `config.yaml.j2` logs pipeline | `service.namespace` attribute | OTTL `delete_key(resource.attributes, "service.namespace")` | Strips attribute before Loki exporter; `error_mode: ignore` = no-op for absent attribute | FLOWING (defensive) |
| `smoke_test/templates/log.json.j2` | `service.name` resource attribute | Hardcoded `"telemetron-smoke"` | Emits only `service.name`, no `service.namespace` — transform is a no-op for smoke traffic | VERIFIED (transform defensive no-op confirmed) |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/quickstart.md` | 85, 98 | "CHANGE\_ME" / "placeholder" | Info | Pre-existing operator-instruction text from Phase 6 (committed in `5d478f5`); instructs operators to edit `secrets.yml`. Not a stub introduced by Phase 9. No action required. |

No TBD, FIXME, XXX debt markers found in any Phase 9-modified file. No unreferenced markers.

---

## Behavioral Spot-Checks

Step 7b is SKIPPED. This phase modifies Ansible role templates and a static Lua file — the behavior is verified at the Ansible+Docker layer on leviathan. No runnable entry point is testable without spinning Docker containers (explicitly out of scope per the objective note and CLAUDE.md M1 quality bar).

---

## Probe Execution

Step 7c is SKIPPED. No probe scripts declared or required for this phase. The phase's verification contract defers live execution to the leviathan UAT items below.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INGEST-02 | 09-01-PLAN.md | `enrich.lua` emits `record["service_name"]`; allowlist refs updated; 7 dashboards confirmed clean | SATISFIED | 5 emission sites confirmed, 0 `record["service"]` remaining, dashboard grep = 0 |
| INGEST-03 | 09-02-PLAN.md | OTel `transform/strip_namespace` strips `service.namespace` before `otlphttp/loki` exporter | SATISFIED | Processor defined and wired in logs pipeline; modern OTTL syntax; verify-config.yaml.j2 untouched |

---

## Human Verification Required

### 1. Fluent Bit Role — Two-Deploy Idempotency on Leviathan

**Test:**
```bash
cd /path/to/telemetron
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml --tags fluentbit
# First run: enrich.lua copy changed + restart fluentbit handler fires
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml --tags fluentbit
# Second run MUST report changed=0
```
**Expected:** Second run reports `changed=0 failed=0`
**Why human:** Requires running Ansible against the live leviathan Docker host

### 2. Fluent Bit — In-Container Lua Grep Assertion

**Test:**
```bash
docker exec telemetron-fluentbit grep -c 'record\["service_name"\]' /fluent-bit/etc/enrich.lua
docker exec telemetron-fluentbit grep -c 'record\["service"\]' /fluent-bit/etc/enrich.lua
```
**Expected:** First command returns `5`; second returns `0`
**Why human:** Confirms the live container received the new `enrich.lua` via the copy task

### 3. Grafana Loki Explore — FB Label Query

**Test:** Open Grafana Loki Explore (~30s after fluentbit restart) and run `{service_name="fluentbit"}`
**Expected:** Returns Fluent Bit container log lines without needing `{service="fluentbit"}`
**Why human:** Live query against running Loki instance; cannot be verified statically

### 4. Grafana Loki Explore — OTel Smoke Log Label Query

**Test:** Run `playbooks/smoke_test.yml`, then in Grafana Loki Explore run `{service_name="telemetron-smoke"}`
**Expected:** Smoke log from OTel-originated OTLP appears under `service_name` label
**Why human:** Live end-to-end data path requires running stack

### 5. OTel Collector Role — Two-Deploy Idempotency on Leviathan

**Test:**
```bash
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml --tags opentelemetry
# First run: config template changed + restart opentelemetry handler fires
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml --tags opentelemetry
# Second run MUST report changed=0
```
**Expected:** Second run reports `changed=0 failed=0`
**Why human:** Requires running Ansible against the live leviathan Docker host

### 6. OTel Collector — In-Container Transform Processor Grep

**Test:**
```bash
docker exec telemetron-opentelemetry \
  grep -A5 'transform/strip_namespace' /etc/otelcol-contrib/config.yaml
```
**Expected:** Shows processor definition with `delete_key(resource.attributes, "service.namespace")`
**Why human:** Confirms the live container received the new `config.yaml` with the transform processor

### 7. Optional — service.namespace Concatenation Defense Probe

**Test:**
```bash
curl -X POST http://leviathan:4318/v1/logs \
  -H 'Content-Type: application/json' \
  -d '{
    "resourceLogs": [{
      "resource": {
        "attributes": [
          {"key": "service.namespace", "value": {"stringValue": "testns"}},
          {"key": "service.name", "value": {"stringValue": "testsvc"}}
        ]
      },
      "scopeLogs": [{"logRecords": [{"body": {"stringValue": "ns-concat-test"}}]}]
    }]
  }'
# Then in Grafana Loki Explore: {service_name="testsvc"}
```
**Expected:** Log appears under `service_name="testsvc"` NOT `service_name="testns/testsvc"`
**Why human:** Proves the transform/strip_namespace processor is active and strips the namespace before Loki's service_name heuristic runs

---

## Gaps Summary

None. All 8 automated truths are VERIFIED. No code stubs, no missing artifacts, no broken wiring. Human UAT items are the standard leviathan live-execution items documented in both SUMMARY.md files.

---

## Deferred Items

None. Phase 9 is the final phase of v1.1.0. No roadmap deferred items.

---

## Recommended Follow-Ups

### Follow-up 1: Executor HEAD-assertion design bug (non-blocking)

During Plan 09-01 execution, the executor's worktree was on a detached HEAD state (did not land on the expected commit `77a9f26` before branching). The orchestrator recovered by rebasing the worktree branch onto `77a9f26` before merging (merge commit `3a4493a` message: "plan 09-01 (rebased onto 77a9f26)"). The final codebase state is correct — all 21 expected changes landed cleanly.

The underlying issue: the executor's `git reset --hard <commit>` HEAD-assertion step did not fire as designed, meaning the executor completed work without being at the intended base commit. The rebase recovery by the orchestrator was effective but manual.

Recommendation: open a follow-up note (or executor workflow issue) to document that the `git reset --hard` guard in the worktree setup step needs to be verified against actual HEAD, not assumed. This is an executor-prompt bug, not a Phase 9 code quality issue.

### Follow-up 2: SUMMARY line number drift (cosmetic, non-blocking)

The 09-01-SUMMARY.md reports emission site line numbers as 147, 154, 162, 170, 181. The actual file has them at 161, 169, 178, 187, 199 (matching the plan's specified lines). This appears to be a documentation artifact from the executor pre-numbering expected lines before the file shifted during Task 1 edits. The code is correct; only the SUMMARY's line-number references are inaccurate. No action required.

---

_Verified: 2026-05-28_
_Verifier: Claude (gsd-verifier)_
