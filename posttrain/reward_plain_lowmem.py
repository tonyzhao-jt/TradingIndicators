"""
Memory-Optimized Rule-Based Reward Function for Trading Indicators VERL Training

This module implements a lightweight reward function that uses rule-based evaluation
instead of large LLM models to avoid memory issues during training.
"""

import sys
import os
import pandas as pd
import ast
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import re
import numpy as np


@dataclass
class LowMemRewardConfig:
    """Configuration for memory-optimized reward function."""
    
    # Weights for different components
    code_quality_weight: float = 0.4
    length_quality_weight: float = 0.3
    keyword_relevance_weight: float = 0.3
    
    # Quality thresholds
    min_code_length: int = 50
    max_code_length: int = 2000
    optimal_length_min: int = 200
    optimal_length_max: int = 800
    
    # Trading-specific keywords for relevance scoring
    trading_keywords: list = None
    
    def __post_init__(self):
        if self.trading_keywords is None:
            self.trading_keywords = [
                # Technical indicators
                'sma', 'ema', 'rsi', 'macd', 'bollinger', 'stochastic', 'atr', 'adx',
                'momentum', 'williams', 'cci', 'roc', 'trix', 'aroon', 'vortex',
                # Trading concepts
                'buy', 'sell', 'signal', 'entry', 'exit', 'stop', 'profit', 'loss',
                'position', 'trade', 'strategy', 'backtest', 'portfolio', 'risk',
                'return', 'equity', 'drawdown', 'sharpe', 'volume', 'price',
                # Data structures
                'dataframe', 'close', 'open', 'high', 'low', 'volume', 'date',
                'pandas', 'numpy', 'bt', 'backtrader', 'zipline', 'pyfolio',
                # Programming constructs
                'def', 'class', 'import', 'return', 'if', 'for', 'while',
                'calculate', 'compute', 'analyze', 'indicator', 'signal'
            ]


class LowMemRewardFunction:
    """Memory-optimized rule-based reward function for trading strategy evaluation."""
    
    def __init__(self, config: LowMemRewardConfig = None, reference_data: pd.DataFrame = None):
        self.config = config or LowMemRewardConfig()
        self.reference_data = reference_data
        
        # Load validation data if available and no reference data provided
        if reference_data is None:
            validation_file = "/workspace/trading_indicators/outputs/data_splits/val.parquet"
            if os.path.exists(validation_file):
                self.load_reference_data(validation_file)
        
        print(f"✓ Initialized LowMemRewardFunction with rule-based evaluation")
    
    def load_reference_data(self, file_path: str):
        """Load reference data from parquet file."""
        try:
            self.reference_data = pd.read_parquet(file_path)
            print(f"✓ Loaded {len(self.reference_data)} reference samples from {file_path}")
        except Exception as e:
            print(f"Warning: Could not load reference data: {e}")
            self.reference_data = None
    
    def __call__(self, prompt: str, response: str, reference_data: Dict[str, Any] = None) -> float:
        """
        Calculate reward using rule-based evaluation.
        
        Args:
            prompt: The input prompt
            response: The generated response
            reference_data: Optional reference data from validation set
            
        Returns:
            Float reward score between 0.0 and 1.0
        """
        try:
            # Component 1: Code quality evaluation
            code_quality_score = self._evaluate_code_quality(response)
            
            # Component 2: Length quality evaluation
            length_score = self._evaluate_length_quality(response)
            
            # Component 3: Keyword relevance evaluation
            keyword_score = self._evaluate_keyword_relevance(prompt, response)
            
            # Combine scores
            final_score = (
                code_quality_score * self.config.code_quality_weight + 
                length_score * self.config.length_quality_weight +
                keyword_score * self.config.keyword_relevance_weight
            )
            
            return min(max(final_score, 0.0), 1.0)  # Clamp to [0, 1]
            
        except Exception as e:
            print(f"Warning: Error in reward calculation: {e}")
            return 0.1  # Return low but non-zero score on error
    
    def _evaluate_code_quality(self, response: str) -> float:
        """Evaluate code quality using rule-based heuristics."""
        
        score = 0.0
        max_score = 10.0
        
        # Check for Python syntax validity
        code_blocks = self._extract_code_blocks(response)
        
        if not code_blocks:
            return 0.1  # Very low score if no code found
        
        for code in code_blocks:
            # Basic syntax check
            if self._is_valid_python_syntax(code):
                score += 2.0
            
            # Check for imports
            if any(line.strip().startswith('import ') or line.strip().startswith('from ') 
                   for line in code.split('\n')):
                score += 1.0
            
            # Check for function definitions
            if 'def ' in code:
                score += 2.0
            
            # Check for class definitions
            if 'class ' in code:
                score += 1.5
            
            # Check for docstrings
            if '"""' in code or "'''" in code:
                score += 1.0
            
            # Check for comments
            if '#' in code:
                score += 0.5
            
            # Check for proper indentation patterns
            lines = [line for line in code.split('\n') if line.strip()]
            if lines and any(line.startswith('    ') or line.startswith('\t') for line in lines):
                score += 1.0
            
            # Bonus for trading-specific patterns
            trading_patterns = ['bt.', 'backtrader', 'strategy', 'indicator', 'signal']
            if any(pattern in code.lower() for pattern in trading_patterns):
                score += 1.0
        
        return min(score / max_score, 1.0)
    
    def _evaluate_length_quality(self, response: str) -> float:
        """Evaluate response length quality."""
        
        length = len(response)
        
        # Too short
        if length < self.config.min_code_length:
            return 0.1
        
        # Too long
        if length > self.config.max_code_length:
            return 0.3
        
        # Optimal length range
        if self.config.optimal_length_min <= length <= self.config.optimal_length_max:
            return 1.0
        
        # Linear decay outside optimal range
        if length < self.config.optimal_length_min:
            ratio = (length - self.config.min_code_length) / (self.config.optimal_length_min - self.config.min_code_length)
            return 0.1 + 0.9 * ratio
        else:
            ratio = (self.config.max_code_length - length) / (self.config.max_code_length - self.config.optimal_length_max)
            return 0.3 + 0.7 * ratio
    
    def _evaluate_keyword_relevance(self, prompt: str, response: str) -> float:
        """Evaluate keyword relevance using trading-specific terms."""
        
        combined_text = (prompt + " " + response).lower()
        
        # Count keyword occurrences
        keyword_count = 0
        unique_keywords = set()
        
        for keyword in self.config.trading_keywords:
            if keyword in combined_text:
                keyword_count += combined_text.count(keyword)
                unique_keywords.add(keyword)
        
        # Scoring based on unique keywords and total occurrences
        unique_score = min(len(unique_keywords) / 20.0, 1.0)  # Up to 20 unique keywords
        frequency_score = min(keyword_count / 50.0, 1.0)      # Up to 50 total occurrences
        
        return 0.7 * unique_score + 0.3 * frequency_score
    
    def _extract_code_blocks(self, text: str) -> list:
        """Extract code blocks from text (markdown format or plain code)."""
        
        code_blocks = []
        
        # Extract markdown code blocks
        pattern = r'```(?:python)?\s*(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        code_blocks.extend([match.strip() for match in matches])
        
        # If no markdown blocks, treat the entire response as potential code
        if not code_blocks:
            # Look for patterns that suggest code
            if any(pattern in text for pattern in ['def ', 'class ', 'import ', 'from ', 'bt.']):
                code_blocks.append(text.strip())
        
        return [block for block in code_blocks if len(block.strip()) > 10]
    
    def _is_valid_python_syntax(self, code: str) -> bool:
        """Check if code has valid Python syntax."""
        
        try:
            ast.parse(code)
            return True
        except (SyntaxError, ValueError):
            # Try to parse as expression
            try:
                ast.parse(code, mode='eval')
                return True
            except:
                return False


def compute_score(data_source: str = None, solution_str: str = None, ground_truth: str = None, 
                 extra_info: Dict[str, Any] = None, **kwargs) -> float:
    """
    Main entry point for VERL reward function.
    
    This function is called by the VERL framework during training with keyword arguments:
    - data_source: The source/prompt of the data
    - solution_str: The response/solution string  
    - ground_truth: The ground truth answer
    - extra_info: Additional information dictionary
    """
    
    # Initialize reward function (singleton pattern for efficiency)
    if not hasattr(compute_score, '_reward_function'):
        compute_score._reward_function = LowMemRewardFunction()
    
    # Use data_source as prompt and solution_str as response for compatibility
    prompt = data_source or ""
    response = solution_str or ""
    
    return compute_score._reward_function(prompt, response, extra_info)


if __name__ == "__main__":
    # Test the reward function
    test_prompt = "Create a simple RSI trading strategy using backtrader"
    test_response = '''
```python
import bt
import pandas as pd

class RSIStrategy(bt.Strategy):
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
    
    def next(self):
        if self.rsi < 30 and not self.position:
            self.buy()
        elif self.rsi > 70 and self.position:
            self.sell()
```
    '''
    
    reward = compute_score(test_prompt, test_response)
    print(f"Test reward score: {reward:.3f}")