#!/bin/bash
DOCKER_BINARY="docker"
IMAGE_NAME="trading_indicators"
FILE_NAME="dockerfile.cuda"
echo "Building CUDA-enabled Docker image..."
DOCKER_BUILDKIT=1 ${DOCKER_BINARY} build -f ${FILE_NAME} -t ${IMAGE_NAME}:cuda-latest .
echo "CUDA image built successfully as ${IMAGE_NAME}:cuda-latest"