# Phase 2: Telemetry Backends - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `02-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 02-telemetry-backends
**Areas discussed:** Plan breakdown, Multitenancy + S3 vault plumbing, Port allocation + verification surface, Retention + limits + metrics-generator

---

## Plan breakdown

### Q1: How should Phase 2 be split into plans?

| Option | Description | Selected |
|--------|-------------|----------|
| Three plans, one per role | 02-01 loki / 02-02 tempo / 02-03 mimir. Mirrors Phase 1's 01-03 per-role-plan shape. Each plan independent. | ✓ |
| Two plans — backends + verification | All three role ports as one plan + cross-backend verify plan. | |
| One combined plan | Single 02-01 covers all three roles. Weaker per-role review granularity. | |
| Three plans + non-alphabetical order | Three per-role plans in a specific order other than LGTM. | |

**User's choice:** Three plans, one per role (Recommended).
**Notes:** No deviation requested; planner uses this shape directly.

---

### Q2: What order for the three plans (and matching playbook ordering)?

| Option | Description | Selected |
|--------|-------------|----------|
| Loki, Tempo, Mimir | Matches LGTM convention + ROADMAP narrative + storage.yml bucket order. | ✓ |
| Alphabetical: Loki, Mimir, Tempo | Strict alphabetical. | |
| By pitfall depth: Loki, Mimir, Tempo | Loki first (markers/labels), Mimir second (consistency/cardinality), Tempo last (simplest). | |

**User's choice:** Loki, Tempo, Mimir (Recommended).
**Notes:** 02-01 loki, 02-02 tempo, 02-03 mimir.

---

### Q3: How does each plan wire its role into the playbook orchestrator?

| Option | Description | Selected |
|--------|-------------|----------|
| Each plan wires its own role | 02-01 appends `role: loki`; 02-02 appends `role: tempo`; 02-03 appends `role: mimir`. End-to-end shippable per plan. | ✓ |
| Wire all three at end of Phase 2 | Roles built in roles/ but playbook updated only at end of 02-03. | |
| Wire-and-uncomment pattern | Pre-populate commented entries; each plan uncomments its own. | |

**User's choice:** Each plan wires its own role (Recommended).
**Notes:** Matches Phase 1 where 01-03 appended `role: minio` as part of itself.

---

## Multitenancy + S3 vault plumbing

### Q4: Tenancy model for Loki and Mimir in M1?

| Option | Description | Selected |
|--------|-------------|----------|
| Disabled in both | Loki `auth_enabled: false`, Mimir `multitenancy_enabled: false`. No X-Scope-OrgID anywhere. Simplest. | ✓ |
| Anonymous-single-tenant in both | Both run with multitenancy machinery live, single tenant `telemetron`. Header added everywhere. | |
| Split: Loki disabled, Mimir anonymous | Asymmetric. | |

**User's choice:** Disabled in both.
**Notes:** User added free-text feedback: *"that question reminds me of something that I think seems to be implied but I will still mention it. I expect you to look for improvements in these roles."* — captured as **D-25** in `02-CONTEXT.md`: each role port is an opinionated improvement pass, not a mirror-translate. Researcher/planner must audit upstream INSPQ for INSPQ-isms beyond the grep gate, missing pitfall guards, and INSPQ-internal-driven defaults, and document deviations per role.

---

### Q5: How should Loki/Tempo/Mimir consume MinIO root credentials from vault?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-backend aliases | Each backend declares `vault_<role>_s3_access_key`/`_secret_key`; aliased to MinIO root in vault.yml.example. Cheap forward-compat. | ✓ |
| Direct reuse of `vault_minio_root_*` | Each template references MinIO vault keys directly. Simplest now; expensive when per-backend creds land. | |
| Shared `vault_s3_*` keys | One pair used by all three. Doesn't reflect per-backend identity. | |

**User's choice:** Per-backend aliases pointing at root for now (Recommended).
**Notes:** Six new vault keys land in vault.yml.example with `"{{ vault_minio_root_user }}"` / `"{{ vault_minio_root_password }}"` as their values so they alias at variable-resolution time.

---

## Port allocation + verification surface

### Q6: How to resolve the Loki gRPC vs Tempo gRPC :9095 clash?

| Option | Description | Selected |
|--------|-------------|----------|
| Move Tempo gRPC to :9096 | Loki keeps :9095 (most docs assume it); Tempo→:9096 minimal-impact. | (initial choice — superseded by Q7) |
| Move Loki gRPC to :9094 | Tempo keeps default; Loki moves. | |
| Move both off :9095 | Loki :9094 + Tempo :9096 + Mimir on :9095. | |
| Use a different scheme | HTTP-port + 5000 (Loki 8100, Tempo 8200, etc.). | |

**User's choice:** Move Tempo gRPC to :9096 (Recommended) — but on follow-up Claude noted Mimir ALSO defaults to :9095, making it a three-way clash. Decision refined in Q7.

---

### Q7: Three-way :9095 clash (Loki + Tempo + Mimir all default to it). Full resolution?

| Option | Description | Selected |
|--------|-------------|----------|
| Loki 9095, Tempo 9096, Mimir 9097 | Loki keeps :9095; Tempo→:9096; Mimir→:9097. All three explicitly pinned. Sequential and memorable. | ✓ |
| Loki 9095, Tempo 9096, Mimir keeps default | Acknowledged-deferred clash on Mimir (only matters in HA ring; monolithic ignores). | |
| All three explicit at numerically-arbitrary ports | Free-text. | |
| Disable gRPC where unused | Loki :9095, Tempo disabled, Mimir disabled. Most aggressive simplification. | |

**User's choice:** Loki 9095, Tempo 9096, Mimir 9097 (Recommended).
**Notes:** Each backend explicitly pins its gRPC port in its config template — no implicit defaults consumed. Captured as D-28 in CONTEXT.

---

### Q8: Phase 2 backend verification — how does each role smoke-test that push lands in MinIO?

| Option | Description | Selected |
|--------|-------------|----------|
| In-network one-shot container per backend | Final task: `curlimages/curl` container on telemetron pushes synthetic; mc one-shot asserts bucket. Mirrors minio's mc ls verify. | ✓ |
| Temporarily host-publish for verify, then unpublish | Brittle, fights no-host-publish convention. | |
| Phase 2 publishes 127.0.0.1 by default, Phase 3 flips back | Operator-friendly but breaks Phase 1 convention. | |
| Defer smoke to Phase 3 | Phase 2 only verifies running+healthy; weakens success criterion 2. | |

**User's choice:** In-network one-shot container per backend (Recommended).
**Notes:** D-32 in CONTEXT. Uses `auto_remove: true` and `changed_when: false` per W7/W8 patterns from Phase 1.

---

### Q9: Host-publish defaults for the three backends in M1?

| Option | Description | Selected |
|--------|-------------|----------|
| All three default false | Mirrors minio. Operator uses `ssh -L` for access. | ✓ |
| Default false + each README ships ssh-L example | Same defaults; documented per-role. | |
| Default 127.0.0.1 for HTTP read paths | Loopback-only on HTTP ports; gRPC/OTLP stay false. | |

**User's choice:** All three default false (Recommended).
**Notes:** D-30 in CONTEXT. Each role's README still ships an "Operator access" section with the `ssh -L` examples (folded under the recommended option's intent).

---

## Retention + limits + metrics-generator

### Q10: Default retention values per backend?

| Option | Description | Selected |
|--------|-------------|----------|
| storage.yml placeholders as-is: 14d/7d/30d | Loki 14d, Tempo 168h+1h (Pitfall 10 dual-knob), Mimir 30d. | ✓ |
| Shorter homelab defaults: 7d/72h/14d | Easier retention validation; less history. | |
| Longer for retention friendliness: 30d/14d/90d | Demonstrates persistence; costs disk. | |

**User's choice:** Use storage.yml placeholders as-is (Recommended).
**Notes:** D-33/D-34/D-35 in CONTEXT. Tempo dual-knob explicitly per Pitfall 10.

---

### Q11: Mimir limits + monolithic-mode tuning defaults?

| Option | Description | Selected |
|--------|-------------|----------|
| PITFALLS recommendations as defaults | max_global_series_per_user 500k, per_metric 100k, query_store_after 12h, sync_interval 5m, cleanup_interval 5m. | ✓ |
| Looser limits, same timings | 1M/200k series limits. | |
| Stricter limits to surface bad behavior fast | 100k/50k. | |

**User's choice:** PITFALLS recommendations as defaults (Recommended).
**Notes:** D-36 in CONTEXT. All five knobs inline-commented with PITFALLS § references.

---

### Q12: Tempo metrics-generator in M1?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to a later milestone | Stays disabled; doc stub in README. | |
| Enable with remote_write to Mimir | Service-graph in Grafana; couples Tempo→Mimir at startup. | |
| Enable processor but no remote_write | Generates metrics, exposes locally; no cross-backend dependency. | ✓ |

**User's choice:** Enable processor but no remote_write.
**Notes:** D-38 in CONTEXT — **research must validate** the no-remote-write config shape for Tempo 2.10.5 (Tempo 2.10 added `metrics_generator.storage.path` local-WAL option). Three fallback paths documented in D-38; planner picks one based on research findings.

---

### Q13: Loki + Fluent Bit label discipline defaults (Pitfall 4) — ship in Phase 2 or wait?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship Loki-side limits in Phase 2; FB allowlist in Phase 3 | Loki `limits_config` ships hardened defaults; FB allowlist later. | ✓ |
| Defer all to Phase 3 | Loki vanilla in Phase 2, both tightened together in Phase 3. | |
| Loki ships permissive limits | 2x PITFALLS values, tightened in Phase 3. | |

**User's choice:** Ship Loki-side limits in Phase 2; Fluent Bit allowlist comes in Phase 3 (Recommended).
**Notes:** D-37 in CONTEXT.

---

## Claude's Discretion

Items where the user did not prescribe — Claude has latitude during planning/implementation:

- Exact Jinja iteration patterns for already-sorted nested dict sections
- Per-role healthcheck timing (interval/timeout/retries)
- Memory limits per backend container (PITFALLS sizing as a start)
- Loki `chunk_target_size`, `chunk_idle_period` (per PITFALLS "Performance Traps")
- Tempo `compactor.compaction.block_ranges_period`
- Exact in-network verify payload shape per backend (researcher proposes, planner specifies)
- README "Improvements over upstream INSPQ" sub-section per role (D-25)

## Deferred Ideas

(See `02-CONTEXT.md` `<deferred>` section for the full list. Highlights:)

- Per-backend MinIO access keys (D-27 makes the migration cheap; hardening phase)
- Distributed/scalable-single-binary modes (PROJECT.md Out of Scope)
- Multi-tenant Loki/Mimir (D-26 disables; documenting path in Phase 6 architecture doc)
- Tempo metrics-generator → remote_write to Mimir (D-38 keeps it off; future hardening if service-graph wanted)
- Fluent Bit Loki label allowlist (Phase 3)
- Prometheus metric_relabel_configs (Phase 3)
- OTel pipeline pitfalls (Phase 3)

---

*Discussion log captured: 2026-05-17*
