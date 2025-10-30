#!/bin/bash
# Run script for data_process_script pipeline

# Set environment variables (optional)
export INPUT_FILE="${INPUT_FILE:-/workspace/trading_indicators/outputs/strategies_20251014_054134.json}"
export OUTPUT_DIR="${OUTPUT_DIR:-/workspace/trading_indicators/outputs/processed_scripts}"
export MIN_LIKES_COUNT="${MIN_LIKES_COUNT:-100}"
export QUALITY_SCORE_THRESHOLD="${QUALITY_SCORE_THRESHOLD:-7.0}"
export MAX_WORKERS="${MAX_WORKERS:-3}"

# LLM configuration
export LOCAL_QWEN_ENDPOINT="${LOCAL_QWEN_ENDPOINT:-http://202.45.128.234:5788/v1/}"
export LOCAL_QWEN_MODEL_NAME="${LOCAL_QWEN_MODEL_NAME:-/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct}"
export LOCAL_QWEN_API_KEY="${LOCAL_QWEN_API_KEY:-none}"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run the pipeline
echo "Starting Data Process Script Pipeline..."
echo "Input: $INPUT_FILE"
echo "Output: $OUTPUT_DIR"
echo "Min Likes: $MIN_LIKES_COUNT"
echo "Quality Threshold: $QUALITY_SCORE_THRESHOLD"
echo ""

python main.py \
    --input "$INPUT_FILE" \
    --output_dir "$OUTPUT_DIR" \
    --min_likes "$MIN_LIKES_COUNT" \
    --quality_threshold "$QUALITY_SCORE_THRESHOLD" \
    --max_workers "$MAX_WORKERS"

echo ""
echo "Pipeline completed!"
