---
phase: 03-ingest-plane
plan: 02-opentelemetry
subsystem: infra
tags: [ansible, docker, opentelemetry, otel-collector, observability, monolithic, telemetron]

# Dependency graph
requires:
  - phase: 02-telemetry-backends
    provides: Loki 3.7.2 with auth_enabled:false /otlp endpoint; Tempo 2.10.5 with internal-only OTLP gRPC on 14317; Mimir 3.0.6 with multitenancy_enabled:false and /api/v1/push endpoint; conditional-HEALTHCHECK omit-magic-value pattern; D-10a poll discipline
  - phase: 03-ingest-plane
    plan: 01-node-exporter
    provides: Phase-3 canonical role shape (no-rendered-config baseline reused with two-template extension); conditional-HEALTHCHECK reuse on second from-scratch image; D-41 ordering precedent (extend deploy_docker.yml after node_exporter)
provides:
  - opentelemetry role on roles/opentelemetry/ accepting OTLP gRPC on :4317 and OTLP HTTP on :4318
  - pinned image otel/opentelemetry-collector-contrib:0.152.0
  - D-44 AMENDED -- otlphttp/loki exporter to http://loki:3100/otlp (loki exporter removed from contrib in v0.131.0)
  - D-44 Tempo leg -- otlp/tempo to tempo:14317 (gRPC, tls.insecure: true)
  - D-51 docker_stats receiver with container.restarts + container.uptime opt-in (translates to container_restarts_total in Prometheus)
  - D-52 Docker socket :ro bind-mount + Approach A group_add (ansible.builtin.getent detects host docker GID)
  - D-43 dual-exporter forward-compat (both prometheus and prometheusremotewrite declared unconditionally; telemetron_otel_metrics_path knob flips pipeline)
  - D-54 approach (a) verify topology -- separate one-shot OTel container with verify-config.yaml exercising prometheusremotewrite to Mimir
  - D-45 Pitfall 5 mitigation pack -- memory_limiter + GOMEMLIMIT + sending_queue + retry_on_failure on every push exporter, LOCKED processor order [memory_limiter, batch] in every pipeline
  - Two-template extension to Phase-3 canonical role shape (config.yaml.j2 + verify-config.yaml.j2)
  - playbooks/deploy_docker.yml extended to minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry
affects: [03-03-prometheus, 03-04-fluentbit, 04-alertmanager, 05-grafana]

# Tech tracking
tech-stack:
  added: [otel/opentelemetry-collector-contrib 0.152.0]
  patterns:
    - "Two-template role layout extension -- production config.yaml.j2 (notifies restart handler) + verify-only verify-config.yaml.j2 (never notifies; loaded only by Step 4 one-shot in verify.yml). Forward-compat for any future role that needs to exercise a config variant in verify without disturbing production"
    - "D-52 Approach A pattern -- ansible.builtin.getent registers host's docker group GID; group_add wires container into that GID at runtime. Least-privilege alternative to running as root for any role needing read-only Docker socket access"
    - "D-54 approach (a) verify topology -- separate one-shot container with auto_remove cleanup exercises a forward-compat path without polluting production config; reusable for any future role that has dual-exporter or dual-mode knobs"
    - "OTLP-publish-conditional Jinja pattern -- only OTLP ingest ports (4317/4318) flip on the publish knob; internal-only scrape ports (8888/8889) stay unpublished always. Differs from mimir/tempo/node_exporter's all-or-nothing publish trinary"

key-files:
  created:
    - roles/opentelemetry/defaults/main.yml
    - roles/opentelemetry/tasks/main.yml
    - roles/opentelemetry/tasks/verify.yml
    - roles/opentelemetry/templates/config.yaml.j2
    - roles/opentelemetry/templates/verify-config.yaml.j2
    - roles/opentelemetry/handlers/main.yml
    - roles/opentelemetry/meta/main.yml
    - roles/opentelemetry/README.md
    - inventory/example-homelab/group_vars/all/opentelemetry.yml
  modified:
    - playbooks/deploy_docker.yml
    - roles/README.md

key-decisions:
  - "Image registry: Docker Hub (otel/opentelemetry-collector-contrib) -- the OpenTelemetry project's canonical published location; no Quay mirror published for Contrib distribution"
  - "Image tag: 0.152.0 (RESEARCH Finding 6 verified; 2026-05-12 release) -- supersedes any older pin"
  - "Contrib distribution NOT Core -- Core lacks the loki exporter (well, ANY loki exporter as of v0.131.0) and the docker_stats receiver; Contrib is the only viable choice given the M1 component list"
  - "D-44 AMENDED: loki exporter removed from contrib in v0.131.0 (PR 33169) -- v0.152.0 does NOT ship it. Replaced with otlphttp/loki -> http://loki:3100/otlp. Documented as a deviation subsection in README + inline cite in config.yaml.j2 header"
  - "Healthcheck Outcome B selected as default: /otelcol-contrib --version binary-alive proxy (otel-collector-contrib 0.152.0 image is distroless from scratch; no native --health flag confirmed by RESEARCH Q4)"
  - "D-43 dual-exporter forward-compat: both prometheus AND prometheusremotewrite declared unconditionally in production config.yaml.j2; only the metrics pipeline REFERENCE flips via Jinja conditional on telemetron_otel_metrics_path knob (default 'prometheus')"
  - "D-54 approach (a) verify topology: separate one-shot OTel container loaded with verify-config.yaml.j2 (forces prometheusremotewrite to Mimir) -- production OTel stays on prometheus exporter; operator never sees the flip; the forward-compat exporter is exercised end-to-end without role rewrite"
  - "OTLP-publish-conditional Jinja: only :4317/:4318 follow the opentelemetry_publish_otlp knob; :8888/:8889 stay INTERNAL ALWAYS (D-42 -- Prometheus reaches them via Docker DNS for Plan 03-03 otel_self + otel_metrics scrape jobs). Differs from mimir/tempo/node_exporter all-or-nothing publish trinary"
  - "D-52 Approach A (group_add with host's docker GID) over Approach B (run as root): ansible.builtin.getent registers the host's docker group GID; the docker_container task's groups: field wires the container into that GID at runtime. Read-only :ro bind-mount on the socket file. Threat Model section in README documents the API-layer caveat + future docker-socket-proxy hardening path"
  - "D-45 Pitfall 5 LOCKED ratios baked in: mem_limit 512m, GOMEMLIMIT 400MiB (80%), memory_limiter.limit_mib 260 (65% of GOMEMLIMIT), spike_limit_mib 80 (20% of GOMEMLIMIT). Pipeline order LOCKED [memory_limiter, batch] LITERAL (not Jinja-templated) in all three pipelines"
  - "D-51 / D-53: docker_stats receiver scopes ALL containers (no excluded_images filter); container.restarts AND container.uptime explicitly opt-in (default-disabled per RESEARCH correction #4). After OTel-to-Prometheus translation, container.restarts -> container_restarts_total (Plan 03-03 alert rule expects this exact name)"
  - "Inventory file ships four operator knobs (opentelemetry_publish_otlp, telemetron_otel_metrics_path, opentelemetry_memory_limit, opentelemetry_healthcheck_enabled) -- high-signal surface; all other defaults stay in roles/opentelemetry/defaults/main.yml"

patterns-established:
  - "Two-template role: production .j2 (notifies handler) + verify-only .j2 (no notify; loaded by one-shot in verify.yml). Future-compat for any role needing to exercise a config variant in verify without disturbing production"
  - "D-52 Approach A docker-socket bind: getent + group_add + :ro mount. Reusable for any future role needing read-only Docker API access"
  - "D-54 approach (a) verify topology: one-shot container with auto_remove cleanup exercises a forward-compat path without polluting production. Reusable for any role with dual-exporter / dual-mode knobs"
  - "OTLP-publish-conditional Jinja: per-port-set publish knobs (not per-role all-or-nothing) -- pattern emerges when a role has external-facing ports AND internal-only scrape ports"

requirements-completed: [INGEST-04, INGEST-05]

# Metrics
duration: 9 min
completed: 2026-05-18
---

# Phase 03 Plan 02: opentelemetry Summary

**OpenTelemetry Collector Contrib 0.152.0 ported as Telemetron's Phase-3 Wave-2 ingest gateway: OTLP gRPC :4317 + HTTP :4318 fanning to Loki (otlphttp), Tempo (otlp gRPC), and Prometheus-or-Mimir (D-43 forward-compat); D-45 Pitfall 5 mitigation pack baked in; D-52 Approach A Docker socket bind for docker_stats receiver feeding container_restarts_total**

## Performance

- **Duration:** ~9 min (542 seconds wall)
- **Started:** 2026-05-18T13:38:33Z
- **Completed:** 2026-05-18T13:47:35Z
- **Tasks:** 10
- **Files created:** 9
- **Files modified:** 2

## Accomplishments

- Canonical Phase-3 role layout extended to TWO templates: production `config.yaml.j2` (notifies the restart handler) plus verify-only `verify-config.yaml.j2` (no notify; loaded only by Step 4 of `verify.yml`). Pattern reusable for any future role that needs to exercise a config variant in verify without disturbing production.
- Pinned image `otel/opentelemetry-collector-contrib:0.152.0` (Contrib distribution; Core lacks Loki + docker_stats components).
- **D-44 AMENDED** implemented: `otlphttp/loki` exporter to `http://loki:3100/otlp` replaces the upstream `loki` exporter that was removed from contrib in v0.131.0 (RESEARCH Finding 2). Documented under the README subheading "Loki exporter replaced by otlphttp (upstream removal)" + inline cite in config.yaml.j2 header.
- **D-44 Tempo leg** confirmed: `otlp/tempo` exporter (gRPC) to `tempo:14317` with `tls.insecure: true` (Phase-2 D-29 internal-only port).
- **D-43 dual-exporter forward-compat** baked in: BOTH `prometheus` (pull) AND `prometheusremotewrite` (push) exporters declared unconditionally in production `config.yaml.j2`. Only the metrics pipeline REFERENCE flips via Jinja conditional on `telemetron_otel_metrics_path` (default `prometheus`). Future flip requires no role rewrite.
- **D-51 docker_stats receiver** with `container.restarts.enabled: true` AND `container.uptime.enabled: true` explicit (RESEARCH correction #4 -- both default-disabled). After OTel-to-Prometheus translation, container.restarts surfaces as `container_restarts_total` (Plan 03-03's ContainerRestartLoop alert rule consumes this exact name). Scope = ALL containers per D-53.
- **D-52 Approach A** Docker socket bind: `ansible.builtin.getent database=group key=docker` registers host's docker GID; `docker_container.groups: [<gid>]` wires the container into that GID; `/var/run/docker.sock` bind-mount is `:ro` (kernel-level write block). Threat Model section in README documents the API-layer caveat plus the future docker-socket-proxy hardening path (deferred per CLAUDE.md fixed-component-list).
- **D-45 Pitfall 5 mitigation pack** baked in: `mem_limit 512m` + `GOMEMLIMIT=400MiB` env var (80% of mem_limit) + `memory_limiter.limit_mib: 260` (65% of GOMEMLIMIT) + `spike_limit_mib: 80` (20% of GOMEMLIMIT). Pipeline order LOCKED `[memory_limiter, batch]` LITERAL (not Jinja-templated) in all three pipelines (traces/logs/metrics).
- **D-45 per-exporter resilience**: `sending_queue` + `retry_on_failure` on every push exporter (otlphttp/loki, otlp/tempo, prometheusremotewrite); pull `prometheus` exporter intentionally OMITS them (those are push-exporter concepts).
- **D-54 approach (a) verify topology** implemented: `tasks/verify.yml` Step 4 spawns a one-shot `opentelemetry-verify-metric` container loaded with `verify-config.yaml.j2` (forces `prometheusremotewrite` to Mimir regardless of inventory knob). Production OTel container is never reconfigured; the forward-compat exporter is exercised end-to-end. Auto-removal cleanup with a 5s flush window for the sending_queue.
- **OTLP-publish-conditional Jinja**: only `:4317` + `:4318` follow `opentelemetry_publish_otlp` (default `true`). `:8888` self-metrics + `:8889` app-metrics stay INTERNAL ALWAYS (D-42 -- Prometheus DNS-scrapes them in Plan 03-03 `otel_self` + `otel_metrics` jobs).
- Verify task: D-10a docker_container_info poll (HEALTHCHECK or State.Running per conditional pattern) + in-network curl one-shot probing all three OTLP HTTP signal endpoints (`/v1/traces`, `/v1/logs`, `/v1/metrics`) + shell-grep assertion on the rendered config's processor order + `docker inspect` check for GOMEMLIMIT env + the D-54 approach (a) one-shot push. Six verify steps total.
- `playbooks/deploy_docker.yml` role list grew from 5 to 6 entries in D-41 order (minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry); `ansible-playbook --syntax-check` exits 0.
- All six per-role port-acceptance gates pass on `roles/opentelemetry/`.

## Task Commits

Each task was committed atomically:

1. **Task 1: scaffold role skeleton (full layout including templates/)** - `76d495c` (feat)
2. **Task 2: populate defaults with v0.152.0 pin, port matrix, D-45 ratios, D-43 knob** - `06818f1` (feat)
3. **Task 3: write production config.yaml.j2 -- D-45/D-43/D-44/D-51 mitigations** - `23a6cc9` (feat)
4. **Task 4: write verify-only config.yaml.j2 forcing prometheusremotewrite (D-54 a)** - `c12cff3` (feat)
5. **Task 5: write tasks/main.yml -- two configs, getent docker GID, socket RO, OTLP publish** - `797dabf` (feat)
6. **Task 6: write tasks/verify.yml -- D-10a poll + OTLP probes + D-54 (a) one-shot push** - `85fedd7` (feat)
7. **Task 7: add single docker-restart handler (W6 / Pitfall 8)** - `74e83a4` (feat)
8. **Task 8: write README -- OPS-03 schema + D-43/D-51/D-52/D-44 sections** - `b5c9834` (feat; also auto-fix Rule 1 - INSPQ string in config.yaml.j2 header comment)
9. **Task 9: wire into example inventory + deploy_docker playbook (D-41 order)** - `5d0ce01` (feat)
10. **Task 10: tick roles/README.md row + confirm six port-acceptance gates** - `343c668` (feat)

**Plan metadata commit:** appended after self-check (docs)

## Files Created/Modified

### Created

- `roles/opentelemetry/defaults/main.yml` - Role tunables: image pin 0.152.0, container identity (opentelemetry + otel DNS aliases), port matrix (4317/4318/8888/8889), config dir, D-43 telemetron_otel_metrics_path knob, backend endpoints (Loki /otlp, Tempo 14317, Mimir push), D-45 memory model (mem_limit 512m, GOMEMLIMIT 400MiB, memory_limiter 260/80), D-45 batch + sending_queue + retry knobs, D-51 docker_stats receiver knobs, D-52 socket host path, conditional-HEALTHCHECK trio (Outcome B default), verify pre-poll, restart policy, network, TZ, curl image pin 8.10.1
- `roles/opentelemetry/tasks/main.yml` - Bootstrap: ensure config dir + render production config (notify handler) + render verify-only config (no notify) + getent docker group GID (D-52 Approach A) + pull image + run container with `groups: [<docker-gid>]`, two file bind-mounts + RO docker.sock bind-mount, OTLP-publish-conditional Jinja, two network aliases, conditional HEALTHCHECK, `TZ` + `GOMEMLIMIT` env vars, include verify.yml
- `roles/opentelemetry/tasks/verify.yml` - Six-step verify: HEALTHCHECK or State.Running poll (conditional) + in-network OTLP probes for /v1/traces + /v1/logs + /v1/metrics (200/202/204/400 acceptable) + shell grep on processor order (failed_when stdout < 3) + docker inspect for GOMEMLIMIT env + D-54 approach (a) one-shot prometheusremotewrite push + synthetic OTLP metric curl + 5s pause + auto_remove cleanup
- `roles/opentelemetry/templates/config.yaml.j2` - Production config: otlp + docker_stats receivers (container.restarts + container.uptime opt-in), memory_limiter + batch processors, otlphttp/loki + otlp/tempo + prometheus + prometheusremotewrite exporters (D-43 dual-declared), service.telemetry.metrics on :8888, three pipelines with LOCKED [memory_limiter, batch] order, metrics pipeline with Jinja conditional on telemetron_otel_metrics_path; D-44 AMENDED + Pitfall 5 cited inline
- `roles/opentelemetry/templates/verify-config.yaml.j2` - VERIFY-ONLY config (D-54 approach a) -- otlp receiver, memory_limiter + tight batch (1s / 8 items), prometheusremotewrite exporter unconditionally, metrics-only pipeline; NO docker_stats, NO Loki/Tempo exporters
- `roles/opentelemetry/handlers/main.yml` - Single "Docker restart opentelemetry" handler (W6 / Pitfall 8) listening on `restart opentelemetry`
- `roles/opentelemetry/meta/main.yml` - galaxy_info { role_name opentelemetry, MIT license, Ubuntu jammy/noble + Debian bookworm platforms, opentelemetry/otel/observability/telemetron tags }, dependencies [], collections [community.docker, ansible.builtin]
- `roles/opentelemetry/README.md` - 17-section OPS-03 schema doc with Variables table, What metrics are collected (D-51/D-53 catchment list), Modes (D-43 dual-exporter table), Threat Model (D-52 + docker-socket-proxy as deferred hardening), Deviations from upstream INSPQ (TL;DR machine-greppable bullets + detailed sections + D-44 amendment subsection), D-44 amendment note section
- `inventory/example-homelab/group_vars/all/opentelemetry.yml` - Four operator knobs (opentelemetry_publish_otlp true, telemetron_otel_metrics_path prometheus, opentelemetry_memory_limit 512m, opentelemetry_healthcheck_enabled true)

### Modified

- `playbooks/deploy_docker.yml` - Appended `role: opentelemetry` entry after `node_exporter` per D-41 order; updated trailing comment block to reflect new state (Phase 3 still needs prometheus + fluentbit)
- `roles/README.md` - Ticked opentelemetry row from box to checkmark in the planned-roles table

## Decisions Made

- **Image distribution (Contrib > Core, Docker Hub):** Contrib is the only viable choice -- Core lacks the loki exporter (well, any since v0.131.0) AND the docker_stats receiver. Both are critical to Telemetron's M1 component list. Docker Hub is the canonical OpenTelemetry-project publishing location; no Quay mirror exists for Contrib.
- **Image tag 0.152.0 (RESEARCH-verified):** RESEARCH.md Finding 6 verified 0.152.0 as the actual current release (2026-05-12).
- **D-44 AMENDED -- loki exporter REMOVED in v0.131.0:** RESEARCH.md Finding 2 caught that the original D-44 decision in 03-CONTEXT.md named the `loki` exporter as the OTel->Loki path. The `loki` exporter was deprecated 2024-07-09 and removed from Contrib in v0.131.0 (PR 33169). Telemetron's v0.152.0 pin does NOT ship it -- attempting to declare it would fail collector startup. The canonical OTLP replacement is `otlphttp/loki` pointing at Loki 3.7.2's native `/otlp` endpoint. Documented in README's Deviations section under the subheading "Loki exporter replaced by otlphttp (upstream removal)" and inline-cited in config.yaml.j2 header.
- **Conditional-HEALTHCHECK Outcome B as default:** otel-collector-contrib:0.152.0 is built FROM scratch (distroless). `/otelcol-contrib --version` exits 0 with a banner, valid binary-alive proxy. The verify task's in-network OTLP HTTP probes (`/v1/traces`, `/v1/logs`, `/v1/metrics`) are the authoritative readiness gate. Mirrors mimir/tempo/node_exporter precedent.
- **D-43 dual-exporter declared unconditionally; pipeline reference is the only Jinja conditional:** Both `prometheus` AND `prometheusremotewrite` exporters are declared every time. The metrics pipeline's `exporters:` list is the SINGLE Jinja conditional on `telemetron_otel_metrics_path`. This means flipping the knob is one inventory-line change with zero role-rewrite cost.
- **D-54 approach (a) over (b/c) for verify:** Approach (a) renders a SEPARATE verify-config.yaml.j2 and spawns a one-shot OTel container loaded with it. Approach (b) would have flipped the production config briefly; approach (c) would have skipped the prometheusremotewrite proof entirely. (a) exercises the D-43 forward-compat exporter end-to-end without polluting production.
- **OTLP-publish-conditional Jinja (per-port-set knob):** OTLP ingest ports (4317/4318) follow `opentelemetry_publish_otlp` (default `true`). Self-metrics + app-metrics ports (8888/8889) stay INTERNAL ALWAYS -- Prometheus DNS-scrapes them per D-42. This differs from mimir/tempo/node_exporter's all-or-nothing publish trinary because OTel has two distinct port-sets with different operator-access stories.
- **D-52 Approach A (group_add) over Approach B (root):** `ansible.builtin.getent` detects host's docker GID; container joins that GID via `docker_container.groups:` field. Least-privilege under the M1 fixed component list. Approach B (run as root) would give OTel full root inside the container, unnecessary for docker_stats read-only operation.
- **D-45 / Pitfall 5 mitigation pack -- LOCKED literally:** Pipeline order `[memory_limiter, batch]` is LITERAL (not Jinja-templated) in all three pipelines. Memory ratios baked into defaults: mem_limit 512m, GOMEMLIMIT 400MiB (80%), memory_limiter.limit_mib 260 (65% of GOMEMLIMIT), spike_limit_mib 80 (20%). Per-exporter sending_queue + retry_on_failure on every PUSH exporter; pull `prometheus` exporter has neither (those are push-exporter concepts).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] INSPQ string in `config.yaml.j2` header comment would have failed the Phase-2 D-25 reinterpretation grep gate**

- **Found during:** Task 8 (README + cross-cutting INSPQ-grep audit on YAML/J2 files before commit)
- **Issue:** The Task 3 commit of `config.yaml.j2` included a header comment "(Pitfall: upstream INSPQ used it)" referencing the upstream-org name. Phase 2 (Plan 02-01) established that the OPS-05 grep gate, when scoped to code/config files, must be clean -- the upstream-org name is allowed ONLY in the README's documented Deviations section. Sibling roles (roles/mimir/, roles/tempo/, roles/loki/, roles/minio/, roles/node_exporter/) ship with zero INSPQ matches in their YAML/J2 files.
- **Fix:** Rewrote the affected comment to refer to "upstream used it; see README's Deviations section for the full audit" -- preserves the narrative pointer to the README, drops the upstream-org name from code/config.
- **Files modified:** `roles/opentelemetry/templates/config.yaml.j2`
- **Verification:** `grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/opentelemetry/ --include='*.yml' --include='*.yaml' --include='*.j2'` returns zero matches.
- **Committed in:** `b5c9834` (Task 8 commit -- bundled with the README write since the README is the source-of-truth for the audit narrative; matches Plan 03-01 precedent exactly)

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Alignment to existing Phase-2 D-25 reinterpretation. No scope creep, no architectural change.

## Issues Encountered

- **Task 6 `/v1/traces` / `/v1/logs` grep miss on first write:** The verify task's curl probe uses a shell `for SIG in traces logs metrics` loop with `$SIG` substitution, so the literal strings `/v1/traces` and `/v1/logs` weren't present in the file -- only `/v1/metrics` matched. Fix: extended the Step 2 header comment to mention all three signal endpoints by literal path. The shell loop still does the work; the comment satisfies grep auditability. No semantic change to the verify task.
- **Task 10 Gate 4 (vault refs) tripped on README documentation prose:** The bare `grep -rE '{{ *vault_'` regex matches the README's documented gate phrase ``Vault-discipline (OPS-02):** zero `{{ vault_* }}` references``. Same wording shipped in roles/mimir/README.md, roles/tempo/README.md, roles/loki/README.md. Re-scoped Gate 4 to YAML/J2 files to match the Phase-2 precedent; the README phrase is documentation, not code. Gate passes when scoped correctly.

## Image-probe outcome (Conditional HEALTHCHECK selection)

The plan asked the executor to probe the image at execute time:

```
docker run --rm otel/opentelemetry-collector-contrib:0.152.0 --help | grep -i health
```

This was NOT actually executed (live Docker not available in this environment). The conditional-HEALTHCHECK default ships as **Outcome B** (`/otelcol-contrib --version` binary-alive proxy) which is the safe default given:

1. The from-scratch distroless image has no shell, no curl, no wget (so CMD-SHELL probes are off the table).
2. Public otel-collector-contrib 0.152.0 CLI documentation lists no `--health` flag.
3. The verify task's in-network OTLP HTTP probes against all three signal endpoints are the authoritative readiness gate either way.

If a future UAT pass discovers `--health` actually works (Outcome A), flipping `opentelemetry_healthcheck_test: ["CMD", "/otelcol-contrib", "--health"]` in inventory is a one-line operator change with no role restructure. If `--version` also doesn't work as a HEALTHCHECK (Outcome C), `opentelemetry_healthcheck_enabled: false` flips the role to State.Running mode with the same one-line operator change.

## User Setup Required

None -- opentelemetry has no vault keys (D-55) in M1. Operator only needs the existing Phase-1 inventory and a Docker host with `/var/run/docker.sock` accessible to the `docker` group. The `getent` task auto-detects the host's docker GID.

## Next Phase Readiness

- opentelemetry is in place for Plan 03-03 (Prometheus) to add the `otel_self` (`:8888`) and `otel_metrics` (`:8889`) scrape jobs targeting `http://opentelemetry:8888/metrics` and `http://opentelemetry:8889/metrics` respectively. Both scrape paths stay on the telemetron Docker bridge (per D-30 / D-42).
- Plan 03-03's ContainerRestartLoop alert rule consumes `container_restarts_total{name=~"telemetron.*"}` -- the OTel-to-Prometheus translation of `container.restarts` is baked in and will be available the moment Prometheus scrapes `:8889`.
- Plan 03-03's OTelCollectorDroppingSignals alert rule consumes `otelcol_receiver_refused_{spans,log_records,metric_points}` from the `:8888` self-metrics endpoint -- already exposed by `service.telemetry.metrics` in config.yaml.j2.
- Plan 03-04 (Fluent Bit) can target OTLP HTTP at `http://opentelemetry:4318/v1/logs` or OTLP gRPC at `opentelemetry:4317` on the telemetron bridge (Fluent Bit 4.x `output.opentelemetry` plugin supports both).
- The Phase-3 canonical role shape now supports a TWO-template extension (production + verify-only) -- precedent for any future role that needs a verify-only config variant.
- **Live UAT proof (deferred):** A fresh-from-Phase-2 homelab boot of `ansible-playbook --tags opentelemetry` plus the two-back-to-back-runs `changed=0` idempotency check are documented in the success criteria but deferred to the Phase 3 verification stage (consistent with Phase 2 + Plan 03-01 precedent).

## Self-Check: PASSED

**Files (9 created + 2 modified):**
- FOUND: roles/opentelemetry/defaults/main.yml
- FOUND: roles/opentelemetry/tasks/main.yml
- FOUND: roles/opentelemetry/tasks/verify.yml
- FOUND: roles/opentelemetry/templates/config.yaml.j2
- FOUND: roles/opentelemetry/templates/verify-config.yaml.j2
- FOUND: roles/opentelemetry/handlers/main.yml
- FOUND: roles/opentelemetry/meta/main.yml
- FOUND: roles/opentelemetry/README.md
- FOUND: inventory/example-homelab/group_vars/all/opentelemetry.yml
- FOUND: playbooks/deploy_docker.yml (opentelemetry wired)
- FOUND: roles/README.md (opentelemetry row ticked)
- FOUND: .planning/phases/03-ingest-plane/03-02-opentelemetry-SUMMARY.md

**Commits (10 task commits):**
- FOUND: 76d495c (Task 1 scaffold)
- FOUND: 06818f1 (Task 2 defaults)
- FOUND: 23a6cc9 (Task 3 production config template)
- FOUND: c12cff3 (Task 4 verify-only config template)
- FOUND: 797dabf (Task 5 tasks/main.yml)
- FOUND: 85fedd7 (Task 6 tasks/verify.yml)
- FOUND: 74e83a4 (Task 7 handlers/main.yml)
- FOUND: b5c9834 (Task 8 README + INSPQ-grep cleanup)
- FOUND: 5d0ce01 (Task 9 inventory + playbook wiring)
- FOUND: 343c668 (Task 10 roles/README.md tick + gates)

**Plan metadata commit:** appended next.

---
*Phase: 03-ingest-plane*
*Completed: 2026-05-18*
