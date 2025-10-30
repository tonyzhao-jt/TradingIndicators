"""Description augmentation node: Regenerate descriptions that don't match code."""
from typing import Dict, Any, List, Tuple
import logging
from llm_client import get_llm

logger = logging.getLogger(__name__)


def check_description_code_match(description: str, code: str, llm_client, max_retries: int = 3) -> Dict[str, Any]:
    """
    Check if description matches the code implementation using LLM.
    
    Args:
        description: Natural language description
        code: Code implementation
        llm_client: LLM client instance
        max_retries: Maximum retry attempts
        
    Returns:
        Dict containing match_score (0-10), reasoning, and match status
    """
    # Handle list output
    if isinstance(code, list):
        code = '\n'.join(str(item) for item in code)
    
    prompt = f"""You are an expert code reviewer. Evaluate if the following description accurately matches the code implementation.

DESCRIPTION:
{description}

CODE:
{code}

Rate the match on a scale of 0-10 where:
- 0-3: Poor match - description and code are unrelated or very different
- 4-6: Partial match - some overlap but significant gaps or inaccuracies
- 7-10: Good match - description accurately reflects the code implementation

Return your response in JSON format:
{{
    "match_score": <number 0-10>,
    "reasoning": "<brief explanation of why they match or don't match>",
    "needs_regeneration": <true/false>
}}"""

    for attempt in range(max_retries):
        try:
            response = llm_client.chat.completions.create(
                model=llm_client.model,
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating code documentation quality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=512
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                logger.warning(f"Could not parse JSON from response: {result_text}")
                
        except Exception as e:
            logger.error(f"Match check attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                return {
                    "match_score": 5,  # Neutral score on failure
                    "reasoning": f"Could not evaluate: {str(e)}",
                    "needs_regeneration": False
                }
    
    return {
        "match_score": 5,
        "reasoning": "Evaluation failed",
        "needs_regeneration": False
    }


def generate_new_description(code: str, llm_client, original_description: str = "", max_tokens: int = 1024, max_retries: int = 3) -> str:
    """
    Generate a new description based on the code implementation.
    
    Args:
        code: Code implementation
        llm_client: LLM client instance
        original_description: Original description for reference (optional)
        max_tokens: Maximum tokens for generated description
        max_retries: Maximum retry attempts
        
    Returns:
        New description string
    """
    # Handle list output
    if isinstance(code, list):
        code = '\n'.join(str(item) for item in code)
    
    # Build prompt with or without original description reference
    if original_description and original_description.strip():
        prompt = f"""You are an expert at documenting trading strategy code. Write a clear, concise description of what the following code does.

ORIGINAL DESCRIPTION (for reference only - may be inaccurate or incomplete):
{original_description}

CODE:
{code}

Requirements:
1. Use the ORIGINAL DESCRIPTION as a reference to understand the intent, but base your description primarily on what the CODE actually does
2. If the original description contains useful context or terminology, incorporate it
3. Describe the technical indicators and calculations used in the code
4. Explain the trading logic or signal generation clearly
5. Mention key parameters or thresholds
6. Keep the description concise and under {max_tokens} tokens
7. Be specific and accurate - only describe what's present in the code
8. Write in clear, professional English
9. Do not mention that this is a regenerated description

Provide only the improved description without any additional explanation or formatting."""
    else:
        prompt = f"""You are an expert at documenting trading strategy code. Write a clear, concise description of what the following code does.

CODE:
{code}

Requirements:
1. Describe the technical indicators and calculations used
2. Explain the trading logic or signal generation
3. Mention key parameters or thresholds
4. Keep the description concise and under {max_tokens} tokens
5. Be specific and accurate - don't add information not present in the code
6. Write in clear, professional English

Provide only the description without any additional explanation or formatting."""

    for attempt in range(max_retries):
        try:
            response = llm_client.chat.completions.create(
                model=llm_client.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical writer specializing in trading strategies and financial code documentation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens
            )
            
            description = response.choices[0].message.content.strip()
            
            # Remove any markdown formatting
            description = description.replace('**', '').replace('*', '')
            description = description.strip()
            
            logger.info(f"Generated new description ({len(description)} chars)")
            return description
            
        except Exception as e:
            logger.error(f"Description generation attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("All description generation attempts failed")
                return ""
    
    return ""


def augment_segment_description(segment: Dict[str, Any], llm_client, match_threshold: float = 6.0) -> Dict[str, Any]:
    """
    Check and potentially regenerate description if it doesn't match the code.
    
    Args:
        segment: Segment dictionary with 'input' and 'output' fields
        llm_client: LLM client instance
        match_threshold: Minimum match score to keep original description (0-10)
        
    Returns:
        Updated segment with potentially regenerated description
    """
    description = segment.get('input', '')
    code = segment.get('output', '')
    
    if not description or not code:
        logger.warning("Segment has empty description or code, skipping augmentation")
        return segment
    
    # Check if description matches code
    logger.info("Checking description-code match...")
    match_result = check_description_code_match(description, code, llm_client)
    
    match_score = match_result.get('match_score', 5)
    needs_regen = match_result.get('needs_regeneration', False)
    
    logger.info(f"Match score: {match_score}/10 - {match_result.get('reasoning', '')}")
    
    # If match score is below threshold, regenerate description
    if match_score < match_threshold or needs_regen:
        logger.info(f"Match score {match_score} below threshold {match_threshold}, regenerating description...")
        # Pass original description as reference for better context
        new_description = generate_new_description(code, llm_client, original_description=description)
        
        if new_description:
            updated_segment = segment.copy()
            updated_segment['input'] = new_description
            updated_segment['_original_input'] = description  # Keep original for reference
            updated_segment['_description_regenerated'] = True
            updated_segment['_match_score'] = match_score
            updated_segment['_match_reasoning'] = match_result.get('reasoning', '')
            
            logger.info("Description regenerated successfully with original as reference")
            return updated_segment
        else:
            logger.warning("Failed to generate new description, keeping original")
            segment['_description_augment_failed'] = True
            return segment
    else:
        logger.info("Description matches code well, keeping original")
        segment['_match_score'] = match_score
        return segment


def augment_segments_descriptions(segments: List[Dict[str, Any]], match_threshold: float = 6.0) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Augment descriptions for all segments where description doesn't match code.
    
    Args:
        segments: List of segment dictionaries
        match_threshold: Minimum match score to keep original description (0-10)
        
    Returns:
        Tuple of (augmented segments, metadata)
    """
    logger.info(f"Starting description augmentation for {len(segments)} segments")
    
    llm_client = get_llm()
    augmented_segments = []
    regenerated_count = 0
    match_scores = []
    
    for idx, segment in enumerate(segments):
        try:
            logger.info(f"Processing segment {idx + 1}/{len(segments)}")
            augmented_segment = augment_segment_description(segment, llm_client, match_threshold)
            augmented_segments.append(augmented_segment)
            
            if augmented_segment.get('_description_regenerated', False):
                regenerated_count += 1
            
            if '_match_score' in augmented_segment:
                match_scores.append(augmented_segment['_match_score'])
                
        except Exception as e:
            logger.error(f"Error augmenting segment {idx}: {str(e)}")
            # Keep original segment if augmentation fails
            segment['_description_augment_error'] = str(e)
            augmented_segments.append(segment)
    
    avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0
    
    metadata = {
        "total_segments": len(segments),
        "regenerated_count": regenerated_count,
        "kept_original_count": len(segments) - regenerated_count,
        "average_match_score": round(avg_match_score, 2),
        "match_threshold": match_threshold
    }
    
    logger.info(f"Description augmentation completed: {regenerated_count}/{len(segments)} descriptions regenerated")
    logger.info(f"Average match score: {avg_match_score:.2f}/10")
    
    return augmented_segments, metadata
