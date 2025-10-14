#!/usr/bin/env python3
"""Test the Pine Script to Backtrader conversion with real data from dataset."""

import json
import sys
import os
import importlib.util

# Add data_agent path for imports
sys.path.append('/workspace/trading_indicators/preprocess/data_agent')

# Import individual modules directly
converter_path = "/workspace/trading_indicators/preprocess/data_agent/code/backtrader_backend/converter.py"
spec = importlib.util.spec_from_file_location("converter", converter_path)
converter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter_module)
convert = converter_module.convert

validator_path = "/workspace/trading_indicators/preprocess/data_agent/code/backtrader_backend/validator.py"
spec = importlib.util.spec_from_file_location("validator", validator_path)
validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator_module)
validate = validator_module.validate

def test_real_strategy_conversion():
    """Test conversion with real strategy from the dataset."""
    
    # Load raw data to find strategy items
    input_file = "/workspace/trading_indicators/outputs/trade_raw_data_20251011_053837.json"
    
    with open(input_file, 'r') as f:
        raw_data = json.load(f)
    
    # Find strategy items
    strategy_items = []
    for item in raw_data:
        code = item.get('source_code', '')
        if 'strategy(' in code and ('strategy.entry' in code or 'strategy.order' in code):
            strategy_items.append(item)
    
    print(f"Found {len(strategy_items)} strategy items in dataset")
    
    if not strategy_items:
        print("No strategy items found")
        return
    
    # Test first strategy
    strategy = strategy_items[0]
    print(f"\nTesting strategy: {strategy.get('name', 'Unknown')}")
    print(f"Description: {strategy.get('description', 'No description')[:100]}...")
    print(f"Pine Script length: {len(strategy.get('source_code', ''))}")
    
    pine_code = strategy.get('source_code', '')
    
    print("\nPine Script (first 500 chars):")
    print("-" * 50)
    print(pine_code[:500] + "...")
    print("-" * 50)
    
    # Test conversion
    print("\n1. Testing conversion...")
    conversion_result = convert(pine_code)
    
    if conversion_result.get('error'):
        print(f"✗ Conversion failed: {conversion_result['error']}")
        return
        
    converted_code = conversion_result.get('converted_code')
    if not converted_code:
        print("✗ No converted code returned")
        return
        
    print("✓ Conversion successful!")
    print(f"Converted code length: {len(converted_code)}")
    
    # Show sample of converted code
    print("\nConverted Backtrader code (first 800 chars):")
    print("-" * 50)
    print(converted_code[:800] + "...")
    print("-" * 50)
    
    # Test validation
    print("\n2. Testing validation...")
    validation_result = validate(pine_code, converted_code)
    
    if validation_result.get('valid'):
        print("✓ Validation successful!")
        print(f"Validation details: {validation_result.get('reason', 'No details')}")
    else:
        print("✗ Validation failed!")
        print(f"Validation error: {validation_result.get('reason', 'No reason')}")
        
        # Show error details for debugging
        reason = validation_result.get('reason', '')
        if len(reason) > 200:
            print(f"\nError details (first 500 chars): {reason[:500]}...")

def test_multiple_strategies():
    """Test conversion with multiple strategies from dataset."""
    
    # Load raw data
    input_file = "/workspace/trading_indicators/outputs/trade_raw_data_20251011_053837.json"
    
    with open(input_file, 'r') as f:
        raw_data = json.load(f)
    
    # Find strategy items
    strategy_items = []
    for item in raw_data:
        code = item.get('source_code', '')
        if 'strategy(' in code and ('strategy.entry' in code or 'strategy.order' in code):
            strategy_items.append(item)
    
    print(f"Testing conversion on {min(3, len(strategy_items))} strategies...")
    
    success_count = 0
    for i, strategy in enumerate(strategy_items[:3]):
        print(f"\n{'='*20} Strategy {i+1} {'='*20}")
        name = strategy.get('name', f'Strategy_{i+1}')
        print(f"Name: {name}")
        
        pine_code = strategy.get('source_code', '')
        print(f"Pine Script length: {len(pine_code)}")
        
        # Test conversion
        conversion_result = convert(pine_code)
        
        if conversion_result.get('error'):
            print(f"✗ Conversion failed: {conversion_result['error']}")
            continue
            
        converted_code = conversion_result.get('converted_code')
        if not converted_code:
            print("✗ No converted code returned")
            continue
            
        print(f"✓ Converted successfully ({len(converted_code)} chars)")
        
        # Test validation
        validation_result = validate(pine_code, converted_code)
        
        if validation_result.get('valid'):
            print("✓ Validation successful!")
            success_count += 1
        else:
            print(f"✗ Validation failed: {validation_result.get('reason', '')[:100]}...")
    
    print(f"\n{'='*50}")
    total_tested = min(3, len(strategy_items))
    print(f"SUMMARY: {success_count}/{total_tested} strategies converted and validated successfully")
    if total_tested > 0:
        print(f"Success rate: {success_count/total_tested*100:.1f}%")
    else:
        print("No strategies found to test")

if __name__ == "__main__":
    print("Testing Pine Script to Backtrader conversion with real data")
    print("=" * 60)
    
    # Test single strategy in detail
    test_real_strategy_conversion()
    
    print("\n" + "=" * 60)
    
    # Test multiple strategies
    test_multiple_strategies()