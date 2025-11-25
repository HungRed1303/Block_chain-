#!/bin/bash
# Test Suite Runner
# Runs all tests and reports results

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "BLOCKCHAIN LAB 01 - TEST SUITE"
echo "========================================"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED} pytest not found. Installing...${NC}"
    pip install pytest pytest-cov
fi

FAILED=0

# Function to run test and track failures
run_test() {
    local test_file=$1
    local test_name=$2
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE} $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN} $test_name PASSED${NC}"
    else
        echo -e "${RED} $test_name FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Unit Tests
echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}     UNIT TESTS${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"

run_test "tests/test_crypto.py" "Cryptography Tests"
run_test "tests/test_state.py" "State Tests"
run_test "tests/test_transaction.py" "Transaction Tests"
run_test "tests/test_block.py" "Block Tests"
run_test "tests/test_network.py" "Network Tests"
run_test "tests/test_consensus.py" "Consensus Tests"

# Integration Tests
echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}     INTEGRATION TESTS${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"

run_test "tests/test_e2e.py" "End-to-End Tests"

# Determinism Check
echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}     DETERMINISM CHECK${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"

if bash scripts/determinism_check.sh > /dev/null 2>&1; then
    echo -e "${GREEN} Determinism Check PASSED${NC}"
else
    echo -e "${RED} Determinism Check FAILED${NC}"
    FAILED=$((FAILED + 1))
fi

# Coverage Report (optional)
echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}     CODE COVERAGE${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"

pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -q

echo ""
echo " Coverage report generated: htmlcov/index.html"
# Final Summary
echo ""
echo "========================================"
echo "TEST SUITE SUMMARY"
echo "========================================"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN} ALL TESTS PASSED${NC}"
    echo ""
    echo "  Unit Tests:        ✓"
    echo "  Integration Tests: ✓"
    echo "  Determinism:       ✓"
    echo ""
    exit 0
else
    echo -e "${RED} $FAILED TEST(S) FAILED${NC}"
    echo ""
    exit 1
fi