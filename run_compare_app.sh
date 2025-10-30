#!/bin/bash

# Run Model Comparison Streamlit App

echo "Starting Model Comparison App..."
echo "================================"

# Set environment variables
export CUDA_VISIBLE_DEVICES=0,1,2,3

# Run streamlit app
streamlit run compare_models_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
