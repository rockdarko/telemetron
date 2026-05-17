# Inventory

One directory per environment. Telemetron is inventory-agnostic — point any environment at any hosts you want.

## Expected shape

```
<env-name>/
├── <env-name>.hosts        # the inventory file
├── group_vars/
│   ├── all.yml
│   ├── grafana.yml
│   ├── loki_monolithic.yml
│   ├── tempo_monolithic.yml
│   ├── prometheus.yml
│   ├── mimir.yml
│   ├── alertmanager.yml
│   ├── fluentbit.yml
│   ├── otel.yml
│   └── ...
└── host_vars/
    └── <hostname>.yml
```

## Bring your own inventory

If you already maintain inventory elsewhere, symlink it in:

```bash
ln -s /path/to/your/inventory inventory/myenv
```

Add the symlink to your local `.git/info/exclude` if it points outside the repo and you don't want it tracked.

## Example envs

Shipped examples will land here as the roles do. None yet.
