# Data SFT - Supervised Fine-Tuning Data Generation

这个模块用于从 `data_process_segments` 的输出生成包含 Chain-of-Thought (COT) 推理的instruction训练数据。

## 功能

将segment-wise的代码样本转换为包含详细思考过程的教学问答对，用于SFT训练。

## Pipeline 流程

1. **COT Generation Node**: 使用LLM根据description和Pine Script代码生成包含step-by-step推理过程的instruction

## 输入格式

来自 `data_process_segments` 的输出：
```json
[
  {
    "input": "Strategy description...",
    "output": "Pine Script code..."
  }
]
```

## 输出格式

SFT训练格式的instruction数据：
```json
[
  {
    "instruction": "How can I implement a strategy that...",
    "output": "I'll help you implement this step by step...\n\nStep 1: Analyze requirements...\nStep 2: Implementation thinking...\nFinal code:\n```\ncode here\n```"
  }
]
```

## 使用方法

```bash
cd /workspace/trading_indicators/preprocess/data_sft

# 使用默认输入文件
./run.sh

# 指定输入文件和输出目录
./run.sh ../data_process_segments/outputs/segment_samples_20251029_035241.json outputs

# 禁用LLM COT生成，使用模板
USE_LLM_COT=false ./run.sh
```

## 配置参数

### 环境变量 (.env)
- `USE_LLM_COT`: 是否使用LLM生成COT (默认: true)
- `LOCAL_QWEN_ENDPOINT`: 本地Qwen模型端点
- `LOCAL_QWEN_MODEL_NAME`: 模型名称
- `MAX_RETRIES`: LLM调用最大重试次数 (默认: 3)

## COT生成特点

### LLM模式 (默认)
- 使用英文prompt，专门针对Pine Script教学设计
- 生成从strategy description到Pine Script代码的完整思考过程
- 包含step-by-step的实现分析
- 自动生成相关的学生问题

### 模板模式 (fallback)
- 当LLM调用失败时自动切换
- 使用预定义模板生成基本的COT结构
- 确保管道的稳定性

## 示例输出

生成的instruction数据包含详细的思考过程：

```
INSTRUCTION: How can I implement a strategy that enters long positions when SPY closes above the 200SMA by 4%?

OUTPUT: I'll help you implement this strategy step by step, breaking down the requirements and translating them into Pine Script code.

Let me analyze the strategy requirements first:
1. Calculate a 200-period Simple Moving Average (SMA)
2. Generate a buy signal when close price exceeds the 200SMA by 4%
3. Only enter long positions when there's no existing position

Step-by-step implementation thinking:
Step 1: Calculate the 200-period SMA using ta.sma(close, 200)
Step 2: Define the threshold as SMA × (1 + 0.04)
Step 3: Create entry condition and position management

Final implementation:
```
sma200 = ta.sma(close, 200)
upperThreshold = sma200 * (1 + 0.04)
enterLong = close > upperThreshold
if enterLong and strategy.position_size == 0
    strategy.entry("Buy", strategy.long)
```
```

## 文件结构

```
data_sft/
├── main.py                     # 主入口文件
├── run.sh                      # 运行脚本  
├── .env                        # 环境配置
├── README.md                   # 说明文档
├── nodes/                      # 处理节点
│   ├── __init__.py
│   └── cot_generation_node.py  # COT生成节点
└── outputs/                    # 输出目录
    └── sft_instructions_*.json # 生成的SFT训练数据
```