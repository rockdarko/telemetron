# Phase 4: Alert Plane - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Port the **`alertmanager`** Ansible role and wire **Prometheus → Alertmanager** so the four Phase-3 baseline alert rules (`HostDown`, `FilesystemAlmostFull`, `ContainerRestartLoop`, `OTelCollectorDroppingSignals`) actually reach Alertmanager when they fire. Alertmanager runs single-instance on `:9093` against the `telemetron` bridge network, ships with the ALERT-01-mandated routing knobs (`group_by: [alertname, cluster, service]`, `group_interval: 5m`, `repeat_interval: 4h`), a single default `null` receiver (alerts dispatched nowhere by M1 default — Karma in Phase 5 is the operator UX), one default inhibition rule (`source severity=critical → target severity=warning, equal: [instance]`), and a persistent `telemetron_alertmanager_data` volume on `/alertmanager` preserving silences + nflog across container restarts.

**Scope reshape from the original Phase-4 design:** The Phase-4 hook router (Flask app under `hooks/router/`, `roles/hook_router/`, sample Jenkinsfiles under `hooks/jobs/`, allowlist + rate-limit + vault-supplied outbound token security model) is **deferred to a future milestone**. Originally framed as the "strongest competitive differentiator" of M1 (per SUMMARY.md), the user concluded mid-discussion that Jenkins-as-target is no longer current enough to lead with, and that re-framing the router as backend-agnostic (generic webhook → CI/automation) is a bigger reshape than M1 wants to absorb. ALERT-02..06 move from M1 §"Alert plane" to v2 §"Alert-V2" (`ALERT-V2-01..05`). Phase 4 becomes a **single-plan phase delivering ALERT-01 only** plus the Prometheus-side wiring needed to make ALERT-01 useful. The hook-router pitch returns in a later milestone alongside HA / Kube / etc.

Each role port mirrors the canonical patterns established by Phases 1–3: D-10a HEALTHCHECK poll, W6 single-handler restart, W7 `changed_when: false` on verify tasks, W8 in-network verify step, OPS-03 README schema, D-25 opinionated improvement (not mechanical translation) over upstream INSPQ, Gate 7 `org.telemetron.{service,job}` label-stamping. One plan + one role port + the cross-role Prometheus extension + the doc-rework cascade that moves the hook router out of M1 scope.

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues from Phase 3 (last decision was D-55). Phase 4 introduces D-56 through D-69.

### Scope reshape — hook router deferral (D-56, D-57, D-58)

- **D-56:** **The hook router (Flask app + Ansible role + sample bundles + observability surface) is deferred from M1 to a future milestone.** Originally framed as the "strongest competitive differentiator" of M1 (`.planning/research/SUMMARY.md` line 14, `.planning/research/FEATURES.md` line 50), the user concluded mid-discussion that Jenkins-as-target is no longer the right pitch for 2026 and that a backend-agnostic rework (generic webhook → CI/automation) is too large a reshape for M1. The hook-router work moves to a future milestone (`ALERT-V2-01..05`) and re-enters the project alongside that milestone's other scope. M1 ships the "LGTM observability plane on a single host with alerts visible in Karma" pitch; the hook-router pitch returns later.

- **D-57:** **Phase 4 reduces to a single plan: `04-01-PLAN.md`.** Original Phase-4 design called for 3 plans (Flask source → alertmanager → hook_router role). With the hook router deferred, plan 04-01 atomically delivers: (a) doc-rework cascade moving hook router to v2; (b) `roles/alertmanager/` port; (c) cross-role extension of `roles/prometheus/templates/prometheus.yml.j2` adding the `alerting: alertmanagers:` block; (d) cross-role retrofit of `roles/prometheus/templates/rules-baseline.yml.j2` adding `severity` labels to the four baseline rules (required for D-63 inhibit rule to match); (e) wire alertmanager into `playbooks/deploy_docker.yml` after `fluentbit`; (f) UAT covering AM → null receiver end-to-end + amtool silence test + AM-as-Prometheus-alerting-target verification. One plan keeps the doc reshape and the role port atomic; no risk of an in-flight inconsistency between "spec says hook router" and "code skipped it."

- **D-58:** **Doc-rework cascade (Phase-4 task 1 in plan 04-01) touches:**
  - **`PROJECT.md`** — "Active" requirements: remove "Write the hook router Flask app source under `hooks/router/` (was inline upstream) and ship sample Jenkinsfile runbooks under `hooks/jobs/`". "Out of Scope" or a new "Deferred for v2" subsection: document the deferral with cross-ref to ALERT-V2-01..05. "Key Decisions" table: existing "Hook router security model" row updates to "(deferred — v2 milestone)" with the original rationale preserved as institutional memory. Mention M1 role count if it changes (14 → 13 if hook_router is excluded; or keep "13 deployed + 1 deferred" framing).
  - **`REQUIREMENTS.md`** — Move ALERT-02..06 from §"Alert plane (ALERT)" into §"v2 Requirements (deferred — not in M1)" as `ALERT-V2-01..05` with one-line each:
    - `ALERT-V2-01`: Hook router Flask app under `hooks/router/` — backend-agnostic webhook bridge (was ALERT-02)
    - `ALERT-V2-02`: Explicit per-rule allowlist (was ALERT-03)
    - `ALERT-V2-03`: Per-(alertname, backend) rate limit default 6/hour (was ALERT-04; "job" renamed to "backend" to match the deferred backend-agnostic design)
    - `ALERT-V2-04`: Sample bundles under `hooks/jobs/` (GitHub Actions repository_dispatch, Slack webhook, generic-curl example, optionally a Jenkinsfile for historical context) (was ALERT-05)
    - `ALERT-V2-05`: `hook_router` Ansible role builds Flask image locally + wires Alertmanager `webhook_configs` (was ALERT-06)
    - Traceability table: keep ALERT-01 → Phase 4; remove ALERT-02..06 rows (or mark as v2).
  - **`ROADMAP.md`** — Phase 4 goal paragraph rewritten to remove hook-router framing; reduces to "Alertmanager dispatches Prometheus's evaluated alerts to a single `null` receiver by default (Karma in Phase 5 is the operator UX); persistent state survives restarts; one default inhibition rule (`source severity=critical → target severity=warning, equal: [instance]`) bounds replay risk; alerts pile up visibly rather than dispatching to anything automatically." Phase 4 success criteria reduced to AM-only checks. Phase 4 "Plans: TBD" → "Plans: 1 (04-01-PLAN.md)".
  - **`CLAUDE.md`** — `Hook router` row in the "Tech stack" recommendation table: mark deferred (or remove). The "Hook router" entry under "Custom / Glue" loses its build instructions but keeps the historical spec for the v2 milestone. The port allocation table loses `Hook Router 5000 / 5000` (or marks it v2). The "What NOT to Use" / "Dependency Graph" sections — review for hook-router references.
  - **`.planning/research/FEATURES.md`** — Rows referencing the hook router as "strongest differentiator" or "M1 scope" are reworded to "deferred to a future milestone." Rationale preserved.
  - **`.planning/research/SUMMARY.md`** — §"Phase 4: Alert Plane" rewritten to alertmanager-only M1 scope; line 14's "single highest-leverage M1 differentiator is the hook router" is reworded.
  - **`roles/README.md`** — `hook_router` row in the role status table: mark "deferred to v2 milestone" (or remove). "Added vs. upstream" line keeps the `node_exporter` addition; the `hook_router` addition mention shifts to "planned for a future milestone." The Gate-7 telemetron-label-stamp paragraph already mentions Phase 4 hook_router — reword to alertmanager-only.
  - **`hooks/README.md`** — Rewritten to mark hook router deferred ("Hook router (Alertmanager → generic CI/automation webhook bridge) is deferred to a future milestone. See `REQUIREMENTS.md` ALERT-V2-01..05 for the planned shape."). Directory survives as institutional memory but ships no code.

### Alertmanager role port (D-59..D-63)

- **D-59:** **Image pin `quay.io/prometheus/alertmanager:v0.32.1`** (locked by ALERT-01 and `CLAUDE.md` recommendation sheet). Quay (not Docker Hub) — co-published with the rest of the Prometheus family; matches Phase-3 node_exporter's Quay-over-Docker-Hub registry preference. Container is **single-instance monolithic** — `--cluster.listen-address=""` (empty string disables the gossip cluster) ships in the role's container args. The HA cluster mode is a future-milestone feature, not M1. Container name: `telemetron-alertmanager`. One tag: `alertmanager` (D-24).

- **D-60:** **Receivers tree — single default `null` receiver; route fan-out via inventory.** `roles/alertmanager/templates/alertmanager.yml.j2` renders:
  ```yaml
  route:
    receiver: 'null'
    group_by: [alertname, cluster, service]
    group_interval: 5m
    repeat_interval: 4h
    routes: []   # {{ alertmanager_extra_routes | default([]) | sorted-keys-jinja }}
  receivers:
    - name: 'null'
    # {{ alertmanager_extra_receivers | default([]) | sorted-keys-jinja }}
  ```
  Operators add real receivers via `alertmanager_extra_receivers` and routes via `alertmanager_extra_routes` (both inventory lists, both sorted-keys-iterated per D-20). The role's README.md explicitly calls out: **"Default receiver is `null` — alerts are visible in the Alertmanager UI and Karma (Phase 5) but dispatched to nothing automatically. Add a real receiver before you rely on this stack to wake you up."** Karma in Phase 5 is the operator UX; combined with the null default, alerts are *visible but not auto-actioned* in M1.

- **D-61:** **Time intervals locked by ALERT-01 — explicit in the rendered config, not relying on AM defaults.** `group_by: [alertname, cluster, service]`, `group_interval: 5m`, `repeat_interval: 4h`, plus `group_wait: 30s` (AM default; explicit anyway for documentation discipline). These are inventory knobs (`alertmanager_group_by`, `alertmanager_group_wait`, `alertmanager_group_interval`, `alertmanager_repeat_interval`) with the ALERT-01 values as defaults. Surfaced in `inventory/example-homelab/group_vars/all/alertmanager.yml`.

- **D-62:** **Persistent state — `telemetron_alertmanager_data` named volume mounted on `/alertmanager`.** Alertmanager writes silences, the notification log (nflog — used for dedup across restarts), and active-alert state under this path. Losing the volume = losing silences + losing dedup memory = Pitfall 7 replay-storm risk on restart. One named volume per D-16 convention. `compactor`-style cleanup is internal to Alertmanager; no external lifecycle needed. The Mimir `mimir-alerts` MinIO bucket from Phase 2 is **unrelated** (it's Mimir's embedded Alertmanager, which is unused in M1).

- **D-63:** **One default inhibition rule — `source severity=critical → target severity=warning, equal: [instance]`.** Standard Alertmanager pattern preventing a HostDown-style critical from spawning a flood of subordinate warnings on the same instance. Inhibit rule renders as:
  ```yaml
  inhibit_rules:
    - source_match:
        severity: critical
      target_match:
        severity: warning
      equal: [instance]
    # {{ alertmanager_extra_inhibit_rules | default([]) | sorted-keys-jinja }}
  ```
  Operators extend via `alertmanager_extra_inhibit_rules`. **This inhibit rule requires the Phase-3 baseline rules to carry `severity` labels — handled by D-65.**

### Prometheus → Alertmanager wiring (D-64, D-65)

- **D-64:** **Phase-4 plan 04-01 extends `roles/prometheus/templates/prometheus.yml.j2` with the `alerting: alertmanagers:` block.** New stanza:
  ```yaml
  alerting:
    alertmanagers:
      - static_configs:
          - targets: ['{{ prometheus_alertmanager_target }}']
  ```
  Adds `prometheus_alertmanager_target: alertmanager:9093` to `roles/prometheus/defaults/main.yml` (overridable per-environment via inventory). **Default-on** — no inventory knob to disable wiring; the alerting plane is part of M1's core value. The prometheus role's existing config-change handler notifies on this template update so `telemetron-prometheus` restarts when the alertmanager plan lands. The `inspq` grep gate + non-ASCII gate re-run against `roles/prometheus/` after the edit (must remain clean).

- **D-65:** **Phase-3 `roles/prometheus/templates/rules-baseline.yml.j2` retrofit — add `severity` labels to the four baseline rules:**
  - `HostDown` → `severity: critical`
  - `OTelCollectorDroppingSignals` → `severity: critical`
  - `FilesystemAlmostFull` → `severity: warning`
  - `ContainerRestartLoop` → `severity: warning`
  
  Required for D-63 inhibit rule to match (without `severity` labels, the `source_match: severity: critical` clause matches nothing). Severity assignment justified: HostDown + OTelCollectorDroppingSignals are pipeline-fatal (no host = no signal; OTel dropping = telemetry going to /dev/null). Filesystem-full + Container-restart-loop are degraded-but-not-fatal. Touch is 4 lines added under each rule's `labels:` map. Same plan 04-01 handles the prometheus restart via the existing config-change handler.

### Vault, gates, and verify (D-66, D-67, D-68, D-69)

- **D-66:** **Vault key surface for Phase 4: NONE added.** Alertmanager has no outbound auth in M1 (null receiver = no destination = no credentials). No inbound auth either (single-host bridge network; D-26 multitenancy-off applies to the trust boundary too). Mirrors Phase-3 D-55. `inventory/example-homelab/group_vars/all/vault.yml.example` does NOT grow in Phase 4. (The previously-planned `vault_hook_router_webhook_secret` + `vault_hook_router_jenkins_token` keys move to the deferred v2 milestone alongside D-56.)

- **D-67:** **All Phase-1+2+3 port-acceptance gates apply to `roles/alertmanager/`:**
  - **Gate 1** (INSPQ grep + non-ASCII) — D-21. Upstream `~/git/inspq/ansible/alert_manager/` has FR-language vars (`soir`, `nuit`, `jours`, `semaine`, `weekend`, `mep_*`), `noreply@inspq.qc.ca`, `America/Montreal`, `vault_inspq_*` paths — D-68 audit lists every match to strip.
  - **Gate 2** (image pin) — OPS-01. `quay.io/prometheus/alertmanager:v0.32.1` (explicit; upstream uses `:latest`).
  - **Gate 3** (vault discipline) — OPS-02. No keys added (D-66) so trivially passes; vault.yml.example unchanged.
  - **Gate 4** (idempotency) — OPS-04. Two consecutive playbook runs must report `changed=0`. Handlers (not `state: restarted`) for restarts; sorted-keys Jinja iteration on `alertmanager_extra_*` lists.
  - **Gate 5** (healthcheck + restart-policy) — OPS-06. `restart: unless-stopped`; healthcheck either via image default or explicit `CMD wget --spider -q http://localhost:9093/-/healthy` (verify image probe during plan-phase research).
  - **Gate 6** (README schema) — OPS-03. Mirrors `roles/minio/README.md` shape: variables → modes → tags → volumes → healthcheck → "Deviations from upstream INSPQ" → deprecation notes (none).
  - **Gate 7** (telemetron label stamp) — Plan 03-05 / INGEST-07. `community.docker.docker_container` task carries:
    ```yaml
    labels:
      org.telemetron.service: telemetron
      org.telemetron.job: alertmanager
    ```

- **D-68:** **D-25 INSPQ deviations audit — known entries to strip in plan 04-01.** Upstream `~/git/inspq/ansible/alert_manager/defaults/main.yml` ships with:
  - `alert_manager_smtp_from: noreply@inspq.qc.ca` → REMOVED (no SMTP receiver in M1; null receiver only).
  - `alert_manager_timezone: "America/Montreal"` → `Etc/UTC` (consume `telemetron_tz` from `group_vars/all/network.yml`; Pitfall 6 DST avoidance).
  - `alert_manager_soir_start_time / nuit_end_time / weekend_jours / mep_semaine_jours / mep_weekend_jours / mep_*_start_time / mep_*_end_time` → REMOVED. These are INSPQ-internal time-of-day routing window vars (`soir`=evening, `nuit`=night, `mep`=mise en production / release window); the entire FR-vocabulary topology is gone. If a future operator needs time-window routing, AM v0.32 has native `time_intervals` and `mute_time_intervals` — surface as a `alertmanager_extra_time_intervals` knob rather than as a hardcoded FR window.
  - `alert_manager_teams: []` + `alert_manager_team_name: "team"` → REMOVED. Telemetron is not INSPQ's multi-team Slack-routing topology; operators build their own routing tree via `alertmanager_extra_routes`.
  - `alert_manager_log_level: "debug"` → `info` (homelab default; operator override via `alertmanager_log_level`).
  - `alert_manager_route: {}` + `alert_manager_receivers: []` → REPLACED with the D-60 / D-61 / D-63 explicit structure.
  - `kubernetes_helm.yml` tasks file → REMOVED (K8s deferred per `PROJECT.md` constraints; `docker.yml` is the M1 deployment path).
  - `alert_manager_kubernetes_*`, `alert_manager_helm_*`, `alert_manager_namespace: telemetron`, `alert_manager_storage_class`, `alert_manager_persistence_enabled`, `alert_manager_pod_security_context`, `alert_manager_openshift_*` → REMOVED.
  - `alert_manager_docker_image_version: latest` → `v0.32.1` (D-59).
  - `alert_manager_docker_external_port: 9093` → kept (port stays 9093 per ALERT-01) but `alertmanager_publish_host: false` default (D-30 no-host-publish).
  - `alert_manager_container_recreate: true` → REMOVED (use handler-restart per D-19, not container-recreate).
  - `alert_manager_email_config_send_resolve` → REMOVED (no SMTP).
  - `alert_manager_smtp_*` (all) → REMOVED.
  - Naming: `alert_manager_*` vars → `alertmanager_*` (per locked naming normalization `ba836d2`).
  - `alert_amanger_weekend_jours` (typo in upstream — `amanger` instead of `manager`) → REMOVED with the rest of the FR window vocabulary.

- **D-69:** **Per-role in-network verify (mirrors Phase-3 D-54).** Plan 04-01's verify step runs:
  - One-shot `curlimages/curl` container on the `telemetron` bridge: `curl -f http://alertmanager:9093/-/ready` (assert 200); `curl -f http://alertmanager:9093/-/healthy` (assert 200).
  - `curl -fsS http://alertmanager:9093/api/v2/status | jq` (assert non-empty config with `route.receiver == "null"`, `route.group_by` contains `alertname`/`cluster`/`service`, `route.group_interval == "5m"`, `route.repeat_interval == "4h"`).
  - `curl -fsS http://alertmanager:9093/api/v2/receivers | jq` (assert single receiver named `null`).
  - **Prometheus → AM round-trip:** `curl -fsS http://prometheus:9090/api/v1/alertmanagers | jq` (assert `data.activeAlertmanagers` has one entry with `url: http://alertmanager:9093/api/v2/alerts`).
  - **Synthetic fire:** Use `amtool` in a one-shot container — `amtool alert add --alertmanager.url=http://alertmanager:9093 alertname=TestAlert severity=warning instance=verify-host` — then `amtool alert query --alertmanager.url=http://alertmanager:9093 alertname=TestAlert` (assert returns the alert in active state).
  - **Silence round-trip:** `amtool silence add` → `amtool silence query` (assert silence exists).
  - All one-shot containers use `auto_remove: true` (W7) and `changed_when: false` (W7) per Phase-1 conventions.

### Claude's Discretion (planner picks within these bounds)

- **Alertmanager `--log.level`** — default `info`; knob `alertmanager_log_level` surfaced in `roles/alertmanager/defaults/main.yml`.
- **Container args** — `--config.file=/etc/alertmanager/alertmanager.yml`, `--storage.path=/alertmanager`, `--web.listen-address=:9093`, `--cluster.listen-address=""` (disable clustering for M1). `--web.external-url` defaults to empty (operator overrides if they put AM behind a reverse proxy).
- **Container name** — `telemetron-alertmanager` (matches Phase-1+2+3 naming).
- **Config bind-mount layout** — Host `/opt/telemetron/alertmanager/alertmanager.yml` → container `/etc/alertmanager/alertmanager.yml:ro`. D-18 flat layout, no nested `config/` subdir.
- **Healthcheck CMD** — verify during plan-phase research whether the `quay.io/prometheus/alertmanager:v0.32.1` image has a default HEALTHCHECK; if not, ship explicit `wget --spider -q http://localhost:9093/-/healthy || exit 1` (mirrors Phase-2 Tempo / Phase-3 OTel conditional-healthcheck pattern when distroless).
- **`alertmanager_extra_*` defaults** — all `[]` (empty list); operators extend.
- **Render shape for `alertmanager_extra_receivers / extra_routes / extra_inhibit_rules`** — list-of-dicts iterated with `{% for item in list | sort(attribute='name') %}` per D-20.
- **Plan 04-01 task order** — planner finalizes. Suggested: (1) doc rework cascade (touches PROJECT/REQUIREMENTS/ROADMAP/SUMMARY/CLAUDE/FEATURES/roles README/hooks README); (2) `roles/alertmanager/` scaffolding (defaults, tasks, templates, handlers, README); (3) `roles/prometheus/templates/prometheus.yml.j2` extension (D-64); (4) `roles/prometheus/templates/rules-baseline.yml.j2` severity retrofit (D-65); (5) `inventory/example-homelab/group_vars/all/alertmanager.yml` ship; (6) `playbooks/deploy_docker.yml` append `alertmanager` role entry after `fluentbit`; (7) port-acceptance gate checks; (8) D-69 verify run.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project framing & scope

- `.planning/PROJECT.md` — Vision, M1 constraints, "Active" requirements, Key Decisions table. **Note:** plan 04-01 task 1 rewrites the hook-router entry in "Active" and the Key Decisions row per D-58.
- `.planning/REQUIREMENTS.md` §"Alert plane (ALERT)" — Only **ALERT-01** stays in M1 after the Phase-4 doc rework. **ALERT-02..06 move to §"v2 Requirements" as ALERT-V2-01..05** per D-58.
- `.planning/ROADMAP.md` §"Phase 4: Alert Plane" — Goal paragraph + success criteria are **rewritten in plan 04-01 task 1** per D-58. The new Phase-4 success criteria are derived from ALERT-01 + D-64 + D-65 + D-69.
- `CLAUDE.md` §"Technology Stack" — Alertmanager row: `quay.io/prometheus/alertmanager:v0.32.1`. Hook router row + "Custom / Glue" section: **rewritten to mark deferred to a future milestone** per D-58.

### Phase 1+2+3 decisions that propagate forward (read in full before Phase 4 planning)

- `.planning/phases/01-foundation-storage/01-CONTEXT.md` — D-04 (network in pre_tasks), D-06 (no shared base role), D-10a (HEALTHCHECK poll), D-12..D-14 (no host publish), D-15..D-18 (inventory + volumes + config layout), D-19..D-21 (handler restart, sorted-keys Jinja, grep gates).
- `.planning/phases/02-telemetry-backends/02-CONTEXT.md` — D-22 (one plan per role), D-23 (each plan wires its own role), D-24 (one tag per role), D-25 (opinionated improvement over upstream), D-26 (multitenancy off — no auth on the internal trust boundary), D-30 (no host publish default), D-32 (in-network verify one-shot — pattern reused as D-69).
- `.planning/phases/03-ingest-plane/03-CONTEXT.md` — D-40 (one deployable unit per plan — Phase 4 simplifies this further: one plan total because the hook-router unit moves out), D-54 (in-network verify topology — directly reused as D-69), D-55 (no vault keys this phase — directly mirrored as D-66), Plan 03-05 / Gate 7 telemetron-label-stamp (directly inherited as D-67 Gate 7).
- `roles/minio/`, `roles/loki/`, `roles/tempo/`, `roles/mimir/`, `roles/node_exporter/`, `roles/opentelemetry/`, `roles/prometheus/`, `roles/fluentbit/` (entire roles) — eight canonical role-port templates. Every layout choice (directory shape, defaults, handlers, README schema, verify-task pattern, D-10a HEALTHCHECK poll, D-54 in-network verify) propagates verbatim to `roles/alertmanager/`. Researcher AND planner should read all eight roles before producing plan 04-01.
- `roles/minio/tasks/bootstrap.yml` — D-10a `docker_container_info` HEALTHCHECK poll pattern.
- `roles/prometheus/templates/prometheus.yml.j2` — **Plan 04-01 extends with the `alerting: alertmanagers:` block per D-64.**
- `roles/prometheus/templates/rules-baseline.yml.j2` — **Plan 04-01 retrofits `severity` labels on the four baseline rules per D-65.**
- `roles/prometheus/defaults/main.yml` — **Plan 04-01 adds `prometheus_alertmanager_target: alertmanager:9093`.**
- `roles/README.md` §"Port process" + §"Per-role port-acceptance gates" — six gates incl. Gate 7. Plan 04-01 also rewrites the `hook_router` row in the role status table per D-58.

### Research backing for this phase

- `.planning/research/PITFALLS.md` §"Pitfall 7: Alertmanager + hook_router replay storms and token leakage" — Backing for D-60 (`null` receiver default avoids unconditional outbound fires) + D-62 (persistent nflog volume preserves dedup across restart) + D-63 (default inhibit rule bounds replay risk). The hook-router-side mitigations (allowlist + rate limit + vault-supplied token + shared-secret header) move with the v2 deferral but are documented here for the future milestone's spec.
- `.planning/research/PITFALLS.md` §"Integration Gotchas" — Rows for "Alertmanager → hook_router" and "hook_router → Jenkins" are now applicable to the deferred v2 milestone; referenced here for completeness.
- `.planning/research/PITFALLS.md` §"Pitfall 8: Ansible role idempotency cascades" — Backing for handler-restart-not-state-restarted in `roles/alertmanager/` (Gate 4 per D-67).
- `.planning/research/PITFALLS.md` §"Pitfall 9: Fork-from-INSPQ leftovers" — Backing for D-68 grep-gate audit + the FR-language vocabulary strip.
- `.planning/research/STACK.md` — Alertmanager image pin `quay.io/prometheus/alertmanager:v0.32.1`; component port matrix.
- `.planning/research/FEATURES.md` — Original "strongest differentiator" hook-router framing (lines 50, 53, 99–104, 143, 162). **Plan 04-01 task 1 rewrites these per D-58.**
- `.planning/research/SUMMARY.md` §"Phase 4: Alert Plane" (lines 14, 60, 104, 154–162). **Plan 04-01 task 1 rewrites these per D-58.**
- `.planning/research/ARCHITECTURE.md` — Signal-flow apps → OTel → backends → AM. The "hook_router Flask :5001" component in the ASCII diagram (lines 53–61) is rewritten to mark deferred.

### Upstream INSPQ source-of-truth (for porting + D-25 / D-68 improvement audit)

- `~/git/inspq/ansible/alert_manager/` (operator workstation) — Source role for plan 04-01. D-68 lists known deviations to strip: FR window vocabulary (`soir`/`nuit`/`jours`/`semaine`/`weekend`/`mep_*`), INSPQ team topology (`alert_manager_teams`, `alert_manager_team_name`), `noreply@inspq.qc.ca` SMTP, `America/Montreal` timezone, SMTP receivers, k8s/Helm/OpenShift tasks, `latest` tag, `container_recreate: true`.

### Ansible module & collection documentation

- [community.docker.docker_container module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_module.html) — Primary module for `roles/alertmanager/tasks/main.yml`.
- [community.docker.docker_container_info module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_info_module.html) — D-10a HEALTHCHECK poll pattern.
- [community.docker.docker_volume module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_volume_module.html) — `telemetron_alertmanager_data` volume.

### Upstream Alertmanager documentation (consulted by research per D-60/D-61/D-63/D-69 shapes)

- [Alertmanager configuration v0.32](https://prometheus.io/docs/alerting/latest/configuration/) — `route`, `receivers`, `inhibit_rules`, `time_intervals`, `mute_time_intervals` syntax.
- [Alertmanager HTTP API v2](https://github.com/prometheus/alertmanager/blob/main/api/v2/openapi.yaml) — `/-/ready`, `/-/healthy`, `/api/v2/status`, `/api/v2/receivers`, `/api/v2/alerts`, `/api/v2/silences` endpoints used by D-69 verify.
- [Prometheus alerting integration](https://prometheus.io/docs/alerting/latest/clients/) — `alerting: alertmanagers:` block in `prometheus.yml`.
- [Alertmanager null receiver](https://prometheus.io/docs/alerting/latest/configuration/#receiver) — Empty-receiver pattern (`- name: 'null'` with no other config).
- [Alertmanager inhibit_rules](https://prometheus.io/docs/alerting/latest/configuration/#inhibit_rule) — `source_match` / `target_match` / `equal` semantics for D-63.
- [amtool reference](https://github.com/prometheus/alertmanager#amtool) — Used by D-69 verify for synthetic alert + silence round-trips.

### Locked naming normalizations (Phase 1 baseline, carried forward + D-68 extension)

- git commit `ba836d2` — naming locked. `alert_manager` → `alertmanager` (var prefix + role name); upstream typo `alert_amanger_weekend_jours` collapsed to nothing (vocabulary removed).
- Phase 1 conventions: vault keys `vault_<role>_<purpose>` (none added in Phase 4 per D-66), volumes `telemetron_<role>_data` (`telemetron_alertmanager_data`), config dirs `/opt/telemetron/<role>/` (`/opt/telemetron/alertmanager/`), tags one-per-role (`alertmanager`), container names `telemetron-<role>` (`telemetron-alertmanager`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`roles/minio/`, `roles/loki/`, `roles/tempo/`, `roles/mimir/`, `roles/node_exporter/`, `roles/opentelemetry/`, `roles/prometheus/`, `roles/fluentbit/`** — Eight canonical role templates from Phases 1–3. Every layout choice (directory shape, defaults file, handler convention, README schema, verify-via-one-shot-container pattern, D-10a HEALTHCHECK poll, D-54 in-network verify) propagates verbatim to `roles/alertmanager/`. Plan 04-01's researcher AND planner should skim all eight before producing the role port.
- **`roles/minio/tasks/bootstrap.yml`** — D-10a `docker_container_info` HEALTHCHECK poll pattern. `roles/alertmanager/` mirrors this for "wait for AM to be ready before running the verify step."
- **`roles/prometheus/templates/prometheus.yml.j2`** — Currently has no `alerting:` block. Plan 04-01 extends with D-64.
- **`roles/prometheus/templates/rules-baseline.yml.j2`** — Currently has four rules with no `severity` labels. Plan 04-01 retrofits with D-65.
- **`roles/prometheus/defaults/main.yml`** — Plan 04-01 adds `prometheus_alertmanager_target: alertmanager:9093`.
- **`roles/node_exporter/`** — Closest analog in Phases 1–3 to `roles/alertmanager/` in shape: stateless-but-with-a-data-volume monolithic container, one config file, simple bind-mount, in-network verify. Pattern-match against this when scaffolding `roles/alertmanager/`.
- **`inventory/example-homelab/group_vars/all/network.yml`** — `telemetron_network`, `telemetron_publish_default: false`, `telemetron_tz: Etc/UTC` (D-68 strips `America/Montreal` and inherits `telemetron_tz`).
- **`inventory/example-homelab/group_vars/all/storage.yml`** — `telemetron_volume_prefix`, `telemetron_config_root`. Plan 04-01 adds `alertmanager.yml` alongside the existing per-role files.
- **`inventory/example-homelab/group_vars/all/vault.yml.example`** — Phase 4 does NOT extend this file (D-66).
- **`playbooks/deploy_docker.yml`** — Roles list ends at `fluentbit`. Plan 04-01 appends `- role: alertmanager` with tag `alertmanager`.
- **`hooks/README.md`** — Plan 04-01 task 1 rewrites this to mark hook router deferred per D-58.

### Established patterns (mirrored from Phases 1–3; planner enforces in Phase 4)

- **Role layout** — `defaults/main.yml`, `tasks/main.yml`, `tasks/verify.yml`, `handlers/main.yml`, `templates/alertmanager.yml.j2`, `meta/main.yml`, `README.md`.
- **Image pin discipline (OPS-01)** — `quay.io/prometheus/alertmanager:v0.32.1`.
- **Volume naming (D-16)** — `telemetron_alertmanager_data`.
- **Config bind-mount (D-18)** — Host `/opt/telemetron/alertmanager/alertmanager.yml` → container `/etc/alertmanager/alertmanager.yml:ro`.
- **Restart-by-handler (D-19, W6)** — One handler `Restart telemetron-alertmanager` triggered by config template change.
- **Sorted-keys Jinja iteration (D-20)** — `{% for k in d.keys() | sort %}` on the `alertmanager_extra_*` lists.
- **In-network verify one-shot (D-54 → D-69)** — Final task runs `curlimages/curl` + `amtool` one-shot containers on the `telemetron` network.
- **Grep gates per role (D-21)** — INSPQ-noise + non-ASCII gates per role port (D-67 Gate 1).
- **No-host-publish default (D-30)** — `alertmanager_publish_host: false`. Operators can opt-in via `alertmanager_published_ports`.
- **Telemetron label stamp (Gate 7)** — `org.telemetron.service=telemetron`, `org.telemetron.job=alertmanager` on the container.

### Integration points

- **`playbooks/deploy_docker.yml`** — Plan 04-01 appends one role entry after `fluentbit`. Final shape after Phase 4: `pre_tasks: [network] → minio → loki → tempo → mimir → node_exporter → opentelemetry → prometheus → fluentbit → alertmanager`. Phase 5 (grafana, karma, promlens) appends on top.
- **`inventory/example-homelab/group_vars/all/`** — Plan 04-01 adds `alertmanager.yml` with `alertmanager_group_by`, `alertmanager_group_wait`, `alertmanager_group_interval`, `alertmanager_repeat_interval`, `alertmanager_log_level`, `alertmanager_extra_receivers`, `alertmanager_extra_routes`, `alertmanager_extra_inhibit_rules`, `alertmanager_publish_host`. Vault file UNCHANGED (D-66).
- **`roles/README.md`** — Plan 04-01 marks `alertmanager` as ☑ ported; marks `hook_router` as "deferred to a future milestone."
- **`roles/prometheus/templates/prometheus.yml.j2`** — Plan 04-01 extends with D-64.
- **`roles/prometheus/templates/rules-baseline.yml.j2`** — Plan 04-01 retrofits D-65.
- **`roles/prometheus/defaults/main.yml`** — Plan 04-01 adds `prometheus_alertmanager_target`.
- **`/opt/telemetron/alertmanager/`** — New host-side config tree created by the role's first task.
- **`telemetron` bridge network** — `telemetron-alertmanager` attaches. Prometheus reaches it via `alertmanager:9093` (D-64). Phase-5 Karma will reach the same name when it lands.

</code_context>

<specifics>
## Specific Ideas

- **Pitfall-7 mitigation toolkit was the original M1 differentiator.** The allowlist + rate limit + vault-supplied token + shared-secret header design was framed as the "single highest-leverage M1 differentiator" in `.planning/research/SUMMARY.md`. By deferring the hook router to v2, M1's pitch trades "turnkey runbook automation" for "single-host LGTM observability plane with alerts visible in Karma." The user's call: a more defensible 2026 pitch in fewer features beats a 2020-era differentiator stretched into 2026.
- **The `null` receiver is a deliberate, called-out choice — not an oversight.** `roles/alertmanager/README.md` MUST explicitly explain it: "Default receiver is `null` — alerts are visible in the Alertmanager UI and Karma (Phase 5) but dispatched to nothing automatically. Add a real receiver before you rely on this stack to wake you up." Otherwise an operator silences the wrong way (deleting receivers thinking they're misconfigured) instead of adding what they need.
- **Karma's role expands.** Originally Phase-5 Karma was a "auxiliary alert UI." With the hook router deferred, Karma becomes THE alert UX in M1 — silences, deduplication views, and grid groupings are how operators interact with the alert plane in single-host M1. Phase 5 planning should treat Karma accordingly.
- **The Phase-3 rules severity-label retrofit (D-65) is small but load-bearing.** Without `severity` labels on the four baseline rules, D-63's inhibit rule matches nothing and the inhibit_rules block is dead code. Four 4-line edits in plan 04-01 keep the inhibit rule meaningful.
- **D-68's INSPQ deviation list is unusually long.** The upstream `alert_manager` role has the heaviest FR-language vocabulary surface in the entire upstream stack (`soir`/`nuit`/`jours`/`semaine`/`weekend`/`mep_*` — Quebec-gov on-call routing). The grep-gate scan WILL surface a lot of matches; plan 04-01 must budget time for a thorough strip.
- **Single-instance Alertmanager + `--cluster.listen-address=""`** — explicitly disable the gossip cluster. The default config tries to bind on `:9094` for cluster gossip; in M1's single-instance model this just emits noisy logs. Disabling cluster mode is one CLI flag; ship it.
- **The hook-router design captured in DISCUSSION-LOG.md is not lost work.** When the v2 milestone picks this back up, the deferred design (two-tier `hook_router_backends` + `hook_router_rules` schema, in-memory rate limit with `workers=1`, Bearer-token inbound auth, `/metrics` with per-backend labels, sample bundles for GH Actions / Slack / generic) is in the audit trail and can be picked up without re-discussion.

</specifics>

<deferred>
## Deferred Ideas

### Out of Phase 4 (lands in v2 milestone — `ALERT-V2-01..05`)

- **Hook router Flask app (`hooks/router/`)** — Backend-agnostic webhook bridge (NOT Jenkins-specific). Two-tier schema: `hook_router_backends: { <name>: { method, url, headers, body_template, auth } }` + `hook_router_rules: { <AlertName>: { backend: <name>, params: {...} } }`. Operators define both via inventory, secrets are env-vars-from-vault. **`ALERT-V2-01`**.
- **Explicit per-rule allowlist enforcement** — No `{*}` wildcards; reject (4xx) unrecognized alerts; log loudly. **`ALERT-V2-02`**.
- **Per-(alertname, backend) rate limit** — Default 6/hour, configurable. Storage: in-memory dict in the Flask process; Gunicorn `workers=1` for an exact window (homelab single-process simplicity). 429 + counter `hook_router_rate_limited_total{alertname, backend}` on overflow. **`ALERT-V2-03`**.
- **Sample bundles under `hooks/jobs/`** — GitHub Actions repository_dispatch (`hooks/jobs/github-actions/example-workflow.yml`), Slack incoming webhook (`hooks/jobs/slack/example-payload.json`), generic curl-equivalent (`hooks/jobs/generic/example-curl.sh`); optionally a Jenkinsfile for historical context. **`ALERT-V2-04`**.
- **`roles/hook_router/`** — Ansible role that builds the Flask image locally via `community.docker.docker_image` (build source = `hooks/router/Dockerfile`), deploys the container, wires the Alertmanager `webhook_configs` receiver pointing at `http://hook-router:5001/alert`, injects shared-secret-header + outbound-token env vars from vault. Builds locally on the target host (no registry dependency). **`ALERT-V2-05`**.
- **Hook router observability** — `/metrics` Prometheus endpoint on the Flask app (counters: `hook_router_requests_total{outcome=accepted|rejected_unknown|rejected_unauthorized|rate_limited}`, `hook_router_backend_calls_total{backend, outcome=success|failure|timeout}`, `hook_router_rate_limited_total{alertname, backend}`; histogram: `hook_router_backend_call_latency_seconds{backend}`; gauge: `hook_router_build_info{version, python_version}`). Plus a Prometheus scrape job for it (hardcoded default `job_name: hook_router` in `prometheus.yml.j2`, matching Phase-3 D-44 pattern for default scrape jobs). **(Implied by ALERT-V2-01.)**
- **Inbound auth shape** — `Authorization: Bearer <vault_hook_router_webhook_secret>` header on Alertmanager → hook_router POSTs. AM v0.32 native support via `http_config.authorization.credentials_file`. (Original framing was `X-Telemetron-Secret` custom header; standardized to Bearer during discussion.) **(Implied by ALERT-V2-01.)**
- **Rules-reload behavior** — Restart-only via Ansible handler (mirrors D-19); no SIGHUP or inotify in the Flask app. Gunicorn re-reads `rules.yml` on container boot. **(Implied by ALERT-V2-05.)**
- **`docs/hook-router.md`** — Already in v2 doc set as `DOCS-V2-04`.

### Out of Phase 4 (lands in Phase 5)

- **Karma over Alertmanager** — Phase 5 (UI-05). With the M1 null-receiver default, Karma is the operator UX for alerts in M1.
- **Grafana datasource UIDs** — Phase 5 (UI-02).
- **Trace-to-logs correlation** — Phase 5 (UI-04).

### Out of Phase 4 (lands in Phase 6)

- **M1 acceptance smoke test (synthetic log + metric + trace in Grafana within 60s)** — Phase 6 (OPS-07).
- **`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`** — Phase 6.

### Already deferred from earlier phases (still applicable)

- **MinIO replacement (Garage / SeaweedFS)** — Already deferred from M1.
- **Multi-tenant Loki/Mimir** — D-26 disables.
- **Distributed/scalable-single-binary modes** — Loki/Tempo/Mimir all support beyond-monolithic.
- **HAProxy in front of distributed backends** — Already deferred per PROJECT.md.
- **Tecnativa-style docker-socket-proxy sidecar** — Defense in depth for the D-52 Docker socket mount (already deferred).
- **Per-component bearer/mTLS auth on the internal bus** — Single-host trust boundary (D-55, D-66).
- **Alertmanager `time_intervals` / `mute_time_intervals`** — Standard AM v0.32 feature; surface as `alertmanager_extra_time_intervals` and `alertmanager_extra_mute_time_intervals` knobs if/when operators need them.
- **Alertmanager HA cluster mode** — `--cluster.listen-address` disabled in M1 (D-59). Re-enable in a future HA milestone alongside `haproxy` and distributed-mode backends.
- **SMTP receivers, Slack default receiver, log-sidecar receiver** — All considered and rejected during discussion (lock vendors / out of scope per CLAUDE.md fixed component list). Operators wire their own via `alertmanager_extra_receivers`.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 4` returned zero matches.

</deferred>

---

*Phase: 04-alert-plane*
*Context gathered: 2026-05-18*
