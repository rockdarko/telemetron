---
status: complete
phase: 02-telemetry-backends
source: [02-VERIFICATION.md]
started: 2026-05-17T00:00:00Z
updated: 2026-05-18T18:40:00Z
runner: claude
target: leviathan (root@leviathan via inventory/leviathan)
---

## Current Test

[testing complete]

## Tests

### 1. End-to-end playbook run lights up all three backends

expected: All three containers (loki, tempo, mimir) reach healthy/running state within ~90s; `verify.yml` in-network curl probes succeed inside each role; a second playbook run reports `changed=0` in the PLAY RECAP.

command: `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags loki,tempo,mimir`

result: pass
evidence: |
  Clean run on leviathan after full teardown of /opt/telemetron/{loki,tempo,mimir}, named volumes, and containers:
  - Run 1: ok=32 changed=15 failed=0 skipped=2
  - Per-role verify.yml succeeded for all three: loki push+bucket-assert, tempo readiness+OTLP push, mimir readiness+bucket-trinity assertion
  - docker ps shows all three healthy: `loki Up (healthy)`, `tempo Up (healthy)`, `mimir Up (healthy)`
  Eight closed gaps documented below.

### 2. Loki write path lands chunks in MinIO

expected: HTTP 204 from Loki on the synthetic push; a fresh object key visible under `loki-chunks` bucket within ~10s.

result: pass
evidence: |
  Covered by roles/loki/tasks/verify.yml steps 2 and 3 in the Phase 2 run.
  Step 2 (Push synthetic log line to Loki) -- returned HTTP 204 after the TS-padding fix (gap loki-verify-push-ts-busybox-incompat below).
  Step 3 (Assert loki-chunks bucket received an object) -- succeeded.

### 3. Tempo OTLP/HTTP push reaches WAL

expected: Tempo returns HTTP 200 on the synthetic OTLP/HTTP POST; trace lands in the WAL within seconds.

result: pass
evidence: |
  Covered by roles/tempo/tasks/verify.yml in the Phase 2 run after the tempo-config-block-ranges-period-unknown fix.
  Tempo /ready returned 200; synthetic OTLP push to internal 14318 accepted.

### 4. Standard OTLP ports :4317 / :4318 are FREE on the host (BACK-05 intent)

expected: ss -tlnp shows only loki:3100, tempo:3200, mimir:9009 IF *_publish_host: true. Tempo's OTLP 14317/14318 stay Docker-internal.

result: pass
evidence: |
  ss -tlnp | grep -E ':(4317|4318|14317|14318|3100|3200|9009)\b' returned ZERO host bindings on leviathan.
  All Phase 2 *_publish_host defaults stayed false; standard OTLP pair (:4317/:4318) is wide open for Phase 3 OTel Collector to claim.

### 5. Idempotent second run reports changed=0

expected: PLAY RECAP `changed=0 failed=0` on a second consecutive run.

result: pass
evidence: |
  Run 1 (fresh): ok=32 changed=15 failed=0
  Run 2 (immediate re-run): ok=29 changed=0 failed=0

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- loki-tempo-mimir-config-mode-unreadable-by-container-uid:
    description: |
      `roles/{loki,tempo,mimir}/tasks/main.yml` rendered config files with
      mode 0600 owned by root:root. The Loki container runs as UID 10001:10001
      and could not open `/etc/loki/loki.yaml`. Same pattern on tempo and mimir.
      Failure mode: container crash-loop on startup with "permission denied".
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: |
      Updated all three config-render tasks to set `owner`/`group` from
      `<role>_container_user` (split on ':'), keeping mode 0600 to lock out
      non-owner readers. Embedded secrets stay protected; the container user
      can read.

- loki-container-uid-mismatch:
    description: |
      `loki_container_user: "1000:0"` in defaults. The grafana/loki:3.7.2
      image's WORKDIR /loki is initialized owned 10001:10001. With UID 1000
      the container could not `mkdir /loki/tsdb-cache`.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: Changed to `"10001:10001"`.

- tempo-container-uid-mismatch:
    description: |
      `tempo_container_user: "1000:0"`; comment claimed "Tempo image runs as
      1000:0 per upstream default" -- wrong. The grafana/tempo:2.10.5
      image's Config.User is `10001:10001`.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: Changed to `"10001:10001"` and fixed the comment.

- mimir-container-uid-wrong:
    description: |
      `mimir_container_user: "472:472"`. 472 is Grafana's UID convention,
      not Mimir's. The grafana/mimir:3.0.6 image's Config.User is 0 (root)
      and the image is distroless. With UID 472 Mimir crashed trying to
      write `./metrics-activity.log` to CWD=/ which is root-owned.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: Changed to `"0:0"` to match image default. Documented tradeoff.

- loki-verify-push-ts-busybox-incompat:
    description: |
      `roles/loki/tasks/verify.yml` synthetic-push used `TS=$(date +%s%N)`
      inside a curlimages/curl one-shot. The curlimages base is Alpine with
      busybox `date` -- which silently drops `%N`. Result: TS was 10-digit
      epoch-seconds; Loki interpreted as nanoseconds (year 1970); rejected
      with 400 "timestamp too old".
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: |
      Changed to `TS=$(date +%s)000000000` -- epoch seconds + nine zeros =
      valid nanoseconds. Matches the pattern already in
      roles/opentelemetry/tasks/verify.yml.

- tempo-config-block-ranges-period-unknown:
    description: |
      `tempo.yaml.j2` rendered `compactor.compaction.block_ranges_period`.
      Field does not exist in tempodb.CompactorConfig in Tempo 2.10.5.
      Tempo crashed at config parse.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: Removed the line; left a comment marker explaining why.

- mimir-config-ooo-time-window-removed:
    description: |
      `mimir.yaml.j2` rendered `blocks_storage.tsdb.out_of_order_time_window`.
      In Mimir 3.0 this moved out of tsdb.TSDBConfig (probably to per-tenant
      `limits:`). Mimir crashed at config parse.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: Removed the line. Per-tenant OOO tuning is a follow-up.

- mimir-config-blocks-retention-period-removed:
    description: |
      `mimir.yaml.j2` rendered `compactor.blocks_retention_period`. Field
      does not exist on compactor.Config in Mimir 3.0. Mimir crashed.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: blocker
    resolution: |
      Removed the line. Default retention is 1 week (fine for M1).
      Per-tenant retention via `limits:` is a follow-up.

- loki-mimir-mc-image-tag-hallucinated:
    description: |
      `loki_mc_image_tag` and `mimir_mc_image_tag` were pinned to the same
      hallucinated `RELEASE.2025-04-22T16-23-26Z` that bit Phase 1.
    status: resolved
    resolved_by: inline fix during Phase 2 UAT 2026-05-18
    severity: major
    resolution: |
      sed-rewrote both files to `RELEASE.2025-04-16T18-13-26Z` (the closest
      published mc release).
