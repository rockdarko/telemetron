#!/usr/bin/env python3
"""
roles/grafana/files/_rewrite_uids.py

Fork-time helper for substituting upstream dashboard datasource template
variables for Telemetron's hardcoded UIDs (D-77 + RESEARCH §3 per-dashboard
substitution map).

This script is committed alongside the JSONs it generates so the
substitution is reproducible. It is NOT executed at container runtime
(D-74 "no runtime download" -- all seven JSONs land on disk pre-rewritten).

When upstream mixin shapes change in a future Telemetron version, refresh
the JSONs by re-downloading sources and re-running this script -- a
deliberate maintenance task, not a recurring role task.

Usage:
  python3 roles/grafana/files/_rewrite_uids.py \\
      --src-dir /tmp/upstream-dashboards \\
      --dest-dir roles/grafana/files/dashboards

The --src-dir is expected to contain the FIVE upstream JSONs
(unmodified, as fetched from their source URLs):
  - dashboard-1860-rev45.json            (Grafana.com 1860 rev 45 -- node-exporter-full)
  - dashboard-15983-rev29.json           (Grafana.com 15983 rev 29 -- OTel Collector)
  - dashboard-loki-operational.json      (grafana/loki v3.7.2)
  - tempo-operational.json               (grafana/tempo v2.10.5)
  - mimir-overview.json                  (grafana/mimir mimir-3.0.6)

Source URLs (RESEARCH §3 table):
  https://grafana.com/api/dashboards/1860/revisions/45/download
  https://grafana.com/api/dashboards/15983/revisions/29/download
  https://raw.githubusercontent.com/grafana/loki/v3.7.2/production/loki-mixin/dashboards/dashboard-loki-operational.json
  https://raw.githubusercontent.com/grafana/tempo/v2.10.5/operations/tempo-mixin/dashboards/tempo-operational.json
  https://raw.githubusercontent.com/grafana/mimir/mimir-3.0.6/operations/mimir-mixin-compiled/dashboards/mimir-overview.json
"""

import argparse
import json
import os
import sys


# Per RESEARCH §3 table + OQ-4:
# All five upstream dashboards have datasource template variables that
# Telemetron substitutes for hardcoded UID references at fork time.
#
# OQ-4 NOTE: Mimir overview's $datasource is the PROMETHEUS scraper that
# collects Mimir's :9009/metrics self-metrics (NOT the Mimir datasource as
# long-term store). UID -> prometheus.
#
# Loki operational dashboard uses RAW STRINGS "$datasource" / "$loki_datasource"
# (no template vars defined in JSON) -- requires string-level replace,
# substituting in JSON objects per Type B procedure in RESEARCH §3.
SUBSTITUTIONS = {
    "dashboard-1860-rev45.json": {
        "output": "host-health.json",
        "type": "template_var",
        "vars": {"DS_PROMETHEUS": "prometheus"},
        "uid_refs": {"${DS_PROMETHEUS}": {"type": "prometheus", "uid": "prometheus"}},
    },
    "dashboard-15983-rev29.json": {
        "output": "otel-collector-self-metrics.json",
        "type": "template_var",
        "vars": {"datasource": "prometheus"},
        "uid_refs": {"${datasource}": {"type": "prometheus", "uid": "prometheus"}},
    },
    "dashboard-loki-operational.json": {
        "output": "loki-self-metrics.json",
        "type": "raw_string",
        "string_subs": {
            '"$datasource"': '{"type":"prometheus","uid":"prometheus"}',
            '"$loki_datasource"': '{"type":"loki","uid":"loki"}',
        },
    },
    "tempo-operational.json": {
        "output": "tempo-self-metrics.json",
        "type": "template_var",
        "vars": {"ds": "prometheus", "logsds": "loki"},
        "uid_refs": {
            "${ds}": {"type": "prometheus", "uid": "prometheus"},
            "${logsds}": {"type": "loki", "uid": "loki"},
        },
    },
    "mimir-overview.json": {
        "output": "mimir-self-metrics.json",
        "type": "template_var",
        # OQ-4: $datasource is the Prometheus scraper of Mimir self-metrics
        # (NOT the Mimir long-term store).
        "vars": {"datasource": "prometheus"},
        "uid_refs": {"${datasource}": {"type": "prometheus", "uid": "prometheus"}},
    },
}


def rewrite_template_var(src_path, dest_path, vars_map, uid_refs):
    """Type A: proper Grafana template variables.

    1. Load JSON.
    2. Remove the template variable entries from .templating.list whose .name
       matches a key in vars_map.
    3. Walk .panels recursively, replacing any datasource ref whose .uid
       matches the template-var form with the hardcoded {type, uid} dict.
    """
    with open(src_path) as f:
        d = json.load(f)

    # 1. Filter templating.list to remove the substituted datasource vars
    if "templating" in d and "list" in d["templating"]:
        d["templating"]["list"] = [
            v for v in d["templating"]["list"]
            if v.get("type") != "datasource" or v.get("name") not in vars_map
        ]

    # 2. Walk panels (and nested rows.panels) substituting datasource.uid
    def walk(obj):
        if isinstance(obj, dict):
            if "datasource" in obj and isinstance(obj["datasource"], dict):
                uid = obj["datasource"].get("uid")
                if uid in uid_refs:
                    obj["datasource"] = dict(uid_refs[uid])
            # Older format: datasource is a string
            if "datasource" in obj and isinstance(obj["datasource"], str):
                if obj["datasource"] in uid_refs:
                    obj["datasource"] = dict(uid_refs[obj["datasource"]])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(d)

    with open(dest_path, "w") as f:
        json.dump(d, f, indent=2, sort_keys=True)
        f.write("\n")


def rewrite_raw_string(src_path, dest_path, string_subs):
    """Type B: raw-string substitution for jsonnet-generated dashboards
    that left literal `"$datasource"` strings without template vars."""
    with open(src_path) as f:
        content = f.read()
    for src, replacement in string_subs.items():
        content = content.replace(src, replacement)
    # Re-parse + pretty-print to confirm validity
    d = json.loads(content)
    with open(dest_path, "w") as f:
        json.dump(d, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src-dir", required=True, help="Directory containing the FIVE upstream JSONs.")
    parser.add_argument("--dest-dir", default="roles/grafana/files/dashboards", help="Output directory for rewritten JSONs.")
    args = parser.parse_args()

    os.makedirs(args.dest_dir, exist_ok=True)

    for src_name, cfg in SUBSTITUTIONS.items():
        src_path = os.path.join(args.src_dir, src_name)
        dest_path = os.path.join(args.dest_dir, cfg["output"])
        if not os.path.exists(src_path):
            print(f"SKIP (source missing): {src_path}", file=sys.stderr)
            continue
        if cfg["type"] == "template_var":
            rewrite_template_var(src_path, dest_path, cfg["vars"], cfg["uid_refs"])
        elif cfg["type"] == "raw_string":
            rewrite_raw_string(src_path, dest_path, cfg["string_subs"])
        print(f"WROTE: {dest_path}")


if __name__ == "__main__":
    main()
