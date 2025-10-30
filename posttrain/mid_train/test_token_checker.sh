#!/bin/bash

# Test script for token static checker
echo "🔍 Testing Token Static Checker..."
echo ""

cd /workspace/trading_indicators/posttrain/mid_train

# Run the token static checker with default settings
echo "📊 Running token analysis on segments_20251014.json..."
python token_static_check.py \
    --model_name "model_cache/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/cdbee75f17c01a7cc42f958dc650907174af0554" \
    --data_path "/workspace/trading_indicators/outputs/dataset/mixed_dataset_script_0.7.json" \
    --output_path "token_statistics_report.json" \
    --show_distribution

echo ""
echo "✅ Token analysis complete! Check token_statistics_report.json for detailed results."

# Also test the formatter
echo ""
echo "🔧 Testing Formatter Classes..."
python -c "
from formatter import FormatterFactory, print_sample_formats

sample = {
    'input': 'Create a simple moving average crossover strategy for EURUSD on 15-minute timeframe',
    'output': '@version=5\nstrategy(\"MA Cross\", overlay=true)\nfast = ta.sma(close, 10)\nslow = ta.sma(close, 20)\nif ta.crossover(fast, slow)\n    strategy.entry(\"Long\", strategy.long)\nif ta.crossunder(fast, slow)\n    strategy.close(\"Long\")'
}

print_sample_formats(sample)
"

echo ""
echo "✅ All tests completed successfully!"