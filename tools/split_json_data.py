#!/usr/bin/env python3
"""
Script to split JSON dataset into training and testing sets
"""

import json
import argparse
import random
from pathlib import Path
from typing import Dict, List, Any

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load JSON data from file"""
    print(f"📂 Loading data from: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Total items loaded: {len(data)}")
    return data

def split_data(data: List[Dict[str, Any]], 
               train_ratio: float = 0.8, 
               random_seed: int = 42) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split data into training and testing sets"""
    
    # Set random seed for reproducibility
    random.seed(random_seed)
    
    # Create a copy and shuffle
    data_copy = data.copy()
    random.shuffle(data_copy)
    
    # Calculate split point
    total_size = len(data_copy)
    train_size = int(total_size * train_ratio)
    
    # Split the data
    train_data = data_copy[:train_size]
    test_data = data_copy[train_size:]
    
    print(f"📈 Training set size: {len(train_data)} ({len(train_data)/total_size*100:.1f}%)")
    print(f"📉 Testing set size: {len(test_data)} ({len(test_data)/total_size*100:.1f}%)")
    
    return train_data, test_data

def save_json_data(data: List[Dict[str, Any]], file_path: str) -> None:
    """Save data to JSON file"""
    print(f"💾 Saving {len(data)} items to: {file_path}")
    
    # Create directory if it doesn't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description='Split JSON dataset into train/test sets')
    
    parser.add_argument('--input', '-i', 
                       default='/workspace/verl/outputs/strategies_20251014_054134.json',
                       help='Input JSON file path')
    
    parser.add_argument('--output-dir', '-o', 
                       default='/workspace/verl/outputs/split_data',
                       help='Output directory for train/test files')
    
    parser.add_argument('--train-ratio', '-r', 
                       type=float, default=0.8,
                       help='Training set ratio (default: 0.8)')
    
    parser.add_argument('--random-seed', '-s',
                       type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    
    parser.add_argument('--prefix', '-p',
                       default='strategies',
                       help='Prefix for output files (default: strategies)')
    
    args = parser.parse_args()
    
    print("🔄 Dataset Splitting Script")
    print("=" * 50)
    print(f"📂 Input file: {args.input}")
    print(f"📁 Output directory: {args.output_dir}")
    print(f"📊 Train ratio: {args.train_ratio}")
    print(f"🎯 Random seed: {args.random_seed}")
    print(f"🏷️  File prefix: {args.prefix}")
    print()
    
    # Validate train ratio
    if not 0 < args.train_ratio < 1:
        print("❌ Error: Train ratio must be between 0 and 1")
        return 1
    
    # Check if input file exists
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return 1
    
    try:
        # Load data
        data = load_json_data(args.input)
        
        if len(data) == 0:
            print("❌ Error: No data found in input file")
            return 1
        
        # Split data
        print("\n🔀 Splitting data...")
        train_data, test_data = split_data(data, args.train_ratio, args.random_seed)
        
        # Prepare output paths
        output_dir = Path(args.output_dir)
        train_file = output_dir / f"{args.prefix}_train.json"
        test_file = output_dir / f"{args.prefix}_test.json"
        
        # Save split data
        print("\n💾 Saving split datasets...")
        save_json_data(train_data, str(train_file))
        save_json_data(test_data, str(test_file))
        
        print("\n✅ Data splitting completed successfully!")
        print(f"📈 Training set: {train_file}")
        print(f"📉 Testing set: {test_file}")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"  - Total items: {len(data)}")
        print(f"  - Training items: {len(train_data)}")
        print(f"  - Testing items: {len(test_data)}")
        print(f"  - Split ratio: {args.train_ratio:.1%} / {1-args.train_ratio:.1%}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)