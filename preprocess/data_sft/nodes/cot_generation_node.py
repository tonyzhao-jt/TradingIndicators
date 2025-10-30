"""
COT Generation Node - 使用LLM生成包含Chain-of-Thought推理的instruction数据
"""

import json
import time
import os
import re
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class COTGenerationNode:
    def __init__(self):
        self.name = "cot_generation_node"
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = 1
    
    def process(self, segments: List[Dict]) -> List[Dict]:
        """Process segments and generate COT instructions"""
        print(f"COTGenerationNode: Processing {len(segments)} segments")
        
        instruction_data = []
        
        for i, segment in enumerate(segments):
            if i % 5 == 0:
                print(f"Processing segment {i+1}/{len(segments)}")
            
            try:
                instruction_sample = self.generate_cot_instruction(segment)
                if instruction_sample:
                    instruction_data.append(instruction_sample)
                    
            except Exception as e:
                print(f"Error generating COT for segment {i}: {e}")
                continue
        
        print(f"COTGenerationNode: Generated {len(instruction_data)} instruction samples")
        return instruction_data
    
    def generate_cot_instruction(self, segment: Dict) -> Dict:
        """Generate a COT instruction from a segment"""
        description = segment['input']
        code = segment['output']
        
        # Try to use LLM for COT generation
        use_llm = os.getenv("USE_LLM_COT", "true").lower() == "true"
        
        if use_llm:
            try:
                instruction, cot_response = self.call_llm_for_cot(description, code)
                return {
                    "instruction": instruction,
                    "output": cot_response
                }
            except Exception as e:
                print(f"LLM COT generation failed, using template: {e}")
        
        # Fall back to template-based COT generation
        return self.template_cot_generation(description, code)
    
    def call_llm_for_cot(self, description: str, code: str) -> tuple:
        """Call LLM to generate COT instruction and response"""
        try:
            from langchain_openai import ChatOpenAI
            
            # Get configuration
            endpoint = os.getenv("LOCAL_QWEN_ENDPOINT", "http://202.45.128.234:5788/v1/")
            model_name = os.getenv("LOCAL_QWEN_MODEL_NAME", "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct")
            api_key = os.getenv("LOCAL_QWEN_API_KEY", "none")
            
            # Create LLM client
            llm = ChatOpenAI(
                base_url=endpoint,
                model=model_name,
                api_key=api_key,
                temperature=0.2,
                max_tokens=800
            )
            
            # Create COT generation prompt
            prompt = self.create_cot_prompt(description, code)
            
            # Call LLM
            response = llm.invoke(prompt)
            response_text = response.content.strip()
            
            # Parse the response to extract instruction and COT response
            instruction, cot_response = self.parse_llm_response(response_text, description, code)
            
            return instruction, cot_response
                
        except Exception as e:
            raise Exception(f"LLM API call failed: {e}")
    
    def create_cot_prompt(self, description: str, code: str) -> str:
        """Create prompt for LLM COT generation"""
        prompt = f"""You are a professional Pine Script programming instructor. Based on the given strategy description and corresponding Pine Script code, generate a student question and a response with detailed thinking process.

Strategy Description: {description}

Target Pine Script Code: {code}

Generate:
1. A direct instruction asking to implement the described strategy (use format "Implement a Pine Script code for [strategy description]")
2. A response with structured thinking process in <think></think> tags, followed by the final code in <answer></answer> tags

Format Requirements:
INSTRUCTION: [Direct instruction: "Implement a Pine Script code for [strategy description]"]

OUTPUT: <think>
[Detailed step-by-step analysis and reasoning process including:
- Strategy requirement analysis
- Implementation approach breakdown  
- Pine Script syntax considerations
- Code structure planning]
</think>
<answer>
[Final Pine Script code implementation]
</answer>

Example Format:
INSTRUCTION: Implement a Pine Script code for moving average crossover strategy.

OUTPUT: <think>
1. **Strategy Analysis**: The moving average crossover strategy requires two moving averages - a fast (shorter period) and slow (longer period) moving average. The core logic is to generate buy signals when the fast MA crosses above the slow MA, and sell signals when it crosses below.

2. **Implementation Requirements**: I need to calculate two SMAs with different periods, detect crossover events, and create boolean signals for entry/exit conditions.

3. **Pine Script Functions**: I'll use ta.sma() for calculating simple moving averages, ta.crossover() to detect when one series crosses above another, and ta.crossunder() for the opposite direction.

4. **Code Structure**: First calculate the moving averages, then use crossover functions to generate the trading signals.
</think>
<answer>
fast_ma = ta.sma(close, 10)
slow_ma = ta.sma(close, 20)
buy_signal = ta.crossover(fast_ma, slow_ma)
sell_signal = ta.crossunder(fast_ma, slow_ma)
</answer>

Now generate a similar educational Q&A pair for the given strategy:"""
        
        return prompt
    
    def parse_llm_response(self, response_text: str, description: str, code: str) -> tuple:
        """Parse LLM response to extract instruction and COT response"""
        try:
            # Look for INSTRUCTION: and OUTPUT: markers
            if "INSTRUCTION:" in response_text and "OUTPUT:" in response_text:
                parts = response_text.split("OUTPUT:")
                instruction_part = parts[0].replace("INSTRUCTION:", "").strip()
                output_part = parts[1].strip()
                
                # Validate that output part has the correct <think> and <answer> structure
                if "<think>" in output_part and "</think>" in output_part and "<answer>" in output_part and "</answer>" in output_part:
                    return instruction_part, output_part
                else:
                    # If structure is wrong, reformat it
                    return instruction_part, self.reformat_to_think_answer(output_part, description, code)
            else:
                # If no markers found, generate a simple instruction and reformat response
                instruction = self.generate_simple_instruction(description)
                formatted_output = self.reformat_to_think_answer(response_text, description, code)
                return instruction, formatted_output
                
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # Fall back to template generation
            template_result = self.template_cot_generation(description, code)
            return template_result["instruction"], template_result["output"]
    
    def generate_simple_instruction(self, description: str) -> str:
        """Generate a simple instruction based on description"""
        # Extract key concepts from description and create direct instructions
        if "sma" in description.lower() or "moving average" in description.lower():
            if "threshold" in description.lower():
                return "Implement a Pine Script code for SMA-based strategy with dynamic thresholds."
            else:
                return "Implement a Pine Script code for moving average crossover strategy."
        elif "rsi" in description.lower():
            return "Implement a Pine Script code for RSI-based trading signals."
        elif "input" in description.lower() and "parameter" in description.lower():
            return "Implement a Pine Script code for configurable strategy parameters."
        elif "threshold" in description.lower() and "entry" in description.lower():
            return "Implement a Pine Script code for threshold-based entry and exit signals."
        elif "signal" in description.lower() or "buy" in description.lower() or "sell" in description.lower():
            return "Implement a Pine Script code for trading signal generation."
        elif "period" in description.lower() and "sma" in description.lower():
            return "Implement a Pine Script code for period-based SMA calculation and thresholds."
        else:
            return "Implement a Pine Script code for the described trading strategy."
    
    def reformat_to_think_answer(self, content: str, description: str, code: str) -> str:
        """Reformat content to <think></think> <answer></answer> structure"""
        # If already in correct format, return as is
        if "<think>" in content and "</think>" in content and "<answer>" in content and "</answer>" in content:
            return content
        
        # Generate thinking process based on description and code
        thinking_process = f"""1. **Strategy Analysis**: {description}

2. **Implementation Requirements**: Based on the strategy description, I need to implement the core logic using appropriate Pine Script functions and syntax.

3. **Code Structure Planning**: I'll analyze the required components and translate them into Pine Script syntax, considering proper variable naming, function usage, and logic flow.

4. **Pine Script Translation**: Converting the conceptual strategy requirements into executable Pine Script code with appropriate technical indicators and conditional logic."""
        
        return f"""<think>
{thinking_process}
</think>
<answer>
{code}
</answer>"""
    
    def template_cot_generation(self, description: str, code: str) -> Dict:
        """Generate COT using template (fallback method)"""
        instruction = self.generate_simple_instruction(description)
        
        # Generate COT response using template with <think> and <answer> tags
        cot_response = f"""<think>
1. **Strategy Analysis**: {description}

2. **Implementation Approach**: I need to break down this strategy into its core components and implement each part using appropriate Pine Script functions.

3. **Technical Requirements**: Identify the necessary technical indicators, parameters, and conditional logic required for this strategy.

4. **Code Structure**: Plan the implementation by determining the sequence of operations and proper Pine Script syntax to achieve the desired functionality.
</think>
<answer>
{code}
</answer>"""
        
        return {
            "instruction": instruction,
            "output": cot_response
        }