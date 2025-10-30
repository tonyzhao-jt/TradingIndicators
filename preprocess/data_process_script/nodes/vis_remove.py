"""Visualization removal node: Remove visualization-related code from Pine Script."""
from typing import Dict, Any, List, Tuple
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm_client import get_llm

logger = logging.getLogger(__name__)


def apply_rule_based_removal(code: str) -> Dict[str, Any]:
    """
    Apply rule-based filtering to remove common visualization patterns.
    
    Args:
        code: Pine Script code
        
    Returns:
        Dict with cleaned_code and metadata
    """
    lines = code.split('\n')
    original_line_count = len(lines)
    cleaned_lines = []
    removed_lines = []
    
    # Patterns to detect and remove visualization-related code
    visualization_patterns = [
        # Plotting functions
        r'^\s*p_\w+\s*=\s*plot\s*\(',
        r'^\s*plot\s*\(',
        r'^\s*plotshape\s*\(',
        r'^\s*plotchar\s*\(',
        r'^\s*plotcandle\s*\(',
        r'^\s*plotbar\s*\(',
        r'^\s*hline\s*\(',
        r'^\s*fill\s*\(',
        r'^\s*bgcolor\s*\(',
        
        # Label and table functions
        r'^\s*label\.new\s*\(',
        r'^\s*label\.set_\w+\s*\(',
        r'^\s*table\.new\s*\(',
        r'^\s*table\.cell\s*\(',
        
        # Box and line drawing
        r'^\s*box\.new\s*\(',
        r'^\s*line\.new\s*\(',
        
        # Comment sections about plotting
        r'^\s*//\s*===.*[Pp]lot',
        r'^\s*//\s*===.*[Vv]isual',
        r'^\s*//\s*===.*[Ll]abel',
        r'^\s*//\s*===.*[Dd]raw',
    ]
    
    for line in lines:
        line_removed = False
        for pattern in visualization_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                removed_lines.append(line.strip())
                line_removed = True
                break
        
        if not line_removed:
            cleaned_lines.append(line)
    
    cleaned_code = '\n'.join(cleaned_lines)
    removed_count = original_line_count - len(cleaned_lines)
    
    return {
        "cleaned_code": cleaned_code,
        "removed_lines": removed_count,
        "visualization_detected": removed_count > 0,
        "removed_samples": removed_lines[:10]  # Keep first 10 for logging
    }


def remove_visualization_single(strategy: Dict[str, Any], llm_client, use_llm: bool = True) -> Dict[str, Any]:
    """
    Remove visualization code from a single strategy.
    
    Args:
        strategy: Strategy dictionary
        llm_client: LLM client instance
        use_llm: Whether to use LLM for removal (in addition to rule-based)
        
    Returns:
        Strategy with cleaned code
    """
    try:
        code = strategy.get("source_code", "")
        
        # First apply rule-based removal
        rule_result = apply_rule_based_removal(code)
        
        # Optionally apply LLM-based removal for better cleaning
        if use_llm and rule_result["visualization_detected"]:
            llm_result = llm_client.remove_visualization(rule_result["cleaned_code"])
            final_code = llm_result["cleaned_code"]
            logger.debug(f"Strategy {strategy.get('id', 'unknown')}: LLM removed additional visualization")
        else:
            final_code = rule_result["cleaned_code"]
        
        # Create updated strategy
        updated_strategy = {
            **strategy,
            "source_code": final_code,
            "original_code": code,
            "visualization_removed": rule_result["visualization_detected"],
            "removed_lines_count": rule_result["removed_lines"]
        }
        
        if rule_result["visualization_detected"]:
            logger.info(f"Removed {rule_result['removed_lines']} visualization lines from {strategy.get('id', 'unknown')}")
        
        return updated_strategy
        
    except Exception as e:
        logger.error(f"Error removing visualization from {strategy.get('id', 'unknown')}: {str(e)}")
        return strategy


def remove_visualization(strategies: List[Dict[str, Any]], use_llm: bool = False, max_workers: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Remove visualization-related code from all strategies.
    
    Args:
        strategies: List of strategy dictionaries
        use_llm: Whether to use LLM for removal (slower but more accurate)
        max_workers: Maximum number of concurrent operations
        
    Returns:
        Tuple of (cleaned_strategies, metadata)
    """
    try:
        if not strategies:
            return [], {"processed_count": 0, "visualization_removed_count": 0}
        
        llm_client = get_llm() if use_llm else None
        cleaned_strategies = []
        visualization_removed_count = 0
        total_lines_removed = 0
        
        logger.info(f"Starting visualization removal for {len(strategies)} strategies...")
        
        if use_llm:
            # Use ThreadPoolExecutor for concurrent processing with LLM
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_strategy = {
                    executor.submit(remove_visualization_single, strategy, llm_client, use_llm): strategy 
                    for strategy in strategies
                }
                
                for future in as_completed(future_to_strategy):
                    try:
                        cleaned_strategy = future.result()
                        cleaned_strategies.append(cleaned_strategy)
                        if cleaned_strategy.get("visualization_removed", False):
                            visualization_removed_count += 1
                            total_lines_removed += cleaned_strategy.get("removed_lines_count", 0)
                    except Exception as e:
                        strategy = future_to_strategy[future]
                        logger.error(f"Failed to clean strategy {strategy.get('id', 'unknown')}: {str(e)}")
                        cleaned_strategies.append(strategy)
        else:
            # Process without LLM (faster, rule-based only)
            for strategy in strategies:
                cleaned_strategy = remove_visualization_single(strategy, None, use_llm=False)
                cleaned_strategies.append(cleaned_strategy)
                if cleaned_strategy.get("visualization_removed", False):
                    visualization_removed_count += 1
                    total_lines_removed += cleaned_strategy.get("removed_lines_count", 0)
        
        metadata = {
            "processed_count": len(cleaned_strategies),
            "visualization_removed_count": visualization_removed_count,
            "total_lines_removed": total_lines_removed,
            "average_lines_removed": total_lines_removed / visualization_removed_count if visualization_removed_count > 0 else 0,
            "used_llm": use_llm
        }
        
        logger.info(f"Visualization removal completed: {visualization_removed_count}/{len(cleaned_strategies)} strategies cleaned")
        logger.info(f"Total lines removed: {total_lines_removed}")
        
        return cleaned_strategies, metadata
        
    except Exception as e:
        logger.error(f"Error in remove_visualization: {str(e)}")
        return strategies, {"error": str(e), "processed_count": 0}
