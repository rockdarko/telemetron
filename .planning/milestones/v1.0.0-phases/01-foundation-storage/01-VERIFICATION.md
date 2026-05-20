---
phase: 01-foundation-storage
verified: 2026-05-17T16:00:00Z
status: passed
score: 5/5 must-haves verified (code) + live-host confirmation on leviathan
re_verification: false
live_uat_confirmed: 2026-05-19
live_uat_evidence: ".planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md (Plan 06-01..06-04 all PASS on leviathan; full 13-role stack including MinIO comes up end-to-end; PLAY RECAP idempotency confirmed changed=0 on re-run -- see Plan 06-04 entry)"
human_verification:
  - test: "Run ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags minio --ask-vault-pass on a writable Docker host"
    expected: "PLAY RECAP shows failed=0; docker network ls shows telemetron bridge; docker inspect minio shows Health.Status=healthy and RestartPolicy=unless-stopped; five buckets present via mc ls"
    result: "PASS on leviathan -- subsumed by Phase 06 full-stack deploy; MinIO + telemetron bridge + healthy state + 5 buckets all confirmed live"
    why_human: "Live run requires a Docker host with /opt/telemetron writable by the Ansible user. Confirmed live on leviathan (Ubuntu 24.04 noble, Docker 29.1.3)."
  - test: "Run the playbook a second time (idempotency gate)"
    expected: "PLAY RECAP shows changed=0, failed=0"
    result: "PASS on leviathan -- confirmed in Plan 06-04 idempotency revalidation"
    why_human: "Idempotency confirmed via back-to-back deploy on leviathan; documented in 06-HUMAN-UAT.md Plan 06-04 entry."
---

# Phase 1: Foundation & Storage Verification Report

**Phase Goal:** Operator can run the foundation playbook against a fresh Docker host and have MinIO up with all five required buckets pre-created (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts), the telemetron Docker bridge network created, the inventory/example-homelab/group_vars/all/ skeleton in place, and the cross-cutting gates (vault, idempotency, image-pin, healthcheck + restart: unless-stopped, INSPQ grep gate) established as port-acceptance criteria that every Phase 2-6 role port inherits.

**Verified:** 2026-05-17T16:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ansible-playbook --tags minio passes --syntax-check against the inventory | VERIFIED | `ansible-playbook --syntax-check` exits 0; confirmed in behavioral spot-check |
| 2 | telemetron Docker bridge network is created in playbook pre_tasks | VERIFIED | `playbooks/deploy_docker.yml` pre_tasks block uses `community.docker.docker_network` with `driver: bridge`, tagged `[always, network]` |
| 3 | Five required buckets declared and bootstrap logic creates them blocking-style | VERIFIED | `storage.yml` declares all 5; `tasks/bootstrap.yml` uses mc with `--ignore-existing` + blocking diff verify; bootstrap is the final task in `tasks/main.yml` |
| 4 | Vault flow: vault.yml.example ships with CHANGE_ME; real vault.yml gitignored | VERIFIED | `vault.yml.example` tracked in git with correct `vault_<role>_<purpose>` names; `.gitignore` pattern `inventory/*/group_vars/*/vault.yml` excludes real vault |
| 5 | Port-acceptance gates (image-pin, INSPQ grep, non-ASCII, healthcheck+restart, idempotency) established and roles/minio/ passes all static gates | VERIFIED | All grep gates return 0; image pinned to explicit RELEASE tag; HEALTHCHECK declared with `minio_restart_policy: unless-stopped`; `changed_when: false` on all mc tasks; gates documented in `roles/README.md` |

**Score:** 5/5 truths verified (static/code-level); 2 items routed to human verification for live-host confirmation

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `roles/minio/defaults/main.yml` | Image pins + tunables | VERIFIED | 100 lines; `minio_image_tag: RELEASE.2025-04-22T22-12-26Z`, `minio_mc_image_tag: RELEASE.2025-04-22T16-23-26Z`, `minio_restart_policy: unless-stopped`, healthcheck config, all vars |
| `roles/minio/tasks/main.yml` | Server deploy tasks; bootstrap as final task | VERIFIED | 94 lines; env-file render, volume create, image pull, container run with healthcheck+restart, final `include_tasks: bootstrap.yml` |
| `roles/minio/tasks/bootstrap.yml` | docker_container_info health poll + mc bucket create + mc ls verify | VERIFIED | 115 lines; 3-step pattern: healthcheck poll, mc mb --ignore-existing, mc ls --json + diff verify; all three steps have `changed_when: false` |
| `roles/minio/handlers/main.yml` | Single handler: docker restart via command | VERIFIED | 15 lines; one handler, `docker restart`, `listen: restart minio`, `changed_when: true`; no state-restarted |
| `roles/minio/templates/minio.env.j2` | Renders vault creds + MINIO_VOLUMES + TZ | VERIFIED | 10 lines; `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_VOLUMES`, `MINIO_BROWSER_REDIRECT_URL`, `TZ` |
| `roles/minio/meta/main.yml` | Galaxy metadata + collection deps | VERIFIED | 27 lines; `community.docker` + `ansible.builtin` collections; no role dependencies |
| `roles/minio/README.md` | Per-role schema: vars, vault keys, tags, modes, volumes, healthcheck, security, idempotency, gates | VERIFIED | 181 lines; all required sections present |
| `ansible.cfg` | roles_path = roles at project root | VERIFIED | 14 lines; `roles_path = roles`, `retry_files_enabled = false`, `diff_always = false` |
| `playbooks/deploy_docker.yml` | pre_tasks network + minio role wired | VERIFIED | pre_tasks with `docker_network` tagged `[always, network]`; `roles: [{role: minio, tags: [minio]}]` |
| `inventory/example-homelab/hosts.yml` | Single-host telemetron group, localhost default | VERIFIED | `telemetron` group, `homelab` host, `ansible_connection: local` |
| `inventory/example-homelab/group_vars/all/network.yml` | telemetron_network, publish_default, TZ | VERIFIED | `telemetron_network: telemetron`, `telemetron_publish_default: false`, `telemetron_tz: Etc/UTC` |
| `inventory/example-homelab/group_vars/all/storage.yml` | volume prefix, 5 bucket names, config root | VERIFIED | `telemetron_volume_prefix: telemetron`, `telemetron_config_root: /opt/telemetron`, all 5 `telemetron_minio_buckets` |
| `inventory/example-homelab/group_vars/all/vault.yml.example` | CHANGE_ME placeholders, vault_ naming, .example tracked | VERIFIED | `vault_minio_root_user` and `vault_minio_root_password` with CHANGE_ME; file tracked in git; real vault.yml gitignored |
| `inventory/example-homelab/group_vars/all/minio.yml` | minio_publish_host: false, minio_container_name literal | VERIFIED | `minio_publish_host: false`, `minio_container_name: minio` (literal, overrides self-referential default) |
| `inventory/example-homelab/README.md` | Quickstart doc | VERIFIED | 99 lines; 4-step quickstart |
| `roles/README.md` | 14-role table + port-acceptance gates section | VERIFIED | Port-acceptance gates section at line 38 with 6 gate commands |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `playbooks/deploy_docker.yml` | `telemetron` Docker network | `community.docker.docker_network` in pre_tasks | WIRED | Network name sourced from `{{ telemetron_network }}` (inventory network.yml) |
| `playbooks/deploy_docker.yml` | `roles/minio` | `roles: [{role: minio, tags: [minio]}]` | WIRED | Role wired at Phase 1 in plan 01-03 |
| `roles/minio/tasks/main.yml` | `roles/minio/tasks/bootstrap.yml` | `ansible.builtin.include_tasks: bootstrap.yml` as final task | WIRED | Last task in main.yml; blocking (D-08) |
| `roles/minio/tasks/main.yml` | `roles/minio/templates/minio.env.j2` | `ansible.builtin.template` → `notify: restart minio` | WIRED | Handler triggered on env-file change |
| `roles/minio/tasks/main.yml` | `roles/minio/handlers/main.yml` | `notify: restart minio` + `listen: restart minio` | WIRED | Single handler; `docker restart {{ minio_container_name }}` |
| `roles/minio/tasks/bootstrap.yml` | MinIO container health | `community.docker.docker_container_info` until `State.Health.Status == healthy` | WIRED | Poll before mc bootstrap fires |
| `roles/minio/tasks/bootstrap.yml` | `vault_minio_root_user` / `vault_minio_root_password` | `env.MC_HOST_local` in mc container | WIRED | Vault vars flow from inventory vault.yml → mc credential URL |
| `roles/minio/defaults/main.yml` | `inventory/example-homelab/group_vars/all/storage.yml` | `minio_buckets: "{{ telemetron_minio_buckets | default([...]) }}"` | WIRED | Inventory value overrides default bucket list |
| `roles/minio/defaults/main.yml` | `inventory/example-homelab/group_vars/all/network.yml` | `minio_network: "{{ telemetron_network | default('telemetron') }}"` | WIRED | Network name flows from inventory |
| `ansible.cfg` | `roles/` directory | `roles_path = roles` | WIRED | Enables `ansible-playbook` to find roles regardless of working directory; confirmed by --syntax-check exit 0 |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces Ansible infrastructure code (roles, templates, playbooks), not data-rendering components. The "data" is the converged Docker host state, which requires live-host verification (see Human Verification section).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Playbook passes syntax check | `ansible-playbook --syntax-check -i inventory/example-homelab playbooks/deploy_docker.yml` | Exit 0; `playbook: playbooks/deploy_docker.yml` | PASS |
| No `:latest` image tags in roles/minio/ | `grep -rcE ':latest' roles/minio/` | All files return 0 | PASS |
| No INSPQ/French fork-leftover patterns | `grep -riE 'inspq|qc.ca|montreal|québec|francais|french' roles/minio/` | 0 matches | PASS |
| No non-ASCII characters | `grep -rPn '[^\x00-\x7F]' roles/minio/` | 0 matches | PASS |
| No `state: restarted` in role | `grep -rciE 'state: restarted' roles/minio/` | 0 matches | PASS |
| Single handler in handlers/main.yml | `grep -cE '^- name:' roles/minio/handlers/main.yml` | 1 | PASS |
| Five buckets in storage.yml | All 5 names in `telemetron_minio_buckets` | loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts present | PASS |
| vault.yml gitignored; vault.yml.example tracked | `git check-ignore` + `git ls-files` | vault.yml ignored; vault.yml.example tracked | PASS |
| Live MinIO deploy + bucket creation | Requires live Docker host | Not run (host /opt/telemetron permission-denied on Rock's homelab; role logic is correct) | SKIP (human) |
| Idempotency: changed=0 on second run | Requires live Docker host | Not verifiable without live run | SKIP (human) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FOUND-01 | 01-01 (doc), 01-02 (code) | telemetron Docker bridge network in playbook pre_tasks | SATISFIED | `deploy_docker.yml` pre_tasks creates `community.docker.docker_network` with `driver: bridge`; no shared base role |
| FOUND-02 | 01-03 | MinIO server + bucket bootstrap blocking | SATISFIED | `roles/minio/` complete; image pinned; bootstrap includes health poll + mc mb + mc ls verify; is final task |
| FOUND-03 | 01-01 (removed) | Intentionally dropped — Postgres requirement removed per D-02 | DROPPED | FOUND-03 is absent from REQUIREMENTS.md; absent from traceability table; rationale in PROJECT.md Key Decisions |
| INV-02 | 01-02 | example-homelab/ group_vars/all/ skeleton | SATISFIED | network.yml, storage.yml, vault.yml.example, minio.yml all present with correct content |
| OPS-01 | 01-03 | All images pinned, no :latest | SATISFIED | `minio_image_tag: RELEASE.2025-04-22T22-12-26Z`; `minio_mc_image_tag: RELEASE.2025-04-22T16-23-26Z`; grep gate passes |
| OPS-02 | 01-02, 01-03 | vault_<role>_<purpose> naming; vault.yml.example; .gitignore | SATISFIED | Keys `vault_minio_root_user` and `vault_minio_root_password` in vault.yml.example; real vault.yml gitignored |
| OPS-03 | 01-03 | Per-role README schema; roles pass yaml syntax check | SATISFIED | roles/minio/README.md is 181 lines with all required sections; --syntax-check exits 0 |
| OPS-04 | 01-03 | Idempotency: changed=0 on second run | SATISFIED (code) / HUMAN (live) | `changed_when: false` on all mc tasks; `state: started + recreate: false` on container; handler for restarts. Live verification needed |
| OPS-05 | 01-01, 01-03 | INSPQ/non-ASCII grep gates documented + roles/minio passes | SATISFIED | gates in roles/README.md; roles/minio/ returns 0 for all gate patterns |
| OPS-06 | 01-03 | Every container has HEALTHCHECK + unless-stopped + Etc/UTC | SATISFIED | `minio_healthcheck_*` vars set; `restart_policy: {{ minio_restart_policy }}` with default `unless-stopped`; `minio_tz: Etc/UTC` via `telemetron_tz` |

**Note on FOUND-03:** The phase requirement list in the verifier prompt includes FOUND-03 as removed (D-21 in plan 01-01). REQUIREMENTS.md confirms FOUND-03 is absent. The traceability table does not reference it. Correctly dropped.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `roles/minio/defaults/main.yml` | 27 | Self-referential default: `minio_container_name: "{{ minio_container_name \| default('minio') }}"` | Warning | Non-standard Ansible pattern. In practice it resolves correctly because: (a) defaults are lowest precedence so the inner `minio_container_name` is undefined at defaults-load time and returns 'minio', and (b) the inventory `minio.yml` overrides it with a literal `minio`. However, it is confusing and could cause a recursive template warning in strict mode. Not a blocker — the syntax check passes and the inventory provides a safe literal override. |

**No blocker anti-patterns found.** The self-referential default is a style warning only; the inventory provides a concrete literal value that takes precedence.

---

### Human Verification Required

#### 1. Live Deploy: MinIO up with network and buckets

**Test:** On a Docker host where the Ansible user can write to `/opt/telemetron/` (or with `telemetron_config_root` overridden to a writable path):

```bash
# Setup
cp inventory/example-homelab/group_vars/all/vault.yml.example \
   inventory/example-homelab/group_vars/all/vault.yml
# Edit vault.yml: set vault_minio_root_user and vault_minio_root_password
ansible-vault encrypt --ask-vault-pass \
  inventory/example-homelab/group_vars/all/vault.yml

# Run
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml \
                 --tags minio \
                 --ask-vault-pass
```

**Expected:**
- PLAY RECAP: `failed=0`
- `docker network ls | grep telemetron` shows bridge network with MinIO attached
- `docker inspect minio --format '{{.State.Health.Status}}'` returns `healthy`
- `docker inspect minio --format '{{.HostConfig.RestartPolicy.Name}}'` returns `unless-stopped`
- mc ls confirms all 5 buckets: loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts

**Why human:** Requires a live Docker host. Plan 01-03 documented that Rock's homelab has `/opt/telemetron` owned by root from a prior experiment. Either chown the directory or set `telemetron_config_root: /home/<user>/telemetron-config` in storage.yml before running. This is a host-prerequisite issue, not a role bug — the role logic is verified correct by inspection.

#### 2. Idempotency Gate

**Test:** Run the playbook a second time immediately after a successful first run (same vault, same inventory):

```bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/deploy_docker.yml \
                 --tags minio \
                 --ask-vault-pass
```

**Expected:** PLAY RECAP shows `changed=0, failed=0`

**Why human:** Can only be confirmed against a live converged host. The code path (`changed_when: false` on all mc tasks, `state: started + recreate: false`, handler-only restarts) is structurally correct by inspection.

---

### Gaps Summary

No gaps. All five observable truths are verified at the code/static level. The two human verification items (live deploy + idempotency) are conditional on a Docker host with correct `/opt/telemetron` permissions — documented as a host-prerequisite, not a role defect. The role correctly ships an override knob (`telemetron_config_root`) and the plan documents the operator action required.

One style warning: the self-referential `minio_container_name` default in `roles/minio/defaults/main.yml` is non-standard but harmless (inventory provides a literal override; syntax check passes).

---

_Verified: 2026-05-17T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
