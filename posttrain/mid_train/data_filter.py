#!/usr/bin/env python3
"""
Data Filter - Filter training samples that exceed maximum token length

This script filters out samples from a dataset that exceed the maximum
sequence length supported by a given model.

Usage:
    python data_filter.py --input data.json --output filtered_data.json --model Qwen/Qwen2.5-Coder-7B-Instruct --max_length 32768
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
from transformers import AutoTokenizer


def load_dataset(file_path: str) -> List[Dict[str, Any]]:
    """Load dataset from JSON file."""
    print(f"Loading dataset from: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} samples")
    return data


def save_dataset(data: List[Dict[str, Any]], file_path: str):
    """Save dataset to JSON file."""
    output_dir = os.path.dirname(file_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} samples to: {file_path}")


def format_sample(sample: Dict[str, Any]) -> str:
    """Format a sample as it would be during training."""
    input_text = sample.get('input', '')
    output_text = sample.get('output', '')
    
    # Standard instruction format
    formatted = f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{input_text}

### Response:
{output_text}"""
    
    return formatted


def get_token_length(tokenizer, text: str) -> int:
    """Get the token length of a text."""
    tokens = tokenizer.encode(text, add_special_tokens=True)
    return len(tokens)


def filter_dataset(
    data: List[Dict[str, Any]], 
    tokenizer,
    max_length: int,
    verbose: bool = False
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Filter dataset by maximum token length.
    
    Args:
        data: List of samples
        tokenizer: Tokenizer to use
        max_length: Maximum allowed token length
        verbose: Whether to print details of filtered samples
        
    Returns:
        Tuple of (filtered_data, statistics)
    """
    filtered_data = []
    removed_data = []
    token_lengths = []
    
    print(f"\nFiltering dataset with max_length={max_length}...")
    
    for i, sample in enumerate(tqdm(data, desc="Processing samples")):
        # Format the sample as it would appear during training
        formatted_text = format_sample(sample)
        
        # Get token length
        token_length = get_token_length(tokenizer, formatted_text)
        token_lengths.append(token_length)
        
        if token_length <= max_length:
            filtered_data.append(sample)
        else:
            removed_data.append({
                'index': i,
                'token_length': token_length,
                'sample': sample
            })
            if verbose:
                print(f"\n[REMOVED] Sample {i}: {token_length} tokens (>{max_length})")
                print(f"  Input preview: {sample.get('input', '')[:100]}...")
    
    # Calculate statistics
    stats = {
        'total_samples': len(data),
        'filtered_samples': len(filtered_data),
        'removed_samples': len(removed_data),
        'retention_rate': len(filtered_data) / len(data) * 100 if data else 0,
        'token_length_stats': {
            'min': min(token_lengths) if token_lengths else 0,
            'max': max(token_lengths) if token_lengths else 0,
            'avg': sum(token_lengths) / len(token_lengths) if token_lengths else 0,
            'median': sorted(token_lengths)[len(token_lengths)//2] if token_lengths else 0
        },
        'removed_details': [
            {
                'index': r['index'],
                'token_length': r['token_length'],
                'input_preview': r['sample'].get('input', '')[:100],
                'output_preview': r['sample'].get('output', '')[:100]
            }
            for r in removed_data[:10]  # Keep only first 10 for summary
        ]
    }
    
    return filtered_data, stats


def main():
    parser = argparse.ArgumentParser(
        description='Filter training samples by maximum token length',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python data_filter.py --input train.json --output train_filtered.json --model Qwen/Qwen2.5-Coder-7B-Instruct

  # Custom max length
  python data_filter.py --input train.json --output train_filtered.json --model Qwen/Qwen2.5-Coder-7B-Instruct --max_length 16384

  # Verbose mode
  python data_filter.py --input train.json --output train_filtered.json --model Qwen/Qwen2.5-Coder-7B-Instruct --verbose

  # Save removed samples
  python data_filter.py --input train.json --output train_filtered.json --model Qwen/Qwen2.5-Coder-7B-Instruct --save_removed removed.json
        """
    )
    
    parser.add_argument('--input', '-i', type=str, required=True,
                        help='Input JSON file path')
    parser.add_argument('--output', '-o', type=str, required=True,
                        help='Output JSON file path for filtered data')
    parser.add_argument('--model', '-m', type=str, required=True,
                        help='Model name or path (for tokenizer)')
    parser.add_argument('--max_length', '-l', type=int, default=None,
                        help='Maximum sequence length (default: auto-detect from model)')
    parser.add_argument('--save_removed', type=str, default=None,
                        help='Save removed samples to this file (optional)')
    parser.add_argument('--save_stats', type=str, default=None,
                        help='Save statistics to this file (optional)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print details of filtered samples')
    parser.add_argument('--trust_remote_code', action='store_true',
                        help='Trust remote code when loading tokenizer')
    
    args = parser.parse_args()
    
    # Load tokenizer
    print(f"\nLoading tokenizer from: {args.model}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            args.model,
            trust_remote_code=args.trust_remote_code
        )
        print(f"Tokenizer loaded successfully")
    except Exception as e:
        print(f"Error loading tokenizer: {e}")
        sys.exit(1)
    
    # Determine max_length
    if args.max_length is not None:
        max_length = args.max_length
        print(f"Using user-specified max_length: {max_length}")
    else:
        # Try to get from model config
        max_length = getattr(tokenizer, 'model_max_length', None)
        if max_length is None or max_length > 1e8:  # Some models have unrealistic defaults
            max_length = 32768  # Safe default
            print(f"Using default max_length: {max_length}")
        else:
            print(f"Using model's max_length: {max_length}")
    
    # Load dataset
    data = load_dataset(args.input)
    
    # Filter dataset
    filtered_data, stats = filter_dataset(
        data, 
        tokenizer, 
        max_length,
        verbose=args.verbose
    )
    
    # Print statistics
    print("\n" + "="*80)
    print("FILTERING STATISTICS")
    print("="*80)
    print(f"Total samples:           {stats['total_samples']}")
    print(f"Filtered samples:        {stats['filtered_samples']}")
    print(f"Removed samples:         {stats['removed_samples']}")
    print(f"Retention rate:          {stats['retention_rate']:.2f}%")
    print(f"\nToken length statistics:")
    print(f"  Min:     {stats['token_length_stats']['min']}")
    print(f"  Max:     {stats['token_length_stats']['max']}")
    print(f"  Average: {stats['token_length_stats']['avg']:.1f}")
    print(f"  Median:  {stats['token_length_stats']['median']}")
    print("="*80)
    
    if stats['removed_samples'] > 0:
        print(f"\nSamples exceeding max_length ({max_length}):")
        for detail in stats['removed_details']:
            print(f"  - Sample {detail['index']}: {detail['token_length']} tokens")
            print(f"    Input: {detail['input_preview']}...")
    
    # Save filtered data
    save_dataset(filtered_data, args.output)
    
    # Save removed samples if requested
    if args.save_removed and stats['removed_samples'] > 0:
        removed_samples = [sample for sample in data if sample not in filtered_data]
        save_dataset(removed_samples, args.save_removed)
        print(f"Removed samples saved to: {args.save_removed}")
    
    # Save statistics if requested
    if args.save_stats:
        stats_file = args.save_stats
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"Statistics saved to: {stats_file}")
    
    print("\n✅ Filtering completed!")


if __name__ == '__main__':
    main()
