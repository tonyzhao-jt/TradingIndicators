#!/bin/bash

echo "🚀 Starting Few-Shot Code Generation Visualizer..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "📦 Installing Streamlit and dependencies..."
    pip install -r requirements_viz.txt
fi

# Set environment variables to avoid common issues
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ENABLE_CORS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

echo "🌐 Starting Streamlit app..."
echo "💡 Access the app at: http://localhost:8501"
echo "🔧 Use Ctrl+C to stop the server"
echo ""

# 启动 streamlit
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0