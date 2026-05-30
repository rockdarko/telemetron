---
phase: 11-undeploy-orchestrator-safety-idempotency
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - playbooks/undeploy_docker.yml
  - roles/alertmanager/tasks/purge.yml
  - roles/fluentbit/tasks/purge.yml
  - roles/garage/tasks/purge.yml
  - roles/grafana/tasks/purge.yml
  - roles/karma/tasks/purge.yml
  - roles/loki/tasks/purge.yml
  - roles/mimir/tasks/purge.yml
  - roles/node_exporter/tasks/purge.yml
  - roles/opentelemetry/tasks/purge.yml
  - roles/prometheus/tasks/purge.yml
  - roles/tempo/tasks/purge.yml
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-05-29
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The Phase 11 undeploy surface implements a layered safety model: a top-level orchestrator (`playbooks/undeploy_docker.yml`) that reverse-traverses the 12 deploy roles, plus 11 per-role `purge.yml` files (no purge for `nfsd`, by design per D-156). The implementation broadly honours the design decisions cited in the headers — `failed_when: false` is correctly scoped to `docker_image state=absent` only (D-154), `docker_volume state=absent` is unguarded so failures surface (D-141 / D-148), per-task `when:` belt-and-suspenders is present (D-153), the D-159 `WARNING: irreversible --` prefix is grep-friendly and uniform, and the loop-vs-single-image shape matches the role inventory (grafana + loki are two-image loops; the eight others that share `curlimages/curl` are single-image; node_exporter / opentelemetry / karma are image-only because they have no named volume).

Two **BLOCKER** defects exist around the orchestrator's `post_tasks` tagging: both the bridge-network removal and the `/opt/telemetron` parent-tree removal carry `tags: always`, which means a targeted single-role invocation like `--tags garage` will silently tear down the shared bridge network (and, with `telemetron_purge_host_dirs=true`, the entire host config tree) while every other deployed role's containers are still running on that network. This breaks the "tag-scoped purge composition" contract advertised in lines 22-24 of the orchestrator header.

A WARNING-tier consistency gap exists: the header on line 5 says "12 per-role tasks/uninstall.yml files" and the comment block at 65-72 says "23 include_role calls", which is correct only if `nfsd` is counted. The nfsd uninstall is gated on `enable_nfsd | default(false)`, so the literal count of include_role tasks executed in a default homelab inventory (where `enable_nfsd: false`) is 22, not 23. This is a doc-precision issue, not a runtime defect.

## Critical Issues

### CR-01: Targeted `--tags <role>` purge tears down the shared bridge network

**File:** `playbooks/undeploy_docker.yml:277-283`
**Issue:** The post_tasks `Remove the telemetron Docker bridge network` task is tagged `[always, network]`. The header comment on lines 22-24 explicitly advertises that `--tags <role>` performs a scoped per-role undeploy. Because `tags: always` runs on every invocation regardless of `--tags`, executing `ansible-playbook ... undeploy_docker.yml --tags garage` will (a) run the `garage` uninstall + purge, then (b) unconditionally hit the `Remove the telemetron Docker bridge network` task in post_tasks, severing network connectivity for every other still-deployed role's container (loki, tempo, mimir, grafana, prometheus, alertmanager, karma, fluentbit, node_exporter, opentelemetry). `docker_network state=absent` with attached containers will either fail loudly or, depending on Docker daemon version, force-detach — either outcome silently corrupts the cluster.

The same `always` tag also makes this run on a no-flag invocation that the operator may intend as a dry-run of just the conservative uninstall path; the network is removed even when no purge flag is set. That's arguably the design intent (the comment on lines 270-271 says "after every container is gone"), but it is incompatible with targeted-role re-runs.

**Fix:** Either drop the `always` tag and rely on the implicit "runs only when no `--tags` filter is given OR `--tags network` is given" behaviour, or guard the task with an explicit "this is a full undeploy" sentinel. Recommended:

```yaml
- name: Remove the telemetron Docker bridge network
  community.docker.docker_network:
    name: "{{ telemetron_network }}"
    state: absent
  tags:
    - network
```

If the desire is for `--tags network` to remove only the network, this minimal change preserves that. The protection against accidental teardown during `--tags garage` comes from Ansible's normal tag filtering — without `always`, the task only runs when no tag filter is set OR when `network` is explicitly named. Then update the orchestrator header (lines 22-24) to call out that `--tags <role>` does NOT remove the bridge network and a full no-tag run is required to tear down the network.

---

### CR-02: Targeted `--tags <role>` purge with `telemetron_purge_host_dirs=true` nukes every other role's host config

**File:** `playbooks/undeploy_docker.yml:288-301`
**Issue:** Same defect class as CR-01, but worse. Both the `WARN -- /opt/telemetron host tree will be removed` debug task AND the `Remove /opt/telemetron parent host tree` `ansible.builtin.file: state=absent` task carry `tags: always`. Running

```
ansible-playbook ... undeploy_docker.yml \
  --tags karma --extra-vars "telemetron_purge_host_dirs=true"
```

will execute the karma uninstall/purge as expected, then ALSO hit the always-tagged parent-tree removal and recursively delete `/opt/telemetron/` — including every still-running role's bind-mounted config directory (`/opt/telemetron/grafana/`, `/opt/telemetron/loki/`, etc.). The next time grafana or loki restarts (or the operator runs `docker compose restart`, or the container's healthcheck triggers a restart), it will fail to bind-mount the now-deleted config.

The orchestrator header on lines 22-24 ("Tag-scoped purge composition (D-151): --tags <role> + purge flags scopes the purge to ONLY the tagged role's artifacts") is therefore contradicted by the orchestrator's own post_tasks for both purge_host_dirs AND the implicit network removal.

**Fix:** Drop `tags: always` from both the WARN debug and the destructive `file` task. Replace with a dedicated tag (e.g. `purge_host_dirs`) or no tag at all so the task only runs on a full unscoped invocation:

```yaml
- name: WARN -- /opt/telemetron host tree will be removed
  ansible.builtin.debug:
    msg: "WARNING: irreversible -- /opt/telemetron purge_host_dirs (parent tree)"
  when: telemetron_purge_host_dirs | default(false) | bool

- name: Remove /opt/telemetron parent host tree
  ansible.builtin.file:
    path: "{{ telemetron_config_root | default('/opt/telemetron') }}"
    state: absent
  when: telemetron_purge_host_dirs | default(false) | bool
```

Then add a guard in the header comment block (and ideally a `pre_tasks` assertion) that `telemetron_purge_host_dirs=true` is incompatible with `--tags <role>` and should only be used on a full-stack undeploy. Without an explicit guard, the documented per-role scope contract is unenforceable.

## Warnings

### WR-01: Orchestrator comment claims "12 per-role tasks/uninstall.yml" but nfsd uninstall is conditional

**File:** `playbooks/undeploy_docker.yml:5-8, 65-72`
**Issue:** Header line 5 says "Invokes 12 per-role tasks/uninstall.yml files in REVERSE of deploy_docker.yml's roles: block order". Line 65 says "23 include_role calls in literal reverse". The deploy ordering listed (garage -> loki -> tempo -> mimir -> node_exporter -> opentelemetry -> prometheus -> fluentbit -> alertmanager -> grafana -> karma -> nfsd) is 12 roles, of which `nfsd` is gated on `enable_nfsd | default(false) | bool`. With the homelab default (`enable_nfsd: false`), only 11 uninstalls + 11 purges = 22 includes actually execute. The "23" count is only correct when `enable_nfsd: true`. This is a documentation precision issue that will mislead reviewers reading the header without cross-checking the inventory default.

**Fix:** Reword to "Invokes up to 12 per-role tasks/uninstall.yml files (nfsd is opt-in via enable_nfsd) in REVERSE of deploy_docker.yml's roles: block order" and "up to 23 include_role calls (22 when enable_nfsd=false, the homelab default)".

---

### WR-02: Garage purge_data warning hides per-volume specificity inside a comma-joined msg

**File:** `roles/garage/tasks/purge.yml:66-68`
**Issue:** The WARN line emits both volume names on a single comma-separated msg:
```yaml
msg: "WARNING: irreversible -- garage purge_data: {{ garage_meta_volume }}, {{ garage_data_volume }}"
```
This is OK for human grep, but if either `garage_meta_volume` or `garage_data_volume` is undefined in an inventory override scenario, the templating yields `WARNING: irreversible -- garage purge_data: , telemetron_garage_data` (or similar) without raising an obvious error. The audit log then implies a volume was removed when nothing matched it. Compare to the loop body (lines 76-83) which iterates over `item` — Ansible WILL raise if the var is undefined inside the loop. The WARN line silently degrades, but the loop fails. Result: the audit log says "WARN about removing X" + "task succeeded" but no removal happened.

**Fix:** Either render the WARN line inside a loop matching the volume loop body so the templating contract matches, or assert both vars are defined at the top of `purge.yml`:

```yaml
- name: Assert garage purge vars are defined
  ansible.builtin.assert:
    that:
      - garage_meta_volume is defined
      - garage_data_volume is defined
    fail_msg: "garage purge.yml requires garage_meta_volume and garage_data_volume to be defined"
  when: telemetron_purge_data | default(false) | bool
  tags:
    - garage
```

---

### WR-03: Pre-task WARN banner only fires once per host, despite always-tag

**File:** `playbooks/undeploy_docker.yml:52-63`
**Issue:** The pre_tasks WARN banner shows the three purge flag states. It's tagged `always` so it displays on targeted `--tags <role>` runs. However the banner is rendered before per-role debug WARN tasks fire, and there is no terminal "summary" task at the end. If an operator runs

```
ansible-playbook ... undeploy_docker.yml --extra-vars "telemetron_purge_data=true"
```

with `-v` muted, the only audit trail of what was destroyed is the per-role WARN lines (`WARNING: irreversible -- garage purge_data: ...`) scattered through the play output. There is no post-play summary. This is not a defect per se but reduces auditability for the "irreversible" claim the headers emphasise.

**Fix:** Add a post_tasks summary debug that runs `tags: always` and lists which roles' purge sections executed. Not strictly required for ship.

---

### WR-04: `become: false` + `ansible.builtin.file state=absent` on `/opt/telemetron` may fail silently on perms

**File:** `playbooks/undeploy_docker.yml:37, 295-299`
**Issue:** Play-level `become: false` (line 37) combined with `ansible.builtin.file: path=/opt/telemetron state=absent` (line 295) requires the SSH user to have write+execute on `/opt/`. If the host's `/opt` is owned by root (the Debian default) and the operator user is not root and does not have passwordless sudo configured to elevate this single task, `state=absent` returns failed but the rest of the play may have already torn down containers and volumes. The operator's recovery story is then "files on disk but no running stack" — which is fine, but the playbook does not flag this is a probable failure mode.

The deploy side has the same `become: false` posture, so any user who could deploy can also remove. This is consistent. But the surface area for `telemetron_purge_host_dirs=true` failing on perms is bigger than for individual role config dirs (which Phase 10's per-role uninstall.yml already removed under the same user).

**Fix:** Either set `become: true` on this specific task with a comment explaining why it differs from the rest of the play, or add an `ansible.builtin.assert` pre-check that the user has write to `telemetron_config_root | dirname`. Document the expected ownership in the orchestrator header.

## Info

### IN-01: Repeated comment block across single-image purge.yml files is high-volume copy-paste

**File:** `roles/{alertmanager,fluentbit,mimir,prometheus,tempo}/tasks/purge.yml` (header comment blocks, lines 1-43 of each)
**Issue:** Five role purges (alertmanager, fluentbit, mimir, prometheus, tempo) carry near-identical 30-40 line header comment blocks describing the same D-152 / D-153 / D-154 / D-141 / D-142 / D-155 trust contract. Only the role name and small role-specific notes (fluentbit's buffer/data asymmetry on lines 21-31; mimir/prometheus/tempo's vanilla shape) differ. This is intentional per the planner's preference for inline self-documentation, but if any D-* decision is revised it must be updated in five places.

**Fix:** No code change required. Optionally, add a short reference like `# Trust contract: see .planning/phases/11-undeploy-orchestrator-safety-idempotency/11-PATTERNS.md` and trim duplicated text.

---

### IN-02: `register: <role>_purge_image_result` (singular) vs `_results` (plural) inconsistency

**File:** `roles/grafana/tasks/purge.yml:96`, `roles/loki/tasks/purge.yml:96`, vs. all other single-image roles
**Issue:** Grafana and Loki use the PLURAL `_results` because they loop. The other eight roles use SINGULAR `_result`. This is correct (Ansible's loop returns `.results[]`), and the post-WARN selection uses the right shape in each case (`.results | selectattr('failed', 'defined') | selectattr('failed') | list | length > 0` for the loops vs `result.failed | default(false)` for the singletons). Naming convention is consistent. No defect.

**Fix:** None — calling out for the reader's benefit.

---

### IN-03: `nfsd` purge is intentionally absent but only documented in the orchestrator header

**File:** `playbooks/undeploy_docker.yml:69-72`, no `roles/nfsd/tasks/purge.yml`
**Issue:** The orchestrator header on line 69 says "nfsd has uninstall-only (NO purge.yml per D-156)". Verified: `roles/nfsd/tasks/` contains `exports.yml`, `install_debian.yml`, `install_redhat.yml`, `main.yml`, `uninstall.yml` and no `purge.yml`. This is correct (nfsd is host-package + kernel NFS, not a container with a Docker image to purge). But if a future maintainer reads only the role directory and asks "where is the symmetric purge?", the answer lives only in the orchestrator comment and in `.planning/phases/11.../11-CONTEXT.md` D-156. Consider a stub `roles/nfsd/tasks/purge.yml` containing only a comment explaining why this file is intentionally absent (or document in `roles/nfsd/README.md`). Optional.

**Fix:** Optional. Add `roles/nfsd/README.md` note: "There is no purge.yml — nfsd is host-package-based, see Phase 11 D-156." Or leave as-is.

---

_Reviewed: 2026-05-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
