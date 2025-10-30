#!/bin/bash
# Filter training data by maximum token length

# Default values
INPUT_FILE="${INPUT_FILE:-/workspace/trading_indicators/outputs/mixed_train.json}"
OUTPUT_FILE="${OUTPUT_FILE:-/workspace/trading_indicators/outputs/mixed_train_filtered.json}"
MODEL="${MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}"
MAX_LENGTH="${MAX_LENGTH:-32768}"
SAVE_REMOVED="${SAVE_REMOVED:-}"
SAVE_STATS="${SAVE_STATS:-}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input|-i)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --model|-m)
            MODEL="$2"
            shift 2
            ;;
        --max_length|-l)
            MAX_LENGTH="$2"
            shift 2
            ;;
        --save_removed)
            SAVE_REMOVED="$2"
            shift 2
            ;;
        --save_stats)
            SAVE_STATS="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --help|-h)
            echo "Usage: bash filter_data.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --input, -i FILE       Input JSON file (default: \$INPUT_FILE)"
            echo "  --output, -o FILE      Output JSON file (default: \$OUTPUT_FILE)"
            echo "  --model, -m MODEL      Model name/path (default: $MODEL)"
            echo "  --max_length, -l NUM   Max sequence length (default: auto-detect)"
            echo "  --save_removed FILE    Save removed samples to file"
            echo "  --save_stats FILE      Save statistics to file"
            echo "  --verbose, -v          Verbose output"
            echo "  --help, -h             Show this help"
            echo ""
            echo "Environment variables:"
            echo "  INPUT_FILE    Input file path"
            echo "  OUTPUT_FILE   Output file path"
            echo "  MODEL         Model name"
            echo "  MAX_LENGTH    Maximum token length"
            echo ""
            echo "Examples:"
            echo "  # Basic usage"
            echo "  bash filter_data.sh --input train.json --output train_filtered.json"
            echo ""
            echo "  # With environment variables"
            echo "  INPUT_FILE=train.json OUTPUT_FILE=train_filtered.json bash filter_data.sh"
            echo ""
            echo "  # Custom max length"
            echo "  bash filter_data.sh --input train.json --output train_filtered.json --max_length 16384"
            echo ""
            echo "  # Save removed samples"
            echo "  bash filter_data.sh --input train.json --output train_filtered.json --save_removed removed.json"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print configuration
echo "================================"
echo "Data Filtering Configuration"
echo "================================"
echo "Input:       $INPUT_FILE"
echo "Output:      $OUTPUT_FILE"
echo "Model:       $MODEL"
echo "Max Length:  $MAX_LENGTH"
if [ -n "$SAVE_REMOVED" ]; then
    echo "Save Removed: $SAVE_REMOVED"
fi
if [ -n "$SAVE_STATS" ]; then
    echo "Save Stats:   $SAVE_STATS"
fi
echo "================================"
echo ""

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Error: Input file not found: $INPUT_FILE"
    exit 1
fi

# Build command
CMD="python data_filter.py --input \"$INPUT_FILE\" --output \"$OUTPUT_FILE\" --model \"$MODEL\" --trust_remote_code"

if [ -n "$MAX_LENGTH" ]; then
    CMD="$CMD --max_length $MAX_LENGTH"
fi

if [ -n "$SAVE_REMOVED" ]; then
    CMD="$CMD --save_removed \"$SAVE_REMOVED\""
fi

if [ -n "$SAVE_STATS" ]; then
    CMD="$CMD --save_stats \"$SAVE_STATS\""
fi

if [ -n "$VERBOSE" ]; then
    CMD="$CMD --verbose"
fi

# Run filtering
echo "Running: $CMD"
echo ""
eval $CMD

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Filtering completed successfully!"
    echo "Output saved to: $OUTPUT_FILE"
else
    echo ""
    echo "❌ Filtering failed!"
    exit 1
fi
