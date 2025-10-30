# Dataset Mixer - 数据集混合工具

## 功能说明

`mix_dataset.py` 是一个用于混合 script 和 segment 数据集的工具，可以按照指定比例创建多样化的训练数据。

## 核心特性

- ✅ **灵活比例控制**: 支持 0.0-1.0 任意比例
- ✅ **不放回采样**: 确保数据不重复
- ✅ **完整采样 Script**: 持续采样直到所有 script 数据都被使用
- ✅ **可控随机性**: 支持设置随机种子以保证可重现性
- ✅ **可选打乱**: 支持打乱或保持顺序
- ✅ **详细统计**: 生成详细的元数据和统计信息

## 采样策略

1. **Script 数据**: 全部使用（不放回）
2. **Segment 数据**: 根据比例从 segment 数据集中随机采样
3. **混合**: 将两个数据集合并
4. **打乱**: 可选打乱最终数据集

### 比例计算示例

假设有 1000 个 script 样本：

- `ratio=0.5` (50% script): 1000 script + 1000 segment = 2000 total
- `ratio=0.3` (30% script): 1000 script + 2333 segment = 3333 total
- `ratio=0.7` (70% script): 1000 script + 429 segment = 1429 total
- `ratio=1.0` (100% script): 1000 script + 0 segment = 1000 total
- `ratio=0.0` (0% script): 全部使用 segment 数据

## 使用方法

### 基本用法

```bash
# 50-50 混合（默认）
python mix_dataset.py \
    --script script_20251030.json \
    --segment segment_20251030.json

# 30% script, 70% segment
python mix_dataset.py \
    --script script_20251030.json \
    --segment segment_20251030.json \
    --ratio 0.3

# 80% script, 20% segment，不打乱
python mix_dataset.py \
    --script script_20251030.json \
    --segment segment_20251030.json \
    --ratio 0.8 \
    --no-shuffle

# 指定输出目录和随机种子
python mix_dataset.py \
    --script script_20251030.json \
    --segment segment_20251030.json \
    --ratio 0.5 \
    --output ./my_datasets \
    --seed 2025
```

### 使用快捷脚本

```bash
# 使用默认配置
bash mix.sh

# 自定义比例
RATIO=0.3 bash mix.sh

# 完全自定义
bash mix.sh script.json segment.json 0.4 ./output
```

### 运行测试

```bash
# 运行所有测试用例
bash test_mix.sh
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--script` | `-s` | Script 数据集路径 | 必需 |
| `--segment` | `-g` | Segment 数据集路径 | 必需 |
| `--ratio` | `-r` | Script 数据占比 (0.0-1.0) | 0.5 |
| `--output` | `-o` | 输出目录 | ./outputs |
| `--no-shuffle` | - | 不打乱数据集 | False |
| `--seed` | - | 随机种子 | 42 |

## 输入格式要求

两个数据集都必须是 JSON 数组格式，每个元素包含 `input` 和 `output` 字段：

```json
[
  {
    "input": "描述文本",
    "output": "代码文本"
  },
  ...
]
```

## 输出文件

### 1. 混合数据集 (`mixed_dataset_YYYYMMDD_HHMMSS.json`)

标准的训练数据格式，只包含 `input` 和 `output`：

```json
[
  {
    "input": "...",
    "output": "..."
  },
  ...
]
```

### 2. 元数据文件 (`mixed_dataset_YYYYMMDD_HHMMSS_metadata.json`)

包含详细的统计信息：

```json
{
  "total_samples": 2000,
  "script_samples": 1000,
  "segment_samples": 1000,
  "script_ratio": 0.5,
  "segment_ratio": 0.5,
  "target_script_ratio": 0.5,
  "shuffle": true,
  "seed": 42,
  "source_files": {
    "script": "/path/to/script.json",
    "segment": "/path/to/segment.json"
  },
  "source_counts": {
    "script_total": 1000,
    "segment_total": 5000
  },
  "source_distribution": {
    "script": 1000,
    "segment": 1000
  },
  "timestamp": "20251030_120000"
}
```

## 使用场景

### 场景 1: 平衡训练

```bash
# 50-50 平衡，同时学习完整策略和代码片段
python mix_dataset.py -s script.json -g segment.json -r 0.5
```

### 场景 2: 强化完整性

```bash
# 70% script，强化完整策略生成能力
python mix_dataset.py -s script.json -g segment.json -r 0.7
```

### 场景 3: 多样性优先

```bash
# 30% script，获得更多样化的代码模式
python mix_dataset.py -s script.json -g segment.json -r 0.3
```

### 场景 4: 多阶段训练

```bash
# 阶段1: 70% segment (基础能力)
python mix_dataset.py -s script.json -g segment.json -r 0.3 -o ./stage1

# 阶段2: 50-50 (平衡)
python mix_dataset.py -s script.json -g segment.json -r 0.5 -o ./stage2

# 阶段3: 70% script (完整性)
python mix_dataset.py -s script.json -g segment.json -r 0.7 -o ./stage3
```

## 最佳实践

### 1. 数据量匹配

确保 segment 数据集足够大：

```python
# 如果 script 有 1000 个样本
# ratio=0.3 需要约 2333 个 segment 样本
# ratio=0.5 需要约 1000 个 segment 样本
# ratio=0.7 需要约 429 个 segment 样本
```

### 2. 可重现性

使用相同的随机种子确保结果可重现：

```bash
python mix_dataset.py -s script.json -g segment.json -r 0.5 --seed 2025
```

### 3. 数据验证

混合前先验证数据格式：

```bash
# 检查格式
python -c "import json; data=json.load(open('script.json')); print(f'{len(data)} samples, keys: {list(data[0].keys())}')"
```

### 4. 分批混合

如果数据量很大，可以分批混合：

```bash
# 创建多个不同比例的数据集
for ratio in 0.3 0.5 0.7; do
  python mix_dataset.py -s script.json -g segment.json -r $ratio -o "./mixed_${ratio}"
done
```

## 示例输出

```
================================================================================
Dataset Mixer - Starting
================================================================================
Script dataset: script_20251030.json
Segment dataset: segment_20251030.json
Script ratio: 50.0%
Segment ratio: 50.0%
Shuffle: True
Random seed: 42
Output directory: ./outputs
================================================================================

Loading data from: script_20251030.json
Loaded 1000 items
Loading data from: segment_20251030.json
Loaded 5000 items
Script format validated successfully
Segment format validated successfully

Target distribution:
  Script samples: 1000 (50.0%)
  Segment samples: 1000 (50.0%)
  Total: 2000

Actual sampling:
  Script: 1000 samples
  Segment: 1000 samples

Dataset shuffled
Mixed dataset saved to: ./outputs/mixed_dataset_20251030_120000.json
Metadata saved to: ./outputs/mixed_dataset_20251030_120000_metadata.json

================================================================================
Mixing Summary
================================================================================
Total samples: 2000
Script samples: 1000 (50.0%)
Segment samples: 1000 (50.0%)
Output file: ./outputs/mixed_dataset_20251030_120000.json
Metadata file: ./outputs/mixed_dataset_20251030_120000_metadata.json
================================================================================
```

## 常见问题

### Q1: Segment 数据不够怎么办？

如果 segment 数据量小于需求量，会自动使用所有可用的 segment 数据，并输出警告。

### Q2: 如何确保数据不重复？

使用 `random.sample()` 进行不放回采样，确保每个样本只出现一次。

### Q3: 打乱会影响结果吗？

打乱只影响数据顺序，不影响数据内容。使用相同的 seed，即使打乱也能得到相同的顺序。

### Q4: 可以混合多个数据集吗？

当前版本支持两个数据集。如需混合多个数据集，可以分步进行：

```bash
# 先混合 A 和 B
python mix_dataset.py -s A.json -g B.json -r 0.5 -o ./step1

# 再混合结果和 C
python mix_dataset.py -s ./step1/mixed_*.json -g C.json -r 0.5 -o ./final
```

## 版本历史

- v1.0.0 (2025-10-30): 初始版本
  - 支持按比例混合两个数据集
  - 不放回采样
  - 可控随机性和打乱
  - 详细统计信息
