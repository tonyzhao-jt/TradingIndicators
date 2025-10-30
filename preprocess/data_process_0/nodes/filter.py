"""Filter node: Filter data based on configurable thresholds."""
import json
from typing import Dict, Any
from config import MIN_LIKES, MIN_DESCRIPTION_WORDS, MIN_CODE_LENGTH


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


def count_characters(text: str) -> int:
    """
    Count the number of characters in a text.
    
    Args:
        text: Input text
        
    Returns:
        Character count
    """
    if not text:
        return 0
    return len(text)


def filter_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter data based on criteria:
    1. Likes > 100
    2. Description > 100 words
    3. Code > 100 characters
    
    Args:
        raw_data: Raw strategy data
        
    Returns:
        Dictionary with filtering results
    """
    # Extract fields with safe defaults - adjust field names to match actual data structure
    likes = raw_data.get("likes_count", 0)  # Changed from "likes" to "likes_count"
    description = raw_data.get("description", "")
    code = raw_data.get("source_code", "")  # Changed from "code" to "source_code"
    
    # Convert likes to int if it's a string
    if isinstance(likes, str):
        try:
            likes = int(likes)
        except ValueError:
            likes = 0
    
    # Count words in description
    description_words = count_words(description)
    
    # Count characters in code
    code_chars = count_characters(code)
    
    # Check each criteria using config values
    likes_pass = likes > MIN_LIKES
    description_pass = description_words > MIN_DESCRIPTION_WORDS
    code_pass = code_chars > MIN_CODE_LENGTH
    
    # Overall pass if all criteria met
    should_keep = likes_pass and description_pass and code_pass
    
    return {
        "should_keep": should_keep,
        "likes": likes,
        "likes_pass": likes_pass,
        "description_words": description_words,
        "description_pass": description_pass,
        "code_chars": code_chars,
        "code_pass": code_pass,
        "reason": _build_filter_reason(likes, likes_pass, description_words, description_pass, code_chars, code_pass)
    }


def _build_filter_reason(likes: int, likes_pass: bool, desc_words: int, desc_pass: bool, 
                        code_chars: int, code_pass: bool) -> str:
    """Build detailed reason for filter decision."""
    from config import MIN_LIKES, MIN_DESCRIPTION_WORDS, MIN_CODE_LENGTH
    
    reasons = []
    
    if not likes_pass:
        reasons.append(f"Likes: {likes} (required: >{MIN_LIKES})")
    
    if not desc_pass:
        reasons.append(f"Description words: {desc_words} (required: >{MIN_DESCRIPTION_WORDS})")
    
    if not code_pass:
        reasons.append(f"Code characters: {code_chars} (required: >{MIN_CODE_LENGTH})")
    
    if not reasons:
        return f"All criteria passed - Likes: {likes}, Description: {desc_words} words, Code: {code_chars} chars"
    
    return f"Failed: {', '.join(reasons)}"