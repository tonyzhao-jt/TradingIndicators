#!/bin/bash
DOCKER_BINARY="docker"
IMAGE_NAME="trading_indicators"
echo "check if mount_path.txt exists"
if [ ! -f "mount_path.txt" ]; then
    echo "mount_path.txt does not exist, please create one"
    exit 1
fi
MOUNT_PATH=$(<mount_path.txt)
echo "The value of MOUNT_PATH is: $MOUNT_PATH"

# Check if NVIDIA Docker runtime is available
if command -v nvidia-docker &> /dev/null; then
    DOCKER_CMD="nvidia-docker"
    echo "Using nvidia-docker for GPU support"
elif ${DOCKER_BINARY} info | grep -q "nvidia"; then
    DOCKER_CMD="${DOCKER_BINARY}"
    GPU_FLAGS="--gpus all"
    echo "Using docker with --gpus all flag"
else
    echo "Warning: NVIDIA Docker runtime not found. Running without GPU support."
    DOCKER_CMD="${DOCKER_BINARY}"
    GPU_FLAGS=""
fi

# Run with GPU flags for CUDA container
${DOCKER_CMD} run --ipc host ${GPU_FLAGS} \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    -v "${MOUNT_PATH}:/workspace/${IMAGE_NAME}" \
    --name "${IMAGE_NAME}_cuda" \
    -it "${IMAGE_NAME}:cuda-latest"