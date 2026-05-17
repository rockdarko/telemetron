# Playbooks

Top-level orchestration. Two deployment targets:

- `deploy_docker.yml` — Docker / VM deployment
- `deploy_kube.yml` — Kubernetes / OpenShift deployment

Both will be populated as roles land. Today: skeleton only.

## Running

```bash
ansible-playbook -i ../inventory/<env> playbooks/deploy_docker.yml
ansible-playbook -i ../inventory/<env> playbooks/deploy_kube.yml
```

Target a single component via tags + limit:

```bash
ansible-playbook -i ../inventory/<env> --tags loki --limit loki playbooks/deploy_docker.yml
```
