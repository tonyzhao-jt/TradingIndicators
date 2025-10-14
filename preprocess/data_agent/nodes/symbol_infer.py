"""Symbol inference node: Infer relevant trading symbols from strategy description."""
import json
from typing import Dict, Any, List, Optional
from llm_client import get_llm


def infer_relevant_symbols(
    description: str,
    name: str = "",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Infer relevant trading symbols from strategy description.
    
    Uses LLM to analyze the strategy description and identify which trading
    symbols or asset pairs are most relevant (e.g., USDT, BTC, ETH, etc.).
    
    Args:
        description: Strategy description text
        name: Strategy name (optional, for additional context)
        temperature: Optional temperature override for LLM
        max_tokens: Optional max_tokens override for LLM
        
    Returns:
        Dictionary containing:
        - symbols: List of inferred symbols (e.g., ["USDT", "BTC"])
        - confidence: Confidence level (high/medium/low)
        - reasoning: Brief explanation of why these symbols were selected
    """
    # Get LLM client
    llm = get_llm(
        node_name="symbol_infer",
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    # Construct prompt
    prompt = _build_inference_prompt(description, name)
    
    # Get LLM response
    try:
        response = llm.invoke(prompt)
        result = _parse_llm_response(response.content)
        return result
    except Exception as e:
        print(f"Error during symbol inference: {str(e)}")
        return {
            "symbols": [],
            "confidence": "low",
            "reasoning": f"Error during inference: {str(e)}"
        }


def _build_inference_prompt(description: str, name: str = "") -> str:
    """
    Build the prompt for symbol inference.
    
    Args:
        description: Strategy description
        name: Strategy name
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a trading strategy analyzer. Your task is to identify which trading symbols or cryptocurrency pairs are most relevant to the given strategy.

Common symbols include:
- Stablecoins: USDT, USDC, BUSD, DAI
- Major cryptocurrencies: BTC, ETH, BNB, SOL, ADA
- Trading pairs: BTC/USDT, ETH/USDT, etc.
- Traditional assets: USD, EUR, GBP, GOLD, etc.

Analyze the following strategy and identify relevant symbols:

Strategy Name: {name if name else "Not provided"}

Strategy Description:
{description[:2000]}

Please provide your analysis in the following JSON format:
{{
    "symbols": ["SYMBOL1", "SYMBOL2", ...],
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of why these symbols are relevant"
}}

Rules:
1. List symbols in order of relevance
2. Include 1-5 symbols maximum
3. Use standard symbol notation (uppercase)
4. Provide high confidence only if symbols are explicitly mentioned
5. Provide medium confidence if symbols are strongly implied
6. Provide low confidence if symbols are only weakly related

Respond with ONLY the JSON object, no additional text."""
    
    return prompt


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM response into structured format.
    
    Args:
        response_text: Raw LLM response
        
    Returns:
        Parsed dictionary with symbols, confidence, and reasoning
    """
    try:
        # Try to extract JSON from response
        response_text = response_text.strip()
        
        # Find JSON block if wrapped in markdown
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate structure
        if not isinstance(result.get("symbols"), list):
            result["symbols"] = []
        
        if result.get("confidence") not in ["high", "medium", "low"]:
            result["confidence"] = "low"
        
        if not isinstance(result.get("reasoning"), str):
            result["reasoning"] = "No reasoning provided"
        
        # Normalize symbols to uppercase
        result["symbols"] = [s.upper() for s in result["symbols"]]
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {str(e)}")
        print(f"Raw response: {response_text[:500]}")
        return {
            "symbols": [],
            "confidence": "low",
            "reasoning": "Failed to parse LLM response"
        }
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        return {
            "symbols": [],
            "confidence": "low",
            "reasoning": f"Error: {str(e)}"
        }


def extract_symbols_list(inference_result: Dict[str, Any]) -> List[str]:
    """
    Extract just the symbols list from inference result.
    
    Args:
        inference_result: Result from infer_relevant_symbols
        
    Returns:
        List of symbol strings
    """
    return inference_result.get("symbols", [])


def format_symbols_for_output(symbols: List[str]) -> str:
    """
    Format symbols list as comma-separated string for output.
    
    Args:
        symbols: List of symbol strings
        
    Returns:
        Comma-separated string (e.g., "USDT,BTC,ETH")
    """
    return ",".join(symbols) if symbols else ""


# Test function
def test_symbol_inference():
    """Test symbol inference with sample data."""
    sample_description = """
    This VWAP trading strategy is designed for Bitcoin and Ethereum pairs
    against USDT. It uses volume-weighted average price to identify entry
    and exit points in cryptocurrency markets. The strategy works best with
    BTC/USDT and ETH/USDT pairs on 15-minute timeframes.
    """
    
    result = infer_relevant_symbols(
        description=sample_description,
        name="VWAP Crypto Strategy"
    )
    
    print("Symbol Inference Result:")
    print(json.dumps(result, indent=2))
    print("\nFormatted symbols:", format_symbols_for_output(result["symbols"]))


if __name__ == "__main__":
    test_symbol_inference()
