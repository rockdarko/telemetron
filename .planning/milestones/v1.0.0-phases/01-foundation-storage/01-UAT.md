---
status: complete
phase: 01-foundation-storage
source: [01-VERIFICATION.md]
started: 2026-05-17T16:00:00Z
updated: 2026-05-18T18:10:00Z
runner: claude
target: leviathan (root@leviathan via inventory/leviathan)
---

## Current Test

[testing complete]

## Tests

### 1. Live deploy: MinIO up with network and buckets
expected: PLAY RECAP failed=0; docker network ls shows telemetron bridge with MinIO attached; docker inspect minio --format '{{.State.Health.Status}}' returns healthy; docker inspect minio --format '{{.HostConfig.RestartPolicy.Name}}' returns unless-stopped; mc ls confirms all 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts).
result: pass
evidence: |
  Clean run on leviathan after full teardown (docker rm -f minio; docker volume rm telemetron_minio_data; rm -rf /opt/telemetron):
  - PLAY RECAP: ok=12 changed=5 failed=0 unreachable=0
  - docker inspect minio --format "{{.State.Health.Status}}" -> "healthy"
  - docker inspect minio --format "{{.HostConfig.RestartPolicy.Name}}" -> "unless-stopped"
  - docker network inspect telemetron showed minio attached
  - mc ls local/ from in-network mc container showed all 5 buckets present (loki-chunks, mimir-alerts, mimir-blocks, mimir-ruler, tempo-traces)
  Pass achieved after closing 3 gaps inline (see Gaps section below).

### 2. Idempotency gate
expected: Run the playbook a second time immediately after a successful first run (same vault, same inventory). PLAY RECAP shows changed=0, failed=0.
result: pass
evidence: |
  Run 1 (fresh): ok=12 changed=5 failed=0
  Run 2 (immediate re-run): ok=11 changed=0 failed=0
  (Second run was -1 ok because the handler ran during Run 1 but had no trigger on Run 2 -- expected.)

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- minio-healthcheck-cmdshell:
    description: |
      `roles/minio/tasks/main.yml` was rendering the Docker HEALTHCHECK as
      `test: "{{ minio_healthcheck_test.split(' ') }}"` where the default in
      `defaults/main.yml` was a single string `"CMD-SHELL curl -sf ... || exit 1"`.
      `.split(' ')` produced `["CMD-SHELL", "curl", "-sf", "<url>", "||", "exit", "1"]`,
      but Docker's CMD-SHELL form expects EXACTLY `["CMD-SHELL", "<one shell string>"]`
      -- everything after the first arg is discarded and the shell runs an empty command.
      Result: `curl` invoked with no args, healthcheck stayed `starting` forever,
      bootstrap pre-poll timed out at 30 retries.
    status: resolved
    resolved_by: inline fix during Phase 1 UAT 2026-05-18
    severity: blocker
    resolution: |
      Changed `minio_healthcheck_test` in defaults/main.yml from a string to a
      list: `[CMD-SHELL, "curl -sf <url> || exit 1"]`. Changed tasks/main.yml
      to consume directly: `test: "{{ minio_healthcheck_test }}"` (no split).
      Added doc comment in defaults explaining the CMD-SHELL contract.

- minio-mc-image-tag-nonexistent:
    description: |
      `minio_mc_image_tag: "RELEASE.2025-04-22T16-23-26Z"` was pinned to a tag
      that was never published to Docker Hub. mc and MinIO server are tagged
      independently; mc was not co-tagged on 2025-04-22. Result: Docker pull
      returned 404 / manifest unknown; bootstrap mc container never started.
    status: resolved
    resolved_by: inline fix during Phase 1 UAT 2026-05-18
    severity: blocker
    resolution: |
      Repinned to `RELEASE.2025-04-16T18-13-26Z` -- the closest published mc
      release. Verified via Docker Hub API.

- minio-failed-when-masks-pull-failure:
    description: |
      `roles/minio/tasks/bootstrap.yml` declared
      `failed_when: minio_bootstrap_result.status is defined and ... != 0`
      on both the bootstrap and verify tasks. When the mc image pull failed
      (pre-fix), the container never ran; community.docker.docker_container
      returned with no `.status` field; failed_when evaluated to false; task
      reported "ok" -- silent failure. Bug minio-mc-image-tag-nonexistent
      went undetected by Ansible alone because of this.
    status: resolved
    resolved_by: inline fix during Phase 1 UAT 2026-05-18
    severity: major
    resolution: |
      Tightened both failed_when clauses to fail when `is failed` OR `status
      is not defined` OR `status != 0`. Now an image-pull failure raises
      `failed=1` instead of being swallowed.

- minio-verify-uses-utils-absent-from-mc-image:
    description: |
      `roles/minio/tasks/bootstrap.yml` Verify task used
      `mc ls --json | sed | sort | diff` pipeline with an embedded `printf`
      to compare expected vs actual bucket lists. Comment claimed
      "busybox-compat -- works inside the minio/mc alpine-based image."
      The current minio/mc image ships ubi9-micro+coreutils (NOT
      alpine+busybox); `sed`, `diff`, and `grep` are absent. Pipeline
      exited 127 (command not found). Buckets WERE present on disk -- only
      the verification was broken.
    status: resolved
    resolved_by: inline fix during Phase 1 UAT 2026-05-18
    severity: major
    resolution: |
      Replaced the sed/diff pipeline with a per-bucket `mc ls local/<b>/
      >/dev/null` loop under `set -e`. Uses only mc + sh builtins; works
      regardless of base-image churn. `mc ls` (not `mc stat`) is correct
      for bucket-prefix existence -- `mc stat` is object-only.
