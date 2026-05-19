---
status: partial
phase: 05-ui-plane
source: [05-VERIFICATION.md]
started: 2026-05-19T18:00:00Z
updated: 2026-05-19T18:00:00Z
host: leviathan
re_verification: yes
previous_round_status: complete (1 pass, 6 issues -> drove Plans 05-05/06/07/08 gap closure)
---

## Current Test

[awaiting human testing -- re-verification round after gap closure landed]

## Tests

### 1. End-to-end `ansible-playbook --tags grafana,karma,promlens` on leviathan, no --skip-tags
expected: Both first deploy and second back-to-back deploy report failed=0 across all three roles. First deploy shows changed counts as roles converge; second deploy reports changed=0 (Gate 4 idempotency).
result: [pending]

### 2. UI-04 trace-to-logs click-through with structured_metadata matcher
expected: Live OTel-instrumented traffic produces a Tempo trace and a correlated Loki log line. Click a span in Grafana Explore -> Tempo; the Logs tab shows the matching log via structured_metadata trace_id matcher. Falls back to regex matcher if the log uses body-embedded trace_id=<hex>.
result: [pending]

### 3. tempo-self-metrics dashboard renders all 74 panels against prometheus datasource
expected: Open Tempo Self-Metrics in Grafana on leviathan; all 74 panels query the provisioned prometheus datasource successfully. No 'Datasource not found' errors on any target.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

[none yet -- awaiting test results]
