# Quick Reference Card for Training Pipeline

## 1. Token Analysis
```bash
python token_static_check.py \
    --data_path /workspace/trading_indicators/outputs/segments_20251014.json \
    --show_distribution
```
**Output**: `token_statistics_report.json`

## 2. Training Options

### Basic Training
```bash
python train_main_0.py --data_path /path/to/data.json
```

### Recommended for segments_20251014.json
```bash
python train_main_0.py \
    --data_path /workspace/trading_indicators/outputs/segments_20251014.json \
    --max_seq_length 2048 \
    --output_dir "./pine-coder"
```

### Full Custom Configuration
```bash
python train_main_0.py \
    --data_path /workspace/trading_indicators/outputs/segments_20251014.json \
    --model_name "Qwen/Qwen2.5-Coder-7B" \
    --max_seq_length 2048 \
    --formatter_type instruction \
    --batch_size 2 \
    --gradient_accumulation_steps 4 \
    --learning_rate 1e-5 \
    --num_epochs 3 \
    --output_dir "./pine-coder-custom"
```

## 3. Key Parameters

| Parameter | Default | Description | Based on Token Analysis |
|-----------|---------|-------------|------------------------|
| `--data_path` | segments_20251014.json | Path to training data | N/A |
| `--max_seq_length` | 2048 | Max sequence length | 2048 (95%), 3200 (99%), 4096 (safe max) |
| `--batch_size` | 2 | Batch size per device | Adjust based on VRAM |
| `--learning_rate` | 1e-5 | Learning rate | Standard for fine-tuning |
| `--num_epochs` | 3 | Training epochs | Balance training time/quality |

## 4. Formatter Options

| Type | Description | Use Case |
|------|-------------|----------|
| `instruction` | Structured format with headers | Default, best for most cases |
| `conversation` | Natural dialogue format | Conversational models |
| `chatml` | ChatML markup format | Models supporting ChatML |
| `alpaca` | Stanford Alpaca format | Alpaca-style models |
| `simple` | Basic concatenation | Simple completion tasks |

## 5. Dataset Statistics (segments_20251014.json)

- **Total samples**: 601
- **Input tokens**: 4-3,085 (avg: 309)
- **Output tokens**: 4-2,925 (avg: 220)
- **Combined tokens**: 33-3,611 (avg: 529)
- **95th percentile**: 1,781 tokens
- **99th percentile**: 3,056 tokens

## 6. Quick Commands

```bash
# See all options
python train_main_0.py --help

# View examples
./train_examples.sh

# Test formatters
python -c "from formatter import print_sample_formats; print_sample_formats({'input': 'test', 'output': 'test'})"

# Check token stats
cat token_statistics_report.json | python -m json.tool
```

## 7. Troubleshooting

**Out of Memory?**
- Reduce `--batch_size` (try 1)
- Reduce `--max_seq_length` (try 1024)
- Increase `--gradient_accumulation_steps` (try 8)

**Training too slow?**
- Increase `--batch_size` (if VRAM allows)
- Decrease `--gradient_accumulation_steps`
- Enable `--fp16` (default: enabled)

**Poor results?**
- Increase `--num_epochs`
- Try different `--formatter_type`
- Adjust `--learning_rate` (try 2e-5 or 5e-6)
- Increase `--max_seq_length` to capture longer samples