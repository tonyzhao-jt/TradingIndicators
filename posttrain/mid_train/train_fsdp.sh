#!/bin/bash

# FSDP Training Script with Accelerate
# Launch multi-GPU training with Fully Sharded Data Parallel

set -e  # Exit on error

# Configuration
DATA_PATH="/workspace/trading_indicators/outputs/dataset/segments_no_aug.json"
MODEL_NAME="model_cache/models--Qwen--Qwen2.5-Coder-7B/snapshots/0396a76181e127dfc13e5c5ec48a8cee09938b02"
MODEL_NAME="model_cache/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c"
OUTPUT_DIR="./pine-coder-4b"
MAX_SEQ_LENGTH=4096

# add date
CURRENT_DATE=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${BASE_OUTPUT_DIR}_${CURRENT_DATE}"

# Training hyperparameters
BATCH_SIZE=1
GRADIENT_ACCUM_STEPS=4
LEARNING_RATE=1e-5
NUM_EPOCHS=5
WARMUP_STEPS=50
LOGGING_STEPS=10
SAVE_STEPS=500

# Formatter settings
FORMATTER_TYPE="instruction"
INSTRUCTION_TEXT="Generate Pine Script v6 code based on the following trading strategy description."

# FSDP config file
FSDP_CONFIG="fsdp_config.yaml"

echo "=================================================================="
echo "Starting FSDP Training with Accelerate"
echo "=================================================================="
echo "Data path: ${DATA_PATH}"
echo "Model: ${MODEL_NAME}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Max sequence length: ${MAX_SEQ_LENGTH}"
echo "Batch size per GPU: ${BATCH_SIZE}"
echo "Gradient accumulation: ${GRADIENT_ACCUM_STEPS}"
echo "FSDP Config: ${FSDP_CONFIG}"
echo "=================================================================="
echo ""

# Check if data file exists
if [ ! -f "${DATA_PATH}" ]; then
    echo "Error: Data file not found at ${DATA_PATH}"
    exit 1
fi

# Check if FSDP config exists
if [ ! -f "${FSDP_CONFIG}" ]; then
    echo "Error: FSDP config file not found at ${FSDP_CONFIG}"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Launch training with accelerate
accelerate launch \
    --config_file "${FSDP_CONFIG}" \
    train_fsdp.py \
    --data_path "${DATA_PATH}" \
    --model_name "${MODEL_NAME}" \
    --max_seq_length ${MAX_SEQ_LENGTH} \
    --formatter_type "${FORMATTER_TYPE}" \
    --instruction_text "${INSTRUCTION_TEXT}" \
    --output_dir "${OUTPUT_DIR}" \
    --batch_size ${BATCH_SIZE} \
    --gradient_accumulation_steps ${GRADIENT_ACCUM_STEPS} \
    --learning_rate ${LEARNING_RATE} \
    --num_epochs ${NUM_EPOCHS} \
    --logging_steps ${LOGGING_STEPS} \
    --save_steps ${SAVE_STEPS} \
    --warmup_steps ${WARMUP_STEPS} \
    --bf16

echo ""
echo "=================================================================="
echo "Training completed!"
echo "Model saved to: ${OUTPUT_DIR}"
echo "=================================================================="
