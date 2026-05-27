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
    |       |-- storage.yml                    # volume prefix, Garage bucket names, retention defaults
    |       |-- garage.yml                     # Garage-specific operator knobs
    |       `-- secrets.yml.example            # secret placeholders (copy to secrets.yml, fill in, protect with your tool of choice)
    `-- README.md                              # this file

Per-role files live under `group_vars/all/` for each deployed component
(`garage.yml`, `loki.yml`, `tempo.yml`, `mimir.yml`, `grafana.yml`, ...).
One file per component; each tunable annotated with what it does and
what its homelab default means.

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

3. **Set up the secrets file:**

   ```bash
   cp inventory/example-homelab/group_vars/all/secrets.yml.example \
      inventory/example-homelab/group_vars/all/secrets.yml

   # Edit secrets.yml -- replace every CHANGE_ME with a strong random value.
   # secrets.yml is gitignored; secrets.yml.example is committed.

   # Protect the file. Operator's choice -- ansible-vault is the path that
   # matches the rest of this README:
   ansible-vault encrypt inventory/example-homelab/group_vars/all/secrets.yml
   # Choose a vault password when prompted; remember it.
   ```

4. **Run the playbook:**

   ```bash
   ansible-playbook -i inventory/example-homelab \
                    playbooks/deploy_docker.yml \
                    --ask-vault-pass
   ```

   Targeted re-runs use `--tags <role>`, e.g.:

   ```bash
   ansible-playbook -i inventory/example-homelab \
                    playbooks/deploy_docker.yml \
                    --tags garage \
                    --ask-vault-pass
   ```

## Secrets discipline (OPS-02)

- Naming convention: role-namespaced — `<role>_<purpose>` (e.g. `garage_admin_token`).
  No `vault_` prefix; the role namespace + descriptive suffix carry the meaning
  (per D-90 / [[feedback-no-decorative-convention-prefixes]]).
- Every sensitive `{{ <role>_<purpose> }}` reference in a role MUST have a matching
  key in `secrets.yml.example` with a `CHANGE_ME` placeholder and a comment naming
  the consuming role.
- The real `secrets.yml` is in `.gitignore`; the `.example` file ships in-repo.
- Protection mechanism is the operator's choice: ansible-vault (use
  `--ask-vault-pass`, `--vault-password-file <path>`, or
  `ANSIBLE_VAULT_PASSWORD_FILE` env var), sops, environment-variable injection,
  an external secret manager, or chmod 600 on a homelab. Telemetron documents
  keys, not mechanism.

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
