"""
Simple LLM-based Reward Function for Trading Indicators VERL Training

This module implements a simplified reward function that uses LLM evaluation
to judge content similarity and code correctness, making it more accessible
for the current model capabilities.
"""

import sys
import os
import pandas as pd
import ast
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import re

# Add the data_agent directory to path for imports
sys.path.append('/workspace/trading_indicators/preprocess/data_agent')

from llm_client import get_llm
from config import LOCAL_QWEN_ENDPOINT, LOCAL_QWEN_MODEL_NAME, LOCAL_QWEN_API_KEY


@dataclass
class PlainRewardConfig:
    """Configuration for plain LLM-based reward function."""
    
    # Weights for different components
    similarity_weight: float = 0.6
    code_correctness_weight: float = 0.4
    
    # Temperature and tokens for LLM evaluation
    llm_temperature: float = 0.3
    llm_max_tokens: int = 512
    
    # Similarity thresholds
    high_similarity_threshold: float = 0.8
    medium_similarity_threshold: float = 0.6
    low_similarity_threshold: float = 0.3


class PlainRewardFunction:
    """Simple LLM-based reward function for trading strategy evaluation."""
    
    def __init__(self, config: PlainRewardConfig = None, reference_data: pd.DataFrame = None):
        self.config = config or PlainRewardConfig()
        self.reference_data = reference_data
        
        # Initialize LLM client
        self.llm = get_llm(
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            endpoint=LOCAL_QWEN_ENDPOINT,
            model_name=LOCAL_QWEN_MODEL_NAME,
            api_key=LOCAL_QWEN_API_KEY
        )
        
        # Auto-load validation data if available and no reference data provided
        if reference_data is None:
            validation_file = "/workspace/trading_indicators/outputs/data_splits/val.parquet"
            if os.path.exists(validation_file):
                self.load_reference_data(validation_file)
        
        print(f"✓ Initialized PlainRewardFunction with LLM: {LOCAL_QWEN_MODEL_NAME}")
    
    def __call__(self, prompt: str, response: str, reference_data: Dict[str, Any] = None) -> float:
        """
        Calculate reward using LLM evaluation.
        
        Args:
            prompt: The input prompt
            response: The generated response
            reference_data: Optional reference data from validation set
            
        Returns:
            Float reward score between 0.0 and 1.0
        """
        try:
            # Component 1: Similarity evaluation
            similarity_score = self._evaluate_similarity(prompt, response, reference_data)
            
            # Component 2: Code correctness evaluation
            code_score = self._evaluate_code_correctness(response)
            
            # Combine scores
            final_score = (
                similarity_score * self.config.similarity_weight + 
                code_score * self.config.code_correctness_weight
            )
            
            return min(max(final_score, 0.0), 1.0)  # Clamp to [0, 1]
            
        except Exception as e:
            print(f"Warning: Error in reward calculation: {e}")
            return 0.1  # Return low but non-zero score on error
    
    def _evaluate_similarity(self, prompt: str, response: str, reference_data: Dict[str, Any] = None) -> float:
        """Evaluate similarity between generated response and reference data using LLM."""
        
        if not reference_data or not self.reference_data:
            # If no reference data available, use a simpler prompt relevance check
            return self._evaluate_prompt_relevance(prompt, response)
        
        # Find the most similar reference strategy
        reference_sample = self._find_best_reference(prompt, response)
        
        if not reference_sample:
            return self._evaluate_prompt_relevance(prompt, response)
        
        # Create evaluation prompt for LLM
        eval_prompt = f"""
Please evaluate the similarity between the generated trading strategy response and the reference strategy on a scale of 0-100.

Consider these aspects:
1. Strategy concept and approach
2. Technical implementation details  
3. Risk management elements
4. Overall coherence and completeness

PROMPT: {prompt}

GENERATED RESPONSE:
{response}

REFERENCE STRATEGY:
Name: {reference_sample.get('name', 'N/A')}
Description: {str(reference_sample.get('description', 'N/A'))[:500]}...
Code: {str(reference_sample.get('source_code', 'N/A'))[:300]}...

Please respond with ONLY a number between 0-100, where:
- 90-100: Extremely similar, almost identical approach
- 70-89: Very similar, same core concept with minor differences
- 50-69: Moderately similar, related approach but different implementation
- 30-49: Somewhat similar, some overlapping concepts
- 10-29: Minimally similar, different approaches
- 0-9: Not similar, completely different or irrelevant

Score:"""
        
        try:
            result = self.llm.invoke(eval_prompt)
            score_text = result.content.strip()
            
            # Extract numeric score
            score_match = re.search(r'\b(\d{1,3})\b', score_text)
            if score_match:
                score = float(score_match.group(1))
                return min(score / 100.0, 1.0)  # Convert to 0-1 scale
            else:
                print(f"Warning: Could not parse similarity score: {score_text}")
                return 0.5
                
        except Exception as e:
            print(f"Warning: LLM similarity evaluation failed: {e}")
            return 0.5
    
    def _evaluate_prompt_relevance(self, prompt: str, response: str) -> float:
        """Evaluate how well the response addresses the prompt."""
        
        eval_prompt = f"""
Please evaluate how well this response addresses the given prompt on a scale of 0-100.

Consider:
1. Does the response answer what was asked?
2. Is the response relevant to trading strategies?
3. Does it include the requested elements?
4. Is the response complete and coherent?

PROMPT: {prompt}

RESPONSE: {response}

Please respond with ONLY a number between 0-100.

Score:"""
        
        try:
            result = self.llm.invoke(eval_prompt)
            score_text = result.content.strip()
            
            score_match = re.search(r'\b(\d{1,3})\b', score_text)
            if score_match:
                score = float(score_match.group(1))
                return min(score / 100.0, 1.0)
            else:
                return 0.5
                
        except Exception as e:
            print(f"Warning: LLM relevance evaluation failed: {e}")
            return 0.5
    
    def _evaluate_code_correctness(self, response: str) -> float:
        """Evaluate code correctness using both syntax check and LLM evaluation."""
        
        # Extract code blocks
        code_blocks = re.findall(r'```(?:python)?\s*(.*?)```', response, re.DOTALL)
        
        if not code_blocks:
            # No code blocks found
            return 0.3
        
        # Check syntax of the main code block
        main_code = code_blocks[0].strip()
        syntax_score = self._check_syntax(main_code)
        
        # LLM evaluation of code quality
        llm_code_score = self._llm_evaluate_code(main_code)
        
        # Combine syntax and LLM scores
        return (syntax_score * 0.4 + llm_code_score * 0.6)
    
    def _check_syntax(self, code: str) -> float:
        """Check Python syntax correctness."""
        
        try:
            # Try to parse the code
            ast.parse(code)
            return 1.0  # Perfect syntax
        except SyntaxError as e:
            print(f"Syntax error in code: {e}")
            return 0.2  # Low score for syntax errors
        except Exception as e:
            print(f"Error parsing code: {e}")
            return 0.4  # Medium score for other parsing issues
    
    def _llm_evaluate_code(self, code: str) -> float:
        """Use LLM to evaluate code quality and correctness."""
        
        eval_prompt = f"""
Please evaluate this trading strategy code on a scale of 0-100.

Consider:
1. Code structure and organization
2. Trading logic correctness
3. Presence of entry/exit conditions
4. Risk management elements
5. Overall implementation quality

CODE:
{code}

Focus on whether this code could work as a trading strategy implementation.
Ignore minor syntax issues, focus on the trading logic.

Please respond with ONLY a number between 0-100.

Score:"""
        
        try:
            result = self.llm.invoke(eval_prompt)
            score_text = result.content.strip()
            
            score_match = re.search(r'\b(\d{1,3})\b', score_text)
            if score_match:
                score = float(score_match.group(1))
                return min(score / 100.0, 1.0)
            else:
                return 0.5
                
        except Exception as e:
            print(f"Warning: LLM code evaluation failed: {e}")
            return 0.5
    
    def _find_best_reference(self, prompt: str, response: str) -> Optional[Dict[str, Any]]:
        """Find the best matching reference strategy from validation data."""
        
        if self.reference_data is None or len(self.reference_data) == 0:
            return None
        
        # For simplicity, return a random reference sample
        # In a more sophisticated implementation, you could use embedding similarity
        import random
        sample_idx = random.randint(0, len(self.reference_data) - 1)
        return self.reference_data.iloc[sample_idx].to_dict()
    
    def load_reference_data(self, validation_file: str):
        """Load reference data from validation file."""
        try:
            self.reference_data = pd.read_parquet(validation_file)
            print(f"✓ Loaded {len(self.reference_data)} reference samples from {validation_file}")
        except Exception as e:
            print(f"Warning: Could not load reference data: {e}")
            self.reference_data = None


def create_plain_reward_function(config_dict: Dict[str, Any] = None, 
                                validation_file: str = None) -> PlainRewardFunction:
    """Factory function to create a plain reward function."""
    
    config = PlainRewardConfig(**config_dict) if config_dict else PlainRewardConfig()
    reward_fn = PlainRewardFunction(config)
    
    if validation_file:
        reward_fn.load_reference_data(validation_file)
    
    return reward_fn


# VERL-compatible function (following GSM8K pattern)
def compute_score(solution_str, ground_truth=None, **kwargs):
    """
    VERL-compatible reward computation function for trading strategies.
    
    Args:
        solution_str: The generated trading strategy response
        ground_truth: Optional ground truth (not used for unsupervised learning)
        **kwargs: Additional arguments
    
    Returns:
        Float score between 0.0 and 1.0
    """
    # Initialize reward function if not already done
    if not hasattr(compute_score, '_reward_fn'):
        compute_score._reward_fn = PlainRewardFunction()
    
    # For unsupervised learning, we evaluate the solution quality directly
    if isinstance(solution_str, str):
        # Single solution case
        dummy_prompt = "Create a trading strategy"  # Default prompt for standalone evaluation
        score = compute_score._reward_fn(dummy_prompt, solution_str)
        return float(score)
    
    # Batch processing case (if solution_str is a list)
    elif isinstance(solution_str, (list, tuple)):
        scores = []
        for response in solution_str:
            dummy_prompt = "Create a trading strategy"
            score = compute_score._reward_fn(dummy_prompt, response)
            scores.append(float(score))
        return scores
    
    else:
        # Fallback for unknown types
        return 0.5


# Example usage and testing
if __name__ == "__main__":
    print("Testing PlainRewardFunction...")
    
    # Test basic functionality
    reward_fn = create_plain_reward_function()
    
    # Sample test
    test_prompt = "Create a simple moving average crossover strategy"
    test_response = """
    Here's a moving average crossover strategy:
    
    ```python
    def ma_crossover_strategy(data, short_period=10, long_period=30):
        # Calculate moving averages
        ma_short = data['close'].rolling(window=short_period).mean()
        ma_long = data['close'].rolling(window=long_period).mean()
        
        # Generate signals
        buy_signal = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        sell_signal = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
        
        # Risk management
        stop_loss = 0.02  # 2% stop loss
        
        return buy_signal, sell_signal, stop_loss
    ```
    
    This strategy buys when the short MA crosses above the long MA and sells when it crosses below.
    It includes a 2% stop loss for risk management.
    """
    
    score = reward_fn(test_prompt, test_response)
    print(f"✓ Test completed. Reward Score: {score:.3f}")
    
    # Test with validation data if available
    validation_path = "/workspace/trading_indicators/outputs/data_splits/val.parquet"
    if os.path.exists(validation_path):
        print(f"Loading validation data from: {validation_path}")
        reward_fn.load_reference_data(validation_path)
        
        # Test with reference data
        score_with_ref = reward_fn(test_prompt, test_response)
        print(f"✓ Test with reference data. Score: {score_with_ref:.3f}")