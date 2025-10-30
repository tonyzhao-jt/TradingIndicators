#!/bin/bash

# Multi-GPU Training Script with torchrun
# Launch 4-GPU training for Pine Script Code Generation

set -e  # Exit on error

# Configuration
NUM_GPUS=4
DATA_PATH="/workspace/trading_indicators/outputs/dataset/mixed_dataset_0.7_filtered.json"
MODEL_NAME="/workspace/trading_indicators/posttrain/mid_train/_20251030_084616/final"
OUTPUT_DIR="./pine-coder-mid-2"
MAX_SEQ_LENGTH=32768 # 32k

# Training hyperparameters
BATCH_SIZE=1
GRADIENT_ACCUM_STEPS=4
LEARNING_RATE=1e-5
NUM_EPOCHS=3
WARMUP_STEPS=100
LOGGING_STEPS=10
SAVE_STEPS=500

# Formatter settings
FORMATTER_TYPE="instruction"
INSTRUCTION_TEXT="Generate Pine Script v6 code based on the following trading strategy description."

echo "=================================================================="
echo "Starting Multi-GPU Training with torchrun"
echo "=================================================================="
echo "Number of GPUs: ${NUM_GPUS}"
echo "Data path: ${DATA_PATH}"
echo "Model: ${MODEL_NAME}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Max sequence length: ${MAX_SEQ_LENGTH}"
echo "Batch size per GPU: ${BATCH_SIZE}"
echo "Effective batch size: $((NUM_GPUS * BATCH_SIZE * GRADIENT_ACCUM_STEPS))"
echo "=================================================================="
echo ""

# Check if data file exists
if [ ! -f "${DATA_PATH}" ]; then
    echo "Error: Data file not found at ${DATA_PATH}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Launch training with torchrun
torchrun \
    --standalone \
    --nnodes=1 \
    --nproc_per_node=${NUM_GPUS} \
    train_main_0.py \
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
    --gradient_checkpointing

echo ""
echo "=================================================================="
echo "Training completed!"
echo "Model saved to: ${OUTPUT_DIR}"
echo "=================================================================="