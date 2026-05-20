---
phase: 04-alert-plane
plan: 02
subsystem: infra
tags: [ansible, docker, alertmanager, prometheus, observability, gap-closure, bug-fix]

# Dependency graph
requires:
  - phase: 04-alert-plane
    provides: "Plan 04-01 alertmanager v0.32.1 role + D-64 Prometheus->AM wiring + D-58 doc cascade. 04-02 closes the two diagnosed UAT gaps in that ship."
provides:
  - "roles/alertmanager/tasks/verify.yml step 5 -- race-free via community.docker.docker_container_exec against the running AM container + Ansible until:/retries:/delay: polling (Bug 1 TIER 1)"
  - "roles/{prometheus,alertmanager}/tasks/main.yml -- meta: flush_handlers immediately before include_tasks: verify.yml so queued restart handlers fire before downstream verify probes (Bug 1 TIER 2 + Bug 2 belt-and-suspenders)"
  - "roles/{alertmanager,fluentbit,loki,mimir,opentelemetry,prometheus,tempo}/tasks/main.yml -- single-file rendered-config bind mounts collapsed to parent-directory bind mounts (Bug 2 FIX A; 12 surfaces -> 7 directory mounts; tempo container path moved from /etc/tempo.yaml to /etc/tempo/tempo.yaml as the only container-side path change)"
  - "roles/README.md -- new Gate 8 banning single-file rendered-config bind mounts; cites moby/moby#6011 (Bug 2 doc gate)"
  - "Auto-fix during UAT: roles/alertmanager/tasks/verify.yml steps 7 + 9 (amtool alert query + silence query) -- single-shot reads replaced with until: polling, same class of fix as step 5 (Rule 1 auto-fix)"
affects: [05-ui-plane, karma, grafana, all-future-role-ports]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parent-directory bind-mount convention for rendered config -- canonical Telemetron pattern from 04-02 forward; documented as Gate 8 in roles/README.md; mandatory for all future role ports"
    - "Ansible-native until:/retries:/delay: polling for in-container verify probes via community.docker.docker_container_exec -- replaces docker_container + auto_remove + while-loop one-shots whenever the probed condition is async (Prom dispatch, AM dispatch)"
    - "meta: flush_handlers immediately before include_tasks: verify.yml -- ensures restart handlers fire before downstream verify probes when a role notifies config-change handlers earlier in its own tasks/main.yml"

key-files:
  created:
    - ".planning/phases/04-alert-plane/04-02-SUMMARY.md"
  modified:
    - "roles/alertmanager/tasks/verify.yml (step 5 rewrite via docker_container_exec; auto-fix steps 7 + 9 with until: polling for amtool dispatch race)"
    - "roles/alertmanager/tasks/main.yml (meta:flush_handlers before include verify; bind mount refactored from single-file to parent-directory under mounts: block)"
    - "roles/prometheus/tasks/main.yml (meta:flush_handlers before include verify; 3 single-file bind mounts collapsed to 1 parent-directory mount)"
    - "roles/loki/tasks/main.yml (single-file bind mount refactored to parent-directory)"
    - "roles/tempo/tasks/main.yml (CLI flag updated to -config.file=/etc/tempo/tempo.yaml; single-file bind refactored to parent-directory)"
    - "roles/mimir/tasks/main.yml (single-file bind mount refactored to parent-directory)"
    - "roles/opentelemetry/tasks/main.yml (two single-file bind mounts collapsed to one parent-directory mount; docker.sock bind under mounts: block preserved byte-identical)"
    - "roles/fluentbit/tasks/main.yml (three single-file bind mounts collapsed to one parent-directory mount; buffer-volume + docker-logs-bind under mounts: block preserved byte-identical)"
    - "roles/README.md (new Gate 8 -- Parent-directory bind-mount convention citing moby/moby#6011)"
    - ".planning/phases/04-alert-plane/04-UAT.md (Tests 1 + 4 flipped from result:issue to result:pass with post-04-02 evidence; Summary updated total/passed=6/issues=0; Gaps annotated status:closed + closed_by:plan-04-02)"

key-decisions:
  - "Bug 1 TIER 1: Step 5 of alertmanager verify rewritten with community.docker.docker_container_exec against the running telemetron-alertmanager container (uses bundled busybox wget), polled via Ansible until:/retries:/delay:. Docker exec API returns exit code synchronously without container-lifecycle reaping -- ansible/ansible#45272 and #47673 cannot fire on this pattern."
  - "Bug 1 TIER 2 + Bug 2 belt-and-suspenders: meta:flush_handlers inserted immediately before include_tasks:verify.yml in prometheus + alertmanager tasks/main.yml. Single change covers both bugs (handler flush eliminates the verify-probes-stale-state class for Phase 4 scope)."
  - "Bug 2 FIX A: 12 single-file rendered-config bind-mount surfaces across 7 roles collapsed to 7 parent-directory bind mounts. Parent-directory mounts resolve directory entries on every open(), so post-rename new inodes are picked up immediately -- moby/moby#6011 (WONTFIX since 2014) is no longer reachable."
  - "Bug 2 special case (tempo): old mount point /etc/tempo.yaml was a top-level FILE inside the container's /etc; binding the host parent dir to /etc would have clobbered everything. Config moved into /etc/tempo/ subdirectory with the CLI flag updated to -config.file=/etc/tempo/tempo.yaml -- the ONLY container-side path change in the whole plan."
  - "Bug 2 doc gate: roles/README.md gets Gate 8 banning single-file rendered-config bind mounts. Future role ports inherit the convention by default; the gate cites moby/moby#6011 and the diagnosis debug doc."
  - "TIER 3 (the 9 remaining latent auto_remove sites in loki/tempo/mimir/prometheus/opentelemetry/fluentbit/node_exporter verify.yml files) DEFERRED. They are latent today (early-exit-0 in <10s normally) and only re-fire if another cross-role probe is added. Captured as Phase 5 readiness note pointing at .planning/debug/alertmanager-verify-prom-am-probe-auto-remove-race.md."
  - "Auto-fix during UAT (Rule 1): once Bug 1/2 were fixed and the play could execute the amtool sequence to completion, step 7 (alert query) and step 9 (silence query) revealed a pre-existing latent race -- amtool's `alert add` returns synchronously while AM's dispatch pipeline processes the alert asynchronously (group_wait=30s in the route), so a back-to-back query reads empty stdout. Fixed in the same commit class as Task 1 with retries=30/delay=2 until: polling. Same fix shape, same race class, same file."

patterns-established:
  - "Parent-directory bind-mount convention for rendered configs -- now Gate 8 in roles/README.md, mandatory for all future role ports"
  - "Ansible-native polling for in-container verify probes (community.docker.docker_container_exec + until:) -- replaces the docker_container + auto_remove + shell-while-loop antipattern documented in ansible/ansible#45272 and #47673"
  - "meta:flush_handlers immediately before include_tasks:verify.yml in roles that notify config-change handlers earlier in their own main.yml -- ensures verify runs against post-restart state"

requirements-completed: [ALERT-01]

# Metrics
duration: 13min
completed: 2026-05-19
---

# Phase 4 Plan 2: Alert Plane Gap Closure Summary

**Bug 1 (auto_remove race) and Bug 2 (stale-inode bind-mount) both closed; alertmanager verify is race-free, 7 roles converted to parent-directory bind mounts (12 surfaces -> 7 mounts), Gate 8 added to roles/README.md preventing regression, and all 6 Phase 4 UAT tests pass on leviathan WITHOUT manual `docker restart` rescue.**

## Performance

- **Duration:** ~13 min (file-edits + live UAT on leviathan + summary write)
- **Started:** 2026-05-19T00:31:52Z
- **Completed:** 2026-05-19T00:44:38Z
- **Tasks:** 7 (6 file-edit tasks + 1 live-UAT checkpoint task; UAT was executed by Claude against leviathan per plan host_context)
- **Files modified:** 10 (9 role files + 1 UAT file; 04-UAT.md was updated with post-fix evidence)

## Accomplishments

- **Bug 1 closed (auto_remove race):** step 5 of `roles/alertmanager/tasks/verify.yml` rewritten with `community.docker.docker_container_exec` against the running AM container (busybox `wget -qO-`), polled via Ansible `until:`/`retries:`/`delay:` (30/2). Live re-run on leviathan: fresh deploy completes with PLAY RECAP `failed=0`. The original "Cannot retrieve result as auto_remove is enabled" error cannot fire on this pattern.
- **Bug 2 closed (stale-inode bind-mount class):** all 12 single-file rendered-config bind-mount surfaces across 7 roles converted to parent-directory bind mounts. Manual atomic-rename regression check on leviathan: after `sudo cp foo foo.new && mv foo.new foo`, the host inode changed from 524589 -> 2097216 AND the container immediately picked up the new inode 2097216 -- definitive proof the parent-directory mount semantics work.
- **Shared belt-and-suspenders fix:** `meta: flush_handlers` inserted before `include_tasks: verify.yml` in both prometheus and alertmanager tasks/main.yml -- one change covers Bug 1 TIER 2 (verify probes post-restart state) and Bug 2 belt-and-suspenders (handler flushes before verify sees the still-stale inode would have).
- **Doc gate landed:** roles/README.md gains Gate 8 (Parent-directory bind-mount convention) citing moby/moby#6011. Future role ports inherit the convention; the anti-pattern is now banned at the role-acceptance-checklist level.
- **Live UAT all-pass on leviathan:** all 6 Phase 4 UAT tests pass (HEALTHCHECK + /api/v2/receivers + /api/v2/status + Prom->AM round-trip + amtool alert/silence + Gate 4 idempotency). No manual `docker restart` rescue needed at any point.

## Task Commits

| Task | Description                                                                                             | Commit  |
|------|---------------------------------------------------------------------------------------------------------|---------|
| 1    | Rewrite alertmanager verify step 5 via docker_container_exec (Bug 1 TIER 1)                              | `93c3141` |
| 2    | Flush handlers before verify in prometheus + alertmanager (Bug 1 TIER 2 + Bug 2 belt)                    | `b349393` |
| 3    | Refactor prometheus to parent-directory bind mount (Bug 2 FIX A, 3 surfaces)                             | `5ee2d0a` |
| 4    | Refactor alertmanager+loki+tempo+mimir to parent-directory bind mounts (Bug 2 FIX A, 4 surfaces)         | `139da86` |
| 5    | Refactor opentelemetry+fluentbit to parent-directory bind mounts (Bug 2 FIX A, 5 surfaces)               | `d9adf6b` |
| 6    | Add Parent-directory bind-mount Gate 8 to roles/README.md (doc gate citing moby/moby#6011)               | `dbda9e3` |
| Auto-fix | Poll amtool alert/silence query with until: (Rule 1 auto-fix surfaced during UAT)                    | `41a970b` |
| 7    | Live UAT re-run on leviathan -- all 6 tests pass; this SUMMARY + 04-UAT.md update + STATE update (final) | (pending final commit) |

## Live UAT Re-run on Leviathan

All 6 tests pass on leviathan 2026-05-19T00:42Z. Fresh-deploy sequence: `ssh leviathan 'docker rm -f telemetron-prometheus telemetron-alertmanager'` -> `ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags alertmanager,prometheus` -> tests 1-6 in order.

### Test 1: HEALTHCHECK reports healthy

```
$ ssh leviathan "docker inspect telemetron-alertmanager --format '{{.State.Health.Status}}'"
healthy
PLAY RECAP: leviathan : ok=30 changed=2 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0
```

PASS. The race-free step 5 + the prometheus meta:flush_handlers combine to eliminate the original Bug 1 manifestation.

### Test 2: /api/v2/receivers null receiver

```
$ ssh leviathan 'docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://alertmanager:9093/api/v2/receivers'
[{"name":"null"}]
```

PASS.

### Test 3: /api/v2/status route knobs (D-61)

```
$ ssh leviathan 'docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://alertmanager:9093/api/v2/status'
...
route:
  receiver: "null"
  group_by:
  - alertname
  - cluster
  - service
  continue: false
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
inhibit_rules:
- source_matchers:
  - severity="critical"
  target_matchers:
  - severity="warning"
  equal:
  - instance
...
```

PASS. All four D-61 route knobs present; corrected source_matchers/target_matchers syntax confirmed live (D-63 + Research Q2).

### Test 4: Prometheus -> Alertmanager round-trip (D-64)

```
$ ssh leviathan 'docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://prometheus:9090/api/v1/alertmanagers'
{"status":"success","data":{"activeAlertmanagers":[{"url":"http://alertmanager:9093/api/v2/alerts"}],"droppedAlertmanagers":[]}}
```

PASS without `docker restart` rescue. Bug 2 belt-and-suspenders (flush_handlers before AM verify probes Prometheus) plus the parent-directory bind mount (verify probes always read the fresh inode anyway) combine to make this work first-try.

**Bug 2 inode-pinning regression check:**

```
Host    inode: sudo stat -c '%i' /opt/telemetron/prometheus/prometheus.yml -> 524589
Container inode: docker exec telemetron-prometheus stat -c '%i' /etc/prometheus/prometheus.yml -> 524589
md5 host  = 47d84aceddde83f32a6e6e6a41ec81a2
md5 cnt   = 47d84aceddde83f32a6e6e6a41ec81a2
```

**Definitive proof of parent-directory mount semantics (manual atomic-rename simulation):**

```
Before manual `cp foo foo.new && mv foo.new foo`:
  Host inode 524589 / Container inode 524589
After manual atomic-rename:
  Host inode 2097216 / Container inode 2097216  <- container picks up NEW inode immediately
```

With the old single-file bind mount, the container would have remained on inode 524589. Bug 2 verifiably closed.

### Test 5: amtool synthetic alert + silence (D-69) + D-62 volume persistence

```
$ ssh leviathan "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 alert add alertname=PostFixTest severity=warning instance=verify-host"
$ sleep 8
$ ssh leviathan "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 alert query alertname=PostFixTest"
Alertname    Starts At                Summary  State   
PostFixTest  2026-05-19 00:41:26 UTC           active  
$ ssh leviathan "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 silence add --comment='04-02 silence test' alertname=PostFixTest"
0a4af9e6-5801-42aa-a4f8-b7dcb07ff3ef
$ ssh leviathan "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 silence query alertname=PostFixTest"
ID                                    Matchers                 Ends At                  Created By  Comment             
0a4af9e6-5801-42aa-a4f8-b7dcb07ff3ef  alertname="PostFixTest"  2026-05-19 01:41:35 UTC  nobody      04-02 silence test
$ ssh leviathan 'docker restart telemetron-alertmanager && sleep 12'
$ ssh leviathan "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 silence query alertname=PostFixTest"
ID                                    Matchers                 Ends At                  Created By  Comment             
0a4af9e6-5801-42aa-a4f8-b7dcb07ff3ef  alertname="PostFixTest"  2026-05-19 01:41:35 UTC  nobody      04-02 silence test  
```

PASS. Silence persists across `docker restart` -- D-62 named-volume nflog persistence confirmed.

### Test 6: Gate 4 idempotency

```
$ timeout 360 ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags alertmanager
PLAY RECAP: leviathan : ok=17 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

PASS. changed=0 / failed=0 -- idempotency preserved across the refactor.

## Decisions Made

See key-decisions in frontmatter -- 7 decisions exercised. Two were canonical Phase-4-gap-closure choices (Bug 1 TIER 1 docker_container_exec rewrite + Bug 2 FIX A parent-directory bind mounts). Three were defense-in-depth / scope-shape calls (meta:flush_handlers belt-and-suspenders for both bugs; tempo's container-side path change as the only mount-target update needed in the plan; TIER 3 deferred to follow-up). Two emerged at execute time (auto-fix Rule 1 for amtool dispatch race in steps 7 + 9; Gate 8 wording in roles/README.md).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Poll amtool alert/silence query with `until:` (verify-task race surfaced during UAT)**

- **Found during:** Task 7 live UAT re-run on leviathan
- **Issue:** With Bug 1 + Bug 2 now fixed, the play proceeded past step 5 and reached step 7 (amtool alert query) immediately after step 6 (amtool alert add). amtool's `alert add` returns synchronously when AM accepts the POST, but AM's internal dispatch / group-by pipeline processes the alert asynchronously (group_wait=30s in the route) -- the alert takes several seconds to surface in the query API. The original single-shot `failed_when: "'TestAlert' not in stdout"` race-faulted with `stdout: "Alertname  Starts At  Summary  State  "` (header-only, no row). The same race-class theoretically applies to step 9 (silence query) even though silence creation is more synchronous in practice.
- **Fix:** Same pattern as Task 1's step 5 fix. Replace single-shot read with Ansible-native polling: `failed_when: false` (let `until:` own the success criteria), `retries: 30`, `delay: 2`, `until: stdout contains TestAlert`. Apply to both step 7 and step 9.
- **Files modified:** `roles/alertmanager/tasks/verify.yml`
- **Verification:** Live re-run on leviathan: full `--tags alertmanager,prometheus` from a fresh state completes with PLAY RECAP `failed=0`. Step 7 retries gracefully until the alert surfaces; step 9 passes on first try.
- **Committed in:** `41a970b`
- **Classification:** Rule 1 (bug fix). Pre-existing latent race that only surfaced after the Bug 1/2 fixes let the play execute the amtool sequence to completion. Same class of fix (verify probes need polling, not single-shot reads) as the original Bug 1 fix in step 5.

**No other deviations.** All 6 task plans executed exactly as written. No CLAUDE.md-driven adjustments needed.

## Deferred (Out of 04-02 Scope)

- **TIER 3 backfill (9 latent auto_remove sites):** loki/tempo/mimir/prometheus(x2)/opentelemetry(x2)/fluentbit/node_exporter all use the same docker_container + auto_remove + shell-loop pattern that Bug 1 hit. They are LATENT today -- their loops early-exit-0 in <10s normally, so the race window stays tiny. Risk re-emerges only when another cross-role probe is added (Phase 5 Karma->AM, Grafana datasource probes, etc.). Captured in `.planning/debug/alertmanager-verify-prom-am-probe-auto-remove-race.md` for the Phase 5+ inheritor. The new docker_container_exec + until: pattern from this plan IS the canonical replacement.
- **MinIO/node_exporter bind-mount review:** minio uses `env_file` (host-side slurp at container create, not bind-mounted); node_exporter has no config file (CLI-flag-driven). Both immune to Bug 2 per the debug doc's blast-radius analysis -- no work needed.
- **Hook router work:** still deferred to v2 milestone per D-56/D-57/D-58 (Plan 04-01). Plan 04-02 does not change that.

## Issues Encountered

One race-class bug surfaced during UAT (amtool dispatch race in verify steps 7 + 9) and was auto-fixed under Rule 1; see "Deviations from Plan" above. No other issues.

The UAT executor was Claude per the plan's `<action>` block + the orchestrator's `<host_context>` -- leviathan is SSH-passwordless with Docker 29, gitignored inventory at `inventory/leviathan/`. Both deploy runs and all 6 test assertions completed without user intervention.

## User Setup Required

None. All UAT was executed against leviathan by Claude per the plan's host_context; no external configuration was required.

## Next Phase Readiness

**Phase 5 (UI Plane) is unblocked.**

Carryover notes for Phase 5:

- **Bind-mount convention now enforced.** Phase 5's grafana, karma, promlens role ports MUST mount config parent directories, not individual files. Gate 8 in `roles/README.md` codifies the rule.
- **Cross-role probes inherit the docker_container_exec + until: pattern.** Any Phase 5 verify task that probes another component (e.g. Karma -> Alertmanager, Grafana datasource healthchecks) should use the new step-5 shape, NOT the older docker_container + auto_remove + shell-loop pattern.
- **meta:flush_handlers is the prevention pattern for verify-probes-stale-state.** Any Phase 5 role that notifies a restart handler on a config change AND then runs a verify task in the same play should add `meta: flush_handlers` immediately before the verify include. (Not retroactively added to loki/tempo/mimir/opentelemetry/fluentbit in 04-02 because their verify probes do not currently exercise the bug, but the pattern is now available.)
- **TIER 3 follow-up ticket** lives in the debug doc `.planning/debug/alertmanager-verify-prom-am-probe-auto-remove-race.md` -- convert the 9 latent sites when a Phase 5 cross-role probe makes any of them firing rather than latent.

## Self-Check: PASSED

**Modified files verified to exist:**

- FOUND: roles/alertmanager/tasks/verify.yml
- FOUND: roles/alertmanager/tasks/main.yml
- FOUND: roles/prometheus/tasks/main.yml
- FOUND: roles/loki/tasks/main.yml
- FOUND: roles/tempo/tasks/main.yml
- FOUND: roles/mimir/tasks/main.yml
- FOUND: roles/opentelemetry/tasks/main.yml
- FOUND: roles/fluentbit/tasks/main.yml
- FOUND: roles/README.md
- FOUND: .planning/phases/04-alert-plane/04-UAT.md
- FOUND: .planning/phases/04-alert-plane/04-02-SUMMARY.md

**Commits verified to exist:**

- FOUND: 93c3141 (Task 1)
- FOUND: b349393 (Task 2)
- FOUND: 5ee2d0a (Task 3)
- FOUND: 139da86 (Task 4)
- FOUND: d9adf6b (Task 5)
- FOUND: dbda9e3 (Task 6)
- FOUND: 41a970b (auto-fix during UAT)

---
*Phase: 04-alert-plane*
*Plan: 02 (gap closure)*
*Completed: 2026-05-19*
