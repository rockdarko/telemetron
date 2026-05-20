# Phase 6: Opt-in, Orchestration, Docs & Smoke Test - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 06-opt-in-orchestration-docs-smoke-test
**Areas discussed:** nfsd role shape, Smoke test shape (OPS-07), Docs scope & voice (DOCS-01/02/03/04), Plan slicing & wave order

---

## Gray Area Selection

User selected all four candidate areas via multiSelect and added an "Other" note:

> "we need to ensure that we position the nfs role as a complementary role to fluentbit to pump logs from remote hosts - challenge me on this method if you think this is not a good way of doing things"

Claude responded with: (a) endorsement of the reframing (it justifies nfsd's M1 inclusion as the legacy escape hatch for hosts that can't run OTel SDK / FB locally); (b) explicit list of 5 hazards to address in the discussion — NFS auth model, containerization brittleness, FB integration scope, INGEST-07 label allowlist break, timezone discipline for non-UTC remote hosts. The framing was accepted; the 5 hazards became the constraints that shaped subsequent decisions.

---

## nfsd role shape (LEGACY-01)

### Q1: Container vs host-package for nfsd?

| Option | Description | Selected |
|--------|-------------|----------|
| Host-package via Ansible | ansible.builtin.package installs nfs-utils (EL) / nfs-kernel-server (Ubuntu); systemd manages nfs-server; /etc/exports populated via blockinfile. Matches upstream; more reliable; deviates from D-19 (every role = container) but well-grounded. Only host-package role in M1. | ✓ |
| Containerized via erichough/nfs-server | Keeps "every role = container" uniformity. Needs --privileged + host kernel modules. Image archived 2022 (security debt). | |
| Don't ship in M1 — defer LEGACY-01 to v2 | Punt entirely. Drops M1 requirement. Breaks "all 14 roles ported" promise. | |

**User's choice:** Host-package via Ansible.

**Notes:** Reliability for an opt-in escape hatch wins over pattern uniformity for a default-off role. Deviation from D-19 documented in role README per D-91.

### Q2: What does enable_nfsd toggle, and where does the FB tail input live?

| Option | Description | Selected |
|--------|-------------|----------|
| enable_nfsd flips BOTH nfsd role + FB tail input | Single inventory knob. When true: nfsd provisions + FB renders conditional [INPUT] tail at /srv/telemetron-nfs/*/*.log with hardcoded labels. Coupling-by-design. | ✓ |
| Two separate knobs (enable_nfsd + fluentbit_tail_nfs_path) | More flexible (operator can run nfsd without FB pickup); two knobs to coordinate. | |
| Don't touch FB role — nfsd is data-plane only | Operator wires their own FB tail via fluentbit_extra_inputs. Cleanest separation; doc-heavy. | |

**User's choice:** enable_nfsd flips both.

**Notes:** "There's no honest reason to run one without the other on a Telemetron host" — coupling is correct.

### Q3: Default share path + export-list shape on the nfsd host?

| Option | Description | Selected |
|--------|-------------|----------|
| /srv/telemetron-nfs/<hostname>/ with allow-list var | Default mount root /srv/telemetron-nfs/. Sub-dirs per remote hostname for label hygiene (FB derives 'host' from path segment 1). nfsd_exports = list of {path, allow} dicts. Default []. | ✓ |
| /var/log/remote/ (FHS-traditional) | Familiar but conflicts with /opt/telemetron + /srv conventions. | |
| Operator-defined nfsd_share_root with no default | Force operator to pick. Honest but adds friction for rare opt-in. | |

**User's choice:** /srv/telemetron-nfs/<hostname>/ with allow-list var.

### Q4: NFS protocol version default?

| Option | Description | Selected |
|--------|-------------|----------|
| NFSv4 only, no Kerberos | Modern default; one-port TCP :2049; no portmapper exposure. AUTH_SYS + IP allow-list as homelab default; Kerberos = v2 hardening. | ✓ |
| NFSv3 + v4 dual-stack | Compatibility with very old clients (Solaris, AIX, ancient Linux). Larger surface. | |
| Operator-defined nfsd_protocol version | Knob exposed, default v4. Smallest opinion. | |

**User's choice:** NFSv4 only, no Kerberos.

### Q5 (check-in): More questions about nfsd, or move to next?

| Option | Description | Selected |
|--------|-------------|----------|
| Move to next area | Role shape + FB hook + share path + protocol locked. Remaining details (FB parser, systemd idempotency, README framing) are Claude's discretion. | ✓ |
| More questions about nfsd | Cover FB-derived label mapping, dual-stack vs IPv6-only, sample rsyslog snippet in docs. | |

**User's choice:** Move to next area.

---

## Smoke test shape (OPS-07)

### Q1: Where does the smoke test live and how does it run?

| Option | Description | Selected |
|--------|-------------|----------|
| Ansible playbook: playbooks/smoke_test.yml | Separate playbook. Tasks: emit synthetic log/metric/trace via curl into OTLP; assert via Grafana proxy. Pure Ansible. | ✓ |
| Shell script: scripts/smoke-test.sh | Standalone bash + curl + jq. Parallel toolchain. | |
| Doc-only walkthrough in docs/quickstart.md | No automation; 60-second budget becomes manual stopwatch. | |

**User's choice:** Ansible playbook: playbooks/smoke_test.yml.

### Q2: What 'synthetic' looks like — producer mechanism?

| Option | Description | Selected |
|--------|-------------|----------|
| curl + jq + raw OTLP/HTTP JSON | POST hand-rolled OTLP JSON to :4318/v1/{logs,metrics,traces}. Zero new deps. | ✓ |
| otel-cli (github.com/equinix-labs/otel-cli) | Purpose-built; adds binary dep. | |
| Operator's own app sending real OTLP | No synthetic generator; breaks fresh-deploy promise. | |

**User's choice:** curl + jq + raw OTLP/HTTP JSON.

### Q3: How is the 60-second deadline asserted in the smoke test?

| Option | Description | Selected |
|--------|-------------|----------|
| Grafana datasource proxy queries with retry-until | Smoke playbook queries GET /api/datasources/proxy/uid/<uid>/... with retries:12 + delay:5 (60s budget). Exercises the bundled UID path operators actually use (per ROADMAP SC3). | ✓ |
| Direct backend queries (skip Grafana proxy) | Hit Loki :3100 / Prometheus :9090 / etc. directly. Faster but doesn't exercise the bundled UID path. | |
| Pure manual: doc says 'wait, then click in Grafana' | Operator stopwatches it. Subjective; no regression catch. | |

**User's choice:** Grafana datasource proxy queries with retry-until.

### Q4: Tagging convention so smoke can opt-in/skip in M1 stack?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate playbook + --tags smoke for individual phases | smoke_test.yml is its own playbook. Three plays tagged log/metric/trace for selective runs. | ✓ |
| Append smoke play to deploy_docker.yml under --tags smoke | Single playbook; couples deploy + smoke contractually. Brittle. | |

**User's choice:** Separate playbook + --tags smoke (log/metric/trace) for individual signal runs.

---

## Docs scope & voice (DOCS-01/02/03/04)

### Q1: Voice / depth for the three docs?

| Option | Description | Selected |
|--------|-------------|----------|
| Terse reference + one teaching walkthrough | architecture.md + inventory.md = terse reference; quickstart.md = full teaching walkthrough. Splits verbose-vs-concise tax by doc purpose. | ✓ |
| All three terse-reference style | Matches roles/<name>/README.md voice. Risk: DOCS-02 'verified verbatim' gets harder. | |
| All three teaching-walkthrough style | Maximally accessible; overkill for architecture reference. | |

**User's choice:** Terse reference + one teaching walkthrough.

### Q2: architecture.md source material?

| Option | Description | Selected |
|--------|-------------|----------|
| Synthesize from .planning/research/* + CLAUDE.md + roles/*/README.md | Distill existing artifacts (port matrix in CLAUDE.md, component table in roles/README.md). Rewrite for public consumption. | ✓ |
| Write fresh from scratch | Cleaner arc; duplicates work; risks drift from validated research. | |

**User's choice:** Synthesize from existing artifacts.

### Q3: inventory.md scope vs. existing inventory/README.md + example-homelab/README.md?

| Option | Description | Selected |
|--------|-------------|----------|
| docs/inventory.md is the deep-dive; existing READMEs stay as quick orientation | Three layers: top-level inventory/README.md (1-page) + example-homelab/README.md (how to use THIS example) + docs/inventory.md (build-your-own deep dive). Cross-link aggressively. | ✓ |
| Merge inventory/README.md INTO docs/inventory.md; leave example-homelab/README.md alone | Single source. Breaks discoverability when browsing inventory/. | |
| docs/inventory.md is just a pointer to the two existing READMEs | Marks DOCS-03 done at minimum effort. Doesn't pass DOCS-03 'in depth' spirit. | |

**User's choice:** docs/inventory.md is the deep-dive.

### Q4: Top-level README.md rewrite — framing & lede?

| Option | Description | Selected |
|--------|-------------|----------|
| Pivot to 'self-hosted observability in one playbook'; INSPQ origin as paragraph 2-3 | Value-prop lede. Quickstart link in para 1. 'Status: early' deleted. Component table reflects what shipped (drop hook_router + HAProxy with v2 callouts). | ✓ |
| Keep INSPQ-fork framing; just delete the 'Status: early' line | Minimal rewrite. Doesn't reflect M1 maturity. | |

**User's choice:** Pivot to 'self-hosted observability in one playbook'.

---

## Plan slicing & wave order

### Q1: How to slice Phase 6 into plans?

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by output — 4 plans | 06-01 nfsd+FB / 06-02 smoke / 06-03 docs / 06-04 README+final. Each shippable in isolation (D-23). Mirrors D-22/D-40/D-70. | ✓ |
| One plan per requirement — 7-8 plans | Smaller blast radius; more ceremony. Fights natural co-deps (docs verify against smoke passing). | |
| One mega plan | Easiest to write; impossible to verify discretely. Loses D-22 clarity. | |

**User's choice:** Grouped by output — 4 plans.

### Q2: Wave order for the 4 plans?

| Option | Description | Selected |
|--------|-------------|----------|
| 06-01 nfsd → 06-02 smoke → 06-03 docs → 06-04 README+final | Strictly sequential. Each plan verifies the prior. Docs depend on smoke; README depends on docs. | ✓ |
| Wave 1: 06-01 ; Wave 2: 06-02 + 06-03 parallel ; Wave 3: 06-04 | Faster; docs-vs-smoke drift risk. | |
| Docs first, then nfsd + smoke | Inverts verify chain; DOCS-02 'verbatim verification' depends on running stack. | |

**User's choice:** Strict sequential.

### Q3: Does the live-UAT-on-leviathan step from prior phases continue in Phase 6?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — quickstart's 'operator runs it verbatim' acceptance happens on leviathan | Phase 5 pattern continues; 06-HUMAN-UAT.md tracks. DOCS-02 SC ('verified verbatim') maps directly to a leviathan run. | ✓ |
| Static gates only; leviathan UAT deferred to milestone-completion | Faster phase; weaker confidence. Docs in particular need a live run. | |

**User's choice:** Yes, leviathan UAT continues.

### Q4 (check-in): Done?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | All four areas covered. Write CONTEXT.md. | ✓ |
| Explore more gray areas | Surface 2-4 more. | |

**User's choice:** I'm ready for context.

---

## Claude's Discretion

Areas explicitly delegated to Claude / researcher / planner (not user-decided):

- Exact `[INPUT] tail` shape for FB NFS path (parser, Mem_Buf_Limit, multiline)
- Whether FB Lua extension is one file or two (lean: extend existing)
- Exact OTLP/HTTP JSON shape for smoke producers
- Ansible `until:` predicate syntax for smoke assertions
- Diagram format for architecture.md (lean: ASCII, no Mermaid)
- Whether quickstart.md ships a "Production hardening" subsection (lean: yes, brief)
- Whether docs cite D-XX numbers (lean: zero D-citations in public docs)
- Whether smoke playbook reads secrets.yml directly (lean: yes, vars_files)
- nfsd README header wording (planner picks)

## Deferred Ideas

Tracked in CONTEXT.md `<deferred>` section in detail. Summary:

- NFS Kerberos hardening → v2
- rsyslog/syslog-ng → NFS recipes → v2 docs
- Multi-host smoke test → v2 (HA-02)
- Synthetic alert / span-graph smoke → v2
- CI integration for smoke → v2 (TEST-01)
- 7 v2 docs (alerts/retention/timestamps/hook-router/instrumentation/migration/metrics) → DOCS-V2-01..07
- Mermaid diagrams → out (stay ASCII)
- Full production-hardening guide → v2 (brief subsection in quickstart only)
- arm64 / Pi 5 / Apple Silicon → out of scope (PROJECT.md)
- Docs hosting (GitHub Pages, etc.) → out

## Notes on the Discussion Flow

- 13 questions across 4 areas + 2 check-ins = 15 AskUserQuestion turns total.
- 0 questions answered with "Other" free-text — recommended options matched user intent on every question (one "Other" note appeared at gray-area selection asking Claude to challenge the FB+NFS framing; that was handled conversationally before the per-area questions).
- 0 deferred ideas turned into in-scope work mid-discussion (scope guardrail held).
- The 5 hazards Claude raised about the nfsd reframing all map to explicit decisions in CONTEXT.md (D-91..D-96). None remain unaddressed.
