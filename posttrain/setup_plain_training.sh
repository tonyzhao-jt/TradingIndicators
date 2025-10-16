#!/bin/bash

# VERL Training Setup with Plain Reward Function
# This script prepares data and starts training with the simplified LLM-based reward function

set -e  # Exit on any error

echo "=== VERL Trading Indicators Training (Plain Reward) ==="

# Configuration
TOOLS_DIR="/workspace/trading_indicators/preprocess/tools"
POSTTRAIN_DIR="/workspace/trading_indicators/posttrain"

# Step 1: Prepare data (if needed)
echo ""
echo "1. Checking training data..."
TRAIN_FILE="/workspace/trading_indicators/outputs/data_splits/train.parquet"
VAL_FILE="/workspace/trading_indicators/outputs/data_splits/val.parquet"

if [ ! -f "$TRAIN_FILE" ] || [ ! -f "$VAL_FILE" ]; then
    echo "Training data not found. Preparing data..."
    cd "$TOOLS_DIR"
    ./prepare_verl_data.sh
    
    if [ $? -ne 0 ]; then
        echo "Error: Data preparation failed!"
        exit 1
    fi
else
    echo "✓ Training data found"
    echo "  - Train: $TRAIN_FILE"
    echo "  - Validation: $VAL_FILE"
fi

# Step 2: Verify plain reward function
echo ""
echo "2. Verifying plain reward function..."
cd "$POSTTRAIN_DIR"

if [ ! -f "reward_plain.py" ]; then
    echo "Error: Plain reward function not found!"
    exit 1
fi

# Test the plain reward function
python -c "
import sys
sys.path.append('/workspace/trading_indicators/preprocess/data_agent')
from reward_plain import create_plain_reward_function

# Test initialization
reward_fn = create_plain_reward_function(validation_file='$VAL_FILE')
print('✓ Plain reward function loaded successfully')

# Quick functionality test
test_prompt = 'Create a RSI trading strategy'
test_response = '''
def rsi_strategy():
    rsi = calculate_rsi(data)
    buy_signal = rsi < 30
    sell_signal = rsi > 70
    return buy_signal, sell_signal
'''
score = reward_fn(test_prompt, test_response)
print(f'✓ Reward function test score: {score:.3f}')
print('✓ Plain reward function is working correctly')
"

if [ $? -ne 0 ]; then
    echo "Error: Plain reward function test failed!"
    exit 1
fi

# Step 3: Check VERL training script
echo ""
echo "3. Checking VERL training configuration..."

if [ ! -f "pt_verl_plain.sh" ]; then
    echo "Error: VERL training script (plain) not found!"
    exit 1
fi

if [ ! -x "pt_verl_plain.sh" ]; then
    chmod +x pt_verl_plain.sh
fi

echo "✓ VERL training script ready"

# Step 4: Display summary and training options
echo ""
echo "=== Setup Complete ==="
echo "Configuration Summary:"
echo "  - Reward Function: Plain LLM-based evaluation"
echo "  - Model: Qwen3-Coder-30B-A3B-Instruct"
echo "  - Training samples: $(python -c "import pandas as pd; print(len(pd.read_parquet('$TRAIN_FILE')))" 2>/dev/null || echo 'Unknown')"
echo "  - Validation samples: $(python -c "import pandas as pd; print(len(pd.read_parquet('$VAL_FILE')))" 2>/dev/null || echo 'Unknown')"
echo "  - Training epochs: 50"
echo "  - Batch size: 8 (optimized for 30B model)"
echo "  - GPU memory optimization: FSDP with param/optimizer offload"
echo ""
echo "Plain Reward Function Features:"
echo "  ✓ LLM-based similarity evaluation (60% weight)"
echo "  ✓ Code correctness check (40% weight)"  
echo "  ✓ Syntax validation"
echo "  ✓ Reference data comparison"
echo ""

# Step 5: Training options
echo "Training Options:"
echo "  1. Start training immediately"
echo "  2. Start training in background (tmux)"
echo "  3. Just show command (don't start)"
echo "  4. Exit"
echo ""

read -p "Choose option (1-4): " -n 1 -r
echo

case $REPLY in
    1)
        echo ""
        echo "Starting VERL training (foreground)..."
        echo "Note: This will run in the current terminal. Use Ctrl+C to stop."
        echo "Monitor progress at: https://wandb.ai/your-username/verl_trading_plain_reward"
        echo ""
        sleep 2
        ./pt_verl_plain.sh
        ;;
    2)
        echo ""
        echo "Starting VERL training in tmux session..."
        
        # Create or attach to tmux session
        SESSION_NAME="verl_training"
        
        if tmux has-session -t $SESSION_NAME 2>/dev/null; then
            echo "Attaching to existing session: $SESSION_NAME"
            tmux attach -t $SESSION_NAME
        else
            echo "Creating new tmux session: $SESSION_NAME"
            tmux new-session -d -s $SESSION_NAME
            tmux send-keys -t $SESSION_NAME "cd $POSTTRAIN_DIR" Enter
            tmux send-keys -t $SESSION_NAME "./pt_verl_plain.sh" Enter
            echo "✓ Training started in background"
            echo "To attach: tmux attach -t $SESSION_NAME"
            echo "To detach: Ctrl+B, then D"
        fi
        ;;
    3)
        echo ""
        echo "VERL training command:"
        echo "  cd $POSTTRAIN_DIR"
        echo "  ./pt_verl_plain.sh"
        echo ""
        echo "Or run with custom arguments:"
        echo "  ./pt_verl_plain.sh trainer.total_epochs=50"
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option. Exiting..."
        exit 1
        ;;
esac

echo ""
echo "=== Training Setup Complete ==="