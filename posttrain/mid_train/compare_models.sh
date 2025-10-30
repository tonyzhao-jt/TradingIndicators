#!/bin/bash
# Compare two models using evaluator.py

# Default values
MODEL1_PATH="${1:-./model_cache/Qwen/Qwen2.5-Coder-7B}"
MODEL2_PATH="${2:-./pine-coder-mid}"
DATA_PATH="${3:-/workspace/trading_indicators/outputs/segments_20251014.json}"
OUTPUT_PATH="${4:-./comparison_results.json}"

echo "=================================================="
echo "Model Comparison Script"
echo "=================================================="
echo "Model 1: $MODEL1_PATH"
echo "Model 2: $MODEL2_PATH"
echo "Test Data: $DATA_PATH"
echo "Output: $OUTPUT_PATH"
echo "=================================================="
echo ""

python evaluator.py \
    --model1_path "$MODEL1_PATH" \
    --model2_path "$MODEL2_PATH" \
    --data_path "$DATA_PATH" \
    --output_path "$OUTPUT_PATH" \
    --max_samples 50 \
    --temperature 0.7 \
    --max_new_tokens 512 \
    --batch_size 1 \
    --device auto \
    --dtype auto \
    --save_outputs

echo ""
echo "Comparison complete! Check results at: $OUTPUT_PATH"
