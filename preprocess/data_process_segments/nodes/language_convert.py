"""Language conversion node: Translate non-English content to English."""
from typing import Dict, Any, List, Tuple
import logging
import re
from llm_client import get_llm

logger = logging.getLogger(__name__)


def detect_non_english(text: str) -> bool:
    """
    Detect if text contains non-English characters.
    
    Args:
        text: Text to check
        
    Returns:
        True if non-English characters are found, False otherwise
    """
    if not text:
        return False
    
    # Check for common non-English character ranges
    # Chinese, Japanese, Korean, Arabic, Cyrillic, etc.
    non_english_patterns = [
        r'[\u4e00-\u9fff]',  # Chinese
        r'[\u3040-\u309f]',  # Japanese Hiragana
        r'[\u30a0-\u30ff]',  # Japanese Katakana
        r'[\uac00-\ud7af]',  # Korean
        r'[\u0400-\u04ff]',  # Cyrillic
        r'[\u0600-\u06ff]',  # Arabic
        r'[\u0e00-\u0e7f]',  # Thai
    ]
    
    for pattern in non_english_patterns:
        if re.search(pattern, text):
            return True
    
    return False


def translate_to_english(text: str, llm_client, field_name: str = "text") -> str:
    """
    Translate non-English text to English using LLM.
    
    Args:
        text: Text to translate
        llm_client: LLM client instance
        field_name: Name of the field being translated (for context)
        
    Returns:
        Translated text in English
    """
    prompt = f"""Translate the following {field_name} to English. Preserve all technical terms, code, and trading terminology. Only translate natural language descriptions, not code snippets or technical identifiers.

Original text:
{text}

Provide only the English translation without any additional explanation or notes."""

    try:
        response = llm_client.chat.completions.create(
            model=llm_client.model,
            messages=[
                {"role": "system", "content": "You are a professional translator specializing in technical and trading content. Translate accurately while preserving technical terms."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2048
        )
        
        translated = response.choices[0].message.content.strip()
        logger.info(f"Translated {field_name} from non-English to English")
        return translated
        
    except Exception as e:
        logger.error(f"Translation failed for {field_name}: {str(e)}")
        return text  # Return original if translation fails


def convert_segment_language(segment: Dict[str, Any], llm_client) -> Dict[str, Any]:
    """
    Convert a segment's input and output to English if they contain non-English text.
    
    Args:
        segment: Segment dictionary with 'input' and 'output' fields
        llm_client: LLM client instance
        
    Returns:
        Updated segment with English text
    """
    updated_segment = segment.copy()
    needs_conversion = False
    
    # Check input field
    input_text = segment.get('input', '')
    if detect_non_english(input_text):
        needs_conversion = True
        logger.info("Non-English detected in input field")
        updated_segment['input'] = translate_to_english(input_text, llm_client, "input description")
    
    # Check output field
    output = segment.get('output', '')
    
    # Handle different output types
    if isinstance(output, str):
        if detect_non_english(output):
            needs_conversion = True
            logger.info("Non-English detected in output field (string)")
            updated_segment['output'] = translate_to_english(output, llm_client, "output code")
    elif isinstance(output, list):
        # Check if any list item contains non-English
        translated_items = []
        for i, item in enumerate(output):
            item_str = str(item)
            if detect_non_english(item_str):
                needs_conversion = True
                logger.info(f"Non-English detected in output field (list item {i})")
                translated_items.append(translate_to_english(item_str, llm_client, f"output code line {i}"))
            else:
                translated_items.append(item)
        if needs_conversion:
            updated_segment['output'] = translated_items
    
    if needs_conversion:
        updated_segment['_language_converted'] = True
        logger.info("Segment language conversion completed")
    
    return updated_segment


def convert_segments_language(segments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convert all segments with non-English content to English.
    
    Args:
        segments: List of segment dictionaries
        
    Returns:
        Tuple of (converted segments, metadata)
    """
    logger.info(f"Starting language conversion for {len(segments)} segments")
    
    llm_client = get_llm()
    converted_segments = []
    conversion_count = 0
    
    for idx, segment in enumerate(segments):
        try:
            converted_segment = convert_segment_language(segment, llm_client)
            converted_segments.append(converted_segment)
            
            if converted_segment.get('_language_converted', False):
                conversion_count += 1
                
        except Exception as e:
            logger.error(f"Error converting segment {idx}: {str(e)}")
            # Keep original segment if conversion fails
            converted_segments.append(segment)
    
    metadata = {
        "total_segments": len(segments),
        "converted_count": conversion_count,
        "kept_original_count": len(segments) - conversion_count
    }
    
    logger.info(f"Language conversion completed: {conversion_count}/{len(segments)} segments converted")
    
    return converted_segments, metadata
