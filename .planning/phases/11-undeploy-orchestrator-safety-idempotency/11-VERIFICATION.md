---
phase: 11-undeploy-orchestrator-safety-idempotency
verified: 2026-05-29T00:00:00Z
updated: 2026-05-30T12:00:00Z
status: human_needed
score: 6/6 must-haves structurally verified; G-01 structurally closed by commit 5eb9833; 2 live-host UAT scenarios pending
overrides_applied: 0
gaps: []
re_verification:
  previous_status: gaps_found
  previous_score: 6/6 structural (5/7 live UAT; 1 gap)
  gaps_closed:
    - "G-01: Orphan Garage S3 key on conservative undeploy + redeploy -- roles/garage/tasks/bootstrap.yml patched in commits 5dc5fd5, 01399a0, 06047b8, 85a6de7, 5eb9833 (CR-11-06-01 regex fix + WR-11-06-01 no_log fix)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Conservative undeploy + redeploy on leviathan (SC-1 + SC-2 + SC-6; D-146 recovery + G-01 closure proof)"
    expected: "`ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` (no purge flags) exits with `failed=0`; `docker ps -a | grep telemetron` returns nothing; `docker network ls | grep telemetron` returns nothing; `docker volume ls | grep telemetron_` returns the same volume list as before; immediate `playbooks/deploy_docker.yml` redeploy succeeds WITHOUT the OLD_KEY delete workaround; `garage : Allow S3 key on Garage buckets` succeeds on all 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts); `playbooks/smoke_test.yml` round-trip passes within 60s; Grafana panels show OLD pre-undeploy data (D-146 recovery proven; G-01 behaviourally closed)."
    why_human: "Requires running Ansible against a live Docker host (leviathan) with a preserved garage_meta volume containing exactly one orphan telemetron key. The recovery branch (bootstrap.yml Tasks C/D/E) and the G-01 fix can only be exercised with the actual Docker daemon + Garage container + preserved metadata volume. Encoded as 11-HUMAN-UAT.md scenario 1 (reset to pending)."
  - test: "telemetron_purge_host_dirs=true + redeploy on leviathan (SC-5 first clause; G-02 closure)"
    expected: "`ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --extra-vars 'telemetron_purge_host_dirs=true'` exits `failed=0`; PLAY OUTPUT shows `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)`; `ssh leviathan ls /opt/telemetron` returns 'No such file or directory'; Garage S3 credentials file at `/opt/telemetron/garage/s3-credentials` specifically gone; immediate redeploy: bootstrap.yml recovery branch fires (host file absent, exactly one telemetron key in preserved metadata), reuses existing key's secret, persists to fresh `/opt/telemetron/garage/s3-credentials`; `bucket allow` succeeds on all 5 buckets; `playbooks/smoke_test.yml` passes; Grafana shows OLD data; `failed=0`."
    why_human: "Host-filesystem state verification requires SSH + live host. The recovery branch triggered by purge_host_dirs (host file removed, metadata volume preserved) is the primary path that proves G-01 is behaviourally fixed for this scenario. Cannot be exercised without a live Docker host. Encoded as 11-HUMAN-UAT.md scenario 4b (reset to pending)."
  - test: "Back-to-back undeploy idempotency on leviathan (SC-3, OPS-01)"
    expected: "Run `ansible-playbook ... undeploy_docker.yml` twice in succession on a clean host. Second run's PLAY RECAP shows `changed=0`; `failed=0` in both runs."
    why_human: "Idempotency assertion requires live host Docker daemon state. Cannot simulate PLAY RECAP `changed=0` without running it. Previously PASSED (2026-05-30); re-run only needed if regression suspected. Encoded as 11-HUMAN-UAT.md scenario 2."
  - test: "Partial-deploy idempotency on leviathan (SC-3 second clause, D-164)"
    expected: "With stack running, `ssh leviathan docker rm -f telemetron-fluentbit telemetron-opentelemetry telemetron-alertmanager`, then run undeploy. PLAY RECAP `failed=0`; no spurious `changed=true` on pre-removed containers; remaining containers cleanly removed."
    why_human: "Requires arbitrary docker daemon state on a live host. Previously PASSED (2026-05-30). Encoded as 11-HUMAN-UAT.md scenario 3."
  - test: "telemetron_purge_data=true on leviathan (SC-4 + part of SC-5)"
    expected: "With `--extra-vars 'telemetron_purge_data=true'`, PLAY-start banner displays the category description; PLAY OUTPUT shows 8 `WARNING: irreversible -- <role> purge_data:` lines; `docker volume ls | grep telemetron_` returns 0 telemetron-prefixed volumes; redeploy succeeds; smoke_test.yml after redeploy shows EMPTY datasources; `failed=0`."
    why_human: "WARNING-banner inspection and post-purge volume-list check require running Ansible against a live Docker host. Previously PASSED (2026-05-30). Encoded as 11-HUMAN-UAT.md scenario 4a."
  - test: "telemetron_purge_images=true on leviathan (SC-5 second clause)"
    expected: "With `--extra-vars 'telemetron_purge_images=true'`, PLAY OUTPUT shows 11 WARN lines; `ssh leviathan docker images` shows 0 rows for the pinned tags; sibling-image edge case verified; redeploy re-pulls images; `failed=0`."
    why_human: "docker_image state=absent + failed_when:false skip-and-warn behaviour can only be observed in PLAY OUTPUT against a live Docker daemon. Previously PASSED (with workaround, 2026-05-30). Encoded as 11-HUMAN-UAT.md scenario 4c."
  - test: "All 3 purge flags combined + scratch-rebuild on leviathan (SC-6, OPS-02 fresh-start)"
    expected: "With `--extra-vars 'telemetron_purge_data=true telemetron_purge_host_dirs=true telemetron_purge_images=true'`, host rebuilt FROM SCRATCH on next deploy; new Garage S3 credentials auto-generated; empty buckets; smoke_test.yml passes within 60s; `failed=0`."
    why_human: "Full lifecycle round-trip across an irreversible operation requires live-host execution. Previously PASSED (2026-05-30). Encoded as 11-HUMAN-UAT.md scenario 5."
---

# Phase 11: Undeploy Orchestrator + Safety + Idempotency Verification Report

**Phase Goal:** Operators can run a single `ansible-playbook playbooks/undeploy_docker.yml` command against their inventory to cleanly remove the Telemetron stack from a Docker host, with conservative defaults that preserve data and opt-in flags for irreversible cleanup.

**Verified:** 2026-05-29 (structural) + 2026-05-30 (live UAT round 1) + 2026-05-30 (re-verification post-gap-closure)
**Status:** human_needed
**Re-verification:** Yes — after G-01 gap closure (commit 5eb9833, plan 11-06)

---

## Historical Record: Initial Verification (2026-05-29 + 2026-05-30 UAT Round 1)

### Live UAT Results (2026-05-30, leviathan — round 1)

| Scenario | Result | Detail |
|----------|--------|--------|
| 1. Conservative undeploy + redeploy | FAIL | Undeploy clean (ok=37 changed=23 failed=0). Redeploy hits G-01 orphan key bug. |
| 2. Back-to-back undeploy idempotency | PASS | Run 1: changed=23. Run 2: changed=0 failed=0. |
| 3. Partial-deploy idempotency | PASS | After manual removal of 3 containers, undeploy: changed=20 failed=0 (3 fewer = pre-removed no-ops). |
| 4a. purge_data=true + redeploy | PASS | 8 WARN lines, 0 telemetron volumes post-purge, smoke test ok=9 failed=0. Fresh metadata = no orphan key. |
| 4b. purge_host_dirs=true + redeploy | SKIPPED | Would hit G-01 (same metadata-preserved path as scenario 1). |
| 4c. purge_images=true + redeploy | PASS (workaround) | 11 WARN lines, sibling-image edge case verified. Required G-01 workaround for redeploy. |
| 5. All 3 flags + scratch deploy | PASS | Walk-in-cold proven: 0 volumes/host-dirs/images post-purge, fresh deploy ok=148, smoke ok=9. |

**Tally (round 1):** 5 pass, 1 fail (G-01), 1 skip (G-01).

---

## Re-verification: 2026-05-30 (post-gap-closure, commit 5eb9833)

### G-01 Gap Closure — Structural Verification

Gap G-01 was patched in `roles/garage/tasks/bootstrap.yml` across commits 5dc5fd5 (discovery + first-run gate tightening), 01399a0 (recovery branch), 06047b8 (orphan-failure branch), 85a6de7 (summary), and 5eb9833 (CR-11-06-01 regex widening + WR-11-06-01 no_log fix). All seven G-01 closure must-haves were verified against the codebase on 2026-05-30.

### G-01 Must-Have Verification Table

| # | Must-Have | File:Line | Status | Evidence |
|---|-----------|-----------|--------|---------|
| MH-1 | `garage key list` task present before step 7d | `bootstrap.yml:161-169` | VERIFIED | Task "List existing Garage S3 keys (G-01: detect orphan from preserved metadata)" at line 161; `command: /garage key list`; `register: garage_key_list_raw`; `changed_when: false`; tags `[garage, garage-bootstrap]` |
| MH-2 | `\S+` regex (not `[0-9a-fA-F]+`) — CR-11-06-01 fix | `bootstrap.yml:179` | VERIFIED | `regex_findall('(?m)^(\\S+)\\s+' ~ garage_s3_key_name ~ '(?:\\s|$)')`. Grep for `\S+` hits; grep for `[0-9a-fA-F]` returns zero matches. The old hex-only pattern is gone. |
| MH-3a | `length == 0` branch gates steps 7d/7e/7f | `bootstrap.yml:193,204,218` | VERIFIED | All three first-run tasks carry `when: not garage_creds_file.stat.exists and garage_existing_telemetron_keys \| length == 0`. Count = 3 (matches plan requirement). |
| MH-3b | `length == 1` recovery branch (Tasks C/D/E) | `bootstrap.yml:252,261,273` | VERIFIED | Three recovery tasks each gated on `when: not garage_creds_file.stat.exists and garage_existing_telemetron_keys \| length == 1`. Count = 3. |
| MH-3c | `length >= 2` orphan-failure branch (Task F) with `orphan key cleanup needed` | `bootstrap.yml:288-303` | VERIFIED | `ansible.builtin.fail` task; gate `when: garage_existing_telemetron_keys \| length >= 2`; `msg:` contains `orphan key cleanup needed` at line 291; contains `garage key delete --yes` operator workaround stub. Count = 1. |
| MH-4 | `no_log: true` on recovery key-info exec — WR-11-06-01 fix | `bootstrap.yml:251` | VERIFIED | Line 251: `  no_log: true` at 2-space indent (task-level directive, not a comment). Preceded by the WR-11-06-01 fix comment at lines 246-250. Applied to Task C (`Read existing telemetron key info (recovery branch)`). |
| MH-5 | `uninstall.yml` NOT modified by plan 11-06 | `git log` check | VERIFIED | `git log --oneline 5dc5fd5^..5eb9833 -- roles/garage/tasks/uninstall.yml` returns empty — zero commits touching `uninstall.yml` in the G-01 closure cycle. Last modification was commit `8dd06dd` (Phase 10). D-141 trust preserved. |
| MH-6 | `ansible-playbook playbooks/deploy_docker.yml --syntax-check` exits 0 | Syntax check run | VERIFIED | Exit code 0. Output: `playbook: playbooks/deploy_docker.yml` (only standard inventory warnings). |
| MH-7 | SC-1..SC-6 originals: no regression on undeploy_docker.yml + 11 purge.yml files | Regression check | VERIFIED | `playbooks/undeploy_docker.yml` is 303 lines (unchanged from prior verification); `--syntax-check` passes; 11 purge.yml files all present; no modifications to any of plans 11-01..11-05 artifacts in commits 5dc5fd5..5eb9833. |

### Mutual Exclusivity Proof

The three branches are correctly mutually exclusive given the `not garage_creds_file.stat.exists` fast-path guard:

- Fast path (host file present): `not garage_creds_file.stat.exists` = false → all three branch conditions are false → steps 7b/7c load credentials from file; no branch fires.
- First-run branch (no file, zero keys): `not exists AND length == 0` → only 7d/7e/7f fire.
- Recovery branch (no file, one key): `not exists AND length == 1` → only Tasks C/D/E fire.
- Orphan-failure branch (two or more keys): `length >= 2` → Task F fails regardless of creds file presence (intentional: two keys with the same name is an operator error whether the file exists or not).

The discovery probe (Task A) and fact-derivation step (Task B) run unconditionally every time (no `when:` clause), so `garage_existing_telemetron_keys` is always defined before any branch evaluates it. No undefined-variable risk.

### Tag Consistency Verification (All 6 New Tasks)

All six new tasks verified to carry `tags: [garage, garage-bootstrap]` matching existing bootstrap steps:

| New Task | Tag `garage` | Tag `garage-bootstrap` | Lines |
|----------|-------------|----------------------|-------|
| Task A: List existing Garage S3 keys | YES | YES | 161-169 |
| Task B: Set garage_existing_telemetron_keys fact | YES | YES | 171-183 |
| Task C: Read existing telemetron key info | YES | YES | 240-255 |
| Task D: Set Garage S3 credential facts from existing key info | YES | YES | 257-264 |
| Task E: Persist recovered Garage S3 credentials to host file | YES | YES | 266-276 |
| Task F: FAIL -- multiple telemetron keys in Garage metadata | YES | YES | 288-303 |

### Anti-Pattern Scan (bootstrap.yml post-patch)

| Pattern | Result |
|---------|--------|
| `TBD\|FIXME\|XXX` debt markers | None found |
| `ignore_errors:` | None found |
| `notify:` | None found |
| Non-ASCII characters | None found |

---

## Goal Achievement

### Observable Truths (ROADMAP Phase 11 Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| SC-1 | `ansible-playbook playbooks/undeploy_docker.yml` removes 12 containers + `telemetron` bridge network; reverse-deploy order | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | Orchestrator exists (303 lines), `--syntax-check` passes, 27 tasks in reverse-deploy order confirmed by prior verification. Live-host container/network removal: 11-HUMAN-UAT.md scenario 1 (reset to pending). |
| SC-2 | Default run preserves all `telemetron_*` named Docker volumes | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | All 11 per-role `purge.yml` files gate `docker_volume state=absent` on `telemetron_purge_data \| default(false) \| bool`; orchestrator-level OR-gate AND per-role belt-and-suspenders when-guards. Conservative-default invariant statically provable. |
| SC-3 | Back-to-back undeploy = `changed=0`; partial-deploy = `failed=0` | BEHAVIOURAL PASS (round 1) | PASSED in 2026-05-30 UAT (scenario 2: changed=0 on run 2; scenario 3: changed=20 failed=0 after 3 pre-removed containers). No regression since no undeploy.yml or purge.yml changes in plan 11-06. |
| SC-4 | `telemetron_purge_data=true` removes all volumes; each irreversible flag emits "WARNING: irreversible" pre-task | BEHAVIOURAL PASS (round 1) | PASSED in 2026-05-30 UAT (scenario 4a: 8 WARN lines, 0 volumes post-purge, smoke ok=9). |
| SC-5 | `telemetron_purge_host_dirs=true` removes /opt/telemetron tree + s3-credentials; `telemetron_purge_images=true` removes pinned image tags only | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | purge_images PASSED in 2026-05-30 UAT (scenario 4c, with workaround). purge_host_dirs (scenario 4b) PENDING — this is the primary G-01 behavioural-closure test. |
| SC-6 | Round-trip: undeploy then deploy succeeds; purge_data round-trip starts fresh | PARTIAL PASS | purge_data round-trip PASSED in round 1 (scenario 5: all-flags fresh deploy ok=148, smoke ok=9). Default conservative round-trip (scenario 1) PENDING G-01 behavioural re-run. |

**Score:** 6/6 success criteria structurally verified; SC-3, SC-4, and the purge_images half of SC-5 behaviourally confirmed in round 1; SC-1, SC-2, SC-6 (conservative path), and the purge_host_dirs half of SC-5 pending live leviathan re-run of scenarios 1 and 4b.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `roles/garage/tasks/bootstrap.yml` | G-01 patch: discovery probe + recovery branch + orphan-failure branch; `\S+` regex; `no_log: true` on key-info exec | VERIFIED | 358 lines; all 7 G-01 must-haves pass; `--syntax-check` clean; `uninstall.yml` untouched |
| `playbooks/undeploy_docker.yml` | M1 undeploy orchestrator, ≥120 lines, reverse-deploy order, 3 opt-in flags | VERIFIED | 303 lines; unchanged from prior verification; CR-01 + CR-02 fixes from prior cycle still present |
| All 11 per-role `purge.yml` files | D-152 / D-153 / D-154 / D-159 contract | VERIFIED | All 11 present (find roles -path '*/tasks/purge.yml' count = 11); unchanged from prior verification |
| `roles/garage/tasks/uninstall.yml` | NOT modified by plan 11-06 (D-141 trust) | VERIFIED | Zero commits touching this file in 5dc5fd5..5eb9833 range |
| `.planning/phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` | Scenarios 1 + 4b reset to pending; gaps G-01 + G-02 marked fix-shipped | TO BE UPDATED | Updated in this verification pass |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `bootstrap.yml` Task B (`garage_existing_telemetron_keys`) | `bootstrap.yml` step 7d `when:` clause | `garage_existing_telemetron_keys \| length == 0` tightened gate | VERIFIED — line 193 |
| `bootstrap.yml` Task C (`/garage key info --show-secret`) | `bootstrap.yml` Task D (set_fact from key info stdout) | `garage_key_info_result.stdout \| regex_search('Key ID:\\s*(\\S+)')` | VERIFIED — lines 240-264 |
| `bootstrap.yml` Task D (fact pair) | `bootstrap.yml` Task E (`Persist recovered Garage S3 credentials`) | `garage_s3_access_key_id` + `garage_s3_secret_key` facts consumed by copy content | VERIFIED — lines 257-276 |
| `bootstrap.yml` Task F | PLAY OUTPUT | `ansible.builtin.fail` msg containing `orphan key cleanup needed` + `garage key delete --yes` workaround | VERIFIED — lines 288-303 |

### Behavioural Spot-Checks (post-patch)

| Behaviour | Command | Result | Status |
|-----------|---------|--------|--------|
| deploy_docker.yml syntax valid | `ansible-playbook playbooks/deploy_docker.yml --syntax-check` | exit 0; `playbook: playbooks/deploy_docker.yml` | PASS |
| undeploy_docker.yml syntax valid | `ansible-playbook playbooks/undeploy_docker.yml --syntax-check` | exit 0; `playbook: playbooks/undeploy_docker.yml` | PASS |
| `\S+` regex in bootstrap.yml (CR-11-06-01 fix present) | `grep "regex_findall.*\\\\S+.*garage_s3_key_name"` | Line 179 hit | PASS |
| Old `[0-9a-fA-F]+` regex absent (CR-11-06-01 old pattern gone) | `grep "regex_findall.*\[0-9a-fA-F\]"` | No matches | PASS |
| `no_log: true` on recovery key-info task (WR-11-06-01 fix present) | `grep -n "no_log:" bootstrap.yml` | Line 251: `  no_log: true` (task-level directive) | PASS |
| Branch gate counts correct | `grep -c "length == 0"`, `grep -c "length == 1"`, `grep -c "length >= 2"` | 3, 3, 1 respectively | PASS |
| Old when: clause absent | `grep -c "when: not garage_creds_file.stat.exists$"` | 0 | PASS |
| `uninstall.yml` not touched by 11-06 commits | `git log 5dc5fd5^..5eb9833 -- roles/garage/tasks/uninstall.yml` | empty (no commits) | PASS |
| 11 purge.yml files present (no regression) | `find roles -path '*/tasks/purge.yml' -type f \| wc -l` | 11 | PASS |
| nfsd has no purge.yml (D-156) | `test ! -f roles/nfsd/tasks/purge.yml` | confirmed absent | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| **UNDEPLOY-01** | Single-entry undeploy playbook with `--ask-vault-pass` + `--tags <role>` UX | STRUCTURAL PASS, LIVE-HOST PENDING | `playbooks/undeploy_docker.yml` verified; scenario 1 re-run is the final live acceptance |
| **PURGE-01** | Conservative-by-default: preserve volumes, host dirs, images | STRUCTURAL PASS, LIVE-HOST PENDING | All 3 flags default false; belt-and-suspenders when-guards verified; scenario 1 re-run confirms volumes preserved |
| **PURGE-02** | 3 opt-in irreversible flags + D-159 WARN messages | PARTIAL PASS | purge_data (4a PASS), purge_images (4c PASS); purge_host_dirs (4b) pending scenario 4b re-run |
| **OPS-01** | Back-to-back undeploy = `changed=0`; partial-deploy = `failed=0` | BEHAVIOURAL PASS | Scenarios 2 + 3 passed in round 1; no regression since no undeploy surface changes in plan 11-06 |
| **OPS-02** | Undeploy followed by fresh deploy succeeds | PARTIAL PASS | purge_data + all-flags round-trips PASSED (scenarios 4a, 5). Conservative round-trip (scenario 1) pending G-01 behavioural confirmation |

### Human Verification Required

Scenarios 1 and 4b are the gate items — both require live-host execution and cannot be exercised statically. Scenarios 2, 3, 4a, 4c, 5 passed in the 2026-05-30 round 1 UAT; they are re-listed here for completeness but are not blockers.

#### BLOCKING: Scenario 1 — Conservative undeploy + redeploy (G-01 behavioural closure)

**Test:** On leviathan with the stack previously run (so `telemetron_garage_meta` volume has a key in its metadata): `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` (no purge flags), then immediately `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml`.

**Expected:** Undeploy: `failed=0`; containers and bridge network gone; all `telemetron_*` volumes preserved. Redeploy: NO manual `garage key delete` workaround needed; bootstrap.yml's recovery branch fires automatically; `garage : Allow S3 key on Garage buckets` succeeds on all 5 buckets; `playbooks/smoke_test.yml` passes within 60s; Grafana shows OLD pre-undeploy data (D-146 recovery proven).

**Why human:** Requires a live Docker host (leviathan) with a `telemetron_garage_meta` volume preserved from a prior undeploy cycle (the exact state that triggers the orphan-key path). The recovery branch (Tasks C/D/E in bootstrap.yml) can only be exercised against a real Garage container with existing metadata.

**Closes:** G-01 behaviourally + SC-1, SC-2, SC-6 (conservative path), UNDEPLOY-01, PURGE-01, OPS-02.

---

#### BLOCKING: Scenario 4b — purge_host_dirs=true + redeploy (G-02 closure)

**Test:** `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml --extra-vars 'telemetron_purge_host_dirs=true'`, then immediately `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml`.

**Expected:** Undeploy: `failed=0`; PLAY OUTPUT shows `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)`; `ssh leviathan ls /opt/telemetron` returns "No such file or directory"; `/opt/telemetron/garage/s3-credentials` specifically gone. Redeploy: bootstrap.yml recovery branch fires (host file gone, one orphan key in preserved `telemetron_garage_meta`); reuses existing key's secret; persists fresh credentials file; `bucket allow` succeeds on all 5 buckets; `playbooks/smoke_test.yml` passes; Grafana shows OLD data; `failed=0`.

**Why human:** Host-filesystem state verification requires SSH + live host. The recovery branch triggered by the host-dirs purge (credentials file removed, metadata volume preserved) is the G-01 fix proof for this specific scenario. Cannot be verified without a real target.

**Closes:** G-02 + SC-5 (purge_host_dirs half), PURGE-02 (host_dirs clause).

---

#### Non-blocking (already PASSED in round 1, re-run optional):

**Scenario 2** — Back-to-back idempotency: PASSED 2026-05-30 (changed=0 on second run). No regression risk (undeploy.yml unchanged in plan 11-06).

**Scenario 3** — Partial-deploy idempotency: PASSED 2026-05-30 (changed=20 failed=0 after 3 pre-removed containers).

**Scenario 4a** — purge_data=true + redeploy: PASSED 2026-05-30 (8 WARN lines, 0 volumes, smoke ok=9).

**Scenario 4c** — purge_images=true + redeploy: PASSED 2026-05-30 (11 WARN lines, sibling-image edge case verified, workaround no longer needed after G-01 fix).

**Scenario 5** — All 3 flags + scratch rebuild: PASSED 2026-05-30 (walk-in-cold proven, ok=148, smoke ok=9).

### Gaps Summary

**G-01 is structurally closed.** All seven must-haves are VERIFIED against the codebase. The `\S+` regex widening (CR-11-06-01 BLOCKER fix) and `no_log: true` on the recovery key-info exec (WR-11-06-01 WARNING fix) are both present in commit 5eb9833. The three branches are mutually exclusive. `uninstall.yml` is untouched per D-141. Syntax check passes. No debt markers introduced.

**Remaining acceptance is live-host behavioural.** Scenarios 1 and 4b must be re-run on leviathan to confirm G-01 is behaviourally closed (recovery branch fires, no manual key-delete workaround needed, Grafana shows OLD data). All other scenarios already have round-1 PASS results that are unaffected by plan 11-06 changes.

---

_Initial verification: 2026-05-29_
_Live UAT round 1: 2026-05-30_
_Re-verification (post-gap-closure): 2026-05-30_
_Verifier: Claude (gsd-verifier)_
