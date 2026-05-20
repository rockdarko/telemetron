---
phase: 5
plan: 7
subsystem: ui-plane
tags: [grafana, loki, derivedfields, trace-correlation, gap-closure, uat]
requires: [UI-04]
provides:
  - "Loki -> Tempo trace correlation now wires against telemetron's actual Loki shape (structured metadata, not stream labels)"
  - "Regex fallback derivedField for body-embedded trace_id in uninstrumented apps"
affects:
  - "roles/grafana/templates/datasources/datasources.yaml.j2 derivedFields block"
  - "roles/grafana/README.md Trace-to-logs section"
tech-stack:
  added: []
  patterns:
    - "Two-matcher derivedField pattern: canonical OTel-native primary + regex fallback for legacy/uninstrumented apps"
    - "Distinct name keys (trace_id, trace_id_body) so Grafana renders both clickable links instead of deduplicating"
key-files:
  created:
    - .planning/phases/05-ui-plane/05-07-SUMMARY.md
  modified:
    - roles/grafana/templates/datasources/datasources.yaml.j2
    - roles/grafana/README.md
    - .planning/ROADMAP.md
decisions:
  - "matcherType: structured_metadata is the Grafana 11+ canonical for Loki 3.x OTel-native trace_id; matcherType: label was the wrong path for telemetron's actual Loki shape (live labels are {env, host, job, service_name} -- no trace_id label)"
  - "Two derivedFields with distinct name keys (trace_id + trace_id_body) renders both links; same name key would dedup"
  - "E2E click-through verification deferred per D-78 (operator-driven; telemetron M1 ships no instrumented sample app)"
metrics:
  duration_minutes: 4
  tasks_executed: 4
  files_touched: 3
  completed: 2026-05-19
---

# Phase 5 Plan 7: Loki derivedField trace_id matcherType fix (UAT gap 3 closure) Summary

Replaced the Loki derivedField `matcherType: label` (which never matched against telemetron's actual Loki stream shape) with a two-matcher form: `structured_metadata` for OTel-native traces + `regex` fallback for body-embedded trace_ids; verified live on leviathan via Grafana provisioning reload API.

## What Shipped

- **`roles/grafana/templates/datasources/datasources.yaml.j2`** — Loki `jsonData.derivedFields` block expanded from one entry to two:
  - **Primary (`trace_id`):** `matcherType: structured_metadata`, `matcherRegex: trace_id` — matches OTel-instrumented apps that push logs via OTLP (Loki 3.x stores `trace_id` as structured metadata per D-78).
  - **Fallback (`trace_id_body`):** `matcherType: regex`, `matcherRegex: '(?:trace_id|traceID)[=:]"?([a-f0-9]+)'` — extracts the id from log line body for uninstrumented apps that hand-format `trace_id=<hex>` or `traceID:<hex>`.
  - Both link to `datasourceUid: tempo` with distinct `urlDisplayLabel` strings.
  - Multi-line inline comment documents the gap-3 root cause, the two-matcher rationale, and the Grafana 11+ structured_metadata syntax.
- **`roles/grafana/README.md`** — Trace-to-logs section expanded from a 5-line paragraph to a 4-subsection treatment:
  - `### Tempo -> Loki` (tracesToLogsV2 direction, unchanged).
  - `### Loki -> Tempo` (derivedFields direction, rewritten to document both matchers + the pre-05-07 root-cause failure mode).
  - `### Label mapping note (D-81 / 999.4 backlog)` — explains why live Loki labels are `{env, host, job, service_name}` and points at the future-milestone reconciliation option.
  - `### What this does NOT cover (M1 scope honesty)` — explicit framing that E2E click-through requires an operator-supplied instrumented app; static wiring is Gate 9 D-73 Step 9.
- **`.planning/ROADMAP.md`** — Phase 5 plans list extended with `- [x] 05-07-PLAN.md -- gap closure (Loki derivedField matcherType structured_metadata + regex fallback); Wave 1`.

## Verification

### Static template parse

`python3 + yaml.safe_load_all` (with Jinja `{{ }}` and `{% %}` stripped) confirms:
- Exactly 2 derivedFields under the Loki datasource jsonData block.
- First entry: `name=trace_id`, `matcherType=structured_metadata`, `datasourceUid=tempo`.
- Second entry: `name=trace_id_body`, `matcherType=regex`, `datasourceUid=tempo`, `matcherRegex='(?:trace_id|traceID)[=:]"?([a-f0-9]+)'`.

The single-quoted YAML scalar preserves the literal `"` in the regex without escape sequences — no need for the documented YAML pipe-block fallback.

### README structural sanity

`grep` confirms `structured_metadata`, `999.4`, and the regex/body-embedded fallback are all referenced; existing `## ` heading shape preserved.

### Live deploy on leviathan

Ran `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags grafana` end-to-end with PLAY RECAP `ok=22 changed=0 unreachable=0 failed=0` — the Phase 5 plan 05-05 verify rewrite (committed at 922a014 earlier in the parallel wave) is what made `--tags grafana` work without `--skip-tags grafana-verify`. Existing Gate 9 / Gate 9.5 / UI-04 wiring asserts all passed.

Rendered file inspection on leviathan:

```
$ ssh leviathan "grep -cE '^          matcherType: (structured_metadata|regex)\$' /opt/telemetron/grafana/provisioning/datasources/datasources.yaml"
2
```

Exactly 2 actual matcher keys (counting only YAML keys, not the comment block that mentions them in prose).

### Live Grafana API (post provisioning reload)

Grafana provisioning files do NOT auto-reload on disk change — the running Grafana served the pre-deploy `matcherType: label` config until the reload endpoint was hit. After `POST /api/admin/provisioning/datasources/reload`:

```
Number of derivedFields: 2
 - trace_id matcherType=structured_metadata datasourceUid=tempo
 - trace_id_body matcherType=regex datasourceUid=tempo
LIVE API OK -- both matchers loaded, both link to tempo
```

Grafana 13.0.1 accepts `matcherType: structured_metadata` without complaint — the documented fallback path (keep `matcherType: label` + add regex, defer structured_metadata to a future Grafana bump) did NOT need to fire.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical functionality] Grafana provisioning hot-reload trigger**

- **Found during:** Task 3 (live UAT)
- **Issue:** Plan 05-07 stated "Grafana hot-reloads provisioning files" but Grafana 13.0.1 does NOT watch provisioning files for changes. The new datasources.yaml on disk was inert; the live Grafana API still reported the pre-05-07 `matcherType: label` config. Running Grafana would have surfaced the new config only after a container restart on the next deploy that touches the grafana_container task — which would be confusing to operators in the meantime.
- **Fix:** Hit Grafana's `POST /api/admin/provisioning/datasources/reload` admin endpoint after deploy. This is the canonical Grafana operation for picking up provisioning changes without a restart. Confirmed via re-querying `GET /api/datasources/uid/loki` that both matchers loaded.
- **Files modified:** none (operational verification step, not a config change)
- **Followup not added to plan:** Adding `uri:` Ansible task to call the reload endpoint at the end of `roles/grafana/tasks/verify.yml` would make this automatic on every grafana-tagged deploy. Deferred — out of scope for a config-only gap closure; logged here for a future polish pass.

### Architectural decisions

None.

### Auth gates

None.

## Open Issues / Followups (out of scope)

- **Auto-reload provisioning in the role:** see deviation #1 above. The grafana role's verify task could call `/api/admin/provisioning/datasources/reload` after rendering datasources.yaml. A future polish-pass plan or a Phase 6 cleanup item.
- **E2E click-through verification:** explicitly deferred per D-78. Requires either an OTel-instrumented sample app (telemetron M1 ships none) or an uninstrumented app with body-embedded trace_id + independent Tempo trace ingest. Operators verify against their own services.
- **Standalone `## Label mapping` README section duplication:** the new `### Label mapping note` subsection inside Trace-to-logs and the existing top-level `## Label mapping` section now overlap in content. Both intentionally left in place — the standalone section was a pre-05-07 anchor; deleting it would expand scope beyond the gap closure. Reconciliation belongs in a future README pass.

## Known Stubs

None. All wiring is concrete and verified.

## Commits

- `922a014` — fix(05-07): change Loki derivedField trace_id matcherType to structured_metadata + add regex fallback
- `5bdc502` — docs(05-07): expand grafana README Trace-to-logs section for dual derivedField matchers
- (final metadata commit landed below by `final_commit` step)

## UAT Gap-Truth 3 Status

**Closed at config layer.** Telemetron's Grafana now ships a derivedField wiring that has a chance of firing against telemetron's actual Loki stream shape:
- The `structured_metadata` matcher catches OTel-native ingest (D-78 happy path).
- The `regex` matcher catches body-embedded trace_id for legacy/uninstrumented apps.
- Pre-05-07 `matcherType: label` would have NEVER fired because telemetron's live Loki labels are `{env, host, job, service_name}` — no `trace_id` label.

E2E runtime confirmation of the actual click-through navigation remains operator-driven per D-78. The plan explicitly acknowledges this — it shipped the config correctness, not the E2E demo.

## Self-Check: PASSED

Verified:
- `roles/grafana/templates/datasources/datasources.yaml.j2` FOUND (modified, structured_metadata + regex matchers present).
- `roles/grafana/README.md` FOUND (modified, expanded Trace-to-logs section).
- `.planning/ROADMAP.md` FOUND (modified, 05-07 plan entry added).
- Commit `922a014` FOUND in git log.
- Commit `5bdc502` FOUND in git log.
- Rendered file on leviathan FOUND with exactly 2 matcher entries.
- Live Grafana API confirms both matchers loaded after provisioning reload.
