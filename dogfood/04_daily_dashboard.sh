#!/bin/bash
#
# Borg V3 Dogfood - Daily Dashboard
# ==================================
# Reads the borg SQLite DB and produces a human-readable summary report.
# Also outputs machine-readable JSON for integration with monitoring tools.
#
# Reports include:
#   - Packs used (which knowledge packs were loaded and how often)
#   - Success rates (overall, per task type, per VPS)
#   - Token savings (estimated vs. baseline)
#   - Failure patterns (common error types, recurring issues)
#   - Queue health (how many tasks pending/completed/failed)
#   - Sync status (last sync time, records sent)
#
# Usage:
#   ./04_daily_dashboard.sh                # today's report
#   ./04_daily_dashboard.sh --yesterday    # yesterday's window
#   ./04_daily_dashboard.sh --json         # machine-readable output
#   ./04_daily_dashboard.sh --vps VPSTAG   # filter by VPS hostname
#   ./04_daily_dashboard.sh --since TS     # custom timestamp window (epoch)
#   ./04_daily_dashboard.sh --all         # full historical report
#
# Environment:
#   BORG_DB_PATH   — path to borg SQLite DB (default: ~/.borg/borg.db)
#   OUTPUT_DIR     — where to write JSON output (default: /opt/borg-dogfood/data)
# -----------------------------------------------------------------------------

set -euo pipefail

# ---- Configuration ----
BORG_DB_PATH="${BORG_DB_PATH:-${HOME}/.borg/borg.db}"
OUTPUT_DIR="${OUTPUT_DIR:-/opt/borg-dogfood/data}"
INSTALL_ROOT="/opt/borg-dogfood"
LOG_DIR="${LOG_DIR:-${INSTALL_ROOT}/logs}"

mkdir -p "${OUTPUT_DIR}"

# ---- CLI flags ----
REPORT_MODE="today"      # today | yesterday | all | since | json
JSON_OUTPUT="false"
VPS_FILTER=""
SINCE_TS=""
REPORT_DATE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yesterday) REPORT_MODE="yesterday"; shift ;;
        --all)      REPORT_MODE="all"; shift ;;
        --json)     JSON_OUTPUT="true"; shift ;;
        --vps)      VPS_FILTER="$2"; shift 2 ;;
        --since)    SINCE_TS="$2"; REPORT_MODE="since"; shift 2 ;;
        --date)     REPORT_DATE="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 [--yesterday|--all|--json] [--vps TAG] [--since TS]"
            exit 0
            ;;
        *) die "Unknown flag: $1" ;;
    esac
done

# ---- Logging helpers ----
log()  { echo -e "\033[0;36m[BOARD]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m  $*" >&2; }
die()  { echo -e "\033[0;31m[FAIL]\033[0m  $*" >&2; exit 1; }

# ---- Compute time window ----
get_time_window() {
    python3 << 'PYEOF'
import datetime, time, sys

mode = sys.argv[1] if len(sys.argv) > 1 else "today"
vps_filter = sys.argv[2] if len(sys.argv) > 2 else ""
since_ts = sys.argv[3] if len(sys.argv) > 3 else ""
report_date = sys.argv[4] if len(sys.argv) > 4 else ""

now = datetime.datetime.utcnow()

if mode == "yesterday":
    end_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_dt - datetime.timedelta(days=1)
elif mode == "today":
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now
elif mode == "since" and since_ts:
    start_dt = datetime.datetime.fromtimestamp(float(since_ts))
    end_dt = now
elif mode == "all":
    start_dt = datetime.datetime(1970, 1, 1)
    end_dt = now
elif mode == "date" and report_date:
    start_dt = datetime.datetime.strptime(report_date, "%Y-%m-%d")
    end_dt = start_dt + datetime.timedelta(days=1)
else:
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now

start_ts = start_dt.timestamp()
end_ts = end_dt.timestamp()

print(f"{start_ts}|{end_ts}|{start_dt.strftime('%Y-%m-%d %H:%M:%S')}|{end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
PYEOF
}

TIME_WINDOW=$(get_time_window "${REPORT_MODE}" "${VPS_FILTER}" "${SINCE_TS}" "${REPORT_DATE}")
START_TS=$(echo "${TIME_WINDOW}" | cut -d'|' -f1)
END_TS=$(echo "${TIME_WINDOW}" | cut -d'|' -f2)
START_DT=$(echo "${TIME_WINDOW}" | cut -d'|' -f3)
END_DT=$(echo "${TIME_WINDOW}" | cut -d'|' -f4)

# ---- SQL query runner ----
query_db() {
    local sql="$1"
    python3 << PYEOF
import sqlite3, os, json, sys
db = os.path.expanduser("${BORG_DB_PATH}")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("${sql}")
rows = c.fetchall()
result = []
for row in rows:
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, bytes):
            d[k] = v.hex()
        elif isinstance(v, str) and v == "None":
            d[k] = None
    result.append(d)
print(json.dumps(result, default=str, indent=2))
conn.close()
PYEOF
}

query_db_single() {
    local sql="$1"
    python3 << PYEOF
import sqlite3, os
db = os.path.expanduser("${BORG_DB_PATH}")
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("${sql}")
row = c.fetchone()
print(row[0] if row else "0")
conn.close()
PYEOF
}

# ---- Fetch all data for the window ----
fetch_data() {
    local vps_clause=""
    [[ -n "${VPS_FILTER}" ]] && vps_clause="AND vps_hostname = '${VPS_FILTER}'"

    # Task outcomes
    OUTCOMES=$(query_db "SELECT * FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS}
        ${vps_clause}
        ORDER BY completed_at DESC")

    # Pack usage
    PACK_USAGE=$(query_db "SELECT * FROM pack_usage
        WHERE used_at >= ${START_TS} AND used_at <= ${END_TS}
        ${vps_clause}
        ORDER BY used_at DESC")

    # Sync log
    SYNC_LOG=$(query_db "SELECT * FROM sync_log
        WHERE synced_at >= datetime('${START_DT}') AND synced_at <= datetime('${END_DT}')
        ORDER BY synced_at DESC")

    # Basic counts
    TOTAL_TASKS=$(query_db_single "SELECT COUNT(*) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS} ${vps_clause}")
    SUCCESSFUL=$(query_db_single "SELECT COUNT(*) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS}
        AND success = 1 ${vps_clause}")
    FAILED=$(query_db_single "SELECT COUNT(*) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS}
        AND success = 0 ${vps_clause}")

    # Token stats
    TOTAL_TOKENS=$(query_db_single "SELECT COALESCE(SUM(tokens_spent), 0) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS} ${vps_clause}")
    TOTAL_SAVED=$(query_db_single "SELECT COALESCE(SUM(tokens_saved), 0) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS} ${vps_clause}")

    # Unique VPSes
    UNIQUE_VPS=$(query_db_single "SELECT COUNT(DISTINCT vps_hostname) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS} ${vps_clause}")

    # Pack stats
    UNIQUE_PACKS=$(query_db_single "SELECT COUNT(DISTINCT pack_id) FROM pack_usage
        WHERE used_at >= ${START_TS} AND used_at <= ${END_TS} ${vps_clause}")

    # Error summary
    ERROR_COUNT=$(query_db_single "SELECT COUNT(*) FROM task_outcomes
        WHERE completed_at >= ${START_TS} AND completed_at <= ${END_TS}
        AND success = 0 ${vps_clause}")
}

# ---- Derive structured metrics ----
compute_metrics() {
    python3 << 'PYEOF'
import json, sys
from datetime import datetime

outcomes_raw = json.loads('''${OUTCOMES}''')
packs_raw = json.loads('''${PACK_USAGE}''')

total = int('''${TOTAL_TASKS}''')
successful = int('''${SUCCESSFUL}''')
failed = int('''${FAILED}''')
total_tokens = int('''${TOTAL_TOKENS}''')
total_saved = int('''${TOTAL_SAVED}''')
unique_vps = int('''${UNIQUE_VPS}''')
unique_packs = int('''${UNIQUE_PACKS}''')
error_count = int('''${ERROR_COUNT}''')

success_rate = (successful / total * 100) if total > 0 else 0.0
fail_rate = (failed / total * 100) if total > 0 else 0.0
token_savings_pct = (total_saved / total_tokens * 100) if total_tokens > 0 else 0.0

# ---- Per-task-type breakdown ----
type_stats = {}
for o in outcomes_raw:
    t = o.get("task_type") or "unknown"
    if t not in type_stats:
        type_stats[t] = {"total": 0, "success": 0, "failed": 0, "tokens": 0}
    type_stats[t]["total"] += 1
    if o.get("success"):
        type_stats[t]["success"] += 1
    else:
        type_stats[t]["failed"] += 1
    type_stats[t]["tokens"] += o.get("tokens_spent", 0) or 0

# ---- Per-VPS breakdown ----
vps_stats = {}
for o in outcomes_raw:
    v = o.get("vps_hostname") or "unknown"
    if v not in vps_stats:
        vps_stats[v] = {"total": 0, "success": 0, "failed": 0, "tokens": 0}
    vps_stats[v]["total"] += 1
    if o.get("success"):
        vps_stats[v]["success"] += 1
    else:
        vps_stats[v]["failed"] += 1
    vps_stats[v]["tokens"] += o.get("tokens_spent", 0) or 0

# ---- Pack usage ranking ----
pack_counts = {}
for p in packs_raw:
    pid = p.get("pack_id") or "unknown"
    if pid not in pack_counts:
        pack_counts[pid] = {"name": p.get("pack_name") or pid,
                            "version": p.get("pack_version") or "unknown",
                            "count": 0, "success": 0, "fail": 0}
    pack_counts[pid]["count"] += 1
    if p.get("success"):
        pack_counts[pid]["success"] += 1
    else:
        pack_counts[pid]["fail"] += 1

top_packs = sorted(pack_counts.values(), key=lambda x: -x["count"])[:10]

# ---- Failure pattern analysis ----
error_buckets = {}
for o in outcomes_raw:
    if not o.get("success"):
        err = o.get("error_msg") or "unknown"
        # Bucket by first line / first 80 chars
        bucket = err.strip().split("\n")[0][:80]
        if len(bucket) < 10:
            bucket = err[:80] or "empty_error"
        error_buckets[bucket] = error_buckets.get(bucket, 0) + 1

top_errors = sorted(error_buckets.items(), key=lambda x: -x[1])[:10]

# ---- Feedback score stats ----
scores = [o.get("feedback_score", 0) for o in outcomes_raw if o.get("feedback_score") is not None]
avg_score = (sum(scores) / len(scores)) if scores else 0.0
min_score = (min(scores) if scores else 0.0)
max_score = (max(scores) if scores else 0.0)

# Output as JSON for machine parsing
result = {
    "report": {
        "generated_at": datetime.utcnow().isoformat(),
        "window_start": "${START_DT}",
        "window_end":   "${END_DT}",
        "vps_filter":   "${VPS_FILTER}" or None,
    },
    "summary": {
        "total_tasks": total,
        "successful":  successful,
        "failed":      failed,
        "success_rate_pct": round(success_rate, 1),
        "fail_rate_pct":    round(fail_rate, 1),
        "unique_vps":       unique_vps,
        "unique_packs":     unique_packs,
    },
    "tokens": {
        "total_spent": total_tokens,
        "total_saved": total_saved,
        "savings_pct": round(token_savings_pct, 1),
    },
    "feedback": {
        "avg_score":   round(avg_score, 3),
        "min_score":   round(min_score, 3),
        "max_score":   round(max_score, 3),
        "scores_count": len(scores),
    },
    "per_task_type": type_stats,
    "per_vps":       vps_stats,
    "top_packs":     top_packs,
    "top_errors":    top_errors,
    "raw_outcomes":  outcomes_raw,
}

print(json.dumps(result, indent=2, default=str))
PYEOF
}

# ---- Render human-readable text report ----
render_text_report() {
    local json_data="$1"

    python3 << PYEOF
import json, sys
from datetime import datetime

data = json.loads('''${json_data}''')
r    = data["report"]
s    = data["summary"]
t    = data["tokens"]
f    = data["feedback"]
pt   = data["per_task_type"]
pv   = data["per_vps"]
pk   = data["top_packs"]
er   = data["top_errors"]

W = 70
def rule(): print("=" * W)
def space(): print()

rule()
print(f"  Borg V3 Dogfood — Daily Dashboard")
print(f"  Window : {r['window_start']} → {r['window_end']}")
if r.get("vps_filter"):
    print(f"  VPS    : {r['vps_filter']}")
else:
    print(f"  VPS    : all ({s['unique_vps']} active)")
print(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
rule()
space()

# ---- Summary KPIs ----
print(f"  TASKS")
print(f"    Total     : {s['total_tasks']:>6}")
print(f"    Success   : {s['successful']:>6}  ({s['success_rate_pct']}%)")
print(f"    Failed    : {s['failed']:>6}  ({s['fail_rate_pct']}%)")
space()

print(f"  TOKENS")
print(f"    Spent     : {t['total_spent']:>10,}")
print(f"    Saved     : {t['total_saved']:>10,}  ({t['savings_pct']}%)")
space()

print(f"  FEEDBACK SCORES  (n={f['scores_count']})")
print(f"    Average   : {f['avg_score']:.3f}")
print(f"    Min / Max : {f['min_score']:.3f} / {f['max_score']:.3f}")
space()

# ---- Per-task-type ----
if pt:
    print(f"  PER TASK TYPE")
    hdr = f"    {'Type':<20} {'Total':>6} {'OK':>6} {'Fail':>6} {'Rate':>8}"
    print(hdr)
    print(f"    {'-'*20} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")
    for typ, vals in sorted(pt.items(), key=lambda x: -x[1]["total"]):
        rate = (vals["success"] / vals["total"] * 100) if vals["total"] > 0 else 0
        print(f"    {typ:<20} {vals['total']:>6} {vals['success']:>6} {vals['failed']:>6} {rate:>7.1f}%")
    space()

# ---- Per-VPS ----
if pv and not r.get("vps_filter"):
    print(f"  PER VPS")
    hdr = f"    {'VPS':<25} {'Total':>6} {'OK':>6} {'Fail':>6} {'Rate':>8}"
    print(hdr)
    print(f"    {'-'*25} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")
    for vps, vals in sorted(pv.items(), key=lambda x: -x[1]["total"]):
        rate = (vals["success"] / vals["total"] * 100) if vals["total"] > 0 else 0
        print(f"    {vps:<25} {vals['total']:>6} {vals['success']:>6} {vals['failed']:>6} {rate:>7.1f}%")
    space()

# ---- Top packs ----
if pk:
    print(f"  TOP PACKS (by use count)")
    hdr = f"    {'Pack ID':<35} {'Name':<15} {'Uses':>5} {'OK':>4} {'Fail':>4}"
    print(hdr)
    print(f"    {'-'*35} {'-'*15} {'-'*5} {'-'*4} {'-'*4}")
    for p in pk:
        print(f"    {p['name']:<35} {str(p.get('version','')):<15} {p['count']:>5} {p['success']:>4} {p['fail']:>4}")
    space()

# ---- Failure patterns ----
if er:
    print(f"  FAILURE PATTERNS")
    for i, (err, cnt) in enumerate(er, 1):
        print(f"    {i}. [{cnt}x] {err[:60]}")
    space()

rule()
print(f"  End of report")
rule()
PYEOF
}

# ---- Main ----
main() {
    log "Fetching data for window: ${START_DT} → ${END_DT}"
    [[ -n "${VPS_FILTER}" ]] && log "VPS filter: ${VPS_FILTER}"

    fetch_data
    METRICS_JSON=$(compute_metrics)

    if [[ "${JSON_OUTPUT}" == "true" ]]; then
        local outfile="${OUTPUT_DIR}/dashboard_${START_TS}_${END_TS}.json"
        echo "${METRICS_JSON}" > "${outfile}"
        log "JSON output: ${outfile}"
        # Also print to stdout
        echo "${METRICS_JSON}"
    else
        render_text_report "${METRICS_JSON}"
    fi
}

main
