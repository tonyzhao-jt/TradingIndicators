"""Visualize the data processing workflow graph."""
from graph import create_data_processing_graph


def visualize():
    """Generate and display the workflow graph visualization."""
    try:
        from IPython.display import Image, display
        
        graph = create_data_processing_graph()
        
        # Generate graph visualization
        png_data = graph.get_graph().draw_mermaid_png()
        
        # Save to file
        output_file = "workflow_graph.png"
        with open(output_file, "wb") as f:
            f.write(png_data)
        
        print(f"Graph visualization saved to: {output_file}")
        
        # Try to display if in notebook
        try:
            display(Image(png_data))
        except:
            print("(Display requires Jupyter notebook environment)")
            
    except ImportError:
        print("Mermaid visualization requires additional dependencies.")
        print("For ASCII representation, use: graph.get_graph().print_ascii()")
        
        # Print ASCII representation
        graph = create_data_processing_graph()
        print("\n" + "="*70)
        print("Workflow Graph Structure")
        print("="*70)
        print(graph.get_graph())


def print_workflow_description():
    """Print a text description of the workflow."""
    description = """
    Data Processing Workflow
    ========================
    
    Entry Point: filter
    
    Node: filter
      Description: Determine whether to keep the current data
      Next: 
        - If PASS → code_converter
        - If REJECT → reject (END)
    
    Node: code_converter
      Description: Convert Pine Script to Pyne Script with self-verification
      Max Attempts: 5
      Next:
        - If SUCCESS → code_validator
        - If FAILED and attempts < 5 → retry code_converter
        - If FAILED and attempts >= 5 → reject (END)
    
    Node: code_validator
      Description: Validate converted code semantics
      Next:
        - If VALID → data_aug_description
        - If INVALID → reject (END)
    
    Node: data_aug_description
      Description: Enhance the description field
      Next: data_aug_reason
    
    Node: data_aug_reason
      Description: Add reasoning process to the data
      Next: END (Success)
    
    Node: reject
      Description: Mark data as rejected
      Next: END (Rejected)
    
    Output: Processed data saved to Parquet files
    """
    print(description)


if __name__ == "__main__":
    print("Generating workflow visualization...\n")
    print_workflow_description()
    print("\n" + "="*70 + "\n")
    visualize()
