#!/bin/bash

# Advanced Multi-GPU Training Script with configurable options
# Supports custom configuration via command line or environment variables

set -e

# Default configuration (can be overridden by environment variables)
NUM_GPUS=${NUM_GPUS:-4}
DATA_PATH=${DATA_PATH:-"/workspace/trading_indicators/outputs/segments_20251014.json"}
MODEL_NAME=${MODEL_NAME:-"Qwen/Qwen2.5-Coder-7B"}
OUTPUT_DIR=${OUTPUT_DIR:-"./pine-coder-4gpu"}
MAX_SEQ_LENGTH=${MAX_SEQ_LENGTH:-2048}

# Training hyperparameters
BATCH_SIZE=${BATCH_SIZE:-2}
GRADIENT_ACCUM_STEPS=${GRADIENT_ACCUM_STEPS:-4}
LEARNING_RATE=${LEARNING_RATE:-1e-5}
NUM_EPOCHS=${NUM_EPOCHS:-3}
WARMUP_STEPS=${WARMUP_STEPS:-100}
LOGGING_STEPS=${LOGGING_STEPS:-10}
SAVE_STEPS=${SAVE_STEPS:-500}

# Formatter settings
FORMATTER_TYPE=${FORMATTER_TYPE:-"instruction"}
INSTRUCTION_TEXT=${INSTRUCTION_TEXT:-"Generate Pine Script v6 code based on the following trading strategy description."}

# Distributed training settings
MASTER_ADDR=${MASTER_ADDR:-"127.0.0.1"}
MASTER_PORT=${MASTER_PORT:-29500}

# Print configuration
echo "=================================================================="
echo "Multi-GPU Training Configuration"
echo "=================================================================="
echo "Distributed Settings:"
echo "  Number of GPUs: ${NUM_GPUS}"
echo "  Master address: ${MASTER_ADDR}"
echo "  Master port: ${MASTER_PORT}"
echo ""
echo "Data & Model:"
echo "  Data path: ${DATA_PATH}"
echo "  Model: ${MODEL_NAME}"
echo "  Output directory: ${OUTPUT_DIR}"
echo ""
echo "Training Parameters:"
echo "  Max sequence length: ${MAX_SEQ_LENGTH}"
echo "  Batch size per GPU: ${BATCH_SIZE}"
echo "  Gradient accumulation: ${GRADIENT_ACCUM_STEPS}"
echo "  Effective batch size: $((NUM_GPUS * BATCH_SIZE * GRADIENT_ACCUM_STEPS))"
echo "  Learning rate: ${LEARNING_RATE}"
echo "  Number of epochs: ${NUM_EPOCHS}"
echo "  Warmup steps: ${WARMUP_STEPS}"
echo ""
echo "Formatter:"
echo "  Type: ${FORMATTER_TYPE}"
echo "=================================================================="
echo ""

# Validate GPU availability
GPU_COUNT=$(nvidia-smi --list-gpus 2>/dev/null | wc -l || echo "0")
if [ "${GPU_COUNT}" -lt "${NUM_GPUS}" ]; then
    echo "Warning: Requested ${NUM_GPUS} GPUs but only ${GPU_COUNT} available"
    echo "Adjusting to use ${GPU_COUNT} GPUs"
    NUM_GPUS=${GPU_COUNT}
fi

if [ "${NUM_GPUS}" -eq "0" ]; then
    echo "Error: No GPUs detected!"
    exit 1
fi

# Check if data file exists
if [ ! -f "${DATA_PATH}" ]; then
    echo "Error: Data file not found at ${DATA_PATH}"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Set CUDA visible devices (optional, remove if you want to use specific GPUs)
export CUDA_VISIBLE_DEVICES=0,1,2,3

# Launch training
echo "Starting training with torchrun..."
echo ""

torchrun \
    --standalone \
    --nnodes=1 \
    --nproc_per_node=${NUM_GPUS} \
    --master_addr=${MASTER_ADDR} \
    --master_port=${MASTER_PORT} \
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
    --fp16 \
    --gradient_checkpointing

EXIT_CODE=$?

echo ""
if [ ${EXIT_CODE} -eq 0 ]; then
    echo "=================================================================="
    echo "Training completed successfully!"
    echo "Model saved to: ${OUTPUT_DIR}"
    echo "=================================================================="
else
    echo "=================================================================="
    echo "Training failed with exit code: ${EXIT_CODE}"
    echo "=================================================================="
fi

exit ${EXIT_CODE}