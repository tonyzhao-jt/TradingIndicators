#!/usr/bin/env python
"""
Test the aug_description node with Best-of-N sampling.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from nodes.aug_description import augment_description_best_of_n


def test_with_sample_data():
    """Test with a sample trading indicator."""
    sample_data = {
        "id": "test-123",
        "name": "VWAP Indicator",
        "description": """
        This indicator calculates the Volume Weighted Average Price (VWAP).
        VWAP is a trading benchmark that gives the average price a security 
        has traded at throughout the day, based on both volume and price.
        It is important because it provides traders with insight into both 
        the trend and value of a security.
        """,
        "source_code": """
//@version=5
indicator("VWAP", overlay=true)

// Calculate VWAP
vwap = ta.vwap(close)

// Plot
plot(vwap, color=color.blue, linewidth=2, title="VWAP")
        """,
        "preview_author": "test_user"
    }
    
    print("="*70)
    print("Testing Description Augmentation with Best-of-N")
    print("="*70)
    print(f"\nIndicator: {sample_data['name']}")
    print(f"Description length: {len(sample_data['description'])} chars")
    
    print("\nGenerating analyses...")
    result = augment_description_best_of_n(sample_data, n=2)
    
    print("\n" + "="*70)
    print("Results")
    print("="*70)
    print(f"Number of candidates: {result['num_candidates']}")
    print(f"All scores: {result['all_scores']}")
    print(f"Best score: {result['best_score']:.2f}")
    print(f"Selected candidate: {result['candidate_id'] + 1}")
    
    print("\n" + "="*70)
    print("Best Analysis Structure")
    print("="*70)
    best_analysis = result['best_analysis']
    
    for key, value in best_analysis.items():
        if isinstance(value, str):
            preview = value[:100] + "..." if len(value) > 100 else value
            print(f"\n{key}:")
            print(f"  {preview}")
        elif isinstance(value, list):
            print(f"\n{key}: [{len(value)} items]")
            if value:
                for item in value[:3]:
                    print(f"  - {item}")
                if len(value) > 3:
                    print(f"  ... and {len(value)-3} more")
        elif isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                preview = str(v)[:80] + "..." if len(str(v)) > 80 else str(v)
                print(f"  {k}: {preview}")
    
    # Save to file for inspection
    output_file = Path(__file__).parent / "test_output_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n\nFull result saved to: {output_file}")
    
    return result


def test_with_real_data():
    """Test with real data from the outputs directory."""
    import os
    
    input_file = "../../outputs/trade_raw_data_20251011_053837.json"
    
    if not os.path.exists(input_file):
        print(f"Real data file not found: {input_file}")
        return None
    
    print("="*70)
    print("Testing with Real Trading Indicator Data")
    print("="*70)
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Use first item
    item = data[0]
    
    print(f"\nIndicator: {item['name']}")
    print(f"Author: {item.get('preview_author', 'Unknown')}")
    print(f"Likes: {item.get('preview_likes_count', 0)}")
    print(f"Description length: {len(item.get('description', ''))} chars")
    print(f"Code length: {len(item.get('source_code', ''))} chars")
    
    print("\nGenerating analyses with Best-of-N (N=3)...")
    result = augment_description_best_of_n(item, n=3)
    
    print("\n" + "="*70)
    print("Results")
    print("="*70)
    print(f"Number of candidates: {result['num_candidates']}")
    print(f"All scores: {[f'{s:.2f}' for s in result['all_scores']]}")
    print(f"Best score: {result['best_score']:.2f}")
    print(f"Selected candidate: {result['candidate_id'] + 1}")
    
    best_analysis = result['best_analysis']
    print(f"\nGenerated fields: {list(best_analysis.keys())}")
    
    if "key_concepts" in best_analysis:
        print(f"Key concepts count: {len(best_analysis['key_concepts'])}")
    
    # Save result
    output_file = Path(__file__).parent / "test_output_real_data.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nFull result saved to: {output_file}")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test description augmentation")
    parser.add_argument("--real", action="store_true", help="Test with real data")
    args = parser.parse_args()
    
    try:
        if args.real:
            result = test_with_real_data()
        else:
            result = test_with_sample_data()
        
        if result:
            print("\n" + "="*70)
            print("✓ Test completed successfully!")
            print("="*70)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
