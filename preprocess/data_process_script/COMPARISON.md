# Data Process Script vs Data Process Segments 对比

## 核心区别

### data_process_script (新建)
**目标**: 提取完整的 Description -> Code 数据对
- 输入: 原始 strategies JSON (`strategies_20251014_054134.json`)
- 输出: 完整策略的描述-代码对 (`script_YYYYMMDD_HHMMSS.json`)
- 粒度: **Script-level** (一个策略 = 一个样本)

### data_process_segments (现有)
**目标**: 提取代码片段级别的训练样本
- 输入: 预处理后的 restructured_data
- 输出: 代码片段的描述-代码对 (`segment_samples_*.json`)
- 粒度: **Segment-level** (一个策略 = 多个片段样本)

## Pipeline 对比

### data_process_script Pipeline

```
Raw Strategies JSON
         |
         v
[1. Filter] ──────────────────────> 过滤低 likes、短描述、短代码
         |
         v
[2. Language Convert] ─────────────> 非英文 → 英文
         |
         v
[3. Visualization Remove] ─────────> 移除 plot, label 等可视化代码
         |
         v
[4. Quality Score & Filter] ───────> LLM 评分，过滤低质量
         |
         v
script_YYYYMMDD_HHMMSS.json
(完整策略描述-代码对)
```

### data_process_segments Pipeline

```
Restructured Data
         |
         v
[1. Pack] ────────────────────────> 提取多个 segments
         |
         v
[2. Filter] ──────────────────────> 过滤短代码、重复 segments
         |
         v
[3. Language Convert] ────────────> 非英文 → 英文
         |
         v
[4. Description Augment] ─────────> 检查匹配度，重新生成描述
         |
         v
[5. Quality Score] ───────────────> LLM 评分
         |
         v
segment_samples_*.json
(代码片段描述-代码对)
```

## 节点功能对比

| 节点 | data_process_script | data_process_segments |
|------|--------------------|-----------------------|
| **Pack** | ❌ 无 (直接提取) | ✅ 提取多个 segments |
| **Filter** | ✅ Likes + 长度过滤 | ✅ 长度 + 重复检测 |
| **Language Convert** | ✅ LLM 翻译 | ✅ LLM 翻译 |
| **Description Augment** | ❌ 无 | ✅ 重新生成描述 |
| **Visualization Remove** | ✅ 移除可视化代码 | ❌ 无 |
| **Quality Score** | ✅ 评分+过滤 | ✅ 评分 |

## 详细对比

### 1. 输入数据

**data_process_script**:
```json
{
  "id": "bznVflR1-...",
  "name": "SPY200SMA Strategy",
  "description": "Summary of the strategy...",
  "source_code": "//@version=5\nstrategy(...)...",
  "likes_count": 17,
  "preview_author": "freefighter07",
  ...
}
```

**data_process_segments**:
```json
{
  "id": "xxx",
  "restructured_data": {
    "overview_and_context": "...",
    "input_parameters": {...},
    "calculation_logic": {...},
    "entry_exit_logic": {...}
  }
}
```

### 2. 过滤条件

**data_process_script**:
- ✅ `likes_count >= 100`
- ✅ `len(description) >= 30`
- ✅ `len(source_code) >= 50`
- ✅ 无空字段

**data_process_segments**:
- ✅ `len(code) >= 20`
- ✅ `len(description) >= 15`
- ✅ 代码重复检测 (similarity < 0.85)
- ✅ 有意义的代码 (非纯注释)

### 3. 可视化处理

**data_process_script** - 专门的 vis_remove 节点:
```python
# 移除内容
- plot(), plotshape(), plotchar()
- label.new(), table.new()
- fill(), bgcolor()
- 可视化相关变量 (p_xxx)

# 保留内容
- strategy.entry(), strategy.close()
- 计算逻辑和指标
- 输入参数
```

**data_process_segments**: 无专门处理（保留原样）

### 4. 质量评分

**data_process_script** - 评分维度:
```python
{
  "match_score": 9,        # 描述和代码匹配度
  "detail_score": 8,       # 描述详细程度
  "clarity_score": 8,      # 描述清晰度
  "code_quality_score": 9, # 代码质量
  "educational_value": 8   # 教育价值
}
```

**data_process_segments** - 评分维度:
```python
{
  "clarity": 8,
  "accuracy": 9,
  "educational_value": 8,
  "code_quality": 9,
  "completeness": 8
}
```

### 5. 输出格式

**data_process_script**:
```json
{
  "input": "完整的策略描述 (英文)",
  "output": "完整的策略代码 (移除可视化)",
  "quality_score": 8.5,
  "quality_metrics": {...},
  "metadata": {
    "id": "xxx",
    "likes_count": 150,
    "was_translated": false,
    "visualization_removed": true,
    ...
  }
}
```

**data_process_segments**:
```json
{
  "input": "某个片段的描述",
  "output": "对应的代码片段",
  "quality_score": 8.2,
  "segment_key": "calculation_logic",
  "source_id": "xxx",
  ...
}
```

## 使用场景

### data_process_script 适用于:
- ✅ **完整策略学习**: 学习如何从描述生成完整策略
- ✅ **端到端训练**: Description → Complete Code
- ✅ **代码生成任务**: 根据需求生成完整可运行的代码
- ✅ **高质量筛选**: 基于 likes 和 LLM 评分的双重过滤
- ✅ **去除噪音**: 移除可视化代码，专注核心逻辑

### data_process_segments 适用于:
- ✅ **细粒度学习**: 学习特定功能的代码实现
- ✅ **模块化训练**: 分别学习参数定义、计算逻辑、交易逻辑等
- ✅ **代码补全**: 根据描述补全特定代码段
- ✅ **代码解释**: 解释特定代码片段的功能
- ✅ **数据增强**: 一个策略生成多个训练样本

## 数据量对比

假设原始数据有 1000 个策略:

**data_process_script**:
- 输入: 1000 strategies
- Filter (likes<100): ~700 strategies
- Language Convert: ~700 strategies
- Vis Remove: ~700 strategies
- Quality Score (threshold=7.0): ~350 strategies
- **最终输出**: ~350 个样本

**data_process_segments**:
- 输入: 1000 strategies
- Pack (每个生成4-6个segments): ~5000 segments
- Filter: ~4000 segments
- Language Convert: ~4000 segments
- Description Augment: ~4000 segments
- Quality Score: ~3000 segments
- **最终输出**: ~3000 个样本

## 质量 vs 数量

| 方面 | data_process_script | data_process_segments |
|------|--------------------|-----------------------|
| **样本数量** | 较少 (~350/1000) | 较多 (~3000/1000) |
| **样本质量** | 更高 (likes+LLM双重过滤) | 中等 (LLM评分) |
| **代码完整性** | 完整可运行 | 代码片段 |
| **训练难度** | 较难 (长序列) | 较易 (短序列) |
| **实用性** | 直接可用的完整代码 | 需要组合使用 |

## 推荐使用策略

### 阶段 1: 基础训练 (data_process_segments)
- 使用细粒度数据训练基础能力
- 学习各种代码模式和结构
- 数据量大，训练更充分

### 阶段 2: 高级训练 (data_process_script)
- 使用完整策略训练端到端能力
- 学习完整策略的组织和结构
- 高质量数据，提升实用性

### 阶段 3: 混合训练
- 50% data_process_segments (细粒度能力)
- 50% data_process_script (完整性和实用性)
- 平衡数量和质量

## 性能对比

| 指标 | data_process_script | data_process_segments |
|------|--------------------|-----------------------|
| **处理速度** | 较快 (节点少) | 较慢 (节点多) |
| **LLM 调用** | 2次/样本 (translate+score) | 3次/样本 (translate+augment+score) |
| **并发支持** | ✅ | ✅ |
| **内存使用** | 中等 | 较高 (多样本) |
| **可扩展性** | 好 | 好 |

## 总结

- **data_process_script**: 追求**质量**和**完整性**，适合生成可直接使用的完整策略代码
- **data_process_segments**: 追求**数量**和**多样性**，适合学习各种代码模式和结构

两者互补，建议根据训练阶段和目标选择或组合使用。
