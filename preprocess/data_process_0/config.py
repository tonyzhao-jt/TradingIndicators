"""Configuration for the data_process_0 processing pipeline."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Local Qwen Model Configuration
LOCAL_QWEN_ENDPOINT = os.getenv("LOCAL_QWEN_ENDPOINT", "http://202.45.128.234:5788/v1/")
LOCAL_QWEN_MODEL_NAME = os.getenv("LOCAL_QWEN_MODEL_NAME", "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct")
LOCAL_QWEN_API_KEY = os.getenv("LOCAL_QWEN_API_KEY", "none")

# Data Processing Configuration
BATCH_SIZE = 10
CHECKPOINT_FILE = "processing_checkpoint.json"
OUTPUT_DIR = "../../outputs/processed"
INPUT_DIR = "../../outputs"

# Intermediate saving configuration
SAVE_INTERMEDIATE_EVERY_N_BATCHES = int(os.getenv("SAVE_INTERMEDIATE_EVERY_N_BATCHES", "5"))  # Save every 50 items

# Filtering thresholds - lowered for testing
MIN_LIKES = 10  # Lowered from 100 to 10
MIN_DESCRIPTION_WORDS = 20  # Lowered from 100 to 20  
MIN_CODE_LENGTH = 100

# Debug: when true, nodes will print their output/result for each item
DEBUG_NODE_OUTPUT = True  # Changed to True for testing

# Node-specific model configurations
NODE_MODELS = {
    "filter": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "visualization_remove": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    },
    "restructure": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
    }
}