#!/bin/bash
# Simple test script for data_process_segments

echo "=== Quick Test of Data Process Segments ==="
echo ""

# Use a smaller file for testing
TEST_INPUT="../../outputs/segments_raw_20251014.json"

if [ ! -f "$TEST_INPUT" ]; then
    echo "Error: Test input file not found: $TEST_INPUT"
    exit 1
fi

echo "Running pipeline with default settings (LLM scoring enabled)..."
echo "Input: $TEST_INPUT"
echo ""

./run.sh "$TEST_INPUT" "test_outputs"