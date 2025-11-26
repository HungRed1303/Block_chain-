#!/bin/bash
# Determinism Check Script - FIXED VERSION
# Compares final state and event sequence (not timestamps)

set -e

echo "========================================"
echo "DETERMINISM CHECK - FIXED"
echo "========================================"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

CONFIG="${1:-config/chain_config.json}"
LOG_DIR="logs"

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

sleep 1

# Run 2
echo -e "${YELLOW}Running simulation #2...${NC}"
python run.py "$CONFIG" > "$LOG_DIR/stdout2.log" 2>&1
EXIT_CODE2=$?

if [ $EXIT_CODE2 -ne 0 ]; then
    echo -e "${RED}Run 2 failed with exit code $EXIT_CODE2${NC}"
    cat "$LOG_DIR/stdout2.log"
    exit 1
fi

cp "$LOG_DIR/simulation.json" "$LOG_DIR/run2.json"
echo -e "${GREEN}✓ Run 2 completed${NC}"

echo ""
echo "Comparing results..."

# Extract final states (ignore timestamps)
python3 << 'PYTHON'
import json
import hashlib

def extract_final_state(log_file):
    """Extract final state hash and event sequence (without timestamps)"""
    with open(log_file, 'r') as f:
        events = json.load(f)
    
    # Extract event types and data (ignore timestamps)
    event_sequence = []
    final_state = None
    
    for event in events:
        event_type = event.get('type')
        event_data = event.get('data', {})
        
        # Store event type and relevant data
        event_sequence.append({
            'type': event_type,
            'data': event_data
        })
        
        # Track final state
        if event_type == 'block_finalized':
            final_state = event_data
    
    return {
        'event_sequence': event_sequence,
        'final_state': final_state,
        'num_events': len(events)
    }

# Compare runs
run1 = extract_final_state('logs/run1.json')
run2 = extract_final_state('logs/run2.json')

print("Run 1:")
print(f"  Events: {run1['num_events']}")
print(f"  Final state: {run1['final_state']}")

print("\nRun 2:")
print(f"  Events: {run2['num_events']}")
print(f"  Final state: {run2['final_state']}")

# Check determinism
issues = []

# 1. Check same number of events
if run1['num_events'] != run2['num_events']:
    issues.append(f"Different event counts: {run1['num_events']} vs {run2['num_events']}")

# 2. Check same event sequence
if run1['event_sequence'] != run2['event_sequence']:
    issues.append("Event sequences differ")

# 3. Check same final state
if run1['final_state'] != run2['final_state']:
    issues.append(f"Final states differ: {run1['final_state']} vs {run2['final_state']}")

if issues:
    print("\n" + "="*60)
    print("DETERMINISM CHECK FAILED")
    print("="*60)
    for issue in issues:
        print(f"  ✗ {issue}")
    exit(1)
else:
    print("\n" + "="*60)
    print("✓ DETERMINISM CHECK PASSED")
    print("="*60)
    print("  ✓ Same number of events")
    print("  ✓ Same event sequence")
    print("  ✓ Same final state")
    exit(0)
PYTHON