# Phase 15: Documentation Cascade - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 15-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 15-documentation-cascade
**Areas discussed:** Per-role ## Backup (4 stateful), Stateless one-liners (8 roles), quickstart ## Backup and restore section, Plan breakdown

---

## Per-role ## Backup section (4 stateful)

### Q1: ## Backup H2 placement in the 4 stateful READMEs

| Option | Description | Selected |
|--------|-------------|----------|
| Between ## Volumes and ## Uninstall (Recommended) | Reads as a data-lifecycle cluster (Volumes → Backup → Uninstall) | ✓ |
| Immediately after ## Uninstall | Preserves Phase 12's Volumes→Uninstall→Healthcheck cluster | |
| Between ## Tags and ## Modes | Invocation-centric framing | |

**User's choice:** Between ## Volumes and ## Uninstall
**Notes:** Captured as D-194.

### Q2: Uniform template vs per-role variation

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform skeleton, per-role 'NOT captured' content (Recommended) | Same H2 structure, per-role content variation for what's not captured | ✓ |
| Fully uniform including bullet text | Maximum template consistency but flattens per-role surprises | |
| Free-form per role | Each role writes its own shape | |

**User's choice:** Uniform skeleton + per-role NOT-captured content
**Notes:** Captured as D-195. Garage's 3-entry tarball with s3-credentials is the surprise that must remain visible.

### Q3: "Captured / Not captured" framing

| Option | Description | Selected |
|--------|-------------|----------|
| Two short bullet lists: 'Captured:' / 'Not captured:' (Recommended) | Mirrors existing role README bullet-list style | ✓ |
| Single prose paragraph | Shorter but buries the surprises | |
| Two-column markdown table | Maximum scannability, unusual for role READMEs | |

**User's choice:** Two short bullet lists
**Notes:** Captured as D-196.

### Q4: Cross-references in stateful ## Backup sections

| Option | Description | Selected |
|--------|-------------|----------|
| Just to quickstart#backup-and-restore (Recommended) | Mirrors Phase 12 Uninstall pattern | ✓ |
| To quickstart + sibling role READMEs | None of the 4 stateful roles has cross-role data dep at backup time | |
| No cross-references | Loses discoverability handoff Phase 12 established | |

**User's choice:** Just to quickstart#backup-and-restore
**Notes:** Captured as D-197.

---

## Stateless 'no backup' one-liner shape (8 roles)

### Q1: Shape of the 'no backup' note

| Option | Description | Selected |
|--------|-------------|----------|
| New ## Backup H2 with one sentence (Recommended) | Uniform with 4 stateful READMEs; same anchor across all 12 deployed roles | ✓ |
| Inline appended to ## Uninstall | Less visual weight; smaller diff | |
| Standalone paragraph above ## Uninstall (no H2) | Lightweight but loses anchor consistency | |

**User's choice:** New ## Backup H2 with one sentence
**Notes:** Captured as D-198.

### Q2: Wording template differentiation

| Option | Description | Selected |
|--------|-------------|----------|
| Two templates — data-in-Garage vs truly-stateless (Recommended) | Loki/Tempo/Mimir vs Karma/FluentBit/OTel/node_exporter/nfsd | ✓ |
| One uniform template | Loses the operator-useful 'your loki data IS backed up' handoff | |
| Per-role custom wording | 8 hand-tuned sentences | |

**User's choice:** Two templates
**Notes:** Captured as D-199.

### Q3: H2 position in stateless READMEs

| Option | Description | Selected |
|--------|-------------|----------|
| Same slot as stateful (Volumes → Backup → Uninstall) (Recommended) | Identical placement across all 12 deployed READMEs | ✓ |
| Between ## Uninstall and ## Healthcheck | 'After destructive, here's why no constructive' | |
| Final section of the README | Lowest visual prominence | |

**User's choice:** Same slot as stateful
**Notes:** Captured as D-200.

### Q4: nfsd handling

| Option | Description | Selected |
|--------|-------------|----------|
| Same template as truly-stateless group (Recommended) | One-sentence H2 placed before nfsd's divergent ## Uninstall block | ✓ |
| Divergent nfsd-specific wording | Explicit disclaimer for /srv/telemetron-nfs/ contents | |
| Skip nfsd — no Docker volume | Loses 12-of-12 uniformity | |

**User's choice:** Same truly-stateless template
**Notes:** Captured as D-201. nfsd's existing ## Uninstall (D-138) already disclaims responsibility for the share root contents.

---

## quickstart.md ## Backup and restore section

### Q1: Structure for the 5 required topics

| Option | Description | Selected |
|--------|-------------|----------|
| Sub-H3 subsections per topic (Recommended) | ### Backup / ### Restore / ### Stop-order / ### Retention / ### Manual fallback | ✓ |
| Flat prose like Phase 12 (no sub-H3s) | Mirror v1.2.0 shape exactly | |
| Hybrid — prose for backup, sub-H3s for restore | Asymmetric structure matches asymmetric complexity | |

**User's choice:** Sub-H3 subsections per topic
**Notes:** Captured as D-202.

### Q2: Line budget

| Option | Description | Selected |
|--------|-------------|----------|
| 150-200 body lines (Recommended) | ~30-50% more content than Phase 12's 120; honest for 2 orchestrators + 5 knobs | ✓ |
| Match Phase 12 ceiling (120 body lines) | Hard ceiling forces brevity | |
| No ceiling, optimize for completeness (200-300+) | Document everything; risks bloating quickstart | |

**User's choice:** 150-200 body lines
**Notes:** Captured as D-203. Acceptance gate 100-220.

### Q3: Manual fallback depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full recipe with concrete commands (Recommended) | Stop, wipe-volume-via-alpine, untar-with-unzstd, restart | ✓ |
| Conceptual + tar command only | Punts volume-mount-path lookup to operator | |
| Just point at Phase 13's tasks/restore.yml | Violates 'without reading source code' goal | |

**User's choice:** Full recipe with concrete docker commands
**Notes:** Captured as D-204. Grafana as worked example; garage's 3-entry layout noted.

### Q4: backup_continue_on_failure treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Brief mention in ### Backup with one-line use-case (Recommended) | Operators see it without it dominating | ✓ |
| Footnote at section bottom | Risk: operators hunt and find nothing | |
| Full subsection | Heavier than needed for homelab audience | |

**User's choice:** Brief one-line mention in ### Backup
**Notes:** Captured as D-205. Also note restore has NO equivalent (D-185 hardcodes bail-out).

---

## Plan breakdown for Phase 15

### Q1: Plan split

| Option | Description | Selected |
|--------|-------------|----------|
| 3 plans, mirror Phase 12 exactly (Recommended) | 15-01 quickstart, 15-02 per-role READMEs (4 stateful + 8 stateless), 15-03 root README + Gate 11 | ✓ |
| 4 plans — split per-role work | Cleaner per-plan diff scope | |
| 5+ plans — separate Gate 11, root README, each role group | Most granular; overkill for 3-req doc phase | |

**User's choice:** 3 plans mirror Phase 12 exactly
**Notes:** Captured as D-209.

### Q2: Wave/parallelization

| Option | Description | Selected |
|--------|-------------|----------|
| All plans parallel-safe (Recommended) | Disjoint file sets; forward-referenced anchors work post-merge | ✓ |
| Sequential — quickstart first, then per-role, then root README | Conservative; mirrors Phase 12 stated order | |
| Two waves: quickstart + per-role parallel, then Gate 11/cross-ref | Hybrid with one sync point | |

**User's choice:** All plans parallel-safe (one wave)
**Notes:** Captured as D-210.

### Q3: Gate 11 detail level

| Option | Description | Selected |
|--------|-------------|----------|
| Match Gate 10's depth (~15 lines, multi-paragraph) (Recommended) | Consistent with Gates 1-10 voice | ✓ |
| Brief gate (~5 lines) | Inconsistent with existing detail level | |
| Match Gate 10 + cite V13 requirement IDs | Couples gate prose to per-milestone IDs | |

**User's choice:** Match Gate 10's depth
**Notes:** Captured as D-207 + D-208.

### Q4: HUMAN-UAT

| Option | Description | Selected |
|--------|-------------|----------|
| Skip HUMAN-UAT — doc-only phase (Recommended) | Phase 12 precedent; verification via grep + read-through | ✓ |
| Lightweight HUMAN-UAT — operator reads quickstart + executes backup | Catches doc-reality drift | |
| Full HUMAN-UAT — doc-driven 7-step round-trip on leviathan | Overkill given Phase 14 already passed | |

**User's choice:** Skip HUMAN-UAT
**Notes:** Captured as D-211. Lightweight doc-read-through captured as deferred milestone-close idea.

---

## Claude's Discretion

(Left to planner with safe defaults — full list in 15-CONTEXT.md `<decisions>` § Claude's Discretion)

- Exact wording of stateless one-liners (two templates locked; ≤5-word planner adjustment OK)
- Exact wording of root README "When something goes wrong" line
- Whether to include sample PLAY OUTPUT for restore WARN banner in quickstart
- Whether manual fallback shows just grafana or all 4 stateful roles
- Exact ordering of the 5 H3s within `## Backup and restore`
- Retention guidance specifics (rsync/restic/find one-liners)
- Acceptance line-count gates for the per-role sections

## Deferred Ideas

(Full list in 15-CONTEXT.md `<deferred>`)

- Off-host backup destinations (BACKUP-V14-01..03, v1.4.0+)
- Encryption-at-rest for tarballs
- Per-role tarball comparison table (Claude's Discretion in plan 15-01)
- Lightweight doc-read-through HUMAN-UAT (v1.3.0 audit-milestone idea)
- Per-role README `## Restore` H2 (future doc pass; not required by DOCS-V13-03)
- PLAY OUTPUT block for restore WARN banner in quickstart (Claude's Discretion)
