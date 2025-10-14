#!/bin/bash
# Test symbol inference node

cd /workspace/trading_indicators/preprocess/data_agent

echo "=== Testing Symbol Inference Node ==="
echo ""

# Test with sample data
echo "1. Testing with sample data..."
python nodes/symbol_infer.py

echo ""
echo "=== Test with Real Data ==="
echo ""

# Test with real trading data
python -c "
import json
import sys
sys.path.insert(0, '.')

from nodes.symbol_infer import infer_relevant_symbols

# Load real data
with open('../../outputs/trade_raw_data_20251011_053837.json', 'r') as f:
    data = json.load(f)

# Test first 3 items
for i, item in enumerate(data[:3]):
    print(f'\n=== Item {i+1}: {item.get(\"name\", \"Unknown\")} ===')
    
    result = infer_relevant_symbols(
        description=item.get('description', '')[:1000],  # Truncate long descriptions
        name=item.get('name', '')
    )
    
    print(f'Symbols: {result[\"symbols\"]}')
    print(f'Confidence: {result[\"confidence\"]}')
    print(f'Reasoning: {result[\"reasoning\"][:200]}...')
    print(f'Formatted: {chr(34)}{chr(44)}{chr(34)}.join(result[\"symbols\"])}')
"

echo ""
echo "=== Test Complete ==="
