# Phase 2: Telemetry Backends - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Port the three telemetry backends — Loki, Tempo, and Mimir — as Ansible roles deployed via Docker on the single homelab host, each in monolithic mode (`-target=all`), each backed by the MinIO buckets bootstrapped in Phase 1 (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`). Each role mirrors the canonical patterns established by the Phase 1 `minio` role port (D-10a HEALTHCHECK poll before any downstream task, W6 single-handler restart, W7 `changed_when: false` on verify tasks, W8 explicit in-network verify step, OPS-03 README schema). Tempo's OTLP receivers move off the standard `:4317`/`:4318` to internal-only alt ports (`:14317`/`:14318`) so the Phase 3 OTel Collector can claim the standard pair.

Three role ports + three playbook wirings + cross-cutting Phase-1-pattern carry-forward. Producers (Prometheus, OTel, Fluent Bit) are Phase 3's job; Grafana datasource provisioning is Phase 5's; Phase 2 stops at "the backends are alive, reachable on the `telemetron` network, and storing objects in the right MinIO buckets."

</domain>

<decisions>
## Implementation Decisions

### Plan structure (D-22, D-23, D-24)

- **D-22:** **Three plans, one per role, in LGTM/storage-bucket order.** `02-01-PLAN.md` ports `roles/loki/`; `02-02-PLAN.md` ports `roles/tempo/`; `02-03-PLAN.md` ports `roles/mimir/`. Mirrors Phase 1's 01-03 minio-as-canonical-template shape. Each plan is independent — backends do not depend on each other, only on Phase-1 MinIO buckets.
- **D-23:** **Each plan wires its own role into `playbooks/deploy_docker.yml`** as the final task of that plan. 02-01 appends `role: loki` after `role: minio`; 02-02 appends `role: tempo`; 02-03 appends `role: mimir`. Mirrors Phase 1 where 01-03 appended `role: minio`. Each plan is end-to-end shippable in isolation; the playbook stays runnable at every commit.
- **D-24:** **Each role gets one tag matching its name** (`--tags loki`, `--tags tempo`, `--tags mimir`). Sub-tags only if reload-without-restart becomes useful (carryover from Phase 1 D-9 "Claude's Discretion" — granularity stays per-role for M1).

### Project expectation: opinionated improvements, not mechanical translation (D-25 — explicit operator instruction)

- **D-25:** **Each role port is an opinionated improvement pass, not a mirror-translate of the INSPQ source.** Researcher and planner are expected to (a) audit the upstream INSPQ role for ported-as-is INSPQ-isms beyond the grep-gate noise (hardcoded paths, default values that only made sense in a Quebec-gov context, INSPQ-specific operational assumptions baked into config); (b) call out missing pitfall guards from PITFALLS.md that the upstream didn't address; (c) propose better defaults where the upstream choice was clearly INSPQ-internal-driven; (d) document each meaningful deviation from upstream in the plan's "Deviations from upstream" section. Operator explicitly requested this expectation be carried into Phase 2 onward — it's not implied by the port checklist, it's required.

### Tenancy (D-26)

- **D-26:** **Multitenancy disabled in both Loki and Mimir.** Loki: `auth_enabled: false` (no `X-Scope-OrgID` header anywhere; all data lives in tenant `fake`). Mimir: `multitenancy_enabled: false`. Producers (Phase 3 Prometheus `remote_write` to Mimir, Phase 3 OTel/Fluent Bit to Loki) need no tenant config. Documented in each role's README under "Modes" alongside the "monolithic only" note. Adding a second tenant in v2 will require flipping the flag + adding the header on every producer config — explicitly an v2 hardening choice, not a v1 simplification debt.

### S3 vault plumbing (D-27)

- **D-27:** **Per-backend vault key aliases pointing at MinIO root creds for now.** Each backend role declares its own vault key surface:
  - `roles/loki/templates/loki.yaml.j2` consumes `{{ vault_loki_s3_access_key }}` / `{{ vault_loki_s3_secret_key }}` *(renamed to `{{ loki_s3_access_key }}` / `{{ loki_s3_secret_key }}` in Phase 4.1 / D-90)*
  - `roles/tempo/templates/tempo.yaml.j2` consumes `{{ vault_tempo_s3_access_key }}` / `{{ vault_tempo_s3_secret_key }}` *(renamed to `{{ tempo_s3_access_key }}` / `{{ tempo_s3_secret_key }}` in Phase 4.1 / D-90)*
  - `roles/mimir/templates/mimir.yaml.j2` consumes `{{ vault_mimir_s3_access_key }}` / `{{ vault_mimir_s3_secret_key }}` *(renamed to `{{ mimir_s3_access_key }}` / `{{ mimir_s3_secret_key }}` in Phase 4.1 / D-90)*

  All six keys live in `inventory/example-homelab/group_vars/all/vault.yml.example` with values `"{{ vault_minio_root_user }}"` / `"{{ vault_minio_root_password }}"` so they alias to the Phase-1 MinIO root creds at variable-resolution time. When a future hardening phase splits MinIO into per-backend users with bucket-scoped IAM policies, only `vault.yml` changes — role templates do not. Cheap forward-compat, zero cost today, no breaking change at hardening time. OPS-02 (`vault_<role>_<purpose>` naming convention) preserved per backend. *(Phase 4.1 / D-90 renamed the file to `secrets.yml.example` and dropped the `vault_` prefix from all 8 keys -- the alias semantics + cheap forward-compat unchanged; only the naming convention evolved.)*

### Port allocation (D-28, D-29, D-30, D-31)

- **D-28:** **gRPC clash resolution: Loki :9095, Tempo :9096, Mimir :9097, all explicitly pinned.** All three backends default their gRPC port to `:9095`; on a single host they collide. Loki keeps `:9095` because most Loki docs/examples assume it AND Loki's query-frontend↔querier path uses gRPC even in monolithic mode. Tempo's `server.grpc_listen_port: 9096` set in its config template. Mimir's `server.grpc_listen_port: 9097` set in its config template. **Every backend explicitly pins its gRPC port — no implicit defaults consumed** (so a future Loki/Tempo/Mimir image bump that changes default ports doesn't silently break the stack).
- **D-29:** **Tempo OTLP alt ports `:14317`/`:14318` explicitly pinned** (BACK-05 + lock-in for OTel Collector on `:4317`/`:4318` in Phase 3). `roles/tempo/defaults/main.yml` surfaces `tempo_otlp_grpc_port: 14317` and `tempo_otlp_http_port: 14318` as overridable knobs but defaults stay. **OTLP-internal-only:** these ports are NOT host-published and NOT operator-facing; they exist for Phase-3 OTel Collector → Tempo traffic on the `telemetron` Docker bridge.
- **D-30:** **All three backends default `<role>_publish_host: false`** (no host port publish, identical to Phase 1 MinIO D-13). Operator access via `ssh -L 3100:localhost:3100 host` (Loki HTTP), `ssh -L 3200:localhost:3200 host` (Tempo HTTP), `ssh -L 9009:localhost:9009 host` (Mimir HTTP). Each role's README ships an "Operator access" section with the matching `ssh -L` examples.
- **D-31:** **Full Phase-2 port matrix** (all container-side; host-publish defaults to false everywhere):
  - Loki: HTTP `:3100`, gRPC `:9095`
  - Tempo: HTTP `:3200`, gRPC `:9096`, OTLP gRPC `:14317`, OTLP HTTP `:14318`
  - Mimir: HTTP `:9009`, gRPC `:9097`
  All explicitly pinned in each role's `defaults/main.yml` and `templates/<backend>.yaml.j2`.

### Verification surface (D-32)

- **D-32:** **Each role's final task is an in-network one-shot verify container** that pushes a synthetic payload to the backend's API (over `telemetron` bridge DNS — e.g. `http://loki:3100/loki/api/v1/push`), then runs a one-shot `minio/mc` container to assert objects landed in the matching MinIO bucket. Mirrors the Phase 1 `minio` role's `mc ls --json` verify step (W8 pattern). Failure of either push or assertion fails the playbook. **Zero host-publish required** for verification — matches the no-host-publish default (D-30). The one-shot containers use `auto_remove: true` and `changed_when: false` (W7).

### Retention defaults (D-33, D-34, D-35)

- **D-33:** **Loki: `loki_retention_period: 14d`** matching the `telemetron_default_log_retention` placeholder in `storage.yml`. Compactor `retention_enabled: true`, `retention_delete_delay: 2h` (default), `retention_delete_worker_count` per Loki upstream default. BACK-02 knob surfaced in `roles/loki/defaults/main.yml` AND mirrored into `inventory/example-homelab/group_vars/all/loki.yml` so operators see the override path. Documented in `roles/loki/README.md`.
- **D-34:** **Tempo dual-knob retention (Pitfall 10):** `tempo_block_retention: 168h` (7d) + `tempo_compacted_block_retention: 1h`. Both knobs MUST be explicitly set — single-value retention silently fails per Pitfall 10. BACK-03 surfaced in `roles/tempo/defaults/main.yml`. Inline comment in the template cites Pitfall 10 for downstream readers. Matches `telemetron_default_trace_retention: 7d` placeholder.
- **D-35:** **Mimir: `mimir_compactor_blocks_retention_period: 30d`** matching `telemetron_default_metric_retention: 30d` placeholder. BACK-04 surfaced in `roles/mimir/defaults/main.yml`.

### Mimir limits & monolithic tuning (D-36)

- **D-36:** **Mimir limits + monolithic-mode tuning per PITFALLS.md guidance, all explicit in `roles/mimir/defaults/main.yml`:**
  - `limits.max_global_series_per_user: 500000` (Pitfall 3)
  - `limits.max_global_series_per_metric: 100000` (Pitfall 3)
  - `query_store_after: 12h` (Pitfall 11 — longer than block-lands-in-storage; shorter than Prometheus local retention which Phase 3 sets to 24h+)
  - `blocks_storage.bucket_store.sync_interval: 5m` (Pitfall 11)
  - `compactor.cleanup_interval: 5m` (Pitfall 11)
  - All five knobs inline-commented with the matching `.planning/research/PITFALLS.md` § reference.

### Loki limits & label discipline (D-37)

- **D-37:** **Loki `limits_config` ships with PITFALLS-aligned defaults in Phase 2:**
  - `max_streams_per_user: 5000` (Pitfall 4)
  - `max_label_value_length: 2048` (Pitfall 4)
  - `max_label_names_per_series: 15` (Pitfall 4)
  - All three knobs inline-commented with the matching PITFALLS § reference.
  Fluent Bit's complementary label allowlist (`{job, host, service, env, level}`) ships in **Phase 3** when the `fluentbit` role lands — not Phase 2. Loki rejects loudly when discipline breaks; Fluent Bit's allowlist is the source-side complement.

### Tempo metrics-generator (D-38 — flagged for research validation)

- **D-38:** **Enable the metrics-generator processor in Tempo, but NO `remote_write` to Mimir.** Intent: generate service-graph + span metrics inside Tempo without coupling Tempo's startup to Mimir's availability (which would create a cross-backend cold-start dependency we don't want in Phase 2). **Research must validate the configuration shape for Tempo 2.10.5** — metrics-generator's modern config typically requires `metrics_generator.storage.remote_write` configured OR a documented "local-only" path (Tempo 2.10 added `metrics_generator.storage.path` as a local WAL). If processor-only-no-remote-write turns out to be unsupported in 2.10.5, the planner falls back to one of: (a) defer metrics-generator entirely (matches CLAUDE.md "ship monolithic only" simplicity), (b) enable processor + local-WAL-only-no-remote-write (preferred if supported), (c) enable processor + remote_write to Mimir (couples Tempo→Mimir at startup; least preferred). **Research note:** consult `https://grafana.com/docs/tempo/latest/metrics-generator/` against Tempo 2.10.5 specifically. Default in `roles/tempo/defaults/main.yml` controlled by `tempo_metrics_generator_enabled: true` knob.

### Schema, working directory, and other Loki/Mimir/Tempo specifics (D-39)

- **D-39:** **Claude's Discretion within research-validated boundaries:**
  - Loki `schema_config`: TSDB (current default since Loki 2.8+; supersedes BoltDB-shipper). Research confirms Loki 3.7.2 schema_config shape.
  - Loki `compactor_working_directory: /var/loki/compactor` (Pitfall 12 — explicit path so it lives on the persistent volume).
  - Mimir `alertmanager_storage` + `ruler_storage`: S3-backed via `mimir-alerts` and `mimir-ruler` buckets (BACK-04 mandates three distinct buckets; filesystem alternative rejected because Mimir refuses to start sharing prefixes).
  - Tempo `storage.trace.backend: s3` pointing at `tempo-traces` (no filesystem fallback in M1).
  - S3 endpoint conventions: each backend's S3 config uses `http://minio:9000` (Docker DNS on `telemetron`), region `us-east-1` (MinIO ignores but the S3 client demands a value), `s3forcepathstyle: true` (MinIO requires path-style not vhost-style).

### Claude's Discretion

- Exact Jinja iteration patterns for nested config sections (D-20 sorted-keys rule applies; ordering within already-sorted dicts is Claude's call).
- Per-role healthcheck timing (`interval`, `timeout`, `retries`) — start from each upstream image's HEALTHCHECK conventions; tune only if startup races appear.
- Memory limits per backend container — start from PITFALLS sizing (Loki 1-2GB, Mimir 2-4GB, Tempo 1GB) and let operator override.
- Loki `chunk_target_size`, `chunk_idle_period` — homelab defaults per PITFALLS "Performance Traps" table (chunk_target_size: 1572864).
- Tempo `compactor.compaction.block_ranges_period` — monolithic-mode appropriate default.
- The exact in-network verify payload shape per backend (synthetic log line content, trace structure, metric series name) — researcher proposes, planner specifies.
- README "Improvements over upstream INSPQ" sub-section per role (D-25) — list shape proposed by planner after researcher's audit pass.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project framing & scope
- `.planning/PROJECT.md` — Vision, constraints, Tech Stack section (CLAUDE.md mirrors this and includes the full per-component pin table for Loki 3.7.2 / Tempo 2.10.5 / Mimir 3.0.6).
- `.planning/REQUIREMENTS.md` §"Backends (BACK)" — Phase 2 REQ-IDs (BACK-01..BACK-05) with full acceptance text.
- `.planning/ROADMAP.md` §"Phase 2: Telemetry Backends" — Goal, success criteria (5 of them), requirement mapping.

### Phase 1 decisions that propagate forward (read in full before Phase 2 planning)
- `.planning/phases/01-foundation-storage/01-CONTEXT.md` — D-04 (network in pre_tasks), D-06 (no shared base role), D-09 (root creds reused), D-10a (`docker_container_info` HEALTHCHECK poll), D-12..D-14 (no host publish), D-15..D-18 (inventory + volumes + config layout), D-19..D-21 (handler restart, sorted-keys Jinja, grep gates).
- `roles/minio/` (entire role) — canonical template. Phase 2 roles mirror its layout (`defaults/main.yml`, `tasks/main.yml`, `tasks/bootstrap.yml`-style verify task, `handlers/main.yml`, `templates/`, `meta/main.yml`, `vars/`, `README.md`).
- `roles/README.md` §"Port process" — grep gates, image-pin gate, vault gate, idempotency gate, healthcheck+restart gate. Every Phase 2 role passes all five.

### Research backing for this phase
- `.planning/research/PITFALLS.md` §"Pitfall 4: Loki label discipline" — Backing for D-37.
- `.planning/research/PITFALLS.md` §"Pitfall 10: Tempo + MinIO retention silently doing nothing" — Backing for D-34 (Tempo dual-knob).
- `.planning/research/PITFALLS.md` §"Pitfall 11: Mimir compactor + ingester block consistency on a single host" — Backing for D-36 (Mimir monolithic tuning).
- `.planning/research/PITFALLS.md` §"Pitfall 12: Loki compactor marker-file loss on container recreate" — Backing for D-39 (Loki `compactor_working_directory` + Phase-1 D-17 one-volume rule).
- `.planning/research/PITFALLS.md` §"Pitfall 3: High-cardinality label explosion" — Backing for D-36 Mimir limits.
- `.planning/research/PITFALLS.md` §"Integration Gotchas" — `Prometheus → Mimir` (local retention vs `query_store_after`); informs Phase 3 but constrains D-36 here.
- `.planning/research/PITFALLS.md` §"Performance Traps" — Loki chunk file proliferation guidance (D-39 chunk_target_size).
- `.planning/research/PITFALLS.md` §""Looks Done But Isn't" Checklist" — Per-backend acceptance items (Loki marker persistence, Mimir remote_write reachability, Tempo retention bucket-size stability).
- `.planning/research/STACK.md` — Image pin sources (Loki 3.7.2, Tempo 2.10.5, Mimir 3.0.6); monolithic-mode CLI flags (`-target=all`); per-backend port matrix.
- `.planning/research/FEATURES.md` — Tempo metrics-generator feature shape (informs D-38 research validation).
- `.planning/research/ARCHITECTURE.md` — Signal flow apps → OTel → backends; storage layout per backend.

### Upstream INSPQ source-of-truth (for porting + improvement audit per D-25)
- `~/git/inspq/ansible/loki/` (operator workstation) — Source role for `02-01-PLAN.md`; audit for INSPQ-isms beyond the grep gate.
- `~/git/inspq/ansible/tempo/` — Source role for `02-02-PLAN.md`.
- `~/git/inspq/ansible/mimir/` — Source role for `02-03-PLAN.md`.

### Ansible module & collection documentation
- [community.docker.docker_container module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_module.html) — Primary module per role (mirrors `roles/minio/`).
- [community.docker.docker_container_info module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_container_info_module.html) — D-10a HEALTHCHECK poll pattern.
- [community.docker.docker_volume module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_volume_module.html) — Per-backend `telemetron_<role>_data` volumes.

### Upstream backend docs (consulted by research per D-38 + per-role specifics)
- [Grafana Loki monolithic mode (deployment-modes)](https://grafana.com/docs/loki/latest/get-started/deployment-modes/) — `-target=all` flag, single-binary architecture, S3 storage config shape.
- [Loki schema_config (TSDB)](https://grafana.com/docs/loki/latest/configure/) — TSDB index schema (Loki 2.8+ default; replaces BoltDB-shipper).
- [Loki retention](https://grafana.com/docs/loki/latest/operations/storage/retention/) — Compactor retention configuration.
- [Grafana Tempo monolithic deployment](https://github.com/grafana/tempo/tree/main/example/docker-compose/single-binary) — Single-binary example config (Tempo 2.10).
- [Tempo configuration reference](https://grafana.com/docs/tempo/latest/configuration/) — Receivers, compactor, metrics-generator (D-38 research).
- [Tempo metrics-generator](https://grafana.com/docs/tempo/latest/metrics-generator/) — Service-graph + span-metrics generator configuration (D-38 — verify the no-remote-write path on 2.10.5).
- [Grafana Mimir monolithic mode](https://grafana.com/docs/mimir/latest/references/architecture/deployment-modes/) — `-target=all` flag.
- [Mimir architecture overview](https://grafana.com/docs/mimir/latest/get-started/about-grafana-mimir-architecture/) — Port `:9009` HTTP; default gRPC `:9095` (D-28 clash source).
- [Mimir multitenancy](https://grafana.com/docs/mimir/latest/configure/about-tenant-ids/) — `multitenancy_enabled: false` shape (D-26).
- [Mimir blocks storage](https://grafana.com/docs/mimir/latest/configure/configure-object-storage-backend/) — S3 endpoint config; alertmanager_storage + ruler_storage shape (D-39).
- [MinIO S3 path-style requirement](https://min.io/docs/minio/linux/integrations/aws-cli-with-minio.html) — `s3forcepathstyle: true` (D-39).

### Locked naming normalizations (Phase 1 baseline, carried forward)
- git commit `ba836d2` — `alert_manager` → `alertmanager`, `postgresql-docker` → `postgres`, etc.
- Phase 1 conventions: vault keys `vault_<role>_<purpose>`, volumes `telemetron_<role>_data`, config dirs `/opt/telemetron/<role>/`, tags one-per-role. *(Vault-key prefix dropped in Phase 4.1 / D-90 — now role-namespaced `<role>_<purpose>`.)*

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`roles/minio/`** — Canonical role template established in Phase 1. Every layout choice (directory shape, defaults file structure, handler convention, README schema, verify-via-one-shot-container pattern) propagates verbatim to Loki/Tempo/Mimir. Researcher AND planner should read this role fully before producing the Phase 2 plan.
- **`roles/minio/tasks/bootstrap.yml`** — Specifically: the D-10a `docker_container_info` HEALTHCHECK poll pattern is the template for "wait for the backend to be ready before pushing the verify payload." Every Phase 2 role mirrors this shape.
- **`roles/minio/handlers/main.yml`** — Single-handler restart pattern (W6) — every Phase 2 role has one handler that runs `docker restart <name>` on config change; never `state: restarted`.
- **`roles/minio/README.md`** — README schema template (Variables / Vault keys / Tags / Modes / Volumes / Healthcheck / Security model / Idempotency / Port-acceptance gates / Deprecation notes / Bring your own X). Each Phase 2 README follows the same shape.
- **`inventory/example-homelab/group_vars/all/storage.yml`** — `telemetron_minio_buckets` (consumed for endpoint config), `telemetron_default_log_retention` (consumed by Loki D-33), `telemetron_default_metric_retention` (D-35), `telemetron_default_trace_retention` (informs D-34). Phase 2 adds `loki.yml`, `tempo.yml`, `mimir.yml` per-role files.
- **`inventory/example-homelab/group_vars/all/vault.yml.example`** — Phase-1 placeholder for `vault_minio_root_user` + `vault_minio_root_password`. Phase 2 extends this file with six aliased keys per D-27 (`vault_loki_s3_access_key`/`_secret_key`, same for tempo and mimir). *(File renamed to `secrets.yml.example` and all 8 keys renamed to unprefixed form in Phase 4.1 / D-90.)*
- **`inventory/example-homelab/group_vars/all/network.yml`** — `telemetron_network`, `telemetron_publish_default`, `telemetron_tz`. Consumed by every Phase 2 role's container task.
- **`playbooks/deploy_docker.yml`** — Has the pre_task that creates the `telemetron` network and a comment block listing Phase 2-6 roles in dependency order. Phase 2 plans append role entries below `role: minio` per D-23.
- **`ansible.cfg`** at project root — `roles_path=roles` already established in Phase 1; no Phase 2 work needed here.

### Established patterns (mirrored from Phase 1; planner enforces in Phase 2)
- **Role layout** — `defaults/main.yml`, `tasks/main.yml`, `tasks/<verify_step>.yml`, `handlers/main.yml`, `templates/<file>.j2`, `meta/main.yml`, `vars/` (where needed), `README.md`. Standard Ansible.
- **Image pin discipline (OPS-01)** — Image+tag pair in `defaults/main.yml` with inline comment linking the upstream release notes. Loki `grafana/loki:3.7.2`, Tempo `grafana/tempo:2.10.5`, Mimir `grafana/mimir:3.0.6`.
- **Vault reference convention (OPS-02)** — `{{ vault_<role>_<purpose> }}`. Phase 2 adds six new keys per D-27. *(Convention changed to role-namespaced `<role>_<purpose>` in Phase 4.1 / D-90.)*
- **Volume naming (D-16)** — `telemetron_<role>_data` named Docker volume. Phase 2 adds three: `telemetron_loki_data`, `telemetron_tempo_data`, `telemetron_mimir_data`.
- **Config bind-mount (D-18)** — Host `/opt/telemetron/<role>/<file>` → container canonical path read-only.
- **Restart-by-handler (D-19, W6)** — Handler runs `docker restart <name>`, never `state: restarted`.
- **Sorted-keys Jinja iteration (D-20)** — `{% for k in d.keys() | sort %}` in every templated config.
- **In-network verify one-shot (W8)** — Final task is a one-shot container on the `telemetron` network that pushes a synthetic payload and asserts MinIO bucket landed (D-32).
- **Grep gates per role (D-21)** — `grep -riE '(inspq|qc\.ca|montreal|québec|francais|french|/srv/nfs/inspq|vault_inspq)' roles/<name>/` returns zero; `grep -rPn '[^\x00-\x7F]' roles/<name>/` returns zero.
- **No-host-publish default (D-12..D-14, D-30)** — `<role>_publish_host: false` in `inventory/example-homelab/group_vars/all/<role>.yml`.

### Integration points
- **`playbooks/deploy_docker.yml`** — Each Phase 2 plan appends one role entry. Final shape after Phase 2: `pre_tasks: [network] → minio → loki → tempo → mimir`. Subsequent phases append on top.
- **`inventory/example-homelab/group_vars/all/`** — Phase 2 adds three per-role files (`loki.yml`, `tempo.yml`, `mimir.yml`) + extends `vault.yml.example` with six S3 alias keys.
- **`roles/README.md`** — Update the role-status table (rows for loki/tempo/mimir) as each plan completes — port-acceptance gates each role passes.
- **`/opt/telemetron/{loki,tempo,mimir}/`** — Three new host-side config trees created by each role's first task.
- **MinIO buckets** — Pre-existing from Phase 1 (`loki-chunks`, `tempo-traces`, `mimir-blocks`, `mimir-ruler`, `mimir-alerts`). Phase 2 backends consume them; Phase 2 does NOT create buckets (Phase 1 owns that).

</code_context>

<specifics>
## Specific Ideas

- **Opinionated improvement audit per D-25.** The upstream INSPQ stack works for INSPQ; that doesn't mean its defaults are right for "clone, edit hostname, run playbook on a homelab Docker host." Each Phase 2 role plan should include a "Deviations from upstream" section in the role README, calling out: (a) which INSPQ-isms beyond the grep gate were dropped (hardcoded hostnames, France/Quebec timezone, internal CA refs, custom NFS paths); (b) which pitfall guards from PITFALLS.md the upstream did not have that this port adds; (c) which defaults differ from upstream and why (e.g. `query_store_after: 12h` for homelab vs whatever INSPQ used for a multi-host deploy).
- **Tempo metrics-generator (D-38) is research-flagged.** Research must verify the exact config shape for Tempo 2.10.5 — the planner must NOT assume processor-only-no-remote-write is supported until research confirms. Three fallback paths documented in D-38; planner picks one based on research findings.
- **"No INSPQ-ism beyond grep gate" is a Rock-explicit expectation.** Phase 1 grep gate catches obvious-string leftovers. Phase 2 audit (D-25) catches the rest — variable values that happen to be Quebec-internal hostnames/CAs/paths, defaults tuned for INSPQ scale, comments alluding to INSPQ runbooks. Document each finding per role.
- **The "second-run-shows-changed=0" gate per OPS-04 applies to every role.** Phase 1 proved this on minio (via `ansible.cfg` + sorted-keys Jinja + handler-restart). Phase 2 inherits the discipline; each plan's acceptance criteria includes the double-run idempotency check.
- **Verification is in-network, not from the control host.** Mirrors minio's `mc ls --json` pattern. The Phase 2 verify step is the per-role smoke; the M1 final smoke (Phase 6, OPS-07) is the end-to-end push-through-OTel test.
- **gRPC port allocation (D-28) is an architecture call, not a docs note.** Picking Loki 9095 / Tempo 9096 / Mimir 9097 propagates to Phase 3 Prometheus scrape config (it scrapes Mimir's `:9097/metrics` for self-metrics) and Phase 5 Grafana datasource health checks (which use gRPC for Tempo).

</specifics>

<deferred>
## Deferred Ideas

### Out of M1 (future milestones)
- **Per-backend MinIO access keys** — D-27 reuses root creds via vault aliases for now. Splitting into per-backend MinIO users with bucket-scoped IAM policies reduces blast radius on cred leak. Hardening phase candidate (queued from Phase 1 D-09; D-27 makes the migration cheaper by introducing the per-backend vault key surface today).
- **Distributed/scalable-single-binary modes** — Loki/Tempo/Mimir all support beyond-monolithic deployments. v2 territory (PROJECT.md "Out of Scope" already lists this).
- **MinIO replacement (Garage / SeaweedFS)** — Already deferred from M1. When MinIO swaps out, Phase 2's S3 endpoint configs in each role template will need updating; the per-backend vault key surface (D-27) makes credential migration cheap.
- **Multi-tenant Loki/Mimir** — D-26 disables. Adding tenants in v2 means flipping the flag + every producer needs the `X-Scope-OrgID` header. Document the path in Phase 6's `docs/architecture.md` for future-Rock.
- **Tempo metrics-generator full integration with remote_write to Mimir** — If D-38's processor-only-no-remote-write path isn't viable for 2.10.5, OR if Rock decides post-M1 he wants the Grafana service-graph view, enabling `metrics_generator.storage.remote_write` to Mimir lands in a hardening phase. Couples Tempo→Mimir at startup but enables the service-graph feature.
- **HAProxy in front of distributed backends** — Already deferred per PROJECT.md; relevant when distributed mode lands.
- **Per-backend WAL tuning, ingester memory limits** — Defaults from PITFALLS guidance are M1-sufficient for homelab; production tuning is a later concern.

### Out of Phase 2 (lands in Phase 3+)
- **Fluent Bit Loki label allowlist (`{job, host, service, env, level}`)** — Phase 3 fluentbit role port (D-37 splits the discipline: Loki-side limits in Phase 2, source-side allowlist in Phase 3).
- **Prometheus `metric_relabel_configs` to drop high-cardinality labels (Pitfall 3)** — Phase 3 prometheus role; Phase 2 Mimir limits are the safety net.
- **OTel Collector pipeline order + GOMEMLIMIT (Pitfall 5)** — Phase 3 opentelemetry role.
- **Synthetic push via OTel Collector** — Phase 2 verifies via direct API push. End-to-end OTel push smoke is Phase 6 OPS-07.

### Reviewed Todos (not folded)
None — `gsd-tools todo match-phase 2` returned zero matches.

</deferred>

---

*Phase: 02-telemetry-backends*
*Context gathered: 2026-05-17*
