#!/bin/bash
#
# Borg V3 Fleet Cron Setup
# =========================
# - SSH into each VPS, add crontab entry: run dogfood_runner.py 5 every 6 hours
# - On LOCAL machine: run sync_fleet.sh every hour, daily_report.sh at 8am UTC
#
# VPS IPs: 147.93.72.73, 72.61.53.248, 76.13.198.23, 76.13.209.192
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_KEY="${HOME}/.ssh/id_ed25519"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"

VPS_IPS=(
    "147.93.72.73"
    "72.61.53.248"
    "76.13.198.23"
    "76.13.209.192"
)

log()   { echo -e "\033[0;34m[CRON]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
die()   { echo -e "\033[0;31m[FAIL]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Add crontab entry to a remote VPS
# ---------------------------------------------------------------------------
setup_vps_cron() {
    local ip="$1"

    log "Setting up cron on ${ip} ..."

    # The dogfood_runner.py command to run
    # "5" means run 5 iterations, every 6 hours means: 0 */6 * * *
    # We schedule: every 6 hours at minute 5
    local cron_entry="5 */6 * * * cd /root && python3 /root/dogfood_runner.py 5 >> /var/log/dogfood_runner.log 2>&1"

    # Check if already installed
    local existing
    existing=$(ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "crontab -l 2>/dev/null || true")
    if echo "${existing}" | grep -q "dogfood_runner.py"; then
        log "  Cron already exists on ${ip} — skipping"
        return 0
    fi

    # Add the cron entry
    ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "echo '${cron_entry}' | crontab -" || {
        warn "  Failed to set cron on ${ip}"
        return 1
    }

    log "  Cron installed on ${ip}: ${cron_entry}"
}

# ---------------------------------------------------------------------------
# Setup local cron: sync_fleet.sh every hour, daily_report.sh at 8am UTC
# ---------------------------------------------------------------------------
setup_local_cron() {
    log "Setting up local crontab ..."

    # Build the local crontab entries
    local sync_cron="0 * * * * ${SCRIPT_DIR}/sync_fleet.sh >> /var/log/borg_sync.log 2>&1"
    local report_cron="0 8 * * * ${SCRIPT_DIR}/daily_report.sh >> /var/log/borg_daily_report.log 2>&1"

    # Get existing crontab
    local existing
    existing=$(crontab -l 2>/dev/null || true)

    # Remove old entries if present
    existing=$(echo "${existing}" | grep -v "sync_fleet.sh" | grep -v "daily_report.sh" | grep -v "# \[BORG")

    # Add header comment
    local new_crontab="${existing}
# [BORG FLEET CRON] — managed by setup_crons.sh
${sync_cron}
${report_cron}
"

    echo "${new_crontab}" | crontab -

    log "  Local crontab updated:"
    log "    sync_fleet.sh : every hour"
    log "    daily_report.sh : 8am UTC daily"
}

# ---------------------------------------------------------------------------
# Remove all cron entries (cleanup)
# ---------------------------------------------------------------------------
remove_crons() {
    log "Removing all Borg fleet cron entries..."

    # Remove from all VPS
    for ip in "${VPS_IPS[@]}"; do
        ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "crontab -r 2>/dev/null || true" || true
        log "  Removed crontab from ${ip}"
    done

    # Remove local entries
    local existing
    existing=$(crontab -l 2>/dev/null || true)
    existing=$(echo "${existing}" | grep -v "sync_fleet.sh" | grep -v "daily_report.sh" | grep -v "# \[BORG")
    echo "${existing}" | crontab - 2>/dev/null || true
    log "  Removed local crontab entries"
}

# ---------------------------------------------------------------------------
# Show current cron status
# ---------------------------------------------------------------------------
show_status() {
    log "Cron status:"
    echo
    echo "  Local crontab:"
    crontab -l 2>/dev/null | grep -E "(sync_fleet|daily_report|BORG)" || echo "    (none)"
    echo
    echo "  VPS crontabs:"
    for ip in "${VPS_IPS[@]}"; do
        local cron
        cron=$(ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "crontab -l 2>/dev/null || true")
        if echo "${cron}" | grep -q "dogfood_runner"; then
            echo "    [OK]   ${ip}"
        else
            echo "    [MISSING] ${ip}"
        fi
    done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    local action="${1:-install}"

    case "${action}" in
        install)
            log "Installing Borg fleet crons..."
            log "VPS IPs: ${VPS_IPS[*]}"

            # Test SSH connectivity first
            log "Testing SSH connectivity..."
            local failed=0
            for ip in "${VPS_IPS[@]}"; do
                if ! ssh -i "${SSH_KEY}" ${SSH_OPTS} "root@${ip}" "echo ok" &>/dev/null; then
                    warn "  Cannot reach ${ip} — skipping"
                    ((failed++))
                fi
            done

            if [[ ${failed} -gt 0 ]]; then
                die "${failed} VPS(s) unreachable — fix connectivity first"
            fi

            # Setup VPS crons
            for ip in "${VPS_IPS[@]}"; do
                setup_vps_cron "${ip}" || warn "Failed to setup ${ip}"
            done

            # Setup local cron
            setup_local_cron

            log "Cron setup complete."
            ;;

        remove)
            remove_crons
            ;;

        status)
            show_status
            ;;

        *)
            echo "Usage: $0 [install|remove|status]"
            exit 1
            ;;
    esac
}

main "$@"
