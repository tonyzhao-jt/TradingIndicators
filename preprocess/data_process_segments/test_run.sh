#!/bin/bash
# Test script for data_process_segments

echo "=== Testing Data Process Segments ==="

# Create test input if needed
TEST_INPUT="../data_process_0/outputs/processed/data_process_0_results_20251024_044926.json"

if [ ! -f "$TEST_INPUT" ]; then
    echo "Test input file not found: $TEST_INPUT"
    echo "Please ensure you have processed data from data_process_0"
    exit 1
fi

echo "Using input file: $TEST_INPUT"

# Run the pipeline
python main.py --input "$TEST_INPUT" --output_dir outputs

echo "=== Test completed ==="