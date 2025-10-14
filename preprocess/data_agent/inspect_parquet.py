"""Inspect the latest processed_batch_*.parquet file and print the first row.

Usage: python inspect_parquet.py [--output-dir PATH]
"""
import sys
from pathlib import Path
import pandas as pd

OUTPUT_DIR = Path("../../outputs/processed")


def _inspect_file(path: Path):
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    print(f"Inspecting: {path}")
    try:
        df = pd.read_parquet(path, engine='pyarrow')
    except Exception as e:
        print(f"Failed to read parquet: {e}")
        return 1

    if df.empty:
        print("Parquet file is empty")
        return 0

    # Print first row nicely
    row = df.iloc[0]
    print("\n-- First record --")
    for k, v in row.to_dict().items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    # If argument provided and it's a file, inspect that file. If argument is a directory or not provided, find latest in directory.
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.is_file():
            raise SystemExit(_inspect_file(p))
        elif p.is_dir():
            out_dir = p
        else:
            print(f"Path not found: {p}")
            raise SystemExit(1)
    else:
        out_dir = OUTPUT_DIR

    if not out_dir.exists():
        print(f"Output directory not found: {out_dir}")
        raise SystemExit(1)

    files = sorted(out_dir.glob("processed_batch_*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("No processed_batch_*.parquet files found in output directory.")
        raise SystemExit(0)

    latest = files[0]
    raise SystemExit(_inspect_file(latest))
 