# Trading Data Processing Pipeline with LangGraph

This project implements a LangGraph-based data processing pipeline for converting and validating Pine Script trading indicators. It uses a local Qwen model for intelligent code conversion and validation.

## Features

- **Batch Processing**: Process large JSON files in configurable batches
- **Checkpoint Recovery**: Automatically resume from interruption points
- **Multi-Node Workflow**: 
  - Filter: Determine whether to keep data
  - Code Converter: Convert Pine Script to Pyne Script with self-verification (up to 5 attempts)
  - Code Validator: Validate converted code semantics
  - Data Augmentation: Enhance descriptions and add reasoning
- **Configurable Models**: Each node can use different model configurations
- **Parquet Output**: Efficiently store processed data in Parquet format

## Configuration

The local model configuration is stored in `.env`:
- `LOCAL_QWEN_ENDPOINT`: http://202.45.128.234:5788/v1/
- `LOCAL_QWEN_MODEL_NAME`: /nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct
- `LOCAL_QWEN_API_KEY`: none

## Installation

```bash
pip install -r requirements.txt
```

## Project Structure

```
data_agent/
├── .env                      # Environment configuration
├── requirements.txt          # Python dependencies
├── config.py                # Configuration loader with node-specific settings
├── llm_client.py            # LLM client wrapper with per-node configuration
├── graph.py                 # LangGraph workflow definition
├── main.py                  # Main data processing pipeline
├── run.sh                   # Convenience run script
└── README.md                # This file
```

## Usage

### Process Trading Data

Process a JSON file containing trading indicator data:

```bash
python main.py ../../outputs/trade_raw_data_20251011_053837.json
```

### Resume from Checkpoint

If processing is interrupted, simply run the same command again to resume:

```bash
python main.py ../../outputs/trade_raw_data_20251011_053837.json
```

### Start Fresh (Ignore Checkpoint)

To start processing from the beginning:

```bash
python main.py ../../outputs/trade_raw_data_20251011_053837.json --no-resume
```

### Test LLM Connection

Test the connection to the local Qwen model:

```bash
python llm_client.py
```

### Test Graph Workflow

Test the LangGraph workflow with sample data:

```bash
python graph.py
```

## Workflow Details

### Processing Nodes

1. **Filter Node** (`filter`)
   - **Intelligent two-stage filtering** to ensure data quality
   - **Stage 1 - Word Count Check** (Objective):
     - Rejects descriptions shorter than `MIN_DESCRIPTION_WORDS` (default: 100 words)
     - Fast fail for obviously insufficient data
   - **Stage 2 - Content Quality Check** (Subjective, LLM-based):
     - Evaluates if description contains sufficient indicator information
     - Checks for specific strategy implementation details
     - Scores from 0-100; passes only if score >= 60
     - Identifies presence of indicators (VWAP, RSI, MACD, etc.)
     - Verifies actionable trading logic is described
   - **Decision**: Rejects data if either check fails

2. **Code Converter Node** (`code_converter`)
   - Converts Pine Script to Pyne Script
   - Implements self-verification loop
   - Maximum 5 conversion attempts
   - Uses higher temperature for creative conversion

3. **Code Validator Node** (`code_validator`)
   - Validates converted code against original
   - Checks semantic equivalence
   - Uses lower temperature for consistent validation
   - Rejects data if validation fails

4. **Data Augmentation - Description** (`data_aug_description`)
   - Enhances the description field using **Best-of-N** sampling
   - Generates N candidate analyses (configurable via `BEST_OF_N` in config)
   - Selects the best analysis based on quality scoring
   - Follows the `document_analysis.json` template structure
   - Output includes: algorithms, key concepts, mathematical models, evaluation metrics, etc.

5. **Symbol Inference Node** (`symbol_infer`)
   - Infers relevant trading symbols from strategy description
   - Identifies which symbols/assets the strategy is designed for
   - Common symbols: USDT, BTC, ETH, USD, EUR, etc.
   - Provides confidence level (high/medium/low) and reasoning
   - Output: Comma-separated list of symbols

6. **Data Augmentation - Reasoning** (`data_aug_reason`)
   - Adds reasoning process to data
   - Default: Adds empty reasoning field
   - Can be extended for LLM-based reasoning

### Workflow Flow

```
Start → Filter → Code Converter (retry up to 5x) → Code Validator → 
  → Data Aug Description → Symbol Infer → Data Aug Reason → Save to Parquet
  
If any step fails: → Reject → End
```

## Configuration

### Batch Size and Quality Parameters

Edit in `config.py`:
- `BATCH_SIZE` (default: 10) - Items per batch
- `BEST_OF_N` (default: 3) - Number of candidates for description analysis
- `MIN_DESCRIPTION_WORDS` (default: 100) - Minimum word count for filtering

### Node-Specific Model Settings

Edit `NODE_MODELS` in `config.py` to customize per-node:
- `endpoint`: API endpoint
- `model_name`: Model identifier
- `temperature`: Sampling temperature (optional)
- `max_tokens`: Maximum response length (optional)

**Note**: Temperature and max_tokens are now optional. If not specified, the model will use its defaults.

Example:
```python
NODE_MODELS = {
    "code_converter": {
        "endpoint": LOCAL_QWEN_ENDPOINT,
        "model_name": LOCAL_QWEN_MODEL_NAME,
        "api_key": LOCAL_QWEN_API_KEY
        # temperature and max_tokens use model defaults
    }
}
```

### Output Location

Edit `OUTPUT_DIR` in `config.py` (default: `../../outputs/processed`)

## Output Format

Processed data is saved as Parquet files with the following **7 fields**:

- `id`: Indicator ID (e.g., "mP5jN8hz-cd-VWAP-mtg-Cx")
- `name`: Indicator name (e.g., "cd_VWAP_mtg_Cx")
- `description`: Enhanced description (augmented using Best-of-N selection)
- `reasoning`: Processing reasoning (currently empty, can be extended)
- `created_at`: Creation timestamp from original data (e.g., "2025-10-10T01:06:03.000Z")
- `source_code`: Converted Pyne Script code (converted from Pine Script)
- `relevant_symbols`: Comma-separated trading symbols (e.g., "USDT,BTC,ETH")

**Note**: Only these 7 fields are included in the final output. All intermediate processing data is discarded.

## Checkpoint Format

Checkpoint file (`processing_checkpoint.json`):
```json
{
  "last_processed_index": 150,
  "processed_count": 151,
  "rejected_count": 12,
  "timestamp": "2025-10-12T10:30:00"
}
```

## Example

```python
from main import DataProcessor

# Create processor
processor = DataProcessor("../../outputs/trade_raw_data_20251011_053837.json")

# Process with checkpoint support
processor.process(resume=True)
```

## Monitoring Progress

The pipeline uses `tqdm` for progress bars and provides:
- Real-time processing status
- Batch completion notifications
- Final statistics (success rate, rejected count)
- Output file locations
