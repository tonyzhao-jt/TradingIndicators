#!/bin/bash

# Merge Parquet Files Script
# This script merges all parquet files in the processed directory

echo "=== Parquet Files Merger ==="

# Set the directories
PROCESSED_DIR="/workspace/trading_indicators/outputs/processed"
TOOLS_DIR="/workspace/trading_indicators/preprocess/tools"
OUTPUT_FILE="/workspace/trading_indicators/outputs/merged_processed_data.parquet"

# Check if processed directory exists
if [ ! -d "$PROCESSED_DIR" ]; then
    echo "Error: Processed directory not found: $PROCESSED_DIR"
    exit 1
fi

# Check if tools directory exists
if [ ! -d "$TOOLS_DIR" ]; then
    echo "Error: Tools directory not found: $TOOLS_DIR"
    exit 1
fi

# Go to tools directory
cd "$TOOLS_DIR"

echo "Working directory: $(pwd)"
echo "Source directory: $PROCESSED_DIR"
echo "Output file: $OUTPUT_FILE"
echo ""

# First, show file information
echo "1. Checking available parquet files..."
python main.py merge "$PROCESSED_DIR" --pattern "processed_batch_*.parquet" --info

echo ""
echo "2. Starting merge process..."

# Perform the actual merge
python main.py merge "$PROCESSED_DIR" \
    --pattern "processed_batch_*.parquet" \
    --output "$OUTPUT_FILE" \
    --sort-by "timestamp" 2>/dev/null || \
python main.py merge "$PROCESSED_DIR" \
    --pattern "processed_batch_*.parquet" \
    --output "$OUTPUT_FILE"

# Check if merge was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "3. Merge completed successfully!"
    echo "   Output file: $OUTPUT_FILE"
    
    # Show basic info about the merged file
    if [ -f "$OUTPUT_FILE" ]; then
        echo "   File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
        echo ""
        echo "4. Inspecting merged file..."
        python main.py inspect "$OUTPUT_FILE" --head 3
    fi
else
    echo ""
    echo "Error: Merge failed!"
    exit 1
fi

echo ""
echo "=== Merge Complete ==="