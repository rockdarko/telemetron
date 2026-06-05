# Phase 15: Documentation Cascade - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 15 is the v1.3.0 doc cascade: operators discover the backup-and-restore story entirely through prose docs — `roles/README.md` Gate 11 + `docs/quickstart.md ## Backup and restore` + per-role README sections + a root-README cross-ref — without reading source code. Zero code changes; pure documentation work mirroring the v1.2.0 Phase 12 shape one-to-one.

Phase 15 closes the 3 remaining v1.3.0 requirements (DOCS-V13-01, DOCS-V13-02, DOCS-V13-03) and lights up the v1.3.0 milestone gate.

**In scope:**
- `roles/README.md`: new Gate 11 in the per-role port-acceptance gates section, matching Gates 1-10 in style/detail.
- `docs/quickstart.md`: new `## Backup and restore` H2 section with sub-H3 subsections per topic.
- `README.md` (root): one-line cross-ref to `docs/quickstart.md#backup-and-restore`.
- 4 stateful role READMEs (garage, prometheus, grafana, alertmanager): new `## Backup` H2 section, uniform skeleton + per-role "what's NOT captured" content.
- 8 stateless role READMEs (loki, tempo, mimir, fluentbit, karma, node_exporter, opentelemetry, nfsd): new `## Backup` H2 with a single sentence (two templates: data-in-Garage vs truly stateless).

**Out of scope:**
- Any change to Phase 13/14 code or task files.
- New backup/restore knobs or operator UX changes.
- Off-host backup destinations (deferred — BACKUP-V14-01..03 are v1.4.0+).
- HUMAN-UAT on leviathan (doc-only phase; Phase 12 precedent).

</domain>

<decisions>
## Implementation Decisions

### Per-role `## Backup` section — 4 stateful roles (D-194..D-197)

- **D-194: `## Backup` H2 placement = between `## Volumes` and `## Uninstall` in each of the 4 stateful role READMEs.** Reads as a data-lifecycle cluster: `## Volumes` (what's on disk) → `## Backup` (how to preserve it) → `## Uninstall` (how to remove it). Mirrors D-171's spirit (Uninstall went between Volumes and Healthcheck because of natural reading flow). Stateful targets: `roles/garage/README.md`, `roles/prometheus/README.md`, `roles/grafana/README.md`, `roles/alertmanager/README.md`. Existing structure already has `## Volumes` and `## Uninstall` H2s in all 4 (verified). Alternative (between Uninstall and Healthcheck) rejected — breaks the volumes→backup→uninstall reading order.

- **D-195: Uniform skeleton + per-role "what's NOT captured" content (mirrors Phase 12 plan 12-02's 11-uniform pattern).** Every stateful `## Backup` section follows the same shape:
  1. One-line intro sentence (what this section covers).
  2. `**Captured:**` short bullet list — what's in the tarball.
  3. `**Not captured:**` short bullet list — what isn't, and why.
  4. Code fence with the per-role tag-scoped invocation (e.g., `ansible-playbook playbooks/backup_docker.yml --tags garage --ask-vault-pass`).
  5. Cross-ref line to `docs/quickstart.md#backup-and-restore` (D-197).
  Per-role content variation is intentional and important — garage captures the host-mounted `s3-credentials` file (D-176; surprising); grafana doesn't capture provisioning (re-renders from version-controlled config); each role's "Not captured" list is what makes the section worth reading. Alternatives rejected: fully-uniform text (hides the surprises); free-form per role (loses cross-role scannability).

- **D-196: "Captured/Not captured" content uses two short bullet lists (per role).** Two `**Label:**` bolded headers followed by 2-5-bullet lists each. Mirrors the bullet-list style already used in role README sections like `## Variables` and `## Healthcheck`. Alternative (single prose paragraph) rejected — buries the surprises; alternative (markdown table) rejected — table not consistent with the rest of role READMEs' prose+list voice.

- **D-197: Each stateful `## Backup` section ends with a single cross-ref line to `docs/quickstart.md#backup-and-restore`** in the exact pattern Phase 12 `## Uninstall` sections use (e.g., grafana's Uninstall: "See `docs/quickstart.md#removing-telemetron` for the full undeploy story..."). Operators land in quickstart for the full story; per-role README is the role-scoped invocation + "what's special about this role." No sibling-role cross-refs (none of the 4 stateful roles has a cross-role data dep at backup time).

### Stateless "no backup" one-liner — 8 roles (D-198..D-201)

- **D-198: Every stateless role README gets a new `## Backup` H2 containing a single sentence.** Uniform with the 4 stateful READMEs — every deployed role has a `## Backup` H2 at the same anchor (`#backup`). Maximum cross-role discoverability: operator scanning any role README finds the section in the same spot, finds a one-line answer for the stateless case. 8 targets: `roles/loki/README.md`, `roles/tempo/README.md`, `roles/mimir/README.md`, `roles/fluentbit/README.md`, `roles/karma/README.md`, `roles/node_exporter/README.md`, `roles/opentelemetry/README.md`, `roles/nfsd/README.md`. Alternatives rejected: inline-appended-to-Uninstall (loses anchor consistency); standalone-paragraph-no-H2 (loses anchor entirely).

- **D-199: Two-template wording — data-in-Garage vs truly-stateless.**
  - **Data-in-Garage roles (loki, tempo, mimir):** "Data lives in Garage S3 buckets — captured by the garage role's backup. See `roles/garage/README.md#backup`."
  - **Truly-stateless roles (karma, fluentbit, node_exporter, opentelemetry, nfsd):** "No operator state to preserve."
  Honest and operator-useful — the loki operator needs to know their data IS being backed up (just not by the loki role). Planner may adjust exact wording but the two-template distinction stays. Alternative (uniform one-template) rejected — flattens the operator-useful Garage handoff.

- **D-200: Stateless `## Backup` sits in the same Volumes → Backup → Uninstall slot as stateful** for roles with a `## Volumes` section. Fallback for roles without `## Volumes` (karma, node_exporter, opentelemetry per Phase 12 inspection — actually all three have ## Volumes per audit): place between the tags-cluster (`## Tags` / `## Modes`) and `## Uninstall`. Same anchor (`#backup`) across all 12 deployed READMEs. Phase 12 plan 12-02 already verified that all 11 of the 12 uniform roles have `## Volumes` — the same fallback need not actually fire, but document it for planner safety.

- **D-201: nfsd uses the truly-stateless template** ("No operator state to preserve."), placed before nfsd's divergent `## Uninstall` block (which sits after `## Verification` per D-172). nfsd is a host-package role serving network exports; the receiving operator's data on `/srv/telemetron-nfs/` is THEIR responsibility (D-138). One-sentence H2; no extra disclaimer text about the share root — Phase 12's D-138 wording in nfsd's `## Uninstall` already disclaims responsibility for the share contents.

### `docs/quickstart.md ## Backup and restore` section (D-202..D-205)

- **D-202: Use sub-H3 subsections per topic instead of flat prose.** The 5 required topics (DOCS-V13-02) each become an H3:
  - `### Backup` — default command, `backup_continue_on_failure` mention, dest path naming, tag-scoped invocation.
  - `### Restore` — full `backup_restore_confirm=true` gate, `backup_restore_from` selector, restore order in PLAY OUTPUT.
  - `### Stop order during Garage restore` — Loki/Tempo/Mimir auto-stop + auto-restart by `restore_docker.yml`; operator doesn't intervene.
  - `### Retention` — Telemetron writes dated tarballs to `/opt/telemetron/backups/<role>/`; operator manages retention with their tool of choice (rsync to off-host, restic, plain `find -mtime`, etc.).
  - `### Manual fallback` — full recipe with concrete docker commands (D-204).
  Phase 12's flat-prose Removing Telemetron worked for ONE orchestrator and 3 knobs; backup/restore has 2 orchestrators and 5 knobs — sub-H3s pay for themselves. Anchors like `#restore` and `#manual-fallback` enable forward-deep-linking. Alternative (flat prose) rejected — wall of text for 5 topics.

- **D-203: Section line budget = 150-200 body lines.** Phase 12 hit 120 for one orchestrator with 3 knobs and a manual fallback. Phase 15 covers 2 orchestrators with 5 knobs + writer-quiesce stop-order + 2 manual fallbacks (extract + restore). ~30-50% more content is honest. Acceptance gate should be 100-220 (generous range matching Phase 12's 40-120 gate's relative looseness). Don't compress for compression's sake. Alternative (hard 120 ceiling) rejected — would gut the manual fallback.

- **D-204: Manual tarball-extraction fallback uses a full recipe with concrete docker commands.** Show: stop the role's container (`docker stop telemetron-grafana`), wipe the named volume (`docker run --rm -v telemetron_grafana_data:/d alpine sh -c 'rm -rf /d/*'`), extract the tarball into the volume (`docker run --rm -v telemetron_grafana_data:/d -v /opt/telemetron/backups/grafana:/b alpine sh -c 'tar --use-compress-program=unzstd -xf /b/<file>.tar.zst -C /d'`), restart (`docker start telemetron-grafana`). Pattern mirrors Phase 12's `docker volume rm` discovery+removal commands. Operators get a working escape hatch matching the doc-cascade goal ("without reading source code"). One worked example for grafana is sufficient (it's the simplest layout — one volume); a comment notes garage's 3-entry tarball has 3 paths to extract and points to the role README for the path map. Alternative (conceptual hand-wave) rejected — punts the docker-volume-name-to-mount-path lookup back to the operator.

- **D-205: `backup_continue_on_failure` (default `false`, opt-in) gets a brief one-line mention inside `### Backup` with a one-line use-case.** Default behavior is bail-out, which is the right safety posture (Phase 14 D-184). The mention: `add --extra-vars backup_continue_on_failure=true to attempt all 4 roles even if one fails (PLAY RECAP aggregates failures)`. Operators see it without it dominating the section. Note that restore has NO equivalent knob — D-185 hardcodes `any_errors_fatal: true` and the doc should briefly state this asymmetry under `### Restore` so operators don't hunt for a missing flag. Alternative (footnote-at-bottom) rejected — risks operators ssh'ing to debug a failure they could have continued past.

### Root README cross-ref (DOCS-V13-02 root clause; D-206)

- **D-206: Root README Quick Start gains a "When something goes wrong" line linking to `docs/quickstart.md#backup-and-restore`,** placed adjacent to the existing "When you're done evaluating" line (added in Phase 12 plan 12-03 / D-174). Same shape, same paragraph style, same indent. Suggested wording: "When something goes wrong, [`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore) covers the backup playbook (conservative by default — operator manages retention) and the restore workflow (with the explicit `--extra-vars backup_restore_confirm=true` safety gate)." Planner may adjust phrasing; the link target and "When something goes wrong" lede are required by DOCS-V13-02.

### Gate 11 in `roles/README.md` (DOCS-V13-01; D-207..D-208)

- **D-207: Gate 11 matches Gate 10's depth (~15 lines, multi-paragraph, same voice).** Gates 1-10 in `roles/README.md` are richly detailed (Gate 10 alone is 17 lines including the nfsd divergence paragraph). Gate 11 follows suit: contract statement → name the 4 stateful roles explicitly (garage, prometheus, grafana, alertmanager) → name the cold-quiesce + block/rescue/always pattern → name the leviathan round-trip as the acceptance heuristic → state that stateless roles document no-backup in their README only (no empty no-op task files). Closing sentence: "Established in Phase 13-14 plans; future role additions inherit this contract." Same closing voice as Gate 10's "Established in Phase 10 plans 10-01 through 10-05; future role additions inherit this contract." Alternatives rejected: brief 5-line gate (inconsistent with Gates 1-10); cite-V13-IDs version (couples gate prose to per-milestone requirement IDs that get re-numbered).

- **D-208: Gate 11 closing paragraph mirrors Gate 10's closing-paragraph pattern.** Gate 10's closing paragraph distinguishes per-role scope (in-gate) from playbook-level scope (out-of-gate). Gate 11 does the same: per-role `tasks/backup.yml` + `tasks/restore.yml` are in-gate (the contract); orchestrator-level concerns — `backup_continue_on_failure` knob, writer-quiesce on Garage restore, restore `any_errors_fatal: true` hardcode — are explicitly out-of-gate (those are `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` concerns from Phase 14, not per-role contract concerns). Forward-point to `docs/quickstart.md#backup-and-restore` for the operator-facing story (same forward-point pattern as Gate 10's reference to `#removing-telemetron`).

### Plan breakdown (D-209..D-210)

- **D-209: 3 plans, one-to-one with the 3 v1.3.0 doc requirements — mirrors Phase 12 exactly.**
  - **Plan 15-01:** `docs/quickstart.md ## Backup and restore` H2 section (5 sub-H3s, ~150-200 body lines, full manual-fallback recipe). Closes DOCS-V13-02 main clause.
  - **Plan 15-02:** Per-role READMEs — 4 stateful `## Backup` H2 sections (uniform skeleton + per-role NOT-captured) AND 8 stateless `## Backup` H2 sections (two-template one-liners). 12 README files modified in one plan. Closes DOCS-V13-03.
  - **Plan 15-03:** `README.md` root cross-ref ("When something goes wrong" line) + `roles/README.md` Gate 11 (matches Gate 10 depth). Closes DOCS-V13-01 and DOCS-V13-02 root-README clause.
  Same 1:1 mapping Phase 12 used (12-01 quickstart H2, 12-02 per-role uninstall sections, 12-03 root README + Gate 10 finalization). Proven structure; verification is easy because each plan maps cleanly to one or two requirement IDs. Alternatives rejected: 4-plan split (extra plan boundary for no real benefit when stateful and stateless touch disjoint file sets within one plan); 5-plan split (overkill for a 3-requirement doc phase).

- **D-210: All 3 plans are parallel-safe and ship in one wave.** Plans touch disjoint file sets: 15-01 touches `docs/quickstart.md` only; 15-02 touches 12 `roles/<role>/README.md` files; 15-03 touches `README.md` and `roles/README.md`. The cross-refs from per-role READMEs (15-02) to `docs/quickstart.md#backup-and-restore` (15-01) and from root README (15-03) to the same anchor work post-merge regardless of plan ordering — Phase 12 plan 12-03 already established that forward-referenced markdown anchors are stable. Planner may wave-1 all three for fastest completion. Alternative (sequential) rejected — Phase 12 also did all 3 in parallel-effect (the merge order didn't matter); paranoia costs serial time for no real-world benefit.

### HUMAN-UAT (D-211)

- **D-211: No HUMAN-UAT for Phase 15 — doc-only phase.** Phase 12 (the v1.2.0 doc cascade) had no HUMAN-UAT — just plan-level acceptance gates and a 12-VERIFICATION.md. Phase 15 is also pure prose; no orchestrator to dry-run, no leviathan invocation. Acceptance is grep checks (anchor presence, required wording per requirement, code-fence balance, no non-ASCII regressions, line-count gates) + 15-VERIFICATION.md. The doc-driven 7-step round-trip is implicitly covered by Phase 14's HUMAN-UAT (which already validated the exact command lines the docs document). Alternatives rejected: lightweight doc-read-through HUMAN-UAT (worthwhile but blocks v1.3.0 close on calendar; capture as deferred milestone-close UAT idea instead); full doc-driven round-trip (overkill — Phase 14 already proved the round-trip works).

### Claude's Discretion (left to planner with safe defaults)

- **Exact wording of the stateless one-liners** — D-199 gives two templates; planner may tighten or extend by ≤5 words per role. The two-template distinction (Garage-backed vs truly-stateless) is locked.
- **Exact wording of the root README "When something goes wrong" line** — D-206 specifies lede + link target; the rest is planner's call within Phase 12's prose voice. Mirror "When you're done evaluating" paragraph shape.
- **Whether to include sample PLAY OUTPUT for the WARN banner in quickstart's `### Restore`** — Phase 12 included a verbatim PLAY OUTPUT block for the undeploy WARN banner (lines 287-295 of current `docs/quickstart.md`). Doing the same for the restore WARN banner is consistent and recommended — planner decides whether to ship.
- **Whether the manual fallback shows just grafana OR all 4 stateful roles with their volume layouts** — D-204 specifies grafana as the worked example. Planner may add a per-role "tarball contents" table (garage 3-entry, prometheus 1-entry, grafana 1-entry, alertmanager 1-entry) if it stays inside the line budget.
- **Exact subsection ordering within `## Backup and restore`** — D-202 lists 5 H3s; the order (Backup → Restore → Stop order → Retention → Manual fallback) is natural but planner may reorder (e.g., move Manual fallback before Retention).
- **Retention guidance specifics** — D-202's `### Retention` says "operator manages retention with their tool of choice"; planner decides whether to include one-line examples (rsync to off-host, restic, plain `find -mtime +30 -delete`). Default if planner is silent: include 2-3 one-line examples.
- **Acceptance criteria for line-count gates** — D-203 says 100-220 range for the quickstart H2. Per-role stateful `## Backup` sections are unspecified; planner picks a per-section gate (suggest 8-25 lines per stateful section). Stateless one-liner sections are by definition ~3-5 lines (H2 + one sentence).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements (locked)
- `.planning/REQUIREMENTS.md` § v1.3.0 — DOCS-V13-01, DOCS-V13-02, DOCS-V13-03 (the 3 Phase 15 requirements; exact wording matters — every required phrase named in the requirement must appear verbatim in the corresponding doc)
- `.planning/ROADMAP.md` § Phase 15 — goal + 4 success criteria (SC1..4)
- `.planning/PROJECT.md` § v1.3.0 — locked design decisions (cold-quiesce, destination, retention, encryption, failure-mode, quality-bar, size) — these shape what the docs describe
- `.planning/STATE.md` § v1.3.0 Decisions — locked-decision list

### Phase 12 precedent (mirror this exactly — Phase 15 is the v1.3.0 analog)
- `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-01-SUMMARY.md` — quickstart `## Removing Telemetron` execution (120 body lines; 4-bullet DOCS-01 contract; D-165..D-168 verification matrix). Phase 15 plan 15-01 mirrors this shape.
- `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-02-SUMMARY.md` — per-role README `## Uninstall` execution (11 uniform + 1 nfsd divergent; D-171 placement). Phase 15 plan 15-02 mirrors this shape, expanded to cover stateful AND stateless variants.
- `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-03-SUMMARY.md` — root README cross-ref + Gate 10 finalization (D-174..D-176). Phase 15 plan 15-03 mirrors this shape, replacing Gate 10 finalization with Gate 11 addition.
- `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-VERIFICATION.md` — verification format Phase 15 will mirror.

### Phase 13/14 outputs (the docs describe these surfaces — must match reality)
- `.planning/phases/13-per-role-backup-restore-tasks/13-CONTEXT.md` — Phase 13 locked decisions (D-176..D-179: dest path, stop timeout, fail-fast, confirm gate, timestamp format); the docs MUST describe these knobs honestly.
- `.planning/phases/14-orchestrators-leviathan-human-uat/14-CONTEXT.md` — Phase 14 locked decisions (D-180..D-193: writer-quiesce model, bail-out vs continue, restore hardcoded any_errors_fatal, banner shapes, tag mechanics, shared-timestamp generation); the docs MUST describe these behaviors.
- `playbooks/backup_docker.yml` — actual orchestrator; PLAY-start banner wording, knob defaults, tag mechanics that the docs reference must match this file's current state.
- `playbooks/restore_docker.yml` — actual orchestrator; WARN banner wording (the `WARNING: irreversible --` prefix), confirm-gate failure message, writer-quiesce step ordering.
- `inventory/example-homelab/group_vars/all/backup.yml` — all 5 knobs with their defaults and comments; quickstart's `### Backup` and `### Restore` examples MUST use these exact knob names.

### Target files (the surface Phase 15 modifies)
- `docs/quickstart.md` — plan 15-01 adds `## Backup and restore` H2; current structure shows insertion point is between `## Upgrade notes` (line 253) and `## Removing Telemetron` (line 272), OR between `## Removing Telemetron` (ends ~393) and `## Building your own inventory` (line 393). Planner picks insertion point; either works.
- `README.md` — plan 15-03 adds the "When something goes wrong" line in `## Quick start` (lines 7-33), adjacent to the existing "When you're done evaluating" paragraph (lines 29-32) added by Phase 12 plan 12-03.
- `roles/README.md` — plan 15-03 adds Gate 11 to `## Per-role port-acceptance gates` section (line 37); Gate 10 ends at line 122. Gate 11 starts at line 123 (next available numbered gate slot).
- 4 stateful role READMEs:
  - `roles/garage/README.md` — has `## Volumes` (line 117), `## Uninstall` (line 125), `## Healthcheck` (line 138). New `## Backup` inserts between line 124 (end of Volumes) and line 125 (start of Uninstall).
  - `roles/prometheus/README.md` — analogous; check actual line numbers in plan.
  - `roles/grafana/README.md` — analogous; uses `---` separators between H2 sections per Phase 12 plan 12-02 note.
  - `roles/alertmanager/README.md` — analogous.
- 8 stateless role READMEs: `roles/{loki,tempo,mimir,fluentbit,karma,node_exporter,opentelemetry,nfsd}/README.md` — all have `## Volumes` and `## Uninstall` per Phase 12 plan 12-02 audit. New `## Backup` inserts in the same slot. nfsd's `## Uninstall` is divergent (after `## Verification`); `## Backup` inserts before that divergent block, in the normal Volumes→Backup slot.

### Pattern references (cross-ref style, prose voice)
- `roles/garage/README.md` § `## Uninstall` (lines 125-136) — canonical cross-ref pattern Phase 15's per-role `## Backup` sections mirror ("See `docs/quickstart.md#removing-telemetron` for the full undeploy story...").
- `README.md` lines 29-32 — "When you're done evaluating" paragraph; Phase 15's "When something goes wrong" paragraph mirrors this exactly.
- `docs/quickstart.md` § `## Removing Telemetron` (lines 272-393) — section voice, code-fence style, line-budget reference; Phase 15's `## Backup and restore` reads in the same register.
- `roles/README.md` § Gate 10 (lines 106-122) — Gate 11's voice/structure/closing-paragraph mirrors Gate 10 exactly.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 12 plan 12-01 (`## Removing Telemetron`)**: structural template for `## Backup and restore`. Same anchor convention (lowercase-hyphenated H2 → `#backup-and-restore`), same code-fence + prose alternation, same cross-ref discipline. Phase 15 plan 15-01 adapts this with sub-H3s.
- **Phase 12 plan 12-02 (12 per-role `## Uninstall` sections)**: template for 12 per-role `## Backup` sections. Same H2 placement decision shape (D-171 ⇒ D-194), same 11-uniform + 1-divergent split shape (but here it's 4 stateful + 8 stateless + 1 nfsd-style-divergent for the stateless template), same cross-ref-to-quickstart pattern. Phase 15 plan 15-02 directly adapts this — biggest single plan in the phase but well-templated.
- **Phase 12 plan 12-03 (root README cross-ref + Gate 10 finalization)**: template for plan 15-03. Same surgical-edit shape — one prose insertion in `README.md`, one new gate paragraph in `roles/README.md`. Phase 15's Gate 11 is additive (not a finalization rewrite like Gate 10), but the prose voice and structural parallelism are identical.
- **`playbooks/backup_docker.yml` PLAY-start banner** (D-186) and **`playbooks/restore_docker.yml` WARN banner** (D-187): canonical operator-facing wording. The quickstart section's `### Backup` and `### Restore` subsections quote these banner lines verbatim (mirrors how Phase 12's `## Removing Telemetron` quotes the undeploy WARN banner at lines 287-295).
- **`inventory/example-homelab/group_vars/all/backup.yml`**: all 5 knob defaults + per-knob comment block. The quickstart subsections can crib the comment prose for the knob descriptions.

### Established Patterns
- **Lowercase-hyphenated H2 → anchor**: GitHub-flavored markdown automatically produces `#backup-and-restore` from `## Backup and restore`. Phase 12 already verified this works for `#removing-telemetron`. No anchor frontmatter needed.
- **Cross-ref to docs/quickstart.md from role READMEs**: Phase 12 set the precedent — every per-role `## Uninstall` ends with `See \`docs/quickstart.md#removing-telemetron\` for the full undeploy story...`. Phase 15 per-role `## Backup` sections do the same: `See \`docs/quickstart.md#backup-and-restore\` for the full backup/restore story...`.
- **No `D-XX` decision references in operator-facing prose** (Phase 12 plan 12-01 verification gate): the docs are for operators; decision IDs are for contributors. Phase 15 docs follow the same rule — no `D-194..D-211` references appear in any output file.
- **No non-ASCII characters in modified prose** (Phase 12 verification gate): Phase 15 inherits this. Pre-existing § / ☑ / em-dash characters in karma/roles/README.md are out-of-scope (Phase 12 plan 12-02 note) — Phase 15 doesn't sweep them either.
- **Code-fence balance check**: every plan's verification asserts even number of ``` fences in modified files.
- **Phase 12's verification used grep-pin gates** for required-wording-in-doc — Phase 15 mirrors: each requirement names specific phrases ("Gate 11", the 4 stateful role names verbatim, `--extra-vars backup_restore_confirm=true`, `Loki/Tempo/Mimir stop before Garage restore`, etc.) which become acceptance criteria for the relevant plan.

### Integration Points
- **Phase 14 → Phase 15**: Phase 14 finalized the orchestrator command lines, knob names, banner wording, and tag mechanics. Phase 15 documents them verbatim. The docs ARE the v1.3.0 milestone-close artifact — if Phase 15 ships docs that contradict Phase 14's actual playbook behavior, the milestone gate must not close. Plan-level verification gates check this by reading the actual playbook file for banner text and command shapes.
- **Phase 12 → Phase 15**: Phase 15 cohabits with Phase 12's `## Removing Telemetron` (in quickstart.md) and Phase 12's 12 `## Uninstall` sections (in role READMEs). Phase 15 inserts new sections without modifying Phase 12's outputs. The data-lifecycle reading flow in role READMEs becomes: `## Volumes → ## Backup (new) → ## Uninstall (Phase 12)`. The quickstart H2 ordering becomes: `## Upgrade notes → ## Removing Telemetron (Phase 12) → ## Backup and restore (new) → ## Building your own inventory` OR the planner may insert Phase 15's H2 BEFORE Phase 12's `## Removing Telemetron` (since backup is operationally a more common operator concern than removal); planner picks the spot in plan 15-01.
- **Phase 15 → v1.3.0 milestone close**: Phase 15 closes the last 3 of 18 v1.3.0 requirements; on Phase 15 plan completion + VERIFICATION + audit-milestone, the milestone is shippable. No phases follow Phase 15 in v1.3.0.

</code_context>

<specifics>
## Specific Ideas

- **Stateful `## Backup` section worked example (garage)** — what plan 15-02's garage section roughly looks like:
  ```markdown
  ## Backup

  The garage role ships `tasks/backup.yml` and `tasks/restore.yml` for atomic
  cold-quiesce backup and restore of Garage's two named volumes plus the
  host-mounted S3 credentials file.

  **Captured (3 entries in the tarball):**
  - `telemetron_garage_meta` volume (LMDB metadata)
  - `telemetron_garage_data` volume (object data blocks)
  - `{{ garage_s3_credentials_file }}` host file (S3 keypair — the credentials
    Loki/Tempo/Mimir use to write to Garage buckets)

  **Not captured:**
  - (nothing — Garage's S3 credentials are intentionally captured even though
    they're a host file, so the restored stack reconnects without operator
    re-bootstrap)

  ```bash
  ansible-playbook playbooks/backup_docker.yml --tags garage --ask-vault-pass
  ```

  See `docs/quickstart.md#backup-and-restore` for the full backup/restore
  story (knobs, restore workflow, manual fallback).
  ```

- **Stateless `## Backup` section worked examples**:
  - loki/tempo/mimir: `Data lives in Garage S3 buckets — captured by the garage role's backup. See \`roles/garage/README.md#backup\`.`
  - karma/fluentbit/node_exporter/opentelemetry: `No operator state to preserve.`
  - nfsd: `No operator state to preserve.` (operator's NFS-shared log data on `/srv/telemetron-nfs/` is the operator's responsibility per the `## Uninstall` disclaimer below)

- **Gate 11 worked example (matches Gate 10 depth)**:
  ```markdown
  **11. Per-role backup/restore contract (BACKUP-V13-01..04 + RESTORE-V13-01..04; D-176..D-179):**

  Every stateful role MUST ship `tasks/backup.yml` and `tasks/restore.yml`
  proven on leviathan end-to-end. The 4 stateful roles are: `garage`,
  `prometheus`, `grafana`, `alertmanager`.

  (a) `tasks/backup.yml` performs cold-quiesce (docker stop, zstd tarball
  of the role's named volume(s) into `/opt/telemetron/backups/<role>/<role>-<UTC-ts>.tar.zst`,
  docker start, verify) wrapped in `block:/rescue:/always:` so the container
  is running at the end regardless of tar success/failure.

  (b) `tasks/restore.yml` asserts `backup_restore_confirm == true` (fail-fast
  gate), runs `tar tf` integrity check, wipes the volume's `_data/`, untars,
  restarts, verifies.

  (c) Both files start with an `ansible.builtin.package: name: zstd
  state: present` pre-task; idempotent on hosts that already have it.

  Stateless roles document their no-backup status in their role README only
  (no empty `tasks/backup.yml` no-op files). The 8 stateless roles are:
  `loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`,
  `opentelemetry`, `nfsd`. Loki/Tempo/Mimir data lives in Garage S3 buckets
  (covered by the garage role); the remaining 5 carry no operator state.

  Orchestrator behavior — the `backup_continue_on_failure` knob,
  writer-quiesce on Garage restore (Loki/Tempo/Mimir stop before, restart
  after), and restore's hardcoded bail-out (`any_errors_fatal: true`) — is
  out of Gate 11 scope. Phase 14 shipped these as
  `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` concerns;
  the per-role contract above is sufficient. See
  `docs/quickstart.md#backup-and-restore` for the operator-facing story.
  Established in Phase 13-14 plans; future role additions inherit this
  contract.
  ```

- **Root README cross-ref worked example** (insert after current line 32, before `## What's included` at line 35):
  ```markdown
  When something goes wrong,
  [`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore)
  covers the backup playbook (conservative by default — local dated tarballs;
  operator manages retention) and the restore workflow (with the explicit
  `--extra-vars backup_restore_confirm=true` safety gate).
  ```

- **Quickstart `## Backup and restore` skeleton** (plan 15-01):
  ```markdown
  ## Backup and restore

  [3-5 line intro: what this section covers, who it's for, what the v1.3.0
  scope is — local-disk tarballs of stateful role data, restore round-trip
  proven on leviathan, off-host destinations are operator-managed.]

  ### Backup

  [Default command + ~4-bullet "what happens" + brief mention of
  backup_continue_on_failure opt-in + per-role --tags invocation.]

  ### Restore

  [Default command with --extra-vars backup_restore_confirm=true gate +
  backup_restore_from selector + WARN banner verbatim quote + note that
  restore is always fail-fast (no continue knob — by design).]

  ### Stop order during Garage restore

  [Writer auto-stop/auto-restart — Loki/Tempo/Mimir handled automatically by
  restore_docker.yml; no operator action needed; --tags garage triggers the
  full stop-restore-restart cycle.]

  ### Retention

  [Dated tarballs at /opt/telemetron/backups/<role>/; operator-managed
  retention with rsync/restic/find -mtime examples.]

  ### Manual fallback

  [Full docker-command recipe — stop, wipe-volume-via-alpine, untar-with-unzstd,
  restart. Worked example on grafana; note garage has 3 paths to extract,
  point at roles/garage/README.md#backup.]
  ```

- **Insertion point in quickstart**: planner's call. Two reasonable options: (a) after `## Removing Telemetron` (current order: Upgrade → Removing → Backup → Building); (b) before `## Removing Telemetron` (Upgrade → Backup → Removing → Building, since backup is a more common operator concern than removal). Either is defensible. Recommendation: option (b) — backup is operationally more frequent than removal; lead with it.

</specifics>

<deferred>
## Deferred Ideas

- **Off-host backup destinations** (`backup_remote_target` rsync/SSH push) — REQUIREMENTS.md tracks as BACKUP-V14-01..03. Out of v1.3.0 scope. Phase 15 docs explicitly state "operator-managed" retention.
- **Encryption-at-rest for tarballs** — out of v1.3.0 scope. Operator can wrap their own GPG/age layer; Phase 15 docs don't promise tarball encryption.
- **Tarball integrity verification beyond `tar tf`** — per-role restore does `tar tf`; a future enhancement (sha256 sidecar, signed manifests) is deferred to a later milestone.
- **Lightweight doc-read-through HUMAN-UAT** — D-211 captures this as a deferred milestone-close idea. Worth doing as part of v1.3.0 audit-milestone (Rock reads quickstart cold, attempts backup/restore using only docs), but does not block Phase 15 ship.
- **Per-role "tarball contents" comparison table** — D-204 captures this as Claude's Discretion within plan 15-01. If it fits the line budget, useful; if not, defer.
- **Per-role README "## Restore" H2** — Phase 15 only ships `## Backup` per requirement. A future doc pass could split into `## Backup` + `## Restore` for symmetry; not required by DOCS-V13-03. Capture if operator feedback surfaces.
- **PLAY OUTPUT block for restore WARN banner in quickstart** — D-202 Claude's Discretion; planner decides whether to include verbatim block like Phase 12 did for undeploy.

</deferred>

---

*Phase: 15-documentation-cascade*
*Context gathered: 2026-06-05*
