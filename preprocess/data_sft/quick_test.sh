#!/bin/bash
# Quick test script for data_sft

echo "=== Quick Test of Data SFT ==="
echo ""

# Use latest segment samples for testing
LATEST_SEGMENTS=$(ls -t ../data_process_segments/outputs/segment_samples_*.json 2>/dev/null | head -1)

if [ -z "$LATEST_SEGMENTS" ]; then
    echo "Error: No segment samples found. Please run data_process_segments first."
    echo "Expected path: ../data_process_segments/outputs/segment_samples_*.json"
    exit 1
fi

echo "Using latest segment samples: $LATEST_SEGMENTS"
echo "Running pipeline with default settings (LLM COT enabled)..."
echo ""

USE_LLM_COT=true ./run.sh "$LATEST_SEGMENTS" "test_outputs"