# Mid-Train Tools

This directory contains utilities for data preparation and analysis during the model training process.

## Files

### 1. `token_static_check.py`
A comprehensive token analysis tool that provides statistical analysis of datasets using specific model tokenizers.

#### Features:
- **Token Counting**: Analyzes input, output, and combined token counts
- **Statistical Analysis**: Provides min, max, mean, median, std deviation, and percentiles
- **Distribution Analysis**: Shows token count distribution across different ranges
- **Multiple Model Support**: Works with any HuggingFace tokenizer
- **Detailed Reporting**: Generates both console output and JSON reports

#### Usage:
```bash
# Basic usage
python token_static_check.py --data_path /path/to/dataset.json

# With custom model and output
python token_static_check.py \
    --model_name "Qwen/Qwen2.5-Coder-7B" \
    --data_path "/workspace/trading_indicators/outputs/segments_20251014.json" \
    --output_path "token_report.json" \
    --show_distribution

# Command line arguments:
# --model_name: Model name for tokenizer (default: "Qwen/Qwen2.5-Coder-7B")
# --data_path: Path to JSON dataset file (default: segments_20251014.json)
# --output_path: Path to save statistics report (default: "token_statistics_report.json")
# --show_distribution: Show token length distribution analysis
```

#### Output Example:
```
================================================================================
TOKEN STATISTICS REPORT
================================================================================
Model: Qwen/Qwen2.5-Coder-7B
Tokenizer vocab size: 151,643
================================================================================

INPUT TOKENS:
----------------------------------------
  Total samples:    601
  Total tokens:     185,623
  Min tokens:       4
  Max tokens:       3,085
  Mean tokens:      308.86
  Median tokens:    133.00
  Std deviation:    374.06
  25th percentile:  55.50
  75th percentile:  473.00
  95th percentile:  1040.30
  99th percentile:  1759.60
```

### 2. `formatter.py`
A flexible data formatting system for preparing training datasets with different prompt templates.

#### Features:
- **Multiple Format Types**: Instruction, Conversation, ChatML, Alpaca, and Simple formats
- **Factory Pattern**: Easy creation of formatters by type
- **Extensible Design**: Simple to add new formatting strategies
- **Validation**: Built-in sample validation
- **Comparison Tools**: Utilities to compare different formats

#### Available Formatters:

1. **InstructionFormatter**: Structured instruction-following format
2. **ConversationFormatter**: Natural conversation flow
3. **ChatMLFormatter**: ChatML (Chat Markup Language) format
4. **AlpacaFormatter**: Stanford Alpaca instruction format
5. **SimpleFormatter**: Basic concatenation format

#### Usage:
```python
from formatter import FormatterFactory, load_and_format_data

# Create a specific formatter
formatter = FormatterFactory.create_formatter("instruction")

# Format a single sample
sample = {"input": "Create a strategy", "output": "@version=5..."}
formatted_text = formatter.format_instruction(sample)

# Format entire dataset
formatted_dataset = formatter.format_dataset(data_list)

# Load and format data in one step
formatted_data = load_and_format_data(
    "data.json", 
    formatter_type="instruction",
    instruction_text="Custom instruction text"
)

# Compare all formats
from formatter import print_sample_formats
print_sample_formats(sample)
```

### 3. `train_main_0.py`
Updated training script that uses the new formatter system and contains English translations. Now supports command-line arguments for flexible configuration.

#### Key Features:
- **Argparse Support**: Full command-line argument support
- **Configurable Data Path**: Pass any dataset path as input
- **Multiple Formatters**: Choose from 5 different formatting styles
- **Flexible Training Parameters**: Customize all training hyperparameters
- **Uses Formatter System**: Integrated with the new formatter classes
- **English Comments**: All Chinese comments translated to English
- **Modular Design**: Clean separation of formatting logic

#### Usage:
```bash
# Basic usage with default settings
python train_main_0.py --data_path /path/to/your/data.json

# Custom configuration
python train_main_0.py \
    --data_path /workspace/trading_indicators/outputs/segments_20251014.json \
    --model_name "Qwen/Qwen2.5-Coder-7B" \
    --max_seq_length 2048 \
    --formatter_type instruction \
    --batch_size 4 \
    --learning_rate 2e-5 \
    --num_epochs 5 \
    --output_dir "./my-pine-coder"

# See all available options
python train_main_0.py --help
```

#### Available Arguments:
- **Data**: `--data_path` (required)
- **Model**: `--model_name`, `--max_seq_length`
- **Formatter**: `--formatter_type`, `--instruction_text`
- **Training**: `--batch_size`, `--learning_rate`, `--num_epochs`, `--output_dir`
- **Advanced**: `--gradient_accumulation_steps`, `--warmup_steps`, `--save_steps`, `--logging_steps`

### 4. `test_token_checker.sh`
Test script that demonstrates both the token checker and formatter functionality.

#### Usage:
```bash
./test_token_checker.sh
```

This will:
1. Run token analysis on the default dataset
2. Generate a detailed statistics report
3. Demonstrate all available formatter types
4. Show sample outputs for comparison

### 5. `train_examples.sh`
Example commands showing different ways to use train_main_0.py with various configurations.

#### Usage:
```bash
./train_examples.sh
```

This displays:
1. Basic usage examples
2. Custom configuration examples
3. Different formatter options
4. Recommendations based on token analysis results

## Installation Requirements

Make sure you have the required dependencies:

```bash
pip install transformers datasets torch trl
```

## Dataset Format

The tools expect JSON datasets with the following structure:
```json
[
    {
        "input": "Trading strategy description...",
        "output": "@version=5\nstrategy(\"Name\", overlay=true)\n..."
    },
    ...
]
```

## Integration with Training Pipeline

1. **Data Analysis**: Use `token_static_check.py` to analyze your dataset before training
2. **Format Selection**: Use `formatter.py` to experiment with different prompt formats  
3. **Training**: Use the updated `train_main_0.py` for actual model training

## Example Workflow

```bash
# 1. Analyze your dataset
cd /workspace/trading_indicators/posttrain/mid_train
python token_static_check.py \
    --data_path /workspace/trading_indicators/outputs/segments_20251014.json \
    --show_distribution

# The report will be saved as: token_statistics_report.json in the current directory

# 2. Review token statistics to determine optimal max_seq_length
# For segments_20251014.json:
#   - 95th percentile: 1781 tokens → use --max_seq_length 2048
#   - 99th percentile: 3056 tokens → use --max_seq_length 3200
#   - Safe maximum: --max_seq_length 4096

# 3. (Optional) Test different formats
python -c "from formatter import print_sample_formats; print_sample_formats({'input': 'test', 'output': 'test'})"

# 4. Train with optimal settings based on analysis
python train_main_0.py \
    --data_path /workspace/trading_indicators/outputs/segments_20251014.json \
    --max_seq_length 2048 \
    --formatter_type instruction \
    --output_dir "./pine-coder-v1"

# 5. (Optional) View all training examples
./train_examples.sh
```

## Output Files

- `token_statistics_report.json`: Comprehensive token analysis results (created in the directory where you run the script)
- `pine-coder/`: Directory containing trained model outputs (from training)

**Default output location**: When you run the token checker from `/workspace/trading_indicators/posttrain/mid_train/`, the report will be saved as `/workspace/trading_indicators/posttrain/mid_train/token_statistics_report.json`

## Notes

- The token checker supports any HuggingFace tokenizer
- Formatter classes are easily extensible for custom formats
- All Chinese text has been translated to English for better international compatibility
- The system is designed to handle large datasets efficiently with progress reporting
- Output files are saved in the current working directory when you run the scripts
- The actual dataset analyzed (segments_20251014.json) contains 601 samples with an average combined length of ~529 tokens