---
phase: 11-undeploy-orchestrator-safety-idempotency
verified: 2026-05-29T00:00:00Z
updated: 2026-05-30T03:40:00Z
status: gaps_found
score: 6/6 must-haves structurally verified; 5/7 live UAT scenarios pass; 1 cross-phase gap blocks D-146 recovery on conservative undeploy
overrides_applied: 0
gaps:
  - id: G-01
    summary: "Orphan Garage S3 key on conservative undeploy + redeploy (Phase 8 bootstrap.yml + Phase 10 garage uninstall.yml interaction)"
    blocks_success_criteria: [SC-1, SC-6]
    blocks_scenarios: [1, 4b]
    detail: "garage uninstall.yml removes /opt/telemetron/garage/s3-credentials while telemetron_garage_meta volume is preserved (correct per D-141). On redeploy, bootstrap.yml creates a NEW telemetron key without checking for an existing one in the metadata, producing two keys with the same name. Subsequent `garage bucket allow --key telemetron` fails with `GetKeyInfo InvalidRequest (400): Bad request: 2 matching keys` on 5 buckets (loki-chunks, tempo-traces, mimir-blocks, mimir-ruler, mimir-alerts)."
    workaround: "docker exec telemetron-garage /garage key delete --yes <OLD_KEY_ID> before retrying deploy"
    fix-location: "Phase 8 roles/garage/tasks/bootstrap.yml -- make key creation idempotent (check `garage key list` for existing telemetron key before creating)"
    fix-plan: "Track as Phase 11 gap-closure plan (e.g. 11-06-PLAN.md) that patches roles/garage/tasks/bootstrap.yml -- the planner will revisit Phase 8 territory but the artifact lands in this phase's directory"
human_verification:
  - test: "Conservative undeploy on leviathan (SC-1 + SC-2 happy path + D-146 recovery)"
    expected: "`ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` exits with `failed=0`; `docker ps -a | grep telemetron` returns nothing; `docker network ls | grep telemetron` returns nothing; `docker volume ls | grep telemetron_` returns the same volume list as before; immediate `playbooks/deploy_docker.yml` redeploy succeeds; smoke_test.yml round-trip passes within 60s; Grafana panels show OLD pre-undeploy data (D-146 recovery proven)."
    why_human: "Requires running ansible against a live Docker host (leviathan). Verifier cannot exercise docker_network state=absent and docker_container teardown without inventory + SSH + Docker daemon. Encoded as 11-HUMAN-UAT.md scenario 1."
  - test: "Back-to-back undeploy idempotency on leviathan (SC-3, OPS-01)"
    expected: "Run `ansible-playbook ... undeploy_docker.yml` twice in succession on a clean host. Second run's PLAY RECAP shows `changed=0`; `failed=0` in both runs."
    why_human: "Idempotency assertion requires live host Docker daemon state. Verifier cannot simulate the PLAY RECAP `changed=0` without running it. Encoded as 11-HUMAN-UAT.md scenario 2."
  - test: "Partial-deploy idempotency on leviathan (SC-3 second clause, D-164)"
    expected: "With stack running, `ssh leviathan docker rm -f telemetron-fluentbit telemetron-opentelemetry telemetron-alertmanager`, then run undeploy. PLAY RECAP `failed=0`; no spurious `changed=true` on pre-removed containers; remaining containers cleanly removed."
    why_human: "Requires arbitrary docker daemon state on a live host. Encoded as 11-HUMAN-UAT.md scenario 3."
  - test: "telemetron_purge_data=true on leviathan (SC-4 + part of SC-5)"
    expected: "With `--extra-vars 'telemetron_purge_data=true'`, PLAY-start banner displays the category description; PLAY OUTPUT shows 8 `WARNING: irreversible -- <role> purge_data:` lines (one per volume-bearing role; garage emits a single line listing both meta + data comma-separated); `docker volume ls | grep telemetron_` returns 0 telemetron-prefixed volumes; redeploy succeeds; smoke_test.yml after redeploy shows EMPTY datasources (fresh buckets); `failed=0`. Encoded as 11-HUMAN-UAT.md scenario 4a."
    why_human: "WARNING-banner inspection and post-purge volume-list check require running ansible against a live Docker host."
  - test: "telemetron_purge_host_dirs=true on leviathan (SC-5 first clause)"
    expected: "With `--extra-vars 'telemetron_purge_host_dirs=true'`, PLAY OUTPUT shows `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)`; `ssh leviathan ls /opt/telemetron` returns 'No such file or directory'; Garage S3 credentials file at `/opt/telemetron/garage/s3-credentials` specifically gone; redeploy recreates the tree cleanly. Encoded as 11-HUMAN-UAT.md scenario 4b."
    why_human: "Host-filesystem state verification requires SSH + live host. Verifier cannot exercise `ansible.builtin.file: state=absent` against /opt/telemetron without a target host."
  - test: "telemetron_purge_images=true on leviathan (SC-5 second clause)"
    expected: "With `--extra-vars 'telemetron_purge_images=true'`, PLAY OUTPUT shows 11 WARN lines (every role except nfsd per D-156); `ssh leviathan docker images` shows 0 rows for the pinned tags; sibling-image edge case proven (grafana removes curlimages/curl:8.10.1 OR loki does, and the other's `failed_when:false` skip-and-warn fires correctly); redeploy re-pulls images; `failed=0`. Encoded as 11-HUMAN-UAT.md scenario 4c."
    why_human: "docker_image state=absent + failed_when:false skip-and-warn behaviour can only be observed in PLAY OUTPUT against a live Docker daemon. Verifier cannot simulate the shared-image race condition without running the playbook."
  - test: "All 3 purge flags combined + scratch-rebuild on leviathan (SC-6, OPS-02 fresh-start)"
    expected: "With `--extra-vars 'telemetron_purge_data=true telemetron_purge_host_dirs=true telemetron_purge_images=true'`, host is rebuilt FROM SCRATCH on next deploy; new Garage S3 credentials auto-generated by bootstrap; empty buckets; smoke_test.yml after fresh deploy passes within 60s budget; `failed=0`. Encoded as 11-HUMAN-UAT.md scenario 5."
    why_human: "Full lifecycle round-trip across an irreversible operation requires live-host execution. Verifier cannot prove the scratch-rebuild story without the target Docker daemon."
---

# Phase 11: Undeploy Orchestrator + Safety + Idempotency Verification Report

**Phase Goal:** Operators can run a single `ansible-playbook playbooks/undeploy_docker.yml` command against their inventory to cleanly remove the Telemetron stack from a Docker host, with conservative defaults that preserve data and opt-in flags for irreversible cleanup.

**Verified:** 2026-05-29 (structural) + 2026-05-30 (live UAT on leviathan)
**Status:** gaps_found
**Re-verification:** No -- initial verification with live UAT round 1

## Live UAT Results (2026-05-30, leviathan)

| Scenario | Result | Detail |
|----------|--------|--------|
| 1. Conservative undeploy + redeploy | FAIL | Undeploy clean (ok=37 changed=23 failed=0). Redeploy hits G-01 orphan key bug. |
| 2. Back-to-back undeploy idempotency | PASS | Run 1: changed=23. Run 2: changed=0 failed=0. |
| 3. Partial-deploy idempotency | PASS | After manual removal of 3 containers, undeploy: changed=20 failed=0 (3 fewer = pre-removed no-ops). |
| 4a. purge_data=true + redeploy | PASS | 8 WARN lines, 0 telemetron volumes post-purge, smoke test ok=9 failed=0. Fresh metadata = no orphan key. |
| 4b. purge_host_dirs=true + redeploy | SKIPPED | Would hit G-01 (same metadata-preserved path as scenario 1). |
| 4c. purge_images=true + redeploy | PASS (workaround) | 11 WARN lines, sibling-image edge case verified. Required G-01 workaround for redeploy. |
| 5. All 3 flags + scratch deploy | PASS | Walk-in-cold proven: 0 volumes/host-dirs/images post-purge, fresh deploy ok=148, smoke ok=9. |

**Tally:** 5 pass, 1 fail (G-01), 1 skip (G-01).

## Goal Achievement

### Observable Truths (ROADMAP Phase 11 Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| SC-1 | `ansible-playbook playbooks/undeploy_docker.yml` removes 12 containers + `telemetron` bridge network; reverse-deploy order | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | Orchestrator exists (304 lines), `--syntax-check` passes, `--list-tasks` enumerates 27 tasks in reverse-deploy order (nfsd -> karma -> grafana -> alertmanager -> fluentbit -> prometheus -> opentelemetry -> node_exporter -> mimir -> tempo -> loki -> garage), `community.docker.docker_network state=absent` present in post_tasks. Live-host container/network removal NOT verifiable without leviathan. |
| SC-2 | Default run preserves all `telemetron_*` named Docker volumes | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | All 11 per-role `purge.yml` files gate the `docker_volume state=absent` task on `telemetron_purge_data \| default(false) \| bool` (D-153 belt-and-suspenders); orchestrator gates each per-role purge include on `telemetron_purge_data \| bool or telemetron_purge_images \| bool`; default vars block sets all 3 flags to `false`. Conservative-default invariant is statically provable; live `docker volume ls` confirmation requires live host. |
| SC-3 | Back-to-back undeploy = `changed=0`; partial-deploy = `failed=0` | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | Every destructive task uses `state=absent` (D-141 trust); `community.docker.docker_network state=absent` is idempotent on missing network; `docker_image state=absent` uses `failed_when: false` (D-154) so in-use images don't fail the run. PLAY RECAP measurement requires live execution -- encoded as 11-HUMAN-UAT.md scenarios 2 + 3. |
| SC-4 | `telemetron_purge_data=true` removes all volumes; each irreversible flag emits "WARNING: irreversible" pre-task | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | All 8 volume-bearing per-role purge.yml files contain literal `WARNING: irreversible -- <role> purge_data:` (verified by grep); garage emits a single comma-separated line for meta + data (D-152); orchestrator post_tasks emits `WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)`. PLAY-output banner verification requires live ansible run. |
| SC-5 | `--extra-vars telemetron_purge_host_dirs=true` removes /opt/telemetron tree + s3-credentials; `telemetron_purge_images=true` removes pinned image tags only | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | Orchestrator post_tasks: `ansible.builtin.file: state=absent path={{ telemetron_config_root \| default('/opt/telemetron') }}` gated on `telemetron_purge_host_dirs`; per-role purge.yml uses `{{ <role>_image }}:{{ <role>_image_tag }}` (pinned tags only, NOT prefix wildcards); `failed_when: false` on the image task means sibling-image races (curlimages/curl) skip-and-warn rather than fail. Live `ls /opt/telemetron` and `docker images` verification require live host. |
| SC-6 | Round-trip: undeploy then deploy succeeds; purge_data round-trip starts fresh | STRUCTURAL PASS, BEHAVIOUR HUMAN-NEEDED | Symmetric inverse: deploy creates bridge network in pre_tasks, undeploy removes in post_tasks (D-150). Garage volume removal (purge_data) triggers Phase 8 D-112 first-run branch on next deploy. Round-trip cannot be statically proven; encoded as 11-HUMAN-UAT.md scenarios 1 (default) + 5 (purge_data fresh-start). |

**Score:** 6/6 success criteria structurally verified; 6/6 require live-leviathan UAT for behavioural confirmation (encoded in 11-HUMAN-UAT.md).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `playbooks/undeploy_docker.yml` | M1 undeploy orchestrator, ≥120 lines, reverse-deploy order, 3 opt-in flags, post_tasks network + host_dirs | VERIFIED | 304 lines; `--syntax-check` passes; 12 `tasks_from: uninstall` + 11 `tasks_from: purge`; reverse-deploy order confirmed by `--list-tasks`; CR-01 + CR-02 fixes applied (commits cf3a511, ddad530) |
| `roles/karma/tasks/purge.yml` | Image-only, 3 tasks, D-159 WARN | VERIFIED | 56 lines, 3 tasks, contains `WARNING: irreversible -- karma purge_images:` and `failed_when: false`, no telemetron_purge_data section, no notify, no ignore_errors |
| `roles/node_exporter/tasks/purge.yml` | Image-only, 3 tasks | VERIFIED | 55 lines, 3 tasks, role tag `node_exporter` (underscore), D-159 WARN present |
| `roles/opentelemetry/tasks/purge.yml` | Image-only, 3 tasks; no docker.sock touches | VERIFIED | 58 lines, 3 tasks, no docker.sock references |
| `roles/alertmanager/tasks/purge.yml` | Single-volume + single-image, 5 tasks | VERIFIED | 78 lines, 5 tasks, references `{{ alertmanager_data_volume }}` |
| `roles/fluentbit/tasks/purge.yml` | Buffer-volume + image, 5 tasks | VERIFIED | 90 lines, 5 tasks, references `{{ fluentbit_buffer_volume }}` (D-50); no `fluentbit_data_volume` references |
| `roles/mimir/tasks/purge.yml` | Single-volume + single-image, 5 tasks | VERIFIED | 78 lines, 5 tasks, references `{{ mimir_data_volume }}` |
| `roles/prometheus/tasks/purge.yml` | TSDB-volume + single-image, 5 tasks | VERIFIED | 78 lines, 5 tasks, references `{{ prometheus_data_volume }}` |
| `roles/tempo/tasks/purge.yml` | Single-volume + single-image, 5 tasks | VERIFIED | 78 lines, 5 tasks, references `{{ tempo_data_volume }}` |
| `roles/garage/tasks/purge.yml` | Two-volume loop + single image, 5 tasks (D-152) | VERIFIED | 125 lines, 5 tasks, single `loop:` over `[garage_meta_volume, garage_data_volume]`, WARN lists both names comma-separated |
| `roles/grafana/tasks/purge.yml` | Single-volume + two-image loop, 5 tasks | VERIFIED | 114 lines, 5 tasks, single docker_image `loop:` over `[grafana_image, grafana_curl_image]`, `failed_when: false` for shared-curl tolerance |
| `roles/loki/tasks/purge.yml` | Single-volume + two-image loop, 5 tasks | VERIFIED | 114 lines, 5 tasks, mirrors grafana shape with loki substitutions |
| `.planning/phases/11-undeploy-orchestrator-safety-idempotency/11-HUMAN-UAT.md` | 7-scenario UAT checklist (1, 2, 3, 4a, 4b, 4c, 5) | VERIFIED | Frontmatter present (status partial, source [11-VERIFICATION.md], started/updated timestamps); 7 numbered scenarios; summary tally total=7/passed=0/pending=7; ## Gaps section present; ASCII-only confirmed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `playbooks/undeploy_docker.yml` tasks: block | Each `roles/<role>/tasks/purge.yml` | `ansible.builtin.include_role` with `tasks_from: purge` | WIRED | 11 `tasks_from: purge` references; each per-role include OR-gated on `telemetron_purge_data \| bool or telemetron_purge_images \| bool`; all 11 target files exist on disk |
| `playbooks/undeploy_docker.yml` tasks: block | Each `roles/<role>/tasks/uninstall.yml` | `ansible.builtin.include_role` with `tasks_from: uninstall` | WIRED | 12 `tasks_from: uninstall` references (all 12 roles including nfsd which is conditionally gated on `enable_nfsd`); each target file shipped in Phase 10 |
| `playbooks/undeploy_docker.yml` post_tasks | `telemetron` Docker bridge network | `community.docker.docker_network: state=absent name={{ telemetron_network }}` | WIRED | Single task with `tags: [network]` (CR-01 fix dropped `tags: always`; commit cf3a511); inverse of deploy's pre_tasks network creation |
| `playbooks/undeploy_docker.yml` post_tasks | `/opt/telemetron` parent host tree | `ansible.builtin.file: state=absent path={{ telemetron_config_root \| default('/opt/telemetron') }}` | WIRED | Gated on `telemetron_purge_host_dirs \| default(false) \| bool`; preceded by D-145 WARN debug task; CR-02 fix dropped `tags: always` on both tasks; inventory-tunable path (NOT hardcoded) |
| Each `purge.yml` | `roles/<role>/defaults/main.yml` variables | Auto-loaded role defaults via `include_role` | WIRED | Spot-checked: karma uses `{{ karma_image }}/{{ karma_image_tag }}`, garage uses `{{ garage_meta_volume }}/{{ garage_data_volume }}`, grafana uses `{{ grafana_image }}/{{ grafana_curl_image }}`, fluentbit uses `{{ fluentbit_buffer_volume }}` — all variable references resolved correctly |

### Behavioural Spot-Checks

| Behaviour | Command | Result | Status |
|-----------|---------|--------|--------|
| Playbook YAML parses cleanly | `ansible-playbook playbooks/undeploy_docker.yml --syntax-check` | `playbook: playbooks/undeploy_docker.yml` (no errors; only inventory-missing warnings) | PASS |
| Task graph is well-formed and ordered | `ansible-playbook playbooks/undeploy_docker.yml --list-tasks` | 27 tasks in reverse-deploy order (nfsd -> karma -> ... -> garage), 11 purge gates, post_tasks emit network + host_dirs in correct order | PASS |
| Bridge-network removal task is no longer `tags: always` (CR-01 regression check) | Inspected `playbooks/undeploy_docker.yml` lines 284-289 | `tags: [network]` only -- `always` removed per commit cf3a511 | PASS |
| `/opt/telemetron` removal tasks are no longer `tags: always` (CR-02 regression check) | Inspected `playbooks/undeploy_docker.yml` lines 294-303 | Both the WARN debug and `ansible.builtin.file: state=absent` task have no `tags:` line; gate is `when: telemetron_purge_host_dirs \| default(false) \| bool` only (per commit ddad530) | PASS |
| All 11 per-role purge.yml files exist on disk | `find roles -path '*/tasks/purge.yml' -type f \| sort` | Lists 11 files: alertmanager, fluentbit, garage, grafana, karma, loki, mimir, node_exporter, opentelemetry, prometheus, tempo | PASS |
| nfsd correctly has NO purge.yml (D-156) | `test ! -f roles/nfsd/tasks/purge.yml` | Confirmed absent; orchestrator does NOT include_role tasks_from: purge for nfsd | PASS |
| Live undeploy on leviathan | `ansible-playbook -i inventory/leviathan playbooks/undeploy_docker.yml` | SKIP (would consume live UAT scenarios; deferred to 11-HUMAN-UAT.md) | SKIP |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| No conventional `scripts/*/tests/probe-*.sh` paths declared in PLANs | `find scripts -path '*/tests/probe-*.sh' -type f 2>/dev/null` | Not declared by any phase 11 PLAN | N/A |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| **UNDEPLOY-01** | 11-04 (`requirements:` frontmatter) | Single-entry undeploy playbook with `--ask-vault-pass` + `--tags <role>` UX | STRUCTURAL PASS, LIVE-HOST HUMAN-NEEDED | `playbooks/undeploy_docker.yml` exists at repo root; same `hosts: telemetron`, same vault flag UX, per-role single-tag scoping confirmed by grep; 12 uninstall + 11 purge includes wired in reverse-deploy order. Live `failed=0` confirmation requires leviathan UAT scenario 1. |
| **PURGE-01** | 11-01, 11-02, 11-03, 11-04 (`requirements:`) | Conservative-by-default: preserve volumes, host dirs, images | STRUCTURAL PASS, LIVE-HOST HUMAN-NEEDED | All 3 purge flags default to `false` in orchestrator vars: block; orchestrator-level OR-gate AND per-role belt-and-suspenders when-guards (D-153); single-discovery default-false invariant statically provable. `docker volume ls` confirmation requires leviathan UAT scenario 1. |
| **PURGE-02** | 11-01, 11-02, 11-03, 11-04 (`requirements:`) | 3 opt-in irreversible flags + D-159 WARN messages | STRUCTURAL PASS, LIVE-HOST HUMAN-NEEDED | Three flags wired: `telemetron_purge_data`, `telemetron_purge_host_dirs`, `telemetron_purge_images`; D-159 `WARNING: irreversible --` prefix grep-verified in every per-role purge.yml; `/opt/telemetron/garage/s3-credentials` covered by parent-tree `file: state=absent`. PLAY-output WARN inspection requires leviathan UAT scenarios 4a/4b/4c. |
| **OPS-01** | 11-04, 11-05 (`requirements:`) | Back-to-back undeploy = `changed=0`; partial-deploy = `failed=0` | STRUCTURAL PASS, LIVE-HOST HUMAN-NEEDED | Every destructive task uses `state=absent` (D-141 trust); idempotency-by-design. PLAY RECAP `changed=0` measurement requires leviathan UAT scenarios 2 + 3. |
| **OPS-02** | 11-04, 11-05 (`requirements:`) | Undeploy followed by fresh deploy succeeds | STRUCTURAL PASS, LIVE-HOST HUMAN-NEEDED | Symmetric inverse with deploy (D-150 network lifecycle); D-146 garage recovery story preserved (Phase 10 garage uninstall.yml unchanged). Live round-trip requires leviathan UAT scenarios 1 (default) + 5 (purge_data fresh-start). |

All 5 requirement IDs declared in PLAN frontmatter map to REQUIREMENTS.md. No orphaned requirements. REQUIREMENTS.md still marks them "Pending" — this is correct because final acceptance requires the live UAT (11-HUMAN-UAT.md scenarios), not just code presence.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (none) | grep for `TBD\|FIXME\|XXX` across all 13 phase-11-modified files | — | No debt markers found |
| (none) | grep for `ignore_errors` across all 11 purge.yml files | — | None present (D-154 `failed_when: false` used instead, as designed) |
| (none) | grep for `notify:` across all 11 purge.yml files | — | None present (D-142 destruction paths fire no handlers) |
| (none) | grep for non-ASCII characters across playbook + 11 purge.yml + 11-HUMAN-UAT.md | — | All files are ASCII-only (D-25 enforced) |
| (none) | grep for sub-tag pollution (`tags:.*-(uninstall\|purge\|data\|image)`) | — | None found (D-133 single-tag rule enforced) |

### Human Verification Required

All 6 ROADMAP Phase 11 Success Criteria require live-leviathan execution to confirm behavioural outcomes. The structural / static layer is fully verified; the behavioural / runtime layer is encoded in `11-HUMAN-UAT.md` (7-scenario checklist already shipped per Plan 11-05). Each scenario in the checklist maps cleanly to one or more Success Criteria:

| 11-HUMAN-UAT.md scenario | Covers SC | Covers REQ |
|---------------------------|-----------|------------|
| 1. Conservative undeploy + redeploy + D-146 recovery | SC-1, SC-2, SC-6 | UNDEPLOY-01, PURGE-01, OPS-02 |
| 2. Back-to-back idempotency | SC-3 (first clause) | OPS-01 |
| 3. Partial-deploy idempotency (D-164) | SC-3 (second clause) | OPS-01 |
| 4a. telemetron_purge_data=true + redeploy | SC-4, SC-5 (volumes) | PURGE-02 |
| 4b. telemetron_purge_host_dirs=true + redeploy | SC-5 (host dirs incl. s3-credentials) | PURGE-02 |
| 4c. telemetron_purge_images=true + redeploy | SC-5 (images) | PURGE-02 |
| 5. All 3 flags combined + scratch rebuild | SC-6 (fresh-start) | OPS-02 (second clause) |

See `human_verification:` frontmatter above for the full pass/fail criteria of each scenario.

### Gaps Summary

**No structural gaps.** The undeploy orchestrator exists, parses cleanly, lists tasks in correct reverse-deploy order, and wires all 12 uninstall + 11 purge includes (nfsd correctly has no purge per D-156). The two critical findings from `11-REVIEW.md` (CR-01: `tags: always` on bridge-network removal; CR-02: `tags: always` on `/opt/telemetron` parent-tree removal) were resolved in commits `cf3a511` and `ddad530` respectively, and verified by re-inspection of the playbook. The `--tags <role>` tag-scoping contract advertised in the orchestrator header is now structurally consistent.

**All remaining acceptance is live-host behavioural.** The Phase 11 goal — "Operators can run a single `ansible-playbook playbooks/undeploy_docker.yml` command [...] with conservative defaults [...] and opt-in flags for irreversible cleanup" — is structurally satisfied by the codebase and conditional on live UAT pass. Phase 12 (Documentation Cascade) is unblocked from a code perspective; final REQUIREMENTS.md status changes from "Pending" -> "Complete" should wait until the 7-scenario UAT is executed against leviathan.

---

_Verified: 2026-05-29_
_Verifier: Claude (gsd-verifier)_
