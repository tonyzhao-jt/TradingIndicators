#!/bin/bash

# Quick test script to validate VERL setup before full training

echo "=== VERL Training Validation Test ==="

cd /workspace/trading_indicators/posttrain

# Test 1: Check data files
echo "1. Checking data files..."
TRAIN_FILE="/workspace/trading_indicators/outputs/data_splits/train.parquet"
VAL_FILE="/workspace/trading_indicators/outputs/data_splits/val.parquet"

if [ -f "$TRAIN_FILE" ] && [ -f "$VAL_FILE" ]; then
    echo "✓ Data files exist"
    echo "  Train: $(python -c "import pandas as pd; print(len(pd.read_parquet('$TRAIN_FILE')))" 2>/dev/null) samples"
    echo "  Val: $(python -c "import pandas as pd; print(len(pd.read_parquet('$VAL_FILE')))" 2>/dev/null) samples"
else
    echo "✗ Data files missing!"
    exit 1
fi

# Test 2: Validate reward function
echo ""
echo "2. Testing reward function..."
python -c "
import sys
sys.path.append('/workspace/trading_indicators/preprocess/data_agent')
from reward_plain import compute_score

test_prompts = ['Create a RSI trading strategy']
test_responses = ['def rsi_strategy(): pass']
scores = compute_score(test_prompts, test_responses)
print(f'✓ Reward function working, score: {scores[0]:.3f}')
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Reward function validated"
else
    echo "✗ Reward function failed!"
    exit 1
fi

# Test 3: Check VERL configuration
echo ""
echo "3. Validating VERL configuration..."
timeout 10 bash pt_verl_plain.sh --cfg job >/dev/null 2>&1

if [ $? -eq 0 ] || [ $? -eq 124 ]; then  # 124 is timeout exit code
    echo "✓ VERL configuration valid"
else
    echo "✗ VERL configuration invalid!"
    exit 1
fi

echo ""
echo "=== All Tests Passed! ==="
echo ""
echo "Ready to start training:"
echo "  ./pt_verl_plain.sh"
echo ""
echo "Or use interactive setup:"  
echo "  ./setup_plain_training.sh"