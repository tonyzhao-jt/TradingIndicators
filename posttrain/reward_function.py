"""
Custom Reward Function for Trading Indicators VERL Training

This module implements a custom reward function that evaluates the quality of 
trading strategy code generation and reasoning based on multiple criteria.
"""

import torch
import numpy as np
import re
from typing import List, Dict, Any, Union
from dataclasses import dataclass


@dataclass 
class TradingStrategyReward:
    """Configuration for trading strategy reward calculation."""
    
    # Weights for different reward components
    code_quality_weight: float = 0.3
    reasoning_quality_weight: float = 0.25
    completeness_weight: float = 0.2
    technical_accuracy_weight: float = 0.15
    innovation_weight: float = 0.1
    
    # Bonus/penalty factors
    syntax_error_penalty: float = -0.5
    incomplete_strategy_penalty: float = -0.3
    good_documentation_bonus: float = 0.2
    risk_management_bonus: float = 0.15


class TradingIndicatorRewardFunction:
    """Custom reward function for trading indicator/strategy generation."""
    
    def __init__(self, config: TradingStrategyReward = None):
        self.config = config or TradingStrategyReward()
        
        # Key indicators for good trading strategies
        self.required_elements = {
            'entry_conditions': ['entry', 'buy', 'long', 'signal'],
            'exit_conditions': ['exit', 'sell', 'short', 'close'],
            'risk_management': ['stop', 'loss', 'risk', 'drawdown', 'position_size'],
            'indicators': ['sma', 'ema', 'rsi', 'macd', 'bollinger', 'vix', 'atr'],
            'backtesting': ['backtest', 'performance', 'sharpe', 'returns'],
        }
        
        # Technical accuracy keywords
        self.technical_keywords = [
            'algorithm', 'strategy', 'indicator', 'signal', 'portfolio',
            'volatility', 'momentum', 'trend', 'support', 'resistance',
            'timeframe', 'market', 'price', 'volume'
        ]
        
    def __call__(self, 
                 prompt: str, 
                 response: str, 
                 reference_data: Dict[str, Any] = None) -> float:
        """
        Calculate reward for a trading strategy generation response.
        
        Args:
            prompt: The input prompt/question
            response: The generated response (strategy code/description)  
            reference_data: Optional reference data from the dataset
            
        Returns:
            Float reward score between -1.0 and 1.0
        """
        total_reward = 0.0
        
        # 1. Code Quality Assessment
        code_quality = self._assess_code_quality(response)
        total_reward += code_quality * self.config.code_quality_weight
        
        # 2. Reasoning Quality
        reasoning_quality = self._assess_reasoning_quality(response, prompt)
        total_reward += reasoning_quality * self.config.reasoning_quality_weight
        
        # 3. Completeness Check
        completeness = self._assess_completeness(response)
        total_reward += completeness * self.config.completeness_weight
        
        # 4. Technical Accuracy
        technical_accuracy = self._assess_technical_accuracy(response)
        total_reward += technical_accuracy * self.config.technical_accuracy_weight
        
        # 5. Innovation/Novelty
        innovation = self._assess_innovation(response)
        total_reward += innovation * self.config.innovation_weight
        
        # Apply bonuses and penalties
        total_reward += self._calculate_bonuses_penalties(response)
        
        # Normalize to [-1, 1] range
        return np.clip(total_reward, -1.0, 1.0)
    
    def _assess_code_quality(self, response: str) -> float:
        """Assess the quality of generated code."""
        score = 0.0
        
        # Check for code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', response)
        if len(code_blocks) > 0:
            score += 0.3
            
        # Check for proper function definitions
        if re.search(r'def \w+\(', response) or re.search(r'class \w+', response):
            score += 0.2
            
        # Check for comments and documentation
        comment_patterns = [r'#.*', r'"""[\s\S]*?"""', r"'''[\s\S]*?'''"]
        has_comments = any(re.search(pattern, response) for pattern in comment_patterns)
        if has_comments:
            score += 0.2
            
        # Check for proper variable naming
        if re.search(r'\b[a-z_][a-z0-9_]*\b', response):
            score += 0.1
            
        # Penalty for obvious syntax errors
        if self._has_syntax_errors(response):
            score += self.config.syntax_error_penalty
            
        return score
    
    def _assess_reasoning_quality(self, response: str, prompt: str) -> float:
        """Assess the quality of reasoning and explanation."""
        score = 0.0
        
        # Check for logical structure
        logical_words = ['because', 'therefore', 'since', 'as a result', 'consequently']
        logical_count = sum(1 for word in logical_words if word.lower() in response.lower())
        score += min(logical_count * 0.1, 0.3)
        
        # Check for strategy explanation
        explanation_words = ['strategy', 'approach', 'method', 'technique', 'algorithm']
        explanation_count = sum(1 for word in explanation_words if word.lower() in response.lower())
        score += min(explanation_count * 0.05, 0.2)
        
        # Check for addressing the prompt
        prompt_keywords = re.findall(r'\b\w+\b', prompt.lower())
        response_lower = response.lower()
        addressed_keywords = sum(1 for keyword in prompt_keywords if keyword in response_lower)
        if len(prompt_keywords) > 0:
            score += (addressed_keywords / len(prompt_keywords)) * 0.3
            
        return score
    
    def _assess_completeness(self, response: str) -> float:
        """Assess if the response covers all necessary components."""
        score = 0.0
        response_lower = response.lower()
        
        for component, keywords in self.required_elements.items():
            if any(keyword in response_lower for keyword in keywords):
                score += 0.2  # Each component worth 0.2
                
        # Check for comprehensive coverage
        if score >= 0.8:  # Most components covered
            score += 0.2
            
        return score
    
    def _assess_technical_accuracy(self, response: str) -> float:
        """Assess technical accuracy and use of proper terminology."""
        score = 0.0
        response_lower = response.lower()
        
        # Count technical keywords
        tech_count = sum(1 for keyword in self.technical_keywords 
                        if keyword in response_lower)
        score += min(tech_count * 0.05, 0.4)
        
        # Check for mathematical formulas or calculations
        math_patterns = [r'\d+\s*[+\-*/]\s*\d+', r'[a-zA-Z]\s*[+\-*/=]\s*[a-zA-Z0-9]']
        has_math = any(re.search(pattern, response) for pattern in math_patterns)
        if has_math:
            score += 0.2
            
        # Check for proper financial terminology
        financial_terms = ['profit', 'loss', 'return', 'volatility', 'sharpe', 'drawdown']
        financial_count = sum(1 for term in financial_terms if term in response_lower)
        score += min(financial_count * 0.05, 0.2)
        
        return score
    
    def _assess_innovation(self, response: str) -> float:
        """Assess innovation and creativity in the approach."""
        score = 0.0
        response_lower = response.lower()
        
        # Look for novel combinations or approaches
        innovative_words = ['novel', 'innovative', 'unique', 'creative', 'advanced', 'hybrid']
        innovation_count = sum(1 for word in innovative_words if word in response_lower)
        score += min(innovation_count * 0.1, 0.3)
        
        # Check for multiple strategy combinations
        if 'combine' in response_lower or 'hybrid' in response_lower:
            score += 0.2
            
        # Check for custom indicators or modifications
        if 'custom' in response_lower or 'modified' in response_lower:
            score += 0.2
            
        return score
    
    def _calculate_bonuses_penalties(self, response: str) -> float:
        """Calculate additional bonuses and penalties."""
        bonus = 0.0
        response_lower = response.lower()
        
        # Risk management bonus
        risk_keywords = ['risk', 'stop loss', 'position size', 'drawdown']
        if any(keyword in response_lower for keyword in risk_keywords):
            bonus += self.config.risk_management_bonus
            
        # Good documentation bonus
        if len(re.findall(r'"""[\s\S]*?"""', response)) > 0:
            bonus += self.config.good_documentation_bonus
            
        # Incomplete strategy penalty
        if len(response) < 50 or 'incomplete' in response_lower:
            bonus += self.config.incomplete_strategy_penalty
            
        return bonus
    
    def _has_syntax_errors(self, response: str) -> bool:
        """Basic check for obvious syntax errors."""
        # Check for unmatched brackets/parentheses
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for char in response:
            if char in brackets:
                stack.append(brackets[char])
            elif char in brackets.values():
                if not stack or stack.pop() != char:
                    return True
                    
        return len(stack) > 0


def create_reward_function(config_dict: Dict[str, Any] = None) -> TradingIndicatorRewardFunction:
    """Factory function to create a reward function with custom configuration."""
    config = TradingStrategyReward(**config_dict) if config_dict else TradingStrategyReward()
    return TradingIndicatorRewardFunction(config)


# Example usage and testing
if __name__ == "__main__":
    # Test the reward function
    reward_fn = create_reward_function()
    
    # Sample prompt and response
    sample_prompt = "Create a trading strategy using RSI and moving averages"
    sample_response = """
    Here's a trading strategy that combines RSI and moving averages:
    
    ```python
    def rsi_ma_strategy(data):
        # Calculate RSI and moving averages
        rsi = calculate_rsi(data, period=14)
        ma_short = data.rolling(20).mean()
        ma_long = data.rolling(50).mean()
        
        # Entry conditions
        buy_signal = (rsi < 30) and (ma_short > ma_long)
        
        # Exit conditions  
        sell_signal = (rsi > 70) or (ma_short < ma_long)
        
        # Risk management
        stop_loss = 0.02  # 2% stop loss
        
        return buy_signal, sell_signal, stop_loss
    ```
    
    This strategy uses RSI oversold conditions combined with bullish moving average crossover
    to generate buy signals. It includes proper risk management with stop losses.
    """
    
    score = reward_fn(sample_prompt, sample_response)
    print(f"Reward Score: {score:.3f}")