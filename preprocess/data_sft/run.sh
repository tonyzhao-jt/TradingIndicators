#!/bin/bash

# Data SFT Pipeline Runner
# This script generates COT instruction data from segment samples

set -e  # Exit on any error

# Configuration
DEFAULT_INPUT="../data_process_segments/outputs/segment_samples_20251029_035241.json"
DEFAULT_OUTPUT="outputs"

INPUT_FILE="${1:-$DEFAULT_INPUT}"
OUTPUT_DIR="${2:-$DEFAULT_OUTPUT}"
USE_LLM_COT="${USE_LLM_COT:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Starting Data SFT Pipeline${NC}"
echo "======================================"

# Check if input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo -e "${RED}❌ Error: Input file not found: $INPUT_FILE${NC}"
    echo "Available segment files:"
    ls -la ../data_process_segments/outputs/*.json 2>/dev/null || echo "No segment files found"
    echo ""
    echo "Usage: $0 [input_file] [output_dir]"
    echo "Example: $0 ../data_process_segments/outputs/segment_samples_20251029_035241.json outputs"
    exit 1
fi

echo -e "${YELLOW}📂 Input file: $INPUT_FILE${NC}"
echo -e "${YELLOW}📁 Output directory: $OUTPUT_DIR${NC}"
echo -e "${YELLOW}🤖 Use LLM COT: $USE_LLM_COT${NC}"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set environment variables
export USE_LLM_COT=$USE_LLM_COT

# Check Python environment
if [[ -f "/workspace/.venv/bin/python" ]]; then
    PYTHON_CMD="/workspace/.venv/bin/python"
    echo -e "${GREEN}🐍 Using virtual environment: $PYTHON_CMD${NC}"
else
    PYTHON_CMD="python"
    echo -e "${YELLOW}🐍 Using system python: $PYTHON_CMD${NC}"
fi

# Build command
CMD="$PYTHON_CMD main.py --input '$INPUT_FILE' --output_dir '$OUTPUT_DIR'"

echo -e "${BLUE}🚀 Running pipeline...${NC}"
echo "Command: $CMD"
echo ""

# Run the pipeline
if eval $CMD; then
    echo ""
    echo -e "${GREEN}✅ Pipeline completed successfully!${NC}"
    echo -e "${GREEN}📊 Check output directory: $OUTPUT_DIR${NC}"
    
    # Show output files
    echo ""
    echo "Generated files:"
    ls -la "$OUTPUT_DIR"/*.json 2>/dev/null || echo "No output files found"
    
    # Show sample from latest output
    LATEST_OUTPUT=$(ls -t "$OUTPUT_DIR"/sft_instructions_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST_OUTPUT" ]]; then
        echo ""
        echo -e "${GREEN}📄 Sample from latest output:${NC}"
        echo "----------------------------------------"
        head -20 "$LATEST_OUTPUT"
        echo "..."
        echo ""
        SAMPLE_COUNT=$(grep -o '"instruction"' "$LATEST_OUTPUT" | wc -l)
        echo -e "${GREEN}📈 Total instruction samples generated: $SAMPLE_COUNT${NC}"
    fi
    
else
    echo -e "${RED}❌ Pipeline failed!${NC}"
    exit 1
fi