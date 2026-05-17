# Hooks

Sources for the **hook router** — a Flask service that bridges Alertmanager webhooks to Jenkins (or any CI) `buildWithParameters` calls. Lets you automate runbooks from alerts (container restarts, cleanup jobs, etc.).

## Planned layout

```
router/      Flask app source + Dockerfile
jobs/        sample Jenkinsfile runbooks you can adapt
```

The router itself is deployed by `roles/hook_router/`. The job definitions are reference examples — every operator ships their own.

## Architecture

1. A Prometheus rule fires.
2. Alertmanager applies its route. A `match` on a `hook-router-*` webhook receiver triggers a POST to the router.
3. The router looks up the alert name in its rules, substitutes `{label}` tokens from the alert payload into the configured parameters.
4. It calls `POST <jenkins_url>/job/<job_path>/buildWithParameters` with vault-supplied credentials.
5. Jenkins instantiates the build.

See `docs/hook-router.md` (coming soon) for the full picture.
