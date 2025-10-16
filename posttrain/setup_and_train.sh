#!/bin/bash

# Complete VERL Training Setup Script for Trading Indicators
# This script prepares data and starts VERL training

set -e  # Exit on any error

echo "=== VERL Trading Indicators Training Setup ==="

# Configuration
TOOLS_DIR="/workspace/trading_indicators/preprocess/tools"
POSTTRAIN_DIR="/workspace/trading_indicators/posttrain"

# Step 1: Prepare data
echo ""
echo "1. Preparing training data..."
cd "$TOOLS_DIR"

if [ ! -f "prepare_verl_data.sh" ]; then
    echo "Error: Data preparation script not found!"
    exit 1
fi

./prepare_verl_data.sh

if [ $? -ne 0 ]; then
    echo "Error: Data preparation failed!"
    exit 1
fi

# Step 2: Verify reward function
echo ""
echo "2. Verifying reward function..."
cd "$POSTTRAIN_DIR"

if [ ! -f "reward_function.py" ]; then
    echo "Error: Reward function not found!"
    exit 1
fi

# Test the reward function
python -c "
from reward_function import create_reward_function
reward_fn = create_reward_function()
print('✓ Reward function loaded successfully')

# Quick test
test_prompt = 'Create a simple moving average strategy'
test_response = '''
def moving_average_strategy():
    # Calculate moving averages
    ma_short = data.rolling(10).mean()
    ma_long = data.rolling(30).mean()
    
    # Entry condition
    buy_signal = ma_short > ma_long
    
    # Exit condition
    sell_signal = ma_short < ma_long
    
    return buy_signal, sell_signal
'''
score = reward_fn(test_prompt, test_response)
print(f'✓ Reward function test score: {score:.3f}')
"

if [ $? -ne 0 ]; then
    echo "Error: Reward function test failed!"
    exit 1
fi

# Step 3: Check VERL training script
echo ""
echo "3. Checking VERL training configuration..."

if [ ! -f "pt_verl.sh" ]; then
    echo "Error: VERL training script not found!"
    exit 1
fi

if [ ! -x "pt_verl.sh" ]; then
    chmod +x pt_verl.sh
fi

echo "✓ VERL training script ready"

# Step 4: Display summary
echo ""
echo "=== Setup Complete ==="
echo "Configuration Summary:"
echo "  - Training data: $(wc -l < /workspace/trading_indicators/outputs/data_splits/train.parquet 2>/dev/null || echo 'N/A') samples"
echo "  - Validation data: $(wc -l < /workspace/trading_indicators/outputs/data_splits/val.parquet 2>/dev/null || echo 'N/A') samples"
echo "  - Reward function: Custom TradingIndicatorRewardFunction"
echo "  - Model: Qwen3-Coder-30B-A3B-Instruct"
echo "  - Training epochs: 50"
echo ""

# Step 5: Ask user if they want to start training
echo "Ready to start VERL training!"
echo ""
read -p "Do you want to start training now? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting VERL training..."
    echo "Note: This may take several hours. Monitor progress in wandb."
    echo "Project: verl_trading_indicators_small"
    echo ""
    
    # Start training
    ./pt_verl.sh
else
    echo ""
    echo "Training setup complete. To start training manually:"
    echo "  cd $POSTTRAIN_DIR"
    echo "  ./pt_verl.sh"
    echo ""
    echo "You can also monitor the training progress at:"
    echo "  https://wandb.ai/your-username/verl_trading_indicators_small"
fi