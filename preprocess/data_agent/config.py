"""Configuration for the LangGraph agent with local Qwen model."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Local Qwen Model Configuration
LOCAL_QWEN_ENDPOINT = os.getenv("LOCAL_QWEN_ENDPOINT", "http://202.45.128.234:5788/v1/")
LOCAL_QWEN_MODEL_NAME = os.getenv("LOCAL_QWEN_MODEL_NAME", "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct")
LOCAL_QWEN_API_KEY = os.getenv("LOCAL_QWEN_API_KEY", "none")

# Model configuration (defaults removed - set per node if needed)
# MODEL_TEMPERATURE = 0.7
# MODEL_MAX_TOKENS = 2048

# Data Processing Configuration
BATCH_SIZE = 10
BEST_OF_N = 3  # Number of candidates to generate for best-of-N selection
MIN_DESCRIPTION_WORDS = 100  # Minimum word count for description filtering
CHECKPOINT_FILE = "processing_checkpoint.json"
OUTPUT_DIR = "../../outputs/processed"
INPUT_DIR = "../../outputs"

# Quality threshold for LLM content quality checks (0-100). Items scoring >= this
# value will be considered passing the subjective content quality check.
QUALITY_SCORE_THRESHOLD = int(os.getenv("QUALITY_SCORE_THRESHOLD", "40"))

# Toggle to enable/disable the LLM-based subjective quality filter. Set to "false" to
# skip the LLM quality check and accept items that pass the word-count check.
ENABLE_QUALITY_FILTER = os.getenv("ENABLE_QUALITY_FILTER", "true").lower() in ["1", "true", "yes"]

# Backend selection for code conversion/validation: 'pyne' or 'backtrader'
BACKEND = os.getenv("BACKEND", "backtrader").lower()

# Debug: when true, nodes will print their output/result for each item
DEBUG_NODE_OUTPUT = os.getenv("DEBUG_NODE_OUTPUT", "false").lower() in ["1", "true", "yes"]

# Toggle whether to use LLM-based semantic validation when validating converted code.
# Default: enabled (True) — set USE_LLM_VALIDATION=false in the environment to disable.
USE_LLM_VALIDATION = os.getenv("USE_LLM_VALIDATION", "true").lower() in ["1", "true", "yes"]

# Node-specific model configurations (temperature and max_tokens removed)
NODE_MODELS = {
    "filter": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "code_converter": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "code_validator": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "data_aug_description": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "data_aug_reason": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "symbol_infer": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    }
}

# Conversion settings
MAX_CONVERSION_ATTEMPTS = 5
