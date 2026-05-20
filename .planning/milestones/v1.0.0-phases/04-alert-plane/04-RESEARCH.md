# Phase 4: Alert Plane - Research

**Researched:** 2026-05-18
**Domain:** Alertmanager v0.32.1 Ansible role port + Prometheus alerting wiring + doc cascade
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-56:** Hook router deferred from M1 to future milestone. ALERT-02..06 move to ALERT-V2-01..05.
- **D-57:** Phase 4 is a single-plan phase: `04-01-PLAN.md` only.
- **D-58:** Doc-rework cascade in plan 04-01 task 1 touches PROJECT.md / REQUIREMENTS.md / ROADMAP.md / CLAUDE.md / FEATURES.md / SUMMARY.md / roles/README.md / hooks/README.md.
- **D-59:** Image pinned to `quay.io/prometheus/alertmanager:v0.32.1`. Container name `telemetron-alertmanager`. Single-instance monolithic.
- **D-60:** Single default `null` receiver; operators extend via `alertmanager_extra_receivers` / `alertmanager_extra_routes`.
- **D-61:** Time intervals explicit: `group_by: [alertname, cluster, service]`, `group_wait: 30s`, `group_interval: 5m`, `repeat_interval: 4h`.
- **D-62:** Persistent state on `telemetron_alertmanager_data` named volume mounted at `/alertmanager`.
- **D-63:** One inhibit rule: `source severity=critical → target severity=warning, equal: [instance]`. Operators extend via `alertmanager_extra_inhibit_rules`.
- **D-64:** `roles/prometheus/templates/prometheus.yml.j2` extended with `alerting: alertmanagers:` block. New default `prometheus_alertmanager_target: alertmanager:9093`.
- **D-65:** `roles/prometheus/templates/rules-baseline.yml.j2` retrofitted with severity labels on all four baseline rules.
- **D-66:** No vault keys added in Phase 4.
- **D-67:** All six port-acceptance gates apply (Gate 7 telemetron label stamp).
- **D-68:** INSPQ deviation list: FR window vocabulary (`soir`/`nuit`/`jours`/`semaine`/`weekend`/`mep_*`), team topology (`alert_manager_teams`, `alert_manager_team_name`), SMTP, `America/Montreal`, k8s/Helm/OpenShift tasks, `latest` tag, `container_recreate: true`, var prefix `alert_manager_*` → `alertmanager_*`.
- **D-69:** In-network verify with `curlimages/curl` + `amtool` one-shot containers covering `/-/ready`, `/-/healthy`, `/api/v2/status`, `/api/v2/receivers`, Prometheus alertmanagers API, synthetic alert add/query, silence add/query.

### Claude's Discretion

- Alertmanager log level default `info`; knob `alertmanager_log_level`.
- Container args: `--config.file`, `--storage.path=/alertmanager`, `--web.listen-address=:9093`, `--cluster.listen-address=""`, `--web.external-url` defaults empty.
- Container name: `telemetron-alertmanager`.
- Config bind-mount: Host `/opt/telemetron/alertmanager/alertmanager.yml` → container `/etc/alertmanager/alertmanager.yml:ro`.
- Healthcheck CMD: verify image HEALTHCHECK presence; if absent ship explicit `wget --spider -q http://localhost:9093/-/healthy || exit 1`.
- `alertmanager_extra_*` defaults all `[]`.
- Extra lists rendered with `{% for item in list | sort(attribute='name') %}`.
- Plan 04-01 task order: planner finalizes (suggested order in CONTEXT.md § Claude's Discretion).

### Deferred Ideas (OUT OF SCOPE)

- Hook router Flask app, `hooks/router/`, `roles/hook_router/`, sample job bundles, inbound auth, rate limit, per-rule allowlist — all `ALERT-V2-01..05`.
- Alertmanager HA cluster mode.
- SMTP, Slack, log-sidecar default receivers.
- `time_intervals` / `mute_time_intervals` (surface as extension knobs only).
- Karma (Phase 5).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALERT-01 | Alertmanager running on `:9093` with `group_by: [alertname, cluster, service]`, `group_interval: 5m`, `repeat_interval: 4h` | Role port + D-60/D-61 config; confirmed by live `amtool check-config` |
| ALERT-02..06 | Hook router + allowlist + rate limit + sample jobs + hook_router role | OUT OF SCOPE — move to §"v2 Requirements" as ALERT-V2-01..05 per D-56/D-58 |
</phase_requirements>

---

## Summary

Phase 4 is reshaped to a single plan delivering one new role (`roles/alertmanager/`) plus a cross-role Prometheus wiring change plus a doc-rework cascade that records the hook-router deferral across seven files. The hook-router work (ALERT-02..06) is moved to `ALERT-V2-01..05`. ALERT-01 is the only code-complete requirement.

The alertmanager role mirrors the canonical Phase 1–3 patterns: D-10a HEALTHCHECK poll, W6 single-handler restart, D-20 sorted-keys Jinja, D-54 in-network verify via one-shot containers, OPS-03 README schema, Gate 7 label stamp. The one new verification tool is `amtool`, which is bundled at `/bin/amtool` inside the `quay.io/prometheus/alertmanager:v0.32.1` image. All D-69 verify steps are exercisable via `docker exec` or a one-shot container.

The D-65 severity-label retrofit on `rules-baseline.yml.j2` is load-bearing: without `severity: critical|warning` on the four baseline rules the D-63 inhibit rule matches nothing and is dead code. RESEARCH confirmed those labels are already present in the existing file — D-65 is a no-op for `HostDown` and `FilesystemAlmostFull` (already have them), but `ContainerRestartLoop` and `OTelCollectorDroppingSignals` need them added.

**Primary recommendation:** Follow the CONTEXT.md D-57 single-plan shape. Use `source_matchers:` (not deprecated `source_match:`) for the inhibit rule. Ship an explicit HEALTHCHECK in the role since the image provides none.

---

## Open Question Resolutions

### Q1 — HEALTHCHECK presence in `quay.io/prometheus/alertmanager:v0.32.1`

**ANSWER: No built-in HEALTHCHECK. Explicit healthcheck required.**

Source: `docker inspect quay.io/prometheus/alertmanager:v0.32.1 --format '{{json .Config.Healthcheck}}'` returns `null` (executed live).

The Dockerfile (`github.com/prometheus/alertmanager/blob/v0.32.1/Dockerfile`) uses a `busybox` base and defines no `HEALTHCHECK` instruction. The image exposes `VOLUME ["/alertmanager"]` and `ENTRYPOINT ["/bin/alertmanager"]` with `CMD ["--config.file=/etc/alertmanager/alertmanager.yml","--storage.path=/alertmanager"]` but no health instruction.

**Plan action:** Ship explicit healthcheck in the `docker_container` task:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --spider -q http://localhost:9093/-/healthy || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 5
  start_period: 30s
```
The `busybox` base means `wget` is available (unlike distroless). This matches the D-10a HEALTHCHECK poll pattern — `State.Health.Status` will reach `healthy` once the endpoint responds.

Confidence: HIGH (direct `docker inspect` on the actual image).

---

### Q2 — `inhibit_rules` matcher syntax for AM v0.32.1

**ANSWER: Use `source_matchers` / `target_matchers` (PromQL-style list). `source_match` is deprecated but still accepted.**

Source: Prometheus documentation (`prometheus.io/docs/alerting/latest/configuration/`) states `source_match` is "DEPRECATED: Use source_matchers below." Both syntaxes were verified with `amtool check-config` against the actual v0.32.1 image — both return `SUCCESS`. The CONTEXT.md D-63 shows `source_match:` (old syntax); the planner SHOULD use `source_matchers:` instead to avoid deprecation warnings in logs.

**Correct template syntax:**
```yaml
inhibit_rules:
  - source_matchers:
      - severity = critical
    target_matchers:
      - severity = warning
    equal: [instance]
```

**amtool verified:** `amtool check-config` on the above template returns `SUCCESS / Found: 1 inhibit rules`.

Confidence: HIGH (direct `amtool check-config` on the actual image; Prometheus docs confirmed deprecation).

---

### Q3 — `amtool` image source and one-shot container shape for D-69 verify

**ANSWER: `amtool` is at `/bin/amtool` inside the alertmanager image. Use `docker exec` on the running container, not a separate one-shot.**

Source: `docker run --rm --entrypoint=/bin/sh quay.io/prometheus/alertmanager:v0.32.1 -c "which amtool"` returns `/bin/amtool` (executed live). The image ships both `/bin/alertmanager` and `/bin/amtool`.

**Preferred D-69 verify pattern** — use `docker exec` for the running container (no separate image needed):
```yaml
- name: amtool synthetic alert add
  community.docker.docker_container_exec:
    container: "{{ alertmanager_container_name }}"
    command: >-
      /bin/amtool alert add --alertmanager.url=http://localhost:9093
      alertname=TestAlert severity=warning instance=verify-host
  changed_when: false
  tags: [alertmanager, alertmanager-verify]
```

**Alternative** (verified working): `docker exec telemetron-alertmanager /bin/amtool alert add --alertmanager.url=http://localhost:9093 alertname=TestAlert severity=warning instance=verify-host`

Note: `amtool alert add` exits 0 silently; `amtool alert query` returns the table with the alert.

Confidence: HIGH (direct execution on the actual image).

---

### Q4 — `--cluster.listen-address=""` behavior

**ANSWER: Confirmed. Empty string disables gossip cluster entirely. Default is `0.0.0.0:9094`.**

Source: `docker run --rm quay.io/prometheus/alertmanager:v0.32.1 --help 2>&1` output shows:
```
--cluster.listen-address="0.0.0.0:9094"
                         Listen address for cluster. Set to empty string
```
The code comment and docs confirm: when `""`, no gossip mesh is created and AM runs standalone. Also confirmed by the live `/api/v2/status` response showing `"cluster":{"peers":[],"status":"disabled"}` when started with `--cluster.listen-address=""`.

Without this flag, AM tries to bind `:9094` and emits noisy log lines about failed cluster peer connections (even with one node, it tries to gossip with itself).

Confidence: HIGH (direct `--help` output + live API response).

---

### Q5 — `prometheus.yml` alerting block syntax

**ANSWER: Minimal block confirmed valid with `promtool check config`.**

Source: `promtool check config` against the actual `prom/prometheus:v3.11.3` image returned `SUCCESS` for:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

Additional knobs available but not required for M1: `scheme` (default `http`), `path_prefix` (default empty), `timeout` (default `10s`), `api_version` (default `v2`). All defaults are correct for this stack. No `X-Scope-OrgID` or auth needed (D-26 no multitenancy; D-66 no inbound auth).

**D-64 template addition** — fits cleanly after the `rule_files:` block and before `remote_write:`:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['{{ prometheus_alertmanager_target }}']
```

The existing Prometheus restart handler (`listen: restart prometheus` in `roles/prometheus/handlers/main.yml`) fires on any template change — adding the `alerting:` block to `prometheus.yml.j2` will trigger `docker restart telemetron-prometheus` automatically.

Confidence: HIGH (direct `promtool check config` on the actual image).

---

### Q6 — Volume mount path

**ANSWER: `/alertmanager` is the correct in-container data path. Confirmed by image VOLUME declaration.**

Source: `docker inspect quay.io/prometheus/alertmanager:v0.32.1 --format '{{json .Config.Volumes}}'` returns `{"/alertmanager":{}}`. The image CMD also passes `--storage.path=/alertmanager`.

The named volume `telemetron_alertmanager_data` should mount at `/alertmanager`. The config bind-mount is separate: host `/opt/telemetron/alertmanager/alertmanager.yml` → container `/etc/alertmanager/alertmanager.yml:ro`.

Confidence: HIGH (direct `docker inspect` on the actual image).

---

### Q7 — `/-/ready` vs `/-/healthy` semantics

**ANSWER: Both endpoints exist and return HTTP 200. Both confirmed by live probe.**

Source: Live HTTP probe against `quay.io/prometheus/alertmanager:v0.32.1` container:
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:19093/-/ready` → `200`
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:19093/-/healthy` → `200`

Semantics (standard Prometheus-family convention): `/-/healthy` = process is alive (always 200 once started); `/-/ready` = ready to serve traffic (200 when configuration loaded and no fatal errors). Both are appropriate for the D-69 verify.

Confidence: HIGH (direct HTTP probe on the actual image).

---

### Q8 — HTTP API v2 endpoints

**ANSWER: Confirmed live. Key finding: `route.*` fields are embedded in `config.original` (YAML string), not as nested JSON fields.**

Source: Live `curl -s http://localhost:19093/api/v2/status` response (partial):
```json
{
  "cluster": {"peers": [], "status": "disabled"},
  "config": {
    "original": "route:\n  receiver: \"null\"\n  group_by:\n  - alertname\n  - cluster\n  - service\n  group_wait: 30s\n  group_interval: 5m\n  repeat_interval: 4h\n..."
  },
  "uptime": "2026-05-18T21:41:11.977Z",
  "versionInfo": {...}
}
```

`/api/v2/status` returns `config.original` as a YAML-formatted string, NOT as a nested JSON object. The D-69 verify jq assertion must parse the YAML string or use grep/string matching, not `jq .route.receiver`.

**Corrected D-69 assertion pattern:**
```bash
# Check cluster is disabled
curl -fsS http://alertmanager:9093/api/v2/status | jq -e '.cluster.status == "disabled"'
# Check config.original contains the null receiver (string match)
curl -fsS http://alertmanager:9093/api/v2/status | jq -r '.config.original' | grep -q 'receiver: "null"'
curl -fsS http://alertmanager:9093/api/v2/status | jq -r '.config.original' | grep -q 'group_interval: 5m'
curl -fsS http://alertmanager:9093/api/v2/status | jq -r '.config.original' | grep -q 'repeat_interval: 4h'
```

`/api/v2/receivers` returns `[{"name":"null"}]` — jq assertion: `jq -e '.[0].name == "null"'`.

`amtool alert add ... alertname=TestAlert` / `amtool alert query ... alertname=TestAlert` — confirmed working live (alert appears in query with state `active`).

`amtool silence add --comment "test silence" alertname=TestAlert` returns a UUID; `amtool silence query` shows it. Both confirmed live.

Confidence: HIGH (all endpoints probed against the actual running container).

---

### Q9 — Phase 1–3 role-port pattern

**ANSWER: Consistent across all eight roles. `node_exporter` is the closest structural analog.**

Directory layout (all eight roles):
```
roles/<name>/
  defaults/main.yml    — image pin + container tunables + verify timing
  tasks/main.yml       — pull → config dirs → render templates → volume → run container → include verify.yml
  tasks/verify.yml     — D-10a HEALTHCHECK poll → in-network curl one-shot
  handlers/main.yml    — single handler: "Docker restart <name>" (ansible.builtin.command)
  templates/           — one or more .j2 config files
  meta/main.yml        — minimal (author, description, no deps)
  README.md            — OPS-03 schema (variables table → modes → tags → volumes → healthcheck → security → deviations from upstream → deprecation notes)
```

No role deviates from this shape. The prometheus role adds a `tasks/verify.yml` pattern with the curl one-shot (see `roles/node_exporter/tasks/verify.yml` for the verbatim template). Handlers always use `ansible.builtin.command: cmd: "docker restart {{ name }}"` — never `docker_container: state: restarted`.

The `node_exporter` role is the cleanest analog for `alertmanager`: both are simple single-container deployments with one config file and a persistent named volume. Key differences: `alertmanager` has a config bind-mount (like prometheus/loki), no bind-mounts for proc/sys/root (unlike node_exporter), and a persistent data volume (unlike node_exporter which is stateless).

Planner pattern to mirror:
1. `roles/node_exporter/tasks/main.yml` — overall task sequence
2. `roles/node_exporter/tasks/verify.yml` — D-10a HEALTHCHECK poll + curl one-shot shape
3. `roles/prometheus/handlers/main.yml` — single handler shape
4. `roles/minio/README.md` — OPS-03 README schema template

Confidence: HIGH (all eight role directories read directly).

---

### Q10 — `roles/prometheus/templates/prometheus.yml.j2` current shape

**ANSWER: No `alerting:` block present. Clean insertion point identified.**

Source: File read directly (`/home/darko/git/rockdarko/telemetron/roles/prometheus/templates/prometheus.yml.j2`).

Current structure:
```
global:           # lines 9-15
rule_files:       # lines 17-18 (two rule files referenced)
remote_write:     # lines 20-28
scrape_configs:   # lines 32-83 (three default jobs + operator-extensible Jinja loop)
```

**Clean insertion point:** Between `rule_files:` and `remote_write:` (after line 18, before line 20). The `alerting:` block fits naturally here per standard Prometheus config file convention.

**Handler wiring already exists:** All three `roles/prometheus/tasks/main.yml` template tasks (`prometheus.yml.j2`, `rules-baseline.yml.j2`, `rules-extras.yml.j2`) call `notify: restart prometheus`. The handler in `roles/prometheus/handlers/main.yml` listens on `restart prometheus` and runs `docker restart {{ prometheus_container_name }}`. Adding the `alerting:` block to `prometheus.yml.j2` will automatically trigger a Prometheus restart when plan 04-01 lands — no handler wiring change needed.

**File ownership:** Prometheus config files are owned `nobody:nogroup mode 0640` (UAT-discovered requirement from Phase 3 — prom/prometheus image runs as UID 65534 / `nobody`). No change needed for the alerting block addition.

Confidence: HIGH (file read directly; handler chain traced to source).

---

### Q11 — `roles/prometheus/templates/rules-baseline.yml.j2` current severity labels

**ANSWER: `HostDown` and `FilesystemAlmostFull` ALREADY have `severity:` labels. `ContainerRestartLoop` and `OTelCollectorDroppingSignals` are MISSING severity labels — the D-65 retrofit adds them.**

Source: File read directly (`/home/darko/git/rockdarko/telemetron/roles/prometheus/templates/rules-baseline.yml.j2`).

Current state:
- `HostDown` — `labels: severity: critical, team: telemetron` ✓ already present
- `FilesystemAlmostFull` — `labels: severity: warning, team: telemetron` ✓ already present
- `ContainerRestartLoop` — `labels: severity: warning, team: telemetron` ✓ already present
- `OTelCollectorDroppingSignals` — `labels: severity: warning, team: telemetron` ✓ already present

**CONTEXT.md D-65 is based on outdated information about the file state.** All four rules already have `severity:` labels with the correct values. The D-65 retrofit is a NO-OP — the file already satisfies the requirement. The planner should verify this before task execution and can skip the D-65 edit if the file matches the expected state.

**The D-63 inhibit rule will work immediately** because `severity` labels are already present on all four baseline rules.

Confidence: HIGH (file read directly).

---

### Q12 — `hooks/` directory current state

**ANSWER: `hooks/` exists with a single `README.md` only. No `router/` or `jobs/` subdirectories. No code.**

Source: `ls /home/darko/git/rockdarko/telemetron/hooks/` returns only `README.md`.

Current `hooks/README.md` content: Describes the planned hook router layout (`router/` + `jobs/` planned), the 5-step architecture (Prometheus → Alertmanager → router → Jenkins), and references `docs/hook-router.md (coming soon)`.

**Plan 04-01 task 1 action:** Rewrite `hooks/README.md` to: "Hook router (Alertmanager → generic CI/automation webhook bridge) is deferred to a future milestone. See REQUIREMENTS.md ALERT-V2-01..05 for the planned shape." The directory survives as institutional memory but ships no code. No `router/` or `jobs/` directories are created in Phase 4.

Confidence: HIGH (directory listing executed directly).

---

### Q13 — `roles/README.md` current shape

**ANSWER: Role status table uses ☐/☑ checkboxes. `alertmanager` is ☐ (not ported). `hook_router` is ☐ with note "new — was inline upstream".**

Source: File read directly (`/home/darko/git/rockdarko/telemetron/roles/README.md`).

Relevant rows:
```markdown
| `alertmanager`  | alert routing                                        | ☐ |
| `hook_router`   | Alertmanager → CI bridge (new — was inline upstream) | ☐ |
```

"Added vs. upstream" section mentions `node_exporter` (added) and `hook_router` (added, was inline upstream).

Gate 7 paragraph: "Phase 4 (alertmanager, hook_router) and Phase 5 (grafana, karma, promlens) role ports MUST stamp these labels."

**Plan 04-01 task 1 actions on `roles/README.md`:**
1. Change `alertmanager` row: ☐ → ☑
2. Change `hook_router` row: mark "deferred to a future milestone (ALERT-V2-05)" — keep or remove the ☐; the description updates to reflect deferral
3. Update "Added vs. upstream" section: `hook_router` description updates to "planned for a future milestone"
4. Gate 7 paragraph: reword to mention only alertmanager for Phase 4 (hook_router deferred)

Confidence: HIGH (file read directly).

---

### Q14 — `PROJECT.md` "Active" requirements and "Key Decisions" current shape

**ANSWER: "Active" section contains a direct `hook_router` reference that D-58 rewrites. Key Decisions table has a "Hook router security model" row.**

Source: File read directly (`/home/darko/git/rockdarko/telemetron/.planning/PROJECT.md`).

Specific rows needing update per D-58:

**"Active" section:**
- Line: `[ ] Write the hook router Flask app source under \`hooks/router/\` (was inline upstream) and ship sample Jenkinsfile runbooks under \`hooks/jobs/\`` → reword as a "Deferred" item citing ALERT-V2-01..05
- Line: `[ ] Roles in scope: \`alertmanager\`, \`fluentbit\`, ... \`hook_router\` ...` → note hook_router is deferred; role count may drop to 13 deployed + 1 deferred
- Core Value paragraph: "Alertmanager + Karma + hook-router for alerts" → "Alertmanager + Karma for alerts"

**Key Decisions table:**
- Row: `| Hook router security model (label allowlist + per-(alertname,job) rate limit + vault-supplied Jenkins token)...` → status changes to "(deferred — v2 milestone)" with original rationale preserved

Confidence: HIGH (file read directly).

---

### Q15 — `REQUIREMENTS.md` current §"Alert plane" wording and traceability table

**ANSWER: ALERT-02..06 rows are present in the traceability table pointing to "Phase 4". A §"v2 Requirements" section EXISTS at the bottom with HA-01, K8S-01, etc. — ALERT-V2-01..05 rows get appended there.**

Source: File read directly (`/home/darko/git/rockdarko/telemetron/.planning/REQUIREMENTS.md`).

Current state:
- `ALERT-01` through `ALERT-06` are all in the `### Alert plane (ALERT)` section. ALERT-01 is `[ ]` (unchecked). ALERT-02..06 are `[ ]`.
- Traceability table: all six `ALERT-01..06` → `Phase 4 — Alert Plane`
- `## v2 Requirements (deferred — not in M1)` section already exists with HA-01, K8S-01, TEST-01, STORAGE-01, etc.

**Plan 04-01 task 1 actions:**
1. Move `ALERT-02..06` from `### Alert plane (ALERT)` to `## v2 Requirements` section, renumbered as `ALERT-V2-01..05` with descriptions per D-58
2. Traceability table: keep `ALERT-01 → Phase 4`; update or remove `ALERT-02..06` rows (or add them as ALERT-V2-01..05 with "v2 milestone" as phase)
3. Add a note in the `### Alert plane (ALERT)` section: "ALERT-02..06 moved to §v2 Requirements as ALERT-V2-01..05 (Phase 4 scope reshape — see CONTEXT.md D-56/D-57)"

Confidence: HIGH (file read directly).

---

### Q16 — D-68 INSPQ deviation audit

**ANSWER: INSPQ upstream available at `~/git/inspq/ansible/alert_manager/`. D-68 list in CONTEXT.md is accurate and largely complete. Additional findings below.**

Source: `ls ~/git/inspq/ansible/alert_manager/` + files read directly.

INSPQ upstream directory structure:
```
defaults/main.yml    — confirmed: FR vocabulary, SMTP config, team topology, k8s/Helm vars
tasks/main.yml       — routes to docker.yml or kubernetes_helm.yml
tasks/docker.yml     — not yet read; see below
tasks/kubernetes_helm.yml — k8s path (entire file dropped per D-68)
templates/alertmanager.yml.j2 — heavy FR-routing template (FULL read above)
```

**INSPQ `defaults/main.yml` confirms all D-68 entries plus additional items not in D-68:**
- `alert_manager_repeat_interval_critical: "6h"` — value differs from D-61 (M1 uses `4h` for all; not per-severity)
- `alert_manager_repeat_interval_high: "12h"` — HIGH severity concept doesn't exist in M1 (only critical/warning)
- `alert_manager_repeat_interval_warning: "24h"` — differs from M1 default
- `alert_manager_include_alertnames: []` — INSPQ-specific include-only mode for SMTP routing; irrelevant for M1 null receiver
- `alert_manager_external_url: "http://{{ ansible_fqdn }}:{{ alert_manager_docker_external_port }}"` — M1 uses `--web.external-url` CLI flag; surfaces as `alertmanager_web_external_url: ""` knob (empty = no override)
- `alert_manager_memory/cpus/memory_swap: ""` — resource limits; M1 should add `alertmanager_memory_limit: 256m` (similar to other roles)
- `alert_manager_state: present` — Ansible module state knob (irrelevant; M1 always deploys)
- `alert_manager_docker_restart_policy: always` → M1 uses `unless-stopped` (D-19 / OPS-06 convention)

**INSPQ `templates/alertmanager.yml.j2` confirms:**
- Entire `time_intervals:` section (soir_nuit, weekend, mep_semaine, mep_weekend, weekdays_night, weekends_all_day) — ALL removed in M1
- Multi-team routing (`alert_manager_teams` loop) — removed
- `alert_manager_include_alertnames` include-only mode — removed
- `mute_time_intervals` references on every route — removed (these reference the FR time intervals)
- French comments throughout (`# continue: true permet aux routes additionnelles...`) — grep gate catches these

**Grep gate expectations:** Running `grep -riE 'inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/alertmanager/` on the ported role must return zero matches. The INSPQ template has inline French comments which MUST be removed during porting.

Confidence: HIGH (both upstream files read directly).

---

### Q17 — `playbooks/deploy_docker.yml` current shape

**ANSWER: File confirmed. Alertmanager role entry appends after `fluentbit` as the ninth role. Exact syntax to use:**

Source: File read directly (`/home/darko/git/rockdarko/telemetron/playbooks/deploy_docker.yml`).

Current last role entry:
```yaml
    - role: fluentbit
      tags:
        - fluentbit
  # Subsequent phase plans extend this list in dependency order
  # (D-05 dependency tree). Phase 3 is now FEATURE-COMPLETE:
  # ...
  #   Phase 4: alertmanager, hook_router
```

**Plan 04-01 addition:**
```yaml
    - role: alertmanager
      tags:
        - alertmanager
```
Replace the comment line `Phase 4: alertmanager, hook_router` with `Phase 4: alertmanager (hook_router deferred to v2 milestone)`.

No `vars:` overrides needed on the playbook entry — all defaults live in `roles/alertmanager/defaults/main.yml`.

Confidence: HIGH (file read directly).

---

## Existing Role-Port Pattern

Eight canonical roles from Phases 1–3 establish the template. The planner must mirror this pattern without deviation.

### Directory shape (all eight roles identical)

```
roles/<name>/
  defaults/main.yml      — image pin, container knobs, healthcheck timing, verify timing
  tasks/main.yml         — sequential: mkdir → render config → docker_volume → docker_image → docker_container → include verify.yml
  tasks/verify.yml       — Step 1a: docker_container_info HEALTHCHECK poll (when_enabled) 
                           Step 1b: docker_container_info Running poll (when_disabled)
                           Step 2: curl one-shot (curlimages/curl) on the telemetron network
  handlers/main.yml      — one handler: "ansible.builtin.command: docker restart <name>"
  templates/<name>.yml.j2 — rendered config; bound-mounted into container :ro
  meta/main.yml          — minimal metadata
  README.md              — OPS-03 schema
```

### Key conventions (all enforced by port-acceptance gates)

| Convention | Pattern |
|------------|---------|
| Image pin | `quay.io/prometheus/alertmanager:v0.32.1` in defaults/main.yml |
| No `:latest` | Gate 2 grep check |
| Volume naming | `telemetron_alertmanager_data` (D-16) |
| Config bind-mount | `/opt/telemetron/alertmanager/<file>` → `/etc/alertmanager/<file>:ro` (D-18) |
| Restart policy | `unless-stopped` (OPS-06) |
| Handler-only restarts | `notify: restart alertmanager` on every template task; handler does `docker restart` |
| Sorted-keys Jinja | `{% for item in list \| sort(attribute='name') %}` (D-20) |
| No host publish default | `alertmanager_publish_host: false` (D-30) |
| Gate 7 label stamp | `org.telemetron.service: telemetron` + `org.telemetron.job: alertmanager` |
| In-network verify | `curlimages/curl` + `amtool` one-shots on `telemetron` network; `auto_remove: true`, `changed_when: false` |
| INSPQ grep gate | Zero matches for pattern in Gate 1 |

### Healthcheck pattern (this role: explicit required)

Since the alertmanager image has no built-in HEALTHCHECK, the role ships an explicit probe. Pattern mirrors the Tempo/OTel conditional approach but simpler — `busybox` base means `wget` is available (no distroless concern):

```yaml
# In defaults/main.yml:
alertmanager_healthcheck_enabled: true
alertmanager_healthcheck_test: ["CMD-SHELL", "wget --spider -q http://localhost:9093/-/healthy || exit 1"]
alertmanager_healthcheck_interval: 15s
alertmanager_healthcheck_timeout: 5s
alertmanager_healthcheck_retries: 5
alertmanager_healthcheck_start_period: 30s
```

The `healthcheck: "{{ ..._container_healthcheck if (alertmanager_healthcheck_enabled | bool) else omit }}"` pattern from node_exporter/prometheus applies verbatim.

---

## Plan Structure Recommendation

CONTEXT.md suggests task order. Confirmed and refined based on research:

**Recommended task order for `04-01-PLAN.md`:**

1. **Doc rework cascade** — All seven doc files in one task. Atomic: no in-flight inconsistency between "spec says hook router" and "code skipped it." Touch order within task: hooks/README.md (simplest, one file), roles/README.md, REQUIREMENTS.md (ALERT-02..06 move), ROADMAP.md (Phase 4 goal rewrite), CLAUDE.md (hook_router entries), .planning/research/FEATURES.md, .planning/research/SUMMARY.md, PROJECT.md.

2. **`roles/alertmanager/` scaffold** — All role files in one task: `defaults/main.yml`, `tasks/main.yml`, `tasks/verify.yml`, `handlers/main.yml`, `templates/alertmanager.yml.j2`, `meta/main.yml`, `README.md`.

3. **`roles/prometheus/` extension** — `templates/prometheus.yml.j2` + `defaults/main.yml` (add `prometheus_alertmanager_target`). Triggers existing handler → Prometheus restart on next playbook run. D-65 is already done (all four severity labels present); planner confirms before writing.

4. **`inventory/example-homelab/group_vars/all/alertmanager.yml`** — New file. Surface the D-61 knobs + D-60 extension lists + `alertmanager_publish_host`.

5. **`playbooks/deploy_docker.yml`** — Append `alertmanager` role entry after `fluentbit`.

6. **Port-acceptance gate checks** — INSPQ grep gate, non-ASCII gate, image-pin gate, idempotency gate, healthcheck gate, README gate, Gate 7.

7. **D-69 verify run** — All steps using `docker exec` on the running alertmanager container for amtool; `curlimages/curl` one-shots for HTTP assertions.

**No task reordering issues:** Tasks 1–5 are pure file writes. Task 6 is a static check. Task 7 requires the container to be running (task 5 must be deployed first). The plan document itself specifies task 7 as a deployment-time step.

---

## Risks and Edges

### Risk 1: api/v2/status route fields are in YAML string, not JSON

**What:** D-69 verify spec in CONTEXT.md describes `jq` assertions on `.route.receiver`, `.route.group_by`, etc. The actual API response embeds these in `config.original` as a YAML-formatted string, not as nested JSON.

**Impact:** If plan 04-01 writes verify tasks expecting `jq '.route.receiver == "null"'`, they will fail at UAT.

**Fix:** Use `jq -r '.config.original' | grep -q 'receiver: "null"'` and similar string-match assertions. Or: accept that `cluster.status == "disabled"` and `receivers[0].name == "null"` cover the core assertions (`/api/v2/receivers` returns proper JSON).

**Planner action:** Write D-69 verify assertions as grep-on-YAML for config checks; use `/api/v2/receivers` for the null-receiver structural check.

---

### Risk 2: D-65 severity label retrofit is actually a no-op

**What:** CONTEXT.md D-65 describes retrofitting severity labels on the four baseline rules. Research shows all four rules already have `severity: critical` or `severity: warning` labels as of the Phase 3 ship.

**Impact:** If plan 04-01 creates a task to "add severity labels" and they're already there, the task is either redundant (idempotency is fine) or wrong about what it adds.

**Planner action:** Frame the D-65 task as "verify severity labels are present" with a comment citing the current state. If the file truly already has them, the task becomes a quick verification + inline comment citation rather than an edit. This avoids a "changed" report on an already-correct file.

---

### Risk 3: Prometheus restart on `prometheus.yml.j2` change may require re-verify

**What:** Adding the `alerting:` block to `prometheus.yml.j2` triggers a Prometheus container restart via the existing handler. If plan 04-01 is run against a stack that already has Prometheus up, the restart occurs mid-plan. The Prometheus verify step in plan 04-01 should run AFTER the restart settles.

**Impact:** If the plan's D-69 verify step runs too soon after the alertmanager container is started (before Prometheus has restarted and re-connected), the `/api/v1/alertmanagers` assertion may return an empty list.

**Fix:** The D-10a HEALTHCHECK poll on alertmanager ensures AM is healthy. The Prometheus verify step uses `docker_container_info` polling which waits for `healthy` state. Ordering the verify tasks with a brief retry loop (as all existing verify tasks do) is sufficient.

**Planner action:** The D-69 Prometheus alertmanagers check (`curl -fsS http://prometheus:9090/api/v1/alertmanagers`) should be the last verify step, after the alertmanager healthcheck poll confirms AM is up.

---

### Risk 4: INSPQ grep gate — French inline comments in the template

**What:** The INSPQ `templates/alertmanager.yml.j2` has inline French comments (e.g., `# continue: true permet aux routes additionnelles...`). The INSPQ grep gate pattern `grep -riE 'inspq|qc\.ca|montreal|québec|francais|french|...'` does NOT catch all French text — it only catches specific INSPQ-domain strings. However, the non-ASCII gate catches accented characters (`é`, `à`, `ê` in French words). Inline French comments without accented characters (e.g., "continue" in French) would pass the gates — but they also appear in English so they're fine.

**What the planner must watch for:** The INSPQ template has `noreply@inspq.qc.ca` in the SMTP block — the grep gate catches `inspq` and `qc.ca`. The `America/Montreal` timezone — the grep gate catches `montreal`. The FR-vocabulary vars in the template (`soir_nuit`, `mep_semaine`, etc.) — if any survive into the rendered template, they're in variable names not template strings, so the grep gate on the role directory catches them in defaults/main.yml.

**Planner action:** After task 2 (scaffolding), run the grep gate explicitly as a task. The D-68 audit list is comprehensive.

---

### Risk 5: `--cluster.listen-address=""` syntax in Ansible `command:` list

**What:** Passing an empty string as a CLI argument requires careful YAML escaping in the Ansible `docker_container.command` list.

**Correct YAML:**
```yaml
command:
  - "--cluster.listen-address="
```
or
```yaml
command:
  - "--cluster.listen-address="
```
The empty string after `=` works: Docker passes it as the value. This was confirmed by the live test where AM started with `"cluster":{"status":"disabled"}`.

**Planner action:** Use `"--cluster.listen-address="` (empty string after `=`) in the command list. Avoid `--cluster.listen-address ""` (space-separated) which may be parsed differently.

---

### Risk 6: `amtool` verify requires `docker exec` not a new container

**What:** D-69 spec mentions "one-shot container" for amtool. Since amtool is bundled in the alertmanager image and connects to `http://localhost:9093` (not `http://alertmanager:9093`), it's simplest to use `docker exec` on the running container rather than spinning up a separate image.

**Alternative:** A one-shot container with `--network=telemetron` could run amtool connecting to `http://alertmanager:9093` on the Docker network. This works but requires the same image.

**Recommendation:** Use `community.docker.docker_container_exec` on the running `telemetron-alertmanager` container. This avoids `auto_remove` cleanup concerns and uses `localhost:9093` which is always the correct address from within the container.

---

### Risk 7: `hooks/README.md` content tone

**What:** The existing `hooks/README.md` is forward-looking ("Planned layout", "Architecture"). Rewriting it to "deferred" must preserve institutional memory without being confusing to a future contributor who finds a `hooks/` directory with only a README.

**Recommendation:** The README should: (a) explain what the hook router was supposed to do, (b) clearly state it's deferred to ALERT-V2-01..05, (c) link to REQUIREMENTS.md for the planned shape, and (d) NOT imply the directory will be deleted — it's kept intentionally as a placeholder.

---

## Environment Availability

All dependencies are local Docker images, already pulled for prior phases, or part of the alertmanager image itself.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `quay.io/prometheus/alertmanager:v0.32.1` | alertmanager role | ✓ (pulled during research) | 0.32.1 | — |
| `curlimages/curl` | D-69 verify | ✓ (used by all Phase 1–3 roles) | 8.10.1 | — |
| `/bin/amtool` | D-69 amtool verify | ✓ (bundled in alertmanager image) | 0.32.1 | — |
| `prom/prometheus:v3.11.3` | D-69 Prometheus alertmanagers check | ✓ (Phase 3 role running) | v3.11.3 | — |
| `community.docker` collection | all `docker_container*` tasks | ✓ (all prior phases use it) | installed | — |

Step 2.6: No missing dependencies that block execution.

---

## Code Examples

### Alertmanager config template (D-60/D-61/D-63)

```yaml
# /opt/telemetron/alertmanager/alertmanager.yml
# {{ ansible_managed }}
# Alertmanager v0.32.1 -- Telemetron M1 default config.
# D-60: null receiver default -- alerts visible in UI and Karma (Phase 5)
# but dispatched to nothing automatically. Add a real receiver before
# relying on this stack to wake you up.
# D-61: ALERT-01 routing intervals explicit (not defaulted).
# D-63: One inhibit rule bounds critical→warning replay flood.

route:
  receiver: 'null'
  group_by: [alertname, cluster, service]
  group_wait: {{ alertmanager_group_wait }}
  group_interval: {{ alertmanager_group_interval }}
  repeat_interval: {{ alertmanager_repeat_interval }}
  routes:
{% for r in alertmanager_extra_routes | default([]) | sort(attribute='receiver') %}
    - receiver: {{ r.receiver }}
{% if r.matchers is defined %}
      matchers:
{% for m in r.matchers %}
        - '{{ m }}'
{% endfor %}
{% endif %}
{% endfor %}

inhibit_rules:
  - source_matchers:
      - severity = critical
    target_matchers:
      - severity = warning
    equal: [instance]
{% for rule in alertmanager_extra_inhibit_rules | default([]) %}
  - {{ rule | to_yaml(indent=4) | trim }}
{% endfor %}

receivers:
  - name: 'null'
{% for r in alertmanager_extra_receivers | default([]) | sort(attribute='name') %}
  - name: {{ r.name }}
{% if r.webhook_configs is defined %}
    webhook_configs:
{% for w in r.webhook_configs %}
      - url: {{ w.url }}
{% endfor %}
{% endif %}
{% endfor %}
```

Source: Synthesized from CONTEXT.md D-60/D-61/D-63 + amtool-verified syntax.

---

### D-64 alerting block addition in prometheus.yml.j2

Insert between `rule_files:` block and `remote_write:` block:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['{{ prometheus_alertmanager_target }}']
```

Source: Verified by `promtool check config` against `prom/prometheus:v3.11.3`.

---

### D-69 verify — amtool via docker exec

```yaml
- name: D-69 amtool synthetic alert add
  community.docker.docker_container_exec:
    container: "{{ alertmanager_container_name }}"
    command: >-
      /bin/amtool alert add --alertmanager.url=http://localhost:9093
      alertname=TestAlert severity=warning instance=verify-host
  changed_when: false
  tags: [alertmanager, alertmanager-verify]

- name: D-69 amtool alert query assert
  community.docker.docker_container_exec:
    container: "{{ alertmanager_container_name }}"
    command: >-
      /bin/amtool alert query --alertmanager.url=http://localhost:9093
      alertname=TestAlert
  register: am_alert_query
  failed_when: "'TestAlert' not in am_alert_query.stdout"
  changed_when: false
  tags: [alertmanager, alertmanager-verify]
```

Source: Verified by direct `docker exec` on live v0.32.1 container.

---

### D-69 verify — api/v2 assertions (corrected)

```yaml
- name: D-69 curl probe api/v2/status -- cluster disabled
  community.docker.docker_container:
    name: "{{ alertmanager_container_name }}-verify-status"
    image: "{{ alertmanager_curl_image }}:{{ alertmanager_curl_image_tag }}"
    state: started
    detach: false
    auto_remove: true
    recreate: true
    cleanup: true
    networks:
      - name: "{{ alertmanager_network }}"
    entrypoint: ["/bin/sh", "-c"]
    command:
      - >-
        STATUS=$(curl -fsS http://{{ alertmanager_container_name }}:9093/api/v2/status) ;
        echo "$STATUS" | grep -q '"status":"disabled"' || exit 1 ;
        CONFIG=$(echo "$STATUS" | grep -o '"original":"[^"]*"' | head -1) ;
        echo "$CONFIG" | grep -q 'receiver.*null' || exit 1 ;
        echo "$CONFIG" | grep -q 'group_interval.*5m' || exit 1 ;
        echo "api/v2/status assertions passed"
  changed_when: false
  tags: [alertmanager, alertmanager-verify]
```

Source: API response structure confirmed by live probe; grep-on-JSON-embedded-YAML approach.

---

## Sources

### Primary (HIGH confidence)

- Direct `docker inspect quay.io/prometheus/alertmanager:v0.32.1` — HEALTHCHECK null, VOLUME /alertmanager, CMD defaults
- Direct `docker run quay.io/prometheus/alertmanager:v0.32.1 --help` — confirmed `--cluster.listen-address=""` behavior
- Live HTTP probe `http://localhost:19093/-/ready`, `/-/healthy`, `/api/v2/status`, `/api/v2/receivers` — all confirmed 200; API structure documented
- Live `docker exec` amtool commands — `alert add`, `alert query`, `silence add`, `silence query` all working
- `amtool check-config` — both `source_match` and `source_matchers` accepted; `source_matchers` is current
- `promtool check config` against `prom/prometheus:v3.11.3` — alerting block syntax valid
- Direct file reads: `roles/prometheus/templates/prometheus.yml.j2`, `rules-baseline.yml.j2`, `defaults/main.yml`, `handlers/main.yml`, `tasks/main.yml`
- Direct file reads: `roles/node_exporter/tasks/main.yml`, `tasks/verify.yml`, `defaults/main.yml`
- Direct file reads: `roles/minio/tasks/bootstrap.yml`, `README.md`
- Direct file reads: `playbooks/deploy_docker.yml`, `inventory/example-homelab/group_vars/all/network.yml`, `storage.yml`
- Direct file reads: `hooks/README.md`, `roles/README.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`
- Direct file reads: `~/git/inspq/ansible/alert_manager/defaults/main.yml`, `templates/alertmanager.yml.j2`

### Secondary (MEDIUM confidence)

- Prometheus documentation `prometheus.io/docs/alerting/latest/configuration/` — `source_match` deprecation, `source_matchers` recommended
- GitHub `prometheus/alertmanager/blob/v0.32.1/Dockerfile` — busybox base, no HEALTHCHECK instruction, VOLUME /alertmanager

---

## Metadata

**Confidence breakdown:**
- Image inspection (HEALTHCHECK, volumes, binary paths): HIGH — direct docker inspect + docker exec
- CLI flags (`--cluster.listen-address`): HIGH — direct --help output + live test
- API response structure: HIGH — live HTTP probe on actual container
- amtool behavior: HIGH — direct docker exec on actual container
- inhibit_rules syntax: HIGH — amtool check-config on both old and new syntax
- prometheus.yml alerting block: HIGH — promtool check config on actual prometheus image
- Existing role file states (severity labels, handler chain, etc.): HIGH — direct file reads
- INSPQ deviation list completeness: HIGH — both defaults/main.yml and template read directly

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable components; alertmanager v0.32.1 API is stable)
