#!/bin/bash
# Post-release cold smoke against the PUBLISHED PyPI wheel.
#
#   bash scripts/cold_smoke_pypi.sh 3.3.20
#
# Spins a fresh python:3.12-slim container and runs DAY1_USER_KIT.md's
# "minutes 0-10" verbatim: pipx install agent-borg==<version>, the README
# quickstart rescue (must MATCH), the honesty probe (must NO_CONFIDENT_MATCH),
# and the `borg status` Value block (the user proof command). Exit 0 = a
# day-1 pilot user following the kit gets value from the published wheel.
#
# Run this AFTER the tag's wheel lands on PyPI, before sending any invite.
set -euo pipefail

VERSION="${1:?usage: bash scripts/cold_smoke_pypi.sh <published-version, e.g. 3.3.20>}"
IMAGE="${COLD_SMOKE_IMAGE:-python:3.12-slim}"

docker run --rm -i "$IMAGE" bash -s "$VERSION" <<'INNER'
set -u
VERSION="$1"
PASS=0; FAIL=0
check() { if [ "$2" -eq 0 ]; then echo "[PASS] $1"; PASS=$((PASS+1)); else echo "[FAIL] $1"; FAIL=$((FAIL+1)); fi }

echo "== cold smoke: agent-borg==${VERSION} on $(python --version) =="
T0=$(date +%s)

# Minute 0-2: install + first rescue (kit, verbatim)
pip install --quiet pipx
export PATH="$PATH:/root/.local/bin"
pipx install "agent-borg==${VERSION}" >/tmp/pipx.log 2>&1
check "pipx install agent-borg==${VERSION} (published wheel)" $?
borg --version >/tmp/v.log 2>&1 && grep -q "$VERSION" /tmp/v.log
check "borg --version reports ${VERSION} ($(head -1 /tmp/v.log 2>/dev/null))" $?

borg rescue "ModuleNotFoundError: No module named flask" --short >/tmp/rescue.log 2>&1
grep -qi "matched" /tmp/rescue.log
check "kit quickstart rescue -> matched" $?
T_VALUE=$(date +%s)

# Minute 6-8: honesty probe (kit, verbatim)
borg rescue "how do I get better at python?" --short >/tmp/probe.log 2>&1
grep -qi "no_confident_match\|no confident match" /tmp/probe.log
check "honesty probe -> NO_CONFIDENT_MATCH" $?

# Minute 8-10: the proof command (kit, verbatim)
borg status >/tmp/status.log 2>&1
grep -q "Value on this machine" /tmp/status.log; check "borg status shows Value block" $?
grep -q "Found known fixes:" /tmp/status.log; check "borg status shows fired tally (found known fixes)" $?
grep -E -q "Caught (after )?your agent (was )?stuck" /tmp/status.log; check "borg status shows caught-your-agent-stuck headline" $?
grep -q "not claimed" /tmp/status.log; check "borg status keeps honesty caveat" $?

TTV=$((T_VALUE - T0))
echo
echo "TTV (install start -> first matched rescue): ${TTV}s"
[ "$TTV" -le 600 ]; check "TTV <= 10 minutes" $?

echo
echo "RESULT: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && echo "COLD SMOKE (${VERSION}): ALL CHECKS PASSED" || echo "COLD SMOKE (${VERSION}): FAILURES PRESENT — do NOT invite users"
exit $FAIL
INNER
