"""Main entry point for parquet file processing tools.

This script provides a convenient interface for various parquet file operations
including merging, inspection, and analysis.
"""
import sys
import argparse
from pathlib import Path
from typing import Optional

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from merge import ParquetMerger


def merge_command(args):
    """Handle the merge subcommand."""
    try:
        merger = ParquetMerger(args.input_dir, args.output)
        
        if args.info:
            # Show file information
            info_df = merger.get_file_info(args.pattern)
            if info_df.empty:
                print(f"No parquet files found matching pattern '{args.pattern}'")
                return 1
            
            print(f"\nParquet files in {args.input_dir}:")
            print(info_df.to_string(index=False))
            print(f"\nTotal files: {len(info_df)}")
            print(f"Total rows: {info_df['rows'].sum()}")
            print(f"Total size: {info_df['size_mb'].sum():.2f} MB")
            return 0
        
        # Perform the merge
        output_file = merger.merge_files(
            pattern=args.pattern,
            output_path=args.output,
            remove_duplicates=not args.no_dedup,
            sort_by=args.sort_by
        )
        
        print(f"\nMerge completed successfully!")
        print(f"Output file: {output_file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def inspect_command(args):
    """Handle the inspect subcommand."""
    try:
        import pandas as pd
        
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 1
        
        print(f"Inspecting: {file_path}")
        
        # Read parquet file
        df = pd.read_parquet(file_path, engine='pyarrow')
        
        if df.empty:
            print("Parquet file is empty")
            return 0
        
        print(f"\nFile info:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Size: {file_path.stat().st_size / (1024*1024):.2f} MB")
        
        print(f"\nColumns:")
        for i, col in enumerate(df.columns):
            dtype = str(df[col].dtype)
            non_null = df[col].count()
            print(f"  {i+1:2d}. {col} ({dtype}) - {non_null}/{len(df)} non-null")
        
        if args.head > 0:
            print(f"\nFirst {args.head} rows:")
            print(df.head(args.head).to_string(index=False))
        
        if args.sample > 0:
            print(f"\nRandom sample of {args.sample} rows:")
            sample_df = df.sample(n=min(args.sample, len(df)))
            print(sample_df.to_string(index=False))
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="Parquet file processing tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Merge subcommand
    merge_parser = subparsers.add_parser('merge', 
                                        help='Merge parquet files from a directory')
    merge_parser.add_argument('input_dir', 
                             help='Directory containing parquet files to merge')
    merge_parser.add_argument('--output', '-o',
                             help='Output file path (auto-generated if not provided)')
    merge_parser.add_argument('--pattern', '-p', 
                             default='*.parquet',
                             help='File pattern to match (default: *.parquet)')
    merge_parser.add_argument('--no-dedup', 
                             action='store_true',
                             help='Do not remove duplicate rows')
    merge_parser.add_argument('--sort-by', '-s',
                             help='Column name to sort the merged data by')
    merge_parser.add_argument('--info', '-i',
                             action='store_true',
                             help='Show file information only (do not merge)')
    
    # Inspect subcommand
    inspect_parser = subparsers.add_parser('inspect', 
                                          help='Inspect a single parquet file')
    inspect_parser.add_argument('file',
                               help='Parquet file to inspect')
    inspect_parser.add_argument('--head', 
                               type=int, default=5,
                               help='Number of first rows to display (default: 5)')
    inspect_parser.add_argument('--sample',
                               type=int, default=0,
                               help='Number of random rows to sample (default: 0)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'merge':
        return merge_command(args)
    elif args.command == 'inspect':
        return inspect_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())