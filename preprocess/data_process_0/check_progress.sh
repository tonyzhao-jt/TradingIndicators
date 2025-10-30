#!/bin/bash
# Check current progress of data_process_0

echo "=== Data Process 0 Progress Check ==="
echo ""

CHECKPOINT_FILE="/workspace/trading_indicators/outputs/processed/processing_checkpoint.json"
INPUT_FILE="/workspace/trading_indicators/outputs/strategies_20251014_054134.json"

if [ -f "$CHECKPOINT_FILE" ]; then
    echo "📊 Current Progress:"
    
    # Get last_index from checkpoint
    LAST_INDEX=$(python3 -c "
import json
with open('$CHECKPOINT_FILE', 'r') as f:
    data = json.load(f)
print(data.get('last_index', 0))
")
    
    # Get total items from input
    TOTAL_ITEMS=$(python3 -c "
import json
with open('$INPUT_FILE', 'r') as f:
    data = json.load(f)
print(len(data))
")
    
    # Get processed count
    PROCESSED_COUNT=$(python3 -c "
import json
with open('$CHECKPOINT_FILE', 'r') as f:
    data = json.load(f)
print(len(data.get('processed_ids', [])))
")
    
    PROGRESS=$(python3 -c "print(f'{($LAST_INDEX/$TOTAL_ITEMS)*100:.1f}')")
    
    echo "  Last processed index: $LAST_INDEX"
    echo "  Total items: $TOTAL_ITEMS"
    echo "  Processed items: $PROCESSED_COUNT"
    echo "  Progress: $PROGRESS%"
    echo "  Remaining: $((TOTAL_ITEMS - LAST_INDEX)) items"
    echo ""
    
    # Show recent processing activity
    echo "📁 Output Files:"
    ls -la /workspace/trading_indicators/outputs/processed/*.json | tail -5
    
else
    echo "❌ No checkpoint found. Processing hasn't started yet."
fi

echo ""
echo "🚀 To continue/start processing, run:"
echo "cd /workspace/trading_indicators/preprocess/data_process_0 && ./run.sh"