"""Quality scoring node: Score and filter strategies based on description-code match."""
from typing import Dict, Any, List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from llm_client import get_llm
from config import QUALITY_SCORE_THRESHOLD

logger = logging.getLogger(__name__)


def score_single_strategy(strategy: Dict[str, Any], llm_client) -> Dict[str, Any]:
    """
    Score a single strategy using LLM.
    
    Args:
        strategy: Strategy dictionary with description and code
        llm_client: LLM client instance
        
    Returns:
        Strategy with added quality scoring information
    """
    try:
        description = strategy.get("description", "")
        code = strategy.get("source_code", "")
        
        # Get quality score from LLM
        scoring_result = llm_client.score_quality(description, code)
        
        # Add scoring information to strategy
        enriched_strategy = {
            **strategy,
            "quality_score": scoring_result.get("score", 0),
            "quality_reasoning": scoring_result.get("reasoning", ""),
            "quality_metrics": {
                "match_score": scoring_result.get("match_score", 0),
                "detail_score": scoring_result.get("detail_score", 0),
                "clarity_score": scoring_result.get("clarity_score", 0),
                "code_quality_score": scoring_result.get("code_quality_score", 0),
                "educational_value": scoring_result.get("educational_value", 0)
            },
            "meets_quality_threshold": scoring_result.get("score", 0) >= QUALITY_SCORE_THRESHOLD,
            "scored_at": time.time()
        }
        
        logger.debug(f"Scored strategy {strategy.get('id', 'unknown')}: {scoring_result.get('score', 0):.1f}")
        return enriched_strategy
        
    except Exception as e:
        logger.error(f"Error scoring strategy {strategy.get('id', 'unknown')}: {str(e)}")
        # Return strategy with default low score
        return {
            **strategy,
            "quality_score": 1.0,
            "quality_reasoning": f"Scoring failed: {str(e)}",
            "quality_metrics": {
                "match_score": 1,
                "detail_score": 1,
                "clarity_score": 1,
                "code_quality_score": 1,
                "educational_value": 1
            },
            "meets_quality_threshold": False,
            "scored_at": time.time()
        }


def score_and_filter(strategies: List[Dict[str, Any]], max_workers: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Score all strategies for quality and filter based on threshold.
    
    Args:
        strategies: List of strategy dictionaries
        max_workers: Maximum number of concurrent LLM requests
        
    Returns:
        Tuple of (high_quality_strategies, metadata)
    """
    try:
        if not strategies:
            return [], {"scored_count": 0, "high_quality_count": 0, "average_score": 0.0}
        
        llm_client = get_llm()
        scored_strategies = []
        
        logger.info(f"Starting quality scoring for {len(strategies)} strategies...")
        
        # Use ThreadPoolExecutor for concurrent LLM requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scoring tasks
            future_to_strategy = {
                executor.submit(score_single_strategy, strategy, llm_client): strategy 
                for strategy in strategies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_strategy):
                try:
                    scored_strategy = future.result()
                    scored_strategies.append(scored_strategy)
                except Exception as e:
                    strategy = future_to_strategy[future]
                    logger.error(f"Failed to score strategy {strategy.get('id', 'unknown')}: {str(e)}")
                    # Add failed strategy with low score
                    failed_strategy = {
                        **strategy,
                        "quality_score": 1.0,
                        "quality_reasoning": f"Scoring failed: {str(e)}",
                        "meets_quality_threshold": False
                    }
                    scored_strategies.append(failed_strategy)
        
        # Filter strategies that meet the quality threshold
        high_quality_strategies = [s for s in scored_strategies if s.get("meets_quality_threshold", False)]
        
        # Calculate statistics
        scores = [s.get("quality_score", 0) for s in scored_strategies]
        
        metadata = {
            "scored_count": len(scored_strategies),
            "high_quality_count": len(high_quality_strategies),
            "filtered_out_count": len(scored_strategies) - len(high_quality_strategies),
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "quality_threshold": QUALITY_SCORE_THRESHOLD,
            "quality_distribution": {
                "excellent_9_10": len([s for s in scores if s >= 9]),
                "good_7_8": len([s for s in scores if 7 <= s < 9]),
                "average_5_6": len([s for s in scores if 5 <= s < 7]),
                "poor_3_4": len([s for s in scores if 3 <= s < 5]),
                "very_poor_1_2": len([s for s in scores if s < 3])
            }
        }
        
        logger.info(f"Quality scoring completed: {len(high_quality_strategies)}/{len(scored_strategies)} strategies meet threshold")
        logger.info(f"Average quality score: {metadata['average_score']:.2f}")
        
        return high_quality_strategies, metadata
        
    except Exception as e:
        logger.error(f"Error in score_and_filter: {str(e)}")
        return [], {"error": str(e), "scored_count": 0}
