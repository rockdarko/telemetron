# Phase 4: Alert Plane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered,
> including the mid-discussion scope reshape that pulled the hook router out of M1.

**Date:** 2026-05-18
**Phase:** 04-alert-plane
**Areas discussed:** Plan structure & sequencing; Hook router internals & rules schema; Prometheus → Alertmanager wiring location; Hook router observability surface; Jenkins-scope reconsideration (mid-discussion pivot); Hook-router deferral scope (post-pivot).

---

## Gray Area Selection

| Area | Selected? |
|------|-----------|
| Plan structure & sequencing | ✓ |
| Hook router internals & rules schema | ✓ |
| Prometheus → Alertmanager wiring location | ✓ |
| Hook router observability surface | ✓ |

User selected all four areas.

---

## Area: Plan structure & sequencing (pre-pivot)

### Q1 — How many plans for Phase 4?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 plans | 04-01 Flask source; 04-02 alertmanager; 04-03 hook_router role (incl. sample Jenkinsfiles) | ✓ |
| 2 plans | 04-01 alertmanager; 04-02 hook_router-everything | |
| 4 plans | One per role + a samples-only plan | |

### Q2 — Inter-plan dependency order

| Option | Description | Selected |
|--------|-------------|----------|
| Flask → alertmanager → hook_router role | Build Flask first (unit-testable in isolation), then standalone AM, then deploy role | ✓ |
| Alertmanager → Flask → hook_router role | AM first; Flask later | |
| Alertmanager → bundled-Flask-and-role | Equivalent to "2 plans" — skipped | |

### Q3 — Where do the sample Jenkinsfiles land?

| Option | Description | Selected |
|--------|-------------|----------|
| In plan 04-03 (hook_router role) | Samples co-located with the deployable unit + README | ✓ |
| In plan 04-01 (Flask source) | Samples alongside the app | |
| Own dedicated plan 04-04 | Most decomposed | |

### Q4 — Verify-step scope per plan

| Option | Description | Selected |
|--------|-------------|----------|
| Role-scoped per plan, E2E in 04-03 | Unit-tests in 04-01; AM `:9093/-/ready` in 04-02; E2E synthetic-alert flow in 04-03 | ✓ |
| E2E in every plan that touches the alert path | More confidence, but duplicates fixture work | |
| Single E2E at end | Saves verify code; loses per-plan green/red signal | |

**Outcome (pre-pivot):** 3 plans, dependency-true order, samples in 04-03, role-scoped + E2E-at-end verifies.

---

## Area: Hook router internals & rules schema (pre-pivot)

### Q1 — Where do operators define the allowlist?

| Option | Description | Selected |
|--------|-------------|----------|
| Inventory dict → rules.yml.j2 | Single source of truth in inventory; Ansible templates the file | ✓ |
| Static rules.yml in the repo, operator-forked | Simpler templating; less consistent with rest of Telemetron | |
| Both — ship defaults, inventory merges | Best-of-both; more code; merge semantics get fiddly | |

### Q2 — Rules-reload behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Restart-only via Ansible handler | Matches D-19; no signal-handling code in Flask | ✓ |
| SIGHUP-triggered in-process reload | Slightly faster than restart | |
| File-watch (inotify) auto-reload | Most automatic; inotify edge cases | |

### Q3 — Rate-limit storage

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory dict (Gunicorn workers=1 for exact window) | No extra datastore; restart-resets accepted | ✓ |
| SQLite on persistent volume | Survives restart | |
| Redis sidecar | Out of scope per fixed component list | |

### Q4 — Inbound auth shape

| Option | Description | Selected |
|--------|-------------|----------|
| Bearer token header from vault | `Authorization: Bearer <vault_hook_router_webhook_secret>`; AM native http_config.authorization | ✓ |
| Custom header X-Telemetron-Secret | Same mechanism, custom name; no benefit | |
| mTLS | High-trust; requires PKI; out of scope for M1 homelab | |

**Outcome (pre-pivot):** Inventory-templated rules.yml; restart-only reload; in-memory rate limit; Bearer-token inbound auth.

---

## Area: Prometheus → Alertmanager wiring location

### Q1 — Where does the `alerting: alertmanagers:` block land?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase-4 alertmanager plan extends prometheus.yml.j2 | One plan touches prometheus.yml.j2 once; cohesive Phase-4 boundary | ✓ |
| Phase-4 plan 04-03 (hook_router) extends prometheus.yml.j2 | Delay wiring until receiver exists | |
| Phase-3 gap-closure plan 03-06 first | Cleaner cross-role separation; adds bureaucratic overhead | |
| Inventory knob default-off | Most defensive; defeats core-value promise | |

### Q2 — Alertmanager receivers tree

| Option | Description | Selected |
|--------|-------------|----------|
| Single default receiver `hook-router` | Default route fans to hook_router; operators extend via inventory | ✓ (pre-pivot) → revised post-pivot to `null` |
| Default `null` receiver + hook-router on webhook=true label | Safe-by-default; requires Prometheus rule label coordination | |
| Two default receivers split by severity | Adds severity label dependency on rules | |

### Q3 — Alertmanager persistent state

| Option | Description | Selected |
|--------|-------------|----------|
| Single `telemetron_alertmanager_data` volume on /alertmanager | Standard pattern; preserves silences + nflog | ✓ |
| Ephemeral state | Saves a volume; Pitfall 7 replay-storm risk on restart | |
| Volume + mimir-alerts S3 replication | Over-engineered for single-instance M1 | |

### Q4 — Inhibition rules

| Option | Description | Selected |
|--------|-------------|----------|
| Ship 1 default: critical inhibits warning, equal:[instance] | Standard pattern; requires Phase-3 rules severity-label retrofit | ✓ |
| No defaults — operators add their own | "No opinions" stance; defeats sane-defaults pitch | |
| Ship 3-4 defaults covering baseline alert quartet | More aggressive blast-radius reduction | |

**Outcome:** AM wiring in Phase-4 plan 04-01; (pre-pivot) hook-router default receiver, (post-pivot) `null` default receiver; persistent volume on /alertmanager; one inhibit rule + Phase-3 rules severity-label retrofit.

---

## Area: Hook router observability surface (pre-pivot)

### Q1 — `/metrics` shape

| Option | Description | Selected |
|--------|-------------|----------|
| Counters + histogram | requests_total, jenkins_calls_total, rate_limited_total + latency histogram | ✓ |
| Counters only | Drop histogram | |
| Bare-minimum | Two counters only | |

### Q2 — How is the hook router added as a Prometheus scrape target?

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded default scrape job in prometheus.yml.j2 | Matches Phase-3 D-44 pattern; defaults define M1 telemetry contract | ✓ |
| Via prometheus_extra_scrape_configs | Operator-removable; inconsistent with otel_self/otel_metrics/node_exporter | |
| Hardcoded but in plan 04-03 to avoid chicken-egg DOWN target | Two Prometheus restarts vs one | |

### Q3 — Sample Jenkinsfiles — which 2-3 to ship?

| Option | Description | Selected |
|--------|-------------|----------|
| ops-restart-container ({instance} → docker restart) | ROADMAP SC #5 explicit cite | (pivoted away) |
| ops-filesystem-cleanup ({filesystem} → cleanup) | ROADMAP SC #5 explicit cite | (pivoted away) |
| ops-host-diagnostic-dump ({instance} → tarball) | Safe non-destructive sample | (pivoted away) |
| ops-otel-restart | Self-referential | (pivoted away) |

**User's response:** *"I have thought about it, and I think remediation pipelines to jenkins should be out of scope. Jenkins is not used as much anymore. I dont think thats relevant."*

This response triggered the mid-discussion scope reconsideration below.

### Q4 — Image build mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| community.docker.docker_image build from hooks/router/Dockerfile | Local build on target host; matches self-hosted ethos | ✓ (pre-pivot) |
| Build on workstation, push to registry | Adds registry dependency | |
| Pre-built in CI | Requires CI plumbing not yet in project | |

**Outcome (pre-pivot):** Full counter+histogram /metrics shape; hardcoded scrape job in prometheus.yml.j2; build locally via Ansible.

---

## Mid-discussion pivot: Jenkins scope reconsideration

User's freeform response to "which Jenkinsfiles to ship?" raised a fundamental scope question: is Jenkins still the right target in 2026?

### Q — What to do about Jenkins-specific glue?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep hook router, make it backend-agnostic (generic webhook → CI) | Bigger doc churn; defensible 2026 pitch | ✓ (initial) → revised to defer entirely |
| Keep Jenkins-specific code but drop sample Jenkinsfiles | Smaller doc churn; drops ALERT-05 | |
| Defer hook router entirely; M1 ships Alertmanager only | Cleanest scope reduction; loses "strongest differentiator" framing | (final) |
| Proceed with Jenkins as-specified | No doc churn; assumes Jenkins audience is still strong | |

User initially picked "backend-agnostic." On the follow-up question about the two-tier schema, user pivoted further to **defer the entire hook router** to a future milestone: *"maybe we should completely remove the hook router of the scope and move that to a later phase of its own after we got telemetron running in terms of observability itself?"*

---

## Post-pivot: Hook-router deferral scope

### Q1 — Where do deferred ALERT-02..06 go?

| Option | Description | Selected |
|--------|-------------|----------|
| Move to v2 Requirements as ALERT-V2-01..05 | Consistent with existing v2 framing (HA-01, K8S-01, etc.) | ✓ |
| Drop entirely; defer indefinitely | Cleanest break; loses institutional memory | |
| New milestone-1.5 between M1 and M2 | Heavy process for one-feature milestone | |

### Q2 — Default Alertmanager receiver if no hook router?

| Option | Description | Selected |
|--------|-------------|----------|
| `null` receiver default; Karma is the UI | Sane "alerts visible but nothing fires by surprise" | ✓ |
| Slack-webhook default | Privileges one vendor; out of scope by same logic that defers the hook router | |
| stdout/log sidecar receiver | Adds component not on CLAUDE.md fixed list | |

### Q3 — Plan count for the reshaped Phase 4?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 plan — alertmanager + Prometheus wiring + scope-doc rework | Single atomic plan | ✓ |
| 2 plans — doc rework first, then alertmanager port | Cleaner cross-plan boundary; heavier process | |

### Q4 — hooks/ tree fate

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as README placeholder with future-milestone note | Preserves institutional memory; signals intent | ✓ |
| Remove the hooks/ directory entirely | Cleanest "M1 doesn't ship this" signal | |

### Q5 — Ready to write context?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | All major decisions locked | ✓ |
| Explore more gray areas | Want to think about more | |

---

## Claude's Discretion (final)

The following items the user explicitly delegated to the planner OR are bounded by clear constraints:

- Alertmanager `--log.level` default — `info` (operator override via `alertmanager_log_level`).
- Container CLI args — `--config.file`, `--storage.path`, `--web.listen-address`, `--cluster.listen-address=""`.
- Container name — `telemetron-alertmanager` (matches Phase-1+2+3 naming).
- Config bind-mount layout — `/opt/telemetron/alertmanager/alertmanager.yml` → `/etc/alertmanager/alertmanager.yml:ro`.
- Healthcheck CMD — verify image default during research; fall back to explicit `wget --spider` if distroless.
- `alertmanager_extra_*` defaults — all `[]`.
- Render shape for extra-routes/extra-receivers/extra-inhibit-rules — list-of-dicts iterated with sorted-attribute Jinja.
- Plan 04-01 task order — planner finalizes; suggested order in CONTEXT.md D-69.

## Deferred Ideas

See CONTEXT.md `<deferred>` section. Key items:

- Hook router Flask app, role, samples, observability — all `ALERT-V2-01..05`.
- Hook router design captured in this log (two-tier `hook_router_backends` + `hook_router_rules` schema, Bearer-token inbound auth, in-memory rate limit with `workers=1`, `/metrics` with per-backend labels, sample bundles for GH Actions / Slack / generic, optional Jenkinsfile for historical context) is preserved here for the v2 milestone to pick up without re-discussion.
- Alertmanager `time_intervals` / `mute_time_intervals` — surface if/when operators need them.
- Alertmanager HA cluster mode — re-enable in future HA milestone.

## Auto-resolved

Not applicable — interactive mode, no `--auto`.

## External Research

Not applicable — no `workflow.research_before_questions` enabled.
