---
phase: 05-ui-plane
plan: 08
subsystem: ui
tags: [karma, promlens, ansible, docker, healthcheck, verify, auto_remove, scratch-image]

# Dependency graph
requires:
  - phase: 05-ui-plane
    provides: "Plan 05-02 (karma role port) + Plan 05-03 (promlens role port); identified UAT gap-truth #4 (karma unhealthy) and gap-truth #5 (default deploy failure on karma+promlens verify)"
provides:
  - "karma_healthcheck_enabled flipped to false by default (UAT gap 4 closed)"
  - "5 docker_container probe tasks across karma+promlens verify.yml converted from auto_remove:true to auto_remove:false + cleanup:true; race-free results"
  - "Pre-existing shell-parse bug in karma->AM probe fixed (Rule-1 auto-fix surfaced during Task 4 UAT)"
  - "Pre-existing GET-vs-POST mismatch against karma /alerts.json fixed (Rule-1 auto-fix)"
  - "Karma README Healthcheck section rewritten to document opt-in posture + scratch-image constraint + re-enable procedure"
affects: [06-opt-in-orchestration-docs, future-phases-touching-karma-or-promlens]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scratch-image constraint pattern: when an upstream image is FROM scratch (no /bin/sh), docker_container_exec is not available -- keep one-shot curlimages/curl container pattern but flip auto_remove:false + cleanup:true + detach:false"
    - "Conditional Docker HEALTHCHECK with default-disabled posture for scratch images that can't be probed via CMD-SHELL"
    - "YAML folded scalar pitfall: more-indented continuation lines preserve newlines (do NOT collapse) -- use plain scalar for shell commands when || / | chains span lines"

key-files:
  created:
    - ".planning/phases/05-ui-plane/05-08-SUMMARY.md"
  modified:
    - "roles/karma/defaults/main.yml -- karma_healthcheck_enabled: true -> false + comment block explaining scratch-image constraint"
    - "roles/karma/README.md -- Healthcheck section rewritten for opt-in posture + re-enable procedure"
    - "roles/karma/tasks/verify.yml -- 3 sites: auto_remove:true -> auto_remove:false (+ inline comments); also Rule-1 auto-fix on AM-connection probe (shell parse + POST method)"
    - "roles/promlens/tasks/verify.yml -- 2 sites: auto_remove:true -> auto_remove:false (+ inline comments)"
    - ".planning/ROADMAP.md -- Phase 5 plans list adds 05-08 entry"

key-decisions:
  - "Default disposition of karma container-level HEALTHCHECK is OFF (opt-in). Image is FROM scratch -- no /bin/sh -- any CMD-SHELL form fails immediately. In-network curl-probe in verify.yml is the canonical health gate."
  - "Karma verify.yml cannot use the grafana-style docker_container_exec rewrite (karma container has no shell to exec into). Keep one-shot curlimages/curl pattern; only flip auto_remove:true -> auto_remove:false with cleanup:true already present."
  - "Pre-emptively fix latent promlens auto_remove sites in the same closure (same defect class, same fix shape) rather than spawning a follow-up plan."
  - "Auto-fix Rule-1: the karma -> Alertmanager probe was silently passing on every deploy with status:2 due to YAML folded-scalar newline preservation + GET-only against karma's POST-only /alerts.json endpoint -- both fixed in one Rule-1 auto-fix commit."

patterns-established:
  - "Scratch-image healthcheck opt-in: when an upstream container image is FROM scratch, ship the role with healthcheck DISABLED by default and document re-enable procedure in role README. Pattern reusable for any future scratch-based image (currently: karma)."
  - "auto_remove:false + cleanup:true + detach:false: the documented community.docker escape hatch from the auto_remove+detach:false race when docker_container_exec isn't viable (target container has no shell)."

requirements-completed: [UI-05]

# Metrics
duration: 8min
completed: 2026-05-19
---

# Phase 5 Plan 08: Karma Healthcheck Opt-In + Verify auto_remove Fix Summary

**Karma image is FROM scratch (no /bin/sh) so the role's CMD-SHELL+wget HEALTHCHECK was guaranteed to fail every interval; flipped karma_healthcheck_enabled default to false, made the in-network curl-probe the canonical health gate, fixed 5 latent auto_remove+detach:false races in karma+promlens verify.yml, and incidentally Rule-1-auto-fixed a silently-failing karma->AM probe (YAML folded-scalar newline-preservation shell parse error + GET-vs-POST mismatch against karma /alerts.json).**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-19T16:45:12Z
- **Completed:** 2026-05-19T16:53:39Z
- **Tasks:** 5 completed (Task 4 was verification-only)
- **Files modified:** 5 (4 role files + 1 roadmap; SUMMARY.md created)

## Accomplishments

- **UAT gap-truth #4 CLOSED.** `docker inspect telemetron-karma --format '{{json .State.Health}}'` returns `null` after a fresh deploy on leviathan. Container is `running`. `/health` still returns 200 `Pong`. No more `unhealthy` despite functional traffic.
- **UAT gap-truth #5 karma + promlens halves CLOSED.** `ansible-playbook --tags karma` completes `failed=0` with all 3 karma verify-probe success tokens (`karma_health_ok`, `karma_ui_ok`, `karma_am_connection_ok`). `ansible-playbook --tags promlens` completes `failed=0` with both promlens tokens (`promlens_root_ok`, `promlens_upstream_prometheus_ok`). Idempotency holds: second back-to-back run reports `changed=0 failed=0`.
- **Latent races eliminated pre-emptively.** 5 docker_container tasks across karma (3) + promlens (2) verify.yml converted from the documented-invalid `auto_remove:true + detach:false` combo to `auto_remove:false + cleanup:true + detach:false`. Same defect class as 04-02 alertmanager-verify and 05-05 grafana-verify.
- **Pre-existing karma->AM probe bug uncovered + fixed.** Rule-1 auto-fix during Task 4 verification: the karma_am_connection_ok assertion had been silently passing for every deploy with status:2 ("/bin/sh: syntax error: unexpected '||'") because YAML `>-` folded scalars preserve newlines on more-indented continuation lines. Reflowed to a plain scalar; also switched the request from GET to POST since karma's /alerts.json endpoint is POST-only.
- **Documentation rewrite.** karma README Healthcheck section now explains why the docker HEALTHCHECK is opt-in (scratch image), what the canonical health gate is (in-network curl-probe), and how operators can re-enable (sidecar pattern or custom image rebuild, both out of M1 scope).

## Task Commits

Each task was committed atomically with `--no-verify` (parallel agent harness):

1. **Task 1: Flip karma_healthcheck_enabled default to false** - `a284495` (fix)
2. **Task 2: Update karma README Healthcheck section** - `03ac2ec` (docs)
3. **Task 3: Fix latent auto_remove race in karma + promlens verify.yml** - `32d7f26` (fix)
4. **Task 4: Live UAT on leviathan (Rule-1 auto-fix surfaced)** - `fc32e1f` (fix, Rule-1)
5. **Task 5: ROADMAP.md update + plan metadata** - (final metadata commit, this SUMMARY commit)

## Files Created/Modified

- `roles/karma/defaults/main.yml` - karma_healthcheck_enabled flipped from true to false; ~20-line comment block added documenting scratch-image constraint, canonical health gate (verify.yml line 27), and re-enable procedure.
- `roles/karma/README.md` - Healthcheck section rewritten: opt-in posture, scratch-image constraint explained, in-network curl-probe documented as canonical gate, three re-enable options listed (all explicitly out of M1 scope).
- `roles/karma/tasks/verify.yml` - 3 docker_container probe tasks (lines 27, 48, 74) switched from `auto_remove: true` to `auto_remove: false` with inline comments citing the community.docker module docs. Plus Rule-1 auto-fix on the AM-connection probe task (lines 85-93): reflowed multi-line YAML folded-scalar shell command to single plain-scalar line; switched from GET-with-fallback to POST with empty JSON body against karma's /alerts.json (POST-only endpoint per RESEARCH sec.2.2).
- `roles/promlens/tasks/verify.yml` - 2 docker_container probe tasks (lines 27, 49) switched from `auto_remove: true` to `auto_remove: false` with same inline comment. Pre-emptive fix: these sites were latent (grafana-verify failed first) and would have activated once 05-05 landed.
- `.planning/ROADMAP.md` - Phase 5 Plans list extended with `- [x] 05-08-PLAN.md -- gap closure (karma healthcheck OPT-IN by default; scratch-image constraint + karma/promlens verify.yml auto_remove race fix); Wave 1`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Karma -> Alertmanager probe was silently failing on every deploy**

- **Found during:** Task 4 live UAT on leviathan (verbose `-v` log inspected container Output field)
- **Issue:** Two independent pre-existing bugs in `roles/karma/tasks/verify.yml` task `Karma -> Alertmanager connection assertion`:
  1. The shell command used a YAML `>-` folded scalar where continuation lines 89-92 were MORE-indented than the indication column on line 88. Per YAML spec, more-indented lines in a folded scalar preserve their newlines (they're "more-indented lines" and do NOT collapse to spaces). The resulting shell input had a literal newline between `'telemetron'` and `||`, which sh parses as a syntax error: `/bin/sh: syntax error: unexpected "||"`.
  2. The probe used GET against karma's `/alerts.json` endpoint with a fallback to `/api/v1/alerts`. Per RESEARCH sec.2.2 (and verified live on leviathan), karma's `/alerts.json` is POST-only (returns HTTP 405 on GET) and `/api/v1/alerts` does not exist on karma v0.130.
  Both combined: the task ran with `status: 2` (shell error) and 0-byte body, but the `failed_when` clause only fires when `attempts >= 15`. Since the until-loop's `is succeeded` check considered status:2 as failed, retry should have happened -- but the task showed `attempts: 1` and `ok` because the shell error path produced an exit but somehow no retry. Net: the UI-05 wiring assertion never actually executed; "karma_am_connection_ok" was never emitted in any pre-05-08 deploy.
- **Fix:** Reflowed the shell command from a multi-line YAML folded scalar to a single plain-scalar line so sh receives one continuous statement. Switched the request from GET-with-fallback to a single POST with `Content-Type: application/json` and empty JSON body `{}` (matches karma's own UI fetch shape).
- **Files modified:** `roles/karma/tasks/verify.yml` lines 85-94
- **Commit:** `fc32e1f`
- **Net effect:** `karma_am_connection_ok` now actually appears in verify logs when karma's response payload contains the configured alertmanager source name (the UI-05 wiring assertion that 05-02 originally intended).

### Other Notes

- Task 4's first deploy returned `changed=0` because karma's container was already running (with the broken pre-05-08 HEALTHCHECK baked in). Per the plan's "If unhealthy still appears" branch, I manually `docker stop && docker rm telemetron-karma` and redeployed; the second deploy correctly built a new container with no HEALTHCHECK configured (`.Config.Healthcheck` is `null`, `.State.Health` is `null`).
- The combined `--tags grafana,karma,promlens --skip-tags grafana-verify` invocation completed `ok=25 changed=0 failed=0 skipped=1` -- confirms the karma + promlens halves of UAT gap-truth #5 are closed. Grafana-verify side is plan 05-05's concern (separate parallel agent).

## Self-Check

Files verified on disk:

- FOUND: `roles/karma/defaults/main.yml` (karma_healthcheck_enabled: false; YAML parses)
- FOUND: `roles/karma/README.md` (contains "scratch image", `karma_healthcheck_enabled`, "in-network curl-probe")
- FOUND: `roles/karma/tasks/verify.yml` (zero `auto_remove: true`; 3 `auto_remove: false` as YAML keys; Rule-1 fix applied to AM probe)
- FOUND: `roles/promlens/tasks/verify.yml` (zero `auto_remove: true`; 2 `auto_remove: false` as YAML keys)
- FOUND: `.planning/phases/05-ui-plane/05-08-SUMMARY.md` (this file)
- FOUND: `.planning/ROADMAP.md` (contains "05-08-PLAN.md" entry)

Commits verified in `git log`:

- FOUND: `a284495` -- fix(05-08): flip karma_healthcheck_enabled default to false
- FOUND: `03ac2ec` -- docs(05-08): rewrite karma README Healthcheck section
- FOUND: `32d7f26` -- fix(05-08): drop latent auto_remove race in karma+promlens verify.yml
- FOUND: `fc32e1f` -- fix(05-08): unbreak karma->AM probe shell parsing + POST method (Rule-1)

## Self-Check: PASSED
