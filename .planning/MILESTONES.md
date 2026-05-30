# Milestones

## v1.2.0 Operator Undeploy Path (Shipped: 2026-05-30 on leviathan)

**Phases:** 3 (10 + 11 + 12) | **Plans:** 15 | **Commits:** 76 since v1.1.0 |
**Files modified:** 65 | **LOC delta:** +5,833 / -43 | **Timeline:** 2026-05-28 → 2026-05-30 (3 days)

### What shipped

A homelab operator who deployed Telemetron with `playbooks/deploy_docker.yml`
can now run the symmetric `playbooks/undeploy_docker.yml` against the same
inventory and cleanly remove the stack from the host without `docker prune`
brute force or hand-by-hand container/network/volume teardown. The default
run removes containers + the `telemetron` Docker bridge network and
preserves named volumes, host dirs, and pinned images. Three opt-in flags
unlock irreversible cleanup — `telemetron_purge_data` (named Docker
volumes), `telemetron_purge_host_dirs` (`/opt/telemetron/`), and
`telemetron_purge_images` (pinned images) — each gated by a per-action
WARNING line and a PLAY-start banner that summarises what will and will
not be destroyed. Idempotency holds: a second `undeploy` against an
already-clean host produces `changed=0`. The complete undeploy story is
discoverable through a 3-concentric-layer doc cascade — root README →
`docs/quickstart.md#removing-telemetron` → per-role `## Uninstall`
sections — so an operator never needs to read source code or run `--help`.

### Key accomplishments

- **Per-role uninstall surface (Phase 10)** — every deploy role
  (alertmanager, fluentbit, garage, grafana, karma, loki, mimir,
  node_exporter, opentelemetry, prometheus, tempo) plus opt-in nfsd
  ships a `tasks/uninstall.yml`. Each file removes its container
  (`state: absent`, `keep_volumes: true`) and its role-private
  `/opt/telemetron/<role>/` config dir while preserving the named data
  volume. Codified as **Gate 10** in `roles/README.md` — "every deploy
  role ships a tested uninstall path" — so future role additions
  inherit the contract.

- **Reverse-order undeploy orchestrator (Phase 11)** —
  `playbooks/undeploy_docker.yml` mirrors `deploy_docker.yml` in
  reverse, with the same `--ask-vault-pass` UX, `--tags <role>`
  targeted-re-run pattern, and `inventory/example-homelab` /
  `inventory/leviathan` compatibility. D-160 PLAY-start banner
  surfaces what each flag combination will do BEFORE any destructive
  task fires (category descriptions, not name enumeration).

- **Opt-in purge flag contract with D-159 WARN template (Phase 11)** —
  every irreversible per-role task is preceded by a separately-named
  debug WARN whose `msg` matches `WARNING: irreversible -- <role>
  <action>: <targets>` exactly. Each role's `tasks/purge.yml` follows
  the canonical 5-task volume+image shape (3-task variant for image-only
  roles: karma, node_exporter, opentelemetry); Garage's two-volume loop
  (`garage_meta` + `garage_data`) and Grafana/Loki's two-image loops
  (role primary + shared `curlimages/curl`) handle the special cases
  with `failed_when: false` + post-skip WARN per D-154.

- **Live UAT on leviathan with G-01 + G-02 closed end-to-end (Phase 11)** —
  7-scenario human UAT covering conservative undeploy + D-146 self-recovery
  proof, back-to-back idempotency (OPS-01), partial-deploy simulation
  (D-164), each purge flag individually (4a/4b/4c), and the all-3-flags
  fresh-start path (OPS-02 second clause). Garage S3 key recovery branch
  (length==1 reuse vs length>=2 explicit failure with operator workaround)
  validated against the actual `garage key list` v2 output format —
  surfaced two regex regressions mid-UAT (column-count + key-name-charset)
  that the planner/checker/reviewer chain all missed; encoded the
  finding in `.claude/projects/.../memory/project_garage_key_list_format.md`
  for future Garage work.

- **Three-layer documentation cascade (Phase 12)** — `docs/quickstart.md`
  gains a 120-line `## Removing Telemetron` section covering the default
  conservative cmd, all 3 purge flags with example invocations, order-of-
  operations sequencing, and the manual `docker volume rm` /
  `docker image rm` fallback. Root README gets the "When you're done
  evaluating" cross-ref (D-174 verbatim). Each of the 12 role READMEs
  gets a new `## Uninstall` H2 — 11 uniform per the D-170 template
  (placed between `## Volumes` and `## Healthcheck`), nfsd diverges per
  D-172 with an explicit "does NOT remove" block (OS packages,
  `nfs-server.service`, `/srv/telemetron-nfs/`). `roles/README.md`
  Gate 10 closing paragraph rewritten per D-175 to reflect Phase 11's
  "no Gate 11" outcome.

- **Quality-bar findings encoded for next milestone** — the live UAT on
  leviathan caught regressions the static verifier never would,
  reinforcing the v1.1.0 lesson that ansible deploy/undeploy phases need
  a real live-deploy gate beyond the planner→checker→executor chain. Two
  regex regressions in Plan 11-06 (`fix(11-06): widen key-list regex
  to \S+` and `fix(11-06): skip Created column when regex-matching`)
  emerged only when a human ran the playbook against a live Garage v2
  container; both were committed during UAT and merged before milestone
  close.

### Requirements traceability

8 / 8 v1.2.0 requirements validated across Phases 10/11/12. Full
traceability table preserved in the archived
`milestones/v1.2.0-REQUIREMENTS.md`.

### Known deferred items at close: 4

(see STATE.md `## Deferred Items` section — all 4 are status-field /
quick-task drift from already-archived v1.0 / v1.1 milestones; no
v1.2.0 work was deferred.)

### Known debt carried forward (tracked for v1.3.0 milestone)

- **Backup / restore for stateful volumes** (`BACKUP-V13-01..04`) —
  Garage S3 data + metadata, Prometheus TSDB, Grafana SQLite, Alertmanager
  state. Reference: deferred-by-design from v1.2.0 scope; backup is
  operator-responsibility today.

- **Preflight check playbook** (`PREFLIGHT-V13-*`) — "is this host ready /
  does it have prior Telemetron state?" surface; quickstart hand-waves
  the question today.

- **`docker_doctor` health-probe playbook** — diagnose-failed-deploys
  surface for operators who hit a partial state mid-deploy.

- **Hook router (Flask + Jenkins `buildWithParameters` auth)** —
  `ALERT-V2-01..05` still deferred from v1.0; no v1.2.0 work added to
  this thread.

- **Distributed / scale-out path + HAProxy + Kube/OpenShift deploy** —
  `DIST-01..03`, multi-arch `ARCH-01..02`, doc deep-dives `DOCS-V2-*` —
  all still deferred per PROJECT.md.

---

## v1.0.0 — M1 — LGTM observability plane on Docker

**Shipped:** 2026-05-19 (on `leviathan` — Ubuntu 24.04, Docker 29.1.3)
**Phases:** 7 active (1, 2, 3, 4, 04.1, 5, 6) + 4 backlog (999.x deferred to v2)
**Plans:** 26 plans, 110 tasks
**Codebase:** ~12,254 LOC across 139 files in `roles/` + `playbooks/` + `inventory/` + `docs/`
**Commits:** 171 (from `05ef1f8` to `b5eccb3`)
**Timeline:** 2026-05-16 → 2026-05-19 (4 days)

### What shipped

A homelab operator can clone the repo, edit one hostname + SSH-user in
`inventory/example-homelab/`, supply a vault password, run a single
`ansible-playbook` command, and have a complete LGTM observability plane
(Loki + Grafana + Tempo + Mimir + Prometheus + OTel Collector + Fluent Bit +
node_exporter + Alertmanager + Karma + PromLens + MinIO + optional nfsd) come
up on a single Docker host. A synthetic OTLP log + metric + trace pushed to
`:4318` is visible in Grafana within 60 seconds. The full deploy is idempotent
(`changed=0` on the second back-to-back run, both for the 13-role default and
the 14-role `enable_nfsd: true` shape).

### Key accomplishments

- **13 Ansible roles ported + 1 opt-in (nfsd as 14th slot)** from the upstream
  INSPQ stack to clean-slate, English-only, MIT-licensed code — every role
  passes the 8 cross-cutting port-acceptance gates (`roles/README.md`).

- **Three monolithic backends ported** with explicit S3 wiring to MinIO:
  Loki 3.7.2 (`loki-chunks`), Tempo 2.10.5 (`tempo-traces`), Mimir 3.0.6 (the
  trinity `mimir-blocks` / `mimir-ruler` / `mimir-alerts`). All three use
  `-target=all` and the conditional-HEALTHCHECK `-version` pattern.

- **OTel Collector Contrib 0.152.0 as the single ingest gateway** —
  OTLP gRPC `:4317` + HTTP `:4318` fanning to Loki (otlphttp), Tempo (otlp gRPC),
  and Prometheus-or-Mimir; Tempo's native OTLP receivers moved to internal-only
  alt ports `:14317`/`:14318` to avoid the port clash.

- **Grafana 13.0.1 OSS with 4 hardcoded-UID datasources** (`prometheus`,
  `loki`, `tempo`, `mimir`) and 7 curated dashboards covering host-health,
  explore landings, and stack self-metrics; trace ↔ log correlation wired via
  Tempo `tracesToLogsV2` + Loki `derivedFields` on `trace_id`.

- **`playbooks/smoke_test.yml` as the M1 acceptance probe** — synthetic OTLP
  log + metric + trace asserted through Grafana's datasource-proxy within a
  60s budget per signal; passes on leviathan including loud-failure mode and
  tag-scoped single-signal runs.

- **Three operator docs authored against the booted stack** —
  `docs/architecture.md` (component reference + signal flow + 17-row port
  table), `docs/quickstart.md` (zero-to-dashboards walkthrough proven verbatim
  on a fresh host), `docs/inventory.md` (9-key secrets contract + symlink
  pattern + multi-host v2 callout).

- **Two famous bugs caught and fixed in live UAT, encoded as gates**:
  (1) docker_container `auto_remove:true + detach:false` race (ansible/ansible#45272)
      → rewired to `docker_container_exec` polling across 9+ verify.yml files;
  (2) moby/moby#6011 single-file rendered-config bind-mount stale-inode
      → 12 surfaces collapsed to 7 parent-directory mounts; Gate 8 added to
      `roles/README.md` so future ports inherit the convention.

### Known debt at ship (tracked for v2)

- **MinIO** pinned to the archived community release `RELEASE.2025-04-22T22-12-26Z`
  with a loud README note. Garage migration queued as a v2 milestone.

- **Hook router** (Flask + per-rule allowlist + per-tuple rate limit + Jenkins
  buildWithParameters auth) deferred to v2 — tracked as `ALERT-V2-01..05` in
  the archived `v1.0.0-REQUIREMENTS.md`. Phase 4 design preserved in the
  archived `04-DISCUSSION-LOG.md`.

- **PromLens** ships pinned at `v0.3.0` and marked deprecation-candidate in
  its role README — Prometheus 3 absorbs its tree-view surface.

- **amd64-only**; arm64 + Apple Silicon support is a candidate for a later
  milestone (all chosen base images publish arm64 but the testing surface
  was amd64 on leviathan).

- **Monolithic-mode only** for Loki/Tempo/Mimir; distributed mode + HAProxy
  + multi-host inventory are deferred to a later milestone.
- **Backlog 999.x phases** (4 items: mimir blocks_retention re-wire, tempo
  block_ranges_period cleanup, fluentbit timestamp_fallback FB-4 syntax,
  fluentbit label-spec-vs-OTel-reality alignment) — captured during M1
  execution for v2 picking.

### Decimal phase

- **Phase 04.1 (INSERTED)**: rename every `vault_*`-prefixed sensitive variable
  to its role-namespaced unprefixed form across 4 roles + `secrets.yml.example`
  rename + doc cascade. Reason: the prefix added no value and implied tooling
  enforcement Ansible doesn't provide (D-90 in Phase 5 CONTEXT).

### Archived artifacts

- `.planning/milestones/v1.0.0-ROADMAP.md` — full phase details + plan list
- `.planning/milestones/v1.0.0-REQUIREMENTS.md` — all 37 v1 requirements with outcomes
- `.planning/milestones/v1.0.0-phases/` — every shipped phase's plans/summaries/UAT/verification

---
