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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0.0 | ~30-40 | 7 (+ 4 backlog) | Established 8 cross-cutting port-acceptance gates; decimal-phase pattern (04.1) for mid-milestone convention drift; live-UAT-on-leviathan as the validation surface |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0.0 | "Boots on leviathan" + smoke test playbook (3 OTLP signals, 60s budget) | n/a (no unit-test surface in M1 — manual UAT) | 0 (no JS/Python runtime deps shipped; everything is upstream pinned container images + role configs) |

### Top Lessons (Verified Across Milestones)

*Single-milestone retrospective; multi-milestone trends will accumulate from v2 onward.*

1. Live UAT on the real homelab host catches what static gates miss — but the gap between "verifier said human_needed" and "live UAT happened on leviathan" needs a tighter feedback loop than M1 had.
2. Decimal phase insertion (04.1) is the right pattern for atomic mid-milestone scope corrections.
