#!/usr/bin/env python3
"""
Data SFT - 生成包含Chain-of-Thought的instruction训练数据

Pipeline:
1. COT Generation Node: 基于input/output生成包含推理过程的instruction

输入格式: [{"input": "description", "output": "code"}, ...]
输出格式: [{"instruction": "question", "output": "COT reasoning + code"}, ...]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from nodes.cot_generation_node import COTGenerationNode


class DataSFT:
    def __init__(self, input_file=None, output_dir=None):
        self.input_file = input_file
        self.output_dir = output_dir or "outputs"
        
        # Initialize nodes
        self.cot_node = COTGenerationNode()
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process(self):
        """Run the complete pipeline"""
        print("Starting Data SFT Pipeline...")
        print("Generating Chain-of-Thought instruction data...")
        
        # Load input data
        print(f"Loading data from: {self.input_file}")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        print(f"Loaded {len(input_data)} segment samples")
        
        # Step 1: Generate COT instructions
        print("\n=== Step 1: COT Generation ===")
        instruction_data = self.cot_node.process(input_data)
        print(f"Generated {len(instruction_data)} instruction samples")
        
        # Save final results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"sft_instructions_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(instruction_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nPipeline completed! Results saved to: {output_file}")
        print(f"Final output: {len(instruction_data)} SFT instruction samples")
        
        return instruction_data


def main():
    parser = argparse.ArgumentParser(description='Generate SFT instruction data from segment samples')
    parser.add_argument('--input', required=True, help='Input JSON file with segment samples')
    parser.add_argument('--output_dir', default='outputs', help='Output directory')
    
    args = parser.parse_args()
    
    processor = DataSFT(
        input_file=args.input,
        output_dir=args.output_dir
    )
    
    processor.process()


if __name__ == "__main__":
    main()