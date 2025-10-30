# Data Process Segments Pipeline

This module processes the output from `data_process_0` to create high-quality segment-wise training data for trading strategy learning.

## Overview

The pipeline takes restructured trading strategy data and creates individual segments with description-code pairs, then filters and scores them for quality.

## Pipeline Steps

### 1. Pack Node
- Extracts individual segments from `restructured_data` 
- Each segment contains a key (like "signal_gen", "risk_management") with description and code
- Creates separate records for each segment

### 2. Filter Node
- Removes segments with short descriptions (< 15 chars)
- Filters out segments without meaningful code (comments only, notes, etc.)
- Deduplicates segments with similar code (>85% similarity)
- Prevents duplicate samples from the same source

### 3. Quality Score Node
- Uses LLM to score each segment on multiple dimensions:
  - Clarity: How well description explains the code
  - Accuracy: Description matches code implementation
  - Educational Value: Usefulness for learning
  - Code Quality: Structure and meaningfulness
  - Completeness: Sufficient context provided
- Assigns overall score (1-10) and detailed metrics
- Marks segments meeting quality threshold (≥7.0)

## Configuration

Key settings in `config.py` and `.env`:
- `MIN_CODE_LENGTH`: Minimum code length (default: 10)
- `MIN_DESCRIPTION_LENGTH`: Minimum description length (default: 20)
- `QUALITY_SCORE_THRESHOLD`: Minimum quality score (default: 6.0)
- `USE_LLM_SCORING`: Enable LLM scoring (default: true)
- `LOCAL_QWEN_ENDPOINT`: Local Qwen API endpoint

## Usage

```bash
# Process all segments
python main.py /path/to/data_process_0_results.json

# Process with custom output directory
python main.py input.json --output-dir /custom/output

# Process limited samples for testing
python main.py input.json --samples 10

# Enable debug output
python main.py input.json --debug
```

## Output Format

The pipeline generates JSON files with:
- Metadata about processing statistics
- List of segments with:
  - Original segment information (key, description, code)
  - Source information (item ID, title, author)
  - Quality scoring results
  - Filtering metadata

High-quality segments (meeting threshold) are marked with `meets_quality_threshold: true`.

## Dependencies

- langraph: Workflow orchestration
- openai: LLM client for quality scoring
- Standard libraries: json, pathlib, logging, etc.

## Environment Variables

- `OPENAI_API_KEY`: Required for LLM quality scoring
- `INPUT_DIR`: Default input directory
- `OUTPUT_DIR`: Default output directory
- `DEBUG_NODE_OUTPUT`: Enable debug output