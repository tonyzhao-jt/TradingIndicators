"""
Data Formatter Classes for Training Data Preparation

This module contains different formatting strategies for preparing training data
from input-output pairs for fine-tuning language models.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import json


class BaseFormatter(ABC):
    """Abstract base class for data formatters."""
    
    @abstractmethod
    def format_instruction(self, sample: Dict[str, Any]) -> str:
        """
        Format a single sample into the desired training format.
        
        Args:
            sample: Dictionary containing 'input' and 'output' keys
            
        Returns:
            Formatted string ready for training
        """
        pass
    
    def format_dataset(self, data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Format entire dataset into training format.
        
        Args:
            data: List of dictionaries with 'input' and 'output' keys
            
        Returns:
            List of dictionaries with 'text' key containing formatted data
        """
        return [{"text": self.format_instruction(item)} for item in data]
    
    def validate_sample(self, sample: Dict[str, Any]) -> bool:
        """
        Validate that sample has required keys.
        
        Args:
            sample: Sample to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ['input', 'output']
        return all(key in sample for key in required_keys)


class InstructionFormatter(BaseFormatter):
    """
    Formatter for instruction-following format.
    Creates structured prompts with instruction, description, and code sections.
    """
    
    def __init__(self, 
                 instruction_text: str = "Generate Pine Script v6 code based on the following trading strategy description.",
                 description_header: str = "Description:",
                 code_header: str = "Code:"):
        """
        Initialize the instruction formatter.
        
        Args:
            instruction_text: The main instruction text
            description_header: Header for the input description
            code_header: Header for the output code
        """
        self.instruction_text = instruction_text
        self.description_header = description_header
        self.code_header = code_header
    
    def format_instruction(self, sample: Dict[str, Any]) -> str:
        """Format sample using instruction template."""
        if not self.validate_sample(sample):
            raise ValueError("Sample must contain 'input' and 'output' keys")
        
        return f"""### Instruction:
{self.instruction_text}

### {self.description_header}
{sample['input']}

### {self.code_header}
{sample['output']}"""


class ConversationFormatter(BaseFormatter):
    """
    Formatter for conversation-style format.
    Creates a more natural conversation flow between user and assistant.
    """
    
    def __init__(self, 
                 user_prefix: str = "Human:",
                 assistant_prefix: str = "Assistant:",
                 system_message: str = "You are a helpful assistant that generates Pine Script code for trading strategies."):
        """
        Initialize the conversation formatter.
        
        Args:
            user_prefix: Prefix for user messages
            assistant_prefix: Prefix for assistant messages
            system_message: System message to set context
        """
        self.user_prefix = user_prefix
        self.assistant_prefix = assistant_prefix
        self.system_message = system_message
    
    def format_instruction(self, sample: Dict[str, Any]) -> str:
        """Format sample using conversation template."""
        if not self.validate_sample(sample):
            raise ValueError("Sample must contain 'input' and 'output' keys")
        
        return f"""System: {self.system_message}

{self.user_prefix} {sample['input']}

{self.assistant_prefix} {sample['output']}"""


class ChatMLFormatter(BaseFormatter):
    """
    Formatter for ChatML format.
    Uses the ChatML (Chat Markup Language) format for structured conversations.
    """
    
    def __init__(self, system_message: str = "You are a helpful assistant that generates Pine Script code for trading strategies."):
        """
        Initialize the ChatML formatter.
        
        Args:
            system_message: System message to set context
        """
        self.system_message = system_message
    
    def format_instruction(self, sample: Dict[str, Any]) -> str:
        """Format sample using ChatML template."""
        if not self.validate_sample(sample):
            raise ValueError("Sample must contain 'input' and 'output' keys")
        
        return f"""<|im_start|>system
{self.system_message}<|im_end|>
<|im_start|>user
{sample['input']}<|im_end|>
<|im_start|>assistant
{sample['output']}<|im_end|>"""


class AlpacaFormatter(BaseFormatter):
    """
    Formatter for Alpaca instruction format.
    Follows the Stanford Alpaca instruction format.
    """
    
    def format_instruction(self, sample: Dict[str, Any]) -> str:
        """Format sample using Alpaca template."""
        if not self.validate_sample(sample):
            raise ValueError("Sample must contain 'input' and 'output' keys")
        
        return f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
Generate Pine Script v6 code for the given trading strategy description.

### Input:
{sample['input']}

### Response:
{sample['output']}"""


class SimpleFormatter(BaseFormatter):
    """
    Simple formatter that just concatenates input and output.
    Useful for straightforward completion tasks.
    """
    
    def __init__(self, separator: str = "\n\n"):
        """
        Initialize the simple formatter.
        
        Args:
            separator: String to separate input and output
        """
        self.separator = separator
    
    def format_instruction(self, sample: Dict[str, Any]) -> str:
        """Format sample using simple concatenation."""
        if not self.validate_sample(sample):
            raise ValueError("Sample must contain 'input' and 'output' keys")
        
        return f"{sample['input']}{self.separator}{sample['output']}"


class FormatterFactory:
    """Factory class to create formatters by name."""
    
    _formatters = {
        "instruction": InstructionFormatter,
        "conversation": ConversationFormatter,
        "chatml": ChatMLFormatter,
        "alpaca": AlpacaFormatter,
        "simple": SimpleFormatter
    }
    
    @classmethod
    def create_formatter(cls, formatter_type: str, **kwargs) -> BaseFormatter:
        """
        Create a formatter instance by type.
        
        Args:
            formatter_type: Type of formatter to create
            **kwargs: Additional arguments for formatter initialization
            
        Returns:
            Formatter instance
            
        Raises:
            ValueError: If formatter type is not recognized
        """
        if formatter_type not in cls._formatters:
            available = ', '.join(cls._formatters.keys())
            raise ValueError(f"Unknown formatter type: {formatter_type}. Available: {available}")
        
        return cls._formatters[formatter_type](**kwargs)
    
    @classmethod
    def list_formatters(cls) -> List[str]:
        """Get list of available formatter types."""
        return list(cls._formatters.keys())


def load_and_format_data(data_path: str, 
                        formatter_type: str = "instruction", 
                        **formatter_kwargs) -> List[Dict[str, str]]:
    """
    Convenience function to load and format data in one step.
    
    Args:
        data_path: Path to JSON file containing the data
        formatter_type: Type of formatter to use
        **formatter_kwargs: Additional arguments for formatter
        
    Returns:
        List of formatted training samples
    """
    # Load data
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create formatter and format data
    formatter = FormatterFactory.create_formatter(formatter_type, **formatter_kwargs)
    return formatter.format_dataset(data)


def print_sample_formats(sample_data: Dict[str, Any]):
    """
    Print sample output for all formatter types.
    Useful for comparing different formats.
    
    Args:
        sample_data: Sample with 'input' and 'output' keys
    """
    print("="*80)
    print("FORMATTER COMPARISON")
    print("="*80)
    
    for formatter_name in FormatterFactory.list_formatters():
        formatter = FormatterFactory.create_formatter(formatter_name)
        formatted = formatter.format_instruction(sample_data)
        
        print(f"\n{formatter_name.upper()} FORMAT:")
        print("-" * 40)
        print(formatted)
        print()


if __name__ == "__main__":
    # Example usage
    sample = {
        "input": "Create a simple moving average crossover strategy",
        "output": "@version=5\nstrategy(\"MA Cross\", overlay=true)\nfast = ta.sma(close, 10)\nslow = ta.sma(close, 20)\nif ta.crossover(fast, slow)\n    strategy.entry(\"Long\", strategy.long)"
    }
    
    print_sample_formats(sample)