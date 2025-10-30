# Multi-GPU Training Guide with torchrun

## Quick Start

### Basic 4-GPU Training
```bash
cd /workspace/trading_indicators/posttrain/mid_train
./train_0.sh
```

This will launch training on 4 GPUs with default settings.

## Available Scripts

### 1. `train_0.sh` - Simple Multi-GPU Training
Basic script with fixed 4-GPU configuration. Good for quick starts.

**Usage:**
```bash
./train_0.sh
```

**Configuration:**
- 4 GPUs (fixed)
- Default hyperparameters
- Easy to modify by editing the script

### 2. `train_0_advanced.sh` - Configurable Multi-GPU Training
Advanced script with environment variable support for flexible configuration.

**Usage:**
```bash
# Default 4-GPU training
./train_0_advanced.sh

# Custom configuration via environment variables
NUM_GPUS=2 BATCH_SIZE=4 LEARNING_RATE=2e-5 ./train_0_advanced.sh

# Custom data path and output
DATA_PATH=/path/to/data.json OUTPUT_DIR=./my-model ./train_0_advanced.sh
```

## Configuration Options (train_0_advanced.sh)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NUM_GPUS` | 4 | Number of GPUs to use |
| `DATA_PATH` | segments_20251014.json | Path to training data |
| `MODEL_NAME` | Qwen/Qwen2.5-Coder-7B | Model to fine-tune |
| `OUTPUT_DIR` | ./pine-coder-4gpu | Output directory |
| `MAX_SEQ_LENGTH` | 2048 | Maximum sequence length |
| `BATCH_SIZE` | 2 | Batch size per GPU |
| `GRADIENT_ACCUM_STEPS` | 4 | Gradient accumulation steps |
| `LEARNING_RATE` | 1e-5 | Learning rate |
| `NUM_EPOCHS` | 3 | Number of epochs |
| `WARMUP_STEPS` | 100 | Warmup steps |
| `LOGGING_STEPS` | 10 | Logging frequency |
| `SAVE_STEPS` | 500 | Checkpoint save frequency |
| `FORMATTER_TYPE` | instruction | Formatter type |
| `MASTER_PORT` | 29500 | Master port for distributed training |

## Examples

### Example 1: Quick 4-GPU Training
```bash
./train_0.sh
```

### Example 2: 2-GPU Training with Larger Batch Size
```bash
NUM_GPUS=2 BATCH_SIZE=4 ./train_0_advanced.sh
```

### Example 3: Custom Model and Data
```bash
MODEL_NAME="Qwen/Qwen2.5-Coder-14B" \
DATA_PATH="/path/to/custom/data.json" \
OUTPUT_DIR="./custom-model" \
./train_0_advanced.sh
```

### Example 4: High Memory Setup (Longer Sequences)
```bash
NUM_GPUS=4 \
MAX_SEQ_LENGTH=4096 \
BATCH_SIZE=1 \
GRADIENT_ACCUM_STEPS=8 \
./train_0_advanced.sh
```

### Example 5: Fast Training (More Epochs, Higher LR)
```bash
NUM_EPOCHS=5 \
LEARNING_RATE=2e-5 \
WARMUP_STEPS=200 \
./train_0_advanced.sh
```

### Example 6: Different Formatter
```bash
FORMATTER_TYPE=chatml \
OUTPUT_DIR="./pine-coder-chatml" \
./train_0_advanced.sh
```

## Understanding Effective Batch Size

The effective batch size is calculated as:
```
Effective Batch Size = NUM_GPUS × BATCH_SIZE × GRADIENT_ACCUM_STEPS
```

**Default configuration:**
- 4 GPUs × 2 batch size × 4 accumulation = **32 effective batch size**

**Memory vs Speed Trade-offs:**

| Setup | GPUs | Batch/GPU | Accum | Effective | Memory | Speed |
|-------|------|-----------|-------|-----------|--------|-------|
| Default | 4 | 2 | 4 | 32 | Medium | Fast |
| High Mem | 4 | 1 | 8 | 32 | Low | Slower |
| Fast | 4 | 4 | 2 | 32 | High | Faster |
| Small GPU | 2 | 1 | 16 | 32 | Low | Slowest |

## Memory Optimization

If you encounter OOM (Out of Memory) errors:

1. **Reduce batch size per GPU:**
   ```bash
   BATCH_SIZE=1 ./train_0_advanced.sh
   ```

2. **Reduce sequence length:**
   ```bash
   MAX_SEQ_LENGTH=1024 ./train_0_advanced.sh
   ```

3. **Increase gradient accumulation:**
   ```bash
   BATCH_SIZE=1 GRADIENT_ACCUM_STEPS=8 ./train_0_advanced.sh
   ```

4. **Use fewer GPUs with more accumulation:**
   ```bash
   NUM_GPUS=2 GRADIENT_ACCUM_STEPS=8 ./train_0_advanced.sh
   ```

## Performance Tuning

### For Maximum Speed:
```bash
NUM_GPUS=4 \
BATCH_SIZE=4 \
GRADIENT_ACCUM_STEPS=2 \
MAX_SEQ_LENGTH=1024 \
./train_0_advanced.sh
```

### For Maximum Quality:
```bash
NUM_GPUS=4 \
BATCH_SIZE=1 \
GRADIENT_ACCUM_STEPS=8 \
MAX_SEQ_LENGTH=4096 \
NUM_EPOCHS=5 \
LEARNING_RATE=5e-6 \
./train_0_advanced.sh
```

### For Balanced Training:
```bash
NUM_GPUS=4 \
BATCH_SIZE=2 \
GRADIENT_ACCUM_STEPS=4 \
MAX_SEQ_LENGTH=2048 \
NUM_EPOCHS=3 \
./train_0_advanced.sh
```

## Monitoring Training

### View GPU Usage:
```bash
watch -n 1 nvidia-smi
```

### Monitor Training Logs:
```bash
# If using tmux
tmux attach

# Or tail the output if redirected
tail -f training.log
```

### TensorBoard (if enabled):
```bash
tensorboard --logdir ./pine-coder-4gpu --port 6006
```

## Troubleshooting

### Error: "No GPUs detected"
**Solution:** Check GPU availability
```bash
nvidia-smi
```

### Error: "CUDA out of memory"
**Solution:** Reduce memory usage
```bash
BATCH_SIZE=1 MAX_SEQ_LENGTH=1024 ./train_0_advanced.sh
```

### Error: "Address already in use"
**Solution:** Change master port
```bash
MASTER_PORT=29501 ./train_0_advanced.sh
```

### Error: "Data file not found"
**Solution:** Check data path
```bash
ls -l /workspace/trading_indicators/outputs/segments_20251014.json
```

### Slow Training Speed
**Check:**
1. GPU utilization: `nvidia-smi`
2. Increase batch size if memory allows
3. Reduce logging frequency: `LOGGING_STEPS=50`
4. Enable gradient checkpointing (already enabled by default)

## Resume Training

To resume from a checkpoint:
```bash
# Modify train_main_0.py to add --resume_from_checkpoint argument
# Or manually specify in the script
```

## Best Practices

1. **Run token analysis first:** Determine optimal `MAX_SEQ_LENGTH`
   ```bash
   python token_static_check.py --show_distribution
   ```

2. **Start with default settings:** Use `./train_0.sh` for initial testing

3. **Monitor first 100 steps:** Check for memory issues early

4. **Save checkpoints frequently:** Set `SAVE_STEPS` based on dataset size

5. **Use validation set:** Consider splitting data for validation

6. **Experiment with formatters:** Try different `FORMATTER_TYPE` options

## Advanced: Multi-Node Training

For training across multiple machines:

```bash
# On master node (node 0)
MASTER_ADDR=192.168.1.100 \
NODE_RANK=0 \
torchrun --nnodes=2 --nproc_per_node=4 ...

# On worker node (node 1)
MASTER_ADDR=192.168.1.100 \
NODE_RANK=1 \
torchrun --nnodes=2 --nproc_per_node=4 ...
```

## Recommended Settings for segments_20251014.json

Based on token analysis (601 samples, avg 529 tokens):

```bash
# Optimal balanced setup
NUM_GPUS=4 \
BATCH_SIZE=2 \
GRADIENT_ACCUM_STEPS=4 \
MAX_SEQ_LENGTH=2048 \
NUM_EPOCHS=3 \
LEARNING_RATE=1e-5 \
./train_0_advanced.sh
```

This provides:
- Effective batch size: 32
- Covers 95% of samples (1781 tokens)
- Good speed/quality trade-off