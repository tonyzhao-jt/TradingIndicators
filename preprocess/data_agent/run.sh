#!/bin/bash

# Script to run the data processing pipeline
# export OUTPUT_DIR="/workspace/trading_indicators/outputs/processed"
# Change to the data_agent directory
cd "$(dirname "$0")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import langgraph" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Check command
if [ "$1" == "process" ]; then
    # Run data processing
    shift
    echo -e "${GREEN}Starting data processing pipeline...${NC}"
    python main.py "$@"
    
elif [ "$1" == "checkpoint" ]; then
    # Manage checkpoint
    shift
    python checkpoint_manager.py "$@"
    
elif [ "$1" == "visualize" ]; then
    # Visualize workflow
    echo -e "${GREEN}Visualizing workflow graph...${NC}"
    python visualize_graph.py
    
elif [ "$1" == "test-llm" ]; then
    # Test LLM connection
    echo -e "${GREEN}Testing LLM connection...${NC}"
    python llm_client.py
    
elif [ "$1" == "test-graph" ]; then
    # Test graph
    echo -e "${GREEN}Testing workflow graph...${NC}"
    python graph.py

elif [ "$1" == "test-aug" ]; then
    # Test description augmentation
    shift
    echo -e "${GREEN}Testing description augmentation...${NC}"
    python test_aug_description.py "$@"

elif [ "$1" == "test-symbol" ]; then
    # Test symbol inference
    echo -e "${GREEN}Testing symbol inference...${NC}"
    bash test_symbol_infer.sh

elif [ "$1" == "test-filter" ]; then
    # Test filter node
    echo -e "${GREEN}Testing filter node...${NC}"
    bash test_filter.sh
    
elif [ "$1" == "inspect-top" ]; then
    # Inspect the provided parquet file or the latest in the processed output directory
    echo -e "${GREEN}Inspecting processed parquet...${NC}"
    # If the user provided a second argument, use it; otherwise call with no args to inspect latest
    if [ -n "$2" ]; then
        python inspect_parquet.py "$2"
    else
        python inspect_parquet.py
    fi
    exit $?

else
    # Show usage
    echo -e "${YELLOW}Trading Data Processing Pipeline${NC}"
    echo ""
    echo "Usage: ./run.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  process <input_file> [--no-resume] [--samples N] - Process trading data (optionally sample N items)"
    echo "  checkpoint <show|reset|set>         - Manage checkpoint"
    echo "  visualize                           - Visualize workflow graph"
    echo "  test-llm                            - Test LLM connection"
    echo "  test-graph                          - Test workflow graph"
    echo "  test-aug [--real]                   - Test description augmentation"
    echo "  test-symbol                         - Test symbol inference"
    echo "  test-filter                         - Test filter node"
    echo ""
    echo "Examples:"
    echo "  ./run.sh process ../../outputs/trade_raw_data_20251011_053837.json"
    echo "  ./run.sh process ../../outputs/trade_raw_data_20251011_053837.json --no-resume"
    echo "  ./run.sh process ../../outputs/trade_raw_data_20251011_053837.json --samples 10"
    echo "  ./run.sh checkpoint show"
    echo "  ./run.sh checkpoint reset"
    echo "  ./run.sh test-symbol"
    echo "  ./run.sh test-filter"
    echo "  ./run.sh visualize"
    echo "  ./run.sh test-aug              # Test with sample data"
    echo "  ./run.sh test-aug --real       # Test with real data"
    echo ""
fi

# Deactivate virtual environment
deactivate
