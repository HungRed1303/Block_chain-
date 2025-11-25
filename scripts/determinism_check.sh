#!/bin/bash
# Determinism Check Script
# Runs simulation twice and compares logs

set -e  # Exit on error

echo "========================================"
echo "DETERMINISM CHECK"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONFIG="${1:-config/chain_config.json}"
LOG_DIR="logs"

# Create logs directory if not exists
mkdir -p "$LOG_DIR"

echo ""
echo "Using config: $CONFIG"
echo ""

# Run 1
echo -e "${YELLOW}Running simulation #1...${NC}"
python run.py "$CONFIG" > "$LOG_DIR/stdout1.log" 2>&1
EXIT_CODE1=$?

if [ $EXIT_CODE1 -ne 0 ]; then
    echo -e "${RED}Run 1 failed with exit code $EXIT_CODE1${NC}"
    cat "$LOG_DIR/stdout1.log"
    exit 1
fi

cp "$LOG_DIR/simulation.json" "$LOG_DIR/run1.json"
echo -e "${GREEN}✓ Run 1 completed${NC}"

# Small delay
sleep 1

# Run 2
echo -e "${YELLOW} Running simulation #2...${NC}"
python run.py "$CONFIG" > "$LOG_DIR/stdout2.log" 2>&1
EXIT_CODE2=$?

if [ $EXIT_CODE2 -ne 0 ]; then
    echo -e "${RED}Run 2 failed with exit code $EXIT_CODE2${NC}"
    cat "$LOG_DIR/stdout2.log"
    exit 1
fi

cp "$LOG_DIR/simulation.json" "$LOG_DIR/run2.json"
echo -e "${GREEN}✓ Run 2 completed${NC}"

# Compare logs
echo ""
echo " Comparing results..."

# Compute hashes
HASH1=$(python3 -c "import json, hashlib; data = json.load(open('$LOG_DIR/run1.json')); print(hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest())")
HASH2=$(python3 -c "import json, hashlib; data = json.load(open('$LOG_DIR/run2.json')); print(hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest())")

echo "  Run 1 hash: $HASH1"
echo "  Run 2 hash: $HASH2"

# Extract final state from logs
STATE1=$(python3 -c "import json; events = json.load(open('$LOG_DIR/run1.json')); finalized = [e for e in events if e['type'] == 'block_finalized']; print(finalized[-1] if finalized else {})")
STATE2=$(python3 -c "import json; events = json.load(open('$LOG_DIR/run2.json')); finalized = [e for e in events if e['type'] == 'block_finalized']; print(finalized[-1] if finalized else {})")

echo ""
echo " Final states:"
echo "  Run 1: $STATE1"
echo "  Run 2: $STATE2"

# Detailed comparison
echo ""
if [ "$HASH1" = "$HASH2" ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN} DETERMINISM CHECK PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "✓ Logs are byte-identical"
    echo "✓ Events occurred in same order"
    echo "✓ Final states match"
    echo ""
    echo "Log hash: $HASH1"
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED} DETERMINISM CHECK FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "✗ Logs differ between runs"
    echo "✗ Non-deterministic behavior detected"
    echo ""
    
    # Show diff (first few lines)
    echo "Differences (first 20 lines):"
    diff <(python3 -m json.tool "$LOG_DIR/run1.json" | head -20) \
         <(python3 -m json.tool "$LOG_DIR/run2.json" | head -20) || true
    
    exit 1
fi