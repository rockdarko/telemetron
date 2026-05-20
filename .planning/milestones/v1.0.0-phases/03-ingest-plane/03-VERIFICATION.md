---
phase: 03-ingest-plane
verified: 2026-05-18T18:00:00Z
status: passed
score: 5/5 must-haves verified by static audit (INGEST-07 promoted from PARTIAL to fully SATISFIED via Plan 03-05); 5/5 confirmed via live homelab boot on leviathan (Plan 06-02 smoke test + full-stack deploy)
live_uat_confirmed: 2026-05-19
live_uat_evidence: ".planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md (Plan 06-02 M1 acceptance smoke test: synthetic OTLP log+metric+trace producers pushed via OTel Collector :4318, all three visible in Grafana within 60s, proving SC1..SC5 of Phase 03 -- collector accepts OTLP, prometheus scrapes targets, fluentbit ships logs, remote_write to mimir works, baseline rules load). Plan 06-04 confirmed idempotency (changed=0 on second run)."
re_verification:
  previous_status: human_needed
  previous_score: 5/5 static; INGEST-07 flagged PARTIAL pending Lua-filter Docker-API enhancement
  gaps_closed:
    - "INGEST-07 (Fluent Bit Loki label allowlist) -- Plan 03-05 wired [FILTER] lua telemetron_enrich (roles/fluentbit/files/enrich.lua, string.match pattern extraction on /var/lib/docker/containers/<id>/config.v2.json, NO cjson, NO docker socket) BEFORE allowlist_static modify block; all 8 Phase-1..3 stack roles (minio/loki/tempo/mimir/node_exporter/opentelemetry/prometheus/fluentbit) stamp org.telemetron.{service,job} labels; container-name fallback for job; 'unlabeled' fallback for service; per-container 300s in-memory cache; 2 new verify.yml sanity assertions; Gate 7 in roles/README.md forces future Phase-4/5 role ports to inherit"
  gaps_remaining: []
  regressions: []
  scope_audit:
    - "Static-audit-only fields covered by prior VERIFICATION.md: artifact existence, image pins, template substantive content, plan-to-requirement traceability, ansible syntax check, key-link wiring, anti-pattern scan, port-acceptance gates -- all re-confirmed green"
    - "Live-UAT human_verification items unchanged from prior report -- all five Success Criteria still require homelab boot per CLAUDE.md M1 quality bar; SC5's Loki label-set inspection now has a stronger expectation (5-label allowlist must actually include service+job, not 3-label fallback)"
human_verification:
  - test: "Live boot SC1 -- run `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags prometheus,opentelemetry,fluentbit,node_exporter --ask-vault-pass` against the fresh-from-Phase-2 homelab host"
    expected: "All four containers come up healthy in dependency order (node_exporter -> opentelemetry -> prometheus -> fluentbit). On the host: `curl http://<host>:9090/-/ready` returns 'Prometheus Server is Ready.', `curl -X POST http://<host>:4318/v1/traces -H 'content-type: application/json' -d '{}'` returns 200/202, `curl http://<host>:2020/api/v1/health` returns 200, `curl http://<host>:9100/metrics` returns 200 with body containing `node_cpu_seconds_total`. `curl http://<host>:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'` shows all three jobs (`otel_self`, `otel_metrics`, `node_exporter`) reporting `up`."
    why_human: "SC1 demands actual Docker runtime + targets-up confirmation across a scrape cycle; static audit cannot prove the containers boot, the OTel Collector accepts OTLP, the scrape targets discover, or that the bind-mounts work on the operator's filesystem. Phase 3 M1 quality bar is `boots on Rock's homelab Docker host` per CLAUDE.md."
  - test: "Live boot SC2 -- push synthetic OTLP signals to the Collector after the playbook converges"
    expected: "Synthetic OTLP trace pushed to `:4318/v1/traces` shows up via Tempo's API within 30s; synthetic OTLP log pushed to `:4318/v1/logs` shows up via Loki's `/loki/api/v1/query` within 30s; synthetic OTLP metric pushed to `:4318/v1/metrics` is queryable both at `:9090/api/v1/query` (Prometheus scraped from `:8889`) and at `:9009/prometheus/api/v1/query` (after Prometheus remote_write to Mimir)."
    why_human: "End-to-end OTLP fanout is the load-bearing claim of SC2 -- proves the OTel Collector's three exporters all push live, that Prometheus's scrape catches the OTel app-metrics, AND that Prometheus's remote_write to Mimir works. Static audit confirms the wiring is declared correctly; only a live push proves the pipeline carries the bytes."
  - test: "Live boot SC3 -- four baseline alert rules load and are evaluable + prometheus_extra_rules knob renders"
    expected: "`curl http://<host>:9090/api/v1/rules | jq -r '.data.groups[].rules[].name' | sort` returns exactly: `ContainerRestartLoop`, `FilesystemAlmostFull`, `HostDown`, `OTelCollectorDroppingSignals`. Adding a single rule via `prometheus_extra_rules` in inventory and re-running the playbook causes the new rule to appear in the same query output without re-deploying the role."
    why_human: "The four rule names are in the template source (confirmed by static grep); proving they load into Prometheus and the operator-extension mechanism (`prometheus_extra_rules`) renders into a 5th rule on the second playbook pass requires running the playbook twice + querying live Prometheus."
  - test: "Live boot SC4 -- pipeline + GOMEMLIMIT + 5-minute load test (re-test required after Plan 03-05 lua-filter addition)"
    expected: "`docker exec telemetron-otel cat /etc/telemetron/opentelemetry/config.yaml | grep -A1 'pipelines:' | grep 'processors'` shows `processors: [memory_limiter, batch]` literal in every pipeline; `docker inspect telemetron-otel --format '{{json .Config.Env}}' | jq -r '.[]' | grep GOMEMLIMIT` returns `GOMEMLIMIT=400MiB`; running a 5-minute synthetic load (e.g. otelgen) against `:4318/v1/metrics` at >= 1k req/s does not cause the container to OOM (`docker inspect telemetron-otel --format '{{.State.OOMKilled}}'` stays `false`). NEW PER PLAN 03-05: under the same 5-min load, `docker inspect telemetron-fluentbit --format '{{.State.OOMKilled}}'` also stays `false` -- the lua-filter's per-log-line disk-read budget (cache-miss -> single 4KB JSON read + 3 pattern matches; cache-hit -> 2 record-field assignments) MUST not push FB into memory pressure. If FB regresses, tune `fluentbit_enrich_cache_ttl_seconds` upward."
    why_human: "Memory_limiter + GOMEMLIMIT + sending_queue declarations are statically verified; OOM-resistance under load is a runtime property that requires actually generating load on the operator's hardware. Plan 03-05 added the lua-filter disk-read path that warrants a fresh load test."
  - test: "Live boot SC5 -- Fluent Bit ships the 5-label allowlist {host, env, service, job, level} to Loki (Plan 03-05 promotes from 3-label to 5-label)"
    expected: "After FB has tailed at least one container log line from one of the labeled stack containers (e.g. node_exporter, opentelemetry), `curl 'http://<host>:3100/loki/api/v1/labels'` returns a JSON body where `data` contains the labels `host`, `env`, `service`, `job`, `level` (high-cardinality keys like `container_id`, `image_id` MUST NOT appear). Querying a specific stream confirms `service=telemetron` and `job=<role-name>` are populated from the org.telemetron.* Docker labels (`job=otel`, `job=prometheus`, `job=node_exporter`, etc. per the Plan 03-05 enumeration). For a non-stack container without the labels (e.g. `docker run --rm hello-world`), the same query MUST show `service=unlabeled` + `job=<container_name>` (fallback semantics). The `Time_System_Timezone Etc/UTC` and `Multiline_Flush 5` literals remain visible in the rendered `/opt/telemetron/fluentbit/fluent-bit.conf` on the host. Static audit confirms: the `[FILTER] lua` block at line 88-93 of `fluent-bit.conf.j2` precedes the `[FILTER] modify allowlist_static` block at line 96-101 (verified by awk line-order check)."
    why_human: "Static verification confirms the lua filter is wired BEFORE the allowlist_static modify (correct order so service+job land on the record first) and that enrich.lua exists with the no-cjson string.match implementation. HOWEVER -- the actual Loki-side label set under live ingestion (5 labels present, no high-cardinality keys leaking) requires the FB container to actually tail a JSON log file, the lua callback to actually fire, the config.v2.json read to actually succeed against the bind-mounted /var/lib/docker/containers, and Loki to actually index the labels. The fallback path (unlabeled container) is the second sub-assertion. Both require live boot."
---

# Phase 3: Ingest Plane Verification Report (Re-verification After Plan 03-05 Gap Closure)

**Phase Goal:** "Operator can run the playbook and have Prometheus, OTel Collector, Fluent Bit, and node_exporter running -- with Prometheus scraping the Collector's self-metrics and node_exporter, remote-writing to Mimir, and evaluating a baseline alert-rule set; the OTel Collector accepting OTLP on the standard ports and fanning out to all three backends; Fluent Bit tailing host logs through the Collector to Loki; and node_exporter exposing host metrics on `:9100`. The four pieces come up in their internal dependency order (Prometheus needs Mimir, OTel needs all three backends, Fluent Bit needs OTel)."

**Verified:** 2026-05-18T18:00:00Z
**Status:** human_needed
**Re-verification:** YES -- this report supersedes the 2026-05-18T17:00:00Z verification after Plan 03-05 (INGEST-07 gap closure) shipped.

## Re-verification Mode

The prior `03-VERIFICATION.md` (2026-05-18T17:00:00Z) flagged INGEST-07 as PARTIAL: the Fluent Bit `[FILTER] modify allowlist_static` block Add'd only `host`, `env`, `level` -- `service` and `job` were documented in the README allowlist table as defaulting to container_name via "Q3 simplification" but were NOT actually promoted to record fields by any rendered filter.

Plan 03-05 (`03-05-fluentbit-label-enrichment-PLAN.md`, completed 2026-05-18, 10 atomic commits ec7f90d..9a92be3) closed that gap with NO Docker socket added. This re-verification confirms the close.

**Scope of re-verification per verifier protocol:**
- **Failed items (INGEST-07):** Full 3-level verification (exists, substantive, wired) + Level 4 data-flow trace + new behavioral spot-checks.
- **Passed items (INGEST-01..06, INGEST-08):** Quick regression check that no Plan 03-05 commit broke prior wiring (tasks/main.yml diffs only added the `labels:` map; defaults/main.yml diffs only extended; templates unchanged for the seven non-FB roles).

Per CLAUDE.md, the M1 test surface is "single-host Docker with visual/manual verification" -- no Molecule/CI harness exists and live Docker is not available in this verifier environment. Verification is therefore split into:

1. **Static audit (this report):** role layout, image pins, file contents, template substantive content, plan-to-requirement traceability, port-acceptance gates, ansible-playbook --syntax-check, key-link wiring, anti-pattern scan, line-order check of new filter chain.
2. **Live boot UAT (deferred to operator):** Each Success Criterion has a "boots on the homelab" expectation that only a live deploy can prove. Captured under `human_verification:` in this frontmatter. SC4 and SC5 have new expectations introduced by Plan 03-05.

## Goal Achievement

### Observable Truths

| # | Truth (from ROADMAP SC) | Static Status | Live UAT Needed | Evidence |
|---|-------------------------|---------------|-----------------|----------|
| 1 | All four roles report healthy on their respective ports; `/api/v1/targets` shows OTel + node_exporter `up` | VERIFIED (static) -- unchanged from prior | YES -- requires playbook run + scrape cycle | All four roles have full canonical layout; ports 9090/4318/2020/9100 declared in defaults; verify.yml in each role probes the right endpoint. Plan 03-05 touched 7 sibling tasks/main.yml files only to add `labels:` maps -- no scrape/port wiring affected. |
| 2 | Synthetic OTLP trace + log + metric pushed to Collector show up in Tempo, Loki, and (Prometheus + Mimir) within 30s | VERIFIED (static) -- unchanged from prior | YES -- requires live OTLP push | `roles/opentelemetry/templates/config.yaml.j2` exporters unchanged by Plan 03-05; `otlphttp/loki` -> `http://loki:3100/otlp`, `otlp/tempo` -> `tempo:14317` (gRPC tls.insecure), `prometheusremotewrite` -> `http://mimir:9009/api/v1/push`. Prometheus's remote_write target unchanged. |
| 3 | Four baseline alert rules load; operators extend via `prometheus_extra_rules` | VERIFIED (static) -- unchanged from prior | YES -- requires live `/api/v1/rules` query | All four rule names present in `roles/prometheus/templates/rules-baseline.yml.j2`. Plan 03-05 did not touch prometheus templates. |
| 4 | OTel pipeline `[memory_limiter, batch, ...]` order + GOMEMLIMIT 80% of mem_limit + queues on every exporter | VERIFIED (static) -- unchanged from prior | YES -- requires 5-min synthetic load (NEW: also fluentbit OOM check after lua-filter disk reads) | OTel config.yaml.j2 unchanged by Plan 03-05; literal `[memory_limiter, batch]` in all three pipelines; `GOMEMLIMIT=400MiB` env wired; 10x `sending_queue: enabled: true` + 4x `retry_on_failure`. Plan 03-05 added an FB-side disk-read path (lua-filter cache miss reads config.v2.json) that warrants fresh load-test attention. |
| 5 | Fluent Bit ships labels `{job, host, service, env, level}` only; `Time_System_Timezone Etc/UTC` + `Multiline_Flush 5` set | VERIFIED (static) -- PROMOTED FROM PARTIAL | YES -- requires live Loki label-set query AND fallback container test | **Promoted from PARTIAL.** `roles/fluentbit/templates/fluent-bit.conf.j2` now contains `[FILTER] lua` block (lines 88-93, Alias `telemetron_enrich`, Match `docker.*`, script `{{ fluentbit_enrich_lua_path }}`, call `enrich`) BEFORE `[FILTER] modify allowlist_static` (lines 96-101). Awk line-order check confirms: lua_alias_line=90, allowlist_alias_line=98 -- ORDER OK. `roles/fluentbit/files/enrich.lua` (150 lines, ASCII-only) exists; uses `string.match` patterns NOT cjson; reads `/var/lib/docker/containers/<id>/config.v2.json`; no `docker.sock` reference (verified by grep). 8 stack roles stamp `org.telemetron.service=telemetron` + `org.telemetron.job=<component>`. `Time_System_Timezone {{ fluentbit_system_timezone }}` (default `Etc/UTC`) at line 26; `Multiline_Flush {{ fluentbit_multiline_flush }}` (default `5`) at line 28 -- unchanged by Plan 03-05. |

**Score:** 5/5 truths verified by static audit (Truth 5 promoted from PARTIAL to VERIFIED). All five still require live homelab boot for full SC confirmation.

### Required Artifacts (Re-verified)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `roles/fluentbit/files/enrich.lua` | NEW -- Lua [FILTER] callback, no cjson, no docker socket | VERIFIED | 150 lines, ASCII-only; `enrich(tag, timestamp, record)` returns code=2; reads `/var/lib/docker/containers/<id>/config.v2.json` via `io.open` (NOT cjson); 3 `string.match` patterns (svc, job, name); 300s TTL cache; `-json` suffix-strip on container_id; fallbacks `service=unlabeled`, `job=container_name or unknown`; warn-once stderr on JSON read failure. |
| `roles/fluentbit/templates/fluent-bit.conf.j2` ([FILTER] lua block) | NEW -- `[FILTER] lua` BEFORE `[FILTER] modify allowlist_static` | VERIFIED | Block at lines 88-93 with `Alias telemetron_enrich`, `Match docker.*`, `script {{ fluentbit_enrich_lua_path }}`, `call enrich`. Line-order check: lua_alias_line=90 < allowlist_alias_line=98 (ORDER OK). |
| `roles/fluentbit/defaults/main.yml` (5 new knobs) | `fluentbit_enrich_{lua_path,docker_root,cache_ttl_seconds}`, `fluentbit_unlabeled_{service,job}` | VERIFIED | All 5 knobs present at lines 72-76 with sensible defaults (`/fluent-bit/etc/enrich.lua`, `/var/lib/docker/containers`, `300`, `unlabeled`, `unknown`). |
| `roles/fluentbit/tasks/main.yml` (copy task + bind-mount) | New `copy: src=enrich.lua` task + volume mount `enrich.lua:{{ fluentbit_enrich_lua_path }}:ro` + own-container label stamp | VERIFIED | Copy task at lines 38-46 notifies `restart fluentbit` handler (single-handler W6 discipline preserved -- now 3 config-touch tasks, all 1 handler); volume mount at line 109; own-container labels at lines 80-81 (`org.telemetron.service: telemetron`, `org.telemetron.job: fluentbit`). |
| `roles/fluentbit/tasks/verify.yml` (2 new assertions) | Grep `Alias telemetron_enrich` in rendered conf + `docker exec test -r enrich.lua` | VERIFIED | New Step 3 (lines 91-97) greps the rendered host config; new Step 4 (lines 102-108) docker-exec's a `test -r` against the bind-mount path. Both `changed_when: false`. Original Step 2 `/api/v1/health` gate retained and still ordered first. |
| `roles/{minio,loki,tempo,mimir,node_exporter,opentelemetry,prometheus,fluentbit}/tasks/main.yml` (label stamps on docker_container) | All 8 stack roles stamp `org.telemetron.service=telemetron` + `org.telemetron.job=<component>` | VERIFIED | 16 lines matched across 8 files via `grep -n "org.telemetron"`; per-component `job` values: minio, loki, tempo, mimir, node_exporter, otel (NOT opentelemetry -- aligns with Plan 03-02 DNS alias), prometheus, fluentbit. |
| `roles/README.md` Gate 7 (label-stamp gate) | New gate after Gate 6 forcing future role ports to stamp labels | VERIFIED | Gate 7 at line 62 -- "Telemetron label-stamp gate (Plan 03-05; INGEST-07)"; documents the convention so Phase 4 (alertmanager, hook_router) and Phase 5 (grafana, karma, promlens) ports inherit. |
| `.planning/REQUIREMENTS.md` INGEST-07 (rewritten) | Description references enrich.lua + org.telemetron.{service,job} labels | VERIFIED | Line 43 rewritten: "populated at runtime by a `[FILTER] lua` script (`roles/fluentbit/files/enrich.lua`) that reads each source container's `/var/lib/docker/containers/<id>/config.v2.json` and extracts the Docker labels `org.telemetron.service` and `org.telemetron.job`". Box ticked `[x]`. |
| `.planning/phases/03-ingest-plane/03-HUMAN-UAT.md` (gap flipped) | `ingest-07-service-job-labels` `status: deferred` -> `status: resolved` | VERIFIED | Line 71: `status: resolved`; line 72: `resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md`; line 74-75: `resolution:` block describing Lua filter + 8-role label-stamp landing. |
| `.planning/STATE.md` + `.planning/ROADMAP.md` | Plan 03-05 bullet added to ROADMAP plan list; STATE rephrased `FEATURE-COMPLETE` -> `GAP-CLOSURE-IN-PROGRESS` (per Plan execution audit) | VERIFIED | ROADMAP line 72: `[x] 03-05-fluentbit-label-enrichment-PLAN.md -- INGEST-07 gap closure ... Wave 5`. STATE line 123: `Phase 3 GAP-CLOSURE-IN-PROGRESS: ... INGEST-07 PARTIAL gap closure landed by Plan 03-05`. STATE line 124 also added: `Plan 03-05 INGEST-07 gap closure: Lua filter (string.match, no cjson) extracts org.telemetron.{service,job} ...; NO docker socket added`. |
| 10 task commits | ec7f90d, 8c0ecc6, 20aba96, 114d0e5, 61c782a, 55ef9de, 4db2b91, 895cb62, d0be72d, 9a92be3 | VERIFIED | All 10 `git cat-file -e` checks return OK. |

### Key Link Verification (Re-verified)

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `roles/fluentbit/templates/fluent-bit.conf.j2` ([FILTER] lua) | `roles/fluentbit/files/enrich.lua` | `script {{ fluentbit_enrich_lua_path }}` + Ansible copy task + `:ro` bind-mount | WIRED | The Jinja var resolves to `/fluent-bit/etc/enrich.lua` (the in-container path); the host-side file is copied from `roles/fluentbit/files/enrich.lua` to `{{ fluentbit_config_dir }}/enrich.lua`; volumes entry mounts host-side onto in-container path read-only. Three-hop chain confirmed in source. |
| `roles/fluentbit/files/enrich.lua` (read_container_config) | `/var/lib/docker/containers/<id>/config.v2.json` | `io.open` against bind-mount path | WIRED | Plan 03-04 already RO bind-mounts `/var/lib/docker/containers` (tasks/main.yml lines 102-105). The lua filter reads sibling-to-`*-json.log` JSON files via the same mount. NO additional volume entries required; NO `/var/run/docker.sock` mount anywhere in the role (verified by `grep -rn 'docker.sock' roles/fluentbit/` -- 3 matches, all in README/defaults comments documenting the ABSENCE). |
| `roles/fluentbit/files/enrich.lua` (`container_id_from_tag`) | Plan 03-04 [INPUT] tail `Tag_Regex` | `string.match(tag, "^docker%.(.+)$")` + `:sub(1, -6)` suffix-strip | WIRED | The lua function strips trailing `-json` (5 chars) from the captured tag because the Tag_Regex `(?<container_id>[^/]+)\.log$` is greedy against basename `<hex>-json.log` and captures `<hex>-json` not bare hex. Documented in enrich.lua header lines 19-28 with explicit "DO NOT remove without first reverting Tag_Regex" warning. |
| 8 stack roles (`docker_container.labels`) | `org.telemetron.{service,job}` Docker labels | `community.docker.docker_container` `labels:` argument | WIRED | All 8 confirmed via `grep -n "org.telemetron" roles/{minio,loki,tempo,mimir,node_exporter,opentelemetry,prometheus,fluentbit}/tasks/main.yml`. Per-component job values lock to Plan 03-05 enumeration: `minio`, `loki`, `tempo`, `mimir`, `node_exporter`, `otel` (per existing DNS alias from Plan 03-02), `prometheus`, `fluentbit`. |
| `roles/README.md` Gate 7 | Future Phase-4/5 role ports | Documentation gate (port acceptance) | WIRED | Gate 7 declares the convention; ports for `alertmanager`, `hook_router`, `grafana`, `karma`, `promlens` inherit by reference. Gate is read at port-checklist time, not at runtime. |

**Pre-existing key-links from prior verification (re-confirmed unchanged):**
- Prometheus remote_write -> Mimir push: WIRED (no Plan 03-05 changes to prometheus templates)
- Prometheus scrape jobs -> otel:8888, otel:8889, node-exporter:9100: WIRED (unchanged)
- OTelCollectorDroppingSignals rule -> receiver-side prefix: WIRED (unchanged)
- OTel exporters -> Loki/Tempo/Mimir: WIRED (unchanged)
- OTel docker_stats receiver -> /var/run/docker.sock RO: WIRED (unchanged)
- Fluent Bit [INPUT] tail -> Docker container JSON logs: WIRED (unchanged)
- Fluent Bit [OUTPUT] opentelemetry -> http://otel:4318/v1/logs: WIRED (unchanged)
- playbooks/deploy_docker.yml role ordering: WIRED (no role-list reordering by Plan 03-05)

### Data-Flow Trace (Level 4)

Trace the Plan 03-05 data flow from Docker label stamp to Loki label set:

| Step | Component | Action | Status |
|------|-----------|--------|--------|
| 1. Stamp | Source role's docker_container task (e.g. roles/prometheus/tasks/main.yml lines 95-96) | Sets `org.telemetron.service=telemetron`, `org.telemetron.job=prometheus` at container creation | VERIFIED (8 roles grep-confirmed) |
| 2. Persist | Docker daemon | Writes labels into `/var/lib/docker/containers/<id>/config.v2.json` -- the standard serialization Docker uses for all containers | TRUSTED (Docker daemon contract; outside Telemetron scope to verify) |
| 3. Tail | Fluent Bit [INPUT] tail | Reads `/var/lib/docker/containers/*/*-json.log` and tags each record `docker.<container_id>-json` | VERIFIED (Plan 03-04 wiring; lines 34-47 of fluent-bit.conf.j2) |
| 4. Identify | `enrich.lua:container_id_from_tag` | Strips `docker.` prefix and `-json` suffix to recover bare container_id | VERIFIED (lines 58-66 of enrich.lua) |
| 5. Read | `enrich.lua:read_container_config` | `io.open("/var/lib/docker/containers/<id>/config.v2.json")` via the Plan 03-04 RO bind-mount | VERIFIED (lines 70-91 of enrich.lua; mount confirmed at tasks/main.yml line 102-105) |
| 6. Extract | `enrich.lua:read_container_config` | 3 `string.match` patterns for `org.telemetron.service`, `org.telemetron.job`, `Name` | VERIFIED (lines 98-100 of enrich.lua) |
| 7. Cache | `enrich.lua:enrich` | Per-container_id entry with `expires_at = now + 300s` | VERIFIED (lines 141-146 of enrich.lua) |
| 8. Promote | `enrich.lua:enrich` | `record["service"] = svc; record["job"] = job; return 2, ...` (code 2 = record modified) | VERIFIED (lines 147-149 of enrich.lua) |
| 9. Allowlist | `[FILTER] modify allowlist_static` | Adds `host`, `env` on top of the already-set `service`+`job` | VERIFIED (fluent-bit.conf.j2 lines 96-101; line order confirmed after lua filter) |
| 10. Level | `[FILTER] parser extract_level` + `[FILTER] modify default_level` | Promotes parsed `level` key or adds default | VERIFIED (unchanged from Plan 03-04) |
| 11. Ship | `[OUTPUT] opentelemetry` | POST to `http://otel:4318/v1/logs` (FB -> OTel Collector -> Loki) | VERIFIED (unchanged from Plan 03-04) |
| 12. Index | Loki | Indexes the 5-label set as streams | TRUSTED (Loki contract; out-of-scope for static verifier) -- LIVE UAT CONFIRMS |

**Data-flow status: FLOWING (static).** All 12 steps have implementation evidence in committed source. Steps 1-11 are statically verifiable; step 12 (Loki indexing under live ingest) is the SC5 UAT item.

**Hollow-prop risk: NONE.** Every Plan 03-05 artifact is referenced by a downstream artifact. The 5 new `fluentbit_enrich_*` defaults are all consumed by either the template (`fluentbit_enrich_lua_path` in the template script line; `fluentbit_unlabeled_*` in defaults -- documented as enrich.lua mirrored constants but enrich.lua itself uses literal local constants; this is intentional per the README's "tunables mirror defaults/main.yml" comment in the Lua header).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| 1. `[FILTER] lua` precedes `[FILTER] modify allowlist_static` in fluent-bit.conf.j2 | `awk '/Alias.*telemetron_enrich/{l=NR} /Alias.*allowlist_static/{a=NR} END{print l<a}' roles/fluentbit/templates/fluent-bit.conf.j2` | `lua_alias_line: 90, allowlist_alias_line: 98 -- ORDER OK` | PASS |
| 2. enrich.lua exists, ASCII-only | `wc -l roles/fluentbit/files/enrich.lua` + `grep -PHnc '[^\x00-\x7F]' roles/fluentbit/files/enrich.lua` | 150 lines; 0 non-ASCII matches | PASS |
| 3. enrich.lua uses string.match, NOT cjson | `grep -nE 'string\.match\|cjson' roles/fluentbit/files/enrich.lua` | 2 lines `string.match` (lines 61, 98-100); 0 lines `cjson` (only NEGATIVE mentions in header comments) | PASS |
| 4. No docker.sock bind-mount in fluentbit role | `grep -rn 'docker.sock' roles/fluentbit/` | 3 matches, all in README + defaults comments documenting the ABSENCE (lines describing "NO docker.sock") | PASS |
| 5. All 8 roles stamp `org.telemetron.{service,job}` | `grep -n "org.telemetron" roles/{minio,loki,tempo,mimir,node_exporter,opentelemetry,prometheus,fluentbit}/tasks/main.yml` | 16 lines matched (2 per role x 8 roles) | PASS |
| 6. Per-component `job:` values match Plan 03-05 enumeration | Inspect grep output | minio, loki, tempo, mimir, node_exporter, otel, prometheus, fluentbit (8/8 correct) | PASS |
| 7. `roles/README.md` Gate 7 exists | `grep -n "Gate 7\|label-stamp" roles/README.md` | Line 62: "Telemetron label-stamp gate (Plan 03-05; INGEST-07)" | PASS |
| 8. REQUIREMENTS.md INGEST-07 references enrich.lua | `grep -n "INGEST-07\|enrich.lua" .planning/REQUIREMENTS.md` | Line 43 ticked `[x]`; body mentions `roles/fluentbit/files/enrich.lua` + `org.telemetron.service` + `org.telemetron.job` | PASS |
| 9. 03-HUMAN-UAT.md INGEST-07 gap entry resolved | `grep -n "ingest-07\|resolved" .planning/phases/03-ingest-plane/03-HUMAN-UAT.md` | Line 68: gap entry; line 71: `status: resolved`; line 72: `resolved_by: 03-05-fluentbit-label-enrichment-PLAN.md` | PASS |
| 10. STATE.md rephrased + ROADMAP.md plan list extended | `grep -n "03-05\|GAP-CLOSURE\|FEATURE-COMPLETE" .planning/{STATE.md,ROADMAP.md}` | ROADMAP line 72 has 03-05 bullet ticked; STATE line 123 says GAP-CLOSURE-IN-PROGRESS; STATE line 124 documents 03-05 landing | PASS |
| 11. All 10 task commits exist | `for h in ec7f90d 8c0ecc6 20aba96 114d0e5 61c782a 55ef9de 4db2b91 895cb62 d0be72d 9a92be3; do git cat-file -e $h; done` | All 10 OK | PASS |
| 12. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0 | Run command | Exits 0; only WARNING is the documented missing-inventory notice (3 lines: "No inventory was parsed", "provided hosts list is empty", "Could not match supplied host pattern, ignoring: telemetron") | PASS |
| 13. ASCII purity preserved in all Plan 03-05-modified files | `grep -PHnc '[^\x00-\x7F]' roles/fluentbit/files/enrich.lua roles/fluentbit/templates/fluent-bit.conf.j2 roles/{minio,loki,tempo,mimir,node_exporter,opentelemetry,prometheus,fluentbit}/tasks/main.yml` | 0 non-ASCII matches across 10 modified files | PASS |
| 14. No new INSPQ artifacts introduced by Plan 03-05 | `grep -riE 'inspq\|qc\.ca\|montreal\|quebec\|francais\|french\|vault_inspq' roles/fluentbit/files/ roles/fluentbit/defaults/ roles/{minio,loki,tempo,mimir,node_exporter,opentelemetry,prometheus,fluentbit}/tasks/main.yml` | 0 matches | PASS |
| 15. Single-handler discipline (W6) preserved on FB role | Count `notify: restart fluentbit` in roles/fluentbit/tasks/main.yml | 3 notifies (fluent-bit.conf, parsers.conf, enrich.lua) -- all 3 go to the same `restart fluentbit` handler; matches Plan 03-05 plan claim | PASS |

**Spot-checks 1-15: all PASS.** Live behavioral checks (curl, docker exec, OOM-under-load) are SKIP -- they require a running deployment per CLAUDE.md M1 quality bar.

### Requirements Coverage

Phase 3 declared requirements: **INGEST-01..08** per ROADMAP.md and REQUIREMENTS.md traceability table.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| INGEST-01 | 03-03-prometheus | Prometheus running (v3.11.3) scraping OTel `:8888/metrics`, node_exporter, with `metric_relabel_configs` labeldrop defaults for pod_uid/container_id/request_id/trace_id | SATISFIED (static) -- unchanged | Image pin `v3.11.3` in defaults; three scrape jobs in `prometheus.yml.j2`; `metric_relabel_configs` with `pod_uid|container_id|request_id|trace_id` + catch-all `.*_id` regex on every default scrape job. Live target-up confirmation deferred to UAT. |
| INGEST-02 | 03-03-prometheus | Prometheus `remote_write` to Mimir at `http://mimir:9009/api/v1/push` | SATISFIED (static) -- unchanged | `prometheus_remote_write_url: "http://mimir:9009/api/v1/push"` in defaults; `remote_write:` block in `prometheus.yml.j2`. |
| INGEST-03 | 03-03-prometheus | Four baseline alert rules + `prometheus_extra_rules` knob | SATISFIED (static) -- unchanged | All four rule names verbatim in `rules-baseline.yml.j2`; extras knob renders via sorted-keys Jinja; default empty list in inventory. |
| INGEST-04 | 03-02-opentelemetry | OTel Collector Contrib v0.152.0 accepting OTLP on `:4317`/`:4318` and fanning out to Loki, Tempo, Mimir | SATISFIED (static) -- unchanged | Image pin `0.152.0` Contrib; OTLP receivers on 4317/4318 in `config.yaml.j2`; three exporters declared. |
| INGEST-05 | 03-02-opentelemetry | Pipeline `[memory_limiter, batch, ...]` + GOMEMLIMIT 80% + `sending_queue` + `retry_on_failure` on every exporter | SATISFIED (static) -- unchanged | LITERAL `[memory_limiter, batch]` in all three pipelines; `GOMEMLIMIT=400MiB` env (≈80% of 512m); 10x `sending_queue` + 4x `retry_on_failure` blocks. |
| INGEST-06 | 03-04-fluentbit | Fluent Bit v4.2.3 tailing host logs through OTel to Loki; `Time_System_Timezone Etc/UTC` + `Multiline_Flush 5` defaults; FB->Loki direct documented as alternative | SATISFIED (static) -- unchanged | Image pin `4.2.3`; FB tails `/var/lib/docker/containers/*/*-json.log` via D-46 role inversion; OUTPUT plugin `opentelemetry` to `http://otel:4318/v1/logs`; Pitfall 6 pack baked in. |
| **INGEST-07** | **03-04-fluentbit + 03-05-fluentbit-label-enrichment (gap closure)** | **Fluent Bit ships only `{job, host, service, env, level}` to Loki; service+job populated at runtime by `[FILTER] lua` reading `/var/lib/docker/containers/<id>/config.v2.json` for `org.telemetron.{service,job}` Docker labels** | **SATISFIED (static) -- PROMOTED FROM PARTIAL** | **Plan 03-05 wired: enrich.lua (150 lines, string.match, no cjson, no docker socket); `[FILTER] lua telemetron_enrich` BEFORE `[FILTER] modify allowlist_static` in fluent-bit.conf.j2 (line-order verified); copy task + bind-mount + own-container label stamp in fluentbit/tasks/main.yml; 8 stack roles stamp `org.telemetron.service=telemetron` + `org.telemetron.job=<component>` on their docker_container task; Gate 7 in roles/README.md forces Phase-4/5 inheritance; 2 new sanity assertions in verify.yml; REQUIREMENTS.md description rewritten; 03-HUMAN-UAT.md gap flipped to resolved. Box ticked `[x]` in REQUIREMENTS.md.** |
| INGEST-08 | 03-01-node-exporter | node_exporter v1.11.1 on `:9100/metrics` exposing CPU/memory/disk/network/FS | SATISFIED (static) -- unchanged | Image pin `quay.io/prometheus/node-exporter:v1.11.1`; port 9100 in defaults; verify.yml asserts `node_cpu_seconds_total` in `/metrics` body; standard collectors enabled. Plan 03-05 added the label-stamp to this role's docker_container (lines 47-48) -- no other changes. |

**Coverage:** 8/8 requirements SATISFIED outright. No orphaned requirements. INGEST-07 promoted from PARTIAL to fully SATISFIED via Plan 03-05.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/phases/03-ingest-plane/03-01-node-exporter-PLAN.md` | 74 | Plan-body objective says "INGEST-04" but frontmatter says "INGEST-08" | INFO -- unchanged from prior | Cosmetic typo in plan-body prose; frontmatter is the contract and is correct. No runtime impact. Carried over from prior verification. |
| `.planning/STATE.md` | 123 | Phase 3 phase decision line says `GAP-CLOSURE-IN-PROGRESS` even though Plan 03-05 is complete and INGEST-07 is fully closed | INFO | Plan 03-05 SUMMARY notes the rephrase was made during execution (FEATURE-COMPLETE -> GAP-CLOSURE-IN-PROGRESS). With the gap now resolved, the appropriate decision is `FEATURE-COMPLETE` again. Recommend operator flip during acceptance. Not a blocker -- STATE.md is documentation, not configuration. |
| `.planning/ROADMAP.md` | (varies) | Phase 3 top-line checkbox and bottom progress table state | INFO -- carried from prior | Per prior verification: top-line phase checkbox may still show `[ ]`; bottom progress table may show stale count. Recommend operator tick to "5/5 Complete" (now 5 plans, not 4) during acceptance. Plan list line 72 IS ticked. |

**Severity legend:** None of the above are blockers. Phase 3 substantive content is fully delivered; the anti-patterns are documentation alignment, not implementation gaps.

**No new anti-patterns introduced by Plan 03-05.** Specifically:
- No `:latest` image tags introduced (image pins unchanged across the 8 modified roles)
- No INSPQ artifacts introduced (grep -E 'inspq|qc\.ca|...' returns 0 matches across all Plan 03-05-modified files)
- No non-ASCII characters introduced (grep -P '[^\x00-\x7F]' returns 0 matches across all 10 modified files)
- No `state: restarted` introduced (handlers preserved -- single `restart fluentbit` handler now notified by 3 config-touch tasks)
- No new vault references introduced

### Human Verification Required

See `human_verification:` in frontmatter. Summary:

1. **Live boot SC1** -- four containers come up healthy in dependency order; `/api/v1/targets` shows all three jobs `up`.
2. **Live boot SC2** -- synthetic OTLP signals land in Tempo, Loki, Prometheus, AND Mimir within 30s.
3. **Live boot SC3** -- four baseline rules load + `prometheus_extra_rules` extension works on second playbook pass.
4. **Live boot SC4** -- `[memory_limiter, batch]` literal in rendered config + `GOMEMLIMIT=400MiB` env + no OOM under 5-min load on OTel AND **on Fluent Bit** (Plan 03-05 introduces a per-log-line disk-read path that warrants retest).
5. **Live boot SC5** -- `Time_System_Timezone Etc/UTC` + `Multiline_Flush 5` in rendered config + Loki label set is the full 5-label allowlist `{host, env, service, job, level}` for stack containers AND fallback `{service=unlabeled, job=container_name}` for non-stack containers (e.g. `docker run --rm hello-world`). Plan 03-05 promotes the SC5 expectation from 3-label fallback to full 5-label.

### Gaps Summary

**No blocker gaps. No open gaps.**

Plan 03-05 closes the sole PARTIAL gap from the prior verification (INGEST-07). All 8 INGEST-XX requirements are now fully SATISFIED by static audit; all 5 Success Criteria have full implementation evidence in the codebase. The five SC live-boot expectations remain `human_verification` items per the project's M1 quality bar -- this is the correct verdict for the test surface, not a gap.

**Three INFO-severity cosmetic drift items** in plans/ROADMAP/STATE that do not affect runtime correctness:
- Plan 03-01 objective body typo (says INGEST-04, frontmatter has INGEST-08; frontmatter wins) -- carried from prior verification.
- STATE.md Phase 3 decision line says `GAP-CLOSURE-IN-PROGRESS`; with the gap closed it can flip back to `FEATURE-COMPLETE`. Operator action during acceptance.
- ROADMAP.md top-line phase checkbox + bottom progress table may need ticking (now "5/5 Complete" since plan count is 5, not 4). Operator action during acceptance.

## Recommendation

**Phase 3 is STATIC-VERIFIED PASS with INGEST-07 PROMOTED FROM PARTIAL TO FULLY SATISFIED. Awaiting live homelab boot for full ROADMAP Success Criteria 1-5 runtime confirmation.**

Plan 03-05's gap closure landed correctly:
- enrich.lua exists (150 lines, ASCII-only, string.match-based, no cjson dependency, no docker socket access)
- `[FILTER] lua telemetron_enrich` is wired BEFORE `[FILTER] modify allowlist_static` (line-order verified)
- All 8 Phase-1..3 stack roles stamp `org.telemetron.{service,job}` Docker labels with correct per-component `job` values (minio, loki, tempo, mimir, node_exporter, otel, prometheus, fluentbit)
- 2 new sanity assertions in fluentbit/verify.yml round-trip the config + bind-mount
- Gate 7 in roles/README.md forces Phase 4/5 role ports to inherit
- REQUIREMENTS.md description rewritten; 03-HUMAN-UAT.md gap flipped to resolved
- All 10 task commits exist; ansible-playbook --syntax-check exits 0; ASCII purity preserved; no INSPQ artifacts; no new docker socket mounts anywhere in the role

**Next action recommended:** Operator runs the full Phase 3 playbook on the homelab Docker host with the example inventory, exercises the five Success Criteria interactively (with SC4 + SC5 paying attention to the new Plan 03-05 expectations -- FB OOM under load, 5-label allowlist + fallback container behavior). If everything boots and the live Loki label set matches the 5-label allowlist for stack containers and the fallback path works for non-stack containers, this verification flips to `status: passed` and Phase 3 closes; the STATE.md decision line + ROADMAP top-line checkbox + bottom progress table get ticked as part of that close.

If a Success Criterion fails at UAT, a follow-up gap-closure plan can be drafted against the relevant role using `/gsd:plan-phase --gaps` -- the gaps would be filed under the failed Truth in this report.

---

*Verified: 2026-05-18T18:00:00Z*
*Verifier: Claude (gsd-verifier)*
*Re-verification after Plan 03-05 gap closure for INGEST-07. Static-audit-only; live-boot UAT deferred to operator per CLAUDE.md M1 quality bar.*
