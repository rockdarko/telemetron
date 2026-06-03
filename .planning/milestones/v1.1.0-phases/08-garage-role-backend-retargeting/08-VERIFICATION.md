---
phase: 08-garage-role-backend-retargeting
verified: 2026-05-27T17:25:34Z
status: human_needed
score: 10/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run smoke_test.yml on leviathan after deploying Phase 8"
    expected: "playbooks/smoke_test.yml completes with failed=0; synthetic OTLP log, metric, and trace data round-trips through Loki, Mimir, and Tempo respectively; all three backends read/write from Garage S3 buckets"
    why_human: "Runtime data-plane write-through to Garage cannot be verified statically. Requires a live Garage container + working bootstrap + Loki/Tempo/Mimir all connected on the telemetron bridge. The static config wiring is verified; the actual writes are not."
  - test: "Verify Garage container health and bucket list on leviathan post-deploy"
    expected: "docker inspect telemetron-garage --format='{{.State.Health.Status}}' returns 'healthy'; docker exec telemetron-garage /garage layout show shows a node assigned with replication_factor 1; docker exec telemetron-garage /garage bucket list shows all 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts)"
    why_human: "Requires a live running container. Bootstrap correctness (layout assign/apply, bucket creation, key persistence) can only be confirmed against an actual Garage instance on leviathan."
  - test: "Verify Garage self-metrics are scraped and visible in Grafana"
    expected: "curl -s -H 'Authorization: Bearer <garage_admin_token>' http://leviathan:3903/metrics returns Prometheus-format text with at least one 'garage_' metric; the Prometheus targets page shows the garage job as UP"
    why_human: "Requires live containers (Prometheus + Garage both running). The scrape config is wired correctly in the template but the actual scrape health is a runtime check."
---

# Phase 8: Garage Role + Backend Retargeting — Verification Report

**Phase Goal:** Operator can run the playbook on leviathan and have Garage v2.3.0 running in place of MinIO as the S3-compatible object store: the garage container is healthy on the telemetron bridge with S3 API on :3900 and admin on :3903, single-node layout is assigned and applied, all five buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts) are bootstrapped with a read/write/owner key, Loki and Tempo and Mimir all write through Garage's S3 API successfully, the minio role and all MinIO-specific vars are gone from the codebase, and Garage's self-metrics at :3903/metrics are scraped by Prometheus or OTel Collector so storage usage appears in Grafana.
**Verified:** 2026-05-27T17:25:34Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Garage v2.3.0 container role exists with image pin dxflrs/garage:v2.3.0 | VERIFIED | `roles/garage/defaults/main.yml`: `garage_image: dxflrs/garage`, `garage_image_tag: "v2.3.0"` |
| 2 | S3 API on :3900 and admin on :3903 configured in TOML template | VERIFIED | `garage.toml.j2`: `api_bind_addr = "[::]:{{ garage_api_port }}"` (port 3900), `api_bind_addr = "0.0.0.0:{{ garage_admin_port }}"` (port 3903) |
| 3 | Single-node layout bootstrap is implemented (layout assign + apply) | VERIFIED | `bootstrap.yml` steps 4-6: defensive dual-check gate (`rc != 0 or 'NO ROLE ASSIGNED'`), layout assign with zone/capacity, layout apply with `--version 1` |
| 4 | All 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts) bootstrapped with read/write/owner key | VERIFIED | `bootstrap.yml` steps 7-10: D-112 key create-persist, `bucket create` loop over `garage_buckets`, `bucket allow --read --write --owner` loop, `bucket info` verify loop; `storage.yml` has all 5 buckets in `telemetron_garage_buckets` |
| 5 | Loki S3 endpoint retargeted to http://garage:3900 with object_store: aws | VERIFIED | `roles/loki/defaults/main.yml`: `loki_s3_endpoint: "http://garage:3900"`; `loki.yaml.j2` line 40: `object_store: aws` |
| 6 | Tempo S3 endpoint retargeted to garage:3900 (no scheme) | VERIFIED | `roles/tempo/defaults/main.yml`: `tempo_s3_endpoint: "garage:3900"` |
| 7 | Mimir S3 endpoint retargeted to garage:3900 (no scheme) | VERIFIED | `roles/mimir/defaults/main.yml`: `mimir_s3_endpoint: "garage:3900"` |
| 8 | Loki/Tempo/Mimir actually write through Garage's S3 API successfully | UNCERTAIN | Config wiring is verified. Actual round-trip write behavior requires live containers on leviathan. See Human Verification. |
| 9 | minio role and all MinIO-specific vars gone from codebase | VERIFIED | `roles/minio/` does not exist; `grep -r 'minio' roles/ playbooks/ inventory/example-homelab/` returns zero operational matches (only migration-context prose in `roles/garage/README.md` and `docs/architecture.md` — acceptable) |
| 10 | Garage self-metrics at :3903/metrics scraped by Prometheus | VERIFIED | `prometheus.yml.j2`: `job_name: garage` with `targets: ['{{ prometheus_garage_target }}']` (default `garage:3903`) and `authorization.credentials: "{{ garage_admin_token }}"` bearer auth |
| 11 | Garage container healthy post-deploy (runtime) | UNCERTAIN | HEALTHCHECK configured (`/garage --version` binary-alive proxy); health status requires live container on leviathan. See Human Verification. |
| 12 | All backend verify.yml tasks use docker_container_exec against Garage (not mc one-shot) | VERIFIED | `loki/tasks/verify.yml` step 3: `docker_container_exec /garage bucket info loki-chunks`; `mimir/tasks/verify.yml` step 2: loop over 3 mimir buckets; `tempo/tasks/verify.yml` step 3 (new D-118): `docker_container_exec /garage bucket info tempo-traces` |

**Score:** 10/12 truths verified (2 require human/live verification — these are runtime behavioral checks)

### Deferred Items

None identified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `roles/garage/defaults/main.yml` | Full Garage default surface | VERIFIED | Contains image pin, port vars, volume vars, bucket list, D-112 credential file path, no mc_image vars |
| `roles/garage/tasks/main.yml` | Config dir, render TOML, volumes, pull, container, bootstrap include | VERIFIED | 7 tasks in correct order; GARAGE_CONFIG_FILE=/etc/garage/garage.toml; bind mount at /etc/garage; Gate 7 labels; Gate 8 parent-dir mount |
| `roles/garage/tasks/bootstrap.yml` | HEALTHCHECK poll + multi-step exec bootstrap with D-112 key persistence | VERIFIED | 10 steps: health poll, node ID, layout show, layout assign/apply (gated), stat/slurp/key-create/persist (D-112), bucket create/allow/verify |
| `roles/garage/templates/garage.toml.j2` | TOML config with rpc_secret, admin, s3_api sections | VERIFIED | `replication_factor = 1`; `[s3_api]` on `[::]:3900`; `[admin]` on `0.0.0.0:3903`; `admin_token` and `metrics_token` templated |
| `roles/garage/handlers/main.yml` | restart garage handler | VERIFIED | `listen: restart garage` via `docker restart {{ garage_container_name }}` |
| `roles/garage/meta/main.yml` | Role metadata | VERIFIED | `role_name: garage`; collections: community.docker, ansible.builtin |
| `roles/garage/README.md` | OPS-03 gate README | VERIFIED | All required sections: Variables, Secrets, Tags, Modes, Volumes, Healthcheck, Security model, Idempotency, Port-acceptance gates |
| `roles/loki/defaults/main.yml` | Retargeted S3 endpoint to Garage | VERIFIED | `loki_s3_endpoint: "http://garage:3900"`; mc_image vars removed |
| `roles/tempo/defaults/main.yml` | Retargeted S3 endpoint to Garage | VERIFIED | `tempo_s3_endpoint: "garage:3900"` |
| `roles/mimir/defaults/main.yml` | Retargeted S3 endpoint to Garage | VERIFIED | `mimir_s3_endpoint: "garage:3900"`; mc_image vars removed |
| `roles/loki/tasks/verify.yml` | Garage-based bucket verification | VERIFIED | `docker_container_exec /garage bucket info {{ loki_s3_bucket }}`; mc one-shot removed |
| `roles/tempo/tasks/verify.yml` | New Garage bucket verify step (D-118) | VERIFIED | New step 3: `docker_container_exec /garage bucket info {{ tempo_s3_bucket }}` |
| `roles/mimir/tasks/verify.yml` | Garage-based bucket verification | VERIFIED | `docker_container_exec` loop over 3 mimir buckets; mc one-shot removed |
| `roles/prometheus/templates/prometheus.yml.j2` | 4th scrape job for Garage metrics | VERIFIED | `job_name: garage`; `targets: ['{{ prometheus_garage_target }}']`; `authorization.credentials: "{{ garage_admin_token }}"` |
| `roles/prometheus/defaults/main.yml` | prometheus_garage_target default | VERIFIED | `prometheus_garage_target: "garage:3903"` |
| `inventory/example-homelab/group_vars/all/secrets.yml.example` | Garage credential placeholders replacing MinIO | VERIFIED | `garage_admin_token: CHANGE_ME`, `garage_rpc_secret: CHANGE_ME`; no `minio_root_*`; no standalone `garage_s3_access_key_id` |
| `inventory/example-homelab/group_vars/all/garage.yml` | Garage operator knobs (D-120) | VERIFIED | `garage_publish_host: false`, `garage_container_name: telemetron-garage` |
| `inventory/example-homelab/group_vars/all/storage.yml` | telemetron_garage_buckets | VERIFIED | All 5 buckets listed; `telemetron_minio_buckets` absent |
| `playbooks/deploy_docker.yml` | role: garage in storage slot | VERIFIED | Line 36: `- role: garage`; `role: minio` absent; ansible syntax check passes (exit 0) |
| `roles/minio/` | Does not exist | VERIFIED | Directory is absent from filesystem |
| `inventory/example-homelab/group_vars/all/minio.yml` | Does not exist | VERIFIED | File is absent from filesystem |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `roles/garage/tasks/main.yml` | `roles/garage/tasks/bootstrap.yml` | `include_tasks: bootstrap.yml` | WIRED | Line 119: `ansible.builtin.include_tasks: bootstrap.yml` as final task |
| `roles/garage/tasks/main.yml` | `roles/garage/templates/garage.toml.j2` | `ansible.builtin.template` | WIRED | `src: garage.toml.j2`, `dest: {{ garage_config_dir }}/garage.toml` |
| `roles/garage/tasks/main.yml` | `roles/garage/handlers/main.yml` | `notify: restart garage` | WIRED | Template task notifies `restart garage`; handler listens on that name |
| `playbooks/deploy_docker.yml` | `roles/garage/tasks/main.yml` | `role: garage` | WIRED | `- role: garage` replaces `- role: minio` |
| `inventory/example-homelab/group_vars/all/storage.yml` | `roles/garage/defaults/main.yml` | `telemetron_garage_buckets` | WIRED | `garage_buckets` default references `telemetron_garage_buckets` |
| `roles/loki/tasks/verify.yml` | `roles/garage/defaults/main.yml` | `garage_container_name` cross-role var | WIRED | `container: "{{ garage_container_name }}"` in verify.yml |
| `roles/prometheus/templates/prometheus.yml.j2` | `roles/garage/defaults/main.yml` | `garage_admin_token` cross-role var | WIRED | `credentials: "{{ garage_admin_token }}"` in prometheus.yml.j2 |
| `secrets.yml.example` D-113 aliases | `roles/garage/tasks/bootstrap.yml` facts | `{{ garage_s3_access_key_id }}` Jinja2 ref | WIRED | `loki_s3_access_key: "{{ garage_s3_access_key_id }}"` (and tempo/mimir equivalents); `garage_s3_access_key_id` is set_fact'd by bootstrap |

### Data-Flow Trace (Level 4)

This phase produces configuration artifacts (Ansible roles, templates), not dynamic UI components. Data-flow tracing is not applicable for Ansible roles — the "data" is the Ansible fact chain from bootstrap to secrets persistence, which is verified at the task level in the artifact checks above.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Ansible syntax check passes | `ansible-playbook --syntax-check playbooks/deploy_docker.yml` | Exit 0 (3 warnings — no inventory, expected) | PASS |
| roles/minio/ does not exist | `ls roles/minio/ 2>/dev/null` | No output (directory absent) | PASS |
| roles/garage/ has all 7 required files | `ls roles/garage/` | defaults, handlers, meta, README.md, tasks, templates all present | PASS |
| No operational minio refs in roles/ | `grep -r 'minio' roles/ playbooks/ inventory/example-homelab/` | Only 3 lines in roles/garage/README.md (migration-context prose) | PASS |
| No mc_image or minio/mc refs | `grep -r 'mc_image\|minio/mc\|MC_HOST_local' roles/` | No output | PASS |
| Prometheus garage job wired with bearer auth | `grep -n 'job_name: garage' + 'authorization' prometheus.yml.j2` | `job_name: garage` at line 83; `authorization.credentials` at line 93 | PASS |

### Probe Execution

No `probe-*.sh` scripts declared or present for this phase. Step 7b: SKIPPED (no probe files; Ansible role phase with no runnable probe harness).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STORE-01 | 08-01-PLAN.md | Garage v2.3.0 on telemetron bridge, S3 :3900, admin :3903, layout assigned, 5 buckets bootstrapped | SATISFIED | `roles/garage/` complete with bootstrap; all 5 buckets in `telemetron_garage_buckets`; ports 3900/3903 confirmed in TOML template |
| STORE-02 | 08-02-PLAN.md | Loki/Tempo/Mimir S3 configs retargeted; object_store: aws for Loki; creds renamed | SATISFIED (static) | All 3 S3 endpoints point to garage:3900; `loki.yaml.j2` has `object_store: aws`; mc_image vars removed; D-113 aliases in secrets.yml.example |
| STORE-03 | 08-03-PLAN.md | roles/minio/ deleted; mc image refs gone; playbook shows garage | SATISFIED | `roles/minio/` absent; `roles/garage/` present; `role: garage` in deploy_docker.yml; zero operational minio refs in roles/playbooks/inventory |
| OPS-01 | 08-02-PLAN.md | Garage self-metrics scraped at :3903/metrics with bearer auth | SATISFIED (static) | `prometheus.yml.j2` job_name: garage with authorization.credentials = garage_admin_token; prometheus_garage_target: "garage:3903" |

All 4 requirements claimed by the 3 plans are traceable to concrete implementation evidence. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `roles/garage/README.md` | 97, 151, 208 | "Placeholder" — word appears in documentation prose | Info | These are explanatory prose ("placeholders ship in...") not code debt markers. No `TBD`, `FIXME`, or `XXX` markers found anywhere in the phase artifacts. |

No blockers. No `TBD`, `FIXME`, or `XXX` markers found in any file modified by this phase.

The CHANGE_ME values in `secrets.yml.example` are intentional operator-supplied credential slots for a template file; they are not stubs.

### Human Verification Required

#### 1. Backend write-through to Garage S3 (smoke test)

**Test:** On leviathan, after deploying Phase 8 (`ansible-playbook -i inventory/leviathan/ playbooks/deploy_docker.yml`), run `ansible-playbook -i inventory/leviathan/ playbooks/smoke_test.yml`
**Expected:** `failed=0`; synthetic OTLP log, metric, and trace data appear in Grafana; Loki, Tempo, and Mimir are all reading/writing from Garage S3 buckets (not local filesystem)
**Why human:** Runtime data-plane behavior cannot be verified statically. The config wiring is correct (endpoints, credentials, bootstrap sequence), but whether objects actually land in Garage requires a live multi-container environment on leviathan.

#### 2. Garage container health and bootstrap validation

**Test:** After deploying on leviathan, run:
- `docker inspect telemetron-garage --format='{{.State.Health.Status}}'` (expect: `healthy`)
- `docker exec telemetron-garage /garage layout show` (expect: node assigned, replication_factor: 1)
- `docker exec telemetron-garage /garage bucket list` (expect: all 5 buckets present)
- `cat /opt/telemetron/garage/s3-credentials` (expect: file exists with `key_id=` and `secret=` lines)
**Expected:** All commands succeed; container is healthy; layout is applied; 5 buckets exist; credentials file persisted
**Why human:** Bootstrap correctness (D-112 key persistence, idempotency gate behavior) requires live Garage instance. Static task review confirms the logic is correct; behavioral confirmation needs leviathan.

#### 3. Prometheus Garage metrics scrape health

**Test:** After deploying on leviathan, check Prometheus targets page (http://leviathan:9090/targets) and confirm the `garage` job shows as `UP`. Run: `curl -s -H "Authorization: Bearer $(grep garage_admin_token /opt/telemetron/prometheus/prometheus.yml | awk '{print $2}')" http://leviathan:3903/metrics | grep '^garage_'`
**Expected:** At least one `garage_` prefixed metric returned; Prometheus targets page shows garage job UP
**Why human:** Requires live containers for both Prometheus and Garage. The scrape config template is wired correctly; the actual scrape health requires runtime confirmation.

### Gaps Summary

No automated-verifiable gaps found. All STORE-01, STORE-02, STORE-03, OPS-01 requirements have concrete implementation evidence in the codebase. The remaining open items are all runtime behavioral verifications requiring leviathan deployment.

The phase's static deliverables (role creation, S3 retargeting, MinIO removal, metrics scrape wiring) are complete and correct. The dynamic deliverables (actual writes, container health, Prometheus scrape UP) require human UAT on leviathan.

---

_Verified: 2026-05-27T17:25:34Z_
_Verifier: Claude (gsd-verifier)_
