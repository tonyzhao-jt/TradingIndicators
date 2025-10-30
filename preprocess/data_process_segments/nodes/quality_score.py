"""Quality score node: Score segments using LLM."""
from typing import Dict, Any, List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from llm_client import get_llm
from config import QUALITY_SCORE_THRESHOLD

logger = logging.getLogger(__name__)


def score_single_segment(segment: Dict[str, Any], llm_client) -> Dict[str, Any]:
    """
    Score a single segment using LLM.
    
    Args:
        segment: Segment dictionary with description and code
        llm_client: LLM client instance
        
    Returns:
        Segment with added quality scoring information
    """
    try:
        description = segment.get("description", "")
        code = segment.get("code", "")
        
        # Get quality score from LLM
        scoring_result = llm_client.score_segment_quality(description, code)
        
        # Add scoring information to segment
        enriched_segment = {
            **segment,
            "quality_score": scoring_result.get("score", 0),
            "quality_reasoning": scoring_result.get("reasoning", ""),
            "quality_metrics": {
                "clarity": scoring_result.get("clarity", 0),
                "accuracy": scoring_result.get("accuracy", 0),
                "educational_value": scoring_result.get("educational_value", 0),
                "code_quality": scoring_result.get("code_quality", 0),
                "completeness": scoring_result.get("completeness", 0)
            },
            "meets_quality_threshold": scoring_result.get("score", 0) >= QUALITY_SCORE_THRESHOLD,
            "scored_at": time.time()
        }
        
        logger.debug(f"Scored segment {segment.get('segment_key', 'unknown')}: {scoring_result.get('score', 0)}")
        return enriched_segment
        
    except Exception as e:
        logger.error(f"Error scoring segment {segment.get('segment_key', 'unknown')}: {str(e)}")
        # Return segment with default low score
        return {
            **segment,
            "quality_score": 1.0,
            "quality_reasoning": f"Scoring failed: {str(e)}",
            "quality_metrics": {
                "clarity": 1,
                "accuracy": 1,
                "educational_value": 1,
                "code_quality": 1,
                "completeness": 1
            },
            "meets_quality_threshold": False,
            "scored_at": time.time()
        }


def score_segments(segments: List[Dict[str, Any]], max_workers: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Score all segments for quality using LLM.
    
    Args:
        segments: List of segment dictionaries
        max_workers: Maximum number of concurrent LLM requests
        
    Returns:
        Tuple of (scored_segments, metadata)
    """
    try:
        if not segments:
            return [], {"scored_count": 0, "high_quality_count": 0, "average_score": 0.0}
        
        llm_client = get_llm()
        scored_segments = []
        
        logger.info(f"Starting quality scoring for {len(segments)} segments...")
        
        # Use ThreadPoolExecutor for concurrent LLM requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scoring tasks
            future_to_segment = {
                executor.submit(score_single_segment, segment, llm_client): segment 
                for segment in segments
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_segment):
                try:
                    scored_segment = future.result()
                    scored_segments.append(scored_segment)
                except Exception as e:
                    segment = future_to_segment[future]
                    logger.error(f"Failed to score segment {segment.get('segment_key', 'unknown')}: {str(e)}")
                    # Add failed segment with low score
                    failed_segment = {
                        **segment,
                        "quality_score": 1.0,
                        "quality_reasoning": f"Scoring failed: {str(e)}",
                        "meets_quality_threshold": False
                    }
                    scored_segments.append(failed_segment)
        
        # Calculate statistics
        scores = [s.get("quality_score", 0) for s in scored_segments]
        high_quality_count = len([s for s in scored_segments if s.get("meets_quality_threshold", False)])
        
        metadata = {
            "scored_count": len(scored_segments),
            "high_quality_count": high_quality_count,
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
        
        logger.info(f"Quality scoring completed: {high_quality_count}/{len(scored_segments)} segments meet threshold")
        logger.info(f"Average quality score: {metadata['average_score']:.2f}")
        
        return scored_segments, metadata
        
    except Exception as e:
        logger.error(f"Error in score_segments: {str(e)}")
        return [], {"error": str(e), "scored_count": 0}