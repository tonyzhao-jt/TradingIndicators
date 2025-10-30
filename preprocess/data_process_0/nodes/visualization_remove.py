"""Visualization Remove node: Remove AI dashboard and visualization related data from code."""
import json
import re
from typing import Dict, Any, Optional
from llm_client import get_llm


def remove_visualization_content(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove AI dashboard and visualization related content from code.
    
    Args:
        raw_data: Raw strategy data
        
    Returns:
        Dictionary with cleaned code and metadata
    """
    code = raw_data.get("source_code", "")  # Changed from "code" to "source_code"
    
    if not code:
        return {
            "cleaned_code": "",
            "removed_lines": 0,
            "visualization_detected": False,
            "reason": "No code to process"
        }
    
    # Use LLM directly for visualization removal
    llm_result = _apply_llm_filtering(code)
    
    return {
        "cleaned_code": llm_result["cleaned_code"],
        "removed_lines": llm_result["removed_lines"],
        "visualization_detected": llm_result["visualization_detected"],
        "llm_analysis": llm_result["analysis"],
        "reason": f"LLM removed {llm_result['removed_lines']} lines"
    }


def _apply_rule_based_filtering(code: str) -> Dict[str, Any]:
    """Apply rule-based filtering to remove common visualization patterns."""
    # First, try to properly format the code by adding newlines if missing
    if '\n' not in code and len(code) > 200:  # Likely a single line with missing newlines
        # Try to add newlines after common Pine Script patterns
        import re
        code = re.sub(r'(\w+\s*=\s*[^=]+?)([a-zA-Z_]\w*\s*=)', r'\1\n\2', code)
        code = re.sub(r'(strategy\.[^)]+\))', r'\1\n', code)
        code = re.sub(r'(if\s+[^{]+)', r'\n\1', code)
        code = re.sub(r'(//\s*===)', r'\n\1', code)
    
    lines = code.split('\n')
    original_line_count = len(lines)
    cleaned_lines = []
    removed_patterns = []
    
    # Patterns to detect and remove visualization-related code - made more specific
    visualization_patterns = [
        # Specific plotting functions (match full line patterns)
        r'^\s*p_\w+\s*=\s*plot\s*\(',
        r'^\s*plot\s*\(',
        r'^\s*plotshape\s*\(',
        r'^\s*plotchar\s*\(',
        r'^\s*plotcandle\s*\(',
        r'^\s*plotbar\s*\(',
        r'^\s*hline\s*\(',
        r'^\s*fill\s*\(',
        r'^\s*bgcolor\s*\(',
        
        # Label and UI functions
        r'^\s*label\.new\s*\(',
        r'^\s*table\.new\s*\(',
        
        # Specific comment sections about plotting
        r'^\s*//\s*===.*[Pp]lotting.*===',
        r'^\s*//\s*===.*[Ll]abels.*===',
        r'^\s*//\s*===.*[Ee]ntry/[Ee]xit.*[Ll]abels.*===',
    ]
    
    for line in lines:
        line_removed = False
        for pattern in visualization_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                removed_patterns.append(f"Pattern '{pattern}' matched: {line.strip()}")
                line_removed = True
                break
        
        if not line_removed:
            cleaned_lines.append(line)
    
    cleaned_code = '\n'.join(cleaned_lines)
    removed_lines = original_line_count - len(cleaned_lines)
    visualization_detected = removed_lines > 0
    
    return {
        "cleaned_code": cleaned_code,
        "removed_lines": removed_lines,
        "visualization_detected": visualization_detected,
        "removed_patterns": removed_patterns
    }


def _apply_llm_filtering(code: str) -> Dict[str, Any]:
    """Use LLM to identify and remove visualization content."""
    if not code.strip():
        return {
            "cleaned_code": code,
            "removed_lines": 0,
            "visualization_detected": False,
            "analysis": "No code to analyze"
        }
    
    llm = get_llm(node_name="visualization_remove", temperature=0.1, max_tokens=4096)
    
    prompt = f"""
You are a Pine Script code analyzer. Your task is to remove ONLY visualization, plotting, and dashboard-related code from the following trading strategy code.

REMOVE these types of code:
1. Plot functions: plot(), plotshape(), plotchar(), plotcandle(), plotbar(), hline()
2. Visual elements: fill(), bgcolor(), label.new(), table.new(), box.new()
3. Color and style definitions that are purely cosmetic
4. AI dashboard or ML visualization components
5. Chart drawing and display functions

KEEP these types of code:
1. All trading logic and calculations
2. Strategy entry/exit functions (strategy.entry, strategy.exit, strategy.close)
3. Input parameters and configurations
4. Mathematical calculations and indicators
5. Variables and data processing
6. Comments that explain trading logic (not plotting)

Original Code:
```
{code}
```

Please respond in this exact JSON format:
{{
    "cleaned_code": "the code with only visualization parts removed",
    "removed_lines": number_of_lines_removed_approximately,
    "visualization_detected": true/false,
    "analysis": "brief explanation of what visualization elements were found and removed"
}}

IMPORTANT: Keep all the core trading strategy logic intact. Only remove the visual/plotting elements.
"""
    
    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)
        
        # Validate the response structure
        if not all(key in result for key in ["cleaned_code", "removed_lines", "visualization_detected", "analysis"]):
            raise ValueError("Invalid response structure")
        
        return result
    
    except Exception as e:
        print(f"Error in LLM visualization filtering: {str(e)}")
        return {
            "cleaned_code": code,
            "removed_lines": 0,
            "visualization_detected": False,
            "analysis": f"LLM filtering failed: {str(e)}"
        }