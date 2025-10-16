"""
Convert trading strategy data to VERL-compatible format.

This script transforms the trading strategy dataset into the format expected by VERL,
creating proper prompt-response pairs with reward signals.
"""

import pandas as pd
import json
import argparse
from pathlib import Path
import sys
from typing import Dict, Any, List


def create_prompt_from_strategy(row: pd.Series) -> str:
    """Create a training prompt from strategy data."""
    
    # Parse the description if it's JSON
    try:
        desc_data = json.loads(row['description']) if isinstance(row['description'], str) else row['description']
        
        if isinstance(desc_data, dict):
            title = desc_data.get('title', row['name'])
            abstract = desc_data.get('abstract', '')
            key_concepts = desc_data.get('key_concepts', [])
        else:
            title = row['name']
            abstract = str(desc_data)
            key_concepts = []
    except (json.JSONDecodeError, TypeError):
        title = row['name']
        abstract = str(row['description'])
        key_concepts = []
    
    # Create a comprehensive prompt
    prompt_parts = [
        f"Create a trading strategy called '{title}'.",
    ]
    
    if abstract:
        prompt_parts.append(f"Strategy description: {abstract}")
    
    if key_concepts:
        concepts_str = ", ".join(key_concepts[:5])  # Limit to first 5 concepts
        prompt_parts.append(f"Focus on these key concepts: {concepts_str}")
    
    # Add requirements based on relevant symbols
    if pd.notna(row['relevant_symbols']):
        symbols = str(row['relevant_symbols'])
        prompt_parts.append(f"The strategy should work with these instruments: {symbols}")
    
    prompt_parts.extend([
        "Include the following in your response:",
        "1. Clear entry and exit conditions",
        "2. Risk management rules",  
        "3. Complete implementation code",
        "4. Explanation of the strategy logic",
        "5. Key parameters and their rationale"
    ])
    
    return " ".join(prompt_parts)


def create_response_from_strategy(row: pd.Series) -> str:
    """Create a training response from strategy data."""
    
    response_parts = []
    
    # Add strategy name and description
    response_parts.append(f"# {row['name']}\n")
    
    # Parse and add description content
    try:
        desc_data = json.loads(row['description']) if isinstance(row['description'], str) else row['description']
        
        if isinstance(desc_data, dict):
            if 'abstract' in desc_data:
                response_parts.append(f"## Strategy Overview\n{desc_data['abstract']}\n")
            
            if 'key_concepts' in desc_data:
                concepts = desc_data['key_concepts']
                if concepts:
                    response_parts.append("## Key Concepts")
                    for concept in concepts:
                        response_parts.append(f"- {concept}")
                    response_parts.append("")
            
            if 'mathematical_models' in desc_data:
                models = desc_data['mathematical_models']
                if models:
                    response_parts.append("## Mathematical Models")
                    for model in models:
                        response_parts.append(f"- {model}")
                    response_parts.append("")
                        
    except (json.JSONDecodeError, TypeError):
        response_parts.append(f"## Description\n{row['description']}\n")
    
    # Add reasoning if available
    if pd.notna(row['reasoning']):
        response_parts.append(f"## Strategy Logic\n{row['reasoning']}\n")
    
    # Add source code
    if pd.notna(row['source_code']):
        response_parts.append("## Implementation\n")
        response_parts.append("```python")
        response_parts.append(str(row['source_code']))
        response_parts.append("```\n")
    
    # Add relevant symbols
    if pd.notna(row['relevant_symbols']):
        response_parts.append(f"## Applicable Instruments\n{row['relevant_symbols']}\n")
    
    return "\n".join(response_parts)


def calculate_reward_score(row: pd.Series) -> float:
    """Calculate a reward score based on data completeness and quality."""
    
    score = 0.0
    
    # Base score for having required fields
    if pd.notna(row['name']):
        score += 0.1
    if pd.notna(row['description']):
        score += 0.2
    if pd.notna(row['source_code']):
        score += 0.3
    if pd.notna(row['reasoning']):
        score += 0.2
    
    # Bonus for rich description
    try:
        desc_data = json.loads(row['description']) if isinstance(row['description'], str) else {}
        if isinstance(desc_data, dict):
            if 'key_concepts' in desc_data and desc_data['key_concepts']:
                score += 0.1
            if 'mathematical_models' in desc_data and desc_data['mathematical_models']:
                score += 0.1
            if 'evaluation_metrics' in desc_data and desc_data['evaluation_metrics']:
                score += 0.1
    except:
        pass
    
    # Quality indicators in source code
    if pd.notna(row['source_code']):
        source_code = str(row['source_code']).lower()
        
        # Check for important strategy elements
        if 'stop' in source_code and 'loss' in source_code:
            score += 0.05
        if 'entry' in source_code or 'buy' in source_code:
            score += 0.05
        if 'exit' in source_code or 'sell' in source_code:
            score += 0.05
        if 'risk' in source_code:
            score += 0.05
        
        # Check for proper structure
        if 'def ' in source_code or 'class ' in source_code:
            score += 0.1
        if 'import' in source_code:
            score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0


def convert_to_verl_format(input_file: str, output_file: str, split_ratio: float = 0.8) -> None:
    """Convert trading strategy data to VERL format."""
    
    print(f"Loading data from: {input_file}")
    df = pd.read_parquet(input_file)
    
    print(f"Original data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Convert each row to VERL format
    verl_data = []
    
    for idx, row in df.iterrows():
        try:
            prompt = create_prompt_from_strategy(row)
            response = create_response_from_strategy(row)
            reward = calculate_reward_score(row)
            
            # Create VERL format following GSM8K pattern
            verl_row = {
                "data_source": "trading_strategies",
                "prompt": [{"role": "user", "content": prompt}],
                "ability": "trading_strategy_generation", 
                "reward_model": {
                    "style": "llm_based",
                    "ground_truth": response  # Use expected response as ground truth
                },
                "extra_info": {
                    'strategy_id': str(row.get('id', idx)),
                    'strategy_name': str(row.get('name', f'strategy_{idx}')),
                    'created_at': str(row.get('created_at', '')),
                    'reward_score': reward
                }
            }
            
            verl_data.append(verl_row)
            
        except Exception as e:
            print(f"Warning: Error processing row {idx}: {e}")
            continue
    
    # Create DataFrame
    verl_df = pd.DataFrame(verl_data)
    
    print(f"Converted data shape: {verl_df.shape}")
    
    # Save the converted data
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    verl_df.to_parquet(output_path, index=False)
    print(f"Saved VERL-formatted data to: {output_path}")
    
    # Show sample
    print("\nSample converted data:")
    sample = verl_df.iloc[0]
    print(f"Data source: {sample['data_source']}")
    print(f"Ability: {sample['ability']}")
    prompt_content = sample['prompt'][0]['content'] if sample['prompt'] else "N/A"
    print(f"Prompt (first 200 chars): {prompt_content[:200]}...")
    ground_truth = sample['reward_model']['ground_truth']
    print(f"Ground truth (first 200 chars): {ground_truth[:200]}...")
    print(f"Reward model style: {sample['reward_model']['style']}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert trading strategy data to VERL format"
    )
    
    parser.add_argument('input_file',
                       help='Input parquet file with trading strategy data')
    parser.add_argument('--output', '-o',
                       default='verl_formatted_data.parquet',
                       help='Output parquet file (default: verl_formatted_data.parquet)')
    
    args = parser.parse_args()
    
    try:
        convert_to_verl_format(args.input_file, args.output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())