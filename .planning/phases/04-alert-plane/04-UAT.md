---
status: complete
phase: 04-alert-plane
source: [04-VERIFICATION.md, 04-HUMAN-UAT.md]
started: 2026-05-18T23:35:00Z
updated: 2026-05-19T00:44:38Z
runner: claude
target: leviathan (root@leviathan via inventory/leviathan)
---

## Current Test

[testing complete -- 6 pass, 0 issues; both bugs closed by plan 04-02 gap closure]

## Tests

### 1. First-run deploy + HEALTHCHECK reports healthy
expected: |
  Run on leviathan:
    ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags alertmanager,prometheus
  Then:
    docker inspect telemetron-alertmanager --format '{{.State.Health.Status}}'
  Expected:
    - PLAY RECAP: failed=0, unreachable=0
    - HEALTHCHECK status: healthy
result: pass
fixed_by: plan-04-02 (Bug 1 TIER 1 -- docker_container_exec rewrite + Bug 1 TIER 2 meta:flush_handlers)
evidence: |
  Post-04-02 re-run on leviathan 2026-05-19T00:42Z:
    PLAY RECAP: leviathan : ok=30 changed=2 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0
    docker inspect telemetron-alertmanager --format '{{.State.Health.Status}}' -> "healthy"
  The new step-5 docker_container_exec + until: pattern avoids the
  auto_remove race entirely (Docker exec API returns exit code synchronously);
  the flush_handlers task before include_tasks: verify.yml guarantees the
  prometheus restart handler fires before the cross-role probe runs.
  Container metadata at probe time:
    - HEALTHCHECK status: healthy
    - RestartPolicy: unless-stopped
    - Labels: org.telemetron.service=telemetron, org.telemetron.job=alertmanager

### 2. /api/v2/receivers null-receiver assertion
expected: |
  docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://alertmanager:9093/api/v2/receivers | jq
  Expected: payload exactly [{"name":"null"}]
result: pass
evidence: |
  $ ssh leviathan 'docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://alertmanager:9093/api/v2/receivers'
  [{"name":"null"}]
  Exit 0.

### 3. /api/v2/status route knobs (D-61)
expected: |
  curl /api/v2/status; grep config.original for:
    - group_by: [alertname, cluster, service]
    - group_wait: 30s
    - group_interval: 5m
    - repeat_interval: 4h
  Plus inhibit_rules with NEW source_matchers/target_matchers syntax (D-63 + Research Q2).
result: pass
evidence: |
  $ ssh leviathan 'docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://alertmanager:9093/api/v2/status'
  Parsed .config.original contains (verbatim excerpt):
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
    receivers:
    - name: "null"
  All four route knobs present; corrected source_matchers/target_matchers syntax confirmed live.

### 4. Prometheus -> Alertmanager round-trip (D-64)
expected: |
  docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://prometheus:9090/api/v1/alertmanagers
  Expected: .data.activeAlertmanagers[0].url == "http://alertmanager:9093/api/v2/alerts"
result: pass
fixed_by: plan-04-02 (Bug 2 FIX A -- parent-directory bind mounts + meta:flush_handlers belt-and-suspenders)
evidence: |
  Post-04-02 re-run on leviathan 2026-05-19T00:42Z (fresh deploy, no manual rescue):
    $ ssh leviathan 'docker run --rm --network telemetron curlimages/curl:8.10.1 -fsS http://prometheus:9090/api/v1/alertmanagers'
    {"status":"success","data":{"activeAlertmanagers":[{"url":"http://alertmanager:9093/api/v2/alerts"}],"droppedAlertmanagers":[]}}
  Inode-pinning regression check (parent-directory mount works):
    Host    inode (sudo stat -c '%i' /opt/telemetron/prometheus/prometheus.yml)              : 524589
    Container inode (docker exec ... stat -c '%i' /etc/prometheus/prometheus.yml)            : 524589
    Host    md5                                                                              : 47d84aceddde83f32a6e6e6a41ec81a2
    Container md5                                                                            : 47d84aceddde83f32a6e6e6a41ec81a2
    SAME on both sides -- no stale-inode pin.
  Definitive proof of parent-directory mount semantics (manual atomic-rename simulation):
    Before manual `cp foo foo.new && mv foo.new foo`:
      Host inode 524589 / Container inode 524589
    After manual atomic-rename:
      Host inode 2097216 / Container inode 2097216 (container picks up NEW inode immediately)
    With the old single-file bind mount, container would have remained on inode 524589.
  Bug 2 verifiably closed.

### 5. amtool synthetic alert + silence (D-69) + D-62 volume persistence
expected: |
  docker exec amtool alert add alertname=TestAlert; query lists it.
  silence add alertname=PersistenceTest; query lists silence.
  docker restart telemetron-alertmanager; silence query STILL lists the silence (proves /alertmanager named-volume persistence).
result: pass
evidence: |
  alert add: success (no error output, exit 0)
  alert query:
    Alertname  Starts At                Summary  State
    TestAlert  2026-05-18 23:49:27 UTC           active
  silence add: returned ID 66144467-7cf2-40ef-94d1-c6bf6f8ffc4c
  silence query (pre-restart): lists silence with matcher alertname="PersistenceTest", Created By nobody
  docker restart telemetron-alertmanager + 12s settle
  silence query (post-restart): SAME silence still listed with same ID -- D-62 persistence confirmed via named volume telemetron_alertmanager_data on /alertmanager.

### 6. Gate 4 idempotency: second --tags alertmanager reports changed=0
expected: |
  ansible-playbook -i inventory/leviathan playbooks/deploy_docker.yml --tags alertmanager
  Expected: PLAY RECAP changed=0
result: pass
evidence: |
  PLAY RECAP: leviathan : ok=17 changed=0 unreachable=0 failed=0 skipped=0
  All 7 verify steps (HEALTHCHECK poll + /-/ready + /api/v2/receivers + /api/v2/status + Prom->AM round-trip + amtool alert add/query + silence add/query) pass on the second run because Prometheus is now properly registered (post-restart in Test 4). Idempotency: clean -- config render tasks ok (not changed), container run task ok (not changed), no handler triggered.
  Note: Test 1's auto_remove race does NOT recur here because the Prom->AM probe loop exits on iteration 1 (wiring already established), so the container terminates before Docker's reap can race the module's exit-code read. Bug is fresh-deploy-only.

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

closed_by: plan-04-02 (gap closure 2026-05-19)

## Gaps

- alertmanager-verify-prom-am-probe-auto-remove-race:
    status: closed
    closed_by: plan-04-02 task-1 (TIER 1 docker_container_exec rewrite) + task-2 (TIER 2 meta:flush_handlers in prometheus + alertmanager tasks/main.yml)
    description: |
      `roles/alertmanager/tasks/verify.yml` step 5 ("Curl-probe Prometheus /api/v1/alertmanagers") uses `community.docker.docker_container` with `auto_remove: true` + `detach: false` and a `while ... sleep 2; done` shell loop that polls for up to 60s. On fresh deploys the loop runs to (or near) its 30-iteration timeout. When the container exits, Docker reaps it (auto_remove) before the Ansible module can read the exit code, producing fatal "Cannot retrieve result as auto_remove is enabled" and PLAY RECAP failed=1. The wiring being probed is fine; the probe pattern is fragile.
      Manifests Tests 1 and 4 (Test 4 cascades from Test 1's mid-play fatal halting handler flush).
    severity_before_fix: blocker
    test: [1, 4]
    diagnosis: |
      Two-layer root cause (see .planning/debug/alertmanager-verify-prom-am-probe-auto-remove-race.md):
      PRIMARY: documented community.docker bug (GH ansible/ansible#45272, #47673) -- `detach: false` + `auto_remove: true` races the module's exit-code read against Docker's reaper. Persists in community.docker 4.5.0. Race probability scales with in-container runtime; the 30-iter*2s loop maximizes the window when its early-exit-0 path isn't hit.
      SECONDARY (trigger): no `meta: flush_handlers` anywhere in playbooks/deploy_docker.yml or any role's tasks/main.yml. The prometheus `restart prometheus` handler queues on the cross-role template change but doesn't fire until end-of-play. Alertmanager role runs in the same play AFTER prometheus, so verify.yml step 5 probes a still-stale Prometheus, the loop runs the full 60s, exits 1, and the auto_remove race fires.
      Blast radius (10 sites, 8 roles, ALL structurally identical -- 9 are LATENT, early-exit-0 in <10s normally):
        - alertmanager/tasks/verify.yml:127  (FIRING -- Phase 4 cross-role probe)
        - node_exporter/tasks/verify.yml:70  (latent, 60s)
        - loki/tasks/verify.yml:85           (latent, 30s)
        - mimir/tasks/verify.yml:76          (latent, 60s)
        - tempo/tasks/verify.yml:73          (latent, 60s)
        - prometheus/tasks/verify.yml:66     (latent, 60s)
        - prometheus/tasks/verify.yml:100    (latent, 60s)
        - opentelemetry/tasks/verify.yml:85  (latent, 60s)
        - opentelemetry/tasks/verify.yml:194 (latent, 30s)
        - fluentbit/tasks/verify.yml:72      (latent, 60s)
    artifacts:
      - roles/alertmanager/tasks/verify.yml
      - .planning/debug/alertmanager-verify-prom-am-probe-auto-remove-race.md
    missing:
      - "TIER 1 (M1-must, single-file): Rewrite alertmanager verify.yml step 5 to use `community.docker.docker_container_exec` against the already-running telemetron-alertmanager container, calling its bundled busybox `wget --spider http://prometheus:9090/api/v1/alertmanagers`, with Ansible-native `until:`/`retries:`/`delay:` polling. Structurally race-free (Docker exec API returns exit code synchronously without container lifecycle)."
      - "TIER 2 (M1-must, defense-in-depth): Add `meta: flush_handlers` at the end of roles/prometheus/tasks/main.yml AND roles/alertmanager/tasks/main.yml, BEFORE the include_tasks: verify.yml line. This guarantees upstream restart-handlers fire before downstream verify probes run. Eliminates the entire 'verify probes stale state' bug class for Phase 4."
      - "TIER 3 (deferred, follow-up phase): Backfill the remaining 9 latent sites with the docker_container_exec + until: idiom. Out of M1 scope; latent risk that re-fires the moment another cross-role probe gets added."

- prometheus-template-rename-bind-mount-stale-inode:
    status: closed
    closed_by: plan-04-02 tasks 3-5 (Bug 2 FIX A parent-directory bind mounts across 7 roles) + task-2 (meta:flush_handlers belt-and-suspenders)
    description: |
      `roles/prometheus/tasks/main.yml` renders `/opt/telemetron/prometheus/prometheus.yml` via `ansible.builtin.template`, which atomic-renames a new inode into place. The container's Docker bind-mount of that single file (not its parent directory) pins to the old inode. After a config change, the container keeps reading the pre-change config until `docker restart` re-binds. The `restart prometheus` handler is correctly notified, but a play that fails BEFORE handler flush leaves the container in the stale-inode state. Same fragility applies to rules/baseline.yml and rules/extra.yml.
      Pure observed-on-leviathan symptom: Test 4's activeAlertmanagers came back EMPTY even though the template + defaults rendered the alerting block correctly.
    severity_before_fix: major
    test: [4]
    diagnosis: |
      Root cause (see .planning/debug/prometheus-template-rename-bind-mount-stale-inode.md):
      Linux mount-namespace + filesystem-rename interaction (moby/moby#6011, open & WONTFIX since 2014). Ansible `template:`/`copy:` default `atomic_move=true` -> write to .tmpXXXX -> rename(2) over target -> new inode. Docker bind-mounts of a SINGLE FILE pin to the original inode via kernel fd at container-start; the container mount namespace never re-resolves the directory entry. Host sees new content; container reads old.
      Aggravating factor: Ansible flushes handlers only at end-of-play. The 04-alert-plane play aborted mid-stream (because of the auto_remove race in the related gap), so the queued `restart prometheus` handler never fired -- fresh prometheus.yml with the D-64 `alerting:` block sat on disk while the container kept reading the pre-D-64 inode.
      Blast radius (7 of 9 roles afflicted, 12 distinct single-file-bind-mount config surfaces -- ALL share the canonical handler shape `Docker restart <name>` listening on `restart <role>`):
        - prometheus       (3 surfaces): prometheus.yml + rules/baseline.yml + rules/extra.yml (tasks/main.yml:125-128)
        - alertmanager     (1 surface):  alertmanager.yml via `mounts:` (tasks/main.yml:88-91)
        - loki             (1 surface):  loki.yaml (tasks/main.yml:84)
        - tempo            (1 surface):  tempo.yaml (tasks/main.yml:91)
        - mimir            (1 surface):  mimir.yaml (tasks/main.yml:88)
        - opentelemetry    (2 surfaces): config.yaml + verify-config.yaml (tasks/main.yml:121-122); only config.yaml is notify-wired
        - fluentbit        (3 surfaces): fluent-bit.conf + parsers.conf + enrich.lua (tasks/main.yml:108-110)
        - minio            (0): uses env_file (host-side slurp); not bind-mounted
        - node_exporter    (0): no config file (CLI-flag-driven)
    artifacts:
      - roles/prometheus/tasks/main.yml
      - roles/prometheus/handlers/main.yml
      - roles/alertmanager/tasks/main.yml
      - roles/loki/tasks/main.yml
      - roles/tempo/tasks/main.yml
      - roles/mimir/tasks/main.yml
      - roles/opentelemetry/tasks/main.yml
      - roles/fluentbit/tasks/main.yml
      - .planning/debug/prometheus-template-rename-bind-mount-stale-inode.md
    missing:
      - "FIX A (recommended, industry standard): Convert each of the 7 afflicted roles' bind-mount entries from `host/file:container/file:ro` to `host_dir:container_dir:ro` (mount the PARENT DIRECTORY, not individual files). Eliminates the bug class entirely -- the container's mount namespace resolves directory entries on every open(), so post-rename new inodes are picked up immediately. ~30 min of mechanical refactoring across 7 roles."
      - "Belt-and-suspenders: also add `meta: flush_handlers` at end of each afflicted role's tasks/main.yml (same as Bug 1 TIER 2 fix -- single change covers both bugs for prometheus + alertmanager). Minimizes the render-to-restart window even with the inode bug fixed."
      - "Doc gate: add a one-liner ban in roles/README.md against single-file rendered-config bind mounts to prevent reintroduction."
      - "REJECTED alternatives (documented for plan integrity): (B) `unsafe_writes: true` -- trades deterministic bug for partial-write bug; (D) force-recreate on config-hash -- fights D-19 'force-recreate is non-idempotent'; (E) Docker 2025+ flag -- moby/moby#6011 still WONTFIX, no such flag exists."
