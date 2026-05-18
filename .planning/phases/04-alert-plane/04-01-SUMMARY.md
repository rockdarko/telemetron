---
phase: 04-alert-plane
plan: 01
subsystem: infra
tags: [ansible, docker, alertmanager, prometheus, observability]

# Dependency graph
requires:
  - phase: 03-ingest-plane
    provides: "Prometheus role with rule_files + remote_write; four baseline alert rules carrying severity labels; telemetron Docker bridge network; org.telemetron.{service,job} label-stamp convention (Gate 7)"
provides:
  - "roles/alertmanager/ -- single-instance monolithic Alertmanager v0.32.1 (quay.io) on :9093 with ALERT-01/D-61 routing knobs, single null receiver default (D-60), one default inhibit rule using corrected source_matchers syntax (D-63 + Research Q2), persistent telemetron_alertmanager_data volume on /alertmanager (D-62)"
  - "Prometheus -> Alertmanager wiring (D-64): roles/prometheus/templates/prometheus.yml.j2 carries alerting: alertmanagers: block; defaults/main.yml exposes prometheus_alertmanager_target: alertmanager:9093"
  - "inventory/example-homelab/group_vars/all/alertmanager.yml -- D-15 operator-tunable surface (D-61 intervals + D-60 extension lists + D-30 publish flag + log level)"
  - "playbooks/deploy_docker.yml extended: minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus -> fluentbit -> alertmanager"
  - "Doc cascade across 5 tracked files (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, hooks/README.md, roles/README.md) + 4 gitignored planning files (CLAUDE.md tech-stack, research/{SUMMARY,FEATURES,ARCHITECTURE}.md) recording hook-router deferral to ALERT-V2-01..05"
affects: [05-ui-plane, karma, grafana, hook-router-v2-milestone]

# Tech tracking
tech-stack:
  added:
    - "quay.io/prometheus/alertmanager:v0.32.1 (single-instance monolithic, --cluster.listen-address= disables gossip)"
    - "amtool /bin/amtool bundled in AM image (Research Q3) -- used via community.docker.docker_container_exec for D-69 verify"
  patterns:
    - "Conditional HEALTHCHECK pattern continued -- explicit wget probe via busybox base when image ships none (Research Q1; mirrors Phase-2 Tempo/Mimir omit-magic guard)"
    - "Two-template Prometheus role pattern extended -- existing config-change handler auto-fires on the cross-role template edit (no new handler wiring)"
    - "Doc-cascade-then-port atomicity -- Task 1 moved the spec before Task 2 wrote the code, so no in-flight inconsistency between 'spec says hook router' and 'code skipped it'"

key-files:
  created:
    - "roles/alertmanager/defaults/main.yml"
    - "roles/alertmanager/tasks/main.yml"
    - "roles/alertmanager/tasks/verify.yml"
    - "roles/alertmanager/handlers/main.yml"
    - "roles/alertmanager/templates/alertmanager.yml.j2"
    - "roles/alertmanager/meta/main.yml"
    - "roles/alertmanager/README.md"
    - "inventory/example-homelab/group_vars/all/alertmanager.yml"
  modified:
    - "roles/prometheus/templates/prometheus.yml.j2 (added alerting: block)"
    - "roles/prometheus/defaults/main.yml (added prometheus_alertmanager_target)"
    - "roles/prometheus/templates/rules-baseline.yml.j2 (D-65 verify-only inline comment)"
    - "playbooks/deploy_docker.yml (appended alertmanager role)"
    - "inventory/example-homelab/group_vars/all/vault.yml.example (removed hook-router speculative key)"
    - ".planning/PROJECT.md (drop hook router from Active/Core Value/Key Decisions)"
    - ".planning/REQUIREMENTS.md (ALERT-02..06 -> ALERT-V2-01..05; trim traceability)"
    - ".planning/ROADMAP.md (Phase 4 goal/SC/plans rewritten to alertmanager-only)"
    - "hooks/README.md (deferral placeholder)"
    - "roles/README.md (tick alertmanager row; rebrand hook_router row deferred)"

key-decisions:
  - "D-59 image pin v0.32.1 from quay.io/prometheus/alertmanager (matches Phase-3 node_exporter quay-over-docker-hub registry preference)"
  - "D-60 single null receiver default + operator extension lists (sorted-keys per D-20)"
  - "D-61 routing intervals explicit in rendered config (not relying on AM defaults): group_by [alertname,cluster,service], group_wait 30s, group_interval 5m, repeat_interval 4h"
  - "D-62 persistent telemetron_alertmanager_data volume on /alertmanager preserves silences + nflog across restart (Pitfall 7 mitigation)"
  - "D-63 one default inhibit rule severity=critical -> severity=warning equal: [instance] using NEW source_matchers syntax (Research Q2 -- CONTEXT.md showed deprecated source_match form)"
  - "D-64 cross-role Prometheus wiring: alerting: alertmanagers: block in prometheus.yml.j2 targets alertmanager:9093; existing restart handler fires automatically"
  - "D-65 severity-label retrofit is VERIFY-ONLY per Research Q11 -- all four baseline rules already carry their labels (Phase 3 shipped them)"
  - "D-66 ZERO vault keys added (null receiver = no outbound destination); planning-stub vault_jenkins_api_token / vault_alertmanager_webhook_secret references cleaned from vault.yml.example"
  - "D-67 all seven port-acceptance gates pass on code/config; D-25 convention (README documents the audit) preserves INSPQ-deviations narrative without tripping Gate 1 on documentation"
  - "Research Q1 explicit HEALTHCHECK via wget --spider (busybox base; image ships none)"
  - "Research Q3 amtool verify via docker_container_exec on running container (amtool is at /bin/amtool inside the image)"
  - "Research Q8 /api/v2/status returns config.original as YAML-string -- verify uses grep-on-YAML, not jq-on-nested-JSON (Risk 1 correction to CONTEXT.md D-69 spec)"
  - "Hook router (Flask + role + bundles + auth) deferred to a future milestone via D-56/D-57/D-58; ALERT-02..06 moved to ALERT-V2-01..05; design preserved in 04-DISCUSSION-LOG.md"

patterns-established:
  - "Doc-rework cascade atomicity: when a phase reshapes scope, the spec rewrite and the code write live in the same plan (no in-flight inconsistency window)"
  - "READ-ME-as-audit-trail: roles/<name>/README.md '## Deviations from upstream INSPQ' documents the strip without code containing the strings (Gate 1 grep gate scopes to code/config per D-25)"
  - "Cross-role config-template edit triggers existing restart handler -- no new handler wiring needed (D-64 extension model)"
  - "D-69 verify uses docker_container_exec for amtool (avoids one-shot image churn; uses bundled binary)"

requirements-completed: [ALERT-01]

# Metrics
duration: 13min
completed: 2026-05-18
---

# Phase 4 Plan 1: Alert Plane Summary

**Alertmanager v0.32.1 single-instance monolithic on :9093 with ALERT-01 routing knobs and a null default receiver, Prometheus alerting block wired to it (D-64), and the hook router deferred to a future milestone via a 5-file doc cascade -- M1 trades the "turnkey runbook automation" pitch for "single-host LGTM observability plane with alerts visible in Karma (Phase 5)."**

## Performance

- **Duration:** ~13 min (file-edits only; no live UAT run in this executor)
- **Started:** 2026-05-18T22:43:09Z
- **Completed:** 2026-05-18T22:55:42Z
- **Tasks:** 7 (5 with file edits + 2 verification-only)
- **Files modified:** 16 (8 new + 8 edits; counts tracked-only changes)

## Accomplishments

- **ALERT-01 code-complete** -- roles/alertmanager/ ships seven files in the canonical Phase 1-3 role shape (defaults, tasks/main, tasks/verify, handlers, templates, meta, README) with the v0.32.1 image pin, ALERT-01/D-61 routing knobs, single null receiver, one D-63 inhibit rule (CORRECTED source_matchers syntax), Gate-7 telemetron labels, persistent named volume on /alertmanager, conditional explicit HEALTHCHECK via wget, and an eight-step in-network verify suite (D-69) using amtool via docker_container_exec.
- **D-64 cross-role wiring** -- roles/prometheus/templates/prometheus.yml.j2 carries `alerting: alertmanagers:` block between rule_files: and remote_write:, defaulting to `alertmanager:9093` via the new `prometheus_alertmanager_target` knob. Existing restart handler fires automatically on next playbook run.
- **D-58 doc-cascade complete (9 files)** -- 5 tracked files + 4 gitignored agent-tooling files. ALERT-02..06 moved to `## v2 Requirements` as ALERT-V2-01..05; ROADMAP Phase 4 goal/SC/plans rewritten to alertmanager-only; PROJECT.md Core Value drops the `+ hook-router` clause and Active drops the Flask write; hooks/README.md rewritten as a deferral placeholder ("M1 does NOT build this image"); roles/README.md ticks the alertmanager row and re-words hook_router as deferred; the Gate-7 paragraph drops hook_router from Phase 4 list.
- **Inventory file shipped** -- inventory/example-homelab/group_vars/all/alertmanager.yml surfaces the D-61 intervals + D-60 extension lists + D-30 publish flag + log level. Vault file unchanged per D-66 (planning-stub hook-router keys removed).
- **Playbook orchestration extended** -- deploy_docker.yml now drives minio -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus -> fluentbit -> alertmanager.

## Task Commits

Each task was committed atomically:

1. **Task 1: Doc-rework cascade (D-58) -- defer hook router to v2** -- `15a4965` (docs)
2. **Task 2: Scaffold roles/alertmanager/ (7 files)** -- `d8809ab` (feat)
3. **Task 3: Extend roles/prometheus/ -- alerting block + D-64 default + D-65 verify** -- `fadb9ff` (feat)
4. **Task 4: Ship inventory/example-homelab/group_vars/all/alertmanager.yml (+ vault-file cleanup)** -- `41a5565` (feat)
5. **Task 5: Wire alertmanager into playbooks/deploy_docker.yml** -- `3aa3124` (feat)
6. **Task 6: Port-acceptance gates 1-7 full-sweep check** -- verification-only (no file edits)
7. **Task 7: Live deployment + D-69 verify (syntax-check only at executor time)** -- verification-only (no file edits)

## Files Created/Modified

**Created (8):**
- `roles/alertmanager/defaults/main.yml` -- role tunables (image pin v0.32.1, ALERT-01 routing knobs, healthcheck timing, network/volume/config-path defaults)
- `roles/alertmanager/tasks/main.yml` -- pull image -> ensure config dir -> render template -> ensure data volume -> run container with explicit HEALTHCHECK + Gate-7 labels + --cluster.listen-address= -> include verify.yml
- `roles/alertmanager/tasks/verify.yml` -- D-10a HEALTHCHECK poll, /-/ready + /-/healthy curl probes, /api/v2/receivers null-receiver assertion, /api/v2/status YAML-grep assertions, Prometheus /api/v1/alertmanagers round-trip, amtool synthetic alert add/query + silence add/query
- `roles/alertmanager/handlers/main.yml` -- single handler `Docker restart alertmanager` listening on `restart alertmanager` (D-19/W6)
- `roles/alertmanager/templates/alertmanager.yml.j2` -- rendered AM config: route with null receiver + D-61 intervals, inhibit_rules with NEW source_matchers syntax (D-63 corrected), receivers list with null + extras
- `roles/alertmanager/meta/main.yml` -- Galaxy metadata (author, license MIT, min_ansible_version 2.15, community.docker)
- `roles/alertmanager/README.md` -- OPS-03 schema (Variables -> Modes -> Tags -> Volumes -> Healthcheck -> Security -> Deviations from upstream INSPQ -> Idempotency -> Port-acceptance gates -> Deprecation notes); explicit `null`-receiver-is-deliberate paragraph
- `inventory/example-homelab/group_vars/all/alertmanager.yml` -- D-61 + D-60 + D-30 operator-tunable knobs

**Modified (8):**
- `roles/prometheus/templates/prometheus.yml.j2` -- inserted `alerting: alertmanagers:` block between rule_files: and remote_write:
- `roles/prometheus/defaults/main.yml` -- added `prometheus_alertmanager_target: "alertmanager:9093"`
- `roles/prometheus/templates/rules-baseline.yml.j2` -- inline comment documenting D-65 severity-label verification (Research Q11: no-op edit)
- `playbooks/deploy_docker.yml` -- appended `- role: alertmanager` after fluentbit; updated trailing comment block
- `inventory/example-homelab/group_vars/all/vault.yml.example` -- removed hook-router speculative key references (D-66)
- `.planning/PROJECT.md` -- Core Value drops `+ hook-router`; Active drops Flask-source bullet; Key Decisions row marked Deferred to v2
- `.planning/REQUIREMENTS.md` -- ALERT-02..06 moved to v2 as ALERT-V2-01..05; deferral note inserted; traceability trimmed
- `.planning/ROADMAP.md` -- Phase 4 goal/SC/plans rewritten to alertmanager-only (D-58)
- `hooks/README.md` -- rewritten as deferral placeholder citing ALERT-V2-01..05
- `roles/README.md` -- alertmanager row ticked; hook_router row rebranded deferred; Gate-7 paragraph reworded

**Also modified (gitignored agent-tooling files, not in commit but updated on disk):**
- `CLAUDE.md` -- tech-stack TL;DR + Custom/Glue + port-allocation rows mark hook router deferred
- `.planning/research/SUMMARY.md` -- "single highest-leverage M1 differentiator" rewording
- `.planning/research/FEATURES.md` -- hook router rows re-tagged deferred with rationale preserved as v2 reference material
- `.planning/research/ARCHITECTURE.md` -- ASCII diagram box relabelled `[hook_router :5001 -- deferred to v2]` + footnote

## Decisions Made

See key-decisions in frontmatter -- 13 decisions exercised (D-56 through D-69 from CONTEXT.md, plus 3 Research corrections).

**Notable corrections honored at execute time:**
- Research Q2: Used new `source_matchers:`/`target_matchers:` syntax in the inhibit rule (CONTEXT.md D-63 showed deprecated `source_match:`).
- Research Q3: amtool verify via `docker_container_exec` on the running container (not a one-shot image).
- Research Q8: `/api/v2/status` config.original is YAML-as-string; verify uses grep-on-YAML, not jq-on-nested-JSON (Risk 1 correction).
- Research Q11: D-65 severity-label retrofit is a no-op; all four baseline rules already carry their labels. Recorded as an inline comment in `rules-baseline.yml.j2` so a future regression is caught.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Cleaned planning-stub hook-router keys from vault.yml.example**
- **Found during:** Task 4 (inventory file ship)
- **Issue:** Task 4 acceptance criterion 5 required `grep -E "vault_alertmanager_" inventory/example-homelab/group_vars/all/vault.yml.example` to return 0 lines (D-66). The file already shipped a commented planning stub `# vault_alertmanager_webhook_secret: CHANGE_ME  # Phase 4 -- shared secret on hook_router inbound` which would have falsely flagged Gate 3 at audit time and contradicted the doc cascade landed in Task 1.
- **Fix:** Replaced the speculative vault-key comments (alertmanager + jenkins) with an explicit "Phase 4 adds NO vault keys (D-66)" note pointing at ALERT-V2-01..05 for the deferred design. The `vault_grafana_admin_password` Phase 5 forward-reference is preserved.
- **Files modified:** `inventory/example-homelab/group_vars/all/vault.yml.example`
- **Verification:** `grep -E 'vault_alertmanager_' inventory/example-homelab/group_vars/all/vault.yml.example` returns 0 lines (Gate 3 pass).
- **Committed in:** `41a5565` (Task 4 commit)

**2. [Documentation discipline] Reworded README "Deviations from upstream INSPQ" to avoid the literal `Quebec-government` / `French` language strings**
- **Found during:** Task 2 (role README write)
- **Issue:** The plan's template README spec included literal phrases like "Quebec-government" and "French-language" describing the upstream context. While established Phase 1-3 convention (D-25) allows INSPQ documentation in role READMEs (since the audit narrative must reference the deviation list), the executor used neutral phrasing ("upstream language", "the upstream on-call topology") to keep the README leaner. Three legitimate `inspq`/`INSPQ` references remain in the README (the "Deviations from upstream INSPQ" section header, the upstream repo path, and the Gate 1 documentation example) -- all mirror existing Phase 1-3 role READMEs.
- **Fix:** README content authored with neutral language for vocabulary references; INSPQ references preserved where they document the audit per D-25.
- **Files modified:** `roles/alertmanager/README.md`
- **Verification:** Code/config gate clean (`grep -riE 'inspq|qc.ca|montreal|quebec|francais|french' roles/alertmanager/ --include='*.yml' --include='*.j2' --include='*.yaml'` returns 0). README INSPQ references = 3, matching Phase-1..3 pattern (`grep -c inspq` on minio=0, loki=11, tempo=6, mimir=5, opentelemetry=7, prometheus=4, fluentbit=2, node_exporter=5).
- **Committed in:** `d8809ab` (Task 2 commit)

**Note on gitignored docs:** CLAUDE.md, `.planning/research/{SUMMARY,FEATURES,ARCHITECTURE}.md` are listed in `.gitignore` as "Agentic / AI tooling - local-only, doesn't pertain to the project itself". The plan's D-58 cascade enumerated 9 files; 5 of those are tracked and were committed (PROJECT, REQUIREMENTS, ROADMAP, hooks/README, roles/README). The 4 gitignored agent-tooling files were updated on disk so the local agentic context stays consistent, but were NOT committed -- following the established `.gitignore` convention preserved through Phases 1-3.

---

**Total deviations:** 2 auto-fixed (1 Rule-2 missing critical, 1 documentation discipline). The vault-cleanup auto-fix prevented a stale planning stub from contradicting the doc cascade and falsely flagging Gate 3. No scope creep -- both auto-fixes were inside the plan's stated scope, just refining wording or removing pre-existing planning debris.

**Impact on plan:** All seven port-acceptance gates pass on the static artifacts. ALERT-01 is code-complete. The plan's "live deployment" Task 7 deferred to follow-up UAT (executor environment has no target homelab host); the syntax-check passes and the role's embedded verify.yml exercises the full D-69 surface when an operator runs `ansible-playbook --tags alertmanager` against their host.

## Issues Encountered

None -- the role port followed the canonical Phase 1-3 template without surprises. The CONTEXT.md D-63 `source_match:` -> Research Q2 corrected `source_matchers:` syntax flip was caught and applied at template-write time. The CONTEXT.md D-65 severity-label retrofit -> Research Q11 no-op flip was caught and applied as an inline verification comment instead of a redundant edit.

## User Setup Required

None -- no external service configuration required. Operators wiring real notification destinations later will set `alertmanager_extra_receivers` + `alertmanager_extra_routes` in their inventory; that surface is documented in `roles/alertmanager/README.md` "Bring your own receivers".

**Optional live UAT** (when operator has a target homelab host available):

```bash
# First-run deploy:
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags alertmanager,prometheus --ask-vault-pass
# Expected: PLAY RECAP shows failed=0, unreachable=0; verify.yml steps all OK

# Idempotency check (Gate 4 live):
ansible-playbook -i inventory/example-homelab playbooks/deploy_docker.yml --tags alertmanager --ask-vault-pass
# Expected: PLAY RECAP shows changed=0

# Manual cross-checks (run from operator workstation against target host):
ssh <host> "docker inspect telemetron-alertmanager --format '{{.State.Health.Status}}'"     # healthy
ssh <host> "docker inspect telemetron-alertmanager --format '{{.HostConfig.RestartPolicy.Name}}'"  # unless-stopped
ssh <host> "docker inspect telemetron-alertmanager --format '{{range .Mounts}}{{.Name}}:{{.Destination}} {{end}}'"  # telemetron_alertmanager_data:/alertmanager
ssh <host> "docker inspect telemetron-alertmanager --format '{{json .Config.Labels}}'"  # org.telemetron.{service,job}
ssh <host> "docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://prometheus:9090/api/v1/alertmanagers"  # contains alertmanager:9093/api/v2/alerts

# AM persistence test (silence survives restart -- D-62):
ssh <host> "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 silence add --comment='persistence test' alertname=PersistenceTest"
ssh <host> "docker restart telemetron-alertmanager"
sleep 30
ssh <host> "docker exec telemetron-alertmanager /bin/amtool --alertmanager.url=http://localhost:9093 silence query alertname=PersistenceTest"
# Expected: silence still listed (proves named-volume nflog persistence)
```

## Next Phase Readiness

**Phase 5 (UI Plane) is unblocked.**

Carryover notes for Phase 5:
- **Karma's role expands.** Originally Phase-5 Karma was framed as an auxiliary alert UI. With the hook router deferred, Karma becomes THE alert UX in M1 -- silences, deduplication views, grid groupings. Phase 5 planning should treat Karma accordingly. Karma in Phase 5 will point at this Alertmanager via the `karma_alertmanager_uri: http://alertmanager:9093` knob (to be set in Phase 5 inventory).
- **Gate 7 inheritance:** every Phase 5 role (grafana, karma, promlens) MUST stamp `org.telemetron.service: telemetron` + `org.telemetron.job: <role>` labels per the convention re-affirmed in `roles/README.md`. Plan 04-01 dropped hook_router from the Phase 4 Gate-7 list.
- **No vault keys added in Phase 4.** Phase 5 will add `vault_grafana_admin_password`; the existing forward-reference in `vault.yml.example` flags this clearly.

**Outstanding items (not blockers):**
- Live UAT execution against operator's homelab Docker host (D-69 verify suite -- the embedded `roles/alertmanager/tasks/verify.yml` runs as the final task of `--tags alertmanager`).
- ALERT-V2-01..05 (hook router design) preserved in `.planning/phases/04-alert-plane/04-DISCUSSION-LOG.md` for the future milestone that picks it up.

## Self-Check: PASSED

**Created files verified to exist:**
- FOUND: roles/alertmanager/defaults/main.yml
- FOUND: roles/alertmanager/tasks/main.yml
- FOUND: roles/alertmanager/tasks/verify.yml
- FOUND: roles/alertmanager/handlers/main.yml
- FOUND: roles/alertmanager/templates/alertmanager.yml.j2
- FOUND: roles/alertmanager/meta/main.yml
- FOUND: roles/alertmanager/README.md
- FOUND: inventory/example-homelab/group_vars/all/alertmanager.yml

**Commits verified to exist:**
- FOUND: 15a4965 (Task 1 -- docs cascade)
- FOUND: d8809ab (Task 2 -- role scaffold)
- FOUND: fadb9ff (Task 3 -- prometheus extension)
- FOUND: 41a5565 (Task 4 -- inventory + vault cleanup)
- FOUND: 3aa3124 (Task 5 -- playbook wire)

---
*Phase: 04-alert-plane*
*Completed: 2026-05-18*
