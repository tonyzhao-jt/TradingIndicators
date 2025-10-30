#!/usr/bin/env python3
"""
Data Process Segments - 处理restructured_data生成segment-wise的训练样本

Pipeline:
1. Pack: 提取restructured_data下的key，得到多条segment wise的数据 (description -> code) sample
2. Filter: 去掉small code/no code snippets，并保证同一数据生成的多组数据不产生重复sample
3. Quality Score: 用LLM对description -> code进行打分，保留分数高的segment samples

输出格式: [{"input": "description", "output": "code"}, ...]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from nodes.pack_node import PackNode
from nodes.filter_node import FilterNode
from nodes.quality_score_node import QualityScoreNode


class DataProcessSegments:
    def __init__(self, input_file=None, output_dir=None):
        self.input_file = input_file
        self.output_dir = output_dir or "outputs"
        
        # Initialize nodes
        self.pack_node = PackNode()
        self.filter_node = FilterNode()
        self.quality_score_node = QualityScoreNode()
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process(self):
        """Run the complete pipeline"""
        print("Starting Data Process Segments Pipeline...")
        
        # Load input data
        print(f"Loading data from: {self.input_file}")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        print(f"Loaded {len(input_data)} items")
        
        # Step 1: Pack segments
        print("\n=== Step 1: Pack Segments ===")
        segments = self.pack_node.process(input_data)
        print(f"Generated {len(segments)} segments")
        
        # Step 2: Filter segments
        print("\n=== Step 2: Filter Segments ===")
        filtered_segments = self.filter_node.process(segments)
        print(f"After filtering: {len(filtered_segments)} segments")
        
        # Step 3: Quality scoring
        print("\n=== Step 3: Quality Scoring ===")
        scored_segments = self.quality_score_node.process(filtered_segments)
        print(f"After quality scoring: {len(scored_segments)} segments")
        
        # Save final results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"segment_samples_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(scored_segments, f, ensure_ascii=False, indent=2)
        
        print(f"\nPipeline completed! Results saved to: {output_file}")
        print(f"Final output: {len(scored_segments)} high-quality segment samples")
        
        return scored_segments


def main():
    parser = argparse.ArgumentParser(description='Process restructured data into segment-wise samples')
    parser.add_argument('--input', required=True, help='Input JSON file with restructured_data')
    parser.add_argument('--output_dir', default='outputs', help='Output directory')
    
    args = parser.parse_args()
    
    processor = DataProcessSegments(
        input_file=args.input,
        output_dir=args.output_dir
    )
    
    processor.process()


if __name__ == "__main__":
    main()