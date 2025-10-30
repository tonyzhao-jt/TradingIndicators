#!/bin/bash

# Data Process Segments Pipeline Runner
# This script processes segments from restructured trading strategy data

set -e  # Exit on any error

# Configuration
DEFAULT_INPUT="../../outputs/segments_20251014.json"
DEFAULT_OUTPUT="outputs"

INPUT_FILE="${1:-$DEFAULT_INPUT}"
OUTPUT_DIR="${2:-$DEFAULT_OUTPUT}"
USE_LLM_SCORING="${USE_LLM_SCORING:-true}"
QUALITY_THRESHOLD="${QUALITY_THRESHOLD:-6.0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Starting Data Process Segments Pipeline${NC}"
echo "======================================"

# Check if input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo -e "${RED}❌ Error: Input file not found: $INPUT_FILE${NC}"
    echo "Available processed files:"
    ls -la ../../outputs/processed/*.json 2>/dev/null || echo "No processed files found"
    echo ""
    echo "Usage: $0 [input_file] [output_dir]"
    echo "Example: $0 ../../outputs/processed/data_process_0_results_20251024_044926.json outputs"
    exit 1
fi

echo -e "${YELLOW}📂 Input file: $INPUT_FILE${NC}"
echo -e "${YELLOW}📁 Output directory: $OUTPUT_DIR${NC}"
echo -e "${YELLOW}🤖 Use LLM scoring: $USE_LLM_SCORING${NC}"
echo -e "${YELLOW}📊 Quality threshold: $QUALITY_THRESHOLD${NC}"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set environment variables for quality scoring
export USE_LLM_SCORING=$USE_LLM_SCORING
export QUALITY_SCORE_THRESHOLD=$QUALITY_THRESHOLD

# Check Python environment
if [[ -f "/workspace/.venv/bin/python" ]]; then
    PYTHON_CMD="/workspace/.venv/bin/python"
    echo -e "${GREEN}� Using virtual environment: $PYTHON_CMD${NC}"
else
    PYTHON_CMD="python"
    echo -e "${YELLOW}� Using system python: $PYTHON_CMD${NC}"
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
    LATEST_OUTPUT=$(ls -t "$OUTPUT_DIR"/segment_samples_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST_OUTPUT" ]]; then
        echo ""
        echo -e "${GREEN}📄 Sample from latest output:${NC}"
        echo "----------------------------------------"
        head -10 "$LATEST_OUTPUT"
        echo "..."
        echo ""
        SAMPLE_COUNT=$(grep -o '"input"' "$LATEST_OUTPUT" | wc -l)
        echo -e "${GREEN}📈 Total samples generated: $SAMPLE_COUNT${NC}"
    fi
    
else
    echo -e "${RED}❌ Pipeline failed!${NC}"
    exit 1
fi