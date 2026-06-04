---
plan: 14-04-human-uat
phase: 14-orchestrators-leviathan-human-uat
status: partial
completed: 2026-06-04T18:05:00Z
requirements:
  - UAT-V13-01
gaps_opened:
  - G-01
  - G-03
---

# Plan 14-04 — Human UAT (live leviathan) — Summary

## Self-Check: PASSED (with gaps tracked)

Skeleton committed, all 11 sub-scenarios executed live against leviathan, evidence captured verbatim in `14-HUMAN-UAT.md`. 9 pass, 2 fail. Two real defects surfaced (G-01, G-03) — both have manifests, evidence, and fix-plans recorded in the doc's `## Gaps` section. No skeleton/format regressions.

## What was built

- **Task 1**: `14-HUMAN-UAT.md` skeleton — frontmatter + 11 sub-scenarios with `expected:` text + `result: pending` + `detail: TBD` (3-line shape per Pattern N), verbatim format matching `v1.2.0-phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md`. Skeleton verify gates all passed (33 grep assertions).
- **Task 2**: live UAT execution against leviathan. Inventory: `inventory/leviathan/` (gitignored). Vault: secrets are plaintext per inventory comment "Plaintext for autonomous Claude-driven UAT runs" — `--ask-vault-pass` not required. SSH passwordless ✓. Sudo passwordless ✓.

## Results matrix (11 sub-scenarios)

| # | Scenario | Result | Notes |
|---|----------|--------|-------|
| 1 | 7-step round-trip (UAT-V13-01) | FAIL | G-01 — restore orchestrator missing writer-config rerender |
| 2a | Confirm-gate orchestrator (OPS-V13-01) | PASS | Verbatim msg fires; 11 containers untouched |
| 2b | Per-role gate defence-in-depth (OPS-V13-01) | PASS | Throwaway playbook; grafana role's gate fires |
| 2c | Identity-level gate (D-188 amended) | PASS | `--tags loki` without confirm still fails at always-tagged gate |
| 3a | Default bail-out (OPS-V13-02) | PASS | Methodology pivot: chmod 000 ineffective vs root, used file-as-dir fault instead |
| 3b | Continue-on-failure (OPS-V13-02 opt-in) | FAIL | G-03 — banner alt text fires but grafana+alertmanager not attempted |
| 4a | `--tags garage` backup (OPS-V13-03) | PASS | Only garage tarball at new ts |
| 4b | `--tags loki` restore with confirm | PASS | 0 role tasks, 11 containers untouched, WARN banner fires |
| 4c | `--tags grafana` restore (D-189 amended) | PASS | Loki StartedAt unchanged before/after |
| 4d-backup | `--tags backup` cross-cutting (SC4) | PASS | 4 tarballs share single ts `20260604T175726Z` |
| 4d-restore | `--tags restore` cross-cutting (SC4) | PASS* | Loki StartedAt `17:48:45 → 18:01:16` (writer stopped+restarted). *Succeeded only because G-01 workaround was already applied in scenario 1 |

## Evidence highlights

**UAT-V13-01 data-survival proof** (despite G-01 workaround):
- Step 2 captured: `trace_id: 47ac47b7804eac0ef04c6f906b25c1ea`, `run_id: 1780594240`, all 4 asserters ok
- Step 3 shared timestamp: `20260604T173059Z` propagated to all 4 tarballs (D-191)
- Step 7 (post-workaround) re-emitted the SAME identifiers from queries through Loki+Prometheus+Mimir+Tempo → data survived purge+restore across all 4 OTLP signal types

**SC4 cross-cutting tag claim proven empirically**:
- `--tags backup` (4d-backup): 4 tarballs at single shared timestamp `20260604T175726Z`
- `--tags restore` (4d-restore): writer-quiesce bracket fires + all 4 role restores complete

**D-188 amended identity-level safety proven empirically**:
- Scenario 2c: `--tags loki` without confirm still fails at the `[always]`-tagged gate BEFORE tag-filtering. Verbatim fail msg contract sentence intact.

**D-189 amended writer-quiesce lock proven empirically**:
- Scenario 4c: `--tags grafana` does NOT fire writer-stop (loki StartedAt identical before/after)
- Scenario 4d-restore: `--tags restore` DOES fire writer-stop (loki StartedAt 17:48:45 → 18:01:16)

## Gaps opened (tracked for follow-up)

### G-01: restore_docker.yml does not re-render writer configs with restored Garage S3 credentials

**Impact:** Restore round-trip is functionally broken without a manual `deploy_docker.yml --tags loki,tempo,mimir,garage` rerun after each restore. UAT-V13-01 is partially demonstrated (data did round-trip after workaround) but the operator contract "single playbook restore" is not honored.

**Fix-plan:** Add a writer-config-rerender step to `restore_docker.yml` after Garage restore + writer-restart. Recommended: re-invoke `include_role: name=<writer> tasks_from=main` for loki/tempo/mimir (idempotent re-render from restored s3-credentials).

**Target:** Phase 14.1 gap-closure plan, OR direct amendment to `playbooks/restore_docker.yml`.

### G-03: backup_continue_on_failure=true does not actually let remaining roles run after a host failure

**Impact:** The documented opt-in `backup_continue_on_failure=true` is functionally a no-op with single-host inventories (which is M1's only supported topology). Banner alt text fires but only roles up to the first failure run. OPS-V13-02 opt-in claim is unsubstantiated.

**Fix-plan:** In `backup_docker.yml`, wrap each per-role `include_role` in `block:/rescue:[meta: clear_host_errors]` when `backup_continue_on_failure: true`. Failed host gets re-added to subsequent task host lists.

**Target:** Phase 14.1 gap-closure plan, OR direct amendment to `playbooks/backup_docker.yml`.

## What this enables

Plans 14-01/02/03 shipped a working backup+restore pipeline for the happy path. This UAT proved the happy-path data round-trip works (with G-01 workaround) AND surfaced two real defects before milestone close. The Phase 15 doc cascade can proceed with the caveat that v1.3.0 release notes must document G-01 + G-03 (or block release until both are fixed via Phase 14.1).

## Deviations from plan

- **Methodology** (scenario 3a/3b): chmod 000 fault-injection in plan is ineffective on leviathan because the backup task runs as root. Pivoted to file-as-dir fault (`mv backups/prometheus backups/prometheus.SAVED && touch backups/prometheus`). Cleanup mirrors the inverse.
- **Frontmatter status**: chose `partial` (not `complete`) because 2 sub-scenarios failed. Consistent with the plan's "leave result: fail and open ## Gaps" directive.
- **--ask-vault-pass**: not used. Inventory `secrets.yml` is plaintext per Rock's "Plaintext for autonomous Claude-driven UAT runs" setup.

## Key files

- Updated: `.planning/phases/14-orchestrators-leviathan-human-uat/14-HUMAN-UAT.md` (status: partial, 9 pass / 2 fail, ## Gaps section opened)
- Logs captured: `/tmp/14uat/s{1-step{1..7},2a,2b,2c,3a,3a-v2,3b,4a,4b,4c,4dbackup,4drestore}.log` (~14 log files; transient, on workstation only)

## Commits

- `fdf84d6` — docs(14-04): ship 14-HUMAN-UAT.md skeleton -- 11 sub-scenarios pending live leviathan UAT
- `1801ae1` — test(14-04): live UAT round-trip on leviathan -- 9/11 pass, 2 gaps opened (G-01, G-03)
