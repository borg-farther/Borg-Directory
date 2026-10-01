#!/usr/bin/env bash
# Build the actual wheel, force-install it from a clean cwd, and exercise the
# first-user CLI + MCP path without allowing the checkout to shadow the wheel.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
cleanup() {
  python3 - "$WORK" "$REPO_ROOT/build" <<'PY'
import shutil, sys
for path in sys.argv[1:]:
    shutil.rmtree(path, ignore_errors=True)
PY
}
trap cleanup EXIT

export HOME="$WORK/home"
export BORG_HOME="$WORK/borg-home"
export BORG_DIR="$BORG_HOME"
export PYTHONPATH=""
export PYTHONNOUSERSITE=1
mkdir -p "$HOME" "$BORG_HOME"

printf '%s\n' '== build wheel in an isolated builder =='
python -m venv "$WORK/builder"
"$WORK/builder/bin/pip" install --quiet --upgrade build
(
  cd "$REPO_ROOT"
  "$WORK/builder/bin/python" -m build --wheel --outdir "$WORK/dist" >/dev/null
)
wheels=("$WORK"/dist/agent_borg-*.whl)
if [ "${#wheels[@]}" -ne 1 ] || [ ! -f "${wheels[0]}" ]; then
  printf '%s\n' 'expected exactly one agent_borg wheel' >&2
  exit 1
fi
WHEEL="${wheels[0]}"
printf 'built: %s\n' "$(basename "$WHEEL")"

printf '%s\n' '== force-install wheel from a clean cwd =='
python -m venv "$WORK/venv"
(
  cd "$WORK"
  "$WORK/venv/bin/pip" install --quiet --isolated --no-cache-dir --force-reinstall "$WHEEL"
)
BIN="$WORK/venv/bin"

(
  cd "$WORK"
  "$BIN/python" - <<'PY'
import importlib.metadata as metadata
from pathlib import Path

import borg
from borg.core.runtime_fingerprint import runtime_fingerprint

venv = Path(__import__('sys').prefix).resolve()
module_path = Path(borg.__file__).resolve()
assert module_path.is_relative_to(venv), (module_path, venv)
version = metadata.version('agent-borg')
assert borg.__version__ == version
fingerprint = runtime_fingerprint()
assert fingerprint['success'] is True, fingerprint
assert fingerprint['source_version_basis'] == 'installed_distribution', fingerprint
assert fingerprint['version_matches_source'] is True, fingerprint
assert fingerprint['reload_status'] == 'loaded_code_matches_source_behavior', fingerprint
print({'version': version, 'module': str(module_path), 'fingerprint': fingerprint['reload_status']})
PY
)

PASS=0
FAIL=0
check() {
  if [ "$2" -eq 0 ]; then
    printf '[PASS] %s\n' "$1"
    PASS=$((PASS + 1))
  else
    printf '[FAIL] %s\n' "$1"
    FAIL=$((FAIL + 1))
  fi
}
check_grep() {
  local description="$1" pattern="$2" file="$3"
  if grep -qiE "$pattern" "$file"; then check "$description" 0; else check "$description" 1; fi
}
OUT="$WORK/out.log"

if (cd "$WORK" && "$BIN/borg" --version) >"$OUT" 2>&1; then
  check 'borg --version entry point resolves' 0
else
  check 'borg --version entry point resolves' 1
fi

(cd "$WORK" && "$BIN/borg" rescue "ModuleNotFoundError: No module named flask" --short) >"$OUT" 2>/dev/null || true
check_grep 'rescue matches from bundled wheel seed corpus' 'matched|bundled seed guidance' "$OUT"

(cd "$WORK" && "$BIN/borg" rescue "how do I get better at python?" --short) >"$OUT" 2>/dev/null || true
check_grep 'honesty probe returns no confident match' 'no_confident_match' "$OUT"

(
  cd "$WORK"
  printf '%s\n%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
    | "$BIN/borg-mcp"
) >"$OUT" 2>/dev/null || true
check_grep 'borg-mcp stdio handshake lists borg_rescue' 'borg_rescue' "$OUT"
check_grep 'borg-mcp stdio handshake lists runtime fingerprint' 'borg_runtime_fingerprint' "$OUT"

printf '\nRESULT: %s passed, %s failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -ne 0 ]; then
  printf '%s\n' 'WHEEL SMOKE: FAILURES — do not publish'
  exit 1
fi
printf '%s\n' 'WHEEL SMOKE: ALL CHECKS PASSED'
