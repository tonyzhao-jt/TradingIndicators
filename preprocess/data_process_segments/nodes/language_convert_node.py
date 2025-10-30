"""
Language Convert Node - Translate non-English content to English
"""

import re
import logging
from typing import List, Dict
from llm_client import get_llm

logger = logging.getLogger(__name__)


class LanguageConvertNode:
    def __init__(self):
        self.name = "language_convert_node"
        self.llm_client = None
    
    def get_llm_client(self):
        """Lazy load LLM client"""
        if self.llm_client is None:
            self.llm_client = get_llm()
        return self.llm_client
    
    def detect_non_english(self, text: str) -> bool:
        """Detect if text contains non-English characters"""
        if not text:
            return False
        
        # Check for common non-English character ranges
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
    
    def translate_to_english(self, text: str, field_name: str = "text") -> str:
        """Translate non-English text to English using LLM"""
        prompt = f"""Translate the following {field_name} to English. Preserve all technical terms, code, and trading terminology. Only translate natural language descriptions, not code snippets or technical identifiers.

Original text:
{text}

Provide only the English translation without any additional explanation or notes."""

        try:
            llm = self.get_llm_client()
            response = llm.client.chat.completions.create(
                model=llm.model,
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
    
    def process(self, segments: List[Dict]) -> List[Dict]:
        """Process segments and convert non-English content to English"""
        print(f"LanguageConvertNode: Processing {len(segments)} segments")
        
        converted_segments = []
        conversion_count = 0
        
        for idx, segment in enumerate(segments):
            try:
                converted_segment = segment.copy()
                needs_conversion = False
                
                # Check input field
                input_text = segment.get('input', '')
                if self.detect_non_english(input_text):
                    needs_conversion = True
                    print(f"  Converting segment {idx + 1}: Non-English detected in input")
                    converted_segment['input'] = self.translate_to_english(input_text, "input description")
                
                # Check output field
                output = segment.get('output', '')
                if isinstance(output, str) and self.detect_non_english(output):
                    needs_conversion = True
                    print(f"  Converting segment {idx + 1}: Non-English detected in output")
                    converted_segment['output'] = self.translate_to_english(output, "output code")
                elif isinstance(output, list):
                    # Check if any list item contains non-English
                    translated_items = []
                    list_converted = False
                    for i, item in enumerate(output):
                        item_str = str(item)
                        if self.detect_non_english(item_str):
                            needs_conversion = True
                            list_converted = True
                            print(f"  Converting segment {idx + 1}: Non-English detected in output line {i}")
                            translated_items.append(self.translate_to_english(item_str, f"output line {i}"))
                        else:
                            translated_items.append(item)
                    if list_converted:
                        converted_segment['output'] = translated_items
                
                if needs_conversion:
                    conversion_count += 1
                    converted_segment['_language_converted'] = True
                
                converted_segments.append(converted_segment)
                
            except Exception as e:
                logger.error(f"Error converting segment {idx}: {str(e)}")
                # Keep original segment if conversion fails
                converted_segments.append(segment)
        
        print(f"LanguageConvertNode: Converted {conversion_count}/{len(segments)} segments to English")
        return converted_segments
