# Phase 8: Garage Role + Backend Retargeting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 08-garage-role-backend-retargeting
**Areas discussed:** Credential surface, Metrics scrape placement, Backend verify migration, Storage var naming

---

## Credential surface

### Q1: Admin token naming

| Option | Description | Selected |
|--------|-------------|----------|
| garage_admin_token | Direct and specific. Matches Garage's own GARAGE_ADMIN_TOKEN env var. Follows the 'no decorative prefix' rule (D-90). | ✓ |
| garage_admin_secret | Slightly more generic — signals it's a secret without tying the name to the upstream env var name. | |
| You decide | Claude picks based on existing naming patterns in the codebase. | |

**User's choice:** garage_admin_token

### Q2: Per-backend alias pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Single shared key | Bootstrap creates ONE Garage API key. All three backends alias to it. Same operational simplicity as MinIO root-cred sharing. Per-backend keys deferred (same as D-27). | ✓ |
| Per-backend keys now | Bootstrap creates 3 separate Garage API keys. More secure but more bootstrap complexity and more vars in secrets.yml. | |
| You decide | Claude picks based on M1/v1.1.0 scope. | |

**User's choice:** Single shared key

### Q3: Key origin

| Option | Description | Selected |
|--------|-------------|----------|
| Operator supplies key in secrets.yml | Operator defines garage_s3_access_key_id and garage_s3_secret_key in secrets.yml.example. Bootstrap uses /garage key import. | |
| Bootstrap generates and extracts | Bootstrap runs /garage key create, captures output, registers as Ansible facts. | ✓ |
| You decide | Claude picks based on Garage's CLI capabilities. | |

**User's choice:** Bootstrap generates and extracts
**Notes:** Follow-up question about idempotency — Garage only reveals the S3 secret at creation time.

### Q4: Key persistence across re-runs

| Option | Description | Selected |
|--------|-------------|----------|
| Persist to host file | Bootstrap writes the generated key ID + secret to a file on the host. Re-runs check the file first. | ✓ |
| Hybrid: generate first, import after | First run: /garage key create. Re-runs: /garage key import with persisted values. | |
| Switch to operator-supplied key | Let the operator define the key in secrets.yml. Bootstrap uses /garage key import. Fully idempotent. | |

**User's choice:** Persist to host file

---

## Metrics scrape placement

### Q1: Scrape job location

| Option | Description | Selected |
|--------|-------------|----------|
| Prometheus hardcoded job | Add a 4th default scrape job in prometheus role's rendered config. Matches the existing pattern. Always on. | ✓ |
| Prometheus extra_scrape_configs | Ship as example in inventory. Operator can customize or remove. | |
| OTel Collector prometheus receiver | Add a prometheus receiver in OTel Collector config. Changes OTel role's scope. | |
| You decide | Claude picks based on existing patterns. | |

**User's choice:** Prometheus hardcoded job

### Q2: Bearer token flow

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in rendered config | Prometheus authorization.credentials in scrape config embeds {{ garage_admin_token }} directly. | ✓ |
| File reference | Write token to separate file, Prometheus uses authorization.credentials_file. Marginally more secure. | |
| You decide | Claude picks based on how sensitive vars are handled in other roles. | |

**User's choice:** Inline in rendered config

### Q3: Toggle for Garage scrape job

| Option | Description | Selected |
|--------|-------------|----------|
| No toggle, always on | Consistent with existing three default jobs. Simpler config surface. | ✓ |
| Conditional on garage_metrics_enabled | Adds a knob but breaks the unconditional precedent. | |

**User's choice:** No toggle, always on

---

## Backend verify migration

### Q1: Verify tool after minio/mc removal

| Option | Description | Selected |
|--------|-------------|----------|
| docker_container_exec against Garage | Run /garage bucket info inside running Garage container. Uses admin token. Follows Phase 4 canonical pattern. | ✓* |
| curl against Garage S3 API | Use S3 ListObjectsV2 via curl with AWS Signature v4. Portable but SigV4 signing in shell is painful. | |
| Drop object-level verify | Remove mc checks; rely on smoke_test.yml for E2E data flow. Simpler but loses per-role assertion. | |
| You decide | Claude picks based on verify task complexity vs. value. | ✓ |

**User's choice:** You decide
**Notes:** Claude recommended docker_container_exec. Rationale: follows Phase 4 pattern, uses available admin token, preserves per-role assertion value.

### Q2: Add Tempo S3 verify for consistency

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add Tempo S3 verify | All three backends get consistent Garage bucket checks. | ✓ |
| No, match existing scope | Only migrate existing checks (Loki + Mimir). | |
| You decide | Claude picks based on scope discipline. | |

**User's choice:** Yes, add Tempo S3 verify

---

## Storage var naming

### Q1: Bucket list variable

| Option | Description | Selected |
|--------|-------------|----------|
| telemetron_garage_buckets | Specific to Garage. Honest about what it configures. | ✓ |
| telemetron_storage_buckets | Generic, storage-agnostic. Future swaps don't rename vars. | |
| You decide | Claude picks based on naming conventions. | |

**User's choice:** telemetron_garage_buckets

### Q2: Inventory file rename

| Option | Description | Selected |
|--------|-------------|----------|
| garage.yml | Direct replacement. Matches role name. | ✓ |
| storage.yml merge | Merge Garage knobs into existing storage.yml. One file for all storage concerns. | |
| You decide | Claude picks based on existing inventory layout. | |

**User's choice:** garage.yml

### Q3: Per-backend S3 alias target

| Option | Description | Selected |
|--------|-------------|----------|
| Alias to garage_s3_access_key_id | Each backend's S3 vars default to {{ garage_s3_access_key_id }}. Direct Garage coupling. | ✓ |
| Alias to a generic telemetron_s3_* | Introduce telemetron_s3_* as intermediaries. One more level of indirection. | |
| You decide | Claude picks based on indirection tradeoffs. | |

**User's choice:** Alias to garage_s3_access_key_id

---

## Claude's Discretion

- **D-117 verify tool:** User deferred the verify tool choice. Claude recommended `docker_container_exec` against Garage over curl S3 API and dropping checks entirely. Rationale: follows Phase 4 canonical pattern, avoids fragile SigV4 signing, preserves per-role S3 assertion.

## Deferred Ideas

None — discussion stayed within phase scope.
