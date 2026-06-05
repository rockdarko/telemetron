---
phase: 15-documentation-cascade
plan: "03"
type: execute
wave: 1
depends_on: []
files_modified:
  - README.md
  - roles/README.md
autonomous: true
requirements:
  - DOCS-V13-01
  - DOCS-V13-02
tags:
  - documentation
  - root-readme
  - gate-11
  - cross-ref
  - DOCS-V13-01
  - DOCS-V13-02

must_haves:
  truths:
    - "Root README's Quick start section contains a 'When something goes wrong' paragraph that links to docs/quickstart.md#backup-and-restore, sitting adjacent to the existing Phase 12 'When you're done evaluating' line (D-206)."
    - "roles/README.md contains a new Gate 11 entry in the Per-role port-acceptance gates section that matches Gate 10's depth, voice, and structure (D-207)."
    - "Gate 11 names all 4 stateful roles verbatim (garage, prometheus, grafana, alertmanager) and all 8 stateless roles verbatim (loki, tempo, mimir, fluentbit, karma, node_exporter, opentelemetry, nfsd) — discoverability for future contributors."
    - "Gate 11 contains the literal file names tasks/backup.yml and tasks/restore.yml — the contract artifact names."
    - "Gate 11 contains the phrase 'proven on leviathan' (acceptance heuristic per D-207)."
    - "Gate 11 closing paragraph distinguishes per-role in-gate scope from orchestrator-level out-of-gate concerns (writer-quiesce, backup_continue_on_failure, restore any_errors_fatal), forward-points to docs/quickstart.md#backup-and-restore (D-208)."
    - "Gate 11 closes with the 'future role additions inherit this contract' line (matches Gate 10's closing-line pattern per D-207)."
  artifacts:
    - path: "README.md"
      provides: "When something goes wrong cross-ref paragraph in Quick start"
      contains: "When something goes wrong"
    - path: "roles/README.md"
      provides: "Gate 11 entry — Per-role backup/restore contract"
      contains: "**11."
  key_links:
    - from: "README.md (root) Quick start"
      to: "docs/quickstart.md#backup-and-restore"
      via: "Inline markdown link `[`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore)`"
      pattern: "docs/quickstart.md#backup-and-restore"
    - from: "roles/README.md Gate 11 closing paragraph"
      to: "docs/quickstart.md#backup-and-restore"
      via: "Forward-pointer sentence: 'See `docs/quickstart.md#backup-and-restore` for the operator-facing story.'"
      pattern: "docs/quickstart.md#backup-and-restore"
---

<objective>
Two surgical prose edits that close DOCS-V13-01 (Gate 11 in `roles/README.md`) and the root-README clause of DOCS-V13-02 ("When something goes wrong" link in `README.md`). Mirrors Phase 12 plan 12-03's shape one-to-one: one inserted cross-ref paragraph in the project root README + one new gate paragraph in the contributor-facing `roles/README.md`.

Purpose: Operators reading the root README's Quick Start section discover the backup-and-restore story (DOCS-V13-02 root clause); future contributors reading `roles/README.md` find Gate 11 codifying the per-role backup/restore contract that the 4 stateful roles inherit, matching the depth and voice of Gates 1-10 (DOCS-V13-01).

Output: 2 modified files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/15-documentation-cascade/15-CONTEXT.md
@.planning/phases/15-documentation-cascade/15-PATTERNS.md
@.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-03-SUMMARY.md

<interfaces>
<!-- Sub-plan A: README.md "When something goes wrong" cross-ref -->
<!-- Analog: README.md lines 30-33 "When you're done evaluating" paragraph (Phase 12 plan 12-03 output). -->

Phase 12 analog paragraph (currently lines 30-33 of `README.md`):

  When you're done evaluating,
  [`docs/quickstart.md#removing-telemetron`](docs/quickstart.md#removing-telemetron)
  documents the symmetric undeploy playbook -- conservative by default
  (volumes preserved); three opt-in flags for irreversible cleanup.

Voice register signals to mirror exactly:
- Opening adverbial phrase: `When X,`
- Inline-code-wrapped link target as the link text: `[\`docs/quickstart.md#X\`](docs/quickstart.md#X)`
- ASCII double-hyphen `--` for parenthetical (renders as em-dash in GFM but stays ASCII in source — matches Phase 12 D-174 explicit instruction per 12-VERIFICATION.md line 81)
- Short declarative continuation; semicolon separator
- 3-5 line wrap; blank-line-terminated

Phase 15 wording template (D-206; planner may adjust phrasing within Phase 12 voice; locked elements: lede `When something goes wrong,`, link target `docs/quickstart.md#backup-and-restore`, knob name `backup_restore_confirm=true`):

  When something goes wrong,
  [`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore)
  covers the backup playbook (conservative by default -- local dated
  tarballs; operator manages retention) and the restore workflow (with the
  explicit `--extra-vars backup_restore_confirm=true` safety gate).

Insertion point: immediately after the existing "When you're done evaluating" paragraph's blank-line terminator (current line ~34 blank), BEFORE `## What's included` (currently line 35). New paragraph + 1 blank separator = ~6 new lines.

<!-- Sub-plan B: roles/README.md Gate 11 -->
<!-- Analog: Gate 10 (currently lines 106-122; Phase 12 plan 12-03 output). -->

Gate 10 full structural template (read verbatim from roles/README.md lines 106-122):
- Opens with `**10. Per-role uninstall contract (UNDEPLOY-02; D-148):**`
- Single-sentence contract statement: "Every deploy role MUST ship a tested uninstall path. The contract has five parts:"
- Lettered sub-clauses (a) through (e) covering existence, container-removal, host-artifact-removal, named-volume-preservation, idempotency
- Divergent-role paragraph: nfsd 3-line divergence paragraph
- Closing paragraph: distinguishes per-role in-gate scope from playbook-level out-of-gate concerns (purge flags); forward-points to `docs/quickstart.md#removing-telemetron`; closes with "Established in Phase 10 plans 10-01 through 10-05; future role additions inherit this contract."

Gate 11 structural mapping (mirror Gate 10 element-by-element per D-207 + D-208 + 15-PATTERNS.md table):

| Element | Gate 11 adaptation |
|---------|---------------------|
| Bold lede | `**11. Per-role backup/restore contract (BACKUP-V13-01..04 + RESTORE-V13-01..04; D-176..D-179):**` |
| Single-sentence contract | "Every stateful role MUST ship `tasks/backup.yml` and `tasks/restore.yml` proven on leviathan end-to-end. The 4 stateful roles are: `garage`, `prometheus`, `grafana`, `alertmanager`." |
| Lettered sub-clauses | (a) backup cold-quiesce wrapped in block:/rescue:/always: so the container is running at the end regardless of tar success/failure; (b) restore confirm-gate + `tar tf` integrity check + wipe + untar + restart + verify; (c) zstd pre-task idempotent on hosts that already have zstd |
| Divergent paragraph | The 8 stateless roles document no-backup status in their README only (no empty `tasks/backup.yml` no-op files). Enumerate: `loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`, `opentelemetry`, `nfsd`. Note that Loki/Tempo/Mimir data lives in Garage S3 (covered by the garage role); the remaining 5 carry no operator state. |
| Closing paragraph | "Orchestrator behavior — the `backup_continue_on_failure` knob, writer-quiesce on Garage restore (Loki/Tempo/Mimir stop before, restart after), and restore's hardcoded bail-out (`any_errors_fatal: true`) — is out of Gate 11 scope. Phase 14 shipped these as `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` concerns; the per-role contract above is sufficient. See `docs/quickstart.md#backup-and-restore` for the operator-facing story. Established in Phase 13-14 plans; future role additions inherit this contract." |

CONTEXT.md `<specifics>` lines 215-249 contain the full ~25-line Gate 11 worked example — executor may adopt verbatim or refine. The example already satisfies all required-phrase gates.

Gate 11 insertion point: immediately after Gate 10's closing line (currently line 122 of `roles/README.md`); executor inserts blank-line separator + Gate 11 block at line 123-N.

Gate 11 body length budget: 15-30 lines (Gate 10 is 17 lines; Gate 8 is ~25 lines; CONTEXT.md `<specifics>` worked example is ~25 lines per D-207 acceptance).

Note on D-IDs in `roles/README.md` (Pattern S3 exception): `roles/README.md` is contributor-facing — Gates 1-10 already cite D-IDs in their ledes (D-90, D-148, etc.). Gate 11's lede SHOULD cite `D-176..D-179` per Gate 10 precedent. Operator-facing files (`README.md`, `docs/quickstart.md`, role READMEs) follow the no-D-ID rule; `roles/README.md` does not.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Insert "When something goes wrong" cross-ref paragraph into root README.md Quick start (sub-plan A)</name>
  <files>README.md</files>
  <read_first>
    <file>README.md</file>
    <reason>Read lines 1-50 to absorb the Quick start section structure and the existing "When you're done evaluating" paragraph at lines 30-33 (Phase 12 plan 12-03 output). The new paragraph mirrors that paragraph's prose voice, line-wrap, indent, and ASCII double-hyphen convention.</reason>
    <file>.planning/phases/15-documentation-cascade/15-CONTEXT.md</file>
    <reason>D-206 specifies the wording template (lede + link target are locked; rest is planner's call within Phase 12 voice). The `<specifics>` section lines 253-258 contain the worked example.</reason>
    <file>.planning/phases/15-documentation-cascade/15-PATTERNS.md</file>
    <reason>Plan 15-03 Sub-plan A section (lines 329-352) contains the analog excerpt, voice register signals, insertion point, wording template, and required-phrase gates.</reason>
    <file>.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-03-SUMMARY.md</file>
    <reason>Phase 12 analog: net change +5 lines (one blank separator + 4-line paragraph + one blank separator before `## What's included`). Same shape applies here. Mirror exact prose voice and ASCII `--` convention (12-VERIFICATION.md line 81 records this as a Phase 12 explicit decision).</reason>
  </read_first>
  <action>
Insert a new "When something goes wrong" paragraph into `README.md`'s `## Quick start` section, placed IMMEDIATELY AFTER the existing "When you're done evaluating" paragraph (current lines 30-33) and BEFORE the `## What's included` H2 (currently line 35).

Use this exact wording template per D-206 (planner may make minor phrasing adjustments within Phase 12 voice; the lede `When something goes wrong,`, the link target `docs/quickstart.md#backup-and-restore`, the knob name `backup_restore_confirm=true`, and the parenthetical `conservative by default -- local dated tarballs; operator manages retention` framing are locked):

  When something goes wrong,
  [`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore)
  covers the backup playbook (conservative by default -- local dated
  tarballs; operator manages retention) and the restore workflow (with the
  explicit `--extra-vars backup_restore_confirm=true` safety gate).

Use ASCII double-hyphen `--` for the parenthetical (Phase 12 D-174 + 12-VERIFICATION.md line 81: "double-hyphen used throughout per 12-03-PLAN explicit instruction matching README style"). DO NOT use the em-dash character — introduces non-ASCII.

Place a blank line separator above and below the new paragraph. Net change: +5 to +6 lines (blank + 5-line paragraph + blank).

The new paragraph sits adjacent to the existing "When you're done evaluating" paragraph (the two evaluation-exit cross-refs become natural reading siblings — the "what to do next" sequence: evaluate → done evaluating → something went wrong).

Zero D-XXX references in the new paragraph (operator-facing prose — Pattern S3).
Zero new non-ASCII characters introduced.
  </action>
  <verify>
    <automated>grep -q '^When something goes wrong' README.md &amp;&amp; grep -q 'docs/quickstart.md#backup-and-restore' README.md &amp;&amp; grep -q 'backup_restore_confirm=true' README.md &amp;&amp; grep -q "operator manages retention" README.md &amp;&amp; awk '/^## Quick start/{q=NR} /^When something goes wrong/{w=NR} /^## What.s included/{n=NR} END{exit (q &amp;&amp; w &amp;&amp; n &amp;&amp; q&lt;w &amp;&amp; w&lt;n)?0:1}' README.md &amp;&amp; awk '/^When you/{y=NR} /^When something/{s=NR} END{exit (y &amp;&amp; s &amp;&amp; y&lt;s)?0:1}' README.md &amp;&amp; awk '/^```/ { c++ } END { exit (c%2==0)?0:1 }' README.md &amp;&amp; ! grep -E 'D-(19[4-9]|2[0-1][0-9])' README.md</automated>
  </verify>
  <acceptance_criteria>
    - `README.md` contains a line starting with `When something goes wrong` (lede verbatim — DOCS-V13-02 grep-pin).
    - `README.md` contains the link target `docs/quickstart.md#backup-and-restore` (DOCS-V13-02 grep-pin).
    - `README.md` contains the knob name `backup_restore_confirm=true` (DOCS-V13-02 grep-pin).
    - `README.md` contains the phrase `operator manages retention` (D-206 framing — must appear verbatim).
    - New paragraph sits between `## Quick start` (H2) and `## What's included` (H2): verified by `grep -n` line-ordering of those three markers.
    - New paragraph sits AFTER the existing `When you're done evaluating` paragraph (sibling-paragraph ordering — D-206): verified by `grep -n '^When you' README.md` and `grep -n '^When something' README.md` line numbers.
    - Code-fence balance: even number of ``` in README.md (prose-only edit — should add zero fences).
    - Zero new non-ASCII characters introduced. No em-dash character (use `--`), no curly quotes, no smart punctuation.
    - Zero `D-XXX` references in the new paragraph (operator-facing — Pattern S3).
    - Paragraph length: 3-6 lines (matches Phase 12 analog 4-line shape).
  </acceptance_criteria>
  <done>
    `README.md` Quick start section contains a "When something goes wrong" 4-line paragraph linking to `docs/quickstart.md#backup-and-restore`, sitting adjacent to and AFTER the existing Phase 12 "When you're done evaluating" paragraph, BEFORE `## What's included`. All required phrases present verbatim; ASCII-only; verification gates pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Insert Gate 11 (Per-role backup/restore contract) into roles/README.md Per-role port-acceptance gates section (sub-plan B)</name>
  <files>roles/README.md</files>
  <read_first>
    <file>roles/README.md</file>
    <reason>Read lines 1-130 of the current file to absorb the Per-role port-acceptance gates structure and the full Gate 10 entry at lines 106-122 (Phase 12 plan 12-03 output). Gate 11 mirrors Gate 10 element-by-element: bold lede, contract statement, lettered sub-clauses, divergent-role paragraph, closing paragraph distinguishing in-gate from out-of-gate scope + forward-point + "Established in Phase X" closing line.</reason>
    <file>.planning/phases/15-documentation-cascade/15-CONTEXT.md</file>
    <reason>D-207 specifies Gate 11 matches Gate 10's depth (~15 lines, multi-paragraph, same voice). D-208 specifies the closing paragraph mirrors Gate 10's in-gate/out-of-gate distinction + forward-pointer. The `<specifics>` section lines 215-249 contains the full ~25-line Gate 11 worked example — executor may adopt verbatim or refine.</reason>
    <file>.planning/phases/15-documentation-cascade/15-PATTERNS.md</file>
    <reason>Plan 15-03 Sub-plan B section (lines 359-414) contains the Gate 10 full reproduction, the 7-row structural-anatomy mapping (lede / contract sentence / sub-clauses / divergent paragraph / closing paragraph / forward-point / closing-line), the insertion point (after line 122), and the complete required-phrase gates list (DOCS-V13-01).</reason>
    <file>.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-03-SUMMARY.md</file>
    <reason>Phase 12 analog: Gate 10 closing paragraph rewrite was a 1-line surgical change. Phase 15's Gate 11 is a 15-30 line INSERTION (not a rewrite of an existing gate). Same prose voice; same `Established in Phase X plans Y-Z; future role additions inherit this contract.` closing-line pattern.</reason>
    <file>playbooks/backup_docker.yml</file>
    <reason>Source-of-truth for `backup_continue_on_failure` knob name and behavior referenced in Gate 11's closing out-of-gate paragraph.</reason>
    <file>playbooks/restore_docker.yml</file>
    <reason>Source-of-truth for `any_errors_fatal: true` hardcode and writer-quiesce stop-order behavior referenced in Gate 11's closing out-of-gate paragraph.</reason>
  </read_first>
  <action>
Insert a new Gate 11 entry into `roles/README.md`'s `## Per-role port-acceptance gates` section, immediately AFTER Gate 10's closing line (currently line 122 of the pre-edit file). Add a blank line separator + the Gate 11 block.

Use the CONTEXT.md `<specifics>` worked example (lines 215-249) as the seed; executor may refine wording within the structural constraints below. Gate 11 MUST contain (per D-207 + D-208 + 15-PATTERNS.md structural-anatomy table):

**Lede** (single line, bold; cites D-IDs per Gate 10 precedent):

  **11. Per-role backup/restore contract (BACKUP-V13-01..04 + RESTORE-V13-01..04; D-176..D-179):**

**Contract statement** (single sentence + role enumeration):

  Every stateful role MUST ship `tasks/backup.yml` and `tasks/restore.yml` proven on leviathan end-to-end. The 4 stateful roles are: `garage`, `prometheus`, `grafana`, `alertmanager`.

**Lettered sub-clauses (a)–(c)** — exactly 3, covering the per-role contract artifacts:

  (a) `tasks/backup.yml` performs cold-quiesce (docker stop, zstd tarball of the role's named volume(s) into `/opt/telemetron/backups/<role>/<role>-<UTC-ts>.tar.zst`, docker start, verify) wrapped in `block:/rescue:/always:` so the container is running at the end regardless of tar success/failure.

  (b) `tasks/restore.yml` asserts `backup_restore_confirm == true` (fail-fast gate), runs `tar tf` integrity check, wipes the volume's `_data/`, untars, restarts, verifies.

  (c) Both files start with an `ansible.builtin.package: name: zstd state: present` pre-task; idempotent on hosts that already have it.

Planner MAY add a 4th sub-clause (d) only if a genuinely distinct contract element emerges (e.g., the Garage s3-credentials inclusion or the Prometheus /prometheus/lock deletion); recommended to fold these into clauses (a)/(b) prose to keep the gate at 3 clauses matching the CONTEXT worked example.

**Divergent-role paragraph** — names all 8 stateless roles verbatim and distinguishes the Garage-handoff subset from the truly-stateless subset:

  Stateless roles document their no-backup status in their role README only (no empty `tasks/backup.yml` no-op files). The 8 stateless roles are: `loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`, `opentelemetry`, `nfsd`. Loki/Tempo/Mimir data lives in Garage S3 buckets (covered by the garage role); the remaining 5 carry no operator state.

**Closing paragraph** (mirrors Gate 10's in-gate / out-of-gate / forward-point / Established-in-Phase pattern per D-208):

  Orchestrator behavior -- the `backup_continue_on_failure` knob, writer-quiesce on Garage restore (Loki/Tempo/Mimir stop before, restart after), and restore's hardcoded bail-out (`any_errors_fatal: true`) -- is out of Gate 11 scope. Phase 14 shipped these as `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` concerns; the per-role contract above is sufficient. See `docs/quickstart.md#backup-and-restore` for the operator-facing story. Established in Phase 13-14 plans; future role additions inherit this contract.

Use ASCII double-hyphen `--` for em-dash positions (matches Gate 10 convention). Use backticks for inline code (`tasks/backup.yml`, `tasks/restore.yml`, role names, knob names, file paths).

Gate 11 body length budget: 15-30 lines (Gate 10 is 17 lines; CONTEXT.md worked example is ~25 lines).

Note: `roles/README.md` is contributor-facing — D-XXX citations in the lede are EXPECTED (Pattern S3 exception). Gates 1-10 cite D-IDs; Gate 11 follows suit by citing D-176..D-179 in its lede.

DO NOT modify Gate 10's existing closing paragraph — Phase 12 plan 12-03 already finalized it (12-VERIFICATION.md line 100-109 verifies the finalized state). Gate 11 is purely additive.
  </action>
  <verify>
    <automated>grep -q '^\*\*11\. ' roles/README.md &amp;&amp; grep -q 'tasks/backup.yml' roles/README.md &amp;&amp; grep -q 'tasks/restore.yml' roles/README.md &amp;&amp; grep -q 'proven on leviathan' roles/README.md &amp;&amp; for r in garage prometheus grafana alertmanager loki tempo mimir fluentbit karma node_exporter opentelemetry nfsd; do grep -q "\`$r\`" roles/README.md || { echo "FAIL: $r not named verbatim in roles/README.md"; exit 1; }; done &amp;&amp; grep -q 'docs/quickstart.md#backup-and-restore' roles/README.md &amp;&amp; grep -q 'future role additions inherit this contract' roles/README.md &amp;&amp; grep -q 'backup_continue_on_failure' roles/README.md &amp;&amp; grep -q 'any_errors_fatal' roles/README.md &amp;&amp; awk '/^\*\*10\./{g10=NR} /^\*\*11\./{g11=NR} END{exit (g10 &amp;&amp; g11 &amp;&amp; g10&lt;g11)?0:1}' roles/README.md &amp;&amp; awk '/^```/ { c++ } END { exit (c%2==0)?0:1 }' roles/README.md</automated>
  </verify>
  <acceptance_criteria>
    - `roles/README.md` contains exactly one new lede line matching `^\*\*11\. ` (Gate 11 bold lede).
    - Gate 11 lede contains `Per-role backup/restore contract` substring (DOCS-V13-01 contract name).
    - Gate 11 contains the phrase `proven on leviathan` (D-207 acceptance heuristic phrasing — required).
    - Gate 11 names all 4 stateful roles VERBATIM as backtick-delimited inline code: `` `garage` ``, `` `prometheus` ``, `` `grafana` ``, `` `alertmanager` ``.
    - Gate 11 names all 8 stateless roles VERBATIM as backtick-delimited inline code: `` `loki` ``, `` `tempo` ``, `` `mimir` ``, `` `fluentbit` ``, `` `karma` ``, `` `node_exporter` ``, `` `opentelemetry` ``, `` `nfsd` ``.
    - Gate 11 contains literal file-name strings `tasks/backup.yml` and `tasks/restore.yml` (DOCS-V13-01 contract artifact names).
    - Gate 11 contains semantic equivalent of "no empty no-op task files" (stateless roles document in README only — required by DOCS-V13-01).
    - Gate 11 closing paragraph forward-points to `docs/quickstart.md#backup-and-restore` (D-208 forward-pointer).
    - Gate 11 closing paragraph names the 3 orchestrator-level concerns explicitly: `backup_continue_on_failure` knob, writer-quiesce on Garage restore (Loki/Tempo/Mimir stop before / restart after), and `any_errors_fatal` hardcode.
    - Gate 11 closing line matches the Gate 10 closing-line pattern: contains `future role additions inherit this contract` (D-207 closing pattern).
    - Gate 11 closing line names the Phase 13-14 origin: contains the substring `Phase 13-14` (or `Phase 13` AND `Phase 14`).
    - Gate 10's lede `^\*\*10\. ` and closing line are unchanged from the pre-edit state (Phase 12 plan 12-03 output preserved — non-regression).
    - Gate 10's lede appears BEFORE Gate 11's lede in the file (line ordering check: `awk '/^\*\*10\./{g10=NR} /^\*\*11\./{g11=NR} END{exit (g10&lt;g11)?0:1}'`).
    - Gate 11 body length: 15-30 lines.
    - Code-fence balance: even number of ``` in `roles/README.md` (Gate 11 is prose-only — adds zero fences).
    - Zero new non-ASCII characters introduced (pre-existing ☑ checkboxes in the inventory table at lines 9-21 and existing § in unrelated sections are out-of-scope per Phase 12 12-VERIFICATION.md anti-patterns table).
    - D-IDs `D-176..D-179` cited in Gate 11 lede (Pattern S3 exception — `roles/README.md` is contributor-facing, gates 1-10 already cite D-IDs).
  </acceptance_criteria>
  <done>
    `roles/README.md` contains a new Gate 11 entry inserted after Gate 10 (line 122 of pre-edit file). Gate 11 matches Gate 10's depth (15-30 lines), structure (lede → contract → sub-clauses → divergent paragraph → closing paragraph with forward-pointer), and voice. All 4 stateful + 8 stateless role names appear verbatim in backticks. Contract file names (tasks/backup.yml, tasks/restore.yml), acceptance heuristic (proven on leviathan), and closing-line pattern (future role additions inherit this contract) all present. Gate 10 is unchanged.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs → operator (root README) | Root README is the project's first-contact surface; misleading cross-refs cost operators time and trust. |
| docs → contributor (roles/README.md) | Gate 11 codifies the contract future role additions inherit; an incomplete or vague gate causes contract drift over future milestones. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-15-12 | Tampering | README.md "When something goes wrong" link target | mitigate | The link `docs/quickstart.md#backup-and-restore` must resolve to the H2 created by plan 15-01 in the same wave. Per D-210 + Phase 12 D-174 precedent: forward-referenced markdown anchors are stable regardless of plan merge order. Acceptance criterion asserts the exact link target string. |
| T-15-13 | Tampering | roles/README.md Gate 11 role enumeration | mitigate | If Gate 11 omits a role name, future contributors may believe that role has no backup/restore obligation (or has one when it shouldn't). Acceptance criteria force verbatim backtick-enclosed inline-code mentions of all 12 deployed role names (4 stateful + 8 stateless) — drift-resistant. |
| T-15-14 | Tampering | roles/README.md Gate 11 contract sub-clauses | mitigate | Sub-clauses (a)/(b)/(c) describe the actual Phase 13 contract: cold-quiesce + block/rescue/always; confirm-gate + tar tf + wipe + untar + restart + verify; zstd pre-task. Executor reads the actual Phase 13 task files indirectly via 15-CONTEXT.md (sourced from those files); if Phase 13 ever changes the contract, Gate 11 prose must update accordingly. Acceptance criteria assert key contract substrings (`tasks/backup.yml`, `tasks/restore.yml`, `proven on leviathan`). |
| T-15-15 | Repudiation | Gate 11 in-gate vs out-of-gate scope | mitigate | Gate 11's closing paragraph distinguishes per-role contract concerns (in-gate) from orchestrator-level concerns (out-of-gate: `backup_continue_on_failure`, writer-quiesce, `any_errors_fatal`). Without this distinction, a future contributor adding a 5th stateful role might assume they need to implement orchestrator behavior in the role. Acceptance criterion asserts all 3 out-of-gate concerns are named in the closing paragraph. |
| T-15-16 | Information Disclosure | D-IDs in roles/README.md vs README.md | accept (low) / mitigate | Gate 11 lede cites D-176..D-179 (contributor-facing — Pattern S3 exception; matches Gate 10's D-148 citation). Root README "When something goes wrong" paragraph MUST NOT cite D-IDs (operator-facing — Pattern S3). Acceptance criteria enforce this asymmetry. |
| T-15-17 | Tampering | Non-regression on Gate 10 | mitigate | Phase 12 plan 12-03 already finalized Gate 10's closing paragraph (12-VERIFICATION.md line 100-109). Gate 11 is purely additive; Gate 10 is untouched. Acceptance criterion asserts `^**10. ` lede exists AND line-orders before `^**11. ` lede (which would fail if Gate 10 were accidentally deleted or modified). |

All threats are LOW severity (doc-only phase). Gate passes — no `high` severity threats per `block_on: high` config.
</threat_model>

<verification>
- `README.md` "When something goes wrong" paragraph present, links to `docs/quickstart.md#backup-and-restore`, contains required phrases verbatim (`backup_restore_confirm=true`, `operator manages retention`), sits AFTER the existing "When you're done evaluating" paragraph and BEFORE `## What's included`.
- `roles/README.md` Gate 11 present, lede matches `^\*\*11\. `, contains all required substrings: contract name (`Per-role backup/restore contract`), 4 stateful role names + 8 stateless role names verbatim in backticks, contract file names (`tasks/backup.yml`, `tasks/restore.yml`), acceptance heuristic (`proven on leviathan`), forward-pointer (`docs/quickstart.md#backup-and-restore`), closing-line pattern (`future role additions inherit this contract`), Phase 13-14 origin attribution.
- Gate 10 unchanged (Phase 12 plan 12-03 output preserved); Gate 10 line-orders before Gate 11.
- Gate 11 body length: 15-30 lines.
- Code-fence balance preserved in both files (no new fences in either).
- Zero new non-ASCII characters introduced (pre-existing ☑ / § / em-dash in `roles/README.md` unrelated sections are out-of-scope per Phase 12 12-VERIFICATION.md anti-patterns table).
- Zero `D-XXX` references in `README.md` (operator-facing); `D-176..D-179` cited in `roles/README.md` Gate 11 lede (contributor-facing — Pattern S3 exception, matches Gate 10 convention).
</verification>

<success_criteria>
- 2 files modified: `README.md` and `roles/README.md`.
- All acceptance criteria for Tasks 1 and 2 pass.
- Threat model gate passes (no `high` severity threats).
- Closes DOCS-V13-01 (Gate 11) in full.
- Closes DOCS-V13-02 root-README clause (the H2 main clause is closed by plan 15-01).
</success_criteria>

<output>
Create `.planning/phases/15-documentation-cascade/15-03-SUMMARY.md` when done, mirroring the structure of `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-03-SUMMARY.md` (frontmatter + per-task changes-made section + DOCS-V13-01 and DOCS-V13-02 root-clause closure statements + deviations + threat flags + self-check).
</output>
