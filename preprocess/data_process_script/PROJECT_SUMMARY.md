# Data Process Script - 项目总结

## 概述

`data_process_script` 是一个数据处理管道，用于从 TradingView 策略原始数据中提取高质量的 Description -> Code 训练样本。

## 目录结构

```
data_process_script/
├── README.md                    # 项目文档
├── main.py                      # 主程序入口
├── config.py                    # 配置文件
├── llm_client.py               # LLM 客户端
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量
├── run.sh                      # 运行脚本
├── quick_test.sh              # 快速测试脚本
├── __init__.py
└── nodes/                      # 处理节点
    ├── __init__.py
    ├── filter.py              # 过滤节点
    ├── language_convert.py    # 语言转换节点
    ├── vis_remove.py         # 可视化移除节点
    └── quality_score.py      # 质量评分节点
```

## 数据流程

### 输入数据
- 文件: `/workspace/trading_indicators/outputs/strategies_20251014_054134.json`
- 格式: TradingView 策略原始数据，包含 description, source_code, likes_count 等字段

### 处理步骤

#### 1. Filter Node (过滤)
**功能**: 去掉低质量策略
- 过滤 `likes_count < 100` 的策略
- 去掉 description 过短 (< 30 字符) 的策略
- 去掉 source_code 过短 (< 50 字符) 的策略
- 去掉空字段

**配置参数**:
```python
MIN_LIKES_COUNT = 100
MIN_CODE_LENGTH = 50
MIN_DESCRIPTION_LENGTH = 30
```

#### 2. Language Convert Node (语言转换)
**功能**: 将非英文描述转换为英文
- 使用 LLM 检测描述语言
- 如果非英文，自动翻译成英文
- 保留原始语言信息

**特点**:
- 支持并发处理 (ThreadPoolExecutor)
- 自动重试机制
- 保留原始描述

#### 3. Visualization Remove Node (可视化移除)
**功能**: 移除代码中的可视化部分，保留核心策略逻辑
- 移除 plot, plotshape, plotchar 等绘图函数
- 移除 label.new, table.new 等UI元素
- 移除 fill, bgcolor 等视觉效果
- 保留 strategy.entry, strategy.close 等交易逻辑

**实现方式**:
1. **规则过滤** (Rule-based): 使用正则表达式快速移除常见模式
2. **LLM 增强** (可选): 使用 LLM 进行更精确的清理

**示例**:
```python
# 移除前
plot(sma200, title="200 SMA", color=color.blue)
label.new(bar_index, high, "BUY", color=color.green)
if enterLong:
    strategy.entry("Buy", strategy.long)

# 移除后
if enterLong:
    strategy.entry("Buy", strategy.long)
```

#### 4. Quality Score Node (质量评分)
**功能**: 评分并过滤低质量样本
- 评估 description 和 code 的匹配度
- 检查 description 的详细程度
- 评估代码质量和教育价值
- 根据阈值过滤

**评分维度**:
- `match_score`: Description 和 Code 的匹配度
- `detail_score`: Description 的详细程度
- `clarity_score`: Description 的清晰度
- `code_quality_score`: 代码质量
- `educational_value`: 教育价值

**质量阈值**: 7.0 (可配置)

### 输出格式

```json
[
  {
    "input": "描述文本 (英文)",
    "output": "代码文本 (移除可视化后)",
    "quality_score": 8.5,
    "quality_metrics": {
      "match_score": 9,
      "detail_score": 8,
      "clarity_score": 8,
      "code_quality_score": 9,
      "educational_value": 8
    },
    "metadata": {
      "id": "bznVflR1-...",
      "name": "Strategy Name",
      "likes_count": 150,
      "author": "username",
      "was_translated": false,
      "original_language": "English",
      "visualization_removed": true,
      "script_url": "https://..."
    }
  },
  ...
]
```

输出文件名: `script_YYYYMMDD_HHMMSS.json`

## 使用方法

### 1. 安装依赖

```bash
cd /workspace/trading_indicators/preprocess/data_process_script
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件或设置环境变量:

```bash
# 输入/输出路径
export INPUT_FILE=/workspace/trading_indicators/outputs/strategies_20251014_054134.json
export OUTPUT_DIR=/workspace/trading_indicators/outputs/processed_scripts

# 过滤参数
export MIN_LIKES_COUNT=100
export QUALITY_SCORE_THRESHOLD=7.0

# LLM 配置
export LOCAL_QWEN_ENDPOINT=http://202.45.128.234:5788/v1/
export LOCAL_QWEN_MODEL_NAME=/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct
```

### 3. 运行管道

**完整运行**:
```bash
bash run.sh
```

**快速测试** (使用前 20 条数据):
```bash
bash quick_test.sh
```

**Python 直接运行**:
```bash
python main.py --input /path/to/input.json --output_dir ./outputs
```

### 4. 命令行参数

```bash
python main.py \
    --input /path/to/input.json \
    --output_dir ./outputs \
    --min_likes 100 \
    --quality_threshold 7.0 \
    --max_workers 3 \
    --no_language_convert    # 禁用语言转换
    --no_vis_remove          # 禁用可视化移除
    --no_quality_score       # 禁用质量评分
```

## 配置参数详解

### Filter 参数
- `MIN_LIKES_COUNT`: 最小点赞数 (默认: 100)
- `MIN_CODE_LENGTH`: 最小代码长度 (默认: 50)
- `MIN_DESCRIPTION_LENGTH`: 最小描述长度 (默认: 30)

### LLM 参数
- `LOCAL_QWEN_ENDPOINT`: LLM API 端点
- `LOCAL_QWEN_MODEL_NAME`: 模型名称
- `LLM_TEMPERATURE`: 温度参数 (默认: 0.1)
- `MAX_WORKERS`: 并发请求数 (默认: 3)

### Quality Score 参数
- `QUALITY_SCORE_THRESHOLD`: 质量分数阈值 (默认: 7.0)
  - 9-10: 优秀
  - 7-8: 良好
  - 5-6: 一般
  - 3-4: 较差
  - 1-2: 很差

## 性能优化

### 并发处理
- Language Convert, Visualization Remove (LLM模式), Quality Score 都支持并发处理
- 使用 ThreadPoolExecutor 进行并发 LLM 调用
- 可通过 `MAX_WORKERS` 参数控制并发数

### 可选节点
- 可以禁用特定节点以加快处理速度
- Visualization Remove 提供纯规则模式 (快速) 和 LLM 增强模式 (精确)

### 批处理
- 支持大规模数据处理
- 自动错误处理和重试
- 详细的日志输出

## 输出统计

管道会生成两个文件:

1. **主输出文件** (`script_YYYYMMDD_HHMMSS.json`): 处理后的训练数据
2. **元数据文件** (`script_YYYYMMDD_HHMMSS_metadata.json`): 统计信息

元数据包含:
- 初始策略数量
- 最终策略数量
- 保留率
- 各步骤的统计信息
- 质量分数分布
- 平均质量分数

## 示例输出

```
================================================================================
Pipeline Summary
================================================================================
Initial strategies: 1000
Final strategies: 285
Retention rate: 28.5%
Average quality score: 7.85
Output file: /workspace/trading_indicators/outputs/processed_scripts/script_20251030_120000.json
================================================================================
```

## 与 data_process_segments 的区别

| 特性 | data_process_segments | data_process_script |
|------|----------------------|---------------------|
| 输入数据 | 预处理后的 restructured_data | 原始 strategies JSON |
| 数据粒度 | Segment-wise (多个片段) | Script-wise (完整脚本) |
| Pack节点 | 提取多个 segments | 直接提取 description+code |
| 可视化处理 | 无 | 有专门的 vis_remove 节点 |
| 过滤条件 | 代码长度、重复检测 | Likes数、代码长度、描述长度 |
| 目标 | 代码片段学习 | 完整策略描述-代码对 |

## 注意事项

1. **LLM 配置**: 确保 LLM endpoint 可访问，API key 正确
2. **内存使用**: 大规模数据处理时注意内存使用
3. **并发控制**: 根据 LLM 服务器性能调整 `MAX_WORKERS`
4. **输出位置**: 确保输出目录有足够的磁盘空间
5. **日志查看**: 出错时查看详细日志进行调试

## 故障排查

### LLM 连接失败
- 检查 `LOCAL_QWEN_ENDPOINT` 配置
- 确认网络连接
- 验证 API key

### 内存不足
- 减少 `MAX_WORKERS`
- 分批处理数据

### 质量分数过低
- 降低 `QUALITY_SCORE_THRESHOLD`
- 检查输入数据质量
- 调整 LLM prompt

## 后续改进

- [ ] 支持断点续传
- [ ] 添加进度条显示
- [ ] 支持更多语言检测
- [ ] 优化可视化移除规则
- [ ] 添加数据增强功能
- [ ] 支持多模型评分对比

## 开发团队

Trading Indicators Project Team

## 版本

v1.0.0 - 2025-10-30
