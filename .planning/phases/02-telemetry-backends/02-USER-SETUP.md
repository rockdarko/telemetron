# Phase 2: User Setup Required

**Generated:** 2026-05-17
**Phase:** 02-telemetry-backends
**Status:** Incomplete

Complete these items for Loki (and subsequent Phase 2 backends) to function on the homelab Docker host. Claude has automated everything possible inside the role and inventory; these items require the operator's hand on the local vault file.

## Account Setup

None. Loki, Tempo, and Mimir consume the MinIO root credentials provisioned in Phase 1 (per D-09 + D-27 aliases). No new external accounts.

## Vault Keys (real values land in vault.yml, not vault.yml.example)

After running this plan, you must extend the **real** `inventory/example-homelab/group_vars/all/vault.yml` (the one in `.gitignore`, decrypted via `ansible-vault edit`) with the two new keys declared by the plan in `vault.yml.example`:

| Status | Key | Value source | File |
|--------|-----|--------------|------|
| [ ] | `vault_loki_s3_access_key` | Same value as `vault_minio_root_user` (already in vault from Phase 1) | `inventory/example-homelab/group_vars/all/vault.yml` |
| [ ] | `vault_loki_s3_secret_key` | Same value as `vault_minio_root_password` (already in vault from Phase 1) | `inventory/example-homelab/group_vars/all/vault.yml` |

Per D-27, these are deliberate aliases. The exact YAML to paste matches what is shown in `vault.yml.example`:

```yaml
vault_loki_s3_access_key: "{{ vault_minio_root_user }}"
vault_loki_s3_secret_key: "{{ vault_minio_root_password }}"
```

Re-encrypt with:

```bash
ansible-vault edit inventory/example-homelab/group_vars/all/vault.yml
# paste the two keys, save
```

## Verification

After completing setup, on the control host:

```bash
# 1. Confirm the vault contains the two new keys
ansible-vault view inventory/example-homelab/group_vars/all/vault.yml | grep -E 'vault_loki_s3_(access|secret)_key'

# 2. Syntax-check the playbook with the vault file resolved
ansible-playbook --syntax-check \
  -i inventory/example-homelab \
  playbooks/deploy_docker.yml \
  --ask-vault-pass

# 3. Run the loki role end-to-end against your homelab Docker host
ansible-playbook \
  -i inventory/example-homelab \
  playbooks/deploy_docker.yml \
  --tags loki \
  --ask-vault-pass

# 4. Confirm container health on the homelab host
docker inspect loki --format '{{.State.Health.Status}}'   # expects: healthy

# 5. Confirm the verify push landed a chunk in MinIO
docker run --rm --network telemetron \
  -e MC_HOST_local="http://<minio_root_user>:<minio_root_password>@minio:9000" \
  minio/mc:RELEASE.2025-04-22T16-23-26Z \
  mc ls --json --recursive local/loki-chunks   # expects: >=1 object key

# 6. Idempotency check (OPS-04): re-run; PLAY RECAP must show changed=0
ansible-playbook \
  -i inventory/example-homelab \
  playbooks/deploy_docker.yml \
  --tags loki \
  --ask-vault-pass
```

Expected:
- Step 1 prints both keys aliased to `vault_minio_root_user` / `vault_minio_root_password`.
- Step 3 runs without error; the verify task in the role passes (D-32 push + bucket assert).
- Step 4 returns `healthy`.
- Step 5 returns at least one object key (Loki chunk).
- Step 6 reports `changed=0` (or `changed=1` only on the very first deploy after a fresh image pull).

---

**Once all items complete:** Mark status as "Complete" at top of file.
