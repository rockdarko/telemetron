# Phase 6: Opt-in, Orchestration, Docs & Smoke Test - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Close out M1. Four discrete outputs:

1. Port the opt-in `nfsd` role (the only role left after Phase 5) and wire it into `playbooks/deploy_docker.yml` as opt-in (default-off). Reframe `nfsd` from "legacy artefact" to "complementary input path for Fluent Bit when remote hosts can't run an OTel SDK or FB agent locally."
2. Author an Ansible-driven M1 acceptance smoke test (`playbooks/smoke_test.yml`) that pushes a synthetic log + metric + trace through OTel Collector OTLP/HTTP and asserts visibility in Grafana via datasource-proxy queries against the four bundled UIDs (`loki`, `prometheus`, `mimir`, `tempo`) inside a 60-second retry budget.
3. Write the three M1 docs (`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`) against a stack that actually booted, synthesized from already-validated `.planning/research/*` + `CLAUDE.md` + per-role READMEs.
4. Rewrite the top-level `README.md` from "early / skeleton only" framing to "self-hosted observability in one playbook" and revalidate end-to-end idempotency on a fresh deploy.

This phase delivers the LEGACY-01, INV-01, INV-03, OPS-07, DOCS-01, DOCS-02, DOCS-03, DOCS-04 requirements and closes M1.

What this phase explicitly does NOT do (scope creep guard, redirected to Deferred Ideas or already-out-of-scope per `PROJECT.md`):

- New role ports (M1 role list is locked at 14 with `nfsd` as the last).
- Multi-host inventory examples (deferred to v2 with HA / distributed-mode work).
- Docs beyond the four authored here (the other 7 planned docs are explicit v2 per `REQUIREMENTS.md` DOCS-V2-01..07).
- Reverse-proxy / TLS recipes beyond the existing `roles/grafana/README.md` "Reverse proxy" subsection (D-85 from Phase 5).
- Anything Kerberos-related on `nfsd` (deferred to v2 hardening).

</domain>

<decisions>
## Implementation Decisions

### nfsd role shape (LEGACY-01)

- **D-91: `nfsd` is a host-package role, not a container role.** Deviates from D-19 (every role uses `community.docker.docker_container`). Rationale: (a) upstream INSPQ uses host-package + systemd nfs-server, which is the proven path; (b) the obvious container image (`erichough/nfs-server`) was archived in 2022 and requires `--privileged` or `CAP_SYS_ADMIN` plus host kernel NFS modules — security debt incompatible with a "clone and run" project; (c) reliability for an opt-in escape hatch matters more than pattern uniformity for a role that defaults off. `roles/nfsd/README.md` documents the deviation explicitly. This is the only host-package role in M1.
- **D-92: `enable_nfsd` is a single inventory knob that flips BOTH the `nfsd` role AND a conditional `[INPUT] tail` block inside `roles/fluentbit/`.** Default `enable_nfsd: false` in `inventory/example-homelab/group_vars/all/nfsd.yml`. When `true`: nfsd role provisions packages + `/etc/exports` + systemd nfs-server; fluentbit role conditionally renders an additional `[INPUT] tail` pointed at `/srv/telemetron-nfs/*/*.log` with hardcoded labels (`job=remote-syslog`, `service=remote`, `host` derived from path segment 1 via FB `Tag` + Lua filter extension). When `false`: neither role touches NFS-related state. Coupling-by-design: there's no honest reason to run one without the other on a Telemetron host.
- **D-93: Default share root `/srv/telemetron-nfs/<hostname>/`.** Sub-dirs per remote hostname provide a deterministic FB path-to-`host`-label mapping (path segment 1 after the share root = `host` label). Exports declared via `nfsd_exports: []` (default empty) — list of `{path, allow}` dicts that match the upstream blockinfile shape. Operators add entries like `nfsd_exports: [{path: /srv/telemetron-nfs/oldbox, allow: "10.0.0.42(rw,sync,root_squash,no_subtree_check)"}]`. Default of `[]` means even with `enable_nfsd: true`, no exports happen until the operator names a remote host — fail-safe.
- **D-94: NFSv4 only, no Kerberos, AUTH_SYS + IP allow-list.** Modern default; one-port TCP `:2049` (firewall-simple, no portmapper/rpcbind exposure). `roles/nfsd/README.md` documents this is acceptable on a single homelab LAN and lists Kerberos as the v2 hardening path. Linux distros default to v4 in 2026.
- **D-95: FB Lua filter extension for path-derived labels.** `roles/fluentbit/files/enrich.lua` extends with a path-segment fallback that fires when the source is the NFS `[INPUT] tail` (not the existing Docker container tail). Specifically: when the FB `tag` matches the NFS tail pattern (e.g. `nfs.<hostname>.<path>`), extract `host` from segment 1 of the tag, set `service: remote`, `job: remote-syslog`. No change to the existing Docker-label-from-config.v2.json path. The Lua filter is the single source of truth for label enrichment regardless of input source.
- **D-96: README framing — "most operators ignore this."** `roles/nfsd/README.md` opens with a "When to use this role" section: most homelab and small-deployment operators do NOT need `nfsd`. It exists for the operator with legacy hosts (e.g. ancient syslog boxes, appliances) that can't run an OTel SDK or a Fluent Bit agent locally and whose only realistic shipping path is "write logs to a file the central host can tail via NFS." Preferred paths (OTel SDK direct from the app; FB on the source host; rsyslog/syslog-ng to OTel) are listed first; NFS is the last-resort fallback.

### Smoke test shape (OPS-07)

- **D-97: New playbook `playbooks/smoke_test.yml`.** Not bolted onto `deploy_docker.yml`. Operator runs `ansible-playbook -i inventory/example-homelab playbooks/smoke_test.yml` after `deploy_docker.yml`. Matches the M1 quickstart shape: deploy first, then verify. Separate playbook means smoke failures don't break the deploy contract and the smoke surface can evolve independently of deploy.
- **D-98: Producers = curl + jq + raw OTLP/HTTP JSON.** Three Ansible tasks, each running `ansible.builtin.uri` or `ansible.builtin.command: curl` against `http://<host>:4318/v1/logs`, `/v1/metrics`, `/v1/traces` with hand-rolled JSON payloads built via Jinja templates in `playbooks/smoke_test/templates/{log,metric,trace}.json.j2`. Zero new binary dependencies — `curl` and `jq` are everywhere; OTel Collector is the only assumed running service. Synthetic identifiers: `service.name="telemetron-smoke"`, distinct `trace_id` generated per smoke run via `lookup('password', '/dev/null length=32 chars=hexdigits')`, metric `telemetron_smoke_metric{run_id="<timestamp>"}`, log body includes the literal string `"telemetron-smoke-test"` + a tag `smoke=true`. Run-id ensures back-to-back smoke runs don't pollute each other.
- **D-99: Asserts via Grafana datasource-proxy queries with `retries:12 / delay:5` (60-second budget).** Four assertion tasks (one each for Loki, Prometheus, Mimir, Tempo — ROADMAP SC3 explicitly names both Prometheus AND Mimir for the metric path, so we cover both):
    - Loki: `GET /api/datasources/proxy/uid/loki/loki/api/v1/query?query={service_name="telemetron-smoke"} |= "telemetron-smoke-test"` — expect `status: success` + non-empty `result[]`.
    - Prometheus: `GET /api/datasources/proxy/uid/prometheus/api/v1/query?query=telemetron_smoke_metric{run_id="<id>"}` — expect non-empty `result[]`.
    - Mimir: `GET /api/datasources/proxy/uid/mimir/prometheus/api/v1/query?query=telemetron_smoke_metric{run_id="<id>"}` — expect non-empty `result[]` (validates Prometheus → Mimir `remote_write` path is healthy).
    - Tempo: `GET /api/datasources/proxy/uid/tempo/api/traces/<trace_id>` — expect 200 + non-empty `batches[]`.

   Each task uses `until: result.json.<path> is non-empty`, `retries: 12`, `delay: 5` for an exact 60-second wall-clock budget. ROADMAP SC3 ("within 60 seconds") becomes a verifiable Ansible assertion, not a stopwatch.
- **D-99a: Mimir asserter URL path is `/api/datasources/proxy/uid/mimir/api/v1/query`, NOT `/api/datasources/proxy/uid/mimir/prometheus/api/v1/query` as originally stated in D-99.** Amendment rationale: the `/prometheus/` infix in D-99 was a documentary error. The proven path in `roles/grafana/tasks/verify.yml:178` (Phase 5, leviathan-verified 2026-05-19) is `/api/datasources/proxy/uid/mimir/api/v1/query`. The Grafana datasource-proxy strips the proxy prefix and prepends the datasource URL (which already points at Mimir's `/prometheus` endpoint), so the client-side path is just `/api/v1/query`. D-99's other three asserter URLs (Loki, Prometheus, Tempo) remain unchanged.
- **D-100: Three play tags: `log`, `metric`, `trace`.** Operator can run `ansible-playbook ... playbooks/smoke_test.yml --tags log` to exercise just one path. Useful when debugging a single signal during stack tuning. Matches the per-role tag convention (D-24) extended to smoke signals.
- **D-101: Grafana Basic Auth for proxy queries.** Reuses `grafana_admin_password` (D-86) for the smoke-test Grafana proxy queries. Smoke test playbook reads from the same secrets surface as the deploy playbook — no new secrets, no new vault keys.

### Docs scope & voice (DOCS-01/02/03/04)

- **D-102: Voice split — terse reference + one teaching walkthrough.** `docs/architecture.md` = terse reference (component table, signal-flow diagram, port matrix, monolithic-mode tradeoff bullets, ~3-4 pages). `docs/inventory.md` = terse reference (directory shape, group_vars conventions, secrets contract, symlink-from-outside-repo pattern, ~2-3 pages). `docs/quickstart.md` = full teaching walkthrough (every command, expected output, where to click in Grafana, troubleshooting section, ~6-8 pages). Splits the verbose-vs-concise tax across docs by purpose.
- **D-103: `docs/architecture.md` synthesized from existing artifacts.** Distill from `.planning/research/` (whichever files exist relating to architecture decisions), `CLAUDE.md` (port matrix and stack table — already structured for this), and per-role `roles/<name>/README.md` (component descriptions). Does NOT just copy-paste; rewrites for public consumption (no D-XX references, no `.planning/` paths in the user-facing doc, no INSPQ heritage details beyond a one-line attribution). The synthesis is a public-facing distillation, not internal documentation surfaced as-is.
- **D-104: `docs/quickstart.md` is the canonical "zero-to-dashboards" walkthrough.** Structure: (a) Prerequisites (Ansible 2.15+, Docker 27+ on target, SSH key auth, `community.docker` collection); (b) Clone the repo; (c) Edit `inventory/example-homelab/hosts.yml` (1 line); (d) Copy `secrets.yml.example` to `secrets.yml`, fill in 4 `CHANGE_ME` values; (e) Optional `ansible-vault encrypt`; (f) `ansible-playbook ... playbooks/deploy_docker.yml --ask-vault-pass`; (g) `ansible-playbook ... playbooks/smoke_test.yml --ask-vault-pass`; (h) Open `http://<host>:3000`, log in as `admin`, click `Loki Explore Landing` dashboard, see the smoke-test log appear; (i) Troubleshooting subsection (common failure modes: SSH key not loaded, Docker not installed, port already in use, OTLP rejected because telemetron network isn't bridged). DOCS-02 acceptance ("verified by an operator running it verbatim on a fresh target") = leviathan run during Plan 06-04 verify.
- **D-105: `docs/inventory.md` is the deep-dive; existing READMEs stay as quick orientation.** Three-layer doc structure: (a) `inventory/README.md` = top-level 1-page orientation + BYO instructions; (b) `inventory/example-homelab/README.md` = "how to use THIS example" (already exists, only minor refresh); (c) `docs/inventory.md` = "building your own from scratch" — full `group_vars/all/` schema per Phase, secrets contract per role with full key list (`minio_root_user`, `minio_root_password`, `loki_s3_*`, `tempo_s3_*`, `mimir_s3_*`, `grafana_admin_password`), `host_vars/` patterns, symlink-from-outside-repo with `.git/info/exclude` hint, multi-host extension preview (with a "this is v2 territory" callout). Cross-link aggressively in both directions.
- **D-106: `README.md` rewrite — pivot to "self-hosted observability in one playbook."** Para 1 leads with the value prop ("Bring up Prometheus + Loki + Tempo + Grafana + Alertmanager on your own hardware with one Ansible command. Single-host Docker. Homelab-friendly."). Para 2 = "Quick start" with a 3-line code block (`git clone`, edit hosts, run playbook) linking to `docs/quickstart.md`. Para 3-4 = component table (drop `hook_router` and `HAProxy` from the "what's in the stack" list with one-line v2 callouts; the current README listing them is aspirational/inaccurate for M1). Para 5 = "Origin" section retaining INSPQ heritage attribution. "Status: early" line deleted entirely. Layout section refreshed to match what's actually in the tree. `docs/README.md` planned-docs table updated to reflect what shipped vs. v2.

### Plan slicing & wave order

- **D-107: 4 plans grouped by output.** Mirrors D-22/D-40/D-70 (one plan per cohesive deliverable; not per requirement; not one mega-plan).
    - `06-01-PLAN.md`: nfsd role port + FB tail-input integration (LEGACY-01; partial INV-03 for nfsd wiring). Per D-22, ships end-to-end on its own — `deploy_docker.yml` extends with `nfsd` as opt-in last role.
    - `06-02-PLAN.md`: `playbooks/smoke_test.yml` + producer templates + Grafana-proxy assertions (OPS-07).
    - `06-03-PLAN.md`: `docs/architecture.md` + `docs/quickstart.md` + `docs/inventory.md` (DOCS-01, DOCS-02, DOCS-03). All three written against a fully-deployed stack.
    - `06-04-PLAN.md`: README rewrite + minor refresh of `docs/README.md` planned-docs table + end-to-end idempotency revalidation on leviathan from a fresh clone perspective (DOCS-04, INV-01, INV-03 close-out). This plan also closes the milestone — the "two back-to-back runs, both `changed=0`" gate per OPS-04 lives here.
- **D-108: Strict sequential wave order, one wave per plan.** Wave 1 = 06-01; Wave 2 = 06-02; Wave 3 = 06-03; Wave 4 = 06-04. Justification: each plan depends on the prior for verify. Smoke can't assert against a non-fully-deployed stack (06-01 wires nfsd into the playbook); docs can't be verified verbatim without smoke (DOCS-02 SC explicitly says "verified by an operator running it verbatim"); README rewrite can't claim "M1 done" until docs ship. No parallelism gained from out-of-order execution; the doc-vs-smoke drift risk that parallel-Wave-2 would introduce is real (quickstart.md describes the smoke step, so smoke needs to exist first).
- **D-109: Live UAT on leviathan continues; DOCS-02 "verbatim verification" acceptance happens there.** Phase 5 established the live-UAT pattern (see `.planning/phases/05-ui-plane/05-HUMAN-UAT.md`). Phase 6 extends it: each plan's verify step includes a leviathan run (06-01 = nfsd opt-in deploy with `enable_nfsd: true` flipped + FB picks up a placeholder log file; 06-02 = smoke test against live leviathan; 06-03 = leviathan quickstart-walkthrough by hand, including the "click in Grafana" step that 05-HUMAN-UAT was unable to automate; 06-04 = two back-to-back full deploys both `changed=0`). Tracked in `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md`.
- **D-110: Per-plan light doc cascade extending D-72.** Each plan updates `roles/README.md` (tick `nfsd` in 06-01; no row tick for other plans, but possibly add new Gates as relevant — e.g. Gate 10 "smoke-test producer + assertion gate" defined in 06-02 if it generalizes), `ROADMAP.md` (mark plan complete in Phase 6 list), and any `PROJECT.md` Active-section line that reflects remaining work ("0 remaining roles; M1 complete" lands in 06-04). Distinct from D-58 (Phase-4 atomic doc cascade for hook-router deferral) — Phase 6 has no scope-reshape, just bookkeeping per plan.

### Claude's Discretion

Areas not requiring user input — Claude/researcher/planner picks the approach. These ARE NOT decisions to question or revisit; they're explicit "you decide" calls:

- Exact `[INPUT] tail` directive shape for the FB NFS path (parser choice, `Mem_Buf_Limit`, multiline handling). Researcher to look at FB 4.2.3 docs for the `tail` plugin and the `Tag` interpolation syntax that powers the path-derived label trick.
- Whether the FB Lua extension is one filter or two (extend existing `enrich.lua` vs. add a sibling `enrich_nfs.lua`). Lean: extend the existing file; one source of truth.
- Exact JSON shape of OTLP/HTTP payloads for smoke producers (researcher reads OTLP spec for the canonical request shape; planner templates it).
- Exact Ansible `until:` predicate syntax for the smoke assertion tasks (Jinja-on-result.json depth).
- Diagram format for `docs/architecture.md` signal flow — ASCII art vs. mermaid vs. just prose. Lean: ASCII so the doc renders in `cat`/raw-GitHub without a Mermaid renderer; aesthetic of plain-text docs matches the homelab audience.
- Whether `docs/quickstart.md` ships a "production hardening" subsection cross-referencing `roles/grafana/README.md` reverse-proxy section (D-85). Lean: yes, brief; ties off a loose end from Phase 5.
- Specifically which Phase-1..5 D-numbered decisions the docs cite (most should NOT be cited in public docs — D-IDs are internal). Lean: docs cite zero D-numbers; CONTEXT.md citations are internal navigation only.
- Whether the smoke test playbook reads `grafana_admin_password` from `secrets.yml` directly or expects it to already be loaded by the deploy playbook context. Lean: smoke playbook loads `secrets.yml` itself via `vars_files` — operator can run smoke independently of deploy.
- nfsd README structure — likely mirrors the Phase-5 promlens deprecation-banner pattern but with a "When to use this role" header instead of `## DEPRECATION CANDIDATE`. Planner picks header wording.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ROADMAP.md + REQUIREMENTS.md (phase-defining)

- `.planning/ROADMAP.md` §"Phase 6: Opt-in, Orchestration, Docs & Smoke Test" — Goal, dependencies, requirements list, 5 Success Criteria (1-5). Authoritative for what the phase delivers.
- `.planning/REQUIREMENTS.md` v1 entries: LEGACY-01 (nfsd opt-in), INV-01 (clone-edit-vault-run quickstart shape), INV-03 (deploy_docker.yml orchestrates all 14 roles in dependency order with per-role tags), OPS-07 (smoke test 60s acceptance), DOCS-01..04 (architecture/quickstart/inventory docs + README rewrite). Authoritative for the discrete deliverables.
- `.planning/REQUIREMENTS.md` v2 entries: ALERT-V2-01..05 (hook_router deferred — referenced when rewriting README to explain absence), DOCS-V2-01..07 (other docs deferred — referenced when refreshing `docs/README.md` planned-docs table), STORAGE-01 (MinIO replacement — referenced if README mentions known-debt).

### Project-level guidance

- `.planning/PROJECT.md` — Validated requirements (Phase 1-5 outputs), Active section ("0 remaining roles; M1 complete" is what 06-04 lands), Out of Scope (don't reintroduce dropped roles), Key Decisions table (D-01..D-90 are precedents, not editable).
- `.planning/STATE.md` — Current position (Phase 6 next; Phase 5 verified on leviathan 2026-05-19); session continuity.
- `CLAUDE.md` — Project-level instructions. Component table, port-allocation cheat sheet (architecture.md draws from this), Three Decisions section (MinIO crisis, MongoDB dropped, PromLens frozen — all needed for README rewrite framing).

### Prior CONTEXT.md (foundational decisions, in numeric order)

- `.planning/phases/01-foundation-storage/01-CONTEXT.md` — D-01..D-21. Especially D-04 (telemetron network in pre_tasks), D-12/D-14 (default no host publish), D-15 (group_vars layout), D-19 (every role = community.docker.docker_container — D-91 deviates from this for nfsd), D-21 (grep gates).
- `.planning/phases/02-telemetry-backends/02-CONTEXT.md` — D-22..D-39. Especially D-22 (one plan per role), D-23 (each plan ships end-to-end), D-24 (per-role tag), D-25 (opinionated port pass, document deviations).
- `.planning/phases/03-ingest-plane/03-CONTEXT.md` — D-40..D-55. Especially D-44/D-47 (OTel exporter shape — relevant to smoke producer choice), D-46 (FB co-located on Telemetron host — directly relevant to nfsd FB-tail integration), D-50 (FB Pitfall-6 mitigation pack — UTC discipline matters when NFS-tailed logs arrive from non-UTC hosts).
- `.planning/phases/04-alert-plane/04-CONTEXT.md` — D-56..D-69, D-90. Especially D-58 (atomic doc cascade pattern), D-65 (severity labels), D-66 (no new vault keys in alert plane — smoke test inherits this discipline), D-69 (community.docker.docker_container_exec pattern for verify).
- `.planning/phases/05-ui-plane/05-CONTEXT.md` — D-70..D-89. Especially D-72 (per-plan light doc cascade — D-110 mirrors), D-73 (Gate 9 datasources-resolve-real-data — Gate 9.5 is precedent for smoke assertion shape), D-77/D-82/D-83/D-84 (UI port matrix that architecture.md documents), D-85 (reverse-proxy section in grafana README — quickstart cross-links), D-86..D-89 (Grafana admin / org / anonymous-viewer defaults — quickstart documents).

### Gates and conventions in `roles/README.md`

- `roles/README.md` "Per-role port-acceptance gates" — Gates 1-9 apply to nfsd port:
    - Gate 1 (INSPQ grep + non-ASCII): real work — upstream INSPQ nfsd has French task names and a `/srv/nfs/inspq` mention.
    - Gate 2 (image pin): N/A — nfsd has no image (host-package per D-91); document the deviation.
    - Gate 3 (secrets discipline): N/A — nfsd has no secrets.
    - Gate 4 (idempotency): real work — `ansible.builtin.package`, `systemd:`, `blockinfile:` are all idempotent but the per-OS branching (EL vs Ubuntu) needs care.
    - Gate 5 (healthcheck/restart): N/A for the role itself (no container); systemd `enabled: yes, state: started` is the equivalent contract.
    - Gate 6 (README schema): real work, document the host-package deviation, "When to use this role" framing per D-96.
    - Gate 7 (label-stamp): N/A — nfsd has no container.
    - Gate 8 (parent-dir bind-mount): N/A — nfsd has no rendered config files bind-mounted into a container.
    - Gate 9 (datasources-resolve-real-data): N/A — nfsd is not a UI role.

### Upstream INSPQ source (for D-25 opinionated-port pass)

- `~/git/inspq/ansible/nfsd/` — upstream role. Tasks: `tasks/main.yml` + `tasks/install.yml` + `tasks/nfs_centos7.yml` + `tasks/nfs_ubuntu.yml`. Task `name:` strings are French. Default `nfsd_state: present`. `nfs_shares` is operator-supplied list. `blockinfile` populates `/etc/exports`. Firewall handling is opinionated (firewalld on EL7, ufw on Ubuntu). Port: opinionated-port pass per D-25 must (a) translate task names FR→EN; (b) reshape `nfs_shares` to `nfsd_exports` matching the Telemetron naming convention; (c) drop the EL7-specific yum-binary workaround unless EL7 support is targeted (lean: drop, target EL8+ / Ubuntu 22.04+); (d) extend with the `/srv/telemetron-nfs/` path discipline (D-93); (e) drop INSPQ-specific `/srv/nfs/inspq` references entirely.

### Inventory examples

- `inventory/example-homelab/group_vars/all/secrets.yml.example` — All 8 secret keys consumed in M1; smoke test reuses `grafana_admin_password`.
- `inventory/example-homelab/group_vars/all/network.yml` — telemetron_network, telemetron_publish_default, telemetron_tz — referenced by docs/inventory.md.
- `inventory/example-homelab/group_vars/all/storage.yml` — telemetron_volume_prefix, telemetron_config_root, MinIO bucket list, retention defaults — referenced by docs/inventory.md.

### User memory (NOT to be cited in user-facing docs, internal navigation only)

- `[[project_fluentbit_role_shift]]` — Telemetron's FB tails Docker container logs on the same host (incl. its own stack); upstream INSPQ used FB to scoop logs from separate legacy hosts. nfsd reframing per D-91/D-92 partially restores the legacy-host pattern as an opt-in path.
- `[[project_leviathan_uat_host]]` — Live-UAT target for Telemetron is `leviathan` (SSH passwordless, Docker 29, `inventory/leviathan/` gitignored). D-109 mandates leviathan runs for each plan's verify.
- `[[feedback_naming_separator]]` — Underscore by default; hyphen only where RFC 1123 / DNS-1123 forces. NFS export paths use `-` (filesystem-safe), inventory var names use `_`.
- `[[feedback_no_decorative_convention_prefixes]]` — D-90 precedent; no `vault_` prefix anywhere. nfsd has no secrets in M1, so this is documentary only.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`playbooks/deploy_docker.yml`** — Master orchestrator. Already wires 12 roles (`minio → loki → tempo → mimir → node_exporter → opentelemetry → prometheus → fluentbit → alertmanager → grafana → karma → promlens`). Plan 06-01 appends `nfsd` last with `when: enable_nfsd | default(false) | bool` task-level conditional or play-level `tags: nfsd` (planner picks). Plan 06-04 verifies the now-13-deployed + 1-opt-in shape.
- **`roles/fluentbit/`** — D-46-established FB role tailing Docker container logs. Plan 06-01 extends with a conditional `[INPUT] tail` block for the NFS path (Jinja conditional on `enable_nfsd`) + extends `roles/fluentbit/files/enrich.lua` with the path-segment-to-host extraction logic.
- **`roles/grafana/tasks/verify.yml`** — Phase 5 `community.docker.docker_container_exec` retry-until pattern is THE canonical model for smoke-assertion task shape (D-69 precedent). Plan 06-02 imitates exactly.
- **`inventory/example-homelab/group_vars/all/*.yml`** — Existing 14 var files (network, storage, secrets.yml.example, per-role files for the 12 deployed roles). Plan 06-01 adds `nfsd.yml` (15th file). Plan 06-04 audits the full set for stale comments referencing not-yet-shipped state.
- **`docs/README.md`** — Lists 10 planned docs. Plan 06-04 updates this to show 3 shipped in M1 (`architecture.md`, `quickstart.md`, `inventory.md`) + 7 deferred to v2 (cross-reference DOCS-V2-01..07).
- **`CLAUDE.md` TL;DR table + port-allocation snapshot + version compatibility matrix** — Three tables already in CLAUDE.md that map 1:1 to sections in `docs/architecture.md`. Distill, don't duplicate.

### Established Patterns

- **One plan per cohesive deliverable** (D-22/D-40/D-70). Each plan ships end-to-end on its own (D-23). Per-role tag (D-24). Plan 06-01..04 follows.
- **`community.docker.docker_container_exec` for verify probes** (D-69, D-73, D-105). Avoids the auto_remove+detach race (ansible/ansible#45272). Smoke test producer + assertion tasks use this pattern via `delegate_to: <grafana container>` where needed — though for OTLP push the natural target is the host curl-ing localhost:4318, not the container.
- **`retries:N / delay:N / until:` polling** for any post-task validation (D-69, D-105 + 04-02 Bug-1 fix + 05-05 grafana verify rewrite). Smoke assertion tasks follow this verbatim (`retries: 12, delay: 5`).
- **Parent-directory bind-mounts** (D-19 + Gate 8). N/A for nfsd (host-package, no bind-mounts) but applies to smoke playbook if it generates intermediate config — likely it doesn't.
- **Idempotency = `changed=0` on second run** (OPS-04 + D-19). Plan 06-01 verifies for nfsd specifically (the host-package + systemd + blockinfile chain is fully idempotent if written carefully — package: state: present, systemd: state: started/enabled: yes, blockinfile: marker:). Plan 06-04 verifies for the whole stack.

### Integration Points

- **`playbooks/deploy_docker.yml` roles list extension:** Plan 06-01 appends `nfsd` as the 13th deployed role (14th overall slot, opt-in). Either play-level conditional (`tags: nfsd` + operator runs with/without) or task-level `when: enable_nfsd`. Lean: task-level `when`, so the role always evaluates in the roles list but no-ops when disabled. Tag `nfsd` regardless for selective runs.
- **`roles/fluentbit/templates/<config>.j2` extension:** Plan 06-01 adds a Jinja-conditional `[INPUT] tail` block. Keep the existing tail input (Docker containers) unchanged; add a sibling tail input only when `enable_nfsd | default(false) | bool`.
- **`inventory/example-homelab/group_vars/all/nfsd.yml`** = new file in Plan 06-01. Default `enable_nfsd: false`. Default `nfsd_exports: []`. Default `nfsd_share_root: /srv/telemetron-nfs`. Default `nfsd_protocol: nfsv4`.
- **`playbooks/smoke_test.yml`** = new file in Plan 06-02. `hosts: telemetron`, `gather_facts: false` (no needed facts; faster), `vars_files: [inventory/example-homelab/group_vars/all/secrets.yml]` (reads `grafana_admin_password`).
- **`playbooks/smoke_test/templates/` directory** = new in Plan 06-02. Three Jinja templates: `log.json.j2`, `metric.json.j2`, `trace.json.j2` (OTLP/HTTP JSON shapes). Researcher confirms OTLP/HTTP body schema in 06-02 RESEARCH.
- **`docs/architecture.md`, `docs/quickstart.md`, `docs/inventory.md`** = new files in Plan 06-03. Researcher to spot-check `.planning/research/` for material that already exists in usable shape.
- **Top-level `README.md` rewrite** + **`docs/README.md` planned-docs table refresh** = both in Plan 06-04.

</code_context>

<specifics>
## Specific Ideas

- **The reframing of nfsd as an FB complement is the load-bearing decision in this phase.** Without it, nfsd is dead weight in M1 (every Telemetron-stack container is already tailed by FB on the same host; remote hosts that can't run FB locally have no log-ingestion story). With it, nfsd justifies its M1 inclusion as the "legacy escape hatch" for hosts that can't run an OTel SDK or a Fluent Bit agent — restoring the upstream INSPQ use case (see `[[project_fluentbit_role_shift]]` user memory) as an opt-in, not the default.
- **5 hazards documented during discussion (informational, all already addressed in decisions):**
    1. NFS auth is IP-only (v3) or Kerberos (v4). Addressed by D-94 (v4 + AUTH_SYS + IP allow-list as homelab-acceptable default; Kerberos = v2).
    2. Containerized NFS is brittle. Addressed by D-91 (host-package only; container path explicitly rejected).
    3. FB integration is real code change. Addressed by D-92 (single knob flips both; planner scope is concrete).
    4. INGEST-07 label allowlist breaks for NFS-tailed logs (no Docker labels available). Addressed by D-95 (path-derived host label via Lua extension; hardcoded `job=remote-syslog, service=remote`).
    5. Timezone hazards from remote hosts in non-UTC. Addressed by README guidance (most M1-target operators ship from UTC; the doc says "remote hosts logging via NFS SHOULD log in UTC"; non-UTC handling is documented as a known caveat, not solved).
- **`docs/quickstart.md` "verified by operator running verbatim" acceptance** is the heaviest single SC in this phase. Plan 06-03 verify includes a leviathan-on-fresh-checkout run, NOT just a static lint of the doc. D-109 makes this explicit.
- **The 60-second budget in OPS-07 should be a strict assertion**, not aspirational. D-99's `retries:12 / delay:5` is the canonical implementation. Smoke fails loudly on retry exhaustion.
- **README rewrite tone:** matter-of-fact, no marketing language. Audience is technical homelab operators; they skim. First-screen content must answer "what is this and do I want it?" and "how do I run it?"

</specifics>

<deferred>
## Deferred Ideas

- **NFS Kerberos hardening** — Deferred to v2. AUTH_SYS + IP allow-list is the M1 default; documented as acceptable for homelab single-LAN. Kerberos requires KDC + realm setup + service principal management — a hardening story that doesn't fit M1's "edit one hostname and go" promise.
- **Remote-host log shipper recipes (rsyslog → NFS export, syslog-ng → NFS export)** — Deferred. nfsd role README mentions "operators write logs from their remote host to the export path however they want"; doesn't ship example rsyslog configs. If demand emerges, ship as `docs/remote-log-ingest.md` in v2.
- **Multi-host smoke test** — Smoke test deliberately targets a single host (the Telemetron host). When v2 lands the multi-host inventory example (HA-02), smoke test extends to verify federation. M1 punts.
- **Synthetic smoke beyond the 3 signals** — No "synthetic alert" or "synthetic trace span graph"; smoke proves the data plane end-to-end, not every UI feature. Karma + alert routing aren't smoke-tested (alerts are visible-not-actioned in M1 anyway per Phase 4 reshape — null receiver; D-66).
- **CI integration for smoke** — Smoke playbook runs on operator command; not on every git push. CI is a v2 (TEST-01) story; smoke playbook becomes the CI's payload at that point.
- **`docs/alerts.md`, `docs/mimir-retention.md`, `docs/fluentbit-timestamps.md`, `docs/hook-router.md`, `docs/instrumentation-otel.md`, `docs/migration-from-inspq.md`, `docs/metrics.md`** — All explicit v2 per REQUIREMENTS.md DOCS-V2-01..07. Phase 6's `docs/README.md` refresh references these as v2 placeholders.
- **Diagram tooling for architecture.md** — Mermaid + GitHub-native rendering exists but adds visual-complexity-as-status-symbol that homelab docs don't need. Stay with ASCII signal flow + plain tables. If the project later wants visually-richer docs, that's a separate "docs polish" milestone.
- **Production-hardening guide** — `docs/quickstart.md` includes a brief "Production hardening" subsection (anonymous viewer, reverse proxy, secrets rotation) but doesn't author a full hardening doc. That's a v2 follow-up alongside Kerberos NFS + per-backend MinIO IAM + Grafana SSO.
- **arm64 / Pi 5 / Apple Silicon support** — Already out of scope per PROJECT.md; not a deferred-from-Phase-6 issue.
- **GitHub Pages or any docs hosting** — Docs live in-repo as Markdown only. No site generation in M1.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 6` returned zero matches; no backlog items relevant to this phase.

</deferred>

---

*Phase: 06-opt-in-orchestration-docs-smoke-test*
*Context gathered: 2026-05-19*
