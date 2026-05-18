#!/bin/bash
#
# Borg V3 Fleet DB Sync Script
# ==============================
# SSH into each VPS, download their /root/.borg/borg_v3.db,
# merge outcomes into the local central DB at ~/.borg/borg_v3.db
# with a hostname column to distinguish sources.
#
# VPS IPs: 147.93.72.73, 72.61.53.248, 76.13.198.23, 76.13.209.192
#
# Usage:
#   ./sync_fleet.sh           # normal sync
#   ./sync_fleet.sh --dry-run # show what would be merged
#   ./sync_fleet.sh --test    # test SSH connectivity only
#

set -euo pipefail

CENTRAL_DB="${HOME}/.borg/borg_v3.db"
SSH_KEY="${HOME}/.ssh/id_ed25519"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"

VPS_IPS=(
    "147.93.72.73"
    "72.61.53.248"
    "76.13.198.23"
    "76.13.209.192"
)

DRY_RUN=""
TEST_MODE=""

log()   { echo -e "\033[0;34m[SYNC]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
die()   { echo -e "\033[0;31m[FAIL]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN="1"; shift ;;
        --test)    TEST_MODE="1"; shift ;;
        *)         die "Unknown flag: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Ensure central DB exists and has hostname column
# ---------------------------------------------------------------------------
ensure_central_schema() {
    CENTRAL_DB="${CENTRAL_DB}" python3 << PYEOF
import sqlite3, os

db = os.path.expanduser("${CENTRAL_DB}")
os.makedirs(os.path.dirname(db), exist_ok=True)

conn = sqlite3.connect(db)
c = conn.cursor()

# Create outcomes table if not exists (matches V3 schema)
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

# Add hostname column if missing (for DBs created before this feature)
try:
    c.execute("ALTER TABLE outcomes ADD COLUMN hostname TEXT DEFAULT 'unknown'")
except sqlite3.OperationalError:
    pass  # Column already exists

# Create index on hostname for per-node queries
c.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_hostname ON outcomes(hostname)")

conn.commit()
conn.close()
print(f"Central DB ready: {db}")
PYEOF
}

# ---------------------------------------------------------------------------
# Test SSH connectivity to all VPS
# ---------------------------------------------------------------------------
test_connectivity() {
    local all_ok=0
    for ip in "${VPS_IPS[@]}"; do
        if ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "echo ok" &>/dev/null; then
            echo "  [OK]  ${ip}"
        else
            echo "  [FAIL] ${ip}"
            all_ok=1
        fi
    done
    return ${all_ok}
}

# ---------------------------------------------------------------------------
# Sync a single VPS: copy remote DB, merge into central DB
# ---------------------------------------------------------------------------
sync_vps() {
    local ip="$1"
    local remote_db="/root/.borg/borg_v3.db"
    local tmpfile
    tmpfile=$(mktemp /tmp/vps_db_${ip}_XXXXXX.sqlite)

    log "Syncing ${ip} ..."

    # Check if remote DB exists
    if ! ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "test -f ${remote_db}" &>/dev/null; then
        warn "  No DB at ${ip}:${remote_db} — skipping"
        return 0
    fi

    # Copy remote DB to temp local file
    if ! scp -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}:${remote_db}" "${tmpfile}" &>/dev/null; then
        warn "  Failed to copy DB from ${ip}"
        rm -f "${tmpfile}"
        return 1
    fi

    local size
    size=$(wc -c < "${tmpfile}")
    log "  Downloaded ${size} bytes from ${ip}"

    # Get hostname from remote VPS
    local remote_hostname
    remote_hostname=$(ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "hostname" 2>/dev/null || echo "${ip}")

    # Merge into central DB
    if [[ -n "${DRY_RUN}" ]]; then
        dry_run_merge "${tmpfile}" "${remote_hostname}" "${ip}"
    else
        merge_db "${tmpfile}" "${remote_hostname}" "${ip}"
    fi

    rm -f "${tmpfile}"
}

# ---------------------------------------------------------------------------
# Dry run: show what would be merged
# ---------------------------------------------------------------------------
dry_run_merge() {
    local tmpfile="$1"
    local remote_hostname="$2"
    local ip="$3"

    python3 << PYEOF
import sqlite3, os

src = "${tmpfile}"
conn = sqlite3.connect(src)
c = conn.cursor()

try:
    c.execute("SELECT COUNT(*) FROM outcomes")
    total = c.fetchone()[0]
    print(f"  [DRY RUN] ${ip} (${remote_hostname}): {total} outcomes in remote DB")
except sqlite3.OperationalError:
    print(f"  [DRY RUN] ${ip}: outcomes table not found or empty")

conn.close()
PYEOF
}

# ---------------------------------------------------------------------------
# Merge remote DB into central DB
# ---------------------------------------------------------------------------
merge_db() {
    local tmpfile="$1"
    local remote_hostname="$2"
    local ip="$3"

    CENTRAL_DB="${CENTRAL_DB}" python3 << PYEOF
import sqlite3, os, sys

src = "${tmpfile}"
dst = os.path.expanduser("${CENTRAL_DB}")

src_conn = sqlite3.connect(src)
dst_conn = sqlite3.connect(dst)
src_c = src_conn.cursor()
dst_c = dst_conn.cursor()

hostname = "${remote_hostname}"

# Get remote outcomes
try:
    src_c.execute("SELECT pack_id, agent_id, task_category, success, tokens_used, time_taken, timestamp FROM outcomes")
    rows = src_c.fetchall()
except sqlite3.OperationalError as e:
    print(f"  Warning: could not read outcomes from ${ip}: {e}", file=sys.stderr)
    src_conn.close()
    dst_conn.close()
    sys.exit(0)

merged = 0
for row in rows:
    try:
        dst_c.execute("""
            INSERT OR IGNORE INTO outcomes
                (pack_id, agent_id, task_category, success, tokens_used, time_taken, timestamp, hostname)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (*row, hostname))
        if dst_c.rowcount > 0:
            merged += 1
    except Exception as e:
        print(f"  Warning inserting row: {e}", file=sys.stderr)

dst_conn.commit()
src_conn.close()
dst_conn.close()
print(f"  Merged {merged} new outcomes from ${ip} (hostname={hostname})")
PYEOF
}

# ---------------------------------------------------------------------------
# Show sync summary
# ---------------------------------------------------------------------------
show_summary() {
    CENTRAL_DB="${CENTRAL_DB}" python3 << PYEOF
import sqlite3, os
from datetime import datetime, timezone

db = os.path.expanduser("${CENTRAL_DB}")
conn = sqlite3.connect(db)
c = conn.cursor()

print()
print("=" * 60)
print("  Fleet Sync Summary")
print("=" * 60)

# Total outcomes
c.execute("SELECT COUNT(*) FROM outcomes")
total = c.fetchone()[0] or 0
print(f"  Total outcomes : {total}")

# Per-node breakdown
print()
print("  PER NODE:")
c.execute("""
    SELECT hostname, COUNT(*) as cnt,
           ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
    FROM outcomes
    GROUP BY hostname
    ORDER BY cnt DESC
""")
for row in c.fetchall():
    print(f"    {str(row[0]):<30} {row[1]:>6} outcomes  {row[2]}% success")

# Recent outcomes (last 5)
print()
print("  RECENT OUTCOMES:")
c.execute("SELECT pack_id, hostname, success, timestamp FROM outcomes ORDER BY id DESC LIMIT 5")
for row in c.fetchall():
    print(f"    [{row[3][:19]}] pack={row[0]:<25} node={str(row[1]):<20} ok={row[2]}")

conn.close()
print()
PYEOF
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log "Fleet DB Sync starting..."
    log "Central DB: ${CENTRAL_DB}"

    if [[ -n "${TEST_MODE}" ]]; then
        log "Testing SSH connectivity..."
        test_connectivity
        exit $?
    fi

    ensure_central_schema

    local failed=0
    for ip in "${VPS_IPS[@]}"; do
        sync_vps "${ip}" || ((failed++))
    done

    show_summary

    if [[ ${failed} -gt 0 ]]; then
        warn "${failed} VPS(s) failed to sync"
        exit 1
    fi

    log "Fleet sync complete."
}

main
