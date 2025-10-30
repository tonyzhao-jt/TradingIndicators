#!/bin/bash

echo "Starting Streamlit Code Analysis Application..."
echo "This application includes:"
echo "1. Few-Shot vs Zero-Shot Code Generation Visualizer" 
echo "2. Code Similarity Analysis"
echo ""

cd /workspace/trading_indicators/training_free
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0