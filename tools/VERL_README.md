# VERL Training Data Preparation

这个目录包含了为 VERL 训练准备数据的工具和脚本。

## 快速开始

### 1. 准备训练数据
运行完整的数据准备流程：

```bash
cd /workspace/trading_indicators/preprocess/tools
./prepare_verl_data.sh
```

这个脚本会：
- 合并所有 `processed_batch_*.parquet` 文件
- 将数据拆分为训练集和验证集
- 更新 VERL 训练脚本的数据路径

### 2. 运行 VERL 训练
数据准备完成后，运行训练：

```bash
cd /workspace/trading_indicators/posttrain
./pt_verl.sh
```

## 手动步骤

如果需要手动控制每个步骤：

### 步骤 1: 合并 parquet 文件
```bash
cd /workspace/trading_indicators/preprocess/tools
python main.py merge ../../outputs/processed \
    --pattern "processed_batch_*.parquet" \
    --output ../../outputs/merged_processed_data.parquet
```

### 步骤 2: 拆分训练/验证数据
```bash
python split_data.py ../../outputs/merged_processed_data.parquet \
    --output-dir ../../outputs/data_splits \
    --train-ratio 0.8
```

### 步骤 3: 检查数据
```bash
# 检查训练数据
python main.py inspect ../../outputs/data_splits/train.parquet

# 检查验证数据  
python main.py inspect ../../outputs/data_splits/val.parquet
```

## 小数据集优化

当前配置针对小数据集（32条样本）进行了优化：

- **Batch sizes**: 降低到适合小数据集
- **Learning rate**: 稍微提高以加快收敛
- **Training epochs**: 增加到50轮以充分利用数据
- **Save/test frequency**: 更频繁的保存和测试
- **Memory optimization**: 启用参数offload节省内存

## 参数说明

### 训练参数调整
- `train_batch_size=8`: 小批次适合小数据集
- `ppo_mini_batch_size=4`: PPO小批次
- `ppo_micro_batch_size_per_gpu=2`: 每GPU微批次
- `total_epochs=50`: 增加训练轮数

### 内存优化
- `param_offload=True`: 参数offload
- `optimizer_offload=True`: 优化器offload
- `gpu_memory_utilization=0.8`: 提高GPU利用率

## 文件结构

```
outputs/
├── processed/              # 原始处理过的batch文件
│   ├── processed_batch_*.parquet
│   └── processing_checkpoint.json
├── merged_processed_data.parquet  # 合并后的数据
└── data_splits/           # 拆分后的训练数据
    ├── train.parquet      # 训练集
    └── val.parquet        # 验证集
```

## 故障排除

1. **数据太少**: 如果数据少于10条，脚本会自动调整拆分比例
2. **内存不足**: 可以进一步降低batch size参数
3. **训练不收敛**: 可以调整学习率或增加训练轮数

## 监控训练

训练过程会输出到控制台和 wandb，项目名称为 `verl_trading_indicators_small`。