DOCKER_BINARY="docker"
IMAGE_NAME="trading_indicators"
echo "check if mount_path.txt exists"
if [ ! -f "mount_path.txt" ]; then
    echo "mount_path.txt does not exist, please create one"
    exit 1
fi
MOUNT_PATH=$(<mount_path.txt)
echo "The value of MOUNT_PATH is: $MOUNT_PATH"
# Run without GPU flags for a CPU-only container
${DOCKER_BINARY} run --ipc host -v "${MOUNT_PATH}:/workspace/${IMAGE_NAME}" --name "${IMAGE_NAME}" -it "${IMAGE_NAME}:latest"