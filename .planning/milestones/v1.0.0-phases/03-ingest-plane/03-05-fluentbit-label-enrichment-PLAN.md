---
plan: 03-05-fluentbit-label-enrichment
phase: 03-ingest-plane
type: execute
wave: 5
depends_on: [03-01-node-exporter, 03-02-opentelemetry, 03-03-prometheus, 03-04-fluentbit]
requirements: [INGEST-07]
requirements_addressed: [INGEST-07]
gap_closure: true
closes_uat: ingest-07-service-job-labels
files_modified:
  - roles/fluentbit/defaults/main.yml
  - roles/fluentbit/files/enrich.lua
  - roles/fluentbit/templates/fluent-bit.conf.j2
  - roles/fluentbit/tasks/main.yml
  - roles/fluentbit/tasks/verify.yml
  - roles/fluentbit/README.md
  - roles/minio/tasks/main.yml
  - roles/loki/tasks/main.yml
  - roles/tempo/tasks/main.yml
  - roles/mimir/tasks/main.yml
  - roles/node_exporter/tasks/main.yml
  - roles/opentelemetry/tasks/main.yml
  - roles/prometheus/tasks/main.yml
  - roles/README.md
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/STATE.md
  - .planning/phases/03-ingest-plane/03-HUMAN-UAT.md
autonomous: true

must_haves:
  truths:
    - "After deploy, `curl http://<host>:3100/loki/api/v1/labels | jq '.data'` returns EXACTLY the five labels `{host, env, service, job, level}` (no high-cardinality keys)."
    - "`docker inspect telemetron-prometheus --format '{{.Config.Labels.org_telemetron_job}}'` returns `prometheus`; same shape returns the correct job name for each of the 8 stack containers."
    - "For a container deployed by an operator WITHOUT `org.telemetron.*` labels, Loki streams show `service=unlabeled` AND `job=<container_name>` for that container's logs."
    - "`grep -r '/var/run/docker.sock' roles/fluentbit/` returns no matches (security gate -- no docker socket mount)."
    - "`grep -E 'Time_System_Timezone +Etc/UTC|Multiline_Flush +5|Read_from_Head +false|storage\\.type +filesystem|storage\\.max_chunks_up +128' roles/fluentbit/templates/fluent-bit.conf.j2 | wc -l` returns 5 (Pitfall 6 mitigation pack preserved)."
  artifacts:
    - path: roles/fluentbit/files/enrich.lua
      provides: "Lua filter that reads /var/lib/docker/containers/<id>/config.v2.json, extracts org.telemetron.{service,job} Docker labels via string.match (NO cjson dependency), strips trailing -json suffix from tag-derived container_id, caches results in-memory with 300s TTL, returns enriched record."
      contains: "function enrich"
    - path: roles/fluentbit/templates/fluent-bit.conf.j2
      provides: "[FILTER] lua block referencing /fluent-bit/etc/enrich.lua function `enrich` placed BEFORE the existing [FILTER] modify allowlist_static block; bind-mount path for the Lua file documented."
      contains: "Name              lua"
    - path: roles/fluentbit/tasks/main.yml
      provides: "Verifies /var/lib/docker/containers RO bind-mount is present (it is, from Plan 03-04); adds enrich.lua bind-mount at /fluent-bit/etc/enrich.lua:ro; copies the Lua file from roles/fluentbit/files/ to the host config dir."
      contains: "enrich.lua"
    - path: roles/fluentbit/defaults/main.yml
      provides: "Three new knobs: fluentbit_enrich_lua_path (default /fluent-bit/etc/enrich.lua), fluentbit_enrich_cache_ttl_seconds (300), fluentbit_enrich_docker_root (/var/lib/docker/containers); plus fluentbit_unlabeled_service ('unlabeled')."
      contains: "fluentbit_enrich_cache_ttl_seconds"
    - path: roles/minio/tasks/main.yml
      provides: "docker_container task gains `labels:` argument with `org.telemetron.service: telemetron` + `org.telemetron.job: minio`."
      contains: "org.telemetron.job: minio"
    - path: roles/loki/tasks/main.yml
      provides: "docker_container task gains `labels:` with service=telemetron + job=loki."
      contains: "org.telemetron.job: loki"
    - path: roles/tempo/tasks/main.yml
      provides: "docker_container task gains `labels:` with service=telemetron + job=tempo."
      contains: "org.telemetron.job: tempo"
    - path: roles/mimir/tasks/main.yml
      provides: "docker_container task gains `labels:` with service=telemetron + job=mimir."
      contains: "org.telemetron.job: mimir"
    - path: roles/node_exporter/tasks/main.yml
      provides: "docker_container task gains `labels:` with service=telemetron + job=node_exporter."
      contains: "org.telemetron.job: node_exporter"
    - path: roles/opentelemetry/tasks/main.yml
      provides: "docker_container task gains `labels:` with service=telemetron + job=otel."
      contains: "org.telemetron.job: otel"
    - path: roles/prometheus/tasks/main.yml
      provides: "docker_container task gains `labels:` with service=telemetron + job=prometheus."
      contains: "org.telemetron.job: prometheus"
    - path: roles/fluentbit/tasks/main.yml
      provides: "FB's OWN docker_container also stamps service=telemetron + job=fluentbit so FB labels its own logs correctly."
      contains: "org.telemetron.job: fluentbit"
    - path: roles/fluentbit/README.md
      provides: "Rewrites 'Labeling operator apps' section: documents the org.telemetron.{service,job} Docker-label convention as THE M1 path (no longer deferred); adds 'Lua enrichment under load' guidance referring to SC4 retest; updates allowlist table showing all five labels now populated; updates Deviations from upstream INSPQ with D-47 amendment."
      contains: "org.telemetron.service"
    - path: roles/README.md
      provides: "Adds a line to the per-role port-acceptance checklist: 'Phase 4/5 role ports MUST stamp org.telemetron.{service,job} labels on their docker_container so Fluent Bit's Lua enrichment picks them up.'"
      contains: "org.telemetron"
    - path: .planning/REQUIREMENTS.md
      provides: "INGEST-07 row promoted from PARTIAL/[x]-with-flag to fully [x] SATISFIED (no PARTIAL flag); existing [x] checkbox stays as-is; description text unchanged."
      contains: "INGEST-07"
    - path: .planning/ROADMAP.md
      provides: "Phase 3 Plans list gains a `- [ ] 03-05-fluentbit-label-enrichment-PLAN.md -- INGEST-07 gap closure (FB Lua + docker-labels)` bullet after the existing 03-04 line."
      contains: "03-05-fluentbit-label-enrichment"
    - path: .planning/STATE.md
      provides: "Phase 3 FEATURE-COMPLETE marker rephrased to GAP-CLOSURE-IN-PROGRESS (or equivalent) reflecting the INGEST-07 PARTIAL closure work landed by this plan."
      contains: "GAP-CLOSURE-IN-PROGRESS"
    - path: .planning/phases/03-ingest-plane/03-HUMAN-UAT.md
      provides: "Gap entry `ingest-07-service-job-labels` status flips from `deferred` to `resolved`; resolution note references this plan."
      contains: "ingest-07-service-job-labels"
  key_links:
    - from: "Fluent Bit Lua filter (enrich.lua function `enrich`)"
      to: "/var/lib/docker/containers/<container_id>/config.v2.json on the host (RO bind-mount from Plan 03-04)"
      via: "io.open() + string.match patterns on raw JSON content (NO cjson) + record['service']/record['job'] assignment"
      pattern: "config\\.v2\\.json"
    - from: "Each role's `community.docker.docker_container` task"
      to: "Container metadata visible to Lua filter (Config.Labels['org.telemetron.{service,job}'])"
      via: "docker_container `labels:` argument with two key-value pairs"
      pattern: "org\\.telemetron\\.(service|job)"
    - from: "Rendered fluent-bit.conf [FILTER] lua block"
      to: "/fluent-bit/etc/enrich.lua inside the container (bind-mount of roles/fluentbit/files/enrich.lua)"
      via: "tasks/main.yml `ansible.builtin.copy` + container volumes list entry"
      pattern: "enrich\\.lua"
    - from: "INGEST-07 acceptance (all 5 labels populated)"
      to: "Lua filter populates record['service'] + record['job'] BEFORE allowlist_static modify filter adds host + env"
      via: "Filter chain ordering -- [FILTER] lua precedes [FILTER] modify allowlist_static in fluent-bit.conf.j2"
      pattern: "(?s)\\[FILTER\\]\\s+Name\\s+lua.*?\\[FILTER\\]\\s+Name\\s+modify\\s+Alias\\s+allowlist_static"
    - from: "FB tag `docker.<hex>-json` (Tag_Regex captures greedy basename)"
      to: "Bare container_id `<hex>` used to build the config.v2.json path"
      via: "`container_id_from_tag` in enrich.lua strips trailing `-json` suffix before path construction"
      pattern: ":sub\\(1, -6\\)"
---

<objective>
Close the INGEST-07 PARTIAL gap flagged by 03-VERIFICATION.md SC5 / 03-HUMAN-UAT.md gap entry `ingest-07-service-job-labels`. Promote `service` and `job` from the Q3 "container_name fallback / deferred Lua-filter" path into FIRST-CLASS, RUNTIME-POPULATED Loki labels driven by Docker container labels (`org.telemetron.service` + `org.telemetron.job`) read on the FB side by a Lua filter from the already-bind-mounted `/var/lib/docker/containers/<id>/config.v2.json` -- NO Docker socket, NO API access.

Purpose: deliver INGEST-07 in full -- "Fluent Bit ships only `{job, host, service, env, level}` to Loki" -- with `service` and `job` actually populated on every shipped record, not just documented as a deferral. Restores the alert -> logs correlation flow Phase 4's hook router depends on (it routes by `(alertname, job)`; the `job` label must be the same identity Loki indexes).

Output: a Lua filter file under `roles/fluentbit/files/enrich.lua`, three new role-defaults knobs, an updated `fluent-bit.conf.j2` with the Lua filter wired BEFORE the existing modify filters, an updated `tasks/main.yml` that copies the Lua file + bind-mounts it into the container, label stamps on ALL EIGHT existing telemetron containers (4 Phase-1+2 storage/backend roles + 4 Phase-3 ingest roles), a documentation amendment to `roles/fluentbit/README.md` replacing the deferred-Lua note with the actual M1 convention, a per-role port-acceptance addition in `roles/README.md` so future Phase 4/5 ports inherit the convention, REQUIREMENTS.md flag-removal, ROADMAP/STATE drift fixes, and UAT.md gap-entry status flip.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/03-ingest-plane/03-CONTEXT.md
@.planning/phases/03-ingest-plane/03-RESEARCH.md
@.planning/phases/03-ingest-plane/03-VERIFICATION.md
@.planning/phases/03-ingest-plane/03-HUMAN-UAT.md
@.planning/phases/03-ingest-plane/03-04-fluentbit-PLAN.md
@.planning/phases/03-ingest-plane/03-04-fluentbit-SUMMARY.md
@CLAUDE.md
@roles/README.md
@roles/fluentbit/defaults/main.yml
@roles/fluentbit/tasks/main.yml
@roles/fluentbit/tasks/verify.yml
@roles/fluentbit/templates/fluent-bit.conf.j2
@roles/fluentbit/README.md
@roles/minio/tasks/main.yml
@roles/loki/tasks/main.yml
@roles/tempo/tasks/main.yml
@roles/mimir/tasks/main.yml
@roles/node_exporter/tasks/main.yml
@roles/opentelemetry/tasks/main.yml
@roles/prometheus/tasks/main.yml
@playbooks/deploy_docker.yml

<interfaces>
<!-- The locked design from the gap_to_close block. Every executor task must honor these literal values. -->

### Path 2 label semantics (NON-NEGOTIABLE)
- `service` = `telemetron` for ALL stack components (STATIC literal -- every role stamps this exact value).
- `job` = per-component (DYNAMIC per container). Eight Phase-1..3 components:
  - `roles/minio/tasks/main.yml`               -> `org.telemetron.job: minio`
  - `roles/loki/tasks/main.yml`                -> `org.telemetron.job: loki`
  - `roles/tempo/tasks/main.yml`               -> `org.telemetron.job: tempo`
  - `roles/mimir/tasks/main.yml`               -> `org.telemetron.job: mimir`
  - `roles/node_exporter/tasks/main.yml`       -> `org.telemetron.job: node_exporter`
  - `roles/opentelemetry/tasks/main.yml`       -> `org.telemetron.job: otel`
  - `roles/prometheus/tasks/main.yml`          -> `org.telemetron.job: prometheus`
  - `roles/fluentbit/tasks/main.yml`           -> `org.telemetron.job: fluentbit`
- Phase 4/5 roles (alertmanager, hook_router, karma, grafana, promlens, nfsd) DO NOT YET EXIST. This plan MUST NOT touch them. Instead it leaves a convention note in `roles/README.md`.

### Source of truth (NON-NEGOTIABLE)
- Docker container `labels:` argument on the `community.docker.docker_container` task in each role.
- NOT static inventory vars (would be a "different identity per env" footgun).
- NOT image-name parsing (would couple labels to image tags).
- Operator apps opt in by setting the SAME labels on their own containers -- documented in `roles/fluentbit/README.md` "Labeling operator apps".

### Lua filter read source (NON-NEGOTIABLE)
- File: `/var/lib/docker/containers/<container_id>/config.v2.json` (sibling of `<container_id>-json.log` that FB already tails).
- Bind-mount already exists from Plan 03-04: `/var/lib/docker/containers:/var/lib/docker/containers:ro`. Verify in Task 4 below; add if missing.
- NO `/var/run/docker.sock` mount. NO Docker daemon API. The security posture is IDENTICAL to Plan 03-04's current state.
- The expected JSON structure (used by the Lua filter):
  ```json
  {
    "Name": "/prometheus",
    "Config": {
      "Labels": {
        "org.telemetron.service": "telemetron",
        "org.telemetron.job": "prometheus"
      }
    }
  }
  ```
- The Lua filter extracts via string.match patterns (NOT cjson -- see below):
  - `service` = match on `"org%.telemetron%.service"%s*:%s*"([^"]*)"`        (fallback: `"unlabeled"`)
  - `job`     = match on `"org%.telemetron%.job"%s*:%s*"([^"]*)"`            (fallback: container_name from `Name` field, leading `/` stripped)
  - `name`    = match on `"Name"%s*:%s*"/?([^"]*)"`                          (top-level Docker Name with optional leading `/`)

### Lua dependency posture -- string.match, NOT cjson (NON-NEGOTIABLE -- revised iteration 1)
- The `fluent/fluent-bit:4.2.3` image bundles LuaJIT but does NOT install `lua-cjson` (separate Alpine package, not in the upstream Dockerfile). `require("cjson.safe")` at FB startup would fail to resolve the module and FB would refuse to start -- WORSE than the gap.
- The Lua filter MUST use `string.match` (Lua-pattern-based) extraction on the raw file contents instead of full JSON parsing. The three fields we need (`service` label, `job` label, top-level `Name`) are all unique enough in the Docker `config.v2.json` serialization that pattern-based extraction is robust:
  - The label keys `"org.telemetron.service"` and `"org.telemetron.job"` are unique strings that do not appear elsewhere in `config.v2.json`.
  - The top-level `"Name"` field appears as a JSON key starting with `/<container_name>` per Docker's serialization (optionally without the leading `/` for some legacy versions; the pattern handles both).
- NO `require("cjson")` and NO `require("cjson.safe")` calls anywhere in enrich.lua. The negative acceptance grep enforces this.

### Tag -> container_id derivation (NON-NEGOTIABLE -- new in iteration 1)
- The existing Plan 03-04 [INPUT] tail Tag is `docker.<container_id>` populated from `Tag_Regex (?<container_id>[^/]+)\.log$`.
- The path `{{ fluentbit_docker_logs_path }}/*/*-json.log` causes the basename `<hex>-json.log` to satisfy the regex such that the greedy `[^/]+` captures `<hex>-json` (NOT the bare `<hex>` directory id).
- Consequence: the FB-set tag is `docker.<hex>-json`, NOT `docker.<hex>`.
- The Lua filter's `container_id_from_tag` MUST strip a trailing `-json` suffix from the captured id before using it to build the `config.v2.json` path. Concretely:
  ```lua
  local id = string.match(tag or "", "^docker%.(.+)$")
  if id and id:sub(-5) == "-json" then id = id:sub(1, -6) end
  return id
  ```
- We do NOT modify Plan 03-04's `Tag_Regex` (changing a shipped role template to fix a Lua-side bug would re-trigger a handler restart for the wrong reason and ripple the gap into the shipped FB role). The strip stays inside `enrich.lua` only.
- Acceptance grep enforces `grep -q ":sub(1, -6)" roles/fluentbit/files/enrich.lua`.
- The Lua file header comment MUST document why this strip exists so a future reader does not delete it as "dead code".

### Lua caching contract (NON-NEGOTIABLE)
- Cache key: bare container_id string (28+ hex chars, post-suffix-strip).
- Cache value: table `{service=..., job=..., container_name=..., expires_at=os.time()+TTL}`.
- TTL: 300 seconds (5 minutes) -- exposed as `fluentbit_enrich_cache_ttl_seconds` knob.
- Cache miss path: read JSON file as raw string, run three string.match patterns, populate cache, return enriched record.
- Cache hit path: return cached values without disk IO.
- JSON read failure (container died / file deleted): emit `service=unlabeled`, `job=unknown`, log a single warning per container_id to FB stderr.
- Expected line count: 60-150 lines of Lua.

### Filter chain ordering (NON-NEGOTIABLE)
The rendered fluent-bit.conf.j2 filter chain MUST be in this order:
1. `[FILTER] lua` (NEW -- enrich.lua function `enrich`) -- sets `service` + `job` record fields from Docker labels.
2. `[FILTER] modify Alias allowlist_static` (EXISTING) -- still adds `host` + `env` static labels.
3. `[FILTER] parser Alias extract_level` (EXISTING) -- regex extract of `level` from log content.
4. `[FILTER] modify Alias default_level` (EXISTING) -- adds default `level info`.
5. `[FILTER] modify Alias timestamp_fallback` (EXISTING -- Pitfall 6 Mode 2 -- DO NOT touch).

The Lua filter MUST be the FIRST filter in the chain so that downstream filters / output see `service` + `job` already set on the record.

### Pitfall 6 mitigation pack (NON-NEGOTIABLE)
ALL FIVE D-50 directives stay in the rendered [SERVICE] block UNCHANGED:
- `Time_System_Timezone {{ fluentbit_system_timezone }}` (default Etc/UTC)
- `Multiline_Flush {{ fluentbit_multiline_flush }}` (default 5)
- `Read_from_Head false` (per-INPUT)
- `storage.type filesystem`
- `storage.max_chunks_up {{ fluentbit_storage_max_chunks_up }}` (default 128)

If the Lua filter under load shifts the FB CPU+memory budget enough that SC4 fails (OOM under 5-min 1k req/s load), the executor MUST tune the Lua filter (longer TTL, smaller cache, simpler logic) and re-test. The verify task records the expectation; the SC4 retest itself is a UAT item (see Task 8).

### INSPQ grep gate scope (per Phase-2 D-25 reinterpretation)
Gate applies to YAML/J2/Lua/conf files ONLY. README documentation may mention upstream-org names. Each acceptance criterion below that uses `grep` for the INSPQ gate scopes to `--include='*.yml' --include='*.yaml' --include='*.j2' --include='*.lua' --include='*.conf'`.

### Six per-role port-acceptance gates (NON-NEGOTIABLE)
Apply to `roles/fluentbit/` AND to every other role whose `tasks/main.yml` this plan modifies:
1. Image-pin: no `:latest`.
2. INSPQ grep (code/config only): zero matches for `inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq`.
3. Non-ASCII (code/config only): zero matches for `[^\x00-\x7F]`.
4. Vault gate: no new vault references introduced (D-55 still holds).
5. Idempotency: no `state: restarted` introduced.
6. OPS-06: every modified docker_container retains its `restart_policy` + `healthcheck` (existing); the `labels:` addition is the ONLY structural change.

`ansible-playbook --syntax-check playbooks/deploy_docker.yml` MUST exit 0 across the whole playbook (the inventory-missing WARNING is acceptable per 03-VERIFICATION.md precedent).
</interfaces>

<gap_inline>
Source: 03-VERIFICATION.md (status: human_needed; score note: "5/5 must-haves verified by static audit; INGEST-07 PARTIAL flagged for operator UAT decision").

Failed truth (SC5): "Fluent Bit ships only the labels `{job, host, service, env, level}` to Loki". Static-audit finding: the rendered `roles/fluentbit/templates/fluent-bit.conf.j2` Adds only `host`, `env`, `level` via `[FILTER] modify`. `service` and `job` are documented in the FB README allowlist table as defaulting to container_name via Q3 fallback -- BUT NO RENDERED FILTER ACTUALLY PROMOTES THEM. The README's "Labeling operator apps" section flags this as a deferred Lua-filter Docker-API enrichment.

Reason this is now a blocker for M1 (not deferred):
- Phase 4's hook router routes alerts by `(alertname, job)`. The `job` label must be the same identity Loki indexes -- otherwise one-click alert -> logs correlation breaks.
- Phase 5's Grafana datasource provisioning ships `tracesToLogsV2` with `customQuery` that joins on `service` and `trace_id`. The `service` label must exist on Loki streams.
- Phase 6 OPS-07 smoke test queries `{job="<X>"}` in Grafana Loki Explore to prove the synthetic log landed. The query returns nothing if `job` isn't a Loki label.

Missing artifacts that this plan creates:
1. A Lua filter file `roles/fluentbit/files/enrich.lua` -- reads `/var/lib/docker/containers/<id>/config.v2.json`, extracts org.telemetron.{service,job} labels with fallbacks, caches with 300s TTL.
2. A `[FILTER] lua` block wired into `fluent-bit.conf.j2` BEFORE the existing modify filters.
3. Bind-mount of enrich.lua into the FB container via `tasks/main.yml`.
4. `labels:` argument on the `docker_container` task in eight existing telemetron roles (minio, loki, tempo, mimir, node_exporter, opentelemetry, prometheus, fluentbit).
5. README amendment in `roles/fluentbit/README.md` replacing the deferred-Lua note.
6. Convention note in `roles/README.md` so Phase 4/5 ports inherit the rule.
7. REQUIREMENTS.md INGEST-07 flag flip + UAT.md gap entry status flip + ROADMAP plan-list bullet + STATE.md FEATURE-COMPLETE marker rephrase.
</gap_inline>
</context>

<tasks>

<scope_note>
This plan ships 10 tasks across 16 files (the larger surface than a typical 2-3-task plan). The scope is justified by the atomic semantic of a single gap closure spanning eight roles whose `docker_container` labels constitute one logical contract; collapsing into fewer tasks would lose per-role acceptance grep granularity, which is the primary verification mechanism for the static audit. The plan stays autonomous (no checkpoints) and respects the file-ownership / wave-5 dependency posture. Reviewers: this is a deliberate exception to the 2-3-task heuristic, not an oversight.
</scope_note>

<task type="auto" id="03-05-01">
  <name>Task 1: Extend fluentbit/defaults/main.yml with Lua-enrichment knobs (TTL, paths, fallback values)</name>
  <files>roles/fluentbit/defaults/main.yml</files>
  <read_first>
    roles/fluentbit/defaults/main.yml
    .planning/phases/03-ingest-plane/03-04-fluentbit-PLAN.md
  </read_first>
  <action>
Edit `roles/fluentbit/defaults/main.yml`. APPEND a new section between the existing "D-50 buffer + timestamp discipline" block (lines 52-57 in the current file) and the "D-47 level extraction regex" block (current lines 59-62). Insert literally:

```yaml
# --- Lua enrichment for INGEST-07 service/job labels (Plan 03-05 gap closure) ---
# Fluent Bit's [FILTER] lua reads /var/lib/docker/containers/<id>/config.v2.json
# (already bind-mounted RO by tasks/main.yml -- the sibling of *-json.log that
# the [INPUT] tail consumes) and extracts the two Telemetron Docker labels
# `org.telemetron.service` + `org.telemetron.job`. Source of truth: each role's
# docker_container `labels:` argument stamps these at container creation.
#
# Fallback semantics:
#   - service unset -> "unlabeled"
#   - job unset     -> container_name (from JSON `Name` field, leading `/` stripped)
#
# NO /var/run/docker.sock mount. NO Docker daemon API access. The Lua filter
# only reads the on-disk JSON files that FB already has RO access to.
fluentbit_enrich_lua_path: "/fluent-bit/etc/enrich.lua"
fluentbit_enrich_docker_root: "/var/lib/docker/containers"
fluentbit_enrich_cache_ttl_seconds: 300
fluentbit_unlabeled_service: "unlabeled"
fluentbit_unlabeled_job: "unknown"
```

EXACT key names. Do NOT touch any other line in the file. Section ordering matters (Lua-enrichment block sits AFTER D-50, BEFORE level-extraction).
  </action>
  <verify>
    <automated>grep -q '^fluentbit_enrich_lua_path: "/fluent-bit/etc/enrich.lua"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_enrich_docker_root: "/var/lib/docker/containers"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_enrich_cache_ttl_seconds: 300$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_unlabeled_service: "unlabeled"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_unlabeled_job: "unknown"$' roles/fluentbit/defaults/main.yml &amp;&amp; awk '/fluentbit_storage_max_chunks_up/{a=NR}/fluentbit_enrich_lua_path/{b=NR}/fluentbit_level_regex/{c=NR}END{exit !(a&lt;b &amp;&amp; b&lt;c)}' roles/fluentbit/defaults/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/defaults/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Five literal lines present: `grep -q '^fluentbit_enrich_lua_path: "/fluent-bit/etc/enrich.lua"$'` AND `grep -q '^fluentbit_enrich_docker_root: "/var/lib/docker/containers"$'` AND `grep -q '^fluentbit_enrich_cache_ttl_seconds: 300$'` AND `grep -q '^fluentbit_unlabeled_service: "unlabeled"$'` AND `grep -q '^fluentbit_unlabeled_job: "unknown"$'`.
    - [ ] Insertion ordering: the new block sits AFTER `fluentbit_storage_max_chunks_up` and BEFORE `fluentbit_level_regex` (awk gate above).
    - [ ] No non-ASCII characters introduced.
    - [ ] No other line in the file changed.
  </acceptance_criteria>
  <done>Defaults file extended with five Lua-enrichment knobs in the correct ordinal position.</done>
</task>

<task type="auto" id="03-05-02">
  <name>Task 2: Author the Lua enrichment filter (roles/fluentbit/files/enrich.lua) -- string.match extraction, -json suffix strip, no cjson dependency</name>
  <files>roles/fluentbit/files/enrich.lua</files>
  <read_first>
    roles/fluentbit/templates/fluent-bit.conf.j2
    roles/fluentbit/defaults/main.yml
    .planning/phases/03-ingest-plane/03-04-fluentbit-SUMMARY.md
  </read_first>
  <action>
Create `roles/fluentbit/files/` directory if absent (mkdir parent). Write a new file `roles/fluentbit/files/enrich.lua` (NOT a Jinja template -- plain Lua) with the structure below. The function name MUST be `enrich` (referenced by the [FILTER] lua block in Task 3). The cache TTL is a Lua local constant in seconds; the docker root path is also a Lua local constant. Reference Fluent Bit Lua filter docs: https://docs.fluentbit.io/manual/pipeline/filters/lua

**Two hard constraints introduced in iteration 1 (do NOT regress):**

1. **NO `require("cjson")` / `require("cjson.safe")` ANYWHERE.** The `fluent/fluent-bit:4.2.3` image bundles LuaJIT but does NOT install `lua-cjson`. `require("cjson.safe")` at FB startup would fail and FB would refuse to start. We use Lua `string.match` patterns on the raw file content to extract the three fields we need (`service` label, `job` label, top-level `Name`). The Docker `config.v2.json` serialization is stable enough that pattern-based extraction is robust: the label keys are unique strings; the top-level `Name` field appears as a JSON key. The three patterns (verbatim, do NOT paraphrase):

   ```lua
   local svc  = raw:match('"org%.telemetron%.service"%s*:%s*"([^"]*)"')
   local job  = raw:match('"org%.telemetron%.job"%s*:%s*"([^"]*)"')
   local name = raw:match('"Name"%s*:%s*"/?([^"]*)"')
   ```

2. **The Plan 03-04 [INPUT] Tag_Regex captures `<hex>-json` (greedy) instead of bare `<hex>`.** The path `*/*-json.log` produces basename `<hex>-json.log`; the regex `(?<container_id>[^/]+)\.log$` is greedy and captures `<hex>-json`. FB therefore sets the tag to `docker.<hex>-json`. The Lua filter MUST strip a trailing `-json` suffix from the captured id before constructing the `config.v2.json` path. The strip stays inside enrich.lua only -- we do NOT modify Plan 03-04's Tag_Regex (changing a shipped role's template to fix a Lua-side bug would re-trigger a handler restart for the wrong reason).

   The relevant snippet inside `container_id_from_tag` (verbatim):
   ```lua
   local id = string.match(tag or "", "^docker%.(.+)$")
   if id and id:sub(-5) == "-json" then id = id:sub(1, -6) end
   return id
   ```
   The Lua file header comment MUST document why this strip exists so a future reader does not delete it as dead code (explain: greedy regex in Tag_Regex captures `<hex>-json`, we strip the suffix to recover the bare directory id used as the path segment).

EXACT content (60-150 lines; ASCII only; English comments):

```lua
-- roles/fluentbit/files/enrich.lua
-- Plan 03-05 -- INGEST-07 gap closure (iteration 1).
--
-- Fluent Bit [FILTER] lua callback that enriches every record with
-- `service` and `job` Loki labels derived from the source container's
-- Docker labels `org.telemetron.service` and `org.telemetron.job`.
--
-- Source of truth: /var/lib/docker/containers/<container_id>/config.v2.json
-- (RO bind-mount; already in place from Plan 03-04). NO Docker socket.
--
-- Dependency posture: NO cjson / NO cjson.safe. The fluent/fluent-bit:4.2.3
-- image bundles LuaJIT but not the lua-cjson Alpine package. We use
-- Lua string.match patterns on the raw JSON content to extract three
-- fields (service label, job label, top-level Name). The Docker
-- config.v2.json serialization is stable enough for pattern extraction:
-- the label keys are globally unique within the file and the top-level
-- "Name" appears with an optional leading "/".
--
-- Tag -> container_id derivation: Plan 03-04's [INPUT] tail uses the
-- Tag_Regex `(?<container_id>[^/]+)\.log$` against the path
-- `*/*-json.log`. The greedy `[^/]+` captures `<hex>-json` (NOT the bare
-- <hex> directory id) because the basename is `<hex>-json.log`. We strip
-- a trailing `-json` suffix on the captured id BEFORE using it as the
-- path segment for `/var/lib/docker/containers/<id>/config.v2.json`.
-- The strip lives in this Lua file only -- we deliberately do NOT touch
-- the shipped Plan 03-04 Tag_Regex (changing a role template to fix a
-- Lua-side bug would re-trigger a handler restart for the wrong reason).
-- DO NOT remove the suffix-strip without first reverting the Tag_Regex.
--
-- Fallbacks:
--   service: unset -> "unlabeled"
--   job:     unset -> container_name (Name field, leading "/" stripped)
--
-- In-memory cache keyed by container_id with 300s TTL avoids per-log-line
-- disk reads. Cache miss -> read JSON as raw string, pattern-match, populate.
-- JSON read failure (container died) -> emit service="unlabeled" + job="unknown"
-- and log a single stderr warning per container_id.

-- Tunables -- mirror roles/fluentbit/defaults/main.yml.
local DOCKER_ROOT = "/var/lib/docker/containers"
local CACHE_TTL_SECONDS = 300
local UNLABELED_SERVICE = "unlabeled"
local UNLABELED_JOB = "unknown"

-- Per-process in-memory cache.
-- key = container_id (string, post-suffix-strip)
-- value = { service=string, job=string, container_name=string, expires_at=number }
local cache = {}

-- Per-process set tracking which container_ids have already emitted a
-- "JSON read failed" stderr warning (so we warn once, not per log line).
local warned = {}

-- Extract container_id from the FB tag set by tasks/main.yml's
-- Tag_Regex. Greedy capture against `<hex>-json.log` yields `<hex>-json`,
-- so we strip the trailing `-json` (6 chars: `-json`) to recover the bare
-- container directory id used as the path segment.
local function container_id_from_tag(tag)
    -- FB tag shape from Plan 03-04 [INPUT] tail: "docker.<container_id>"
    -- where <container_id> includes the trailing "-json" per the greedy regex.
    local id = string.match(tag or "", "^docker%.(.+)$")
    if id and id:sub(-5) == "-json" then
        id = id:sub(1, -6)
    end
    return id
end

-- Read and pattern-match /var/lib/docker/containers/<id>/config.v2.json.
-- Returns service, job, container_name, ok. NO cjson dependency.
local function read_container_config(container_id)
    local path = DOCKER_ROOT .. "/" .. container_id .. "/config.v2.json"
    local f, err = io.open(path, "r")
    if not f then
        if not warned[container_id] then
            io.stderr:write(string.format(
                "[enrich.lua] WARN: cannot open %s: %s -- using fallbacks\n",
                path, tostring(err)))
            warned[container_id] = true
        end
        return nil, nil, nil, false
    end
    local raw = f:read("*all")
    f:close()
    if not raw or raw == "" then
        if not warned[container_id] then
            io.stderr:write(string.format(
                "[enrich.lua] WARN: empty config.v2.json at %s -- using fallbacks\n",
                path))
            warned[container_id] = true
        end
        return nil, nil, nil, false
    end
    -- Pattern-match the three fields. Patterns are robust because:
    --   - "org.telemetron.service" and "org.telemetron.job" are unique
    --     label keys that do not appear elsewhere in config.v2.json.
    --   - The top-level "Name" appears as a JSON key starting with /.
    -- NO cjson dependency -- the FB 4.2.3 image does not ship lua-cjson.
    local svc  = raw:match('"org%.telemetron%.service"%s*:%s*"([^"]*)"')
    local job  = raw:match('"org%.telemetron%.job"%s*:%s*"([^"]*)"')
    local name = raw:match('"Name"%s*:%s*"/?([^"]*)"') or ""
    if not svc or svc == "" then
        svc = UNLABELED_SERVICE
    end
    if not job or job == "" then
        if name ~= "" then
            job = name
        else
            job = UNLABELED_JOB
        end
    end
    return svc, job, name, true
end

-- Public callback. Signature per Fluent Bit Lua filter docs:
--   function name(tag, timestamp, record)
--   returns code, timestamp, record  -- code 2 = record modified
function enrich(tag, timestamp, record)
    local container_id = container_id_from_tag(tag)
    if not container_id then
        record["service"] = UNLABELED_SERVICE
        record["job"] = UNLABELED_JOB
        return 2, timestamp, record
    end

    local now = os.time()
    local entry = cache[container_id]
    if entry and entry.expires_at > now then
        record["service"] = entry.service
        record["job"] = entry.job
        return 2, timestamp, record
    end

    local svc, job, name, ok = read_container_config(container_id)
    if not ok then
        -- Read failed -- still emit the record with fallback labels.
        record["service"] = UNLABELED_SERVICE
        record["job"] = UNLABELED_JOB
        return 2, timestamp, record
    end

    cache[container_id] = {
        service = svc,
        job = job,
        container_name = name,
        expires_at = now + CACHE_TTL_SECONDS,
    }
    record["service"] = svc
    record["job"] = job
    return 2, timestamp, record
end
```

Constraints:
- Filename MUST be `enrich.lua` (referenced in fluent-bit.conf.j2 in Task 3).
- Function name MUST be `enrich`.
- NO `require("cjson")` and NO `require("cjson.safe")` (negative grep acceptance).
- Three `raw:match` patterns present using the exact literal patterns above.
- `-json` suffix strip present via `:sub(1, -6)` (acceptance grep).
- Suffix-strip is documented in the file header (explanation of why it exists).
- ASCII only.
- Line count between 60 and 150 (inclusive).
- On tag `docker.abc123def-json` the function `container_id_from_tag` MUST return `abc123def` (NOT `abc123def-json`); the constructed JSON path MUST end with `abc123def/config.v2.json`. A future executor reviewing this file should be able to verify the unit-test semantic by visual inspection: input `docker.abc123def-json` -> output `abc123def` -> path `/var/lib/docker/containers/abc123def/config.v2.json`.
  </action>
  <verify>
    <automated>test -d roles/fluentbit/files &amp;&amp; test -f roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "^function enrich(tag, timestamp, record)$" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "config.v2.json" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "org.telemetron.service" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "org.telemetron.job" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "CACHE_TTL_SECONDS = 300" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "UNLABELED_SERVICE" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "UNLABELED_JOB" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q "raw:match" roles/fluentbit/files/enrich.lua &amp;&amp; ! grep -q "require.*cjson" roles/fluentbit/files/enrich.lua &amp;&amp; grep -q ":sub(1, -6)" roles/fluentbit/files/enrich.lua &amp;&amp; ! grep -q "/var/run/docker.sock" roles/fluentbit/files/enrich.lua &amp;&amp; LINES=$(wc -l &lt; roles/fluentbit/files/enrich.lua) &amp;&amp; [ "$LINES" -ge 60 ] &amp;&amp; [ "$LINES" -le 150 ] &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/files/enrich.lua</automated>
  </verify>
  <acceptance_criteria>
    - [ ] File exists at exact path: `test -f roles/fluentbit/files/enrich.lua`.
    - [ ] Function name `enrich` exists at top level: `grep -q "^function enrich(tag, timestamp, record)$"`.
    - [ ] Reads correct JSON path: `grep -q "config.v2.json"`.
    - [ ] Looks up correct Docker label keys: `grep -q "org.telemetron.service"` AND `grep -q "org.telemetron.job"`.
    - [ ] TTL constant set to 300: `grep -q "CACHE_TTL_SECONDS = 300"`.
    - [ ] Fallback constants present: `grep -q "UNLABELED_SERVICE"` AND `grep -q "UNLABELED_JOB"`.
    - [ ] string.match extraction (positive): `grep -q "raw:match"`.
    - [ ] NO cjson dependency (negative): `! grep -q "require.*cjson"`.
    - [ ] `-json` suffix strip present: `grep -q ":sub(1, -6)"`.
    - [ ] NO Docker socket reference: `! grep -q "/var/run/docker.sock"`.
    - [ ] Line count: `wc -l` returns between 60 and 150.
    - [ ] ASCII-only: `! grep -qP '[^\x00-\x7F]'`.
  </acceptance_criteria>
  <done>Lua filter file exists with `enrich` callback, string.match-based label extraction from config.v2.json, -json suffix strip with header-comment rationale, 300s TTL cache, fallbacks, no cjson dependency, no socket access.</done>
</task>

<task type="auto" id="03-05-03">
  <name>Task 3: Wire [FILTER] lua block into fluent-bit.conf.j2 BEFORE existing modify filters</name>
  <files>roles/fluentbit/templates/fluent-bit.conf.j2</files>
  <read_first>
    roles/fluentbit/templates/fluent-bit.conf.j2
    roles/fluentbit/files/enrich.lua
    roles/fluentbit/defaults/main.yml
  </read_first>
  <action>
Edit `roles/fluentbit/templates/fluent-bit.conf.j2`. INSERT a new `[FILTER] lua` block IMMEDIATELY BEFORE the existing `[FILTER] modify` block whose `Alias` is `allowlist_static` (current line ~84). The new block MUST precede it -- so the Lua filter sets `service` + `job` record fields before allowlist_static adds `host` + `env`.

EXACT insertion (preserve surrounding lines, insert this block between the `{% endfor %}` of `fluentbit_extra_tail_paths` (current line ~81) and the `# D-47 label allowlist:` comment + `[FILTER] modify Alias allowlist_static` (current lines 83-89)):

```ini
# Plan 03-05: INGEST-07 service + job label enrichment.
# Reads /var/lib/docker/containers/<id>/config.v2.json (RO bind-mount;
# already mounted by tasks/main.yml -- sibling of *-json.log). Extracts
# org.telemetron.{service,job} Docker labels with container-name + 'unlabeled'
# fallbacks. NO Docker socket access. Cache TTL 300s (see enrich.lua).
[FILTER]
    Name              lua
    Alias             telemetron_enrich
    Match             docker.*
    script            {{ fluentbit_enrich_lua_path }}
    call              enrich

```

The block:
- Goes BEFORE the existing `allowlist_static` modify filter (so allowlist_static still adds host + env on TOP of the Lua-set service/job).
- Match pattern `docker.*` (matches the existing [INPUT] tail's `Tag docker.<container_id>`).
- Calls function `enrich` from `{{ fluentbit_enrich_lua_path }}` (defaults to `/fluent-bit/etc/enrich.lua`).
- Inline comment cites Plan 03-05 and explains the no-socket security posture.

Do NOT touch:
- The [SERVICE] block (Pitfall 6 mitigation pack stays UNTOUCHED).
- The [INPUT] tail block (in particular the `Tag_Regex` line -- iteration 1 confirmed the suffix-strip lives in enrich.lua, NOT here).
- The conditional extension knob blocks (system_logs / journald / extra_tail_paths).
- The other three [FILTER] modify blocks (allowlist_static, default_level, timestamp_fallback) -- they remain in their existing order.
- The [FILTER] parser extract_level block.
- The [OUTPUT] opentelemetry block.

NB: the existing `allowlist_static` modify filter currently has TWO `Add` lines (`host` + `env`). LEAVE BOTH. After Task 3 the filter chain reads: lua (sets service+job) -> modify allowlist_static (adds host+env) -> parser extract_level (regex level) -> modify default_level (fallback level=info) -> modify timestamp_fallback (Pitfall 6 mode 2).
  </action>
  <verify>
    <automated>grep -q "^\[FILTER\]$" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Name              lua$" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Alias             telemetron_enrich$" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "call              enrich$" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "fluentbit_enrich_lua_path" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Plan 03-05" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; awk '/Alias             telemetron_enrich/{a=NR}/Alias             allowlist_static/{b=NR}END{exit !(a&gt;0 &amp;&amp; b&gt;0 &amp;&amp; a&lt;b)}' roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Time_System_Timezone" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Multiline_Flush" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Read_from_Head    false" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "storage.type      filesystem" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "timestamp_fallback" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; ! grep -q "/var/run/docker.sock" roles/fluentbit/templates/fluent-bit.conf.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] [FILTER] lua block exists: `grep -q "Name              lua$"` AND `grep -q "Alias             telemetron_enrich$"` AND `grep -q "call              enrich$"`.
    - [ ] References the configurable path: `grep -q "fluentbit_enrich_lua_path"`.
    - [ ] Inline citation: `grep -q "Plan 03-05"`.
    - [ ] ORDERING -- lua filter BEFORE allowlist_static (awk gate compares line numbers).
    - [ ] Pitfall 6 mitigation pack UNCHANGED: `grep -q "Time_System_Timezone"` AND `grep -q "Multiline_Flush"` AND `grep -q "Read_from_Head    false"` AND `grep -q "storage.type      filesystem"`.
    - [ ] timestamp_fallback filter retained: `grep -q "timestamp_fallback"`.
    - [ ] ASCII-only.
    - [ ] No Docker socket reference introduced: `! grep -q "/var/run/docker.sock"`.
  </acceptance_criteria>
  <done>fluent-bit.conf.j2 has [FILTER] lua block first in chain, citing Plan 03-05; Pitfall 6 mitigation pack intact; Tag_Regex untouched; no socket reference.</done>
</task>

<task type="auto" id="03-05-04">
  <name>Task 4: Wire enrich.lua bind-mount into fluentbit/tasks/main.yml + confirm /var/lib/docker/containers RO bind-mount still present</name>
  <files>roles/fluentbit/tasks/main.yml</files>
  <read_first>
    roles/fluentbit/tasks/main.yml
    roles/fluentbit/defaults/main.yml
    roles/fluentbit/files/enrich.lua
  </read_first>
  <action>
Edit `roles/fluentbit/tasks/main.yml`. Two changes:

**Change A (copy the Lua file to the host config dir):** INSERT a new `ansible.builtin.copy` task IMMEDIATELY AFTER the existing "Render Fluent Bit parsers config (parsers.conf)" task (current lines 28-36) and BEFORE the "Ensure Fluent Bit buffer volume exists" task (current lines 38-43). The new task copies the role's `files/enrich.lua` to `{{ fluentbit_config_dir }}/enrich.lua` on the target host. Notify the same single restart handler.

EXACT new task block to insert:

```yaml
- name: Copy Fluent Bit Lua enrichment script (Plan 03-05 INGEST-07)
  ansible.builtin.copy:
    src: enrich.lua
    dest: "{{ fluentbit_config_dir }}/enrich.lua"
    mode: "0640"
  notify: restart fluentbit
  tags:
    - fluentbit
    - fluentbit-config
```

**Change B (bind-mount the Lua file into the container at the canonical FB etc path):** Edit the existing `community.docker.docker_container` task's `volumes:` list (current lines 93-95). The list currently has two entries:
- `"{{ fluentbit_config_dir }}/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro"`
- `"{{ fluentbit_config_dir }}/parsers.conf:/fluent-bit/etc/parsers.conf:ro"`

APPEND a third entry:
- `"{{ fluentbit_config_dir }}/enrich.lua:{{ fluentbit_enrich_lua_path }}:ro"`

**Verify (no change required):** The existing `mounts:` list (current lines 82-92) already contains:
```
- source: "{{ fluentbit_docker_logs_path }}"
  target: "{{ fluentbit_docker_logs_path }}"
  type: bind
  read_only: true
```
which IS the `/var/lib/docker/containers` RO bind-mount that the Lua filter depends on. If this entry is missing, ADD it. (Confirm via grep before continuing.)

Do NOT touch:
- The conditional healthcheck Jinja expression.
- The published_ports triple-conditional Jinja.
- The mounts: list (buffer volume + docker logs bind already correct).
- The `env: { TZ: ... }` block.
- The verify include_tasks at the end.
- The `notify: restart fluentbit` count (the new copy task brings the total from 2 to 3 -- this is expected and correct: all three rendered/copied files notify the same handler).
  </action>
  <verify>
    <automated>grep -q "name: Copy Fluent Bit Lua enrichment script" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "src: enrich.lua$" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "dest:.*fluentbit_config_dir.*enrich.lua" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "enrich.lua:.*fluentbit_enrich_lua_path.*:ro" roles/fluentbit/tasks/main.yml &amp;&amp; awk '/Render Fluent Bit parsers config/{a=NR}/Copy Fluent Bit Lua enrichment script/{b=NR}/Ensure Fluent Bit buffer volume/{c=NR}END{exit !(a&lt;b &amp;&amp; b&lt;c)}' roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "/var/lib/docker/containers" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "read_only: true" roles/fluentbit/tasks/main.yml &amp;&amp; [ "$(grep -c 'notify: restart fluentbit' roles/fluentbit/tasks/main.yml)" = "3" ] &amp;&amp; ! grep -qE "state:\s*restarted" roles/fluentbit/tasks/main.yml &amp;&amp; ! grep -q "/var/run/docker.sock" roles/fluentbit/tasks/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] New copy task exists: `grep -q "name: Copy Fluent Bit Lua enrichment script"` AND `grep -q "src: enrich.lua$"` AND `grep -q "dest:.*fluentbit_config_dir.*enrich.lua"`.
    - [ ] New bind-mount entry in `volumes:`: `grep -q "enrich.lua:.*fluentbit_enrich_lua_path.*:ro"`.
    - [ ] Copy task is positioned between parsers render and buffer-volume tasks (awk ordering gate).
    - [ ] /var/lib/docker/containers RO bind-mount still present: `grep -q "/var/lib/docker/containers"` AND `grep -q "read_only: true"`.
    - [ ] Three `notify: restart fluentbit` lines (one each for fluent-bit.conf, parsers.conf, enrich.lua).
    - [ ] D-19 enforced: `! grep -qE "state:\s*restarted"`.
    - [ ] NO Docker socket added: `! grep -q "/var/run/docker.sock"`.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>tasks/main.yml copies enrich.lua to host + bind-mounts it into container at fluentbit_enrich_lua_path; existing docker-logs RO bind retained; no socket added.</done>
</task>

<task type="auto" id="03-05-05">
  <name>Task 5: Stamp org.telemetron.{service,job} Docker labels on Phase-1+2 storage/backend role containers (minio, loki, tempo, mimir)</name>
  <files>roles/minio/tasks/main.yml, roles/loki/tasks/main.yml, roles/tempo/tasks/main.yml, roles/mimir/tasks/main.yml</files>
  <read_first>
    roles/minio/tasks/main.yml
    roles/loki/tasks/main.yml
    roles/tempo/tasks/main.yml
    roles/mimir/tasks/main.yml
  </read_first>
  <action>
For EACH of the four roles (`minio`, `loki`, `tempo`, `mimir`) edit `roles/<role>/tasks/main.yml`. Locate the `community.docker.docker_container:` task (the one that has `state: started`, `restart_policy: ...`, `networks: ...`, etc.). INSERT a `labels:` argument as a SIBLING key of the existing `state:`, `restart_policy:`, `networks:`, `mounts:`, `healthcheck:`, `env:`, etc. arguments. Place the `labels:` block IMMEDIATELY AFTER the existing `networks:` block (consistent visual ordering across all eight roles -- networks first identifies the container on the bridge, labels stamp identity).

EXACT block per role:

**roles/minio/tasks/main.yml** -- insert after the `networks:` block of the `Run MinIO server container` task:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: minio
```

**roles/loki/tasks/main.yml** -- insert after the `networks:` block of the Loki run-container task:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: loki
```

**roles/tempo/tasks/main.yml** -- insert after the `networks:` block of the Tempo run-container task:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: tempo
```

**roles/mimir/tasks/main.yml** -- insert after the `networks:` block of the Mimir run-container task:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: mimir
```

Constraints:
- The two label values per role are LITERAL strings (no Jinja vars) -- this guarantees the labels render identically regardless of inventory and avoids accidental rename drift.
- Indentation must match the surrounding `state:` / `restart_policy:` / `networks:` siblings of the same docker_container task (typically four spaces from column 0, since the task itself is indented two and the arguments four).
- Each role's existing INSPQ grep gate (Pitfall 9) must still pass AFTER the edit -- the literal `telemetron` does NOT trip the gate (it's the project name).
- No `state: restarted` introduced.
- ASCII-only.
- Do NOT touch any other key/value in the docker_container task.
  </action>
  <verify>
    <automated>grep -q "org.telemetron.service: telemetron$" roles/minio/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: minio$" roles/minio/tasks/main.yml &amp;&amp; grep -q "org.telemetron.service: telemetron$" roles/loki/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: loki$" roles/loki/tasks/main.yml &amp;&amp; grep -q "org.telemetron.service: telemetron$" roles/tempo/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: tempo$" roles/tempo/tasks/main.yml &amp;&amp; grep -q "org.telemetron.service: telemetron$" roles/mimir/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: mimir$" roles/mimir/tasks/main.yml &amp;&amp; for r in minio loki tempo mimir ; do awk -v r="$r" '/networks:/{a=NR}/org\.telemetron\.service: telemetron/{b=NR}END{exit !(a&gt;0 &amp;&amp; b&gt;0 &amp;&amp; a&lt;b)}' roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; for r in minio loki tempo mimir ; do ! grep -qE "state:\s*restarted" roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; for r in minio loki tempo mimir ; do ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; for r in minio loki tempo mimir ; do ! grep -qP '[^\x00-\x7F]' roles/$r/tasks/main.yml || exit 1 ; done</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Four files contain the literal label key/value pairs: `grep -q "org.telemetron.service: telemetron$"` AND `grep -q "org.telemetron.job: <role>$"` on each of minio, loki, tempo, mimir.
    - [ ] Per-role ordering: `labels:` block appears AFTER `networks:` block in each file (awk gate per role).
    - [ ] No `state: restarted` introduced anywhere.
    - [ ] INSPQ grep gate still passes on each of the four files.
    - [ ] ASCII-only on all four files.
  </acceptance_criteria>
  <done>Four Phase-1+2 role tasks/main.yml files each stamp the two Docker labels on their docker_container, preserving the INSPQ grep + non-ASCII gates and idempotency.</done>
</task>

<task type="auto" id="03-05-06">
  <name>Task 6: Stamp org.telemetron.{service,job} Docker labels on Phase-3 ingest role containers (node_exporter, opentelemetry, prometheus, fluentbit)</name>
  <files>roles/node_exporter/tasks/main.yml, roles/opentelemetry/tasks/main.yml, roles/prometheus/tasks/main.yml, roles/fluentbit/tasks/main.yml</files>
  <read_first>
    roles/node_exporter/tasks/main.yml
    roles/opentelemetry/tasks/main.yml
    roles/prometheus/tasks/main.yml
    roles/fluentbit/tasks/main.yml
  </read_first>
  <action>
Mirror Task 5's pattern for the four Phase-3 roles. EXACT block per role, inserted as a SIBLING key after `networks:` on the role's docker_container task:

**roles/node_exporter/tasks/main.yml** -- after the `networks:` block of the node_exporter run-container task:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: node_exporter
```

**roles/opentelemetry/tasks/main.yml** -- after the `networks:` block of the OTel run-container task. Job name `otel` per the gap_to_close locked enumeration (NOT `opentelemetry` -- aligns with the existing Docker container DNS alias `otel` set in Plan 03-02):
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: otel
```

**roles/prometheus/tasks/main.yml** -- after the `networks:` block of the Prometheus run-container task:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: prometheus
```

**roles/fluentbit/tasks/main.yml** -- after the `networks:` block of the Fluent Bit run-container task (around current line 65-68). FB labels its OWN container so FB's own log lines (which it tails from /var/lib/docker/containers/<fluentbit_id>/*-json.log) get `service=telemetron + job=fluentbit`:
```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: fluentbit
```

Same constraints as Task 5: literal strings, sibling of `state:`/`restart_policy:`/`networks:`, INSPQ grep clean, ASCII only, no `state: restarted`.

NB: this task does NOT modify the new `Copy Fluent Bit Lua enrichment script` task from Task 4 -- only the existing `community.docker.docker_container` task. Verify the three `notify: restart fluentbit` count from Task 4 is still 3.
  </action>
  <verify>
    <automated>grep -q "org.telemetron.service: telemetron$" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: node_exporter$" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q "org.telemetron.service: telemetron$" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: otel$" roles/opentelemetry/tasks/main.yml &amp;&amp; grep -q "org.telemetron.service: telemetron$" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: prometheus$" roles/prometheus/tasks/main.yml &amp;&amp; grep -q "org.telemetron.service: telemetron$" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "org.telemetron.job: fluentbit$" roles/fluentbit/tasks/main.yml &amp;&amp; for r in node_exporter opentelemetry prometheus fluentbit ; do awk -v r="$r" '/networks:/{a=NR}/org\.telemetron\.service: telemetron/{b=NR}END{exit !(a&gt;0 &amp;&amp; b&gt;0 &amp;&amp; a&lt;b)}' roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; [ "$(grep -c 'notify: restart fluentbit' roles/fluentbit/tasks/main.yml)" = "3" ] &amp;&amp; for r in node_exporter opentelemetry prometheus fluentbit ; do ! grep -qE "state:\s*restarted" roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; for r in node_exporter opentelemetry prometheus fluentbit ; do ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; for r in node_exporter opentelemetry prometheus fluentbit ; do ! grep -qP '[^\x00-\x7F]' roles/$r/tasks/main.yml || exit 1 ; done</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Four files contain literal label key/value pairs with correct job per role: `node_exporter`, `otel`, `prometheus`, `fluentbit`.
    - [ ] Per-role ordering: labels: block after networks: block in each file.
    - [ ] FB notify count still 3 (Task 4 invariant preserved).
    - [ ] No `state: restarted` introduced.
    - [ ] INSPQ grep clean on all four files.
    - [ ] ASCII-only on all four files.
  </acceptance_criteria>
  <done>Four Phase-3 role tasks/main.yml files each stamp the two Docker labels; FB labels its own container; all six per-role gates remain green.</done>
</task>

<task type="auto" id="03-05-07">
  <name>Task 7: Update verify.yml -- add post-restart Lua-filter sanity assertion + SC4 retest hook</name>
  <files>roles/fluentbit/tasks/verify.yml</files>
  <read_first>
    roles/fluentbit/tasks/verify.yml
    roles/fluentbit/templates/fluent-bit.conf.j2
    roles/fluentbit/files/enrich.lua
  </read_first>
  <action>
Edit `roles/fluentbit/tasks/verify.yml`. APPEND TWO new tasks after the existing Step 2 (`/api/v1/health` 200 probe) but BEFORE any closing comment. Both new tasks are non-blocking sanity assertions -- they validate that the rendered config + Lua file are present and self-consistent, but the authoritative "labels are populated in Loki under load" check is a UAT item (Phase 6 OPS-07 plus the SC4 retest documented in `roles/fluentbit/README.md` Verification scope section -- updated in Task 8).

**Step 3 -- assert rendered fluent-bit.conf contains the [FILTER] lua block on the host:**
```yaml
- name: Verify rendered fluent-bit.conf contains [FILTER] lua block (INGEST-07)
  ansible.builtin.command:
    cmd: "grep -q 'Alias             telemetron_enrich' {{ fluentbit_config_dir }}/fluent-bit.conf"
  changed_when: false
  tags:
    - fluentbit
    - fluentbit-verify
```

**Step 4 -- assert enrich.lua is bind-mounted and readable inside the container:**
```yaml
- name: Verify enrich.lua is bind-mounted inside Fluent Bit container (INGEST-07)
  ansible.builtin.command:
    cmd: "docker exec {{ fluentbit_container_name }} test -r {{ fluentbit_enrich_lua_path }}"
  changed_when: false
  tags:
    - fluentbit
    - fluentbit-verify
```

Constraints:
- Both tasks use `changed_when: false` (read-only checks, mirror Phase-2 D-32 + W7 convention).
- Both are tagged `fluentbit, fluentbit-verify` to match the existing verify steps.
- Step 3 greps the rendered file on the HOST (after the template renders it); Step 4 `docker exec`s into the container to confirm the bind-mount worked.
- ASCII-only.
- NO end-to-end Loki query assertion here -- that's Phase 6 OPS-07.
- NO synthetic load test here -- that's the SC4 retest UAT item documented in Task 8's README update.
- The existing Step 1a (HEALTHCHECK poll) and Step 1b (Running fallback) and Step 2 (/api/v1/health 200) MUST remain untouched.
- Stylistic note: `ansible.builtin.command` + `grep` is brittle vs `slurp` + content checks but functional; documented here as a deliberate minor stylistic choice (slurp refactor deferred -- not blocking for INGEST-07 closure).
  </action>
  <verify>
    <automated>grep -q "Verify rendered fluent-bit.conf contains \[FILTER\] lua block" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "Verify enrich.lua is bind-mounted inside Fluent Bit container" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "telemetron_enrich" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "fluentbit_enrich_lua_path" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "docker exec" roles/fluentbit/tasks/verify.yml &amp;&amp; [ "$(grep -c 'changed_when: false' roles/fluentbit/tasks/verify.yml)" -ge 3 ] &amp;&amp; grep -q "/api/v1/health" roles/fluentbit/tasks/verify.yml &amp;&amp; awk '/api\/v1\/health/{a=NR}/Verify rendered fluent-bit.conf/{b=NR}END{exit !(a&gt;0 &amp;&amp; b&gt;0 &amp;&amp; a&lt;b)}' roles/fluentbit/tasks/verify.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/tasks/verify.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Both new tasks present by name.
    - [ ] Step 3 references `telemetron_enrich` alias.
    - [ ] Step 4 references `fluentbit_enrich_lua_path` and uses `docker exec`.
    - [ ] At least three `changed_when: false` (Steps 2/3/4).
    - [ ] Existing `/api/v1/health` Step 2 retained AND ordered BEFORE the new steps.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>verify.yml gains two non-blocking Lua-sanity assertions while preserving the M1 acceptance gate (Step 2 /api/v1/health) ordering.</done>
</task>

<task type="auto" id="03-05-08">
  <name>Task 8: Rewrite roles/fluentbit/README.md sections that documented the Q3 deferral (Loki label allowlist + Labeling operator apps + Deviations from upstream + Verification scope SC4 retest note)</name>
  <files>roles/fluentbit/README.md</files>
  <read_first>
    roles/fluentbit/README.md
    roles/fluentbit/files/enrich.lua
    roles/fluentbit/templates/fluent-bit.conf.j2
    roles/fluentbit/defaults/main.yml
  </read_first>
  <action>
Edit `roles/fluentbit/README.md` with four targeted section rewrites. Preserve every section heading and the surrounding prose; rewrite ONLY the bullet/table content + the specific paragraphs flagged below.

**Section A -- `## Loki label allowlist (D-47)`** (currently lines 54-74):

Replace the table rows for `service` and `job` AND the "Q3 simplification" paragraph. New table content (keep the existing two-column shape):

| Label     | Source                                                                 |
|-----------|------------------------------------------------------------------------|
| `host`    | `{{ ansible_hostname }}` rendered at deploy time (static literal)      |
| `env`     | `{{ telemetron_env | default('homelab') }}` rendered at deploy time    |
| `service` | Docker label `org.telemetron.service` (M1 convention: `telemetron`); fallback `unlabeled` |
| `job`     | Docker label `org.telemetron.job` (M1 convention: per-component); fallback container_name from JSON `Name` field |
| `level`   | regex-extracted from log line via `level_extractor` parser; `info` default |

Replace the Q3-simplification paragraph with:

```
The `service` and `job` labels are populated at runtime by a `[FILTER] lua`
script (`roles/fluentbit/files/enrich.lua`) that reads each source container's
`/var/lib/docker/containers/<id>/config.v2.json` -- the sibling of the JSON
log file Fluent Bit already tails. The script extracts the two Docker labels
`org.telemetron.service` and `org.telemetron.job` (M1 convention: each
telemetron stack role stamps these on its `docker_container` at creation
time), caches results per container_id with a 300-second TTL, and falls
back to `service=unlabeled` + `job=<container_name>` when a container is
not stamped. NO Docker socket is mounted -- the Lua filter only reads the
on-disk JSON files Fluent Bit already has RO access to via the bind-mount
from Plan 03-04.
```

**Section B -- `## Labeling operator apps`** (currently lines 76-96):

REPLACE the entire section body (keep the heading). New body:

```
Operator workloads colocated on the Telemetron Docker host opt into the
Loki label scheme by stamping two Docker labels on their own
containers at creation time:

| Label key                  | Value                              | Purpose                              |
|----------------------------|------------------------------------|--------------------------------------|
| `org.telemetron.service`   | a stable service identifier        | populates Loki `service` label       |
| `org.telemetron.job`       | a per-component identifier         | populates Loki `job` label           |

The Fluent Bit Lua filter (`roles/fluentbit/files/enrich.lua`) picks
up these labels from the container's `config.v2.json` on the host and
applies them to every log line shipped to Loki. Unlabeled operator
containers still ship logs -- they just land with `service=unlabeled`
and `job=<container_name>` until the operator stamps the convention
labels.

Stamping pattern in docker run:

```bash
docker run -d \
  --network telemetron \
  --label org.telemetron.service=myapp \
  --label org.telemetron.job=myapp-web \
  myapp:1.2.3
```

In docker-compose:

```yaml
services:
  myapp-web:
    image: myapp:1.2.3
    networks: [telemetron]
    labels:
      org.telemetron.service: myapp
      org.telemetron.job: myapp-web
```

In an Ansible role using `community.docker.docker_container`:

```yaml
- community.docker.docker_container:
    name: myapp-web
    image: myapp:1.2.3
    networks:
      - name: telemetron
    labels:
      org.telemetron.service: myapp
      org.telemetron.job: myapp-web
```

The eight Phase-1..3 telemetron stack roles (minio, loki, tempo, mimir,
node_exporter, opentelemetry, prometheus, fluentbit) all stamp these
labels per Plan 03-05; Phase 4/5 role ports inherit the convention via
the per-role port-acceptance checklist in `roles/README.md`.
```

**Section C -- `## Deviations from upstream INSPQ (D-25)`** -- in the existing "### Added (Pitfall 6 mitigation pack -- THE biggest D-25 improvement)" subsection (currently lines 385-416), APPEND a new bullet at the end of the Added subsection:

```
- **Lua-filter Docker-label enrichment (Plan 03-05 D-47 amendment)** -- a
  `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) reads each
  source container's `/var/lib/docker/containers/<id>/config.v2.json`
  and extracts `org.telemetron.service` + `org.telemetron.job` Docker
  labels onto the record. M1 convention -- replaces the Q3 simplification
  that defaulted `service` and `job` to `container_name`. NO Docker socket
  mount; the Lua filter only reads the JSON files that Fluent Bit's tail
  already bind-mounts RO from /var/lib/docker/containers.
```

**Section D -- `## Verification scope`** (currently lines 318-326): APPEND a new paragraph at the end of the existing prose:

```
Plan 03-05 added two non-blocking verify-task assertions that confirm
the rendered `[FILTER] lua` block exists in the host-rendered config
and that `enrich.lua` is readable inside the container via the bind-
mount. The full Lua-under-load contract -- the SC4 retest (5-minute
synthetic load at >= 1k req/s without OOM, mirrored from
03-VERIFICATION.md's human_verification entry) -- is a UAT item: per-
log-line Lua execution shifts the FB CPU+memory budget, and if SC4
regresses under load, the Lua filter must be tuned (longer TTL, smaller
cache, simpler logic). The default TTL of 300 seconds + per-container
cache entry is sized to keep the per-log-line work to a cache lookup
plus two record-field assignments under steady state.
```

Constraints:
- ALL OTHER sections of the README remain UNCHANGED (variables table, vault keys, tags, modes, volumes, healthcheck, operator access, security model, idempotency, port-acceptance gates, deprecation notes -- DO NOT touch).
- **NARROW SCOPE -- iteration 1 revision:** Remove or revise lines that contain the exact phrases `Q3 simplification` and `deferred Lua-filter Docker-API enhancement` (and minor permutations such as `deferred Lua-filter`). Leave all OTHER uses of the word `deferred` untouched -- those are correct, unrelated deferrals (Q9 smoke deferral to Phase 6 OPS-07, multi-region forward modes, opt-in nfsd, Phase 6 OPS-07 smoke gate, future-milestone Garage migration) that MUST stay. A literal executor reading this prose should NOT touch the Q9 / Phase 6 / nfsd / multi-region paragraphs.
- ASCII-only outside the existing Deviations from upstream section's Dropped subsection (which already contains French task names as historical artifacts -- those stay per Phase-2 D-25 reinterpretation).
- The README's Variables table can optionally be appended with the four new knobs (`fluentbit_enrich_lua_path`, `fluentbit_enrich_docker_root`, `fluentbit_enrich_cache_ttl_seconds`, `fluentbit_unlabeled_service`, `fluentbit_unlabeled_job`); not strictly required for INGEST-07 closure but good operator hygiene -- include for completeness.
  </action>
  <verify>
    <automated>grep -q "org.telemetron.service" roles/fluentbit/README.md &amp;&amp; grep -q "org.telemetron.job" roles/fluentbit/README.md &amp;&amp; grep -q "enrich.lua" roles/fluentbit/README.md &amp;&amp; grep -q "config.v2.json" roles/fluentbit/README.md &amp;&amp; grep -q "300-second TTL" roles/fluentbit/README.md &amp;&amp; grep -q "NO Docker socket" roles/fluentbit/README.md &amp;&amp; grep -q "Plan 03-05" roles/fluentbit/README.md &amp;&amp; grep -q "SC4 retest" roles/fluentbit/README.md &amp;&amp; ! grep -q "Q3 simplification" roles/fluentbit/README.md &amp;&amp; ! grep -q "deferred Lua-filter" roles/fluentbit/README.md &amp;&amp; grep -q "Phase 6 OPS-07" roles/fluentbit/README.md &amp;&amp; grep -q "## Loki label allowlist" roles/fluentbit/README.md &amp;&amp; grep -q "## Labeling operator apps" roles/fluentbit/README.md &amp;&amp; grep -q "## Deviations from upstream" roles/fluentbit/README.md &amp;&amp; grep -q "## Verification scope" roles/fluentbit/README.md</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All four target sections updated with the new content (key literals present: org.telemetron.{service,job}, enrich.lua, config.v2.json, 300-second TTL, NO Docker socket, Plan 03-05, SC4 retest).
    - [ ] Q3 deferral language gone: `! grep -q "Q3 simplification"` AND `! grep -q "deferred Lua-filter"`.
    - [ ] Q9 / Phase 6 OPS-07 smoke deferral PRESERVED: `grep -q "Phase 6 OPS-07"`.
    - [ ] All existing section headings preserved (Loki label allowlist, Labeling operator apps, Deviations from upstream, Verification scope).
    - [ ] Other sections (variables, vault, tags, modes, volumes, healthcheck, operator access, security model, idempotency, port-acceptance gates, deprecation notes) NOT touched -- spot-check by ensuring the variables-table line for `fluentbit_image_tag` is still present (`grep -q 'fluentbit_image_tag.*4.2.3'`).
  </acceptance_criteria>
  <done>README documents the org.telemetron.{service,job} convention as the M1 default, drops Q3 deferral language, preserves unrelated deferrals (Q9 / Phase 6 / multi-region / nfsd), adds SC4 retest UAT note.</done>
</task>

<task type="auto" id="03-05-09">
  <name>Task 9: Add a per-role port-acceptance line in roles/README.md so Phase 4/5 ports inherit the org.telemetron.{service,job} convention</name>
  <files>roles/README.md</files>
  <read_first>
    roles/README.md
  </read_first>
  <action>
Edit `roles/README.md`. APPEND a new gate (Gate 7) to the existing "Per-role port-acceptance gates" section (currently lines 38-60), AFTER Gate 6 (the README gate). EXACT new block:

```markdown
**7. Telemetron label-stamp gate (Plan 03-05; INGEST-07):** every `community.docker.docker_container` task in a Telemetron role MUST include a `labels:` argument with the two key/value pairs:

```yaml
labels:
  org.telemetron.service: telemetron
  org.telemetron.job: <component>
```

`<component>` matches the role name (e.g. `prometheus`, `loki`, `node_exporter`) so that Fluent Bit's `[FILTER] lua` enrichment (`roles/fluentbit/files/enrich.lua`) picks them up from `/var/lib/docker/containers/<id>/config.v2.json` and ships them as the `service` + `job` Loki labels (INGEST-07 allowlist). Phase 4 (alertmanager, hook_router) and Phase 5 (grafana, karma, promlens) role ports MUST stamp these labels. No Docker socket access is added; the Lua filter only reads the bind-mounted JSON files Fluent Bit already tails.
```

Constraints:
- New gate appended AFTER Gate 6, BEFORE any closing newline / EOF.
- The fenced YAML block inside the bullet uses three backticks (matching the existing README's code-fence style).
- The literal `<component>` is intentional (placeholder); the convention text explains the substitution.
- ASCII-only.
- Other rows in the planned-roles status table (currently lines 7-22) NOT touched.
  </action>
  <verify>
    <automated>grep -q "Telemetron label-stamp gate" roles/README.md &amp;&amp; grep -q "org.telemetron.service: telemetron" roles/README.md &amp;&amp; grep -q "org.telemetron.job:" roles/README.md &amp;&amp; grep -q "enrich.lua" roles/README.md &amp;&amp; grep -q "config.v2.json" roles/README.md &amp;&amp; grep -q "Phase 4.*alertmanager" roles/README.md &amp;&amp; grep -q "Phase 5" roles/README.md &amp;&amp; awk '/Per-role port-acceptance gates/{a=NR}/Telemetron label-stamp gate/{b=NR}END{exit !(a&gt;0 &amp;&amp; b&gt;a)}' roles/README.md &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/README.md</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Gate 7 heading exists: `grep -q "Telemetron label-stamp gate"`.
    - [ ] Convention values present: `grep -q "org.telemetron.service: telemetron"` AND `grep -q "org.telemetron.job:"`.
    - [ ] References the Lua filter + JSON path: `grep -q "enrich.lua"` AND `grep -q "config.v2.json"`.
    - [ ] References Phase 4 (alertmanager) AND Phase 5: forward-looking guidance for the un-ported roles.
    - [ ] Gate 7 appears AFTER the existing per-role port-acceptance gates heading (awk ordering gate).
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>roles/README.md gains Gate 7 documenting the org.telemetron.{service,job} stamping convention; future Phase 4/5 role ports inherit it.</done>
</task>

<task type="auto" id="03-05-10">
  <name>Task 10: Flip REQUIREMENTS.md INGEST-07 + 03-HUMAN-UAT.md gap entry status + add ROADMAP plan-list bullet + rephrase STATE.md FEATURE-COMPLETE marker + run all port-acceptance gates + final syntax check</name>
  <files>.planning/REQUIREMENTS.md, .planning/phases/03-ingest-plane/03-HUMAN-UAT.md, .planning/ROADMAP.md, .planning/STATE.md</files>
  <read_first>
    .planning/REQUIREMENTS.md
    .planning/phases/03-ingest-plane/03-HUMAN-UAT.md
    .planning/ROADMAP.md
    .planning/STATE.md
    roles/fluentbit/README.md
    roles/README.md
    roles/fluentbit/files/enrich.lua
    roles/fluentbit/templates/fluent-bit.conf.j2
    roles/fluentbit/tasks/main.yml
    playbooks/deploy_docker.yml
  </read_first>
  <action>
Five sub-steps. All edits are surgical -- modify ONLY the lines flagged below.

**Sub-step A -- REQUIREMENTS.md INGEST-07 row:**

Edit `.planning/REQUIREMENTS.md` line 43 (the INGEST-07 bullet). It currently reads (preserve the existing `[x]` checkbox):

```
- [x] **INGEST-07**: Fluent Bit ships only a small allowlist of labels to Loki: `{job, host, service, env, level}`. High-cardinality fields go to Loki structured metadata, not labels. Allowlist documented in `roles/fluentbit/README.md`.
```

REPLACE the bullet body with (keep the `- [x] **INGEST-07**:` prefix; just update the post-colon description to remove the PARTIAL flag implicitly carried by 03-VERIFICATION.md and add the implementation pointer):

```
- [x] **INGEST-07**: Fluent Bit ships only a small allowlist of labels to Loki: `{job, host, service, env, level}`. `service` and `job` are populated at runtime by a `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) that reads each source container's `/var/lib/docker/containers/<id>/config.v2.json` and extracts the Docker labels `org.telemetron.service` and `org.telemetron.job` (each telemetron stack role stamps these on its container). High-cardinality fields go to Loki structured metadata, not labels. Allowlist documented in `roles/fluentbit/README.md`.
```

**Sub-step B -- 03-HUMAN-UAT.md gap entry flip:**

Edit `.planning/phases/03-ingest-plane/03-HUMAN-UAT.md` lines 66-74 (the `## Gaps` block). Locate the `ingest-07-service-job-labels:` entry. REPLACE the `status: deferred` line with `status: resolved`. APPEND a new field `resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md` directly below the status line. Also rewrite the `decision_needed:` block (which lives below status) to a `resolution:` block that summarizes:

The replacement YAML block (preserve exact indentation -- the existing entry is two-space-indented under `- ingest-07-service-job-labels:`):

```yaml
- ingest-07-service-job-labels:
    description: |
      INGEST-07 PARTIAL -- `roles/fluentbit/templates/fluent-bit.conf.j2` originally Add'd only `host`/`env`/`level` via `[FILTER] modify`. The required `service` and `job` labels were documented in the README allowlist table as "default to container_name via Q3 fallback", but no rendered filter actually promoted them.
    status: resolved
    resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md
    severity: minor
    resolution: |
      Plan 03-05 adds a `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) that reads `/var/lib/docker/containers/<id>/config.v2.json` (already bind-mounted RO from Plan 03-04 -- no Docker socket) and extracts the Docker labels `org.telemetron.service` and `org.telemetron.job`. All eight Phase-1..3 telemetron stack roles stamp these labels on their `docker_container` task; Phase 4/5 role ports inherit the convention via Gate 7 in `roles/README.md`. The Lua filter caches per-container lookups with a 300s TTL; SC4 (5-min 1k-req/s OOM resistance) re-tested as a UAT item per the README Verification scope section.
```

**Sub-step C -- ROADMAP.md Phase 3 plan-list bullet (new in iteration 1):**

Edit `.planning/ROADMAP.md`. Locate the Phase 3 Plans block (around lines 67-71). It currently reads:

```
- [x] 03-01-node-exporter-PLAN.md -- node_exporter v1.11.1 role port (INGEST-08); Wave 1
- [x] 03-02-opentelemetry-PLAN.md -- OTel Collector Contrib 0.152.0 role port with D-44 amendment + D-43 dual-exporter + D-51 docker_stats (INGEST-04, INGEST-05); Wave 2
- [x] 03-03-prometheus-PLAN.md -- Prometheus 3.11.3 role port with 4 baseline alert rules + Pitfall 3 relabel defaults + remote_write to Mimir (INGEST-01, INGEST-02, INGEST-03); Wave 3
- [x] 03-04-fluentbit-PLAN.md -- Fluent Bit 4.2.3 role port with D-46 role inversion + D-47 label allowlist + D-50 Pitfall 6 mitigation pack (INGEST-06, INGEST-07); Wave 4
```

APPEND a fifth bullet after the 03-04 line:

```
- [ ] 03-05-fluentbit-label-enrichment-PLAN.md -- INGEST-07 gap closure (FB Lua + docker-labels); Wave 5
```

ALSO update the `**Plans**:` count near the top of the Phase 3 section. If it currently reads `**Plans**: 4 plans`, change to `**Plans**: 5 plans`.

**Sub-step D -- STATE.md FEATURE-COMPLETE marker rephrase (new in iteration 1):**

Edit `.planning/STATE.md`. Locate the line that reads (currently line 122 in the Accumulated Context / Decisions block):

```
- [Phase 03-ingest-plane]: Phase 3 FEATURE-COMPLETE: all four ingest plane roles ported (node_exporter, opentelemetry, prometheus, fluentbit); deploy_docker.yml orchestrates minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus -> fluentbit; canonical Phase-3 role shape proven in four patterns (stateless no-config, two-template production+verify, three-template config+rules, two-template production+parsers)
```

REPLACE the `FEATURE-COMPLETE` token with `GAP-CLOSURE-IN-PROGRESS` and adjust the prose minimally so it reads:

```
- [Phase 03-ingest-plane]: Phase 3 GAP-CLOSURE-IN-PROGRESS: all four ingest plane roles ported (node_exporter, opentelemetry, prometheus, fluentbit); deploy_docker.yml orchestrates minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus -> fluentbit; canonical Phase-3 role shape proven in four patterns (stateless no-config, two-template production+verify, three-template config+rules, two-template production+parsers); INGEST-07 PARTIAL gap closure landed by Plan 03-05.
```

Preserve all other lines in STATE.md (do NOT touch the frontmatter, progress block, or any other decision line).

**Sub-step E -- run all port-acceptance gates and syntax check:**

Run the following commands. The acceptance gate below treats each as MUST pass:

1. Image-pin (no `:latest` in any modified role):
   `! grep -rE 'image:.*:latest' roles/fluentbit/ roles/minio/tasks/main.yml roles/loki/tasks/main.yml roles/tempo/tasks/main.yml roles/mimir/tasks/main.yml roles/node_exporter/tasks/main.yml roles/opentelemetry/tasks/main.yml roles/prometheus/tasks/main.yml`

2. INSPQ grep gate (code/config only -- YAML/J2/Lua/conf):
   `! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.lua' --include='*.conf'` AND repeat for each of the seven other modified `roles/<r>/tasks/main.yml` files.

3. Non-ASCII gate (code/config only):
   `! grep -rPl '[^\x00-\x7F]' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.lua' --include='*.conf'` AND repeat the per-file check on each modified `roles/<r>/tasks/main.yml`.

4. Vault gate (no new vault refs):
   `! grep -rE '{{ *vault_' roles/fluentbit/files/ roles/fluentbit/templates/fluent-bit.conf.j2 roles/fluentbit/tasks/main.yml`

5. Idempotency gate (no `state: restarted` anywhere modified):
   `! grep -rE 'state:\s*restarted' roles/fluentbit/ roles/minio/tasks/main.yml roles/loki/tasks/main.yml roles/tempo/tasks/main.yml roles/mimir/tasks/main.yml roles/node_exporter/tasks/main.yml roles/opentelemetry/tasks/main.yml roles/prometheus/tasks/main.yml`

6. OPS-06 retained (every modified docker_container still has restart_policy + healthcheck reference):
   For each role in {fluentbit, minio, loki, tempo, mimir, node_exporter, opentelemetry, prometheus}: `grep -q "restart_policy:" roles/<r>/tasks/main.yml` AND `grep -q "healthcheck:" roles/<r>/tasks/main.yml`. (Note: prometheus/node_exporter/opentelemetry/mimir/tempo use conditional `healthcheck:` Jinja expressions; the literal `healthcheck:` token still appears.)

7. Plan 03-05's new gate: `! grep -q "/var/run/docker.sock" roles/fluentbit/files/enrich.lua roles/fluentbit/templates/fluent-bit.conf.j2 roles/fluentbit/tasks/main.yml`. (NB: a separate Plan 03-02 OTel does mount `/var/run/docker.sock` -- that's the existing D-52 docker_stats receiver, NOT new from this plan. The acceptance gate scopes to fluentbit files only.)

8. ROADMAP/STATE drift sanity:
   `grep -q "03-05-fluentbit-label-enrichment" .planning/ROADMAP.md` AND `! grep -q "Phase 3 FEATURE-COMPLETE" .planning/STATE.md` (the FEATURE-COMPLETE token has been rephrased to GAP-CLOSURE-IN-PROGRESS in the Phase-3 decision line) AND `grep -q "GAP-CLOSURE-IN-PROGRESS" .planning/STATE.md`.

9. Syntax check: `ansible-playbook --syntax-check playbooks/deploy_docker.yml 2>&1 | grep -q "playbook:.*deploy_docker.yml"`. The inventory-missing WARNING is acceptable per 03-VERIFICATION.md precedent (exit 0 with WARNING).

If ANY of 1-9 fails, the executor MUST fix the offending file and re-run before committing this task.
  </action>
  <verify>
    <automated>grep -q "INGEST-07.*Fluent Bit ships only" .planning/REQUIREMENTS.md &amp;&amp; grep -q "enrich.lua" .planning/REQUIREMENTS.md &amp;&amp; grep -q "org.telemetron.service" .planning/REQUIREMENTS.md &amp;&amp; grep -q "status: resolved" .planning/phases/03-ingest-plane/03-HUMAN-UAT.md &amp;&amp; grep -q "resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md" .planning/phases/03-ingest-plane/03-HUMAN-UAT.md &amp;&amp; grep -q "03-05-fluentbit-label-enrichment" .planning/ROADMAP.md &amp;&amp; ! grep -q "Phase 3 FEATURE-COMPLETE" .planning/STATE.md &amp;&amp; grep -q "GAP-CLOSURE-IN-PROGRESS" .planning/STATE.md &amp;&amp; ! grep -rE 'image:.*:latest' roles/fluentbit/ &amp;&amp; ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.lua' --include='*.conf' &amp;&amp; ! grep -rPl '[^\x00-\x7F]' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.lua' --include='*.conf' &amp;&amp; ! grep -rE '{{ *vault_' roles/fluentbit/files/ roles/fluentbit/templates/fluent-bit.conf.j2 roles/fluentbit/tasks/main.yml &amp;&amp; ! grep -rE 'state:\s*restarted' roles/fluentbit/ &amp;&amp; for r in fluentbit minio loki tempo mimir node_exporter opentelemetry prometheus ; do grep -q "restart_policy:" roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; for r in fluentbit minio loki tempo mimir node_exporter opentelemetry prometheus ; do grep -q "healthcheck:" roles/$r/tasks/main.yml || exit 1 ; done &amp;&amp; ! grep -q "/var/run/docker.sock" roles/fluentbit/files/enrich.lua &amp;&amp; ! grep -q "/var/run/docker.sock" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; ! grep -q "/var/run/docker.sock" roles/fluentbit/tasks/main.yml &amp;&amp; ansible-playbook --syntax-check playbooks/deploy_docker.yml 2>&amp;1 | grep -q "playbook:.*deploy_docker.yml"</automated>
  </verify>
  <acceptance_criteria>
    - [ ] REQUIREMENTS.md INGEST-07 row updated with Lua-filter + Docker-label description.
    - [ ] 03-HUMAN-UAT.md gap entry status is `resolved` AND has `resolved_by` field.
    - [ ] ROADMAP.md Phase 3 plan list contains the 03-05 bullet: `grep -q "03-05-fluentbit-label-enrichment" .planning/ROADMAP.md`.
    - [ ] STATE.md FEATURE-COMPLETE marker rephrased: `! grep -q "Phase 3 FEATURE-COMPLETE" .planning/STATE.md` AND `grep -q "GAP-CLOSURE-IN-PROGRESS" .planning/STATE.md`.
    - [ ] Image-pin gate passes (no `:latest`).
    - [ ] INSPQ grep gate passes in code/config files only.
    - [ ] Non-ASCII gate passes in code/config files only.
    - [ ] Vault gate passes (no new vault refs).
    - [ ] Idempotency gate passes (no `state: restarted`).
    - [ ] OPS-06 retained on every modified docker_container task.
    - [ ] No `/var/run/docker.sock` reference introduced anywhere in fluentbit files.
    - [ ] `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0 (warning about missing inventory acceptable).
  </acceptance_criteria>
  <done>REQUIREMENTS.md flag flipped, UAT gap entry resolved, ROADMAP bullet added, STATE.md marker rephrased, all gates green, syntax check exits 0. INGEST-07 promoted from PARTIAL to fully SATISFIED.</done>
</task>

</tasks>

<verification>
**Static verification (executor runs each):**

1. All ten task-level acceptance_criteria pass.
2. `find roles/fluentbit -type f | sort` includes the new `roles/fluentbit/files/enrich.lua` file (alongside existing defaults/main.yml, tasks/main.yml, tasks/verify.yml, templates/fluent-bit.conf.j2, templates/parsers.conf.j2, handlers/main.yml, meta/main.yml, README.md).
3. `roles/fluentbit/templates/fluent-bit.conf.j2` filter chain ordering: `[FILTER] lua` (alias telemetron_enrich) precedes `[FILTER] modify` (alias allowlist_static); both precede `[FILTER] parser` (alias extract_level); existing `timestamp_fallback` modify filter retained.
4. All eight modified `roles/<r>/tasks/main.yml` files contain `org.telemetron.service: telemetron` + `org.telemetron.job: <role>` (with `otel` for opentelemetry).
5. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
6. `roles/README.md` Gate 7 documents the label-stamp convention.
7. `roles/fluentbit/README.md` no longer mentions Q3 simplification / deferred Lua-filter; documents the M1 convention; Q9 / Phase 6 OPS-07 / nfsd / multi-region deferrals preserved.
8. `.planning/REQUIREMENTS.md` INGEST-07 description references `enrich.lua` and `org.telemetron.service`.
9. `.planning/phases/03-ingest-plane/03-HUMAN-UAT.md` gap entry `ingest-07-service-job-labels` shows `status: resolved` + `resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md`.
10. `.planning/ROADMAP.md` Phase 3 plan list has the 03-05 bullet; plan count updated.
11. `.planning/STATE.md` Phase-3 FEATURE-COMPLETE marker rephrased to GAP-CLOSURE-IN-PROGRESS.
12. Pitfall 6 mitigation pack still intact in fluent-bit.conf.j2 (Etc/UTC, Multiline_Flush 5, Read_from_Head false, storage.type filesystem, storage.max_chunks_up 128).
13. `enrich.lua` contains `:sub(1, -6)` (`-json` suffix strip), `raw:match` (string.match extraction), and NO `require(.*cjson)` (negative grep -- cjson dependency removed per iteration 1 fix).

**Live verification (deferred to UAT after homelab boot):**

14. `ansible-playbook --tags fluentbit` (and the eight other affected role tags) completes; all eight containers come up healthy.
15. `docker inspect telemetron-<r> --format '{{json .Config.Labels}}' | jq -r '."org.telemetron.service",."org.telemetron.job"'` returns `telemetron` + the role-specific job for each of the eight containers.
16. `docker exec telemetron-fluentbit test -r /fluent-bit/etc/enrich.lua` exits 0.
17. After at least one container log line has been tailed and shipped, `curl http://<host>:3100/loki/api/v1/labels | jq -r '.data[]' | sort` returns AT MOST the five labels `env`, `host`, `job`, `level`, `service` (high-cardinality keys absent). This is SC5's literal "ships only" assertion.
18. `curl 'http://<host>:3100/loki/api/v1/label/job/values'` returns the per-component job names: `prometheus`, `loki`, `tempo`, `mimir`, `node_exporter`, `otel`, `fluentbit`, `minio` (plus any unlabeled operator containers as their container_name).
19. **SC4 retest:** 5-minute synthetic load at >=1k req/s against `:4318/v1/metrics` does NOT OOM `telemetron-otel` AND does NOT OOM `telemetron-fluentbit` (the Lua filter cache + TTL hold under load). If FB OOMs, tune `fluentbit_enrich_cache_ttl_seconds` upward or simplify enrich.lua per Task 8 README note.
20. Idempotency: a second back-to-back playbook run reports `changed=0` for the fluentbit tag AND for the seven other affected role tags.
</verification>

<success_criteria>
- [ ] All ten task-level acceptance_criteria pass.
- [ ] `roles/fluentbit/files/enrich.lua` exists; function `enrich` defined; 60-150 lines; string.match extraction (no cjson); `-json` suffix strip present; NO Docker socket reference.
- [ ] `roles/fluentbit/templates/fluent-bit.conf.j2` has `[FILTER] lua` block (alias `telemetron_enrich`) BEFORE the existing `[FILTER] modify` allowlist_static block; Tag_Regex untouched.
- [ ] `roles/fluentbit/tasks/main.yml` copies `enrich.lua` to host config dir AND bind-mounts it into the container at `fluentbit_enrich_lua_path`.
- [ ] `roles/fluentbit/tasks/main.yml`'s `/var/lib/docker/containers` RO bind-mount preserved.
- [ ] Eight roles (minio, loki, tempo, mimir, node_exporter, opentelemetry, prometheus, fluentbit) all stamp `org.telemetron.service: telemetron` + `org.telemetron.job: <component>` on their `docker_container` task.
- [ ] `roles/fluentbit/README.md` documents the convention as M1 default (no longer Q3-deferred); SC4 retest noted in Verification scope; unrelated deferrals (Q9 / Phase 6 / multi-region / nfsd) preserved.
- [ ] `roles/README.md` Gate 7 documents the per-role label-stamping convention for future Phase 4/5 ports.
- [ ] `.planning/REQUIREMENTS.md` INGEST-07 row reflects Lua-filter implementation.
- [ ] `.planning/phases/03-ingest-plane/03-HUMAN-UAT.md` gap entry `ingest-07-service-job-labels` flipped to status: resolved with resolved_by pointer.
- [ ] `.planning/ROADMAP.md` Phase 3 plan list has the new 03-05 bullet; plan count updated.
- [ ] `.planning/STATE.md` Phase-3 FEATURE-COMPLETE marker rephrased to GAP-CLOSURE-IN-PROGRESS.
- [ ] `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
- [ ] Pitfall 6 mitigation pack intact (Etc/UTC + Multiline_Flush 5 + Read_from_Head false + storage.type filesystem + storage.max_chunks_up 128).
- [ ] INSPQ grep gate green (code/config only) AND grep gate green on `roles/fluentbit/` AND on every other modified role's `tasks/main.yml` (image-pin, non-ASCII code/config-only, vault, idempotency, OPS-06).
- [ ] No `/var/run/docker.sock` reference introduced in any fluentbit file (Lua, J2, YAML).
- [ ] All Phase-3 INGEST-XX requirements remain satisfied or improved; INGEST-07 promoted from PARTIAL to fully SATISFIED.
</success_criteria>

<output>
After completion, create `.planning/phases/03-ingest-plane/03-05-fluentbit-label-enrichment-SUMMARY.md` documenting:

1. Lua filter design choices (cache TTL 300s, fallback values, string.match extraction with `raw:match` patterns INSTEAD of cjson per iteration 1 fix, `-json` suffix strip rationale, line count actually shipped).
2. Filter chain re-ordering in fluent-bit.conf.j2 (which existing filters moved relative to the new lua block); confirmation that Plan 03-04's Tag_Regex was NOT touched and that the suffix-strip lives in enrich.lua only.
3. The eight role tasks/main.yml `labels:` additions (one paragraph per role with the exact job value used).
4. Phase 4/5 forward-compat note added to roles/README.md as Gate 7.
5. SC4 retest expectation captured in README -- noting it is a UAT item, not a static-audit gate.
6. REQUIREMENTS.md INGEST-07 row description rewrite + 03-HUMAN-UAT.md status flip diff + ROADMAP plan-list bullet add + STATE.md FEATURE-COMPLETE rephrase.
7. Any execute-time surprises -- explicitly confirm that `cjson.safe` is NOT required at FB startup (the iteration 1 revision removed the dependency to avoid a hard FB startup failure on `fluent/fluent-bit:4.2.3` which does not bundle lua-cjson); the `string.match` patterns return all three needed fields without parsing the whole JSON.
8. Confirmation that no `/var/run/docker.sock` was introduced anywhere (security posture identical to Plan 03-04).
9. Re-verification handoff: the verifier (run by /gsd:execute-phase 03 --gaps-only post-execute) should flip Phase 3 from `human_needed` -> `passed` once SC1-SC5 pass on the homelab.
</output>
</content>
</invoke>