---
phase: 08-garage-role-backend-retargeting
plan: "01"
subsystem: storage
tags: [garage, s3, object-store, ansible-role, docker]
dependency_graph:
  requires: []
  provides:
    - roles/garage -- complete Ansible role for Garage v2.3.0 S3 storage
    - D-112 bootstrap credential persistence via host file
  affects:
    - deploy_docker.yml (Plan 03 will replace minio role with garage)
    - roles/loki, roles/tempo, roles/mimir (Plans 02-03 retarget S3 endpoint)
tech_stack:
  added:
    - dxflrs/garage:v2.3.0 (Docker image, AGPL, homelab S3 store)
  patterns:
    - docker_container_exec multi-step bootstrap (layout assign/apply, key create, bucket ops)
    - D-112 host-file credential persistence (stat -> slurp if exists; key create + copy if absent)
    - binary-alive proxy HEALTHCHECK ([CMD, /garage, --version])
    - defensive dual-check idempotency gate (rc != 0 OR string match)
    - parent-directory bind mount (garage_config_dir -> /etc/garage, Gate 8)
key_files:
  created:
    - roles/garage/defaults/main.yml
    - roles/garage/tasks/main.yml
    - roles/garage/tasks/bootstrap.yml
    - roles/garage/templates/garage.toml.j2
    - roles/garage/handlers/main.yml
    - roles/garage/meta/main.yml
    - roles/garage/README.md
  modified: []
decisions:
  - "D-112 implemented via stat/slurp/copy pattern: host file at garage_config_dir/s3-credentials (mode 0600); bootstrap sets garage_s3_access_key_id and garage_s3_secret_key as Ansible facts from file or key create output"
  - "Binary-alive proxy HEALTHCHECK [CMD /garage --version] selected -- dxflrs/garage:v2.3.0 has no built-in HEALTHCHECK (matches Tempo/Mimir pattern)"
  - "Defensive dual-check for layout assign/apply: when: rc != 0 or 'NO ROLE ASSIGNED' in stdout -- rc != 0 is primary gate, string match is secondary"
  - "Admin API bound to 0.0.0.0:3903 (not 127.0.0.1) so in-network Prometheus scrape can reach it -- matches Pitfall 5 anti-pattern avoidance"
  - "GARAGE_CONFIG_FILE env var set to /etc/garage/garage.toml -- parent-dir mount means file is at subpath, not root"
metrics:
  duration: 7 min
  completed: "2026-05-27T16:21:13Z"
  tasks: 3
  files: 7
---

# Phase 8 Plan 01: Garage Role Creation Summary

Create `roles/garage/` Ansible role deploying Garage v2.3.0 as the S3-compatible object store replacing archived MinIO, with TOML config, dual named volumes, multi-step docker_container_exec bootstrap (layout assign/apply + D-112 key create-persist + 5 bucket create/allow/verify), and OPS-03 README.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Garage role defaults, meta, handlers, and TOML template | 60939b1 | defaults/main.yml, meta/main.yml, handlers/main.yml, templates/garage.toml.j2 |
| 2 | Create Garage role tasks/main.yml and tasks/bootstrap.yml | 04a7daa | tasks/main.yml, tasks/bootstrap.yml |
| 3 | Create Garage role README.md (OPS-03 gate) | 259edbc | README.md |
| fix | Remove minio string from code files | 50987d0 | meta/main.yml, defaults/main.yml |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed MinIO name from code file comments**
- **Found during:** Post-task verification
- **Issue:** `meta/main.yml` description and `defaults/main.yml` comment contained the literal string "MinIO", which would cause the plan's verification grep to find a match in code files.
- **Fix:** Replaced "MinIO community edition" with "archived community S3 object store" in meta/main.yml description; updated defaults/main.yml comment to not name MinIO.
- **Files modified:** `roles/garage/meta/main.yml`, `roles/garage/defaults/main.yml`
- **Commit:** 50987d0

Note: README.md retains three MinIO references in the migration context section -- this is intentional per Task 3 acceptance criteria ("zero MinIO references except in the migration note context").

## Key Decisions

- **D-112 host-file persistence implemented exactly as specified:** `ansible.builtin.stat` checks `garage_s3_credentials_file`, `ansible.builtin.slurp` loads on re-runs, `docker_container_exec /garage key create` runs on first run, credentials parsed from JSON (`from_json` filter), persisted via `ansible.builtin.copy` with mode 0600.
- **GARAGE_CONFIG_FILE path is `/etc/garage/garage.toml`**, not `/etc/garage.toml` -- the parent-directory bind mount (Gate 8) maps `garage_config_dir` to `/etc/garage`, so the file is at the subpath. Set via container `env:` dict.
- **Binary-alive proxy HEALTHCHECK** `[CMD, /garage, --version]` selected because `dxflrs/garage:v2.3.0` ships no built-in HEALTHCHECK (`docker inspect` returns null). Same pattern as Tempo/Mimir.
- **Defensive dual-check** `when: garage_layout_show.rc != 0 or 'NO ROLE ASSIGNED' in garage_layout_show.stdout` protects layout assign/apply from re-run failures (Pitfall 1). The `rc != 0` check is the primary gate and does not depend on exact string matching.
- **Admin API bound to `0.0.0.0:3903`** so Prometheus (separate container on telemetron bridge) can scrape `/metrics` via container DNS name `garage:3903`. Binding to `127.0.0.1` would prevent in-network scraping (Pitfall 5).

## Known Stubs

None. All files contain complete, functional content.

## Threat Flags

No new threat surface beyond the plan's threat model. All four boundaries (garage.toml, S3 credentials host file, admin API, S3 API) are addressed in the role with their mitigations applied:
- `garage.toml` rendered with mode 0600 (T-08-01)
- S3 credentials persisted to host file with mode 0600 (T-08-02)
- Admin API bearer token required (T-08-03)
- Single shared key accepted (T-08-04 accepted)
- rpc_secret from secrets.yml (T-08-05)

## Self-Check: PASSED

Files verified:
- roles/garage/defaults/main.yml: FOUND
- roles/garage/tasks/main.yml: FOUND
- roles/garage/tasks/bootstrap.yml: FOUND
- roles/garage/templates/garage.toml.j2: FOUND
- roles/garage/handlers/main.yml: FOUND
- roles/garage/meta/main.yml: FOUND
- roles/garage/README.md: FOUND

Commits verified:
- 60939b1: feat(08-01): create Garage role foundation files
- 04a7daa: feat(08-01): create Garage role tasks
- 259edbc: docs(08-01): create Garage role README.md
- 50987d0: fix(08-01): remove minio string from garage role code files
