---
gsd_state_version: 1.0
milestone: v0.32.1
milestone_name: milestone
status: verifying
stopped_at: Completed 05-03-promlens-PLAN.md
last_updated: "2026-05-19T11:45:29.877Z"
last_activity: 2026-05-19
progress:
  total_phases: 11
  completed_phases: 6
  total_plans: 17
  completed_plans: 17
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-17)

**Core value:** A homelab operator can clone the repo, edit one hostname in the example inventory, run a single Ansible playbook, and end up with a working LGTM + Alertmanager + hook-router observability plane on a single Docker host.
**Current focus:** Phase 05 — ui-plane

## Current Position

Phase: 05 (ui-plane) — EXECUTING
Plan: 3 of 3
Status: Phase complete — ready for verification
Last activity: 2026-05-19

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-foundation-storage P02 | 4 | 3 tasks | 8 files |
| Phase 01-foundation-storage P01 | 8min | 3 tasks | 4 files |
| Phase 01-foundation-storage P03 | 8min | 3 tasks | 9 files |
| Phase 02-telemetry-backends P01 | 7 min | 3 tasks | 12 files |
| Phase 02-telemetry-backends P02 | 8 min | 3 tasks | 11 files |
| Phase 02-telemetry-backends P03 | 7 min | 3 tasks | 11 files |
| Phase 03-ingest-plane P01 | 7min | 8 tasks | 9 files |
| Phase 03-ingest-plane P02-opentelemetry | 9 min | 10 tasks | 11 files |
| Phase 03-ingest-plane P03-prometheus | 9 min | 11 tasks | 12 files |
| Phase 03-ingest-plane P04-fluentbit | 8 min | 10 tasks | 9 files |
| Phase 03 P05 | 9 min | 10 tasks | 16 files |
| Phase 04-alert-plane P1 | 13min | 7 tasks tasks | 16 files files |
| Phase 04-alert-plane P02 | 13min | 7 tasks | 10 files |
| Phase 04.1-drop-vault-prefix P01 | 105 | 7 tasks | 20 files |
| Phase 05 P01 | 14 min | 3 tasks | 24 files |
| Phase 05 P02 | 7 | 2 tasks | 11 files |
| Phase 05 P03 | 8 | 2 tasks | 10 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work (Phase 1):

- MinIO bucket bootstrap is a blocking step inside the `minio` role — downstream backends do not start until `mc mb --ignore-existing` exits for all five buckets (highest-impact M1 pitfall).
- Pinned MinIO `RELEASE.2025-04-22T22-12-26Z` with loud README note; Garage migration queued for a future milestone.
- All vault references use `vault_<role>_<purpose>` naming; `.vault_pass` in `.gitignore`; `vault.yml.example` ships in `inventory/example-homelab/`.
- INSPQ grep gate (`inspq|qc\.ca|montreal|québec|vault_inspq_` + non-ASCII check) is established in Phase 1 and enforced on every role port from Phase 2 onward.
- [Phase 01-foundation-storage]: telemetron Docker bridge network created in playbook pre_tasks tagged [always, network], not in any role (D-04)
- [Phase 01-foundation-storage]: Five MinIO buckets in storage.yml (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts) consumed by Phase 2 roles
- [Phase 01-foundation-storage]: vault_<role>_<purpose> naming pattern established; vault.yml gitignored; vault.yml.example committed with CHANGE_ME placeholders
- [Phase 01-foundation-storage]: Drop application_web_docker from M1: reverse-proxy-agnostic design; network plumbing moves to playbook pre_tasks (D-01, D-04)
- [Phase 01-foundation-storage]: Drop postgres from M1: Grafana uses embedded SQLite; FOUND-03 removed from REQUIREMENTS.md (D-02)
- [Phase 01-foundation-storage]: M1 role count is 14: alertmanager, fluentbit, grafana, hook_router, karma, loki, mimir, minio, nfsd, node_exporter, opentelemetry, prometheus, promlens, tempo (D-03)
- [Phase 01-foundation-storage]: Per-role port-acceptance gates established in Phase 1 (D-21): grep, image-pin, vault, idempotency, healthcheck+restart, README schema — canonical reference in roles/README.md
- [Phase 01-foundation-storage]: ansible.cfg with roles_path=roles is required at project root for ansible-playbook to find roles/ from any working directory -- established in Plan 03 (confirmed by syntax-check failure without it)
- [Phase 01-foundation-storage]: minio role canonical patterns established (D-10a docker_container_info HEALTHCHECK poll, W6 single-handler, W7 changed_when:false for mc tasks, W8 mc ls --json verify, OPS-03 README schema) -- Phase 2-6 roles mirror this template
- [Phase 02-telemetry-backends]: Loki image pinned to grafana/loki:3.7.2 with TSDB schema v13 and -target=all monolithic CLI; auth_enabled:false (D-26); explicit gRPC port pin 9095 (D-28)
- [Phase 02-telemetry-backends]: D-27 per-backend vault key surface established: vault_loki_s3_access_key / vault_loki_s3_secret_key alias to vault_minio_root_user / vault_minio_root_password -- cheap forward-compat for the deferred per-backend MinIO IAM hardening
- [Phase 02-telemetry-backends]: D-25 INSPQ grep gate is interpreted as code/config-only (excluding README documentation) so the D-25-mandated 'Deviations from upstream INSPQ' README section can document the audit without tripping the gate
- [Phase 02-telemetry-backends]: Tempo image pinned to grafana/tempo:2.10.5 with -target=all monolithic CLI; D-29/BACK-05 OTLP receivers on internal-only :14317/:14318; D-28 gRPC port pin 9096
- [Phase 02-telemetry-backends]: D-34 dual-knob retention -- BOTH block_retention 168h AND compacted_block_retention 1h in rendered config with inline Pitfall 10 citation; single-knob silently fails (highest-impact M1 Tempo pitfall)
- [Phase 02-telemetry-backends]: D-38 resolved to path (b) -- metrics-generator [service-graphs, span-metrics, local-blocks] persists to local WAL at /var/tempo/generator/wal; zero remote_write in rendered config (Tempo startup decoupled from Mimir)
- [Phase 02-telemetry-backends]: Conditional Docker HEALTHCHECK pattern via tempo_healthcheck_enabled + Ansible omit magic value -- handles RESEARCH Finding 6 MEDIUM-confidence distroless health-binary uncertainty; image probe confirmed Outcome B (-version proxy) for Tempo 2.10.5
- [Phase 02-telemetry-backends]: Mimir image pinned to grafana/mimir:3.0.6 with -target=all monolithic CLI; D-28 gRPC port 9097 (completes no-clash port trinity: Loki 9095 / Tempo 9096 / Mimir 9097)
- [Phase 02-telemetry-backends]: D-26 multitenancy_enabled:false in Mimir -- single-tenant anonymous; Phase 3 Prometheus remote_write needs no X-Scope-OrgID header
- [Phase 02-telemetry-backends]: D-36 / Pitfall 11 + Pitfall 3 five-knob monolithic tuning in Mimir (max_global_series_per_user 500000, max_global_series_per_metric 100000, query_store_after 12h, bucket_store.sync_interval 5m, compactor.cleanup_interval 5m) -- all five inline-cited in rendered config; upstream had ZERO of these guards (highest-impact D-25 improvement)
- [Phase 02-telemetry-backends]: D-39 / BACK-04 / Pitfall G three-distinct-bucket S3 trinity in Mimir -- blocks_storage.s3.bucket_name=mimir-blocks, ruler_storage.s3.bucket_name=mimir-ruler, alertmanager_storage.s3.bucket_name=mimir-alerts; Mimir refuses to start sharing bucket+prefix across stores
- [Phase 02-telemetry-backends]: Mimir image probe confirmed Outcome B: no native -health flag in grafana/mimir:3.0.6; default mimir_healthcheck_test=[CMD,/bin/mimir,-version] binary-alive proxy; authoritative readiness gate is verify task's /ready curl probe -- reuses Plan 02-02 Tempo conditional-healthcheck pattern verbatim
- [Phase 02-telemetry-backends]: Phase 2 FEATURE-COMPLETE: deploy_docker.yml roles list is minio -> loki -> tempo -> mimir in dependency order; D-27 vault alias surface complete (six keys: 2x Loki + 2x Tempo + 2x Mimir aliasing to MinIO root creds); canonical role template proven across four roles
- [Phase 03-ingest-plane]: Image registry: Quay (quay.io/prometheus/node-exporter) over Docker Hub matches Phase-1 alertmanager registry choice and avoids Docker Hub rate-limit risk
- [Phase 03-ingest-plane]: node_exporter pinned to v1.11.1 (RESEARCH Finding 6, 2026-04-07 release) -- corrects CONTEXT.md's stale v1.8.x mention
- [Phase 03-ingest-plane]: Conditional-HEALTHCHECK Outcome B (--version binary-alive proxy) is the safe default for from-scratch node_exporter image; authoritative readiness gate is verify task's in-network /metrics curl asserting node_cpu_seconds_total
- [Phase 03-ingest-plane]: Container hardening (read-only/cap_drop/no-new-privileges/tmpfs/pids_limit) kept from upstream but guarded by node_exporter_container_hardening_enabled knob -- six fields collapse to omit when false for RHEL/SELinux flexibility
- [Phase 03-ingest-plane]: Phase-3 canonical role shape (Wave 1) proven on a stateless no-config role: no rendered config dir, no Docker volume, three RO bind-mounts (/proc /sys /), pid_mode host -- template for subsequent Phase-3 plans
- [Phase 03-ingest-plane]: D-44 AMENDED: loki exporter removed from contrib in v0.131.0 (RESEARCH Finding 2 PR 33169); v0.152.0 ships otlphttp/loki to http://loki:3100/otlp (Loki 3.7.2 native OTLP, auth_enabled:false) -- README subheading 'Loki exporter replaced by otlphttp (upstream removal)' documents amendment
- [Phase 03-ingest-plane]: D-43 dual-exporter forward-compat: BOTH prometheus AND prometheusremotewrite declared unconditionally in production config.yaml.j2; metrics pipeline reference flips via Jinja conditional on telemetron_otel_metrics_path knob (default 'prometheus'); future flip requires no role rewrite
- [Phase 03-ingest-plane]: D-54 approach (a) verify topology: SEPARATE verify-config.yaml.j2 template loaded by one-shot OTel container with auto_remove; exercises D-43 prometheusremotewrite to Mimir end-to-end without polluting production config -- two-template role layout pattern reusable for future roles with dual-mode knobs
- [Phase 03-ingest-plane]: D-52 Approach A Docker socket bind: ansible.builtin.getent detects host docker GID; docker_container.groups: wires container into that GID at runtime; /var/run/docker.sock bind-mount is :ro (kernel-level write block); Threat Model section in README documents API-layer caveat + docker-socket-proxy deferred hardening
- [Phase 03-ingest-plane]: D-51 docker_stats receiver: container.restarts AND container.uptime explicitly opt-in (default-disabled per RESEARCH correction #4); scope = ALL containers per D-53 (no excluded_images); after OTel-to-Prometheus translation surfaces as container_restarts_total (Plan 03-03 alert rule expects this exact name)
- [Phase 03-ingest-plane]: D-45 Pitfall 5 LOCKED ratios baked in: mem_limit 512m, GOMEMLIMIT 400MiB (80%), memory_limiter.limit_mib 260 (65% of GOMEMLIMIT), spike_limit_mib 80 (20% of GOMEMLIMIT); pipeline order LOCKED [memory_limiter, batch] LITERAL in all three pipelines; sending_queue + retry_on_failure on every push exporter (pull prometheus exporter intentionally omits)
- [Phase 03-ingest-plane]: OTLP-publish-conditional per-port-set knob: only :4317/:4318 follow opentelemetry_publish_otlp (default true); :8888 self-metrics + :8889 app-metrics stay INTERNAL ALWAYS for Prometheus DNS scrape (D-42); pattern emerges when a role has external-facing ports AND internal-only scrape ports
- [Phase 03-ingest-plane]: Image pin v3.11.3 (RESEARCH Finding 6, 2026-04-27 release) selected over v3.5.1 LTS for current homelab quickstart audience; LTS is one-knob inventory flip
- [Phase 03-ingest-plane]: OTelCollectorDroppingSignals uses otelcol_receiver_refused_{spans,log_records,metric_points} prefix per RESEARCH correction #2 -- CONTEXT.md processor_refused_* mention SUPERSEDED
- [Phase 03-ingest-plane]: Three default scrape jobs (otel_self/otel_metrics/node_exporter) hardcoded as DEFAULTS in rendered config; operators add more via prometheus_extra_scrape_configs but cannot remove the three (they define the M1 telemetry contract)
- [Phase 03-ingest-plane]: Pitfall 3 mitigation per-default-scrape-job (not global): each job ships metric_relabel_configs with explicit pod_uid|container_id|request_id|trace_id + catch-all .*_id labeldrop -- 6 total labeldrop entries in rendered config
- [Phase 03-ingest-plane]: D-25 audit dropped three forbidden Prometheus CLI flags (--web.enable-remote-write-receiver, --enable-feature=remote-write-receiver, --web.enable-otlp-receiver): Telemetron Prometheus WRITES remote_write to Mimir; does not RECEIVE it
- [Phase 03-ingest-plane]: Retention 15d (vs upstream 30d) -- deliberately longer than Mimir query_store_after 12h so Grafana resolves recent queries against Prometheus while Mimir handles long-term
- [Phase 03-ingest-plane]: Phase-3 canonical role shape extended to THREE-template layout (production config + two supplementary rule docs) -- all three notify single restart handler; precedent for any future role with config + dashboards/datasources/rules
- [Phase 03-ingest-plane]: Fluent Bit 4.2.3 pinned (last 4.x stable, Feb 2026); 5.x line GA May 2026 too new for M1 per CLAUDE.md tech-stack constraints
- [Phase 03-ingest-plane]: D-46 role inversion as headline deviation: Telemetron M1 colocates FB with workloads on a single Docker host (tail /var/lib/docker/containers/*/*-json.log); inverts upstream legacy-host-scoop pattern; user memory project_fluentbit_role_shift.md is source-of-truth narrative
- [Phase 03-ingest-plane]: D-47 Loki label allowlist baked in: {host, env, service, job, level}; high-cardinality keys (container_id, image_id, image_name) NOT promoted (Pitfall 4 source-side mitigation); Q3 simplification - service/job default to container_name; Docker-label promotion deferred to Lua-filter enhancement documented under 'Labeling operator apps'
- [Phase 03-ingest-plane]: D-50 Pitfall 6 mitigation pack THE biggest D-25 improvement: Time_System_Timezone Etc/UTC (Mode 1 DST avoidance, single most impactful one-liner) + Multiline_Flush 5 (Mode 3 fail-fast) + Read_from_Head false (Mode 4 no replay) + storage.type filesystem + storage.max_chunks_up 128 + fallback @timestamp filter (Mode 2); upstream had zero of these
- [Phase 03-ingest-plane]: Phase 3 GAP-CLOSURE-IN-PROGRESS: all four ingest plane roles ported (node_exporter, opentelemetry, prometheus, fluentbit); deploy_docker.yml orchestrates minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus -> fluentbit; canonical Phase-3 role shape proven in four patterns (stateless no-config, two-template production+verify, three-template config+rules, two-template production+parsers); INGEST-07 PARTIAL gap closure landed by Plan 03-05.
- [Phase 03-ingest-plane]: Plan 03-05 INGEST-07 gap closure: Lua filter (string.match, no cjson) extracts org.telemetron.{service,job} from /var/lib/docker/containers/<id>/config.v2.json; 8 stack roles stamp the labels; NO docker socket added
- [Phase 03-ingest-plane]: Iteration-1 design call: NO cjson dependency in enrich.lua (FB 4.2.3 image lacks lua-cjson); string.match on raw JSON for service/job/Name fields; -json suffix strip (:sub(1, -6)) lives in Lua only, NOT in Plan 03-04 Tag_Regex
- [Phase 03-ingest-plane]: Gate 7 added to roles/README.md per-role port-acceptance checklist: every community.docker.docker_container in a Telemetron role MUST stamp org.telemetron.service + org.telemetron.job; Phase 4/5 ports inherit (alertmanager, hook_router, grafana, karma, promlens)
- [Phase 04-alert-plane]: D-58 doc-cascade atomicity: when a phase reshapes scope, spec rewrite and code write live in the same plan -- no in-flight inconsistency between spec saying 'hook router in M1' and code skipping it. Phase 4 dropped from 3-plans-with-hook-router to 1-plan-alertmanager-only (D-56/D-57)
- [Phase 04-alert-plane]: D-63 corrected inhibit-rule syntax: source_matchers/target_matchers (PromQL-style) -- v0.32.1 still accepts deprecated source_match form but emits warnings; Research Q2 amtool check-config verified both syntaxes
- [Phase 04-alert-plane]: Research Q1 explicit HEALTHCHECK via wget --spider in role defaults: image ships none (docker inspect HEALTHCHECK=null); busybox base means wget available (no distroless concern unlike Tempo/Mimir/OTel)
- [Phase 04-alert-plane]: D-69 verify via docker_container_exec for amtool: bundled at /bin/amtool in AM image (Research Q3); avoids one-shot image churn and uses localhost:9093 from inside the container. /api/v2/status config.original is YAML-as-string (Research Q8 Risk-1) so verify uses grep-on-YAML not jq-on-nested-JSON
- [Phase 04-alert-plane]: D-65 severity-label retrofit was a no-op (Research Q11): all four baseline rules already carry severity labels from Phase 3 ship; inline comment in rules-baseline.yml.j2 documents the verification so future regressions are caught
- [Phase 04-alert-plane]: D-66 zero vault keys added in Phase 4: null receiver = no outbound destination; single-host telemetron bridge trust boundary; planning-stub hook-router keys cleaned from vault.yml.example with deferral note pointing at ALERT-V2-01..05
- [Phase 04-alert-plane]: Hook router (Flask + role + bundles + auth) deferred to a future milestone: ALERT-02..06 moved to v2 Requirements as ALERT-V2-01..05; M1 trades 'turnkey runbook automation' pitch for 'single-host LGTM observability plane with alerts visible in Karma (Phase 5)'; design preserved in 04-DISCUSSION-LOG.md
- [Phase 04-alert-plane]: Bug 1 TIER 1 fix: alertmanager verify step 5 rewritten with community.docker.docker_container_exec + Ansible until:/retries:/delay: polling against the running AM container; eliminates the auto_remove+detach:false+while-loop race (ansible/ansible#45272 + #47673)
- [Phase 04-alert-plane]: Bug 1 TIER 2 + Bug 2 belt-and-suspenders shared fix: meta:flush_handlers inserted immediately before include_tasks:verify.yml in prometheus + alertmanager tasks/main.yml; guarantees restart handlers fire before downstream verify probes
- [Phase 04-alert-plane]: Bug 2 FIX A: 12 single-file rendered-config bind-mount surfaces across 7 roles collapsed to 7 parent-directory bind mounts; eliminates moby/moby#6011 stale-inode class; tempo special case moves container path from /etc/tempo.yaml to /etc/tempo/tempo.yaml (only container-side path change)
- [Phase 04-alert-plane]: Gate 8 added to roles/README.md banning single-file rendered-config bind mounts; cites moby/moby#6011 and the diagnosis debug doc; future role ports inherit the convention
- [Phase 04-alert-plane]: Auto-fix during UAT (Rule 1): alertmanager verify steps 7 + 9 (amtool alert/silence query) converted from single-shot read to until:/retries:/delay: polling -- amtool alert add returns synchronously but AM dispatch processes async; same race class as Bug 1, same fix shape, same file
- [Phase 04-alert-plane]: TIER 3 deferred: 9 latent docker_container+auto_remove sites in loki/tempo/mimir/prometheus/opentelemetry/fluentbit/node_exporter verify files captured in debug doc; convert when a Phase 5 cross-role probe makes any of them firing rather than latent
- [Phase 04-alert-plane]: All 6 Phase 4 UAT tests pass on leviathan post-04-02 (HEALTHCHECK + receivers + status + Prom->AM + amtool + idempotency); manual atomic-rename inode test proves parent-directory mount semantics work definitively (524589 -> 2097216 visible immediately inside container)
- [Phase 04.1-drop-vault-prefix]: D-90: Drop vault_ prefix -- role-namespace+suffix is self-documenting; prefix implied Ansible Vault tooling enforcement that was never present
- [Phase 04.1-drop-vault-prefix]: vault.yml.example renamed to secrets.yml.example via git mv to preserve rename history; **/secrets.yml added to .gitignore
- [Phase 05]: D-77: Hardcoded datasource UIDs (prometheus, loki, tempo, mimir); pre-rewritten dashboard JSONs committed
- [Phase 05]: D-79/D-80: tracesToLogsV2 on Tempo datasource with service.name->service_name tag; derivedFields on Loki with matcherType:label
- [Phase 05]: D-82: UI plane exempt from telemetron_publish_default:false; grafana_publish_host:true default for browser access
- [Phase 05]: CONFIG_FILE env var is mandatory for Karma -- binary searches CWD (/) by default without it
- [Phase 05]: Karma alertmanager URL is http://alertmanager:9093 (Docker bridge DNS); D-25 audit fix from upstream localhost:9093
- [Phase 05]: Karma alertmanager source name is telemetron (not alertmanager) -- less self-referential in UI (D-25 rename)
- [Phase 05]: PromLens uses CLI flags only (kingpin) -- no PROMLENS_DEFAULT_BACKEND_URL env var (RESEARCH §2.3 correction over CONTEXT.md Claude's Discretion line 152)
- [Phase 05]: D-25 audit: Grafana SA integration dropped from PromLens (no --grafana.url / --grafana.api-token); shared-links SQLite dropped; pure-CLI stateless role
- [Phase 05]: Phase 5 UI Plane complete: 3/3 plans (grafana+karma+promlens); UI-01..UI-06 all delivered; PromLens explicit HEALTHCHECK on root / (no /health endpoint in v0.3.0)

### Roadmap Evolution

- Phase 04.1 inserted after Phase 4: Drop vault prefix (URGENT) -- 2026-05-19. Spec: `.planning/phases/05-ui-plane/05-CONTEXT.md` D-90. Drops the `vault_*` prefix from sensitive variables project-wide; renames 4 roles + 8 vault.yml.example keys + doc cascade. Hard precondition for Phase 5 plan 05-01.

### Pending Todos

None yet.

### Blockers/Concerns

- **Phase 5 blocked on Phase 4.1**: per CONTEXT.md D-90, plan 05-01 must NOT begin until 04.1 lands. Phase 5 inherits the new convention (e.g. `grafana_admin_password`, no `vault_` prefix) — running 05 before 04.1 would create a half-converted codebase.

## Session Continuity

Last session: 2026-05-19T11:45:29.872Z
Stopped at: Completed 05-03-promlens-PLAN.md
Resume file: None
