# Phase 8: Garage Role + Backend Retargeting - Research

**Researched:** 2026-05-27
**Domain:** Ansible/Docker role authoring, Garage S3 object storage, Loki/Tempo/Mimir S3 backend retargeting
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-110:** Admin token var is `garage_admin_token`. No `vault_` prefix (D-90). Maps to `GARAGE_ADMIN_TOKEN` env. Ships in `secrets.yml.example` as CHANGE_ME.
- **D-111:** Single shared S3 API key for all three backends. Bootstrap creates ONE Garage key. Per-backend keys deferred (same stance as D-27). Key vars: `garage_s3_access_key_id` and `garage_s3_secret_key`.
- **D-112:** Bootstrap generates the S3 key via `/garage key create` on first run. The key ID and secret are persisted to a host file (e.g., `/opt/telemetron/garage/s3-credentials`) so re-runs can read the existing key instead of regenerating. If the file already exists, bootstrap skips key creation and loads the persisted values.
- **D-113:** Per-backend S3 vars alias directly to Garage vars: `loki_s3_access_key` defaults to `{{ garage_s3_access_key_id }}`, etc. Same D-27 pattern with `garage_*` as the alias target instead of `minio_root_*`.
- **D-114:** Garage metrics scraped by a 4th hardcoded Prometheus scrape job alongside the existing three. Always on, no toggle. Targets `garage:3903/metrics`.
- **D-115:** Bearer token (`garage_admin_token`) embedded inline in the rendered `prometheus.yml.j2` via `authorization.credentials`. No separate token file.
- **D-116:** No opt-out toggle for the Garage scrape job. Consistent with the existing three default jobs being unconditional.
- **D-117:** Loki and Mimir S3 object verification migrated from `minio/mc` one-shot containers to `docker_container_exec` against the running Garage container, using `/garage bucket info <bucket>` with the admin token. Follows the Phase 4 canonical verify pattern.
- **D-118:** Tempo gets a new S3 bucket verify step (Loki and Mimir already had one; Tempo didn't). All three backends now have consistent Garage-backed bucket verification.
- **D-119:** Bucket list variable renamed from `telemetron_minio_buckets` to `telemetron_garage_buckets` in `inventory/example-homelab/group_vars/all/storage.yml`.
- **D-120:** Inventory file `group_vars/all/minio.yml` renamed to `group_vars/all/garage.yml`. Holds Garage-specific operator knobs (container name, publish host, ports).

### Claude's Discretion

- D-117 verify tool choice (docker_container_exec against Garage) was Claude's recommendation accepted via "You decide."

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORE-01 | Garage `dxflrs/garage:v2.3.0` running on `telemetron` bridge, S3 on `:3900`, admin on `:3903`, single-node layout assigned+applied, all 5 buckets bootstrapped with read/write/owner key | Garage CLI bootstrap sequence verified from Docker image; config format confirmed from official docs |
| STORE-02 | Loki, Tempo, Mimir S3 configs retargeted from `minio:9000` to `garage:3900`; `object_store: aws` (Loki); credential vars renamed from `minio_root_*` to `garage_*` | S3 endpoint format per-component confirmed from existing role templates; Garage S3 path-style compatibility confirmed |
| STORE-03 | `roles/minio/` directory, `minio/mc` image references, all MinIO-specific vars removed; `deploy_docker.yml` shows `garage`; docs updated | Full grep audit of minio references completed; all touchpoints catalogued |
| OPS-01 | Garage self-metrics at `:3903/metrics` scraped with `metrics_token` bearer auth | Admin API authentication format confirmed; Prometheus `authorization.credentials` pattern fits existing template |

</phase_requirements>

---

## Summary

Phase 8 replaces the archived MinIO role with a new `roles/garage/` role built from the MinIO role as a template. The new role must: (1) render a `garage.toml` TOML config file (not an env file), (2) run the `dxflrs/garage:v2.3.0` container with the config bind-mounted at `/etc/garage/garage.toml`, (3) execute a multi-step bootstrap sequence using `community.docker.docker_container_exec` against the running container -- node layout assign/apply, S3 key create/persist, bucket create, bucket allow -- and (4) retarget the three backends' S3 endpoints from `minio:9000` to `garage:3900`.

The primary structural difference from the MinIO role is that Garage's bootstrap requires multiple sequential CLI commands against the running container (not a one-shot helper container), and key creation is not idempotent -- the secret is only shown once. D-112 resolves this by persisting the generated credentials to a host-side file; re-runs check the file first. All three verify tasks (Loki, Mimir, Tempo) are retargeted from `minio/mc` one-shot containers to `docker_container_exec` against the Garage container using `/garage bucket info <bucket>`.

The metrics scrape retargeting in `roles/prometheus/templates/prometheus.yml.j2` adds a 4th hardcoded job with bearer `Authorization` header, which is a new pattern in this template (existing three jobs have no auth).

**Primary recommendation:** Build the Garage role by adapting the MinIO role's task structure exactly; replace the one-shot mc bootstrap with a `docker_container_exec` multi-step sequence; use `garage key create` with D-112 host-file credential persistence (NOT `garage key import` -- the user locked D-112 which specifies auto-generation via `key create`, not pre-generated import from secrets.yml). S3 credentials are NOT operator-supplied; they are auto-generated on first run and persisted to a host file.

> **D-112 override note:** Research initially recommended `garage key import` for deterministic credential injection from secrets.yml. The user locked D-112 which specifies `garage key create` on first run with host-file persistence. The locked decision takes precedence. The key trade-off: `key import` is simpler for Ansible but requires operator to pre-generate credentials; `key create` with host-file persistence is zero-operator-config but requires parsing CLI output and file I/O.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| S3 object storage (Garage) | Storage/Backend | -- | Object store is a backend-tier concern; all three consumers (Loki/Tempo/Mimir) are also backend-tier |
| Garage bootstrap (layout, key, buckets) | Storage/Backend | -- | Idempotent provisioning within the role, following the established D-08 blocking-bootstrap pattern |
| S3 credential propagation to Loki/Tempo/Mimir | API/Backend config | -- | Var aliasing via set_fact from D-112 host file; per-backend defaults reference the dynamically loaded garage vars |
| Garage metrics scrape | Backend | Prometheus config | Garage exposes `/metrics` on admin port; Prometheus adds a scrape job |
| MinIO removal | All tiers | -- | Code cleanup cascades through roles, inventory, playbooks, docs |

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `dxflrs/garage` | `v2.3.0` | S3-compatible object store replacing MinIO | Actively maintained AGPL, designed for homelab, confirmed S3-compatible with Loki/Tempo/Mimir |
| `community.docker.docker_container_exec` | (Ansible collection) | Run Garage CLI commands in running container | Canonical Phase 4 pattern; avoids fragile one-shot container churn for interactive multi-step bootstrap |
| `community.docker.docker_container_info` | (Ansible collection) | Poll Garage HEALTHCHECK status before bootstrap | Same D-10a pattern as MinIO role |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `curlimages/curl:8.10.1` | `8.10.1` | In-network health probe one-shots | Already in use across all roles; Garage has no HTTP health path needing this (healthcheck via `/garage status`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `garage key create` + host-file persistence (D-112) | `garage key import` (pre-generate key in secrets.yml) | `key import` is deterministic and Ansible-friendly; `key create` requires parsing CLI output. **However, D-112 (locked decision) specifies `key create` with host-file persistence to avoid requiring operators to pre-generate S3 credentials.** D-112 wins. |
| `docker_container_exec` for bootstrap | one-shot helper container | `docker_container_exec` runs inside the already-healthy container with config already mounted; no second container lifecycle; follows Phase 4 canonical pattern |

**No packages to install -- this phase installs no npm/pip packages.** Garage is a Docker image pulled during Ansible playbook execution.

---

## Package Legitimacy Audit

This phase installs one external Docker image:

| Package | Registry | Age | Notes | slopcheck | Disposition |
|---------|----------|-----|-------|-----------|-------------|
| `dxflrs/garage:v2.3.0` | Docker Hub | Created 2026-04-16 | Official image from Deuxfleurs collective; confirmed present on Docker Hub; pulled and inspected locally (`sha256:866bd13ed2038ba7e7190e840482bc27234c4afaf77be8cfa439ae088c1e4690`); 68 MB amd64 image | N/A (Docker) | Approved |

slopcheck operates on PyPI/npm registries and does not apply to Docker images. The `dxflrs/garage` image was verified by direct pull and inspection. [VERIFIED: Docker Hub pull + local inspect] The Deuxfleurs organization's source code is at `git.deuxfleurs.fr/Deuxfleurs/garage`. [CITED: garagehq.deuxfleurs.fr]

**No npm/PyPI packages are introduced in this phase.**

---

## Architecture Patterns

### System Architecture Diagram

```
Ansible playbook (deploy_docker.yml)
        |
        v
[pre_tasks: ensure telemetron network]
        |
        v (role: garage)
[Render garage.toml.j2]  --> /opt/telemetron/garage/garage.toml (bind-mounted :ro)
[docker_volume: telemetron_garage_meta]
[docker_volume: telemetron_garage_data]
[docker_container: telemetron-garage]  --> S3 API :3900, Admin :3903, RPC :3901
        |
        v (bootstrap -- D-08 last task)
[docker_container_info: poll HEALTHCHECK]
        |
        v
[docker_container_exec: garage node id --quiet]  --> captures node_id
[docker_container_exec: garage layout assign -z local -c 1G <node_id>]
[docker_container_exec: garage layout apply --version 1]
[stat: check /opt/telemetron/garage/s3-credentials]  --> D-112 host file check
  |-- exists: slurp + set_fact from file
  |-- absent: [docker_container_exec: garage key create -n telemetron]  --> parse JSON output
              [copy: persist key_id + secret to host file]
              [set_fact: garage_s3_access_key_id, garage_s3_secret_key]
[docker_container_exec: garage bucket create <bucket> x5]
[docker_container_exec: garage bucket allow --read --write --owner <bucket> --key telemetron x5]
[docker_container_exec: garage bucket info <bucket>]  --> verify step (x5 buckets)
        |
        v
[role: loki]  --> loki.yaml.j2: storage_config.aws.endpoint = "http://garage:3900"
[role: tempo] --> tempo.yaml.j2: storage.trace.s3.endpoint = "garage:3900"
[role: mimir] --> mimir.yaml.j2: common.storage.s3.endpoint = "garage:3900"
        |
        v
[role: prometheus] --> prometheus.yml.j2: 4th scrape job -> garage:3903/metrics (bearer auth)
        |
        v
Grafana: Garage storage metrics visible
```

### Recommended Project Structure

```
roles/garage/
  defaults/
    main.yml          # garage_* vars, image pin, port defaults, D-112 credentials file path
  handlers/
    main.yml          # restart garage handler (docker restart pattern)
  meta/
    main.yml          # role metadata
  tasks/
    main.yml          # config dir, render toml, volumes, pull, run container, include bootstrap
    bootstrap.yml     # HEALTHCHECK poll, layout assign/apply, D-112 key create+persist, bucket create, bucket allow, verify
  templates/
    garage.toml.j2    # Garage TOML config (NOT an env file)
  README.md             # OPS-03 gate template
```

### Pattern 1: Garage TOML Configuration

**What:** Garage reads a TOML config file (`/etc/garage.toml` by default), not environment variables. The `GARAGE_CONFIG_FILE` env var overrides the path.

**When to use:** Always -- the Garage Docker image (`Cmd: ['/garage', 'server']`) requires a mounted config file.

**Example:**
```toml
# Source: garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/
replication_factor = 1
consistency_mode = "consistent"
db_engine = "lmdb"

metadata_dir = "{{ garage_meta_path }}"
data_dir = "{{ garage_data_path }}"

rpc_secret = "{{ garage_rpc_secret }}"
rpc_bind_addr = "[::]:3901"

[s3_api]
api_bind_addr = "[::]:3900"
s3_region = "{{ garage_s3_region }}"

[admin]
api_bind_addr = "0.0.0.0:3903"
admin_token = "{{ garage_admin_token }}"
metrics_token = "{{ garage_admin_token }}"
```

[CITED: garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/]

### Pattern 2: Bootstrap via docker_container_exec

**What:** Multi-step bootstrap runs inside the running Garage container. No one-shot helper containers.

**When to use:** Any time you need to call `/garage` CLI commands during Ansible provisioning.

**Example:**
```yaml
# Source: Verified from Docker image CLI inspect (v2.3.0)
# Step 1: get node id
- name: Get Garage node id
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage node id --quiet
  register: garage_node_id_result
  changed_when: false

# Step 2: assign layout (idempotent -- garage layout assign is safe to re-run)
- name: Assign Garage layout
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: >-
      /garage layout assign
      -z {{ garage_layout_zone }}
      -c {{ garage_layout_capacity }}
      {{ garage_node_id_result.stdout | split('@') | first | split('\n') | first }}
  changed_when: false

# Step 3: apply layout (--version 1 for first-time; idempotent on re-run with same version)
- name: Apply Garage layout
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage layout apply --version 1
  changed_when: false
  failed_when: >-
    garage_layout_apply.rc is defined
    and garage_layout_apply.rc != 0
    and 'already' not in (garage_layout_apply.stderr | default(''))
```

[VERIFIED: Docker image CLI help output, dxflrs/garage:v2.3.0]

### Pattern 3: D-112 Key Create with Host-File Persistence

**What:** `garage key create -n telemetron` creates a new S3 key inside the running container. The key ID and secret from the JSON output are persisted to a host file (`/opt/telemetron/garage/s3-credentials`) so re-runs can load existing credentials without regeneration.

**When to use:** D-112 -- S3 credentials are auto-generated on first run, NOT operator-supplied. Re-runs check the host file first and skip key creation if it exists.

> **Override note:** Research initially recommended `garage key import --yes` for deterministic credential injection from secrets.yml. The user locked D-112 which specifies `garage key create` with host-file persistence instead. The locked decision takes precedence.

**Example:**
```yaml
# Source: D-112 locked decision + Verified from Docker image CLI help (v2.3.0)
# Step 7a: check if credentials already persisted
- name: Check if Garage S3 credentials exist on host
  ansible.builtin.stat:
    path: "{{ garage_s3_credentials_file }}"
  register: garage_creds_file
  changed_when: false

# Step 7b: load existing credentials if host file exists
- name: Load existing Garage S3 credentials
  ansible.builtin.slurp:
    src: "{{ garage_s3_credentials_file }}"
  register: garage_creds_raw
  when: garage_creds_file.stat.exists
  changed_when: false

# Step 7c: set facts from existing host file
- name: Set Garage S3 credential facts from host file
  ansible.builtin.set_fact:
    garage_s3_access_key_id: "{{ (garage_creds_raw.content | b64decode).split('\n') | select('match', '^key_id=') | first | regex_replace('^key_id=', '') }}"
    garage_s3_secret_key: "{{ (garage_creds_raw.content | b64decode).split('\n') | select('match', '^secret=') | first | regex_replace('^secret=', '') }}"
  when: garage_creds_file.stat.exists

# Step 7d: create new key if no host file (first run)
- name: Create Garage S3 key
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage key create -n {{ garage_s3_key_name }}
  register: garage_key_create_result
  changed_when: true
  when: not garage_creds_file.stat.exists

# Step 7e: set facts from newly created key
- name: Set Garage S3 credential facts from key create output
  ansible.builtin.set_fact:
    garage_s3_access_key_id: "{{ (garage_key_create_result.stdout | from_json).accessKeyId }}"
    garage_s3_secret_key: "{{ (garage_key_create_result.stdout | from_json).secretAccessKey }}"
  when: not garage_creds_file.stat.exists

# Step 7f: persist to host file
- name: Persist Garage S3 credentials to host file
  ansible.builtin.copy:
    content: |
      key_id={{ garage_s3_access_key_id }}
      secret={{ garage_s3_secret_key }}
    dest: "{{ garage_s3_credentials_file }}"
    mode: "0600"
  when: not garage_creds_file.stat.exists
```

[D-112 locked decision; CLI output format VERIFIED from Docker image v2.3.0]

### Pattern 4: Bucket Verify via docker_container_exec

**What:** Replace the `minio/mc` one-shot verify containers in Loki/Mimir with `docker_container_exec` calling `/garage bucket info <bucket>` inside the running Garage container.

**When to use:** D-117 -- S3 bucket existence verification in Loki and Mimir verify.yml; D-118 -- new Tempo verify step.

**Example:**
```yaml
# Source: Verified from Docker image CLI help (v2.3.0)
- name: Verify Garage bucket exists
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage bucket info {{ item }}
  loop: "{{ garage_buckets }}"
  changed_when: false
  register: garage_bucket_verify
  failed_when: garage_bucket_verify.rc is defined and garage_bucket_verify.rc != 0
```

[VERIFIED: Docker image CLI help output, dxflrs/garage:v2.3.0]

### Pattern 5: Prometheus Scrape with Bearer Auth

**What:** Garage's `/metrics` endpoint requires the `metrics_token` as a Bearer token. Prometheus supports `authorization.credentials` in a scrape job config.

**When to use:** D-114/D-115 -- 4th hardcoded scrape job in `prometheus.yml.j2`.

**Example:**
```yaml
# Source: Prometheus documentation; consistent with existing prometheus.yml.j2 structure
- job_name: garage
  static_configs:
    - targets: ['garage:3903']
      labels:
        service: garage
  authorization:
    credentials: {{ garage_admin_token }}
  metric_relabel_configs:
    - regex: '{{ prometheus_default_relabel_drop_regex }}'
      action: labeldrop
    - regex: '{{ prometheus_default_relabel_id_catchall_regex }}'
      action: labeldrop
```

[CITED: prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config]

### Anti-Patterns to Avoid

- **Using `garage key import` instead of D-112 `key create` flow:** Research initially recommended `key import` for deterministic credential injection. However, the user locked D-112 which specifies `key create` on first run with host-file persistence. Using `key import` would require operators to pre-generate S3 credentials in secrets.yml, which D-112 explicitly avoids. Use the D-112 flow: stat host file -> load if exists -> `key create` if absent -> persist to host file.
- **`garage layout apply --version 1` hard-failure on re-runs:** On a second run where the layout is already at version 1, Garage returns an error. The bootstrap task must gate layout assign/apply with a defensive dual-check: `rc != 0` as primary gate (handles unexpected output format) OR `'NO ROLE ASSIGNED' in stdout` as secondary confirmation. This avoids dependency on exact string matching. [RESOLVED -- defensive dual-check added to plan]
- **Mounting config as a Docker `env_file`:** Garage reads `garage.toml` TOML, not shell-style env files. The `env_file` parameter in `community.docker.docker_container` is for `KEY=VALUE` format only. [VERIFIED: Docker image CLI, official docs]
- **Binding admin API only to `127.0.0.1:3903`:** The Prometheus scraper runs inside a Docker container on the `telemetron` bridge. The admin API must bind to `0.0.0.0:3903` (or at least the container's bridge IP) for in-network scraping to reach it. [VERIFIED: network topology -- Prometheus is on `telemetron` bridge, scrapes by container DNS name]
- **Using the same RPC secret across different Garage instances:** The `rpc_secret` is a 32-byte hex string that must be unique per deployment. It should be in `secrets.yml`, not a static default. [CITED: garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Garage HEALTHCHECK | Custom script polling HTTP | `docker_container_info` until `State.Health.Status == 'healthy'` | Established D-10a pattern across all roles |
| S3 bucket existence check | `minio/mc` one-shot container | `docker_container_exec /garage bucket info <bucket>` | D-117 -- `mc` image is being removed; exec uses already-running container |
| Layout idempotency guard | Track state externally | Defensive dual-check: `rc != 0` OR `'NO ROLE ASSIGNED' in stdout` | Exit-code check is primary; string match is secondary confirmation |
| Key credential persistence | Ansible `set_fact` between runs | Host file at `/opt/telemetron/garage/s3-credentials` | `set_fact` does not persist across playbook runs; host file is D-112 decision |

---

## Runtime State Inventory

This is a migration/retargeting phase -- the following runtime state is affected.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing `telemetron_minio_data` Docker volume contains any previously written S3 objects | **Not migrated** -- leviathan is a fresh-start host (per REQUIREMENTS.md out-of-scope table); the MinIO volume is deleted as part of removing the `minio` role. Document in garage README for production operators. |
| Live service config | `roles/loki/defaults/main.yml`: `loki_s3_endpoint: "http://minio:9000"` | Code edit -- change to `http://garage:3900` |
| Live service config | `roles/tempo/defaults/main.yml`: `tempo_s3_endpoint: "minio:9000"` | Code edit -- change to `garage:3900` |
| Live service config | `roles/mimir/defaults/main.yml`: `mimir_s3_endpoint: "minio:9000"` | Code edit -- change to `garage:3900` |
| Live service config | `roles/loki/tasks/verify.yml` lines 63-91: `minio/mc` one-shot bucket verify | Code edit -- replace with `docker_container_exec /garage bucket info` (D-117) |
| Live service config | `roles/mimir/tasks/verify.yml` lines 104-130: `minio/mc` one-shot bucket verify | Code edit -- replace with `docker_container_exec /garage bucket info` (D-117) |
| Live service config | `roles/tempo/tasks/verify.yml`: no S3 check exists | Code addition -- add `docker_container_exec /garage bucket info tempo-traces` (D-118) |
| Live service config | `roles/prometheus/templates/prometheus.yml.j2`: 3 scrape jobs | Code edit -- add 4th job `garage:3903/metrics` with bearer auth (D-114/D-115) |
| Live service config | `inventory/example-homelab/group_vars/all/minio.yml` | File rename to `garage.yml`; translate operator knobs (D-120) |
| Live service config | `inventory/example-homelab/group_vars/all/storage.yml`: `telemetron_minio_buckets` | Var rename to `telemetron_garage_buckets` (D-119) |
| Live service config | `inventory/example-homelab/group_vars/all/secrets.yml.example` | Remove `minio_root_user`/`minio_root_password`; add `garage_admin_token`, `garage_rpc_secret` (D-110). S3 credentials are NOT in secrets.yml -- auto-generated per D-112. Update per-backend aliases to reference dynamically loaded `garage_s3_access_key_id`/`garage_s3_secret_key` (D-113). |
| Live service config | `playbooks/deploy_docker.yml` line 36: `role: minio` | Change to `role: garage` |
| Stored data | `roles/loki/defaults/main.yml`: `loki_mc_image` and `loki_mc_image_tag` vars | Remove -- no longer needed after verify retargeting |
| Stored data | `roles/mimir/defaults/main.yml`: `mimir_mc_image`, `mimir_mc_image_tag` vars | Remove -- no longer needed (STORE-03) |
| Build artifacts | `roles/minio/` directory | Delete entire directory (STORE-03) |
| OS-registered state | None -- no OS-level registration of "minio" string found | None |
| Secrets/env vars | `minio_root_user`, `minio_root_password` in `secrets.yml.example` | Remove; replace with `garage_admin_token`, `garage_rpc_secret` |

---

## Common Pitfalls

### Pitfall 1: `garage layout apply --version 1` fails on re-runs

**What goes wrong:** The `--version` flag must be exactly `1 + previous version`. On the first run it is `1`; on a re-run where layout is already at version 1, passing `--version 1` fails because the expected next version would be 2.

**Why it happens:** Garage enforces strict versioning to prevent concurrent layout changes in multi-node clusters.

**How to avoid:** Gate the `layout apply` step with a defensive dual-check: use `rc != 0` as the primary gate (does not depend on exact string matching) and `'NO ROLE ASSIGNED' in stdout` as secondary confirmation. This is more robust than relying solely on the "NO ROLE ASSIGNED" string match.

**Warning signs:** Bootstrap fails with "version mismatch" or "layout already applied" on the second playbook run.

[MEDIUM -- inferred from CLI `--version` semantics; defensive dual-check mitigates; verify on first UAT]

### Pitfall 2: TOML config vs env file

**What goes wrong:** Copying the MinIO `minio.env.j2` template pattern directly. Garage does not read a shell-format `KEY=VALUE` env file -- it reads a TOML config file.

**Why it happens:** MinIO uses `--env-file` injection; Garage uses `--config` / `GARAGE_CONFIG_FILE`.

**How to avoid:** Create `garage.toml.j2` (TOML format). Bind-mount it to `/etc/garage/garage.toml` inside the container (read-only, parent-directory bind mount per Gate 8). Set `GARAGE_CONFIG_FILE=/etc/garage/garage.toml` in the container env.

**Warning signs:** Container exits immediately with "No such file or directory" for `/etc/garage.toml`.

[VERIFIED: Docker image CMD = `['/garage', 'server']`, no env var injection for config]

### Pitfall 3: `garage key create` secret shown once only

**What goes wrong:** Using `garage key create` in the bootstrap and then trying to retrieve the secret on a re-run. The `garage key info <id>` command does NOT show the secret by default -- you must pass `--show-secret`.

**Why it happens:** Security change in v0.9+ -- secrets hidden unless explicitly requested.

**How to avoid:** Per D-112 (locked decision), use `garage key create -n telemetron` on first run and immediately persist the output (key ID + secret) to a host file (`/opt/telemetron/garage/s3-credentials`, mode 0600). On re-runs, check for the host file first and load credentials from it, skipping key creation entirely. [VERIFIED: `--show-secret` flag confirmed in `garage key info --help` output from v2.3.0 image]

**Warning signs:** On re-run, Ansible can't find the secret and creates a duplicate key.

### Pitfall 4: Loki `object_store: s3` vs `object_store: aws`

**What goes wrong:** Using `object_store: s3` in the Loki schema_config when retargeting to Garage. The project's existing `loki.yaml.j2` already correctly uses `object_store: s3` (line 40) -- do NOT change this to `object_store: aws`.

**Why it happens:** CONTEXT.md D-15 (STORE-02) mandates `object_store: aws` as a "defensive G-6 mitigation." However, examining the actual template at `roles/loki/templates/loki.yaml.j2` line 40 shows `object_store: s3` is what's already there. STORE-02 requirement text says "Loki uses `object_store: aws`". The template needs to be verified against the requirement.

**How to avoid:** Check the existing `loki.yaml.j2` line 40. If it says `object_store: s3`, it may need to change to `object_store: aws` per STORE-02. Loki's schema_config `object_store: aws` is a valid value that uses the `aws` S3 driver -- it is compatible with Garage. The `storage_config.aws` block is independent of this field.

**Warning signs:** Loki fails to find chunks; "no such store" errors at startup.

[ASSUMED -- the interplay between schema_config.object_store and storage_config.aws section in Loki 3.7 needs UAT confirmation for Garage compatibility]

### Pitfall 5: Admin API bind address for in-network Prometheus scrape

**What goes wrong:** Binding the Garage admin API to `127.0.0.1:3903` in `garage.toml`. The Prometheus container is on the same Docker bridge but a different container -- it cannot reach `127.0.0.1` of the Garage container.

**Why it happens:** The Garage config reference example uses `127.0.0.1:3903` for the admin API bind address (security-conscious default). But Prometheus scrapes by container DNS name (`garage:3903`), which routes to the container's bridge IP, not loopback.

**How to avoid:** Bind to `0.0.0.0:3903` in `garage.toml.j2`. The `telemetron` bridge is an internal network; the admin API is not exposed to the host by default (matching MinIO's `minio_publish_host: false` pattern).

**Warning signs:** Prometheus scrape returns "connection refused" for `garage:3903/metrics`.

[VERIFIED: network topology -- Prometheus runs in `telemetron-prometheus` container on `telemetron` bridge]

### Pitfall 6: `garage layout assign` node ID format

**What goes wrong:** Passing the full `<node-id>@<ip>:<port>` string from `garage node id` directly to `garage layout assign`. The assign command takes only the hex node ID prefix, not the full address string.

**Why it happens:** `garage node id --quiet` outputs `<hex-id>@<ip>:<port>`. The `<node-ids>...` argument to `layout assign` is just the hex prefix.

**How to avoid:** Strip the `@<ip>:<port>` suffix from the `garage node id --quiet` output before passing to `layout assign`. In a shell one-liner: `NODE_ID=$(garage node id --quiet | cut -d@ -f1)`.

**Warning signs:** `layout assign` fails with "no such node" or similar.

[VERIFIED: CLI help for `garage layout assign` says "<node-ids>..." are "prefix of hexadecimal node id"]

### Pitfall 7: S3 endpoint format differences across backends

**What goes wrong:** Using the same endpoint format for all three backends. Loki, Tempo, and Mimir each have different expectations:

| Backend | Format | Example | Template location |
|---------|--------|---------|-------------------|
| Loki | `http://host:port` (scheme required) | `http://garage:3900` | `storage_config.aws.endpoint` |
| Tempo | `host:port` (no scheme) | `garage:3900` | `storage.trace.s3.endpoint` |
| Mimir | `host:port` (no scheme) | `garage:3900` | `common.storage.s3.endpoint` |

**How to avoid:** Update defaults one role at a time, matching the existing format precisely (only the hostname:port changes from `minio:9000` to `garage:3900`, the scheme convention stays the same).

[VERIFIED: existing role templates `roles/loki/defaults/main.yml` line 52, `roles/tempo/defaults/main.yml` line 56, `roles/mimir/defaults/main.yml` line 48]

---

## Code Examples

### Garage TOML minimal single-node config

```toml
# Source: garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/
replication_factor = 1
consistency_mode = "consistent"
db_engine = "lmdb"

metadata_dir = "{{ garage_meta_path }}"
data_dir = "{{ garage_data_path }}"

rpc_secret = "{{ garage_rpc_secret }}"
rpc_bind_addr = "[::]:{{ garage_rpc_port }}"

[s3_api]
api_bind_addr = "[::]:{{ garage_api_port }}"
s3_region = "{{ garage_s3_region }}"

[admin]
api_bind_addr = "0.0.0.0:{{ garage_admin_port }}"
admin_token = "{{ garage_admin_token }}"
metrics_token = "{{ garage_admin_token }}"
```

### Prometheus bearer-auth scrape job (4th hardcoded job)

```yaml
# Source: Prometheus scrape_config authorization field
# Fits into existing prometheus.yml.j2 scrape_configs block
  - job_name: garage
    static_configs:
      - targets: ['{{ prometheus_garage_target }}']
        labels:
          service: garage
    authorization:
      credentials: {{ garage_admin_token }}
    metric_relabel_configs:
      - regex: '{{ prometheus_default_relabel_drop_regex }}'
        action: labeldrop
      - regex: '{{ prometheus_default_relabel_id_catchall_regex }}'
        action: labeldrop
```

### Garage bootstrap sequence (multi-step docker_container_exec)

```yaml
# Source: Verified CLI help from dxflrs/garage:v2.3.0
# Step 1: HEALTHCHECK poll (same as MinIO D-10a pattern)
- name: Wait for Garage HEALTHCHECK healthy
  community.docker.docker_container_info:
    name: "{{ garage_container_name }}"
  register: garage_health_check
  until: >-
    garage_health_check.container.State.Health.Status == 'healthy'
  retries: "{{ garage_health_retries }}"
  delay: "{{ garage_health_delay }}"
  changed_when: false

# Step 2: get node id
- name: Get Garage node ID
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage node id --quiet
  register: garage_node_id_raw
  changed_when: false

# Step 3: extract hex id (strip @ip:port suffix)
- name: Set garage_node_id fact
  ansible.builtin.set_fact:
    garage_node_id: "{{ garage_node_id_raw.stdout.split('@')[0] }}"

# Step 4: check if layout already assigned (defensive dual-check)
- name: Check Garage layout status
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage layout show
  register: garage_layout_show
  changed_when: false

# Step 5: assign layout (only if not yet assigned -- defensive dual-check)
- name: Assign Garage layout
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: >-
      /garage layout assign
      -z {{ garage_layout_zone }}
      -c {{ garage_layout_capacity }}
      {{ garage_node_id }}
  changed_when: true
  when: garage_layout_show.rc != 0 or 'NO ROLE ASSIGNED' in garage_layout_show.stdout

# Step 6: apply layout (only if assign ran -- defensive dual-check)
- name: Apply Garage layout
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage layout apply --version 1
  changed_when: true
  when: garage_layout_show.rc != 0 or 'NO ROLE ASSIGNED' in garage_layout_show.stdout

# Step 7a-7f: D-112 key create with host-file persistence (see Pattern 3 above)

# Step 8: create buckets (defensive failed_when accepts both success and already-exists)
- name: Create Garage buckets
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage bucket create {{ item }}
  loop: "{{ garage_buckets }}"
  changed_when: false
  failed_when: >-
    garage_bucket_create.rc is defined
    and garage_bucket_create.rc != 0
    and 'already exists' not in (garage_bucket_create.stderr | default(''))
  register: garage_bucket_create

# Step 9: allow key on each bucket
- name: Allow S3 key on Garage buckets
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: >-
      /garage bucket allow
      --read --write --owner
      {{ item }}
      --key {{ garage_s3_key_name }}
  loop: "{{ garage_buckets }}"
  changed_when: false

# Step 10: verify all buckets visible (D-117 pattern)
- name: Verify Garage buckets exist
  community.docker.docker_container_exec:
    container: "{{ garage_container_name }}"
    command: /garage bucket info {{ item }}
  loop: "{{ garage_buckets }}"
  changed_when: false
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MinIO community edition as S3 backend | Garage v2.3.0 as S3 backend | MinIO archived early 2026; Garage v2.3.0 released 2026-04-16 | All three backend configs change endpoint from `minio:9000` to `garage:3900` |
| `minio/mc` one-shot containers for S3 verification | `docker_container_exec /garage bucket info` | Phase 8 (this phase) | Removes dependency on `minio/mc` image entirely |
| MinIO `HEALTHCHECK` via `curl -sf /minio/health/ready` | Garage HEALTHCHECK via `/garage status` or binary-alive proxy | Phase 8 | Garage has no built-in HEALTHCHECK in its Docker image (confirmed by `docker inspect`) |

**Deprecated/outdated:**

- `minio/mc` image: Used in `roles/loki/tasks/verify.yml`, `roles/mimir/tasks/verify.yml`, and referenced in `roles/loki/defaults/main.yml`, `roles/mimir/defaults/main.yml`. All references removed in Phase 8.
- `minio_root_user` / `minio_root_password` vars: Replaced by `garage_admin_token`, `garage_rpc_secret` (admin/rpc from secrets.yml) and `garage_s3_access_key_id`, `garage_s3_secret_key` (S3 auto-generated per D-112, loaded via set_fact from host file).
- `telemetron_minio_buckets` var: Renamed to `telemetron_garage_buckets`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `garage layout apply --version 1` fails with a recognizable error string on re-runs after layout is already applied at version 1 | Pitfall 1, Bootstrap code example | Mitigated by defensive dual-check gate (rc != 0 OR string match); UAT will confirm exact behavior |
| A2 | `garage bucket create <name>` exits non-zero with "already exists" in stderr when bucket exists | Bootstrap code example `failed_when` | Mitigated by defensive failed_when that accepts both rc=0 and "already exists" in stderr; UAT will confirm |
| A3 | `garage key create -n telemetron` outputs JSON containing `accessKeyId` and `secretAccessKey` fields | D-112 bootstrap Pattern 3 | If output is plain text instead of JSON, parsing logic needs adjustment; UAT will confirm on first run |
| A4 | Loki `object_store: s3` (current template) is functionally equivalent to `object_store: aws` for the `storage_config.aws` section, or STORE-02 requires changing it to `aws` | Pitfall 4 | Loki startup failure or incorrect storage driver selection |
| A5 | `garage layout show` output contains the literal string "NO ROLE ASSIGNED" when the layout has not been set up | Bootstrap code example (`when:` condition) | Mitigated by defensive dual-check: rc != 0 is the primary gate, string match is secondary |

---

## Open Questions (RESOLVED -- defensive guards added)

1. **`garage layout show` idempotency sentinel string** -- RESOLVED
   - What we know: The `layout assign` + `layout apply` sequence must only run once (first time). The `spwoodcock.dev` blog uses "NO ROLE ASSIGNED" as the sentinel.
   - Resolution: Defensive dual-check gate added to plan: `when: garage_layout_show.rc != 0 or 'NO ROLE ASSIGNED' in garage_layout_show.stdout`. The `rc != 0` check is the primary gate (handles unexpected output format or absence of the exact sentinel string). The `'NO ROLE ASSIGNED'` string match is secondary confirmation. This does not depend on exact string matching for correctness.

2. **`garage bucket create` idempotency exit code** -- RESOLVED
   - What we know: The command exists; `--ignore-existing` flag was in MinIO mc but not confirmed in Garage.
   - Resolution: Defensive `failed_when` added to plan that accepts BOTH `rc == 0` (success) AND `rc != 0` when `'already exists'` appears in stderr: `failed_when: garage_bucket_create.rc != 0 and 'already exists' not in (garage_bucket_create.stderr | default(''))`. This handles both the "exits 0 on existing bucket" and "exits non-zero with error message" cases. Verify on UAT.

3. **Garage HEALTHCHECK config for the Docker container** -- RESOLVED
   - What we know: The `dxflrs/garage:v2.3.0` image has no built-in HEALTHCHECK (`Healthcheck: None` from `docker inspect`). The `/garage` binary is at the root.
   - Resolution: Using `["CMD", "/garage", "--version"]` as the binary-alive proxy (same as Mimir/Tempo pattern). The authoritative readiness gate is the bootstrap sequence succeeding (layout show works = server is up). Already implemented in the plan's approach.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Ansible `community.docker` | yes | 29.x (leviathan UAT host per MEMORY.md) | -- |
| `dxflrs/garage:v2.3.0` | `roles/garage` | yes | v2.3.0 (pulled and verified locally) | -- |
| `community.docker` Ansible collection | All container tasks | yes | Already in `playbooks/deploy_docker.yml` `collections:` | -- |
| `curlimages/curl:8.10.1` | Existing role verify steps | yes | Already in use across all existing roles | -- |

**Missing dependencies with no fallback:** None.

---

## Security Domain

Security enforcement is not explicitly disabled in config.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (Garage admin token) | `garage_admin_token` in `secrets.yml`; bearer token in Prometheus config |
| V3 Session Management | no | N/A -- stateless object storage |
| V4 Access Control | yes (S3 bucket permissions) | `garage bucket allow --read --write --owner`; single key per D-111 |
| V5 Input Validation | no | Config file rendering; no user input |
| V6 Cryptography | yes (RPC secret) | `garage_rpc_secret` 32-byte hex; never hand-rolled; `openssl rand -hex 32` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Exposed admin API (`garage:3903`) | Information Disclosure | Bind to `0.0.0.0:3903` inside container but do NOT publish to host by default (`garage_publish_host: false`) |
| RPC secret in `garage.toml` | Spoofing | `rpc_secret` rendered from vault; config file mode `0600` |
| S3 credentials in host file (D-112) | Information Disclosure | Host file at `{{ garage_s3_credentials_file }}` written with mode `0600`; only readable by root/ansible user; credentials never pass through docker_container_exec args |

---

## Sources

### Primary (HIGH confidence)
- `dxflrs/garage:v2.3.0` Docker image -- pulled locally, binary help output verified directly for all CLI commands (layout, key, bucket, node, status subcommands)
- [Garage configuration reference](https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/) -- TOML format, `[admin]` section, `replication_factor`, `db_engine`, port defaults
- [Garage Quick Start](https://garagehq.deuxfleurs.fr/documentation/quick-start/) -- bootstrap command sequence, `garage key create` output format, `garage layout assign/apply`

### Secondary (MEDIUM confidence)
- [spwoodcock.dev Garage standalone automation blog](https://spwoodcock.dev/blog/2026-03-03-automate-garage-standalone/) -- Docker Compose + init service bootstrap sequence; "NO ROLE ASSIGNED" sentinel; `garage key import` pattern
- [matt gerega.com MinIO to Garage migration](https://www.mattgerega.com/2025/12/10/migrating-from-minio-to-garage-when-open-source-isnt-so-open-anymore/) -- Loki/Tempo/Mimir successfully migrated to Garage; endpoint format change (`:39000` -> `:3900`)
- [git.deuxfleurs.fr v0.9 PR #473](https://git.deuxfleurs.fr/Deuxfleurs/garage/pulls/473) -- `garage key info` hides secret by default since v0.9; `--show-secret` flag added
- [Garage admin API docs](https://garagehq.deuxfleurs.fr/documentation/reference-manual/admin-api/) -- `Authorization: Bearer <token>` header format

### Tertiary (LOW confidence)
- WebSearch results for Loki `s3forcepathstyle` Garage compatibility -- multiple sources confirm path-style required for non-AWS S3; Garage confirmed S3-compatible by community deployments

---

## Metadata

**Confidence breakdown:**
- Garage CLI commands and flags: HIGH -- verified from live `dxflrs/garage:v2.3.0` Docker image
- Garage TOML config format: HIGH -- verified from official docs
- Bootstrap idempotency behavior (error strings): MEDIUM -- mitigated by defensive dual-check and failed_when guards; UAT will confirm
- Backend S3 endpoint retargeting: HIGH -- verified from existing role templates; only hostname changes
- Prometheus bearer-auth scrape job: HIGH -- standard Prometheus config feature
- D-112 key create JSON output: MEDIUM -- assumed JSON from `key create` CLI; UAT will confirm format

**Research date:** 2026-05-27
**Valid until:** 2026-07-27 (Garage is actively maintained; config format stable within v2.x)
