"""
Description augmentation node using Best-of-N sampling.

This module generates N candidate description analyses and selects the best one
based on quality scoring.
"""

import json
from typing import Dict, Any, List, Optional
from llm_client import get_llm


def generate_description_analysis(
    raw_data: Dict[str, Any],
    llm,
    temperature: float = 0.8
) -> Dict[str, Any]:
    """
    Generate a single description analysis following the template structure.
    
    Args:
        raw_data: Raw trading indicator data
        llm: LLM client instance
        temperature: Sampling temperature
        
    Returns:
        Dictionary containing the structured analysis
    """
    # Extract relevant fields from raw data
    title = raw_data.get("name", "")
    description = raw_data.get("description", "")
    source_code = raw_data.get("source_code", "")
    
    # Create prompt based on template structure
    prompt = f"""Analyze the following trading indicator and create a structured analysis following this JSON template format:

Indicator Name: {title}

Description: {description[:2000]}...

Source Code (excerpt): {source_code[:1000]}...

Please generate a comprehensive JSON analysis with the following structure:
{{
  "title": "Indicator name",
  "abstract": "Brief summary of what the indicator does and its key features",
  "main_algorithms": {{
    "algorithms": "Detailed description of the algorithms and methods used"
  }},
  "key_concepts": [
    "List of key technical concepts",
    "Trading strategies",
    "Technical indicators used"
  ],
  "mathematical_models": [
    "Mathematical formulas used (if any)",
    "Calculation methods"
  ],
  "implementation_requirements": [
    "Required data sources",
    "Technical requirements"
  ],
  "evaluation_metrics": [
    "How to evaluate the indicator's performance"
  ],
  "datasets_mentioned": [
    "Data sources mentioned",
    "Timeframes",
    "Market types"
  ],
  "code_blocks": [],
  "high_level_logic": "Overall logic and workflow of the indicator",
  "required_modules": {{
    "packages_or_libs": "Required libraries or packages"
  }},
  "complexity_analysis": "Analysis of computational complexity",
  "novelty": "What makes this indicator unique or innovative",
  "content_preview": {{
    "title": "Indicator name",
    "authors": ["Author username"],
    "abstract_preview": "Short preview of functionality",
    "key_sections": ["Main features", "Usage", "Parameters"]
  }}
}}

Generate a detailed, accurate analysis in valid JSON format. Be specific and technical."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Try to extract JSON from response
        # Handle cases where LLM wraps JSON in markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        analysis = json.loads(content)
        return analysis
        
    except json.JSONDecodeError as e:
        # If JSON parsing fails, return a basic structure
        return {
            "title": title,
            "abstract": f"Error parsing analysis: {str(e)}",
            "main_algorithms": {"algorithms": "Parse error"},
            "key_concepts": [],
            "mathematical_models": [],
            "implementation_requirements": [],
            "evaluation_metrics": [],
            "datasets_mentioned": [],
            "code_blocks": [],
            "high_level_logic": "Error in generation",
            "required_modules": {"packages_or_libs": "Unknown"},
            "complexity_analysis": "Error",
            "novelty": "Error in generation",
            "content_preview": {
                "title": title,
                "authors": [raw_data.get("preview_author", "Unknown")],
                "abstract_preview": description[:200] if description else "",
                "key_sections": []
            },
            "parse_error": str(e),
            "raw_response": content[:500]
        }
    except Exception as e:
        # Handle other errors
        return {
            "title": title,
            "abstract": f"Error generating analysis: {str(e)}",
            "error": str(e)
        }


def score_description_analysis(analysis: Dict[str, Any]) -> float:
    """
    Score a description analysis based on completeness and quality.
    
    Args:
        analysis: The generated analysis dictionary
        
    Returns:
        Quality score (higher is better)
    """
    score = 0.0
    
    # Check if parsing was successful
    if "parse_error" in analysis or "error" in analysis:
        return score
    
    # Score based on presence and quality of key fields
    weights = {
        "title": 5.0,
        "abstract": 15.0,
        "main_algorithms": 15.0,
        "key_concepts": 10.0,
        "mathematical_models": 10.0,
        "implementation_requirements": 10.0,
        "evaluation_metrics": 5.0,
        "datasets_mentioned": 5.0,
        "high_level_logic": 15.0,
        "complexity_analysis": 5.0,
        "novelty": 10.0,
        "content_preview": 5.0
    }
    
    for field, weight in weights.items():
        if field in analysis:
            value = analysis[field]
            
            # Check if field has meaningful content
            if isinstance(value, str) and len(value) > 20:
                score += weight
            elif isinstance(value, dict) and value:
                # Check dictionary fields
                if field == "main_algorithms":
                    if "algorithms" in value and len(value["algorithms"]) > 30:
                        score += weight
                elif field == "required_modules":
                    if "packages_or_libs" in value and len(value["packages_or_libs"]) > 10:
                        score += weight
                elif field == "content_preview":
                    if "abstract_preview" in value and len(value.get("abstract_preview", "")) > 20:
                        score += weight
                else:
                    score += weight * 0.5
            elif isinstance(value, list) and len(value) > 0:
                # Score based on list length
                if len(value) >= 3:
                    score += weight
                elif len(value) >= 1:
                    score += weight * 0.5
    
    # Bonus for comprehensive key_concepts
    if "key_concepts" in analysis and isinstance(analysis["key_concepts"], list):
        if len(analysis["key_concepts"]) >= 5:
            score += 5.0
        if len(analysis["key_concepts"]) >= 10:
            score += 5.0
    
    # Bonus for having mathematical models
    if "mathematical_models" in analysis and isinstance(analysis["mathematical_models"], list):
        if len(analysis["mathematical_models"]) >= 3:
            score += 5.0
    
    return score


def augment_description_best_of_n(
    raw_data: Dict[str, Any],
    n: Optional[int] = None,
    temperature: float = 0.8,
    node_name: str = "data_aug_description"
) -> Dict[str, Any]:
    """
    Generate N candidate description analyses and select the best one.
    
    Uses Best-of-N sampling to generate multiple candidates and selects
    the highest quality analysis based on completeness and structure.
    
    Args:
        raw_data: Raw trading indicator data
        n: Number of candidates to generate (from config if not specified)
        temperature: Sampling temperature for generation
        node_name: Node name for LLM configuration
        
    Returns:
        Dictionary containing the best analysis and metadata
    """
    from config import BEST_OF_N
    
    if n is None:
        n = BEST_OF_N
    
    # Get LLM client
    llm = get_llm(node_name=node_name)
    
    print(f"  Generating {n} candidate analyses...")
    
    # Generate N candidates
    candidates = []
    for i in range(n):
        print(f"    Candidate {i+1}/{n}...", end=" ")
        analysis = generate_description_analysis(raw_data, llm, temperature)
        score = score_description_analysis(analysis)
        candidates.append({
            "analysis": analysis,
            "score": score,
            "candidate_id": i
        })
        print(f"Score: {score:.2f}")
    
    # Select best candidate
    best_candidate = max(candidates, key=lambda x: x["score"])
    
    print(f"  Selected candidate {best_candidate['candidate_id']+1} with score {best_candidate['score']:.2f}")
    
    # Return best analysis with metadata
    return {
        "best_analysis": best_candidate["analysis"],
        "best_score": best_candidate["score"],
        "candidate_id": best_candidate["candidate_id"],
        "all_scores": [c["score"] for c in candidates],
        "num_candidates": n
    }


if __name__ == "__main__":
    # Test the module
    test_data = {
        "name": "Test Indicator",
        "description": "This is a test trading indicator for demonstration purposes.",
        "source_code": "// Test Pine Script code\nindicator('Test')\nplot(close)",
        "preview_author": "test_user"
    }
    
    print("Testing description augmentation with Best-of-N...")
    result = augment_description_best_of_n(test_data, n=2)
    print(f"\nBest score: {result['best_score']}")
    print(f"All scores: {result['all_scores']}")
    print(f"\nBest analysis keys: {list(result['best_analysis'].keys())}")
