---
phase: 260519-sod
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  # DELETE (5 files in role + 1 inventory file)
  - roles/promlens/defaults/main.yml
  - roles/promlens/handlers/main.yml
  - roles/promlens/meta/main.yml
  - roles/promlens/tasks/main.yml
  - roles/promlens/tasks/verify.yml
  - roles/promlens/README.md
  - inventory/example-homelab/group_vars/all/promlens.yml
  # EDIT (live tree)
  - playbooks/deploy_docker.yml
  - inventory/example-homelab/group_vars/all/network.yml
  - README.md
  - docs/architecture.md
  - docs/inventory.md
  - roles/README.md
  - roles/grafana/README.md
  # EDIT (planning bookkeeping; force-add per .gitignore)
  - CLAUDE.md
  - .planning/PROJECT.md
  - .planning/STATE.md
  - .planning/RETROSPECTIVE.md
autonomous: false
requirements: [v1.0.1-patch]
must_haves:
  truths:
    - "PromLens container no longer deploys when running `ansible-playbook playbooks/deploy_docker.yml`"
    - "`ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0 with no reference to the removed role"
    - "Live-tree grep for `promlens|PromLens|PROMLENS` (excluding `.planning/`) returns zero matches"
    - "v1.0.1 git tag exists locally with annotated message explaining the removal rationale"
    - "Operator reading docs/architecture.md, README.md, and docs/inventory.md sees no PromLens references and finds a one-line pointer to Prometheus 3's native UI"
    - "Planning history (CLAUDE.md, PROJECT.md, STATE.md, RETROSPECTIVE.md) records that PromLens shipped in v1.0.0 and was removed in v1.0.1"
  artifacts:
    - path: "roles/promlens/"
      provides: "DELETED — entire role directory removed via `git rm -r`"
    - path: "inventory/example-homelab/group_vars/all/promlens.yml"
      provides: "DELETED — operator tunables removed"
    - path: "playbooks/deploy_docker.yml"
      provides: "Updated — role entry + trailing pipeline comment drop `promlens`"
    - path: "docs/architecture.md"
      provides: "Updated — component table (now 12 rows), port table (16 rows), ASCII signal-flow UI plane box, and Known Debt PromLens bullet removed; one-line Prometheus 3 UI note added"
    - path: "README.md"
      provides: "Updated — top-level component table drops PromLens row; Not in M1 subsection adds PromLens removal entry"
    - path: ".planning/RETROSPECTIVE.md"
      provides: "Updated — appends `## Post-Ship Correction: v1.0.1 — PromLens removed` subsection capturing rationale + lesson"
  key_links:
    - from: "playbooks/deploy_docker.yml"
      to: "roles/promlens/"
      via: "role entry"
      pattern: "role: promlens"
      expected: "absent (zero matches in playbooks/)"
    - from: "ansible-playbook --syntax-check"
      to: "playbooks/deploy_docker.yml"
      via: "syntax validation"
      expected: "exit 0, no missing-role error"
---

<objective>
Remove PromLens from the Telemetron stack as the v1.0.1 patch ship. PromLens
(`prom/promlens:v0.3.0`, last tagged Dec 2022) was bundled in M1 v1.0.0 for
upstream-INSPQ parity. Post-ship investigation today confirmed the upstream
repo has had Dependabot-only commits for 3.5 years and no functional release.
Prometheus 3.x's native Mantine-based UI at `http://prometheus:9090/graph`
absorbs the tree-view + query-explorer use case that was PromLens's only
remaining value. Remove cleanly and tag v1.0.1.

Purpose: Stop shipping unmaintained code on a "clone-and-run" homelab project.
Capability is preserved (Prometheus 3 native UI). Zero operator regression.

Output: 14-file change set across three atomic commits + v1.0.1 annotated git
tag. ASK USER before pushing tag/main to origin.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@.planning/STATE.md
@.planning/PROJECT.md
@.planning/RETROSPECTIVE.md
@playbooks/deploy_docker.yml
@README.md
@docs/architecture.md
@docs/inventory.md
@roles/README.md
@roles/grafana/README.md
@roles/promlens/README.md
@inventory/example-homelab/group_vars/all/promlens.yml
@inventory/example-homelab/group_vars/all/network.yml

<interfaces>
<!-- Authoritative facts the executor needs without re-reading. -->

**Current playbook role entry (playbooks/deploy_docker.yml lines 69-71):**
```
    - role: promlens
      tags:
        - promlens
```
Delete this 3-line block. The `nfsd` block (lines 72-75) and its
`when: enable_nfsd | default(false) | bool` guard MUST remain untouched.

**Current playbook trailing comment (playbooks/deploy_docker.yml lines 76-79):**
```
  # M1 deploy order is FEATURE-COMPLETE:
  # minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry
  # -> prometheus -> fluentbit -> alertmanager -> grafana -> karma
  # -> promlens -> nfsd (opt-in via enable_nfsd).
```
Rewrite so the chain reads:
```
  # M1 deploy order (v1.0.1 — PromLens removed):
  # minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry
  # -> prometheus -> fluentbit -> alertmanager -> grafana -> karma
  # -> nfsd (opt-in via enable_nfsd).
```

**Current role count phrasing in playbook header comment (lines 1-7):**
```
# Orchestrates 13 deployed roles plus `nfsd` as a 14th opt-in slot
```
Rewrite to:
```
# Orchestrates 12 deployed roles plus `nfsd` as a 13th opt-in slot
```

**network.yml PromLens block (inventory/example-homelab/group_vars/all/network.yml lines 22-33):**
The UI-plane comment block currently lists Grafana / Karma / PromLens and includes a
multi-line PromLens DEPRECATION CANDIDATE note. Drop the PromLens line AND the
deprecation-candidate paragraph. Result should list only Grafana + Karma in the
"UI plane port allocation" comment.

**Current README.md component table (lines 32-46):** 13 rows. Drop the PromLens row
(line 45). Add a bullet to the "Not in M1" section (lines 50-55) explaining the
removal: PromLens was bundled in v1.0.0 for upstream parity; removed in v1.0.1
after confirming the upstream repo has been Dependabot-only since Dec 2022;
Prometheus 3's native UI covers the tree-view + query-explorer use case at
`http://prometheus:9090/graph`.

**Current docs/architecture.md edits (3 spots):**
- Components table (lines 91-105): drop the PromLens row (line 104). Count drops
  13 -> 12. The `nfsd` row (line 105) remains.
- Port Allocation table (lines 109-127): drop the PromLens row (line 120). Count
  drops 17 -> 16.
- Signal Flow ASCII diagram UI PLANE block (lines 74-82): the four-box row currently
  shows Grafana | Karma | PromLens | MinIO. Re-render as a three-box row:
  Grafana | Karma | MinIO console (preserve port labels, alignment, and the
  outer +----+ border).
- Known Debt section (lines 173-188): drop the "PromLens is frozen" bullet (lines
  180-183). Replace it with: "PromLens was removed in v1.0.1. The bundled
  Prometheus 3.x UI at `http://prometheus:9090/graph` covers the tree-view and
  query-explorer use case that PromLens served in v1.0.0."

**Current docs/inventory.md edit (directory-shape block, lines 13-38):**
Drop the `promlens.yml` line from the `group_vars/all/` listing (line 35).

**Current roles/README.md edits:**
- Planned roles table (lines 7-22): drop the `promlens` row (line 21). The
  "Ported" column header and other rows stay identical.
- Gate 7 callout (line 70): currently lists "Phase 5 (grafana, karma, promlens)"
  -- rewrite to "Phase 5 (grafana, karma)". The PromLens removal is a v1.0.1
  patch; the historical Phase-5 role-shape lineage drops promlens from this
  in-flight gate description.

**Current roles/grafana/README.md edit (line 5):**
```
Requirements: UI-01 (persistent volume), UI-02 (datasource UIDs), UI-03 (curated dashboards), UI-04 (trace-to-logs correlation). Cross-linked to Phase 5 `karma` (plan 05-02) and `promlens` (plan 05-03 -- deprecation candidate) roles.
```
Rewrite as:
```
Requirements: UI-01 (persistent volume), UI-02 (datasource UIDs), UI-03 (curated dashboards), UI-04 (trace-to-logs correlation). Cross-linked to Phase 5 `karma` (plan 05-02) role.
```

**CLAUDE.md edits:**
- "Per-Role Recommendation Sheet" table (early in tech-stack section): drop the
  `promlens` row.
- "UI / Edge" table: drop the PromLens row.
- "PromLens reality check" / "DEPRECATE-IN-PLACE" callout: append a final line
  saying "**Update v1.0.1 (2026-05-19):** PromLens was removed from the stack
  after confirming Dependabot-only upstream commits since Dec 2022. The
  Prometheus 3 native UI absorbs the tree-view feature."

**.planning/PROJECT.md edits:**
- In Validated phases section, the Phase 5 (ui-plane) bullet currently
  references PromLens. Append `(removed in v1.0.1 — see RETROSPECTIVE.md)`
  inline.
- In Out of Scope section, ADD a new entry verbatim:
  `**PromLens (removed v1.0.1)** — shipped in v1.0.0 for upstream parity; removed post-ship after confirming upstream is functionally frozen since Dec 2022 (Dependabot-only commits). Prometheus 3's native UI covers the tree-view use case. Not coming back.`

**.planning/STATE.md edits (frontmatter + body):**
- Frontmatter `stopped_at`: append `; v1.0.1 patch shipped 2026-05-19 (PromLens removed).`
- Frontmatter `last_updated`: bump to a fresh ISO-8601 UTC timestamp at write time.
- Body `last_activity` line (around line 8 + line 33): update to
  `2026-05-19 — v1.0.1 patch shipped: PromLens removed from stack`.
- `### Known Debt (carried into v2)` section: DELETE the PromLens bullet
  (currently line 208: `**PromLens v0.3.0** marked deprecation-candidate; Prometheus 3 absorbs the tree-view surface.`). It's no longer debt; it's gone.

**.planning/RETROSPECTIVE.md edits:**
- Append a new subsection under the v1.0.0 entry (find the v1.0.0 heading; the
  new subsection lives directly after the last v1.0.0 content). Use this
  template:

```
## Post-Ship Correction: v1.0.1 — PromLens removed

**Date:** 2026-05-19 (same day as v1.0.0 ship).

**What happened:** During M1 ship-day review of bundled components, a quick
upstream check confirmed `prom/promlens` has had only Dependabot dependency-update
commits since the v0.3.0 tag in December 2022. No functional release in 3.5
years; no maintainer activity beyond bot bumps.

**The call:** Remove PromLens from the stack as a v1.0.1 patch ship.
Prometheus 3.x's native Mantine-based UI at `http://prometheus:9090/graph`
absorbs the PromQL tree-view + query-explorer feature that was PromLens's only
remaining value. Zero capability loss for operators.

**Scope:** 14 files touched (5 role files deleted, 1 inventory file deleted,
8 docs/config edits). v1.0.1 annotated git tag with the removal rationale.

**Lesson for v2:** Before deciding to ship any component "for upstream parity,"
confirm upstream maintenance status. The cost of shipping an unmaintained
component in a clone-and-run project is non-trivial (operator confusion, CVE
exposure, future removal work). The check is cheap -- `git log -1 <upstream>`
and a glance at release tags -- and would have prevented PromLens from
appearing in v1.0.0 at all.
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete PromLens role + inventory + playbook wiring</name>
  <files>
    roles/promlens/ (entire directory deleted via `git rm -r`)
    inventory/example-homelab/group_vars/all/promlens.yml
    playbooks/deploy_docker.yml
    inventory/example-homelab/group_vars/all/network.yml
  </files>
  <action>
    Delete the entire `roles/promlens/` tree (5 files: defaults/main.yml,
    handlers/main.yml, meta/main.yml, tasks/main.yml, tasks/verify.yml, plus
    README.md) using `git rm -r roles/promlens`. Delete
    `inventory/example-homelab/group_vars/all/promlens.yml` using `git rm`.

    Edit `playbooks/deploy_docker.yml`:
    - Remove the 3-line `- role: promlens` block (lines 69-71 per
      `<interfaces>` snapshot). Verify the `nfsd` block immediately below
      stays intact INCLUDING its `when: enable_nfsd | default(false) | bool`
      guard.
    - Rewrite the playbook header comment "Orchestrates 13 deployed roles
      plus `nfsd` as a 14th opt-in slot" to read "Orchestrates 12 deployed
      roles plus `nfsd` as a 13th opt-in slot".
    - Rewrite the trailing pipeline comment to drop the `-> promlens` segment
      and bump the header line to "M1 deploy order (v1.0.1 — PromLens
      removed):" per the `<interfaces>` snapshot.

    Edit `inventory/example-homelab/group_vars/all/network.yml`:
    - In the "UI plane port allocation (Phase 5; D-82 / D-84)" comment block
      (lines 22-33), delete the PromLens line (`# PromLens   :8081  ...`) AND
      the multi-line DEPRECATION CANDIDATE paragraph that follows it. Keep
      only Grafana + Karma entries plus the closing reverse-proxy paragraph.

    Stage all four touched paths and create commit 1:
    `chore(promlens): remove role + inventory + playbook wiring`

    Body should briefly explain: upstream repo has been Dependabot-only since
    Dec 2022; Prometheus 3 native UI absorbs the use case; v1.0.1 patch ship.
  </action>
  <verify>
    <automated>
      cd /home/darko/git/rockdarko/telemetron \
      && test ! -e roles/promlens \
      && test ! -e inventory/example-homelab/group_vars/all/promlens.yml \
      && ansible-playbook --syntax-check playbooks/deploy_docker.yml \
      && grep -v '^#' playbooks/deploy_docker.yml | grep -c "promlens" | grep -qx 0 \
      && grep -v '^#' inventory/example-homelab/group_vars/all/network.yml | grep -ic "promlens" | grep -qx 0
    </automated>
  </verify>
  <done>
    `roles/promlens/` and `inventory/.../promlens.yml` no longer exist on
    disk. `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits
    0 with no missing-role error. Zero `promlens` references survive in
    playbook task body (comments still mention the removal historically -- the
    grep gate filters comments). One atomic commit landed:
    `chore(promlens): remove role + inventory + playbook wiring`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Drop PromLens from architecture + inventory + README + role READMEs</name>
  <files>
    docs/architecture.md
    docs/inventory.md
    README.md
    roles/README.md
    roles/grafana/README.md
  </files>
  <action>
    Per the surgical edit list in `<interfaces>`:

    1. **docs/architecture.md** — three edits:
       a. Components table (lines 91-105): delete the `| PromLens | ... |` row
          at line 104. The 13-row table becomes a 12-row table; nfsd row stays.
       b. Port Allocation table (lines 109-127): delete the `| PromLens | 8080 | 8081 |`
          row at line 120. The 17-row table becomes a 16-row table.
       c. Signal Flow ASCII diagram UI PLANE block (lines 74-82): replace the
          4-box row (Grafana | Karma | PromLens | MinIO) with a 3-box row
          (Grafana | Karma | MinIO console). Preserve the `+----+` border style,
          the port labels (`:3000`, `:8082`, `:9001`), and the surrounding
          UI PLANE outer box. Visually inspect alignment after edit.
       d. Known Debt section (lines 173-188): delete the "PromLens is frozen"
          bullet (lines 180-183) and REPLACE with a single one-line note:
          `- **PromLens was removed in v1.0.1.** The bundled Prometheus 3.x UI at`
          `  http://prometheus:9090/graph covers the tree-view and query-explorer`
          `  use case that PromLens served in v1.0.0.`

    2. **docs/inventory.md** — single edit:
       In the directory-shape block (lines 13-38), drop the
       `        promlens.yml` line at line 35. Keep all other group_vars/all
       entries identical.

    3. **README.md** — two edits:
       a. Component table (lines 32-46): delete the
          `| PromLens | prom/promlens:v0.3.0 | PromQL editor (deprecation candidate) |`
          row at line 45. The 13-row table becomes a 12-row table; nfsd row at
          line 46 remains the trailing row.
       b. "Not in M1" subsection (lines 50-55): ADD a new bullet (placement:
          first item in the list, before Hook router, since PromLens is the
          most recent removal):
          `- **PromLens** was bundled in v1.0.0 for upstream-INSPQ parity and`
          `  removed in v1.0.1 after confirming the upstream repo has been`
          `  Dependabot-only since December 2022. Prometheus 3.x's native UI at`
          `  http://prometheus:9090/graph covers the PromQL tree-view +`
          `  query-explorer use case.`

    4. **roles/README.md** — two edits:
       a. Planned roles table (lines 7-22): delete the
          `| `promlens`                | PromQL editor (deprecation candidate)             | ☑ |`
          row at line 21. Table goes from 14 rows to 13.
       b. Gate 7 callout (line 70): replace
          `Phase 5 (grafana, karma, promlens) role ports MUST stamp these labels.`
          with
          `Phase 5 (grafana, karma) role ports MUST stamp these labels.`

    5. **roles/grafana/README.md** — single edit at line 5:
       Replace
       `Cross-linked to Phase 5 `karma` (plan 05-02) and `promlens` (plan 05-03 -- deprecation candidate) roles.`
       with
       `Cross-linked to Phase 5 `karma` (plan 05-02) role.`

    Stage all five touched files and create commit 2:
    `docs: drop PromLens from architecture + inventory + README + role READMEs`

    Body should note: live-tree documentation now consistently reflects v1.0.1
    state; Prometheus 3 native UI is called out as the replacement.
  </action>
  <verify>
    <automated>
      cd /home/darko/git/rockdarko/telemetron \
      && grep -c -i "promlens" docs/architecture.md docs/inventory.md README.md roles/README.md roles/grafana/README.md 2>/dev/null | awk -F: '$2 != "1" && $2 != "0" { print "FAIL: " $0; bad=1 } END { exit bad }' \
      && grep -i "removed in v1.0.1\|removed in v1\\.0\\.1" docs/architecture.md README.md \
      && ansible-playbook --syntax-check playbooks/deploy_docker.yml
    </automated>
    <human-check>
      Eyeball the docs/architecture.md "UI PLANE" ASCII diagram — confirm the
      3-box row (Grafana | Karma | MinIO) is well-aligned with the outer
      `+----+` border. ASCII art is the one thing automated grep can't
      validate aesthetically.
    </human-check>
  </verify>
  <done>
    All five docs/role-README files no longer carry deployment-claim PromLens
    references; the only surviving mentions are the "removed in v1.0.1"
    historical notes in docs/architecture.md and README.md. ASCII signal-flow
    diagram redrawn cleanly (human-checked). Syntax-check still passes. One
    atomic commit landed:
    `docs: drop PromLens from architecture + inventory + README + role READMEs`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Record PromLens removal in planning history + tag v1.0.1</name>
  <files>
    CLAUDE.md
    .planning/PROJECT.md
    .planning/STATE.md
    .planning/RETROSPECTIVE.md
  </files>
  <action>
    Per the edit specs in `<interfaces>`:

    1. **CLAUDE.md** — three edits:
       a. "Per-Role Recommendation Sheet" table near top: delete the
          `| `promlens` | `prom/promlens` | `v0.3.0` | LOW | **DEPRECATE-IN-PLACE** -- see § PromLens reality check |`
          row. Table row count drops by 1.
       b. "UI / Edge" table: delete the PromLens row similarly.
       c. "PromLens reality check" / "DEPRECATE-IN-PLACE" prose section
          (`### 3. PromLens is functionally frozen`): append a final bold
          line:
          `**Update v1.0.1 (2026-05-19):** PromLens was removed from the stack`
          `after confirming Dependabot-only upstream commits since Dec 2022.`
          `Prometheus 3's native UI absorbs the tree-view feature.`

    2. **.planning/PROJECT.md** — two edits:
       a. Validated phases / Phase 5 (ui-plane) bullet: append inline
          ` (removed in v1.0.1 — see RETROSPECTIVE.md)` to the PromLens
          mention. Read the file first to find the exact bullet wording before
          editing.
       b. Out of Scope section: ADD a new bullet at the end of the list
          verbatim:
          `**PromLens (removed v1.0.1)** — shipped in v1.0.0 for upstream`
          `parity; removed post-ship after confirming upstream is functionally`
          `frozen since Dec 2022 (Dependabot-only commits). Prometheus 3's`
          `native UI covers the tree-view use case. Not coming back.`

    3. **.planning/STATE.md** — three edits:
       a. Frontmatter `stopped_at`: append
          `; v1.0.1 patch shipped 2026-05-19 (PromLens removed).`
       b. Frontmatter `last_updated`: bump to a fresh ISO-8601 UTC timestamp
          at the time of the write (use `date -u +%Y-%m-%dT%H:%M:%S.000Z`).
       c. Body `last_activity` lines (frontmatter line 8 AND body line 33):
          update both to
          `2026-05-19 — v1.0.1 patch shipped: PromLens removed from stack`.
       d. `### Known Debt (carried into v2)` section: DELETE the PromLens
          bullet (currently `**PromLens v0.3.0** marked deprecation-candidate; Prometheus 3 absorbs the tree-view surface.`).

    4. **.planning/RETROSPECTIVE.md** — append the
       `## Post-Ship Correction: v1.0.1 — PromLens removed` subsection
       verbatim from the `<interfaces>` template. Placement: directly under
       the v1.0.0 entry, before any cross-milestone trends section. Read the
       file first to identify the v1.0.0 heading boundary.

    Stage with explicit `git add -f` (because `.planning/` is in `.gitignore`
    but planning files are force-tracked):
    `git add CLAUDE.md && git add -f .planning/PROJECT.md .planning/STATE.md .planning/RETROSPECTIVE.md`

    Create commit 3:
    `chore(planning): record PromLens removal in CLAUDE.md + PROJECT.md + STATE.md + RETROSPECTIVE.md (v1.0.1)`

    After the commit lands, create the annotated git tag (locally only):
    `git tag -a v1.0.1 -m "v1.0.1 — PromLens removed (upstream frozen since 2022; Prometheus 3 UI covers the use case). See .planning/RETROSPECTIVE.md for full rationale."`

    Final post-edit validation: run the live-tree grep gate
    `grep -rIl -E "promlens|PromLens|PROMLENS" --include="*.yml" --include="*.yaml" --include="*.j2" --include="*.md" --exclude-dir=".planning" --exclude-dir=".git" .`
    and confirm the output is empty. If non-empty, fix the stragglers
    before declaring done.

    **DO NOT push** the tag or main to origin. The user decides when to push.
  </action>
  <verify>
    <automated>
      cd /home/darko/git/rockdarko/telemetron \
      && git tag --list v1.0.1 | grep -qx v1.0.1 \
      && git rev-parse v1.0.1 > /dev/null \
      && grep -q "v1.0.1" .planning/RETROSPECTIVE.md \
      && grep -q "v1.0.1" .planning/PROJECT.md \
      && grep -q "v1.0.1" .planning/STATE.md \
      && grep -q "v1.0.1" CLAUDE.md \
      && test -z "$(grep -rIl -E 'promlens|PromLens|PROMLENS' --include='*.yml' --include='*.yaml' --include='*.j2' --include='*.md' --exclude-dir='.planning' --exclude-dir='.git' . 2>/dev/null | grep -v -E '^(./README\.md|./docs/architecture\.md)$')" \
      && ansible-playbook --syntax-check playbooks/deploy_docker.yml
    </automated>
  </verify>
  <done>
    All four planning files updated; one atomic commit landed with
    `git add -f` semantics intact; `v1.0.1` annotated git tag exists locally;
    live-tree grep gate confirms only the two intentional "removed in v1.0.1"
    historical references survive (README.md + docs/architecture.md);
    syntax-check still passes; tag NOT yet pushed to origin.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Three atomic commits landed; v1.0.1 annotated git tag created locally;
    PromLens fully excised from live tree; planning history records the
    removal rationale. M1 quality bar ("boots on Rock's homelab Docker host")
    cannot be revalidated from this session — leviathan SSH access is the
    deploy gate and a syntax-check is the most this quick task can prove.
  </what-built>
  <how-to-verify>
    1. Run `git log --oneline -4` and confirm the three new commits exist in
       the expected order:
       - chore(promlens): remove role + inventory + playbook wiring
       - docs: drop PromLens from architecture + inventory + README + role READMEs
       - chore(planning): record PromLens removal ... (v1.0.1)

    2. Run `git tag --list v1.0.1` and confirm `v1.0.1` is present.

    3. Run `git show v1.0.1 --no-patch` and confirm the annotated tag message
       reads correctly.

    4. (Optional, deferred) Next time you deploy to leviathan, run a full
       `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml`
       and confirm:
       - ok=N changed=0 idempotency holds (N drops vs v1.0.0 because PromLens
         is one fewer role).
       - `docker ps --filter name=telemetron-` shows no `telemetron-promlens`
         container.
       - `docker rm -f telemetron-promlens 2>/dev/null` cleans up the stale
         container if leviathan still has it from the v1.0.0 deploy.

    5. Decide: **push to origin now, or hold?**
       - To push when ready: `git push origin main && git push origin v1.0.1`
       - To hold: do nothing; the tag and commits sit locally until you say so.
  </how-to-verify>
  <resume-signal>
    Type "approved" if commits + tag look right (whether or not you push
    today). Type "push it" to authorize me to run the two push commands
    above. Describe issues otherwise.
  </resume-signal>
</task>

</tasks>

<verification>
- `ansible-playbook --syntax-check playbooks/deploy_docker.yml` exits 0.
- Live-tree grep
  `grep -rIl -E "promlens|PromLens|PROMLENS" --include="*.yml" --include="*.yaml" --include="*.j2" --include="*.md" --exclude-dir=".planning" --exclude-dir=".git" .`
  returns at most two paths (README.md + docs/architecture.md), both of which
  contain only "removed in v1.0.1" historical notes.
- `roles/promlens/` directory no longer exists.
- `inventory/example-homelab/group_vars/all/promlens.yml` no longer exists.
- `git tag --list v1.0.1` shows `v1.0.1`.
- Three atomic commits land in the order: (1) role/inventory/playbook,
  (2) docs, (3) planning + tag.
- M1 deploy-time validation (full live UAT on leviathan) is **out of scope for
  this quick task** per CLAUDE.md constraint; flagged for next leviathan
  deploy.
</verification>

<success_criteria>
- PromLens is gone from the deployed-stack surface: role, inventory file,
  playbook wiring, all documentation tables.
- Documentation preserves the historical record: README.md and
  docs/architecture.md tell operators that PromLens was removed in v1.0.1 and
  point at Prometheus 3 as the replacement.
- Planning history (CLAUDE.md + PROJECT.md + STATE.md + RETROSPECTIVE.md)
  captures both the removal and the lesson ("confirm upstream maintenance
  status BEFORE shipping for parity").
- `v1.0.1` annotated git tag exists locally with a rationale-bearing message.
- User is in the loop on the push decision (not pushed autonomously).
</success_criteria>

<output>
Create `.planning/quick/260519-sod-remove-promlens-from-the-telemetron-stac/260519-sod-SUMMARY.md` when done with:
- The three commit SHAs.
- The tag SHA.
- The grep-gate final output (should be 2 paths or empty).
- Whether the user authorized the push (and if so, when it ran).
- A one-line "leviathan revalidation deferred to next deploy" note.
</output>
