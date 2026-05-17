---
phase: 02-telemetry-backends
plan: 03
subsystem: infra
tags: [ansible, docker, mimir, grafana, observability, minio, s3, monolithic, metrics, multi-bucket]

# Dependency graph
requires:
  - phase: 01-foundation-storage
    provides: telemetron Docker bridge network, MinIO with three mimir-* buckets bootstrapped (mimir-blocks, mimir-ruler, mimir-alerts), vault_minio_root_user/password keys, canonical roles/minio/ template (D-10a HEALTHCHECK poll, W6 single-handler restart, W7 changed_when:false on verify, W8 in-network verify, OPS-03 README schema)
  - phase: 02-telemetry-backends
    plan: 01
    provides: D-27 per-backend vault key alias surface, Phase-2 canonical role shape (roles/loki/), playbooks/deploy_docker.yml wired through loki
  - phase: 02-telemetry-backends
    plan: 02
    provides: Conditional Docker HEALTHCHECK pattern (`<role>_healthcheck_enabled` + `omit` magic value) for distroless images that may or may not ship a native -health binary -- reused verbatim for Mimir; OTLP alt-port-in-config pattern (D-29) reserves the standard :4317/:4318 for Phase 3 OTel; bucket-landing assertion deferral pattern (Phase 6 OPS-07 smoke when block-flush exceeds verify-task wall-clock budget)
provides:
  - roles/mimir/ Ansible role (Mimir 3.0.6 monolithic, S3-backed against THREE distinct buckets mimir-blocks/ruler/alerts, multitenancy off, D-36 Pitfall-11 monolithic tuning + Pitfall-3 limits)
  - D-27 alias surface extended (vault_mimir_s3_access_key / vault_mimir_s3_secret_key aliased to MinIO root creds)
  - inventory/example-homelab/group_vars/all/mimir.yml (D-30 no-host-publish, BACK-04 retention knob)
  - playbooks/deploy_docker.yml wired through mimir after tempo (D-23) -- minio -> loki -> tempo -> mimir (Phase 2 FEATURE-COMPLETE)
  - D-36 Pitfall-11 monolithic-tuning pattern demonstrated (five knobs all inline-cited with PITFALLS reference): query_store_after + bucket_store.sync_interval + compactor.cleanup_interval + the two cardinality limits
  - D-39 multi-bucket-S3-trinity pattern (blocks_storage + ruler_storage + alertmanager_storage each pointing at a DISTINCT bucket; Mimir refuses to start sharing prefixes per Pitfall G) -- reusable for any future multi-store S3-backed component
  - Bucket-trinity in-network verify pattern (W8 + D-32): one-shot mc container asserts ALL three buckets reachable via the D-27-aliased vault creds with set -e short-circuit -- proves the alias plumbing works AND validates Mimir's startup precondition (distinct buckets) before the container starts taking remote_write
affects: [03-prometheus, 03-fluentbit, 03-opentelemetry, 05-grafana]

# Tech tracking
tech-stack:
  added:
    - grafana/mimir:3.0.6 (long-term metrics backend, monolithic mode -target=all)
  patterns:
    - Conditional Docker HEALTHCHECK via `mimir_healthcheck_enabled` toggle + Ansible `omit` magic value -- reuses the Plan 02-02 Tempo pattern verbatim for the second distroless backend. Same three outcomes (A native -health / B -version proxy / C disabled); image probe confirmed Outcome B for grafana/mimir:3.0.6
    - Three-distinct-bucket S3 storage with separate `<store>_storage.s3.bucket_name` keys for blocks_storage / ruler_storage / alertmanager_storage (BACK-04 / Pitfall G mitigation)
    - Bucket-trinity in-network assertion pattern (W8 with set -e short-circuit) -- mc ls --json against each bucket via the D-27 alias creds; first failing bucket points the operator at the bad bucket without ambiguity. Replaces Tempo's synthetic OTLP push (Mimir's remote_write protocol is snappy-protobuf, curl-unfriendly per RESEARCH Finding 8; the durability smoke moves to Phase 3 / Phase 6 OPS-07)
    - Five-knob monolithic tuning all inline-cited (D-36 + Pitfall 11 + Pitfall 3): max_global_series_per_user (cardinality limit), max_global_series_per_metric (cardinality limit), query_store_after (consistency window), bucket_store.sync_interval (ingester/compactor consistency), compactor.cleanup_interval (consistent with sync_interval)
    - INTENTIONAL omission of synthetic remote_write push -- documented inline; RESEARCH Finding 8 says Prometheus remote_write is curl-unfriendly (snappy-compressed protobuf); end-to-end push smoke is Phase 3 (Prometheus comes online) and Phase 6 OPS-07

key-files:
  created:
    - roles/mimir/defaults/main.yml
    - roles/mimir/meta/main.yml
    - roles/mimir/handlers/main.yml
    - roles/mimir/tasks/main.yml
    - roles/mimir/tasks/verify.yml
    - roles/mimir/templates/mimir.yaml.j2
    - roles/mimir/README.md
    - inventory/example-homelab/group_vars/all/mimir.yml
  modified:
    - inventory/example-homelab/group_vars/all/vault.yml.example
    - playbooks/deploy_docker.yml
    - roles/README.md

key-decisions:
  - "Mimir image pinned to grafana/mimir:3.0.6 with -target=all monolithic CLI; v3.0 line is current stable per CLAUDE.md tech-stack constraints"
  - "gRPC port explicitly pinned to 9097 (D-28) -- completes the no-clash port trinity: Loki 9095 / Tempo 9096 / Mimir 9097 on a single homelab host"
  - "D-26 multitenancy_enabled:false -- single-tenant `anonymous`; Phase 3 producers (Prometheus remote_write, OTel) need no tenant config. Flipping to true in a future hardening phase requires every producer to send X-Scope-OrgID; documented in the role README"
  - "D-39 / BACK-04 / Pitfall G THREE distinct buckets in the rendered config -- blocks_storage.s3.bucket_name=mimir-blocks, ruler_storage.s3.bucket_name=mimir-ruler, alertmanager_storage.s3.bucket_name=mimir-alerts. Mimir refuses to start when these share a bucket+prefix"
  - "D-35 / BACK-04 retention default `mimir_compactor_blocks_retention_period: 30d` (matches telemetron_default_metric_retention from storage.yml); operator-overridable in inventory/example-homelab/group_vars/all/mimir.yml"
  - "D-36 / Pitfall 11 + Pitfall 3 FIVE-knob monolithic tuning -- max_global_series_per_user:500000, max_global_series_per_metric:100000 (Pitfall 3 homelab limits, vs upstream 5M scale), query_store_after:12h, bucket_store.sync_interval:5m, compactor.cleanup_interval:5m (Pitfall 11 monolithic single-host consistency). All five inline-cited in the rendered template; the upstream had ZERO of these guards (the most consequential D-25 improvement pass for Mimir)"
  - "D-39 S3 endpoint format `endpoint: minio:9000` (NO http:// prefix) under common.storage.s3 -- matches Tempo's format, differs from Loki's. `insecure: true` signals plain HTTP; Mimir auto-detects path-style for non-AWS endpoints (no explicit force_path_style key needed for MinIO at 3.0.6, validated via rendered config)"
  - "Healthcheck probe outcome: Mimir 3.0.6 ships NO native -health binary flag (confirmed via `docker run --rm grafana/mimir:3.0.6 -help 2>&1 | grep -iE -- '-health(-check)?'` -> no match). Outcome B applies: mimir_healthcheck_test default is `[\"CMD\", \"/bin/mimir\", \"-version\"]` (binary-alive proxy; `-version` exits 0 with `Mimir, version 3.0.6 (...)` banner -- verified empirically). Authoritative readiness gate is the verify task's in-network /ready curl probe"
  - "D-27 vault key alias surface extended: vault_mimir_s3_access_key / vault_mimir_s3_secret_key alias to vault_minio_root_user / vault_minio_root_password -- same cheap forward-compat pattern as Loki + Tempo for the deferred per-backend MinIO IAM hardening. Phase-2 vault.yml.example is now complete (Loki + Tempo + Mimir aliases all present)"

patterns-established:
  - "Three-distinct-bucket S3 storage trinity for components with multiple internal stores -- each store gets its own top-level `<store>_storage.s3.bucket_name` key; bucket names live in defaults and surface explicit in the rendered config so a future maintainer reading /etc/mimir/mimir.yaml can immediately see which buckets each store needs."
  - "Bucket-trinity verify-task assertion with set -e short-circuit: one-shot mc container runs `mc ls --json local/bucket1; mc ls --json local/bucket2; mc ls --json local/bucket3` against the role's vault creds. First failing bucket aborts the playbook and points at the bad bucket without operator hunting."
  - "Five-knob monolithic tuning template comments: each knob is inline-cited with the matching PITFALLS.md section reference (Pitfall 11 / Pitfall 3) AND the CONTEXT.md decision reference (D-36). Future maintainers see the trap inline, no document-hunting required."
  - "Phase 2 final acceptance shape: with mimir wired, the full deploy_docker.yml roles list is minio -> loki -> tempo -> mimir, in dependency order. Pre-task creates the telemetron Docker bridge network, then each role runs its config-render + volume + pull + container + verify cycle; the canonical-template + canonical-verify pattern works as designed for FOUR roles."

requirements-completed:
  - BACK-01
  - BACK-04

# Metrics
duration: 7 min
completed: 2026-05-17
---

# Phase 2 Plan 3: Mimir Role Port Summary

**Grafana Mimir 3.0.6 monolithic-mode Ansible role deployed via Docker against the THREE distinct MinIO buckets bootstrapped in Phase 1 (mimir-blocks / mimir-ruler / mimir-alerts) -- D-26 multitenancy off, D-28 gRPC pinned to 9097, D-36 + Pitfall 11 five-knob monolithic tuning all inline-cited, D-35 / BACK-04 retention default 30d, D-27 vault alias surface complete, conditional Docker HEALTHCHECK (Outcome B `-version` proxy) reusing the Plan 02-02 Tempo pattern, in-network `/ready` curl probe + bucket-trinity mc-ls assertion as the verify gate. Phase 2 is FEATURE-COMPLETE -- the full minio -> loki -> tempo -> mimir chain is now wired in playbooks/deploy_docker.yml.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-17T17:23:00Z
- **Completed:** 2026-05-17T17:30:45Z
- **Tasks:** 3
- **Files created:** 8 (7 role/inventory + this SUMMARY)
- **Files modified:** 3 (vault.yml.example, playbooks/deploy_docker.yml, roles/README.md)

## Accomplishments

- **Mimir 3.0.6 role ported** from the upstream INSPQ source-of-truth, structurally mirroring the just-landed `roles/tempo/` template (which itself mirrors `roles/loki/` / `roles/minio/`) -- same six-task `tasks/main.yml` shape, same single-handler W6 restart, same D-10a `docker_container_info` pre-poll, same W8 in-network verify, same OPS-03 README schema. The canonical role template proves it works for the THIRD Phase-2 backend with only Mimir-specific tunables changing.
- **D-25 opinionated-improvement pass over the upstream applied:** dropped `latest` image tag, `America/Toronto` timezone, French task names, INSPQ-scale limits (5M -> 500k series), 2-year retention (2y -> 30d), filesystem storage backend (-> S3 with three buckets), `inventory_hostname`-embedded container names (-> simple `mimir`), `alertmanager.external_url` upstream hostname pattern, `ruler.alertmanager_url` upstream hostname pattern, LVM tasks, UFW tasks, `standalone` conditional dead code, `alertmanager.fallback_config_file` upstream path. **Added the missing-in-upstream guards:** D-36 Pitfall-11 monolithic tuning (the upstream had ZERO of these guards), D-36 Pitfall-3 cardinality limits, D-28 explicit gRPC port pin, D-39 three-distinct-bucket S3 (the upstream defaulted to filesystem and never validated S3 multi-bucket). This is the most consequential D-25 improvement pass for any Phase-2 role -- five PITFALLS guards that were entirely absent in the upstream.
- **BACK-01 delivered:** Mimir monolithic against the Phase-1 MinIO buckets with the named volume `telemetron_mimir_data` covering `/data` (tsdb/, tsdb-sync/, compactor/, alertmanager/, ruler/).
- **BACK-04 delivered (the highest-impact M1 Mimir requirement):**
  - Three distinct buckets in the rendered config: `blocks_storage.s3.bucket_name: mimir-blocks`, `ruler_storage.s3.bucket_name: mimir-ruler`, `alertmanager_storage.s3.bucket_name: mimir-alerts`. Mimir refuses to start when these share a prefix (Pitfall G).
  - `compactor.blocks_retention_period: {{ mimir_compactor_blocks_retention_period }}` defaulting to `30d` via `telemetron_default_metric_retention`.
  - All five D-36 / Pitfall 11 + Pitfall 3 knobs present in the rendered config and inline-cited.
- **D-26 delivered:** `multitenancy_enabled: false` is the top-level YAML key in the rendered config; producers in Phase 3 need no tenant config.
- **D-28 delivered:** `server.grpc_listen_port: 9097` is the explicit pin in the rendered config; completes the no-clash port trinity Loki 9095 / Tempo 9096 / Mimir 9097.
- **D-27 alias surface complete:** `vault.yml.example` now declares all six Phase-2 alias keys (Loki + Tempo + Mimir), each aliasing to `vault_minio_root_user` / `vault_minio_root_password`. Phase 1 MinIO block + Loki block + Tempo block untouched; only the Mimir block was appended.
- **D-23 playbook wiring complete:** `playbooks/deploy_docker.yml` now runs `minio -> loki -> tempo -> mimir` in series (lines 36 / 39 / 42 / 45 respectively). Pre_task for `telemetron` network creation untouched. **Phase 2 is FEATURE-COMPLETE** -- the trailing comment block now lists only Phase 3+ roles as remaining.
- **`roles/README.md` port-status table updated:** `mimir` row flipped from open box to ticked. Four of fourteen roles ported (`minio`, `loki`, `tempo`, `mimir`).
- **Healthcheck probe executed:** `docker run --rm grafana/mimir:3.0.6 -help 2>&1 | grep -iE -- '-health(-check)?'` returned no match. Mimir 3.0.6 does NOT ship a native `-health` binary flag in the distroless image. The role default `mimir_healthcheck_test: ["CMD", "/bin/mimir", "-version"]` is **Outcome B** -- the binary-alive proxy. `-version` was confirmed to exit 0 with the `Mimir, version 3.0.6 (branch: HEAD, revision: 25026e72)` banner. The verify task's in-network `/ready` curl probe (Step 1c) is the authoritative readiness gate.
- **`ansible-lint roles/mimir/`** passes the **production** profile with **0 failures and 0 warnings** (matches the Loki + Tempo baseline).
- **`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/deploy_docker.yml`** exits 0 with the mimir role wired alongside minio + loki + tempo.

## Task Commits

Each task was committed atomically as a sequential executor (pre-commit hooks ran on every commit -- no `--no-verify`):

1. **Task 1: roles/mimir/ skeleton -- defaults, meta, handlers, template, README, inventory mimir.yml, vault.yml.example extension** -- `8856b9d` (feat)
2. **Task 2: roles/mimir/tasks/main.yml + tasks/verify.yml (conditional healthcheck + bucket-trinity assertion)** -- `800fcbf` (feat)
3. **Task 3: Wire mimir into playbooks/deploy_docker.yml + flip roles/README.md status row** -- `56a045d` (feat)

**Plan metadata commit:** (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md) -- to be recorded by the final-commit step.

## Files Created/Modified

### Created (8)

- `roles/mimir/defaults/main.yml` -- full Mimir tunable surface: image pin `grafana/mimir:3.0.6` (OPS-01), D-28 gRPC pin `9097`, D-26 `mimir_multitenancy_enabled: false`, D-30 `mimir_publish_host: false`, D-35 `mimir_compactor_blocks_retention_period: 30d` (via telemetron_default_metric_retention), D-36 five tuning knobs (`mimir_max_global_series_per_user: 500000`, `mimir_max_global_series_per_metric: 100000`, `mimir_query_store_after: 12h`, `mimir_bucket_store_sync_interval: 5m`, `mimir_compactor_cleanup_interval: 5m`), D-39 three distinct bucket vars (`mimir_blocks_bucket: mimir-blocks`, `mimir_ruler_bucket: mimir-ruler`, `mimir_alerts_bucket: mimir-alerts`) + S3 endpoint `minio:9000` (NO scheme; Mimir/Tempo format) + `mimir_s3_insecure: true`, conditional healthcheck via `mimir_healthcheck_enabled` + Outcome-B default `["CMD", "/bin/mimir", "-version"]`, restart policy `unless-stopped` (OPS-06), `mimir_container_user: "472:472"` (RESEARCH Finding 7), mc image pinned at `RELEASE.2025-04-22T16-23-26Z`, curl image pinned at `curlimages/curl:8.10.1`.
- `roles/mimir/meta/main.yml` -- galaxy_info + `community.docker` collection dependency.
- `roles/mimir/handlers/main.yml` -- single handler `Docker restart mimir` (W6 / D-19 / Pitfall 8); no `state: restarted` anywhere.
- `roles/mimir/tasks/main.yml` -- 6-task shape: ensure config dir, render template with `notify: restart mimir`, ensure volume, pull image, run container with conditional CMD-form healthcheck (`omit` when disabled) + restart policy + no-host-publish default, include `verify.yml` as final blocking task.
- `roles/mimir/tasks/verify.yml` -- four steps: (1a, when `mimir_healthcheck_enabled`) `docker_container_info` polls `State.Health.Status == 'healthy'` (D-10a); (1b, when disabled) polls `State.Running == true`; (1c, always) one-shot `curlimages/curl` curl-probes `http://mimir:9009/ready` (authoritative readiness gate); (2) one-shot `minio/mc` container asserts ALL THREE buckets reachable via `mc ls --json` with set -e short-circuit using D-27-aliased vault creds (W8 + BACK-04 + Pitfall G). Synthetic remote_write push intentionally omitted with inline RESEARCH Finding 8 citation. All steps: `changed_when: false`, `auto_remove: true`, `detach: false`, `failed_when` on non-zero exit.
- `roles/mimir/templates/mimir.yaml.j2` -- full Mimir 3.0.6 monolithic config from RESEARCH Finding 3: `target: all`, `multitenancy_enabled` rendered from defaults (D-26), `server` with explicit `grpc_listen_port: 9097` (D-28), `common.storage.s3` with `endpoint: minio:9000` (no scheme), THREE separate storage blocks (`blocks_storage.s3.bucket_name`, `ruler_storage.s3.bucket_name`, `alertmanager_storage.s3.bucket_name` -- D-39 / BACK-04 / Pitfall G), `compactor` with BOTH `blocks_retention_period` AND `cleanup_interval` (D-35 + D-36), `querier.query_store_after` (D-36), `blocks_storage.bucket_store.sync_interval` (D-36), `blocks_storage.tsdb.out_of_order_time_window` (Mimir OOO window), `limits` with `max_global_series_per_user` + `max_global_series_per_metric` (D-36 + Pitfall 3). All five D-36 knobs inline-cited with Pitfall reference. Pitfall 11 cited 3 times (sync_interval + cleanup_interval + query_store_after); Pitfall 3 cited 2 times (both cardinality limits); Pitfall G + BACK-04 cited in the three-bucket section header.
- `roles/mimir/README.md` -- 289 lines, mirrors `roles/tempo/README.md` schema section-by-section. Documents three-bucket trinity (BACK-04 + Pitfall G), D-36 / Pitfall 11 + Pitfall 3 monolithic tuning, three healthcheck outcomes (A native -health / B -version proxy / C disabled), full D-25 deviation table (5M->500k series, 2y->30d retention, filesystem->S3, dropped LVM/UFW/inventory_hostname/standalone-conditional, added D-36 + D-28 + D-39 guards that the upstream lacked), deprecation notes (Mimir is the locked LTM backend; VictoriaMetrics/Thanos explicitly out of M1 scope).
- `inventory/example-homelab/group_vars/all/mimir.yml` -- D-30 `mimir_publish_host: false`, BACK-04 `mimir_compactor_blocks_retention_period: "{{ telemetron_default_metric_retention | default('30d') }}"`.

### Modified (3)

- `inventory/example-homelab/group_vars/all/vault.yml.example` -- extended with the D-27 alias keys (`vault_mimir_s3_access_key`, `vault_mimir_s3_secret_key`) aliased to `vault_minio_root_user` / `vault_minio_root_password`, appended immediately after the Phase-2 Tempo section. Phase 1 + Loki + Tempo sections untouched. The Phase-2 vault alias surface is now feature-complete (six alias keys total: 2x Loki + 2x Tempo + 2x Mimir).
- `playbooks/deploy_docker.yml` -- appended `- role: mimir` with tag `[mimir]` after the existing tempo entry. Final order: minio (line 36) -> loki (line 39) -> tempo (line 42) -> mimir (line 45). Pre_task for `telemetron` network creation untouched. The trailing comment block updated: removed the Phase-2 "mimir (after tempo)" line since Phase 2 is now complete; Phase 3+ remaining roles preserved as-is.
- `roles/README.md` -- port-status table: `mimir` row flipped from open box to ticked. Four of fourteen roles ported.

## Decisions Made

- **Default `mimir_healthcheck_test` set to Outcome B in defaults/main.yml.** The image probe at execute time returned no `-health` flag (confirmed empirically: `docker run --rm grafana/mimir:3.0.6 -help 2>&1 | grep -iE -- '-health(-check)?'` -> no match; the only relevant help output was generic flag listing without any health-binary option), so Outcome A is ruled out for this image tag. `-version` exits 0 with the version banner -- valid binary-alive proxy. The verify task's `/ready` curl probe is the authoritative readiness gate regardless. Operators can flip to Outcome C (`mimir_healthcheck_enabled: false`) without touching the role if they prefer the omit-HEALTHCHECK shape.
- **Kept the upstream-INSPQ deviation audit table in `roles/mimir/README.md` as required by D-25, despite the INSPQ grep gate hits.** Same precedent as Loki + Tempo Deviation 1: the grep gate is scoped to code/config files (its intent is "no INSPQ-isms as config artifacts / vault paths / hardcoded values"); D-25 explicitly requires every Phase-2 role README to document upstream deviations -- which necessarily mentions the source-of-truth project name. All INSPQ-string matches in `roles/mimir/` are exclusively in `README.md`. `grep -riEc 'inspq|qc\\.ca|montreal|...' roles/mimir/defaults/ roles/mimir/meta/ roles/mimir/handlers/ roles/mimir/tasks/ roles/mimir/templates/ inventory/example-homelab/group_vars/all/mimir.yml playbooks/deploy_docker.yml` returns zero matches.
- **Surfaced `mimir_healthcheck_test` in defaults/main.yml in Task 1 (not Task 2 as the plan suggested as optional).** The plan's Task 2 action section suggested probing the image then optionally appending the healthcheck test variable; writing the complete defaults file in Task 1 with the Outcome-B default keeps the file diff atomic per Phase-1 W2 (one-task-one-commit). Same call as Plan 02-02 Deviation 4. The probe was executed before Task 1 commit so the default landed correctly first time.
- **Pinned `mimir_curl_image` / `mimir_curl_image_tag` defaults for the `/ready` probe one-shot (not hardcoded).** OPS-01 spirit -- operator override path is `mimir_curl_image_tag: <other-tag>` in `inventory/<env>/group_vars/all/mimir.yml`. Same pattern as Tempo + Loki Deviation 5.
- **Added `mimir_mc_image` / `mimir_mc_image_tag` defaults pinning `minio/mc:RELEASE.2025-04-22T16-23-26Z` for the bucket-trinity assertion.** Same pin as the Phase-1 minio role bootstrap. Mirrors Loki's `loki_mc_image` pattern.
- **Added `blocks_storage.tsdb.out_of_order_time_window` to the rendered template** under the `tsdb` sub-block (not at the top-level `limits` block as some Mimir samples show). Mimir 3.x docs confirm this is the correct location for the OOO window. Default `mimir_ooo_time_window: 30m` matches upstream INSPQ's value.
- **No explicit `force_path_style` key set in the rendered config** -- per RESEARCH Open Question #2, Mimir 3.x auto-detects path-style for non-AWS endpoints, and the `insecure: true` flag is sufficient to signal MinIO's plain-HTTP + path-style requirement. The `endpoint: minio:9000` (no scheme) format under `common.storage.s3` is the validated shape from the official Mimir play-with-grafana-mimir example.

## Deviations from Plan

None requiring inline fixes. The plan was followed verbatim modulo the Task-1-vs-Task-2 split of the healthcheck-test default (planned as optionally-Task-2; executed in Task 1 for atomicity per the established Phase-2 W2 precedent -- documented above under "Decisions Made"). No template comments tripped the gates (lesson learned from Plan 02-02 Tempo Deviation 1 + 2 was applied proactively: README.md is the documented exception for INSPQ-string mentions, code/config files use "upstream" phrasing). Single-line OTLP body issue from Plan 02-02 didn't apply here (no synthetic push payload to build for Mimir). `ansible-lint roles/mimir/` passed the production profile with 0 failures + 0 warnings on the first run.

**Total deviations:** 0 inline fixes (all Phase-2 lessons-learned applied proactively in this third role port).
**Impact on plan:** None. The role mirrors the canonical roles/{loki,tempo}/ template verbatim; the Phase-2 wave-1 wiring shape is preserved (minio -> loki -> tempo -> mimir); all port-acceptance gates pass on roles/mimir/; ansible-lint passes the production profile cleanly.

## Issues Encountered

- **In-network end-to-end test was NOT executed during plan execution.** Same situation as Plans 02-01 + 02-02: the executor runs on Rock's workstation, not on the homelab Docker target host. The end-to-end test requires (a) the `telemetron` network created on the target, (b) the Phase 1 MinIO container running with all three `mimir-*` buckets bootstrapped, (c) the Loki + Tempo containers from Plans 02-01 + 02-02 also running, (d) a populated `vault.yml` with the D-27 Mimir keys. Local workstation has Docker (the image probe ran) but no populated vault and not the homelab MinIO state. The exact run sequence for human verification is documented below under "User Setup Required".
- **`ansible-playbook --syntax-check` PASSED** with the mimir role wired into `deploy_docker.yml` (alongside minio + loki + tempo), confirming the role is structurally valid Ansible (modules resolve, tags parse, includes load).
- **`ansible-lint roles/mimir/`** passes the **production** profile with 0 failures and 0 warnings on the first run -- no inline fixes needed.
- **No carry-forward blockers from Plans 02-01 + 02-02.** The canonical-template pattern + conditional-healthcheck pattern + dual-knob-or-multi-bucket-trinity-retention pattern all work as designed for the THIRD Phase-2 backend.

## Authentication Gates

None. No auth interactions needed (vault password is provided at operator playbook-run time on the target host, not during role port development).

## User Setup Required

External services require manual configuration on the homelab target host. Operators should:

1. Extend `inventory/example-homelab/group_vars/all/vault.yml` with `vault_mimir_s3_access_key` and `vault_mimir_s3_secret_key` (aliases to existing `vault_minio_root_user` / `vault_minio_root_password` per D-27). Re-encrypt with `ansible-vault encrypt`.
2. Run the end-to-end deploy + verify (targeted to mimir alone):
   ```bash
   ansible-playbook -i inventory/example-homelab \
                    playbooks/deploy_docker.yml \
                    --tags mimir --ask-vault-pass
   ```
3. Verify the rendered config has the load-bearing knobs (belt-and-suspenders check on top of the verify task's automated gates):
   ```bash
   docker exec mimir cat /etc/mimir/mimir.yaml | grep 'grpc_listen_port:'
   # Expects: grpc_listen_port: 9097

   docker exec mimir cat /etc/mimir/mimir.yaml | grep -E 'bucket_name: mimir-(blocks|ruler|alerts)'
   # Expects: 3 lines (one per bucket)

   docker exec mimir cat /etc/mimir/mimir.yaml | grep -E 'max_global_series_per_user|max_global_series_per_metric|query_store_after|sync_interval|cleanup_interval'
   # Expects: 5 lines (all D-36 knobs present)

   docker exec mimir cat /etc/mimir/mimir.yaml | grep 'multitenancy_enabled:'
   # Expects: multitenancy_enabled: false

   docker exec mimir cat /etc/mimir/mimir.yaml | grep 'blocks_retention_period:'
   # Expects: blocks_retention_period: 30d

   # Verify /ready endpoint:
   docker run --rm --network telemetron curlimages/curl:8.10.1 \
     curl -sS http://mimir:9009/ready
   # Expects: ready

   # Verify all three buckets reachable via mimir creds (D-27 alias works):
   docker run --rm --network telemetron \
     -e MC_HOST_local="http://${MROOT}:${MPASS}@minio:9000" \
     minio/mc:RELEASE.2025-04-22T16-23-26Z mc ls local/mimir-blocks local/mimir-ruler local/mimir-alerts

   # Phase 2 acceptance -- full minio + loki + tempo + mimir stack:
   docker inspect minio loki tempo mimir --format '{{.Name}} {{.State.Status}} {{.State.Health.Status}}'
   ```
4. Re-run idempotency check (Phase 2 FULL playbook this time):
   ```bash
   ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --ask-vault-pass
   # Expects PLAY RECAP: changed=0 on the second run
   ```

## Next Phase Readiness

**Phase 2 is FEATURE-COMPLETE.** All three telemetry backends (Loki + Tempo + Mimir) are ported, wired into `playbooks/deploy_docker.yml` in dependency order after `minio` (full chain: minio -> loki -> tempo -> mimir), and pass all five per-role port-acceptance gates. The canonical role template pattern was proven across four roles total (minio + loki + tempo + mimir), with two healthcheck approaches established (native `-health` flag for Loki; conditional binary-alive proxy + State.Running fallback for Tempo and Mimir).

**Phase 3 (Ingest Plane)** is ready for planning. Phase 3 will append the producer-side roles to `playbooks/deploy_docker.yml`:
- `prometheus` -- short-term metrics + alerting eval; will `remote_write` to mimir on port 9009 (D-26 single-tenant, no X-Scope-OrgID needed).
- `opentelemetry` -- OTel Collector; will own standard OTLP ports `:4317`/`:4318` (reserved by Plan 02-02 D-29/BACK-05); forwards traces to tempo on `:14318` and logs to loki on `:3100/loki/api/v1/push`.
- `fluentbit` -- log shipping with the source-side label allowlist `{job, host, service, env, level}` complementing Plan 02-01's Loki-side limits (D-37).
- `node_exporter` -- host metrics scraped by prometheus.

The patterns Phase 3 reuses from Phase 2:
- D-23 wire-after-previous role-list append.
- D-10a HEALTHCHECK poll + (when needed) conditional healthcheck with `omit` magic value.
- D-27 vault alias surface (extends with `vault_prometheus_*`, `vault_otel_*` etc. if any new credentials land).
- D-30 no-host-publish default.
- W6 single-handler restart, W7 changed_when:false, W8 in-network verify.
- OPS-03 README schema.

**No blockers carried forward.**

---

## Self-Check: PASSED

All claimed files exist on disk and all task commits are in git history:

- `roles/mimir/defaults/main.yml` -- FOUND
- `roles/mimir/meta/main.yml` -- FOUND
- `roles/mimir/handlers/main.yml` -- FOUND
- `roles/mimir/tasks/main.yml` -- FOUND
- `roles/mimir/tasks/verify.yml` -- FOUND
- `roles/mimir/templates/mimir.yaml.j2` -- FOUND
- `roles/mimir/README.md` -- FOUND (289 lines)
- `inventory/example-homelab/group_vars/all/mimir.yml` -- FOUND
- `inventory/example-homelab/group_vars/all/vault.yml.example` -- MODIFIED (D-27 mimir alias keys appended after Tempo section)
- `playbooks/deploy_docker.yml` -- MODIFIED (mimir role wired after tempo; line 45)
- `roles/README.md` -- MODIFIED (mimir status flipped to ticked)
- Task 1 commit `8856b9d` -- FOUND in git log
- Task 2 commit `800fcbf` -- FOUND in git log
- Task 3 commit `56a045d` -- FOUND in git log

`ansible-lint roles/mimir/` (production profile): 0 failures, 0 warnings.
`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/deploy_docker.yml` (with mimir wired): exits 0.

Grep gate roll-up:
- `grep -riEc 'inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq' roles/mimir/defaults/ roles/mimir/meta/ roles/mimir/handlers/ roles/mimir/tasks/ roles/mimir/templates/ inventory/example-homelab/group_vars/all/mimir.yml playbooks/deploy_docker.yml` -- ZERO matches on code/config.
- `grep -rPnc '[^\x00-\x7F]' roles/mimir/ inventory/example-homelab/group_vars/all/mimir.yml` -- ZERO non-ASCII characters.
- `grep -rE ':latest' roles/mimir/` -- ZERO floating-tag references (OPS-01).
- `grep -ciE 'state: restarted' roles/mimir/handlers/main.yml roles/mimir/defaults/main.yml roles/mimir/tasks/` -- ZERO directive matches (the single hit in roles/mimir/README.md is a negative documentation reference: "state: restarted is never used (Pitfall 8)").

Phase-2 acceptance roll-up across all four roles wired (minio + loki + tempo + mimir):
- All four `- role:` entries present in `playbooks/deploy_docker.yml`.
- Order preserved: minio (36) < loki (39) < tempo (42) < mimir (45).
- Pre_task `community.docker.docker_network` for the telemetron bridge untouched (1 occurrence).

---

*Phase: 02-telemetry-backends*
*Plan: 02-03 (Mimir)*
*Completed: 2026-05-17*
*Phase 2 FEATURE-COMPLETE: minio -> loki -> tempo -> mimir*
