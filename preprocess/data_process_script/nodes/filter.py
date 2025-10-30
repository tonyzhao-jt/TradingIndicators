"""Filter node: Remove low-quality strategies based on likes, code length, and description length."""
from typing import Dict, Any, List, Tuple
import logging

from config import MIN_LIKES_COUNT, MIN_CODE_LENGTH, MIN_DESCRIPTION_LENGTH

logger = logging.getLogger(__name__)


def is_empty_field(value: Any) -> bool:
    """Check if a field is empty or contains only whitespace."""
    if value is None:
        return True
    
    if isinstance(value, str):
        return len(value.strip()) == 0
    
    return False


def filter_strategies(strategies: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Filter strategies based on likes count, code length, and description length.
    
    Args:
        strategies: List of raw strategy dictionaries
        
    Returns:
        Tuple of (filtered_strategies, metadata)
    """
    try:
        if not strategies:
            return [], {"filtered_count": 0, "removed_count": 0}
        
        initial_count = len(strategies)
        filtered_strategies = []
        removed_reasons = {
            "low_likes": 0,
            "empty_fields": 0,
            "short_description": 0,
            "short_code": 0
        }
        
        for strategy in strategies:
            # Check likes count
            likes_count = strategy.get("likes_count", 0)
            if likes_count < MIN_LIKES_COUNT:
                removed_reasons["low_likes"] += 1
                logger.debug(f"Removed strategy {strategy.get('id', 'unknown')}: likes={likes_count} < {MIN_LIKES_COUNT}")
                continue
            
            # Get description and code
            description = strategy.get("description", "")
            code = strategy.get("source_code", "")
            
            # Check for empty fields
            if is_empty_field(description) or is_empty_field(code):
                removed_reasons["empty_fields"] += 1
                logger.debug(f"Removed strategy {strategy.get('id', 'unknown')}: empty field(s)")
                continue
            
            # Check description length
            if len(description.strip()) < MIN_DESCRIPTION_LENGTH:
                removed_reasons["short_description"] += 1
                logger.debug(f"Removed strategy {strategy.get('id', 'unknown')}: description too short")
                continue
            
            # Check code length
            if len(code.strip()) < MIN_CODE_LENGTH:
                removed_reasons["short_code"] += 1
                logger.debug(f"Removed strategy {strategy.get('id', 'unknown')}: code too short")
                continue
            
            # All checks passed
            filtered_strategies.append(strategy)
        
        metadata = {
            "initial_count": initial_count,
            "filtered_count": len(filtered_strategies),
            "removed_count": initial_count - len(filtered_strategies),
            "removed_reasons": removed_reasons,
            "filter_criteria": {
                "min_likes": MIN_LIKES_COUNT,
                "min_code_length": MIN_CODE_LENGTH,
                "min_description_length": MIN_DESCRIPTION_LENGTH
            }
        }
        
        logger.info(f"Filter completed: {len(filtered_strategies)}/{initial_count} strategies passed")
        logger.info(f"Removed reasons: {removed_reasons}")
        
        return filtered_strategies, metadata
        
    except Exception as e:
        logger.error(f"Error in filter_strategies: {str(e)}")
        return [], {"error": str(e), "filtered_count": 0}
