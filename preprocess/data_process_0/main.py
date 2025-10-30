"""Main entry point for the data_process_0 pipeline."""
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from tqdm import tqdm

from graph import create_data_processing_graph
from config import BATCH_SIZE, CHECKPOINT_FILE, OUTPUT_DIR, INPUT_DIR, SAVE_INTERMEDIATE_EVERY_N_BATCHES


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
        
        # Statistics tracking
        self._stats = {
            "total_processed": 0,
            "filter_passed": 0,
            "filter_failed": 0,
            "visualization_removed": 0,
            "successfully_restructured": 0,
            "errors": 0
        }
        
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint from file if exists."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                return checkpoint
        return {"processed_ids": set(), "last_index": 0}

    def _save_checkpoint(self, processed_ids: set, last_index: int):
        """Save checkpoint to file."""
        checkpoint = {
            "processed_ids": list(processed_ids),
            "last_index": last_index,
            "timestamp": datetime.now().isoformat(),
            "stats": self._stats
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    def process_file(self, samples: int = None) -> str:
        """
        Process the input file and return the output file path.
        
        Args:
            samples: Optional limit on number of samples to process
            
        Returns:
            Path to the output file
        """
        self.samples = samples
        
        # Load input data
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("Input file must contain a JSON array")
        
        # Limit samples if specified
        if self.samples:
            data = data[:self.samples]
            print(f"Processing limited to {self.samples} samples")
        
        # Get already processed IDs from checkpoint
        processed_ids = set(self.checkpoint.get("processed_ids", []))
        last_index = self.checkpoint.get("last_index", 0)
        
        # Filter out already processed items
        remaining_data = []
        for i, item in enumerate(data):
            if i >= last_index or item.get("id") not in processed_ids:
                remaining_data.append((i, item))
        
        print(f"Total items: {len(data)}")
        print(f"Already processed: {len(data) - len(remaining_data)}")
        print(f"Remaining to process: {len(remaining_data)}")
        
        if not remaining_data:
            print("All items already processed!")
            return self._get_output_file()
        
        # Process in batches
        processed_results = []
        batch_size = BATCH_SIZE
        save_interval = SAVE_INTERMEDIATE_EVERY_N_BATCHES  # Save intermediate results every N batches
        
        for i in tqdm(range(0, len(remaining_data), batch_size), desc="Processing batches"):
            batch = remaining_data[i:i + batch_size]
            batch_results = self._process_batch(batch)
            processed_results.extend(batch_results)
            
            # Update checkpoint with new processed IDs
            new_processed_ids = {item["id"] for _, result in zip(batch, batch_results) 
                               for item in [result.get("raw_data", {})] if item.get("id")}
            processed_ids.update(new_processed_ids)
            
            # Update last index
            if batch:
                last_index = max(last_index, batch[-1][0] + 1)
            
            # Save checkpoint
            self._save_checkpoint(processed_ids, last_index)
            
            # Save intermediate results every save_interval batches
            batch_num = i // batch_size + 1
            if batch_num % save_interval == 0:
                self._save_intermediate_results(processed_results, batch_num)
                print(f"Intermediate results saved after batch {batch_num}")
        
        
        # Save results
        output_file = self._save_results(processed_results)
        self._print_final_stats()
        
        return output_file

    def _process_batch(self, batch: List[tuple]) -> List[Dict[str, Any]]:
        """Process a batch of items."""
        batch_results = []
        
        for index, item in batch:
            try:
                # Create initial state
                initial_state = {
                    "raw_data": item,
                    "status": "new"
                }
                
                # Process through graph
                result = self.graph.invoke(initial_state)
                
                # Update statistics
                self._update_stats(result)
                
                batch_results.append(result)
                
            except Exception as e:
                print(f"Error processing item {item.get('id', 'unknown')}: {str(e)}")
                error_result = {
                    "raw_data": item,
                    "status": "processing_error",
                    "error_message": str(e)
                }
                batch_results.append(error_result)
                self._stats["errors"] += 1
        
        return batch_results

    def _update_stats(self, result: Dict[str, Any]):
        """Update processing statistics."""
        self._stats["total_processed"] += 1
        
        status = result.get("status", "unknown")
        
        if status == "rejected_by_filter":
            self._stats["filter_failed"] += 1
        elif "filter" in status and "error" not in status:
            self._stats["filter_passed"] += 1
            
        if status == "visualization_removed" or status == "completed":
            self._stats["visualization_removed"] += 1
            
        if status == "completed":
            self._stats["successfully_restructured"] += 1

    def _save_intermediate_results(self, results: List[Dict[str, Any]], batch_num: int):
        """Save intermediate processing results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"data_process_0_intermediate_batch{batch_num}_{timestamp}.json"
        
        # Prepare output data
        output_data = {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "input_file": str(self.input_file),
                "total_items": len(results),
                "batch_number": batch_num,
                "is_intermediate": True,
                "processing_stats": self._stats
            },
            "results": results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def _save_results(self, results: List[Dict[str, Any]]) -> str:
        """Save processing results to output file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"data_process_0_results_{timestamp}.json"
        
        # Prepare output data
        output_data = {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "input_file": str(self.input_file),
                "total_items": len(results),
                "is_intermediate": False,
                "processing_stats": self._stats
            },
            "results": results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {output_file}")
        return str(output_file)

    def _get_output_file(self) -> str:
        """Get the latest output file path."""
        output_files = list(self.output_dir.glob("data_process_0_results_*.json"))
        if output_files:
            latest_file = max(output_files, key=lambda x: x.stat().st_mtime)
            return str(latest_file)
        return str(self.output_dir / "data_process_0_results_latest.json")

    def _print_final_stats(self):
        """Print final processing statistics."""
        print("\n" + "="*50)
        print("PROCESSING COMPLETE")
        print("="*50)
        print(f"Total processed: {self._stats['total_processed']}")
        print(f"Filter passed: {self._stats['filter_passed']}")
        print(f"Filter failed: {self._stats['filter_failed']}")
        print(f"Visualization removed: {self._stats['visualization_removed']}")
        print(f"Successfully restructured: {self._stats['successfully_restructured']}")
        print(f"Errors: {self._stats['errors']}")
        
        if self._stats['total_processed'] > 0:
            success_rate = (self._stats['successfully_restructured'] / self._stats['total_processed']) * 100
            print(f"Success rate: {success_rate:.1f}%")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run data_process_0 pipeline")
    parser.add_argument("input_file", help="Path to input JSON file")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--samples", type=int, help="Limit number of samples to process")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = DataProcessor(
        input_file=args.input_file,
        output_dir=args.output_dir
    )
    
    # Process file
    output_file = processor.process_file(samples=args.samples)
    print(f"\nProcessing complete! Output saved to: {output_file}")


if __name__ == "__main__":
    main()