# Data Process Script

提取高质量的完整的 Description -> Code 的数据。

## 输入数据

从 `/workspace/trading_indicators/outputs/strategies_20251014_054134.json` 直接提取 description 和 source_code。

## Pipeline 步骤

1. **Filter**: 去掉 likes_count < 100 的策略，去掉 description 或者 code 过短的策略
2. **Language Convert**: 如果有非英文，转换成英文
3. **Vis Remove**: 去掉代码中 visualize 的部分
4. **Scoring**: 用大模型为提取的 input output 打分，看他们是否 match，description 是否有充足的 detail，根据 threshold 决定是否 filter

## 输出格式

```json
[
  {
    "input": "description text",
    "output": "code text",
    "quality_score": 8.5,
    "quality_metrics": {...},
    "metadata": {...}
  },
  ...
]
```

输出到 `script_YYYYMMDD_HHMMSS.json`

## 使用方法

```bash
# 基本使用
python main.py

# 指定输入文件
python main.py --input /path/to/strategies.json

# 指定输出目录
python main.py --output_dir ./outputs

# 自定义阈值
python main.py --min_likes 100 --quality_threshold 7.0

# 使用运行脚本
bash run.sh
```

## 配置

在 `.env` 或 `config.py` 中配置:

- `MIN_LIKES_COUNT`: 最小点赞数 (默认: 100)
- `MIN_CODE_LENGTH`: 最小代码长度 (默认: 50)
- `MIN_DESCRIPTION_LENGTH`: 最小描述长度 (默认: 30)
- `QUALITY_SCORE_THRESHOLD`: 质量分数阈值 (默认: 7.0)
- LLM 配置

## 节点说明

### 1. Filter Node
- 过滤低点赞数策略
- 去掉描述或代码过短的样本
- 去掉空字段

### 2. Language Convert Node
- 检测非英文内容
- 使用 LLM 翻译成英文
- 保留原始语言信息

### 3. Visualization Remove Node
- 移除可视化相关代码 (plot, label, fill 等)
- 保留核心策略逻辑
- 基于规则+LLM 双重过滤

### 4. Quality Score Node
- 评估 description 和 code 的匹配度
- 检查描述的详细程度
- 根据阈值过滤低质量样本
