# Phase 15: Documentation Cascade - Pattern Map

**Mapped:** 2026-06-05
**Files to modify:** 15 (1 quickstart, 12 role READMEs, root README, roles/README.md)
**Analogs found:** 15 / 15 (every target has a clean Phase 12 analog in-tree)
**Phase shape:** Pure markdown additions; zero code changes; mirrors v1.2.0 Phase 12 plans 12-01/12-02/12-03 one-to-one.

---

## File Classification

| New section | File to modify | Role | Data flow | Closest analog | Match quality |
|---|---|---|---|---|---|
| `## Backup and restore` H2 (5 sub-H3s) | `docs/quickstart.md` | docs / operator-guide | flat reference doc | `docs/quickstart.md` § `## Removing Telemetron` (lines 272-391) | exact (same file, sibling H2) |
| `## Backup` H2 (skeleton + Captured/Not) | `roles/garage/README.md` | role README / stateful | reference doc | `roles/garage/README.md` § `## Uninstall` (lines 125-136) | exact |
| `## Backup` H2 (skeleton + Captured/Not) | `roles/prometheus/README.md` | role README / stateful | reference doc | `roles/prometheus/README.md` § `## Uninstall` (lines 175-185) | exact |
| `## Backup` H2 (skeleton + Captured/Not) | `roles/grafana/README.md` | role README / stateful | reference doc | `roles/grafana/README.md` § `## Uninstall` (lines 108-118) | exact (NOTE: this file uses `---` separators) |
| `## Backup` H2 (skeleton + Captured/Not) | `roles/alertmanager/README.md` | role README / stateful | reference doc | `roles/alertmanager/README.md` § `## Uninstall` (lines 82-92) | exact |
| `## Backup` H2 (one-liner; Garage-backed) | `roles/loki/README.md` | role README / stateless data-in-Garage | reference doc | `roles/loki/README.md` § `## Uninstall` (lines 95-105) | role-match |
| `## Backup` H2 (one-liner; Garage-backed) | `roles/tempo/README.md` | role README / stateless data-in-Garage | reference doc | `roles/tempo/README.md` § `## Uninstall` (lines 156-166) | role-match |
| `## Backup` H2 (one-liner; Garage-backed) | `roles/mimir/README.md` | role README / stateless data-in-Garage | reference doc | `roles/mimir/README.md` § `## Uninstall` (lines 129-139) | role-match |
| `## Backup` H2 (one-liner; truly stateless) | `roles/fluentbit/README.md` | role README / stateless | reference doc | `roles/fluentbit/README.md` § `## Uninstall` (lines 271-281) | role-match |
| `## Backup` H2 (one-liner; truly stateless) | `roles/karma/README.md` | role README / stateless | reference doc | `roles/karma/README.md` § `## Uninstall` (lines 89-99) | role-match |
| `## Backup` H2 (one-liner; truly stateless) | `roles/node_exporter/README.md` | role README / stateless | reference doc | `roles/node_exporter/README.md` § `## Uninstall` (lines 88-98) | role-match |
| `## Backup` H2 (one-liner; truly stateless) | `roles/opentelemetry/README.md` | role README / stateless | reference doc | `roles/opentelemetry/README.md` § `## Uninstall` (lines 164-174) | role-match |
| `## Backup` H2 (one-liner; truly stateless; divergent placement) | `roles/nfsd/README.md` | role README / divergent-stateless | reference doc | `roles/nfsd/README.md` § `## Uninstall` (lines 192-213) — placement AFTER `## Verification`, not after `## Volumes` | divergent (placement difference) |
| "When something goes wrong" cross-ref paragraph | `README.md` (root) | project README | reference doc | `README.md` "When you're done evaluating" paragraph (lines 30-33) | exact (sibling paragraph) |
| Gate 11 (multi-paragraph) | `roles/README.md` § `## Per-role port-acceptance gates` | contributor-facing reference | catalog doc | `roles/README.md` § Gate 10 (lines 106-122) | exact (next numbered gate) |

---

## Plan 15-01 — `docs/quickstart.md ## Backup and restore`

### Primary analog: `docs/quickstart.md ## Removing Telemetron` (lines 272-391; 120 body lines)

**Insertion-point candidates** (planner picks one in plan 15-01; either works):

| Option | Insert after | Insert before | Reading order | Recommendation per CONTEXT.md `<specifics>` |
|---|---|---|---|---|
| (a) After `## Removing Telemetron` | line 391 (end of `### Manual fallback`) | line 393 `## Building your own inventory` | Upgrade → Removing → **Backup and restore** → Building | acceptable |
| (b) Before `## Removing Telemetron` | line 270 (end of `## Upgrade notes`) | line 272 `## Removing Telemetron` | Upgrade → **Backup and restore** → Removing → Building | **recommended** (backup is operationally more frequent than removal) |

### Excerpt 1 — section opener and conservative-default prose (`docs/quickstart.md:272-285`)

```markdown
## Removing Telemetron

Undeploy is the symmetric inverse of deploy. The playbook is
conservative by default: containers and per-role config directories are
removed, but named Docker volumes, the `/opt/telemetron/` host tree,
and pinned Docker images are preserved. Three opt-in irreversible flags
handle full teardown.

\`\`\`bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/undeploy_docker.yml \
                 --ask-vault-pass
\`\`\`
```

Voice: short declarative sentences, "conservative by default" framing, command block with multi-line ansible-playbook invocation broken on `\` continuations. Mirror this exact register for `## Backup and restore`'s opener.

### Excerpt 2 — verbatim PLAY OUTPUT banner block (`docs/quickstart.md:286-299`)

```markdown
Expected PLAY OUTPUT at the start of every run (all flags false):

\`\`\`text
WARNING: irreversible operations status:
  telemetron_purge_data=False
    (named volumes preserved)
  telemetron_purge_host_dirs=False
    (/opt/telemetron/ parent preserved)
  telemetron_purge_images=False
    (Docker images preserved)
\`\`\`

To undeploy a single role, add `--tags <role>` (same pattern as
`deploy_docker.yml`).
```

Pattern: verbatim PLAY OUTPUT block in ```text fence, immediately followed by short "to do X, add Y" tag line. Phase 15's `### Restore` subsection should quote the actual `restore_docker.yml` WARN banner verbatim (see § "Canonical banner source" below).

### Excerpt 3 — sub-H3 with code fence + tag invocation (`docs/quickstart.md:301-316`)

```markdown
### Opt-in purge flags

Each flag is irreversible. Pass via `--extra-vars`. Every destructive
action emits a `WARNING: irreversible -- <role> <action>: <targets>`
line; grep `^WARNING:` against PLAY OUTPUT for an audit trail. All
three flags may be combined in a single `--extra-vars` string.

**`telemetron_purge_data`** -- all `telemetron_*` named Docker volumes
will be removed.

\`\`\`bash
ansible-playbook -i inventory/example-homelab \
                 playbooks/undeploy_docker.yml \
                 --ask-vault-pass \
                 --extra-vars "telemetron_purge_data=true"
\`\`\`
```

Pattern: H3 → opening prose ("operator does X to get Y") → **bold knob name** + one-line description → code fence with full multi-line invocation including the knob via `--extra-vars`. The 5 H3s in `## Backup and restore` follow this rhythm (D-202 + D-203 + D-205).

### Excerpt 4 — manual fallback recipe shape (`docs/quickstart.md:362-391`)

```markdown
### Manual fallback

\`\`\`bash
docker volume ls | grep telemetron_
\`\`\`

Named volumes (alphabetical): `telemetron_alertmanager_data`,
`telemetron_fluentbit_buffer`, `telemetron_garage_data`,
`telemetron_garage_meta`, `telemetron_grafana_data`,
`telemetron_karma_data` (if any), `telemetron_loki_data`,
`telemetron_mimir_data`, `telemetron_prometheus_data`,
`telemetron_tempo_data`.

\`\`\`bash
docker images | grep -E 'grafana|loki|tempo|mimir|prom|otel|fluent|karma|alertmanager|garage|node-exporter'
\`\`\`

\`\`\`bash
# Remove a single named volume after containers are down:
docker volume rm telemetron_grafana_data
# Remove all telemetron_* named volumes at once:
docker volume ls -q --filter "name=telemetron_" | xargs -r docker volume rm
# Remove a pinned image:
docker image rm grafana/grafana-oss:13.0.1
```
```

Pattern: discovery command → operator-readable list of names → action commands. Phase 15's `### Manual fallback` adapts this: stop role container → wipe-volume-via-alpine `docker run --rm -v ...` → extract-tarball-via-alpine `docker run --rm -v ... -v ...` → restart container. Use grafana as the worked example (D-204; simplest volume layout — one volume).

### Canonical banner source — must be quoted verbatim in `## Backup and restore`

**Backup banner** — quote verbatim from `playbooks/backup_docker.yml:119-127` (NO `WARNING: irreversible --` prefix; backup is not destructive):

```yaml
- name: Banner -- backup invocation context (D-186; tags always for --tags <role> visibility)
  ansible.builtin.debug:
    msg: |
      Backup destination: {{ backup_dest_root }}/<role>/
      backup_continue_on_failure={{ backup_continue_on_failure | default(false) }}
        {{ '(all 4 roles will attempt their backup; failures aggregated in PLAY RECAP)' if (backup_continue_on_failure | default(false) | bool) else '(first role failure will abort the playbook)' }}
      backup_stop_timeout={{ backup_stop_timeout }}s
```

**Restore WARN banner** — quote verbatim from `playbooks/restore_docker.yml:110-117`:

```yaml
- name: WARN -- restore will permanently replace volume contents (D-187)
  ansible.builtin.debug:
    msg: |
      WARNING: irreversible -- restore will PERMANENTLY REPLACE volume contents on all 4 stateful roles (garage, prometheus, grafana, alertmanager)
      Target timestamp: {{ backup_restore_from | default('<latest per role>') }}
      Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir
```

The `Restore order:` line ALREADY contains the `Loki/Tempo/Mimir stop before Garage restore` phrasing required by DOCS-V13-02 — quoting the banner satisfies that grep-pin gate without paraphrasing.

### Knob source — `inventory/example-homelab/group_vars/all/backup.yml`

All 5 knob names + defaults are defined here (read this entire 42-line file when writing the `### Backup` and `### Restore` H3s; crib the per-knob comment prose for descriptions):

| Knob | Default | Source line | Used in H3 |
|---|---|---|---|
| `backup_dest_root` | `/opt/telemetron/backups` | `backup.yml:13` | `### Backup`, `### Retention` |
| `backup_stop_timeout` | `60` | `backup.yml:20` | `### Backup` (brief) |
| `backup_continue_on_failure` | `false` | `backup.yml:25` | `### Backup` (D-205 one-liner) |
| `backup_restore_confirm` | `false` | `backup.yml:33` | `### Restore` (the gate) |
| `backup_restore_from` | `""` | `backup.yml:41` | `### Restore` (selector) |

### Section budget & gates (from CONTEXT.md D-203 + D-211)

- Body-line range: **100-220** (generous; matches Phase 12's 40-120 ratio)
- Required verbatim phrases (DOCS-V13-02 grep-pin gates):
  - `backup_restore_confirm=true` (knob name; appears in `### Restore`)
  - `Loki/Tempo/Mimir stop before Garage restore` OR the banner's literal `Restore order: stop Loki/Tempo/Mimir -> garage -> prometheus -> grafana -> alertmanager -> restart Loki/Tempo/Mimir`
  - dated tarballs / `/opt/telemetron/backups/<role>/`
  - "operator manages retention" (operator-managed framing)
- Code-fence balance: even number of ``` fences
- Zero non-ASCII characters in new prose
- Zero `D-XXX` decision references in operator-facing prose

---

## Plan 15-02 — Per-role README `## Backup` sections (12 files)

### Common pattern across all 12 — placement and cross-ref

**Slot for 11 of 12** (all roles except nfsd):
```
## Volumes
[existing — table or "None" line]

## Backup            <-- NEW (Phase 15)
[skeleton OR one-liner]

## Uninstall
[existing — Phase 12 output]
```

**nfsd divergent slot** (D-201; mirrors D-172):
```
## Verification
[existing]

## Backup            <-- NEW (Phase 15) — sits BEFORE Uninstall, but Uninstall is already
                         post-Verification because Phase 12 D-172 chose that placement
## Uninstall
[existing — Phase 12 output]
```

### Canonical cross-ref line (mirror exactly for every per-role `## Backup`)

From `roles/garage/README.md:135-136` (Phase 12 plan 12-02 output):

```markdown
See `docs/quickstart.md#removing-telemetron` for the full undeploy story
(purge flags, manual fallback, order-of-operations).
```

Phase 15 adaptation (mandatory — drop in at end of each stateful `## Backup`):

```markdown
See `docs/quickstart.md#backup-and-restore` for the full backup/restore
story (knobs, restore workflow, manual fallback).
```

### Per-file slot map — all 12 role READMEs

| # | Role | README path | Stateful/Stateless | `## Volumes` line | `## Uninstall` line | `## Backup` insertion point | Template variant (D-199) | Wording |
|---|---|---|:---:|---:|---:|---|---|---|
| 1 | garage | `roles/garage/README.md` | **stateful** | 117 | 125 | between 124 and 125 | full skeleton | per CONTEXT.md `<specifics>` (3-entry tarball; S3 credentials surprise) |
| 2 | prometheus | `roles/prometheus/README.md` | **stateful** | 166 | 175 | between 174 and 175 | full skeleton | 1-entry tarball (`telemetron_prometheus_data`); NOT-captured = nothing host-side; NOTE: restore deletes `/prometheus/lock` |
| 3 | grafana | `roles/grafana/README.md` | **stateful** | 98 | 108 (note `---` separator on 106) | between 105 and 106 (insert BEFORE the `---` separator so order becomes Volumes → `---` → Backup → `---` → Uninstall); planner may choose to add `---` before/after the new H2 to match existing file convention | full skeleton | 1-entry tarball (`telemetron_grafana_data`); NOT captured = provisioning (re-renders from version-controlled config) per D-195 |
| 4 | alertmanager | `roles/alertmanager/README.md` | **stateful** | 75 | 82 | between 81 and 82 | full skeleton | 1-entry tarball (`telemetron_alertmanager_data`); empty-data stat-guard from Phase 13 plan 13-05 / AP-1 |
| 5 | loki | `roles/loki/README.md` | stateless (Garage-backed) | 88 | 95 | between 94 and 95 | one-liner: data-in-Garage | "Data lives in Garage S3 buckets — captured by the garage role's backup. See `roles/garage/README.md#backup`." |
| 6 | tempo | `roles/tempo/README.md` | stateless (Garage-backed) | 149 | 156 | between 155 and 156 | one-liner: data-in-Garage | same template as loki (substitute Tempo) |
| 7 | mimir | `roles/mimir/README.md` | stateless (Garage-backed) | 122 | 129 | between 128 and 129 | one-liner: data-in-Garage | same template as loki (substitute Mimir) |
| 8 | fluentbit | `roles/fluentbit/README.md` | stateless (truly) | 262 | 271 | between 270 and 271 | one-liner: truly-stateless | "No operator state to preserve." |
| 9 | karma | `roles/karma/README.md` | stateless (truly) | 85 | 89 | between 88 and 89 | one-liner: truly-stateless | "No operator state to preserve." |
| 10 | node_exporter | `roles/node_exporter/README.md` | stateless (truly) | 76 | 88 | between 87 and 88 | one-liner: truly-stateless | "No operator state to preserve." |
| 11 | opentelemetry | `roles/opentelemetry/README.md` | stateless (truly) | 153 | 164 | between 163 and 164 | one-liner: truly-stateless | "No operator state to preserve." |
| 12 | **nfsd** (DIVERGENT) | `roles/nfsd/README.md` | stateless (truly) | n/a (no `## Volumes`) | 192 (after `## Verification` at 172, NOT after Volumes) | between 191 and 192 (immediately before `## Uninstall`, which sits post-Verification per D-172) | one-liner: truly-stateless | "No operator state to preserve." (D-201 — operator's `/srv/telemetron-nfs/` data is THEIR responsibility; Phase 12's `## Uninstall` disclaimer below already covers it) |

### Stateful skeleton template (apply uniformly to rows 1-4)

Pattern derived from CONTEXT.md `<specifics>` garage worked example. Five-part shape per D-195:

```markdown
## Backup

[1-line intro: "The <role> role ships `tasks/backup.yml` and
`tasks/restore.yml` for atomic cold-quiesce backup and restore of <role>'s
<volume(s)>."]

**Captured (<N> entries in the tarball):**
- [bullet 1 — named volume]
- [bullet 2 — additional named volume if any]
- [bullet 3 — host file if any — garage only: s3-credentials]

**Not captured:**
- [bullet — what isn't in the tarball, and why; garage has "(nothing)"
  because S3 creds are captured intentionally; grafana has "provisioning
  (re-renders from version-controlled config)"; prometheus / alertmanager
  fill per role]

\`\`\`bash
ansible-playbook playbooks/backup_docker.yml --tags <role> --ask-vault-pass
\`\`\`

See `docs/quickstart.md#backup-and-restore` for the full backup/restore
story (knobs, restore workflow, manual fallback).
```

### Stateless one-liner templates (apply uniformly to rows 5-12)

**Variant A — data-in-Garage (loki, tempo, mimir):**

```markdown
## Backup

Data lives in Garage S3 buckets — captured by the garage role's backup.
See `roles/garage/README.md#backup`.
```

**Variant B — truly stateless (fluentbit, karma, node_exporter, opentelemetry, nfsd):**

```markdown
## Backup

No operator state to preserve.
```

Per D-200 + CONTEXT.md `<claudes_discretion>`: planner MAY tighten or extend by ≤5 words per role. Two-template distinction is LOCKED.

### Per-stateful-role "Captured/Not captured" content (planner must fill these honestly from Phase 13 outputs)

| Role | Captured (verbatim guidance) | Not captured (verbatim guidance) | Source-of-truth file |
|---|---|---|---|
| garage | 3 entries: `telemetron_garage_meta` volume (LMDB metadata), `telemetron_garage_data` volume (object data blocks), `{{ garage_s3_credentials_file }}` host file (S3 keypair the writers use) | (nothing — credentials are intentionally captured even though host-mounted, so restore reconnects without operator re-bootstrap) | `roles/garage/tasks/backup.yml` (Phase 13 plan 13-02); D-176 |
| prometheus | 1 entry: `telemetron_prometheus_data` volume (TSDB + lockfile + WAL) | (nothing host-side beyond rendered config which re-renders on next deploy); note that `tasks/restore.yml` deletes `/prometheus/lock` after untar before restart (PP-1) | `roles/prometheus/tasks/backup.yml` (Phase 13 plan 13-03) |
| grafana | 1 entry: `telemetron_grafana_data` volume (embedded SQLite — dashboards, orgs, users, sessions, plugins cache) | provisioning tree (`/opt/telemetron/grafana/`) — re-renders from version-controlled config on next deploy; admin password rotation if it changed post-backup (operator concern per GR-4) | `roles/grafana/tasks/backup.yml` (Phase 13 plan 13-04) |
| alertmanager | 1 entry: `telemetron_alertmanager_data` volume (silences + nflog + active-alert state — Pitfall 7 dedup memory); empty-data stat-guard (AP-1) handles fresh-install case gracefully | rendered `alertmanager.yml` (re-renders from version-controlled config) | `roles/alertmanager/tasks/backup.yml` (Phase 13 plan 13-05) |

### Plan 15-02 verification gates (one acceptance criterion per row)

- All 12 role READMEs contain `^## Backup$` exactly once
- All 12 contain anchor-equivalent `#backup` link target (GitHub auto-generates from H2)
- All 4 stateful README `## Backup` sections contain both `**Captured` and `**Not captured` bold labels
- All 8 stateless README `## Backup` sections are ≤5 body lines (excluding the H2 itself)
- Roles 5-7 (loki, tempo, mimir) contain literal substring `garage role` or `roles/garage/README.md#backup`
- Roles 8-12 contain literal substring `No operator state to preserve` (planner may extend ≤5 words but this lede stays)
- All 4 stateful `## Backup` sections end with the `docs/quickstart.md#backup-and-restore` cross-ref line
- Code-fence balance: even number of ``` fences per file
- Zero non-ASCII characters introduced in modified files (existing § / ☑ / em-dash in karma + roles/README.md are pre-existing per CONTEXT.md `<established_patterns>` — out of scope)
- Per-section line budget for stateful: 8-25 body lines (per CONTEXT.md `<claudes_discretion>`)

---

## Plan 15-03 — Root README + roles/README.md Gate 11

### Sub-plan A: `README.md` "When something goes wrong" cross-ref

**Analog: `README.md` "When you're done evaluating" paragraph (lines 30-33)**

```markdown
When you're done evaluating,
[`docs/quickstart.md#removing-telemetron`](docs/quickstart.md#removing-telemetron)
documents the symmetric undeploy playbook -- conservative by default
(volumes preserved); three opt-in flags for irreversible cleanup.
```

Voice: opening adverbial phrase (`When X,`), inline link with full code-fenced URL as both link text and target, em-dash for parenthetical, "conservative by default" framing, semicolon-separated continuation, 4-line wrap.

**Insertion point:** immediately after line 33 (the existing paragraph's blank-line-terminated last line), before the `## What's included` H2 at line 35. The new paragraph occupies what is currently line 34's blank.

**Phase 15 wording template** (from CONTEXT.md D-206; planner may adjust phrasing within Phase 12 voice):

```markdown
When something goes wrong,
[`docs/quickstart.md#backup-and-restore`](docs/quickstart.md#backup-and-restore)
covers the backup playbook (conservative by default -- local dated
tarballs; operator manages retention) and the restore workflow (with the
explicit `--extra-vars backup_restore_confirm=true` safety gate).
```

**Required-phrase gates (DOCS-V13-02 root clause):**
- `When something goes wrong` (lede; required)
- `docs/quickstart.md#backup-and-restore` (link target; required)
- `backup_restore_confirm=true` (knob name appears verbatim)

### Sub-plan B: `roles/README.md` Gate 11

**Analog: Gate 10 (lines 106-122) — Phase 12 plan 12-03 / D-175 output**

Full 17-line Gate 10 block reproduced here verbatim (it is the planner's structural template):

```markdown
**10. Per-role uninstall contract (UNDEPLOY-02; D-148):**

Every deploy role MUST ship a tested uninstall path. The contract has five parts:

(a) `tasks/uninstall.yml` exists in the role and is invocable by the orchestrator via `include_role: { name: <role>, tasks_from: uninstall }` (D-132). The file references role variables from the role's own `defaults/main.yml` directly (D-134) -- no hardcoded container names, no hardcoded paths.

(b) Stops and removes the role's container via `community.docker.docker_container` with `state: absent` and `keep_volumes: true`. The `keep_volumes: true` argument is the explicit mechanism that prevents the docker module from touching the named Docker volume(s) the container is attached to -- the volume is preserved by default per UNDEPLOY-02.

(c) Removes role-private host artifacts under `/opt/telemetron/<role>/` (the role's `<role>_config_dir`) via `ansible.builtin.file` with `state: absent`. Removal is scoped to the role's own subdirectory only; the parent `/opt/telemetron/` is the orchestrator's concern, not the role's (D-144).

(d) Does NOT touch named Docker volumes. The volume-preservation default is the most operator-protective posture for a homelab: an accidental `undeploy` followed by `deploy` re-bootstraps cleanly against surviving data. Wholesale named-volume removal is reserved for Phase 11's `telemetron_purge_data=true` flag, not anything a per-role `uninstall.yml` does.

(e) Idempotent: re-running the uninstall against an already-clean host (container absent, config directory absent) produces `changed=0` in the PLAY RECAP. The mechanism is to trust `state: absent` semantics on the underlying modules ...

`nfsd` follows the same contract with its host-package adaptation [... divergence paragraph ...]

Orchestrator behaviour -- purge flags (`telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images`), reverse-order role iteration in `playbooks/undeploy_docker.yml`, WARNING messages for irreversible operations -- is out of Gate 10 scope. Phase 11 shipped these as playbook-level concerns and did NOT add a Gate 11; the per-role contract above is sufficient. See `docs/quickstart.md#removing-telemetron` for the operator-facing story. Established in Phase 10 plans 10-01 through 10-05; future role additions inherit this contract.
```

**Structural anatomy of Gate 10 (mirror exactly in Gate 11):**

| Element | Gate 10 example | Gate 11 adaptation |
|---|---|---|
| Bold lede with `**N. <title> (<REQ-IDs>; D-XXX):**` | `**10. Per-role uninstall contract (UNDEPLOY-02; D-148):**` | `**11. Per-role backup/restore contract (BACKUP-V13-01..04 + RESTORE-V13-01..04; D-176..D-179):**` |
| Single-sentence contract statement | "Every deploy role MUST ship a tested uninstall path. The contract has five parts:" | "Every stateful role MUST ship `tasks/backup.yml` and `tasks/restore.yml` proven on leviathan end-to-end. The 4 stateful roles are: `garage`, `prometheus`, `grafana`, `alertmanager`." |
| Lettered sub-clauses `(a)`, `(b)`, `(c)`, ... | 5 parts (a-e) covering existence, container-removal, host-artifact-removal, named-volume-preservation, idempotency | 3 parts (a-c) per CONTEXT.md worked example: (a) backup cold-quiesce + block/rescue/always; (b) restore confirm-gate + `tar tf` + wipe + untar + restart + verify; (c) zstd pre-task; planner may add (d) if a 4th genuinely-distinct contract clause emerges |
| Divergent-role paragraph after main contract | `nfsd` divergent paragraph (3 lines) | Statement that the 8 stateless roles document no-backup status in their README only (no empty `tasks/backup.yml` no-op files); enumerate them; Loki/Tempo/Mimir data in Garage handoff distinction |
| Closing paragraph distinguishing in-gate from out-of-gate scope | "Orchestrator behaviour -- purge flags ... -- is out of Gate 10 scope. Phase 11 shipped these as playbook-level concerns and did NOT add a Gate 11 ..." | "Orchestrator behavior -- the `backup_continue_on_failure` knob, writer-quiesce on Garage restore (Loki/Tempo/Mimir stop before, restart after), and restore's hardcoded bail-out (`any_errors_fatal: true`) -- is out of Gate 11 scope. Phase 14 shipped these as `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` concerns; the per-role contract above is sufficient." |
| Forward-point cross-ref | `See \`docs/quickstart.md#removing-telemetron\` for the operator-facing story.` | `See \`docs/quickstart.md#backup-and-restore\` for the operator-facing story.` |
| Closing sentence pattern | `Established in Phase 10 plans 10-01 through 10-05; future role additions inherit this contract.` | `Established in Phase 13-14 plans; future role additions inherit this contract.` |

**Gate 11 insertion point:** immediately after line 122 (Gate 10's closing line, no terminating blank line follows in current file — planner adds the blank-line separator + Gate 11 block). Becomes new lines 123-N.

**Worked Gate 11 reference (from CONTEXT.md `<specifics>` — planner may adopt verbatim or refine):**

The CONTEXT.md `<specifics>` section contains a full ~25-line Gate 11 draft starting with `**11. Per-role backup/restore contract...` — use it as the seed. It already exhibits all structural elements above.

**Required-phrase gates (DOCS-V13-01):**
- `Gate 11` (the heading number must appear; satisfied by `**11.` lede)
- Literal names: `garage`, `prometheus`, `grafana`, `alertmanager` (all four stateful, verbatim, in one place)
- Literal names: `loki`, `tempo`, `mimir`, `fluentbit`, `karma`, `node_exporter`, `opentelemetry`, `nfsd` (all eight stateless, verbatim, in one place)
- `tasks/backup.yml` and `tasks/restore.yml` (literal file names)
- `proven on leviathan` (acceptance heuristic phrasing per D-207)
- `no empty no-op task files` (or semantic equivalent: states that stateless roles document status in README only)
- Cross-ref: `docs/quickstart.md#backup-and-restore`
- Closing-line phrase: `future role additions inherit this contract` (matches Gate 10's closing-line pattern per D-207)

**Gate 11 length budget:** 15-30 body lines (Gate 10 is 17 lines; matches Gate 8 at ~25 lines; CONTEXT.md `<specifics>` worked example is ~25 lines).

### Plan 15-03 verification gates (DOCS-V13-01 + DOCS-V13-02 root clause)

- `README.md` contains line matching `When something goes wrong` (lede appears verbatim)
- `README.md` contains link to `docs/quickstart.md#backup-and-restore`
- `roles/README.md` contains `^\*\*11\. ` (Gate 11 lede)
- `roles/README.md` Gate 11 names all 4 stateful roles verbatim
- `roles/README.md` Gate 11 names all 8 stateless roles verbatim
- `roles/README.md` Gate 11 contains `tasks/backup.yml` and `tasks/restore.yml` literal strings
- `roles/README.md` Gate 11 forward-points to `docs/quickstart.md#backup-and-restore`
- Code-fence balance: even number of ``` fences (Gate 11 is prose-only — should add zero fences)
- Zero non-ASCII characters introduced in modified files
- Zero `D-XXX` decision references in operator-facing prose in `README.md` (Gate 11 in `roles/README.md` MAY cite D-IDs per Gate 10 precedent — `roles/README.md` is contributor-facing, not operator-facing)

---

## Shared Patterns (apply across all 3 plans)

### Pattern S1 — Lowercase-hyphenated H2 → GitHub auto-anchor

**Source:** `docs/quickstart.md ## Removing Telemetron` produces `#removing-telemetron` automatically (verified in Phase 12).

**Apply to:**
- `docs/quickstart.md ## Backup and restore` → `#backup-and-restore` (used by 13 cross-refs across phase 15 outputs)
- `roles/<role>/README.md ## Backup` → `#backup` (uniform across all 12 deployed roles per D-200)
- All sub-H3s within `## Backup and restore` produce sub-anchors automatically (`#backup`, `#restore`, `#stop-order-during-garage-restore`, `#retention`, `#manual-fallback`)

No anchor frontmatter, no manual `<a name="">`, no `{#anchor}` extensions needed.

### Pattern S2 — Cross-ref voice (mirror "When you're done evaluating" tonal register)

**Source:** `README.md:30-33`

**Voice register signals:**
- Opening adverbial phrase (`When X,`)
- Inline-code-wrapped link target as link text: `[`docs/quickstart.md#X`](docs/quickstart.md#X)`
- Em-dash for parenthetical (4 hyphens render as em-dash; matches existing Phase 12 outputs)
- Short declarative continuation after em-dash
- 3-5 line wrap, blank-line-terminated

**Apply to:**
- Root README "When something goes wrong" paragraph (Plan 15-03 sub-plan A)
- Optionally — per-role README cross-refs to quickstart (already standardized by Phase 12 garage pattern; Phase 15 inherits)

### Pattern S3 — No decision-ID references in operator-facing prose

**Source:** CONTEXT.md `<established_patterns>` — Phase 12 plan 12-01 verification gate.

**Apply to:**
- `docs/quickstart.md ## Backup and restore` (operator-facing — zero `D-XXX` allowed)
- `README.md` "When something goes wrong" (operator-facing — zero `D-XXX` allowed)
- Per-role README `## Backup` sections (operator-facing — zero `D-XXX` allowed)

**Exception:** `roles/README.md` Gate 11 is contributor-facing (the file already cites `D-90`, `D-148`, `D-148`, `D-30`, `D-148`, etc. in Gates 1-10 — Gate 11 follows suit and SHOULD cite the relevant D-IDs in its lede per Gate 10 pattern).

### Pattern S4 — Code-fence balance (verification gate every plan inherits from Phase 12)

Every modified file MUST have an even number of ` ``` ` fence delimiters. Verification command:

```bash
grep -c '^```' <file> | awk '{ if ($1 % 2 != 0) exit 1 }'
```

### Pattern S5 — Zero non-ASCII regressions

**Source:** CONTEXT.md `<established_patterns>` + Pitfall 9 (`.planning/research/PITFALLS.md`).

Pre-existing non-ASCII characters in `karma/README.md` and `roles/README.md` (§ / ☑ / em-dash) are out of scope. Phase 15 introduces ZERO new non-ASCII characters. Verification:

```bash
grep -rPn '[^\x00-\x7F]' <modified-files>
# diff against same command's output BEFORE phase 15 edits
```

### Pattern S6 — Plan parallelism (D-210)

All 3 plans modify disjoint file sets:
- **15-01:** `docs/quickstart.md` only
- **15-02:** 12 × `roles/<role>/README.md` only
- **15-03:** `README.md` + `roles/README.md` only

Forward-referenced markdown anchors (per-role README → quickstart `#backup-and-restore`; root README → quickstart `#backup-and-restore`; quickstart self-references) are stable regardless of merge order. Phase 12 D-174 already validated this. Planner may wave-1 all three plans.

---

## No Analog Found

None. Every Phase 15 target has a clean Phase 12 analog in-tree. This is the doc-cascade equivalent of Phase 12 directly — the structural template is fully proven.

---

## Metadata

**Analog search scope:**
- `docs/quickstart.md` (full file; 441 lines)
- `roles/README.md` (full file; 122 lines)
- `README.md` (full file; 102 lines)
- All 12 deployed-role READMEs (7,180 lines total across the 12)
- `playbooks/backup_docker.yml` + `playbooks/restore_docker.yml` (banner extraction; lines 105-127 of each)
- `inventory/example-homelab/group_vars/all/backup.yml` (full file; 42 lines)

**Files scanned:** 19 (1 quickstart + 13 READMEs + 2 playbooks + 1 inventory file + 2 planning files)

**Pattern extraction date:** 2026-06-05

**Total analog excerpts captured:** 20+ (Plan 15-01: 4 excerpt blocks + 2 banner sources + 5 knob-source rows; Plan 15-02: 1 cross-ref pattern + 12-row slot map + 4-row stateful-content table; Plan 15-03: 1 root README excerpt + Gate 10 full reproduction + 7-row structural-anatomy table)
