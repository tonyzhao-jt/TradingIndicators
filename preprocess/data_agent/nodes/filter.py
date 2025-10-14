"""Filter node: Determine if trading strategy data should be kept for processing."""
import json
from typing import Dict, Any, Optional
from llm_client import get_llm
from config import QUALITY_SCORE_THRESHOLD, ENABLE_QUALITY_FILTER


def count_words(text: str) -> int:
    """
    Count the number of words in a text.
    
    Args:
        text: Input text
        
    Returns:
        Word count
    """
    if not text:
        return 0
    return len(text.split())


def check_word_count(description: str, min_words: int = 100) -> Dict[str, Any]:
    """
    Check if description meets minimum word count requirement.
    
    Args:
        description: Strategy description text
        min_words: Minimum required word count
        
    Returns:
        Dictionary with:
        - passed: Whether word count check passed
        - word_count: Actual word count
        - reason: Explanation
    """
    word_count = count_words(description)
    passed = word_count >= min_words
    
    return {
        "passed": passed,
        "word_count": word_count,
        "reason": f"Word count: {word_count} (minimum: {min_words})"
    }


def assess_content_quality(
    description: str,
    name: str = "",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Use LLM to assess if description contains sufficient indicator and strategy details.
    
    Evaluates whether the description provides:
    1. Clear indicator/technical analysis information
    2. Specific strategy implementation details
    3. Actionable trading logic
    
    Args:
        description: Strategy description text
        name: Strategy name (optional, for context)
        temperature: Optional temperature override
        max_tokens: Optional max_tokens override
        
    Returns:
        Dictionary with:
        - passed: Whether content quality check passed
        - score: Quality score (0-100)
        - reasoning: Detailed explanation
        - indicators_present: Whether indicators are described
        - strategy_present: Whether strategy details are present
    """
    # Get LLM client
    llm = get_llm(
        node_name="filter",
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    # Construct prompt
    prompt = _build_quality_assessment_prompt(description, name)
    
    # Get LLM response
    try:
        response = llm.invoke(prompt)
        result = _parse_quality_response(response.content)
        return result
    except Exception as e:
        print(f"Error during quality assessment: {str(e)}")
        # On error, default to rejecting to be safe
        return {
            "passed": False,
            "score": 0,
            "reasoning": f"Error during assessment: {str(e)}",
            "indicators_present": False,
            "strategy_present": False
        }


def _build_quality_assessment_prompt(description: str, name: str = "") -> str:
    """
    Build the prompt for quality assessment.
    
    Args:
        description: Strategy description
        name: Strategy name
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a trading strategy quality assessor. Your task is to evaluate whether a strategy description contains sufficient information about indicators and implementation details.

A GOOD description should include:
1. **Indicators**: Clear mention of technical indicators used (e.g., VWAP, RSI, MACD, Moving Averages, Volume, etc.)
2. **Strategy Logic**: Specific details on how the strategy works (entry/exit rules, conditions, calculations)
3. **Implementation Details**: Concrete information about how to implement the strategy

A BAD description is:
- Too vague or general
- Just marketing language without technical details
- No mention of specific indicators or how they're used
- No clear explanation of strategy logic

Strategy Name: {name if name else "Not provided"}

Strategy Description:
{description[:2000]}

Please evaluate this description and provide your assessment in the following JSON format:
{{
    "passed": true/false,
    "score": 0-100,
    "reasoning": "Detailed explanation of your decision",
    "indicators_present": true/false,
    "strategy_present": true/false
}}

Scoring guidelines:
- 80-100: Excellent - Rich technical details, clear indicators, specific implementation steps
- 60-79: Good - Has indicators and strategy logic, but could be more detailed
- 40-59: Fair - Some technical content but lacks specifics
- 20-39: Poor - Very vague, minimal technical content
- 0-19: Unacceptable - No meaningful indicator or strategy information

Set "passed" to true ONLY if score >= {QUALITY_SCORE_THRESHOLD}.

Respond with ONLY the JSON object, no additional text."""
    
    return prompt


def _parse_quality_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM response for quality assessment.
    
    Args:
        response_text: Raw LLM response
        
    Returns:
        Parsed dictionary with quality assessment
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
        
        # Validate and normalize structure
        if not isinstance(result.get("passed"), bool):
            result["passed"] = False
        
        if not isinstance(result.get("score"), (int, float)):
            result["score"] = 0
        else:
            result["score"] = max(0, min(100, int(result["score"])))
        
        if not isinstance(result.get("reasoning"), str):
            result["reasoning"] = "No reasoning provided"
        
        if not isinstance(result.get("indicators_present"), bool):
            result["indicators_present"] = False
        
        if not isinstance(result.get("strategy_present"), bool):
            result["strategy_present"] = False
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse quality assessment JSON: {str(e)}")
        print(f"Raw response: {response_text[:500]}")
        return {
            "passed": False,
            "score": 0,
            "reasoning": "Failed to parse LLM response",
            "indicators_present": False,
            "strategy_present": False
        }
    except Exception as e:
        print(f"Error parsing quality response: {str(e)}")
        return {
            "passed": False,
            "score": 0,
            "reasoning": f"Error: {str(e)}",
            "indicators_present": False,
            "strategy_present": False
        }


def filter_data(
    raw_data: Dict[str, Any],
    min_words: int = 100,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main filter function: Determine if data should be kept for processing.
    
    Applies two checks:
    1. Word count check (objective)
    2. Content quality check (subjective, LLM-based)
    
    Args:
        raw_data: Raw trading strategy data
        min_words: Minimum word count requirement
        temperature: Optional temperature override
        max_tokens: Optional max_tokens override
        
    Returns:
        Dictionary with:
        - should_keep: Final decision (True/False)
        - word_check: Word count check results
        - quality_check: Quality assessment results
        - rejection_reason: Reason for rejection (if rejected)
    """
    description = raw_data.get("description", "")
    name = raw_data.get("name", "")
    
    # Check 1: Word count
    word_check = check_word_count(description, min_words)
    
    # If word count fails, reject immediately (no need for LLM check)
    if not word_check["passed"]:
        return {
            "should_keep": False,
            "word_check": word_check,
            "quality_check": None,
            "rejection_reason": f"Description too short: {word_check['reason']}"
        }
    
    # Check 2: Content quality (LLM-based) - skip if disabled in config
    quality_check = None
    if ENABLE_QUALITY_FILTER:
        quality_check = assess_content_quality(
            description=description,
            name=name,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Final decision: use configured threshold as the pass cutoff
        score = quality_check.get("score", 0)
        should_keep = score >= QUALITY_SCORE_THRESHOLD
    else:
        # If quality filter disabled, accept item based on word count only
        quality_check = {
            "passed": True,
            "score": 100,
            "reasoning": "Quality filter disabled - auto-accepted based on word count",
            "indicators_present": True,
            "strategy_present": True
        }
        should_keep = True
    rejection_reason = None
    
    if not should_keep:
        rejection_reason = (
            f"Insufficient content quality (score: {quality_check['score']}/100). "
            f"{quality_check['reasoning']}"
        )
    
    return {
        "should_keep": should_keep,
        "word_check": word_check,
        "quality_check": quality_check,
        "rejection_reason": rejection_reason
    }


# Test function
def test_filter():
    """Test filter with various descriptions."""
    
    test_cases = [
        {
            "name": "Test 1: Too Short",
            "data": {
                "name": "Short Strategy",
                "description": "This is a simple trading strategy that uses VWAP."
            }
        },
        {
            "name": "Test 2: Long but Vague",
            "data": {
                "name": "Vague Strategy",
                "description": " ".join(["This is a great strategy"] * 30)
            }
        },
        {
            "name": "Test 3: Good Quality",
            "data": {
                "name": "VWAP Strategy",
                "description": """
                This VWAP-based trading strategy uses Volume Weighted Average Price as the primary indicator.
                The strategy enters long positions when price crosses above VWAP with increased volume.
                Entry conditions: 1) Close > VWAP, 2) Volume > 1.5x average volume, 3) RSI > 50
                Exit conditions: 1) Close < VWAP, or 2) Take profit at 2% gain, or 3) Stop loss at 1% loss
                The strategy also uses moving average crossovers for trend confirmation.
                Best suited for 5-minute to 15-minute timeframes on liquid assets.
                Risk management: Position size is 2% of portfolio per trade.
                The VWAP is calculated using standard formula: sum(price * volume) / sum(volume).
                Additional filters include checking for market structure and avoiding trades during low volatility periods.
                """ * 3
            }
        }
    ]
    
    print("\n=== Filter Node Testing ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{test_case['name']}")
        print("-" * 60)
        
        result = filter_data(test_case["data"], min_words=100)
        
        print(f"Decision: {'✓ KEEP' if result['should_keep'] else '✗ REJECT'}")
        print(f"Word Count: {result['word_check']['word_count']} words")
        
        if result['quality_check']:
            print(f"Quality Score: {result['quality_check']['score']}/100")
            print(f"Indicators Present: {result['quality_check']['indicators_present']}")
            print(f"Strategy Present: {result['quality_check']['strategy_present']}")
        
        if result['rejection_reason']:
            print(f"Rejection Reason: {result['rejection_reason'][:150]}...")
        
        print()


if __name__ == "__main__":
    test_filter()
