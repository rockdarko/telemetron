# Phase 14: Orchestrators + Leviathan HUMAN-UAT - Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 7 (2 new playbooks + 4 amended task files + 1 new HUMAN-UAT doc)
**Analogs found:** 7 / 7 (every file has at least one strong in-repo analog)

---

## File Classification

| New/Modified File | Type | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `playbooks/backup_docker.yml` | NEW | orchestrator playbook | sequential include_role over 4 roles + shared timestamp set_fact | `playbooks/undeploy_docker.yml` | exact (structural shape) |
| `playbooks/restore_docker.yml` | NEW | orchestrator playbook | confirm-gate -> stop-writers -> include_role -> start-writers | `playbooks/undeploy_docker.yml` (shape) + `roles/garage/tasks/backup.yml` (stop/start loop block) | exact (combined shape) |
| `roles/garage/tasks/backup.yml` | MODIFIED | task file | accept override knob via `set_fact` | self (current shape) — D-191 minimal amend | exact (in-place edit) |
| `roles/prometheus/tasks/backup.yml` | MODIFIED | task file | accept override knob via `set_fact` | self (current shape) — D-191 minimal amend | exact (in-place edit) |
| `roles/grafana/tasks/backup.yml` | MODIFIED | task file | accept override knob via `set_fact` | self (current shape) — D-191 minimal amend | exact (in-place edit) |
| `roles/alertmanager/tasks/backup.yml` | MODIFIED | task file | accept override knob via `set_fact` | self (current shape) — D-191 minimal amend | exact (in-place edit) |
| `14-HUMAN-UAT.md` | NEW | audit doc (markdown) | YAML frontmatter + numbered scenarios | `.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` | exact (verbatim format) |

---

## Pattern Assignments

### 1. `playbooks/backup_docker.yml` (orchestrator, sequential include_role)

**Primary analog:** `playbooks/undeploy_docker.yml`
**Secondary analog:** `playbooks/deploy_docker.yml` (for per-role `tags: <role>` convention SC4)

#### Pattern A — Play scaffold (file path + header docstring)

**Source:** `playbooks/undeploy_docker.yml` lines 1-48
**Excerpt (lines 1-48):**

```yaml
---
# Telemetron -- M1 undeploy orchestrator (Docker target)
#
# Removes the Telemetron observability plane from a single Docker host.
# Invokes 12 per-role tasks/uninstall.yml files in REVERSE of
# deploy_docker.yml's roles: block order (D-149); the `telemetron` Docker
# bridge network is removed in post_tasks below (D-150). ...
# ...
# Usage:
#   ansible-playbook -i inventory/example-homelab \
#                    playbooks/undeploy_docker.yml \
#                    --ask-vault-pass

- name: Telemetron -- undeploy from Docker host
  hosts: telemetron
  gather_facts: true
  become: false

  collections:
    - community.docker

  vars:
    # Opt-in irreversible purge flags. Default false; set via --extra-vars. (D-153)
    telemetron_purge_data: false
    telemetron_purge_host_dirs: false
    telemetron_purge_images: false
```

**How Phase 14 adapts this:** Same docstring style explaining role enumeration, per-role `--tags <role>` re-run, and `--ask-vault-pass` usage; same `hosts: telemetron`, `gather_facts: true`, `become: false`, `collections: [community.docker]`. `vars:` block holds `backup_continue_on_failure: false` (D-184 default). Add play-level `any_errors_fatal: "{{ not (backup_continue_on_failure | default(false) | bool) }}"` (D-184).

#### Pattern B — `tags: always` PLAY-start banner (D-160 / D-186)

**Source:** `playbooks/undeploy_docker.yml` lines 55-70
**Excerpt:**

```yaml
  pre_tasks:
    # D-157 + D-160: PLAY-start WARN banner. Category descriptions (no counts/names)
    # so the banner is stable across role additions. Tagged `always` (Pattern 8)
    # so the banner displays even on --tags <role> targeted runs.
    - name: WARN -- irreversible purge flags status
      ansible.builtin.debug:
        msg: |
          WARNING: irreversible operations status:
            telemetron_purge_data={{ telemetron_purge_data | default(false) }}
              {{ 'all telemetron_* named Docker volumes will be removed' if telemetron_purge_data | default(false) | bool else '(named volumes preserved)' }}
            telemetron_purge_host_dirs={{ telemetron_purge_host_dirs | default(false) }}
              {{ '/opt/telemetron/ parent tree will be removed' if telemetron_purge_host_dirs | default(false) | bool else '(/opt/telemetron/ parent preserved)' }}
            telemetron_purge_images={{ telemetron_purge_images | default(false) }}
              {{ 'all Telemetron-pinned Docker images will be removed' if telemetron_purge_images | default(false) | bool else '(Docker images preserved)' }}
      tags:
        - always
```

**How Phase 14 adapts this (D-186):** Same `ansible.builtin.debug` + multi-line `msg: |` + `tags: [always]` shape. NO `WARNING: irreversible --` prefix (backup is not destructive). Banner lines:
- `Backup destination: {{ backup_dest_root }}/<role>/`
- `backup_continue_on_failure={{ backup_continue_on_failure }}` with category description (`(first role failure will abort the playbook)` if false / `(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)` if true)
- `backup_stop_timeout={{ backup_stop_timeout }}s`

#### Pattern C — D-191 shared-timestamp set_fact (NEW pattern; inline in `pre_tasks`)

**Source (raw shape):** Each per-role `tasks/backup.yml` currently does its own `date -u +%Y%m%dT%H%M%SZ` — e.g., `roles/garage/tasks/backup.yml` lines 79-85:

```yaml
- name: Record UTC timestamp for Garage backup filename (D-179 ISO 8601 basic)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - garage
    - backup
```

**How Phase 14 adapts this (D-191):** Hoist the `date` command to `pre_tasks:` of `backup_docker.yml` ONCE, register as `backup_ts`, then `set_fact: backup_timestamp_shared: "{{ backup_ts.stdout }}"`. Both tasks `tags: always` so they fire under `--tags <role>` invocations too. Pass to each role via `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }`.

#### Pattern D — Per-role `include_role` with `tags: [<role>]` (D-149 + SC4)

**Source:** `playbooks/undeploy_docker.yml` lines 80-275 (the 23 include_role calls)
**Excerpt (representative slice, lines 124-139):**

```yaml
    - name: Invoke alertmanager uninstall
      ansible.builtin.include_role:
        name: alertmanager
        tasks_from: uninstall
      tags:
        - alertmanager

    - name: Invoke alertmanager purge (gated)
      ansible.builtin.include_role:
        name: alertmanager
        tasks_from: purge
      when: >-
        telemetron_purge_data | default(false) | bool
        or telemetron_purge_images | default(false) | bool
      tags:
        - alertmanager
```

**How Phase 14 adapts this:** Same `ansible.builtin.include_role` + `name:` + `tasks_from: backup` + `tags: [<role>]` shape, but only **4 calls** in **forward-deploy order** (garage -> prometheus -> grafana -> alertmanager — NOT reverse, per ROADMAP SC1 and CONTEXT.md "Established Patterns" note). Each call adds `vars: { backup_timestamp_override: "{{ backup_timestamp_shared }}" }`. No `when:` gating (backup is unconditional within its tag scope). Adapted shape:

```yaml
    - name: Invoke garage backup
      ansible.builtin.include_role:
        name: garage
        tasks_from: backup
      vars:
        backup_timestamp_override: "{{ backup_timestamp_shared }}"
      tags:
        - garage
    # ... same shape for prometheus, grafana, alertmanager
```

#### Pattern E — Per-role tag for SC4 (cross-check with `deploy_docker.yml`)

**Source:** `playbooks/deploy_docker.yml` lines 35-72
**Excerpt:**

```yaml
  roles:
    - role: garage
      tags:
        - garage
    - role: loki
      tags:
        - loki
```

**How Phase 14 adapts this:** Confirms the single-element `tags: - <role>` convention (NOT `tags: [<role>, backup]` on the include_role itself — the per-role backup.yml tasks already carry both tags via their block-level tags). The orchestrator-level `tags:` only needs `<role>` so that `--tags garage` selects the include_role and the included tasks' `[garage, backup]` tags both fire.

---

### 2. `playbooks/restore_docker.yml` (orchestrator, confirm-gated, with writer-quiesce bracket)

**Primary analog:** `playbooks/undeploy_docker.yml` (banner shape + include_role list)
**Secondary analog:** `roles/garage/tasks/backup.yml` (the docker-stop + docker_container_info poll loop body)
**Tertiary analog:** `roles/grafana/tasks/verify.yml` (the canonical healthy-poll `until:`+`retries:`+`delay:` shape)

#### Pattern F — `WARNING: irreversible --` PLAY-start WARN banner (D-159 + D-187)

**Source:** `playbooks/undeploy_docker.yml` lines 56-70 (same as Pattern B above), AND the post_tasks single-line variant at lines 294-296:

```yaml
    - name: WARN -- /opt/telemetron host tree will be removed
      ansible.builtin.debug:
        msg: "WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)"
      when: telemetron_purge_host_dirs | default(false) | bool
```

**How Phase 14 adapts this (D-187):** Use the multi-line `msg: |` shape from lines 60-68 (NOT the single-line variant), with `tags: [always]`. The headline line MUST start with the verbatim `WARNING: irreversible -- ` prefix (grep target). Three banner lines per D-187:

- Line 1 (headline): `WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)`
- Line 2: `Target timestamp: {{ backup_restore_from | default('<latest per role>') }}`
- Line 3: `Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir`

#### Pattern G — Confirm-gate `ansible.builtin.fail` (mirrors per-role gate; new pattern at orchestrator level)

**Source (precedent):** the per-role gate lives inside each `tasks/restore.yml` (Phase 13). The orchestrator-level `fail:` shape mirrors that idiomatic Ansible form. Closest existing repo precedent for the "fail if knob false" pattern is the orchestrator-level `when:` opt-in pattern from `playbooks/undeploy_docker.yml` lines 101-104:

```yaml
      when: >-
        telemetron_purge_data | default(false) | bool
        or telemetron_purge_images | default(false) | bool
```

**How Phase 14 adapts this (OPS-V13-01):** Idiomatic Ansible `ansible.builtin.fail`, `tags: [always]`, runs as the FIRST `pre_tasks` entry (before the banner — operator should not see the banner if the gate fires):

```yaml
  pre_tasks:
    - name: Refuse to run restore without explicit confirm-gate (OPS-V13-01)
      ansible.builtin.fail:
        msg: |
          Restore refused. Pass --extra-vars backup_restore_confirm=true to proceed.
          See docs/quickstart.md#backup-and-restore for the operator opt-in contract.
      when: not (backup_restore_confirm | default(false) | bool)
      tags:
        - always
```

#### Pattern H — Writer-stop loop body (docker stop + docker_container_info poll until exited)

**Source (verbatim):** `roles/garage/tasks/backup.yml` lines 122-142

```yaml
    - name: Stop Garage container for cold-quiesce backup (XP-1; PITFALLS GP-1)
      ansible.builtin.command: "docker stop -t {{ garage_backup_stop_timeout }} {{ garage_container_name }}"
      changed_when: true
      become: true

    # Verbatim shape from roles/garage/tasks/bootstrap.yml lines 21-35,
    # with the until: clause flipped from Health.Status == 'healthy' to
    # State.Running == false. 30 retries * 2s = 60s -- mirrors the
    # garage_backup_stop_timeout budget rather than the bootstrap health
    # retries (which are tuned for first-start, not stop).
    - name: Wait for Garage container to reach stopped state
      community.docker.docker_container_info:
        name: "{{ garage_container_name }}"
      register: garage_stopped_check
      until: >-
        garage_stopped_check.container is defined
        and garage_stopped_check.container.State is defined
        and garage_stopped_check.container.State.Running == false
      retries: 30
      delay: 2
      changed_when: false
```

**How Phase 14 adapts this (D-181):** Same shape but as a `loop:` over the 3 writers, sequential. Uses the shared `backup_stop_timeout` (D-182). Tagged `[garage]` ONLY (D-189). The poll loop register must be loop-scoped so it does not collide across iterations. Recommended structure:

```yaml
    - name: Stop Garage writers (Loki/Tempo/Mimir) before Garage restore (D-181, D-189)
      ansible.builtin.command: "docker stop -t {{ backup_stop_timeout }} {{ item.container_name }}"
      loop:
        - { role: loki,  container_name: "{{ loki_container_name }}" }
        - { role: tempo, container_name: "{{ tempo_container_name }}" }
        - { role: mimir, container_name: "{{ mimir_container_name }}" }
      loop_control:
        label: "{{ item.role }}"
      changed_when: true
      become: true
      tags:
        - garage

    - name: Wait for Garage writers to reach stopped state
      community.docker.docker_container_info:
        name: "{{ item.container_name }}"
      register: writer_stopped_check
      until: >-
        writer_stopped_check.container is defined
        and writer_stopped_check.container.State is defined
        and writer_stopped_check.container.State.Running == false
      retries: 30
      delay: 2
      changed_when: false
      loop:
        - { role: loki,  container_name: "{{ loki_container_name }}" }
        - { role: tempo, container_name: "{{ tempo_container_name }}" }
        - { role: mimir, container_name: "{{ mimir_container_name }}" }
      loop_control:
        label: "{{ item.role }}"
      tags:
        - garage
```

#### Pattern I — Writer-restart loop body (docker start + docker_container_info poll until healthy)

**Source (verbatim, the post-backup restart pair):** `roles/garage/tasks/backup.yml` lines 197-218

```yaml
  always:
    # AN-2: ALWAYS restart, even if any block: task failed. docker start
    # is symmetric with the docker stop above -- no community.docker
    # equivalent is needed and using the CLI keeps the symmetry obvious.
    - name: Restart Garage container after backup (AN-2 always-restart guarantee)
      ansible.builtin.command: "docker start {{ garage_container_name }}"
      changed_when: true
      become: true

    # D-178: Garage has NO tasks/verify.yml -- the inline healthy-poll is
    # the verify mechanism. Verbatim shape from roles/garage/tasks/bootstrap.yml
    # lines 21-35 (same retries/delay defaults from the same defaults file).
    - name: Wait for Garage container HEALTHCHECK to report healthy post-backup
      community.docker.docker_container_info:
        name: "{{ garage_container_name }}"
      register: garage_post_backup_health
      until: >-
        garage_post_backup_health.container is defined
        and garage_post_backup_health.container.State is defined
        and garage_post_backup_health.container.State.Health is defined
        and garage_post_backup_health.container.State.Health.Status == 'healthy'
      retries: "{{ garage_health_retries }}"
      delay: "{{ garage_health_delay }}"
      changed_when: false
```

**Cross-reference healthy-poll shape:** `roles/grafana/tasks/verify.yml` lines 21-37:

```yaml
- name: Wait for grafana container HEALTHCHECK to report healthy
  community.docker.docker_container_info:
    name: "{{ grafana_container_name }}"
  register: grafana_health_check
  until: >-
    grafana_health_check.container is defined
    and grafana_health_check.container.State is defined
    and grafana_health_check.container.State.Health is defined
    and grafana_health_check.container.State.Health.Status == 'healthy'
  retries: "{{ grafana_health_retries }}"
  delay: "{{ grafana_health_delay }}"
  changed_when: false
  when: grafana_healthcheck_enabled | bool
  tags:
    - grafana
    - grafana-verify
```

**How Phase 14 adapts this (D-183):** Same docker_container_info + `until: ... State.Health.Status == 'healthy'` shape, as a `loop:` over the 3 writers. Lives in `tasks:` (NOT `always:` — restore orchestrator has no block/always — and NOT `post_tasks:` per D-193 lock so `--tags garage` runs the restart too). Tagged `[garage]` (D-189). Retries/delay should NOT reuse a single role's `<role>_health_retries`; pick a literal value that accommodates the slowest writer's start budget. Suggested: `retries: 30, delay: 2` to mirror the writer-stop budget at 60s.

```yaml
    - name: Start Garage writers (Loki/Tempo/Mimir) after Garage restore (D-183, D-189)
      ansible.builtin.command: "docker start {{ item.container_name }}"
      loop:
        - { role: loki,  container_name: "{{ loki_container_name }}" }
        - { role: tempo, container_name: "{{ tempo_container_name }}" }
        - { role: mimir, container_name: "{{ mimir_container_name }}" }
      loop_control:
        label: "{{ item.role }}"
      changed_when: true
      become: true
      tags:
        - garage

    - name: Wait for Garage writers to report healthy
      community.docker.docker_container_info:
        name: "{{ item.container_name }}"
      register: writer_healthy_check
      until: >-
        writer_healthy_check.container is defined
        and writer_healthy_check.container.State is defined
        and writer_healthy_check.container.State.Health is defined
        and writer_healthy_check.container.State.Health.Status == 'healthy'
      retries: 30
      delay: 2
      changed_when: false
      loop:
        - { role: loki,  container_name: "{{ loki_container_name }}" }
        - { role: tempo, container_name: "{{ tempo_container_name }}" }
        - { role: mimir, container_name: "{{ mimir_container_name }}" }
      loop_control:
        label: "{{ item.role }}"
      tags:
        - garage
```

#### Pattern J — `any_errors_fatal: true` hardcoded at play level (D-185)

**Source:** No exact precedent — first orchestrator in the repo to use `any_errors_fatal: true`. Closest precedent for play-level keyword is the `playbooks/undeploy_docker.yml` shape (lines 41-53) showing where to place play-level keys.

**How Phase 14 adapts this:** Add `any_errors_fatal: true` at play level alongside `gather_facts`, `become`, etc. NO operator knob. Document explicitly in a header comment that `backup_continue_on_failure` does NOT apply to restore (D-185).

---

### 3. `roles/garage/tasks/backup.yml` (MODIFIED — D-191 amend only)

**Analog:** SELF — Phase 13 shipped this file; Phase 14 makes ONE minimal amendment.

#### Pattern K — D-191 amend: accept `backup_timestamp_override` via `set_fact` indirection

**Current shape (lines 79-86, verbatim) — BEFORE state:**

```yaml
# D-179: ISO 8601 basic UTC timestamp (YYYYMMDDTHHMMSSZ) -- monotonic +
# lexicographically chronological, so the Phase 14 latest-discovery glob
# (`find ... | sort -r | head -1`) Just Works without a date parser.
- name: Record UTC timestamp for Garage backup filename (D-179 ISO 8601 basic)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - garage
    - backup
```

**Current downstream consumers (verbatim, lines 173, 188) — these must keep working:**

```yaml
          {{ backup_dest_root }}/garage/garage-{{ backup_timestamp.stdout }}.tar.zst
```

```yaml
        path: "{{ backup_dest_root }}/garage/garage-{{ backup_timestamp.stdout }}.tar.zst"
```

**How Phase 14 adapts this (D-191):** Pick CONTEXT.md "Option B" (always call `date`, then `set_fact`) for minimum-diff implementation. Insert a `set_fact` AFTER the existing `date` task and BEFORE the block. Replace every `backup_timestamp.stdout` in the file with `backup_timestamp_effective`. Two filename-construction sites in this file (lines 173 and 188). AFTER state:

```yaml
- name: Record UTC timestamp for Garage backup filename (D-179 ISO 8601 basic)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - garage
    - backup

# D-191 (Phase 14): when invoked from playbooks/backup_docker.yml the
# orchestrator passes a single shared timestamp so all 4 tarballs in a
# multi-role run share one filename suffix. Standalone include_role calls
# (no override set) fall through to the per-role inline date.stdout.
- name: Resolve effective backup timestamp (D-191 orchestrator override or inline)
  ansible.builtin.set_fact:
    backup_timestamp_effective: "{{ backup_timestamp_override | default(backup_timestamp.stdout) }}"
  tags:
    - garage
    - backup
```

Then mechanical s/`backup_timestamp.stdout`/`backup_timestamp_effective`/ across the 2 filename sites.

---

### 4. `roles/prometheus/tasks/backup.yml` (MODIFIED — D-191 amend only)

**Analog:** SELF — same amendment as #3.

**Current shape (lines 65-71, verbatim) — BEFORE state:**

```yaml
# D-179 timestamp: ISO 8601 basic UTC (YYYYMMDDTHHMMSSZ). Lexicographic
# sort of these filenames is chronological -- consumed by restore's
# `find ... | sort -r | head -1` latest-discovery.
- name: Generate backup timestamp (D-179 ISO 8601 basic UTC)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - prometheus
    - backup
```

**Current downstream consumers (verbatim, lines 122, 132):**

```yaml
          {{ backup_dest_root }}/prometheus/prometheus-{{ backup_timestamp.stdout }}.tar.zst
```

```yaml
        path: "{{ backup_dest_root }}/prometheus/prometheus-{{ backup_timestamp.stdout }}.tar.zst"
```

**How Phase 14 adapts this:** Same Pattern K. Insert `set_fact: backup_timestamp_effective` after line 71, before the block at line 83. Replace 2 filename sites.

---

### 5. `roles/grafana/tasks/backup.yml` (MODIFIED — D-191 amend only)

**Analog:** SELF — same amendment as #3.

**Current shape (lines 74-80, verbatim) — BEFORE state:**

```yaml
- name: Record UTC timestamp for backup filename (D-179 ISO 8601 basic)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - grafana
    - backup
```

**Current downstream consumers (verbatim, lines 129, 139):**

```yaml
          {{ backup_dest_root }}/grafana/grafana-{{ backup_timestamp.stdout }}.tar.zst
```

```yaml
        path: "{{ backup_dest_root }}/grafana/grafana-{{ backup_timestamp.stdout }}.tar.zst"
```

**How Phase 14 adapts this:** Same Pattern K. Insert `set_fact: backup_timestamp_effective` after line 80, before the block. Replace 2 filename sites.

---

### 6. `roles/alertmanager/tasks/backup.yml` (MODIFIED — D-191 amend only)

**Analog:** SELF — same amendment as #3.

**Current shape (lines 102-111, verbatim) — BEFORE state:**

```yaml
# D-179: ISO 8601 basic UTC timestamp (YYYYMMDDTHHMMSSZ). Generated once
# per backup invocation; lexicographic sort is chronological because the
# format is monotonic.
- name: Generate UTC backup timestamp (D-179)
  ansible.builtin.command: date -u +%Y%m%dT%H%M%SZ
  register: backup_timestamp
  changed_when: false
  tags:
    - alertmanager
    - backup
```

**Current downstream consumers (verbatim, lines 151, 159):**

```yaml
          {{ backup_dest_root }}/alertmanager/alertmanager-{{ backup_timestamp.stdout }}.tar.zst
```

```yaml
        path: "{{ backup_dest_root }}/alertmanager/alertmanager-{{ backup_timestamp.stdout }}.tar.zst"
```

**How Phase 14 adapts this:** Same Pattern K. Insert `set_fact: backup_timestamp_effective` after line 111, before the block at line 116. Replace 2 filename sites.

---

### 7. `14-HUMAN-UAT.md` (NEW — audit doc)

**Primary analog:** `.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md`

#### Pattern L — YAML frontmatter

**Source (verbatim, lines 1-7):**

```yaml
---
status: complete
phase: 11-undeploy-orchestrator-safety-idempotency
source: [11-VERIFICATION.md]
started: 2026-05-29T00:00:00Z
updated: 2026-05-30T12:25:00Z
---
```

**How Phase 14 adapts this:** Starting state `status: in_progress` (or `pending` if Claude's-Discretion picks that — see CONTEXT.md). Adapted frontmatter:

```yaml
---
status: in_progress
phase: 14-orchestrators-leviathan-human-uat
source: [14-VERIFICATION.md]
started: 2026-06-XXT00:00:00Z
updated: 2026-06-XXT00:00:00Z
---
```

Note: `source:` should only include `14-VERIFICATION.md` if Phase 14 ships one; otherwise omit the key entirely (planner's call). The CONTEXT.md "Claude's Discretion" block says the initial commit can use `status: pending` and flip to `complete` after live UAT — both forms are valid; copy whichever the planner picks.

#### Pattern M — Top-level structure: `## Current Test` + `## Tests` + numbered scenarios

**Source (verbatim, lines 9-18):**

```markdown
## Current Test

[Round 2 complete 2026-05-30. All 7 scenarios pass on leviathan. G-01 + G-02 behaviourally closed via recovery branch (commits 5eb9833 + 319559f).]

## Tests

### 1. Conservative undeploy + redeploy (OPS-02 happy path; D-146 recovery proof; G-01 behavioural closure)
expected: `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` completes with `failed=0` and no purge flags set; named volumes `telemetron_*_data` survive -- `docker volume ls | grep telemetron_` shows all 11 telemetron-prefixed volumes intact ...
result: pass
detail: PASSED 2026-05-30 round 2 (post-fix). Undeploy clean (ok=37 changed=23 failed=0). ...
```

**How Phase 14 adapts this:** Same `## Current Test` (one-line bracketed status), `## Tests`, numbered `###` headings with parenthesised "(REQ; sub-claim; gap-id)" titles. Each scenario uses the **literal three-line shape** with no blank lines between them:

```
expected: <prose>
result: <pending|pass|fail>
detail: <prose; PASSED <date> ... ok=N changed=N failed=0 ...>
```

#### Pattern N — Sub-scenarios with letter suffix (4a, 4b, 4c)

**Source (verbatim, lines 30-43):**

```markdown
### 4a. telemetron_purge_data=true + redeploy
expected: ...
result: pass
detail: ...

### 4b. telemetron_purge_host_dirs=true + redeploy (G-02 closure)
expected: ...
result: pass
detail: ...

### 4c. telemetron_purge_images=true + redeploy
expected: ...
result: pass
detail: ...
```

**How Phase 14 adapts this:** Same letter-suffix shape for Scenario 2 (a, b) and Scenario 3 (a, b) per CONTEXT.md D-192. Scenario 1 (the 7-step round-trip) and Scenario 4 (tag-scoped) have no sub-scenarios.

#### Pattern O — `## Summary` block at end

**Source (verbatim, lines 50-57):**

```markdown
## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0
```

**How Phase 14 adapts this:** Same block. Initial values `passed: 0`, `pending: <total>` until live UAT runs; live UAT flips them.

#### Pattern P — `## Gaps` block (only when defects open during UAT)

**Source (verbatim, lines 59-73, showing G-01 closure form):**

```markdown
## Gaps

### G-01: Orphan S3 key on conservative undeploy + redeploy (Phase 8/10 cross-phase defect)
status: closed
manifests-in: scenarios 1, 4b
fix-commits: 5dc5fd5, 01399a0, 06047b8, 85a6de7, 5eb9833, 2626989, 319559f
fix-plan: 11-06-PLAN.md
fix-summary: ...
```

**How Phase 14 adapts this:** Section is OPTIONAL — ship the doc without it; add `## Gaps` only if a scenario surfaces a defect during the live leviathan run. Use the same `### G-XX:` + `status:`/`manifests-in:`/`fix-commits:`/`fix-plan:`/`fix-summary:` shape if it does.

---

## Shared Patterns

### Shared Pattern 1: `community.docker` collection at play level

**Source:** `playbooks/undeploy_docker.yml` lines 46-47 + `playbooks/deploy_docker.yml` lines 22-23 + `playbooks/smoke_test.yml` lines 32-33

```yaml
  collections:
    - community.docker
```

**Apply to:** Both new orchestrators. The writer-stop/start loops reference `community.docker.docker_container_info`, so the collection MUST be loaded at play level (not relying on FQCN alone — keeps style consistent across all 3 orchestrators in the repo).

---

### Shared Pattern 2: Sequential cold-quiesce loop body (docker stop -t {{ timeout }} + docker_container_info poll until exited)

**Source (verbatim):** `roles/garage/tasks/backup.yml` lines 122-142 (excerpted under Pattern H above); identical shape in `roles/prometheus/tasks/backup.yml` lines 90-105, `roles/grafana/tasks/backup.yml` lines 95-112, `roles/alertmanager/tasks/backup.yml` lines 118-133.

**Why this matters:** The pattern Phase 13 standardised across 4 stateful roles. The writer-quiesce loop in `restore_docker.yml` MUST use the same shape verbatim — operators reading any of the 4 `tasks/backup.yml` files and then `restore_docker.yml` should recognise the same idiom. CONTEXT.md D-181 locks "mirrors the cold-quiesce pattern Phase 13 standardized." Do not invent a new shape.

**Apply to:** `restore_docker.yml` writer-stop block.

---

### Shared Pattern 3: Sequential restart loop body (docker start + docker_container_info poll until healthy)

**Source (verbatim):** `roles/garage/tasks/backup.yml` lines 197-218 + `roles/grafana/tasks/verify.yml` lines 21-32. Both cited under Pattern I.

**Apply to:** `restore_docker.yml` writer-restart block. Uses `State.Health.Status == 'healthy'` form (3 writers all ship HEALTHCHECK in their Dockerfiles per Gate 7 — confirm in defaults/main.yml if needed).

---

### Shared Pattern 4: `tags: always` on banner + confirm-gate

**Source:** `playbooks/undeploy_docker.yml` lines 69-70 (banner) — the only `tags: always` precedent in the repo's orchestrator playbooks.

```yaml
      tags:
        - always
```

**Apply to:**
- `backup_docker.yml`: PLAY-start banner + 2 timestamp pre_tasks (`date` + `set_fact`)
- `restore_docker.yml`: confirm-gate `fail:` + PLAY-start banner

Why timestamp tasks need `tags: always`: under `--tags garage`, the `date` and `set_fact` tasks must still fire so the include_role can consume `backup_timestamp_shared`. The CONTEXT.md "Specific Ideas" block lists them under `pre_tasks:` without explicit tags; planner must add `tags: always` to all three pre_tasks so `--tags <role>` runs still get the shared timestamp.

---

### Shared Pattern 5: `become: true` ONLY on host-side commands (not on the include_role itself)

**Source:** `roles/garage/tasks/backup.yml` lines 51, 71, 124, 180, 200 (every host-side command); `playbooks/undeploy_docker.yml` line 44 (play-level `become: false`).

```yaml
- name: Stop Garage container for cold-quiesce backup (XP-1; PITFALLS GP-1)
  ansible.builtin.command: "docker stop -t {{ garage_backup_stop_timeout }} {{ garage_container_name }}"
  changed_when: true
  become: true
```

**Apply to:** Writer-stop and writer-restart `command:` tasks in `restore_docker.yml` carry `become: true`. The `docker_container_info` polls do NOT need `become:` (read-only Docker API access via socket; play-level `become: false` is correct).

---

## Landmines and Discovered Facts

### Writer container name defaults (verbatim from defaults/main.yml)

Required for the writer-quiesce loop in `restore_docker.yml`:

| Var | File:Line | Default value |
|-----|-----------|---------------|
| `loki_container_name` | `roles/loki/defaults/main.yml:20` | `telemetron-loki` |
| `tempo_container_name` | `roles/tempo/defaults/main.yml:22` | `telemetron-tempo` |
| `mimir_container_name` | `roles/mimir/defaults/main.yml:20` | `telemetron-mimir` |
| `garage_container_name` | `roles/garage/defaults/main.yml:21` | `telemetron-garage` |

These resolve at orchestrator runtime via Ansible's normal variable precedence (group_vars + role defaults). No need to load them explicitly in the orchestrator `vars:` block — the `include_role` call brings them in. But the writer-stop loop runs BEFORE the `include_role: name=garage tasks_from=restore` invokes any role, so the orchestrator depends on group_vars or all-scope inventory carrying these vars. They DO — Ansible loads `role defaults` lazily; the orchestrator-level reference to `{{ loki_container_name }}` works because Loki's role defaults are loaded as soon as ANY include_role somewhere in the play touches Loki. **There is no `include_role: name=loki` anywhere in restore_docker.yml.** This is a real concern: the orchestrator references `loki_container_name` / `tempo_container_name` / `mimir_container_name` without ever invoking those roles.

**Mitigation:** Either (planner picks one)
1. **Hardcode the container names inline** in the loop list-of-dicts (matches the CONTEXT.md Specific Ideas pattern; trades the indirection for one-line operator override via `--extra-vars loki_container_name=...`). Recommended — minimal-diff.
2. **Add the 3 writer container name vars to `inventory/example-homelab/group_vars/all/backup.yml`** so they are loaded at all-group scope. Adds a 3-line stanza; requires Phase 15 doc cascade to mention the override surface.
3. **Stub `include_role: name=loki tasks_from=defaults_only`** via `include_vars` — over-engineered.

Default if planner is silent: **Option 1** (hardcode). The CONTEXT.md "Specific Ideas" block already uses `{{ loki_container_name }}` etc., implying Option 2; planner should explicitly choose and document.

### Phase 13 `tasks/backup.yml` files all have an identical timestamp shape

The 4 amendments are mechanically uniform. Every file has the same `date -u +%Y%m%dT%H%M%SZ` + `register: backup_timestamp` + `changed_when: false` + tags block. The set_fact insertion + filename-site rewrite is the SAME 3-step recipe across all 4 files. Planner should write ONE plan action covering all 4 files (with the exact line numbers for each filename consumer site listed under each file's section above) rather than 4 separate plans.

### `undeploy_docker.yml` uses `roles:` block in `deploy_docker.yml` but `include_role` in `undeploy_docker.yml`

`deploy_docker.yml` lines 35-72 uses a `roles:` block; `undeploy_docker.yml` lines 80-275 uses 23 explicit `include_role` calls. CONTEXT.md "Established Patterns" locks `include_role` (not `roles:` block) for Phase 14. Per D-149: explicit include_role lets each call carry its own tag set + ordering. Both new orchestrators MUST use `include_role` (not `roles:`).

### `roles:` keyword precedence vs `include_role` in tag handling

`deploy_docker.yml` uses `roles:` because tag handling there is simpler — Ansible applies `tags:` to ALL of a role's tasks via the `roles:` keyword. `include_role` requires the included tasks themselves to carry the tag (which they do, in every Phase 13 `tasks/backup.yml` and `tasks/restore.yml` — every task ends with `tags: [<role>, backup]` or `tags: [<role>, restore]`). The Phase 14 orchestrators' include_role `tags: [<role>]` directive applies to the **task that does the include**, not to the included tasks themselves; the included tasks carry their own tags. This is why `--tags <role>` selects: (a) the include_role task at orchestrator level, AND (b) every task inside the included file whose block-level tags include `<role>`.

### `any_errors_fatal` semantics

`any_errors_fatal: true` aborts the play on the FIRST host's first task failure (Telemetron is single-host, so equivalent to "first task failure aborts the play"). Documented behaviour matches D-184 (backup) and D-185 (restore — hardcoded true).

### No existing `block:`/`rescue:`/`always:` precedent at orchestrator level

The `block:` pattern lives inside per-role `tasks/backup.yml` (Phase 13 introduced it). NEITHER `deploy_docker.yml` NOR `undeploy_docker.yml` uses `block:` at play level. The Phase 14 orchestrators should follow that precedent: NO `block:` at play level. `any_errors_fatal` handles failure semantics; the per-role tasks own their own `block:`/`always:` restart guarantee.

### `set_fact` for `backup_timestamp_effective` is intentionally per-role (NOT a play-level fact)

CONTEXT.md D-191 locks "Phase 14 includes a small amendment to each of the 4 `tasks/backup.yml` files Phase 13 shipped: change the filename generation to use `backup_timestamp_override | default(<existing inline date call>)`." The fact lives in each role's task scope (`set_fact` without `delegate_to`); the override knob `backup_timestamp_override` is passed in via the orchestrator's `vars:` block on the `include_role` call. This preserves the standalone-`include_role` path (D-191 explicit: "Standalone `include_role: tasks_from=backup` (without the orchestrator) still works because the `default(<inline date>)` branch fires when `backup_timestamp_override` is unset.")

### `restore_docker.yml` reuses `backup_stop_timeout`, NOT a new `restore_stop_timeout`

CONTEXT.md "Specific Ideas" uses `{{ backup_stop_timeout }}` for the writer-quiesce loop. The Phase 13 group_vars at `inventory/example-homelab/group_vars/all/backup.yml` (verbatim lines 20-22):

```yaml
# Seconds to wait between SIGTERM and SIGKILL when stopping a container for
# cold-quiesce backup or restore. 60s default gives Prometheus WAL flush
# and Garage LMDB clean-close ~6x the Docker default (10s). ...
backup_stop_timeout: 60
```

The comment explicitly says "backup or restore" — single knob serves both. No new knob.

### `playbooks/smoke_test.yml` provides `smoke_trace_id` + `smoke_run_id` via `lookup` + epoch

For HUMAN-UAT scenario 1 steps 2 and 7, the mechanism is at `playbooks/smoke_test.yml` lines 44, 50:

```yaml
    smoke_trace_id: "{{ lookup('ansible.builtin.password', '/dev/null length=32 chars=hexdigits') | lower }}"
    ...
    smoke_run_id:   "{{ ansible_date_time.epoch }}"
```

Step 2 of HUMAN-UAT scenario 1: run smoke_test.yml and capture the recorded values from PLAY OUTPUT (lines 219-220 of smoke_test.yml print them). Step 7: re-invoke smoke_test.yml with `--extra-vars smoke_trace_id=<recorded> smoke_run_id=<recorded>` so the assertion proxies query the SAME trace_id + run_id that step 2 emitted. No changes to smoke_test.yml needed in Phase 14.

---

## No Analog Found

None. Every Phase 14 file has at least one strong in-repo analog.

---

## Metadata

**Analog search scope:**
- `playbooks/*.yml`
- `roles/garage/tasks/backup.yml`, `roles/prometheus/tasks/backup.yml`, `roles/grafana/tasks/backup.yml`, `roles/alertmanager/tasks/backup.yml`
- `roles/grafana/tasks/verify.yml`
- `roles/loki/defaults/main.yml`, `roles/tempo/defaults/main.yml`, `roles/mimir/defaults/main.yml`, `roles/garage/defaults/main.yml`
- `inventory/example-homelab/group_vars/all/backup.yml`
- `.planning/milestones/v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md`
- `.planning/milestones/v1.0.0-phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md`
- `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/phases/13-per-role-backup-restore-tasks/13-CONTEXT.md`

**Files scanned (read in full or via line-range):** 13

**Pattern extraction date:** 2026-06-03

---

*Phase: 14-orchestrators-leviathan-human-uat*
*Mapper: gsd-pattern-mapper*
