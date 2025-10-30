"""LLM client for language conversion, visualization removal, and quality scoring."""
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
    """OpenAI LLM client for various text processing tasks."""
    
    def __init__(self):
        """Initialize the LLM client."""
        from config import LOCAL_QWEN_ENDPOINT, LOCAL_QWEN_API_KEY
        
        # Set API key from environment
        api_key = os.getenv("OPENAI_API_KEY", LOCAL_QWEN_API_KEY)
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Use custom endpoint if configured
        base_url = os.getenv("OPENAI_BASE_URL", LOCAL_QWEN_ENDPOINT)
        
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = LLM_MODEL
        
    def detect_and_translate(self, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Detect if text is in English, if not, translate to English.
        
        Args:
            text: Text to check and potentially translate
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing is_english, translated_text, and original_language
        """
        prompt = f"""Detect if the following text is in English. If not, translate it to English.

TEXT:
{text}

Return ONLY a JSON object:
{{
    "is_english": <true/false>,
    "original_language": "<language_name or 'English'>",
    "translated_text": "<english_translation or original_text_if_already_english>"
}}"""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=3000  # Increased to avoid truncation
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Try to extract JSON from response
                try:
                    # Find JSON in the response - look for complete JSON object
                    start_idx = result_text.find('{')
                    if start_idx != -1:
                        # Try to find matching closing brace
                        brace_count = 0
                        end_idx = start_idx
                        for i in range(start_idx, len(result_text)):
                            if result_text[i] == '{':
                                brace_count += 1
                            elif result_text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if end_idx > start_idx:
                            json_text = result_text[start_idx:end_idx]
                            result = json.loads(json_text)
                            # Validate required fields
                            if 'is_english' in result and 'translated_text' in result:
                                return result
                            else:
                                logger.warning(f"Missing required fields in JSON: {list(result.keys())}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}, text: {result_text[:200]}")
                
                # If JSON parsing fails, return original text
                return {
                    "is_english": True,
                    "original_language": "Unknown",
                    "translated_text": text
                }
                
            except Exception as e:
                logger.warning(f"Language detection attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    return {
                        "is_english": True,
                        "original_language": "Unknown",
                        "translated_text": text
                    }
                time.sleep(1)
        
        return {
            "is_english": True,
            "original_language": "Unknown",
            "translated_text": text
        }
    
    def remove_visualization(self, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Remove visualization-related code using LLM.
        
        Args:
            code: Pine Script code
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing cleaned_code and analysis
        """
        prompt = f"""You are a Pine Script expert. Remove all visualization-related code from the following Pine Script code while preserving the core trading logic.

Remove these elements:
- plot(), plotshape(), plotchar(), plotcandle(), plotbar(), hline()
- fill(), bgcolor()
- label.new(), table.new()
- Any variables only used for plotting (like p_xxx variables)
- Comments about plotting/visualization

Keep:
- Strategy logic (strategy.entry, strategy.close, strategy.exit)
- Calculations and indicators
- Input parameters
- Strategy configuration
- Trading conditions and signals

CODE:
{code}

Return ONLY a JSON object:
{{
    "cleaned_code": "<code_with_visualization_removed>",
    "removed_elements": ["<list of removed patterns>"],
    "visualization_detected": <true/false>
}}"""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=6000  # Increased to avoid truncation for code
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Try to extract JSON from response
                try:
                    # Find JSON in the response - look for complete JSON object
                    start_idx = result_text.find('{')
                    if start_idx != -1:
                        # Try to find matching closing brace
                        brace_count = 0
                        end_idx = start_idx
                        for i in range(start_idx, len(result_text)):
                            if result_text[i] == '{':
                                brace_count += 1
                            elif result_text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if end_idx > start_idx:
                            json_text = result_text[start_idx:end_idx]
                            result = json.loads(json_text)
                            # Validate required fields
                            if 'cleaned_code' in result:
                                return result
                            else:
                                logger.warning(f"Missing required fields in JSON: {list(result.keys())}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}, text: {result_text[:200]}")
                
                # If JSON parsing fails, return original code
                return {
                    "cleaned_code": code,
                    "removed_elements": [],
                    "visualization_detected": False
                }
                
            except Exception as e:
                logger.warning(f"Visualization removal attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    return {
                        "cleaned_code": code,
                        "removed_elements": [],
                        "visualization_detected": False
                    }
                time.sleep(1)
        
        return {
            "cleaned_code": code,
            "removed_elements": [],
            "visualization_detected": False
        }
    
    def score_quality(self, description: str, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Score the quality and match between description and code.
        
        Args:
            description: Natural language description
            code: Code implementation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing score, reasoning, and metadata
        """
        prompt = f"""You are an expert evaluator of trading strategy documentation. Evaluate the following description-code pair.

DESCRIPTION:
{description}

CODE:
{code}

Rate this pair on a scale of 1-10 based on:
1. **Match**: Do the description and code match? Does the code implement what's described?
2. **Description Detail**: Does the description provide sufficient detail about the strategy?
3. **Clarity**: How clear and understandable is the description?
4. **Code Quality**: Is the code well-structured and complete?
5. **Educational Value**: How useful is this for learning?

Scoring Guidelines:
- 9-10: Excellent - Perfect match, detailed description, high quality
- 7-8: Good - Good match, adequate detail, solid code
- 5-6: Average - Basic match, minimal detail
- 3-4: Poor - Weak match or very brief description
- 1-2: Very Poor - Mismatch or insufficient information

Return ONLY a JSON object:
{{
    "score": <number_1_to_10>,
    "reasoning": "<brief_explanation>",
    "match_score": <1_to_10>,
    "detail_score": <1_to_10>,
    "clarity_score": <1_to_10>,
    "code_quality_score": <1_to_10>,
    "educational_value": <1_to_10>
}}"""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=500
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                try:
                    # Find JSON in the response - look for complete JSON object
                    start_idx = result_text.find('{')
                    if start_idx != -1:
                        # Try to find matching closing brace
                        brace_count = 0
                        end_idx = start_idx
                        for i in range(start_idx, len(result_text)):
                            if result_text[i] == '{':
                                brace_count += 1
                            elif result_text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if end_idx > start_idx:
                            json_text = result_text[start_idx:end_idx]
                            result = json.loads(json_text)
                            
                            # Validate and normalize scores
                            if 'score' in result:
                                result['score'] = max(1, min(10, float(result.get('score', 5))))
                                return result
                            else:
                                logger.warning(f"Missing 'score' field in JSON: {list(result.keys())}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}, text: {result_text[:200]}")
                
                # Return default score if parsing fails
                return {
                    "score": 5.0,
                    "reasoning": "Failed to parse LLM response",
                    "match_score": 5,
                    "detail_score": 5,
                    "clarity_score": 5,
                    "code_quality_score": 5,
                    "educational_value": 5
                }
                
            except Exception as e:
                logger.warning(f"Quality scoring attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    return {
                        "score": 1.0,
                        "reasoning": f"Scoring failed: {str(e)}",
                        "match_score": 1,
                        "detail_score": 1,
                        "clarity_score": 1,
                        "code_quality_score": 1,
                        "educational_value": 1
                    }
                time.sleep(1)
        
        return {
            "score": 1.0,
            "reasoning": "Max retries exceeded",
            "match_score": 1,
            "detail_score": 1,
            "clarity_score": 1,
            "code_quality_score": 1,
            "educational_value": 1
        }


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
