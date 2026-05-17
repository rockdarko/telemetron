# Telemetron -- example-homelab inventory

Fully-worked single-host Docker example inventory. Clone, edit one or two
values, run the playbook, end up with a working observability stack on a
single Docker host.

## What's in here

    example-homelab/
    |-- hosts.yml                              # single-host `telemetron` group
    |-- group_vars/
    |   `-- all/
    |       |-- network.yml                    # telemetron_network, publish default, TZ
    |       |-- storage.yml                    # volume prefix, MinIO bucket names, retention defaults
    |       |-- minio.yml                      # MinIO-specific operator knobs
    |       `-- vault.yml.example              # vault placeholders (copy to vault.yml, fill in, encrypt)
    `-- README.md                              # this file

Phase 2 onward will add per-role files under `group_vars/all/` as the
roles land (`loki.yml`, `tempo.yml`, `mimir.yml`, `grafana.yml`, ...).
Same pattern as `minio.yml` -- one file per component, each tunable
annotated with what it does and what its homelab default means.

## Quickstart

1. **Clone the repo** (you've done this).

2. **Optionally edit `hosts.yml`** to target a remote Docker host instead
   of the Ansible control host:

   ```yaml
   homelab:
     ansible_host: my-docker-host.example.com   # was: localhost
     ansible_user: rock                         # was: $USER
     # remove `ansible_connection: local`
   ```

   Default behavior (no edit) runs against the Ansible control host
   itself via local connection.

3. **Set up the vault file:**

   ```bash
   cp inventory/example-homelab/group_vars/all/vault.yml.example \
      inventory/example-homelab/group_vars/all/vault.yml

   # Edit vault.yml -- replace every CHANGE_ME with a strong random value.
   # vault.yml is gitignored; vault.yml.example is committed.

   ansible-vault encrypt inventory/example-homelab/group_vars/all/vault.yml
   # Choose a vault password when prompted; remember it.
   ```

4. **Run the playbook** (Phase 1 ships the MinIO role only; Phases 2-6
   add the rest):

   ```bash
   ansible-playbook -i inventory/example-homelab \
                    playbooks/deploy_docker.yml \
                    --ask-vault-pass
   ```

   Targeted re-runs use `--tags <role>`, e.g.:

   ```bash
   ansible-playbook -i inventory/example-homelab \
                    playbooks/deploy_docker.yml \
                    --tags minio \
                    --ask-vault-pass
   ```

## Vault discipline (OPS-02)

- Naming convention: `vault_<role>_<purpose>` (e.g. `vault_minio_root_password`).
- Every `{{ vault_* }}` reference in a role MUST have a matching key in
  `vault.yml.example` with a `CHANGE_ME` placeholder and a comment naming
  the consuming role.
- The real `vault.yml` is in `.gitignore`; the `.example` file ships in-repo.
- Vault password sources: `--ask-vault-pass` (interactive),
  `--vault-password-file <path>`, or the `ANSIBLE_VAULT_PASSWORD_FILE` env var.

## Prerequisites

The `community.docker` Ansible collection must be installed on the control host:

```bash
ansible-galaxy collection install community.docker
```

## Bring your own inventory

If you already maintain inventory elsewhere, symlink it in:

```bash
ln -s /path/to/your/inventory inventory/myenv
```

Add the symlink to your local `.git/info/exclude` if it points outside
the repo and you don't want it tracked.
