"""Restructure node: Remove comments and reorganize both description and code into structured components."""
import json
import re
from typing import Dict, Any, Optional
from llm_client import get_llm


def restructure_strategy_data(raw_data: Dict[str, Any], cleaned_code: str) -> Dict[str, Any]:
    """
    Restructure strategy data by removing comments and reorganizing both description and code.
    
    Components (in order):
    - strategy_setup: Initial setup and configuration
    - input_params: Input parameters and settings
    - filtering_sys: Filtering systems and conditions
    - smart_money: Smart money concepts and logic
    - signal_gen: Signal generation logic
    - risk_management: Risk management and position sizing
    - core_method: Core calculation methods and algorithms (placed last)
    
    Args:
        raw_data: Original strategy data
        cleaned_code: Code after visualization removal
        
    Returns:
        Dictionary with restructured description and code components in JSON format
    """
    if not cleaned_code.strip():
        return {
            "restructured_data": {},
            "success": False,
            "reason": "No code to process"
        }
    
    # First remove comments from code
    code_without_comments = _remove_comments(cleaned_code)
    
    # Get description from raw data
    description = raw_data.get("description", "")
    
    # Then restructure both description and code using LLM
    restructured_result = _restructure_with_llm(code_without_comments, description, raw_data)
    
    return restructured_result


def _remove_comments(code: str) -> str:
    """Remove comments from the code."""
    lines = code.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove single line comments (// style)
        if '//' in line:
            # Find the position of // and remove everything after it
            comment_pos = line.find('//')
            line = line[:comment_pos]
        
        # Remove multi-line comment markers if they appear on the same line
        line = re.sub(r'/\*.*?\*/', '', line)
        
        # Keep the line if it's not empty after comment removal
        if line.strip():
            cleaned_lines.append(line)
    
    # Remove multi-line comments that span multiple lines
    code_str = '\n'.join(cleaned_lines)
    code_str = re.sub(r'/\*.*?\*/', '', code_str, flags=re.DOTALL)
    
    return code_str


def _restructure_with_llm(code: str, description: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to restructure both description and code into structured components."""
    llm = get_llm(node_name="restructure", temperature=0.1, max_tokens=4096)
    
    strategy_name = raw_data.get("name", "Unknown Strategy")
    
    prompt = f"""
You are a trading strategy analyzer. Your task is to analyze the following trading strategy and restructure both the description and code into structured components.

Strategy Name: {strategy_name}

Original Description:
{description}

Code to analyze:
```
{code}
```

IMPORTANT INSTRUCTIONS:
1. EXTRACT relevant text from the original description for each component - don't rewrite
2. If description doesn't have info for a component, extract what you can from the code
3. When description and code conflict, PRIORITIZE CODE and supplement description based on code
4. Organize into these 7 components IN THIS EXACT ORDER:

1. **strategy_setup**: Extract description text about general strategy overview, purpose, what it does
2. **input_params**: Extract description text about parameters, settings, customizable values
3. **filtering_sys**: Extract description text about filtering, conditions, screening
4. **smart_money**: Extract description text about institutional logic, smart money concepts
5. **signal_gen**: Extract description text about signals, entry/exit rules, trading conditions
6. **risk_management**: Extract description text about risk control, protection, money management
7. **core_method**: Extract description text about calculations, algorithms, mathematical methods (PLACE LAST)

For each component:
- description: Extract relevant parts from original description OR supplement based on code if missing
- code: Assign code lines to the most appropriate category

Respond in this exact JSON format:
{{
    "strategy_setup": {{
        "description": "extracted text from original description about strategy overview",
        "code": "code lines for setup and configuration"
    }},
    "input_params": {{
        "description": "extracted text from original description about parameters", 
        "code": "code lines for input parameters"
    }},
    "filtering_sys": {{
        "description": "extracted text from original description about filtering",
        "code": "code lines for filtering systems"
    }},
    "smart_money": {{
        "description": "extracted text from original description about smart money concepts",
        "code": "code lines for smart money logic"
    }},
    "signal_gen": {{
        "description": "extracted text from original description about signals and trading rules",
        "code": "code lines for signal generation"
    }},
    "risk_management": {{
        "description": "extracted text from original description about risk management",
        "code": "code lines for risk management"
    }},
    "core_method": {{
        "description": "extracted text from original description about calculations and methods",
        "code": "code lines for core methods and calculations"
    }},
    "analysis_summary": "brief summary of how the original description was mapped to components"
}}
"""
    
    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)
        
        # Validate the response structure
        expected_keys = ["strategy_setup", "input_params", "filtering_sys", "smart_money", 
                        "signal_gen", "risk_management", "core_method", "analysis_summary"]
        
        if not all(key in result for key in expected_keys):
            raise ValueError("Invalid response structure - missing expected keys")
        
        # Validate that each component has both description and code
        for key in expected_keys[:-1]:  # Exclude analysis_summary
            if not isinstance(result[key], dict) or "description" not in result[key] or "code" not in result[key]:
                raise ValueError(f"Invalid structure for component {key}")
        
        return {
            "restructured_data": {
                "strategy_setup": result["strategy_setup"],
                "input_params": result["input_params"], 
                "filtering_sys": result["filtering_sys"],
                "smart_money": result["smart_money"],
                "signal_gen": result["signal_gen"],
                "risk_management": result["risk_management"],
                "core_method": result["core_method"]
            },
            "analysis_summary": result["analysis_summary"],
            "success": True,
            "reason": "Successfully restructured strategy data"
        }
    
    except Exception as e:
        print(f"Error in LLM strategy restructuring: {str(e)}")
        return {
            "restructured_data": {
                "strategy_setup": {"description": "", "code": ""},
                "input_params": {"description": "", "code": ""},
                "filtering_sys": {"description": "", "code": ""},
                "smart_money": {"description": "", "code": ""},
                "signal_gen": {"description": "", "code": ""},
                "risk_management": {"description": "", "code": ""},
                "core_method": {"description": description, "code": code}  # Put all content in core_method as fallback
            },
            "analysis_summary": f"LLM restructuring failed: {str(e)}",
            "success": False,
            "reason": f"LLM restructuring failed, fallback applied: {str(e)}"
        }