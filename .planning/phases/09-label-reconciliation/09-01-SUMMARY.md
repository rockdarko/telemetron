---
phase: 09-label-reconciliation
plan: "01"
subsystem: fluentbit-loki-label
tags: [fluentbit, loki, label-rename, INGEST-02, D-121, D-122, D-123]
dependency_graph:
  requires: []
  provides: [INGEST-02-closed, service_name-loki-label-aligned]
  affects: [roles/fluentbit, roles/nfsd, loki-log-query-surface]
tech_stack:
  added: []
  patterns: [lua-record-key-rename, doc-cascade-atomicity]
key_files:
  created: []
  modified:
    - roles/fluentbit/files/enrich.lua
    - roles/fluentbit/defaults/main.yml
    - roles/fluentbit/README.md
    - roles/nfsd/README.md
decisions:
  - "D-121 LOCK upheld: only Loki record-key renames; Docker source label org.telemetron.service and Lua cache field entry.service unchanged"
  - "D-122 doc cascade: all 8 Loki-label-service references updated atomically in a single plan to prevent in-flight inconsistency"
  - "D-123 verify-only: zero dashboard JSON edits; regression-guard grep confirmed zero bare service= selectors across 7 dashboards"
  - "D-130 NFS scope: enrich.lua NFS branch value stays 'remote'; only the record key renames"
metrics:
  duration: "3 minutes"
  completed: "2026-05-28T11:35:40Z"
  tasks: 3
  files: 4
---

# Phase 09 Plan 01: Label Reconciliation — Fluent Bit service_name Rename Summary

Renamed Fluent Bit's Loki record-key emission from `service` to `service_name` at all 5 emission sites in `enrich.lua`, cascaded the rename through `defaults/main.yml`, `fluentbit/README.md` (7 touch points), and `nfsd/README.md` (RESEARCH amendment), and confirmed zero bare `service=` LogQL selectors across the 7 curated Grafana dashboards. Closes INGEST-02.

## Tasks Completed

| Task | Description | Commit | Files Changed |
|------|-------------|--------|---------------|
| 1    | Rename 5 record-key emissions in enrich.lua + update header docstring | a5fef5a | roles/fluentbit/files/enrich.lua |
| 2    | Cascade rename through fluentbit defaults comment + README + nfsd README | 1bffedb | roles/fluentbit/defaults/main.yml, roles/fluentbit/README.md, roles/nfsd/README.md |
| 3    | Verify-only: dashboard regression-guard + handler-notify confirmation | (no-op) | none |

## Task 1 — enrich.lua Emission Site Renames

**5 emission sites renamed** (all `record["service"]` -> `record["service_name"]`):

| Line | Context | Before | After |
|------|---------|--------|-------|
| 147 | NFS branch (D-130) | `record["service"] = "remote"` | `record["service_name"] = "remote"` |
| 154 | no-container_id fallback | `record["service"] = UNLABELED_SERVICE` | `record["service_name"] = UNLABELED_SERVICE` |
| 162 | cache hit | `record["service"] = entry.service` | `record["service_name"] = entry.service` |
| 170 | read-failed fallback | `record["service"] = UNLABELED_SERVICE` | `record["service_name"] = UNLABELED_SERVICE` |
| 181 | cache-miss success path | `record["service"] = svc` | `record["service_name"] = svc` |

**Header docstring updated** (2 lines):
- Line 4: `` -- `service_name` and `job` Loki labels derived from the source container's ``
- Line 36: `-- JSON read failure (container died) -> emit service_name="unlabeled" + job="unknown"`

**Verification grep results:**
```bash
grep -c 'record\["service"\]' roles/fluentbit/files/enrich.lua   # returns 0
grep -c 'record\["service_name"\]' roles/fluentbit/files/enrich.lua  # returns 5
grep -q '`service_name` and `job` Loki labels' roles/fluentbit/files/enrich.lua  # exits 0
grep -q 'emit service_name="unlabeled"' roles/fluentbit/files/enrich.lua  # exits 0
grep -q 'entry.service' roles/fluentbit/files/enrich.lua  # exits 0 (cache field untouched)
grep -c 'org.telemetron.service' roles/fluentbit/files/enrich.lua  # returns 2 (Docker source label refs intact)
```

**D-121 LOCK confirmed:**
- `entry.service` cache field name on line 162 RHS is unchanged
- `cache[container_id] = { service = svc, ... }` table field names unchanged
- `org.telemetron.service` Docker label references in header (lines 6, 11, 14 region) unchanged

## Task 2 — Doc Cascade (8 edits across 3 files)

**roles/fluentbit/defaults/main.yml** — 1 edit:
- BEFORE: `# service / job: container_name fallback (Q3 -- Docker-label promotion deferred)`
- AFTER:  `# service_name / job: container_name fallback (D-121: service -> service_name OTel-convention rename; Q3 Docker-label promotion deferred)`

**roles/fluentbit/README.md** — 6 edits:
1. Label table row cell 1: `` `service` `` -> `` `service_name` ``
2. Prose line 70: "The `service_name` and `job` labels are populated at runtime..."
3. Prose line 77: "back to `service_name=unlabeled` + `job=<container_name>` when..."
4. Labeling table third column: "populates Loki `service_name` label"
5. Prose line 95: "they just land with `service_name=unlabeled`..."
6. Alt-INI Labels example: `service_name=$service_name`

**roles/nfsd/README.md** — 1 edit (RESEARCH amendment, doc honesty):
- BEFORE: `` hardcodes `service = "remote"` and `job = "remote-syslog"` ``
- AFTER:  `` hardcodes `service_name = "remote"` and `job = "remote-syslog"` ``

**Verification grep results:**
```bash
grep -q 'service_name / job: container_name fallback' roles/fluentbit/defaults/main.yml  # exits 0
grep -q 'D-121' roles/fluentbit/defaults/main.yml  # exits 0
grep -cE 'service=\$service|`service=unlabeled`|populates Loki `service` label|`service` and `job` labels' roles/fluentbit/README.md  # returns 0
grep -q 'service_name=\$service_name' roles/fluentbit/README.md  # exits 0
grep -q 'populates Loki `service_name` label' roles/fluentbit/README.md  # exits 0
grep -q 'org.telemetron.service' roles/fluentbit/README.md  # exits 0 (Docker source label refs intact)
grep -q 'service_name = "remote"' roles/nfsd/README.md  # exits 0
grep -q 'job = "remote-syslog"' roles/nfsd/README.md  # exits 0 (D-130 value unchanged)
```

## Task 3 — Verify-Only Gate Results

**A1 — Dashboard regression-guard (D-123):**
```bash
grep -rnE '"service=|{service=' roles/grafana/files/dashboards/
# Returns: 0 matches — PASS
```

**A2 — Dashboard service_name coverage:**
```bash
grep -rl 'service_name' roles/grafana/files/dashboards/
# Returns 2 files:
#   roles/grafana/files/dashboards/loki-explore-landing.json
#   roles/grafana/files/dashboards/tempo-explore-landing.json
# PASS (>= 2)
```

**B — Handler-notify confirmation:**
```bash
grep -A6 'Copy Fluent Bit Lua enrichment script' roles/fluentbit/tasks/main.yml | grep -q 'notify: restart fluentbit'
# exits 0 — PASS
```

Task around line 43 of `roles/fluentbit/tasks/main.yml`:
```yaml
- name: Copy Fluent Bit Lua enrichment script (Plan 03-05 INGEST-07)
  ansible.builtin.copy:
    src: enrich.lua
    dest: "{{ fluentbit_config_dir }}/enrich.lua"
    mode: "0640"
  notify: restart fluentbit
```

No role edits needed — the handler-notify wiring was correct from Plan 03-05.

## Leviathan Operator Runbook (UAT)

### Two-deploy idempotency check

```bash
cd /path/to/telemetron

# First run after Phase 9 edits — picks up Lua copy (changed) + restart handler (changed)
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml --tags fluentbit
# Expected: changed > 0 (enrich.lua copy task changed, restart fluentbit handler fired)

# Second run MUST be idempotent
ansible-playbook -i inventory/leviathan/hosts.yml playbooks/deploy_docker.yml --tags fluentbit
# Expected: changed=0 (no files differ, handler does not fire)
```

### In-container Lua grep assertion

```bash
docker exec telemetron-fluentbit grep -c 'record\["service_name"\]' /fluent-bit/etc/enrich.lua
# Expected: 5

docker exec telemetron-fluentbit grep -c 'record\["service"\]' /fluent-bit/etc/enrich.lua
# Expected: 0
```

### Grafana Loki Explore validation (wait ~30s post-restart for new log lines)

```logql
{service_name="telemetron"}
```
Expected: returns Docker-container logs from the Telemetron stack.

Old `{service="..."}` streams remain visible for historical data per D-128 (Loki retains existing streams until retention expires — no data loss).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All 5 emission sites are fully wired. Doc cascade covers all identified touch points. Dashboard JSONs confirmed clean.

## Threat Flags

None. The rename is a literal key-string substitution with no new input surfaces, no new network paths, and no auth changes. See plan threat model for full STRIDE analysis.

## Forward Pointer

**09-02-PLAN.md** covers the remaining Phase 9 work:
- OTel Collector service.name -> service_name relabeling in the otelcol config (aligns the OTel-originated log label to match the newly-renamed FB label)
- `docs/quickstart.md` label section update reflecting the post-rename unified query pattern `{service_name="telemetron"}`

After 09-02 completes, both log sources (Fluent Bit and OTel) will surface under the same `service_name` label in Grafana Loki Explore, closing the label split that forced operators to write two queries.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| roles/fluentbit/files/enrich.lua exists | FOUND |
| roles/fluentbit/defaults/main.yml exists | FOUND |
| roles/fluentbit/README.md exists | FOUND |
| roles/nfsd/README.md exists | FOUND |
| Commit a5fef5a exists | FOUND |
| Commit 1bffedb exists | FOUND |
| enrich.lua service_name count = 5 | 5 |
| enrich.lua service count = 0 | 0 |
