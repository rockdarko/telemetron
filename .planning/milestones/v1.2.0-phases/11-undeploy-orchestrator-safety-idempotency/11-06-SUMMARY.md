---
phase: 11-undeploy-orchestrator-safety-idempotency
plan: "06"
subsystem: garage-bootstrap
tags: [garage, bootstrap, idempotency, gap-closure, G-01, D-146, D-112]
dependency_graph:
  requires:
    - roles/garage/tasks/bootstrap.yml (pre-patch Phase 8 file)
    - 11-HUMAN-UAT.md (G-01 workaround command embedded verbatim in fail msg)
    - 11-VERIFICATION.md (G-01 gap definition + root cause)
  provides:
    - roles/garage/tasks/bootstrap.yml (patched -- idempotent S3 key bootstrap against preserved metadata volumes)
  affects:
    - D-146 recovery story (conservative undeploy + redeploy now reuses orphan key)
    - 11-HUMAN-UAT.md scenarios 1 and 4b (unblocked -- no longer hit G-01 orphan key bug)
tech_stack:
  added: []
  patterns:
    - ansible regex_findall with multiline (?m) anchor for tabular CLI output parsing
    - Three-branch mutual-exclusivity gate pattern on garage_existing_telemetron_keys length
    - ansible.builtin.fail with operator-actionable multi-line msg including copy-paste workaround
key_files:
  created: []
  modified:
    - roles/garage/tasks/bootstrap.yml
decisions:
  - "Option A chosen (bootstrap-side idempotency) over Option B (uninstall-side key delete) per operator decision -- preserves D-146 data recovery story"
  - "regex_findall with (?m)^([0-9a-fA-F]+)\\s+<key_name>(?:\\s|$) extracts hex Key IDs from tabular `garage key list` output; | first safe in recovery branch (gated on length==1)"
  - "All three first-run steps 7d/7e/7f tightened together (not decoupled) to ensure they fire as a unit -- decoupling would risk step 7e/7f firing without 7d output"
  - "Task F (orphan-failure) uses ansible.builtin.fail with no ignore_errors, no notify -- halts play loudly so operator gets actionable error instead of opaque Garage 400 response"
metrics:
  duration: "3m"
  completed: "2026-05-30T08:21:43Z"
  tasks_completed: 4
  files_modified: 1
---

# Phase 11 Plan 06: G-01 Garage Orphan Key Idempotency Summary

Patched `roles/garage/tasks/bootstrap.yml` to make Garage S3 key creation idempotent against preserved metadata volumes -- closes 11-VERIFICATION.md gap G-01 and transitively unblocks 11-HUMAN-UAT.md scenarios 1 and 4b (G-02).

## What Was Built

Three new branches inserted into the D-112 S3 key bootstrap block in `roles/garage/tasks/bootstrap.yml`, between the existing step 7c (host-file credential load) and the bucket-create separator:

**Discovery (Tasks A + B):** `garage key list` probe queries Garage's preserved metadata for keys named `{{ garage_s3_key_name }}`; `regex_findall` with multiline anchor extracts matching hex Key IDs into `garage_existing_telemetron_keys` fact (list, empty = zero matches).

**First-run gate tightened (Tasks 7d/7e/7f):** All three steps now require `garage_existing_telemetron_keys | length == 0` in addition to `not garage_creds_file.stat.exists` -- preventing duplicate key creation when exactly one orphan key exists.

**Recovery branch (Tasks C + D + E):** When `length == 1` AND no host credentials file: extract existing key's secret via `garage key info --show-secret <KEY_ID>`, populate the same fact pair as the first-run branch, and persist to `{{ garage_s3_credentials_file }}` (mode 0600) so the next run takes the fast path. This is the D-146 data recovery story made executable.

**Orphan-failure branch (Task F):** When `length >= 2`: `ansible.builtin.fail` with `orphan key cleanup needed` in the message, plus the verbatim `garage key delete --yes <OLD_KEY_ID>` workaround command operators can copy-paste from PLAY OUTPUT.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Insert key-discovery step + tighten existing first-run gate | 5dc5fd5 | roles/garage/tasks/bootstrap.yml |
| 2 | Add recovery branch (single-key reuse) -- the D-146 executable path | 01399a0 | roles/garage/tasks/bootstrap.yml |
| 3 | Add orphan-failure branch (>=2 keys) with operator workaround in fail msg | 06047b8 | roles/garage/tasks/bootstrap.yml |
| 4 | End-to-end verification + tag consistency audit | (no file changes; all checks passed) | -- |

## Verification Results

All plan-level gates pass:

| Gate | Result |
|------|--------|
| `ansible-playbook playbooks/deploy_docker.yml --syntax-check` exits 0 | PASS |
| `grep -c 'garage_existing_telemetron_keys \| length == 0'` returns 3 | PASS (3) |
| `grep -c 'garage_existing_telemetron_keys \| length == 1'` returns 3 | PASS (3) |
| `grep -c 'garage_existing_telemetron_keys \| length >= 2'` returns 1 | PASS (1) |
| `grep -q 'garage key list'` | PASS |
| `grep -q 'garage key info --show-secret'` | PASS |
| `grep -q 'orphan key cleanup needed'` | PASS |
| `grep -q 'garage_existing_telemetron_keys'` | PASS |
| OLD `when: not garage_creds_file.stat.exists$` (end-of-line) absent | PASS |
| ASCII-only (D-25) | PASS |
| No TBD/FIXME/XXX debt markers | PASS |
| No `ignore_errors:` introduced (D-142) | PASS |
| No `notify:` introduced | PASS |
| Task ordering: 1-6, 7a-7c, NEW discovery, 7d-7f (tightened), NEW recovery, NEW orphan-failure, 8-10 | PASS |
| Only `roles/garage/tasks/bootstrap.yml` modified | PASS |

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None. The patch is fully wired. Live UAT re-runs on leviathan (11-HUMAN-UAT.md scenarios 1 and 4b) are deferred to the operator per D-163 sequential approval pattern and encoded as `kind: live-host` items in the plan frontmatter. Those are behavioural confirmation steps, not stubs.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes beyond what is covered by the plan's `<threat_model>` block (T-11-06-01 through T-11-06-05 + T-11-06-SC). The `garage key info --show-secret` stdout (T-11-06-03) has the same exposure profile as the existing step 7d `garage key create` stdout -- both were already accepted by Phase 8.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `roles/garage/tasks/bootstrap.yml` exists | FOUND |
| `11-06-SUMMARY.md` exists | FOUND |
| Commit 5dc5fd5 (Task 1) | FOUND |
| Commit 01399a0 (Task 2) | FOUND |
| Commit 06047b8 (Task 3) | FOUND |
| `garage key list` in bootstrap.yml | FOUND |
| `garage key info --show-secret` in bootstrap.yml | FOUND |
| `orphan key cleanup needed` in bootstrap.yml | FOUND |
