#!/bin/bash
#
# Borg V3 Dogfood - DB Sync Script
# =================================
# Rsyncs outcome data from the local borg SQLite DB to a central server.
# Intended to run every 5 minutes via cron (set up by 01_vps_setup.sh).
#
# This script is idempotent — safe to run multiple times.
# Only new records (since last sync) are sent to avoid duplication.
#
# Usage:
#   ./03_db_sync.sh                    # sync with configured central server
#   ./03_db_sync.sh --dry-run          # show what would be sent
#   ./03_db_sync.sh --local /path/to/dump.json   # import from a dump file
#   ./03_db_sync.sh --server           # run as central receiving server
#
# Environment variables:
#   CENTRAL_SERVER   — hostname/IP of central server
#   CENTRAL_USER     — SSH user on central (default: root)
#   CENTRAL_PORT     — SSH port (default: 22)
#   CENTRAL_PATH     — path to receive data (default: /srv/borg-sync/incoming)
#   SSH_KEY          — path to SSH key (default: ~/.ssh/id_ed25519)
#   VPS_HOSTNAME     — identifier for this VPS (set automatically)
#   BORG_DB_PATH     — path to borg SQLite DB (default: ~/.borg/borg.db)
#   RSYNC_PASSWORD   — if using rsync daemon mode
#   LOG_DIR          — log directory (default: /opt/borg-dogfood/logs)
# -----------------------------------------------------------------------------

set -euo pipefail

# ---- Configuration ----
INSTALL_ROOT="/opt/borg-dogfood"
LOG_DIR="${LOG_DIR:-${INSTALL_ROOT}/logs}"
DATA_DIR="${DATA_DIR:-${INSTALL_ROOT}/data}"
RUN_DIR="${RUN_DIR:-${INSTALL_ROOT}/run}"

CENTRAL_SERVER="${CENTRAL_SERVER:-}"
CENTRAL_USER="${CENTRAL_USER:-root}"
CENTRAL_PORT="${CENTRAL_PORT:-22}"
CENTRAL_PATH="${CENTRAL_PATH:-/srv/borg-sync/incoming}"
SSH_KEY="${SSH_KEY:-${HOME}/.ssh/id_ed25519}"
VPS_HOSTNAME="${VPS_HOSTNAME:-$(hostname 2>/dev/null || echo 'vps-unknown')}"
BORG_DB_PATH="${BORG_DB_PATH:-${HOME}/.borg/borg.db}"
RSYNC_PASSWORD="${RSYNC_PASSWORD:-}"

mkdir -p "${LOG_DIR}" "${DATA_DIR}"

# Sync state file — records last sync timestamp to avoid re-sending old data
LAST_SYNC_FILE="${RUN_DIR}/last_sync_timestamp.txt"
LAST_SYNC_TS="${LAST_SYNC_TS:-0}"

# ---- CLI flags ----
MODE="push"      # push | dry-run | local | server
IMPORT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)  MODE="dry-run"; shift ;;
        --local)    MODE="local"; IMPORT_FILE="$2"; shift 2 ;;
        --server)   MODE="server"; shift ;;
        *) die "Unknown flag: $1" ;;
    esac
done

# ---- Logging helpers ----
TIMESTAMP=$(date +%Y-%m-%d\ %H:%M:%S)
log()  { echo -e "\033[0;34m[SYNC]\033[0m ${TIMESTAMP} $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m ${TIMESTAMP} $*" >&2; }
die()  { echo -e "\033[0;31m[FAIL]\033[0m ${TIMESTAMP} $*" >&2; exit 1; }

# ---- Database query helper ----
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
# Convert to JSON-serializable dicts
result = []
for row in rows:
    d = dict(row)
    # Convert any bytes to hex
    for k, v in d.items():
        if isinstance(v, bytes):
            d[k] = v.hex()
    result.append(d)
print(json.dumps(result, default=str))
conn.close()
PYEOF
}

# ---- Export new records to JSON ----
export_new_records() {
    local since_ts="${LAST_SYNC_TS}"
    if [[ -f "${LAST_SYNC_FILE}" ]]; then
        since_ts=$(cat "${LAST_SYNC_FILE}")
    fi

    # Fetch task_outcomes newer than last sync
    local outcomes_json
    outcomes_json=$(query_db "SELECT * FROM task_outcomes WHERE completed_at > ${since_ts}")

    # Fetch pack_usage newer than last sync
    local packs_json
    packs_json=$(query_db "SELECT * FROM pack_usage WHERE used_at > ${since_ts}")

    # Fetch sync_log entries for this VPS (for audit trail)
    local sync_log_json
    sync_log_json=$(query_db "SELECT * FROM sync_log WHERE synced_at > datetime('now', '-1 day')")

    # Write combined payload
    local payload_file="${DATA_DIR}/sync_payload_${VPS_HOSTNAME}_$(date +%Y%m%d_%H%M%S).json"
    python3 << PYEOF
import json, os
payload = {
    "sync_meta": {
        "vps_hostname": "${VPS_HOSTNAME}",
        "synced_at": __import__('datetime').datetime.utcnow().isoformat(),
        "records_since_ts": ${since_ts},
        "schema_version": "1.0"
    },
    "task_outcomes": json.loads('''${outcomes_json}'''),
    "pack_usage": json.loads('''${packs_json}'''),
    "sync_log": json.loads('''${sync_log_json}''')
}
out_path = "${payload_file}"
with open(out_path, 'w') as f:
    json.dump(payload, f, indent=2, default=str)
print(f"Payload written: {out_path}")
PYEOF

    echo "${payload_file}"
}

# ---- Log sync attempt to DB ----
log_sync_attempt() {
    local records="$1"
    local status="$2"
    local error_msg="$3"

    python3 << PYEOF
import sqlite3, os
db = os.path.expanduser("${BORG_DB_PATH}")
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("""
    INSERT INTO sync_log (records_sent, destination, status, error_msg)
    VALUES (?, ?, ?, ?)
""", (${records}, "${CENTRAL_SERVER:-local}", "${status}", "${error_msg}"))
conn.commit()
conn.close()
PYEOF
}

# ---- Upload payload via rsync over SSH ----
rsync_push() {
    local payload_file="$1"
    [[ -z "${CENTRAL_SERVER}" ]] && die "CENTRAL_SERVER not set."

    local remote_dest="${CENTRAL_USER}@${CENTRAL_SERVER}:${CENTRAL_PATH}/"

    log "Pushing ${payload_file} -> ${remote_dest}"

    # Ensure remote directory exists (create if missing)
    ssh -p "${CENTRAL_PORT}" -i "${SSH_KEY}" -o StrictHostKeyChecking=no \
        "${CENTRAL_USER}@${CENTRAL_SERVER}" \
        "mkdir -p ${CENTRAL_PATH}/${VPS_HOSTNAME}" 2>/dev/null || true

    local rsync_cmd=(
        rsync
        -az
        --progress
        -e "ssh -p ${CENTRAL_PORT} -i ${SSH_KEY} -o StrictHostKeyChecking=no"
        "${payload_file}"
        "${remote_dest}/"
    )

    if [[ "${MODE}" == "dry-run" ]]; then
        log "[DRY-RUN] Would run: ${rsync_cmd[*]}"
        log "[DRY-RUN] Payload size: $(wc -c < "${payload_file}") bytes"
        return 0
    fi

    local exit_code=0
    "${rsync_cmd[@]}" || exit_code=$?

    if [[ ${exit_code} -eq 0 ]]; then
        log "Sync successful."
        return 0
    else
        warn "rsync exited with code ${exit_code}."
        return ${exit_code}
    fi
}

# ---- Receive mode (central server) ----
run_server() {
    log "Running as central sync receiver on port ${CENTRAL_PORT}..."
    log "Listening for incoming syncs to: ${CENTRAL_PATH}/"
    die "Server mode not yet implemented — use rsync daemon or SSH reverse tunnel."
}

# ---- Update last sync timestamp ----
update_last_sync() {
    local ts="$1"
    echo "${ts}" > "${LAST_SYNC_FILE}"
    chmod 600 "${LAST_SYNC_FILE}"
}

# ---- Import from a dump file (for testing/recovery) ----
import_dump() {
    local file="$1"
    [[ ! -f "${file}" ]] && die "Import file not found: ${file}"

    log "Importing records from ${file}..."

    python3 << PYEOF
import sqlite3, os, json

db = os.path.expanduser("${BORG_DB_PATH}")
conn = sqlite3.connect(db)
c = conn.cursor()

with open("${file}") as f:
    data = json.load(f)

meta = data.get("sync_meta", {})
records_imported = 0

# Import task_outcomes
for row in data.get("task_outcomes", []):
    try:
        c.execute("""
            INSERT INTO task_outcomes
                (task_id, task_type, queued_at, started_at, completed_at,
                 success, error_msg, agent_id, vps_hostname, pack_id,
                 tokens_spent, tokens_saved, feedback_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
        """, (
            row.get("task_id"), row.get("task_type"),
            row.get("queued_at"), row.get("started_at"), row.get("completed_at"),
            row.get("success"), row.get("error_msg"), row.get("agent_id"),
            row.get("vps_hostname"), row.get("pack_id"),
            row.get("tokens_spent", 0), row.get("tokens_saved", 0),
            row.get("feedback_score", 0.0), row.get("metadata")
        ))
        records_imported += 1
    except Exception as e:
        print(f"  Warning: {e}", file=sys.stderr)

# Import pack_usage
for row in data.get("pack_usage", []):
    try:
        c.execute("""
            INSERT INTO pack_usage
                (pack_id, pack_name, pack_version, used_at, task_id, success)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
        """, (
            row.get("pack_id"), row.get("pack_name"), row.get("pack_version"),
            row.get("used_at"), row.get("task_id"), row.get("success")
        ))
    except Exception as e:
        print(f"  Warning: {e}", file=sys.stderr)

conn.commit()
conn.close()
print(f"Imported {records_imported} records.")
PYEOF
}

# ---- Show sync status ----
show_status() {
    log "Sync status for ${VPS_HOSTNAME}:"
    log "  Last sync : $(cat "${LAST_SYNC_FILE}" 2>/dev/null || echo 'never')"
    log "  DB path   : ${BORG_DB_PATH}"
    log "  Central   : ${CENTRAL_SERVER:-not configured}"

    # Count pending (unsynced) records
    local since_ts="0"
    [[ -f "${LAST_SYNC_FILE}" ]] && since_ts=$(cat "${LAST_SYNC_FILE}")

    local pending_count
    pending_count=$(python3 << PYEOF
import sqlite3, os
db = os.path.expanduser("${BORG_DB_PATH}")
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM task_outcomes WHERE completed_at > ${since_ts}")
print(c.fetchone()[0])
conn.close()
PYEOF
    )
    log "  Pending   : ${pending_count} new outcome records"
}

# ---- Main ----
main() {
    log "Borg DB Sync — mode: ${MODE}"

    case "${MODE}" in
        push|dry-run)
            show_status

            if [[ "${MODE}" == "dry-run" ]]; then
                log "[DRY-RUN] Would export and sync."
            fi

            # Build SSH known_hosts to avoid interactive prompts
            # (StrictHostKeyChecking=no is passed to ssh/rsync above)

            payload_file=$(export_new_records)
            local payload_size
            payload_size=$(wc -c < "${payload_file}")
            log "Payload size: ${payload_size} bytes"

            if [[ "${payload_size}" -lt 100 ]]; then
                log "Empty payload — nothing to sync."
                rm -f "${payload_file}"
                exit 0
            fi

            local exit_code=0
            rsync_push "${payload_file}" || exit_code=$?

            # Update timestamp on success
            if [[ ${exit_code} -eq 0 ]]; then
                local now_ts
                now_ts=$(python3 -c "import time; print(time.time())")
                update_last_sync "${now_ts}"
                log_sync_attempt "$(jq '.task_outcomes | length' "${payload_file}")" \
                                 "success" ""
            else
                log_sync_attempt "0" "failed" "rsync exited ${exit_code}"
                exit ${exit_code}
            fi

            # Cleanup old payload files (keep last 3)
            ls -t "${DATA_DIR}"/sync_payload_${VPS_HOSTNAME}_*.json 2>/dev/null | \
                tail -n +4 | xargs rm -f 2>/dev/null || true
            ;;

        local)
            import_dump "${IMPORT_FILE}"
            ;;

        server)
            run_server
            ;;
    esac
}

main
