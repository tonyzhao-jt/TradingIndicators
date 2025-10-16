# Parquet File Processing Tools

This directory contains tools for processing and merging parquet files, specifically designed for handling trading indicator data.

## Files

- `main.py` - Main entry point with subcommands for various operations
- `merge.py` - Core merging functionality for combining multiple parquet files

## Installation

Make sure you have the required dependencies installed:

```bash
pip install pandas pyarrow
```

## Usage

### Quick Merge (using merge.py directly)

```bash
# Basic merge - combines all .parquet files in a directory
python merge.py /path/to/parquet/files

# Merge with custom output path
python merge.py /path/to/files --output merged_data.parquet

# Merge specific pattern with sorting
python merge.py /path/to/files --pattern "processed_*.parquet" --sort-by timestamp

# Show file information without merging
python merge.py /path/to/files --info
```

### Using Main Interface (main.py)

The main script provides subcommands for different operations:

#### Merge Command

```bash
# Basic merge
python main.py merge /path/to/parquet/files

# Advanced merge options
python main.py merge /path/to/files \
  --output merged_result.parquet \
  --pattern "processed_batch_*.parquet" \
  --sort-by timestamp \
  --no-dedup

# Show file information
python main.py merge /path/to/files --info
```

#### Inspect Command

```bash
# Inspect a single parquet file
python main.py inspect /path/to/file.parquet

# Show more details
python main.py inspect /path/to/file.parquet --head 10 --sample 5
```

## Examples for Trading Indicators Data

### Merge processed batches

```bash
# Merge all processed batch files
python main.py merge ../../outputs/processed --pattern "processed_batch_*.parquet"

# Merge with timestamp sorting
python main.py merge ../../outputs/processed \
  --pattern "processed_batch_*.parquet" \
  --output ../../outputs/all_processed_data.parquet \
  --sort-by timestamp

# Check what files would be merged
python main.py merge ../../outputs/processed \
  --pattern "processed_batch_*.parquet" \
  --info
```

### Inspect processed data

```bash
# Quick inspection
python main.py inspect ../../outputs/processed/processed_batch_80_20251014_120534.parquet

# Detailed inspection
python main.py inspect ../../outputs/processed/processed_batch_80_20251014_120534.parquet \
  --head 3 --sample 2
```

## Command Line Options

### Merge Options

- `input_dir`: Directory containing parquet files to merge
- `--output`, `-o`: Output file path (auto-generated if not provided)
- `--pattern`, `-p`: File pattern to match (default: `*.parquet`)
- `--no-dedup`: Do not remove duplicate rows
- `--sort-by`, `-s`: Column name to sort the merged data by
- `--info`, `-i`: Show file information only (do not merge)

### Inspect Options

- `file`: Parquet file to inspect
- `--head`: Number of first rows to display (default: 5)
- `--sample`: Number of random rows to sample (default: 0)

## Features

- **Smart file discovery**: Automatically finds parquet files matching patterns
- **Duplicate removal**: Optionally removes duplicate rows during merge
- **Flexible sorting**: Sort merged data by any column
- **File information**: Get detailed statistics about parquet files
- **Error handling**: Graceful handling of corrupted or unreadable files
- **Memory efficient**: Processes files incrementally for large datasets

## Output

The merged parquet file will contain all data from the input files with:
- Consistent schema across all input files
- Optional duplicate removal
- Optional sorting by specified column
- Preserved data types and structure

## Notes

- Files are processed in order of modification time (newest first)
- Invalid or corrupted parquet files are skipped with warnings
- Output directory is created automatically if it doesn't exist
- Original files are never modified or deleted