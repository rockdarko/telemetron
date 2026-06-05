---
phase: 15-documentation-cascade
plan: "02"
type: execute
wave: 1
depends_on: []
files_modified:
  - roles/garage/README.md
  - roles/prometheus/README.md
  - roles/grafana/README.md
  - roles/alertmanager/README.md
  - roles/loki/README.md
  - roles/tempo/README.md
  - roles/mimir/README.md
  - roles/fluentbit/README.md
  - roles/karma/README.md
  - roles/node_exporter/README.md
  - roles/opentelemetry/README.md
  - roles/nfsd/README.md
autonomous: true
requirements:
  - DOCS-V13-03
tags:
  - documentation
  - role-readmes
  - backup
  - DOCS-V13-03

must_haves:
  truths:
    - "Every deployed-role README (12 files) contains exactly one `## Backup` H2 section so the operator finds backup information at the same anchor in every role's README (#backup)."
    - "Each of the 4 stateful role READMEs (garage, prometheus, grafana, alertmanager) has a `## Backup` section using the uniform 5-part skeleton: one-line intro, Captured bullet list, Not captured bullet list, tag-scoped invocation bash fence, cross-ref to docs/quickstart.md#backup-and-restore."
    - "Each stateful section's Captured/Not-captured bullets honestly describe what the corresponding tasks/backup.yml actually captures vs what re-renders from config — the operator-useful surprises (Garage's s3-credentials IS captured; Grafana's provisioning is NOT captured) are stated explicitly."
    - "The 3 Garage-backed stateless roles (loki, tempo, mimir) have `## Backup` sections containing a single sentence pointing the operator to the garage role's backup."
    - "The 5 truly-stateless roles (fluentbit, karma, node_exporter, opentelemetry, nfsd) have `## Backup` sections containing the single sentence 'No operator state to preserve.' (or ≤5 word extension)."
    - "The nfsd README's `## Backup` section is placed immediately BEFORE its divergent `## Uninstall` block (which sits post-Verification per Phase 12 D-172), preserving the divergent reading flow established by Phase 12."
  artifacts:
    - path: "roles/garage/README.md"
      provides: "## Backup H2 with 3-entry tarball Captured list (telemetron_garage_meta volume, telemetron_garage_data volume, s3-credentials host file) + (nothing) Not-captured"
      contains: "## Backup"
    - path: "roles/prometheus/README.md"
      provides: "## Backup H2 with 1-entry tarball Captured (telemetron_prometheus_data) + Not-captured note re: /prometheus/lock"
      contains: "## Backup"
    - path: "roles/grafana/README.md"
      provides: "## Backup H2 with 1-entry tarball Captured (telemetron_grafana_data) + Not-captured (provisioning re-renders from version-controlled config per D-195)"
      contains: "## Backup"
    - path: "roles/alertmanager/README.md"
      provides: "## Backup H2 with 1-entry tarball Captured (telemetron_alertmanager_data) + empty-data stat-guard note"
      contains: "## Backup"
    - path: "roles/loki/README.md"
      provides: "## Backup H2 one-liner pointing to garage role"
      contains: "## Backup"
    - path: "roles/tempo/README.md"
      provides: "## Backup H2 one-liner pointing to garage role"
      contains: "## Backup"
    - path: "roles/mimir/README.md"
      provides: "## Backup H2 one-liner pointing to garage role"
      contains: "## Backup"
    - path: "roles/fluentbit/README.md"
      provides: "## Backup H2 stateless one-liner"
      contains: "## Backup"
    - path: "roles/karma/README.md"
      provides: "## Backup H2 stateless one-liner"
      contains: "## Backup"
    - path: "roles/node_exporter/README.md"
      provides: "## Backup H2 stateless one-liner"
      contains: "## Backup"
    - path: "roles/opentelemetry/README.md"
      provides: "## Backup H2 stateless one-liner"
      contains: "## Backup"
    - path: "roles/nfsd/README.md"
      provides: "## Backup H2 stateless one-liner, placed before divergent ## Uninstall block per D-201"
      contains: "## Backup"
  key_links:
    - from: "roles/{garage,prometheus,grafana,alertmanager}/README.md ## Backup"
      to: "docs/quickstart.md#backup-and-restore"
      via: "End-of-section cross-ref line: 'See `docs/quickstart.md#backup-and-restore` for the full backup/restore story (knobs, restore workflow, manual fallback).'"
      pattern: "docs/quickstart.md#backup-and-restore"
    - from: "roles/{loki,tempo,mimir}/README.md ## Backup"
      to: "roles/garage/README.md#backup"
      via: "Data-in-Garage handoff sentence"
      pattern: "roles/garage/README.md#backup"
---

<objective>
Add a `## Backup` H2 section to every deployed-role README — 4 stateful roles (garage, prometheus, grafana, alertmanager) with the full 5-part skeleton (D-195), plus 8 stateless roles (loki, tempo, mimir, fluentbit, karma, node_exporter, opentelemetry, nfsd) with the appropriate two-template one-liner (D-199). 12 files modified in one plan.

Purpose: Operators scanning any role's README find backup information at the same anchor (`#backup`) — the stateful roles document what is and is not captured in the tarball (the operator-useful surprises drive the section's value: Garage captures host-mounted `s3-credentials` intentionally; Grafana does NOT capture provisioning because it re-renders from version-controlled config); the stateless roles either point to Garage as the actual backup target (loki/tempo/mimir) or state "No operator state to preserve." (fluentbit/karma/node_exporter/opentelemetry/nfsd).

Output: 12 modified files. New `## Backup` H2 inserted between `## Volumes` and `## Uninstall` for 11 roles; the nfsd README inserts between `## Verification` and the divergent `## Uninstall` block per D-201.

Closes DOCS-V13-03 in full.
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
@.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-02-SUMMARY.md

<interfaces>
<!-- 12-file slot map: insertion line ranges, template variant, per-role wording guidance. -->
<!-- All line numbers below are FROM the PATTERNS.md per-file slot map (verified). Insertions are ADDITIVE — the line numbers shift downward after each insert; executor MUST re-read line numbers fresh for each file rather than rely on cached counts. -->

Stateful skeleton template (rows 1-4 — apply uniformly per D-195):
- One-line intro: "The &lt;role&gt; role ships `tasks/backup.yml` and `tasks/restore.yml` for atomic cold-quiesce backup and restore of &lt;role&gt;'s &lt;volume(s)&gt;."
- `**Captured (&lt;N&gt; entries in the tarball):**` followed by 1-3 bullets.
- `**Not captured:**` followed by 1-2 bullets (Garage uses single bullet `(nothing — ... intentionally captured)`).
- bash fence with `ansible-playbook playbooks/backup_docker.yml --tags &lt;role&gt; --ask-vault-pass`.
- Cross-ref line: "See `docs/quickstart.md#backup-and-restore` for the full backup/restore story (knobs, restore workflow, manual fallback)."

Stateless Variant A (loki, tempo, mimir — data-in-Garage):
"Data lives in Garage S3 buckets — captured by the garage role's backup. See `roles/garage/README.md#backup`."

Stateless Variant B (fluentbit, karma, node_exporter, opentelemetry, nfsd — truly stateless):
"No operator state to preserve."

Per-role insertion slot map (verified line numbers from 15-PATTERNS.md):

| # | Role | Path | Stateful? | Insert AFTER line | Insert BEFORE line | Template | Special notes |
|---|------|------|-----------|-------------------|--------------------|---------|---------------|
| 1 | garage | roles/garage/README.md | yes | 124 (end of ## Volumes section) | 125 (## Uninstall) | full skeleton | 3-entry tarball; D-176 s3-credentials surprise |
| 2 | prometheus | roles/prometheus/README.md | yes | 174 | 175 (## Uninstall) | full skeleton | 1-entry tarball; mention /prometheus/lock deletion on restore (PP-1) |
| 3 | grafana | roles/grafana/README.md | yes | 105 | 106 (the `---` separator before ## Uninstall at 108) | full skeleton | grafana uses `---` separators between H2 sections; planner adds `---` before and after the new H2 to match existing convention; 1-entry tarball; Not-captured = provisioning |
| 4 | alertmanager | roles/alertmanager/README.md | yes | 81 | 82 (## Uninstall) | full skeleton | 1-entry tarball; empty-data stat-guard (AP-1) note |
| 5 | loki | roles/loki/README.md | no (Garage-backed) | 94 | 95 (## Uninstall) | Variant A | substitute "Loki data" in opening |
| 6 | tempo | roles/tempo/README.md | no (Garage-backed) | 155 | 156 (## Uninstall) | Variant A | substitute "Tempo data" |
| 7 | mimir | roles/mimir/README.md | no (Garage-backed) | 128 | 129 (## Uninstall) | Variant A | substitute "Mimir data" |
| 8 | fluentbit | roles/fluentbit/README.md | no (truly) | 270 | 271 (## Uninstall) | Variant B | one-line |
| 9 | karma | roles/karma/README.md | no (truly) | 88 | 89 (## Uninstall) | Variant B | one-line |
| 10 | node_exporter | roles/node_exporter/README.md | no (truly) | 87 | 88 (## Uninstall) | Variant B | one-line |
| 11 | opentelemetry | roles/opentelemetry/README.md | no (truly) | 163 | 164 (## Uninstall) | Variant B | one-line |
| 12 | nfsd | roles/nfsd/README.md | no (truly, divergent placement) | 191 (post-Verification at 172 — divergent per D-172) | 192 (## Uninstall) | Variant B | one-line; D-201 — operator's /srv/telemetron-nfs/ is THEIR responsibility (already covered by Phase 12's Uninstall disclaimer below) |

Per-stateful-role Captured/Not-captured content (executor must fill these honestly):

| Role | Captured | Not captured |
|------|----------|--------------|
| garage | 3 entries: `telemetron_garage_meta` volume (LMDB metadata); `telemetron_garage_data` volume (object data blocks); `{{ garage_s3_credentials_file }}` host file (S3 keypair Loki/Tempo/Mimir use to write to Garage buckets) | (nothing — Garage's S3 credentials are intentionally captured even though they're a host file, so the restored stack reconnects without operator re-bootstrap) |
| prometheus | 1 entry: `telemetron_prometheus_data` volume (TSDB blocks + chunks_head + WAL) | (nothing host-side — rendered config re-renders from version-controlled templates on next deploy); NOTE: `tasks/restore.yml` deletes `/prometheus/lock` after untar before container start (the lockfile is PID-based and stale from the backup-time process) |
| grafana | 1 entry: `telemetron_grafana_data` volume (embedded SQLite `grafana.db` — dashboards, orgs, users, sessions — plus `plugins/` cache) | provisioning tree at `{{ grafana_config_dir }}/provisioning/` re-renders from version-controlled config on container start; admin password rotation if it changed post-backup (operator concern per GR-4) |
| alertmanager | 1 entry: `telemetron_alertmanager_data` volume (silences + nflog + active-alert state — protobuf files that hold Pitfall 7 dedup memory); empty-data stat-guard (AP-1) handles fresh-deploy case cleanly | rendered `alertmanager.yml` (re-renders from version-controlled config on next deploy) |

Cross-ref pattern (mirror exactly — verbatim end-of-section line for every stateful `## Backup`):

  See `docs/quickstart.md#backup-and-restore` for the full backup/restore
  story (knobs, restore workflow, manual fallback).

This mirrors Phase 12 plan 12-02's per-role cross-ref to `docs/quickstart.md#removing-telemetron`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ## Backup H2 sections to the 4 stateful role READMEs (garage, prometheus, grafana, alertmanager) with the uniform 5-part skeleton</name>
  <files>roles/garage/README.md, roles/prometheus/README.md, roles/grafana/README.md, roles/alertmanager/README.md</files>
  <read_first>
    <file>roles/garage/README.md</file>
    <reason>See the current ## Volumes (line 117) and ## Uninstall (line 125) anchors to confirm insertion point. Read the existing ## Uninstall section (lines 125-136) to mirror its cross-ref voice ("See `docs/quickstart.md#removing-telemetron` for the full undeploy story..."). Absorb the prose register and bash-fence style.</reason>
    <file>roles/prometheus/README.md</file>
    <reason>See current ## Volumes (line 166) and ## Uninstall (line 175). The `## Retention` H2 sits between Volumes and Uninstall in prometheus per Phase 12 12-02-SUMMARY decision note — the new ## Backup must go between ## Volumes and ## Retention (still satisfying "between Volumes and Uninstall" spirit), OR between ## Retention and ## Uninstall. Verify actual line numbers and pick the slot that preserves Volumes→Backup data-lifecycle ordering.</reason>
    <file>roles/grafana/README.md</file>
    <reason>Grafana README uses `---` separators between H2 sections — Phase 12 plan 12-02 note. Read lines 98 (## Volumes) through 110 (post-Uninstall) to see the `---` convention. The new ## Backup H2 must include matching `---` separators above and/or below to maintain the file's visual convention. Confirm separator placement before writing.</reason>
    <file>roles/alertmanager/README.md</file>
    <reason>See current ## Volumes (line 75) and ## Uninstall (line 82). Lightest of the 4 stateful files — clean slot insertion.</reason>
    <file>.planning/phases/15-documentation-cascade/15-PATTERNS.md</file>
    <reason>Plan 15-02 section contains: the 5-part stateful skeleton template (lines 254-280), the per-role Captured/Not-captured content table (lines 305-310), the cross-ref pattern (lines 219-233), the 12-file slot map (lines 237-250). All line ranges and template variants come from this file.</reason>
    <file>.planning/phases/15-documentation-cascade/15-CONTEXT.md</file>
    <reason>D-194 (placement between Volumes and Uninstall); D-195 (5-part uniform skeleton); D-196 (two bullet lists with bolded labels); D-197 (cross-ref line); the `<specifics>` block (lines 183-208) has the garage worked-example skeleton verbatim — use it as the seed for the garage section.</reason>
    <file>.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-02-SUMMARY.md</file>
    <reason>Phase 12 analog: 12 per-role uniform ## Uninstall sections with cross-ref discipline; per-role placement table; deviations recorded for grafana's `---` separator convention and prometheus's interleaved ## Retention section. Phase 15 inherits both conventions.</reason>
    <file>roles/garage/tasks/backup.yml</file>
    <reason>Source-of-truth for what garage's backup.yml ACTUALLY captures. The Captured bullet list must match this file's behavior exactly — read it to confirm the 3-entry shape (meta volume + data volume + s3-credentials host file).</reason>
    <file>roles/prometheus/tasks/backup.yml</file>
    <reason>Source-of-truth for prometheus capture (1-entry tarball: telemetron_prometheus_data) and the restore lock-file behavior. Read tasks/restore.yml as well to confirm the /prometheus/lock deletion step.</reason>
    <file>roles/grafana/tasks/backup.yml</file>
    <reason>Source-of-truth for grafana capture (1-entry tarball: telemetron_grafana_data). Confirm provisioning is NOT captured (it lives at {{ grafana_config_dir }}/provisioning/ — host-mounted from version-controlled config).</reason>
    <file>roles/alertmanager/tasks/backup.yml</file>
    <reason>Source-of-truth for alertmanager capture (1-entry tarball: telemetron_alertmanager_data) and the empty-data stat-guard (AP-1) handling.</reason>
  </read_first>
  <action>
For each of the 4 stateful role READMEs, insert a new `## Backup` H2 section between `## Volumes` and `## Uninstall` (per D-194) using the uniform 5-part skeleton from D-195:

  1. One-line intro: "The &lt;role&gt; role ships `tasks/backup.yml` and `tasks/restore.yml` for atomic cold-quiesce backup and restore of &lt;role&gt;'s &lt;volume(s)&gt;."
  2. `**Captured (&lt;N&gt; entries in the tarball):**` followed by an unordered bullet list (1-3 bullets).
  3. `**Not captured:**` followed by an unordered bullet list (1-2 bullets, single bullet OK).
  4. Bash fence with the per-role tag-scoped invocation:
     ```bash
     ansible-playbook playbooks/backup_docker.yml --tags &lt;role&gt; --ask-vault-pass
     ```
  5. End-of-section cross-ref line (verbatim — mirrors Phase 12 cross-ref discipline):
     "See `docs/quickstart.md#backup-and-restore` for the full backup/restore story (knobs, restore workflow, manual fallback)."

Per-role content (use the verbatim guidance from 15-PATTERNS.md per-stateful-role Captured/Not-captured table; the executor confirms accuracy by reading each role's actual `tasks/backup.yml`):

- **garage** (`roles/garage/README.md`, insert between line 124 and 125 of the pre-edit file): use the worked example from 15-CONTEXT.md `<specifics>` lines 183-208 as the seed. 3-entry Captured list naming both volumes and the `{{ garage_s3_credentials_file }}` host file. Not-captured = "(nothing — Garage's S3 credentials are intentionally captured even though they're a host file, so the restored stack reconnects without operator re-bootstrap)" per D-176. Section length 12-20 lines body.

- **prometheus** (`roles/prometheus/README.md`): insert in the Volumes → (Retention) → Uninstall cluster — choose between Volumes-and-Retention OR Retention-and-Uninstall; recommended placement is between Volumes and Retention (preserves Volumes → Backup data-lifecycle ordering). 1-entry Captured (`telemetron_prometheus_data` volume — TSDB blocks + chunks_head + WAL). Not-captured = nothing host-side; ADD a sentence noting that `tasks/restore.yml` deletes `/prometheus/lock` after untar and before `docker start` (PP-1 contract — lockfile is PID-based and stale from the backup-time process). Section length 10-18 lines body.

- **grafana** (`roles/grafana/README.md`): insert with `---` separators above AND below the new H2 to match the existing file's H2-section convention (Phase 12 plan 12-02 noted this — `roles/grafana/README.md` uses `---` between H2s). 1-entry Captured (`telemetron_grafana_data` volume — embedded SQLite `grafana.db` for dashboards/orgs/users/sessions, plus `plugins/` cache). Not-captured = provisioning tree (re-renders from version-controlled config on container start — D-195's canonical surprise); admin password rotation (operator concern if password changed post-backup, per GR-4). Section length 10-20 lines body.

- **alertmanager** (`roles/alertmanager/README.md`): insert between line 81 and 82 of pre-edit file. 1-entry Captured (`telemetron_alertmanager_data` volume — silences + nflog + active-alert state, protobuf files holding Pitfall 7 dedup memory); mention the empty-data stat-guard (AP-1) note that handles fresh-deploy case cleanly. Not-captured = rendered `alertmanager.yml` (re-renders from version-controlled config). Section length 10-18 lines body.

Across all 4 files:
- Zero `D-XXX` references in operator-facing prose (Pattern S3 — these are operator-facing role READMEs, not contributor-facing).
- Zero new non-ASCII characters introduced (pre-existing § in karma is out-of-scope and not in these 4 files anyway).
- Code-fence balance: each file gains exactly 1 bash fence pair (= 2 ``` delimiters per file); total file fence count remains even.
- Cross-ref line text matches verbatim across all 4 files (operator scanning multiple stateful READMEs sees the same exit-point line).
  </action>
  <verify>
    <automated>for f in roles/garage/README.md roles/prometheus/README.md roles/grafana/README.md roles/alertmanager/README.md; do [ "$(grep -c '^## Backup$' "$f")" -eq 1 ] || { echo "FAIL: $f missing ## Backup"; exit 1; }; grep -q '\*\*Captured' "$f" || { echo "FAIL: $f missing **Captured"; exit 1; }; grep -q '\*\*Not captured' "$f" || { echo "FAIL: $f missing **Not captured"; exit 1; }; grep -q 'docs/quickstart.md#backup-and-restore' "$f" || { echo "FAIL: $f missing cross-ref"; exit 1; }; grep -q 'ansible-playbook playbooks/backup_docker.yml --tags' "$f" || { echo "FAIL: $f missing tag-scoped invocation"; exit 1; }; awk '/^```/ { c++ } END { exit (c%2==0)?0:1 }' "$f" || { echo "FAIL: $f fence imbalance"; exit 1; }; done &amp;&amp; grep -q 'telemetron_garage_meta' roles/garage/README.md &amp;&amp; grep -q 'telemetron_garage_data' roles/garage/README.md &amp;&amp; grep -q 's3-credentials' roles/garage/README.md &amp;&amp; grep -q 'telemetron_prometheus_data' roles/prometheus/README.md &amp;&amp; grep -q '/prometheus/lock' roles/prometheus/README.md &amp;&amp; grep -q 'telemetron_grafana_data' roles/grafana/README.md &amp;&amp; grep -qi 'provisioning' roles/grafana/README.md &amp;&amp; grep -q 'telemetron_alertmanager_data' roles/alertmanager/README.md</automated>
  </verify>
  <acceptance_criteria>
    - Each of the 4 stateful README files contains exactly one `^## Backup$` line.
    - Each of the 4 contains `**Captured` (with the bold label) somewhere within the `## Backup` section.
    - Each of the 4 contains `**Not captured` (with the bold label) somewhere within the `## Backup` section.
    - Each of the 4 contains the literal cross-ref `docs/quickstart.md#backup-and-restore`.
    - Each of the 4 contains the tag-scoped invocation pattern `ansible-playbook playbooks/backup_docker.yml --tags &lt;role&gt; --ask-vault-pass` with the correct `&lt;role&gt;` substituted (`--tags garage`, `--tags prometheus`, `--tags grafana`, `--tags alertmanager`).
    - `## Backup` H2 appears AFTER `## Volumes` and BEFORE `## Uninstall` in each of the 4 files — verified by line-number ordering (`grep -n '^## '`).
    - `roles/garage/README.md ## Backup` contains all 3 captured entry markers: `telemetron_garage_meta`, `telemetron_garage_data`, and `s3-credentials`.
    - `roles/prometheus/README.md ## Backup` mentions `/prometheus/lock` (PP-1 restore-time deletion note) and `telemetron_prometheus_data`.
    - `roles/grafana/README.md ## Backup` mentions `telemetron_grafana_data` AND contains the word `provisioning` (Not-captured surprise per D-195).
    - `roles/grafana/README.md ## Backup` is surrounded by `---` separators (preserving the file's H2-separator convention from Phase 12 plan 12-02).
    - `roles/alertmanager/README.md ## Backup` contains `telemetron_alertmanager_data`.
    - Code-fence balance: even number of ``` per file (one new bash fence pair added per file).
    - Zero new non-ASCII characters introduced in any of the 4 files.
    - Zero `D-XXX` references in `## Backup` section prose (Pattern S3 — operator-facing).
    - Per-file ## Backup section body length within 8-25 lines (CONTEXT.md `<claudes_discretion>` budget).
  </acceptance_criteria>
  <done>
    All 4 stateful role READMEs contain a new `## Backup` H2 section with the uniform 5-part skeleton, the per-role Captured/Not-captured bullets honestly describing each role's tarball contents, the tag-scoped invocation bash fence, and the verbatim cross-ref to `docs/quickstart.md#backup-and-restore`. Grafana includes `---` separators per existing file convention. Prometheus mentions the `/prometheus/lock` deletion behavior.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add ## Backup H2 sections to the 3 Garage-backed stateless role READMEs (loki, tempo, mimir) using Variant A one-liner</name>
  <files>roles/loki/README.md, roles/tempo/README.md, roles/mimir/README.md</files>
  <read_first>
    <file>roles/loki/README.md</file>
    <reason>See current ## Volumes (line 88) and ## Uninstall (line 95) — confirm insertion slot between line 94 and 95. Read the ## Uninstall section to absorb prose voice.</reason>
    <file>roles/tempo/README.md</file>
    <reason>See current ## Volumes (line 149) and ## Uninstall (line 156) — confirm insertion slot between line 155 and 156.</reason>
    <file>roles/mimir/README.md</file>
    <reason>See current ## Volumes (line 122) and ## Uninstall (line 129) — confirm insertion slot between line 128 and 129.</reason>
    <file>.planning/phases/15-documentation-cascade/15-PATTERNS.md</file>
    <reason>Plan 15-02 section, Stateless Variant A template (lines 284-291): "Data lives in Garage S3 buckets — captured by the garage role's backup. See `roles/garage/README.md#backup`." Per D-199 / D-200, planner may tighten or extend by ≤5 words per role but the substring `garage role` and the cross-ref to `roles/garage/README.md#backup` must remain.</reason>
    <file>.planning/phases/15-documentation-cascade/15-CONTEXT.md</file>
    <reason>D-199 specifies the two-template distinction. D-200 specifies the uniform `## Backup` placement (same slot as stateful). D-198 specifies the H2 (not inlined into ## Uninstall).</reason>
  </read_first>
  <action>
For each of the 3 Garage-backed stateless role READMEs, insert a new `## Backup` H2 section between `## Volumes` and `## Uninstall` (the same Volumes → Backup → Uninstall slot as the 4 stateful roles, per D-200) containing the Variant A one-liner per D-199:

  ```markdown
  ## Backup

  Data lives in Garage S3 buckets — captured by the garage role's backup. See `roles/garage/README.md#backup`.
  ```

NOTE: Use ASCII characters only. The em-dash above is shown for clarity in this plan — substitute ASCII `--` (double-hyphen) in the actual file to avoid introducing new non-ASCII characters (Pattern S5).

Actual text to insert (per file, with ASCII):

  ## Backup

  Data lives in Garage S3 buckets -- captured by the garage role's backup. See `roles/garage/README.md#backup`.

Per D-199 + Claude's Discretion: planner may extend by ≤5 words per role to substitute the role name explicitly (e.g., "Loki data lives in..." instead of generic "Data lives in...") for the loki/tempo/mimir variant. The substring `garage role` AND the cross-ref `roles/garage/README.md#backup` must remain in all 3 files.

Insertion points (per 15-PATTERNS.md slot map; line numbers are pre-edit):
- `roles/loki/README.md`: between line 94 (end of ## Volumes section) and line 95 (## Uninstall).
- `roles/tempo/README.md`: between line 155 and line 156.
- `roles/mimir/README.md`: between line 128 and line 129.

Section body length: 3-5 lines (H2 header + blank line + single sentence + optional blank line).

Across all 3 files:
- Each `## Backup` section is ≤5 body lines (excluding the H2 itself).
- Each contains the literal substring `garage role` OR `roles/garage/README.md#backup` (per 15-PATTERNS.md verification gate).
- Each preserves the Volumes → Backup → Uninstall reading flow.
- Zero new non-ASCII characters introduced (use ASCII `--` not em-dash; ASCII `"` not curly quotes).
- Zero `D-XXX` references in operator-facing prose.
- Code-fence balance: each file's fence count is unchanged (the one-liner adds no fences).
  </action>
  <verify>
    <automated>for f in roles/loki/README.md roles/tempo/README.md roles/mimir/README.md; do [ "$(grep -c '^## Backup$' "$f")" -eq 1 ] || { echo "FAIL: $f missing ## Backup"; exit 1; }; grep -q 'roles/garage/README.md#backup' "$f" || { echo "FAIL: $f missing garage cross-ref"; exit 1; }; awk '/^```/ { c++ } END { exit (c%2==0)?0:1 }' "$f" || { echo "FAIL: $f fence imbalance"; exit 1; }; done &amp;&amp; grep -q 'garage role' roles/loki/README.md &amp;&amp; grep -q 'garage role' roles/tempo/README.md &amp;&amp; grep -q 'garage role' roles/mimir/README.md</automated>
  </verify>
  <acceptance_criteria>
    - Each of `roles/{loki,tempo,mimir}/README.md` contains exactly one `^## Backup$` line.
    - Each contains the literal cross-ref `roles/garage/README.md#backup`.
    - Each contains the literal substring `garage role` (data-in-Garage handoff lede).
    - `## Backup` H2 appears AFTER `## Volumes` and BEFORE `## Uninstall` in each file (grep -n line-ordering check).
    - Per-file `## Backup` section body is ≤ 5 lines (excluding the H2 header line itself).
    - Zero new non-ASCII characters introduced (no em-dash, no curly quotes, no smart punctuation).
    - Zero `D-XXX` references in the new section prose.
    - Code-fence balance: even number of ``` per file (one-liner adds no fences).
  </acceptance_criteria>
  <done>
    All 3 Garage-backed stateless role READMEs contain a new `## Backup` H2 section in the Volumes → Backup → Uninstall slot, with a single sentence pointing the operator to `roles/garage/README.md#backup`. ASCII-only; verification gates pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add ## Backup H2 sections to the 5 truly-stateless role READMEs (fluentbit, karma, node_exporter, opentelemetry, nfsd) using Variant B one-liner</name>
  <files>roles/fluentbit/README.md, roles/karma/README.md, roles/node_exporter/README.md, roles/opentelemetry/README.md, roles/nfsd/README.md</files>
  <read_first>
    <file>roles/fluentbit/README.md</file>
    <reason>See current ## Volumes (line 262) and ## Uninstall (line 271) — confirm insertion slot between line 270 and 271.</reason>
    <file>roles/karma/README.md</file>
    <reason>See current ## Volumes (line 85) and ## Uninstall (line 89) — confirm insertion slot between line 88 and 89. NOTE: karma already contains pre-existing § non-ASCII characters in unrelated sections (Phase 12 12-02-SUMMARY deviations note) — DO NOT modify those; only the new ## Backup section must be ASCII-clean.</reason>
    <file>roles/node_exporter/README.md</file>
    <reason>See current ## Volumes (line 76) and ## Uninstall (line 88) — confirm insertion slot between line 87 and 88.</reason>
    <file>roles/opentelemetry/README.md</file>
    <reason>See current ## Volumes (line 153) and ## Uninstall (line 164) — confirm insertion slot between line 163 and 164.</reason>
    <file>roles/nfsd/README.md</file>
    <reason>DIVERGENT placement: nfsd has no `## Volumes` and its `## Uninstall` is placed AFTER `## Verification` (line 172) per Phase 12 D-172. The new `## Backup` H2 inserts immediately BEFORE the `## Uninstall` block at line 192 (between line 191 and 192). Read lines 170-195 of the current file to understand the post-Verification structure before inserting.</reason>
    <file>.planning/phases/15-documentation-cascade/15-PATTERNS.md</file>
    <reason>Plan 15-02 section, Stateless Variant B template (lines 293-299): "No operator state to preserve." (D-201 says nfsd uses this exact template — operator's `/srv/telemetron-nfs/` data is THEIR responsibility, already disclaimed by Phase 12's ## Uninstall divergent block below).</reason>
    <file>.planning/phases/15-documentation-cascade/15-CONTEXT.md</file>
    <reason>D-199 (two-template distinction); D-201 (nfsd uses Variant B; no extra disclaimer — Phase 12 D-138 already covered the share-root disclaimer); D-200 (uniform slot for stateless roles with ## Volumes; divergent slot for nfsd).</reason>
    <file>.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-02-SUMMARY.md</file>
    <reason>Phase 12 precedent for nfsd's divergent placement (D-172 — post-Verification). Phase 15 mirrors this divergent positioning by placing ## Backup immediately before nfsd's ## Uninstall block (which is also divergent-positioned).</reason>
  </read_first>
  <action>
For each of the 5 truly-stateless role READMEs, insert a new `## Backup` H2 section containing the Variant B one-liner per D-199:

  ## Backup

  No operator state to preserve.

Per-file insertion points (line numbers are pre-edit):
- `roles/fluentbit/README.md`: between line 270 (end of ## Volumes section) and line 271 (## Uninstall). Slot: Volumes → Backup → Uninstall.
- `roles/karma/README.md`: between line 88 and line 89. Slot: Volumes → Backup → Uninstall.
- `roles/node_exporter/README.md`: between line 87 and line 88. Slot: Volumes → Backup → Uninstall.
- `roles/opentelemetry/README.md`: between line 163 and line 164. Slot: Volumes → Backup → Uninstall.
- `roles/nfsd/README.md` (DIVERGENT — D-201): between line 191 and line 192 (immediately before the divergent ## Uninstall block, which sits post-Verification per Phase 12 D-172). Slot: Verification → ...other content... → Backup → Uninstall.

Section body length: 3-5 lines (H2 header + blank line + single sentence + optional blank line).

Per D-199 + Claude's Discretion: planner may extend by ≤5 words per role but the lede phrase `No operator state to preserve` must remain. Suggested minimal forms:
- fluentbit: "No operator state to preserve."
- karma: "No operator state to preserve."
- node_exporter: "No operator state to preserve."
- opentelemetry: "No operator state to preserve."
- nfsd: "No operator state to preserve." (D-201 — NO extra disclaimer about `/srv/telemetron-nfs/`; Phase 12's ## Uninstall divergent block already disclaims responsibility per D-138).

Across all 5 files:
- Each `## Backup` section is ≤5 body lines (excluding the H2 itself).
- Each contains the literal substring `No operator state to preserve`.
- Zero new non-ASCII characters introduced. NOTE: karma already has pre-existing § characters in unrelated sections (out-of-scope per Phase 12 12-02-SUMMARY deviation); do not touch them and do not introduce new ones in the ## Backup section.
- Zero `D-XXX` references in operator-facing prose.
- Code-fence balance: each file's fence count is unchanged.
- nfsd's `## Backup` appears AFTER `## Verification` (line ordering check) and BEFORE `## Uninstall` (preserves the divergent reading flow).
  </action>
  <verify>
    <automated>for f in roles/fluentbit/README.md roles/karma/README.md roles/node_exporter/README.md roles/opentelemetry/README.md roles/nfsd/README.md; do [ "$(grep -c '^## Backup$' "$f")" -eq 1 ] || { echo "FAIL: $f missing ## Backup"; exit 1; }; grep -q 'No operator state to preserve' "$f" || { echo "FAIL: $f missing stateless lede"; exit 1; }; awk '/^```/ { c++ } END { exit (c%2==0)?0:1 }' "$f" || { echo "FAIL: $f fence imbalance"; exit 1; }; done &amp;&amp; awk '/^## Verification$/{v=NR} /^## Backup$/{b=NR} /^## Uninstall$/{u=NR} END{exit (v &amp;&amp; b &amp;&amp; u &amp;&amp; v&lt;b &amp;&amp; b&lt;u)?0:1}' roles/nfsd/README.md</automated>
  </verify>
  <acceptance_criteria>
    - Each of `roles/{fluentbit,karma,node_exporter,opentelemetry,nfsd}/README.md` contains exactly one `^## Backup$` line.
    - Each contains the literal substring `No operator state to preserve` (D-199 Variant B lede).
    - For 4 of 5 files (fluentbit, karma, node_exporter, opentelemetry): `## Backup` appears AFTER `## Volumes` and BEFORE `## Uninstall` in `grep -n '^## '` ordering.
    - For nfsd: `## Backup` appears AFTER `## Verification` and BEFORE `## Uninstall` (preserving the divergent post-Verification flow per D-172 + D-201).
    - nfsd `## Backup` section contains ONLY the Variant B one-liner — no extra disclaimer about `/srv/telemetron-nfs/` (per D-201; the divergent ## Uninstall below already disclaims it via D-138).
    - Per-file `## Backup` section body is ≤ 5 lines.
    - Zero new non-ASCII characters introduced in any of the 5 files. Pre-existing § in karma is unchanged (out-of-scope per Phase 12 deviation).
    - Zero `D-XXX` references in the new section prose.
    - Code-fence balance: even number of ``` per file (one-liner adds no fences).
  </acceptance_criteria>
  <done>
    All 5 truly-stateless role READMEs contain a new `## Backup` H2 section with the single sentence "No operator state to preserve." Placement: standard Volumes→Backup→Uninstall slot for 4 roles; divergent post-Verification slot for nfsd. ASCII-only; verification gates pass.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs → operator | Per-role READMEs are the operator's role-scoped backup reference; misstated "Captured" / "Not captured" lists cause confusion about what is recoverable from a tarball. |
| README → README | Cross-refs between role READMEs and `docs/quickstart.md` rely on stable anchors; broken anchors silently degrade discoverability. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-15-06 | Tampering | roles/garage/README.md ## Backup Captured list | mitigate | The 3-entry Captured list must match `roles/garage/tasks/backup.yml` (Phase 13 plan 13-02) exactly. Acceptance criterion: literal substrings `telemetron_garage_meta`, `telemetron_garage_data`, `s3-credentials` all present. Executor reads `roles/garage/tasks/backup.yml` before writing. |
| T-15-07 | Tampering | roles/grafana/README.md ## Backup Not-captured list | mitigate | If the Not-captured list omits the "provisioning re-renders from version-controlled config" surprise (D-195's canonical surprise for grafana), operators may believe their custom dashboards are NOT preserved (false) or their provisioning IS preserved (false). Acceptance criterion: substring `provisioning` is present in `roles/grafana/README.md ## Backup`. |
| T-15-08 | Tampering | roles/prometheus/README.md ## Backup /prometheus/lock note | mitigate | The PP-1 lockfile-deletion behavior is restore-only; mentioning it in the Backup section (per CONTEXT.md `<specifics>` for prometheus) prevents operators from believing they need to do this manually. Acceptance criterion: substring `/prometheus/lock` is present. |
| T-15-09 | Denial of Service | Cross-ref to docs/quickstart.md#backup-and-restore | mitigate (parallel-safe) | All 4 stateful `## Backup` sections forward-link to `docs/quickstart.md#backup-and-restore` — an anchor created by plan 15-01 in the same wave. Per D-210 + Phase 12 D-174 precedent: forward-referenced markdown anchors are stable regardless of plan merge order. Acceptance criterion asserts the exact link target. |
| T-15-10 | Information Disclosure | D-IDs in per-role README operator-facing prose | accept (low) | Pattern S3 mandates zero `D-XXX` references in operator-facing prose. Severity LOW. Acceptance criterion: per-section prose contains no `D-(19[4-9]|2[0-1][0-9])` substring. |
| T-15-11 | Repudiation | Stateless one-liner accuracy | accept (low) | Variant A loki/tempo/mimir handoff to garage role: if Garage's backup ever ceases to actually back up Loki/Tempo/Mimir data, this sentence becomes a lie. Mitigation: contract is enforced by Gate 11 (plan 15-03) + Phase 13 plan 13-02; tested end-to-end on leviathan per Phase 14 UAT-V13-01. Severity LOW. |

All threats are LOW severity (doc-only phase). Gate passes — no `high` severity threats per `block_on: high` config.
</threat_model>

<verification>
- All 12 deployed-role READMEs contain exactly one `^## Backup$` line.
- All 4 stateful sections contain `**Captured` and `**Not captured` bold labels, the tag-scoped bash fence, and the verbatim cross-ref to `docs/quickstart.md#backup-and-restore`.
- All 3 Garage-backed stateless sections contain `garage role` and `roles/garage/README.md#backup`.
- All 5 truly-stateless sections contain `No operator state to preserve`.
- nfsd's `## Backup` is in the divergent post-Verification slot (Verification → Backup → Uninstall ordering verified).
- All 4 stateful sections fall within 8-25 body lines; all 8 stateless sections fall within ≤5 body lines.
- Code-fence balance: even number of ``` per file (4 stateful files add 1 bash fence pair each; 8 stateless files add 0 fences).
- Zero NEW non-ASCII characters introduced across all 12 files.
- Zero `D-XXX` references in operator-facing prose across all 12 files.
- Source-of-truth invariants: garage Captured list matches `roles/garage/tasks/backup.yml`; prometheus Not-captured note matches `roles/prometheus/tasks/restore.yml` PP-1 step; grafana Not-captured = provisioning per D-195; alertmanager Captured includes empty-data-stat-guard mention.
</verification>

<success_criteria>
- 12 files modified (one `## Backup` H2 per file): roles/{garage,prometheus,grafana,alertmanager,loki,tempo,mimir,fluentbit,karma,node_exporter,opentelemetry,nfsd}/README.md.
- All acceptance criteria for Tasks 1, 2, 3 pass.
- Threat model gate passes (no `high` severity threats).
- Closes DOCS-V13-03 in full (every stateful role README has full skeleton; every stateless role README has the appropriate one-liner).
</success_criteria>

<output>
Create `.planning/phases/15-documentation-cascade/15-02-SUMMARY.md` when done, mirroring the structure of `.planning/milestones/v1.2.0-phases/12-documentation-cascade/12-02-SUMMARY.md` (frontmatter listing 12 modified files + per-role summary table + DOCS-V13-03 contract coverage + deviations + self-check).
</output>
