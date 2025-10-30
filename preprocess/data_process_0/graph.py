"""LangGraph workflow definition for data_process_0 pipeline."""
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from llm_client import get_llm
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import DEBUG_NODE_OUTPUT, MIN_LIKES, MIN_DESCRIPTION_WORDS, MIN_CODE_LENGTH
import json
from nodes.filter import filter_data
from nodes.visualization_remove import remove_visualization_content
from nodes.restructure import restructure_strategy_data


# Define the state structure for data processing
class DataProcessingState(TypedDict):
    """State structure for data processing workflow."""
    raw_data: Dict[str, Any]  # Current item being processed
    filter_result: Optional[bool]  # Whether to keep the data after filtering
    cleaned_code: Optional[str]  # Code after visualization removal
    visualization_metadata: Optional[Dict[str, Any]]  # Metadata from visualization removal
    restructured_data: Optional[Dict[str, Any]]  # Final restructured data structure
    restructure_metadata: Optional[Dict[str, Any]]  # Metadata from restructuring
    error_message: Optional[str]  # Error message if any
    status: str  # Current processing status


def filter_node(state: DataProcessingState) -> DataProcessingState:
    """
    Filter node: Determine whether to keep the current data based on criteria:
    - Likes > 100
    - Description > 100 words  
    - Code > 100 characters
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with filter result
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: filter | id={item_id} | name={item_name}")

    try:
        filter_result_dict = filter_data(raw_data=state["raw_data"])
        filter_result = filter_result_dict.get("should_keep", False)
        
        out = {
            "filter_result": filter_result,
            "status": "filtered" if filter_result else "rejected_by_filter",
            "filter_metadata": filter_result_dict
        }
        
        if DEBUG_NODE_OUTPUT:
            debug = {"passed": filter_result, "details": filter_result_dict}
            print(f"  [DEBUG OUTPUT] filter -> {debug}")
        return out
    except Exception as e:
        print(f"Error in filter node: {str(e)}")
        return {
            "filter_result": False,
            "status": "filter_error",
            "error_message": f"Filter failed: {str(e)}"
        }


def visualization_remove_node(state: DataProcessingState) -> DataProcessingState:
    """
    Visualization remove node: Remove AI dashboard and visualization related content.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with cleaned code
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: visualization_remove | id={item_id} | name={item_name}")

    try:
        result = remove_visualization_content(raw_data=state["raw_data"])
        
        out = {
            "cleaned_code": result.get("cleaned_code", ""),
            "visualization_metadata": result,
            "status": "visualization_removed"
        }
        
        if DEBUG_NODE_OUTPUT:
            debug = {
                "removed_lines": result.get("removed_lines", 0),
                "visualization_detected": result.get("visualization_detected", False)
            }
            print(f"  [DEBUG OUTPUT] visualization_remove -> {debug}")
        return out
    except Exception as e:
        print(f"Error in visualization_remove node: {str(e)}")
        return {
            "cleaned_code": state["raw_data"].get("code", ""),
            "status": "visualization_remove_error", 
            "error_message": f"Visualization removal failed: {str(e)}"
        }


def restructure_node(state: DataProcessingState) -> DataProcessingState:
    """
    Restructure node: Remove comments and reorganize both description and code into structured components.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with restructured data
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: restructure | id={item_id} | name={item_name}")

    try:
        cleaned_code = state.get("cleaned_code", "")
        result = restructure_strategy_data(
            raw_data=state["raw_data"],
            cleaned_code=cleaned_code
        )
        
        out = {
            "restructured_data": result.get("restructured_data", {}),
            "restructure_metadata": result,
            "status": "completed"
        }
        
        if DEBUG_NODE_OUTPUT:
            debug = {
                "success": result.get("success", False),
                "components": list(result.get("restructured_data", {}).keys())
            }
            print(f"  [DEBUG OUTPUT] restructure -> {debug}")
        return out
    except Exception as e:
        print(f"Error in restructure node: {str(e)}")
        return {
            "restructured_data": {},
            "status": "restructure_error",
            "error_message": f"Restructuring failed: {str(e)}"
        }


def should_continue_after_filter(state: DataProcessingState) -> str:
    """Decision function: Continue processing if filter passed."""
    if state.get("filter_result", False):
        return "visualization_remove"
    else:
        return END


def create_data_processing_graph() -> StateGraph:
    """
    Create the data processing graph with three nodes:
    1. filter - Filter based on likes, description, code criteria
    2. visualization_remove - Remove visualization and dashboard code  
    3. restructure - Remove comments and reorganize both description and code structure
    
    Returns:
        StateGraph: The constructed processing graph
    """
    # Create the graph
    graph = StateGraph(DataProcessingState)
    
    # Add nodes
    graph.add_node("filter", filter_node)
    graph.add_node("visualization_remove", visualization_remove_node)
    graph.add_node("restructure", restructure_node)
    
    # Set entry point
    graph.set_entry_point("filter")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "filter",
        should_continue_after_filter,
        {
            "visualization_remove": "visualization_remove",
            END: END
        }
    )
    
    # Add sequential edges
    graph.add_edge("visualization_remove", "restructure")
    graph.add_edge("restructure", END)
    
    # Compile the graph
    app = graph.compile()
    return app


if __name__ == "__main__":
    # Test the graph creation
    graph = create_data_processing_graph()
    print("Graph created successfully!")
    
    # Test with sample data
    test_data = {
        "raw_data": {
            "id": "test_001",
            "name": "Test Strategy",
            "likes": 150,
            "description": " ".join(["word"] * 120),  # 120 words
            "code": "// This is a test\nstrategy('Test')\nplot(close)\n" + "x" * 100  # >100 chars
        },
        "status": "new"
    }
    
    try:
        result = graph.invoke(test_data)
        print("Test result:", result["status"])
    except Exception as e:
        print(f"Test failed: {e}")