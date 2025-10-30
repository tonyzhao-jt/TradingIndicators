#!/bin/bash

echo "Setting up Python environment for few-shot testing..."

# 安装依赖
pip install requests

echo "Starting few-shot vs zero-shot comparison..."

# 运行简单测试
python3 simple_test.py

echo "Test completed! Check the results in comparison_results.json"