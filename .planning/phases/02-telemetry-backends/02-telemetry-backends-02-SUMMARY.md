---
phase: 02-telemetry-backends
plan: 02
subsystem: infra
tags: [ansible, docker, tempo, grafana, observability, minio, s3, monolithic, otlp]

# Dependency graph
requires:
  - phase: 01-foundation-storage
    provides: telemetron Docker bridge network, MinIO with tempo-traces bucket bootstrapped, vault_minio_root_user/password keys, canonical roles/minio/ template (D-10a HEALTHCHECK poll, W6 single-handler restart, W7 changed_when:false on verify, W8 in-network verify, OPS-03 README schema)
  - phase: 02-telemetry-backends
    plan: 01
    provides: D-27 per-backend vault key alias surface, Phase-2 canonical role shape (roles/loki/), playbooks/deploy_docker.yml wired through loki
provides:
  - roles/tempo/ Ansible role (Tempo 2.10.5 monolithic, S3-backed against tempo-traces, OTLP receivers on internal-only :14317/:14318)
  - D-27 alias surface extended (vault_tempo_s3_access_key / vault_tempo_s3_secret_key aliased to MinIO root creds)
  - inventory/example-homelab/group_vars/all/tempo.yml (D-30 no-host-publish, BACK-03 dual-knob retention knobs, D-38 metrics-generator toggle)
  - playbooks/deploy_docker.yml wired through tempo after loki (D-23) -- minio -> loki -> tempo
  - D-34 dual-knob retention pattern (Pitfall 10 mitigation) demonstrated; reusable for any future trace-or-metrics backend with two-phase mark-then-delete retention
  - Conditional healthcheck pattern (`tempo_healthcheck_enabled` + `omit` magic value) for distroless images that may or may not ship a native -health binary -- applicable to Mimir in Plan 02-03
affects: [02-03-mimir, 03-prometheus, 03-fluentbit, 03-opentelemetry, 05-grafana]

# Tech tracking
tech-stack:
  added:
    - grafana/tempo:2.10.5 (trace backend, monolithic mode -target=all)
    - curlimages/curl:8.10.1 (reused from Plan 02-01 for /ready probe + OTLP push one-shots)
  patterns:
    - Conditional Docker HEALTHCHECK via `tempo_healthcheck_enabled` toggle + Ansible `omit` magic value -- handles RESEARCH Finding 6 MEDIUM-confidence distroless-image health-binary uncertainty without branching the role per image tag
    - Authoritative readiness via in-network /ready curl probe (Step 1c) -- belt-and-suspenders gate independent of Docker HEALTHCHECK availability
    - OTLP push verification at internal-only alt port (:14318) -- proves BACK-05 wiring without exposing OTLP ports to the host
    - JSON body assembly via printf with split format args -- keeps long synthetic payloads under the 160-char ansible-lint yaml[line-length] cap without changing wire semantics (JSON whitespace is insignificant)
    - INTENTIONAL omission of Step 3 (bucket-landing assertion) -- documented inline; RESEARCH Finding 8 says Tempo's 2h max_block_duration default makes single-trace bucket verification unreliable in a Phase-2 verify window

key-files:
  created:
    - roles/tempo/defaults/main.yml
    - roles/tempo/meta/main.yml
    - roles/tempo/handlers/main.yml
    - roles/tempo/tasks/main.yml
    - roles/tempo/tasks/verify.yml
    - roles/tempo/templates/tempo.yaml.j2
    - roles/tempo/README.md
    - inventory/example-homelab/group_vars/all/tempo.yml
  modified:
    - inventory/example-homelab/group_vars/all/vault.yml.example
    - playbooks/deploy_docker.yml
    - roles/README.md

key-decisions:
  - "Tempo image pinned to grafana/tempo:2.10.5 with -target=all monolithic CLI; v3.0 is pre-release and explicitly out of M1 scope per CLAUDE.md tech-stack constraints"
  - "gRPC port explicitly pinned to 9096 (D-28) -- moves off the default 9095 to avoid clash with Loki on a single homelab host; Mimir will move to 9097 in Plan 02-03"
  - "OTLP receivers bind to internal-only alt ports :14317 (gRPC) and :14318 (HTTP) per D-29 / BACK-05; standard :4317/:4318 reserved for the Phase 3 OTel Collector"
  - "D-34 dual-knob retention -- BOTH `block_retention: 168h` AND `compacted_block_retention: 1h` are set in the rendered config with inline Pitfall 10 citation; single-knob retention silently fails (highest-impact M1 Tempo pitfall)"
  - "D-38 resolved to path (b) -- metrics-generator processors [service-graphs, span-metrics, local-blocks] persist to a local WAL at /var/tempo/generator/wal; zero `remote_write` block in the rendered config so Tempo's startup is decoupled from Mimir availability (full Grafana service-graph view requires post-M1 remote_write -- deferred)"
  - "Healthcheck probe outcome: Tempo 2.10.5 ships NO native -health binary flag (confirmed via `docker run --rm grafana/tempo:2.10.5 -help | grep -iE -- '-health'` -> no match). Outcome B applies: tempo_healthcheck_test default is `[\"CMD\", \"/tempo\", \"-version\"]` (binary-alive proxy, exit code 0). Authoritative readiness gate is the verify task's in-network /ready curl probe"
  - "D-27 vault key alias surface extended: vault_tempo_s3_access_key / vault_tempo_s3_secret_key alias to vault_minio_root_user / vault_minio_root_password -- same cheap forward-compat pattern as Plan 02-01 for the deferred per-backend MinIO IAM hardening"

patterns-established:
  - "Conditional Docker HEALTHCHECK pattern for distroless images: `healthcheck: \"{{ container_healthcheck if (healthcheck_enabled | bool) else omit }}\"` -- handles uncertain native-health-binary availability without role branching. Reusable for Mimir in Plan 02-03."
  - "OTLP alt-port-in-config pattern: OTLP receivers bound to non-standard ports (:14317/:14318) on the Docker bridge with the standard pair reserved for the Phase 3 OTel Collector to claim. Verify task pushes to the alt port to prove the wiring."
  - "Dual-knob retention pattern with inline Pitfall citation in the rendered config template -- future maintainers see the trap inline."
  - "Bucket-landing assertion deferred to Phase 6 OPS-07 smoke test: when a backend's block-flush window exceeds the role's verify-task wall-clock budget, the verify gates at 'push returned 200' and the durability-on-S3 check lives in the longer-running OPS-07 smoke."

requirements-completed:
  - BACK-01
  - BACK-03
  - BACK-05

# Metrics
duration: 8 min
completed: 2026-05-17
---

# Phase 2 Plan 2: Tempo Role Port Summary

**Grafana Tempo 2.10.5 monolithic-mode Ansible role deployed via Docker against MinIO tempo-traces bucket with conditional-healthcheck (Outcome B `-version` proxy), in-network `/ready` + OTLP `:14318/v1/traces` synthetic-push verify, D-34 dual-knob retention (168h + 1h with inline Pitfall 10 citation), D-29/BACK-05 OTLP alt ports (:14317/:14318 internal-only), and D-38 metrics-generator path (b) local-WAL-only operation -- second Phase-2 backend ported atop the canonical role template.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-17T17:06:43Z
- **Completed:** 2026-05-17T17:15:22Z
- **Tasks:** 3
- **Files created:** 8 (7 role/inventory + this SUMMARY)
- **Files modified:** 3 (vault.yml.example, playbooks/deploy_docker.yml, roles/README.md)

## Accomplishments

- Tempo 2.10.5 role ported from the upstream INSPQ source-of-truth, structurally mirroring the just-landed `roles/loki/` template (which itself mirrors `roles/minio/`) -- same six-task `tasks/main.yml` shape, same single-handler `W6` restart, same `D-10a` `docker_container_info` pre-poll, same `W8` in-network verify, same `OPS-03` README schema. The canonical role template proves it works for a SECOND Phase-2 backend with only Tempo-specific tunables changing.
- D-25 opinionated-improvement pass over the upstream applied: dropped `latest` image tag, `America/Toronto` timezone, French task names, Jaeger receivers (`thrift_http`, `thrift_binary`, `thrift_compact`), standard-port assumption `:4317`/`:4318` (replaced with alt `:14317`/`:14318`), local-backend storage (replaced with S3/MinIO), single-knob retention (replaced with dual-knob D-34), distributed-mode dead code (memberlist, replication_factor, scalable-single-binary vars), half-config metrics-generator (replaced with full D-38 path b).
- **BACK-01 delivered:** Tempo monolithic against the Phase-1 `tempo-traces` bucket with the named volume `telemetron_tempo_data` covering `/var/tempo` (wal/, traces/, generator/wal, generator/traces).
- **BACK-03 delivered (the highest-impact M1 Tempo pitfall):** dual-knob retention in the rendered config -- BOTH `compactor.compaction.block_retention: {{ tempo_block_retention }}` AND `compactor.compaction.compacted_block_retention: {{ tempo_compacted_block_retention }}` are present, with an inline `# See PITFALLS.md Pitfall 10 ...` citation comment. Defaults set `168h` (7d, mark phase) and `1h` (delete phase) respectively. Both knobs surface in `inventory/example-homelab/group_vars/all/tempo.yml` for operator visibility.
- **BACK-05 delivered:** OTLP receivers bind to internal-only `:14317` (gRPC) and `:14318` (HTTP). The rendered config contains `endpoint: "0.0.0.0:14317"` and `endpoint: "0.0.0.0:14318"` under `distributor.receivers.otlp.protocols`. Standard `:4317`/`:4318` are NOT in the rendered config and are NOT host-published, reserving them for the Phase 3 OTel Collector.
- **D-38 resolved to path (b):** the rendered config has the top-level `metrics_generator.storage.path: /var/tempo/generator/wal` block AND the `overrides.defaults.metrics_generator.processors: [service-graphs, span-metrics, local-blocks]` block. Zero `remote_write` occurrences in the rendered template. Tempo's startup is decoupled from Mimir availability.
- **D-27 alias surface extended:** `vault.yml.example` now declares `vault_tempo_s3_access_key` and `vault_tempo_s3_secret_key`, both aliased to `vault_minio_root_user` / `vault_minio_root_password`. Phase 1 MinIO block + Loki block untouched.
- **D-23 playbook wiring complete:** `playbooks/deploy_docker.yml` now runs `minio -> loki -> tempo` in series. Pre_task for `telemetron` network creation untouched. The trailing comment block updated to reflect Mimir as the sole remaining Wave-1 role.
- **`roles/README.md` port-status table updated:** `tempo` row flipped from `[ ]` to `[x]`. Three of fourteen roles ported (`minio`, `loki`, `tempo`).
- **Healthcheck probe executed:** `docker run --rm grafana/tempo:2.10.5 -help 2>&1 | grep -iE -- '-health(-check)?'` returned no match. Tempo 2.10.5 does NOT ship a native `-health` binary flag in the distroless image. The role default `tempo_healthcheck_test: ["CMD", "/tempo", "-version"]` is **Outcome B** -- the binary-alive proxy. `-version` was confirmed to exit 0 with the `tempo, version v2.10.5` banner. The verify task's in-network `/ready` curl probe (Step 1c) is the authoritative readiness gate.
- **`ansible-lint roles/tempo/`** passes the **production** profile with 0 failures and 0 warnings (matches the Loki baseline).
- **`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/deploy_docker.yml`** exits 0 with the tempo role wired alongside minio + loki.

## Task Commits

Each task was committed atomically as a sequential executor (pre-commit hooks ran on every commit -- no `--no-verify`):

1. **Task 1: roles/tempo/ skeleton -- defaults, meta, handlers, template, README, inventory tempo.yml, vault.yml.example extension** -- `eec3586` (feat)
2. **Task 2: roles/tempo/tasks/main.yml + tasks/verify.yml (conditional healthcheck + OTLP synthetic push)** -- `8920cea` (feat)
3. **Task 3: Wire tempo into playbooks/deploy_docker.yml + flip roles/README.md status row** -- `df7fe87` (feat)

**Plan metadata commit:** (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md) -- to be recorded by the final-commit step.

## Files Created/Modified

### Created (8)

- `roles/tempo/defaults/main.yml` -- full Tempo tunable surface: image pin `grafana/tempo:2.10.5` (OPS-01), D-28 gRPC pin `9096`, D-29 OTLP alt ports `14317`/`14318`, D-30 `tempo_publish_host: false`, D-34 dual-knob retention defaults (168h + 1h), D-38 `tempo_metrics_generator_enabled: true`, D-39 Tempo-specific S3 endpoint `minio:9000` (no scheme) + `forcepathstyle: true`, conditional healthcheck via `tempo_healthcheck_enabled` + `tempo_healthcheck_test: ["CMD","/tempo","-version"]` (Outcome B), restart policy `unless-stopped` (OPS-06), `tempo_curl_image: curlimages/curl` pinned at `8.10.1`.
- `roles/tempo/meta/main.yml` -- galaxy_info + `community.docker` collection dependency.
- `roles/tempo/handlers/main.yml` -- single handler `Docker restart tempo` (W6 / D-19 / Pitfall 8); no `state: restarted` anywhere.
- `roles/tempo/tasks/main.yml` -- 6-task shape: ensure config dir, render template with `notify: restart tempo`, ensure volume, pull image, run container with conditional CMD-form healthcheck (`omit` when disabled) + restart policy + no-host-publish default + OTLP alt ports never host-published under any condition, include `verify.yml` as final blocking task.
- `roles/tempo/tasks/verify.yml` -- four steps: (1a, when `tempo_healthcheck_enabled`) `docker_container_info` polls `State.Health.Status == 'healthy'` (D-10a); (1b, when disabled) polls `State.Running == true`; (1c, always) one-shot `curlimages/curl` curl-probes `http://tempo:3200/ready` (authoritative readiness gate); (2) one-shot curl POSTs synthetic OTLP/HTTP trace to `http://tempo:14318/v1/traces`, accepts 200/202/204 (W8). Step 3 intentionally omitted with inline RESEARCH Finding 8 citation. All steps: `changed_when: false`, `auto_remove: true`, `detach: false`, `failed_when` on non-zero exit.
- `roles/tempo/templates/tempo.yaml.j2` -- full Tempo 2.10.5 monolithic config from RESEARCH Finding 4: `stream_over_http_enabled: true`, `server` with explicit `grpc_listen_port: 9096` (D-28), `distributor.receivers.otlp` with `0.0.0.0:14317` (gRPC) + `0.0.0.0:14318` (HTTP) (D-29/BACK-05), `metrics_generator.storage.path` + `metrics_generator.traces_storage.path` (D-38), `storage.trace.s3` with `endpoint: minio:9000` (no scheme), `bucket: tempo-traces`, `forcepathstyle: true`, `insecure: true`, `storage.trace.wal.path` + `storage.trace.local.path`, `compactor.compaction` with BOTH `block_retention` AND `compacted_block_retention` AND inline Pitfall 10 citation (D-34/BACK-03), `overrides.defaults.metrics_generator.processors: [service-graphs, span-metrics, local-blocks]` (D-38 path b). Zero `remote_write` occurrences.
- `roles/tempo/README.md` -- 294 lines, mirrors `roles/loki/README.md` schema section-by-section. Documents OTLP alt ports (BACK-05), dual-knob retention (BACK-03 + Pitfall 10), metrics-generator path (b) (D-38), three healthcheck outcomes (A native -health / B -version proxy / C disabled), deviation table (D-25), deprecation notes (Tempo 3.x deferred).
- `inventory/example-homelab/group_vars/all/tempo.yml` -- D-30 `tempo_publish_host: false`, BACK-03 dual-knob `tempo_block_retention: 168h` + `tempo_compacted_block_retention: 1h`, D-38 `tempo_metrics_generator_enabled: true`.

### Modified (3)

- `inventory/example-homelab/group_vars/all/vault.yml.example` -- extended with the D-27 alias keys (`vault_tempo_s3_access_key`, `vault_tempo_s3_secret_key`) aliased to `vault_minio_root_user` / `vault_minio_root_password`, appended immediately after the Phase 2 Loki section. Phase 1 + Loki sections untouched.
- `playbooks/deploy_docker.yml` -- appended `- role: tempo` with tag `[tempo]` after the existing loki entry. Final order: minio (line 36) -> loki (line 39) -> tempo (line 42). Pre_task for `telemetron` network creation untouched. The trailing comment block updated to reflect Mimir as the sole remaining Wave-1 role.
- `roles/README.md` -- port-status table: `tempo` row flipped from `[ ]` to `[x]`. Three of fourteen roles ported.

## Decisions Made

- **Default `tempo_healthcheck_test` set to Outcome B in defaults/main.yml.** The image probe at execute time returned no `-health` flag (confirmed empirically: `docker run --rm grafana/tempo:2.10.5 -help 2>&1 | grep -iE -- '-health'` -> no match), so Outcome A is ruled out for this image tag. `-version` exits 0 with a version banner -- valid binary-alive proxy. The verify task's `/ready` curl probe is the authoritative readiness gate regardless. Operators can flip to Outcome C (`tempo_healthcheck_enabled: false`) without touching the role if they prefer the omit-HEALTHCHECK shape.
- **Kept the upstream-INSPQ deviation audit table in `roles/tempo/README.md` as required by D-25, despite the INSPQ grep gate.** Same precedent as Loki Deviation 1: the grep gate is scoped to code/config files (its intent is "no INSPQ-isms as config artifacts / vault paths / hardcoded values"); D-25 explicitly requires every Phase-2 role README to document upstream deviations -- which necessarily mentions the source-of-truth project name. All INSPQ-string matches in `roles/tempo/` are exclusively in `README.md`. `grep -riE 'inspq|qc\\.ca|montreal|...' roles/tempo/defaults/ roles/tempo/meta/ roles/tempo/handlers/ roles/tempo/tasks/ roles/tempo/templates/` returns zero matches.
- **Reworded `defaults/main.yml` comment from "per INSPQ default" to "per upstream default".** Same intent (Tempo image's default UID is 1000:0); zero gate hits on code/config. README documentation retains the explicit INSPQ deviation table per D-25.
- **Reworded two template comments from "remote_write intentionally absent" / "no remote_write" to "cross-backend write to Mimir intentionally absent" / "no cross-backend forwarding".** The plan's acceptance criterion `grep -c 'remote_write' roles/tempo/templates/tempo.yaml.j2` returns 0 -- the verbatim self-documenting "no remote_write" comments tripped the literal gate. Reworded comments preserve the operator-facing intent (D-38 path b means no Mimir forwarding) with zero literal `remote_write` substring matches. Same pattern as Loki Deviation 2 (`:latest` self-documenting comment).
- **Decomposed the synthetic OTLP body construction via `printf` with split format args.** The first draft put the JSON body on a single 413-char line, tripping `ansible-lint` yaml[line-length] (>160 chars). Rebuilt as `printf '%s%s%s...' 'json-part-1' 'json-part-2' ...`. The wire payload is functionally identical (JSON whitespace is insignificant); `ansible-lint roles/tempo/` passes the production profile with 0 failures and 0 warnings.
- **Pinned `curlimages/curl:8.10.1` via `tempo_curl_image` / `tempo_curl_image_tag` defaults** (same pin as Loki, surfaced as Tempo-prefixed vars per OPS-01 -- operator override path is `tempo_curl_image_tag: <other-tag>` in `inventory/<env>/group_vars/all/tempo.yml`).
- **Surfaced `tempo_healthcheck_test` in defaults/main.yml in Task 1 (not Task 2 as the plan suggested).** The plan suggested Task 1 might omit it and Task 2 could append it -- but writing the complete defaults file in Task 1 avoids a second edit and keeps the file diff atomic per Phase-1 W2 (one-task-one-commit). No information loss.

## Deviations from Plan

### Inline fixes during verification (deviation Rule 1)

**1. [Rule 1 - Bug] Template comments mentioning `remote_write` tripped the D-38 path-b gate**
- **Found during:** Task 1 verification (first pass).
- **Issue:** The first draft of `roles/tempo/templates/tempo.yaml.j2` had two self-documenting comments: "local WAL only; remote_write intentionally absent" and "local-only; no remote_write". The plan's acceptance criterion `grep -c 'remote_write' roles/tempo/templates/tempo.yaml.j2` MUST return 0 (D-38 path b is the absence of `remote_write` in the rendered config). The literal substring matches in the comments tripped the gate (count: 2).
- **Fix:** Reworded both comments to use "cross-backend write to Mimir intentionally absent" and "no cross-backend forwarding" -- same intent, zero gate hits. Operator-facing documentation preserved.
- **Files modified:** `roles/tempo/templates/tempo.yaml.j2`.
- **Verification:** `grep -c 'remote_write' roles/tempo/templates/tempo.yaml.j2` returns 0. Rendered config semantics unchanged.
- **Committed in:** Task 1 commit `eec3586` (after the inline fix).

**2. [Rule 1 - Bug] Defaults comment mentioning "INSPQ default" tripped the INSPQ grep gate on code/config**
- **Found during:** Task 1 verification (first pass).
- **Issue:** The `tempo_container_user: "1000:0"` comment originally read "per INSPQ default (Claude's Discretion D-39)" -- the literal `INSPQ` substring tripped the D-21 grep gate (`grep -riE 'inspq|qc\.ca|montreal|...' roles/tempo/defaults/main.yml` returned 1). Code/config files MUST have zero INSPQ matches (the README deviation table is the documented exception).
- **Fix:** Reworded to "per upstream default" -- same intent, zero gate hits. The Tempo image's default UID is 1000:0 regardless of the upstream project name.
- **Files modified:** `roles/tempo/defaults/main.yml`.
- **Verification:** `grep -riE 'inspq|...' roles/tempo/defaults/ roles/tempo/meta/ roles/tempo/handlers/ roles/tempo/tasks/ roles/tempo/templates/` returns zero matches. README documentation retains the explicit INSPQ deviation table per D-25.
- **Committed in:** Task 1 commit `eec3586` (after the inline fix).

**3. [Rule 1 - Bug] Single 413-char OTLP body line tripped `ansible-lint` yaml[line-length] (>160)**
- **Found during:** Task 2 verification (`ansible-lint roles/tempo/`).
- **Issue:** The plan's verify.yml literal for Step 2 put the full OTLP JSON body on a single shell line (413 chars after the YAML `>-` folded scalar joined the lines). `ansible-lint` production profile flagged 2 yaml[line-length] violations (lines 108 + 109 of the original verify.yml).
- **Fix:** Rebuilt the BODY construction as `BODY=$(printf '%s%s%s%s%s%s%s%s%s' 'json-part-1' 'json-part-2' ...)` with each format arg under 80 chars. JSON whitespace is insignificant; wire payload semantics unchanged.
- **Files modified:** `roles/tempo/tasks/verify.yml`.
- **Verification:** `ansible-lint roles/tempo/` passes the production profile with 0 failures and 0 warnings -- matches the Loki baseline. All gates still hold: `/v1/traces: 1`, `tempo_otlp_http_port: 1`, `auto_remove: true: 2`, `detach: false: 2`, `failed_when:: 2`, `changed_when: false: 4`.
- **Committed in:** Task 2 commit `8920cea` (after the inline fix).

### Plan-extending decisions

**4. [Rule 2 - Missing Critical] Moved Task 2's "append `tempo_healthcheck_test` to defaults" instruction up into Task 1**
- **Found during:** Task 1 (writing defaults).
- **Issue:** The plan instructed Task 1 to write `defaults/main.yml` AND Task 2 to optionally append `tempo_healthcheck_test` if Task 1 omitted it. Splitting the defaults file across two commits would violate the canonical "one-task-one-atomic-commit" pattern from Phase 1.
- **Fix:** Wrote the full defaults file (including `tempo_healthcheck_test: ["CMD", "/tempo", "-version"]`) in Task 1. Task 2 consumed the variable without further edits to defaults.
- **Files modified:** `roles/tempo/defaults/main.yml` (Task 1).
- **Verification:** `grep -c 'tempo_healthcheck_test' roles/tempo/defaults/main.yml` returns 3 (one declaration + two doc-references in comments). Task 2's gate `grep -c 'tempo_healthcheck_test' roles/tempo/tasks/main.yml roles/tempo/defaults/main.yml >= 2` passes (5 total).
- **Committed in:** Task 1 commit `eec3586`.

**5. [Rule 2 - Missing Critical] Pinned `curlimages/curl` via Tempo-prefixed defaults vars (not hardcoded)**
- **Found during:** Task 2 (writing verify.yml).
- **Issue:** The plan's verify.yml text hardcoded `curlimages/curl:8.10.1` inline. Same OPS-01-spirit issue as Loki Deviation 5 -- operator can't override without editing the role.
- **Fix:** Surfaced as `tempo_curl_image` / `tempo_curl_image_tag` defaults; verify.yml consumes them. Operator override path: set the variable in `inventory/<env>/group_vars/all/tempo.yml`.
- **Files modified:** `roles/tempo/defaults/main.yml`, `roles/tempo/tasks/verify.yml`.
- **Verification:** Image+tag pair no longer hardcoded in task files; verify.yml renders the correct image+tag from defaults.
- **Committed in:** Task 1 commit `eec3586` (defaults) + Task 2 commit `8920cea` (verify.yml consumption).

---

**Total deviations:** 5 documented (3 plan-text contradictions / lint fixes resolved by intent, 2 plan-extending OPS-01 / W2 hygiene fixes).
**Impact on plan:** All five are minor / surface-level. No scope creep. No architectural change. The role still mirrors the canonical `roles/loki/` template verbatim; the Phase-2 wave-1 wiring shape is preserved (`minio -> loki -> tempo`); all five port-acceptance gates pass on `roles/tempo/`; `ansible-lint roles/tempo/` passes the production profile cleanly.

## Issues Encountered

- **In-network end-to-end test was NOT executed during plan execution.** Same situation as Plan 02-01: the executor runs on Rock's workstation, not on the homelab Docker target host. The end-to-end test requires (a) the `telemetron` network created on the target, (b) the Phase 1 MinIO container running with the `tempo-traces` bucket bootstrapped, (c) Plan 02-01's Loki container also running, (d) a populated `vault.yml` with the new D-27 keys. Local workstation has Docker (the image probe ran) but no populated vault and not the homelab MinIO state. The exact run sequence for human verification is documented below under "User Setup Required" / will be referenced in `02-USER-SETUP.md` (Phase 2 file already exists; appended in this plan's metadata commit step).
- **`ansible-playbook --syntax-check` PASSED** with the tempo role wired into `deploy_docker.yml` (alongside minio + loki), confirming the role is structurally valid Ansible (modules resolve, tags parse, includes load).
- **`ansible-lint roles/tempo/`** passes the **production** profile with 0 failures and 0 warnings.
- **No carry-forward blockers from Plan 02-01.** The canonical-template pattern works as designed for the second Phase-2 backend.

## Authentication Gates

None. No auth interactions needed (vault password is provided at operator playbook-run time on the target host, not during role port development).

## User Setup Required

External services require manual configuration on the homelab target host. Operators should:

1. Extend `inventory/example-homelab/group_vars/all/vault.yml` with `vault_tempo_s3_access_key` and `vault_tempo_s3_secret_key` (aliases to existing `vault_minio_root_user` / `vault_minio_root_password` per D-27). Re-encrypt with `ansible-vault encrypt`.
2. Run the end-to-end deploy + verify:
   ```bash
   ansible-playbook -i inventory/example-homelab \
                    playbooks/deploy_docker.yml \
                    --tags tempo --ask-vault-pass
   ```
3. Verify alt-port binding in the rendered config (the verify task already runs the synthetic push; this is a belt-and-suspenders check):
   ```bash
   docker exec tempo cat /etc/tempo.yaml | grep -E 'endpoint:.*"0.0.0.0:1431[78]"'
   # Expects: both 14317 and 14318 lines
   docker exec tempo cat /etc/tempo.yaml | grep -E '"0\.0\.0\.0:431[78]"' || echo "OK: no standard OTLP ports in tempo config"
   docker exec tempo cat /etc/tempo.yaml | grep -E 'block_retention:|compacted_block_retention:' | wc -l   # Expects: 2
   docker exec tempo cat /etc/tempo.yaml | grep -c 'remote_write'                                          # Expects: 0
   ```
4. Re-run idempotency check:
   ```bash
   ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags tempo --ask-vault-pass
   # Expects PLAY RECAP: changed=0
   ```

## Next Phase Readiness

- **Plan 02-03 (Mimir)** -- ready. Pattern is fully established now. Mimir's port differs from Loki + Tempo in:
  - Image pin: `grafana/mimir:3.0.6`
  - gRPC port: `9097` (D-28 -- Loki keeps 9095, Tempo took 9096, Mimir takes 9097)
  - Three distinct S3 buckets: `mimir-blocks`, `mimir-ruler`, `mimir-alerts` (`alertmanager_storage` + `ruler_storage` are S3-backed, not filesystem)
  - `query_store_after: 12h` + `bucket_store.sync_interval: 5m` + `compactor.cleanup_interval: 5m` (D-36 / Pitfall 11)
  - `multitenancy_enabled: false` + `auth.no_auth_tenant: anonymous` (D-26)
  - Mimir S3 endpoint format: `minio:9000` (no scheme -- same as Tempo, unlike Loki)
  - Mimir is also distroless -- conditional healthcheck pattern from this plan reuses verbatim. RESEARCH Finding 6 indicates Mimir 3.0.6 also lacks a native `-health` flag (planner should probe at plan-write time -- the same `docker run --rm grafana/mimir:3.0.6 -help | grep -i health` shell pattern).
- **No blockers carried forward.** The canonical-template pattern + conditional-healthcheck pattern + dual-knob-retention pattern all proven on a second backend.

---

## Self-Check: PASSED

All claimed files exist on disk and all task commits are in git history:

- `roles/tempo/defaults/main.yml` -- FOUND
- `roles/tempo/meta/main.yml` -- FOUND
- `roles/tempo/handlers/main.yml` -- FOUND
- `roles/tempo/tasks/main.yml` -- FOUND
- `roles/tempo/tasks/verify.yml` -- FOUND
- `roles/tempo/templates/tempo.yaml.j2` -- FOUND
- `roles/tempo/README.md` -- FOUND (294 lines)
- `inventory/example-homelab/group_vars/all/tempo.yml` -- FOUND
- `inventory/example-homelab/group_vars/all/vault.yml.example` -- MODIFIED (D-27 tempo alias keys appended)
- `playbooks/deploy_docker.yml` -- MODIFIED (tempo role wired after loki)
- `roles/README.md` -- MODIFIED (tempo status flipped to [x])
- Task 1 commit `eec3586` -- FOUND in git log
- Task 2 commit `8920cea` -- FOUND in git log
- Task 3 commit `df7fe87` -- FOUND in git log

`ansible-lint roles/tempo/` (production profile): 0 failures, 0 warnings.
`ansible-playbook --syntax-check -i inventory/example-homelab playbooks/deploy_docker.yml` (with tempo wired): exits 0.

Grep gate roll-up on code/config:
- `grep -riE 'inspq|qc\.ca|montreal|...' roles/tempo/defaults/ roles/tempo/meta/ roles/tempo/handlers/ roles/tempo/tasks/ roles/tempo/templates/ inventory/example-homelab/group_vars/all/tempo.yml playbooks/deploy_docker.yml` -- ZERO matches.
- `grep -rPn '[^\x00-\x7F]' roles/tempo/ inventory/example-homelab/group_vars/all/tempo.yml` -- ZERO non-ASCII characters.
- `grep -rE ':latest' roles/tempo/` -- ZERO floating-tag references.
- `grep -c 'remote_write' roles/tempo/templates/tempo.yaml.j2` -- ZERO (D-38 path b confirmed).

---

*Phase: 02-telemetry-backends*
*Completed: 2026-05-17*
