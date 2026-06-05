# Phase 13: Per-Role Backup & Restore Tasks - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 13-per-role-backup-restore-tasks
**Areas discussed:** Garage tarball shape, Stop-timeout per role, Verify pattern, Timestamp format + latest-discovery

---

## Garage tarball shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single tarball | One `garage-<ts>.tar.zst` with three top-level entries: `meta/`, `data/`, `s3-credentials`. Symmetric with the 3 other roles (one tarball per role). Restore is one untar. Operator latest-discovery uniform across all roles. | ✓ |
| Two tarballs (meta + data split) | `garage-meta-<ts>.tar.zst` and `garage-data-<ts>.tar.zst`; `s3-credentials` bundled into the meta tarball. Allows independent meta-only recovery. Asymmetric vs other 3 roles; restore needs two untars + ordering. | |

**User's choice:** Single tarball (Recommended option)
**Notes:** Symmetry across all 4 stateful roles wins. Any single-volume corruption case is already covered by the operator keeping multiple dated backups; the two-tarball ordering surface buys nothing in exchange for the asymmetry.

---

## Stop-timeout per role

| Option | Description | Selected |
|--------|-------------|----------|
| Per-role override with shared default 60s | `backup_stop_timeout: 60` in `group_vars/all/`, per-role override `<role>_backup_stop_timeout` defaulting from it. 6× Docker default. Operator can tune without code change. | ✓ |
| Hard-coded uniform 60s, no override knob | 60 baked into every backup task literal. Simpler; operators who need longer edit role tasks/backup.yml directly. | |
| Trust Docker default (10s) | No `-t` flag. Saves 50s on normal-case shutdowns. Risk: SIGKILL on slow checkpoint corrupts Prometheus/Garage state. | |

**User's choice:** Per-role override with shared default 60s (Recommended option)
**Notes:** Belt-and-suspenders against the PP-1 / GP-1 class of corruption. The shared-default + per-role-override shape mirrors Telemetron's existing `telemetron_*` defaulting pattern.

---

## Verify pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Re-use existing `tasks/verify.yml` after restart | `include_tasks: verify.yml` in the `always:` block of every backup + restore task. Garage diverges with inline `docker_container_info` healthy poll (no verify.yml). | ✓ |
| Inline minimal health probe | `docker_container_info` poll until `State.Health.Status == healthy`. Lighter, restore-specific. Decouples from any drift in verify.yml. | |
| Both: inline health poll AND verify.yml | Inline poll first, then verify.yml. Most coverage, longest path (~30s/role extra). | |

**User's choice:** Re-use existing `tasks/verify.yml` after restart (Recommended option)
**Notes:** Single source of truth for "is this role healthy" wins over divergent verification paths. Garage's inline-poll divergence is forced by its missing `verify.yml`, not a design preference — Phase 13 should NOT create a new `roles/garage/tasks/verify.yml` just for symmetry (out of scope).

---

## Timestamp format + latest-discovery

| Option | Description | Selected |
|--------|-------------|----------|
| ISO 8601 basic: `YYYYMMDDTHHMMSSZ` | `garage-20260603T143012Z.tar.zst`. `T` separator + trailing `Z` make UTC explicit. `date -u +%Y%m%dT%H%M%SZ` one-liner. Single `*.tar.zst` glob discovery. | ✓ |
| Dashed local-style: `YYYYMMDD-HHMMSS` | `garage-20260603-143012.tar.zst`. Matches STATE.md example; no `T`/`Z` marker — UTC-ness implicit. | |
| RFC 3339 with hyphens + colons: `YYYY-MM-DDTHH:MM:SSZ` | Most human-readable; colons in filenames break Windows SMB shares (low risk for amd64-Linux Telemetron but adds drag for operators rsyncing to NAS later). | |

**User's choice:** ISO 8601 basic `YYYYMMDDTHHMMSSZ` (Recommended option)
**Notes:** `T`+`Z` makes the format unambiguous. STATE.md's `YYYYMMDD-HHMMSS` example is now superseded — `/gsd:transition` between Phase 13 and Phase 14 will reconcile it.

---

## Claude's Discretion

Three items deferred to planner with safe defaults:

1. **Pre-flight disk-space check via `backup_space_factor: 1.5`** — research recommended, but Telemetron has no hidden-capacity-knob precedent. Default if planner is silent: skip.
2. **Alertmanager empty `data/` directory guard** — STACK.md open question 2. Planner picks `stat`-then-skip-with-debug vs tar-empty-dir vs sentinel file.
3. **Sub-order within Phase 13** — research recommended Garage → Prometheus → Grafana → Alertmanager. Plans can be written in parallel (the 8 task files don't share files).

## Deferred Ideas

- Pre-flight disk-space check (`backup_space_factor`) — operator-managed default; planner discretion.
- Backup tarball checksum sidecar (`*.sha256`) — FEATURES.md "deferred"; Phase 14 `tar tf` covers v1.3.0.
- `manifest.json` per tarball — tarball filename + listing serve as manifest for v1.3.0.
- `<role>-latest` symlink — `find | sort -r | head -1` is the v1.3.0 contract.
- `backup_before_restore` auto-snapshot — deferred per FEATURES.md.
- Off-host destination knobs (rsync / S3 push) — BACKUP-V14-01/02.
- STATE.md timestamp format example update — handled by `/gsd:transition`, not by Phase 13 planner.
