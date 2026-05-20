---
plan: 03-01-node-exporter
phase: 03-ingest-plane
type: execute
wave: 1
depends_on: []
requirements: [INGEST-08]
files_modified:
  - roles/node_exporter/defaults/main.yml
  - roles/node_exporter/tasks/main.yml
  - roles/node_exporter/tasks/verify.yml
  - roles/node_exporter/handlers/main.yml
  - roles/node_exporter/meta/main.yml
  - roles/node_exporter/README.md
  - inventory/example-homelab/group_vars/all/node_exporter.yml
  - playbooks/deploy_docker.yml
  - roles/README.md
autonomous: true

must_haves:
  truths:
    - "An in-network curl to http://node-exporter:9100/metrics returns 200 with a body containing `node_cpu_seconds_total` (ROADMAP SC1 + INGEST-04)."
    - "Telemetron operator can run `ansible-playbook --tags node_exporter` against a fresh-from-Phase-2 host and the node-exporter container comes up healthy and persists across reboot (OPS-06 unless-stopped)."
    - "Re-running the playbook reports `changed=0` for the node_exporter tag (OPS-04 idempotency gate)."
    - "All six per-role port-acceptance gates pass on `roles/node_exporter/` (image-pin, grep, non-ASCII, vault-N/A per D-55, idempotency, healthcheck+restart, README)."
    - "node-exporter container appears as an `up` scrape target later when Plan 03-03 wires Prometheus (deferred verify); plan 03-01's own verify is direct in-network curl."
  artifacts:
    - path: roles/node_exporter/defaults/main.yml
      provides: "Role tunables: image pin quay.io/prometheus/node-exporter:v1.11.1, container identity, port :9100, no-host-publish default, bind-mounts /proc /sys / -> /host/{proc,sys,root}, conditional-HEALTHCHECK pattern."
      contains: "v1.11.1"
    - path: roles/node_exporter/tasks/main.yml
      provides: "Bootstrap sequence: config dir (no rendered config -- node_exporter is CLI-flag-driven), pull image, run container with pid_mode host and bind-mounts, include verify.yml."
      contains: "include_tasks: verify.yml"
    - path: roles/node_exporter/tasks/verify.yml
      provides: "D-10a HEALTHCHECK or State.Running poll + in-network curl one-shot asserting /metrics body contains node_cpu_seconds_total."
      contains: "node_cpu_seconds_total"
    - path: roles/node_exporter/handlers/main.yml
      provides: "Single restart handler (W6) via `docker restart` -- never state: restarted (Pitfall 8)."
      contains: "Docker restart node_exporter"
    - path: roles/node_exporter/README.md
      provides: "OPS-03 schema: variables, vault (N/A per D-55), tags, modes, volumes (N/A), healthcheck, operator access, security model, idempotency, port-acceptance gates, Deviations from upstream INSPQ."
      contains: "## Deviations from upstream INSPQ"
    - path: inventory/example-homelab/group_vars/all/node_exporter.yml
      provides: "Operator-facing knobs surfaced: node_exporter_publish_host default false; container hardening enabled."
      contains: "node_exporter_publish_host"
    - path: playbooks/deploy_docker.yml
      provides: "node_exporter role wired in D-41 order: after mimir, before opentelemetry."
      contains: "role: node_exporter"
    - path: roles/README.md
      provides: "Port-status table row for node_exporter ticked."
      contains: "| `node_exporter`"
  key_links:
    - from: "roles/node_exporter/tasks/main.yml"
      to: "roles/node_exporter/tasks/verify.yml"
      via: "ansible.builtin.include_tasks (D-32 / D-54 carry-forward)"
      pattern: "include_tasks: verify.yml"
    - from: "roles/node_exporter/templates_or_tasks notify"
      to: "roles/node_exporter/handlers/main.yml"
      via: "notify: restart node_exporter (W6 single-handler pattern)"
      pattern: "notify:.*restart node_exporter"
    - from: "playbooks/deploy_docker.yml"
      to: "roles/node_exporter/"
      via: "role list entry after mimir (D-41 order)"
      pattern: "role: node_exporter"
    - from: "roles/node_exporter/tasks/main.yml docker_container.mounts"
      to: "host /proc /sys /"
      via: "RO bind-mounts at /host/{proc,sys,root} with --path.{procfs,sysfs,rootfs} args"
      pattern: "/host/proc.*/host/sys.*/host/root"
---

<objective>
Port the `node_exporter` role into `roles/node_exporter/` mirroring the Phase-2 canonical role-template layout (`roles/{minio,loki,tempo,mimir}/`), shipping host metrics on `:9100/metrics` over the `telemetron` Docker bridge network. Pin image to `quay.io/prometheus/node-exporter:v1.11.1` (research correction to CONTEXT.md's stale `v1.8.x` mention). Wire as Wave 1 of Phase 3 -- zero intra-phase dependencies, plays after the Phase-2 stack via the deploy_docker.yml role-order chain.

Purpose: deliver INGEST-04 (host metrics exposed on `:9100/metrics`) which is the simplest leg of the ingest plane and the foundation that Plan 03-03's Prometheus will scrape. Establishes the Phase-3-role conventions (no-rendered-config, distroless conditional-HEALTHCHECK, in-network /metrics verify) that the heavier OTel/Prometheus/FB plans inherit.

Output: a full canonical role layout under `roles/node_exporter/` plus one inventory file plus the playbook wiring plus the roles/README.md status row tick. Six port-acceptance gates pass.
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
@roles/mimir/README.md
@roles/loki/tasks/verify.yml
@inventory/example-homelab/group_vars/all/network.yml
@inventory/example-homelab/group_vars/all/storage.yml
@inventory/example-homelab/group_vars/all/mimir.yml
@playbooks/deploy_docker.yml

<interfaces>
<!-- Key Phase-1/2 conventions and inventory vars the executor MUST reference verbatim. -->
<!-- No code exploration needed -- contracts are listed here. -->

From inventory/example-homelab/group_vars/all/network.yml:
- telemetron_network: telemetron      # Docker bridge name; created by playbook pre_tasks (D-04)
- telemetron_publish_default: false   # Default no-host-publish (D-12, D-14, D-30)
- telemetron_tz: Etc/UTC               # OPS-06 + Pitfall 6

From inventory/example-homelab/group_vars/all/storage.yml:
- telemetron_volume_prefix: telemetron        # node_exporter is STATELESS -- no volume needed
- telemetron_config_root: /opt/telemetron     # node_exporter is CLI-only -- no rendered config

From the canonical role template (roles/mimir):
- D-10a HEALTHCHECK poll uses community.docker.docker_container_info with State.Health.Status
- Conditional healthcheck pattern (Tempo/Mimir Outcome A/B/C): `<role>_healthcheck_enabled` + `omit` magic value
- W6 single handler: `- name: Docker restart <role>` running `ansible.builtin.command: cmd: docker restart {{ <role>_container_name }}` with `changed_when: true` and `listen: restart <role>`
- D-30 published_ports Jinja: triple-conditional yielding [] when false, [127.0.0.1:p:p] when '127.0.0.1', [p:p] when true
- meta/main.yml shape: galaxy_info { role_name, author, description, license: MIT, min_ansible_version "2.15", platforms Ubuntu jammy/noble + Debian bookworm, galaxy_tags }, dependencies: [], collections: [community.docker, ansible.builtin]
- README OPS-03 schema headings (in this order): What this role does, Variables, Vault keys, Tags, Modes, Volumes, Healthcheck, Operator access, Security model, Idempotency, Port-acceptance gates, Deviations from upstream INSPQ, Deprecation notes (optional)

From RESEARCH.md Finding 6 (canonical containerized node_exporter shape):
- image: quay.io/prometheus/node-exporter (Quay matches Alertmanager pin pattern; avoid prom/node-exporter Docker Hub for rate-limit risk)
- image_tag: v1.11.1 (verified 2026-04-07 release)
- pid_mode: host  (REQUIRED for some collectors)
- command flags (verbatim):
    --path.procfs=/host/proc
    --path.sysfs=/host/sys
    --path.rootfs=/host/root
    --collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+|var/lib/kubelet/.+)($|/)
    --collector.filesystem.fs-types-exclude=^(autofs|binfmt_misc|bpf|cgroup2?|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|iso9660|mqueue|nsfs|overlay|proc|procfs|pstore|rpc_pipefs|securityfs|selinuxfs|squashfs|sysfs|tracefs)$
    --web.listen-address=0.0.0.0:9100
- mounts: /proc -> /host/proc:ro, /sys -> /host/sys:ro, / -> /host/root:ro (propagation: rslave for the root mount)
- HEALTHCHECK note: image is from-scratch (no wget). Image probe at execute time; researcher most-likely outcome = B (only --version proxy) so default `node_exporter_healthcheck_test: ["CMD", "/bin/node_exporter", "--version"]` with `_healthcheck_enabled: true`; if probe shows nothing, flip `_healthcheck_enabled: false` and rely on State.Running + in-network /metrics curl.

From RESEARCH.md INSPQ Deviation Audit (D-25 entries that MUST appear in README):
- Dropped: native deployment method (Docker-only per CLAUDE.md), LVM tasks, UFW rules, French task names, default-on host publish, textfile collector, America/Toronto TZ, `:latest` tag, the typo `node_explorer_docker_restart_policy`.
- Replaced: `--path.rootfs=/rootfs` -> `--path.rootfs=/host/root`, `prom/node-exporter` -> `quay.io/prometheus/node-exporter`.
- Added: Pre-poll HEALTHCHECK + in-network verify (D-10a + D-32 + D-54), conditional `node_exporter_publish_host: false` (security default flip), pinned image tag.
- Kept (security hardening from upstream): `read_only: true`, `cap_drop: [ALL]`, `capabilities: [DAC_READ_SEARCH]`, `security_opts: ['no-new-privileges:true']`, `tmpfs: ['/tmp']`, `pids_limit: 512` -- guarded by `node_exporter_container_hardening_enabled: true` knob.
</interfaces>

<phase_decisions_inline>
- D-40: Plan 03-01 owns roles/node_exporter/ exclusively.
- D-41: Wave 1 -- no intra-phase deps; depends_on: []. Playbook role order after this plan: minio -> loki -> tempo -> mimir -> node_exporter (this plan appends node_exporter as the new last entry).
- D-30/D-12/D-14: `node_exporter_publish_host: false` default. Operator access via SSH local-forward.
- D-19/W6: single handler, `docker restart node-exporter` -- never `state: restarted`.
- D-20: Jinja `| sort` on any operator-supplied dicts (N/A here -- no rendered config).
- D-21: INSPQ grep gate + non-ASCII gate. Scope: code/config files; README documents D-25 audit per Phase-2 reinterpretation (allowed to mention "upstream INSPQ").
- D-25: Per-role README "Deviations from upstream INSPQ" section is mandatory. Concrete entries per the audit list above.
- D-54: In-network verify one-shot curls /metrics; asserts node_cpu_seconds_total in body.
- D-55: NO vault keys added. node_exporter has no auth surface.
- Pitfall 5 N/A (not OTel), Pitfall 6 partial (TZ default Etc/UTC), Pitfall 8 (handler-driven restart), Pitfall 9 (grep gates).
</phase_decisions_inline>
</context>

<tasks>

<task type="auto" id="03-01-01">
  <name>Task 1: Create node_exporter role skeleton mirroring roles/mimir/ layout exactly</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/mimir/tasks/main.yml
    roles/mimir/handlers/main.yml
    roles/mimir/meta/main.yml
    roles/mimir/README.md
    roles/README.md
    .planning/phases/03-ingest-plane/03-CONTEXT.md
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Create the directory tree `roles/node_exporter/{defaults,tasks,handlers,meta}/` (no templates/ subdir -- node_exporter is CLI-flag-driven, no rendered config; no vars/ subdir -- N/A in M1). Create empty/skeleton files:
  - roles/node_exporter/defaults/main.yml (skeleton header comment block)
  - roles/node_exporter/tasks/main.yml (skeleton comment header pointing at canonical mimir template)
  - roles/node_exporter/tasks/verify.yml (skeleton comment header)
  - roles/node_exporter/handlers/main.yml (skeleton comment header)
  - roles/node_exporter/meta/main.yml (minimal galaxy_info per the Phase-2 mimir shape -- description names node_exporter v1.11.1 host-metrics, license MIT, collections community.docker + ansible.builtin)
  - roles/node_exporter/README.md (skeleton with OPS-03 headings in the canonical order; per D-25 reinterpretation, the "Deviations from upstream INSPQ" section is the one place "INSPQ" is allowed in the role's files)

Use `ansible-playbook` syntax-check-clean YAML (`---` document marker, two-space indent). Match mimir's exact filename casing (`main.yml` not `main.yaml`).
  </action>
  <verify>
    <automated>test -d roles/node_exporter/defaults &amp;&amp; test -d roles/node_exporter/tasks &amp;&amp; test -d roles/node_exporter/handlers &amp;&amp; test -d roles/node_exporter/meta &amp;&amp; test -f roles/node_exporter/defaults/main.yml &amp;&amp; test -f roles/node_exporter/tasks/main.yml &amp;&amp; test -f roles/node_exporter/tasks/verify.yml &amp;&amp; test -f roles/node_exporter/handlers/main.yml &amp;&amp; test -f roles/node_exporter/meta/main.yml &amp;&amp; test -f roles/node_exporter/README.md &amp;&amp; grep -q "^galaxy_info:" roles/node_exporter/meta/main.yml &amp;&amp; grep -q "license: MIT" roles/node_exporter/meta/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] `test -d roles/node_exporter/{defaults,tasks,handlers,meta}` -- all four dirs exist
    - [ ] `test -f roles/node_exporter/{defaults/main.yml,tasks/main.yml,tasks/verify.yml,handlers/main.yml,meta/main.yml,README.md}` -- six required files exist
    - [ ] `grep -q "^galaxy_info:" roles/node_exporter/meta/main.yml`
    - [ ] `grep -q "license: MIT" roles/node_exporter/meta/main.yml`
    - [ ] `grep -q "community.docker" roles/node_exporter/meta/main.yml` AND `grep -q "ansible.builtin" roles/node_exporter/meta/main.yml`
    - [ ] No `templates/` or `vars/` subdir (node_exporter is CLI-only)
    - [ ] Files begin with `---` document marker
  </acceptance_criteria>
  <done>Role skeleton on disk; meta/main.yml has galaxy_info { role_name: node_exporter, license: MIT, platforms Ubuntu jammy/noble + Debian bookworm, galaxy_tags metrics/node-exporter/observability/telemetron }, dependencies: [], collections: [community.docker, ansible.builtin]; other YAML files contain only header comments (real content lands in subsequent tasks).</done>
</task>

<task type="auto" id="03-01-02" tdd="false">
  <name>Task 2: Populate defaults/main.yml with role-tuned values (image pin, ports, no-host-publish, conditional-HEALTHCHECK, hardening knobs)</name>
  <read_first>
    roles/mimir/defaults/main.yml
    roles/node_exporter/defaults/main.yml
    inventory/example-homelab/group_vars/all/network.yml
    inventory/example-homelab/group_vars/all/storage.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/phases/03-ingest-plane/03-CONTEXT.md
  </read_first>
  <action>
Write `roles/node_exporter/defaults/main.yml` mirroring `roles/mimir/defaults/main.yml`'s section structure and inline-comment density. Every value must be a concrete literal -- no placeholders.

Required keys (verbatim):

```yaml
# ---
# roles/node_exporter/defaults/main.yml
# node_exporter role tunables. Override per-environment in
# inventory/<env>/group_vars/all/node_exporter.yml.
#
# node_exporter v1.11.1 -- host metrics (CPU, memory, disk, network, FS)
# on :9100/metrics. Scraped by Phase-3 Prometheus (Plan 03-03) over the
# telemetron Docker bridge.

# --- Image pin (OPS-01) ---
# Quay registry pin matches Phase-1 alertmanager convention; avoids Docker Hub
# rate-limit risk for unauth pulls. See RESEARCH.md Finding 6.
node_exporter_image: quay.io/prometheus/node-exporter
node_exporter_image_tag: "v1.11.1"

# --- Container identity ---
# DNS name on the telemetron network. Plan 03-03 Prometheus scrapes
# http://{{ node_exporter_container_name }}:9100/metrics.
node_exporter_container_name: node-exporter

# --- Host port publishing (D-30) ---
node_exporter_publish_host: "{{ node_exporter_publish_host | default(false) }}"

# --- Port matrix ---
node_exporter_port: 9100

# --- Network ---
node_exporter_network: "{{ telemetron_network | default('telemetron') }}"

# --- Timezone (OPS-06; Pitfall 6) ---
node_exporter_tz: "{{ telemetron_tz | default('Etc/UTC') }}"

# --- Restart policy (OPS-06) ---
node_exporter_restart_policy: unless-stopped

# --- Resource limits (homelab-safe) ---
node_exporter_memory_limit: 128m

# --- Container hardening (Claude's Discretion; INSPQ-kept-improved set) ---
# When true (default), applies the upstream INSPQ security hardening set:
# read-only rootfs, drop ALL caps, add DAC_READ_SEARCH, no-new-privileges,
# tmpfs /tmp, pids_limit 512. Operators can flip to false per environment
# (e.g. RHEL SELinux interactions).
node_exporter_container_hardening_enabled: true

# --- Healthcheck approach (conditional pattern; RESEARCH Open Question Q4) ---
# node_exporter image is built FROM scratch -- no shell, no wget. Image
# probe at execute time picks the outcome:
#   Outcome A: native --health flag (unlikely; verify with --help)
#   Outcome B: only --version (binary-alive proxy) -- DEFAULT
#   Outcome C: nothing useful -- set node_exporter_healthcheck_enabled: false
# In all three, the verify task's in-network curl to /metrics is the
# authoritative readiness gate.
node_exporter_healthcheck_enabled: true
node_exporter_healthcheck_test: ["CMD", "/bin/node_exporter", "--version"]
node_exporter_healthcheck_interval: 15s
node_exporter_healthcheck_timeout: 5s
node_exporter_healthcheck_retries: 5
node_exporter_healthcheck_start_period: 10s

# --- Verify pre-poll (D-10a) ---
# 60s total budget = 30 retries x 2s. node_exporter cold-start is fast
# (just open /proc + start HTTP server).
node_exporter_health_retries: 30
node_exporter_health_delay: 2

# --- Curl image pin for the verify one-shot (OPS-01) ---
node_exporter_curl_image: curlimages/curl
node_exporter_curl_image_tag: "8.10.1"
```

Use the EXACT key names listed above -- they are referenced by tasks/main.yml + tasks/verify.yml + handlers/main.yml downstream. No alphabetical sorting -- preserve the section ordering shown (mirrors roles/mimir defaults).
  </action>
  <verify>
    <automated>grep -q '^node_exporter_image: quay.io/prometheus/node-exporter$' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q '^node_exporter_image_tag: "v1.11.1"$' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q '^node_exporter_container_name: node-exporter$' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q '^node_exporter_port: 9100$' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q '^node_exporter_publish_host:' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q '^node_exporter_restart_policy: unless-stopped$' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q '^node_exporter_healthcheck_enabled: true$' roles/node_exporter/defaults/main.yml &amp;&amp; grep -q 'node_exporter_container_hardening_enabled' roles/node_exporter/defaults/main.yml &amp;&amp; ! grep -qE ':\s*latest' roles/node_exporter/defaults/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Exact image pin: `grep -q '^node_exporter_image: quay.io/prometheus/node-exporter$'` AND `grep -q '^node_exporter_image_tag: "v1.11.1"$'`
    - [ ] Exact container name `node-exporter` (NOT `node_exporter` -- dashes for Docker DNS): `grep -q '^node_exporter_container_name: node-exporter$'`
    - [ ] Port pin: `grep -q '^node_exporter_port: 9100$'`
    - [ ] No-host-publish default present: `grep -q '^node_exporter_publish_host:' roles/node_exporter/defaults/main.yml`
    - [ ] Restart policy `unless-stopped` (OPS-06): `grep -q '^node_exporter_restart_policy: unless-stopped$'`
    - [ ] TZ aliases telemetron_tz (Etc/UTC default): `grep -q "telemetron_tz" roles/node_exporter/defaults/main.yml`
    - [ ] Conditional healthcheck knob present: `grep -q '^node_exporter_healthcheck_enabled: true$'`
    - [ ] Hardening knob declared: `grep -q '^node_exporter_container_hardening_enabled: true$'`
    - [ ] Image-pin gate: `! grep -qE ':\s*latest' roles/node_exporter/defaults/main.yml` (zero `:latest` references)
    - [ ] Curl image pin for verify: `grep -q '^node_exporter_curl_image_tag: "8.10.1"$'`
  </acceptance_criteria>
  <done>defaults/main.yml has every key the downstream tasks consume; all literals match the RESEARCH/CONTEXT spec; no floating tags; section ordering mirrors roles/mimir.</done>
</task>

<task type="auto" id="03-01-03" tdd="false">
  <name>Task 3: Write tasks/main.yml -- pull image, run container with bind-mounts + pid_mode host + hardening, include verify</name>
  <read_first>
    roles/mimir/tasks/main.yml
    roles/loki/tasks/main.yml
    roles/node_exporter/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/research/PITFALLS.md
  </read_first>
  <action>
Write `roles/node_exporter/tasks/main.yml` modeled on `roles/mimir/tasks/main.yml`. node_exporter has NO rendered config (CLI-flag driven), so SKIP the "ensure config dir" and "render config" steps that mimir has -- start at "pull image".

Concrete sequence:

1. `community.docker.docker_image` pull task: image `{{ node_exporter_image }}:{{ node_exporter_image_tag }}`, `source: pull`, `force_source: false`. Tags: `[node_exporter]`.

2. `community.docker.docker_container` run task with these explicit fields:
   - `name: "{{ node_exporter_container_name }}"`
   - `image: "{{ node_exporter_image }}:{{ node_exporter_image_tag }}"`
   - `state: started`
   - `recreate: false`           # D-19 / Pitfall 8: never recreate to "restart"
   - `restart_policy: "{{ node_exporter_restart_policy }}"`
   - `memory: "{{ node_exporter_memory_limit }}"`
   - `pid_mode: host`           # Required for some collectors per RESEARCH Finding 6
   - `read_only: "{{ node_exporter_container_hardening_enabled | bool }}"`
   - `cap_drop: "{{ ['ALL'] if (node_exporter_container_hardening_enabled | bool) else omit }}"`
   - `capabilities: "{{ ['DAC_READ_SEARCH'] if (node_exporter_container_hardening_enabled | bool) else omit }}"`
   - `security_opts: "{{ ['no-new-privileges:true'] if (node_exporter_container_hardening_enabled | bool) else omit }}"`
   - `tmpfs: "{{ ['/tmp'] if (node_exporter_container_hardening_enabled | bool) else omit }}"`
   - `pids_limit: "{{ 512 if (node_exporter_container_hardening_enabled | bool) else omit }}"`
   - `networks: [{ name: "{{ node_exporter_network }}", aliases: ["{{ node_exporter_container_name }}"] }]`
   - `published_ports:` -- triple-conditional Jinja from roles/mimir lines 64-73 verbatim, substituting node_exporter vars:
     ```
     published_ports: >-
       {{
         (
           [ node_exporter_port | string + ':' + node_exporter_port | string ]
           if node_exporter_publish_host is sameas true else
           [ '127.0.0.1:' + node_exporter_port | string + ':' + node_exporter_port | string ]
           if node_exporter_publish_host == '127.0.0.1' else
           []
         )
       }}
     ```
   - `command:` -- VERBATIM list from RESEARCH Finding 6:
     ```
     - "--path.procfs=/host/proc"
     - "--path.sysfs=/host/sys"
     - "--path.rootfs=/host/root"
     - "--collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+|var/lib/kubelet/.+)($|/)"
     - "--collector.filesystem.fs-types-exclude=^(autofs|binfmt_misc|bpf|cgroup2?|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|iso9660|mqueue|nsfs|overlay|proc|procfs|pstore|rpc_pipefs|securityfs|selinuxfs|squashfs|sysfs|tracefs)$"
     - "--web.listen-address=0.0.0.0:{{ node_exporter_port }}"
     ```
   - `mounts:` -- three bind-mounts (NOT `volumes:` -- use `mounts:` form per mimir pattern):
     - `{ source: /proc, target: /host/proc, type: bind, read_only: true }`
     - `{ source: /sys,  target: /host/sys,  type: bind, read_only: true }`
     - `{ source: /,     target: /host/root, type: bind, read_only: true, propagation: rslave }`
   - `healthcheck:` -- conditional via the mimir vars-form pattern (lines 89-98):
     ```
     healthcheck: "{{ node_exporter_container_healthcheck if (node_exporter_healthcheck_enabled | bool) else omit }}"
     ```
     with vars: section computing `node_exporter_container_healthcheck: { test, interval, timeout, retries, start_period }`.
   - `env: { TZ: "{{ node_exporter_tz }}" }`
   - tags: `[node_exporter, node_exporter-container]`

3. Final task (D-32): `ansible.builtin.include_tasks: verify.yml` with tags `[node_exporter, node_exporter-verify]`.

All task `name:` strings ENGLISH; all comments ENGLISH; no `state: restarted` ANYWHERE (Pitfall 8). No `volumes:` short-form -- use `mounts:` per mimir convention.
  </action>
  <verify>
    <automated>grep -q "community.docker.docker_image" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q "community.docker.docker_container" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q "pid_mode: host" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q "include_tasks: verify.yml" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q -- "--path.procfs=/host/proc" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q -- "--path.sysfs=/host/sys" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q -- "--path.rootfs=/host/root" roles/node_exporter/tasks/main.yml &amp;&amp; ! grep -qE "state:\s*restarted" roles/node_exporter/tasks/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/node_exporter/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] `grep -q "community.docker.docker_image" roles/node_exporter/tasks/main.yml` (pull task present)
    - [ ] `grep -q "community.docker.docker_container" roles/node_exporter/tasks/main.yml` (run task present)
    - [ ] `grep -q "pid_mode: host" roles/node_exporter/tasks/main.yml` (Finding 6 requirement)
    - [ ] `grep -q -- "--path.procfs=/host/proc" roles/node_exporter/tasks/main.yml` AND `grep -q -- "--path.sysfs=/host/sys" roles/node_exporter/tasks/main.yml` AND `grep -q -- "--path.rootfs=/host/root" roles/node_exporter/tasks/main.yml` -- all three flags present verbatim
    - [ ] `grep -q "/host/proc" roles/node_exporter/tasks/main.yml` AND `grep -q "/host/sys" roles/node_exporter/tasks/main.yml` AND `grep -q "/host/root" roles/node_exporter/tasks/main.yml` (three bind-mounts)
    - [ ] `grep -q "propagation: rslave" roles/node_exporter/tasks/main.yml` (root bind-mount propagation)
    - [ ] `grep -q "node_exporter_container_hardening_enabled" roles/node_exporter/tasks/main.yml` (hardening conditional plumbed)
    - [ ] `grep -q "no-new-privileges:true" roles/node_exporter/tasks/main.yml` (hardening set applied)
    - [ ] `grep -q "include_tasks: verify.yml" roles/node_exporter/tasks/main.yml` (verify wired as final task)
    - [ ] D-19 enforcement: `! grep -qE "state:\s*restarted" roles/node_exporter/tasks/main.yml` (zero matches)
    - [ ] ASCII-only: `! grep -qP '[^\x00-\x7F]' roles/node_exporter/tasks/main.yml`
    - [ ] All task `name:` strings ASCII English: `grep -E "^- name:" roles/node_exporter/tasks/main.yml | grep -qvP '[^\x00-\x7F]' || true` (all task names are pure ASCII)
    - [ ] Conditional healthcheck omit-magic-value present: `grep -q "if (node_exporter_healthcheck_enabled | bool) else omit" roles/node_exporter/tasks/main.yml`
  </acceptance_criteria>
  <done>tasks/main.yml runs pull -> docker_container with all bind-mounts, hardening conditionals, port-publish triple-conditional, conditional healthcheck, include_tasks verify -- mirrors mimir layout shape modulo node_exporter-specific (no config render, pid_mode host, three bind-mounts).</done>
</task>

<task type="auto" id="03-01-04" tdd="false">
  <name>Task 4: Write tasks/verify.yml -- D-10a poll + in-network /metrics curl asserting node_cpu_seconds_total</name>
  <read_first>
    roles/mimir/tasks/verify.yml
    roles/loki/tasks/verify.yml
    roles/node_exporter/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
  </read_first>
  <action>
Write `roles/node_exporter/tasks/verify.yml` modeled on `roles/mimir/tasks/verify.yml` (Steps 1a / 1b / 1c). Three steps:

**Step 1a -- Wait for Docker HEALTHCHECK healthy (when enabled):**
- `community.docker.docker_container_info: { name: "{{ node_exporter_container_name }}" }` register `ne_health_check`.
- `until: >- ne_health_check.container is defined and ne_health_check.container.State is defined and ne_health_check.container.State.Health is defined and ne_health_check.container.State.Health.Status == 'healthy'`
- `retries: "{{ node_exporter_health_retries }}"`, `delay: "{{ node_exporter_health_delay }}"`
- `changed_when: false`
- `when: node_exporter_healthcheck_enabled | bool`
- tags: `[node_exporter, node_exporter-verify]`

**Step 1b -- Wait for State.Running (when healthcheck disabled):**
- Same module call, register `ne_running_check`.
- `until: >- ne_running_check.container is defined and ne_running_check.container.State is defined and ne_running_check.container.State.Running is true`
- Same retries/delay/changed_when/tags.
- `when: not (node_exporter_healthcheck_enabled | bool)`

**Step 2 -- In-network curl to /metrics asserting node_cpu_seconds_total body match (this is THE authoritative gate per D-54):**
Use `community.docker.docker_container` one-shot with:
  - `name: "{{ node_exporter_container_name }}-verify-metrics"`
  - `image: "{{ node_exporter_curl_image }}:{{ node_exporter_curl_image_tag }}"` (curlimages/curl:8.10.1 pinned)
  - `state: started`, `detach: false`, `auto_remove: true`, `recreate: true`, `cleanup: true`
  - `networks: [{ name: "{{ node_exporter_network }}" }]`
  - `entrypoint: ["/bin/sh", "-c"]`
  - `command:` -- single-line shell loop curling /metrics up to 30x (60s total) and grepping body for `node_cpu_seconds_total`:
    ```
    >-
      i=0 ;
      while [ $i -lt 30 ] ; do
        BODY=$(curl -sS -o - -w "HTTPCODE=%{http_code}" http://{{ node_exporter_container_name }}:{{ node_exporter_port }}/metrics 2>/dev/null) ;
        CODE=$(echo "$BODY" | grep -oE 'HTTPCODE=[0-9]+' | cut -d= -f2) ;
        if [ "$CODE" = "200" ] &amp;&amp; echo "$BODY" | grep -q '^node_cpu_seconds_total' ; then echo "metrics_ok=200_with_node_cpu_seconds_total" ; exit 0 ; fi ;
        i=$((i+1)) ;
        sleep 2 ;
      done ;
      echo "node-exporter /metrics never returned 200 with node_cpu_seconds_total within 60s" ;
      exit 1
    ```
  - `register: ne_verify_metrics`
  - `failed_when: ne_verify_metrics.status is defined and ne_verify_metrics.status != 0`
  - `changed_when: false`
  - tags: `[node_exporter, node_exporter-verify]`

All task `name:` strings English. No French. No `state: restarted`. ASCII only.
  </action>
  <verify>
    <automated>grep -q "community.docker.docker_container_info" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "State.Health.Status == 'healthy'" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "State.Running is true" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "auto_remove: true" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "changed_when: false" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "node_cpu_seconds_total" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "/metrics" roles/node_exporter/tasks/verify.yml &amp;&amp; grep -q "telemetron_network\|node_exporter_network" roles/node_exporter/tasks/verify.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/node_exporter/tasks/verify.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Step 1a HEALTHCHECK poll: `grep -q "community.docker.docker_container_info" roles/node_exporter/tasks/verify.yml` AND `grep -q "State.Health.Status == 'healthy'" roles/node_exporter/tasks/verify.yml`
    - [ ] Step 1b running-state fallback: `grep -q "State.Running is true" roles/node_exporter/tasks/verify.yml`
    - [ ] Both 1a and 1b are conditional on the same knob: `grep -c "node_exporter_healthcheck_enabled | bool" roles/node_exporter/tasks/verify.yml` returns >= 2
    - [ ] Step 2 in-network one-shot: `grep -q "auto_remove: true" roles/node_exporter/tasks/verify.yml` AND `grep -q "changed_when: false" roles/node_exporter/tasks/verify.yml` AND `grep -q "recreate: true" roles/node_exporter/tasks/verify.yml`
    - [ ] Step 2 attaches to telemetron network: `grep -q "node_exporter_network" roles/node_exporter/tasks/verify.yml`
    - [ ] Assertion body: `grep -q "node_cpu_seconds_total" roles/node_exporter/tasks/verify.yml` (the load-bearing metric name)
    - [ ] curls `/metrics`: `grep -q "/metrics" roles/node_exporter/tasks/verify.yml`
    - [ ] Failure mode wired: `grep -q "failed_when:" roles/node_exporter/tasks/verify.yml`
    - [ ] ASCII-only: `! grep -qP '[^\x00-\x7F]' roles/node_exporter/tasks/verify.yml`
    - [ ] No restart pattern in verify: `! grep -qE "state:\s*restarted" roles/node_exporter/tasks/verify.yml`
  </acceptance_criteria>
  <done>verify.yml passes a 60s-budget readiness gate, then runs a one-shot curlimages/curl container in-network asserting /metrics returns 200 with `node_cpu_seconds_total` in the body. Step 1a runs when healthcheck enabled; Step 1b runs when disabled. Step 2 always runs.</done>
</task>

<task type="auto" id="03-01-05" tdd="false">
  <name>Task 5: Write handlers/main.yml -- single docker-restart handler (W6 pattern, NEVER state: restarted)</name>
  <read_first>
    roles/mimir/handlers/main.yml
    roles/loki/handlers/main.yml
  </read_first>
  <action>
Write `roles/node_exporter/handlers/main.yml` mirroring `roles/mimir/handlers/main.yml` exactly modulo names. node_exporter has NO rendered config (no template notify points), so this handler is unused in M1 -- but it MUST EXIST per the canonical role-template pattern so future config changes (e.g. command-flag knob additions) can notify without role restructure.

Exact content:

```yaml
# ---
# roles/node_exporter/handlers/main.yml
# Per D-19 / Pitfall 8: container restarts on config change use
# `docker restart <name>`. The module-level state parameter is never
# used for restarts -- force-recreate is non-idempotent.
#
# node_exporter is CLI-flag-driven (no rendered config file in M1), so
# this handler is currently unused. It exists for future-compat -- when
# command-flag knobs surface, the run-container task can notify this
# handler on flag changes without role restructure.

- name: Docker restart node_exporter
  ansible.builtin.command:
    cmd: "docker restart {{ node_exporter_container_name }}"
  changed_when: true
  listen: restart node_exporter
```

Use `ansible.builtin.command` (NOT `shell:`). `changed_when: true` -- restart is intentional state mutation. `listen:` declared so notifiers use string form `notify: restart node_exporter`.
  </action>
  <verify>
    <automated>grep -q "^- name: Docker restart node_exporter$" roles/node_exporter/handlers/main.yml &amp;&amp; grep -q "listen: restart node_exporter" roles/node_exporter/handlers/main.yml &amp;&amp; grep -q "ansible.builtin.command:" roles/node_exporter/handlers/main.yml &amp;&amp; grep -q "changed_when: true" roles/node_exporter/handlers/main.yml &amp;&amp; ! grep -q "state: restarted" roles/node_exporter/handlers/main.yml &amp;&amp; ! grep -qP '[^\x00-\x7F]' roles/node_exporter/handlers/main.yml</antomated>
  </verify>
  <acceptance_criteria>
    - [ ] Handler name pattern: `grep -q "^- name: Docker restart node_exporter$" roles/node_exporter/handlers/main.yml`
    - [ ] Listen string: `grep -q "listen: restart node_exporter" roles/node_exporter/handlers/main.yml`
    - [ ] Module: `grep -q "ansible.builtin.command:" roles/node_exporter/handlers/main.yml` (NOT shell)
    - [ ] Idempotent intent: `grep -q "changed_when: true" roles/node_exporter/handlers/main.yml`
    - [ ] D-19 enforced: `! grep -q "state: restarted" roles/node_exporter/handlers/main.yml`
    - [ ] ASCII-only: `! grep -qP '[^\x00-\x7F]' roles/node_exporter/handlers/main.yml`
    - [ ] Single handler (file has exactly one `- name:` at column 0): `grep -c "^- name:" roles/node_exporter/handlers/main.yml` returns `1`
  </acceptance_criteria>
  <done>handlers/main.yml has the canonical single restart handler; file is unused in M1 but exists per the role-template convention.</done>
</task>

<task type="auto" id="03-01-06" tdd="false">
  <name>Task 6: Write README.md with OPS-03 schema + D-25 deviations + conditional-HEALTHCHECK explanation</name>
  <read_first>
    roles/mimir/README.md
    roles/loki/README.md
    roles/node_exporter/defaults/main.yml
    .planning/phases/03-ingest-plane/03-RESEARCH.md
    .planning/research/PITFALLS.md
  </read_first>
  <action>
Write `roles/node_exporter/README.md` mirroring `roles/mimir/README.md`'s exact section ordering and depth. ALL headings ENGLISH; D-25 Deviations section is the one and only place where the upstream-project name appears.

Required H2 sections in order:

1. `# roles/node_exporter` -- one-paragraph overview (deploys quay.io/prometheus/node-exporter:v1.11.1 on the telemetron Docker bridge, scraped by Plan 03-03 Prometheus at http://node-exporter:9100/metrics).

2. `## What this role does` -- numbered list of 1) pull image, 2) run container with three bind-mounts + pid_mode host + hardening set + conditional healthcheck, 3) verify task polls health/running state then curls /metrics asserting `node_cpu_seconds_total`.

3. `## Variables` -- markdown table of every defaults/main.yml key with default value + purpose column. Include all keys from Task 2.

4. `## Vault keys` -- "None (per Phase 3 D-55). node_exporter has no auth surface. `inventory/example-homelab/group_vars/all/vault.yml.example` is unchanged by this role."

5. `## Tags` -- "- `node_exporter` -- runs the whole role (D-24 single tag per role)"

6. `## Modes` -- "Single mode (containerized via Docker per CLAUDE.md). Stock collectors enabled; systemd and textfile collectors are deferred opt-ins."

7. `## Volumes` -- "None (node_exporter is stateless). Three host RO bind-mounts: `/proc` -> `/host/proc`, `/sys` -> `/host/sys`, `/` -> `/host/root` (propagation rslave)."

8. `## Healthcheck` -- explain the conditional-HEALTHCHECK pattern (Outcome A native --health, Outcome B --version proxy default, Outcome C disabled with State.Running fallback). Mention image probe at execute time: `docker run --rm quay.io/prometheus/node-exporter:v1.11.1 --help | grep -i health`.

9. `## Operator access (no host publish by default per D-30)` -- show SSH local-forward example: `ssh -L 9100:localhost:9100 <host>` then `curl http://localhost:9100/metrics`.

10. `## Security model` -- list: no host publish default, container hardening enabled (read-only rootfs, dropped caps, no-new-privileges, tmpfs /tmp, pids_limit 512), pid_mode: host is REQUIRED for collectors and the kernel-level access is read-only via bind-mounts.

11. `## Idempotency` -- standard OPS-04 paragraph; show the two-run command pattern.

12. `## Port-acceptance gates` -- enumerate the six (image-pin, grep, non-ASCII, vault-N/A, idempotency, healthcheck+restart, README) and state each passes.

13. `## Deviations from upstream INSPQ (D-25)` -- the audit section. Mandatory bulleted entries (research surfaces these):
    - Dropped: `node_exporter_deployment_method: native` (Docker-only per CLAUDE.md), LVM tasks, UFW rules, French task names, default-on host publish, textfile collector + LVM-on-textfile assumption, `America/Toronto` TZ, `:latest` image tag, `node_explorer_*` upstream typo variants.
    - Replaced: `--path.rootfs=/rootfs` -> `--path.rootfs=/host/root` (current upstream README); `prom/node-exporter` Docker Hub -> `quay.io/prometheus/node-exporter` Quay (matches Phase-1 alertmanager registry choice).
    - Added: D-10a HEALTHCHECK pre-poll + D-54 in-network /metrics verify (upstream had no verify step), conditional `node_exporter_publish_host: false` security default, pinned image tag v1.11.1.
    - Kept (got it right): `pid_mode: host`, container hardening set (`read_only`, `cap_drop: [ALL]`, `capabilities: [DAC_READ_SEARCH]`, `no-new-privileges:true`, tmpfs `/tmp`, `pids_limit: 512`) -- guarded by `node_exporter_container_hardening_enabled` knob so operators with SELinux quirks can flip off.

14. `## Bring your own collectors` -- short paragraph: stock collectors only in M1; systemd / textfile / `--collector.<name>` opt-ins are deferred (operators can extend command flags via a future knob; tracked in CONTEXT.md Deferred Ideas).

15. `## Deprecation notes` -- "None."

ASCII-only outside of the `## Deviations from upstream INSPQ (D-25)` section (the audit section is the documented exemption per Phase-2 D-25-interpretation -- code/config files stay clean but the README's audit section is explicitly allowed to name the upstream project).
  </action>
  <verify>
    <automated>grep -qE "^# roles/node_exporter" roles/node_exporter/README.md &amp;&amp; grep -q "^## What this role does" roles/node_exporter/README.md &amp;&amp; grep -q "^## Variables" roles/node_exporter/README.md &amp;&amp; grep -q "^## Vault keys" roles/node_exporter/README.md &amp;&amp; grep -q "^## Tags" roles/node_exporter/README.md &amp;&amp; grep -q "^## Modes" roles/node_exporter/README.md &amp;&amp; grep -q "^## Volumes" roles/node_exporter/README.md &amp;&amp; grep -q "^## Healthcheck" roles/node_exporter/README.md &amp;&amp; grep -q "^## Operator access" roles/node_exporter/README.md &amp;&amp; grep -q "^## Security model" roles/node_exporter/README.md &amp;&amp; grep -q "^## Idempotency" roles/node_exporter/README.md &amp;&amp; grep -q "^## Port-acceptance gates" roles/node_exporter/README.md &amp;&amp; grep -q "^## Deviations from upstream INSPQ" roles/node_exporter/README.md &amp;&amp; grep -q "v1.11.1" roles/node_exporter/README.md &amp;&amp; grep -q "quay.io/prometheus/node-exporter" roles/node_exporter/README.md &amp;&amp; grep -q "ssh -L 9100" roles/node_exporter/README.md</automated>
  </verify>
  <acceptance_criteria>
    - [ ] All 13 required H2 headings present (the grep set in verify covers each)
    - [ ] Image pin documented: `grep -q "v1.11.1" roles/node_exporter/README.md` AND `grep -q "quay.io/prometheus/node-exporter" roles/node_exporter/README.md`
    - [ ] SSH local-forward example: `grep -q "ssh -L 9100" roles/node_exporter/README.md`
    - [ ] D-25 audit has >= 3 bullet categories: `grep -cE "^- (Dropped:|Replaced:|Added:|Kept)" roles/node_exporter/README.md` returns >= 3
    - [ ] Conditional-HEALTHCHECK pattern explained: `grep -q "Outcome A" roles/node_exporter/README.md` AND `grep -q "Outcome B" roles/node_exporter/README.md` AND `grep -q "Outcome C" roles/node_exporter/README.md`
    - [ ] Security model lists pid_mode: host justification: `grep -q "pid_mode" roles/node_exporter/README.md`
    - [ ] Vault keys section says None / D-55: `grep -q "D-55" roles/node_exporter/README.md`
    - [ ] Bind-mount triple documented: `grep -q "/host/proc" roles/node_exporter/README.md` AND `grep -q "/host/sys" roles/node_exporter/README.md` AND `grep -q "/host/root" roles/node_exporter/README.md`
  </acceptance_criteria>
  <done>README mirrors mimir schema; D-25 deviations section documents the audit; image probe command documented; SSH local-forward operator access path documented.</done>
</task>

<task type="auto" id="03-01-07" tdd="false">
  <name>Task 7: Create inventory/example-homelab/group_vars/all/node_exporter.yml + wire role into playbooks/deploy_docker.yml after mimir</name>
  <read_first>
    inventory/example-homelab/group_vars/all/mimir.yml
    inventory/example-homelab/group_vars/all/network.yml
    playbooks/deploy_docker.yml
    .planning/phases/03-ingest-plane/03-CONTEXT.md
  </read_first>
  <action>
**Step A: Create `inventory/example-homelab/group_vars/all/node_exporter.yml`** mirroring `mimir.yml`'s shape. Surface the high-signal operator knobs (publish flag + hardening flag + healthcheck enabled flag). Exact content:

```yaml
# ---
# Telemetron -- node_exporter operator knobs (Phase 3, D-30, D-55)
# Role-specific overrides for the `node_exporter` role.
# See roles/node_exporter/defaults/main.yml for the full default surface.

# Default: zero host port publish. Operator access via SSH local-forward:
#   ssh -L 9100:localhost:9100 <host>
node_exporter_publish_host: false

# Container hardening (read-only rootfs, drop ALL caps, add DAC_READ_SEARCH,
# no-new-privileges, tmpfs /tmp, pids_limit 512). Flip to false on hosts
# where SELinux or other layers interact poorly.
node_exporter_container_hardening_enabled: true

# Conditional HEALTHCHECK (RESEARCH Q4). Image probe outcomes:
#   Outcome A: --health flag present (unlikely)
#   Outcome B: --version proxy (default)
#   Outcome C: flip to false; rely on State.Running + verify /metrics curl
node_exporter_healthcheck_enabled: true
```

**Step B: Edit `playbooks/deploy_docker.yml`** to append `node_exporter` role entry after `mimir` per D-41 order. Insert this block before the `# Subsequent phase plans extend this list...` comment:

```yaml
    - role: node_exporter
      tags:
        - node_exporter
```

Update the trailing comment block to reflect the new state -- change `Phase 3: prometheus, opentelemetry, fluentbit, node_exporter` to `Phase 3: opentelemetry, prometheus, fluentbit (node_exporter now wired)` so the comment stays factual.

Run `ansible-playbook --syntax-check playbooks/deploy_docker.yml` and expect exit 0.
  </action>
  <verify>
    <automated>test -f inventory/example-homelab/group_vars/all/node_exporter.yml &amp;&amp; grep -q "^node_exporter_publish_host: false$" inventory/example-homelab/group_vars/all/node_exporter.yml &amp;&amp; grep -q "^node_exporter_container_hardening_enabled: true$" inventory/example-homelab/group_vars/all/node_exporter.yml &amp;&amp; grep -q "    - role: node_exporter$" playbooks/deploy_docker.yml &amp;&amp; grep -qE "^\s*- node_exporter\s*$" playbooks/deploy_docker.yml &amp;&amp; ansible-playbook --syntax-check playbooks/deploy_docker.yml 2>&amp;1 | grep -q "playbook:.*deploy_docker.yml"</automated>
  </verify>
  <acceptance_criteria>
    - [ ] Inventory file exists: `test -f inventory/example-homelab/group_vars/all/node_exporter.yml`
    - [ ] Inventory file contains expected knob defaults: `grep -q "^node_exporter_publish_host: false$"` AND `grep -q "^node_exporter_container_hardening_enabled: true$"` AND `grep -q "^node_exporter_healthcheck_enabled: true$"`
    - [ ] Playbook references the role: `grep -q "    - role: node_exporter$" playbooks/deploy_docker.yml`
    - [ ] Single-tag declaration (D-24): `grep -qE "^\s*- node_exporter\s*$" playbooks/deploy_docker.yml`
    - [ ] D-41 order: node_exporter row appears AFTER `- role: mimir` row -- `awk '/- role: mimir/{m=NR}/- role: node_exporter/{n=NR}END{exit !(m<n)}' playbooks/deploy_docker.yml` exits 0
    - [ ] Syntax check passes: `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0
    - [ ] ASCII-only on the inventory file: `! grep -qP '[^\x00-\x7F]' inventory/example-homelab/group_vars/all/node_exporter.yml`
  </acceptance_criteria>
  <done>Operator inventory file lands at the canonical location; playbook role list grows by exactly one entry in D-41 order; syntax check passes.</done>
</task>

<task type="auto" id="03-01-08" tdd="false">
  <name>Task 8: Tick roles/README.md status row + run all six port-acceptance gates</name>
  <read_first>
    roles/README.md
    roles/node_exporter/defaults/main.yml
    roles/node_exporter/tasks/main.yml
    roles/node_exporter/handlers/main.yml
    roles/node_exporter/README.md
  </read_first>
  <action>
**Step A: Update `roles/README.md`** -- change the `node_exporter` row's Ported column from `☐` to `☑`. Find the row matching `| \`node_exporter\`` and replace the trailing `| ☐ |` with `| ☑ |`. Touch nothing else in roles/README.md.

**Step B: Run all six port-acceptance gates** locally (these are the verification commands that prove M1-ready):

1. **Image-pin gate (OPS-01):** `grep -rE 'image:.*:latest' roles/node_exporter/` returns NO matches.
2. **INSPQ grep gate (Pitfall 9, D-21):** `grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/node_exporter/` returns matches ONLY in the README's `## Deviations from upstream INSPQ` section (Phase-2 D-25 reinterpretation -- README-documented audit allowed; code/config files must be clean). Use `--include='*.yml' --include='*.yaml' --include='*.j2'` to restrict the gate to non-README files for the zero-tolerance check.
3. **Non-ASCII gate (OPS-05):** `grep -rPl '[^\x00-\x7F]' roles/node_exporter/ --include='*.yml' --include='*.yaml' --include='*.j2'` returns NO matches.
4. **Vault gate (OPS-02):** `! grep -rE '{{ *vault_' roles/node_exporter/` -- node_exporter has no vault refs per D-55; zero matches expected.
5. **Idempotency gate (OPS-04, Pitfall 8):** No `state: restarted` anywhere: `! grep -rE 'state:\s*restarted' roles/node_exporter/`. The live two-run idempotency check (`changed=0` on second `ansible-playbook` run) is a UAT-time check, not a static check.
6. **Healthcheck + restart-policy gate (OPS-06):** `grep -q "restart_policy:" roles/node_exporter/tasks/main.yml` AND `grep -q "healthcheck:" roles/node_exporter/tasks/main.yml`.
7. **README gate (OPS-03):** all required H2 sections present (validated in Task 6).

If any gate fails, fix in the relevant prior task's file -- do not paper over.
  </action>
  <verify>
    <automated>grep -qE "^\| \`node_exporter\`\s*\|.*\|\s*☑\s*\|" roles/README.md &amp;&amp; ! grep -rE 'image:.*:latest' roles/node_exporter/ &amp;&amp; ! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/node_exporter/ --include='*.yml' --include='*.yaml' --include='*.j2' &amp;&amp; ! grep -rPl '[^\x00-\x7F]' roles/node_exporter/ --include='*.yml' --include='*.yaml' --include='*.j2' &amp;&amp; ! grep -rE '{{ *vault_' roles/node_exporter/ &amp;&amp; ! grep -rE 'state:\s*restarted' roles/node_exporter/ &amp;&amp; grep -q "restart_policy:" roles/node_exporter/tasks/main.yml &amp;&amp; grep -q "healthcheck:" roles/node_exporter/tasks/main.yml</automated>
  </verify>
  <acceptance_criteria>
    - [ ] roles/README.md row ticked: `grep -qE "^\| \`node_exporter\`\s*\|.*\|\s*☑\s*\|" roles/README.md`
    - [ ] Image-pin gate (OPS-01): `! grep -rE 'image:.*:latest' roles/node_exporter/`
    - [ ] INSPQ grep gate (code/config only): `! grep -riE 'inspq|qc\.ca|montreal|quebec|francais|french|/srv/nfs/inspq|vault_inspq' roles/node_exporter/ --include='*.yml' --include='*.yaml' --include='*.j2'`
    - [ ] Non-ASCII gate: `! grep -rPl '[^\x00-\x7F]' roles/node_exporter/ --include='*.yml' --include='*.yaml' --include='*.j2'`
    - [ ] Vault N/A per D-55: `! grep -rE '{{ *vault_' roles/node_exporter/`
    - [ ] D-19/Pitfall-8 idempotency: `! grep -rE 'state:\s*restarted' roles/node_exporter/`
    - [ ] OPS-06 restart-policy declared: `grep -q "restart_policy:" roles/node_exporter/tasks/main.yml`
    - [ ] OPS-06 healthcheck declared: `grep -q "healthcheck:" roles/node_exporter/tasks/main.yml`
  </acceptance_criteria>
  <done>roles/README.md row is `☑`; all six gates pass on `roles/node_exporter/`; plan is M1-ready -- live UAT confirmation deferred to the Phase 3 verification phase.</done>
</task>

</tasks>

<verification>
**Static verification (run after all tasks complete):**

1. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
2. All eight task-level acceptance_criteria pass (greps above).
3. `find roles/node_exporter -type f` returns exactly: defaults/main.yml, handlers/main.yml, meta/main.yml, tasks/main.yml, tasks/verify.yml, README.md.
4. `find roles/node_exporter -type d` returns: defaults, handlers, meta, tasks (NO templates/, NO vars/).
5. `grep -c "include_tasks: verify.yml" roles/node_exporter/tasks/main.yml` returns `1` (verify wired as final task per D-32).
6. roles/README.md has node_exporter row ticked.

**Live verification (deferred to Phase 3 verification stage):**

7. On a fresh-from-Phase-2 homelab host: `ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags node_exporter --ask-vault-pass` completes; `docker inspect node-exporter --format '{{.State.Health.Status}}'` returns `healthy` (Outcome A/B) OR `docker inspect node-exporter --format '{{.State.Running}}'` returns `true` (Outcome C); `docker inspect node-exporter --format '{{.HostConfig.RestartPolicy.Name}}'` returns `unless-stopped`.
8. The verify task's curl one-shot completes with status 0 (asserts /metrics returns 200 and body contains `node_cpu_seconds_total`).
9. Second back-to-back run reports `changed=0` for the node_exporter tag.

</verification>

<success_criteria>
- [ ] `roles/node_exporter/` directory contains the canonical six-file layout (defaults, tasks/main, tasks/verify, handlers, meta, README) mirroring `roles/mimir/`.
- [ ] All eight task-level acceptance_criteria pass.
- [ ] All six per-role port-acceptance gates pass.
- [ ] roles/README.md status table row for node_exporter shows `☑`.
- [ ] playbooks/deploy_docker.yml contains a `role: node_exporter` entry positioned after `role: mimir`, with tag `node_exporter`.
- [ ] inventory/example-homelab/group_vars/all/node_exporter.yml exists with the three operator knobs (publish_host, hardening_enabled, healthcheck_enabled) at their researched defaults.
- [ ] `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
- [ ] INGEST-04 marked satisfied in this plan's `requirements` field; live UAT proof deferred to Phase 3 verification.
</success_criteria>

<output>
After completion, create `.planning/phases/03-ingest-plane/03-01-node-exporter-SUMMARY.md` documenting the role layout, the image pin choice (quay.io vs Docker Hub), the conditional-HEALTHCHECK image-probe outcome, the D-25 deviations recorded, and any execute-time surprises.
</output>
</content>
</invoke>