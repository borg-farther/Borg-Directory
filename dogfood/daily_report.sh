#!/bin/bash
#
# Borg V3 Fleet Daily Report
# ============================
# Runs sync_fleet.sh first, then reads the central DB and outputs a
# text summary: total outcomes, success rate, per-node breakdown,
# per-pack rates, drift alerts.
#
# Usage:
#   ./daily_report.sh              # today's report
#   ./daily_report.sh --yesterday   # yesterday's window
#   ./daily_report.sh --json        # machine-readable JSON output
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CENTRAL_DB="${HOME}/.borg/borg_v3.db"
REPORT_MODE="today"
JSON_OUTPUT="false"

log() { echo -e "\033[0;36m[REPORT]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yesterday) REPORT_MODE="yesterday"; shift ;;
        --json)     JSON_OUTPUT="true"; shift ;;
        *)          log "Unknown flag: $1"; shift ;;
    esac
done

# ---------------------------------------------------------------------------
# Compute time window
# ---------------------------------------------------------------------------
get_window() {
    python3 << 'PYEOF'
import datetime

mode = "today"  # default from bash

now = datetime.datetime.utcnow()
if mode == "yesterday":
    end_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_dt - datetime.timedelta(days=1)
else:
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now

print(f"{start_dt.timestamp()}|{end_dt.timestamp()}|{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}|{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}")
PYEOF
}

# ---------------------------------------------------------------------------
# Ensure central DB has schema
# ---------------------------------------------------------------------------
ensure_schema() {
    CENTRAL_DB="${CENTRAL_DB}" python3 << PYEOF
import sqlite3, os

db = os.path.expanduser("${CENTRAL_DB}")
os.makedirs(os.path.dirname(db), exist_ok=True)

conn = sqlite3.connect(db)
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS outcomes (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        pack_id      TEXT    NOT NULL,
        agent_id     TEXT,
        task_category TEXT   NOT NULL,
        success      INTEGER NOT NULL,
        tokens_used  INTEGER DEFAULT 0,
        time_taken   REAL    DEFAULT 0.0,
        timestamp    TEXT    NOT NULL,
        hostname     TEXT    DEFAULT 'unknown'
    )
""")

try:
    c.execute("ALTER TABLE outcomes ADD COLUMN hostname TEXT DEFAULT 'unknown'")
except sqlite3.OperationalError:
    pass

c.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_hostname ON outcomes(hostname)")
conn.commit()
conn.close()
PYEOF
}

# ---------------------------------------------------------------------------
# Fetch report data and compute metrics
# ---------------------------------------------------------------------------
generate_report() {
    local window_info="$1"
    local start_ts=$(echo "$window_info" | cut -d'|' -f1)
    local end_ts=$(echo "$window_info" | cut -d'|' -f2)
    local start_dt=$(echo "$window_info" | cut -d'|' -f3)
    local end_dt=$(echo "$window_info" | cut -d'|' -f4)

    CENTRAL_DB="${CENTRAL_DB}" python3 << PYEOF
import sqlite3, os, json, sys
from datetime import datetime, timezone

db = os.path.expanduser("${CENTRAL_DB}")
start_ts = float("${start_ts}")
end_ts = float("${end_ts}")

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Fetch outcomes in window (timestamp is ISO8601 string, compare as strings)
c.execute("""
    SELECT * FROM outcomes
    WHERE timestamp >= ? AND timestamp <= ?
    ORDER BY id DESC
""", ("${start_dt}", "${end_dt}"))
rows = [dict(r) for r in c.fetchall()]

total = len(rows)
successes = sum(1 for r in rows if r['success'])
failures = total - successes
success_rate = (successes / total * 100) if total > 0 else 0.0

# Per-node breakdown
c.execute("""
    SELECT hostname,
           COUNT(*) as cnt,
           ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
    FROM outcomes
    WHERE timestamp >= ? AND timestamp <= ?
    GROUP BY hostname
    ORDER BY cnt DESC
""", ("${start_dt}", "${end_dt}"))
per_node = {r['hostname']: {'count': r['cnt'], 'rate': r['rate']} for r in c.fetchall()}

# Per-pack breakdown
c.execute("""
    SELECT pack_id,
           COUNT(*) as cnt,
           ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate,
           SUM(tokens_used) as tokens
    FROM outcomes
    WHERE timestamp >= ? AND timestamp <= ?
    GROUP BY pack_id
    ORDER BY cnt DESC
    LIMIT 20
""", ("${start_dt}", "${end_dt}"))
per_pack = []
for r in c.fetchall():
    per_pack.append({
        'pack_id': r['pack_id'],
        'count': r['cnt'],
        'rate': r['rate'],
        'tokens': r['tokens'] or 0
    })

# Per-task_category breakdown
c.execute("""
    SELECT task_category,
           COUNT(*) as cnt,
           ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
    FROM outcomes
    WHERE timestamp >= ? AND timestamp <= ?
    GROUP BY task_category
    ORDER BY cnt DESC
""", ("${start_dt}", "${end_dt}"))
per_category = []
for r in c.fetchall():
    per_category.append({
        'category': r['task_category'],
        'count': r['cnt'],
        'rate': r['rate']
    })

# Drift alerts: packs with <40% success rate over last 20 outcomes (global)
c.execute("""
    SELECT pack_id, hostname, COUNT(*) as n,
           ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
    FROM (SELECT * FROM outcomes ORDER BY id DESC LIMIT 20)
    GROUP BY pack_id, hostname
    HAVING rate < 40
    ORDER BY rate ASC
""")
drift_alerts = []
for r in c.fetchall():
    drift_alerts.append({
        'pack_id': r['pack_id'],
        'hostname': r['hostname'],
        'recent_outcomes': r['n'],
        'recent_success_rate': r['rate']
    })

# Token stats
c.execute("""
    SELECT SUM(tokens_used) as total_tokens, AVG(time_taken) as avg_time
    FROM outcomes
    WHERE timestamp >= ? AND timestamp <= ?
""", ("${start_dt}", "${end_dt}"))
stats_row = c.fetchone()
total_tokens = stats_row['total_tokens'] or 0 if stats_row else 0
avg_time = stats_row['avg_time'] or 0.0 if stats_row else 0.0

conn.close()

result = {
    "report": {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_start": "${start_dt}",
        "window_end":   "${end_dt}",
        "mode":         "${REPORT_MODE}",
    },
    "summary": {
        "total_outcomes": total,
        "successes":      successes,
        "failures":       failures,
        "success_rate_pct": round(success_rate, 1),
        "total_tokens":   total_tokens,
        "avg_time_seconds": round(avg_time, 2),
    },
    "per_node":     per_node,
    "per_pack":     per_pack,
    "per_category": per_category,
    "drift_alerts": drift_alerts,
}

print(json.dumps(result, indent=2, default=str))
PYEOF
}

# ---------------------------------------------------------------------------
# Render text report (reads from temp JSON file)
# ---------------------------------------------------------------------------
render_text() {
    local json_file="$1"

    python3 << PYEOF
import json

with open("${json_file}") as f:
    data = json.load(f)

r  = data["report"]
s  = data["summary"]
pn = data["per_node"]
pp = data["per_pack"]
pc = data["per_category"]
da = data["drift_alerts"]

W = 65

def rule(): print("=" * W)
def space(): print()

rule()
print(f"  Borg V3 Fleet — Daily Report")
print(f"  Window : {r['window_start']} → {r['window_end']}")
print(f"  Generated: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
rule()
space()

# ---- KPIs ----
print(f"  OUTCOMES")
print(f"    Total     : {s['total_outcomes']:>6}")
print(f"    Success   : {s['successes']:>6}  ({s['success_rate_pct']}%)")
print(f"    Failed    : {s['failures']:>6}")
space()

print(f"  PERFORMANCE")
print(f"    Total tokens : {s['total_tokens']:>12,}")
print(f"    Avg time (s)  : {s['avg_time_seconds']:>10.2f}")
space()

# ---- Per-node ----
if pn:
    print(f"  PER NODE")
    hdr = f"    {'Node':<28} {'Count':>7} {'Success Rate':>13}"
    print(hdr)
    print(f"    {'-'*28} {'-'*7} {'-'*13}")
    for node, vals in sorted(pn.items(), key=lambda x: -x[1]['count']):
        print(f"    {str(node):<28} {vals['count']:>7} {vals['rate']:>12.1f}%")
    space()

# ---- Per-pack ----
if pp:
    print(f"  TOP PACKS (by use count)")
    hdr = f"    {'Pack ID':<30} {'Uses':>6} {'Rate':>8} {'Tokens':>10}"
    print(hdr)
    print(f"    {'-'*30} {'-'*6} {'-'*8} {'-'*10}")
    for p in pp:
        print(f"    {p['pack_id']:<30} {p['count']:>6} {p['rate']:>7.1f}% {p['tokens']:>10,}")
    space()

# ---- Per-category ----
if pc:
    print(f"  PER TASK CATEGORY")
    hdr = f"    {'Category':<25} {'Count':>7} {'Rate':>9}"
    print(hdr)
    print(f"    {'-'*25} {'-'*7} {'-'*9}")
    for c_item in pc:
        print(f"    {c_item['category']:<25} {c_item['count']:>7} {c_item['rate']:>8.1f}%")
    space()

# ---- Drift alerts ----
if da:
    print(f"  DRIFT ALERTS  (packs with <40% success in recent 20 outcomes)")
    hdr = f"    {'Pack ID':<30} {'Node':<15} {'N':>4} {'Rate':>7}"
    print(hdr)
    print(f"    {'-'*30} {'-'*15} {'-'*4} {'-'*7}")
    for a in da:
        print(f"    {a['pack_id']:<30} {str(a['hostname']):<15} {a['recent_outcomes']:>4} {a['recent_success_rate']:>6.1f}%")
    space()
else:
    print(f"  DRIFT ALERTS  : none")
    space()

rule()
print(f"  End of report")
rule()
PYEOF
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log "Running fleet sync first..."
    "${SCRIPT_DIR}/sync_fleet.sh" || warn "Sync had errors — continuing with existing data"

    log "Generating report..."
    ensure_schema

    WINDOW=$(get_window)
    local tmp_json
    tmp_json=$(mktemp /tmp/borg_report_XXXXXX.json)

    generate_report "${WINDOW}" > "${tmp_json}"

    if [[ "${JSON_OUTPUT}" == "true" ]]; then
        cat "${tmp_json}"
    else
        render_text "${tmp_json}"
    fi

    rm -f "${tmp_json}"
}

main
