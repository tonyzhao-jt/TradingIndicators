"""LLM client for segment quality scoring."""
import os
import openai
from typing import Dict, Any, Optional
import time
import json
import logging

from config import LLM_MODEL, LLM_TEMPERATURE

# Set up logging
logger = logging.getLogger(__name__)

class LLMClient:
    """OpenAI LLM client for quality scoring."""
    
    def __init__(self):
        """Initialize the LLM client."""
        # Set API key from environment
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = openai.OpenAI()
        
    def score_segment_quality(self, description: str, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Score the quality of a description-code segment pair.
        
        Args:
            description: Natural language description
            code: Code implementation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing score, reasoning, and metadata
        """
        prompt = f"""You are an expert evaluator of trading strategy code documentation. Evaluate the following description-code pair for quality and educational value.

DESCRIPTION:
{description}

CODE:
{code}

Rate this pair on a scale of 1-10 based on:
1. **Clarity**: How well does the description explain what the code does?
2. **Accuracy**: Does the description accurately reflect the code implementation?
3. **Educational Value**: How useful is this for learning trading strategy concepts?
4. **Code Quality**: Is the code well-structured and meaningful?
5. **Completeness**: Does the description provide sufficient context?

Scoring Guidelines:
- 9-10: Excellent - Clear, accurate, highly educational
- 7-8: Good - Minor issues but solid overall
- 5-6: Average - Adequate but room for improvement
- 3-4: Poor - Significant issues with clarity or accuracy
- 1-2: Very Poor - Misleading or very low quality

Return ONLY a JSON object with:
{{
    "score": <number_1_to_10>,
    "reasoning": "<brief_explanation>",
    "clarity": <1_to_10>,
    "accuracy": <1_to_10>,
    "educational_value": <1_to_10>,
    "code_quality": <1_to_10>,
    "completeness": <1_to_10>
}}"""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=300
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                try:
                    result = json.loads(result_text)
                    
                    # Validate required fields
                    required_fields = ['score', 'reasoning', 'clarity', 'accuracy', 'educational_value', 'code_quality', 'completeness']
                    if all(field in result for field in required_fields):
                        # Ensure score is within valid range
                        result['score'] = max(1, min(10, float(result['score'])))
                        return result
                    else:
                        logger.warning(f"Missing required fields in response: {result}")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {result_text}, error: {e}")
                    
            except Exception as e:
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        # Return default low score if all attempts failed
        return {
            "score": 1.0,
            "reasoning": "Failed to get LLM evaluation",
            "clarity": 1,
            "accuracy": 1,
            "educational_value": 1,
            "code_quality": 1,
            "completeness": 1
        }


def get_llm() -> LLMClient:
    """Get a configured LLM client instance."""
    return LLMClient()