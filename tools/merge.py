"""Merge multiple parquet files from a given folder into a single parquet file.

This module provides functionality to merge parquet files with similar schema
from a directory into a consolidated parquet file.
"""
import sys
from pathlib import Path
from typing import List, Optional, Union
import pandas as pd
import argparse
from datetime import datetime


class ParquetMerger:
    """Class to handle merging of parquet files."""
    
    def __init__(self, input_dir: Union[str, Path], output_path: Optional[Union[str, Path]] = None):
        """Initialize the ParquetMerger.
        
        Args:
            input_dir: Directory containing parquet files to merge
            output_path: Output file path. If None, will be auto-generated
        """
        self.input_dir = Path(input_dir)
        self.output_path = Path(output_path) if output_path else None
        
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")
        if not self.input_dir.is_dir():
            raise ValueError(f"Input path is not a directory: {self.input_dir}")
    
    def find_parquet_files(self, pattern: str = "*.parquet") -> List[Path]:
        """Find all parquet files in the input directory.
        
        Args:
            pattern: Glob pattern to match files (default: "*.parquet")
            
        Returns:
            List of Path objects for parquet files
        """
        files = list(self.input_dir.glob(pattern))
        # Sort by modification time (newest first) for consistent ordering
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files
    
    def merge_files(self, 
                   pattern: str = "*.parquet",
                   output_path: Optional[Union[str, Path]] = None,
                   remove_duplicates: bool = True,
                   sort_by: Optional[str] = None) -> Path:
        """Merge parquet files into a single file.
        
        Args:
            pattern: Glob pattern to match files (default: "*.parquet")
            output_path: Output file path. If None, uses instance default or auto-generates
            remove_duplicates: Whether to remove duplicate rows
            sort_by: Column name to sort by (optional)
            
        Returns:
            Path to the merged output file
        """
        files = self.find_parquet_files(pattern)
        
        if not files:
            raise ValueError(f"No parquet files found matching pattern '{pattern}' in {self.input_dir}")
        
        print(f"Found {len(files)} parquet files to merge:")
        for f in files:
            print(f"  - {f.name}")
        
        # Read and combine all parquet files
        dataframes = []
        total_rows = 0
        
        for file_path in files:
            try:
                df = pd.read_parquet(file_path, engine='pyarrow')
                dataframes.append(df)
                total_rows += len(df)
                print(f"  Loaded {len(df)} rows from {file_path.name}")
            except Exception as e:
                print(f"  Warning: Failed to read {file_path.name}: {e}")
                continue
        
        if not dataframes:
            raise ValueError("No valid parquet files could be read")
        
        print(f"\nCombining {len(dataframes)} dataframes with {total_rows} total rows...")
        
        # Concatenate all dataframes
        merged_df = pd.concat(dataframes, ignore_index=True)
        
        # Remove duplicates if requested
        if remove_duplicates:
            initial_rows = len(merged_df)
            merged_df = merged_df.drop_duplicates()
            final_rows = len(merged_df)
            if initial_rows != final_rows:
                print(f"Removed {initial_rows - final_rows} duplicate rows")
        
        # Sort if requested
        if sort_by and sort_by in merged_df.columns:
            print(f"Sorting by column: {sort_by}")
            merged_df = merged_df.sort_values(by=sort_by)
        
        # Determine output path
        if output_path:
            final_output_path = Path(output_path)
        elif self.output_path:
            final_output_path = self.output_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_output_path = self.input_dir / f"merged_{timestamp}.parquet"
        
        # Ensure output directory exists
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save merged dataframe
        print(f"\nSaving merged data to: {final_output_path}")
        merged_df.to_parquet(final_output_path, engine='pyarrow', index=False)
        
        print(f"Successfully merged {len(merged_df)} rows into {final_output_path}")
        return final_output_path
    
    def get_file_info(self, pattern: str = "*.parquet") -> pd.DataFrame:
        """Get information about parquet files in the directory.
        
        Args:
            pattern: Glob pattern to match files
            
        Returns:
            DataFrame with file information
        """
        files = self.find_parquet_files(pattern)
        
        if not files:
            return pd.DataFrame(columns=['filename', 'size_mb', 'rows', 'columns', 'modified'])
        
        file_info = []
        for file_path in files:
            try:
                df = pd.read_parquet(file_path, engine='pyarrow')
                size_mb = file_path.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                file_info.append({
                    'filename': file_path.name,
                    'size_mb': round(size_mb, 2),
                    'rows': len(df),
                    'columns': len(df.columns),
                    'modified': modified
                })
            except Exception as e:
                print(f"Warning: Could not read {file_path.name}: {e}")
        
        return pd.DataFrame(file_info)


def main():
    """Command line interface for the ParquetMerger."""
    parser = argparse.ArgumentParser(
        description="Merge parquet files from a directory into a single file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python merge.py /path/to/parquet/files
  python merge.py /path/to/files --output merged_data.parquet
  python merge.py /path/to/files --pattern "processed_*.parquet" --sort-by timestamp
  python merge.py /path/to/files --info  # Just show file information
        """
    )
    
    parser.add_argument('input_dir', 
                       help='Directory containing parquet files to merge')
    parser.add_argument('--output', '-o',
                       help='Output file path (auto-generated if not provided)')
    parser.add_argument('--pattern', '-p', 
                       default='*.parquet',
                       help='File pattern to match (default: *.parquet)')
    parser.add_argument('--no-dedup', 
                       action='store_true',
                       help='Do not remove duplicate rows')
    parser.add_argument('--sort-by', '-s',
                       help='Column name to sort the merged data by')
    parser.add_argument('--info', '-i',
                       action='store_true',
                       help='Show file information only (do not merge)')
    
    args = parser.parse_args()
    
    try:
        merger = ParquetMerger(args.input_dir, args.output)
        
        if args.info:
            # Just show file information
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


if __name__ == "__main__":
    sys.exit(main())