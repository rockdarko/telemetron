# Phase 05 Deferred Items


## 05-06 deferred (out-of-scope -- belongs to 05-05)

**Gate 9.5 bash syntax error in `roles/grafana/tasks/verify.yml`:**
- Symptom: `ansible-playbook --tags grafana` fails at "Gate 9.5 -- assert no provisioned dashboard has unresolved $datasource panel refs" with `syntax error near unexpected token '|'`.
- Cause: shell variable `${ds_prometheus}` inside a Jinja-rendered `set -o pipefail` heredoc-like block, paired with multi-line continuation, gets the `|` literally interpreted.
- Scope: pre-existing in the verify.yml file 05-06 did not modify; 05-05 is the parallel agent owning verify.yml; out-of-scope for 05-06 per deviation rules.
- Status: 05-06's static checks (zero upstream UIDs in deployed file) succeed regardless -- the dashboard file ships to leviathan correctly before the gate fires.
