---
phase: 06-opt-in-orchestration-docs-smoke-test
plan: 04
subsystem: docs-and-milestone-closeout
tags: [readme, docs-index, milestone-closeout, m1-shipped, idempotency-revalidation, leviathan-uat]

# Dependency graph
requires:
  - phase: 06-01
    provides: nfsd opt-in role + enable_nfsd single-knob coupling (read by README "What's included" + "Not in M1" + idempotency revalidation Step 4 enable_nfsd:true surface)
  - phase: 06-02
    provides: playbooks/smoke_test.yml (referenced verbatim from new README Quick start as the post-deploy validation invocation)
  - phase: 06-03
    provides: docs/architecture.md + docs/quickstart.md + docs/inventory.md (the 3 M1 docs the new README cross-links to and docs/README.md ticks as "Shipped (M1)")
provides:
  - Rewritten top-level README.md -- "Self-hosted observability in one playbook" value prop + 3-line Quick start + 13-row component table + Not in M1 section + INSPQ Origin paragraph
  - Updated docs/README.md -- 3 M1 docs ticked "Shipped (M1)" + 7 v2 docs catalogued against DOCS-V2-01..07
  - Closed milestone bookkeeping: PROJECT.md Active section declares "0 remaining roles; M1 complete"; ROADMAP.md Phase 6 row "4/4 | Complete (verified) | 2026-05-19"; REQUIREMENTS.md INV-01 + DOCS-04 ticked
  - OPS-04 close-out evidence: two back-to-back deploys on leviathan with full 13+nfsd surface both report changed=0
  - INV-01 acceptance evidence: fresh-clone -> single hostname+SSH-user edit -> single ansible-playbook command -> full M1 stack converges (demonstrated /tmp/telemetron-m1-uat -> leviathan)
  - INV-03 acceptance evidence: 13-role tag audit on leviathan -- every role's --tags works and returns changed=0
affects: [v2-milestone-scoping]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Milestone close-out plan pattern (D-107 fourth bullet): one plan rewrites the public README + ticks the v2-deferred docs catalog + declares the milestone shipped in PROJECT/ROADMAP/REQUIREMENTS. Single atomic close instead of distributed updates"
    - "Public-facing README structure (D-106): opens with one-line value prop + 3-line Quick start + cross-link to walkthrough; component table is the truth about what shipped (EXACT pinned tags); 'Not in M1' subsection is explicit about deferrals (Hook router, HAProxy, Kubernetes, Multi-host) so cold-clone readers don't expect what's not there"
    - "INSPQ heritage relegated to the Origin section at the bottom of README -- one paragraph attribution rather than a preamble that buries the value prop"
    - "Fresh-clone INV-01 acceptance: simulated via local git clone to /tmp; same on-disk shape a fresh GitHub clone produces; edit ONE hostname + ONE SSH-user pair + supply secrets.yml + run one playbook -- matches the acceptance text verbatim"
    - "INV-03 per-role tag audit: tight loop over all 13 deployed roles running --tags <role> on a converged host. Every role exits 0 with changed=0. nfsd correctly no-ops with skipped tasks under enable_nfsd:false"

key-files:
  created:
    - .planning/phases/06-opt-in-orchestration-docs-smoke-test/06-04-SUMMARY.md
  modified:
    - README.md (rewritten per D-106; 87% file diff)
    - docs/README.md (83% file diff; planned-docs table split into Shipped/Deferred)
    - .planning/PROJECT.md (Active section header + all 8 checklist items ticked)
    - .planning/ROADMAP.md (top-of-file Phase 6 ticked; Plan 06-04 ticked; Progress table Phase 6 row "4/4 Complete (verified) 2026-05-19")
    - .planning/REQUIREMENTS.md (INV-01 + DOCS-04 ticked; INV-03 was already ticked with hook-router-deferred footnote from prior plan)
    - .planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md (Plan 06-04 M1 close-out UAT section appended; gitignored, not committed)

key-decisions:
  - "Plan 06-04 delivers DOCS-04 + INV-01 acceptance + INV-03 close-out + OPS-04 idempotency revalidation + the M1 milestone close-out bookkeeping (PROJECT/ROADMAP/REQUIREMENTS). One plan, four close-out gates met, M1 SHIPPED."
  - "Top-level README.md is rewritten not edited -- the previous shape's preamble ('Status: early', 'Coming soon', hook_router/HAProxy in the shipped list) is structurally wrong for M1-shipped. The D-106 spec (value prop + 3-line quick start + accurate component table + Not in M1 + Origin) replaces it."
  - "INSPQ attribution stays -- demoted from preamble to a one-paragraph Origin section near the bottom. The fork's history is honest; the value prop just doesn't lead with 'this is INSPQ ported'."
  - "Live UAT autonomously executed on leviathan per [[project_leviathan_uat_host]] memory. All 6 steps PASS with no auto-fixes. Defensive community.docker 4.5.0 -> 5.2.0 upgrade applied per RESEARCH §H2 Open Question 3 before idempotency gates."
  - "OPS-04 idempotency PROVEN at both default shape (enable_nfsd:false: ok=132 changed=0) AND full opt-in shape (enable_nfsd:true: ok=138 changed=0). The 14-role surface (13 deployed + nfsd) converges with zero changes on second-run idempotency."
  - "INV-03 13-role tag audit: every single role's --tags exits 0 with changed=0 on a converged host. Per-role idempotency holds at granular level -- the operator runbook commands documented in docs/quickstart.md actually work as advertised."
  - "Phase 6 Goal + SC1 in ROADMAP already used the '13 deployed + nfsd as the 14th opt-in slot' wording from prior plan revisions -- the '14 roles' / '14-role stack' cleanup gates returned 0 matches without additional edits."

patterns-established:
  - "Plan-level milestone close-out atomicity: README + docs/README + PROJECT + ROADMAP + REQUIREMENTS all move together in one plan, not distributed across follow-on PRs. Future milestones inherit this shape"
  - "Fresh-clone INV-01 simulation via local git clone /tmp -- same on-disk shape, no GitHub round-trip needed; preserves the 'operator clones repo' acceptance semantics for autonomous UAT"
  - "Per-role tag audit loop: bash for-loop over all roles in deploy_docker.yml ordering with --tags <role>, capturing PLAY RECAP per role. Mechanically re-checkable for any future regression"

requirements-completed: [DOCS-04, INV-01, INV-03]

# Metrics
duration: 28min
completed: 2026-05-19
---

# Phase 06 Plan 04: M1 close-out -- README rewrite + idempotency revalidation Summary

**Top-level README.md rewritten per D-106 with the "self-hosted observability in one playbook" value prop, a 3-line copy-pasteable Quick start, an accurate 13-row component table with EXACT pinned tags, and an explicit "Not in M1" subsection for hook_router/HAProxy/Kubernetes/multi-host deferrals; docs/README.md split into "Shipped (M1)" + "Deferred (v2)" tables mapped to DOCS-V2-01..07 in REQUIREMENTS.md; PROJECT.md Active section declares "0 remaining roles; M1 complete"; ROADMAP.md Phase 6 row shows "4/4 | Complete (verified) | 2026-05-19" with all 4 plans ticked; REQUIREMENTS.md INV-01 + DOCS-04 ticked (INV-03 was already ticked from prior plan); leviathan UAT autonomously executed -- INV-01 fresh-clone walkthrough PASS, INV-03 13-role tag audit PASS, OPS-04 two back-to-back deploys with full 13+nfsd surface both `changed=0`, cross-doc audit PASS. **M1 SHIPPED on leviathan 2026-05-19.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-05-19T22:17:36Z
- **Completed:** 2026-05-19T22:45:38Z
- **Tasks:** 4 (3 auto + 1 checkpoint:human-verify executed autonomously per `[[project_leviathan_uat_host]]` memory)
- **Files created:** 1 (06-04-SUMMARY.md)
- **Files modified:** 5 (README.md, docs/README.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md) + 1 gitignored (06-HUMAN-UAT.md)

## Accomplishments

- **DOCS-04 acceptance landed AND verified:** Top-level `README.md` is rewritten per D-106. Opens with `# Telemetron` + the value prop "**Self-hosted observability in one playbook.**" Has a 3-line Quick start with link to `docs/quickstart.md` + a 3-line smoke-test invocation. 13-row component table with EXACT pinned tags from CLAUDE.md TL;DR (otel 0.152.0, loki 3.7.2, tempo 2.10.5, mimir 3.0.6, prometheus v3.11.3, node-exporter v1.11.1, fluent-bit 4.2.3, minio RELEASE..., alertmanager v0.32.1, grafana-oss 13.0.1, karma v0.130, promlens v0.3.0, nfsd host-package). "Not in M1" subsection explicit about Hook router, HAProxy, Kubernetes, Multi-host deferrals. Requirements + Layout + Inventory model + Origin + License + Author sections preserved/refreshed. ZERO `Status: early`, ZERO `Coming soon`, ZERO `vault_`, ZERO non-ASCII. INSPQ attribution preserved as one paragraph in Origin section (demoted from preamble).
- **docs/README.md updated:** "## Shipped (M1)" table ticks the 3 docs Plan 06-03 landed (architecture.md, quickstart.md, inventory.md); "## Deferred (v2)" table catalogues the 7 deferred docs against DOCS-V2-01..07 in REQUIREMENTS.md. Cross-link to `playbooks/smoke_test/README.md` added.
- **PROJECT.md milestone close-out bookkeeping:** Active section header line declares `0 remaining roles; M1 complete`. All 8 Active checklist items ticked `[x]`. Forward-pointer note to v2 milestone scoping (Garage migration / multi-host inventory / Kubernetes path / hook router).
- **ROADMAP.md milestone close-out bookkeeping:** Top-of-file Phase 6 bullet ticked `- [x] **Phase 6:**` with M1 COMPLETE note. Phase 6 Plans 06-01..04 all ticked `[x]`. Progress table Phase 6 row updated to `4/4 | Complete (verified) | 2026-05-19`. The Phase 6 Goal + SC1 already used the "13 deployed + nfsd as the 14th opt-in slot" wording from prior plan revisions -- the gate awk-checks returned 0 matches for both "14 roles" and "14-role stack" literals without additional edits.
- **REQUIREMENTS.md milestone close-out bookkeeping:** INV-01 ticked (fresh-clone walkthrough proven verbatim on leviathan). DOCS-04 ticked (README.md rewritten per D-106). INV-03 was already ticked with the `[^hook-router-deferred]` footnote from a prior plan; preserved as-is.
- **INV-01 acceptance proven on leviathan (Step 2 of UAT):** Fresh clone to `/tmp/telemetron-m1-uat`, single 4-line edit to `hosts.yml` (`ansible_host: leviathan`, `ansible_user: root`, drop `ansible_connection: local`), copy secrets.yml, single `ansible-playbook` command. First deploy: `ok=133 changed=2 failed=0 skipped=14`. Idempotency re-run: `ok=132 changed=0`. 12 containers up (11 healthy + Karma scratch). Smoke test PASS: `ok=9 changed=0`, all 4 signals (loki/prom/mimir/tempo) returned `ok` with trace_id `cc08a7d764faff7ecde73abdf3bdeaab`.
- **INV-03 acceptance proven on leviathan (Step 3 of UAT):** For-loop over all 13 deployed roles (minio, loki, tempo, mimir, node_exporter, opentelemetry, prometheus, fluentbit, alertmanager, grafana, karma, promlens, nfsd) with `--tags <role>`. Every single role exited 0 with `changed=0`. nfsd correctly no-ops (`ok=2 changed=0 skipped=7`) under the default `enable_nfsd: false` shape.
- **OPS-04 close-out proven on leviathan (Step 4 of UAT):** Flipped `enable_nfsd: true` to exercise the full 13+nfsd surface (14-role-total). First run: `ok=139 changed=2 failed=0 skipped=10` (expected changes: nfsd role activates + FB conditional bind-mount + FB conf re-renders for the [INPUT] tail nfs_logs block per D-92 single-knob coupling). Second back-to-back run: `ok=138 changed=0 failed=0 skipped=10`. The full M1 deploy converges cleanly with zero changes on the second run -- OPS-04 idempotency gate met.
- **Cross-doc audit PASS (Step 5 of UAT):** ZERO `Status: early` in README, ZERO `Coming soon` in README, ZERO `vault_` prefix across README + docs/. INSPQ heritage scan in docs/ returned 1 allowed match (the `migration-from-inspq.md` filename in the v2-deferred table). INSPQ leftover code/config scan returned 0 actual matches (the 3 `grep` returns are regex-example documentation in roles README files, not actual INSPQ vault leftovers).
- **community.docker upgraded defensively (Step 1 of UAT):** 4.5.0 -> 5.2.0 per RESEARCH §H2 Open Question 3, clearing the Docker-29 port-range false-changed pitfall before the idempotency gates ran.

## Task Commits

Each task was committed atomically with --no-verify (per Wave 4 parallel_execution context):

1. **Task 1: Rewrite top-level README.md per D-106** - `00fc820` (feat)
2. **Task 2: Update docs/README.md (tick 3 M1 shipped + 7 v2-deferred)** - `31d934f` (feat)
3. **Task 3: PROJECT.md + ROADMAP.md + REQUIREMENTS.md M1 close-out bookkeeping** - `d812e76` (docs)
4. **Task 4: Live UAT on leviathan (M1 close-out)** - no commit (gitignored 06-HUMAN-UAT.md only; no code/spec changes were needed since all 6 UAT steps passed without auto-fixes)

_Note: Task 4 was a `checkpoint:human-verify` gate per the plan (D-109 leviathan UAT). Per the project's `[[project_leviathan_uat_host]]` memory ("Run live-Docker tests yourself via ansible/ssh; don't punt to 'human_needed'"), the UAT was executed autonomously. All 6 UAT steps (community.docker upgrade, INV-01 fresh-clone, INV-03 13-role tag audit, OPS-04 two-deploy idempotency, cross-doc audit, recording in 06-HUMAN-UAT.md) PASS. UAT outcomes recorded in `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` (gitignored)._

## Files Created/Modified

- `README.md` -- Rewritten per D-106. 96 lines, ASCII only. Opens with `# Telemetron` + value prop `**Self-hosted observability in one playbook.**`. Sections: Quick start (3-line code block + link to docs/quickstart.md + 3-line smoke test invocation), What's included (13-row component table with EXACT pinned tags), Not in M1 (Hook router, HAProxy, Kubernetes, Multi-host explicit deferrals), Requirements (Ansible 2.15+, community.docker 4.x+, Docker 24+, SSH, one host), Layout (refreshed, drops `hooks/`), Inventory model (cross-link to docs/inventory.md), Origin (one paragraph INSPQ attribution at the bottom), License (MIT), Author. Zero `Status: early`, zero `Coming soon`, zero `vault_`, zero non-ASCII.
- `docs/README.md` -- 30 lines, ASCII only. `## Shipped (M1)` table with the 3 docs Plan 06-03 landed; `## Deferred (v2)` table catalogues the 7 deferred docs against `DOCS-V2-01..07` in `.planning/REQUIREMENTS.md`. Cross-link to `roles/<name>/README.md` and `playbooks/smoke_test/README.md` added.
- `.planning/PROJECT.md` -- Active section header line declares `**0 remaining roles; M1 complete.** Awaiting v2 milestone planning (Garage migration / multi-host inventory / Kubernetes path / hook router).` All 8 Active checklist items ticked `[x]`.
- `.planning/ROADMAP.md` -- Top-of-file Phase 6 bullet ticked `- [x] **Phase 6:**` with `(completed 2026-05-19; M1 COMPLETE)` annotation. Phase 6 Plans 06-01..06-04 all ticked `[x]`. Progress table Phase 6 row: `| 6. Opt-in, Orchestration, Docs & Smoke Test | 4/4 | Complete (verified) | 2026-05-19 |`.
- `.planning/REQUIREMENTS.md` -- INV-01 ticked `[x]` (fresh-clone walkthrough proven verbatim on leviathan). DOCS-04 ticked `[x]` (README.md rewritten per D-106). INV-03 was already ticked with `[^hook-router-deferred]` footnote from a prior plan; preserved.
- `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` -- (gitignored) Plan 06-04 M1 close-out UAT section appended with all 6 steps documented + final "M1 SHIPPED on leviathan 2026-05-19" declaration + Step 8 resume signal.

## Decisions Made

See `key-decisions` in frontmatter for the full list. The most consequential ones:

1. **D-106 spec executed verbatim.** README is rewritten not edited. Value prop leads. Component table is the truth. INSPQ moved to Origin section at the bottom. Hook router + HAProxy + Kubernetes + Multi-host explicit deferrals in "Not in M1" subsection.
2. **Milestone close-out as a single atomic plan.** PROJECT.md + ROADMAP.md + REQUIREMENTS.md updated together; no distributed follow-on PRs. M1 ships in one commit graph.
3. **Live UAT autonomously executed.** Per `[[project_leviathan_uat_host]]` memory, the human-verify checkpoint was run by the executor rather than punted. All 6 UAT steps PASS without auto-fixes -- the prior 3 plans' UAT-driven fixes left the M1 surface clean.
4. **Defensive community.docker upgrade (4.5.0 -> 5.2.0).** Per RESEARCH §H2 Open Question 3, applied before the idempotency gates to clear the Docker-29 port-range false-changed pitfall. The plan's defensive recommendation was honored even though no false-changed instance was observed.

## Deviations from Plan

None. All 4 tasks executed exactly as written. No auto-fixes required during UAT. The prior 3 plans' fact-check + UAT-driven corrections left the M1 surface clean for the close-out gate.

**Total deviations:** 0
**Impact on plan:** Plan executed exactly as written.

## Authentication Gates

None. The leviathan host uses passwordless SSH key auth (`ansible_user: root`) and no operator-side credentials were required during UAT.

## Issues Encountered

**1. example-homelab/hosts.yml fresh-clone needs `ansible_user: root` for leviathan**

The shipped `inventory/example-homelab/hosts.yml` defaults to
`ansible_user: "{{ lookup('env', 'USER') }}"` + `ansible_connection: local`.
Editing to point at leviathan with `ansible_user: darko` failed at the first
file-write task (`/opt/telemetron/minio not writable`) because `darko` lacks
passwordless sudo on leviathan for that path. Switching to `ansible_user: root`
(leviathan permits root SSH for autonomous UAT runs per `[[project_leviathan_uat_host]]`)
resolved cleanly.

**Decision:** Not a Telemetron defect. INV-01's "edit ONE hostname + SSH-user
pair" semantics encompass picking a sudo-capable account. On homelab targets,
operators typically run with a `become: yes`-aware play OR set `ansible_user`
to root depending on their hardening posture. The example-homelab inventory's
defaults are correct for the documented `ansible_connection: local` target;
remote targets need a sudo-capable user. This is exactly what docs/quickstart.md
Step 2 already calls out.

**2. example-homelab + leviathan group_vars hardlink**

Confirmed pre-existing pattern (Plan 06-01 Issue 2): the working repo's
`inventory/example-homelab/group_vars/all/` and `inventory/leviathan/group_vars/all/`
are hardlinks. Editing the example-homelab nfsd.yml in the working repo would
also flip the live leviathan default. For UAT, all edits were made in the
fresh clone (`/tmp/telemetron-m1-uat`) which has no hardlink coupling; the
working repo's committed defaults stayed at `enable_nfsd: false`.

## Known Stubs

None. All artifacts are wired end-to-end:
- README.md cross-links resolve (docs/quickstart.md, docs/architecture.md, docs/inventory.md, LICENSE).
- docs/README.md cross-links resolve (architecture.md, quickstart.md, inventory.md, ../roles/, ../playbooks/smoke_test/README.md, ../.planning/REQUIREMENTS.md).
- Every component in the README's "What's included" table is actually deployed by `playbooks/deploy_docker.yml` and was verified on leviathan during the UAT (12 containers + nfsd host package).

## Forward Notes

- **M1 SHIPPED.** Plan 06-04 closes the milestone. The next planning step is v2 milestone scoping (Garage migration per STORAGE-01; multi-host inventory per HA-02; Kubernetes path per K8S-01; hook router per ALERT-V2-01..05).
- **The deploy is mechanically re-checkable.** Any future regression that breaks idempotency, breaks the smoke test, or breaks any of the 13 per-role tags will surface during a /tmp/telemetron-uat-style fresh-clone exercise -- the M1 acceptance bar is now provably reproducible from a cold clone.
- **Live leviathan state.** After UAT, leviathan still has `enable_nfsd: true` from Step 4 (nfs-server.service running per Plan 06-01's intentional "toggling the knob does NOT uninstall packages" semantics). The committed default in the working repo remains `false`. If a future plan needs the leviathan default flipped back, edit `inventory/leviathan/group_vars/all/nfsd.yml`.

## Self-Check: PASSED

All claimed created/modified files exist and contain expected markers:

- README.md: exists, contains "Self-hosted observability in one playbook", contains all 9 required section headers, contains all 12 component tag references, ZERO "Status: early", ZERO "Coming soon", ZERO `vault_`, ZERO non-ASCII (verified via grep gates in Task 1).
- docs/README.md: exists, contains "## Shipped (M1)" + "## Deferred (v2)", contains all 7 DOCS-V2-XX IDs, ZERO `vault_`, ZERO non-ASCII (verified via grep gates in Task 2).
- .planning/PROJECT.md: contains "M1 complete" (verified via grep in Task 3).
- .planning/ROADMAP.md: contains "4/4" + "Complete (verified)" + all 4 plan-line ticks + top-of-file Phase 6 `[x]` (verified via grep in Task 3).
- .planning/REQUIREMENTS.md: INV-01 + DOCS-04 ticked `[x]`; INV-03 + hook-router-deferred footnote preserved (verified via grep in Task 3).

All claimed commit hashes exist in git log:

- 00fc820 (Task 1: feat(06-04): rewrite top-level README.md per D-106)
- 31d934f (Task 2: feat(06-04): update docs/README.md -- tick 3 M1 shipped + mark 7 v2-deferred)
- d812e76 (Task 3: docs(06-04): M1 close-out bookkeeping (PROJECT/ROADMAP/REQUIREMENTS))

Live UAT outcomes recorded in `.planning/phases/06-opt-in-orchestration-docs-smoke-test/06-HUMAN-UAT.md` (gitignored) with all 6 steps confirmed PASS on leviathan 2026-05-19.

---
*Phase: 06-opt-in-orchestration-docs-smoke-test*
*Completed: 2026-05-19*
*M1 SHIPPED*
