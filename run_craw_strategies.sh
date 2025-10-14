#!/bin/bash

# TradingView Strategies Crawler
# This script specifically crawls trading strategies from TradingView
# It covers both regular strategies and editor's picks strategies

echo "🎯 Starting TradingView Strategies Crawl..."
echo "📋 Source URLs:"
echo "   1. Regular Strategies: https://www.tradingview.com/scripts/?script_type=strategies"
echo "   2. Editor's Pick Strategies: https://www.tradingview.com/scripts/editors-picks/?script_type=strategies"
echo ""

# Generate timestamp for output file
timestamp=$(date +%Y%m%d_%H%M%S)
output_file="/workspace/trading_indicators/outputs/strategies_${timestamp}.json"

# Run the crawler with strategy-only mode
cd /workspace/trading_indicators/crawler && \
python main_trading.py \
    --strategy-only \
    --pages 40 \
    --output-file "${output_file}" \
    --verbose

echo ""
echo "✅ Strategy crawling completed!"
echo "📁 Output saved to: ${output_file}"