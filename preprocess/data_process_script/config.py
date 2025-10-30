"""Configuration file for data_process_script pipeline."""
import os
from pathlib import Path

# Directory paths
BASE_DIR = Path(__file__).parent
INPUT_FILE = os.getenv("INPUT_FILE", "/workspace/trading_indicators/outputs/strategies_20251014_054134.json")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/workspace/trading_indicators/outputs/processed_scripts")

# Processing parameters
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
DEBUG_NODE_OUTPUT = os.getenv("DEBUG_NODE_OUTPUT", "false").lower() == "true"

# Filter parameters
MIN_LIKES_COUNT = int(os.getenv("MIN_LIKES_COUNT", "100"))  # Minimum likes to include strategy
MIN_CODE_LENGTH = int(os.getenv("MIN_CODE_LENGTH", "50"))  # Minimum code length to consider
MIN_DESCRIPTION_LENGTH = int(os.getenv("MIN_DESCRIPTION_LENGTH", "30"))  # Minimum description length

# Quality scoring parameters
QUALITY_SCORE_THRESHOLD = float(os.getenv("QUALITY_SCORE_THRESHOLD", "7.0"))  # Minimum quality score (1-10)

# LLM settings
LOCAL_QWEN_ENDPOINT = os.getenv("LOCAL_QWEN_ENDPOINT", "http://202.45.128.234:5788/v1/")
LOCAL_QWEN_MODEL_NAME = os.getenv("LOCAL_QWEN_MODEL_NAME", "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct")
LOCAL_QWEN_API_KEY = os.getenv("LOCAL_QWEN_API_KEY", "none")
LLM_MODEL = os.getenv("LLM_MODEL", LOCAL_QWEN_MODEL_NAME)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# Maximum concurrent LLM requests
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "3"))

# Enable/disable specific nodes
ENABLE_LANGUAGE_CONVERT = os.getenv("ENABLE_LANGUAGE_CONVERT", "true").lower() == "true"
ENABLE_VIS_REMOVE = os.getenv("ENABLE_VIS_REMOVE", "true").lower() == "true"
ENABLE_QUALITY_SCORE = os.getenv("ENABLE_QUALITY_SCORE", "true").lower() == "true"
