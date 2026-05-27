---
phase: 08-garage-role-backend-retargeting
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - roles/garage/defaults/main.yml
  - roles/garage/handlers/main.yml
  - roles/garage/meta/main.yml
  - roles/garage/tasks/bootstrap.yml
  - roles/garage/tasks/main.yml
  - roles/garage/templates/garage.toml.j2
  - roles/loki/defaults/main.yml
  - roles/loki/tasks/verify.yml
  - roles/loki/templates/loki.yaml.j2
  - roles/mimir/defaults/main.yml
  - roles/mimir/tasks/verify.yml
  - roles/mimir/templates/mimir.yaml.j2
  - roles/tempo/defaults/main.yml
  - roles/tempo/tasks/verify.yml
  - roles/tempo/templates/tempo.yaml.j2
  - roles/prometheus/defaults/main.yml
  - roles/prometheus/templates/prometheus.yml.j2
  - inventory/example-homelab/group_vars/all/secrets.yml.example
  - inventory/example-homelab/group_vars/all/storage.yml
  - inventory/example-homelab/group_vars/all/garage.yml
  - playbooks/deploy_docker.yml
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-05-27
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Phase 8 delivers: a new `roles/garage/` role (Garage v2.3.0 S3-compatible store), backend retargeting of Loki, Tempo, and Mimir from MinIO to Garage, D-112 credential auto-generation/persistence, a Prometheus garage scrape job, and updated verify tasks that use `docker_container_exec` instead of `mc` one-shots.

The role structure is sound and the idempotency reasoning is well-documented. Two critical issues were found: an unverified assumption about `garage key create` JSON output format that will fail at first-run boot, and an unquoted secrets variable in the Prometheus config that can produce invalid YAML depending on the token value. Five warnings cover self-referential variable definitions, a layout version freeze, a dead default variable, a file parsing failure mode, and an admin API binding inconsistency. Three info-level items round out the review.

---

## Critical Issues

### CR-01: `garage key create` output assumed to be JSON — not verified, no `--output-format` flag

**File:** `roles/garage/tasks/bootstrap.yml:163-175`

**Issue:** Step 7d runs `/garage key create -n {{ garage_s3_key_name }}` and Step 7e parses the result with `garage_key_create_result.stdout | from_json`. The research file (08-RESEARCH.md line 656) explicitly marks this as assumption A3 with MEDIUM confidence: "If output is plain text instead of JSON, parsing logic needs adjustment; UAT will confirm on first run."

In Garage v0.9 through v2.x, `garage key create` defaults to human-readable tabular output, **not JSON**. A typical output looks like:
```
Key name: telemetron
Key ID: GK...
Secret key: <secret>
```
No `--output-format json` (or equivalent) flag is present in the command. If the default output format is not JSON, `from_json` will throw a Jinja2 `AnsibleFilterError` at Step 7e on every first-run deployment. Because the credentials file does not yet exist on first run, there is no fallback path — the entire bootstrap fails and Garage will be running but misconfigured.

**Fix:** Add `--output-format json` (Garage v2 flag) to the key create command and verify the exact JSON field names (`accessKeyId` / `secretAccessKey`) against the v2.3.0 image before shipping. If the flag is not available in v2.3.0, switch to parsing the human-readable output or use `garage key import` with pre-generated credentials from `secrets.yml`.

```yaml
# Step 7d (corrected):
    command: /garage key create -n {{ garage_s3_key_name }} --output-format json
```

If `--output-format` is unavailable in v2.3.0, use `grep` + `awk` to extract key ID and secret from the tabular output instead of `from_json`.

---

### CR-02: Prometheus template renders `garage_admin_token` without YAML quoting

**File:** `roles/prometheus/templates/prometheus.yml.j2:94`

**Issue:** The garage scrape job renders the admin token without quotes:
```yaml
    authorization:
      credentials: {{ garage_admin_token }}
```

The `secrets.yml.example` describes `garage_admin_token` as "an arbitrary string, recommend 32+." If the operator chooses a token that starts with `{`, `[`, `*`, `&`, contains `: `, or any other YAML special character sequence, the rendered `prometheus.yml` will be syntactically invalid YAML. Prometheus will fail to start or reject the config with a parse error. A token beginning with `#` (valid shell comment character) would silently truncate the credentials line.

All other token/secret values in the Garage TOML template use TOML double-quote strings (`admin_token = "{{ garage_admin_token }}"`), making TOML parsing safe — only the Prometheus YAML rendering is unguarded.

**Fix:** Add quotes:
```yaml
      credentials: "{{ garage_admin_token }}"
```

---

## Warnings

### WR-01: Self-referential `*_publish_host` defaults cause recursive variable error without inventory override

**Files:**
- `roles/garage/defaults/main.yml:29`
- `roles/loki/defaults/main.yml:28`
- `roles/mimir/defaults/main.yml:25`
- `roles/tempo/defaults/main.yml:31`
- `roles/prometheus/defaults/main.yml:21`

**Issue:** Every role contains a self-referential defaults entry of the form:
```yaml
garage_publish_host: "{{ garage_publish_host | default(false) }}"
```
Ansible's `| default(filter)` does not break infinite recursion for variables that reference themselves — it evaluates to the current value of the same variable, which in `defaults/` is the Jinja expression itself. Ansible raises `recursive loop detected in template string` when this is evaluated without a higher-precedence definition.

This works today only because the example inventory explicitly overrides every `*_publish_host` to `false` (e.g. `inventory/example-homelab/group_vars/all/garage.yml:14`). An operator who creates a minimal inventory without these overrides — a valid use case — will hit a confusing recursive template error on first run.

**Fix:** Replace with a plain false literal in defaults:
```yaml
garage_publish_host: false
```
If per-environment override is needed, operators use their own `group_vars`. The defaults file should contain the bare default, not a self-referential expression.

---

### WR-02: `garage layout apply --version 1` hard-coded — silently no-ops on layout capacity/zone changes

**File:** `roles/garage/tasks/bootstrap.yml:94-101`

**Issue:** Step 6 runs:
```yaml
    command: /garage layout apply --version 1
```
with `when: garage_layout_show.rc != 0 or 'NO ROLE ASSIGNED' in garage_layout_show.stdout`.

This gate is correct for first-run idempotency. However, if an operator later changes `garage_layout_zone` or `garage_layout_capacity` in their inventory (e.g. expanding capacity from 1G to 10G), the gate will **not** fire on re-run (the node has a zone already; `'NO ROLE ASSIGNED'` will not appear). The layout change is staged but never applied. Garage silently continues with the old layout.

Additionally, `--version 1` hard-codes the layout generation. Garage's layout versioning is monotonically increasing; if a manual `garage layout apply --version 2` has ever been run on the target (e.g. during recovery), the next Ansible-driven apply at `--version 1` will fail with a version conflict.

**Fix:** Detect the current layout version dynamically and apply at `version+1`, or add a documented "manual step required" warning in the role README for capacity/zone changes. At minimum, the hard-coded `--version 1` should be a variable:
```yaml
garage_layout_version: 1   # increment manually after first deploy if re-applying layout
```

---

### WR-03: Credential file parsing uses `| first` on potentially empty list — crashes on malformed file

**File:** `roles/garage/tasks/bootstrap.yml:138-153`

**Issue:** Step 7c parses the credentials file with:
```yaml
garage_s3_access_key_id: >-
  {{
    (garage_creds_raw.content | b64decode).split('\n')
    | select('match', '^key_id=')
    | first
    | regex_replace('^key_id=', '')
  }}
```
If `garage_s3_credentials_file` exists but is malformed (empty file, truncated write from a failed previous run, missing `key_id=` line), `select('match', '^key_id=')` returns an empty list and `| first` raises `jinja2.exceptions.UndefinedError: No first item, the sequence was empty`. The task fails with a cryptic Jinja error rather than a useful diagnostic message.

The same applies to the `secret=` line parse for `garage_s3_secret_key`.

**Fix:** Add a default fallback or an explicit check before `first`:
```yaml
garage_s3_access_key_id: >-
  {{
    (garage_creds_raw.content | b64decode).split('\n')
    | select('match', '^key_id=')
    | list
    | first | default('')
    | regex_replace('^key_id=', '')
  }}
```
Then add a subsequent assertion task to fail with a clear error if either fact is empty after loading from the file.

---

### WR-04: Dead default variable `mimir_ooo_time_window` — documented but not wired into template

**Files:** `roles/mimir/defaults/main.yml:76`, `roles/mimir/templates/mimir.yaml.j2` (absent)

**Issue:** `roles/mimir/defaults/main.yml` defines:
```yaml
mimir_ooo_time_window: 30m
```
The mimir.yaml.j2 template contains no reference to this variable. The template comment at line 41–44 explicitly notes that `out_of_order_time_window` was removed from the `tsdb:` block because it moved to `limits:` in Mimir 3.0. However, the limits block at the bottom of the template (lines 82–85) also does not include `out_of_order_time_window`. The default variable is therefore dead code.

The `roles/mimir/README.md` documents `mimir_ooo_time_window: "30m"` as an active knob, compounding the confusion: operators who set this variable in inventory will see no effect.

**Fix:** Either add `out_of_order_time_window: {{ mimir_ooo_time_window }}` under the `limits:` block in `mimir.yaml.j2`, or remove `mimir_ooo_time_window` from both `defaults/main.yml` and the README.

---

### WR-05: Garage admin API binds `0.0.0.0` while S3 API binds `[::]` — IPv6 gap on dual-stack hosts

**File:** `roles/garage/templates/garage.toml.j2:19,31`

**Issue:**
```toml
[s3_api]
api_bind_addr = "[::]:{{ garage_api_port }}"   # binds IPv4+IPv6

[admin]
api_bind_addr = "0.0.0.0:{{ garage_admin_port }}"   # binds IPv4 only
```
On a dual-stack Docker host, `[::]:3900` receives S3 traffic on both IPv4 and IPv6. The admin API on `0.0.0.0:3903` only binds IPv4. The Prometheus garage scrape job targets `garage:3903` via the Docker bridge network (IPv4 DNS alias), so in practice this works. But the inconsistency means that if the Prometheus container or another admin API consumer ever resolves `garage` to an IPv6 address (possible in future Docker networking changes), the scrape will fail with `connection refused` while S3 traffic continues working.

**Fix:** Make the admin API bind address consistent with the S3 API:
```toml
[admin]
api_bind_addr = "[::]:{{ garage_admin_port }}"
```

---

## Info

### IN-01: `s3_web` section in `garage.toml.j2` uses hardcoded port 3902, no variable

**File:** `roles/garage/templates/garage.toml.j2:25`

**Issue:** The `[s3_web]` section contains `bind_addr = "[::]:3902"` with no corresponding `garage_web_port` variable in `defaults/main.yml`. All other ports (`garage_api_port`, `garage_rpc_port`, `garage_admin_port`) are variables. The S3 web endpoint is not used by any Telemetron component, but the hardcoded port creates an inconsistency — operators who need to change this port cannot do so without editing the template directly.

**Fix:** Add `garage_web_port: 3902` to `roles/garage/defaults/main.yml` and reference it in the template.

---

### IN-02: Credential fact has no runtime assertion when isolated tag run skips Garage bootstrap

**Files:** `inventory/example-homelab/group_vars/all/secrets.yml.example:42-57`

**Issue:** The inventory S3 credential aliases:
```yaml
loki_s3_access_key: "{{ garage_s3_access_key_id }}"
mimir_s3_access_key: "{{ garage_s3_access_key_id }}"
tempo_s3_access_key: "{{ garage_s3_access_key_id }}"
```
These resolve to Ansible facts set by `roles/garage/tasks/bootstrap.yml`. If an operator runs `--tags loki` without running `--tags garage` first (e.g. on a second-day config-only re-run), `garage_s3_access_key_id` is undefined, causing a Jinja2 `undefined variable` error when the Loki config template renders. The error message points to the Loki template, not to the missing Garage bootstrap, which will be confusing.

The READMEs document this dependency, but there is no runtime assertion in the Loki/Tempo/Mimir roles to surface a clear message.

**Fix:** Add an assertion at the top of each backend's `tasks/main.yml`:
```yaml
- name: Assert Garage S3 credentials are loaded
  ansible.builtin.assert:
    that:
      - garage_s3_access_key_id is defined
      - garage_s3_access_key_id | length > 0
    fail_msg: >
      garage_s3_access_key_id is not defined. Run the garage role first
      (ansible-playbook ... --tags garage) to bootstrap S3 credentials.
```

---

### IN-03: `playbooks/deploy_docker.yml` has no `vars_files:` or assertion for `secrets.yml`

**File:** `playbooks/deploy_docker.yml`

**Issue:** The playbook references `garage_admin_token`, `garage_rpc_secret`, and `grafana_admin_password` from `secrets.yml`, which must be populated by the operator. The playbook does not validate that `secrets.yml` has been created from the example, nor does it fail early if variables are at their `CHANGE_ME` placeholder values. A first-time operator who forgets to copy and populate `secrets.yml` will get a container that starts with `garage_admin_token: CHANGE_ME` — a security misconfiguration that will not produce an obvious error at deploy time.

**Fix:** Add a pre_tasks assertion block:
```yaml
- name: Assert required secrets are set
  ansible.builtin.assert:
    that:
      - garage_admin_token is defined
      - garage_admin_token != 'CHANGE_ME'
      - garage_rpc_secret is defined
      - garage_rpc_secret != 'CHANGE_ME'
    fail_msg: "Secrets not configured. Copy secrets.yml.example to secrets.yml and fill in all CHANGE_ME values."
```

---

_Reviewed: 2026-05-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
