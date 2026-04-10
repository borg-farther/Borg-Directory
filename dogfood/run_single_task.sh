#!/bin/bash
# Run a single experiment task via subagent and measure results
# Usage: ./run_single_task.sh TASK_ID CONDITION [results_file]
# CONDITION: control | treatment

set -e

TASK_ID="$1"
CONDITION="$2"
RESULTS_FILE="${3:-/root/hermes-workspace/borg/dogfood/results.json}"
REPO_BASE="/root/hermes-workspace/borg/dogfood/experiment_repos"
WORK_DIR="/tmp/experiment_${TASK_ID}_${CONDITION}"

if [ -z "$TASK_ID" ] || [ -z "$CONDITION" ]; then
    echo "Usage: $0 TASK_ID [control|treatment] [results_file]"
    exit 1
fi

REPO_DIR="${REPO_BASE}/${TASK_ID}"
if [ ! -d "$REPO_DIR" ]; then
    echo "ERROR: Repo not found: $REPO_DIR"
    exit 1
fi

echo "=== EXPERIMENT RUN ==="
echo "Task: $TASK_ID"
echo "Condition: $CONDITION"
echo "Work dir: $WORK_DIR"
echo ""

# 1. Prepare workspace
rm -rf "$WORK_DIR"
cp -r "$REPO_DIR" "$WORK_DIR"
cd "$WORK_DIR"
chmod +x setup.sh check.sh 2>/dev/null

# 2. Run setup
echo "[SETUP] Running setup.sh..."
bash setup.sh 2>&1 | tail -3
echo ""

# 3. Verify starting state fails
echo "[VERIFY] Checking starting state fails..."
bash check.sh >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "ERROR: check.sh passes in starting state! Task invalid."
    exit 1
fi
echo "  Starting state correctly fails. ✓"
echo ""

# 4. Read the prompt from README.md
PROMPT=$(cat README.md 2>/dev/null | head -20)
echo "[PROMPT] Task description:"
echo "  $PROMPT" | head -5
echo ""

# 5. Start timer
START_TIME=$(date +%s)
echo "[START] $(date -Iseconds)"
echo ""

# The actual agent run happens externally (via delegate_task)
# This script just prepares and verifies
echo "[READY] Workspace prepared at: $WORK_DIR"
echo "[READY] After agent finishes, run:"
echo "  cd $WORK_DIR && bash check.sh"
echo "  Then: python3 /root/hermes-workspace/borg/dogfood/record_result.py $TASK_ID $CONDITION [true|false] [tokens] [time] [tool_calls] [borg_searches]"
