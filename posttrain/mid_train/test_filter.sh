#!/bin/bash
# Quick test for data_filter.py

echo "Testing data_filter.py..."
echo ""

# Use the mixed dataset that was just created
INPUT="/workspace/trading_indicators/outputs/dataset/mixed_dataset_0.7_original.json"
OUTPUT="/workspace/trading_indicators/outputs/mixed_train_filtered_test.json"
REMOVED="/workspace/trading_indicators/outputs/mixed_train_removed_test.json"
STATS="/workspace/trading_indicators/outputs/mixed_train_stats_test.json"

# Check if input exists
if [ ! -f "$INPUT" ]; then
    echo "❌ Input file not found: $INPUT"
    echo "Please run the mix.sh script first to create mixed data"
    exit 1
fi

echo "Input:  $INPUT"
echo "Output: $OUTPUT"
echo ""

# Run filter with test parameters
python data_filter.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --model "Qwen/Qwen2.5-Coder-7B-Instruct" \
    --max_length 32768 \
    --save_removed "$REMOVED" \
    --save_stats "$STATS" \
    --trust_remote_code \
    --verbose

echo ""
echo "Test completed!"
echo ""
echo "Files created:"
echo "  - Filtered data: $OUTPUT"
echo "  - Removed data:  $REMOVED"
echo "  - Statistics:    $STATS"
