#!/bin/bash
# Run script for data_process_0 pipeline

# Set default input file if not provided
INPUT_FILE=${1:-"../../outputs/strategies_20251014_054134.json"}
OUTPUT_DIR=${2:-"../../outputs/processed"}
SAMPLES=${3:-""}

echo "Running data_process_0 pipeline..."
echo "Input file: $INPUT_FILE"
echo "Output directory: $OUTPUT_DIR"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file $INPUT_FILE does not exist"
    exit 1
fi

# Install requirements if needed
echo "Installing requirements..."
pip install -r requirements.txt

# Run the processing pipeline
if [ -n "$SAMPLES" ]; then
    echo "Processing $SAMPLES samples..."
    python main.py "$INPUT_FILE" --output-dir "$OUTPUT_DIR" --samples "$SAMPLES"
else
    echo "Processing all samples..."
    python main.py "$INPUT_FILE" --output-dir "$OUTPUT_DIR"
fi

echo "Processing complete!"