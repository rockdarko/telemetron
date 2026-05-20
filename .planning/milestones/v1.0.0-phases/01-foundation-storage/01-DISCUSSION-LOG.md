# Phase 1: Foundation & Storage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `01-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 1-foundation-storage
**Areas discussed:** app_web_docker shape, Bucket bootstrap pattern, Host binding & exposure, Inventory & volumes

---

## app_web_docker shape

### Q1: What is the primary shape of application_web_docker?

| Option | Description | Selected |
|--------|-------------|----------|
| Task-running base (recommended) | `include_role`-driven shared base with templated container rendering. Maximum DRY. | |
| Pure defaults provider | Only `defaults/main.yml` shared vars; roles write own docker_container tasks. | |
| Hybrid: tasks for plumbing only | Owns network + base dirs + shared facts; roles render own containers. | |
| Other (free text) | — | ✓ |

**User's choice:** "that role is something we use at INSPQ to go along any role that deploys a docker container that exposes a REST service. The idea is to deploy the container and configure an apache virtualhost behind it with an external URL. I was thinking we might want to remove that from our stuff as this is very INSPQ specific. That kind of binds users into their reverse proxy solution and I myself don'T even use it in my homelab (I use caddy). I feel like this should be out of scope as well. What do you think?"

**Notes:** Decision flipped to **drop `application_web_docker` from M1 entirely**. INSPQ used the role to pair every containerized REST service with an Apache vhost — Telemetron is reverse-proxy-agnostic by design. 16 roles → 15. (Subsequently 15 → 14 after a later question dropped Postgres.)

### Q2: Where does the `telemetron` docker network get created?

| Option | Description | Selected |
|--------|-------------|----------|
| In application_web_docker tasks (recommended) | First consuming role triggers idempotent network create. | ✓ (moot) |
| In playbooks/deploy_docker.yml pre_tasks | Playbook-level pre_task creates network. | (effective) |
| In a dedicated `network` role | 17th tiny role. | |

**User's choice:** "In application_web_docker tasks" — but with that role dropped, network creation effectively moves to **`playbooks/deploy_docker.yml` pre_tasks** (the user's listed second-choice option).

### Q3: Which Ansible module for container management?

| Option | Description | Selected |
|--------|-------------|----------|
| community.docker.docker_container (recommended) | Imperative per-container; best idempotency. | ✓ |
| community.docker.docker_compose_v2 | Declarative compose stacks; worse idempotency for stateful services. | |
| Mix — docker_container per role, compose only where useful | Inconsistency risk; no compelling M1 use case. | |

**User's choice:** community.docker.docker_container

### Q4 (follow-up): Thin shared utilities layer or zero shared layer?

| Option | Description | Selected |
|--------|-------------|----------|
| Shared via inventory group_vars only (recommended) | INV-02 group_vars/all/ holds shared knobs; roles reference. | ✓ |
| Shared Jinja macros file | playbooks/macros/container.j2; less template dup but hidden dep. | |
| Just per-role defaults, no shared layer | Maximum self-containment; minor duplication. | |

**User's choice:** Shared via inventory group_vars only

---

## Bucket bootstrap pattern

### Q1: How is the mc bucket bootstrap actually performed?

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot mc container per playbook run (recommended) | Ephemeral `minio/mc` via docker_container, `detach: false, auto_remove: true`. | ✓ |
| Loop of ansible.builtin.uri calls to MinIO S3 API | Pure-Ansible signing or boto3 dep; painful. | |
| Install mc on the target host via apt/release tarball + run shell | Host-side dep Telemetron doesn't otherwise need. | |

**User's choice:** One-shot mc container

### Q2: How do downstream backend roles wait for bootstrap?

| Option | Description | Selected |
|--------|-------------|----------|
| Playbook role ordering + mc task exit code (recommended) | Serial deploy_docker.yml; minio role exits after bootstrap returns 0. | ✓ |
| Explicit `meta: flush_handlers` + wait_for bucket existence | Belt-and-suspenders; adds ~10s. | |
| Async + register handle, check in downstream role | Premature complexity; Phase 1 is serial. | |

**User's choice:** Playbook role ordering

### Q3: mc credentials?

| Option | Description | Selected |
|--------|-------------|----------|
| MinIO root from vault (recommended) | `vault_minio_root_user` + `vault_minio_root_password` env vars. | ✓ |
| Dedicated bootstrap user with bucket-create policy | Smaller blast radius; overkill for homelab. | |

**User's choice:** MinIO root from vault

### Q4 (follow-up): How does mc wait for MinIO to be ready?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-task: ansible.builtin.uri poll `/minio/health/ready` (recommended) | Explicit Ansible until/retries pre-gate. | ✓ |
| Rely on Docker HEALTHCHECK + serial task ordering | docker_container `wait_for: healthy`. | |
| Let mc retry internally via its own backoff | Noisiest; transient errors in logs. | |

**User's choice:** Pre-task uri poll

### Q5 (follow-up): mc image pin?

| Option | Description | Selected |
|--------|-------------|----------|
| `minio/mc:RELEASE.2025-04-22T16-23-26Z` paired (recommended) | Locked with server pin; no protocol drift. | ✓ |
| `minio/mc:latest` for bootstrap only | mc forward-compat; minor drift risk. | |

**User's choice:** Paired pin

---

## Host binding & exposure

### Q1: How does Postgres expose port 5432?

| Option | Description | Selected |
|--------|-------------|----------|
| Telemetron-network only — no host publish (recommended) | Postgres invisible to host firewall; Grafana reaches via DNS. | |
| Bind to 127.0.0.1:5432 on host | Host-side `psql` convenience. | |
| Bind to 0.0.0.0:5432 — LAN-reachable | Worst default. | |
| Other (free text) | — | ✓ |

**User's choice:** "mmm where is postgres required in our setup? I suspect its out of scope"

**Notes:** Question made Rock re-examine the requirement. Result: **drop the `postgres` role from M1 entirely** (Grafana uses embedded SQLite for single-host homelab). FOUND-03 removed from REQUIREMENTS. 15 → 14 roles. Postgres becomes v2 territory only if HA Grafana lands. (See Q1a follow-up.)

### Q1a (follow-up): Drop Postgres and use SQLite?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — drop Postgres, Grafana uses SQLite (recommended) | Removes FOUND-03; 15 → 14 roles. | ✓ |
| Keep Postgres for forward-compat | Maintenance cost in M1. | |
| Make it opt-in: SQLite default, Postgres opt-in flag | Branching logic in Grafana role + postgres role + tests. | |

**User's choice:** Drop Postgres

### Q1b (follow-up): Where does the Grafana SQLite file live?

| Option | Description | Selected |
|--------|-------------|----------|
| Named Docker volume `telemetron_grafana_data` (recommended) | Matches volume-naming convention. | ✓ |
| Bind mount under /opt/telemetron/grafana/data | Operator-visible files; backup ergonomics. | |

**User's choice:** Named volume

### Q2: How does MinIO expose 9000 + 9001?

| Option | Description | Selected |
|--------|-------------|----------|
| Telemetron-network only for both (recommended) | Console via SSH local-forward. | ✓ |
| Console (:9001) on 127.0.0.1, API (:9000) network-only | Compromise. | |
| Both on 127.0.0.1 on the host | Visible from host loopback. | |

**User's choice:** Telemetron-network only for both

### Q3: Convention for ALL future service ports in Phase 2-5?

| Option | Description | Selected |
|--------|-------------|----------|
| Default = network-only; opt-in to 127.0.0.1 per-service via inventory (recommended) | `<role>_publish_host` knob per role. | ✓ |
| Per-role default judgment — UIs to 127.0.0.1, backends network-only | Less uniform; matches usage. | |
| Default everything to 0.0.0.0 | Upstream-INSPQ habit. Pitfalls-listed recurring mistake. | |

**User's choice:** Default network-only, opt-in via inventory

---

## Inventory & volumes

### Q1: What goes in each group_vars/all/ file?

| Option | Description | Selected |
|--------|-------------|----------|
| Domain split: network / storage / vault + per-role files (recommended) | One file per concern; defaults in role defaults/main.yml. | ✓ |
| Flat: one `all.yml` with everything | Easier to scan; harder to override one section. | |
| Per-role only — no domain split | Cross-cutting things end up duplicated or arbitrarily placed. | |

**User's choice:** Domain split

### Q2: Docker volume topology?

| Option | Description | Selected |
|--------|-------------|----------|
| Named Docker volumes with `telemetron_` prefix (recommended) | `docker volume ls` shows inventory; Pitfall #12 satisfied. | ✓ |
| Bind mounts under `/opt/telemetron/<role>/data` | Operator-visible files; permission choreography. | |
| Hybrid: bind mount only what humans peek at | Best of both; conventional. | |

**User's choice:** Named volumes

### Q3: Where do rendered role configs live on the host?

| Option | Description | Selected |
|--------|-------------|----------|
| Bind-mounted `/etc/telemetron/<role>/` on host (recommended) | FHS-strict; configs under /etc. | (revised) |
| Baked into container via Dockerfile/COPY | Reproducible artifact; opaque. | |
| Named volume populated at first-run, then mounted | Worst debuggability. | |

**User's choice:** Initially `/etc/telemetron/<role>/`, **revised to `/opt/telemetron/<role>/`** — Rock's homelab convention; FHS-wise `/opt` is for add-on stacks; single tree for the whole project (`tar` / `du` / `rm` friendly).

### Q4 (follow-up): Internal layout under `/opt/telemetron/<role>/`?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat: `/opt/telemetron/<role>/` holds configs directly (recommended) | Low ceremony. | ✓ |
| Sub-dirs: `/opt/telemetron/<role>/{config,logs,...}` | Forward-compat nesting. | |
| Mirror container paths: `/opt/telemetron/<role>/etc/<role>/` | Verbose; rarely useful. | |

**User's choice:** Flat

---

## Claude's Discretion

Rock deferred to Claude on:

- Exact `ansible-lint` profile (starting with `production`).
- Per-role tagging granularity (one tag per role; sub-tags only if reload-without-restart becomes useful).
- Per-role healthcheck timing details (defaults from upstream image conventions).
- Vault file split (single `vault.yml` per inventory until secret count grows past 15).
- MinIO UI knobs (`MINIO_BROWSER_REDIRECT_URL`, etc.) — defaults until an operator needs them.

---

## Deferred Ideas

Out of M1 (route to PROJECT.md "Out of Scope"):

- `application_web_docker` role (INSPQ-specific reverse-proxy binding).
- `postgres` role (no M1 consumer; Grafana uses SQLite).
- Reverse-proxy configuration / external URL exposure (operator's choice).

Future milestones:

- Per-backend MinIO access keys (hardening phase).
- MinIO replacement (Garage / SeaweedFS) — already in PROJECT.md Key Decisions.
- Backups (named volume escape hatch documented; no automated story in M1).
- HA Grafana + Postgres return.
- Vault file split if secret count grows past 15.
- Sub-tags within roles for reload-vs-restart granularity.
