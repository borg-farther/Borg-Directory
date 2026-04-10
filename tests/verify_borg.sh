#!/bin/bash
# =============================================================================
# Borg E2E Verification Scorecard
# =============================================================================
# Runs the full verification harness and outputs a human-readable scorecard.
#
# Usage: bash tests/verify_borg.sh
#   or:  ./tests/verify_borg.sh
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BORG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_FILE="$SCRIPT_DIR/test_e2e_verify.py"

cd "$BORG_DIR"

echo "=============================================="
echo "  BORG E2E VERIFICATION SCORECARD"
echo "  $(date)"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
TRACE_CAPTURE="?"
TRACE_RETRIEVAL="?"
PACK_SEARCH="?"
FULL_LOOP="?"
VALUE_ADD="?"

# Run pytest with detailed output
echo -e "${BLUE}[RUNNING]${NC} Running E2E verification harness..."
echo ""

# Run pytest and capture output
PYTEST_OUTPUT=$(python -m pytest "$TEST_FILE" -v --tb=short 2>&1) || true

echo "$PYTEST_OUTPUT"
echo ""

# Parse results
# Count passes, failures, xfails
TOTAL_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "PASSED" || true)
TOTAL_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "FAILED" || true)
TOTAL_XFAIL=$(echo "$PYTEST_OUTPUT" | grep -c "XFAIL" || true)
TOTAL_XPASS=$(echo "$PYTEST_OUTPUT" | grep -c "XPASS" || true)

echo ""
echo "----------------------------------------------"
echo "  TEST SUMMARY"
echo "----------------------------------------------"
echo "  Total PASSED : $TOTAL_PASS"
echo "  Total FAILED : $TOTAL_FAIL"
echo "  Total XFAIL  : $TOTAL_XFAIL (expected failures)"
echo "  Total XPASS  : $TOTAL_XPASS (unexpected passes)"
echo ""

# Individual test result parsing
get_test_result() {
    local test_name="$1"
    # Look for this test's result
    if echo "$PYTEST_OUTPUT" | grep -q "${test_name}.*XPASS"; then
        echo "PASS"  # Was xfail but now passes!
    elif echo "$PYTEST_OUTPUT" | grep -q "${test_name}.*XFAIL"; then
        echo "FAIL"  # Expected fail and still fails
    elif echo "$PYTEST_OUTPUT" | grep -q "${test_name}.*PASSED"; then
        echo "PASS"
    elif echo "$PYTEST_OUTPUT" | grep -q "${test_name}.*FAILED"; then
        echo "FAIL"
    else
        echo "?"
    fi
}

# Categorize by functional area
echo ""
echo "=============================================="
echo "  FUNCTIONAL AREA SCORECARD"
echo "=============================================="
echo ""

# TRACE CAPTURE
# Tests: TestTraceCapture
TC_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestTraceCapture.*PASSED" || true)
TC_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "TestTraceCapture.*FAILED" || true)
if [ "$TC_FAIL" -gt 0 ]; then
    TRACE_CAPTURE="FAIL"
    echo -e "  TRACE CAPTURE  : ${RED}FAIL${NC} ($TC_PASS passed, $TC_FAIL failed)"
elif [ "$TC_PASS" -gt 0 ]; then
    TRACE_CAPTURE="PASS"
    echo -e "  TRACE CAPTURE  : ${GREEN}PASS${NC} ($TC_PASS passed)"
else
    echo -e "  TRACE CAPTURE  : ${YELLOW}?${NC} (no results)"
fi

# TRACE RETRIEVAL
# Tests: TestTraceRetrieval (mostly xfail)
TR_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestTraceRetrieval.*PASSED" || true)
TR_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "TestTraceRetrieval.*FAILED" || true)
TR_XPASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestTraceRetrieval.*XPASS" || true)
if [ "$TR_XPASS" -gt 0 ]; then
    TRACE_RETRIEVAL="PASS"
    echo -e "  TRACE RETRIEVAL: ${GREEN}PASS${NC} (was xfail, now passes!)"
elif [ "$TR_FAIL" -gt 0 ] && [ "$TR_PASS" -eq 0 ]; then
    TRACE_RETRIEVAL="FAIL"
    echo -e "  TRACE RETRIEVAL: ${YELLOW}FAIL${NC} (expected fail - not wired yet)"
elif [ "$TR_PASS" -gt 0 ] && [ "$TR_FAIL" -eq 0 ]; then
    TRACE_RETRIEVAL="PASS"
    echo -e "  TRACE RETRIEVAL: ${GREEN}PASS${NC}"
else
    echo -e "  TRACE RETRIEVAL: ${YELLOW}PARTIAL${NC} ($TR_PASS pass, $TR_FAIL fail)"
fi

# PACK SEARCH
# Tests: TestPackSearch
PS_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestPackSearch.*PASSED" || true)
PS_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "TestPackSearch.*FAILED" || true)
if [ "$PS_FAIL" -gt 0 ]; then
    PACK_SEARCH="FAIL"
    echo -e "  PACK SEARCH    : ${RED}FAIL${NC} ($PS_PASS passed, $PS_FAIL failed)"
elif [ "$PS_PASS" -gt 0 ]; then
    PACK_SEARCH="PASS"
    echo -e "  PACK SEARCH    : ${GREEN}PASS${NC} ($PS_PASS passed)"
else
    echo -e "  PACK SEARCH    : ${YELLOW}?${NC} (no results)"
fi

# FULL LOOP
# Tests: TestFullLoop
FL_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestFullLoop.*PASSED" || true)
FL_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "TestFullLoop.*FAILED" || true)
FL_XPASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestFullLoop.*XPASS" || true)
if [ "$FL_XPASS" -gt 0 ]; then
    FULL_LOOP="PASS"
    echo -e "  FULL LOOP      : ${GREEN}PASS${NC} (was xfail, now passes!)"
elif [ "$FL_FAIL" -gt 0 ] && [ "$FL_PASS" -eq 0 ]; then
    FULL_LOOP="FAIL"
    echo -e "  FULL LOOP      : ${YELLOW}FAIL${NC} (expected fail - not wired yet)"
elif [ "$FL_PASS" -gt 0 ]; then
    FULL_LOOP="PASS"
    echo -e "  FULL LOOP      : ${GREEN}PASS${NC} ($FL_PASS passed)"
else
    echo -e "  FULL LOOP      : ${YELLOW}?${NC} (no results)"
fi

# VALUE MEASUREMENT
# Tests: TestValueMeasurement
VM_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestValueMeasurement.*PASSED" || true)
VM_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "TestValueMeasurement.*FAILED" || true)
VM_XPASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestValueMeasurement.*XPASS" || true)
if [ "$VM_XPASS" -gt 0 ]; then
    VALUE_ADD="PASS"
    echo -e "  VALUE ADD      : ${GREEN}PASS${NC} (was xfail, now passes!)"
elif [ "$VM_FAIL" -gt 0 ] && [ "$VM_PASS" -eq 0 ]; then
    VALUE_ADD="FAIL"
    echo -e "  VALUE ADD      : ${YELLOW}FAIL${NC} (expected fail - not wired yet)"
elif [ "$VM_PASS" -gt 0 ]; then
    VALUE_ADD="PASS"
    echo -e "  VALUE ADD      : ${GREEN}PASS${NC} ($VM_PASS passed)"
else
    echo -e "  VALUE ADD      : ${YELLOW}?${NC} (no results)"
fi

# SYSTEM HEALTH
SH_PASS=$(echo "$PYTEST_OUTPUT" | grep -c "TestSystemHealth.*PASSED" || true)
SH_FAIL=$(echo "$PYTEST_OUTPUT" | grep -c "TestSystemHealth.*FAILED" || true)
if [ "$SH_FAIL" -gt 0 ]; then
    echo -e "  SYSTEM HEALTH   : ${RED}FAIL${NC} ($SH_PASS passed, $SH_FAIL failed)"
elif [ "$SH_PASS" -gt 0 ]; then
    echo -e "  SYSTEM HEALTH   : ${GREEN}PASS${NC} ($SH_PASS passed)"
fi

echo ""
echo "=============================================="
echo "  SCORECARD SUMMARY"
echo "=============================================="
echo ""
printf "  %-20s %-10s\n" "TRACE CAPTURE:" "$TRACE_CAPTURE"
printf "  %-20s %-10s\n" "TRACE RETRIEVAL:" "$TRACE_RETRIEVAL (expected fail)"
printf "  %-20s %-10s\n" "PACK SEARCH:" "$PACK_SEARCH"
printf "  %-20s %-10s\n" "FULL LOOP:" "$FULL_LOOP (expected fail)"
printf "  %-20s %-10s\n" "VALUE ADD:" "$VALUE_ADD (expected fail)"
echo ""

# Overall status
OVERALL="PASS"
if [ "$TRACE_CAPTURE" != "PASS" ]; then
    OVERALL="FAIL"
fi
if [ "$PACK_SEARCH" != "PASS" ]; then
    OVERALL="FAIL"
fi

if [ "$OVERALL" == "PASS" ]; then
    echo -e "  ${GREEN}OVERALL: PASS${NC} - Core functionality working"
else
    echo -e "  ${RED}OVERALL: FAIL${NC} - Fix issues above before shipping"
fi

echo ""
echo "=============================================="
echo ""

# Exit with appropriate code
if [ "$OVERALL" == "PASS" ]; then
    exit 0
else
    exit 1
fi
