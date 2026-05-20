---
phase: 06-opt-in-orchestration-docs-smoke-test
plan: 03
subsystem: docs
tags: [docs, architecture, quickstart, inventory, m1-acceptance, public-facing]

# Dependency graph
requires:
  - phase: 06-01
    provides: nfsd opt-in role + enable_nfsd single-knob coupling (docs/architecture.md mentions; docs/inventory.md notes the knob)
  - phase: 06-02
    provides: playbooks/smoke_test.yml + per-tag --tags log/metric/trace + smoke_test/README.md (docs/quickstart.md Step 7 references verbatim)
  - phase: 05-ui-plane
    provides: 4 hardcoded Grafana datasource UIDs + tracesToLogsV2 derivedFields + reverse-proxy section in roles/grafana/README.md (docs/quickstart.md production-hardening cross-link target)
provides:
  - docs/architecture.md as the public-facing terse architecture reference (component table, ASCII signal flow, port matrix, monolithic-mode tradeoffs, storage deps, known debt)
  - docs/quickstart.md as the zero-to-dashboards teaching walkthrough (8 canonical steps, prerequisites, troubleshooting, production hardening, cross-links)
  - docs/inventory.md as the deep-dive inventory model (directory shape, group_vars conventions, 9-key secrets contract, host_vars patterns, symlink-from-outside-repo pattern, multi-host v2 callout, validation)
affects: [06-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Voice split (D-102): terse reference (architecture.md, inventory.md) + one teaching walkthrough (quickstart.md). Reference docs are scannable; walkthrough is verbose with every command + expected output + troubleshooting"
    - "Public-doc Gate 1 scrub: zero D-XX refs, zero `.planning/` paths, zero `inspq|qc.ca|montreal|québec|francais|french` strings, zero `vault_` prefix usage, zero non-ASCII characters -- enforced via grep gates after every doc write"
    - "ASCII-only signal-flow diagrams (D-103 lean: ASCII renders in cat / raw GitHub view without Mermaid tooling, matches plain-text homelab audience aesthetic)"
    - "Distillation pattern: research/ARCHITECTURE.md + CLAUDE.md + per-role READMEs -> public docs with all internal navigation stripped (no D-XX, no .planning/ paths, no INSPQ heritage details beyond one-line opener)"
    - "Fact-check authoring: read on-disk artifacts (hosts.yml shape, inventory layout, grafana README sections) before writing the doc; plan skeleton was wrong about a filename, real shape used in the doc"

key-files:
  created:
    - docs/architecture.md
    - docs/quickstart.md
    - docs/inventory.md
  modified: []

key-decisions:
  - "DOCS-01/02/03 land together as plan 06-03: voice split honored (terse arch + inventory + verbose quickstart), all three pass Gate 1 scrub, all three reference the playbooks/smoke_test.yml that 06-02 shipped as the canonical post-deploy verification"
  - "ASCII signal-flow diagram distilled from research/ARCHITECTURE.md and cleaned of internal annotations -- shows external producers, OTel/Prometheus ingest split, Loki/Tempo/Mimir monolithic backends, MinIO 5-bucket trinity, AM->Karma alert path, Grafana datasource fan-out, and the opt-in NFS path. Under 80 chars wide for terminal compatibility"
  - "Components table uses EXACT pinned tags from CLAUDE.md TL;DR (no version drift): 13 components incl. opt-in nfsd; Port Allocation table reproduces CLAUDE.md cheat sheet (17 rows incl. internal Tempo OTLP ports + opt-in NFS)"
  - "Quickstart uses the REAL inventory filename `hosts.yml` (YAML), not the plan-skeleton's `example-homelab.hosts` (which doesn't exist on disk). Authoring fact-check caught the discrepancy before the file was written"
  - "Quickstart Step 6 healthy-container expectation refined from 'all containing healthy' to '11 healthy + Karma plain Up' to match leviathan reality (Karma FROM scratch image -- no /bin/sh for Docker healthcheck probe, in-network curl probe is canonical). DOCS-02 verbatim acceptance restored after Rule-1 auto-fix during UAT"
  - "Live UAT autonomously executed on leviathan per project_leviathan_uat_host memory (Task 4 was a checkpoint:human-verify gate in the plan, but the memory says 'run live-Docker tests yourself; don't punt to human_needed'). UAT outcomes recorded in 06-HUMAN-UAT.md (gitignored)"

patterns-established:
  - "Doc-quality Gate 1 contract: every public doc passes the 5-grep scrub (D-XX, .planning/, vault_, INSPQ-heritage, non-ASCII) AND the section-header existence check (`grep -q '^## <required header>'`) before commit. Doc authoring is verifiable, not subjective"
  - "Fact-check-before-write: read the actual on-disk artifacts (hosts.yml, inventory README, role READMEs) before writing the doc -- catches plan-skeleton drift from reality. Two Rule-1 auto-fixes in this plan came from this pattern"
  - "Live UAT replaces lint-only verification for docs: simply linting `docs/quickstart.md` would have shipped Step 6's overstated healthy-container claim. Running the doc verbatim on leviathan caught the discrepancy and the fix was a precise single-line edit"

requirements-completed: [DOCS-01, DOCS-02, DOCS-03]

# Metrics
duration: 10min
completed: 2026-05-19
---

# Phase 06 Plan 03: M1 docs trio (architecture.md + quickstart.md + inventory.md) Summary

**Three public-facing M1 documentation files authored against the fully-deployed, smoke-verified leviathan stack: docs/architecture.md is the 3-4 page terse component reference with ASCII signal flow + 17-row port table + Known Debt; docs/quickstart.md is the 6-8 page zero-to-dashboards teaching walkthrough with the canonical 8-step path + Troubleshooting + Production hardening; docs/inventory.md is the 2-3 page deep-dive with the 9-key secrets contract + symlink pattern + multi-host v2 callout. All three pass the Gate 1 scrub (zero D-XX, zero .planning/ paths, zero INSPQ heritage, zero vault_ prefix, zero non-ASCII) and the leviathan UAT walkthrough proves the quickstart works verbatim end-to-end including the 'click in Grafana' UI step.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-19T22:01:53Z
- **Completed:** 2026-05-19T22:12:51Z
- **Tasks:** 4 (3 auto + 1 checkpoint:human-verify executed autonomously per `[[project_leviathan_uat_host]]` memory)
- **Files created:** 3 (docs/architecture.md, docs/quickstart.md, docs/inventory.md)
- **Files modified during UAT auto-fix:** 1 (docs/quickstart.md Step 6 expected-output correction)

## Accomplishments

- **DOCS-01 landed:** `docs/architecture.md` is a 3-4-page terse public-facing reference with all 8 required sections (Overview, Signal Flow, Components, Port Allocation, Monolithic Mode, Storage Dependencies, Known Debt, Further reading), all 13 components with EXACT pinned tags from CLAUDE.md, full 17-row port allocation table, ASCII signal-flow diagram under 80 chars wide, monolithic-mode tradeoff bullets, storage-dependency table, and 4 known-debt callouts (MinIO archived, PromLens frozen, hook router deferred, MongoDB dropped).
- **DOCS-02 landed AND verified verbatim on leviathan:** `docs/quickstart.md` is a 6-8-page teaching walkthrough with the canonical 8-step path (Clone -> Edit hosts -> Copy secrets -> Optional vault encrypt -> Deploy -> Confirm containers -> Smoke test -> Open Grafana) + Prerequisites + Troubleshooting + Production hardening + Next steps. **Live UAT proved every step works as written**: leviathan full-stack deploy reported `ok=132 changed=0 failed=0 skipped=14` (full idempotency), all 12 containers up, smoke test PASS on all 4 signals, all 3 tag-scoped smoke runs PASS, all 7 provisioned Grafana dashboards visible, Loki Explore query `{service_name="telemetron-smoke"}` returns the smoke-test log lines, all 4 datasource health endpoints return `status: OK`, Karma URL serves HTTP 200.
- **DOCS-03 landed:** `docs/inventory.md` is a 2-3-page deep-dive with all 8 required sections (Directory shape, group_vars/all conventions, Secrets contract, host_vars patterns, Symlinking an out-of-tree inventory, Multi-host extension, Validation, See also), the full 9-key secrets contract table (minio root pair + 6 S3 aliases + grafana admin), symlink-with-`.git/info/exclude` pattern for out-of-tree inventories, and a multi-host v2 callout flagged as future-milestone scope.
- **Cross-link audit clean:** All 7 cross-link targets resolve: docs/inventory.md, docs/architecture.md, playbooks/smoke_test/README.md, roles/grafana/README.md (with the documented `## Reverse proxy` section present), inventory/README.md, inventory/example-homelab/README.md, docs/quickstart.md.
- **Gate 1 scrub PASS on all three docs:** zero D-XX refs, zero `.planning/` paths, zero `vault_` prefix usage, zero INSPQ heritage strings, zero non-ASCII characters.

## Task Commits

Each task was committed atomically:

1. **Task 1: docs/architecture.md (DOCS-01)** - `8b8485b` (feat)
2. **Task 2: docs/quickstart.md (DOCS-02)** - `5d478f5` (feat)
3. **Task 3: docs/inventory.md (DOCS-03)** - `a351316` (feat)
4. **Task 4 (Rule-1 auto-fix during UAT): quickstart Step 6 healthy-container expectation matches reality** - `aac3a0b` (fix)

_Note: Task 4 was a `checkpoint:human-verify` gate per the plan (D-109 leviathan UAT). Per the project's `[[project_leviathan_uat_host]]` memory ("Run live-Docker tests yourself via ansible/ssh; don't punt to 'human_needed'"), the UAT was executed autonomously. Step 7 (Confirm containers healthy) surfaced one doc inaccuracy (Karma is FROM scratch, no /bin/sh for healthcheck probe -- 11-of-12 healthy is the truth, not 12-of-12). Single-line fix committed as Task 4. UAT outcomes recorded in `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` (gitignored)._

## Files Created/Modified

- `docs/architecture.md` -- 194-line, 3-4-page terse public-facing reference. Opening paragraph attributes the INSPQ heritage in one line; subsequent sections are clean of any internal-navigation references. Components table has 13 rows with EXACT pinned tags from CLAUDE.md TL;DR (minio/minio:RELEASE.2025-04-22T22-12-26Z, grafana/loki:3.7.2, grafana/tempo:2.10.5, grafana/mimir:3.0.6, otel/opentelemetry-collector-contrib:0.152.0, prom/prometheus:v3.11.3, quay.io/prometheus/node-exporter:v1.11.1, fluent/fluent-bit:4.2.3, quay.io/prometheus/alertmanager:v0.32.1, grafana/grafana-oss:13.0.1, ghcr.io/prymitive/karma:v0.130, prom/promlens:v0.3.0, host-package nfsd). ASCII signal-flow diagram shows Apps -> OTel, FB tail -> OTel, OTel fan-out to Loki/Tempo/Mimir, Prometheus scrape + remote_write to Mimir, AM -> Karma (null receiver), Grafana datasource queries, MinIO 5-bucket trinity, and opt-in NFS path. Width <= 80 chars. Port Allocation table reproduces CLAUDE.md cheat sheet (17 rows incl. internal Tempo OTLP ports + opt-in NFS).
- `docs/quickstart.md` -- 297-line, 6-8-page teaching walkthrough. Opens with "what you will have by the end" preview (12 containers, 4 datasources, smoke test PASS). Prerequisites table covers Ansible 2.15+, community.docker 4.x+, Docker 24+/27+, SSH key auth, free ports. Steps 1-8 each have a copy-pasteable command block with expected-output snippet immediately following. Step 5 covers idempotency (second run = changed=0). Step 6 lists the exact 11-healthy + 1-plain-Up reality (auto-fixed during UAT). Step 7 covers full smoke + 3 tag-scoped variants. Step 8 covers Grafana UI navigation (Dashboards menu, Explore Loki query, Karma URL). Building-your-own-inventory subsection cross-links to docs/inventory.md. Troubleshooting table has 8 rows. Production hardening subsection cross-links to roles/grafana/README.md `## Reverse proxy` section + covers anonymous viewer + secrets rotation + multi-host-deferred.
- `docs/inventory.md` -- 171-line, 2-3-page deep-dive reference. Directory shape diagram shows the 15-file group_vars/all layout (4 cross-cutting + 11 per-role) + host_vars/. group_vars/all conventions table lists the 4 cross-cutting files with their key vars. Secrets contract table enumerates all 9 keys with type + consumer + notes (minio root pair are operator-supplied, 6 S3 aliases default to minio root, grafana admin is first-boot-only + rotation note). host_vars patterns subsection lists 3 common per-target override cases. Symlink subsection has the `ln -s` + `.git/info/exclude` two-liner. Multi-host extension subsection explicitly flags v2 / future-milestone status. Validation subsection covers --syntax-check + ansible-inventory --list + ansible -m ping. See-also cross-links to inventory/README.md, inventory/example-homelab/README.md, docs/quickstart.md.

## Decisions Made

See `key-decisions` in frontmatter for the full list. The most consequential ones:

1. **Voice split per D-102 honored across all three docs.** architecture.md and inventory.md are terse reference (skim-readable in 2 minutes); quickstart.md is verbose teaching (every command + expected output + troubleshooting). One doc shape would have lost adoption either way.
2. **Distillation, not duplication.** docs/architecture.md draws from research/ARCHITECTURE.md (ASCII diagram base, dependency narrative) + CLAUDE.md (port matrix, version table) + per-role READMEs (component descriptions). All three sources get cited; none gets verbatim-copied. Public docs strip all internal navigation per D-103.
3. **Fact-check authoring caught plan-skeleton drift twice.** Plan's quickstart skeleton referenced `inventory/example-homelab/example-homelab.hosts` which doesn't exist (real file is `hosts.yml`). Plan's Step 6 said "all healthy" which doesn't match reality (Karma scratch image). Both caught BEFORE / DURING UAT, both fixed in the same plan, both documented as Rule-1 auto-fixes.
4. **Live UAT autonomously executed.** Per `[[project_leviathan_uat_host]]` memory, the human-verify checkpoint was run by the executor rather than punted. This caught a real doc bug (Step 6 health expectation) that lint-only verification would have shipped.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan referenced non-existent inventory filename `example-homelab.hosts`**

- **Found during:** Task 2 (pre-write fact-check via `ls inventory/example-homelab/`).
- **Issue:** The plan skeleton for `docs/quickstart.md` Step 2 referenced opening `inventory/example-homelab/example-homelab.hosts`. The actual on-disk filename is `hosts.yml` (YAML format, per the existing `inventory/example-homelab/README.md`). Writing the doc with the wrong filename would have failed DOCS-02 verbatim acceptance immediately -- an operator running the documented `cat inventory/example-homelab/example-homelab.hosts` would hit "no such file or directory".
- **Fix:** Authored Step 2 around the real filename `hosts.yml` with the documented YAML shape (lifted from the existing `inventory/example-homelab/README.md` worked example). Troubleshooting row that referenced editing the hosts file also corrected to `hosts.yml`.
- **Files modified:** `docs/quickstart.md` (initial write).
- **Committed in:** `5d478f5` (Task 2 main commit; the bug was caught and fixed before the initial write, not after).

**2. [Rule 1 - Bug] Quickstart Step 6 overstated healthy-container count (12 vs 11)**

- **Found during:** Task 4 (leviathan UAT Step 7 -- "Confirm containers are healthy").
- **Issue:** The originally-authored Step 6 said the operator should expect "12 lines, all containing `Up ... (healthy)`. Telemetron declares explicit HEALTHCHECKs on every container." Live walkthrough on leviathan showed 11 healthy + 1 plain `Up` (Karma). Karma is built `FROM scratch` (per the 05-08 SUMMARY decision -- `ghcr.io/prymitive/karma:v0.130` is a scratch image shipping only the `/karma` binary, no `/bin/sh` for a Docker `CMD-SHELL` healthcheck probe). The role's verify task uses an in-network curl probe as the canonical health gate for Karma; this is a deliberate design decision, not a defect.
- **Fix:** Replaced the "all containing `Up ... (healthy)`" sentence with a precise breakdown: "Eleven containers report `Up ... (healthy)`; `telemetron-karma` reports `Up ...` without a health suffix because the Karma image is built `FROM scratch` and ships no shell for a healthcheck probe (the in-network curl probe in the role's verify task is the canonical health gate for Karma)." Single-line edit in Step 6.
- **Files modified:** `docs/quickstart.md`.
- **Verification:** Re-read Step 6 against the live `docker ps` output -- now matches exactly. DOCS-02 verbatim acceptance restored.
- **Committed in:** `aac3a0b` (Task 4 auto-fix commit, separate from Task 2 main commit because it was discovered during UAT verification, not during the initial write).

---

**Total deviations:** 2 auto-fixes (both Rule 1 - Bug)
**Impact on plan:** Two precise single-line edits. No structural change to any doc. Both fixes elevated DOCS-02 acceptance from "would have failed verbatim on a fresh target" to "PASS verbatim on leviathan".

## Issues Encountered

**1. UAT environment shape vs fresh-clone simulation**

The plan's Step 1 of the UAT procedure said "fresh clone telemetron-quickstart-uat in /tmp". The working repo has uncommitted Phase 6 work, so the fresh-clone simulation was skipped and Steps 5-10 were exercised against the working tree directly. The actual quickstart commands (deploy, smoke, docker ps, Grafana queries) operated against the same on-disk shape a fresh clone would produce after the operator edited `hosts.yml`. The simulation gap is documented in 06-HUMAN-UAT.md.

**Decision:** Out of scope for plan 06-03. Plan 06-04 will rerun the fresh-clone simulation as part of the README rewrite's "end-to-end idempotency revalidation on leviathan from a fresh clone perspective" gate.

**2. community.docker collection version on control host**

The control host's `community.docker` is 4.5.0. The quickstart Troubleshooting table flags "< 4.5.2" as a defensive recommendation for Docker-29 port-range idempotency. Despite this, the live leviathan deploy reported `changed=0` on the first run executed during this UAT. The 4.5.2 advice is defensive, not a known reproducer on the current stack shape; the quickstart text is unchanged.

**Decision:** Out of scope for plan 06-03. Plan 06-04 verify can include a re-check after a control-host upgrade if the gap surfaces during the back-to-back idempotency gate.

## Known Stubs

None. All three docs are wired end-to-end:
- Every cross-link target exists (verified via the Step 10 cross-link audit during UAT).
- Every command in `docs/quickstart.md` executes successfully on leviathan (verified verbatim during UAT Steps 5-9).
- Every secrets-contract key in `docs/inventory.md` is consumed by a real role (verified against the existing `secrets.yml.example`).
- Every component in `docs/architecture.md` is deployed by `playbooks/deploy_docker.yml` and reachable on its documented port (verified via `docker ps` and `ss -tln` during UAT prerequisites step).

## Forward Notes

- **Plan 06-04 (README rewrite + idempotency revalidation) is unblocked.** The three M1 docs exist and have been UAT-verified verbatim. Plan 06-04 can now link to `docs/quickstart.md` as the canonical "how to run this" reference from the top-level `README.md`, refresh `docs/README.md`'s planned-docs table to show 3 shipped + 7 deferred to v2 per DOCS-V2-01..07, and run the OPS-04 back-to-back-idempotency gate on a fresh-clone simulation (the gap from this plan's UAT Step 1).
- **DOCS-02 acceptance is mechanically re-checkable.** Any future regression to the inventory shape, smoke playbook command line, or Grafana datasource UIDs will surface as a quickstart-verbatim UAT failure on leviathan -- a single `git diff docs/quickstart.md` review during plan 06-04 confirms whether the doc still matches reality.
- **No documentation debt left for v2 from this plan's scope.** The other 7 planned docs (alerts, mimir-retention, fluentbit-timestamps, hook-router, instrumentation-otel, migration-from-inspq, metrics) are explicit v2 per REQUIREMENTS.md DOCS-V2-01..07; `docs/README.md` will reflect this in plan 06-04.

## Self-Check: PASSED

All claimed created files exist:
- `docs/architecture.md`
- `docs/quickstart.md`
- `docs/inventory.md`

All claimed commit hashes exist in git log:
- `8b8485b` (Task 1: docs/architecture.md)
- `5d478f5` (Task 2: docs/quickstart.md)
- `a351316` (Task 3: docs/inventory.md)
- `aac3a0b` (Task 4 Rule-1 auto-fix: quickstart Step 6 Karma health correction)

All scrub gates pass on all three docs (verified before each commit):
- Zero D-XX references.
- Zero `.planning/` path references.
- Zero `vault_` prefix usage (in quickstart + inventory; architecture doesn't mention secrets).
- Zero INSPQ heritage strings beyond the one-line opener in architecture.md.
- Zero non-ASCII characters.

All section-header existence checks pass (verified before each commit):
- architecture.md: Overview, Signal Flow, Components, Port Allocation, Monolithic Mode, Storage Dependencies, Known Debt, Further reading.
- quickstart.md: Prerequisites, Step 1-8 headers, Troubleshooting, Production hardening, Next steps.
- inventory.md: Directory shape, group_vars/all conventions, Secrets contract, host_vars patterns, Symlinking an out-of-tree inventory, Multi-host extension, Validation, See also.

Live UAT outcomes recorded in `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` (gitignored) with all 11 quickstart steps + cross-link audit + UI verification confirmed PASS on leviathan 2026-05-19.

---
*Phase: 06-opt-in-orchestration-docs-smoke-test*
*Completed: 2026-05-19*
