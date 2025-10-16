"""Split merged parquet data into train and validation sets.

This script splits the merged parquet file into training and validation datasets
for VERL training with proper ratio and shuffling.
"""
import pandas as pd
import argparse
from pathlib import Path
from sklearn.model_selection import train_test_split
import sys


def split_data(input_file, output_dir, train_ratio=0.8, random_seed=42, shuffle=True):
    """Split parquet data into train and validation sets.
    
    Args:
        input_file: Path to input parquet file
        output_dir: Directory to save train/val files
        train_ratio: Ratio of data for training (default: 0.8)
        random_seed: Random seed for reproducibility
        shuffle: Whether to shuffle data before splitting
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading data from: {input_path}")
    df = pd.read_parquet(input_path)
    
    total_rows = len(df)
    print(f"Total rows: {total_rows}")
    
    if total_rows < 2:
        raise ValueError("Need at least 2 rows to split data")
    
    # For very small datasets, ensure at least 1 sample in validation
    if total_rows <= 5:
        # For tiny datasets, use 1 sample for validation
        train_size = total_rows - 1
        val_size = 1
        print(f"Small dataset detected: using {train_size} for train, {val_size} for validation")
        
        if shuffle:
            df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
        
        train_df = df.iloc[:train_size]
        val_df = df.iloc[train_size:]
        
    else:
        # Use train_test_split for larger datasets
        train_df, val_df = train_test_split(
            df, 
            train_size=train_ratio,
            random_state=random_seed,
            shuffle=shuffle
        )
    
    print(f"Train set: {len(train_df)} rows")
    print(f"Validation set: {len(val_df)} rows")
    
    # Save splits
    train_file = output_path / "train.parquet"
    val_file = output_path / "val.parquet"
    
    train_df.to_parquet(train_file, index=False)
    val_df.to_parquet(val_file, index=False)
    
    print(f"Saved train data to: {train_file}")
    print(f"Saved validation data to: {val_file}")
    
    return train_file, val_file


def main():
    parser = argparse.ArgumentParser(
        description="Split merged parquet data into train/validation sets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python split_data.py merged_data.parquet --output-dir ./splits
  python split_data.py merged_data.parquet --train-ratio 0.9 --seed 123
  python split_data.py merged_data.parquet --no-shuffle
        """
    )
    
    parser.add_argument('input_file',
                       help='Input parquet file to split')
    parser.add_argument('--output-dir', '-o',
                       default='./data_splits',
                       help='Output directory for train/val files (default: ./data_splits)')
    parser.add_argument('--train-ratio', '-r',
                       type=float, default=0.8,
                       help='Ratio of data for training (default: 0.8)')
    parser.add_argument('--seed', '-s',
                       type=int, default=42,
                       help='Random seed (default: 42)')
    parser.add_argument('--no-shuffle',
                       action='store_true',
                       help='Do not shuffle data before splitting')
    
    args = parser.parse_args()
    
    try:
        train_file, val_file = split_data(
            input_file=args.input_file,
            output_dir=args.output_dir,
            train_ratio=args.train_ratio,
            random_seed=args.seed,
            shuffle=not args.no_shuffle
        )
        
        print(f"\nSplit completed successfully!")
        print(f"Train file: {train_file}")
        print(f"Validation file: {val_file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())