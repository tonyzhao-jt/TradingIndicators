#!/bin/bash
# Test filter node with various descriptions

cd /workspace/trading_indicators/preprocess/data_agent

echo "=== Testing Filter Node ==="
echo ""

# Test with built-in test cases
echo "1. Testing with built-in test cases..."
python nodes/filter.py

echo ""
echo "=== Test with Real Data Samples ==="
echo ""

# Test with real trading data
python -c "
import json
import sys
sys.path.insert(0, '.')

from nodes.filter import filter_data
from config import MIN_DESCRIPTION_WORDS

# Load real data
with open('../../outputs/trade_raw_data_20251011_053837.json', 'r') as f:
    data = json.load(f)

print(f'Testing with MIN_DESCRIPTION_WORDS = {MIN_DESCRIPTION_WORDS}')
print()

# Test first 5 items
pass_count = 0
reject_count = 0

for i, item in enumerate(data[:5]):
    print(f'=== Item {i+1}: {item.get(\"name\", \"Unknown\")[:50]} ===')
    
    # Get description stats
    desc = item.get('description', '')
    word_count = len(desc.split())
    print(f'Description length: {word_count} words')
    
    # Run filter
    result = filter_data(item, min_words=MIN_DESCRIPTION_WORDS)
    
    decision = '✓ KEEP' if result['should_keep'] else '✗ REJECT'
    print(f'Decision: {decision}')
    
    if result['quality_check']:
        qc = result['quality_check']
        print(f'Quality Score: {qc[\"score\"]}/100')
        print(f'Indicators: {\"✓\" if qc[\"indicators_present\"] else \"✗\"}')
        print(f'Strategy: {\"✓\" if qc[\"strategy_present\"] else \"✗\"}')
        print(f'Reasoning: {qc[\"reasoning\"][:150]}...')
    
    if result['rejection_reason']:
        print(f'Rejection: {result[\"rejection_reason\"][:150]}...')
    
    if result['should_keep']:
        pass_count += 1
    else:
        reject_count += 1
    
    print()

print(f'=== Summary ===')
print(f'Passed: {pass_count}/{pass_count + reject_count}')
print(f'Rejected: {reject_count}/{pass_count + reject_count}')
print(f'Pass Rate: {pass_count/(pass_count + reject_count)*100:.1f}%')
"

echo ""
echo "=== Test Complete ==="
