#!/usr/bin/env bash
# Build the wheel, install it in a FRESH venv (no source tree on sys.path), and
# smoke the day-1 path — so packaging breaks (missing seeds_data, broken entry
# points) are caught PRE-publish in CI, not after the wheel is on PyPI.
#
# CI runs `pip install -e .` (editable/source), which CANNOT catch a wheel that
# ships without its data files: the source tree's seeds_data is always present,
# so every editable test passes while the built wheel would answer every rescue
# with no_confident_match. This script closes that gap.
#
#   bash scripts/wheel_smoke.sh
#
# Exit 0 = a fresh `pip install agent-borg` of THIS commit's wheel delivers the
# day-1 path (entry points + bundled seeds + MCP stdio).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WORK="$(mktemp -d)"
# Also remove any build/ that `python -m build` leaves in the source tree — a
# stale build/lib/ is flagged by the hygiene tests (TestNoStaleBuildArtifact).
trap 'rm -rf "$WORK" "$REPO_ROOT/build"' EXIT
# Isolate HOME/BORG_HOME so the cold-start marker + receipts never touch the host.
export HOME="$WORK/home"; mkdir -p "$HOME"
export BORG_HOME="$WORK/borg"

echo "== build wheel (in a dedicated builder venv) =="
python -m venv "$WORK/builder"
"$WORK/builder/bin/pip" install --quiet --upgrade build
"$WORK/builder/bin/python" -m build --wheel --outdir "$WORK/dist" >/dev/null
WHEEL="$(ls -1 "$WORK"/dist/agent_borg-*.whl | head -1)"
echo "built: $(basename "$WHEEL")"

echo "== install wheel into a fresh venv (no source tree) =="
python -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install --quiet "$WHEEL"
BIN="$WORK/venv/bin"

PASS=0; FAIL=0
chk(){ if [ "$2" -eq 0 ]; then echo "[PASS] $1"; PASS=$((PASS+1)); else echo "[FAIL] $1"; FAIL=$((FAIL+1)); fi; }
# grep a captured logfile, set -e-safe (note: `borg rescue` intentionally exits 1
# on a miss, so we never gate on the CLI's exit code — only on the output).
chk_grep(){ local desc="$1" pat="$2" file="$3"; if grep -qiE "$pat" "$file"; then chk "$desc" 0; else chk "$desc" 1; fi; }

OUT="$WORK/out.log"
# Run everything from $WORK so the repo's ./borg is NOT importable — we test the
# INSTALLED package, not the checkout.

if ( cd "$WORK" && "$BIN/borg" --version ) >/dev/null 2>&1; then
  chk "borg --version (entry point resolves)" 0; else chk "borg --version (entry point resolves)" 1; fi

# The load-bearing packaging check: seeds_data IS in the wheel, so a known rescue
# MATCHES. A wheel built without seeds_data fails exactly here (not in editable CI).
( cd "$WORK" && "$BIN/borg" rescue "ModuleNotFoundError: No module named flask" --short ) >"$OUT" 2>/dev/null || true
chk_grep "rescue -> matched (bundled seed corpus present in wheel)" "matched" "$OUT"

# Honesty path intact from the wheel.
( cd "$WORK" && "$BIN/borg" rescue "how do I get better at python?" --short ) >"$OUT" 2>/dev/null || true
chk_grep "honesty probe -> no_confident_match" "no_confident_match" "$OUT"

# MCP stdio entry point handshakes and lists tools from the installed wheel.
( cd "$WORK" && printf '%s\n%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | "$BIN/borg-mcp" ) >"$OUT" 2>/dev/null || true
chk_grep "borg-mcp stdio handshake lists borg_rescue" "borg_rescue" "$OUT"

echo
echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ]; then
  echo "WHEEL SMOKE: ALL CHECKS PASSED"
else
  echo "WHEEL SMOKE: FAILURES — the built wheel is broken; do NOT publish"
  exit 1
fi
