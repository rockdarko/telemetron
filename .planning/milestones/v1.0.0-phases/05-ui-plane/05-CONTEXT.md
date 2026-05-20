# Phase 5: UI Plane - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning (after phase 4.1 lands per D-90)

<domain>
## Phase Boundary

Port the three Ansible roles that close the M1 stack with the **operator-facing UI plane** — `grafana`, `karma`, `promlens` — and provision Grafana's datasources + curated starter dashboards + trace-to-logs correlation so a fresh deploy renders real data without manual configuration.

**Grafana (`grafana/grafana-oss:13.0.1`)** runs on host `:3000` with embedded SQLite as the backing store on a `telemetron_grafana_data` named volume; provisions four datasources at **explicit, stable UIDs** (`prometheus`, `loki`, `tempo`, `mimir`); ships **7 curated dashboards** (host health, Loki Explore landing, Tempo Explore landing, OTel Collector self-metrics, Loki/Tempo/Mimir self-metrics) rendering real data on a fresh deploy; wires trace-to-logs correlation via `tracesToLogsV2` on the Tempo datasource + a structured-metadata `trace_id` derived field on the Loki datasource for OTLP-pushed app logs. **Karma (`ghcr.io/prymitive/karma:v0.130` — GHCR official, NOT the `lmierzwa/karma` Docker Hub fork)** runs on host `:8082`, reads alerts from the Phase-4 Alertmanager at `http://alertmanager:9093`, is THE operator alert UX in M1 (per Phase-4 specifics — null receiver makes Karma the visible alert surface). **PromLens (`prom/promlens:v0.3.0`)** runs on host `:8081`, points at `http://prometheus:9090`, and ships with a deprecation-candidate header in `roles/promlens/README.md` noting that Prometheus 3's built-in UI absorbs the tree-view feature.

Each role mirrors the canonical patterns established by Phases 1–4: D-10a HEALTHCHECK poll, W6 single-handler restart, W7 `changed_when: false` on verify tasks, W8 in-network verify step, OPS-03 README schema, D-25 opinionated improvement over upstream INSPQ, Gate 7 `org.telemetron.{service,job}` label-stamping, Gate 8 parent-directory bind-mount convention. Three role ports + the UI-plane host-publishing exemption from D-30 + the doc cascade and roles/README.md row tick per role.

**Hard precondition:** Phase 4.1 (`drop-vault-prefix`, per D-90) MUST land before Phase 5 plan 05-01 begins. Phase 5 names its first new secret variable `grafana_admin_password` — with no `vault_` prefix — so the rename of existing `vault_minio_root_user/password`, `vault_loki_s3_*`, `vault_tempo_s3_*`, `vault_mimir_s3_*` to their unprefixed forms must complete first, or Phase 5 inherits a half-converted convention.

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues from Phase 4 (last decision was D-69). Phase 5 introduces D-70 through D-89, plus the cross-phase D-90.

### Plan structure & order (D-70, D-71, D-72, D-73)

- **D-70:** **Three plans, one per role, mirroring D-22 / D-40.** `05-01-PLAN.md` ports `roles/grafana/` (the heavy one: container + 4-datasource provisioning + 7-dashboard provisioning + tracesToLogsV2 + derived `trace_id` field). `05-02-PLAN.md` ports `roles/karma/` (container + Karma config pointing at Alertmanager + UI access). `05-03-PLAN.md` ports `roles/promlens/` (container + Prometheus URL + deprecation-candidate README header). Each plan is end-to-end shippable in isolation (D-23 carry-forward); each wires its own role into `playbooks/deploy_docker.yml` as its final task; the playbook stays runnable at every commit. One tag per role per D-24 (`grafana`, `karma`, `promlens`).

- **D-71:** **Dependency-true order: grafana → karma → promlens.** Grafana first because **its datasource provisioning is the de-facto end-to-end smoke test for everything Phase 1–4 shipped** (per ROADMAP.md Phase-5 description) — if Grafana boots and its four datasources resolve real data, the whole pre-Phase-5 stack is validated. Karma second because the Phase-4 spec made Karma THE alert UX in M1 (null receiver = alerts visible-not-actioned; Karma's the visible surface). PromLens last because it's the deprecation candidate — lowest stakes, smallest risk. No plan depends on a later plan's output (Grafana doesn't need Karma to provision; Karma doesn't need PromLens). Playbook role list extension after each plan: `… → fluentbit → alertmanager → grafana → karma → promlens`.

- **D-72:** **Per-role light doc cascade in each plan.** Each plan updates `roles/README.md` (tick the role's box), `roles/<role>/README.md` (the new file per Gate 6), `ROADMAP.md` (mark its plan complete in the Phase-5 Plans list), and any PROJECT.md "Active" line that mentions remaining role count (e.g. "4 remaining" → "3 remaining" → "2 remaining" → "1 remaining" → "0 remaining; Phase 5 complete"). No mid-phase rewrite of PROJECT.md Key-Decisions or REQUIREMENTS.md sections — the decisions captured here in CONTEXT.md flow into PROJECT.md only at Phase 5 transition via `/gsd:transition`. STATE.md is updated by the GSD workflow itself. Distinct from D-58 (Phase-4 single atomic cascade for hook-router deferral) — Phase-5 has no scope-reshape; the cascade is just bookkeeping per plan.

- **D-73:** **Gate 9 — "datasources-resolve-real-data" verify gate, added to `roles/README.md`.** Phase 5 introduces a new port-acceptance gate specific to the Grafana role: the verify step in plan 05-01 MUST issue `curl http://grafana:3000/api/datasources/uid/<uid>/health` for each of the four UIDs (`prometheus`, `loki`, `tempo`, `mimir`) and assert HTTP 200 + `status: "OK"`; AND issue one canonical query against each datasource asserting real data:
  - `prometheus`: query `up` → expect non-empty `result[]`
  - `loki`: query `{job=~".+"}` for last 1h → expect at least one stream
  - `tempo`: query `/api/search?limit=1` → expect at least one trace OR explicit "no traces yet" stable state
  - `mimir`: query `/prometheus/api/v1/query?query=up` → expect non-empty `result[]`
  
  Mirrors the D-69 / D-54 in-network-verify pattern (one-shot `curlimages/curl` container on the `telemetron` bridge with auth via the admin bearer token derived from `grafana_admin_password`). Gate 9 lands in `roles/README.md` "Per-role port-acceptance gates" subsection as part of plan 05-01's doc cascade. Karma + PromLens plans pass standard Gates 1-8 only; Gate 9 applies to Grafana specifically because Grafana is the only role with cross-component datasource provisioning. Justification for promoting this to a roles/README.md gate: it's THE M1 acceptance heuristic for "everything wired correctly" and operators reading the gate list see it as the canonical Phase-5 success heuristic.

### Dashboard source & curation (D-74, D-75, D-76, D-77)

- **D-74:** **Hybrid source strategy: official upstream mixins + hand-rolled landing pages.** For backend self-metrics dashboards (Loki, Tempo, Mimir self-metrics), pull canonical JSON from the official upstream `grafana/loki`, `grafana/tempo`, `grafana/mimir` repos at the same `tag/version` as our pinned images. For node_exporter, use the official `grafana-dashboards/node-exporter-full` JSON (commit-pinned at fork time). For OTel Collector self-metrics, use the official `open-telemetry/opentelemetry-collector-contrib` dashboard. Hand-roll the two **Explore landing pages** (Loki Explore + Tempo Explore) — they're just curated nav (one row with `service_name` dropdown + a "View in Explore" link panel pointing at the right datasource). All seven JSONs committed at fork time to `roles/grafana/files/dashboards/*.json`; **no runtime download** (preserves the "works on an air-gapped homelab" story). When upstream mixin shapes change in future Telemetron versions, refresh the JSONs deliberately as a maintenance task.

- **D-75:** **Exactly 7 dashboards out of the box — the UI-03 explicit list, no padding.** (1) `host-health.json` (node_exporter), (2) `loki-explore-landing.json` (hand-rolled), (3) `tempo-explore-landing.json` (hand-rolled), (4) `otel-collector-self-metrics.json` (upstream contrib), (5) `loki-self-metrics.json` (upstream mixin), (6) `tempo-self-metrics.json` (upstream mixin), (7) `mimir-self-metrics.json` (upstream mixin). All seven within the UI-03 5-10 range. Operators can add their own via the D-76 drop-in dir.

- **D-76:** **File-based provisioning + operator drop-in dir.** Role ships JSONs in `/etc/grafana/provisioning/dashboards/telemetron/*.json` (read-only bind-mount from `/opt/telemetron/grafana/dashboards/telemetron/` — parent-dir mount per Gate 8). Grafana auto-loads on boot and hot-reloads on file change. `roles/grafana/templates/dashboards.yml.j2` (the provisioning manifest) declares two folders:
  ```yaml
  providers:
    - name: telemetron
      folder: Telemetron
      type: file
      options:
        path: /etc/grafana/provisioning/dashboards/telemetron
    - name: operator
      folder: Operator
      type: file
      options:
        path: /etc/grafana/provisioning/dashboards/operator
  ```
  Inventory knob `grafana_dashboard_extra_dir` (default `""`, conditional bind-mount via Jinja) bind-mounts an operator-supplied host path to `/etc/grafana/provisioning/dashboards/operator`. Two-folder UI separation: "Telemetron" (role-shipped, treat as read-only) and "Operator" (operator-owned). No API calls; survives Grafana restart trivially; survives `docker volume rm telemetron_grafana_data` (dashboards are file-provisioned, not stored in SQLite).

- **D-77:** **Hardcoded datasource UIDs in dashboard JSONs.** UI-02 locks UIDs to `prometheus`, `loki`, `tempo`, `mimir`. Bundled dashboard JSONs reference these strings directly in their `datasource.uid` fields. No Jinja-templating of the dashboard files — they're committed as final JSON under `roles/grafana/files/dashboards/`. Justification: UI-02 explicitly states "UIDs do not change between deploys"; templating would imply operator-overridable UIDs, which contradicts UI-02. Future-Telemetron v2 wanting per-environment UID renames becomes its own story; not a Phase-5 concern.

### Trace-to-logs correlation plumbing (D-78, D-79, D-80, D-81)

- **D-78:** **Realistic correlation scope: OTLP-pushed app logs only.** Trace context survives only when an operator's app uses an OTel SDK and pushes logs OTLP-native to the OTel Collector on `:4318`, which forwards via `otlphttp/loki` to Loki 3.7.2's native OTLP endpoint (`http://loki:3100/otlp`). Loki stores `trace_id` (and `span_id`, `trace_flags`) as **structured metadata** on those records (Loki 3.x OTLP-native ingestion default — not as a label, to avoid cardinality explosion). FB-tailed Docker stdout/stderr logs **do not** carry `trace_id` unless the app embeds it in the log body. Honest framing in `roles/grafana/README.md` "Trace-to-logs correlation" section: trace-to-logs works for OTLP-instrumented apps; uninstrumented apps fall back to ad-hoc service/host filtering in Explore. Body-regex extraction is NOT shipped in M1 (single source of truth: structured metadata).

- **D-79:** **`tracesToLogsV2` customQuery on Tempo datasource:** the canonical LogQL filter on structured metadata, locked to:
  ```
  {${__tags}} | trace_id="${__span.traceId}"
  ```
  Grafana substitutes `${__tags}` from the configured tag list (see D-80) and `${__span.traceId}` from the trace span being clicked. Loki resolves `trace_id="..."` against structured metadata as a precise match. Tempo datasource provisioning template (`roles/grafana/templates/datasources/tempo.yaml.j2`) renders the full `tracesToLogsV2` block:
  ```yaml
  tracesToLogsV2:
    datasourceUid: loki
    spanStartTimeShift: '-1h'
    spanEndTimeShift: '1h'
    tags:
      - { key: 'service.name', value: 'service_name' }
    filterByTraceID: false
    filterBySpanID: false
    customQuery: true
    query: '{${__tags}} | trace_id="${__span.traceId}"'
  ```
  Loki datasource derivedFields template (`roles/grafana/templates/datasources/loki.yaml.j2`) declares the reverse — a clickable `trace_id` link from log lines to Tempo:
  ```yaml
  derivedFields:
    - name: 'trace_id'
      matcherType: 'label'         # Loki structured-metadata extractor
      matcherRegex: 'trace_id'
      url: '${__value.raw}'
      datasourceUid: 'tempo'
      urlDisplayLabel: 'View Trace'
  ```
  `matcherType: label` works for Loki 3.x structured-metadata fields (the field surfaces as a "label" in Grafana's terminology even though it's stored as structured metadata, not a stream label).

- **D-80:** **Forwarded tags: `service.name` → `service_name` only.** OTel pushes resource attribute `service.name`; Loki's `otlphttp/loki` ingestion path surfaces it as the `service_name` label (per 999.4 backlog observation). The `tracesToLogsV2.tags` block forwards exactly this one attribute. When an operator clicks "Logs for this span" in Grafana, the Loki query becomes `{service_name="<the service>"} | trace_id="<the trace>"`. Minimal, predictable, matches the LGTM single-tag default. Tags list documented in `roles/grafana/README.md`. Future: if operators consistently want host-scoping too, add `host.name` → `host` as a second tag (separate Phase 5+x decision).

- **D-81:** **Accept the FB-vs-OTel Loki label drift (999.4 backlog); do not fix in Phase 5.** Live Loki labels today are `{host, job, service_name}` — the OTel-pushed `service.name` resource attribute surfaces as `service_name`, NOT the Phase-3 D-47 spec'd label `service`. Three resolution paths exist (999.4):
  - (a) Accept that OTel-pushed logs surface OTel attribute names; rewrite the Phase-3 SC5 spec to match reality
  - (b) Wire FB's enriched labels to overwrite OTel attributes on the Loki side
  - (c) Move canonical naming to a relabel rule on the OTel Collector's `loki` exporter side (cleanest — single place owns the label contract)
  
  Phase 5 picks **(a)** for now — ship Grafana provisioning with `service_name` as the canonical Loki service label, document the OTel-attribute-to-Loki-label mapping in `roles/grafana/README.md` "Label mapping" section, and leave 999.4 in the backlog for a future-Rock decision on whether to retrofit (c). Justification: Phase 5 is the UI plane, not the ingest plane; option (c) belongs in a Phase-3 or post-M1 phase that revisits the OTel config.

### Host port publishing for UI roles (D-82, D-83, D-84, D-85)

- **D-82:** **UI plane is exempt from D-30's default-off host publishing.** Each Phase-5 role's `defaults/main.yml` sets `<role>_publish_host: true` (overriding D-30's `telemetron_publish_default: false` for UI plane only). Specifically: `grafana_publish_host: true`, `karma_publish_host: true`, `promlens_publish_host: true`. Justification: UI-03 success criterion 1 ("Operator runs `ansible-playbook --tags grafana,karma,promlens`, opens `http://<host>:3000`, logs in") requires Grafana be reachable from a browser without inventory edits. Operators wanting reverse-proxy-only access flip these to `false` per-role and run a reverse proxy that talks to the `telemetron` bridge network. Documented in `roles/grafana/README.md`, `roles/karma/README.md`, `roles/promlens/README.md` "Network → Host publishing" section.

- **D-83:** **Bind address for published UI ports: `0.0.0.0`.** Homelab operators reach their stack from any LAN IP. `0.0.0.0` is the predictable homelab default. Per-role inventory knob `<role>_bind_address: 0.0.0.0` exposed for security-conscious operators who want `127.0.0.1` (loopback + `ssh -L` tunneling) or a specific interface. Documented in each role's README "Network → Bind address" subsection with the explicit security trade-off (Grafana is auth-gated by `grafana_admin_password`; Karma is read-only by default; PromLens is read-only). Per Phase-1+2+3+4 D-30 precedent, this knob is a port-publishing concern, not a Grafana-config concern (Grafana itself can also bind via its own `http_addr` setting but the host-port-publish boundary is the load-bearing one).

- **D-84:** **Confirm D-31 port matrix unchanged: Grafana host `:3000`, Karma host `:8082`, PromLens host `:8081`.** All three are inventory-overrideable via `<role>_host_port` (defaults `3000`/`8082`/`8081`). Documented in `inventory/example-homelab/group_vars/all/network.yml` port-allocation comment block (extending the existing one).

- **D-85:** **Reverse-proxy / TLS termination recipe lives in `roles/grafana/README.md`.** The Grafana role README gains a "Reverse proxy" section documenting the Caddy/Traefik/nginx pattern: flip `grafana_publish_host: false`, run the reverse proxy on the host network (or on `telemetron` bridge as a non-role-owned container), proxy `https://grafana.example.com` → `http://grafana:3000` via the `telemetron` bridge. Cross-reference from Phase-6 `docs/quickstart.md` "Production hardening" subsection (Phase 6 doc — Phase 5 just leaves a `<!-- TODO Phase 6 -->` marker, not the recipe itself; recipe stays canonical in role README). Karma + PromLens READMEs cross-reference the Grafana README pattern (the recipe is identical; the only thing that changes is the upstream port).

### Grafana admin & access model (D-86, D-87, D-88, D-89)

- **D-86:** **Vault key naming: `grafana_admin_password` — no `vault_` prefix** (per project-wide convention change D-90). The role references `{{ grafana_admin_password }}` directly in its Jinja templates (env injection on the Grafana container, since Grafana reads `GF_SECURITY_ADMIN_PASSWORD` from env). `roles/grafana/README.md` "Secrets" subsection documents the contract: `grafana_admin_password` must be defined by the operator's inventory; encryption mechanism is the operator's choice (ansible-vault, sops, env-var injection, external lookup plugin, chmod-600 plaintext file in a homelab — operator's call, NOT a Telemetron concern). `inventory/example-homelab/group_vars/all/secrets.yml.example` (renamed from `vault.yml.example` per D-90) gets `grafana_admin_password: CHANGE_ME` added.

- **D-87:** **Anonymous viewer access: default off; `grafana_anonymous_enabled` knob exposed.** Grafana defaults to login-required (`auth.anonymous.enabled: false`). Role exposes `grafana_anonymous_enabled: false` as the default; operator flips to `true` if they want a TV-mode wall display. When enabled, Grafana provisions `auth.anonymous.org_role: Viewer` + `auth.anonymous.org_name: "Main Org."` (matches D-89's stock org choice). Documented in `roles/grafana/README.md` "Access model" section with the security trade-off (anonymous viewer = anyone on the LAN bind address can read dashboards without authentication). Conservative default: doesn't surprise operators who expect login-required.

- **D-88:** **Admin user details: username `admin`, email `admin@telemetron.local`.** Standard Grafana convention. Email is a synthetic local-only address — NOT the operator's real email, since the operator hasn't supplied one and `admin@telemetron.local` is unambiguously a placeholder. Operators override via `grafana_admin_user` / `grafana_admin_email` inventory knobs if they have an SSO/LDAP path lined up post-M1. Documented in `roles/grafana/README.md` "Variables → Admin user" subsection. First-login flow: Grafana detects an existing `admin` user, doesn't trigger the password-reset prompt (since the password is provisioned via env).

- **D-89:** **Stock `Main Org.` — no org provisioning.** Grafana's default org name is `Main Org.` (note the trailing period — it's literal). Phase 5 does not provision orgs; operators rename via UI if they care. Justification: smallest moving-parts surface; no risk of UID drift or rename foot-guns; matches Grafana OSS norms. Multi-org provisioning is a v2 story if/when SSO or per-team isolation lands.

### Project-level convention change (D-90)

- **D-90:** **Drop the `vault_` prefix from all sensitive variables, project-wide.** Inserts a new decimal phase **4.1 (`drop-vault-prefix`)** between Phase 4 and Phase 5. Rationale (per [[feedback-no-decorative-convention-prefixes]]): the prefix (a) adds no value beyond what role-namespace + descriptive suffix already conveys, (b) steers operators toward Ansible vault specifically when vaulting is one option among many (sops, env vars, external secret managers, plaintext-chmod-600 in a homelab), and (c) implies tooling enforcement that Ansible doesn't actually provide — `vault_foo` works the same as `foo`. Sensitive variables are documented in each role's README "Secrets" subsection — that's where the contract lives, not in the variable name.

  **Phase 4.1 scope (executed by `/gsd:insert-phase 4.1` before Phase 5):**
  - Rename across 4 roles' Jinja references: `roles/{minio,loki,tempo,mimir}/` templates + `community.docker.docker_container` env injections. Specifically:
    - `vault_minio_root_user` → `minio_root_user`
    - `vault_minio_root_password` → `minio_root_password`
    - `vault_loki_s3_access_key` → `loki_s3_access_key`
    - `vault_loki_s3_secret_key` → `loki_s3_secret_key`
    - `vault_tempo_s3_access_key` → `tempo_s3_access_key`
    - `vault_tempo_s3_secret_key` → `tempo_s3_secret_key`
    - `vault_mimir_s3_access_key` → `mimir_s3_access_key`
    - `vault_mimir_s3_secret_key` → `mimir_s3_secret_key`
  - Rename `inventory/example-homelab/group_vars/all/vault.yml.example` → `inventory/example-homelab/group_vars/all/secrets.yml.example`; rename all 8 keys inside it; update the in-file usage comment block. The corresponding `vault.yml` (gitignored, operator-local) becomes `secrets.yml` — leviathan-side migration: `mv vault.yml secrets.yml && sed -i 's/vault_//g' secrets.yml && ansible-vault encrypt secrets.yml` (since the operator's existing file is already vault-encrypted, also: `ansible-vault decrypt`, edit, re-encrypt).
  - Doc cascade: `PROJECT.md` OPS-02 line + Key Decisions entries mentioning `vault_<role>_<purpose>`; `REQUIREMENTS.md` OPS-02 acceptance text; `roles/README.md` Gate 3 wording (Vault-discipline gate → "Secrets-discipline gate"); historical references in `.planning/phases/01-foundation-storage/01-CONTEXT.md` and `.planning/phases/02-telemetry-backends/02-CONTEXT.md` (D-09 + D-27 mentions — annotate inline with a `(superseded by D-90)` note rather than rewriting, since historical CONTEXT.md is institutional memory).
  - Verify: re-run six per-role gates (1: grep clean, 2: image pin, 3: secrets-discipline using new naming, 4: idempotency, 5: healthcheck+restart, 6: README schema) for all 4 affected roles; live-host smoke on leviathan (push a metric, push a log — confirm nothing broke).
  - Gate 7 (Telemetron label-stamp) and Gate 8 (parent-dir bind mounts) are unaffected.
  - **Phase 4.1 has one plan: `4.1-01-PLAN.md`. Phase 5 plan 05-01 MUST NOT begin until 4.1 lands.**

  Cross-references in CONTEXT.md: D-86 (Phase 5's first new secret variable uses the new convention from day 1 — `grafana_admin_password`, not `vault_grafana_admin_password`). Going forward, every new role's "Secrets" README subsection lists the unprefixed variables the role expects from the operator's inventory.

### Claude's Discretion (planner picks within these bounds)

- **Grafana container args** — Grafana 13.0.1 reads `grafana.ini` from `/etc/grafana/grafana.ini`. The role templates `grafana.ini.j2` with sections for `[server]`, `[database]`, `[security]`, `[auth.anonymous]`, `[users]`, `[paths]`. Env injection of `GF_SECURITY_ADMIN_PASSWORD` + `GF_SECURITY_ADMIN_USER` + `GF_SECURITY_ADMIN_EMAIL` overrides INI defaults at startup (Grafana env > ini).
- **Karma config shape** — Karma supports YAML config or env vars; the role uses YAML at `/etc/karma/karma.yaml` bind-mounted from `/opt/telemetron/karma/karma.yaml` (parent-dir bind per Gate 8). Minimum config: `alertmanager.servers: [{ name: telemetron, uri: http://alertmanager:9093 }]`. Planner finalizes whether to expose `karma_extra_filters` / `karma_silence_form_strip` / `karma_ui_theme` etc. as inventory knobs.
- **PromLens config shape** — PromLens 0.3.0 reads CLI flags; container env vars `PROMLENS_DEFAULT_BACKEND_URL=http://prometheus:9090` is the minimum. Role README marks deprecation-candidate in a banner at the top with a Prometheus-3-UI absorption note (mirror Phase-2 Tempo conditional-healthcheck deprecation-note discipline).
- **Healthcheck details for each role** — Grafana ships HEALTHCHECK in image (`wget --spider http://localhost:3000/api/health`); Karma ships `wget --spider http://localhost:8080/health` (or similar — planner verifies during research); PromLens 0.3.0 image may lack HEALTHCHECK (planner uses the conditional-healthcheck pattern from Phase-2 Tempo / Phase-3 OTel if so).
- **Plan task order per role** — Planner finalizes. Suggested for plan 05-01 (grafana): (1) `roles/grafana/` scaffolding (defaults, tasks, handlers, README); (2) datasource provisioning templates (`prometheus.yaml.j2`, `loki.yaml.j2`, `tempo.yaml.j2`, `mimir.yaml.j2`) under `templates/datasources/`; (3) dashboard provisioning manifest (`dashboards.yml.j2`) + the 7 dashboard JSONs under `files/dashboards/`; (4) `inventory/example-homelab/group_vars/all/grafana.yml`; (5) `secrets.yml.example` add `grafana_admin_password` key; (6) `playbooks/deploy_docker.yml` append `grafana` role entry after `alertmanager`; (7) port-acceptance gate checks (1-9); (8) D-73 / Gate 9 verify run.
- **Container labels per Gate 7** — `org.telemetron.service: telemetron` + `org.telemetron.job: grafana` (and karma, promlens). Stamps on all three roles' `community.docker.docker_container` tasks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project framing & scope

- `.planning/PROJECT.md` — Vision, M1 constraints, "Active" requirements (the "4 remaining" → "3/2/1/0 remaining" trail in D-72), Key Decisions table. **Note:** D-90 changes the OPS-02 "vault" wording project-wide; Phase 4.1 plan owns that doc rewrite.
- `.planning/REQUIREMENTS.md` §"UI plane (UI)" — UI-01 through UI-06 acceptance text. Traceability table maps all six REQ-IDs to Phase 5.
- `.planning/ROADMAP.md` §"Phase 5: UI Plane" — Goal paragraph + 5 success criteria. SC-1 (datasource UIDs resolvable), SC-2 (every panel renders real data), SC-3 (trace span → Loki Explore with `trace_id` filter), SC-4 (Karma at `:8082`, PromLens at `:8081`), SC-5 (PromLens deprecation README + Karma GHCR image).
- `CLAUDE.md` §"Technology Stack" — Grafana row (`grafana/grafana-oss:13.0.1`), Karma row (`ghcr.io/prymitive/karma:v0.130`), PromLens row (`prom/promlens:v0.3.0` deprecation-candidate). §"Port-allocation snapshot" — Grafana 3000, Karma 8082, PromLens 8081, Mimir 9009, Tempo 3200, Loki 3100, Prometheus 9090, Alertmanager 9093.

### Phase 1+2+3+4 decisions that propagate forward (read in full before Phase 5 planning)

- `.planning/phases/01-foundation-storage/01-CONTEXT.md` — D-04 (network in pre_tasks), D-06 (no shared base role), D-10a (HEALTHCHECK poll), D-12..D-14 (no host publish — UI plane breaks per D-82), D-15..D-18 (inventory + volumes + config layout), D-19..D-21 (handler restart, sorted-keys Jinja, grep gates). **D-09 / OPS-02 wording superseded by D-90.**
- `.planning/phases/02-telemetry-backends/02-CONTEXT.md` — D-22 (one plan per role — Phase 5 inherits as D-70), D-23 (each plan wires its own role — Phase 5 inherits), D-24 (one tag per role — Phase 5 tags: grafana/karma/promlens), D-25 (opinionated improvement over upstream), D-26 (multitenancy off — Mimir datasource needs no `X-Scope-OrgID`), D-30 (no host publish default — Phase 5 breaks per D-82), D-31 (port matrix — D-84 confirms unchanged), D-32 (in-network verify one-shot — pattern reused for Gate 9 / D-73). **D-27 (vault key alias surface) superseded by D-90 — the six aliases keep their semantic but lose the `vault_` prefix.**
- `.planning/phases/03-ingest-plane/03-CONTEXT.md` — D-40 (one deployable unit per plan — Phase 5 inherits as D-70), D-42 (OTel→Prometheus→Mimir single ingest path — Grafana Mimir datasource queries against `:9009/prometheus`), D-43 (forward-compat dual-exporter — declared-but-not-flipped), D-44 (Loki + Tempo legs via OTel — D-79 trace-to-logs piggybacks on this path), D-47 (FB Loki label allowlist `{job, host, service, env, level}` — **D-81 documents the drift from this spec to live `{host, job, service_name}`**), D-54 (in-network verify topology — directly reused for Gate 9). **D-55 (no vault keys this phase) superseded by D-90 naming.**
- `.planning/phases/04-alert-plane/04-CONTEXT.md` — D-56/D-57/D-58 (Phase-4 scope reshape — Karma becomes THE alert UX in M1 per Phase-4 specifics, locked-in here for D-71 ordering rationale), D-60 (null receiver default — alerts visible-not-actioned, Karma is the visible surface), D-67 (all gates apply — Phase 5 extends with Gate 9 per D-73), D-69 (in-network verify pattern — reused for Gate 9). **D-66 (no vault keys this phase) superseded by D-90 naming.**
- `roles/minio/`, `roles/loki/`, `roles/tempo/`, `roles/mimir/`, `roles/node_exporter/`, `roles/opentelemetry/`, `roles/prometheus/`, `roles/fluentbit/`, `roles/alertmanager/` (entire roles) — nine canonical role-port templates. Every layout choice (directory shape, defaults, handlers, README schema, verify-task pattern, D-10a HEALTHCHECK poll, D-54/D-69 in-network verify, Gate 7 label stamp, Gate 8 parent-dir bind mount) propagates verbatim to `roles/grafana/`, `roles/karma/`, `roles/promlens/`. Researcher AND planner should read all nine before producing each Phase-5 plan.
- `roles/README.md` — Per-role port-acceptance gates 1-8. **Phase 5 plan 05-01 adds Gate 9 (datasources-resolve-real-data) per D-73.**
- `roles/prometheus/templates/rules-baseline.yml.j2` — Severity labels on the 4 baseline rules (Phase 4 D-65). Karma will display these severities in its grid view.

### 999.x backlog interplay

- `.planning/ROADMAP.md` §"Phase 999.4: Reconcile FB 5-label spec with OTel-first ingest reality" — **Directly applicable to D-81.** Phase 5 picks option (a) — accept live `{host, job, service_name}` labels and document. 999.4 stays open as a candidate for a post-M1 OTel relabel-rule fix.
- Other 999.x phases (999.1 Mimir retention, 999.2 Tempo block-ranges cleanup, 999.3 FB timestamp fallback) — not directly applicable to Phase 5 but live in the same backlog parking lot.

### Research backing for this phase

- `.planning/research/STACK.md` — Image pins (Grafana 13.0.1, Karma v0.130, PromLens v0.3.0); component port matrix.
- `.planning/research/PITFALLS.md` §"Pitfall 4: Loki label discipline" — Backing for D-81 999.4 drift framing; OTel-attribute-to-Loki-label translation rules.
- `.planning/research/PITFALLS.md` §"Pitfall 8: Ansible role idempotency cascades" — Backing for handler-restart-not-state-restarted in all three Phase-5 roles.
- `.planning/research/PITFALLS.md` §"Pitfall 9: Fork-from-INSPQ leftovers" — Backing for D-25 deviation audit per role (Grafana / Karma / PromLens upstream INSPQ checkouts likely carry FR-language vocabulary, `inspq.qc.ca` SMTP defaults, `America/Montreal` timezone, INSPQ dashboard JSON content).
- `.planning/research/FEATURES.md` — Grafana datasource provisioning shape (UID-pinning rationale); Karma vs alternatives (Karma chosen because it's Alertmanager-native, NOT a general alert UI); PromLens vs Prometheus 3 UI (PromLens deprecation rationale).
- `.planning/research/SUMMARY.md` — UI-02 (datasource UID pinning) called out as a top portability pitfall in the research.

### Upstream INSPQ source-of-truth (for porting + D-25 improvement audit)

- `~/git/inspq/ansible/grafana/` (operator workstation) — Source role for plan 05-01. D-25 audit MUST surface: FR-language dashboard titles/panel labels, `inspq.qc.ca` SMTP defaults, `America/Montreal` TZ, INSPQ-internal Postgres backing store (replaced by D-04 embedded SQLite per UI-01), any Quebec-gov SSO/LDAP path, hardcoded organizational dashboards.
- `~/git/inspq/ansible/karma/` — Source role for plan 05-02. D-25 audit MUST surface: FR-language Karma filters/labels, INSPQ team grouping config, hardcoded INSPQ Alertmanager URL.
- `~/git/inspq/ansible/promlens/` — Source role for plan 05-03. D-25 audit MUST surface: FR-language defaults if any, deprecation-candidate framing absent from upstream.

### Upstream dashboard JSON sources (per D-74)

- [grafana/loki/production/loki-mixin/dashboards/](https://github.com/grafana/loki/tree/main/production/loki-mixin/dashboards) — Loki self-metrics dashboards at version-pinned commit (match Loki 3.7.2 tag).
- [grafana/mimir/operations/mimir-mixin/dashboards/](https://github.com/grafana/mimir/tree/main/operations/mimir-mixin/dashboards) — Mimir self-metrics dashboards (match Mimir 3.0.6 tag).
- [grafana/tempo/operations/tempo-mixin/dashboards/](https://github.com/grafana/tempo/tree/main/operations/tempo-mixin/dashboards) — Tempo self-metrics dashboards (match Tempo 2.10.5 tag).
- [open-telemetry/opentelemetry-collector-contrib dashboards](https://github.com/open-telemetry/opentelemetry-collector-contrib) — OTel Collector self-metrics dashboard. Researcher locates exact path (typically `examples/grafana-dashboards/` or similar).
- [prometheus/node_exporter — community dashboards](https://github.com/prometheus/node_exporter) → [Grafana.com node-exporter-full ID 1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) — node_exporter host-health dashboard. Commit-pinned JSON committed at fork time per D-74 (no runtime download).

### Grafana / Karma / PromLens upstream documentation

- [Grafana 13 datasource provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources) — YAML shape, UID pinning, derivedFields, tracesToLogsV2.
- [Grafana 13 dashboard provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards) — File-based provider config, folder organization, updateIntervalSeconds.
- [Grafana 13 `auth.anonymous` config](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/anonymous-auth/) — D-87 reference.
- [Grafana 13 environment variables](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#override-configuration-with-environment-variables) — `GF_SECURITY_ADMIN_PASSWORD`, `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_EMAIL` env precedence over `grafana.ini`.
- [Tempo `tracesToLogsV2` Grafana docs](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/#trace-to-logs) — customQuery shape, tag forwarding.
- [Loki `derivedFields` Grafana docs](https://grafana.com/docs/grafana/latest/datasources/loki/configure-loki-data-source/#derived-fields) — matcherType `label` vs `regex`, structured metadata extraction.
- [Loki 3.x OTLP-native ingestion](https://grafana.com/docs/loki/latest/send-data/otel/) — Structured-metadata vs label disposition for OTel resource attributes; trace_id propagation.
- [Karma 0.130 configuration](https://github.com/prymitive/karma/blob/main/docs/CONFIGURATION.md) — YAML config schema, alertmanager.servers, UI filters/themes.
- [PromLens 0.3.0 README](https://github.com/prometheus/promlens) — CLI flags, default-backend-URL, deprecation status.

### Ansible module & collection documentation

- [community.docker.docker_container module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_module.html) — Primary module for all three Phase-5 roles.
- [community.docker.docker_container_info module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_info_module.html) — D-10a HEALTHCHECK poll pattern.
- [community.docker.docker_volume module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_volume_module.html) — `telemetron_grafana_data` volume.

### Locked naming normalizations (carried forward + D-90 update)

- git commit `ba836d2` — naming locked.
- Phase 1 conventions (per D-90 update): sensitive variables `<role>_<purpose>` (no `vault_` prefix); volumes `telemetron_<role>_data` (`telemetron_grafana_data`; Karma + PromLens stateless — no volumes); config dirs `/opt/telemetron/<role>/` (`/opt/telemetron/grafana/`, `/opt/telemetron/karma/`, `/opt/telemetron/promlens/`); tags one-per-role (`grafana`, `karma`, `promlens`); container names `telemetron-<role>` (`telemetron-grafana`, `telemetron-karma`, `telemetron-promlens`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`roles/minio/`, `roles/loki/`, `roles/tempo/`, `roles/mimir/`, `roles/node_exporter/`, `roles/opentelemetry/`, `roles/prometheus/`, `roles/fluentbit/`, `roles/alertmanager/`** — Nine canonical role templates from Phases 1–4. Every layout choice (directory shape, defaults file, handler convention, README schema, verify-via-one-shot-container pattern, D-10a HEALTHCHECK poll, D-54 in-network verify, Gate 7 label stamp, Gate 8 parent-dir bind mount) propagates verbatim to `roles/grafana/`, `roles/karma/`, `roles/promlens/`. Researcher AND planner should skim all nine before producing each Phase-5 plan.
- **`roles/minio/tasks/bootstrap.yml`** — D-10a `docker_container_info` HEALTHCHECK poll pattern. `roles/grafana/` mirrors this for "wait for Grafana to be ready before running Gate 9 verify."
- **`roles/alertmanager/`** — Closest analog in shape to Phase-5 roles: stateless-but-with-persistent-state, monolithic container, in-network verify, single bind-mount config dir per Gate 8. Karma in particular mirrors this pattern (no datastore beyond in-memory cache; reads Alertmanager via HTTP).
- **`roles/prometheus/`** — Relevant for Grafana's Prometheus datasource: it exposes `:9090/api/v1/query` on the `telemetron` bridge, no auth, no TLS. Grafana datasource provisioning point at `http://prometheus:9090` directly.
- **`roles/loki/`** — Relevant for D-79 derivedFields: Loki exposes `:3100/loki/api/v1/query_range` on the `telemetron` bridge, no auth. Grafana points at `http://loki:3100`.
- **`roles/tempo/`** — Relevant for D-79 tracesToLogsV2: Tempo exposes `:3200/api/search` + `:3200/api/traces/<id>` on the `telemetron` bridge, no auth. Grafana points at `http://tempo:3200`.
- **`roles/mimir/`** — Relevant for Grafana's Mimir datasource: Mimir exposes `:9009/prometheus/api/v1/query` (Prometheus-compatible) on the `telemetron` bridge, no auth (D-26 multitenancy off). Grafana datasource type is `prometheus` pointed at `http://mimir:9009/prometheus`.
- **`roles/alertmanager/`** — Relevant for plan 05-02 Karma: Alertmanager exposes `:9093/api/v2/alerts` on the `telemetron` bridge. Karma config points at `http://alertmanager:9093`.
- **`inventory/example-homelab/group_vars/all/network.yml`** — `telemetron_network`, `telemetron_publish_default: false` (D-82 inverts for UI plane), `telemetron_tz: Etc/UTC`. Plan 05-01 extends the port-allocation comment block.
- **`inventory/example-homelab/group_vars/all/storage.yml`** — `telemetron_volume_prefix`, `telemetron_config_root`. Plan 05-01 adds `grafana.yml`; plans 05-02 and 05-03 add `karma.yml` and `promlens.yml`.
- **`inventory/example-homelab/group_vars/all/secrets.yml.example`** — After phase 4.1 renaming per D-90, this is where `grafana_admin_password: CHANGE_ME` is added in plan 05-01.
- **`playbooks/deploy_docker.yml`** — Roles list ends at `alertmanager` after Phase 4. Each Phase-5 plan appends one role entry per D-71 order: `… → alertmanager → grafana → karma → promlens`.
- **`roles/README.md`** — Plan 05-01 adds Gate 9 per D-73 to the "Per-role port-acceptance gates" subsection. Each plan ticks its role's box in the "Planned roles (port status)" table.

### Established patterns (mirrored from Phases 1–4; planner enforces in Phase 5)

- **Role layout** — `defaults/main.yml`, `tasks/main.yml`, `tasks/verify.yml`, `handlers/main.yml`, `templates/<role>.yml.j2`, `templates/datasources/*.yaml.j2` (grafana only), `files/dashboards/*.json` (grafana only), `meta/main.yml`, `README.md`.
- **Image pin discipline (OPS-01)** — `grafana/grafana-oss:13.0.1`, `ghcr.io/prymitive/karma:v0.130`, `prom/promlens:v0.3.0`.
- **Volume naming (D-16, D-90-updated)** — `telemetron_grafana_data` (embedded SQLite + plugins cache). Karma + PromLens are stateless — no volumes.
- **Config bind-mount (D-18, Gate 8)** — Parent-directory mounts: host `/opt/telemetron/grafana/` → container `/etc/grafana/provisioning/:ro` (datasources + dashboards subdirs); host `/opt/telemetron/karma/` → container `/etc/karma/:ro`; host `/opt/telemetron/promlens/` → container `/etc/promlens/:ro` (if promlens has config — most likely env-only).
- **Restart-by-handler (D-19, W6)** — One handler per role triggered by config template change. Datasource/dashboard hot-reload may bypass restart (Grafana auto-reloads file-provisioned datasources + dashboards).
- **Sorted-keys Jinja iteration (D-20)** — `{% for k in d.keys() | sort %}` on any `<role>_extra_*` lists (e.g. `grafana_extra_datasources`, `karma_extra_filters` if surfaced).
- **In-network verify one-shot (D-54 → D-69 → D-73 Gate 9)** — Each plan's final task runs `curlimages/curl` one-shot containers on the `telemetron` network.
- **Grep gates per role (D-21, Gate 1)** — INSPQ-noise + non-ASCII gates per role port.
- **Per-role host publishing (D-82 overrides D-30)** — `grafana_publish_host: true`, `karma_publish_host: true`, `promlens_publish_host: true` as Phase-5 role defaults.
- **Telemetron label stamp (Gate 7)** — `org.telemetron.service: telemetron`, `org.telemetron.job: <role>` on all three containers.
- **Parent-directory bind mounts (Gate 8)** — All config bind-mounts use parent-dir form; no single-file mounts.

### Integration points

- **`playbooks/deploy_docker.yml`** — Plan 05-01 appends `- role: grafana` (tag: grafana) after `alertmanager`. Plan 05-02 appends `- role: karma` (tag: karma). Plan 05-03 appends `- role: promlens` (tag: promlens). Final shape after Phase 5: `pre_tasks: [network] → minio → loki → tempo → mimir → node_exporter → opentelemetry → prometheus → fluentbit → alertmanager → grafana → karma → promlens`. Phase 6 (nfsd opt-in) appends conditionally.
- **`inventory/example-homelab/group_vars/all/`** — Plan 05-01 adds `grafana.yml` (`grafana_publish_host`, `grafana_host_port`, `grafana_bind_address`, `grafana_anonymous_enabled`, `grafana_admin_user`, `grafana_admin_email`, `grafana_dashboard_extra_dir`, `grafana_extra_datasources`). Plan 05-02 adds `karma.yml`. Plan 05-03 adds `promlens.yml`. Secrets file (`secrets.yml.example` per D-90) gains `grafana_admin_password` in plan 05-01.
- **`roles/README.md`** — Each plan ticks the role's box; plan 05-01 also adds Gate 9 per D-73.
- **`/opt/telemetron/grafana/`** — New host-side config tree with `provisioning/datasources/`, `provisioning/dashboards/telemetron/` (and `provisioning/dashboards/operator/` symlink if `grafana_dashboard_extra_dir` is set), `grafana.ini`.
- **`/opt/telemetron/karma/`** — New host-side config tree with `karma.yaml`.
- **`/opt/telemetron/promlens/`** — New host-side config tree (likely sparse or empty — PromLens reads CLI flags + env).
- **`telemetron` bridge network** — All three Phase-5 containers attach. Grafana reaches Prometheus / Loki / Tempo / Mimir / Alertmanager by Docker DNS. Karma reaches Alertmanager. PromLens reaches Prometheus.
- **Host network exposure** — Grafana :3000, Karma :8082, PromLens :8081 published per D-82 + D-83 + D-84.

</code_context>

<specifics>
## Specific Ideas

- **Grafana's datasource provisioning is the de-facto end-to-end smoke test for everything Phase 1–4 shipped.** ROADMAP.md explicitly calls this out. If Grafana boots and its four datasources resolve real data via Gate 9 (D-73), the entire pre-Phase-5 stack is validated. Plan 05-01 should treat this as the headline success criterion.
- **Karma's role is elevated by the Phase-4 reshape.** With Alertmanager's `null` default receiver (D-60), alerts are visible-not-actioned. Karma becomes THE operator alert UX in M1 — silence management, deduplication views, grid groupings. `roles/karma/README.md` should call this out explicitly: "In M1, Karma is your primary alert interface. Until you wire a real Alertmanager receiver (custom), Karma's silence/ack UX is how you interact with the alert plane."
- **PromLens is shipped only for upstream parity.** `roles/promlens/README.md` MUST open with a deprecation banner: "PromLens (v0.3.0, last tagged 2022-12) is shipped for upstream-INSPQ parity. Prometheus 3.x's built-in UI absorbs PromLens's tree-view feature (CLAUDE.md "PromLens reality check"). New deployments should use Prometheus's native UI at `http://prometheus:9090/graph`. PromLens will likely be dropped in a future Telemetron milestone."
- **The 7-dashboard list is the M1 acceptance heuristic.** Operators evaluating Telemetron will land on Grafana and click around the bundled dashboards. If any of the 7 is broken or missing, the impression is "Telemetron doesn't quite work out of the box." Plan 05-01 must verify all 7 render real data — not just one or two.
- **The `service_name` Loki label is canonical for M1.** Phase-3 spec'd `{job, host, service, env, level}` but live reality is `{host, job, service_name}` (per 999.4 backlog). Phase 5 accepts this and documents it in `roles/grafana/README.md` "Label mapping" section. Future-Telemetron deciding to reconcile (likely option (c) from 999.4: relabel on OTel exporter side) is a post-M1 concern. The Grafana role does NOT try to retroactively fix the label drift from the UI side.
- **The `vault_` prefix drop (D-90) is a project-level convention change that surfaced in Phase-5 discuss but applies retroactively to Phases 1–4.** Phase 4.1 atomizes the rename across all affected roles and docs. Phase 5 starts clean with `grafana_admin_password` and no `vault_` prefix anywhere. The lesson — [[feedback-no-decorative-convention-prefixes]] — is now durable in user memory and will be applied to all future convention decisions: no decoration prefixes, no implied tooling, no operator-steering.
- **Anonymous viewer (D-87) is the homelab nice-to-have that's still off-by-default.** Some operators run a "wall display TV" mode where Grafana shows a dashboard 24/7 without login. Phase 5 supports this via `grafana_anonymous_enabled: true` but defaults off. Documented in role README so operators can flip it confidently.
- **Reverse-proxy / TLS termination is not Telemetron's job (D-85).** PROJECT.md "Out of Scope" explicitly says reverse-proxy is operator-supplied. Phase 5 documents the pattern (flip `<role>_publish_host: false`, run Caddy/Traefik against the `telemetron` bridge) in `roles/grafana/README.md` but doesn't ship a reverse-proxy role.

</specifics>

<deferred>
## Deferred Ideas

### Out of Phase 5 (lands in phase 4.1 — `drop-vault-prefix`, a precondition)

- **Project-wide rename of `vault_*` to `<role>_*`** — D-90. Touches 4 roles (minio, loki, tempo, mimir) + 8 vault keys in `secrets.yml.example` (renamed from `vault.yml.example`) + doc cascade (PROJECT.md OPS-02, REQUIREMENTS.md OPS-02, roles/README.md Gate 3, Phase 1+2 CONTEXT.md historical annotations). Phase 5 plan 05-01 MUST NOT begin until 4.1 lands.

### Out of Phase 5 (lands in Phase 6 — `opt-in-orchestration-docs-smoke-test`)

- **M1 acceptance smoke test (synthetic log + metric + trace in Grafana within 60s)** — OPS-07. The 7 dashboards rendering real data (D-75) is half the test; the synthetic-payload-roundtrip is the other half. Lands in Phase 6.
- **`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`** — Phase 6.
- **Top-level `README.md` post-M1 update** — Phase 6.
- **`nfsd` opt-in role** — Phase 6.

### Out of Phase 5 (candidates for a post-M1 milestone)

- **999.4 fix (option (c) — OTel-side Loki label relabel)** — D-81 accepts the live `{host, job, service_name}` reality. Future milestone retrofits `service.name` → `service` via OTel exporter relabel for canonical naming. Phase 5 ships with `service_name`.
- **SSO / LDAP / OAuth on Grafana** — D-88 admin/admin@telemetron.local is M1; SSO is post-M1. Operator-supplied for now (override `grafana.ini` via `grafana_extra_ini_sections` knob, if the role surfaces it).
- **Multi-org Grafana provisioning** — D-89 ships stock `Main Org.`. Multi-org is a v2 story when per-team isolation matters.
- **Grafana Enterprise features** — Explicitly NOT M1; UI-01 pins `grafana-oss` variant. Enterprise is out of scope per PROJECT.md.
- **TLS / reverse proxy / external URL** — D-85 documents the pattern but ships no role. Operator hardening pass.
- **Dashboard marketplace ingestion / community-import UI** — Out of scope per PROJECT.md REQUIREMENTS.md.
- **ML-driven anomaly detection panel plugins** — Out of scope per PROJECT.md.
- **Trace-to-logs body-regex extraction** — D-78 ships structured-metadata-only extraction. If a future operator's log line contains `trace_id=<hex>` as plain text (uninstrumented app), they can add a second `derivedFields` entry manually via `grafana_extra_derived_fields` knob (planner decides whether to surface this knob in Phase 5).
- **Tracing `host.name` tag in tracesToLogsV2** — D-80 ships `service.name` only. Future: add `host.name` if operators consistently want host-scoped trace-to-logs.
- **PromLens replacement / removal** — D-86's deprecation banner is the first step. Future milestone may drop the role entirely once Telemetron operators stop installing PromLens (telemetered via the role's "deprecation candidate" flag).
- **Karma silence-import API** — Phase 5 ships Karma stock. If operators want to bulk-manage silences via API (e.g. import from PagerDuty), surface as a future knob.
- **Mimir per-tenant Grafana datasource** — D-26 ships multitenancy off. If/when multitenancy lands (v2 hardening), the Mimir datasource grows a `X-Scope-OrgID` header config.

### Already deferred from earlier phases (still applicable)

- **MinIO replacement (Garage / SeaweedFS)** — Already deferred from M1.
- **Multi-tenant Loki/Mimir** — D-26 disables for M1.
- **Distributed/scalable-single-binary modes** — Loki/Tempo/Mimir all support beyond-monolithic; deferred.
- **HAProxy in front of distributed backends** — Already deferred per PROJECT.md.
- **Tecnativa-style docker-socket-proxy sidecar** — Defense in depth; already deferred.
- **Per-component bearer/mTLS auth on the internal bus** — Single-host trust boundary (D-55, D-66, D-90 unchanged).
- **Hook router (Flask app + role + bundles + auth)** — Phase-4 D-56 deferred to ALERT-V2-01..05.
- **Distributed example inventory** — PROJECT.md.
- **Kubernetes / OpenShift deployment** — PROJECT.md.
- **CI test harness (molecule / Vagrant)** — TEST-01.
- **Multi-architecture (arm64) support** — ARCH-01.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 5` returned zero matches.

</deferred>

---

*Phase: 05-ui-plane*
*Context gathered: 2026-05-19*
*Hard precondition: phase 4.1 (drop-vault-prefix) lands before plan 05-01 begins*
