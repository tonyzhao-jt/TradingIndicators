"""LangGraph workflow definition for data_process_segments pipeline."""
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from llm_client import get_llm
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import DEBUG_NODE_OUTPUT, MIN_CODE_LENGTH, MIN_DESCRIPTION_LENGTH, QUALITY_SCORE_THRESHOLD
import json
from nodes.pack import pack_segments
from nodes.filter import filter_segments  
from nodes.quality_score import score_segments


# Define the state structure for segment processing
class SegmentProcessingState(TypedDict):
    """State structure for segment processing workflow."""
    raw_item: Dict[str, Any]  # Original processed item from data_process_0
    packed_segments: Optional[List[Dict[str, Any]]]  # Extracted segments
    filtered_segments: Optional[List[Dict[str, Any]]]  # After filtering and deduplication
    scored_segments: Optional[List[Dict[str, Any]]]  # After quality scoring
    filter_metadata: Optional[Dict[str, Any]]  # Metadata from filtering
    quality_metadata: Optional[Dict[str, Any]]  # Metadata from quality scoring
    error_message: Optional[str]  # Error message if any
    status: str  # Current processing status


def pack_node(state: SegmentProcessingState) -> SegmentProcessingState:
    """
    Extract segments from restructured_data.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with packed segments
    """
    try:
        if DEBUG_NODE_OUTPUT:
            print("📦 PACK NODE: Starting segment extraction...")
            
        packed_segments, metadata = pack_segments(state["raw_item"])
        
        if DEBUG_NODE_OUTPUT:
            print(f"📦 PACK NODE: Extracted {len(packed_segments)} segments")
            
        return {
            **state,
            "packed_segments": packed_segments,
            "status": "packed"
        }
        
    except Exception as e:
        error_msg = f"Pack node error: {str(e)}"
        print(f"❌ PACK NODE ERROR: {error_msg}")
        return {
            **state,
            "error_message": error_msg,
            "status": "error"
        }


def filter_node(state: SegmentProcessingState) -> SegmentProcessingState:
    """
    Filter and deduplicate segments.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with filtered segments
    """
    try:
        if DEBUG_NODE_OUTPUT:
            print("🔍 FILTER NODE: Starting segment filtering...")
            
        filtered_segments, metadata = filter_segments(state["packed_segments"])
        
        if DEBUG_NODE_OUTPUT:
            print(f"🔍 FILTER NODE: {len(filtered_segments)} segments passed filtering")
            
        return {
            **state,
            "filtered_segments": filtered_segments,
            "filter_metadata": metadata,
            "status": "filtered"
        }
        
    except Exception as e:
        error_msg = f"Filter node error: {str(e)}"
        print(f"❌ FILTER NODE ERROR: {error_msg}")
        return {
            **state,
            "error_message": error_msg,
            "status": "error"
        }


def quality_score_node(state: SegmentProcessingState) -> SegmentProcessingState:
    """
    Score segment quality using LLM.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with scored segments
    """
    try:
        if DEBUG_NODE_OUTPUT:
            print("⭐ QUALITY SCORE NODE: Starting quality scoring...")
            
        scored_segments, metadata = score_segments(state["filtered_segments"])
        
        if DEBUG_NODE_OUTPUT:
            high_quality_count = len([s for s in scored_segments if s.get("quality_score", 0) >= QUALITY_SCORE_THRESHOLD])
            print(f"⭐ QUALITY SCORE NODE: {high_quality_count}/{len(scored_segments)} segments meet quality threshold")
            
        return {
            **state,
            "scored_segments": scored_segments,
            "quality_metadata": metadata,
            "status": "scored"
        }
        
    except Exception as e:
        error_msg = f"Quality score node error: {str(e)}"
        print(f"❌ QUALITY SCORE NODE ERROR: {error_msg}")
        return {
            **state,
            "error_message": error_msg,
            "status": "error"
        }


def should_continue_after_pack(state: SegmentProcessingState) -> str:
    """Determine next step after pack node."""
    if state["status"] == "error":
        return END
    if not state.get("packed_segments") or len(state["packed_segments"]) == 0:
        return END
    return "filter"


def should_continue_after_filter(state: SegmentProcessingState) -> str:
    """Determine next step after filter node."""
    if state["status"] == "error":
        return END
    if not state.get("filtered_segments") or len(state["filtered_segments"]) == 0:
        return END
    return "quality_score"


def should_continue_after_quality(state: SegmentProcessingState) -> str:
    """Determine next step after quality scoring."""
    return END


def create_segment_processing_graph() -> StateGraph:
    """
    Create the segment processing workflow graph.
    
    Returns:
        Configured StateGraph for segment processing
    """
    workflow = StateGraph(SegmentProcessingState)

    # Add nodes
    workflow.add_node("pack", pack_node)
    workflow.add_node("filter", filter_node) 
    workflow.add_node("quality_score", quality_score_node)

    # Set entry point
    workflow.set_entry_point("pack")

    # Add conditional edges
    workflow.add_conditional_edges(
        "pack",
        should_continue_after_pack,
        {
            "filter": "filter",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "filter",
        should_continue_after_filter,
        {
            "quality_score": "quality_score",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "quality_score",
        should_continue_after_quality,
        {
            END: END
        }
    )

    return workflow.compile()