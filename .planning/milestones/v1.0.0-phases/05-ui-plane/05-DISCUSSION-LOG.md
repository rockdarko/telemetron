# Phase 5: UI Plane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 05-ui-plane
**Areas discussed:** Plan structure & order, Dashboard source & curation, Trace-to-logs correlation plumbing, Host port publishing, Grafana admin & access model
**Cross-phase decision surfaced:** drop the `vault_` prefix project-wide (D-90 / phase 4.1 insertion)

---

## Area 1: Plan structure & order

### Q1.1: How many plans for Phase 5?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 plans — one per role | Mirrors D-40 exactly: 05-01 grafana, 05-02 karma, 05-03 promlens. Grafana plan is heavyweight; Karma + PromLens lighter but each has its own opinionated decision. Each plan is end-to-end shippable; playbook is runnable at every commit. | ✓ |
| 2 plans — Grafana solo + Karma/PromLens combined | 05-01 grafana (heavy); 05-02 karma + promlens combined. Ties PromLens (deprecation candidate) to Karma — coupling feels wrong. | |
| 1 plan — all three together | Closest to Phase-4 final shape but ignores D-40. Bigger blast radius. | |

**User's choice:** 3 plans — one per role
**Notes:** Locked as D-70.

### Q1.2: Dependency order within Phase 5

| Option | Description | Selected |
|--------|-------------|----------|
| grafana → karma → promlens | Grafana first (datasource provisioning is the de-facto end-to-end smoke test per ROADMAP.md). Karma second (alert UX in M1). PromLens last (deprecation candidate). | ✓ |
| karma → grafana → promlens | Karma first as "finish the alert plane UX." Grafana second; PromLens last. | |
| Roadmap-textual order | Same as option 1 framed differently. Outcome identical. | |

**User's choice:** grafana → karma → promlens
**Notes:** Locked as D-71.

### Q1.3: D-58-style doc-rework cascade scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-role light cascade | Each plan updates roles/README.md (tick box), PROJECT.md "Active" line when count changes, CLAUDE.md if tech-stack row changes. No PROJECT.md Key-Decisions row unless real decision. STATE.md by workflow. | ✓ |
| Single combined cascade in plan 05-01 | Front-load all doc-rework into the first plan; subsequent plans only update roles/README.md row + ROADMAP.md tick. Couples Grafana plan to Karma/PromLens decisions ahead of time. | |
| No cascade until Phase 5 is fully done | One big cascade at end-of-phase. Cleanest commits but risks in-flight inconsistency. | |

**User's choice:** Per-role light cascade
**Notes:** Locked as D-72.

### Q1.4: Phase-5-specific 9th gate

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — "datasources-resolve-real-data" verify gate | Phase-5 Grafana plan adds a verify task: curl GET each provisioned datasource's `/api/datasources/uid/<uid>/health` + query each datasource for a real series. Mirrors D-69 / D-54 in-network-verify pattern. Documents in roles/README.md as Gate 9. | ✓ |
| No — existing 8 gates cover it | Treat datasource verify as just D-54-style in-network verify per plan. Less doc churn. | |
| Yes, but only for Grafana plan | Verify gate exists in plan 05-01 only; Karma + PromLens use standard 8 gates. | |

**User's choice:** Yes — "datasources-resolve-real-data" verify gate
**Notes:** Locked as D-73. Karma + PromLens still pass standard Gates 1-8; Gate 9 is Grafana-specific because Grafana is the only role with cross-component datasource provisioning.

---

## Area 2: Dashboard source & curation

### Q2.1: Source strategy for the 5-10 dashboards

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid — official mixins + 2-3 hand-rolled | Pull official mixin JSONs from Loki/Tempo/Mimir/OTel upstream repos for backend self-metrics. Hand-roll the 2-3 Explore landing pages. node_exporter dashboard from official repo. All committed in `roles/grafana/files/dashboards/*.json` at fork time — no runtime download. | ✓ |
| Build everything from scratch | Minimal panels per dashboard, deliberately small, no external dependencies. Slower to write, less rich. Avoids version-drift problems. | |
| Grafana.com gallery imports | Reference dashboards by Grafana.com ID and let Grafana provisioning fetch on first boot. Requires outbound HTTPS to grafana.com at deploy time — breaks "air-gapped homelab" story. | |

**User's choice:** Hybrid — official mixins + 2-3 hand-rolled
**Notes:** Locked as D-74. Air-gap-friendly: all JSONs committed at fork time; refresh as a maintenance task when mixin shapes change.

### Q2.2: Dashboard count target

| Option | Description | Selected |
|--------|-------------|----------|
| 7 — the UI-03 explicit list | (1) host health / node_exporter, (2) Loki Explore landing, (3) Tempo Explore landing, (4) OTel Collector self-metrics, (5) Loki self-metrics, (6) Tempo self-metrics, (7) Mimir self-metrics. No padding, no surprises. | ✓ |
| 5 — minimal floor | Collapse the three backend self-metrics into one 'LGTM health' dashboard with rows. Saves curation effort, smaller fresh-deploy surface. Loses backend-specific drill-downs. | |
| 10 — add Prometheus, Alertmanager, Karma + 8/9 health | Add backend dashboards for Phase-3/4 components (Prometheus internals, Alertmanager nflog stats). More complete but mostly noise on a homelab. | |

**User's choice:** 7 — the UI-03 explicit list
**Notes:** Locked as D-75. Within UI-03's 5-10 range.

### Q2.3: Provisioning mechanism + operator override pattern

| Option | Description | Selected |
|--------|-------------|----------|
| File-based + drop-in dir | Role ships JSONs in `/etc/grafana/provisioning/dashboards/*.json`. Operator adds dashboards via `grafana_dashboard_extra_dir` inventory knob — bind-mounted alongside. Two folders: `Telemetron` (role-shipped) + `Operator` (operator-supplied). No API calls; survives Grafana restart trivially. | ✓ |
| File-based only, no operator override | Just the role-shipped dashboards. Operators who want more edit them in the UI and SQLite saves the override. Simpler role; loses IaC story for operator dashboards. | |
| API-import on first boot | Role's verify step POSTs each dashboard JSON via Grafana HTTP API. Brittle re-run idempotency; doesn't survive `docker volume rm`. | |

**User's choice:** File-based + drop-in dir
**Notes:** Locked as D-76. Two-folder UI separation keeps role-shipped dashboards visibly distinct from operator dashboards.

### Q2.4: Datasource UID handling in dashboard JSONs

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded UIDs in JSON | UI-02 locks UIDs to `prometheus`, `loki`, `tempo`, `mimir`. Bundled dashboards reference these strings directly. No Jinja templating. Simpler, fewer moving parts. If we ever need operator-renamed UIDs, that's v2. | ✓ |
| Jinja-templated UIDs | Dashboards live under `templates/dashboards/*.json.j2`; Jinja interpolates `{{ grafana_datasource_uid_prometheus }}` etc. UI-02 explicitly says UIDs do NOT change between deploys — conflicts with the spec. | |
| Files now, templates if v2 needs operator-overridable UIDs | Same as option 1 but explicitly call out migration path in role README "Future work" section. Adds maintenance overhead for a future-need. | |

**User's choice:** Hardcoded UIDs in JSON
**Notes:** Locked as D-77. Matches UI-02 spec directly.

---

## Area 3: Trace-to-logs correlation plumbing (UI-04)

### Q3.1: Realistic scope — which logs can carry trace_id?

| Option | Description | Selected |
|--------|-------------|----------|
| OTLP-pushed app logs only | Trace context survives only when operator apps use OTel SDK and push OTLP-native to OTel Collector (which writes via `otlphttp/loki` to Loki 3.7.2's OTLP endpoint). Loki stores `trace_id` as **structured metadata**. FB-tailed Docker stdout/stderr DOES NOT have `trace_id` unless app embeds it. Honest framing: trace-to-logs works for instrumented apps; uninstrumented apps fall back to ad-hoc grep. | ✓ |
| OTLP-pushed + body-regex for `trace_id=<hex>` | Two extractors: structured-metadata derivedField + body-regex derivedField. Wider coverage at the cost of one extra derived field. | |
| Body-regex only | Skip structured-metadata extraction; rely on log lines printing trace_id. Loses OTLP-native correlation story. | |

**User's choice:** OTLP-pushed app logs only
**Notes:** Locked as D-78. Body-regex deferred to a future-Rock decision; honest scope.

### Q3.2: tracesToLogsV2 customQuery shape on Tempo datasource

| Option | Description | Selected |
|--------|-------------|----------|
| `{${__tags}} \| trace_id="${__span.traceId}"` | LogQL filter on structured metadata. `__tags` substituted from configured tag list; `__span.traceId` substituted with actual trace ID. Works for OTLP-pushed logs where Loki surfaces `trace_id` as structured metadata. | ✓ |
| `{${__tags}} \|~ "${__span.traceId}"` | Loose substring search across log body. Covers body-printed trace ids but doesn't use structured-metadata efficiency. Slower. | |
| Defer the exact shape to planner research | Document intent and let planner pin during plan-phase research. Risk: ambiguity surfaces during execution; UAT fails on a typo. | |

**User's choice:** `{${__tags}} \| trace_id="${__span.traceId}"`
**Notes:** Locked as D-79. Pinned now; researcher confirms Grafana 13.0.1 + Loki 3.7.2 syntax during plan-phase research and corrects if needed.

### Q3.3: Forwarded tags from trace to logs

| Option | Description | Selected |
|--------|-------------|----------|
| `service.name` only | OTel pushes `service.name` → Loki surfaces as `service_name` label. tracesToLogsV2 forwards just this one tag. Minimal, predictable, matches LGTM single-tag default. | ✓ |
| `service.name` + `host.name` | Adds host binding. Useful in multi-node operator apps but deepens 999.4 backlog. | |
| Defer to planner | Planner inspects what OTel actually pushes via tcpdump or curl on live :4318 endpoint. | |

**User's choice:** `service.name` only
**Notes:** Locked as D-80. Future: add `host.name` → `host` as second tag if operators consistently want host-scoping.

### Q3.4: 999.4 backlog interplay — fix or accept?

| Option | Description | Selected |
|--------|-------------|----------|
| Accept + document | Phase 5 ships with Loki labels as they actually arrive today (`{host, job, service_name}`). roles/grafana/README.md documents the OTel-to-Loki label mapping. 999.4 stays open; canonical fix (option (c) — relabel on OTel exporter side) lands later. | ✓ |
| Fix the drift inside Phase 5 (option (c)) | Plan 05-01 also touches `roles/opentelemetry/templates/config.yaml.j2` to rename `service.name` → `service` before otlphttp/loki pushes. Single source-of-truth; bigger Phase-5 scope. | |
| Fix the drift on FB side (option (b)) | Plan 05-01 touches FB to push canonical names. Reverses the OTel-pushes-canonical assumption. | |

**User's choice:** Accept + document
**Notes:** Locked as D-81. Phase 5 is the UI plane, not the ingest plane; option (c) belongs in a post-M1 phase.

---

## Area 4: Host port publishing for UI roles (vs D-30)

### Q4.1: D-30 default behavior for UI plane

| Option | Description | Selected |
|--------|-------------|----------|
| UI plane default-on; per-role knob to disable | Each role's `defaults/main.yml` sets `<role>_publish_host: true` (overriding D-30 default-off for UI plane only). Quickstart works out of the box without inventory edits. | ✓ |
| Stay D-30 default-off; operator flips the knob | Pure consistency with Phase-1..4 convention. Quickstart needs explicit "edit inventory to publish ports" step. Annoying friction. | |
| Conditional default `<role>_publish_host: "{{ telemetron_publish_default \| default(true) }}"` | Inverts D-30 default specifically for UI plane via wrapper. Same outcome as option 1 but more Jinja indirection. | |

**User's choice:** UI plane default-on; per-role knob to disable
**Notes:** Locked as D-82. Operators wanting reverse-proxy-only flip per-role to false.

### Q4.2: Bind address for published UI ports

| Option | Description | Selected |
|--------|-------------|----------|
| 0.0.0.0 — LAN-reachable | Homelab operators want browser to hit `http://<homelab-host>:3000` from any LAN IP. Documented in role README with security trade-off (Grafana auth-gated; Karma/PromLens read-only). Operators override per-role via `<role>_bind_address`. | ✓ |
| 127.0.0.1 only — operator tunnels with `ssh -L` | Safest default; quickstart needs ssh-tunnel section. Breaks 'open Grafana, click a dashboard' UX of UI-03 SC-1. | |
| Inventory knob `<role>_bind_address` defaulting to 0.0.0.0 | Same effective default as option 1 but explicit override knob. | |

**User's choice:** 0.0.0.0 — LAN-reachable
**Notes:** Locked as D-83. Per-role `<role>_bind_address` knob surfaced for security-conscious operators.

### Q4.3: Confirm D-31 port matrix

| Option | Description | Selected |
|--------|-------------|----------|
| Keep D-31 — Grafana 3000 / Karma 8082 / PromLens 8081 | All three inventory-overrideable via `<role>_host_port`. Documented in network.yml port-allocation comment block. | ✓ |
| Move Karma to higher non-conflicting port (e.g. 8090) | Avoid 8081/8082 tight pairing in case operator has app on 808x. Cosmetic. | |
| Compress to canonical port range (3000-3002) | Grafana 3000, Karma 3001, PromLens 3002. Neat range but breaks convention that ports loosely reflect component family. | |

**User's choice:** Keep D-31
**Notes:** Locked as D-84.

### Q4.4: Reverse-proxy / TLS recipe location

| Option | Description | Selected |
|--------|-------------|----------|
| `roles/grafana/README.md` 'Reverse proxy' section | Document Caddy/Traefik/nginx recipe in Grafana role README (headline UI). Show inventory knob + reverse-proxy snippet. Cross-ref from `docs/quickstart.md` 'production hardening' subsection. | ✓ |
| Defer entirely to Phase-6 docs/quickstart.md | Phase 5 only ships the knob; Phase 6 documents recipe. Cleanest scope boundary but ships Phase 5 with undocumented production path. | |
| Both — role README + Phase-6 quickstart | Same content in two places. Maintenance burden. | |

**User's choice:** `roles/grafana/README.md` 'Reverse proxy' section
**Notes:** Locked as D-85. Karma + PromLens READMEs cross-reference the Grafana pattern.

---

## Area 5: Grafana admin & access model

### Q5.1: Vault key naming for Grafana admin password

> **Note:** This question surfaced the cross-phase decision D-90 (drop `vault_` prefix project-wide). Original options below are the pre-D-90 framings; the chosen path is the unprefixed name documented in CONTEXT.md D-86.

| Option | Description | Selected |
|--------|-------------|----------|
| `vault_grafana_admin_password` | Matches OPS-02 convention + pre-figured comment in vault.yml.example line 53. | (challenged → rejected) |
| `vault_grafana_admin_user` + `vault_grafana_admin_password` (both vaulted) | Vault both. Marginal value. | |
| Use Ansible vault for password only; hardcode `admin` as username | Same outcome as option 1 framed differently. | |
| **(challenge response)** Drop the `vault_` prefix → `grafana_admin_password` | User rejected the `vault_` prefix on three grounds: (a) adds no value, (b) steers operator toward Ansible vault when vaulting is one option among many, (c) implies tooling enforcement Ansible doesn't provide. Convention dropped project-wide via phase 4.1 insertion (D-90). | ✓ |

**User's choice:** `grafana_admin_password` (no `vault_` prefix)
**Notes:**
- User's exact words: "I dont understand why we put a vault_ prefix to variables... a very very terrible idea... passwords don't need to be vaulted, it's only a good practice."
- Saved as durable user feedback memory (`feedback_no_decorative_convention_prefixes.md`).
- Phase 4.1 (`drop-vault-prefix`) inserted before Phase 5 to execute the rename across 4 existing roles + secrets.yml.example + doc cascade.
- Locked as D-86 (Phase 5 naming) + D-90 (project-wide convention change).

### Q5.2: Anonymous viewer access

| Option | Description | Selected |
|--------|-------------|----------|
| Default off; inventory knob to enable | Grafana defaults `auth.anonymous.enabled: false`. Role exposes `grafana_anonymous_enabled: false` knob. Operators flip to `true` for TV-mode wall display. Conservative default. | ✓ |
| Default on for home dashboard only | `auth.anonymous.enabled: true` with Viewer role. Wall-display works out-of-box. Bigger surprise surface. | |
| Skip anonymous viewer entirely — not in M1 | Don't surface the knob; operators wanting it edit grafana.ini manually. Loses homelab affordance. | |

**User's choice:** Default off; inventory knob to enable
**Notes:** Locked as D-87.

### Q5.3: Admin user details

| Option | Description | Selected |
|--------|-------------|----------|
| Username `admin`, email `admin@telemetron.local` | Standard Grafana convention. Synthetic local-only email. Operators override via `grafana_admin_user` / `grafana_admin_email`. | ✓ |
| Username `telemetron`, email blank | Avoid common-attacker `admin`. But Grafana strongly defaults `admin` for first-login; custom name surprises operators. | |
| Operator-supplied via inventory (no defaults) | Most secure but breaks quickstart's 'one inventory edit' promise. | |

**User's choice:** Username `admin`, email `admin@telemetron.local`
**Notes:** Locked as D-88.

### Q5.4: Grafana org provisioning

| Option | Description | Selected |
|--------|-------------|----------|
| Stock `Main Org.` | Grafana default. No provisioning needed. Operators rename via UI if they care. Smallest moving-parts surface. | ✓ |
| Rename to `Telemetron` | Provision org via Grafana 13.x org provisioning. Cosmetic 'this is our stack' touch. Slight rename foot-gun risk. | |
| Don't touch orgs; let operators self-organize | Same as option 1 framed differently. | |

**User's choice:** Stock `Main Org.`
**Notes:** Locked as D-89.

---

## Cross-phase decision (surfaced during Q5.1)

### D-90: Drop the `vault_` prefix from all sensitive variables, project-wide

**Trigger:** User challenged the `vault_` convention during Q5.1 of Area 5. After review, three failures emerged:
1. **No added value:** `grafana_admin_password` carries the same meaning as `vault_grafana_admin_password`.
2. **Steers the operator:** `vault_*` implies operator MUST use Ansible vault, when vaulting is one option among many.
3. **Implies enforcement that isn't there:** Ansible doesn't read the prefix; `vault_foo` works the same as `foo`. Misleading-by-implication.

**Resolution path chosen (Claude's call, delegated by user "I will let you figure out where to put that in our workflow"):**
- Insert decimal phase **4.1 (`drop-vault-prefix`)** between Phase 4 and Phase 5.
- Phase 4.1 scope: rename across 4 roles' Jinja references + 8 keys in `vault.yml.example` (renamed to `secrets.yml.example`) + doc cascade (PROJECT.md OPS-02, REQUIREMENTS.md OPS-02, roles/README.md Gate 3, Phase 1+2 CONTEXT.md historical references annotated).
- Phase 4.1 has one plan: `4.1-01-PLAN.md`. Re-runs Gates 1-8 for all 4 affected roles + leviathan smoke test.
- Phase 5 plan 05-01 MUST NOT begin until 4.1 lands.

**Alternative placements considered (and rejected):**
- (a) Phase 5 plan 05-01 doc-rework cascade (task 1) — Mirrors Phase-4 D-58 pattern but muddies Phase 5 plan (Grafana port + vault rename in same plan).
- (c) Pre-step in plan 05-01, before any Grafana code — Same as (a), same downside.
- (d) Post-M1 cleanup — Defers a known-wrong convention; bakes more `vault_*` references in before fixing.

**Chosen rationale:** Phase 4.1 keeps the rename atomic with its own git history; Phase 5 starts clean; bounded scope (4 roles + ~12 Jinja refs + 8 keys + 6 docs) fits a single plan.

---

## Claude's Discretion (areas deferred to planner)

- **Grafana container args** — `grafana.ini` sections + env injection of `GF_SECURITY_ADMIN_*` overrides.
- **Karma config shape** — YAML at `/etc/karma/karma.yaml`; minimum config is alertmanager.servers; planner finalizes `karma_extra_filters` / `karma_silence_form_strip` / `karma_ui_theme` knob surface.
- **PromLens config shape** — CLI flags + env var `PROMLENS_DEFAULT_BACKEND_URL`. Role README opens with deprecation-candidate banner.
- **Healthcheck details per role** — Planner verifies image-shipped HEALTHCHECK during research; uses conditional-healthcheck pattern (Phase-2 Tempo / Phase-3 OTel) when distroless or missing.
- **Plan task order per role** — Planner finalizes during plan-phase. Suggested orders captured in CONTEXT.md.
- **Container labels per Gate 7** — `org.telemetron.service: telemetron` + `org.telemetron.job: <role>` on all three containers.

---

## Deferred Ideas (not folded into Phase 5)

### Out of Phase 5 (lands in phase 4.1)
- Project-wide `vault_*` → `<role>_*` rename (D-90 / pre-Phase-5 dependency)

### Out of Phase 5 (lands in Phase 6)
- M1 acceptance smoke test (synthetic log + metric + trace in Grafana within 60s) — OPS-07
- `docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md` — Phase 6
- Top-level README.md post-M1 update
- `nfsd` opt-in role

### Out of Phase 5 (post-M1 candidates)
- 999.4 fix (OTel-side Loki label relabel) — `service.name` → `service` retrofit
- SSO / LDAP / OAuth on Grafana
- Multi-org Grafana provisioning
- Grafana Enterprise features (explicitly NOT M1)
- TLS / reverse-proxy roles (operator-supplied per PROJECT.md)
- Dashboard marketplace ingestion
- Trace-to-logs body-regex extraction (D-78 ships structured-metadata only)
- `host.name` tag in tracesToLogsV2 (D-80 ships `service.name` only)
- PromLens replacement / removal
- Karma silence-import API
- Mimir per-tenant Grafana datasource (multitenancy off in M1 per D-26)
