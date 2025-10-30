#!/bin/bash
# Download model using model_downloader.py

# Example usage:
# ./download_model.sh "Qwen/Qwen2.5-Coder-7B"
# ./download_model.sh "meta-llama/Llama-2-7b-hf" ./custom_cache

MODEL_NAME="${1:-Qwen/Qwen2.5-Coder-7B}"
CACHE_DIR="${2:-./model_cache}"

echo "=================================================="
echo "Model Download Script"
echo "=================================================="
echo "Model: $MODEL_NAME"
echo "Cache Directory: $CACHE_DIR"
echo "=================================================="
echo ""

python model_downloader.py \
    --model_name "$MODEL_NAME" \
    --cache_dir "$CACHE_DIR" \
    --max_workers 8

echo ""
echo "Download complete!"
