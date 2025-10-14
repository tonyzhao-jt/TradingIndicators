"""Main entry point for the data processing pipeline."""
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from tqdm import tqdm

from graph import create_data_processing_graph
from config import BATCH_SIZE, CHECKPOINT_FILE, OUTPUT_DIR, INPUT_DIR


class DataProcessor:
    """Batch data processor with checkpoint recovery."""
    
    def __init__(self, input_file: str, output_dir: str = OUTPUT_DIR):
        """
        Initialize the data processor.
        
        Args:
            input_file: Path to input JSON file
            output_dir: Directory to save processed data
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Checkpoint file location
        self.checkpoint_file = self.output_dir / CHECKPOINT_FILE
        
        # Create the processing graph
        self.graph = create_data_processing_graph()

        # Load checkpoint if exists
        self.checkpoint = self._load_checkpoint()

        # Optional sample limit (set by CLI) — process only first N items if provided
        self.samples: int | None = None
        
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint from file if exists."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                
                # Restore strategy and rejection stats if available
                if "strategy_stats" in checkpoint:
                    self._strategy_stats = checkpoint["strategy_stats"]
                if "rejection_stats" in checkpoint:
                    self._rejection_stats = checkpoint["rejection_stats"]
                
                return checkpoint
        return {
            "last_processed_index": -1,
            "processed_count": 0,
            "rejected_count": 0,
            "timestamp": None
        }
    
    def _save_checkpoint(self):
        """Save checkpoint to file."""
        self.checkpoint["timestamp"] = datetime.now().isoformat()
        
        # Save strategy stats in checkpoint
        if hasattr(self, '_strategy_stats'):
            self.checkpoint["strategy_stats"] = self._strategy_stats
        if hasattr(self, '_rejection_stats'):
            self.checkpoint["rejection_stats"] = self._rejection_stats
            
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
    
    def _load_input_data(self) -> List[Dict[str, Any]]:
        """Load input data from JSON file."""
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    
    def _process_item(self, item: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Process a single data item through the workflow.
        
        Args:
            item: Data item to process
            index: Index of the item
            
        Returns:
            Processed data with status
        """
        initial_state = {
            "raw_data": item,
            "filter_result": None,
            "converted_code": None,
            "validation_result": None,
            "augmented_description": None,
            "description_metadata": None,
            "reasoning": None,
            "relevant_symbols": None,
            "symbol_metadata": None,
            "conversion_attempts": 0,
            "error_message": None,
            "status": "pending"
        }
        
        try:
            result = self.graph.invoke(initial_state)
            
            # Check if item was rejected at any stage
            status = result.get("status", "unknown")
            
            # Check if this is a strategy item (contains strategy() call)
            source_code = item.get("source_code", "")
            is_strategy = 'strategy(' in source_code and ('strategy.entry' in source_code or 'strategy.order' in source_code)
            
            if is_strategy:
                self._strategy_stats["total_strategies"] += 1
            
            # Track rejection reasons and strategy conversion stats
            if not hasattr(self, '_rejection_stats'):
                self._rejection_stats = {
                    "filter": 0,
                    "conversion": 0,
                    "validation": 0,
                    "other": 0
                }
            
            if not hasattr(self, '_strategy_stats'):
                self._strategy_stats = {
                    "total_strategies": 0,
                    "conversion_success": 0,
                    "conversion_failed": 0,
                    "validation_success": 0,
                    "validation_failed": 0,
                    "llm_quality_rejected": 0
                }
            
            # If rejected, track reason and return None to exclude from output
            if status in ["rejected", "rejected_by_filter", "filter_error"]:
                self._rejection_stats["filter"] += 1
                # Check if strategy was rejected for quality reasons
                if is_strategy and "quality" in result.get("rejection_reason", "").lower():
                    self._strategy_stats["llm_quality_rejected"] += 1
                return None  # Don't include in output
            elif status in ["conversion_failed", "conversion_error"]:
                self._rejection_stats["conversion"] += 1
                if is_strategy:
                    self._strategy_stats["conversion_failed"] += 1
                return None
            elif status in ["validation_failed", "validation_error"]:
                self._rejection_stats["validation"] += 1
                if is_strategy:
                    self._strategy_stats["validation_failed"] += 1
                return None
            elif status == "error":
                self._rejection_stats["other"] += 1
                return None
            
            # Track successful strategy conversions
            if is_strategy:
                if result.get("converted_code"):
                    self._strategy_stats["conversion_success"] += 1
                if result.get("validation_result"):
                    self._strategy_stats["validation_success"] += 1
            
            # Build processed record with only required fields
            # Output fields: id, name, description, reasoning, created_at, source_code, relevant_symbols
            processed = {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": result.get("augmented_description", ""),  # Use augmented description as final description
                "reasoning": result.get("reasoning", ""),
                "created_at": item.get("preview_created_at", ""),
                "source_code": result.get("converted_code", ""),  # Use converted code as final source_code
                "relevant_symbols": ",".join(result.get("relevant_symbols", [])),  # Comma-separated symbols
            }
            
            return processed
            
        except Exception as e:
            if not hasattr(self, '_rejection_stats'):
                self._rejection_stats = {"filter": 0, "conversion": 0, "validation": 0, "other": 0}
            self._rejection_stats["other"] += 1
            return None
    
    def _save_batch_to_parquet(self, batch_data: List[Dict[str, Any]], batch_num: int):
        """
        Save a batch of processed data to parquet file.
        
        Args:
            batch_data: List of processed records
            batch_num: Batch number for filename
        """
        if not batch_data:
            return
        
        # Filter out None values (rejected items) and keep only successful records
        successful_records = [
            record for record in batch_data 
            if record is not None and record.get("id") and record.get("name")
        ]
        
        if not successful_records:
            print(f"  No successful records in batch {batch_num}")
            return
        
        # Track batch statistics
        if not hasattr(self, '_batch_stats'):
            self._batch_stats = []
        
        self._batch_stats.append({
            "batch_num": batch_num,
            "total": len(batch_data),
            "accepted": len(successful_records),
            "rejected": len(batch_data) - len(successful_records)
        })
        
        # Create DataFrame with only the required columns
        df = pd.DataFrame(successful_records)
        
        # Ensure column order
        column_order = ["id", "name", "description", "reasoning", "created_at", "source_code", "relevant_symbols"]
        df = df[column_order]
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"processed_batch_{batch_num}_{timestamp}.parquet"
        
        # Save to parquet
        df.to_parquet(output_file, index=False, engine='pyarrow')
        print(f"  Saved batch {batch_num} to {output_file} ({len(successful_records)} records)")
    
    def _print_final_report(self, total_items: int, start_index: int):
        """
        Print final processing report with acceptance rate statistics.
        
        Args:
            total_items: Total number of items in dataset
            start_index: Index where processing started (for resume)
        """
        print("\n" + "="*70)
        print("📊 FINAL PROCESSING REPORT")
        print("="*70)
        
        # Calculate statistics
        processed_count = self.checkpoint['processed_count']
        rejected_count = self.checkpoint['rejected_count']
        accepted_count = processed_count - rejected_count
        
        # Calculate acceptance rate
        acceptance_rate = (accepted_count / processed_count * 100) if processed_count > 0 else 0
        rejection_rate = (rejected_count / processed_count * 100) if processed_count > 0 else 0
        
        # Print overview
        print(f"\n📁 Input File: {self.input_file}")
        print(f"📂 Output Directory: {self.output_dir}")
        
        print(f"\n📈 Processing Statistics:")
        print(f"  • Total items in dataset: {total_items}")
        print(f"  • Items processed: {processed_count}")
        if start_index > 0:
            print(f"  • Items skipped (resumed): {start_index}")
        
        print(f"\n✅ Acceptance Statistics:")
        print(f"  • Accepted: {accepted_count} items")
        print(f"  • Rejected: {rejected_count} items")
        print(f"  • Acceptance Rate: {acceptance_rate:.2f}%")
        print(f"  • Rejection Rate: {rejection_rate:.2f}%")
        
        # Batch statistics
        if hasattr(self, '_batch_stats') and self._batch_stats:
            print(f"\n📦 Batch-wise Statistics:")
            total_batches = len(self._batch_stats)
            avg_acceptance = sum(s['accepted'] for s in self._batch_stats) / sum(s['total'] for s in self._batch_stats) * 100
            
            print(f"  • Total batches: {total_batches}")
            print(f"  • Average batch acceptance: {avg_acceptance:.2f}%")
            
            # Show batch details
            print(f"\n  Batch Details:")
            for stat in self._batch_stats[-5:]:  # Show last 5 batches
                batch_rate = (stat['accepted'] / stat['total'] * 100) if stat['total'] > 0 else 0
                print(f"    Batch {stat['batch_num']}: {stat['accepted']}/{stat['total']} ({batch_rate:.1f}%)")
            
            if len(self._batch_stats) > 5:
                print(f"    ... and {len(self._batch_stats) - 5} more batches")
        
        # List output files
        print(f"\n📄 Output Files:")
        parquet_files = sorted(self.output_dir.glob("processed_batch_*.parquet"))
        if parquet_files:
            total_size = sum(f.stat().st_size for f in parquet_files)
            print(f"  • Generated {len(parquet_files)} Parquet file(s)")
            print(f"  • Total size: {total_size / 1024 / 1024:.2f} MB")
            
            # Show first few files
            for f in parquet_files[:3]:
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"    - {f.name} ({size_mb:.2f} MB)")
            
            if len(parquet_files) > 3:
                print(f"    ... and {len(parquet_files) - 3} more file(s)")
        else:
            print("  • No output files generated")
        
        # Strategy conversion statistics
        if hasattr(self, '_strategy_stats') and self._strategy_stats["total_strategies"] > 0:
            strategy_stats = self._strategy_stats
            print(f"\n🎯 Strategy Code Conversion Statistics:")
            print(f"  • Total strategies found: {strategy_stats['total_strategies']}")
            
            if strategy_stats['total_strategies'] > 0:
                conv_success_rate = (strategy_stats['conversion_success'] / strategy_stats['total_strategies']) * 100
                val_success_rate = (strategy_stats['validation_success'] / strategy_stats['total_strategies']) * 100
                
                print(f"  • Code conversion successful: {strategy_stats['conversion_success']} ({conv_success_rate:.1f}%)")
                print(f"  • Code conversion failed: {strategy_stats['conversion_failed']} ({(strategy_stats['conversion_failed'] / strategy_stats['total_strategies']) * 100:.1f}%)")
                print(f"  • Validation successful: {strategy_stats['validation_success']} ({val_success_rate:.1f}%)")  
                print(f"  • Validation failed: {strategy_stats['validation_failed']} ({(strategy_stats['validation_failed'] / strategy_stats['total_strategies']) * 100:.1f}%)")
                print(f"  • LLM quality rejected: {strategy_stats['llm_quality_rejected']} ({(strategy_stats['llm_quality_rejected'] / strategy_stats['total_strategies']) * 100:.1f}%)")

        # Rejection breakdown
        if hasattr(self, '_rejection_stats') and sum(self._rejection_stats.values()) > 0:
            print(f"\n❌ Rejection Breakdown:")
            total_rejections = sum(self._rejection_stats.values())
            
            for reason, count in sorted(self._rejection_stats.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    percentage = (count / total_rejections * 100)
                    reason_name = {
                        "filter": "Filter (quality/length)",
                        "conversion": "Code Conversion Failed",
                        "validation": "Validation Failed",
                        "other": "Other Errors"
                    }.get(reason, reason)
                    print(f"  • {reason_name}: {count} ({percentage:.1f}%)")
        
        # Quality insights
        print(f"\n💡 Quality Insights:")
        if acceptance_rate >= 80:
            print(f"  ✓ Excellent acceptance rate! Most data meets quality standards.")
        elif acceptance_rate >= 60:
            print(f"  ✓ Good acceptance rate. Data quality is generally satisfactory.")
        elif acceptance_rate >= 40:
            print(f"  ⚠ Moderate acceptance rate. Consider reviewing rejection reasons.")
        else:
            print(f"  ⚠ Low acceptance rate. Many items rejected for quality issues.")
        
        print(f"\n  Common rejection reasons may include:")
        print(f"    • Descriptions shorter than {self._get_min_words()} words")
        print(f"    • Insufficient indicator/strategy details")
        print(f"    • Missing technical implementation information")
        print(f"    • Code conversion failures")
        print(f"    • Validation errors")
        
        print("\n" + "="*70)
        print("✅ Processing Complete!")
        print("="*70)
    
    def _get_min_words(self) -> int:
        """Get minimum words configuration."""
        try:
            from config import MIN_DESCRIPTION_WORDS
            return MIN_DESCRIPTION_WORDS
        except:
            return 100  # default
    
    def process(self, resume: bool = True):
        """
        Process all data in batches with checkpoint support.
        
        Args:
            resume: Whether to resume from checkpoint
        """
        print("="*70)
        print("Data Processing Pipeline")
        print("="*70)
        
        # Load input data
        print(f"\nLoading data from: {self.input_file}")
        data = self._load_input_data()

        # Apply sample limit if provided
        if getattr(self, 'samples', None) and isinstance(self.samples, int) and self.samples > 0:
            data = data[: self.samples]

        total_items = len(data)
        print(f"Total items: {total_items}")
        
        # Determine starting point
        start_index = self.checkpoint["last_processed_index"] + 1 if resume else 0
        
        if resume and start_index > 0:
            print(f"\nResuming from index: {start_index}")
            print(f"Already processed: {self.checkpoint['processed_count']} items")
        
        # Process in batches
        batch_num = start_index // BATCH_SIZE
        current_batch = []
        
        print(f"\nProcessing with batch size: {BATCH_SIZE}")
        print("="*70)
        
        for idx in tqdm(range(start_index, total_items), desc="Processing"):
            item = data[idx]

            # Process item
            processed = self._process_item(item, idx)
            current_batch.append(processed)

            # Update checkpoint
            self.checkpoint["last_processed_index"] = idx
            self.checkpoint["processed_count"] += 1

            # _process_item returns None for rejected/errored items; handle defensively
            if processed is None:
                self.checkpoint["rejected_count"] += 1
            
            # Save batch when full
            if len(current_batch) >= BATCH_SIZE:
                self._save_batch_to_parquet(current_batch, batch_num)
                current_batch = []
                batch_num += 1
                
                # Save checkpoint after each batch
                self._save_checkpoint()
        
        # Save remaining items
        if current_batch:
            self._save_batch_to_parquet(current_batch, batch_num)
        
        # Final checkpoint save
        self._save_checkpoint()
        
        # Generate final report
        self._print_final_report(total_items, start_index)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_json_file> [--no-resume]")
        print("\nExample:")
        print(f"  python main.py {INPUT_DIR}/trade_raw_data_20251011_053837.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    resume = "--no-resume" not in sys.argv
    # Parse optional --samples argument (supports --samples N or --samples=N)
    samples = None
    if "--samples" in sys.argv:
        try:
            i = sys.argv.index("--samples")
            samples = int(sys.argv[i + 1])
        except Exception:
            print("Invalid --samples value. It should be an integer.\n")
            sys.exit(1)
    else:
        # support --samples=N style
        for a in sys.argv[2:]:
            if a.startswith("--samples="):
                try:
                    samples = int(a.split("=", 1)[1])
                except Exception:
                    print("Invalid --samples value. It should be an integer.\n")
                    sys.exit(1)
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Create processor and run
    processor = DataProcessor(input_file)
    if samples:
        processor.samples = samples
    
    try:
        processor.process(resume=resume)
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted. Progress saved to checkpoint.")
        print("Run again to resume from last checkpoint.")
    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
