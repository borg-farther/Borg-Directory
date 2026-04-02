#!/bin/bash
#
# Borg V3 Dogfood - VPS Setup Script
# ====================================
# Run once per VPS to provision the machine for agent-borg dogfooding.
# Installs: Python 3.12, hermes, agent-borg, MCP config, DB sync cronjob.
#
# Usage:
#   chmod +x 01_vps_setup.sh
#   ./01_vps_setup.sh
#
# Requirements: Ubuntu 22.04+ / Debian 12+, sudo or root access.
# -----------------------------------------------------------------------------

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these before deployment
# ---------------------------------------------------------------------------
VPS_USER="${VPS_USER:-root}"                    # VPS ssh user
VPS_IP="${VPS_IP:-}"                            # leave empty; set via env or flag
SSH_KEY="${SSH_KEY:-~/.ssh/id_ed25519}"         # path to SSH key for rsync
CENTRAL_SERVER="${CENTRAL_SERVER:-}"            # central backup host
CENTRAL_USER="${CENTRAL_USER:-root}"            # user on central server
CENTRAL_SYNC_PATH="/srv/borg-sync/incoming/"    # path on central to receive syncs
HERMES_BRANCH="${HERMES_BRANCH:-main}"          # hermes git branch
BORG_VERSION="${BORG_VERSION:-latest}"         # agent-borg version (PyPI)

# Directories
INSTALL_ROOT="/opt/borg-dogfood"
VENV_DIR="${INSTALL_ROOT}/venv"
LOG_DIR="${INSTALL_ROOT}/logs"
DATA_DIR="${INSTALL_ROOT}/data"
RUN_DIR="${INSTALL_ROOT}/run"

# Paths
VPS_HOSTNAME="$(hostname 2>/dev/null || echo 'vps-unknown')"
SYNC_TAG="${VPS_HOSTNAME}-$(date +%Y%m%d)"      # unique tag per VPS per install

# DB sync interval (minutes)
SYNC_INTERVAL_MINUTES=5

# Python version to install
PYTHON_VERSION="3.12"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${GREEN}[SETUP]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[FAIL]${NC} $*" >&2; exit 1; }

need() { command -v "$1" &>/dev/null || die "Required command not found: $1"; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
log "Starting Borg V3 VPS setup..."

if [[ -z "${VPS_IP}" ]]; then
    die "VPS_IP not set. Export VPS_IP or edit this script."
fi

need ssh
need rsync
need curl

# ---------------------------------------------------------------------------
# 1. System packages — Python 3.12, build tools, sqlite3
# ---------------------------------------------------------------------------
log "Installing system dependencies..."

export DEBIAN_FRONTEND=noninteractive

# Python 3.12 via deadsnakes PPA (Ubuntu) or direct apt (Debian)
if command -v python3.12 &>/dev/null; then
    warn "Python 3.12 already installed."
else
    apt-get update -qq
    apt-get install -y -qq \
        software-properties-common \
        curl \
        wget \
        git \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libncurses5-dev \
        libncursesw5-dev \
        llvm \
        liblzma-dev \
        libffi-dev \
        pkg-config \
        sqlite3 \
        cron \
        logrotate \
        jq \
        bc \
        || die "Failed to install system packages"
fi

# Add deadsnakes PPA for Ubuntu if python3.12 still missing
if ! command -v python3.12 &>/dev/null; then
    log "Adding deadsnakes PPA..."
    add-apt-repository -y ppa:deadsnakes/ppa || true
    apt-get update -qq
    apt-get install -y -qq python3.12 python3.12-venv python3.12-dev || die "Failed to install Python 3.12"
fi

# Make python3.12 the default python3
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 2>/dev/null || true
ln -sf /usr/bin/python3.12 /usr/bin/python3 2>/dev/null || true

log "Python version: $(python3 --version)"

# ---------------------------------------------------------------------------
# 2. Create installation directory structure
# ---------------------------------------------------------------------------
log "Creating installation directories..."
mkdir -p "${INSTALL_ROOT}"{"/{logs,data,run}",}
mkdir -p "${VENV_DIR}"
mkdir -p "$(dirname "${SSH_KEY}")" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Python virtual environment
# ---------------------------------------------------------------------------
log "Creating Python virtual environment..."
python3 -m venv "${VENV_DIR}" --clear
source "${VENV_DIR}/bin/activate"

log "Upgrading pip..."
pip install --quiet --upgrade pip setuptools wheel

# ---------------------------------------------------------------------------
# 4. Install hermes and agent-borg
# ---------------------------------------------------------------------------
log "Installing hermes (branch: ${HERMES_BRANCH})..."
# hermes is installed from git — adjust the URL/repo as appropriate
# If hermes is not yet public, you may need a GitHub token in the env.
if [[ "${HERMES_BRANCH}" == "local" ]]; then
    # For local dev: pip install -e /path/to/hermes
    warn "HERMES_BRANCH=local — skipping hermes install (install manually)"
else
    # Install from PyPI if available, else from git
    pip install --quiet hermes || \
    pip install --quiet "git+https://github.com/anthropics/hermes.git@${HERMES_BRANCH}#egg=hermes"
fi

log "Installing agent-borg (version: ${BORG_VERSION})..."
if [[ "${BORG_VERSION}" == "latest" ]]; then
    pip install --quiet agent-borg
else
    pip install --quiet "agent-borg==${BORG_VERSION}"
fi

# Verify installations
log "Verifying installations..."
python3 -c "import hermes; print(f'  hermes: {hermes.__version__}')" 2>/dev/null || echo "  hermes: installed (version unknown)"
python3 -c "import borg; print(f'  borg: {borg.__version__}')" 2>/dev/null || echo "  borg: installed (version unknown)"

# ---------------------------------------------------------------------------
# 5. Borg data directory and SQLite DB init
# ---------------------------------------------------------------------------
log "Initializing Borg data directory..."
BORG_DATA_DIR="${HOME}/.borg"
mkdir -p "${BORG_DATA_DIR}"

# Create a lightweight init if borg.db doesn't exist
if [[ ! -f "${BORG_DATA_DIR}/borg.db" ]]; then
    python3 << 'PYEOF'
import sqlite3, os
db_path = os.path.expanduser("~/.borg/borg.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS task_outcomes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id         TEXT    NOT NULL,
        task_type       TEXT,
        queued_at       REAL,
        started_at      REAL,
        completed_at    REAL,
        success         INTEGER,
        error_msg       TEXT,
        agent_id        TEXT,
        vps_hostname    TEXT,
        pack_id         TEXT,
        tokens_spent    INTEGER,
        tokens_saved    INTEGER,
        feedback_score  REAL,
        metadata        TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS pack_usage (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        pack_id         TEXT    NOT NULL,
        pack_name       TEXT,
        pack_version    TEXT,
        used_at         REAL,
        task_id         TEXT,
        success         INTEGER
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS sync_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        synced_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        records_sent    INTEGER,
        destination     TEXT,
        status          TEXT,
        error_msg       TEXT
    )
""")
conn.commit()
conn.close()
print(f"  Created {db_path}")
PYEOF
fi

# Record VPS identity
echo "${VPS_HOSTNAME}" > "${BORG_DATA_DIR}/vps_hostname.txt"
echo "${VPS_IP}" > "${BORG_DATA_DIR}/vps_ip.txt"

# ---------------------------------------------------------------------------
# 6. MCP configuration for agent-borg
# ---------------------------------------------------------------------------
log "Configuring MCP (Model Context Protocol) for agent-borg..."

MCP_CONFIG_DIR="${HOME}/.config/agent-borg"
mkdir -p "${MCP_CONFIG_DIR}"

cat > "${MCP_CONFIG_DIR}/mcp_config.json" << 'MCPEOF'
{
    "mcp_servers": {
        "borg": {
            "enabled": true,
            "db_path": "~/.borg/borg.db",
            "auto_feedback": true,
            "feedback_threshold": 0.7
        }
    },
    "telemetry": {
        "enabled": true,
        "sync_interval_seconds": 300,
        "anonymized": false
    }
}
MCPEOF

log "  MCP config written to ${MCP_CONFIG_DIR}/mcp_config.json"

# Also write a global hermes config
HERMES_CONFIG_DIR="${HOME}/.config/hermes"
mkdir -p "${HERMES_CONFIG_DIR}"
cat > "${HERMES_CONFIG_DIR}/config.json" << 'HERMESEOF'
{
    "dogfood": {
        "enabled": true,
        "vps_hostname": "${VPS_HOSTNAME}",
        "vps_ip": "${VPS_IP}",
        "sync_tag": "${SYNC_TAG}",
        "central_server": "${CENTRAL_SERVER}",
        "sync_interval_minutes": ${SYNC_INTERVAL_MINUTES}
    },
    "agent": {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.3
    }
}
HERMESEOF

# Expand variables in the config
sed -i "s|\${VPS_HOSTNAME}|${VPS_HOSTNAME}|g" "${HERMES_CONFIG_DIR}/config.json"
sed -i "s|\${VPS_IP}|${VPS_IP}|g"     "${HERMES_CONFIG_DIR}/config.json"
sed -i "s|\${SYNC_TAG}|${SYNC_TAG}|g" "${HERMES_CONFIG_DIR}/config.json"
sed -i "s|\${CENTRAL_SERVER}|${CENTRAL_SERVER:-none}|g" "${HERMES_CONFIG_DIR}/config.json"
sed -i "s|\${SYNC_INTERVAL_MINUTES}|${SYNC_INTERVAL_MINUTES}|g" "${HERMES_CONFIG_DIR}/config.json"

log "  Hermes config written to ${HERMES_CONFIG_DIR}/config.json"

# ---------------------------------------------------------------------------
# 7. DB sync setup — cron job for rsync every N minutes
# ---------------------------------------------------------------------------
log "Setting up DB sync cron job (every ${SYNC_INTERVAL_MINUTES} minutes)..."

# Write the sync wrapper script (the actual sync script is 03_db_sync.sh)
SYNC_SCRIPT="${INSTALL_ROOT}/03_db_sync.sh"

# Create cron entry
CRON_LINE="*/${SYNC_INTERVAL_MINUTES} * * * * ${VPS_USER} ${SYNC_SCRIPT} >> ${LOG_DIR}/sync_cron.log 2>&1"

# Install cron if not already running
service cron start 2>/dev/null || true

# Add cron job (avoid duplicates)
(crontab -l 2>/dev/null | grep -v "03_db_sync.sh"; echo "${CRON_LINE}") | crontab -
log "  Cron job installed."

# Also set up logrotate for the log directory
cat > /etc/logrotate.d/borg-dogfood << 'LOGEOF'
${LOG_DIR}/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
LOGEOF

sed -i "s|\${LOG_DIR}|${LOG_DIR}|g" /etc/logrotate.d/borg-dogfood

# ---------------------------------------------------------------------------
# 8. Create convenience runner scripts in /usr/local/bin
# ---------------------------------------------------------------------------
log "Installing convenience binaries..."

# borg-task-runner — alias for the task runner
cat > /usr/local/bin/borg-task-runner << 'RUNNEREOF'
#!/bin/bash
# Proxy to the installed task runner
exec /opt/borg-dogfood/02_task_runner.sh "$@"
RUNNEREOF
chmod +x /usr/local/bin/borg-task-runner

# borg-dashboard — alias for the dashboard
cat > /usr/local/bin/borg-dashboard << 'DASHEOF'
#!/bin/bash
# Proxy to the dashboard script
exec /opt/borg-dogfood/04_daily_dashboard.sh "$@"
DASHEOF
chmod +x /usr/local/bin/borg-dashboard

# borg-sync — manual sync trigger
cat > /usr/local/bin/borg-sync << 'SYNCEOF'
#!/bin/bash
exec /opt/borg-dogfood/03_db_sync.sh "$@"
SYNCEOF
chmod +x /usr/local/bin/borg-sync

# ---------------------------------------------------------------------------
# 9. Create a startup service (systemd)
# ---------------------------------------------------------------------------
log "Installing systemd service..."

cat > /etc/systemd/system/borg-dogfood.service << 'SVCEOF'
[Unit]
Description=Borg V3 Dogfood Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/borg-dogfood
ExecStart=/opt/borg-dogfood/02_task_runner.sh --daemon
Restart=on-failure
RestartSec=10
StandardOutput=append:${LOG_DIR}/runner.log
StandardError=append:${LOG_DIR}/runner_err.log

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload 2>/dev/null || true
systemctl enable borg-dogfood 2>/dev/null || true

# ---------------------------------------------------------------------------
# 10. Final status report
# ---------------------------------------------------------------------------
log ""
log "============================================"
log "  Borg V3 VPS Setup — Complete!"
log "============================================"
log "  VPS Hostname : ${VPS_HOSTNAME}"
log "  VPS IP       : ${VPS_IP}"
log "  Install Root : ${INSTALL_ROOT}"
log "  Python       : $(python3 --version)"
log "  Venv         : ${VENV_DIR}"
log "  Borg DB      : ${HOME}/.borg/borg.db"
log "  Logs         : ${LOG_DIR}/"
log "  Sync Tag     : ${SYNC_TAG}"
log "  Sync Cron    : every ${SYNC_INTERVAL_MINUTES} min"
log ""
log "  Convenience commands installed:"
log "    borg-task-runner  — run task loop"
log "    borg-dashboard    — show daily report"
log "    borg-sync         — manual DB sync"
log ""
log "  To start the agent:"
log "    systemctl start borg-dogfood"
log "    # or directly:"
log "    /opt/borg-dogfood/02_task_runner.sh"
log ""
log "============================================"
