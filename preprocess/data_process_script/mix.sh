#!/bin/bash
# Mix datasets script

# Default paths (可以通过环境变量覆盖)
SCRIPT_FILE="${SCRIPT_FILE:-/workspace/trading_indicators/outputs/dataset/script_20251030_095104.json}"
SEGMENT_FILE="${SEGMENT_FILE:-/workspace/trading_indicators/outputs/segments_20251014.json}"
OUTPUT_DIR="${OUTPUT_DIR:-./outputs}"
RATIO="${RATIO:-0.5}"
SEED="${SEED:-42}"

# 帮助信息
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: bash mix.sh [SCRIPT_FILE] [SEGMENT_FILE] [RATIO] [OUTPUT_DIR]"
    echo ""
    echo "Environment variables:"
    echo "  SCRIPT_FILE  - Path to script dataset (default: /workspace/trading_indicators/outputs/processed_scripts/script_20251030.json)"
    echo "  SEGMENT_FILE - Path to segment dataset (default: /workspace/trading_indicators/outputs/segments/segment_samples_20251030.json)"
    echo "  RATIO        - Script ratio 0.0-1.0 (default: 0.5 = 50% script, 50% segment)"
    echo "  OUTPUT_DIR   - Output directory (default: ./outputs)"
    echo "  SEED         - Random seed (default: 42)"
    echo ""
    echo "Examples:"
    echo "  # Mix with 50-50 ratio"
    echo "  bash mix.sh"
    echo ""
    echo "  # Mix with 30% script, 70% segment"
    echo "  RATIO=0.3 bash mix.sh"
    echo ""
    echo "  # Custom files"
    echo "  bash mix.sh script.json segment.json 0.4 ./my_output"
    exit 0
fi

# 使用命令行参数（如果提供）
if [ ! -z "$1" ]; then
    SCRIPT_FILE="$1"
fi

if [ ! -z "$2" ]; then
    SEGMENT_FILE="$2"
fi

if [ ! -z "$3" ]; then
    RATIO="$3"
fi

if [ ! -z "$4" ]; then
    OUTPUT_DIR="$4"
fi

# 检查文件存在
if [ ! -f "$SCRIPT_FILE" ]; then
    echo "Error: Script file not found: $SCRIPT_FILE"
    exit 1
fi

if [ ! -f "$SEGMENT_FILE" ]; then
    echo "Error: Segment file not found: $SEGMENT_FILE"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 运行混合脚本
echo "Mixing datasets..."
echo "Script file: $SCRIPT_FILE"
echo "Segment file: $SEGMENT_FILE"
echo "Ratio: $RATIO ($(echo "$RATIO * 100" | bc)% script, $(echo "(1 - $RATIO) * 100" | bc)% segment)"
echo "Output: $OUTPUT_DIR"
echo "Seed: $SEED"
echo ""

python mix_dataset.py \
    --script "$SCRIPT_FILE" \
    --segment "$SEGMENT_FILE" \
    --ratio "$RATIO" \
    --output "$OUTPUT_DIR" \
    --seed "$SEED"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "Mixing completed successfully!"
else
    echo ""
    echo "Mixing failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
