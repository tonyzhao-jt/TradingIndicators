"""Language conversion node: Detect and translate non-English text to English."""
from typing import Dict, Any, List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm_client import get_llm

logger = logging.getLogger(__name__)


def convert_single_strategy(strategy: Dict[str, Any], llm_client) -> Dict[str, Any]:
    """
    Convert description to English if it's in another language.
    
    Args:
        strategy: Strategy dictionary
        llm_client: LLM client instance
        
    Returns:
        Strategy with converted description
    """
    try:
        description = strategy.get("description", "")
        
        # Use LLM to detect and translate
        result = llm_client.detect_and_translate(description)
        
        # Create updated strategy
        updated_strategy = {
            **strategy,
            "description": result["translated_text"],
            "original_description": description if not result["is_english"] else None,
            "original_language": result["original_language"],
            "was_translated": not result["is_english"]
        }
        
        if not result["is_english"]:
            logger.info(f"Translated strategy {strategy.get('id', 'unknown')} from {result['original_language']}")
        
        return updated_strategy
        
    except Exception as e:
        logger.error(f"Error converting strategy {strategy.get('id', 'unknown')}: {str(e)}")
        return strategy


def convert_language(strategies: List[Dict[str, Any]], max_workers: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convert non-English descriptions to English.
    
    Args:
        strategies: List of strategy dictionaries
        max_workers: Maximum number of concurrent LLM requests
        
    Returns:
        Tuple of (converted_strategies, metadata)
    """
    try:
        if not strategies:
            return [], {"converted_count": 0, "translation_count": 0}
        
        llm_client = get_llm()
        converted_strategies = []
        translation_count = 0
        
        logger.info(f"Starting language conversion for {len(strategies)} strategies...")
        
        # Use ThreadPoolExecutor for concurrent LLM requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all conversion tasks
            future_to_strategy = {
                executor.submit(convert_single_strategy, strategy, llm_client): strategy 
                for strategy in strategies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_strategy):
                try:
                    converted_strategy = future.result()
                    converted_strategies.append(converted_strategy)
                    if converted_strategy.get("was_translated", False):
                        translation_count += 1
                except Exception as e:
                    strategy = future_to_strategy[future]
                    logger.error(f"Failed to convert strategy {strategy.get('id', 'unknown')}: {str(e)}")
                    # Add original strategy if conversion fails
                    converted_strategies.append(strategy)
        
        metadata = {
            "processed_count": len(converted_strategies),
            "translation_count": translation_count,
            "already_english_count": len(converted_strategies) - translation_count
        }
        
        logger.info(f"Language conversion completed: {translation_count}/{len(converted_strategies)} strategies translated")
        
        return converted_strategies, metadata
        
    except Exception as e:
        logger.error(f"Error in convert_language: {str(e)}")
        return strategies, {"error": str(e), "converted_count": 0}
