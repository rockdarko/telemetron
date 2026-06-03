---
phase: 09-label-reconciliation
plan: "02"
subsystem: ingest/otel-collector
tags: [otel-collector, loki, ottl, transform-processor, upgrade-docs, INGEST-03]
requirements: [INGEST-03]

dependency_graph:
  requires: [09-01-PLAN]
  provides: [INGEST-03-closed, D-129-upgrade-docs]
  affects: [roles/opentelemetry, docs/quickstart.md]

tech_stack:
  added: []
  patterns:
    - "transform/strip_namespace processor in OTel Collector logs pipeline"
    - "Modern path-qualified OTTL syntax (delete_key(resource.attributes, ...))"
    - "D-125 append-after-batch pipeline order for transform processors"

key_files:
  created: []
  modified:
    - roles/opentelemetry/templates/config.yaml.j2
    - docs/quickstart.md

decisions:
  - "D-124: Modern path-qualified OTTL syntax chosen over legacy context-block form per RESEARCH recommendation; verbatim match to v0.152.0 README delete_key example"
  - "D-125: transform/strip_namespace appends LAST after [memory_limiter, batch]; D-45 memory-limiter-first lock preserved"
  - "D-126: transform wired into LOGS pipeline only; traces and metrics pipelines byte-identical post-edit"
  - "D-127: unconditional processor; no new inventory variable added to defaults/main.yml"
  - "D-128: clean-break transition; old service= streams age out per Loki retention; no relabeling or migration"
  - "D-129: Upgrade notes subsection placed between Step 8 and Building your own inventory per placement guidance"

metrics:
  duration: "3 minutes"
  completed_date: "2026-05-28T11:36:00Z"
  tasks_completed: 2
  files_changed: 2
---

# Phase 09 Plan 02: OTel Collector transform/strip_namespace + Upgrade Notes Summary

**One-liner:** OTel Collector logs pipeline gains transform/strip_namespace processor using modern path-qualified OTTL syntax to defensively strip service.namespace before Loki ingestion (INGEST-03), plus quickstart Upgrade notes documenting the service -> service_name label change (D-129).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add transform/strip_namespace processor + wire into logs pipeline | d1f5b65 | roles/opentelemetry/templates/config.yaml.j2 |
| 2 | Add Upgrade notes subsection to docs/quickstart.md | d37cb1c | docs/quickstart.md |

## Task 1 Detail: OTel Collector Transform Processor

### Before/After: Processors Block Addition

**BEFORE** (lines 50-54 of config.yaml.j2):
```yaml
  batch:
    timeout: {{ opentelemetry_batch_timeout }}
    send_batch_size: {{ opentelemetry_batch_send_batch_size }}
    send_batch_max_size: {{ opentelemetry_batch_send_batch_max_size }}

exporters:
```

**AFTER** (lines 50-67 of config.yaml.j2):
```yaml
  batch:
    timeout: {{ opentelemetry_batch_timeout }}
    send_batch_size: {{ opentelemetry_batch_send_batch_size }}
    send_batch_max_size: {{ opentelemetry_batch_send_batch_max_size }}

  # D-124: strip service.namespace from resource attributes so Loki's
  # service_name heuristic does not concatenate namespace/service into
  # the label value (upstream issue #32497). Logs pipeline only (D-126).
  # Always-on (D-127); modern path-qualified OTTL syntax per
  # transformprocessor v0.152.0 README (legacy context-block form still
  # works -- fall back to it if a future version regresses).
  transform/strip_namespace:
    error_mode: ignore
    log_statements:
      - delete_key(resource.attributes, "service.namespace")

exporters:
```

### Before/After: Logs Pipeline Reference

**BEFORE** (line 139):
```yaml
      processors: [memory_limiter, batch]
```

**AFTER** (line 151):
```yaml
      processors: [memory_limiter, batch, transform/strip_namespace]   # D-125: append after batch (D-45 order preserved); D-126 logs-only
```

### Traces and Metrics Pipelines: Byte-Identical

Both pipelines are confirmed unchanged post-edit:

```yaml
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]

    metrics:
      # docker_stats feeds the container.restarts signal (D-51).
      receivers: [otlp, docker_stats]
      processors: [memory_limiter, batch]
```

No `transform` appears in either traces or metrics pipeline (verified by grep returning empty).

### verify-config.yaml.j2 Confirmation

`roles/opentelemetry/templates/verify-config.yaml.j2` is untouched. This is the D-54 Approach A one-shot template used for syntax verification; it exercises the Mimir remote_write path, not the logs-to-Loki path. Confirmed via `git diff --name-only HEAD~2 HEAD` shows only `config.yaml.j2` and `docs/quickstart.md` changed.

### Acceptance Criteria Met

- `grep -c 'transform/strip_namespace' ...config.yaml.j2` returns 2 (definition + pipeline reference)
- `delete_key(resource.attributes, "service.namespace")` present (modern path-qualified OTTL, not bare `attributes`)
- `error_mode: ignore` present
- `log_statements:` present (NOT trace_statements or metric_statements)
- Logs pipeline: `[memory_limiter, batch, transform/strip_namespace]`
- Traces pipeline: `[memory_limiter, batch]` (no transform)
- Metrics pipeline: `[memory_limiter, batch]` (no transform)
- D-124 cite present in processor block comment
- D-126 cite present in pipeline inline comment
- No new variable in `roles/opentelemetry/defaults/main.yml`
- `verify-config.yaml.j2` not modified

## Task 2 Detail: Upgrade Notes in quickstart.md

### New Subsection Added

Placed between Step 8 ("Open Grafana") content and `## Building your own inventory`:

```markdown
## Upgrade notes

If upgrading from a v1.0.x deployment (or a pre-Phase-9 v1.1.0 build),
the Loki label key for Fluent-Bit-shipped Docker logs changed from
`service=` to `service_name=`. This aligns with the OpenTelemetry
`service.name` resource-attribute convention so Fluent Bit-originated and
OTel-Collector-originated logs share one queryable label key. Old Loki
streams ingested before the upgrade retain the `service=` label and age
out per your Loki retention setting; query historical pre-upgrade windows
with `{service="..."}` and post-upgrade windows with
`{service_name="..."}`. The 7 curated dashboards already use
`service_name=`. No data migration is required.

The OTel Collector also strips the `service.namespace` resource attribute
from logs before forwarding to Loki so that OTel-SDK-instrumented apps
that set both `service.namespace` and `service.name` do not see them
concatenated into the `service_name` Loki label (upstream issue #32497).
This is on by default and requires no inventory configuration.
```

### Structural Integrity

- Section count: 13 -> 14 (exactly +1 new top-level section)
- Line count: 302 -> 320 (delta: 18 lines; within 15-25 plan range)
- All original sections present and unchanged: Prerequisites, Steps 1-8, Building your own inventory, Troubleshooting, Production hardening (brief), Next steps
- `## Upgrade notes` appears before `## Building your own inventory` in file order (verified by awk)

## Deviations from Plan

### Auto-noted: Plan Check 5 False Negative

The plan's E2E check 5 (`grep -A2 '^    metrics:' ... | grep -v transform | grep -q 'processors: \[memory_limiter, batch\]'`) produces a false negative because `grep -A2` captures the first occurrence of `metrics:` in the file, which is inside the `receivers.docker_stats.metrics:` block (not the pipeline metrics section). The actual metrics pipeline at `processors: [memory_limiter, batch]` is 3 lines after the `metrics:` heading, outside the `-A2` window.

**Finding:** The metrics pipeline is definitively unchanged at line 156 (`processors: [memory_limiter, batch]`). No transform processor appears anywhere near the metrics pipeline. The plan's grep check has a pattern-matching limitation; the actual code is correct.

**Resolution:** No code change needed. Documented here for clarity.

## Known Stubs

None. Both file changes are complete functional edits (not placeholders).

## Threat Flags

No new security surface introduced. The transform/strip_namespace processor:
- Operates inside the existing OTel Collector process on a literal fixed key
- Uses `error_mode: ignore` (absent key is a no-op; no crash or DoS surface)
- No new auth surface; no new network endpoint
- No new Ansible role; no new Jinja variables

All threats in the plan's STRIDE register dispositioned `accept` with inline rationale. No new unregistered threat surface found.

## Leviathan Operator Runbook

Steps 9-11 from the plan's `<verification>` block are manual (leviathan UAT). The automated checks above cover the code-correctness bar. For the live deployment verification:

### Two-deploy idempotency assertion

```bash
# First deploy (expects changed>0 for template + handler restart)
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml \
  --tags opentelemetry

# Second deploy (expects changed=0)
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml \
  --tags opentelemetry
# Expected: ok=N changed=0 failed=0
```

### In-container transform/strip_namespace grep

```bash
docker exec telemetron-opentelemetry \
  grep -A5 'transform/strip_namespace' /etc/otelcol-contrib/config.yaml
```

Expected output shows the processor definition with `delete_key(resource.attributes, "service.namespace")`.

### Optional: service.namespace OTLP defensive probe

```bash
# Inject a one-shot OTLP log with both service.namespace and service.name
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

# In Grafana Loki Explore, query: {service_name="testsvc"}
# Expected: the log appears under service_name="testsvc" (NOT "testns/testsvc")
```

## Plan Pointer

The Fluent Bit half of Phase 9 (enrich.lua service -> service_name rename, D-121/D-122) lives in `09-01-PLAN.md`. This plan (09-02) closes the OTel Collector side (INGEST-03) and the documentation cascade (D-129). Together they complete the Phase 9 label reconciliation objective.

## Self-Check: PASSED

- `roles/opentelemetry/templates/config.yaml.j2` exists with transform/strip_namespace processor
- `docs/quickstart.md` exists with ## Upgrade notes section
- Commit d1f5b65: `feat(09-02): add transform/strip_namespace processor to OTel logs pipeline`
- Commit d37cb1c: `docs(09-02): add Upgrade notes subsection to quickstart.md (D-129)`
- verify-config.yaml.j2 not modified (confirmed)
- No new defaults variable (confirmed)
