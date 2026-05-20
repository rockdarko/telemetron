# Phase 6: Opt-in, Orchestration, Docs & Smoke Test - Research

**Researched:** 2026-05-19
**Domain:** NFS host-package role, Fluent Bit Lua extension, OTLP/HTTP JSON payloads, Ansible Grafana-proxy assertions, Ansible NFS idempotency, Markdown docs conventions
**Confidence:** HIGH for OTLP payload shapes and Lua filter return codes (official specs verified). HIGH for NFS distro branching (Red Hat + Ubuntu official docs). MEDIUM for FB tail Tag_Regex path interpolation nuance (docs confirmed pattern, but named-capture-to-tag interpolation is Rewrite Tag territory — see Finding A3). HIGH for smoke assertion shape (mirrored from Phase 5 verify.yml, already proven on leviathan).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**nfsd role shape (LEGACY-01)**
- D-91: `nfsd` is a host-package role, not a container role. Only host-package role in M1.
- D-92: `enable_nfsd` is a single inventory knob that flips BOTH the `nfsd` role AND a conditional `[INPUT] tail` block inside `roles/fluentbit/`. Default `enable_nfsd: false` in `inventory/example-homelab/group_vars/all/nfsd.yml`.
- D-93: Default share root `/srv/telemetron-nfs/<hostname>/`. `nfsd_exports: []` (default empty list of `{path, allow}` dicts). Default of `[]` means no exports happen until operator names a remote host.
- D-94: NFSv4 only, no Kerberos, AUTH_SYS + IP allow-list. One-port TCP `:2049`.
- D-95: FB Lua filter extension for path-derived labels. When FB tag matches NFS tail pattern (e.g. `nfs.<hostname>.<path>`), extract `host` from segment 1 of the tag, set `service: remote`, `job: remote-syslog`. No change to existing Docker-label-from-config.v2.json path.
- D-96: `roles/nfsd/README.md` opens with "When to use this role" section. Most operators do NOT need `nfsd`.

**Smoke test shape (OPS-07)**
- D-97: New playbook `playbooks/smoke_test.yml`. Not bolted onto `deploy_docker.yml`.
- D-98: Producers = `ansible.builtin.uri` or `ansible.builtin.command: curl` against `:4318/v1/logs`, `/v1/metrics`, `/v1/traces` with hand-rolled JSON payloads in `playbooks/smoke_test/templates/{log,metric,trace}.json.j2`. OTLP/HTTP only (no gRPC).
- D-99: Asserts via Grafana datasource-proxy queries with `retries: 12 / delay: 5` (60-second budget). Four assertion tasks: Loki, Prometheus, Mimir, Tempo.
  - Loki: `GET /api/datasources/proxy/uid/loki/loki/api/v1/query?query={service_name="telemetron-smoke"} |= "telemetron-smoke-test"`
  - Prometheus: `GET /api/datasources/proxy/uid/prometheus/api/v1/query?query=telemetron_smoke_metric{run_id="<id>"}`
  - Mimir: `GET /api/datasources/proxy/uid/mimir/prometheus/api/v1/query?query=telemetron_smoke_metric{run_id="<id>"}`
  - Tempo: `GET /api/datasources/proxy/uid/tempo/api/traces/<trace_id>`
- D-100: Three play tags: `log`, `metric`, `trace`.
- D-101: Grafana Basic Auth via `grafana_admin_password`.

**Docs scope & voice (DOCS-01/02/03/04)**
- D-102: Voice split — terse reference (`architecture.md`, `inventory.md`) + one teaching walkthrough (`quickstart.md`).
- D-103: `docs/architecture.md` synthesized from `.planning/research/` + CLAUDE.md + per-role READMEs. No D-XX references, no `.planning/` paths.
- D-104: `docs/quickstart.md` structure: Prerequisites → Clone → Edit hosts → Copy secrets → Optional vault encrypt → deploy playbook → smoke test → Open Grafana → Troubleshooting.
- D-105: `docs/inventory.md` deep-dive: group_vars/all/ schema, secrets contract, host_vars/ patterns, symlink-from-outside-repo.
- D-106: `README.md` rewrite — "self-hosted observability in one playbook." Delete "Status: early." Drop hook_router and HAProxy from stack list.

**Plan slicing & wave order**
- D-107: 4 plans: 06-01 (nfsd + FB tail), 06-02 (smoke_test.yml), 06-03 (3 docs), 06-04 (README rewrite + idempotency revalidation).
- D-108: Strict sequential — Wave 1 = 06-01, Wave 2 = 06-02, Wave 3 = 06-03, Wave 4 = 06-04.
- D-109: Live UAT on leviathan for each plan's verify.
- D-110: Per-plan light doc cascade (roles/README.md tick nfsd in 06-01; ROADMAP.md mark plan complete; PROJECT.md Active section).

### Claude's Discretion

- Exact `[INPUT] tail` directive shape for the FB NFS path (parser choice, `Mem_Buf_Limit`, multiline handling).
- Whether the FB Lua extension is one filter or two — lean: extend existing `enrich.lua`.
- Exact JSON shape of OTLP/HTTP payloads for smoke producers.
- Exact Ansible `until:` predicate syntax for smoke assertion tasks.
- Diagram format for `docs/architecture.md` — ASCII art (lean: ASCII so `cat`/raw-GitHub works without Mermaid renderer).
- Whether `docs/quickstart.md` ships a "production hardening" subsection — lean: yes, brief.
- Whether docs cite D-numbers — lean: zero D-numbers in public docs.
- Whether smoke playbook loads `secrets.yml` itself — lean: yes, via `vars_files`.
- nfsd README structure — likely mirrors promlens deprecation-banner pattern but with "When to use this role" header.

### Deferred Ideas (OUT OF SCOPE)

- NFS Kerberos hardening (v2)
- Remote-host log shipper recipes (rsyslog → NFS)
- Multi-host smoke test
- Synthetic alert/trace span graph in smoke
- CI integration for smoke
- `docs/alerts.md`, `docs/mimir-retention.md`, `docs/fluentbit-timestamps.md`, `docs/hook-router.md`, `docs/instrumentation-otel.md`, `docs/migration-from-inspq.md`, `docs/metrics.md` (all DOCS-V2-01..07)
- Mermaid diagrams for architecture.md
- Full production-hardening guide
- arm64 / Pi 5 / Apple Silicon support
- GitHub Pages or any docs hosting
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEGACY-01 | `nfsd` role default-off; `roles/nfsd/README.md` documents what it does | Sections A (FB tail), B (Lua), E (NFS host-package) |
| INV-01 | Operator can clone, edit one hostname, supply vault password, run `deploy_docker.yml` end-to-end | Section H (idempotency), Section G (README conventions) |
| INV-03 | `playbooks/deploy_docker.yml` orchestrates 14 roles in dependency order with per-role tags | Existing deploy_docker.yml already has 12; nfsd appends last with `when:` |
| OPS-07 | M1 smoke test: synthetic log + metric + trace visible in Grafana within 60s | Sections C (OTLP payloads), D (Grafana proxy assertions) |
| DOCS-01 | `docs/architecture.md` with components, signal flow, port allocation | Section I (synthesis pattern), existing research files |
| DOCS-02 | `docs/quickstart.md` verified by operator running it verbatim | Section G (doc conventions), D-104 structure |
| DOCS-03 | `docs/inventory.md` deep-dive inventory model | Existing group_vars structure documented |
| DOCS-04 | Top-level `README.md` updated post-M1 | Section G (README anti-patterns) |
</phase_requirements>

---

## Summary

Phase 6 closes M1. Four discrete implementation tasks, each with different technical domains. This research covers all "Claude's Discretion" areas identified in CONTEXT.md plus the cross-cutting patterns the planner needs to structure the four plans.

**nfsd role (Plan 06-01):** The upstream INSPQ nfsd role targets EL7 (with a yum-binary workaround) and Ubuntu, using `blockinfile` for `/etc/exports` and firewall management. The Telemetron port targets EL8+/Ubuntu 22.04+ only, drops the EL7 yum binary workaround, drops firewall management (operator's domain — consistent with Phase 1-5 role pattern), renames `nfs_shares` to `nfsd_exports`, and adds the `/srv/telemetron-nfs/` path discipline. Both distributions use the systemd service name `nfs-server.service` (confirmed below). FB tail integration uses the asterisk-in-tag path-expansion mechanism to produce `nfs.*` tags, then the Lua filter extracts the host from the tag segments.

**Smoke test (Plan 06-02):** OTLP/HTTP JSON payloads are fully specified in the OpenTelemetry proto examples. The canonical request bodies are verified against official spec and match what OTel Collector Contrib 0.152.0 accepts. Smoke assertions mirror the `roles/grafana/tasks/verify.yml` `docker_container_exec` + `retries:12 / delay:5` pattern exactly. Tempo returns HTTP 404 with body "trace not found" when not yet ingested — the retry loop handles this.

**Docs (Plan 06-03):** Synthesis material already exists in `.planning/research/` (ARCHITECTURE.md, PITFALLS.md, STACK.md, FEATURES.md, SUMMARY.md) and CLAUDE.md (port-allocation cheat sheet, component table, version compatibility matrix). ASCII signal-flow diagrams render in `cat` and raw GitHub without tooling. The ARCHITECTURE.md research file already contains a usable ASCII diagram that needs distillation for public consumption.

**README rewrite + idempotency (Plan 06-04):** "Status: early" language deleted. HAProxy and hook_router removed from component list with v2 callouts. Idempotency contract: second run `changed=0` confirmed by leviathan. Known false-changed sources in `community.docker.docker_container` (image re-pull, port range normalization in Docker 29) do not apply because all Phase 1-5 roles use `state: started` not `state: present` (no re-pull) and the Docker 29 port-range normalization fix is in community.docker 4.5.2+ (leviathan's collection version should be checked at verify time).

**Primary recommendation:** Follow the exact `docker_container_exec` + `until:` retry pattern from `roles/grafana/tasks/verify.yml` for all smoke assertions; use OTLP spec canonical JSON for producers; extend `enrich.lua` in-place for NFS path label extraction.

---

## Standard Stack

### Core (Phase 6 specific — no new images)

Phase 6 introduces no new Docker images. The nfsd role uses host packages only (D-91).

| Package | Version | Purpose | Distro |
|---------|---------|---------|--------|
| `nfs-utils` | distro default | NFS server userland | EL8+ (RHEL, Rocky, AlmaLinux) |
| `nfs-kernel-server` | distro default | NFS server userland | Ubuntu 22.04+ / Debian |

**No new Ansible collections needed.** All required collections (`community.docker`, `ansible.builtin`) are already in use from Phase 1-5.

### Reused From Prior Phases

| Component | Version | Role in Phase 6 |
|-----------|---------|-----------------|
| OTel Collector Contrib | 0.152.0 | OTLP/HTTP target for smoke test producers |
| Grafana OSS | 13.0.1 | Datasource proxy endpoint for smoke assertions |
| `ansible.builtin.uri` | built-in | Smoke test OTLP push tasks |
| `community.docker.docker_container_exec` | built-in | Smoke assertion tasks (same as grafana verify.yml) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| host-package nfsd | `erichough/nfs-server` container | Container image archived 2022; requires `--privileged` or `CAP_SYS_ADMIN`; security debt |
| `ansible.builtin.uri` for OTLP push | `ansible.builtin.command: curl` | Both work; `uri` is more Ansible-idiomatic; `curl` avoids JSON serialization edge cases in Jinja — planner chooses |

---

## Architecture Patterns

### Finding A: Fluent Bit Tail Input for NFS Path with Tag Interpolation

**Confirmed behavior (HIGH confidence — docs.fluentbit.io/manual/4.1/data-pipeline/inputs/tail):**

The FB tail input `Tag` directive supports asterisk expansion: if the tag contains `*`, that asterisk is replaced with the absolute path of the monitored file, with forward slashes converted to dots.

For a file at `/srv/telemetron-nfs/oldbox/auth.log`, with `Tag nfs.*` the resulting tag is:
```
nfs.srv.telemetron-nfs.oldbox.auth.log
```

The Lua filter then parses this tag by splitting on `.` — segment 0 is `nfs`, segment 1 is `srv`, segment 2 is `telemetron-nfs`, segment 3 is the hostname (`oldbox`), and subsequent segments are the log filename components.

**Critical limitation — `Tag_Regex` named groups do NOT interpolate into `Tag`:**

`Tag_Regex` extracts named capture groups (e.g. `(?<container_id>...)`) that are usable as placeholders in the `Tag` string (e.g. `Tag docker.<container_id>`). This pattern works well when the capture group target is the filename component — as in the existing Docker container tail in `fluent-bit.conf.j2`.

For the NFS case, the path we need is a directory component (`/srv/telemetron-nfs/<hostname>/file.log`), not the filename. To extract `hostname` via `Tag_Regex`, the pattern would need to match across directory separators, which requires anchoring from the full path. The simpler and proven approach: use `Tag nfs.*` (asterisk expansion) and let the Lua filter split the resulting dotted path to extract the hostname segment. This avoids `Tag_Regex` complexity entirely.

**Recommended NFS `[INPUT] tail` block:**

```ini
{% if enable_nfsd | default(false) | bool %}
[INPUT]
    Name              tail
    Alias             nfs_logs
    Path              {{ nfsd_share_root | default('/srv/telemetron-nfs') }}/*/*.log
    Tag               nfs.*
    Refresh_Interval  10
    Read_from_Head    false
    Skip_Long_Lines   On
    Mem_Buf_Limit     5MB
    storage.type      filesystem
    DB                /var/log/flb-nfs.db
{% endif %}
```

No parser is specified (raw syslog-shaped lines from remote hosts are highly variable; the operator's responsibility per D-96 framing). `Read_from_Head false` matches the Docker tail default (D-50 Mode 4). `DB` tracks offset across FB restarts. `Mem_Buf_Limit 5MB` is conservative (half the Docker-container input limit) because NFS tailed logs are expected to be much lower volume. No `multiline` handling: syslog-shaped lines are typically single-line; the operator can add `Multiline` as an override if their legacy hosts produce multi-line logs.

**Important:** The `[OUTPUT]` block is `Match *` which already catches `nfs.*` tags. No additional output rule needed.

### Finding B: Fluent Bit Lua Filter Return Code Contract

**Confirmed (HIGH confidence — docs.fluentbit.io/manual/data-pipeline/filters/lua):**

Standard three-parameter callback signature: `function cb(tag, timestamp, record)`

Return codes:
- `-1`: Drop the record entirely
- `0`: No modification; pass record unchanged
- `1`: Record and timestamp both modified; use returned timestamp
- `2`: Timestamp unchanged; only record modified (use returned record table)

The existing `enrich.lua` already uses return code `2` consistently. The NFS branch extension must also return `2`.

**Extension pattern for `enrich.lua`:**

The NFS branch fires when the tag starts with `nfs.` — this is a clean prefix that will not collide with the existing `docker.*` tag path. The tag for an NFS-tailed file looks like `nfs.srv.telemetron-nfs.<hostname>.<filename_with_dots>`. Segment index 3 (zero-based, splitting on `.`) is the hostname — provided the share root is exactly `/srv/telemetron-nfs` (two path components after the leading slash, plus `nfs` prefix = 3 leading segments consumed: `nfs`, `srv`, `telemetron-nfs`, then hostname at index 3).

```lua
-- NFS path branch: tag = "nfs.srv.telemetron-nfs.<hostname>.<filename...>"
-- Segment 0: nfs
-- Segment 1: srv
-- Segment 2: telemetron-nfs  (last component of /srv/telemetron-nfs)
-- Segment 3: hostname (first sub-dir after share root)
local function hostname_from_nfs_tag(tag)
    local parts = {}
    for part in string.gmatch(tag, "[^.]+") do
        parts[#parts + 1] = part
    end
    return parts[4]  -- 1-indexed in Lua: parts[4] = segment index 3
end

function enrich(tag, timestamp, record)
    -- NFS path: tag starts with "nfs."
    if string.match(tag, "^nfs%.") then
        local host = hostname_from_nfs_tag(tag)
        record["host"]    = host or "unknown-nfs-host"
        record["service"] = "remote"
        record["job"]     = "remote-syslog"
        return 2, timestamp, record
    end

    -- Existing Docker path (unchanged)
    local container_id = container_id_from_tag(tag)
    -- ... rest of existing logic ...
end
```

**One filter vs. two:** Extend the existing `enrich.lua` (one source of truth). The Jinja `Match docker.*` on the existing filter block remains unchanged; add a second `[FILTER] lua` block with `Match nfs.*` that calls the same `enrich` function. The single `enrich` function handles the dispatch internally via tag prefix.

**Actually simpler structure:** The existing `[FILTER] lua` uses `Match docker.*`. The NFS extension requires a separate `[FILTER] lua` block with `Match nfs.*` — both blocks call the same `enrich` function from the same `enrich.lua` file. This keeps the Match predicates clean and avoids the combined `Match *` hitting both paths unnecessarily.

```ini
{% if enable_nfsd | default(false) | bool %}
[FILTER]
    Name              lua
    Alias             telemetron_enrich_nfs
    Match             nfs.*
    script            {{ fluentbit_enrich_lua_path }}
    call              enrich
{% endif %}
```

The existing `[FILTER] lua` block (Match `docker.*`) is untouched.

### Finding C: OTLP/HTTP JSON Payload Shapes

**Confirmed (HIGH confidence — verified against official opentelemetry-proto/examples JSON files):**

**Headers for all three endpoints:**
```
Content-Type: application/json
```

**Expected response:** `HTTP 200 OK` on success.

**C1: Log payload (`POST /v1/logs`)**

Minimum viable payload for smoke test:
```json
{
  "resourceLogs": [
    {
      "resource": {
        "attributes": [
          {
            "key": "service.name",
            "value": { "stringValue": "telemetron-smoke" }
          }
        ]
      },
      "scopeLogs": [
        {
          "scope": { "name": "telemetron-smoke" },
          "logRecords": [
            {
              "timeUnixNano": "{{ ansible_date_time.epoch }}000000000",
              "observedTimeUnixNano": "{{ ansible_date_time.epoch }}000000000",
              "severityNumber": 9,
              "severityText": "INFO",
              "traceId": "{{ smoke_trace_id }}",
              "spanId": "{{ smoke_span_id }}",
              "body": { "stringValue": "telemetron-smoke-test smoke=true run_id={{ smoke_run_id }}" },
              "attributes": [
                { "key": "smoke", "value": { "stringValue": "true" } }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**C2: Metric payload (`POST /v1/metrics`)**

Minimum viable payload (gauge metric for simplicity — no aggregation temporality required):
```json
{
  "resourceMetrics": [
    {
      "resource": {
        "attributes": [
          {
            "key": "service.name",
            "value": { "stringValue": "telemetron-smoke" }
          }
        ]
      },
      "scopeMetrics": [
        {
          "metrics": [
            {
              "name": "telemetron_smoke_metric",
              "description": "Telemetron M1 smoke test signal",
              "unit": "1",
              "gauge": {
                "dataPoints": [
                  {
                    "asDouble": 1,
                    "timeUnixNano": "{{ ansible_date_time.epoch }}000000000",
                    "attributes": [
                      { "key": "run_id", "value": { "stringValue": "{{ smoke_run_id }}" } }
                    ]
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

**Why gauge not sum:** A gauge requires no `aggregationTemporality` or `isMonotonic` fields — shorter, less error-prone for a hand-rolled Jinja template. Prometheus and Mimir will ingest it as a gauge metric. The `run_id` label makes each smoke run individually queryable.

**C3: Trace payload (`POST /v1/traces`)**

```json
{
  "resourceSpans": [
    {
      "resource": {
        "attributes": [
          {
            "key": "service.name",
            "value": { "stringValue": "telemetron-smoke" }
          }
        ]
      },
      "scopeSpans": [
        {
          "scope": { "name": "telemetron-smoke" },
          "spans": [
            {
              "traceId": "{{ smoke_trace_id }}",
              "spanId": "{{ smoke_span_id }}",
              "name": "telemetron-smoke-span",
              "startTimeUnixNano": "{{ ansible_date_time.epoch }}000000000",
              "endTimeUnixNano": "{{ (ansible_date_time.epoch | int + 1) }}000000000",
              "kind": 2,
              "attributes": [
                { "key": "smoke", "value": { "stringValue": "true" } },
                { "key": "run_id", "value": { "stringValue": "{{ smoke_run_id }}" } }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**traceId / spanId format confirmed:** traceId = 32 hex characters (case-insensitive). spanId = 16 hex characters. Both are hex-encoded strings per OTLP JSON spec ("case-insensitive hex-encoded strings, not base64").

**C4: Generating smoke_trace_id / smoke_span_id in Ansible**

The `ansible.builtin.password` lookup with `/dev/null` as path generates a new random value on every invocation WITHOUT writing to disk:

```yaml
vars:
  smoke_trace_id: "{{ lookup('ansible.builtin.password', '/dev/null length=32 chars=hexdigits') | lower }}"
  smoke_span_id:  "{{ lookup('ansible.builtin.password', '/dev/null length=16 chars=hexdigits') | lower }}"
  smoke_run_id:   "{{ ansible_date_time.epoch }}"
```

**Note:** `chars=hexdigits` uses Python's `string.hexdigits` which includes both upper and lower case a-f — applying `| lower` normalizes to lowercase hex. Per OTLP spec, case-insensitive is fine, but lowercase is conventional.

**Alternative for smoke_run_id:** `ansible_date_time.epoch` is the Unix timestamp as a string. It provides per-run uniqueness for the metric label without requiring additional lookup.

### Finding D: Grafana Datasource-Proxy Smoke Assertions

**Confirmed pattern (HIGH confidence — copied from `roles/grafana/tasks/verify.yml` Phase 5, proven on leviathan):**

The canonical assertion pattern is `community.docker.docker_container_exec` against the running `telemetron-grafana` container with `retries: 12 / delay: 5` (60-second wall-clock budget):

```yaml
- name: "Smoke assert -- Loki received smoke log"
  community.docker.docker_container_exec:
    container: "{{ grafana_container_name }}"
    argv:
      - /bin/sh
      - -c
      - |
        set -e
        BODY=$(curl -fsS -u {{ grafana_admin_user }}:{{ grafana_admin_password }} \
          'http://localhost:{{ grafana_http_port }}/api/datasources/proxy/uid/loki/loki/api/v1/query?query=%7Bservice_name%3D%22telemetron-smoke%22%7D+%7C%3D+%22telemetron-smoke-test%22')
        echo "$BODY" | grep -q '"result":\[{' || { echo "Loki smoke log not found yet: $BODY"; exit 1; }
        echo "loki_smoke_ok"
  register: smoke_assert_loki
  retries: 12
  delay: 5
  until: smoke_assert_loki is succeeded
  changed_when: false
  failed_when: smoke_assert_loki is failed and smoke_assert_loki.attempts | default(0) >= 12
  tags:
    - log
```

**D1: Loki query endpoint and non-empty result predicate:**

URL: `GET /api/datasources/proxy/uid/loki/loki/api/v1/query?query=<LogQL>`

Successful non-empty response JSON structure:
```json
{"status":"success","data":{"resultType":"streams","result":[{"stream":{...},"values":[...]}]}}
```

Non-empty predicate: `grep -q '"result":\[{'` (checks that result is a non-empty array with at least one stream object).

**D2: Prometheus / Mimir instant-query endpoint:**

Prometheus: `GET /api/datasources/proxy/uid/prometheus/api/v1/query?query=<PromQL>`
Mimir: `GET /api/datasources/proxy/uid/mimir/api/v1/query?query=<PromQL>` (Mimir proxied datasource uses `/api/v1/query` not `/prometheus/api/v1/query` — the Grafana Mimir datasource in Telemetron is configured as type `prometheus` pointing at Mimir's `/prometheus` subpath; the Grafana proxy adds the correct prefix).

**Correction from CONTEXT.md D-99:** The CONTEXT.md text says `mimir` proxy uses `/prometheus/api/v1/query`. Verify the actual Mimir datasource URL in `roles/grafana/templates/datasources.yml.j2` — if the datasource URL already includes `/prometheus`, then the proxy endpoint from Grafana is `/api/datasources/proxy/uid/mimir/api/v1/query`. Confirmed from `roles/grafana/tasks/verify.yml` Step 7: `'http://localhost:{{ grafana_http_port }}/api/datasources/proxy/uid/mimir/api/v1/query?query=up'` (the verify step already works on leviathan — use this exact path for smoke parity).

Non-empty predicate for Prometheus/Mimir: `grep -q '"result":\[' && grep -q '"metric"'` (confirms non-empty result array with metric entries).

**D3: Tempo trace fetch — 404 behavior confirmed:**

Tempo returns `HTTP 404` with body `trace not found` when a trace is not yet ingested or not yet flushed from WAL into a queryable block. This is a documented, expected transient state (grafana/tempo issues #2650, #3192). The retry loop handles it.

Tempo via Grafana datasource proxy: `GET /api/datasources/proxy/uid/tempo/api/traces/<trace_id>`

Non-empty predicate: `grep -q '"batches":\['` on a 200 response. The retry condition is `until: smoke_assert_tempo is succeeded` — the task exits non-zero on `curl -fsS` when Tempo returns 404 (`-f` = fail on 4xx/5xx), which triggers the retry.

**Timing note:** For a monolithic Tempo instance, new traces are typically queryable within 5-30 seconds after ingestion (WAL flush to ingester queryable state). The 60-second budget (12 × 5s) covers this window comfortably for a single-host monolithic deployment.

**D4: Auth pattern**

Basic Auth header: `-u {{ grafana_admin_user }}:{{ grafana_admin_password }}` — matches the existing verify.yml Step 3-8 pattern exactly. The smoke playbook loads `secrets.yml` directly via `vars_files:` so it reads `grafana_admin_password` without the deploy playbook context.

**D5: Smoke playbook preamble**

```yaml
---
- name: Telemetron -- M1 acceptance smoke test
  hosts: telemetron
  gather_facts: true          # needed for ansible_date_time.epoch in run_id
  become: false

  vars_files:
    - "{{ inventory_dir }}/group_vars/all/secrets.yml"

  vars:
    smoke_trace_id: "{{ lookup('ansible.builtin.password', '/dev/null length=32 chars=hexdigits') | lower }}"
    smoke_span_id:  "{{ lookup('ansible.builtin.password', '/dev/null length=16 chars=hexdigits') | lower }}"
    smoke_run_id:   "{{ ansible_date_time.epoch }}"
```

### Finding E: Idempotent Host-Package NFS Role for EL8+/Ubuntu 22.04+

**Confirmed (HIGH confidence — Red Hat official docs + Ubuntu official docs + community.general.ufw module docs):**

**E1: Package names by distro family**

| ansible_os_family | Package name | Systemd service name |
|-------------------|-------------|---------------------|
| `RedHat` (RHEL, Rocky, AlmaLinux, CentOS 8+) | `nfs-utils` | `nfs-server.service` |
| `Debian` (Ubuntu 22.04+, Debian 11+) | `nfs-kernel-server` | `nfs-server.service` |

**Key finding:** Both distributions use `nfs-server.service` as the canonical systemd unit name. On Ubuntu, installing `nfs-kernel-server` creates the `nfs-kernel-server` alias name that some docs reference, but the actual unit is `nfs-server.service` on modern Ubuntu (22.04+). The upstream INSPQ `nfs_ubuntu.yml` calls `systemd: name: nfs-server state: restarted` (not `nfs-kernel-server.service`) — this confirms the single unit name works cross-distro.

**INSPQ observation:** The upstream `nfs_ubuntu.yml` uses `nfs-server` for the restart task at the end but `nfs-kernel-server` for the start/enable task. This inconsistency is an INSPQ bug. The Telemetron port should use `nfs-server.service` for BOTH start/enable and the handler (both distros).

**E2: Idempotent /etc/exports management**

`ansible.builtin.blockinfile` with a unique marker is the correct idiom. Critically: use a SINGLE `blockinfile` call with all exports rendered inside the Jinja block — NOT a `loop:` around `blockinfile` (each loop iteration replaces the block from the previous iteration, leaving only the last export in the file). The upstream INSPQ role already demonstrates this pattern correctly.

Telemetron export block shape:
```yaml
- name: Manage nfsd exports in /etc/exports
  ansible.builtin.blockinfile:
    path: /etc/exports
    marker: "# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK"
    block: |
      {% for export in nfsd_exports %}
      {{ export.path }} {{ export.allow }}
      {% endfor %}
    create: true
  notify: Reload nfsd exports
  when: nfsd_exports | length > 0
```

The `create: true` ensures `/etc/exports` exists even on a fresh host. The handler runs `exportfs -ra` (not service restart):

```yaml
- name: Reload nfsd exports
  ansible.builtin.command:
    cmd: exportfs -ra
  changed_when: false
```

`changed_when: false` keeps the handler idempotent from Ansible's perspective (exportfs -ra always returns 0).

**E3: Why NOT to manage firewalls in the role**

Consistent with Phase 1-5 roles: Telemetron roles do not configure firewalls (no `firewalld`, no `ufw` tasks). The upstream INSPQ role manages firewalls, which is an INSPQ-specific assumption. In a homelab single-LAN environment, the operator controls firewall policy. The `roles/nfsd/README.md` documents the required port (TCP 2049 for NFSv4) as an operator-action item, not a role task.

**E4: rpcbind on EL8+**

EL7 required enabling `rpcbind` separately. On EL8+, `nfs-server.service` has socket-activated rpcbind — `rpcbind` is pulled as a dependency and started automatically. No explicit `rpcbind` task needed when targeting EL8+.

**E5: Idempotency of core tasks**

| Task | Module | Idempotent? | Notes |
|------|--------|-------------|-------|
| Install package | `ansible.builtin.package: state: present` | YES | no-op if already installed |
| Enable/start service | `ansible.builtin.systemd: state: started enabled: yes` | YES | no-op if already running |
| Manage /etc/exports | `ansible.builtin.blockinfile` | YES | idempotent by marker; only notifies handler if content changed |
| exportfs -ra (handler) | `ansible.builtin.command: changed_when: false` | YES with `changed_when: false` | handler only fires when blockinfile reports changed |
| Create /srv/telemetron-nfs | `ansible.builtin.file: state: directory` | YES | no-op if exists |

**E6: No Gate 2 (image-pin), Gate 3 (secrets), Gate 5 (container healthcheck), Gate 7 (label-stamp), Gate 8 (parent-dir bind-mount)**

All container gates are N/A for nfsd — it has no container. The `roles/nfsd/README.md` must explicitly document that this role deviates from the container pattern (D-91) and list which gates apply and which are N/A.

### Finding F: Markdown Docs Conventions

**F1: Copy-pasteable commands**

Use fenced code blocks with explicit shell type annotation:
```
```bash
command here
```
```
Never wrap with angle brackets or italics. The reader must be able to copy the exact text.

**F2: Expected output snippets**

Inline expected output as a separate fenced block immediately after the command block, prefixed with a brief comment:
```
```
# Expected last line:
PLAY RECAP ****
leviathan : ok=36  changed=0  failed=0
```
```

For Grafana UI steps, use bold text to indicate what to look for: "Click **Dashboards** in the left sidebar. You should see **Loki Explore Landing** in the list."

**F3: ASCII signal-flow diagrams**

The existing `ARCHITECTURE.md` research file (`.planning/research/ARCHITECTURE.md`) already contains a complete ASCII signal-flow diagram. The public `docs/architecture.md` distills this into a cleaner version without internal planning references. Key conventions:
- Use `─►` for directional arrows in ASCII (or `-->` when Unicode is risky)
- Label each arrow with the protocol/port
- Use `┌─┐ │ └─┘` box-drawing characters for component boxes (renders in monospaced terminals and GitHub)
- Avoid wide lines (keep under 80 chars for `cat` terminal compatibility)

**F4: Port-allocation table**

The CLAUDE.md `### Port-allocation snapshot (homelab single-host)` table is the source of truth. The `docs/architecture.md` reproduces it essentially verbatim — it is already formatted as a Markdown table and reads cleanly in GitHub raw view.

**F5: Cross-linking**

`docs/quickstart.md` → `docs/inventory.md` for "building your own inventory"
`docs/quickstart.md` → `roles/grafana/README.md` "Reverse proxy" for production hardening
`docs/inventory.md` → `inventory/example-homelab/README.md` for the worked example
Top-level `README.md` → `docs/quickstart.md` as the primary "how to run this" reference

### Finding G: README Anti-Patterns for Technical Homelab Projects

**G1: What the current README does wrong**

- "Status: early. This is a clean-slate fork..." — buries the lede and signals "not ready"
- "Quick start: Coming soon as roles land in `roles/`." — a placeholder after 5 phases of shipped work
- Lists HAProxy and Hook Router as shipped components when neither is in M1
- No code block showing the actual three-command quickstart
- The value prop ("one-stop observability stack") appears but isn't backed up with "here is how to run it"

**G2: Effective README structure for technical homelab projects (synthesized from Loki, Prometheus, Vector, Grafana Alloy READMEs)**

```
# Project Name

One-sentence value prop.

## Quick start
[3-line code block: git clone, edit one file, run playbook]
Full walkthrough → docs/quickstart.md

## What's included
[Component table — only what's actually shipped]

## Requirements
[Minimal prerequisites — OS, Docker version, Ansible version]

## Origin
[Attribution — INSPQ fork, what was changed]
```

**G3: What NOT to include**

- Badge walls (CI status, coverage, version) — not applicable to an Ansible role collection
- Animated GIFs / screenshots — maintenance burden; break in raw view
- Marketing language ("enterprise-grade", "production-ready") — homelab audience is technical and will reject it
- Aspirational features listed as current — removes credibility when the reader tries to use them
- Internal references (D-XX decision IDs, `.planning/` paths)

**G4: "Status: early" replacement language**

Delete entirely. The README landing section should make the project's shipping status obvious through description ("bring up the full M1 stack") rather than a warning label. If there are known limitations, surface them in a `## Known limitations` section at the bottom, not in the opening paragraph.

### Finding H: OPS-04 Idempotency Contract

**H1: What "changed=0" means**

The Ansible PLAY RECAP line for a host shows:
```
hostname : ok=N  changed=0  failed=0  unreachable=0  skipped=M  rescued=0  ignored=0
```
`changed=0` means every task that ran on the second playbook execution reported no state change. Tasks that are skipped (due to `when:` conditions evaluating false) do not appear in `changed`.

**H2: Known false-changed sources in community.docker.docker_container**

Confirmed sources (community.docker GitHub issues #142, #1080):
1. **Image re-pull:** Using `pull: true` causes a changed report even when the image is unchanged. Telemetron roles use `pull: false` (the default) — images are pulled once, not re-pulled. Not applicable.
2. **Docker 29.0.0 port range normalization:** Docker 29 normalizes port ranges (e.g. `8080-8082:8080-8082`) into individual port mappings, causing community.docker to detect a diff on the second run. Fixed in community.docker 4.5.2+. Leviathan runs Docker 29 (per user memory `project_leviathan_uat_host`) — the collection version needs verification at plan 06-04 execute time.
3. **Command/entrypoint empty list handling:** Fixed in community.docker with `command_handling: correct`. Phase 1-5 roles do not set `command:` explicitly for most containers — not applicable.
4. **Non-deterministic template ordering:** Jinja `{% for k in dict %}` over an unsorted dict produces different output orderings across runs, causing a diff. Phase 1-5 templates already use `| sort` for dict iteration per OPS-04.

**H3: Second-run verification procedure**

```bash
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml
# Observe PLAY RECAP — confirm changed=0
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml
# Observe PLAY RECAP — must report changed=0 again
```

`--check --diff` is a dry-run pre-screen but is NOT the authoritative test — some modules behave differently in check mode. The actual second run is the OPS-04 gate.

**H4: nfsd-specific idempotency risks**

- `ansible.builtin.blockinfile` with a stable marker is inherently idempotent.
- `exportfs -ra` in the handler only fires when blockinfile reports changed — which only happens when `/etc/exports` content changes. `changed_when: false` on the command task prevents the handler's changed status from polluting the recap.
- `ansible.builtin.systemd: state: started` is idempotent (no-op when already running).
- `ansible.builtin.package: state: present` is idempotent (no-op when already installed).

### Finding I: `docs/architecture.md` Synthesis Pattern

**I1: Source materials available in `.planning/research/`**

Verified files:
- `ARCHITECTURE.md` — component table, signal-flow ASCII diagram, dependency graph, port table, cross-cutting concerns, anti-patterns, integration points. PRIMARY SOURCE for architecture.md.
- `PITFALLS.md` — homelab-relevant pitfalls (MinIO start-order race, Grafana UID mismatch, etc.). NOT directly in architecture.md but informs monolithic-mode tradeoffs bullet.
- `STACK.md` — per-role recommendation table, Three Decisions. PRIMARY SOURCE for component table and known-debt callout (MinIO archived).
- `FEATURES.md`, `SUMMARY.md` — supplementary, check if needed during plan execution.
- `CLAUDE.md` — port-allocation cheat sheet (directly table-formatted), version compatibility matrix, component table with `Pinned Tag` and `Why` columns. SECONDARY SOURCE — already written for clarity.

**I2: What needs rewriting for public consumption**

The ARCHITECTURE.md research file contains internal planning notes (D-XX references, reversibility notes, INSPQ comparisons, open questions). The public `docs/architecture.md` must:
- Remove all D-XX references
- Remove `.planning/` path references
- Remove "Open questions" and "Confidence" annotations
- Keep: ASCII diagram (cleaned up), port table, component table, monolithic-mode tradeoff summary, dependency graph narrative

The INSPQ attribution stays as a one-liner in the README origin section, not in architecture.md.

**I3: Architecture.md target structure (terse reference, ~3-4 pages)**

```markdown
# Architecture

## Overview
[One paragraph: single-host Docker, OTel gateway, LGTM + Alertmanager]

## Signal Flow
[ASCII diagram — distilled from ARCHITECTURE.md research]

## Components
[Table: Component | Image | Port | Mode | Purpose]

## Port Allocation
[Table: directly from CLAUDE.md port-allocation snapshot]

## Monolithic Mode (M1)
[4 bullets: Loki -target=all, Tempo -target=all, Mimir -target=all, MinIO single-node]

## Storage Dependencies
[Loki→loki-chunks, Tempo→tempo-traces, Mimir→3 buckets, Grafana→SQLite]

## Known Debt
[MinIO archived: see README; PromLens frozen: see roles/promlens/README.md]
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OTLP JSON payload | Custom serialization | Spec canonical JSON from opentelemetry-proto/examples | Exact field names, enum encoding, and string-vs-integer types are specified; hand-rolled JSON misses edge cases |
| NFS exports management | Custom file manipulation | `ansible.builtin.blockinfile` with marker | Idempotent by design; handles block replacement without leaving orphan lines |
| Random hex ID generation | Custom shell `od` or `head /dev/urandom` pipe | `lookup('ansible.builtin.password', '/dev/null length=32 chars=hexdigits')` | Single-expression, no temp file, works in Jinja context |
| Grafana query assertion | Custom HTTP library | `docker_container_exec` + `curl -fsS` (same as grafana verify.yml) | Already proven on leviathan; avoids auto_remove race (ansible/ansible#45272) |
| Multi-line shell in Lua filter | String concatenation | `string.gmatch(tag, "[^.]+")` iterator | Standard Lua idiom for splitting on delimiter; no external dependency |

---

## Common Pitfalls

### Pitfall 1: FB Tag asterisk expansion includes path components you don't expect

**What goes wrong:** With `Path /srv/telemetron-nfs/*/*.log` and `Tag nfs.*`, the asterisk expands to the FULL ABSOLUTE PATH with slashes replaced by dots. For `/srv/telemetron-nfs/oldbox/auth.log`, the tag becomes `nfs.srv.telemetron-nfs.oldbox.auth.log` — 5 dot-segments, not 2.

**Why it happens:** The asterisk replacement covers the entire file path from root, not just the wildcard-matched portion.

**How to avoid:** The Lua `hostname_from_nfs_tag` function must count segments correctly. Segment index 4 (1-indexed) is the hostname. Hardcode this constant and document it with an inline comment citing the exact path structure it assumes. If `nfsd_share_root` is changed to a path with a different depth, the Lua constant must also change.

**Warning signs:** `host` label on NFS-tailed logs shows `telemetron-nfs` (segment 3, off by one) instead of the actual hostname.

### Pitfall 2: Tempo 404 during smoke test retry exhaustion

**What goes wrong:** The `smoke_assert_tempo` task retries 12 times (60 seconds) but Tempo still returns 404 at the end, failing the smoke test.

**Why it happens:** In a single-host monolithic Tempo, traces should be queryable within seconds. If 60 seconds is insufficient, the OTel Collector likely failed to forward the trace (check OTel Collector logs for export errors) or the trace payload was malformed (incorrect traceId/spanId hex length).

**How to avoid:** Verify the trace payload with a manual `curl -v` before the smoke playbook runs in anger. Confirm OTel Collector `:4318` is reachable from the Ansible controller or the target host. The smoke task should run from the Ansible target host (not the controller), so `delegate_to` is not needed — the uri task runs on the target where OTel Collector is accessible at `localhost:4318`.

**Warning signs:** OTel Collector logs show `Failed to push trace data` or `connection refused`. Trace smoke task fails immediately (0 retries) rather than exhausting retries.

### Pitfall 3: blockinfile for /etc/exports with empty nfsd_exports

**What goes wrong:** When `nfsd_exports: []`, the blockinfile task renders an empty block between its markers. This is valid but leaves two orphan marker lines in `/etc/exports`. On a second run, the block content is empty again — idempotent but confusing.

**How to avoid:** Guard the blockinfile task with `when: nfsd_exports | length > 0`. When the list is empty, the task is skipped entirely. The handler is not triggered. `/etc/exports` is not touched. Consistent with D-93 ("fail-safe: no exports happen until the operator names a remote host").

### Pitfall 4: Lua filter NFS branch runs on Docker logs due to Match *

**What goes wrong:** If the NFS `[FILTER] lua` block uses `Match *` instead of `Match nfs.*`, it runs on Docker container logs too, where the tag is `docker.<id>`. The `hostname_from_nfs_tag` function returns `nil` for `docker.*` tags because they don't have enough dot-segments — `record["host"]` gets set to `"unknown-nfs-host"` on every Docker container log, overwriting the correct hostname.

**How to avoid:** The NFS Lua filter block MUST use `Match nfs.*`. The existing Docker Lua filter block uses `Match docker.*`. Neither uses `Match *`. This is already the design in Finding B.

### Pitfall 5: Smoke test reads secrets.yml with wrong path

**What goes wrong:** `vars_files: ["inventory/example-homelab/group_vars/all/secrets.yml"]` uses a relative path that only works when the playbook is run from the repo root. Operators running from a different working directory get a "vars file not found" error.

**How to avoid:** Use `{{ inventory_dir }}/group_vars/all/secrets.yml` which Ansible resolves relative to the inventory path regardless of working directory. This matches the implicit vars_files behavior of the `group_vars/all/` directory during normal playbook runs.

---

## Code Examples

### Verified Pattern: docker_container_exec + retries (from roles/grafana/tasks/verify.yml)

```yaml
# Source: roles/grafana/tasks/verify.yml Step 4 (verified on leviathan 2026-05-19)
- name: "Gate 9 -- canonical query (prometheus: up)"
  community.docker.docker_container_exec:
    container: "{{ grafana_container_name }}"
    argv:
      - /bin/sh
      - -c
      - |
        set -e
        BODY=$(curl -fsS -u {{ grafana_admin_user }}:{{ grafana_admin_password }} \
          'http://localhost:{{ grafana_http_port }}/api/datasources/proxy/uid/prometheus/api/v1/query?query=up')
        echo "$BODY" | grep -q '"result":\[' || { echo "prometheus query no result: $BODY"; exit 1; }
        echo "$BODY" | grep -q '"metric"' || { echo "prometheus query empty result: $BODY"; exit 1; }
        echo "canonical_query_prometheus_ok"
  register: grafana_verify_query_prom
  retries: 15
  delay: 4
  until: grafana_verify_query_prom is succeeded
  changed_when: false
  failed_when: grafana_verify_query_prom is failed and grafana_verify_query_prom.attempts | default(0) >= 15
```

The smoke test uses `retries: 12 / delay: 5` (vs verify.yml's `retries: 15 / delay: 4`) because the OPS-07 budget is exactly 60s.

### Verified Pattern: blockinfile for /etc/exports (from INSPQ nfsd upstream)

```yaml
# Source: ~/git/inspq/ansible/nfsd/tasks/nfs_centos7.yml (adapted for Telemetron)
- name: Manage nfsd exports in /etc/exports
  ansible.builtin.blockinfile:
    path: /etc/exports
    marker: "# {mark} TELEMETRON NFSD ANSIBLE MANAGED BLOCK"
    block: |
      {% for export in nfsd_exports %}
      {{ export.path }} {{ export.allow }}
      {% endfor %}
    create: true
  notify: Reload nfsd exports
  when: nfsd_exports | length > 0
```

### Verified Pattern: OTLP/HTTP push via ansible.builtin.uri

```yaml
# OTLP/HTTP log push to OTel Collector -- smoke producer
- name: Push synthetic log via OTLP/HTTP
  ansible.builtin.uri:
    url: "http://{{ otel_host | default('localhost') }}:{{ otel_otlp_http_port | default(4318) }}/v1/logs"
    method: POST
    body_format: json
    headers:
      Content-Type: "application/json"
    body: "{{ lookup('template', 'smoke_test/templates/log.json.j2') | from_json }}"
    status_code: 200
  tags:
    - log
```

### Verified Pattern: Lua Lua tag-prefix dispatch

```lua
-- Source: roles/fluentbit/files/enrich.lua (extension pattern for Phase 6)
function enrich(tag, timestamp, record)
    -- NFS path: tag = "nfs.srv.telemetron-nfs.<hostname>.<filename...>"
    if string.match(tag, "^nfs%.") then
        local parts = {}
        for part in string.gmatch(tag, "[^.]+") do
            parts[#parts + 1] = part
        end
        -- parts[1]=nfs, parts[2]=srv, parts[3]=telemetron-nfs, parts[4]=hostname
        -- This constant assumes share root = /srv/telemetron-nfs (depth 2 after /).
        local host = parts[4] or "unknown-nfs-host"
        record["host"]    = host
        record["service"] = "remote"
        record["job"]     = "remote-syslog"
        return 2, timestamp, record
    end

    -- Existing Docker path (unchanged from Plan 03-05)
    local container_id = container_id_from_tag(tag)
    -- ... rest of existing Docker logic ...
end
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `nfs-utils` / `nfs-kernel-server` | nfsd role | via `ansible.builtin.package` | distro default | — (host-package install is a role task) |
| `exportfs` | nfsd handler | ships with nfs-utils/nfs-kernel-server | — | — |
| OTel Collector `:4318` | smoke test producers | assumed running (Phase 3 landed) | 0.152.0 | — (pre-condition: deploy_docker.yml must have run) |
| Grafana `:3000` | smoke test assertions | assumed running (Phase 5 landed) | 13.0.1 | — |
| `curl` inside grafana container | smoke assertions (docker_container_exec) | confirmed present in grafana-oss image | built-in | — (same image confirmed in grafana verify.yml Phase 5) |
| `community.docker` collection | nfsd role wiring (deploy_docker.yml when:), smoke playbook | confirmed present (Phase 1) | 4.x | — |

**Missing dependencies with no fallback:** None — all dependencies are either already running (Phases 1-5) or installed as role tasks (nfs packages).

---

## State of the Art

| Old Approach (INSPQ upstream) | Telemetron M1 Approach | Impact |
|-------------------------------|------------------------|--------|
| Containerized nfsd (`erichough/nfs-server`) | Host-package nfsd (kernel NFS via systemd) | Avoids `--privileged` requirement; more reliable; archived image concern eliminated |
| EL7 yum-binary workaround in nfs_centos7.yml | `ansible.builtin.package: state: present` (EL8+) | Simpler; standard module; no Python binding workaround needed on EL8+ |
| Separate CentOS7 and Ubuntu task files | `when: ansible_os_family` branching in main.yml | Less file fragmentation; still distro-aware |
| Firewall management in nfsd role | No firewall management | Consistent with Phase 1-5 operator-manages-firewall pattern |
| `nfs_shares` variable name | `nfsd_exports` | Matches Telemetron naming convention (role-prefix) |
| French task names | English task names (OPS-05) | Required by project constraint |
| Smoke test = "does it start?" | Smoke test = synthetic signal through full pipeline | Proves end-to-end data path, not just process liveness |

**Deprecated/outdated:**
- EL7 target: The INSPQ `nfs_centos7.yml` contained a `yum -y install` binary workaround for a Python binding issue on OracleLinux 7 with a custom Python install. Targeting EL8+ eliminates this entirely.
- `rpcbind` explicit start (EL7 requirement): Not needed on EL8+ (socket-activated by nfs-server dependency).

---

## Open Questions

1. **Mimir datasource proxy path for smoke assertion**
   - What we know: `roles/grafana/tasks/verify.yml` Step 7 uses `/api/datasources/proxy/uid/mimir/api/v1/query?query=up` and this works on leviathan.
   - What's unclear: CONTEXT.md D-99 says `/prometheus/api/v1/query`. The actual path depends on how the Mimir datasource URL is configured in `roles/grafana/templates/datasources.yml.j2`.
   - Recommendation: At plan 06-02 implement time, check the rendered datasource URL for mimir; use the same path that verify.yml Step 7 already uses (proven correct on leviathan).

2. **FB tag segment depth if nfsd_share_root is not /srv/telemetron-nfs**
   - What we know: The Lua hostname extraction assumes exactly 3 leading segments (`nfs`, `srv`, `telemetron-nfs`) before the hostname.
   - What's unclear: If an operator overrides `nfsd_share_root` to a different depth (e.g. `/data/nfs`), the constant `parts[4]` would be wrong.
   - Recommendation: Hardcode the segment count as a Lua constant derived from the compile-time default path depth; document in `enrich.lua` and `roles/nfsd/README.md` that changing `nfsd_share_root` requires a corresponding update to the Lua extraction logic. This is a known limitation acceptable for M1.

3. **community.docker version on leviathan and Docker 29 port-range idempotency**
   - What we know: Docker 29 + community.docker < 4.5.2 can produce false-changed on port-range containers.
   - What's unclear: The exact community.docker version installed on leviathan.
   - Recommendation: At plan 06-04 verify time, run `ansible-galaxy collection list community.docker` on the controller. If < 4.5.2, upgrade before the idempotency gate run.

---

## Validation Architecture

The project does not use an automated test harness (TEST-01 is a v2 requirement). Validation is live-UAT on leviathan per D-109. No nyquist_validation section needed (`.planning/config.json` does not exist → treat as absent → include section).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual UAT on leviathan (SSH + Docker 29) |
| Config file | None — live host |
| Quick run command | `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags nfsd` |
| Full suite command | `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml` (followed by `playbooks/smoke_test.yml`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Exists? |
|--------|----------|-----------|-------------------|---------|
| LEGACY-01 | nfsd deploys when `enable_nfsd: true`; no-ops when false | manual-UAT | `ansible-playbook --tags nfsd` on leviathan with `enable_nfsd: true` then `false` | Role does not exist yet — Wave 0 |
| INV-01 | Full stack deploys from scratch on fresh host | manual-UAT | `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml` | Plan 06-04 verify |
| INV-03 | All 14 roles in deploy_docker.yml; per-role tags work | smoke (ansible syntax-check) | `ansible-playbook --syntax-check playbooks/deploy_docker.yml` | Partial — nfsd not yet wired |
| OPS-07 | Synthetic log+metric+trace visible in Grafana within 60s | automated-playbook | `ansible-playbook -i inventory/leviathan playbooks/smoke_test.yml` | Playbook does not exist yet — Wave 0 |
| DOCS-01 | architecture.md exists with components/signal-flow/ports | manual review | `test -f docs/architecture.md` | File does not exist yet |
| DOCS-02 | quickstart.md works step-by-step on fresh target | manual-UAT | Run verbatim on leviathan | File does not exist yet |
| DOCS-03 | inventory.md covers group_vars schema + secrets contract | manual review | `test -f docs/inventory.md` | File does not exist yet |
| DOCS-04 | README.md reflects M1 shipped state | manual review | `grep -v "Status: early" README.md` | README exists; needs rewrite |

### Wave 0 Gaps

- [ ] `roles/nfsd/` — entire role, all task files, defaults, handlers, README
- [ ] `inventory/example-homelab/group_vars/all/nfsd.yml` — `enable_nfsd: false` default + `nfsd_exports: []`
- [ ] `playbooks/smoke_test.yml` — new playbook
- [ ] `playbooks/smoke_test/templates/log.json.j2` — OTLP log payload
- [ ] `playbooks/smoke_test/templates/metric.json.j2` — OTLP metric payload
- [ ] `playbooks/smoke_test/templates/trace.json.j2` — OTLP trace payload
- [ ] `docs/architecture.md` — new file
- [ ] `docs/quickstart.md` — new file
- [ ] `docs/inventory.md` — new file
- [ ] Extension to `roles/fluentbit/files/enrich.lua` — NFS branch in `enrich()` function
- [ ] Extension to `roles/fluentbit/templates/fluent-bit.conf.j2` — conditional NFS `[INPUT] tail` + `[FILTER] lua` blocks

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 6 |
|-----------|-------------------|
| Tech stack — Ansible only | nfsd role is Ansible `ansible.builtin.package` + `systemd` + `blockinfile` — no Terraform/scripts |
| Tech stack — Docker for M1 | nfsd is the ONE exception (D-91 host-package); documented deviation |
| Components are fixed | No new components added in Phase 6 |
| Language — English only | All task `name:` strings must be English; upstream INSPQ nfsd has French names — full translation required |
| Naming — Locked | `nfsd_exports` (not `nfs_shares`); `enable_nfsd` (not `nfs_enable`) |
| Test surface — Single host | Leviathan UAT only; no molecule |
| Inventory portability | `inventory/example-homelab/group_vars/all/nfsd.yml` ships default-off |
| No vault_ prefix (D-90) | nfsd has no secrets in M1 — not applicable, but no `vault_` prefix if secrets are added later |
| Fluent Bit pinned to 4.2.3 | NFS tail input uses FB 4.2.3 `[INPUT] tail` syntax — no FB 5.x API surface |
| OTel Collector Contrib 0.152.0 | Smoke test targets `:4318` OTLP/HTTP endpoint available in this version |
| Grafana OSS 13.0.1 | Datasource-proxy paths used in smoke assertions match this version |
| GSD Workflow Enforcement | All edits go through `gsd:execute-phase` — no direct repo edits outside GSD |

---

## Sources

### Primary (HIGH confidence)
- Official OTLP spec — https://opentelemetry.io/docs/specs/otlp/#otlphttp — JSON encoding, content-type, status codes
- `opentelemetry-proto/examples/*.json` (GitHub) — canonical log/metric/trace JSON payloads verified verbatim
- Fluent Bit 4.1 tail input docs — https://docs.fluentbit.io/manual/4.1/data-pipeline/inputs/tail — Tag asterisk expansion, Mem_Buf_Limit, Path_Key, Read_from_Head, DB, Skip_Long_Lines
- Fluent Bit Lua filter docs — https://docs.fluentbit.io/manual/data-pipeline/filters/lua — return code contract (-1/0/1/2), callback signature
- Red Hat RHEL 8 NFS docs — https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/deploying_different_types_of_servers/deploying-an-nfs-server_deploying-different-types-of-servers — `nfs-utils` package, `nfs-server.service` unit
- Ubuntu 22.04 NFS docs — https://documentation.ubuntu.com/server/how-to/networking/install-nfs/ — `nfs-kernel-server` package, `nfs-server.service` unit
- `ansible.builtin.password` lookup docs — https://docs.ansible.com/ansible/latest/collections/ansible/builtin/password_lookup.html — `/dev/null` path, `length`, `chars` parameters
- `roles/grafana/tasks/verify.yml` (this repo, proven on leviathan 2026-05-19) — `docker_container_exec` + `retries: 15 / delay: 4` pattern
- `roles/fluentbit/files/enrich.lua` (this repo) — existing Lua filter structure for extension pattern
- `roles/fluentbit/templates/fluent-bit.conf.j2` (this repo) — existing conditional `[INPUT]` block pattern for NFS extension

### Secondary (MEDIUM confidence)
- Tempo GitHub issues #2650, #3192 — 404 behavior when trace not yet ingested; retry loop is correct fix
- community.docker GitHub issues #142, #1080, changelog — Docker 29 port-range normalization and false-changed sources
- geerlingguy/ansible-role-nfs (GitHub) — confirms `blockinfile` + handler pattern for `/etc/exports`; `exportfs -ra` preferred over service restart
- Ansible password lookup plugin (docs.ansible.com) — `/dev/null` generates per-run random without disk write

### Tertiary (LOW confidence, not used for decisions)
- community.general NFS articles (ansiblepilot.medium.com) — consulted for cross-verification; superseded by official docs

**Research date:** 2026-05-19
**Valid until:** 2026-06-19 (30 days — stable tech; Ansible/FB/OTLP APIs don't change rapidly)
