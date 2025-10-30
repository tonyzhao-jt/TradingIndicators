#!/usr/bin/env python3
"""
Data Process Script - Extract high-quality description->code pairs from raw strategy data

This pipeline processes raw trading strategy data from TradingView to extract
clean, high-quality description-code pairs suitable for training.

Pipeline Steps:
1. Filter: Remove strategies with low likes (<100), short descriptions, or short code
2. Language Convert: Translate non-English descriptions to English using LLM
3. Vis Remove: Remove visualization-related code (plot, label, etc.) to keep core logic
4. Quality Score: Score description-code match and filter based on quality threshold

Input: strategies_20251014_054134.json (raw strategy data)
Output: script_YYYYMMDD_HHMMSS.json (clean description-code pairs)
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config import (
    INPUT_FILE, OUTPUT_DIR, MIN_LIKES_COUNT, MIN_CODE_LENGTH, 
    MIN_DESCRIPTION_LENGTH, QUALITY_SCORE_THRESHOLD, MAX_WORKERS,
    ENABLE_LANGUAGE_CONVERT, ENABLE_VIS_REMOVE, ENABLE_QUALITY_SCORE
)
from nodes import filter_strategies, convert_language, remove_visualization, score_and_filter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataProcessScript:
    """Main pipeline for processing trading strategy scripts."""
    
    def __init__(self, input_file=None, output_dir=None, enable_language_convert=True, 
                 enable_vis_remove=True, enable_quality_score=True, max_workers=3):
        """
        Initialize the pipeline.
        
        Args:
            input_file: Path to input JSON file
            output_dir: Directory for output files
            enable_language_convert: Whether to enable language conversion
            enable_vis_remove: Whether to enable visualization removal
            enable_quality_score: Whether to enable quality scoring
            max_workers: Maximum concurrent workers for LLM calls
        """
        self.input_file = input_file or INPUT_FILE
        self.output_dir = output_dir or OUTPUT_DIR
        self.enable_language_convert = enable_language_convert
        self.enable_vis_remove = enable_vis_remove
        self.enable_quality_score = enable_quality_score
        self.max_workers = max_workers
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Statistics
        self.stats = {
            "start_time": datetime.now().isoformat(),
            "input_file": self.input_file,
            "pipeline_config": {
                "language_convert": enable_language_convert,
                "vis_remove": enable_vis_remove,
                "quality_score": enable_quality_score,
                "max_workers": max_workers
            }
        }
    
    def load_input_data(self) -> list:
        """Load input data from JSON file."""
        logger.info(f"Loading data from: {self.input_file}")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} strategies")
        return data
    
    def save_output(self, data: list, metadata: dict):
        """Save processed data to output file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"script_{timestamp}.json")
        
        # Convert to simple input-output format for training
        training_data = []
        detailed_metadata = []
        
        for item in data:
            # Simple training format: only input and output
            training_item = {
                "input": item.get("description", ""),
                "output": item.get("source_code", "")
            }
            training_data.append(training_item)
            
            # Detailed metadata for each item
            item_metadata = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "likes_count": item.get("likes_count", 0),
                "author": item.get("preview_author", ""),
                "was_translated": item.get("was_translated", False),
                "original_language": item.get("original_language", "English"),
                "visualization_removed": item.get("visualization_removed", False),
                "removed_lines_count": item.get("removed_lines_count", 0),
                "script_url": item.get("script_url", ""),
                "quality_score": item.get("quality_score", 0),
                "quality_metrics": item.get("quality_metrics", {}),
                "quality_reasoning": item.get("quality_reasoning", "")
            }
            detailed_metadata.append(item_metadata)
        
        # Save training data (simple format)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Training data saved to: {output_file}")
        
        # Save detailed metadata (includes pipeline stats + per-item metadata)
        metadata_file = os.path.join(self.output_dir, f"script_{timestamp}_metadata.json")
        full_metadata = {
            "pipeline_statistics": metadata,
            "items_metadata": detailed_metadata
        }
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(full_metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Metadata saved to: {metadata_file}")
        
        return output_file
    
    def process(self):
        """Run the complete pipeline."""
        logger.info("=" * 80)
        logger.info("Starting Data Process Script Pipeline")
        logger.info("=" * 80)
        
        # Load input data
        strategies = self.load_input_data()
        self.stats["initial_count"] = len(strategies)
        
        # Step 1: Filter strategies
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Filter Strategies")
        logger.info("=" * 80)
        strategies, filter_metadata = filter_strategies(strategies)
        self.stats["filter"] = filter_metadata
        logger.info(f"After filtering: {len(strategies)} strategies")
        
        # Step 2: Language conversion (if enabled)
        if self.enable_language_convert:
            logger.info("\n" + "=" * 80)
            logger.info("Step 2: Language Conversion")
            logger.info("=" * 80)
            strategies, language_metadata = convert_language(strategies, max_workers=self.max_workers)
            self.stats["language_convert"] = language_metadata
            logger.info(f"After language conversion: {len(strategies)} strategies")
        
        # Step 3: Visualization removal (if enabled)
        if self.enable_vis_remove:
            logger.info("\n" + "=" * 80)
            step_num = 3 if self.enable_language_convert else 2
            logger.info(f"Step {step_num}: Visualization Removal")
            logger.info("=" * 80)
            strategies, vis_metadata = remove_visualization(strategies, use_llm=False)
            self.stats["vis_remove"] = vis_metadata
            logger.info(f"After visualization removal: {len(strategies)} strategies")
        
        # Step 4: Quality scoring and filtering (if enabled)
        if self.enable_quality_score:
            logger.info("\n" + "=" * 80)
            step_num = 2
            if self.enable_language_convert:
                step_num += 1
            if self.enable_vis_remove:
                step_num += 1
            logger.info(f"Step {step_num}: Quality Scoring and Filtering")
            logger.info("=" * 80)
            strategies, quality_metadata = score_and_filter(strategies, max_workers=self.max_workers)
            self.stats["quality_score"] = quality_metadata
            logger.info(f"After quality filtering: {len(strategies)} strategies")
        
        # Save results
        self.stats["final_count"] = len(strategies)
        self.stats["end_time"] = datetime.now().isoformat()
        
        logger.info("\n" + "=" * 80)
        logger.info("Saving Results")
        logger.info("=" * 80)
        output_file = self.save_output(strategies, self.stats)
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("Pipeline Summary")
        logger.info("=" * 80)
        logger.info(f"Initial strategies: {self.stats['initial_count']}")
        logger.info(f"Final strategies: {self.stats['final_count']}")
        logger.info(f"Retention rate: {self.stats['final_count']/self.stats['initial_count']*100:.1f}%")
        if 'quality_score' in self.stats:
            logger.info(f"Average quality score: {self.stats['quality_score'].get('average_score', 0):.2f}")
        logger.info(f"Output file: {output_file}")
        logger.info("=" * 80)
        
        return output_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Process trading strategy scripts for training')
    parser.add_argument('--input', type=str, default=INPUT_FILE,
                        help='Input JSON file with raw strategies')
    parser.add_argument('--output_dir', type=str, default=OUTPUT_DIR,
                        help='Output directory for processed data')
    parser.add_argument('--min_likes', type=int, default=MIN_LIKES_COUNT,
                        help='Minimum likes count for filtering')
    parser.add_argument('--quality_threshold', type=float, default=QUALITY_SCORE_THRESHOLD,
                        help='Minimum quality score threshold')
    parser.add_argument('--max_workers', type=int, default=MAX_WORKERS,
                        help='Maximum concurrent workers for LLM calls')
    parser.add_argument('--no_language_convert', action='store_true',
                        help='Disable language conversion')
    parser.add_argument('--no_vis_remove', action='store_true',
                        help='Disable visualization removal')
    parser.add_argument('--no_quality_score', action='store_true',
                        help='Disable quality scoring')
    
    args = parser.parse_args()
    
    # Update config with command line arguments
    if args.min_likes != MIN_LIKES_COUNT:
        import config
        config.MIN_LIKES_COUNT = args.min_likes
    
    if args.quality_threshold != QUALITY_SCORE_THRESHOLD:
        import config
        config.QUALITY_SCORE_THRESHOLD = args.quality_threshold
    
    # Create and run pipeline
    pipeline = DataProcessScript(
        input_file=args.input,
        output_dir=args.output_dir,
        enable_language_convert=not args.no_language_convert,
        enable_vis_remove=not args.no_vis_remove,
        enable_quality_score=not args.no_quality_score,
        max_workers=args.max_workers
    )
    
    try:
        pipeline.process()
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
