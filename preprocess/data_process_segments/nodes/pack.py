"""Pack node: Extract segments from restructured_data."""
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


def pack_segments(raw_item: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extract individual segments from restructured_data.
    
    Args:
        raw_item: Original processed item containing restructured_data
        
    Returns:
        Tuple of (segments_list, metadata)
    """
    try:
        # Extract restructured_data from the item
        restructured_data = None
        
        # Check if restructured_data is in restructure_metadata (nested structure)
        if "restructure_metadata" in raw_item and "restructured_data" in raw_item["restructure_metadata"]:
            restructured_data = raw_item["restructure_metadata"]["restructured_data"]
        # Check if restructured_data is directly in the item
        elif "restructured_data" in raw_item:
            restructured_data = raw_item["restructured_data"]
        else:
            logger.warning("No restructured_data found in raw_item")
            return [], {"error": "No restructured_data found", "segments_extracted": 0}
        
        if not isinstance(restructured_data, dict):
            logger.warning("restructured_data is not a dictionary")
            return [], {"error": "Invalid restructured_data format", "segments_extracted": 0}
        
        segments = []
        
        # Extract each key-value pair as a segment
        for segment_key, segment_data in restructured_data.items():
            if not isinstance(segment_data, dict):
                logger.warning(f"Segment {segment_key} is not a dictionary, skipping")
                continue
                
            # Ensure required fields exist
            if "description" not in segment_data or "code" not in segment_data:
                logger.warning(f"Segment {segment_key} missing description or code, skipping")
                continue
            
            segment = {
                "segment_key": segment_key,
                "description": segment_data["description"],
                "code": segment_data["code"],
                "source_item_id": raw_item.get("raw_data", {}).get("id", "unknown"),
                "source_title": raw_item.get("raw_data", {}).get("name", "unknown"),
                "source_author": raw_item.get("raw_data", {}).get("preview_author", "unknown")
            }
            
            segments.append(segment)
            
        metadata = {
            "segments_extracted": len(segments),
            "source_id": raw_item.get("raw_data", {}).get("id", "unknown"),
            "original_segments_count": len(restructured_data) if restructured_data else 0
        }
        
        logger.info(f"Successfully extracted {len(segments)} segments from {metadata['source_id']}")
        return segments, metadata
        
    except Exception as e:
        logger.error(f"Error in pack_segments: {str(e)}")
        return [], {"error": str(e), "segments_extracted": 0}