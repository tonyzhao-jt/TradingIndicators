"""
Token Static Checker

This module analyzes token statistics for a dataset using a specific model's tokenizer.
It provides detailed statistics on input, output, and combined token counts.
"""

import json
import argparse
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import statistics
from transformers import AutoTokenizer


class TokenStatistics:
    """Class to store and calculate token statistics."""
    
    def __init__(self):
        self.input_tokens = []
        self.output_tokens = []
        self.combined_tokens = []
    
    def add_sample(self, input_count: int, output_count: int, combined_count: int):
        """Add token counts for a sample."""
        self.input_tokens.append(input_count)
        self.output_tokens.append(output_count)
        self.combined_tokens.append(combined_count)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Calculate comprehensive statistics for all token types."""
        stats = {}
        
        for token_type, tokens in [
            ("input", self.input_tokens),
            ("output", self.output_tokens),
            ("combined", self.combined_tokens)
        ]:
            if tokens:
                stats[token_type] = {
                    "count": len(tokens),
                    "total": sum(tokens),
                    "min": min(tokens),
                    "max": max(tokens),
                    "mean": statistics.mean(tokens),
                    "median": statistics.median(tokens),
                    "std_dev": statistics.stdev(tokens) if len(tokens) > 1 else 0.0,
                    "percentile_25": statistics.quantiles(tokens, n=4)[0] if len(tokens) >= 4 else min(tokens),
                    "percentile_75": statistics.quantiles(tokens, n=4)[2] if len(tokens) >= 4 else max(tokens),
                    "percentile_95": statistics.quantiles(tokens, n=20)[18] if len(tokens) >= 20 else max(tokens),
                    "percentile_99": statistics.quantiles(tokens, n=100)[98] if len(tokens) >= 100 else max(tokens)
                }
            else:
                stats[token_type] = {}
        
        return stats


class TokenStaticChecker:
    """Main class for token static analysis."""
    
    def __init__(self, model_name: str):
        """
        Initialize the token checker.
        
        Args:
            model_name: Name or path of the model to load tokenizer from
        """
        self.model_name = model_name
        self.tokenizer = None
        self.load_tokenizer()
    
    def load_tokenizer(self):
        """Load the tokenizer for the specified model."""
        try:
            print(f"Loading tokenizer for model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            print(f"Tokenizer loaded successfully. Vocab size: {self.tokenizer.vocab_size}")
        except Exception as e:
            print(f"Error loading tokenizer: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            Number of tokens
        """
        # Handle None, empty strings, or non-string types
        if text is None or text == '':
            return 0
        
        # Convert to string if not already
        if not isinstance(text, str):
            text = str(text)
        
        try:
            tokens = self.tokenizer.encode(text, add_special_tokens=True)
            return len(tokens)
        except Exception as e:
            print(f"Error tokenizing text (type: {type(text)}): {e}")
            return 0
    
    def analyze_dataset(self, data_path: str) -> TokenStatistics:
        """
        Analyze token statistics for the entire dataset.
        
        Args:
            data_path: Path to the JSON dataset file
            
        Returns:
            TokenStatistics object with comprehensive statistics
        """
        print(f"Loading dataset from: {data_path}")
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
        except Exception as e:
            print(f"Error loading dataset: {e}")
            raise
        
        print(f"Dataset loaded. Total samples: {len(dataset)}")
        
        stats = TokenStatistics()
        
        for i, sample in enumerate(dataset):
            if i % 100 == 0:
                print(f"Processing sample {i+1}/{len(dataset)}")
            
            # Extract input and output text, ensuring they are strings
            input_text = sample.get('input', '')
            output_text = sample.get('output', '')
            
            # Convert to string if needed
            if not isinstance(input_text, str):
                input_text = str(input_text) if input_text is not None else ''
            if not isinstance(output_text, str):
                output_text = str(output_text) if output_text is not None else ''
            
            # Count tokens
            input_tokens = self.count_tokens(input_text)
            output_tokens = self.count_tokens(output_text)
            
            # Combined tokens (input + output + any special tokens)
            combined_text = input_text + output_text
            combined_tokens = self.count_tokens(combined_text)
            
            # Add to statistics
            stats.add_sample(input_tokens, output_tokens, combined_tokens)
        
        print("Analysis complete!")
        return stats
    
    def print_statistics(self, stats: TokenStatistics):
        """Print formatted statistics to console."""
        statistics_data = stats.get_statistics()
        
        print("\n" + "="*80)
        print("TOKEN STATISTICS REPORT")
        print("="*80)
        print(f"Model: {self.model_name}")
        print(f"Tokenizer vocab size: {self.tokenizer.vocab_size}")
        print("="*80)
        
        for token_type in ["input", "output", "combined"]:
            if token_type in statistics_data:
                data = statistics_data[token_type]
                print(f"\n{token_type.upper()} TOKENS:")
                print("-" * 40)
                print(f"  Total samples:    {data.get('count', 0):,}")
                print(f"  Total tokens:     {data.get('total', 0):,}")
                print(f"  Min tokens:       {data.get('min', 0):,}")
                print(f"  Max tokens:       {data.get('max', 0):,}")
                print(f"  Mean tokens:      {data.get('mean', 0):.2f}")
                print(f"  Median tokens:    {data.get('median', 0):.2f}")
                print(f"  Std deviation:    {data.get('std_dev', 0):.2f}")
                print(f"  25th percentile:  {data.get('percentile_25', 0):.2f}")
                print(f"  75th percentile:  {data.get('percentile_75', 0):.2f}")
                print(f"  95th percentile:  {data.get('percentile_95', 0):.2f}")
                print(f"  99th percentile:  {data.get('percentile_99', 0):.2f}")
    
    def save_statistics_to_file(self, stats: TokenStatistics, output_path: str):
        """Save statistics to JSON file."""
        statistics_data = stats.get_statistics()
        
        # Add metadata
        report = {
            "metadata": {
                "model_name": self.model_name,
                "vocab_size": self.tokenizer.vocab_size,
                "analysis_timestamp": None  # Could add datetime if needed
            },
            "statistics": statistics_data
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\nStatistics saved to: {output_path}")
        except Exception as e:
            print(f"Error saving statistics: {e}")
    
    def get_token_distribution_analysis(self, stats: TokenStatistics) -> Dict[str, Any]:
        """Get additional distribution analysis."""
        analysis = {}
        
        for token_type in ["input", "output", "combined"]:
            tokens = getattr(stats, f"{token_type}_tokens")
            if tokens:
                # Token length distribution
                distribution = defaultdict(int)
                for count in tokens:
                    # Group into ranges
                    if count < 50:
                        distribution["0-49"] += 1
                    elif count < 100:
                        distribution["50-99"] += 1
                    elif count < 200:
                        distribution["100-199"] += 1
                    elif count < 500:
                        distribution["200-499"] += 1
                    elif count < 1000:
                        distribution["500-999"] += 1
                    elif count < 2000:
                        distribution["1000-1999"] += 1
                    else:
                        distribution["2000+"] += 1
                
                analysis[token_type] = dict(distribution)
        
        return analysis


def main():
    """Main function to run the token static checker."""
    parser = argparse.ArgumentParser(description="Token Static Checker for Dataset Analysis")
    parser.add_argument(
        "--model_name", 
        type=str, 
        default="Qwen/Qwen2.5-Coder-7B",
        help="Model name or path for tokenizer"
    )
    parser.add_argument(
        "--data_path",
        type=str,
        default="/workspace/trading_indicators/outputs/segments_20251014.json",
        help="Path to the dataset JSON file"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="token_statistics_report.json",
        help="Path to save the statistics report"
    )
    parser.add_argument(
        "--show_distribution",
        action="store_true",
        help="Show token length distribution analysis"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize checker
        checker = TokenStaticChecker(args.model_name)
        
        # Analyze dataset
        stats = checker.analyze_dataset(args.data_path)
        
        # Print statistics
        checker.print_statistics(stats)
        
        # Show distribution if requested
        if args.show_distribution:
            print("\n" + "="*80)
            print("TOKEN DISTRIBUTION ANALYSIS")
            print("="*80)
            distribution = checker.get_token_distribution_analysis(stats)
            for token_type, dist in distribution.items():
                print(f"\n{token_type.upper()} TOKEN DISTRIBUTION:")
                print("-" * 40)
                for range_str, count in sorted(dist.items()):
                    percentage = (count / len(getattr(stats, f"{token_type}_tokens"))) * 100
                    print(f"  {range_str:>12} tokens: {count:>6} samples ({percentage:5.1f}%)")
        
        # Save to file
        checker.save_statistics_to_file(stats, args.output_path)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
