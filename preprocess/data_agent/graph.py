"""LangGraph workflow definition for trading data processing."""
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from llm_client import get_llm
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from code.pyne_backend import converter as pyne_converter
from code.pyne_backend import validator as pyne_validator
from code.backtrader_backend import converter as bt_converter
from code.backtrader_backend import validator as bt_validator
from config import BACKEND
from config import DEBUG_NODE_OUTPUT
import json
from nodes.aug_description import augment_description_best_of_n
from nodes.symbol_infer import infer_relevant_symbols, extract_symbols_list
from nodes.filter import filter_data
from nodes.classify import run as classify_node


# Define the state structure for data processing
class DataProcessingState(TypedDict):
    """State structure for data processing workflow."""
    raw_data: Dict[str, Any]  # Current item being processed
    filter_result: Optional[bool]  # Whether to keep the data
    converted_code: Optional[str]  # Converted pyne script
    validation_result: Optional[bool]  # Whether the conversion is valid
    augmented_description: Optional[str]  # Enhanced description
    description_metadata: Optional[Dict[str, Any]]  # Metadata from best-of-N selection
    reasoning: Optional[str]  # Reasoning process
    relevant_symbols: Optional[List[str]]  # Inferred trading symbols
    symbol_metadata: Optional[Dict[str, Any]]  # Symbol inference metadata
    conversion_attempts: int  # Number of conversion attempts
    error_message: Optional[str]  # Error message if any
    status: str  # Current processing status


def filter_node(state: DataProcessingState) -> DataProcessingState:
    """
    Filter node: Determine whether to keep the current data.
    
    Applies two checks:
    1. Word count check: Description must have >= MIN_DESCRIPTION_WORDS
    2. Quality check: LLM evaluates if description has sufficient indicator and strategy details
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with filter result
    """
    from config import MIN_DESCRIPTION_WORDS
    
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: filter | id={item_id} | name={item_name}")

    try:
        # Use the filter_data function from nodes.filter
        result = filter_data(
            raw_data=state["raw_data"],
            min_words=MIN_DESCRIPTION_WORDS
        )
        
        should_keep = result["should_keep"]
        rejection_reason = result.get("rejection_reason", "")
        
        # Log filtering decision
        if not should_keep:
            item_name = state["raw_data"].get("name", "Unknown")
            print(f"  ✗ Filtered out: {item_name}")
            if result.get("word_check"):
                print(f"    - Word count: {result['word_check']['word_count']} words")
            if result.get("quality_check"):
                print(f"    - Quality score: {result['quality_check']['score']}/100")
            if rejection_reason:
                print(f"    - Reason: {rejection_reason[:100]}...")
        
        out = {
            "filter_result": should_keep,
            "status": "filtered" if should_keep else "rejected_by_filter",
            "error_message": rejection_reason if not should_keep else None
        }
        if DEBUG_NODE_OUTPUT:
            print(f"  [DEBUG OUTPUT] filter -> {out}")
        return out
        
    except Exception as e:
        # On error, reject to be safe
        print(f"  Error in filter node: {str(e)}")
        return {
            "filter_result": False,
            "status": "filter_error",
            "error_message": f"Filter error: {str(e)}"
        }


def code_converter_node(state: DataProcessingState) -> DataProcessingState:
    """
    Code converter node: Convert Pine Script to Pyne Script with self-verification.
    Allows up to 5 attempts for successful conversion.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with converted code
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: code_converter | id={item_id} | name={item_name}")

    # TODO: Implement Pine Script to Pyne Script conversion with self-verification
    # This is a placeholder that shows the structure
    
    attempts = state.get("conversion_attempts", 0)
    source_code = state["raw_data"].get("source_code", "")
    # If validator produced feedback on previous attempt, pass it to converter
    feedback = state.get("error_message")
    
    if not source_code:
        return {
            "converted_code": None,
            "conversion_attempts": attempts + 1,
            "error_message": "No source code found",
            "status": "conversion_failed"
        }
    
    # Choose backend per configuration
    backend_choice = BACKEND

    if backend_choice == "pyne":
        # Pass validator feedback to the LLM converter when present to guide fixes
        resp = pyne_converter.convert(source_code, node_name="code_converter", feedback=feedback)
    else:
        resp = bt_converter.convert(source_code, node_name="code_converter", feedback=feedback)

    out = None
    if resp.get("converted_code"):
        out = {
            "converted_code": resp["converted_code"],
            "conversion_attempts": attempts + 1,
            "status": "converted",
            "llm_preview": resp.get("llm_response")
        }
    else:
        out = {
            "converted_code": None,
            "conversion_attempts": attempts + 1,
            "error_message": resp.get("error", "Conversion failed"),
            "status": "conversion_error"
        }
    if DEBUG_NODE_OUTPUT:
        debug = {"status": out.get("status"), "error": out.get("error_message", None), "attempt": attempts + 1}
        if out.get("llm_preview"):
            debug["llm_preview_len"] = len(out.get("llm_preview"))
        print(f"  [DEBUG OUTPUT] code_converter -> {debug}")
    return out


def code_validator_node(state: DataProcessingState) -> DataProcessingState:
    """
    Code validator node: Validate the converted code.
    Checks if conversion was successful and if the generated code matches the original intent.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with validation result
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: code_validator | id={item_id} | name={item_name}")

    converted_code = state.get("converted_code")
    
    if not converted_code:
        return {
            "validation_result": False,
            "status": "validation_failed"
        }
    
    # Choose backend validator (match converter choice)
    backend_choice = BACKEND
    original_code = state["raw_data"].get("source_code", "")

    if backend_choice == "pyne":
        result = pyne_validator.validate(original_code, converted_code, node_name="code_validator")
    else:
        result = bt_validator.validate(original_code, converted_code, node_name="code_validator")

    out = None
    if result.get("valid"):
        out = {
            "validation_result": True,
            "status": "validated",
            "validation_reason": result.get("reason", "")
        }
    else:
        # On validation failure provide feedback to the converter (reason) so converter can try again
        out = {
            "validation_result": False,
            "error_message": result.get("reason", "Validation failed"),
            "status": "validation_rejected"
        }
    if DEBUG_NODE_OUTPUT:
        debug = {"status": out.get("status"), "reason": (out.get("error_message", "") or "")[:200]}
        # Also include attempt number if present
        debug["attempt"] = state.get("conversion_attempts", 0)
        print(f"  [DEBUG OUTPUT] code_validator -> {debug}")
    return out


def data_aug_description_node(state: DataProcessingState) -> DataProcessingState:
    """
    Data augmentation (description) node: Enhance the description field using Best-of-N.
    
    Generates N candidate analyses and selects the best one based on quality scoring.
    Uses the document_analysis.json template structure.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with augmented description
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: data_aug_description | id={item_id} | name={item_name}")

    try:
        # Use Best-of-N to generate enhanced description analysis
        result = augment_description_best_of_n(
            raw_data=state["raw_data"],
            node_name="data_aug_description"
        )
        
        # Convert best analysis to JSON string for storage
        augmented_description = json.dumps(result["best_analysis"], indent=2)
        out = {
            "augmented_description": augmented_description,
            "status": "description_processed",
            "description_metadata": {
                "best_score": result["best_score"],
                "candidate_id": result["candidate_id"],
                "all_scores": result["all_scores"],
                "num_candidates": result["num_candidates"]
            }
        }
        if DEBUG_NODE_OUTPUT:
            debug = {"best_score": result.get("best_score")}
            print(f"  [DEBUG OUTPUT] data_aug_description -> {debug}")
        return out
    except Exception as e:
        # Fallback to original description on error
        original_desc = state["raw_data"].get("description", "")
        return {
            "augmented_description": original_desc,
            "status": "description_error",
            "error_message": f"Description augmentation failed: {str(e)}"
        }


def symbol_infer_node(state: DataProcessingState) -> DataProcessingState:
    """
    Symbol inference node: Infer relevant trading symbols from the description.
    
    Analyzes the strategy description to identify which trading symbols
    or asset pairs are relevant (e.g., USDT, BTC, ETH).
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with relevant_symbols
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: symbol_infer | id={item_id} | name={item_name}")

    try:
        # Get the description to analyze
        description = state.get("augmented_description") or state["raw_data"].get("description", "")
        name = state["raw_data"].get("name", "")
        
        # Use symbol inference
        result = infer_relevant_symbols(
            description=description,
            name=name
        )
        
        # Extract symbols list
        symbols = extract_symbols_list(result)
        
        out = {
            "relevant_symbols": symbols,
            "symbol_metadata": {
                "confidence": result.get("confidence", "low"),
                "reasoning": result.get("reasoning", "")
            },
            "status": "symbols_inferred"
        }
        if DEBUG_NODE_OUTPUT:
            debug = {"symbols": symbols}
            print(f"  [DEBUG OUTPUT] symbol_infer -> {debug}")
        return out
    except Exception as e:
        print(f"Error in symbol inference: {str(e)}")
        return {
            "relevant_symbols": [],
            "symbol_metadata": {
                "confidence": "low",
                "reasoning": f"Error: {str(e)}"
            },
            "status": "symbol_inference_error",
            "error_message": f"Symbol inference failed: {str(e)}"
        }


def data_aug_reason_node(state: DataProcessingState) -> DataProcessingState:
    """
    Data augmentation (reasoning) node: Add reasoning process to the data.
    Adds an empty reasoning field by default.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state with reasoning
    """
    # Log node entry
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: data_aug_reason | id={item_id} | name={item_name}")

    # Default: add empty reasoning field
    # TODO: Add LLM-based reasoning generation if needed
    out = {"reasoning": "", "status": "reasoning_added"}
    if DEBUG_NODE_OUTPUT:
        print(f"  [DEBUG OUTPUT] data_aug_reason -> {out}")
    return out


def should_retry_conversion(state: DataProcessingState) -> str:
    """
    Determine if code conversion should be retried.
    
    Args:
        state: Current processing state
        
    Returns:
        Next node name
    """
    from config import MAX_CONVERSION_ATTEMPTS
    
    attempts = state.get("conversion_attempts", 0)
    converted_code = state.get("converted_code")
    
    # If conversion succeeded, move to validation
    if converted_code:
        return "code_validator"
    
    # If max attempts reached, reject the data
    if attempts >= MAX_CONVERSION_ATTEMPTS:
        return "reject"
    
    # Otherwise, retry conversion
    return "code_converter"


def should_continue_after_validation(state: DataProcessingState) -> str:
    """
    Determine next step after validation.
    
    Args:
        state: Current processing state
        
    Returns:
        Next node name
    """
    validation_result = state.get("validation_result", False)
    
    if validation_result:
        return "data_aug_description"
    else:
        return "reject"


def should_classify_continue(state: DataProcessingState) -> str:
    """
    Determine next step after classification.
    
    Args:
        state: Current processing state
        
    Returns:
        Next node name
    """
    status = state.get("status", "")
    
    if status == "rejected_by_classifier":
        return "reject"
    else:
        return "filter"


def should_filter(state: DataProcessingState) -> str:
    """
    Determine if data should be kept after filtering.
    
    Args:
        state: Current processing state
        
    Returns:
        Next node name
    """
    filter_result = state.get("filter_result", False)
    
    if filter_result:
        return "code_converter"
    else:
        return "reject"


def reject_node(state: DataProcessingState) -> DataProcessingState:
    """
    Reject node: Mark data as rejected.
    
    Args:
        state: Current processing state
        
    Returns:
        Updated state marked as rejected
    """
    # Log node entry for rejected items
    raw = state.get("raw_data", {}) or {}
    item_id = raw.get("id", "<no-id>")
    item_name = raw.get("name", "<no-name>")
    print(f"  -> Node: reject | id={item_id} | name={item_name}")
    out = {"status": "rejected"}
    if DEBUG_NODE_OUTPUT:
        print(f"  [DEBUG OUTPUT] reject -> {out}")
    return out


def create_data_processing_graph():
    """
    Create and compile the data processing workflow graph.
    
    The workflow includes:
    - filter: Determine if data should be processed
    - code_converter: Convert Pine Script to Pyne Script (up to 5 attempts)
    - code_validator: Validate the converted code
    - data_aug_description: Enhance description field (Best-of-N)
    - symbol_infer: Infer relevant trading symbols from description
    - data_aug_reason: Add reasoning to the data
    
    Returns:
        Compiled graph for data processing
    """
    workflow = StateGraph(DataProcessingState)
    
    # Add all nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("filter", filter_node)
    workflow.add_node("code_converter", code_converter_node)
    workflow.add_node("code_validator", code_validator_node)
    workflow.add_node("data_aug_description", data_aug_description_node)
    workflow.add_node("symbol_infer", symbol_infer_node)
    workflow.add_node("data_aug_reason", data_aug_reason_node)
    workflow.add_node("reject", reject_node)
    
    # Set entry point to classification node
    workflow.set_entry_point("classify")

    # After classify, either reject immediately or continue to filter
    workflow.add_conditional_edges(
        "classify",
        should_classify_continue,
        {
            "filter": "filter",
            "reject": "reject"
        }
    )
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "filter",
        should_filter,
        {
            "code_converter": "code_converter",
            "reject": "reject"
        }
    )
    
    workflow.add_conditional_edges(
        "code_converter",
        should_retry_conversion,
        {
            "code_converter": "code_converter",
            "code_validator": "code_validator",
            "reject": "reject"
        }
    )
    
    workflow.add_conditional_edges(
        "code_validator",
        should_continue_after_validation,
        {
            "data_aug_description": "data_aug_description",
            "reject": "reject"
        }
    )
    
    # Linear flow after validation passes
    # description -> symbol_infer -> reasoning -> END
    workflow.add_edge("data_aug_description", "symbol_infer")
    workflow.add_edge("symbol_infer", "data_aug_reason")
    workflow.add_edge("data_aug_reason", END)
    workflow.add_edge("reject", END)
    
    # Compile the graph
    graph = workflow.compile()
    return graph


if __name__ == "__main__":
    # Test the graph with sample data
    graph = create_data_processing_graph()
    
    sample_data = {
        "id": "test-123",
        "name": "Test Indicator",
        "description": "A test trading indicator",
        "source_code": "// Pine Script code here"
    }
    
    initial_state = {
        "raw_data": sample_data,
        "filter_result": None,
        "converted_code": None,
        "validation_result": None,
        "augmented_description": None,
        "reasoning": None,
        "conversion_attempts": 0,
        "error_message": None,
        "status": "pending"
    }
    
    print("\n=== Testing Data Processing Graph ===")
    result = graph.invoke(initial_state)
    print(f"Final Status: {result['status']}")
    print(f"Conversion Attempts: {result['conversion_attempts']}")
    if result.get("error_message"):
        print(f"Error: {result['error_message']}")
