---
plan: 03-04-fluentbit
phase: 03-ingest-plane
type: execute
wave: 4
depends_on: [03-02-opentelemetry]
requirements: [INGEST-06, INGEST-07]
files_modified:
  - roles/fluentbit/defaults/main.yml
  - roles/fluentbit/tasks/main.yml
  - roles/fluentbit/tasks/verify.yml
  - roles/fluentbit/handlers/main.yml
  - roles/fluentbit/meta/main.yml
  - roles/fluentbit/templates/fluent-bit.conf.j2
  - roles/fluentbit/templates/parsers.conf.j2
  - roles/fluentbit/README.md
  - inventory/example-homelab/group_vars/all/fluentbit.yml
  - playbooks/deploy_docker.yml
  - roles/README.md
autonomous: true

must_haves:
  truths:
    - "In-network curl to http://fluentbit:2020/api/v1/health returns 200 (ROADMAP SC1 + INGEST-06 health gate)."
    - "FB tails `/var/lib/docker/containers/*/*-json.log` by default with the `docker` JSON parser (D-46 role inversion vs INSPQ)."
    - "Rendered fluent-bit.conf contains `Time_System_Timezone Etc/UTC` (Pitfall 6 single-most-impactful one-liner; D-50)."
    - "Rendered fluent-bit.conf contains `Multiline_Flush 5` (Pitfall 6 fail-fast aggregation bound; D-50)."
    - "Rendered fluent-bit.conf contains `Read_from_Head false` (D-50 -- don't replay pre-deploy logs on first boot)."
    - "Rendered fluent-bit.conf contains a fallback `@timestamp` modify filter (Pitfall 6 mode 2 mitigation; D-50)."
    - "Rendered fluent-bit.conf has `storage.type filesystem` plus `storage.path /var/log/flb-storage/` plus `storage.max_chunks_up 128` (D-50)."
    - "FB ships to `opentelemetry` output at `http://otel:4318/v1/logs` (D-49; via Plan 03-02's OTel)."
    - "FB→Loki direct path documented as alternative in README per INGEST-06."
    - "Container has bind-mount `telemetron_fluentbit_buffer` named volume at /var/log/flb-storage/ (D-50 + Phase-1 D-16)."
    - "Container has bind-mount `/var/lib/docker/containers` host -> container RO (so FB can tail Docker JSON logs)."
    - "D-47 allowlist label set `{job, host, service, env, level}` rendered in filter chain."
    - "D-48 extension knobs (`fluentbit_tail_system_logs`, `fluentbit_tail_journald`, `fluentbit_extra_tail_paths`) all default-off and conditionally rendered."
    - "Re-running the playbook reports `changed=0` for the fluentbit tag (OPS-04)."
    - "All six per-role port-acceptance gates pass on `roles/fluentbit/`."
  artifacts:
    - path: roles/fluentbit/defaults/main.yml
      provides: "Image pin fluent/fluent-bit:4.2.3, port :2020 (HTTP server), no-host-publish default, telemetron_fluentbit_buffer volume reference, conditional HEALTHCHECK pattern, D-47 label allowlist knobs, D-48 extension flags."
      contains: "4.2.3"
    - path: roles/fluentbit/templates/fluent-bit.conf.j2
      provides: "Rendered FB config: [SERVICE] with Time_System_Timezone Etc/UTC + storage.type filesystem + Multiline_Flush 5, [INPUT] tail Docker JSON logs + conditional extension inputs (D-48), [FILTER] modify/parser/grep allowlist chain (D-47), [OUTPUT] opentelemetry to otel:4318/v1/logs (D-49) + fallback @timestamp filter."
      contains: "Time_System_Timezone Etc/UTC"
    - path: roles/fluentbit/templates/parsers.conf.j2
      provides: "docker JSON parser + level_extractor regex parser (D-47 level extraction from log content)."
      contains: "level_extractor"
    - path: roles/fluentbit/tasks/main.yml
      provides: "Bootstrap: ensure config dir, render two templates (notify), ensure telemetron_fluentbit_buffer volume, pull image, run container with /var/lib/docker/containers RO + buffer-volume + conditional HEALTHCHECK, include verify.yml."
      contains: "include_tasks: verify.yml"
    - path: roles/fluentbit/tasks/verify.yml
      provides: "D-10a poll + curl :2020/api/v1/health 200 assertion."
      contains: "/api/v1/health"
    - path: roles/fluentbit/handlers/main.yml
      provides: "Single restart handler (W6) via docker restart."
      contains: "Docker restart fluentbit"
    - path: roles/fluentbit/README.md
      provides: "OPS-03 schema + D-46 role-inversion explanation + D-47 label allowlist + D-48 extension knobs + D-49 OTel transport rationale + D-50 buffer/timezone rationale + 'Labeling operator apps' section + FB->Loki direct alternative + D-25 audit."
      contains: "## Labeling operator apps"
    - path: inventory/example-homelab/group_vars/all/fluentbit.yml
      provides: "Operator knobs: fluentbit_publish_host: false, fluentbit_tail_system_logs/journald/extra_tail_paths default-off, fluentbit_env, fluentbit_buffer_volume."
      contains: "fluentbit_extra_tail_paths"
    - path: playbooks/deploy_docker.yml
      provides: "fluentbit role wired after prometheus."
      contains: "role: fluentbit"
  key_links:
    - from: "roles/fluentbit/templates/fluent-bit.conf.j2 [INPUT] tail"
      to: "/var/lib/docker/containers/*/*-json.log"
      via: "Bind-mount host /var/lib/docker/containers -> container RO + Path glob"
      pattern: "/var/lib/docker/containers/\\*/\\*-json\\.log"
    - from: "roles/fluentbit/templates/fluent-bit.conf.j2 [OUTPUT] opentelemetry"
      to: "http://otel:4318/v1/logs"
      via: "D-49 -- opentelemetry output plugin; OTLP/HTTP wire format"
      pattern: "(Host\\s+otel|otel:4318|/v1/logs)"
    - from: "roles/fluentbit/templates/fluent-bit.conf.j2 storage block"
      to: "telemetron_fluentbit_buffer named volume"
      via: "storage.path /var/log/flb-storage/ bind-mounted by tasks/main.yml"
      pattern: "storage.type\\s+filesystem"
    - from: "Pitfall 6 mitigation (the single biggest D-25 improvement for FB)"
      to: "Time_System_Timezone Etc/UTC + Multiline_Flush 5 + Read_from_Head false + fallback @timestamp"
      via: "all four explicit in [SERVICE] and [FILTER] modify blocks"
      pattern: "(Etc/UTC|Multiline_Flush\\s+5|Read_from_Head\\s+false)"
---

<objective>
Port the `fluentbit` role into `roles/fluentbit/` mirroring the Phase-2 canonical role-template layout. Carries INGEST-06 (FB tails Docker container logs by default per D-46 role inversion, ships through OTel via D-49 `opentelemetry` output plugin, applies D-47 label allowlist + D-50 buffer/timezone discipline). Pitfall 6 mitigation pack is the load-bearing D-25 improvement for this role.

Purpose: deliver INGEST-06 (FB tailing Docker container logs through OTel to Loki + Time_System_Timezone Etc/UTC + Multiline_Flush 5). Establishes the FB role-inversion vs upstream INSPQ (homelab single-host colocated FB-with-workloads pattern documented in user memory `project_fluentbit_role_shift.md`).

Output: full canonical role layout under `roles/fluentbit/` plus two Jinja templates (fluent-bit.conf + parsers.conf) plus inventory file plus playbook wiring plus roles/README.md status row tick. All six port-acceptance gates pass.
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
@.planning/research/PITFALLS.md
@CLAUDE.md
@roles/README.md
@roles/mimir/defaults/main.yml
@roles/mimir/tasks/main.yml
@roles/mimir/tasks/verify.yml
@roles/mimir/handlers/main.yml
@roles/mimir/meta/main.yml
@inventory/example-homelab/group_vars/all/network.yml
@inventory/example-homelab/group_vars/all/storage.yml
@inventory/example-homelab/group_vars/all/mimir.yml
@playbooks/deploy_docker.yml
@.planning/phases/03-ingest-plane/03-02-opentelemetry-PLAN.md

<interfaces>
<!-- Plan 03-02 wired OTel; FB ships through it. -->

From Plan 03-02 (opentelemetry):
- OTel OTLP HTTP endpoint: http://otel:4318/v1/logs (the FB -> OTel ship target per D-49)

From Phase-1 D-16:
- Named volume `telemetron_fluentbit_buffer` already DECLARED in `inventory/example-homelab/group_vars/all/storage.yml` semantics (Phase-1 reserved the name in the volume-prefix scheme); this plan ACTUALLY CREATES the Docker volume + mounts it at /var/log/flb-storage/ in the FB container.

D-46: FB default tail path = `/var/lib/docker/containers/*/*-json.log` (Docker JSON file driver default location). Parsed with FB's built-in `docker` JSON parser. ROLE INVERSION vs INSPQ (memory: project_fluentbit_role_shift.md) -- this MUST be documented in README's D-25 section.

D-47 label allowlist (Loki labels FB ships):
- `host` -- statically `{{ ansible_hostname }}` (set at deploy time via Jinja in fluent-bit.conf.j2; FB sees this as a literal).
- `env` -- `{{ telemetron_env | default('homelab') }}` at deploy time.
- `service` -- container_name (extracted from file path; fallback when no Docker label).
- `job` -- container_name (same fallback as service).
- `level` -- extracted from log line via regex `(?i)\b(INFO|WARN|ERROR|FATAL|DEBUG|TRACE)\b`; default `info`.
- HIGH-CARDINALITY FIELDS (container_id, image_id, image_name, full image tag) -> Loki structured metadata, NOT labels. This is the source-side Pitfall 4 mitigation.

NB: per RESEARCH Open Question Q3, FB 4.2 tail input does NOT enrich records with container Docker labels at tail time. The role ships the simpler fallback (container_name as job/service) and documents Docker-label-based labeling as a deferred opt-in (Lua filter or v2 enhancement).

D-48 extension knobs (all default-off):
- `fluentbit_tail_system_logs: false` -- conditionally adds an [INPUT] tail for /var/log/{syslog,auth.log,kern.log,messages}.
- `fluentbit_tail_journald: false` -- conditionally adds an [INPUT] systemd for /run/log/journal (requires Linux-with-systemd; bind-mount /run/systemd/journal/socket).
- `fluentbit_extra_tail_paths: []` -- list of paths; each entry emits one [INPUT] tail section. Preserves upstream-INSPQ legacy-host-scoop use case without making it the default.

D-49: ship via `opentelemetry` output plugin to `http://otel:4318/v1/logs`. NOT `loki` direct.

D-50 buffer + timestamp discipline (THE Pitfall 6 mitigation pack):
- `storage.type filesystem` in [SERVICE] and per-INPUT.
- `storage.path /var/log/flb-storage/` (mounted as the named volume `telemetron_fluentbit_buffer`).
- `storage.max_chunks_up 128` (homelab-sized in-flight chunk window).
- `Time_System_Timezone Etc/UTC` -- single most impactful Pitfall 6 mitigation.
- `Multiline_Flush 5` -- fail-fast aggregation bound.
- `Read_from_Head false` (per-INPUT).
- `[FILTER] modify` with `Add @timestamp ${ingest_time}` (only adds when key missing; Pitfall 6 mode 2 fallback).

INSPQ Deviation Audit (D-25) -- entries that MUST appear in README:
- Dropped: `:latest` tag; K8s helm branches; French task names ("gérer les mount points...", "S'assurer que le répertoire...", "gérer le lvm...", "monter le lvm..."); LVM tasks; nfs.yml + fluentbit_nfs_mounts; docker_cleanup.yml; `restart_policy: always`; default k8s tail path `/var/log/containers/*.log`; default k8s `kubernetes` filter; default `stdout` output; `fluentbit_namespace` + helm vars + servicemonitor + openshift_scc; `fluentbit_kubernetes_*` host paths; `fluentbit_root_dir: /opt/fluentbit` (use Phase-1 D-18 layout).
- Replaced: tail path -> `/var/lib/docker/containers/*/*-json.log` (role inversion per D-46); kubernetes filter -> D-47 modify+parser+grep allowlist chain; stdout output -> D-49 opentelemetry output.
- Added (Pitfall 6 mitigation pack -- the headline D-25 improvement for FB):
  - `Time_System_Timezone Etc/UTC` (upstream had none).
  - `Multiline_Flush 5` (upstream had none).
  - `Read_from_Head false` (upstream had none).
  - `storage.type filesystem` + `storage.max_chunks_up 128` + named buffer volume (upstream had `storage.path` COMMENTED OUT).
  - Fallback `@timestamp` modify filter (Pitfall 6 mode 2 mitigation; upstream had nothing).
  - D-47 label allowlist filter chain (upstream had K8s filter doing different work).
  - D-49 opentelemetry output (upstream used stdout for debugging only).
  - D-48 default-off extension knobs (preserves upstream legacy-host-scoop use case as opt-in).

Verify task scope (per RESEARCH Open Question Q9 + Finding 9 end-to-end caveat):
- Step 1: HEALTHCHECK or Running poll.
- Step 2: in-network curl `:2020/api/v1/health` returns 200. THIS IS THE M1 ACCEPTANCE GATE per the simplification recommendation.
- End-to-end FB->Loki smoke deferred to Phase 6 OPS-07 (single-push bucket-landing is impractical for FB output chunking).

</interfaces>

<phase_decisions_inline>
- D-40: Plan 03-04 owns roles/fluentbit/.
- D-41: Wave 4 -- depends_on: [03-02-opentelemetry]. FB ships through OTel; OTel must exist first (in role-list ordering; runtime FB will retry against OTel if not yet up).
- D-46: Default tail = Docker container JSON logs; ROLE INVERSION vs INSPQ (memory: project_fluentbit_role_shift.md).
- D-47: Label allowlist `{job, host, service, env, level}`; high-cardinality fields to Loki structured metadata.
- D-48: Extension knobs default-off; preserve upstream INSPQ legacy-host-scoop use case as opt-in.
- D-49: Ship via `opentelemetry` output plugin (NOT loki direct -- documented as alternative in README).
- D-50: Buffer + timestamp discipline (Pitfall 6 mitigation pack).
- D-30: fluentbit_publish_host: false default.
- D-54: in-network verify one-shot curl /api/v1/health; end-to-end FB->Loki smoke deferred per Q9.
- D-55: no vault keys.
- Pitfall 4 + 6 + 8 + 9 all mitigated.
</phase_decisions_inline>
</context>

<tasks>

<task type="auto" id="03-04-01">
  <name>Task 1: Create fluentbit role skeleton (full layout including templates/)</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/mimir/tasks/main.yml
    roles/mimir/handlers/main.yml
    roles/mimir/meta/main.yml
    roles/README.md
  </read_first>
  <action>
Create `roles/fluentbit/{defaults,tasks,templates,handlers,meta}/`. Create skeleton files:
  - roles/fluentbit/defaults/main.yml
  - roles/fluentbit/tasks/main.yml
  - roles/fluentbit/tasks/verify.yml
  - roles/fluentbit/templates/fluent-bit.conf.j2
  - roles/fluentbit/templates/parsers.conf.j2
  - roles/fluentbit/handlers/main.yml
  - roles/fluentbit/meta/main.yml (galaxy_info; description: "Deploys Fluent Bit 4.2.3 for Telemetron -- tails Docker container JSON logs by default and ships through OTel Collector to Loki."; galaxy_tags: logs, fluent-bit, observability, telemetron)
  - roles/fluentbit/README.md (skeleton)

Every YAML file starts with `---`.
  </action>
  <verify>
    <automated>test -d roles/fluentbit/defaults &amp;&amp; test -d roles/fluentbit/tasks &amp;&amp; test -d roles/fluentbit/templates &amp;&amp; test -d roles/fluentbit/handlers &amp;&amp; test -d roles/fluentbit/meta &amp;&amp; test -f roles/fluentbit/defaults/main.yml &amp;&amp; test -f roles/fluentbit/tasks/main.yml &amp;&amp; test -f roles/fluentbit/tasks/verify.yml &amp;&amp; test -f roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; test -f roles/fluentbit/templates/parsers.conf.j2 &amp;&amp; test -f roles/fluentbit/handlers/main.yml &amp;&amp; test -f roles/fluentbit/meta/main.yml &amp;&amp; test -f roles/fluentbit/README.md &amp;&amp; grep -q "^galaxy_info:" roles/fluentbit/meta/main.yml &amp;&amp; grep -q "license: MIT" roles/fluentbit/meta/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All five dirs + eight required files exist.
    - [ ] meta/main.yml has galaxy_info + license: MIT.
  </acceptance_criteria>
  <done>Skeleton matches Phase-2 canonical layout with two templates.</done>
</task>

<task type="auto" id="03-04-02" tdd="false">
  <name>Task 2: Populate defaults/main.yml with image pin, port, buffer volume, allowlist, extension knobs, conditional HEALTHCHECK</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/fluentbit/defaults/main.yml
    inventory/example-homelab/group_vars/all/storage.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/fluentbit/defaults/main.yml`. Required keys:

```yaml
# ---
# roles/fluentbit/defaults/main.yml
# Fluent Bit role tunables. Override per-environment in
# inventory/<env>/group_vars/all/fluentbit.yml.
#
# Fluent Bit 4.2.3 -- tails Docker container JSON logs by default
# (D-46 role inversion vs upstream INSPQ) and ships through OTel
# Collector at http://otel:4318/v1/logs (D-49 opentelemetry output).

# --- Image pin (OPS-01) ---
# See: https://fluentbit.io/announcements/v4.2.0/
# 4.x is M1-stable; 5.x released May 2026, too new for M1.
fluentbit_image: fluent/fluent-bit
fluentbit_image_tag: "4.2.3"

# --- Container identity ---
fluentbit_container_name: fluentbit

# --- Host port publishing (D-30) ---
# Default false. FB's :2020 HTTP server (/api/v1/health, /api/v1/metrics)
# is reachable on the telemetron bridge; operator access via SSH local-forward.
fluentbit_publish_host: "{{ fluentbit_publish_host | default(false) }}"

# --- Port matrix ---
fluentbit_http_port: 2020

# --- Config layout (D-18) ---
fluentbit_config_dir: "{{ telemetron_config_root | default('/opt/telemetron') }}/fluentbit"

# --- Buffer volume (D-50, Phase-1 D-16) ---
fluentbit_buffer_volume: "{{ telemetron_volume_prefix | default('telemetron') }}_fluentbit_buffer"

# --- D-46 default tail path (role inversion vs INSPQ) ---
fluentbit_docker_logs_path: "/var/lib/docker/containers"

# --- D-47 label allowlist (deploy-time static labels) ---
# host: ansible_hostname (set in Jinja at template render time)
# env: telemetron_env override
# service / job: container_name fallback (Q3 -- Docker-label promotion deferred)
telemetron_env: "{{ telemetron_env | default('homelab') }}"

# --- D-48 extension knobs (all default-off) ---
fluentbit_tail_system_logs: false
fluentbit_tail_journald: false
fluentbit_extra_tail_paths: []

# --- D-49 OTel destination (set by Plan 03-02 OTel) ---
fluentbit_otel_host: "otel"
fluentbit_otel_port: 4318
fluentbit_otel_logs_uri: "/v1/logs"

# --- D-50 buffer + timestamp discipline (Pitfall 6 mitigation pack) ---
fluentbit_system_timezone: "Etc/UTC"
fluentbit_multiline_flush: 5
fluentbit_storage_max_chunks_up: 128
fluentbit_storage_backlog_mem_limit: "50M"
fluentbit_flush_interval: 5

# --- D-47 level extraction regex ---
# Default Fluent Bit grep-style regex on log line content for level promotion.
fluentbit_level_regex: '(?i)\b(?<level>INFO|WARN|ERROR|FATAL|DEBUG|TRACE)\b'
fluentbit_default_level: info

# --- Healthcheck approach (conditional; same pattern as Phase-2 roles) ---
# FB image is distroless; image probe at execute time picks the outcome.
# Default Outcome B = binary-alive proxy via `/fluent-bit/bin/fluent-bit --version`.
fluentbit_healthcheck_enabled: true
fluentbit_healthcheck_test: ["CMD", "/fluent-bit/bin/fluent-bit", "--version"]
fluentbit_healthcheck_interval: 15s
fluentbit_healthcheck_timeout: 5s
fluentbit_healthcheck_retries: 5
fluentbit_healthcheck_start_period: 30s

# --- Verify pre-poll (D-10a) ---
fluentbit_health_retries: 30
fluentbit_health_delay: 2

# --- Restart policy (OPS-06) ---
fluentbit_restart_policy: unless-stopped

# --- Resource limits ---
fluentbit_memory_limit: 256m

# --- Network ---
fluentbit_network: "{{ telemetron_network | default('telemetron') }}"

# --- Timezone (OPS-06) ---
fluentbit_tz: "{{ telemetron_tz | default('Etc/UTC') }}"

# --- Curl image pin for verify (OPS-01) ---
fluentbit_curl_image: curlimages/curl
fluentbit_curl_image_tag: "8.10.1"
```

EXACT key names. Section ordering mirrors mimir.
  </action>
  <verify>
    <automated>grep -q '^fluentbit_image: fluent/fluent-bit$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_image_tag: "4.2.3"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_http_port: 2020$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q 'fluentbit_buffer_volume' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '_fluentbit_buffer' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_docker_logs_path: "/var/lib/docker/containers"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_tail_system_logs: false$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_tail_journald: false$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_extra_tail_paths: \[\]$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_system_timezone: "Etc/UTC"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_multiline_flush: 5$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_storage_max_chunks_up: 128$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_otel_host: "otel"$' roles/fluentbit/defaults/main.yml &amp;&amp; grep -q '^fluentbit_otel_port: 4318$' roles/fluentbit/defaults/main.yml &amp;&amp; ! grep -qE ':\s*latest' roles/fluentbit/defaults/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Image pin: `^fluentbit_image: fluent/fluent-bit$` AND `^fluentbit_image_tag: "4.2.3"$`.
    - [ ] Port 2020 literal.
    - [ ] Buffer volume name pattern: `_fluentbit_buffer` substring present.
    - [ ] Docker logs path D-46: `^fluentbit_docker_logs_path: "/var/lib/docker/containers"$`.
    - [ ] D-48 knobs all default-off: `^fluentbit_tail_system_logs: false$`, `^fluentbit_tail_journald: false$`, `^fluentbit_extra_tail_paths: \[\]$`.
    - [ ] D-50 pack: `^fluentbit_system_timezone: "Etc/UTC"$`, `^fluentbit_multiline_flush: 5$`, `^fluentbit_storage_max_chunks_up: 128$`.
    - [ ] D-49 OTel destination: `^fluentbit_otel_host: "otel"$`, `^fluentbit_otel_port: 4318$`.
    - [ ] No `:latest`.
    - [ ] Conditional HEALTHCHECK knob present.
  </acceptance_criteria>
  <done>defaults/main.yml has every literal templates + tasks consume; D-46/D-47/D-48/D-49/D-50 knobs all wired.</done>
</task>

<task type="auto" id="03-04-03" tdd="false">
  <name>Task 3: Write templates/fluent-bit.conf.j2 -- [SERVICE] (Pitfall 6 pack) + [INPUT] Docker JSON tail + conditional extension inputs (D-48) + [FILTER] allowlist chain (D-47) + [OUTPUT] opentelemetry (D-49) + fallback @timestamp filter</name>
  <read_first>
    roles/fluentbit/defaults/main.yml
    roles/loki/templates/loki.yaml.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/research/PITFALLS.md
  </read_first>
  <action>
Write `roles/fluentbit/templates/fluent-bit.conf.j2` based on RESEARCH Finding 9 (canonical shape). All Pitfall 6 mitigations explicit and inline-cited.

Required content shape (the .ini format Fluent Bit uses, not YAML):

```ini
# /opt/telemetron/fluentbit/fluent-bit.conf
# {{ ansible_managed }}
# Fluent Bit 4.2.3 -- Telemetron-tuned.
# Pitfall 6 mitigation pack inline-cited; D-50 buffer/timezone discipline.

[SERVICE]
    Parsers_File              parsers.conf
    Log_Level                 info
    Flush                     {{ fluentbit_flush_interval }}
    HTTP_Server               On
    HTTP_Listen               0.0.0.0
    HTTP_Port                 {{ fluentbit_http_port }}
    Health_Check              On
    HC_Error_Count            5
    HTTP_Metrics              On
    # D-50: filesystem buffer survives container restart without log loss.
    storage.path              /var/log/flb-storage/
    storage.sync              normal
    storage.checksum          off
    storage.backlog.mem_limit {{ fluentbit_storage_backlog_mem_limit }}
    storage.max_chunks_up     {{ fluentbit_storage_max_chunks_up }}
    # Pitfall 6 (Mode 1: DST drift) -- UTC everywhere; never DST-observing TZ.
    Time_System_Timezone      {{ fluentbit_system_timezone }}
    # Pitfall 6 (Mode 3: multiline parser stuck timestamp) -- fail-fast bound.
    Multiline_Flush           {{ fluentbit_multiline_flush }}

# D-46: Docker container logs default tail.
# ROLE INVERSION vs upstream INSPQ -- single-host colocated FB-with-workloads;
# see roles/fluentbit/README.md "Deviations from upstream INSPQ" section.
[INPUT]
    Name              tail
    Alias             docker_containers
    Path              {{ fluentbit_docker_logs_path }}/*/*-json.log
    Parser            docker
    Tag               docker.<container_id>
    Tag_Regex         (?<container_id>[^/]+)\.log$
    Refresh_Interval  5
    Read_from_Head    false
    Mem_Buf_Limit     10MB
    Skip_Long_Lines   On
    storage.type      filesystem
    Buffer_Max_Size   1MB
    Buffer_Chunk_Size 32KB

# D-48: extension knobs (default-off).
{% if fluentbit_tail_system_logs | default(false) %}
[INPUT]
    Name              tail
    Alias             system_logs
    Path              /var/log/syslog,/var/log/auth.log,/var/log/kern.log,/var/log/messages
    Tag               system.*
    Refresh_Interval  10
    Read_from_Head    false
    Skip_Long_Lines   On
    storage.type      filesystem
{% endif %}

{% if fluentbit_tail_journald | default(false) %}
[INPUT]
    Name              systemd
    Alias             journald
    Path              /run/log/journal
    Tag               journald.*
    Read_From_Tail    on
    Strip_Underscores on
{% endif %}

{% for entry in fluentbit_extra_tail_paths | default([]) | sort %}
[INPUT]
    Name              tail
    Alias             extra_{{ loop.index }}
    Path              {{ entry }}
    Tag               extra.{{ loop.index }}.*
    Refresh_Interval  10
    Read_from_Head    false
    storage.type      filesystem
{% endfor %}

# D-47 label allowlist: static deploy-time labels.
[FILTER]
    Name              modify
    Alias             allowlist_static
    Match             docker.*
    Add               host {{ ansible_hostname }}
    Add               env {{ telemetron_env | default('homelab') }}

# D-47 level extraction via regex parser. Fallback default when no match.
[FILTER]
    Name              parser
    Alias             extract_level
    Match             docker.*
    Key_Name          log
    Parser            level_extractor
    Reserve_Data      On
    Preserve_Key      On

[FILTER]
    Name              modify
    Alias             default_level
    Match             docker.*
    Add               level {{ fluentbit_default_level }}

# Pitfall 6 (Mode 2: missing date in source line) -- fallback @timestamp.
# modify Add operates only when the key is absent.
[FILTER]
    Name              modify
    Alias             timestamp_fallback
    Match             *
    Add               @timestamp ${ingest_time}

# D-49: ship to OTel Collector via OTLP/HTTP.
[OUTPUT]
    Name                 opentelemetry
    Alias                otel_logs
    Match                *
    Host                 {{ fluentbit_otel_host }}
    Port                 {{ fluentbit_otel_port }}
    Logs_uri             {{ fluentbit_otel_logs_uri }}
    log_response_payload false
    Tls                  Off
```

All comments ENGLISH. ASCII only.
  </action>
  <verify>
    <automated>grep -q "^\[SERVICE\]" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Time_System_Timezone" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Etc/UTC" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Multiline_Flush" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Read_from_Head    false" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "storage.type      filesystem" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "storage.max_chunks_up" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "/var/lib/docker/containers" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Parser            docker" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Name              opentelemetry" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "/v1/logs" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "fluentbit_tail_system_logs" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "fluentbit_tail_journald" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "fluentbit_extra_tail_paths" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "Pitfall 6" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "D-46" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "D-47" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "D-49" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; grep -q "D-50" roles/fluentbit/templates/fluent-bit.conf.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/templates/fluent-bit.conf.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] [SERVICE] block: `grep -q "^\[SERVICE\]" roles/fluentbit/templates/fluent-bit.conf.j2`.
    - [ ] Pitfall 6 pack: `grep -q "Time_System_Timezone"` AND `grep -q "Etc/UTC"` AND `grep -q "Multiline_Flush"` AND `grep -q "Read_from_Head    false"`.
    - [ ] D-50 storage block: `grep -q "storage.type      filesystem"` AND `grep -q "storage.max_chunks_up"`.
    - [ ] D-46 tail path: `grep -q "/var/lib/docker/containers"` AND `grep -q "Parser            docker"`.
    - [ ] D-49 opentelemetry output: `grep -q "Name              opentelemetry"` AND `grep -q "/v1/logs"`.
    - [ ] D-48 conditional knobs: `grep -q "fluentbit_tail_system_logs"` AND `grep -q "fluentbit_tail_journald"` AND `grep -q "fluentbit_extra_tail_paths"`.
    - [ ] D-47 allowlist filter chain: `grep -q "allowlist_static"` AND `grep -q "Name              modify"`.
    - [ ] Fallback @timestamp filter: `grep -q "timestamp_fallback"` AND `grep -q "Add               @timestamp"`.
    - [ ] Pitfall + D-XX inline citations: `grep -q "Pitfall 6"` AND `grep -q "D-46"` AND `grep -q "D-47"` AND `grep -q "D-49"` AND `grep -q "D-50"`.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>fluent-bit.conf.j2 has all D-46/47/48/49/50 mitigations plus Pitfall 6 pack plus role-inversion citation.</done>
</task>

<task type="auto" id="03-04-04" tdd="false">
  <name>Task 4: Write templates/parsers.conf.j2 -- docker JSON parser + level_extractor regex</name>
  <read_first>
    roles/fluentbit/defaults/main.yml
    roles/fluentbit/templates/fluent-bit.conf.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/fluentbit/templates/parsers.conf.j2`. Two parsers required:

```ini
# /opt/telemetron/fluentbit/parsers.conf
# {{ ansible_managed }}
# Fluent Bit parsers consumed by fluent-bit.conf -- docker JSON for the
# tail input (D-46), level_extractor for the [FILTER] parser stanza (D-47).

[PARSER]
    Name        docker
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%LZ
    Time_Keep   On

[PARSER]
    Name        level_extractor
    Format      regex
    Regex       {{ fluentbit_level_regex }}
```

ASCII only.
  </action>
  <verify>
    <automated>grep -q "Name        docker$" roles/fluentbit/templates/parsers.conf.j2 &amp;&amp; grep -q "Format      json" roles/fluentbit/templates/parsers.conf.j2 &amp;&amp; grep -q "Name        level_extractor$" roles/fluentbit/templates/parsers.conf.j2 &amp;&amp; grep -q "Format      regex" roles/fluentbit/templates/parsers.conf.j2 &amp;&amp; grep -q "fluentbit_level_regex" roles/fluentbit/templates/parsers.conf.j2 &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/templates/parsers.conf.j2</automated>
  </verify>
  <acceptance_criteria>
    - [ ] docker parser: `grep -q "Name        docker$"` AND `grep -q "Format      json"`.
    - [ ] level_extractor parser: `grep -q "Name        level_extractor$"` AND `grep -q "Format      regex"`.
    - [ ] References regex var: `grep -q "fluentbit_level_regex"`.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>parsers.conf.j2 has both required parsers.</done>
</task>

<task type="auto" id="03-04-05" tdd="false">
  <name>Task 5: Write tasks/main.yml -- config dir, render two templates (notify), ensure buffer volume, pull image, run container with two bind-mounts + conditional HEALTHCHECK, include verify</name>
  <read_first>
    roles/mimir/tasks/main.yml
    roles/fluentbit/defaults/main.yml
    roles/fluentbit/templates/fluent-bit.conf.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/fluentbit/tasks/main.yml`. Task sequence:

1. **Ensure config dir**: `ansible.builtin.file: path: "{{ fluentbit_config_dir }}" state: directory mode: 0755`. Tags: [fluentbit, fluentbit-config].

2. **Render fluent-bit.conf**: `ansible.builtin.template: src: fluent-bit.conf.j2 dest: "{{ fluentbit_config_dir }}/fluent-bit.conf" mode: 0640`. `notify: restart fluentbit`. Tags: [fluentbit, fluentbit-config].

3. **Render parsers.conf**: same module, src parsers.conf.j2, dest "{{ fluentbit_config_dir }}/parsers.conf", mode 0640. `notify: restart fluentbit`. Tags: [fluentbit, fluentbit-config].

4. **Ensure buffer volume** (D-50 + Phase-1 D-16): `community.docker.docker_volume: name: "{{ fluentbit_buffer_volume }}" state: present`. Tags: [fluentbit].

5. **Pull image**: `community.docker.docker_image: name: "{{ fluentbit_image }}:{{ fluentbit_image_tag }}" source: pull force_source: false`. Tags: [fluentbit].

6. **Run container** -- `community.docker.docker_container`:
   - name, image, state: started, recreate: false, restart_policy, memory
   - command: `["/fluent-bit/bin/fluent-bit", "-c", "/fluent-bit/etc/fluent-bit.conf"]`
   - networks: aliases `["{{ fluentbit_container_name }}"]`
   - `published_ports:` -- triple-conditional Jinja mirror of mimir for `fluentbit_http_port`
   - `mounts:` -- TWO entries:
     - `{ source: "{{ fluentbit_buffer_volume }}", target: "/var/log/flb-storage", type: volume }` (D-50 buffer)
     - `{ source: "{{ fluentbit_docker_logs_path }}", target: "{{ fluentbit_docker_logs_path }}", type: bind, read_only: true }` (D-46 Docker log tail source)
   - `volumes:` -- TWO bind-mounts (config files):
     - `"{{ fluentbit_config_dir }}/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro"`
     - `"{{ fluentbit_config_dir }}/parsers.conf:/fluent-bit/etc/parsers.conf:ro"`
   - `healthcheck:` -- conditional via vars-form mirroring mimir
   - `env: { TZ: "{{ fluentbit_tz }}" }`
   - Tags: [fluentbit, fluentbit-container]

7. **Include verify**: `ansible.builtin.include_tasks: verify.yml`. Tags: [fluentbit, fluentbit-verify].

All task names ENGLISH; no `state: restarted`; ASCII only.
  </action>
  <verify>
    <automated>grep -q "src: fluent-bit.conf.j2" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "src: parsers.conf.j2" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "community.docker.docker_volume" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "fluentbit_buffer_volume" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "/var/log/flb-storage" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "/var/lib/docker/containers" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "read_only: true" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "notify: restart fluentbit" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "include_tasks: verify.yml" roles/fluentbit/tasks/main.yml &amp;&amp; ! grep -qE "state:\s*restarted" roles/fluentbit/tasks/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Both template renders present: `grep -q "src: fluent-bit.conf.j2"` AND `grep -q "src: parsers.conf.j2"`.
    - [ ] Buffer volume created via docker_volume: `grep -q "community.docker.docker_volume"` AND `grep -q "fluentbit_buffer_volume"`.
    - [ ] Buffer volume mounted at /var/log/flb-storage: `grep -q "/var/log/flb-storage"`.
    - [ ] Docker logs bind-mount RO: `grep -q "/var/lib/docker/containers"` AND `grep -q "read_only: true"`.
    - [ ] Config files bind-mounted RO at canonical FB paths.
    - [ ] Both renders notify restart: `grep -c "notify: restart fluentbit" roles/fluentbit/tasks/main.yml` returns 2.
    - [ ] include_tasks final task.
    - [ ] D-19 enforced: `! grep -qE "state:\s*restarted"`.
    - [ ] ASCII-only.
    - [ ] Conditional HEALTHCHECK: `grep -q "if (fluentbit_healthcheck_enabled | bool) else omit"`.
  </acceptance_criteria>
  <done>tasks/main.yml renders both configs, manages volume + container, includes verify.</done>
</task>

<task type="auto" id="03-04-06" tdd="false">
  <name>Task 6: Write tasks/verify.yml -- D-10a poll + /api/v1/health 200 probe (M1 acceptance gate per Q9)</name>
  <read_first>
    roles/mimir/tasks/verify.yml
    roles/fluentbit/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/fluentbit/tasks/verify.yml`. Per RESEARCH Q9 simplification, end-to-end FB->Loki smoke deferred to Phase 6 OPS-07. M1 acceptance gate = `:2020/api/v1/health` returns 200.

**Step 1a -- HEALTHCHECK poll** (when enabled): `community.docker.docker_container_info` for `{{ fluentbit_container_name }}`, until State.Health.Status=='healthy', retries `{{ fluentbit_health_retries }}`, delay `{{ fluentbit_health_delay }}`, `when: fluentbit_healthcheck_enabled | bool`.

**Step 1b -- State.Running fallback** (when disabled).

**Step 2 -- /api/v1/health 200 probe**: one-shot curlimages/curl on telemetron network. Shell loop:
```
i=0 ;
while [ $i -lt 30 ] ; do
  CODE=$(curl -sS -o /dev/null -w "%{http_code}" http://{{ fluentbit_container_name }}:{{ fluentbit_http_port }}/api/v1/health 2>/dev/null) ;
  if [ "$CODE" = "200" ] ; then echo "health_ok=200" ; exit 0 ; fi ;
  i=$((i+1)) ;
  sleep 2 ;
done ;
echo "fluentbit /api/v1/health never returned 200 within 60s" ;
exit 1
```
auto_remove: true, changed_when: false, failed_when on non-zero status.

(NO Step 3 -- end-to-end FB->Loki smoke deferred to Phase 6.)

All task names ENGLISH. ASCII only.
  </action>
  <verify>
    <automated>grep -q "community.docker.docker_container_info" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "State.Health.Status == 'healthy'" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "State.Running is true" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "/api/v1/health" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "auto_remove: true" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "changed_when: false" roles/fluentbit/tasks/verify.yml &amp;&amp; grep -q "fluentbit_network" roles/fluentbit/tasks/verify.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/tasks/verify.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Step 1a HEALTHCHECK poll + Step 1b Running fallback.
    - [ ] Step 2 /api/v1/health probe.
    - [ ] auto_remove + changed_when: false on the one-shot.
    - [ ] Attached to telemetron network.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>verify.yml has HEALTHCHECK/Running poll + /api/v1/health 200 assertion. End-to-end FB->Loki is documented in README as Phase 6.</done>
</task>

<task type="auto" id="03-04-07" tdd="false">
  <name>Task 7: Write handlers/main.yml</name>
  <read_first>
    roles/mimir/handlers/main.yml
  </read_first>
  <action>
```yaml
# ---
# roles/fluentbit/handlers/main.yml
# Per D-19 / Pitfall 8: container restarts on config change use
# `docker restart <name>`. Force-recreate is non-idempotent.

- name: Docker restart fluentbit
  ansible.builtin.command:
    cmd: "docker restart {{ fluentbit_container_name }}"
  changed_when: true
  listen: restart fluentbit
```
  </action>
  <verify>
    <automated>grep -q "^- name: Docker restart fluentbit$" roles/fluentbit/handlers/main.yml &amp;&amp; grep -q "listen: restart fluentbit" roles/fluentbit/handlers/main.yml &amp;&amp; ! grep -q "state: restarted" roles/fluentbit/handlers/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/fluentbit/handlers/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Single handler with canonical W6 pattern.
    - [ ] No state: restarted.
    - [ ] ASCII-only.
  </acceptance_criteria>
  <done>handlers/main.yml has the canonical single handler.</done>
</task>

<task type="auto" id="03-04-08" tdd="false">
  <name>Task 8: Write README.md -- OPS-03 schema + D-46 role-inversion explanation + D-47 label allowlist + D-48 extension knobs + 'Labeling operator apps' section + FB->Loki direct alternative + D-25 audit</name>
  <read_first>
    roles/mimir/README.md
    roles/loki/README.md
    roles/fluentbit/defaults/main.yml
    roles/fluentbit/templates/fluent-bit.conf.j2
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/fluentbit/README.md`. Required H2 sections:

1. `# roles/fluentbit` -- overview.
2. `## What this role does` -- numbered list.
3. `## Default tail path (D-46 role inversion)` -- explain that FB tails `/var/lib/docker/containers/*/*-json.log` on the same Docker host where the Telemetron stack itself runs. This INVERTS the upstream INSPQ pattern (FB on legacy hosts shipping app-specific log files to a central observability host). Single-host colocated FB-with-workloads. Reference user memory `project_fluentbit_role_shift.md`.
4. `## Loki label allowlist (D-47)` -- enumerate the five allowed labels (host, env, service, job, level) and explain mapping. NOTE Q3 simplification: `service` and `job` default to container_name (Docker-label-based promotion deferred to v2).
5. `## Labeling operator apps` -- THE LOAD-BEARING SECTION per planning_context. Explain: operators who want Docker-label-driven labeling can add a `[FILTER] lua` script to enrich tail records with container Docker labels via the Docker API at read time. Document this as a deferred enhancement.
6. `## Extension knobs (D-48, all default-off)` -- describe `fluentbit_tail_system_logs`, `fluentbit_tail_journald` (Linux-with-systemd only -- requires bind-mount `/run/systemd/journal/socket`), `fluentbit_extra_tail_paths` (preserves upstream-INSPQ legacy-host-scoop use case as opt-in).
7. `## Transport (D-49)` -- ship via `opentelemetry` output plugin (OTLP/HTTP) to `http://otel:4318/v1/logs`. Document FB->Loki direct as an alternative (per INGEST-06): operators who want to bypass OTel can set... and replace the [OUTPUT] block with `loki` output pointing at `http://loki:3100/loki/api/v1/push`. Document this even if not exposed as a knob in M1.
8. `## Buffer + timestamp discipline (D-50; Pitfall 6 mitigation pack)` -- enumerate the five knobs (storage.type filesystem, storage.max_chunks_up 128, Time_System_Timezone Etc/UTC, Multiline_Flush 5, Read_from_Head false) and the fallback @timestamp filter. Emphasize Time_System_Timezone is the single most impactful one-liner.
9. `## Variables` -- markdown table.
10. `## Vault keys` -- "None (Phase 3 D-55)."
11. `## Tags` -- "- `fluentbit`".
12. `## Volumes` -- table: `telemetron_fluentbit_buffer` (named, /var/log/flb-storage) for filesystem buffer; bind-mount `/var/lib/docker/containers` host -> container RO; two config-file bind-mounts.
13. `## Healthcheck` -- conditional pattern.
14. `## Operator access (no host publish by default per D-30)` -- SSH local-forward.
15. `## Security model` -- short.
16. `## Idempotency` -- standard.
17. `## Port-acceptance gates` -- six gates.
18. `## Deviations from upstream INSPQ (D-25)` -- the audit:
    - **Role inversion (D-46)** -- THE HEADLINE deviation. Upstream INSPQ used FB on legacy hosts to scoop app-specific logs to a central observability host. Telemetron M1 colocates FB with workloads on a single Docker host, tailing container JSON logs by default. The `fluentbit_extra_tail_paths` knob (D-48) preserves the upstream use case as opt-in.
    - **Dropped:** K8s helm branches, French task names, LVM tasks, nfs.yml + fluentbit_nfs_mounts, docker_cleanup.yml, `:latest` tag, default k8s tail path /var/log/containers, default `kubernetes` filter, default `stdout` output, restart_policy always, UFW, `fluentbit_root_dir: /opt/fluentbit` (Phase-1 D-18 flat layout instead), `America/Toronto` TZ (D-50 Etc/UTC instead).
    - **Replaced:** tail path -> /var/lib/docker/containers (D-46); kubernetes filter -> D-47 modify+parser+grep allowlist; stdout output -> D-49 opentelemetry output.
    - **Added (Pitfall 6 mitigation pack -- THE biggest D-25 improvement):** Time_System_Timezone Etc/UTC, Multiline_Flush 5, Read_from_Head false, storage.type filesystem + storage.max_chunks_up 128, fallback @timestamp modify filter, D-47 label allowlist filter chain, D-48 default-off extension knobs, D-49 opentelemetry output.
19. `## Deprecation notes` -- "None for M1."

ASCII-only outside D-25 audit section.
  </action>
  <verify>
    <automated>grep -qE "^# roles/fluentbit" roles/fluentbit/README.md &amp;&amp; grep -q "^## Default tail path" roles/fluentbit/README.md &amp;&amp; grep -q "^## Loki label allowlist" roles/fluentbit/README.md &amp;&amp; grep -q "^## Labeling operator apps" roles/fluentbit/README.md &amp;&amp; grep -q "^## Extension knobs" roles/fluentbit/README.md &amp;&amp; grep -q "^## Transport" roles/fluentbit/README.md &amp;&amp; grep -q "^## Buffer + timestamp discipline" roles/fluentbit/README.md &amp;&amp; grep -q "^## Variables" roles/fluentbit/README.md &amp;&amp; grep -q "^## Vault keys" roles/fluentbit/README.md &amp;&amp; grep -q "^## Tags" roles/fluentbit/README.md &amp;&amp; grep -q "^## Deviations from upstream INSPQ" roles/fluentbit/README.md &amp;&amp; grep -q "Etc/UTC" roles/fluentbit/README.md &amp;&amp; grep -q "Multiline_Flush" roles/fluentbit/README.md &amp;&amp; grep -q "/v1/logs" roles/fluentbit/README.md &amp;&amp; grep -q "4.2.3" roles/fluentbit/README.md &amp;&amp; grep -q "role inversion" roles/fluentbit/README.md &amp;&amp; grep -q "FB.*Loki direct" roles/fluentbit/README.md</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All 19 required H2 sections (the grep set above covers the key load-bearing ones).
    - [ ] D-46 role inversion explicit: `grep -q "role inversion"`.
    - [ ] D-47 label allowlist documented.
    - [ ] D-48 extension knobs documented.
    - [ ] D-49 transport + FB->Loki direct alternative per INGEST-06: `grep -q "FB.*Loki direct"`.
    - [ ] D-50 Pitfall 6 mitigations enumerated: `grep -q "Etc/UTC"` AND `grep -q "Multiline_Flush"`.
    - [ ] Image tag pin documented.
    - [ ] "Labeling operator apps" section per planning_context.
    - [ ] D-25 audit has all four categories (role inversion + Dropped + Replaced + Added).
  </acceptance_criteria>
  <done>README has full OPS-03 schema + D-46/47/48/49/50 sections + Labeling operator apps + FB->Loki direct alternative + D-25 audit.</done>
</task>

<task type="auto" id="03-04-09" tdd="false">
  <name>Task 9: Create inventory/example-homelab/group_vars/all/fluentbit.yml + wire role into playbooks/deploy_docker.yml after prometheus</name>
  <read_first>
    inventory/example-homelab/group_vars/all/mimir.yml
    playbooks/deploy_docker.yml
  </read_first>
  <action>
**Step A:** Create `inventory/example-homelab/group_vars/all/fluentbit.yml`:

```yaml
# ---
# Telemetron -- fluentbit operator knobs (Phase 3, D-30, D-46, D-48, D-50)
# Role-specific overrides for the `fluentbit` role.
# See roles/fluentbit/defaults/main.yml for the full default surface.

# Default: zero host port publish. Operator access via SSH:
#   ssh -L 2020:localhost:2020 <host>
fluentbit_publish_host: false

# D-48 extension knobs (all default-off). Flip selectively per host.
# tail_system_logs: when true, tails /var/log/{syslog,auth.log,kern.log,messages}.
# tail_journald: requires Linux-with-systemd; bind-mount /run/systemd/journal/socket
#                in roles/fluentbit/tasks/main.yml when flipping this on.
# extra_tail_paths: list of arbitrary tail paths -- preserves the upstream
#                   INSPQ legacy-host-scoop use case as opt-in (D-46 inversion docs).
fluentbit_tail_system_logs: false
fluentbit_tail_journald: false
fluentbit_extra_tail_paths: []

# Default env label applied to all FB-shipped logs.
telemetron_env: homelab

# Conditional HEALTHCHECK (image probe outcome at execute time).
fluentbit_healthcheck_enabled: true
```

**Step B:** Edit `playbooks/deploy_docker.yml`. Append `fluentbit` after `prometheus` (D-41 order). Tag `fluentbit`. Update trailing comment block (Phase 3 now complete in the playbook).

Run syntax check.
  </action>
  <verify>
    <automated>test -f inventory/example-homelab/group_vars/all/fluentbit.yml &amp;&amp; grep -q "^fluentbit_publish_host: false$" inventory/example-homelab/group_vars/all/fluentbit.yml &amp;&amp; grep -q "^fluentbit_tail_system_logs: false$" inventory/example-homelab/group_vars/all/fluentbit.yml &amp;&amp; grep -q "^fluentbit_extra_tail_paths: \[\]$" inventory/example-homelab/group_vars/all/fluentbit.yml &amp;&amp; grep -q "    - role: fluentbit$" playbooks/deploy_docker.yml &amp;&amp; awk '/- role: prometheus/{p=NR}/- role: fluentbit/{f=NR}END{exit !(p&lt;f)}' playbooks/deploy_docker.yml &amp;&amp; ansible-playbook --syntax-check playbooks/deploy_docker.yml 2>&amp;1 | grep -q "playbook:.*deploy_docker.yml"</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Inventory file exists with expected knobs.
    - [ ] Playbook references `role: fluentbit`.
    - [ ] D-41 order: fluentbit AFTER prometheus.
    - [ ] Syntax check exits 0.
    - [ ] ASCII-only on inventory file.
  </acceptance_criteria>
  <done>Inventory + playbook updates land; Phase 3 playbook order complete.</done>
</task>

<task type="auto" id="03-04-10" tdd="false">
  <name>Task 10: Tick roles/README.md status row + run all six port-acceptance gates</name>
  <read_first>
    roles/README.md
    roles/fluentbit/defaults/main.yml
    roles/fluentbit/tasks/main.yml
    roles/fluentbit/handlers/main.yml
    roles/fluentbit/README.md
    roles/fluentbit/templates/fluent-bit.conf.j2
    roles/fluentbit/templates/parsers.conf.j2
  </read_first>
  <action>
**Step A:** Update `roles/README.md` -- change the `fluentbit` row's Ported column to `☑`.

**Step B:** Run the six port-acceptance gates:
1. Image-pin: `! grep -rE 'image:.*:latest' roles/fluentbit/`
2. INSPQ grep (code/config): `! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.conf'`
3. Non-ASCII: `! grep -rPl '[^\x00-\x7F]' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.conf'`
4. Vault gate (D-55): `! grep -rE '{{ *vault_' roles/fluentbit/`
5. Idempotency: `! grep -rE 'state:\s*restarted' roles/fluentbit/`
6. OPS-06: `grep -q "restart_policy:" roles/fluentbit/tasks/main.yml` AND `grep -q "healthcheck:" roles/fluentbit/tasks/main.yml`.

Bonus check: `! grep -q "America/Montreal\|America/Toronto" roles/fluentbit/` -- Pitfall 6 DST avoidance.
  </action>
  <verify>
    <automated>grep -qE "^\| \`fluentbit\`\s*\|.*\|\s*☑\s*\|" roles/README.md &amp;&amp; ! grep -rE 'image:.*:latest' roles/fluentbit/ &amp;&amp; ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.conf' &amp;&amp; ! grep -rPl '[^\x00-\x7F]' roles/fluentbit/ --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.conf' &amp;&amp; ! grep -rE '{{ *vault_' roles/fluentbit/ &amp;&amp; ! grep -rE 'state:\s*restarted' roles/fluentbit/ &amp;&amp; grep -q "restart_policy:" roles/fluentbit/tasks/main.yml &amp;&amp; grep -q "healthcheck:" roles/fluentbit/tasks/main.yml &amp;&amp; ! grep -rE 'America/(Montreal|Toronto)' roles/fluentbit/</automated>
  </verify>
  <acceptance_criteria>
    - [ ] roles/README.md fluentbit row ticked.
    - [ ] All six gates pass.
    - [ ] No DST-observing TZ literal anywhere (Pitfall 6).
  </acceptance_criteria>
  <done>roles/README.md row `☑`; all six gates green; Pitfall 6 source-side discipline confirmed.</done>
</task>

</tasks>

<verification>
**Static verification:**

1. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
2. All ten task-level acceptance_criteria pass.
3. `find roles/fluentbit -type f | sort` returns: defaults/main.yml, handlers/main.yml, meta/main.yml, tasks/main.yml, tasks/verify.yml, templates/fluent-bit.conf.j2, templates/parsers.conf.j2, README.md.
4. fluent-bit.conf.j2 contains all five Pitfall 6 mitigations (Time_System_Timezone Etc/UTC, Multiline_Flush 5, Read_from_Head false, storage.type filesystem, fallback @timestamp).
5. fluent-bit.conf.j2 contains [INPUT] tail on Docker JSON path + [OUTPUT] opentelemetry to otel:4318/v1/logs.
6. roles/README.md row ticked.

**Live verification (deferred to Phase 3 verification stage):**

7. `ansible-playbook --tags fluentbit` completes; FB container healthy or running.
8. `curl http://fluentbit:2020/api/v1/health` returns 200.
9. `docker inspect telemetron-fluentbit --format '{{.HostConfig.Mounts}}'` shows `telemetron_fluentbit_buffer` volume + `/var/lib/docker/containers` RO bind-mount.
10. Second back-to-back run reports `changed=0` for fluentbit tag.
11. (Phase 6 OPS-07) End-to-end synthetic log -> Loki within 60s.

</verification>

<success_criteria>
- [ ] `roles/fluentbit/` directory contains full canonical layout (defaults, tasks/main, tasks/verify, two templates, handlers, meta, README).
- [ ] All ten task-level acceptance_criteria pass.
- [ ] All six per-role port-acceptance gates pass.
- [ ] roles/README.md status table row for fluentbit shows `☑`.
- [ ] playbooks/deploy_docker.yml contains `role: fluentbit` after `role: prometheus`.
- [ ] inventory/example-homelab/group_vars/all/fluentbit.yml exists with operator knobs.
- [ ] `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
- [ ] Pitfall 6 mitigation pack (Etc/UTC + Multiline_Flush 5 + Read_from_Head false + storage.type filesystem + fallback @timestamp) all rendered in fluent-bit.conf.j2.
- [ ] D-46 role inversion documented in README.
- [ ] D-49 OTel transport + FB->Loki direct alternative both documented.
- [ ] INGEST-06 marked satisfied; INGEST-07 (label allowlist) source-side mitigation in place; live UAT deferred to Phase 6 OPS-07.
</success_criteria>

<output>
After completion, create `.planning/phases/03-ingest-plane/03-04-fluentbit-SUMMARY.md` documenting: image probe outcome, D-46 role-inversion implementation, D-47 label allowlist + Q3 fallback (container_name vs Docker labels), D-48 extension knob shape, D-49 OTel transport + FB->Loki direct alternative, D-50 Pitfall 6 mitigation pack list, D-25 deviations, execute-time surprises.
</output>
</content>
</invoke>