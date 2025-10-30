#!/usr/bin/env python3
"""
Model Downloader with Snapshot Download
Uses HuggingFace's snapshot_download for efficient model downloading with resume support.
"""

import argparse
import os
from pathlib import Path
from typing import Optional, List
from huggingface_hub import snapshot_download, login
import json
from datetime import datetime


class ModelDownloader:
    """Download models efficiently using snapshot_download."""
    
    def __init__(
        self,
        cache_dir: str = "./model_cache",
        token: Optional[str] = None
    ):
        """
        Initialize the model downloader.
        
        Args:
            cache_dir: Directory to cache downloaded models
            token: HuggingFace token for private models (optional)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.token = token
        
        if token:
            login(token=token)
    
    def download_model(
        self,
        model_name: str,
        revision: str = "main",
        ignore_patterns: Optional[List[str]] = None,
        allow_patterns: Optional[List[str]] = None,
        max_workers: int = 8,
        force_download: bool = False
    ) -> str:
        """
        Download a model using snapshot_download for efficient parallel downloading.
        
        Args:
            model_name: HuggingFace model name (e.g., "Qwen/Qwen2.5-Coder-7B")
            revision: Model revision/branch to download (default: "main")
            ignore_patterns: Patterns to ignore during download
            allow_patterns: Only download files matching these patterns
            max_workers: Number of parallel download workers
            force_download: Force re-download even if cached
            
        Returns:
            Path to the downloaded model directory
        """
        print(f"{'='*80}")
        print(f"MODEL DOWNLOADER")
        print(f"{'='*80}")
        print(f"Model: {model_name}")
        print(f"Revision: {revision}")
        print(f"Cache directory: {self.cache_dir}")
        print(f"Max workers: {max_workers}")
        print(f"{'='*80}\n")
        
        # Default ignore patterns to save space
        if ignore_patterns is None:
            ignore_patterns = [
                "*.gguf",  # GGUF format files
                "*.msgpack",  # MessagePack files
                "*.h5",  # Keras files
                "*.ot",  # Old PyTorch files
            ]
        
        try:
            start_time = datetime.now()
            print(f"Starting download at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("This may take a while depending on model size and network speed...\n")
            
            # Download the model
            local_dir = snapshot_download(
                repo_id=model_name,
                revision=revision,
                cache_dir=str(self.cache_dir),
                ignore_patterns=ignore_patterns,
                allow_patterns=allow_patterns,
                max_workers=max_workers,
                force_download=force_download,
                token=self.token,
                resume_download=True,  # Enable resume for interrupted downloads
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n{'='*80}")
            print(f"✓ Download completed successfully!")
            print(f"{'='*80}")
            print(f"Model path: {local_dir}")
            print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
            print(f"{'='*80}\n")
            
            # Save download metadata
            self._save_download_info(model_name, local_dir, revision, duration)
            
            return local_dir
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"✗ Error downloading model: {str(e)}")
            print(f"{'='*80}\n")
            raise
    
    def _save_download_info(
        self,
        model_name: str,
        local_dir: str,
        revision: str,
        duration: float
    ):
        """Save download information to a JSON file."""
        info_file = self.cache_dir / "download_info.json"
        
        # Load existing info
        if info_file.exists():
            with open(info_file, 'r') as f:
                download_info = json.load(f)
        else:
            download_info = {"downloads": []}
        
        # Add new download info
        download_info["downloads"].append({
            "model_name": model_name,
            "local_path": local_dir,
            "revision": revision,
            "download_time": datetime.now().isoformat(),
            "duration_seconds": duration
        })
        
        # Save updated info
        with open(info_file, 'w') as f:
            json.dump(download_info, f, indent=2)
    
    def list_downloaded_models(self):
        """List all downloaded models."""
        info_file = self.cache_dir / "download_info.json"
        
        if not info_file.exists():
            print("No downloaded models found.")
            return []
        
        with open(info_file, 'r') as f:
            download_info = json.load(f)
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADED MODELS")
        print(f"{'='*80}")
        
        for i, info in enumerate(download_info["downloads"], 1):
            print(f"\n{i}. {info['model_name']}")
            print(f"   Path: {info['local_path']}")
            print(f"   Revision: {info['revision']}")
            print(f"   Downloaded: {info['download_time']}")
            print(f"   Duration: {info['duration_seconds']:.2f}s")
        
        print(f"\n{'='*80}\n")
        
        return download_info["downloads"]


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download HuggingFace models using snapshot_download",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a model
  python model_downloader.py --model_name "Qwen/Qwen2.5-Coder-7B"
  
  # Download with custom cache directory
  python model_downloader.py --model_name "Qwen/Qwen2.5-Coder-7B" --cache_dir "./models"
  
  # Download specific revision
  python model_downloader.py --model_name "Qwen/Qwen2.5-Coder-7B" --revision "v1.0"
  
  # Download only specific files
  python model_downloader.py --model_name "Qwen/Qwen2.5-Coder-7B" --allow_patterns "*.safetensors" "*.json"
  
  # List downloaded models
  python model_downloader.py --list
        """
    )
    
    parser.add_argument(
        "--model_name",
        type=str,
        help="HuggingFace model name (e.g., 'Qwen/Qwen2.5-Coder-7B')"
    )
    parser.add_argument(
        "--cache_dir",
        type=str,
        default="./model_cache",
        help="Directory to cache downloaded models (default: ./model_cache)"
    )
    parser.add_argument(
        "--revision",
        type=str,
        default="main",
        help="Model revision/branch to download (default: main)"
    )
    parser.add_argument(
        "--ignore_patterns",
        nargs="+",
        help="Patterns to ignore during download (e.g., '*.gguf')"
    )
    parser.add_argument(
        "--allow_patterns",
        nargs="+",
        help="Only download files matching these patterns (e.g., '*.safetensors' '*.json')"
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=8,
        help="Number of parallel download workers (default: 8)"
    )
    parser.add_argument(
        "--force_download",
        action="store_true",
        help="Force re-download even if cached"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="HuggingFace token for private models (or set HF_TOKEN env variable)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all downloaded models"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()
    
    # Get token from args or environment
    token = args.token or os.environ.get("HF_TOKEN")
    
    # Initialize downloader
    downloader = ModelDownloader(
        cache_dir=args.cache_dir,
        token=token
    )
    
    # List models if requested
    if args.list:
        downloader.list_downloaded_models()
        return
    
    # Download model
    if not args.model_name:
        print("Error: --model_name is required (unless using --list)")
        return
    
    try:
        local_path = downloader.download_model(
            model_name=args.model_name,
            revision=args.revision,
            ignore_patterns=args.ignore_patterns,
            allow_patterns=args.allow_patterns,
            max_workers=args.max_workers,
            force_download=args.force_download
        )
        
        print(f"Model successfully downloaded to: {local_path}")
        print(f"You can now use this path in your training/inference scripts.")
        
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        print("You can resume the download by running the same command again.")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
