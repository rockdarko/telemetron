---
phase: 03-ingest-plane
plan: 03-prometheus
subsystem: infra
tags: [ansible, docker, prometheus, alerting, remote-write, mimir, observability, monolithic, telemetron]

# Dependency graph
requires:
  - phase: 02-telemetry-backends
    provides: Mimir 3.0.6 with multitenancy_enabled:false (D-26) accepting remote_write at http://mimir:9009/api/v1/push; canonical Phase-2 role template + conditional-HEALTHCHECK omit-magic-value pattern
  - phase: 03-ingest-plane
    plan: 01-node-exporter
    provides: node-exporter:9100/metrics scrape target on the telemetron bridge (INGEST-08)
  - phase: 03-ingest-plane
    plan: 02-opentelemetry
    provides: OTel Collector self-metrics on :8888 + Prometheus-format app-metrics on :8889; container_restarts_total (via docker_stats container.restarts opt-in); otelcol_receiver_refused_* internal-telemetry counters
provides:
  - prometheus role on roles/prometheus/ scraping otel_self/otel_metrics/node_exporter and remote_write to Mimir
  - pinned image prom/prometheus:v3.11.3
  - three default scrape jobs with Pitfall 3 metric_relabel_configs labeldrop defaults baked in
  - four baseline alert rules (HostDown, FilesystemAlmostFull, ContainerRestartLoop, OTelCollectorDroppingSignals) with RESEARCH correction #2 (otelcol_receiver_refused_* prefix) applied
  - operator-extensible alert rules via prometheus_extra_rules knob (D-20 sorted-keys idempotency)
  - operator-extensible scrape jobs via prometheus_extra_scrape_configs knob
  - remote_write to http://mimir:9009/api/v1/push (no X-Scope-OrgID per D-26)
  - in-network verify one-shot asserting /-/ready 200 + /api/v1/targets all-up + /api/v1/rules four-rule load
  - playbooks/deploy_docker.yml extended to minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus
affects: [03-04-fluentbit, 04-alertmanager, 04-hook_router, 05-grafana, 06-orchestration-docs]

# Tech tracking
tech-stack:
  added: [prom/prometheus v3.11.3]
  patterns:
    - "Three-template role layout extension (production config + two rule templates) -- precedent for any future role that ships a base config + multiple supplementary docs (e.g., dashboards, recording rules)"
    - "Inline metric_relabel_configs labeldrop discipline -- per-job Pitfall 3 mitigation pack baked in as a default rather than a documented optional; high-cardinality keys die at scrape time and never become active series"
    - "Three-render notify-handler discipline -- all three rule/config templates notify the single 'restart prometheus' handler; tested via grep -c returning 3"
    - "in-network /api/v1/* assertion pattern -- verify-only curl one-shots assert specific JSON fragments via grep (jq is intentionally avoided to keep curlimages/curl base small); 60s retry loop on targets-up because verify runs immediately after container start"

key-files:
  created:
    - roles/prometheus/defaults/main.yml
    - roles/prometheus/tasks/main.yml
    - roles/prometheus/tasks/verify.yml
    - roles/prometheus/templates/prometheus.yml.j2
    - roles/prometheus/templates/rules-baseline.yml.j2
    - roles/prometheus/templates/rules-extras.yml.j2
    - roles/prometheus/handlers/main.yml
    - roles/prometheus/meta/main.yml
    - roles/prometheus/README.md
    - inventory/example-homelab/group_vars/all/prometheus.yml
  modified:
    - playbooks/deploy_docker.yml
    - roles/README.md

key-decisions:
  - "Image pin v3.11.3 from RESEARCH Finding 6 (2026-04-27 release) -- selected stable line over v3.5.1 LTS for current homelab quickstart audience; LTS is a one-knob inventory flip for ops-heavy operators"
  - "Three default scrape jobs hardcoded (otel_self, otel_metrics, node_exporter) -- not operator-toggleable since they ARE the telemetron M1 telemetry plane. Operators add MORE jobs via prometheus_extra_scrape_configs; cannot remove the three defaults without editing the template"
  - "RESEARCH correction #2 baked in: OTelCollectorDroppingSignals uses otelcol_receiver_refused_{spans,log_records,metric_points} -- NOT the processor-side counters. CONTEXT.md's processor_refused_* mention is superseded; the alert would never fire correctly with the wrong prefix"
  - "ContainerRestartLoop expression depends on Plan 03-02's D-51 opt-in (docker_stats container.restarts.enabled: true). Without that opt-in, the alert silently never fires -- documented in README's note section"
  - "D-25 audit dropped --web.enable-remote-write-receiver / --enable-feature=remote-write-receiver / --web.enable-otlp-receiver flags: Telemetron's Prometheus WRITES remote_write to Mimir; it does not RECEIVE it. The audit comment in tasks/main.yml deliberately avoids the literal flag strings (grep gate would fail otherwise -- same lesson as Plan 03-02 INSPQ-comment auto-fix)"
  - "Retention 15d (vs upstream 30d) is Claude's Discretion sized to be longer than Mimir's 12h query_store_after -- ensures Grafana's recent-query path resolves against Prometheus while Mimir handles long-term"
  - "Conditional-HEALTHCHECK Outcome B default (binary-alive proxy via /bin/prometheus --version) -- same Phase-2 pattern as mimir/tempo/node_exporter/opentelemetry. Authoritative readiness gate is verify.yml's /-/ready + /api/v1/targets + /api/v1/rules chain"
  - "Verify step 3 (targets-up) wrapped in 60s retry loop: verify runs immediately after container start, so targets need a scrape cycle to flip to up. Step 4 (rules-loaded) does NOT retry because rule parse happens synchronously on startup -- if rules are absent, they're broken, not slow"
  - "metric_relabel_configs Pitfall 3 mitigation is APPLIED PER DEFAULT JOB, not globally: each of the three default scrape jobs (otel_self, otel_metrics, node_exporter) gets the labeldrop pair (explicit pod_uid|container_id|request_id|trace_id + catch-all .*_id). Total 6 labeldrop entries in the rendered config"
  - "Inventory file ships four operator knobs (publish_host, retention_time, extra_rules, extra_scrape_configs) -- high-signal surface; all other defaults stay in roles/prometheus/defaults/main.yml"

patterns-established:
  - "Three-template role: production config.j2 + two rule .j2 templates -- all three notify the single restart handler. Future-compat for any role needing config + supplementary docs"
  - "Inline-default metric_relabel_configs labeldrop -- Pitfall 3 mitigation baked into every default scrape job, not documented as optional. Reusable shape for any future role that scrapes high-cardinality producers"
  - "API-endpoint assertion via curl + grep -- /-/ready (string match), /api/v1/targets (json grep on job + health up), /api/v1/rules (json grep on rule name). Reusable for any role exposing JSON status APIs"
  - "Comment-string avoidance pattern -- avoid embedding literal forbidden CLI flag strings in audit comments inside tasks/main.yml (the grep gate sees comments same as code). Phrase audits as 'the X feature flags are not enabled' rather than 'NO --web.enable-X-receiver'"

requirements-completed: [INGEST-01, INGEST-02, INGEST-03]

# Metrics
duration: 9 min
completed: 2026-05-18
---

# Phase 03 Plan 03: prometheus Summary

**Prometheus 3.11.3 ported as Telemetron's Phase-3 Wave-3 short-term-metrics + alerting-eval plane: three default scrape jobs (otel_self/otel_metrics/node_exporter) with Pitfall 3 labeldrop defaults; four baseline alert rules including OTelCollectorDroppingSignals with the RESEARCH-correction receiver_refused_* prefix; remote_write to Mimir as the M1 default; operator-extensible scrape + alert surfaces via prometheus_extra_* knobs**

## Performance

- **Duration:** ~9 min (513 seconds wall)
- **Started:** 2026-05-18T13:52:56Z
- **Completed:** 2026-05-18T14:01:29Z
- **Tasks:** 11
- **Files created:** 10
- **Files modified:** 2

## Accomplishments

- Canonical Phase-3 role layout extended to THREE templates: production `prometheus.yml.j2` + `rules-baseline.yml.j2` + `rules-extras.yml.j2`. All three notify the single `restart prometheus` handler (W6); `grep -c notify` returns exactly 3 in tasks/main.yml.
- Pinned image `prom/prometheus:v3.11.3` (RESEARCH Finding 6 verified current release, 2026-04-27).
- **Three default scrape jobs** hardcoded as defaults (D-42 + INGEST-08):
  - `otel_self` -> `otel:8888` (OTel Collector self-metrics; source of `otelcol_receiver_refused_*` for the OTelCollectorDroppingSignals alert).
  - `otel_metrics` -> `otel:8889` (OTel Collector app-metrics in Prometheus format; source of `container_restarts_total` for the ContainerRestartLoop alert).
  - `node_exporter` -> `node-exporter:9100` (host metrics from Plan 03-01; INGEST-08).
- **Pitfall 3 mitigation pack** baked into every default scrape job: `metric_relabel_configs` block with two `labeldrop` rules per job -- explicit `pod_uid|container_id|request_id|trace_id` plus the catch-all `.*_id` regex. Total six `action: labeldrop` entries in the rendered config (3 jobs * 2 labeldrop entries).
- **Four baseline alert rules (INGEST-03)** in `rules-baseline.yml.j2`:
  - `HostDown`: `up == 0` for 2m (critical)
  - `FilesystemAlmostFull`: `(node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.15` for 5m (warning, fstype-filtered)
  - `ContainerRestartLoop`: `increase(container_restarts_total[10m]) >= 3` for 0m (warning; D-51 OTel-translated metric)
  - `OTelCollectorDroppingSignals`: `rate(otelcol_receiver_refused_{spans,log_records,metric_points}) > 0` for 5m (warning; **RESEARCH correction #2** receiver-side prefix)
- **remote_write to Mimir** as M1 default: `http://mimir:9009/api/v1/push` with tuned queue_config (capacity 10000, max_samples_per_send 2000, batch_send_deadline 5s, 1-5 shards) and NO `X-Scope-OrgID` header (D-26 single-tenant Mimir per Phase-2).
- **Operator-extensible alert rules** (`prometheus_extra_rules`) via sorted-keys D-20 Jinja iteration -- empty default renders a legal-YAML group with empty rules list. README documents the schema with a working example.
- **Operator-extensible scrape jobs** (`prometheus_extra_scrape_configs`) via sorted-keys D-20 Jinja iteration.
- **D-25 audit** dropped the three forbidden Prometheus CLI flags (`--web.enable-remote-write-receiver`, `--enable-feature=remote-write-receiver`, `--web.enable-otlp-receiver`): Telemetron's Prometheus WRITES remote_write to Mimir; it does not RECEIVE it. Phase-2 Mimir already owns that role.
- **Conditional HEALTHCHECK** Outcome B default (`/bin/prometheus --version` binary-alive proxy) -- mirrors Phase-2 mimir/tempo + Plan 03-01 node_exporter + Plan 03-02 opentelemetry precedent. Authoritative readiness gate is the verify task's `/-/ready` + `/api/v1/targets` + `/api/v1/rules` chain.
- **Verify task** (`tasks/verify.yml`) implements four steps:
  - Step 1a/1b: HEALTHCHECK or State.Running poll (conditional on `prometheus_healthcheck_enabled`).
  - Step 2: in-network curl probe of `/-/ready` with 60s retry budget.
  - Step 3: `/api/v1/targets` assertion -- all three job names present AND at least one target reporting `"health":"up"` -- wrapped in 60s retry loop (targets need a scrape cycle to flip up).
  - Step 4: `/api/v1/rules` assertion -- all four baseline rule names load (single-shot; rules parse synchronously on startup).
- `playbooks/deploy_docker.yml` role list grew from 6 to 7 entries in D-41 order: `minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus`. `ansible-playbook --syntax-check` exits 0.
- `inventory/example-homelab/group_vars/all/prometheus.yml` ships four high-signal operator knobs: `prometheus_publish_host`, `prometheus_retention_time`, `prometheus_extra_rules`, `prometheus_extra_scrape_configs`.
- All six per-role port-acceptance gates pass on `roles/prometheus/` (Gates 2/4/5 scoped to YAML/J2 files per Phase-2 D-25 reinterpretation precedent).

## Task Commits

Each task was committed atomically:

1. **Task 1: scaffold prometheus role skeleton** - `a9748e1` (feat)
2. **Task 2: populate prometheus defaults with v3.11.3 pin and knobs** - `18062a5` (feat)
3. **Task 3: render production prometheus.yml with 3 scrape jobs + remote_write to Mimir** - `e506f65` (feat)
4. **Task 4: render baseline alert rules (INGEST-03) -- 4 rules with receiver_refused correction** - `395f7f4` (feat)
5. **Task 5: render operator-extensible rules-extras template (INGEST-03)** - `b8832a4` (feat)
6. **Task 6: write tasks/main.yml -- bootstrap, three template renders, container with retention/lifecycle** - `742ef52` (feat)
7. **Task 7: write tasks/verify.yml -- D-10a poll + targets/rules assertions (D-54)** - `ece7f91` (feat)
8. **Task 8: add single docker-restart handler (W6 / Pitfall 8)** - `1544d60` (feat)
9. **Task 9: write README -- OPS-03 schema + baseline-rules table + D-25 audit** - `5cf5ddb` (feat)
10. **Task 10: wire prometheus into example inventory + deploy_docker playbook (D-41)** - `aa95f26` (feat)
11. **Task 11: tick roles/README.md prometheus row + confirm six port-acceptance gates** - `db42699` (feat)

**Plan metadata commit:** appended after self-check (docs)

## Files Created/Modified

### Created

- `roles/prometheus/defaults/main.yml` - Role tunables: image pin v3.11.3, container identity, port 9090, no-host-publish default, retention 15d, three default scrape targets, Pitfall 3 relabel regex defaults, remote_write knobs (URL + queue_config), operator extension knobs, conditional-HEALTHCHECK trio (Outcome B default), verify pre-poll, curl pin
- `roles/prometheus/tasks/main.yml` - Bootstrap: ensure config dir + rules subdir, render three templates (all notify restart), docker_volume + docker_image + docker_container with retention/lifecycle CLI args (forbidden receiver flags omitted per D-25), triple-conditional published_ports, three RO config bind-mounts, conditional HEALTHCHECK, include verify.yml
- `roles/prometheus/tasks/verify.yml` - Four-step verify: HEALTHCHECK or State.Running poll + /-/ready 200 probe + /api/v1/targets all-jobs-up assertion (60s retry) + /api/v1/rules four-rule-name assertion
- `roles/prometheus/templates/prometheus.yml.j2` - Production prometheus.yml: global scrape/eval interval + external_labels, rule_files glob (baseline + extra), remote_write block to Mimir, three default scrape jobs with Pitfall 3 labeldrop defaults, operator-extensible scrape_configs iteration (D-20 sorted-keys)
- `roles/prometheus/templates/rules-baseline.yml.j2` - Four baseline alert rules with Jinja-escaped Prometheus annotation templating; OTelCollectorDroppingSignals uses receiver_refused_* prefix per RESEARCH correction #2; ContainerRestartLoop uses container_restarts_total per D-51 OTel-translated metric name
- `roles/prometheus/templates/rules-extras.yml.j2` - Operator-extensible rules group (telemetron.operator-extras); sorted-keys iteration over prometheus_extra_rules + sorted labels/annotations dicts; empty default renders legal-YAML empty group
- `roles/prometheus/handlers/main.yml` - Single "Docker restart prometheus" handler (W6 / Pitfall 8) listening on `restart prometheus`
- `roles/prometheus/meta/main.yml` - galaxy_info { role_name prometheus, MIT license, Ubuntu jammy/noble + Debian bookworm platforms, prometheus/metrics/observability/telemetron tags }, dependencies [], collections [community.docker, ansible.builtin]
- `roles/prometheus/README.md` - 18-section OPS-03 schema doc with default-scrape-targets table, baseline-rules table with full expressions + receiver_refused correction note + D-51 container_restarts_total provenance note, prometheus_extra_rules schema docs with example, Variables table, retention rationale (15d > Mimir 12h), conditional-HEALTHCHECK Outcomes A/B/C, Deviations from upstream INSPQ (TL;DR machine-greppable bullets + detailed sections)
- `inventory/example-homelab/group_vars/all/prometheus.yml` - Four operator knobs (publish_host false, retention_time 15d, extra_rules [], extra_scrape_configs [])

### Modified

- `playbooks/deploy_docker.yml` - Appended `role: prometheus` entry after `opentelemetry` per D-41 order with tag `prometheus`; updated trailing comment block to reflect new state (Phase 3 still needs fluentbit)
- `roles/README.md` - Ticked prometheus row from box to checkmark in the planned-roles table

## Decisions Made

- **Image pin v3.11.3 (stable over LTS):** RESEARCH Finding 6 verified v3.11.3 as the current stable release (2026-04-27); v3.5.1 is marked LTS. Selected v3.11.3 over v3.5.1 LTS for the current homelab quickstart audience -- LTS is a one-knob inventory flip for ops-heavy operators (`prometheus_image_tag: "v3.5.1"`).
- **Three default scrape jobs hardcoded:** otel_self/otel_metrics/node_exporter are not operator-toggleable since they ARE the telemetron M1 telemetry plane. Operators add MORE jobs via `prometheus_extra_scrape_configs`; removing one of the three defaults requires editing the role template (not the inventory). This is intentional -- the defaults define the M1 telemetry contract.
- **RESEARCH correction #2 baked into OTelCollectorDroppingSignals:** the alert expression uses `otelcol_receiver_refused_{spans,log_records,metric_points}` -- the receiver-side counters per the OTel internal-telemetry docs. CONTEXT.md's mention of `otelcol_processor_refused_*` is superseded. Any reference to processor-side refused counters anywhere in the rendered config or templates would be wrong and would result in the alert never firing.
- **ContainerRestartLoop has a Plan 03-02 D-51 dependency:** the alert expression uses `container_restarts_total`, which only exists when Plan 03-02's docker_stats receiver has `container.restarts.enabled: true` (D-51 opt-in). Without that opt-in, the alert silently never fires. Documented as a note in the README's Baseline Alert Rules section.
- **D-25 audit dropped three forbidden Prometheus CLI flags** (`--web.enable-remote-write-receiver`, `--enable-feature=remote-write-receiver`, `--web.enable-otlp-receiver`): Telemetron's Prometheus WRITES remote_write to Mimir; it does not RECEIVE it. Phase-2 Mimir already owns that role. The audit comment in `tasks/main.yml` deliberately avoids the literal flag strings (the grep gate would fail otherwise -- same lesson learned from Plan 03-02's INSPQ-comment auto-fix).
- **Retention 15d (Claude's Discretion over upstream 30d):** sized to be deliberately longer than Mimir's `query_store_after: 12h` (Phase-2 D-36). Grafana's recent-query path (<= 12h) resolves against Prometheus's local TSDB; older queries fall back to Mimir via remote_read. 15d gives a comfortable buffer.
- **Conditional-HEALTHCHECK Outcome B as default:** Prometheus 3.11.3 distroless base has no shell/curl/wget and no documented `--health` CLI flag. `/bin/prometheus --version` is the binary-alive proxy. The verify task's `/-/ready` + `/api/v1/targets` + `/api/v1/rules` chain is the authoritative readiness gate. Same shape as the four Phase-2/3 precedents.
- **Verify step 3 (targets-up) wraps in 60s retry; step 4 (rules-loaded) does NOT:** Targets need a scrape cycle (15s interval) to flip to `up`, so the assertion retries until at least one target reports `health: up`. Rules parse synchronously on Prometheus startup -- if `/api/v1/rules` doesn't return all four names on the first call, they're broken, not slow. No retry adds clarity to failure mode.
- **Pitfall 3 mitigation per-job (not global):** Each of the three default scrape jobs gets its own `metric_relabel_configs` block with two `labeldrop` rules (explicit + catch-all). Total six labeldrop entries in the rendered config. Per-job placement makes it explicit which scrape source the relabel applies to and gives operators a clear template to follow when adding their own jobs.
- **Inventory file ships four operator knobs:** `publish_host`, `retention_time`, `extra_rules`, `extra_scrape_configs`. High-signal surface -- everything else stays in `defaults/main.yml`. The two extra-* knobs are the M1 extension surface; the publish/retention knobs are the most-likely operator overrides.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Inline value comments on default vars broke literal `$`-anchored grep gates**

- **Found during:** Task 2 verify (acceptance regex on otel_self_target / otel_metrics_target)
- **Issue:** Task 2 plan acceptance required `grep -q '^prometheus_otel_self_target: "otel:8888"$'` AND `grep -q '^prometheus_otel_metrics_target: "otel:8889"$'`. The initial defaults render included trailing inline comments (`prometheus_otel_self_target: "otel:8888"     # OTel self-metrics`) which broke the `$` anchor.
- **Fix:** Moved per-line comments to a header comment block above the three scrape-target var declarations; the lines themselves match the `$`-anchored pattern verbatim.
- **Files modified:** `roles/prometheus/defaults/main.yml`
- **Verification:** Both `grep -q '^prometheus_otel_self_target: "otel:8888"$'` AND the otel_metrics variant return zero.
- **Committed in:** `18062a5` (Task 2 commit -- bundled into the initial defaults write before commit, no separate fix commit)

**2. [Rule 1 - Bug] `X-Scope-OrgID` literal string in template header comment broke the no-tenant-header gate**

- **Found during:** Task 3 verify (`! grep -q "X-Scope-OrgID"`)
- **Issue:** Plan Task 3 verify required `! grep -q "X-Scope-OrgID" roles/prometheus/templates/prometheus.yml.j2`. The initial render's header comment said "D-26 no X-Scope-OrgID on remote_write" which trips the literal-string grep.
- **Fix:** Rewrote the comment to say "D-26: no tenant header on remote_write" -- preserves narrative meaning without embedding the literal string.
- **Files modified:** `roles/prometheus/templates/prometheus.yml.j2`
- **Verification:** `! grep -q "X-Scope-OrgID" roles/prometheus/templates/prometheus.yml.j2` returns zero.
- **Committed in:** `e506f65` (Task 3 commit -- bundled into the template fix before commit)

**3. [Rule 1 - Bug] Forbidden CLI flag literals in audit comment broke the D-25 audit grep gate**

- **Found during:** Task 6 verify (`! grep -q -- "--web.enable-remote-write-receiver"` AND `! grep -q -- "--web.enable-otlp-receiver"`)
- **Issue:** Plan Task 6 verify required the forbidden Prometheus CLI flags to NOT appear anywhere in `tasks/main.yml`. The initial render included an audit comment block listing the flag names verbatim ("D-25 audit: NO --web.enable-remote-write-receiver, NO --enable-feature=remote-write-receiver, NO --web.enable-otlp-receiver -- Telemetron's Prometheus WRITES remote_write to Mimir; does not RECEIVE it.") which trips the literal-string grep.
- **Fix:** Rewrote the audit comment to say "the remote-write-receiver and otlp-receiver feature flags are intentionally NOT enabled here" -- preserves narrative meaning without embedding the literal flag strings. The audit narrative survives in the README's Deviations section where the literal flag names appear (the gate is scoped to code, not README).
- **Files modified:** `roles/prometheus/tasks/main.yml`
- **Verification:** Both `! grep -q -- "--web.enable-remote-write-receiver"` AND `! grep -q -- "--web.enable-otlp-receiver"` return zero in tasks/main.yml; the literal flag names remain documented in `roles/prometheus/README.md`.
- **Committed in:** `742ef52` (Task 6 commit -- bundled into the tasks/main.yml fix before commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 - same pattern: literal-string grep gates trip on documentation comments inside code/config files)
**Impact on plan:** All three are the "audit string in code" lesson learned in Plan 03-01 (INSPQ comment) and Plan 03-02 (INSPQ comment) -- the gate sees comments same as code. Fix is always to rephrase the comment to preserve narrative meaning without the literal trip string. No scope creep, no architectural change.

## Issues Encountered

- **`ugrep` regex error on `{{ *vault_` pattern (re-encountered):** Same issue Plan 03-01 documented. The vault-discipline grep gate uses a regex that `ugrep` (the default `grep` binary on this host) interprets as an empty subexpression. Verified zero `{{ vault_` references via `grep -F '{{ vault_'` plain-text test instead -- no vault references exist in roles/prometheus/ (Prometheus has no auth surface in M1 per D-26 single-tenant Mimir).
- **`grep -rE 'state:\s*restarted' roles/prometheus/` (no file-type scope) trips on README documentation:** Same issue as Plan 03-01 and Plan 03-02. The README's Idempotency section contains the documented don't-do-this phrase `` `state: restarted` is never used (Pitfall 8) `` -- same wording shipped in roles/{mimir,tempo,loki,node_exporter,opentelemetry}/README.md. Re-scoped Gate 5 to YAML/J2 files per Phase-2 precedent. Gate passes when scoped correctly.
- **Plan acceptance literal-string strictness on audit comments:** Three of the eleven tasks (2, 3, 6) had verify gates that grep for literal strings the audit narrative wanted to mention in comments inside YAML/J2 files. The lesson learned across Plans 03-01 (INSPQ), 03-02 (INSPQ + vault), and 03-03 (X-Scope-OrgID + forbidden flags) is consistent: phrase audit comments in code/config to preserve narrative meaning without the literal trip strings, then document the full literal-flag-name audit in the README's Deviations section (where the gate doesn't apply -- README is documentation, not code/config).

## Image-probe outcome (Conditional HEALTHCHECK selection)

The plan asked the executor to probe the image at execute time:

```
docker run --rm prom/prometheus:v3.11.3 --help | grep -i health
```

This was NOT actually executed (live Docker not available in this environment). The conditional-HEALTHCHECK default ships as **Outcome B** (`/bin/prometheus --version` binary-alive proxy) which is the safe default given:

1. The Prometheus 3.11.3 image is built on a distroless base -- no shell, no curl, no wget (so CMD-SHELL probes are off the table).
2. Public Prometheus 3.x CLI documentation lists no `--health` flag (the closest equivalent is the HTTP `/-/healthy` and `/-/ready` endpoints, which are HTTP-layer not CLI-layer).
3. The verify task's in-network `/-/ready` curl + `/api/v1/targets` + `/api/v1/rules` chain is the authoritative readiness gate either way.

If a future UAT pass discovers `--health` actually works (Outcome A), flipping `prometheus_healthcheck_test: ["CMD", "/bin/prometheus", "--health"]` in inventory is a one-line operator change with no role restructure. If `--version` also doesn't work as a HEALTHCHECK (Outcome C), `prometheus_healthcheck_enabled: false` flips the role to State.Running mode with the same one-line operator change.

## OTelCollectorDroppingSignals prefix correction confirmation

Per the plan's CRITICAL RESEARCH correction #2:

> OTel self-metrics for refused records use prefix `otelcol_receiver_refused_*`, NOT `otelcol_processor_refused_*`.

The rendered `rules-baseline.yml.j2` uses the receiver-side prefix:

```yaml
- alert: OTelCollectorDroppingSignals
  expr: |
    (
      rate(otelcol_receiver_refused_spans[5m])
      + rate(otelcol_receiver_refused_log_records[5m])
      + rate(otelcol_receiver_refused_metric_points[5m])
    ) > 0
```

Confirmed via:
- `grep -q "otelcol_receiver_refused_spans" roles/prometheus/templates/rules-baseline.yml.j2` -> match
- `grep -q "otelcol_receiver_refused_log_records" ..` -> match
- `grep -q "otelcol_receiver_refused_metric_points" ..` -> match
- `! grep -q "otelcol_processor_refused" ..` -> zero matches (PASS)

The README's Baseline Alert Rules section documents the correction inline with a "Note on OTelCollectorDroppingSignals (RESEARCH correction #2)" paragraph naming both prefixes and explaining why the receiver-side counters are the canonical names.

## D-25 Deviation List (per plan output spec)

The full audit narrative is in `roles/prometheus/README.md` under "Deviations from upstream INSPQ (D-25)". TL;DR machine-greppable bullets:

- Dropped: K8s helm/operator branches, French strings, restart_policy `always`, `America/Toronto` TZ, remote-write-receiver feature flag, otlp-receiver feature flag, URL-encoded alert rule format, `prometheus_retention_size`, `prometheus_alertmanager_alerting_rules` extension surface, UFW rules, `:latest` tag.
- Replaced: retention `30d` -> `15d`; nested `root_dir/data_dir/config_dir` -> flat `/opt/telemetron/prometheus/<file>`.
- Added: Pitfall 3 metric_relabel_configs labeldrop defaults; four baseline alert rules (INGEST-03); three default scrape jobs (D-42 + INGEST-08); remote_write to Mimir as M1 default (INGEST-02); in-network verify one-shot (D-54).
- Kept: single-server monolithic Prometheus; 15s scrape_interval; named Docker volume.

## User Setup Required

None -- prometheus has no auth surface in M1 (D-26 single-tenant Mimir), no vault keys (D-55), and no rendered-config secrets. Operator only needs the existing Phase-1 inventory and a Docker host with the `telemetron` Docker bridge network (created by deploy_docker.yml pre_tasks).

## Next Phase Readiness

- prometheus is in place for Plan 03-04 (Fluent Bit) -- Fluent Bit ships logs to OTel Collector (which forwards to Loki); Prometheus does not directly interact with Fluent Bit. The Phase 3 ingest plane is now complete except for the log shipper.
- Phase 4 (alertmanager + hook_router) will consume the Prometheus `/api/v1/alerts` endpoint via Alertmanager scrape; the four baseline alert rules will produce live alerts the moment Alertmanager is wired up.
- Phase 5 (grafana) will add a Prometheus datasource at `http://prometheus:9090` and a Mimir datasource at `http://mimir:9009/prometheus` -- the 15d/12h retention split documented in this plan's README ensures recent queries hit Prometheus and older queries hit Mimir.
- The Phase-3 canonical role shape now supports THREE-template extension (production config + two supplementary rule docs) -- precedent for any future role that needs a base config plus multiple supplementary docs (e.g., Grafana dashboards + datasources + alert rules).
- **Live UAT proof (deferred):** A fresh-from-Phase-2 homelab boot of `ansible-playbook --tags prometheus` plus the two-back-to-back-runs `changed=0` idempotency check are documented in the success criteria but deferred to the Phase 3 verification stage (consistent with Phase 2 + Plans 03-01/03-02 precedent).

## Self-Check: PASSED

**Files (10 created + 2 modified):**
- FOUND: roles/prometheus/defaults/main.yml
- FOUND: roles/prometheus/tasks/main.yml
- FOUND: roles/prometheus/tasks/verify.yml
- FOUND: roles/prometheus/templates/prometheus.yml.j2
- FOUND: roles/prometheus/templates/rules-baseline.yml.j2
- FOUND: roles/prometheus/templates/rules-extras.yml.j2
- FOUND: roles/prometheus/handlers/main.yml
- FOUND: roles/prometheus/meta/main.yml
- FOUND: roles/prometheus/README.md
- FOUND: inventory/example-homelab/group_vars/all/prometheus.yml
- FOUND: playbooks/deploy_docker.yml (prometheus wired after opentelemetry)
- FOUND: roles/README.md (prometheus row ticked)
- FOUND: .planning/phases/03-ingest-plane/03-03-prometheus-SUMMARY.md

**Commits (11 task commits):**
- FOUND: a9748e1 (Task 1 scaffold)
- FOUND: 18062a5 (Task 2 defaults)
- FOUND: e506f65 (Task 3 prometheus.yml.j2)
- FOUND: 395f7f4 (Task 4 rules-baseline.yml.j2)
- FOUND: b8832a4 (Task 5 rules-extras.yml.j2)
- FOUND: 742ef52 (Task 6 tasks/main.yml)
- FOUND: ece7f91 (Task 7 tasks/verify.yml)
- FOUND: 1544d60 (Task 8 handlers/main.yml)
- FOUND: 5cf5ddb (Task 9 README.md)
- FOUND: aa95f26 (Task 10 inventory + playbook wiring)
- FOUND: db42699 (Task 11 roles/README.md tick + gates)

**Plan metadata commit:** appended next.

---
*Phase: 03-ingest-plane*
*Completed: 2026-05-18*
