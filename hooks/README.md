# Hooks

The hook router was originally planned as part of Telemetron M1
(`ALERT-02..06`) -- a Flask service bridging Alertmanager webhooks to
Jenkins `buildWithParameters` calls, with a per-rule allowlist,
per-`(alertname, job)` rate limit, and a vault-supplied outbound token.

**Status: deferred to a future milestone.**

Mid-M1 discussion concluded that Jenkins-as-target was no longer the
right pitch for 2026 and that re-framing the router as
backend-agnostic (generic webhook -> CI / automation) is a larger
reshape than M1 should absorb. The deferred design -- including the
two-tier `hook_router_backends` / `hook_router_rules` schema, the
shared-secret inbound auth header, the in-memory rate limit, and the
observability surface -- is captured in
`.planning/phases/04-alert-plane/04-DISCUSSION-LOG.md` for the
milestone that picks it up.

See `.planning/REQUIREMENTS.md` `## v2 Requirements` -- `ALERT-V2-01`
through `ALERT-V2-05` -- for the planned shape. The `hooks/` directory
survives as institutional memory; this README is its only content
until v2.

In M1, Alertmanager (`roles/alertmanager/` -- Phase 4) ships with a
single default `null` receiver. Alerts are visible in the Alertmanager
UI and (via Phase 5) in Karma but are not dispatched to anything
automatically. Operators wire their own receivers via
`alertmanager_extra_receivers` in inventory.

M1 does NOT build this image.
