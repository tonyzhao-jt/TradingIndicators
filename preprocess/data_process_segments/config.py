"""Configuration file for data_process_segments pipeline."""
import os
from pathlib import Path

# Directory paths
BASE_DIR = Path(__file__).parent
INPUT_DIR = os.getenv("INPUT_DIR", "/workspace/trading_indicators/outputs/processed")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/workspace/trading_indicators/outputs/segments")
CHECKPOINT_FILE = "segments_processing_checkpoint.json"

# Processing parameters
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
DEBUG_NODE_OUTPUT = os.getenv("DEBUG_NODE_OUTPUT", "false").lower() == "true"

# Quality filtering parameters
MIN_CODE_LENGTH = int(os.getenv("MIN_CODE_LENGTH", "20"))  # Minimum code length to consider
MIN_DESCRIPTION_LENGTH = int(os.getenv("MIN_DESCRIPTION_LENGTH", "15"))  # Minimum description length
QUALITY_SCORE_THRESHOLD = float(os.getenv("QUALITY_SCORE_THRESHOLD", "7.0"))  # Minimum quality score (1-10)

# LLM settings for quality scoring
LOCAL_QWEN_ENDPOINT = os.getenv("LOCAL_QWEN_ENDPOINT", "http://202.45.128.234:5788/v1/")
LOCAL_QWEN_MODEL_NAME = os.getenv("LOCAL_QWEN_MODEL_NAME", "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct")
LOCAL_QWEN_API_KEY = os.getenv("LOCAL_QWEN_API_KEY", "none")
LLM_MODEL = os.getenv("LLM_MODEL", LOCAL_QWEN_MODEL_NAME)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# Code similarity threshold for deduplication
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))  # Threshold for considering code similar

# Description-code match threshold for augmentation (only used when --enable_description_augment true)
DESCRIPTION_MATCH_THRESHOLD = float(os.getenv("DESCRIPTION_MATCH_THRESHOLD", "6.0"))  # Minimum match score (0-10) to keep original description