"""Filter node: Remove small/no-code segments and deduplicate."""
from typing import Dict, Any, List, Tuple
import logging
import hashlib
from difflib import SequenceMatcher
import re

from config import MIN_CODE_LENGTH, MIN_DESCRIPTION_LENGTH, SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


def is_empty_field(value: Any) -> bool:
    """
    Check if a field is empty or contains only whitespace.
    
    Args:
        value: Value to check (can be string, list, or other types)
        
    Returns:
        True if field is empty, False otherwise
    """
    if value is None:
        return True
    
    if isinstance(value, str):
        return len(value.strip()) == 0
    
    if isinstance(value, list):
        # Check if list is empty or all items are empty strings
        if len(value) == 0:
            return True
        return all(isinstance(item, str) and len(item.strip()) == 0 for item in value)
    
    return False


def is_code_meaningful(code: str) -> bool:
    """
    Check if code segment is meaningful (not just comments or simple notes).
    
    Args:
        code: Code string to check
        
    Returns:
        True if code is meaningful, False otherwise
    """
    if not code or len(code.strip()) < MIN_CODE_LENGTH:
        return False
    
    # Remove comments and whitespace
    cleaned_code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)  # Remove // comments
    cleaned_code = re.sub(r'/\*.*?\*/', '', cleaned_code, flags=re.DOTALL)  # Remove /* */ comments
    cleaned_code = re.sub(r'#.*$', '', cleaned_code, flags=re.MULTILINE)  # Remove # comments
    cleaned_code = re.sub(r'\s+', ' ', cleaned_code).strip()  # Normalize whitespace
    
    # Check for actual code patterns (assignments, function calls, etc.)
    code_patterns = [
        r'=\s*[^=]',  # Assignment (not ==)
        r'\w+\s*\(',  # Function calls
        r'\b(if|while|for|function|def|var|let|const|input\.)\b',  # Keywords
        r'\w+\.\w+',  # Object/method access
        r'\[.*\]',    # Array/index access
    ]
    
    has_code = any(re.search(pattern, cleaned_code, re.IGNORECASE) for pattern in code_patterns)
    
    # Check for "Note:" patterns which are usually not code
    is_note_only = re.match(r'^\s*Note:\s*\(.*\)\s*$', code.strip(), re.IGNORECASE | re.DOTALL)
    
    return has_code and not is_note_only


def calculate_code_similarity(code1: str, code2: str) -> float:
    """
    Calculate similarity between two code segments.
    
    Args:
        code1: First code segment
        code2: Second code segment
        
    Returns:
        Similarity ratio (0.0 to 1.0)
    """
    # Normalize code for comparison
    def normalize_code(code):
        # Remove whitespace and comments
        normalized = re.sub(r'\s+', ' ', code.strip())
        normalized = re.sub(r'//.*$', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'#.*$', '', normalized, flags=re.MULTILINE)
        return normalized.lower()
    
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)
    
    # Use sequence matcher to get similarity
    return SequenceMatcher(None, norm1, norm2).ratio()


def filter_segments(segments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Filter segments by removing small/no-code segments and deduplicating.
    
    Args:
        segments: List of segment dictionaries
        
    Returns:
        Tuple of (filtered_segments, metadata)
    """
    try:
        if not segments:
            return [], {"filtered_count": 0, "removed_count": 0, "duplicate_count": 0}
        
        initial_count = len(segments)
        filtered_segments = []
        removed_reasons = {
            "empty_fields": 0,
            "short_description": 0,
            "no_meaningful_code": 0,
            "duplicate_code": 0
        }
        
        # First pass: Remove segments with empty fields, short descriptions or no meaningful code
        for segment in segments:
            # Support both old format (description/code) and new format (input/output)
            description = segment.get("description", segment.get("input", ""))
            code = segment.get("code", segment.get("output", ""))
            
            # Check for empty fields
            if is_empty_field(description) or is_empty_field(code):
                removed_reasons["empty_fields"] += 1
                logger.debug(f"Removed segment with empty field(s)")
                continue
            
            # Convert to string for further checks
            description_str = description.strip() if isinstance(description, str) else str(description).strip()
            code_str = code if isinstance(code, str) else '\n'.join(str(item) for item in code) if isinstance(code, list) else str(code)
            code_str = code_str.strip()
            
            # Check description length
            if len(description_str) < MIN_DESCRIPTION_LENGTH:
                removed_reasons["short_description"] += 1
                continue
                
            # Check if code is meaningful
            if not is_code_meaningful(code_str):
                removed_reasons["no_meaningful_code"] += 1
                continue
                
            filtered_segments.append(segment)
        
        # Second pass: Remove duplicate code segments
        final_segments = []
        seen_codes = []
        
        for segment in filtered_segments:
            # Support both old format (code) and new format (output)
            code = segment.get("code", segment.get("output", ""))
            # Handle list format
            if isinstance(code, list):
                code = '\n'.join(str(item) for item in code)
            
            is_duplicate = False
            
            # Check against all previously seen codes
            for seen_code in seen_codes:
                similarity = calculate_code_similarity(code, seen_code)
                if similarity >= SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    removed_reasons["duplicate_code"] += 1
                    break
            
            if not is_duplicate:
                seen_codes.append(code)
                final_segments.append(segment)
        
        metadata = {
            "initial_count": initial_count,
            "filtered_count": len(final_segments),
            "removed_count": initial_count - len(final_segments),
            "removed_reasons": removed_reasons,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "min_code_length": MIN_CODE_LENGTH,
            "min_description_length": MIN_DESCRIPTION_LENGTH
        }
        
        logger.info(f"Filtering results: {initial_count} -> {len(final_segments)} segments")
        logger.info(f"Removed: {removed_reasons}")
        
        return final_segments, metadata
        
    except Exception as e:
        logger.error(f"Error in filter_segments: {str(e)}")
        return [], {"error": str(e), "filtered_count": 0}