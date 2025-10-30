#!/usr/bin/env python3
"""
Model Evaluator for Comparing Two Models
Supports inference on different machines and comparison of generation results.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from datasets import Dataset
from tqdm import tqdm
import numpy as np
from difflib import unified_diff
import hashlib


class ModelInferencer:
    """Handles model loading and inference."""
    
    def __init__(
        self,
        model_path: str,
        device: str = "auto",
        dtype: str = "auto",
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        trust_remote_code: bool = True
    ):
        """
        Initialize model for inference.
        
        Args:
            model_path: Path to the model (local or HuggingFace)
            device: Device to load model on ("auto", "cuda", "cpu")
            dtype: Data type for model ("auto", "float16", "bfloat16", "float32")
            load_in_8bit: Load model in 8-bit quantization
            load_in_4bit: Load model in 4-bit quantization
            trust_remote_code: Trust remote code from HuggingFace
        """
        self.model_path = model_path
        self.device = device
        self.dtype = dtype
        
        print(f"\n{'='*80}")
        print(f"Loading model: {model_path}")
        print(f"{'='*80}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=trust_remote_code
        )
        
        # Ensure pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Prepare model loading kwargs
        model_kwargs = {
            "trust_remote_code": trust_remote_code,
        }
        
        # Set dtype
        if dtype == "float16":
            model_kwargs["torch_dtype"] = torch.float16
        elif dtype == "bfloat16":
            model_kwargs["torch_dtype"] = torch.bfloat16
        elif dtype == "float32":
            model_kwargs["torch_dtype"] = torch.float32
        
        # Set device
        if device == "auto":
            model_kwargs["device_map"] = "auto"
        elif device == "cuda":
            if not torch.cuda.is_available():
                print("Warning: CUDA not available, falling back to CPU")
                device = "cpu"
        
        # Quantization
        if load_in_8bit:
            model_kwargs["load_in_8bit"] = True
        elif load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        
        # Load model
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            **model_kwargs
        )
        
        # Move to device if not using device_map
        if device != "auto" and not (load_in_8bit or load_in_4bit):
            self.model = self.model.to(device)
        
        self.model.eval()
        
        print(f"✓ Model loaded successfully")
        print(f"Device: {next(self.model.parameters()).device}")
        print(f"Dtype: {next(self.model.parameters()).dtype}")
        print(f"{'='*80}\n")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        do_sample: bool = True,
        num_return_sequences: int = 1,
        **kwargs
    ) -> List[str]:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            do_sample: Whether to use sampling
            num_return_sequences: Number of sequences to generate
            **kwargs: Additional generation parameters
            
        Returns:
            List of generated texts
        """
        # Tokenize input
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        
        # Move to device
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                do_sample=do_sample,
                num_return_sequences=num_return_sequences,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                **kwargs
            )
        
        # Decode outputs
        generated_texts = []
        for output in outputs:
            # Remove input tokens
            generated = output[inputs["input_ids"].shape[1]:]
            text = self.tokenizer.decode(generated, skip_special_tokens=True)
            generated_texts.append(text)
        
        return generated_texts
    
    def batch_generate(
        self,
        prompts: List[str],
        batch_size: int = 4,
        **generation_kwargs
    ) -> List[List[str]]:
        """
        Generate text for multiple prompts in batches.
        
        Args:
            prompts: List of input prompts
            batch_size: Batch size for generation
            **generation_kwargs: Generation parameters
            
        Returns:
            List of lists of generated texts
        """
        all_results = []
        
        for i in tqdm(range(0, len(prompts), batch_size), desc="Generating"):
            batch_prompts = prompts[i:i + batch_size]
            
            for prompt in batch_prompts:
                results = self.generate(prompt, **generation_kwargs)
                all_results.append(results)
        
        return all_results


class ModelComparator:
    """Compare outputs from two models."""
    
    def __init__(self, model1_name: str, model2_name: str):
        """
        Initialize comparator.
        
        Args:
            model1_name: Name/identifier for first model
            model2_name: Name/identifier for second model
        """
        self.model1_name = model1_name
        self.model2_name = model2_name
    
    def compare_outputs(
        self,
        prompts: List[str],
        model1_outputs: List[List[str]],
        model2_outputs: List[List[str]]
    ) -> Dict[str, Any]:
        """
        Compare outputs from two models.
        
        Args:
            prompts: Input prompts
            model1_outputs: Outputs from model 1
            model2_outputs: Outputs from model 2
            
        Returns:
            Comparison results dictionary
        """
        comparisons = []
        
        for i, (prompt, out1, out2) in enumerate(zip(prompts, model1_outputs, model2_outputs)):
            # Take first output if multiple sequences
            output1 = out1[0] if isinstance(out1, list) else out1
            output2 = out2[0] if isinstance(out2, list) else out2
            
            # Calculate metrics
            comparison = {
                "index": i,
                "prompt": prompt,
                f"{self.model1_name}_output": output1,
                f"{self.model2_name}_output": output2,
                "output_length_diff": len(output1) - len(output2),
                "are_identical": output1 == output2,
                "similarity_score": self._calculate_similarity(output1, output2),
                "diff": self._generate_diff(output1, output2)
            }
            
            comparisons.append(comparison)
        
        # Generate summary statistics
        summary = {
            "total_comparisons": len(comparisons),
            "identical_outputs": sum(c["are_identical"] for c in comparisons),
            "avg_similarity": np.mean([c["similarity_score"] for c in comparisons]),
            "avg_length_diff": np.mean([abs(c["output_length_diff"]) for c in comparisons]),
            f"avg_{self.model1_name}_length": np.mean([len(c[f"{self.model1_name}_output"]) for c in comparisons]),
            f"avg_{self.model2_name}_length": np.mean([len(c[f"{self.model2_name}_output"]) for c in comparisons]),
        }
        
        return {
            "summary": summary,
            "comparisons": comparisons,
            "model1_name": self.model1_name,
            "model2_name": self.model2_name,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two texts."""
        if text1 == text2:
            return 1.0
        
        # Simple character-based similarity
        len1, len2 = len(text1), len(text2)
        if len1 == 0 and len2 == 0:
            return 1.0
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Use difflib for sequence matching
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def _generate_diff(self, text1: str, text2: str) -> str:
        """Generate unified diff between two texts."""
        if text1 == text2:
            return "No differences"
        
        diff = unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=self.model1_name,
            tofile=self.model2_name,
            lineterm=""
        )
        
        return "".join(diff)
    
    def save_comparison(self, results: Dict[str, Any], output_path: str):
        """Save comparison results to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Comparison results saved to: {output_file}")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print comparison summary."""
        summary = results["summary"]
        
        print(f"\n{'='*80}")
        print(f"COMPARISON SUMMARY")
        print(f"{'='*80}")
        print(f"Model 1: {results['model1_name']}")
        print(f"Model 2: {results['model2_name']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"{'-'*80}")
        print(f"Total comparisons: {summary['total_comparisons']}")
        print(f"Identical outputs: {summary['identical_outputs']} ({summary['identical_outputs']/summary['total_comparisons']*100:.1f}%)")
        print(f"Average similarity: {summary['avg_similarity']:.3f}")
        print(f"Average length difference: {summary['avg_length_diff']:.1f} chars")
        print(f"Average {results['model1_name']} output length: {summary[f'avg_{results[\"model1_name\"]}_length']:.1f} chars")
        print(f"Average {results['model2_name']} output length: {summary[f'avg_{results[\"model2_name\"]}_length']:.1f} chars")
        print(f"{'='*80}\n")


def load_test_data(data_path: str, max_samples: Optional[int] = None) -> List[str]:
    """Load test data from JSON file."""
    print(f"\nLoading test data from: {data_path}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract prompts based on data structure
    prompts = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Try different possible prompt fields
                prompt = item.get('input') or item.get('prompt') or item.get('instruction') or item.get('query')
                if prompt:
                    prompts.append(prompt)
            elif isinstance(item, str):
                prompts.append(item)
    elif isinstance(data, dict):
        # Handle dictionary with multiple entries
        for key, value in data.items():
            if isinstance(value, str):
                prompts.append(value)
    
    if max_samples:
        prompts = prompts[:max_samples]
    
    print(f"✓ Loaded {len(prompts)} prompts")
    
    return prompts


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare two models by running inference and analyzing outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two models
  python evaluator.py \\
    --model1_path "./model_cache/model1" \\
    --model2_path "./model_cache/model2" \\
    --data_path "./test_data.json" \\
    --output_path "./comparison_results.json"
  
  # Compare with custom generation parameters
  python evaluator.py \\
    --model1_path "Qwen/Qwen2.5-Coder-7B" \\
    --model2_path "./pine-coder-mid" \\
    --data_path "/workspace/trading_indicators/outputs/segments_20251014.json" \\
    --max_samples 50 \\
    --temperature 0.7 \\
    --max_new_tokens 512
  
  # Load models in 4-bit for lower memory usage
  python evaluator.py \\
    --model1_path "./model1" \\
    --model2_path "./model2" \\
    --data_path "./test_data.json" \\
    --load_in_4bit
        """
    )
    
    # Model arguments
    parser.add_argument(
        "--model1_path",
        type=str,
        required=True,
        help="Path to first model (local path or HuggingFace model name)"
    )
    parser.add_argument(
        "--model2_path",
        type=str,
        required=True,
        help="Path to second model (local path or HuggingFace model name)"
    )
    parser.add_argument(
        "--model1_name",
        type=str,
        help="Display name for model 1 (default: basename of model1_path)"
    )
    parser.add_argument(
        "--model2_name",
        type=str,
        help="Display name for model 2 (default: basename of model2_path)"
    )
    
    # Data arguments
    parser.add_argument(
        "--data_path",
        type=str,
        required=True,
        help="Path to test data JSON file"
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        help="Maximum number of samples to evaluate (default: all)"
    )
    
    # Generation arguments
    parser.add_argument(
        "--max_new_tokens",
        type=int,
        default=512,
        help="Maximum number of new tokens to generate (default: 512)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)"
    )
    parser.add_argument(
        "--top_p",
        type=float,
        default=0.9,
        help="Nucleus sampling parameter (default: 0.9)"
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=50,
        help="Top-k sampling parameter (default: 50)"
    )
    parser.add_argument(
        "--do_sample",
        action="store_true",
        default=True,
        help="Use sampling for generation (default: True)"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=1,
        help="Batch size for generation (default: 1)"
    )
    
    # Model loading arguments
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device to load models on (default: auto)"
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="auto",
        choices=["auto", "float16", "bfloat16", "float32"],
        help="Data type for models (default: auto)"
    )
    parser.add_argument(
        "--load_in_8bit",
        action="store_true",
        help="Load models in 8-bit quantization"
    )
    parser.add_argument(
        "--load_in_4bit",
        action="store_true",
        help="Load models in 4-bit quantization"
    )
    
    # Output arguments
    parser.add_argument(
        "--output_path",
        type=str,
        default="./comparison_results.json",
        help="Path to save comparison results (default: ./comparison_results.json)"
    )
    parser.add_argument(
        "--save_outputs",
        action="store_true",
        default=True,
        help="Save individual model outputs to separate files"
    )
    
    return parser.parse_args()


def main():
    """Main evaluation function."""
    args = parse_args()
    
    # Set model names
    model1_name = args.model1_name or Path(args.model1_path).name
    model2_name = args.model2_name or Path(args.model2_path).name
    
    print(f"\n{'='*80}")
    print(f"MODEL EVALUATION AND COMPARISON")
    print(f"{'='*80}")
    print(f"Model 1: {model1_name} ({args.model1_path})")
    print(f"Model 2: {model2_name} ({args.model2_path})")
    print(f"Test data: {args.data_path}")
    print(f"{'='*80}\n")
    
    # Load test data
    prompts = load_test_data(args.data_path, args.max_samples)
    
    if not prompts:
        print("Error: No prompts found in test data")
        return
    
    # Generation parameters
    gen_kwargs = {
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "do_sample": args.do_sample,
    }
    
    print(f"\nGeneration parameters:")
    for k, v in gen_kwargs.items():
        print(f"  {k}: {v}")
    print()
    
    # Load models and run inference
    print(f"\n{'='*80}")
    print(f"LOADING MODELS AND RUNNING INFERENCE")
    print(f"{'='*80}\n")
    
    # Model 1 inference
    print(f"[1/2] Running inference with {model1_name}...")
    inferencer1 = ModelInferencer(
        model_path=args.model1_path,
        device=args.device,
        dtype=args.dtype,
        load_in_8bit=args.load_in_8bit,
        load_in_4bit=args.load_in_4bit
    )
    model1_outputs = inferencer1.batch_generate(
        prompts,
        batch_size=args.batch_size,
        **gen_kwargs
    )
    
    # Clear GPU memory if using CUDA
    if torch.cuda.is_available():
        del inferencer1
        torch.cuda.empty_cache()
    
    # Model 2 inference
    print(f"\n[2/2] Running inference with {model2_name}...")
    inferencer2 = ModelInferencer(
        model_path=args.model2_path,
        device=args.device,
        dtype=args.dtype,
        load_in_8bit=args.load_in_8bit,
        load_in_4bit=args.load_in_4bit
    )
    model2_outputs = inferencer2.batch_generate(
        prompts,
        batch_size=args.batch_size,
        **gen_kwargs
    )
    
    # Clear GPU memory
    if torch.cuda.is_available():
        del inferencer2
        torch.cuda.empty_cache()
    
    # Compare outputs
    print(f"\n{'='*80}")
    print(f"COMPARING OUTPUTS")
    print(f"{'='*80}\n")
    
    comparator = ModelComparator(model1_name, model2_name)
    results = comparator.compare_outputs(prompts, model1_outputs, model2_outputs)
    
    # Save results
    comparator.save_comparison(results, args.output_path)
    
    # Save individual outputs if requested
    if args.save_outputs:
        output_dir = Path(args.output_path).parent
        
        # Save model 1 outputs
        model1_output_file = output_dir / f"{model1_name}_outputs.json"
        with open(model1_output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "model": model1_name,
                "outputs": [{"prompt": p, "output": o[0]} for p, o in zip(prompts, model1_outputs)]
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Model 1 outputs saved to: {model1_output_file}")
        
        # Save model 2 outputs
        model2_output_file = output_dir / f"{model2_name}_outputs.json"
        with open(model2_output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "model": model2_name,
                "outputs": [{"prompt": p, "output": o[0]} for p, o in zip(prompts, model2_outputs)]
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Model 2 outputs saved to: {model2_output_file}")
    
    # Print summary
    comparator.print_summary(results)
    
    print(f"✓ Evaluation completed successfully!")
    print(f"\nResults saved to: {args.output_path}")


if __name__ == "__main__":
    main()
