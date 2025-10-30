#!/bin/bash
# Quick test script for data_process_script pipeline
# Tests with a small subset of data

# Set test parameters
export INPUT_FILE="${INPUT_FILE:-/workspace/trading_indicators/outputs/strategies_20251014_054134.json}"
export OUTPUT_DIR="${OUTPUT_DIR:-./test_outputs}"
export MIN_LIKES_COUNT="${MIN_LIKES_COUNT:-50}"  # Lower threshold for testing
export QUALITY_SCORE_THRESHOLD="${QUALITY_SCORE_THRESHOLD:-6.0}"  # Lower threshold for testing
export MAX_WORKERS="${MAX_WORKERS:-2}"  # Fewer workers for testing
export DEBUG_NODE_OUTPUT="true"

# LLM configuration
export LOCAL_QWEN_ENDPOINT="${LOCAL_QWEN_ENDPOINT:-http://202.45.128.234:5788/v1/}"
export LOCAL_QWEN_MODEL_NAME="${LOCAL_QWEN_MODEL_NAME:-/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct}"
export LOCAL_QWEN_API_KEY="${LOCAL_QWEN_API_KEY:-none}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create a small test dataset (first 20 items)
TEST_INPUT="$OUTPUT_DIR/test_input.json"
echo "Creating test dataset from first 20 items..."
python3 -c "
import json
with open('$INPUT_FILE', 'r') as f:
    data = json.load(f)
with open('$TEST_INPUT', 'w') as f:
    json.dump(data[:20], f, indent=2)
print(f'Created test dataset with {min(20, len(data))} items')
"

# Run the pipeline with test data
echo ""
echo "Running test pipeline..."
echo "Input: $TEST_INPUT"
echo "Output: $OUTPUT_DIR"
echo ""

python main.py \
    --input "$TEST_INPUT" \
    --output_dir "$OUTPUT_DIR" \
    --min_likes "$MIN_LIKES_COUNT" \
    --quality_threshold "$QUALITY_SCORE_THRESHOLD" \
    --max_workers "$MAX_WORKERS"

echo ""
echo "Test completed! Check $OUTPUT_DIR for results."
