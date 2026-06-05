---
phase: 15-documentation-cascade
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/quickstart.md
autonomous: true
requirements:
  - DOCS-V13-02
tags:
  - documentation
  - quickstart
  - backup
  - restore
  - DOCS-V13-02

must_haves:
  truths:
    - "Operator reading docs/quickstart.md finds a `## Backup and restore` H2 section that covers the default backup command, the restore workflow with the confirm-gate, the Garage-restore stop-order, the retention model, and a manual tarball-extraction fallback."
    - "Operator can copy-paste the default backup command line and run it without further reading."
    - "Operator sees the `--extra-vars backup_restore_confirm=true` gate stated explicitly and understands it as the deliberate opt-in."
    - "Operator reads Loki/Tempo/Mimir stop-before-Garage-restore behavior and understands restore_docker.yml handles it automatically (no manual intervention)."
    - "Operator who refuses to run restore_docker.yml has a complete copy-paste manual fallback recipe using docker commands only."
    - "Operator sees retention is operator-managed (find/rsync/restic/borg are operator concerns; Telemetron stays opinion-free)."
  artifacts:
    - path: "docs/quickstart.md"
      provides: "## Backup and restore H2 section with 5 sub-H3 subsections"
      contains: "## Backup and restore"
  key_links:
    - from: "docs/quickstart.md ## Backup and restore"
      to: "playbooks/backup_docker.yml banner (D-186) and playbooks/restore_docker.yml WARN banner (D-187)"
      via: "verbatim quoted command lines and banner output"
      pattern: "backup_restore_confirm=true|backup_continue_on_failure|backup_restore_from|Restore order: stop Loki/Tempo/Mimir"
    - from: "docs/quickstart.md ## Backup and restore"
      to: "inventory/example-homelab/group_vars/all/backup.yml"
      via: "knob names match exactly"
      pattern: "backup_dest_root|backup_stop_timeout|backup_continue_on_failure|backup_restore_confirm|backup_restore_from"
---

<objective>
Add a `## Backup and restore` H2 section to `docs/quickstart.md` (mirroring Phase 12 plan 12-01's `## Removing Telemetron` shape) with 5 sub-H3 subsections (`### Backup`, `### Restore`, `### Stop order during Garage restore`, `### Retention`, `### Manual fallback`) that close DOCS-V13-02's main clause.

Purpose: Operators discover the v1.3.0 backup-and-restore story entirely through this section — default commands, the `backup_restore_confirm=true` opt-in safety gate, the writer-quiesce stop-order, local-disk retention model, and a copy-paste manual fallback for operators who refuse to use `restore_docker.yml`. No source-code reading required.

Output: One modified file (`docs/quickstart.md`) with a new H2 section between `## Upgrade notes` (line 270) and `## Removing Telemetron` (line 272) per D-202 + CONTEXT.md `<specifics>` recommendation (backup is operationally more frequent than removal — lead with it).
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
@.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-01-SUMMARY.md

<interfaces>
<!-- Source-of-truth references the executor must read before writing prose. -->
<!-- These files define the exact command-line / banner / knob shapes that quickstart prose must match verbatim. -->

From playbooks/backup_docker.yml (lines 119-127) — Backup PLAY-start banner (D-186):
- Exact banner format (debug msg block):
  - "Backup destination: {{ backup_dest_root }}/<role>/"
  - "backup_continue_on_failure={{ backup_continue_on_failure | default(false) }}"
  - Conditional suffix: "(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)" if true, else "(first role failure will abort the playbook)"
  - "backup_stop_timeout={{ backup_stop_timeout }}s"

From playbooks/restore_docker.yml (lines 110-117) — Restore WARN banner (D-187):
- Exact banner format (debug msg block):
  - "WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)"
  - "Target timestamp: {{ backup_restore_from | default('<latest per role>') }}"
  - "Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir"
- NOTE: the "Restore order:" line ALREADY satisfies the DOCS-V13-02 "Loki/Tempo/Mimir stop before Garage restore" grep-pin gate when quoted verbatim.

From inventory/example-homelab/group_vars/all/backup.yml — 5 knobs with defaults (verbatim source-of-truth for ### Backup / ### Restore / ### Retention H3s):
- backup_dest_root = "/opt/telemetron/backups"        (line 13) — used in ### Backup and ### Retention
- backup_stop_timeout = 60                            (line 20) — used in ### Backup (brief)
- backup_continue_on_failure = false                  (line 25) — used in ### Backup per D-205
- backup_restore_confirm = false                      (line 33) — used in ### Restore (THE gate)
- backup_restore_from = ""                            (line 41) — used in ### Restore (selector)

From docs/quickstart.md (lines 272-391) — Phase 12 ## Removing Telemetron section is the structural template:
- Same H2 anchor convention (`## X` → GitHub auto-anchor `#x` lowercase-hyphenated)
- Same fence style (bash, text), same multi-line ansible-playbook with `\` continuations
- Same cross-ref discipline (cross-ref to role README from quickstart; e.g. roles/garage/README.md)
- Same "conservative by default" framing register
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Insert ## Backup and restore H2 section into docs/quickstart.md between ## Upgrade notes and ## Removing Telemetron</name>
  <files>docs/quickstart.md</files>
  <read_first>
    <file>docs/quickstart.md</file>
    <reason>See current line 270 (end of ## Upgrade notes) and line 272 (## Removing Telemetron) to confirm insertion point; absorb the prose voice and code-fence style of the analog ## Removing Telemetron section (lines 272-391) to mirror exactly.</reason>
    <file>.planning/phases/15-documentation-cascade/15-PATTERNS.md</file>
    <reason>The "Plan 15-01" section contains line-ranged analog excerpts (272-285, 286-299, 301-316, 362-391), the verbatim backup/restore banner sources, the 5-knob source-of-truth table, and the verbatim phrase gates this task must satisfy.</reason>
    <file>.planning/phases/15-documentation-cascade/15-CONTEXT.md</file>
    <reason>D-202 lists the 5 required H3s; D-203 sets the 100-220 line budget; D-204 specifies grafana as the manual-fallback worked example; D-205 specifies the backup_continue_on_failure one-liner placement; the `<specifics>` block has the skeleton scaffold (lines 261-296).</reason>
    <file>.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-01-SUMMARY.md</file>
    <reason>Phase 12 analog: 120 body lines for the ## Removing Telemetron section, 4-bullet DOCS-01 contract coverage table, D-165..D-168 verification matrix. Phase 15 mirrors this shape and scale (D-203 budget is 100-220 which already accounts for the larger 5-H3 scope).</reason>
    <file>playbooks/backup_docker.yml</file>
    <reason>Source-of-truth for the D-186 PLAY-start banner (lines 119-127 per PATTERNS) — the ### Backup subsection quotes the operator-facing banner output verbatim.</reason>
    <file>playbooks/restore_docker.yml</file>
    <reason>Source-of-truth for the D-187 WARN banner (lines 110-117 per PATTERNS) — the ### Restore subsection quotes this banner verbatim, and the "Restore order:" line satisfies the "Loki/Tempo/Mimir stop before Garage restore" grep-pin gate without paraphrasing.</reason>
    <file>inventory/example-homelab/group_vars/all/backup.yml</file>
    <reason>Source-of-truth for all 5 knob names + defaults + per-knob comment prose; the ### Backup / ### Restore / ### Retention H3s reference these knob names exactly (`backup_dest_root`, `backup_stop_timeout`, `backup_continue_on_failure`, `backup_restore_confirm`, `backup_restore_from`). Quickstart must not invent knob names that don't exist in this file.</reason>
  </read_first>
  <action>
Insert the new `## Backup and restore` H2 section into `docs/quickstart.md` between the existing `## Upgrade notes` (ending at line 270) and `## Removing Telemetron` (starting line 272). Reading order becomes: Upgrade notes → Backup and restore (new) → Removing Telemetron → Building your own inventory (per D-202 + CONTEXT.md `<specifics>` option (b) recommendation).

The section MUST contain exactly these 5 H3 subsections in this order:

  1. `### Backup`
  2. `### Restore`
  3. `### Stop order during Garage restore`
  4. `### Retention`
  5. `### Manual fallback`

Open with a 3-5 line intro paragraph that frames the section: what it covers (local-disk dated tarballs of stateful role data; restore round-trip), v1.3.0 scope (single-host, single-version, operator-managed retention), and the conservative-by-default posture. Mirror the "Undeploy is the symmetric inverse..." opening register from lines 272-279 of the analog.

`### Backup`: lead with the default command (multi-line `ansible-playbook -i inventory/example-homelab playbooks/backup_docker.yml --ask-vault-pass` in a bash fence with `\` line continuations matching the Phase 12 style at lines 280-284). Then quote the D-186 backup PLAY-start banner verbatim in a ```text fence (the exact 4-line msg block from `playbooks/backup_docker.yml` lines 119-127 — pull the `Backup destination:`, `backup_continue_on_failure=`, and `backup_stop_timeout=` lines). Then a brief prose paragraph naming `backup_dest_root` default (`/opt/telemetron/backups`) and the tarball filename pattern (`<role>-<UTC-timestamp>.tar.zst`, mode 0600, dest dir mode 0700). Include the D-205 one-liner mention of `backup_continue_on_failure=true` opt-in with use-case explanation ("attempts all 4 roles even if one fails; failures aggregated in PLAY RECAP"). Close with a one-line per-role tag-scoped invocation: "To back up a single role, add `--tags <role>` (any of: `garage`, `prometheus`, `grafana`, `alertmanager`)."

`### Restore`: lead with the default command including the `--extra-vars backup_restore_confirm=true` gate (multi-line bash fence). State explicitly that the playbook refuses to run without this flag (OPS-V13-01 contract). Quote the D-187 WARN banner verbatim in a ```text fence — the 3-line msg block from `playbooks/restore_docker.yml` lines 110-117 including `WARNING: irreversible -- restore will PERMANENTLY REPLACE...`, `Target timestamp:`, and the literal `Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir` line. Include a brief prose paragraph on the `backup_restore_from` selector (timestamp string or `<latest per role>` if empty). Add a one-line explicit asymmetry note per D-205: "Restore has no continue-on-failure knob — `any_errors_fatal: true` is hardcoded so a partial-restore half-state can't accumulate silently."

`### Stop order during Garage restore`: 4-8 line paragraph stating that `restore_docker.yml` automatically stops Loki, Tempo, and Mimir before the Garage restore (because they are Garage S3 writers and would crash-loop if Garage stops while they are writing — XP-2 pitfall in PROJECT.md). State that the operator does NOT intervene; the orchestrator restarts them after Garage is restored. Mention that `--tags garage` triggers the full stop-restore-restart cycle (not just the Garage step in isolation).

`### Retention`: short paragraph stating that Telemetron writes dated tarballs to `/opt/telemetron/backups/<role>/` with the literal phrase "operator manages retention" appearing in the prose. Per D-204 Claude's Discretion: include 2-3 one-line examples of operator retention tooling (e.g., `find /opt/telemetron/backups/ -mtime +30 -delete`, `rsync` to off-host, `restic` integration). Explicitly state Telemetron stays opinion-free on the off-host layer (mirroring the reverse-proxy-agnostic philosophy from v1.0).

`### Manual fallback`: full worked-example recipe for operators who refuse to use `restore_docker.yml`. Use grafana as the worked example (D-204 — simplest layout, one volume). Show 4 bash fence steps:
  1. `docker stop telemetron-grafana`
  2. Wipe the named volume via alpine: `docker run --rm -v telemetron_grafana_data:/d alpine sh -c 'rm -rf /d/*'`
  3. Extract the tarball via alpine + unzstd: `docker run --rm -v telemetron_grafana_data:/d -v /opt/telemetron/backups/grafana:/b alpine sh -c 'tar --use-compress-program=unzstd -xf /b/<file>.tar.zst -C /d'`
  4. `docker start telemetron-grafana`
Close with a one-line note: "Garage's 3-entry tarball has 3 paths to extract (telemetron_garage_meta volume, telemetron_garage_data volume, host-mounted `s3-credentials` file) — see `roles/garage/README.md#backup` for the path map."

Across the section: zero `D-XXX` decision references in the prose (Phase 12 gate inheritance — this is operator-facing, not contributor-facing). Zero non-ASCII regressions (no curly quotes, no smart dashes — use ASCII `--` not the em-dash character). Even number of ``` fences. Body line count 100-220 per D-203.

Write the section in the same prose voice as the Phase 12 ## Removing Telemetron section (lines 272-391): short declarative sentences, "conservative by default" framing, multi-line ansible-playbook commands with `\` continuations, code-fence-followed-by-one-sentence-explanation rhythm.
  </action>
  <verify>
    <automated>grep -c '^## Backup and restore$' docs/quickstart.md | awk '{ exit ($1==1)?0:1 }' &amp;&amp; grep -c '^### Backup$' docs/quickstart.md | awk '{ exit ($1==1)?0:1 }' &amp;&amp; grep -c '^### Restore$' docs/quickstart.md | awk '{ exit ($1==1)?0:1 }' &amp;&amp; grep -c '^### Stop order during Garage restore$' docs/quickstart.md | awk '{ exit ($1==1)?0:1 }' &amp;&amp; grep -c '^### Retention$' docs/quickstart.md | awk '{ exit ($1==1)?0:1 }' &amp;&amp; grep -c '^### Manual fallback$' docs/quickstart.md | awk '{ exit ($1==1)?0:1 }' &amp;&amp; grep -q 'backup_restore_confirm=true' docs/quickstart.md &amp;&amp; grep -q 'Loki/Tempo/Mimir' docs/quickstart.md &amp;&amp; grep -q '/opt/telemetron/backups' docs/quickstart.md &amp;&amp; grep -q 'operator manages retention' docs/quickstart.md &amp;&amp; awk '/^```/ { c++ } END { exit (c%2==0)?0:1 }' docs/quickstart.md &amp;&amp; ! grep -nP '[^\x00-\x7F]' docs/quickstart.md | grep -v '^[0-9]*:.*[§☑]' | grep . &amp;&amp; ! grep -E 'D-(19[4-9]|2[0-1][0-9])' docs/quickstart.md</automated>
  </verify>
  <acceptance_criteria>
    - Exactly 1 occurrence of `^## Backup and restore$` in docs/quickstart.md (grep -c == 1).
    - Exactly 1 occurrence each of the 5 H3s: `^### Backup$`, `^### Restore$`, `^### Stop order during Garage restore$`, `^### Retention$`, `^### Manual fallback$` (grep -c == 1 for each).
    - H2 section appears between `## Upgrade notes` and `## Removing Telemetron` — verified by extracting the line numbers and asserting `line(## Upgrade notes) &lt; line(## Backup and restore) &lt; line(## Removing Telemetron)`.
    - Verbatim phrase `backup_restore_confirm=true` present (DOCS-V13-02 grep-pin gate).
    - Verbatim phrase `backup_continue_on_failure` present (D-205 + OPS-V13-02 mention).
    - Verbatim phrase `backup_restore_from` present (D-187 selector mention).
    - Literal `Loki/Tempo/Mimir` substring present (DOCS-V13-02 stop-order phrasing; the D-187 banner quote satisfies this).
    - Literal `Restore order: stop Loki/Tempo/Mimir -&gt; garage -&gt; prometheus -&gt; grafana -&gt; alertmanager -&gt; restart Loki/Tempo/Mimir` present (D-187 banner quoted verbatim).
    - Literal `/opt/telemetron/backups` present (dated-tarball destination per DOCS-V13-02).
    - Literal `operator manages retention` present (DOCS-V13-02 operator-managed framing).
    - Literal `WARNING: irreversible -- restore will PERMANENTLY REPLACE` present (D-187 WARN banner verbatim).
    - Literal `docker run --rm -v telemetron_grafana_data` present (D-204 manual-fallback worked example).
    - Literal `tar --use-compress-program=unzstd` present (D-204 manual-fallback extraction command).
    - Section body line count between 100 and 220 inclusive (D-203 budget).
    - Even number of ``` fence delimiters across the entire file (code-fence balance — Pattern S4).
    - Zero NEW non-ASCII characters introduced (pre-existing § / ☑ / em-dash in unmodified sections are out of scope per Phase 12 verification precedent; verification compares lines in the new section only).
    - Zero `D-XXX` decision references in operator-facing prose (Pattern S3) — `! grep -E 'D-(19[4-9]|2[0-1][0-9])' docs/quickstart.md` returns empty.
    - All 5 sub-H3s appear in the order Backup → Restore → Stop order during Garage restore → Retention → Manual fallback (verified by `grep -n '^### '` line ordering within the section).
  </acceptance_criteria>
  <done>
    docs/quickstart.md contains a new `## Backup and restore` H2 section between `## Upgrade notes` and `## Removing Telemetron` with all 5 required H3 subsections, all DOCS-V13-02 grep-pin phrases present verbatim, banner blocks quoted verbatim from the actual playbook files, line count within 100-220, code-fence balance preserved, and zero D-ID leaks into operator-facing prose.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs → operator | The docs are the operator's source of truth; copy-pasted commands run against the production homelab. A stale or wrong command example causes data loss during restore. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-15-01 | Tampering | docs/quickstart.md backup command examples | mitigate | Quote the actual `playbooks/backup_docker.yml` D-186 banner verbatim (read from file during task); verify exact knob names match `inventory/example-homelab/group_vars/all/backup.yml`. Grep-pin acceptance criterion asserts `backup_restore_confirm=true` and `backup_continue_on_failure` appear verbatim. |
| T-15-02 | Tampering | docs/quickstart.md restore WARN banner | mitigate | Quote the actual `playbooks/restore_docker.yml` D-187 banner verbatim including the literal `Restore order: stop Loki/Tempo/Mimir -&gt; garage -&gt; prometheus -&gt; grafana -&gt; alertmanager -&gt; restart Loki/Tempo/Mimir` line. Acceptance criterion asserts this verbatim phrase is present. |
| T-15-03 | Information Disclosure | docs/quickstart.md operator-facing prose | accept (low) | Risk: `D-XXX` planning IDs leak into operator-facing prose, exposing internal planning structure. Severity LOW — no secrets disclosed, only project methodology. Mitigation: explicit acceptance criterion `! grep -E 'D-(19[4-9]|2[0-1][0-9])' docs/quickstart.md` enforces zero D-ID leaks (Phase 12 verification gate inheritance — Pattern S3). |
| T-15-04 | Tampering | docs/quickstart.md ### Manual fallback recipe | mitigate | Operator copies wrong unzstd / tar flags → restore produces empty volume. Mitigation: use the canonical `tar --use-compress-program=unzstd` invocation that the per-role `tasks/restore.yml` files use (verified against `roles/grafana/tasks/restore.yml` Phase 13 output). Acceptance criterion asserts this exact substring appears. |
| T-15-05 | Denial of Service | Broken cross-ref to anchor `#backup-and-restore` | mitigate (parallel-safe) | Per-role READMEs (plan 15-02) and root README (plan 15-03) forward-link to `#backup-and-restore`. GitHub auto-anchor produces this lowercase-hyphenated slug from `## Backup and restore`. Acceptance criterion asserts the exact H2 spelling. |

All threats are LOW severity (doc-only phase, no auth/schema/network surface). Gate passes — no `high` severity threats per `block_on: high` config.
</threat_model>

<verification>
- `## Backup and restore` H2 exists exactly once, between `## Upgrade notes` and `## Removing Telemetron`.
- All 5 required H3 subsections present in the locked order.
- DOCS-V13-02 verbatim phrases all present: `backup_restore_confirm=true`, `Loki/Tempo/Mimir`, `/opt/telemetron/backups`, `operator manages retention`.
- D-186 backup banner block quoted verbatim from `playbooks/backup_docker.yml` lines 119-127.
- D-187 restore WARN banner block quoted verbatim from `playbooks/restore_docker.yml` lines 110-117, including the `Restore order:` line.
- D-204 manual-fallback recipe present (grafana worked example with docker stop / alpine wipe / alpine untar / docker start).
- Body line count for the new H2 section: 100-220 (D-203).
- Code-fence balance: even number of ``` across the entire file.
- Zero new non-ASCII characters introduced.
- Zero `D-XXX` references in operator-facing prose.
</verification>

<success_criteria>
- File modified: `docs/quickstart.md` only.
- Net change: section body 100-220 lines added between line 270 and line 272 of the pre-edit file.
- All acceptance criteria for Task 1 pass.
- Threat model gate passes (no `high` severity threats).
- Closes DOCS-V13-02 main clause (operator-facing quickstart section); root-README clause is closed by plan 15-03.
</success_criteria>

<output>
Create `.planning/phases/15-documentation-cascade/15-01-SUMMARY.md` when done, mirroring the structure of `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-01-SUMMARY.md` (frontmatter + section details + DOCS-V13-02 contract coverage table + decision verification matrix + acceptance gate results + deviations + self-check).
</output>
