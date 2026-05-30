# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0.0 — M1 — LGTM observability plane on Docker

**Shipped:** 2026-05-19 (on `leviathan`, Ubuntu 24.04, Docker 29.1.3)
**Phases:** 7 active (1, 2, 3, 4, 04.1, 5, 6) + 4 backlog 999.x | **Plans:** 26 | **Tasks:** 110
**Commits:** 171 over 4 days (2026-05-16 → 2026-05-19) | **Code+docs:** ~12,254 LOC across 139 files

### What Was Built

- **13 Ansible roles + 1 opt-in (nfsd as 14th slot)** ported from upstream INSPQ to clean-slate English-only MIT, each passing the 8 cross-cutting port-acceptance gates in `roles/README.md`.
- **Three monolithic backends** with explicit S3 wiring to MinIO: Loki 3.7.2, Tempo 2.10.5, Mimir 3.0.6 — all on `-target=all` plus the conditional-HEALTHCHECK `-version` proxy pattern.
- **OTel Collector Contrib 0.152.0 as single ingest gateway** — OTLP `:4317/:4318` fanning to all three backends; Tempo's native OTLP receivers banished to internal-only alt ports `:14317/:14318` to clear the port clash.
- **Grafana 13.0.1 OSS with 4 hardcoded-UID datasources + 7 curated dashboards** + trace↔log correlation via Tempo `tracesToLogsV2` and Loki `derivedFields trace_id`.
- **`playbooks/smoke_test.yml`** — synthetic OTLP log+metric+trace asserted through Grafana's datasource-proxy in a 60s/signal budget. Passes on leviathan including loud-failure mode and `--tags log/metric/trace` single-signal runs.
- **Three operator docs against the booted stack** — `docs/architecture.md` (3-4pg reference), `docs/quickstart.md` (6-8pg walkthrough proven verbatim on a fresh host), `docs/inventory.md` (2-3pg deep-dive).
- **Top-level README rewritten** with the "self-hosted observability in one playbook" value prop, copy-pasteable 3-line Quick start, accurate 13-row component table with EXACT pinned tags, explicit "Not in M1" subsection for deferrals.

### What Worked

- **Plan-Phase Then Execute-Phase rhythm.** The GSD `/gsd:plan-phase` → `/gsd:execute-phase` loop kept context costs predictable: orchestrator stayed lean, subagents got fresh context, plans landed without context blowup even on the 8-plan Phase 5 UI Plane wave.
- **Cross-cutting gates as the de-facto regression net.** Establishing all 8 port-acceptance gates (`grep-clean / image-pin / secrets-discipline / idempotency / healthcheck+restart / README-schema / label-stamp / parent-dir bind-mount`) in `roles/README.md` during Phase 1 paid off every phase after: each new role port had to satisfy the existing list before it could merge. Gate 8 (parent-dir bind mounts) was added mid-M1 after a real bug, and every subsequent role inherited the convention.
- **Conditional-HEALTHCHECK pattern (Outcome B: `-version` proxy).** Reusable across distroless / from-scratch images that ship no `/bin/sh` (Tempo, Mimir, Karma). Plan 02-02 invented the pattern; Plans 02-03, 05-02 reused it verbatim.
- **D-43 dual-exporter forward-compat in OTel Collector.** Declaring BOTH `prometheus` AND `prometheusremotewrite` exporters unconditionally + flipping via a Jinja conditional on a single knob means future "rip out the Prometheus middle-tier" requires no role rewrite.
- **Live-UAT on leviathan as the quality bar.** Per CLAUDE.md ("boots on Rock's homelab Docker host"), automated CI was explicitly out of scope. The 4-day ship cadence was only possible because UAT was "deploy + eyeball + auto-fix" rather than "build a molecule harness."
- **Decimal phase 04.1 (INSERTED) for the vault_ prefix rename.** Catching a naming convention drift mid-M1 and addressing it as an inserted phase rather than a sprawling rewrite kept Phase 5 unblocked and the rename atomic across 4 roles + `secrets.yml.example` + doc cascade.

### What Was Inefficient

- **Two famous bugs only caught during live UAT** — both well-documented ecosystem patterns (ansible/ansible#45272 auto_remove race + moby/moby#6011 single-file bind-mount stale-inode) that an experienced reviewer might have flagged at plan-write time. Net: two gap-closure plans (04-02 + 05-04 family) that wouldn't have been needed.
- **Initial milestone version pickup grabbed the Alertmanager pin (`v0.32.1`)** instead of M1. `gsd-sdk query init.execute-phase` looked at the wrong field. Required manual disambiguation during milestone close.
- **PROJECT.md "Pending (M1)" Key Decisions sat stale.** All 11 decisions stayed at `— Pending (M1)` through the whole milestone instead of being flipped to `✓ Good` at phase boundaries. Fine to clean up in bulk at milestone close, but the table was misleading mid-stream.
- **Stale verification statuses (`human_needed` on phases 1/2/3) were never flipped.** Verifier honestly said "live spot-checks need a Docker host" → stack later booted on leviathan via 06-HUMAN-UAT.md → no one updated the upstream phase VERIFICATION.md files. Surfaced as 6 false-positive items in the pre-close audit.
- **PromLens v0.3.0 ported despite being a known dead end.** Shipped only for upstream parity. With hindsight: explicitly drop in M1 and add the deprecation note to docs/architecture.md instead of carrying a third UI surface.

### Patterns Established

- **Anti-pattern: single-file rendered-config bind mounts.** Banned project-wide via Gate 8 in `roles/README.md` after moby/moby#6011 surfaced. All future role ports inherit the parent-directory mount convention.
- **Anti-pattern: `community.docker.docker_container` with `auto_remove:true + detach:false` for verify probes.** Banned in favor of `community.docker.docker_container_exec` polling against the live container with `until:/retries:/delay:`. The race (ansible/ansible#45272 + #47673) is silent and intermittent.
- **Naming convention: role-namespace + suffix only.** No decorative `vault_*` prefix on sensitive variables — the prefix added no value and implied tooling enforcement Ansible doesn't actually provide. Per [[feedback-no-decorative-convention-prefixes]] in user memory. Codified via D-90 and shipped in Phase 04.1.
- **Naming convention: underscore by default, hyphen only where DNS-strict.** Per [[feedback-naming-separator]]. Container names + hostnames + K8s resources get `-`; Docker volumes + Ansible vars get `_`.
- **Phase 4/5 verify pattern: `docker_container_exec` + Ansible `until:/retries:/delay:` polling.** Eliminates the auto_remove race AND handles async dispatch races (amtool alert query, prometheus reload). Reusable for any "wait for stack to converge" probe.
- **Hardcoded Grafana datasource UIDs (`prometheus / loki / tempo / mimir`).** Auto-generated UIDs break every bundled dashboard on a fresh install. The `_rewrite_uids.py` walker normalizes upstream dashboards to the hardcoded set; Gate 9.5 in `roles/grafana/tasks/verify.yml` blocks unresolved `"uid": "$..."` panel refs at deploy time.
- **Docker-label promotion via FB Lua filter without Docker socket access.** `string.match` on `/var/lib/docker/containers/<id>/config.v2.json` reads container metadata read-only from the host filesystem — promotes `org.telemetron.{service,job}` labels to Loki labels without the docker-socket-proxy security surface.

### Key Lessons

1. **Live UAT IS the validation surface for M1; the verifier punts to it intentionally.** Static gates are a necessary precondition but not sufficient. Build the muscle to flip `human_needed → passed` (with the live-UAT evidence link) as soon as the stack boots, not at milestone-close cleanup time.
2. **Two ecosystem bugs (ansible/ansible#45272 + moby/moby#6011) cost roughly a day each.** For v2: scan plans against a "known anti-patterns" checklist before plan-check; both these bugs have been famous in the Ansible+Docker community for years.
3. **Decimal phase insertion is the right release valve for naming/convention drift.** Rather than letting a rename sprawl across an in-flight phase, freeze the in-flight phase, insert a phase, ship the rename atomically, then unblock.
4. **`commit_docs: false` + 43 force-tracked `.planning/*` files works but is surprising at milestone-close time.** When archiving moved phase dirs into `.planning/milestones/` (gitignored), git showed 39 deletions until I explicitly `git add -f` the new archive paths so git could detect renames. For v2: either commit *all* planning artifacts unconditionally, or document the dual-tracking story so future operators don't miss the archival add.
5. **Honesty about deferrals beats turnkey aspirations.** Phase 4 mid-M1 reshape (D-56 deferring hook router to v2) preserved a shippable M1; trying to ship the Flask app + per-rule allowlist + per-tuple rate limit + Jenkins token wiring inside M1 would have either blown the timeline or shipped a half-implementation. The README "Not in M1" subsection sets accurate expectations.
6. **`/gsd:complete-milestone` audit found 6 stale flags that all reduced to bookkeeping, not real gaps.** Useful safety check; the inline-resolve path was the right choice over acknowledge-and-defer because the stale flags would have stayed misleading forever.

### Cost Observations

- Model mix: predominantly Sonnet (executor_model: sonnet, verifier_model: sonnet); Opus invoked for the orchestrator + milestone close.
- Sessions: estimated 30-40 spread over 4 days; rich planning + research cycle per phase.
- Notable: 26-plan / 110-task M1 shipped in ~4 calendar days at the Sonnet price point thanks to wave-based parallel execution within the GSD `execute-phase` workflow.

---

## Post-Ship Correction: v1.0.1 — PromLens removed

**Date:** 2026-05-19 (same day as v1.0.0 ship).

**What happened:** During ship-day review of bundled components, a quick upstream check confirmed `prom/promlens` has had only Dependabot dependency-update commits since the v0.3.0 tag in December 2022. No functional release in 3.5 years; no maintainer activity beyond bot bumps. The role had already been marked deprecation-candidate in its own README when v1.0.0 shipped, but it was still in the deploy set.

**The call:** Remove PromLens from the stack as a v1.0.1 patch ship. Prometheus 3.x's native Mantine-based UI at `http://prometheus:9090/graph` absorbs the PromQL tree-view + query-explorer feature that was PromLens's only remaining value. Zero capability loss for operators.

**Scope:** 13 files touched in the live tree (7 deletions: 6 role files + 1 inventory file; 6 doc/config edits) + 4 planning bookkeeping files (CLAUDE.md, PROJECT.md, STATE.md, RETROSPECTIVE.md) + this v1.0.1 entry. Three atomic commits plus the annotated `v1.0.1` git tag.

**Lesson for v2:** Before deciding to ship any component "for upstream parity," confirm upstream maintenance status. The cost of shipping unmaintained code in a clone-and-run project is non-trivial (operator confusion, CVE exposure, future removal work). The check is cheap — `gh api repos/<org>/<repo>` for `pushed_at` + last tag, plus a glance at recent commits to see if they're Dependabot-only — and would have prevented PromLens from appearing in v1.0.0 at all. Add this to the v2 planning checklist: every component slot answers "is upstream actually shipping?" before being scoped in.

**Process observation:** v1.0.1 ran through `/gsd:quick` (not a full phase) and demonstrated the patch-release loop works cleanly on top of the milestone-archive structure. The worktree-isolation path failed because the orchestrator forgot the `isolation="worktree"` parameter on the Agent call; the executor caught the discrepancy and halted instead of self-recovering — exactly the right behavior. Falling back to inline execution on `main` for a 3-commit doc/cleanup patch was the right call; the worktree dance adds value when there are parallel agents, not for single-track surgical edits.

---

## Milestone: v1.2.0 — Operator Undeploy Path

**Shipped:** 2026-05-30 on leviathan
**Phases:** 3 (10, 11, 12) | **Plans:** 15 | **Commits since v1.1.0:** 76 | **LOC delta:** +5,833 / -43 across 65 files | **Timeline:** 3 days (2026-05-28 → 2026-05-30)

### What Was Built

A symmetric `playbooks/undeploy_docker.yml` that mirrors `deploy_docker.yml` in reverse: removes the 12 deployed containers + the `telemetron` Docker bridge network on a default run, with three opt-in purge flags (`telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images`) for irreversible cleanup. Every destructive task is preceded by a D-159 `WARNING: irreversible -- <role> <action>: <targets>` debug task; the playbook opens with a D-160 PLAY-start banner summarising what each enabled flag means. Every deploy role ships a `tasks/uninstall.yml` (Gate 10 in `roles/README.md` codifies the contract); the complete story is discoverable through a 3-concentric-layer documentation cascade (root README → `docs/quickstart.md#removing-telemetron` → 12 role README `## Uninstall` sections + nfsd's divergent "does NOT remove" block per D-172).

### What Worked

- **The 3-phase decomposition matched the work shape.** Phase 10 = per-role surface (a uniform mechanical pass through 13 directories), Phase 11 = orchestrator + UAT (the heavyweight phase, single playbook + 7 live scenarios), Phase 12 = pure doc cascade (16 Markdown files, no code). Each phase had a single clear axis; no inter-phase scope creep.
- **CONTEXT.md as the spec, end to end.** Phase 12's `12-CONTEXT.md` locked verbatim wording for D-170 (per-role template) and D-174 (root README sentence). The planner translated decisions to plans; the executor translated plans to files; the verifier confirmed the files match decisions. Zero re-litigation downstream. The decision-coverage gate (which flagged `D-168` as uncovered until the planner cited it in must_haves) caught the only translation slip cheaply, before execution.
- **Worktree-isolated parallel execution in Phase 12.** 3 plans across 15 files ran concurrently in 3 separate worktrees, merged cleanly in sequence (zero conflicts because plans touched disjoint files). Wave 1 finished in ~10 minutes wall time; sequential execution would have taken ~25 min. Re-validated the v1.0.0 pattern.
- **Audit-then-acknowledge for stale-prior-milestone items.** The pre-close artifact audit surfaced 4 items (Phase 8/9 verification status drift, orphan PromLens quick-task) all from already-archived milestones. STATE.md `## Deferred Items` table captured them with provenance so future audits don't re-surface them as new problems.

### What Was Inefficient

- **UI gate substring-grep false positive on the docs-only phase.** The plan-phase UI gate uses `grep -iE "UI|interface|frontend|...|view|..."` which matches substring `ui` inside `requirements` and `build`. For Phase 12 (pure docs, zero UI), the gate fired anyway and would have blocked planning if not for explicit override. The orchestrator recognised the false positive but the gate's substring matching is the root cause — `\b(UI|interface|...)\b` with word boundaries would have been correct.
- **`gsd-sdk query milestone.complete` auto-generated MILESTONES.md entry was unusable as written.** The "Key accomplishments" auto-extracted 10 raw plan-level one-liners verbatim including 2 `One-liner:` placeholders and 1 pre-existing-issue note. Required a complete manual rewrite to match the v1.0.0 / v1.1.0 milestone-level prose style. The CLI's accomplishment extractor should either filter `null` returns from `summary-extract` or aggregate at the phase level before the milestone level.
- **The post-planning gap analysis reports every uncovered REQ-ID across the entire `REQUIREMENTS.md`, not just the phase's IDs.** Phase 12's report flagged OPS-01/02/PURGE-01/02/UNDEPLOY-01/02 as "Not covered" — but those belong to phases 10/11 (already shipped). Noisy false positive that requires manual interpretation. The check should be scoped to `phase_req_ids` only, or at minimum group `Covered by phase N` rather than `Not covered`.
- **One executor's worktree CWD drifted into the agent's worktree during post-wave cleanup.** Triggered the #3174 guard and required `cd /home/darko/git/rockdarko/telemetron` before manual worktree merges could proceed. The orchestrator's `pwd` should be pinned at the start of post-wave cleanup, not left implicit; `WAVE_WORKTREE_MANIFEST` env var also evaporated between Bash calls (shells aren't persistent across tool invocations) so the SDK helper couldn't be invoked at all and the orchestrator fell back to manual `git merge` loops.

### Patterns Established

- **Symmetric playbook contract (`deploy_docker.yml` ↔ `undeploy_docker.yml`).** Same inventory, same `--ask-vault-pass`, same `--tags <role>` UX, reverse role order. Future operator-facing playbooks (preflight, doctor, backup, restore) inherit this UX shape — operators learn the conventions once.
- **D-159 WARN template + D-160 PLAY-start banner as the destructive-action contract.** Any future role or playbook with destructive opt-in behaviour follows the same shape: per-action `WARNING: irreversible -- <role> <action>: <targets>` debug task + PLAY-start banner with category descriptions (not name enumeration, not counts). `^WARNING:` is grep-friendly in PLAY OUTPUT for operators auditing destruction.
- **Three-concentric-layer documentation cascade.** Root README (first contact, one sentence) → quickstart (full reference, all sub-contracts) → per-role README (role-scoped cmd, `--tags <role>`). Predetermined anchor name (`#removing-telemetron`) lets cross-refs land in any order. Future cross-cutting operator concerns inherit this shape.
- **Force-add convention for shipping `.planning/` artifacts.** `.planning/` is gitignored; phase-completion commits force-add VERIFICATION.md and SUMMARY.md so the artifacts ship while planning intermediates (CONTEXT.md, PLAN.md, RESEARCH.md, REVIEW.md) stay local. v1.0.0/v1.1.0/v1.2.0 phase-complete commits all follow this pattern.

### Key Lessons

1. **Substring-grep is a class of false-positive bug in workflow gates.** Phase 12's UI gate firing on `requirements` substring is the latest instance. Audit every workflow gate that uses `grep -iE` against keyword lists and ask: do the alternation tokens need word boundaries? For 1-2-character tokens like `ui`, the answer is unambiguously yes.
2. **The decision-coverage gate is cheap insurance.** A single missing `D-168` citation in 12-01's `must_haves.truths` would have shipped silently if `gsd-sdk query check.decision-coverage-plan` hadn't refused to mark the phase planned. The gate cost ~30 seconds (a one-line edit to a truth) and prevented a real coverage gap.
3. **Live UAT remains the only gate that catches output-format-assumption regressions.** Plan 11-06's two regex fixes (`\S+` widening + Created-column skipping for `garage key list` v2 output) emerged only when a human ran the playbook against a live Garage v2 container. The planner, checker, code-reviewer, and verifier all read upstream docs and assumed the output format — none of them ran the actual binary. Confirmed for the third milestone in a row.
4. **The orchestrator's `pwd` must be pinned, not implicit, in post-wave cleanup.** Worktree subagents change `pwd` as a side effect; the orchestrator inherits the last child's cwd and ends up in a worktree when it tries to merge. The #3174 guard exists for this exact failure mode — but pinning explicitly at the start of cleanup is better than recovering after a guard fires.
5. **Worktree force-removal needs the `--force --force` (or unlock-first) path documented.** The Claude Code agent harness locks worktrees with `pid 133875: claude agent ...`; even after the agent returns, the lock persists until manually released. `gsd-sdk query worktree.cleanup-wave` should attempt `git worktree unlock` automatically before `git worktree remove` and surface a clear error when the unlock path fails.

### Cost Observations

- Model mix: predominantly Sonnet for executors (default in config); Opus for planner; Sonnet for verifier and plan-checker. Mixed-model strategy worked — heavy thinking on the planner, fast wide-context on the executors and verifier.
- Sessions: 1 long-running session covering Phase 12 + milestone close (~3 hours wall time, including 3 worktree executors + 1 verifier + 1 planner revision + 1 plan-checker revision + this milestone close).
- Notable: docs-only phase post-merge gate was almost no-op (no test command for an Ansible project, no compiled build) — saved time appropriately. Skipping `gsd-code-review` on the 100%-Markdown diff was the right judgment call; reviewing prose for "bugs and security issues" produces zero signal. Future docs-only phases should opt out automatically.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0.0 | ~30-40 | 7 (+ 4 backlog) | Established 8 cross-cutting port-acceptance gates; decimal-phase pattern (04.1) for mid-milestone convention drift; live-UAT-on-leviathan as the validation surface |
| v1.1.0 | ~10-15 | 3 | Garage migration with live-UAT-as-only-gate; three mid-UAT regex regressions caught only on the live host; introduced the principle that ansible deploy phases need a live-deploy gate beyond static verification |
| v1.2.0 | ~5-8 | 3 | Symmetric undeploy playbook with three opt-in purge flags; D-159 WARN template + D-160 PLAY-start banner as the destructive-action contract; Gate 10 for per-role uninstall surface; 3-layer doc cascade pattern for cross-cutting operator concerns |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0.0 | "Boots on leviathan" + smoke test playbook (3 OTLP signals, 60s budget) | n/a (no unit-test surface in M1 — manual UAT) | 0 (no JS/Python runtime deps shipped; everything is upstream pinned container images + role configs) |
| v1.1.0 | "Boots on leviathan" + smoke test + 3rd-deploy idempotency check (`ok=135, changed=0, failed=0`) | n/a (still manual UAT) | 0 (Garage replaces MinIO; same zero-runtime-dep profile) |
| v1.2.0 | "Boots + uninstalls on leviathan" — 7-scenario UAT covering conservative undeploy, idempotency, each purge flag, all-3-flags fresh-start | n/a (still manual UAT; ansible idempotency `changed=0` on already-clean host) | 0 (no new components; same zero-runtime-dep profile) |

### Top Lessons (Verified Across Milestones)

1. **Live UAT on the real homelab host catches what static gates miss** — verified in v1.0 (alertmanager auto_remove race), v1.1 (3 Garage bootstrap regressions), and v1.2 (2 `garage key list` regex regressions). The planner→checker→reviewer chain reads upstream docs; none of them run the actual binary. *Pattern: every ansible deploy/undeploy phase needs a human-UAT-on-leviathan gate as the last step.*
2. **Decimal phase insertion (04.1) is the right pattern for atomic mid-milestone scope corrections.** Used once in v1.0.0; pattern still holds.
3. **Force-add convention for `.planning/` artifacts at phase/milestone completion.** Consistent across all 3 milestones; planning intermediates (CONTEXT.md, PLAN.md, RESEARCH.md) stay local while shipped artifacts (SUMMARY.md, VERIFICATION.md, milestone archive files) get force-added at the completion commit.
4. **`gsd-sdk` auto-generated content needs review-and-rewrite at milestone close.** v1.0.0 / v1.1.0 / v1.2.0 all required manual rewrites of MILESTONES.md auto-content. The extractors aren't smart enough to filter null one-liners or aggregate at the milestone level — treat the output as a draft, not a deliverable.
