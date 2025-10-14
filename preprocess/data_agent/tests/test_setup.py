#!/usr/bin/env python
"""
Simple test script to verify the data processing pipeline setup.
"""

import sys
import os
from pathlib import Path


def test_imports():
    """Test if all required packages are installed."""
    print("Testing imports...")
    try:
        import langgraph
        print("  ✓ langgraph")
    except ImportError:
        print("  ✗ langgraph - Please run: pip install langgraph")
        return False
    
    try:
        import langchain
        print("  ✓ langchain")
    except ImportError:
        print("  ✗ langchain - Please run: pip install langchain")
        return False
    
    try:
        import langchain_openai
        print("  ✓ langchain-openai")
    except ImportError:
        print("  ✗ langchain-openai - Please run: pip install langchain-openai")
        return False
    
    try:
        import pandas
        print("  ✓ pandas")
    except ImportError:
        print("  ✗ pandas - Please run: pip install pandas")
        return False
    
    try:
        import pyarrow
        print("  ✓ pyarrow")
    except ImportError:
        print("  ✗ pyarrow - Please run: pip install pyarrow")
        return False
    
    try:
        import tqdm
        print("  ✓ tqdm")
    except ImportError:
        print("  ✗ tqdm - Please run: pip install tqdm")
        return False
    
    return True


def test_config():
    """Test if configuration is loaded correctly."""
    print("\nTesting configuration...")
    try:
        from config import (
            LOCAL_QWEN_ENDPOINT,
            LOCAL_QWEN_MODEL_NAME,
            LOCAL_QWEN_API_KEY,
            BATCH_SIZE,
            NODE_MODELS
        )
        print(f"  ✓ Configuration loaded")
        print(f"    - Endpoint: {LOCAL_QWEN_ENDPOINT}")
        print(f"    - Model: {LOCAL_QWEN_MODEL_NAME}")
        print(f"    - Batch Size: {BATCH_SIZE}")
        print(f"    - Configured Nodes: {len(NODE_MODELS)}")
        return True
    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        return False


def test_llm_client():
    """Test if LLM client can be created."""
    print("\nTesting LLM client...")
    try:
        from llm_client import get_llm
        
        # Test default LLM
        llm = get_llm()
        print("  ✓ Default LLM client created")
        
        # Test node-specific LLM
        llm_filter = get_llm(node_name="filter")
        print("  ✓ Filter node LLM client created")
        
        llm_converter = get_llm(node_name="code_converter")
        print("  ✓ Code converter node LLM client created")
        
        return True
    except Exception as e:
        print(f"  ✗ LLM client error: {e}")
        return False


def test_graph_creation():
    """Test if workflow graph can be created."""
    print("\nTesting graph creation...")
    try:
        from graph import create_data_processing_graph
        
        graph = create_data_processing_graph()
        print("  ✓ Workflow graph created successfully")
        
        # Get node information
        nodes = graph.get_graph().nodes
        print(f"    - Total nodes: {len(nodes)}")
        print(f"    - Nodes: {list(nodes.keys())}")
        
        return True
    except Exception as e:
        print(f"  ✗ Graph creation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_processor():
    """Test if DataProcessor can be initialized."""
    print("\nTesting DataProcessor...")
    try:
        # Create a dummy test file
        test_file = Path("/tmp/test_input.json")
        import json
        test_data = [{
            "id": "test-123",
            "name": "Test Indicator",
            "description": "Test description",
            "source_code": "// Test code"
        }]
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        from main import DataProcessor
        
        processor = DataProcessor(str(test_file), output_dir="/tmp/test_output")
        print("  ✓ DataProcessor initialized")
        
        # Clean up
        test_file.unlink()
        
        return True
    except Exception as e:
        print(f"  ✗ DataProcessor error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_output_directory():
    """Test if output directory can be created."""
    print("\nTesting output directory...")
    try:
        from config import OUTPUT_DIR
        output_path = Path(OUTPUT_DIR)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Output directory: {output_path}")
        print(f"    - Exists: {output_path.exists()}")
        print(f"    - Writable: {os.access(output_path, os.W_OK)}")
        return True
    except Exception as e:
        print(f"  ✗ Output directory error: {e}")
        return False


def test_input_files():
    """Test if input files exist."""
    print("\nChecking for input files...")
    from config import INPUT_DIR
    input_path = Path(INPUT_DIR)
    
    if not input_path.exists():
        print(f"  ! Input directory does not exist: {input_path}")
        return True  # Not critical
    
    json_files = list(input_path.glob("*.json"))
    print(f"  ✓ Input directory: {input_path}")
    print(f"    - JSON files found: {len(json_files)}")
    
    if json_files:
        print(f"    - Example: {json_files[0].name}")
    
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("Data Processing Pipeline - Setup Verification")
    print("="*70)
    
    tests = [
        ("Package imports", test_imports),
        ("Configuration", test_config),
        ("LLM client", test_llm_client),
        ("Graph creation", test_graph_creation),
        ("DataProcessor", test_data_processor),
        ("Output directory", test_output_directory),
        ("Input files", test_input_files),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Unexpected error in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("-"*70)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! The pipeline is ready to use.")
        print("\nNext steps:")
        print("  1. Run: ./run.sh test-llm")
        print("  2. Run: ./run.sh test-graph")
        print("  3. Run: ./run.sh process <input_file>")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install missing packages: pip install -r requirements.txt")
        print("  - Check .env file configuration")
        print("  - Verify model endpoint is accessible")
        return 1


if __name__ == "__main__":
    sys.exit(main())
