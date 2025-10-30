# Data Process Segments - 新增节点说明

## 概览

在原有的 Pack → Filter → Quality Score 流程基础上，新增了两个 LLM 节点：

### 新增节点

#### 1. Language Convert Node (语言转换节点)
**位置**: Filter 之后，Description Augment 之前

**功能**:
- 自动检测 `input` 和 `output` 字段中的非英文内容
- 支持检测：中文、日文、韩文、俄文(西里尔文)、阿拉伯文、泰文等
- 使用 LLM 将检测到的非英文内容翻译成英文
- 保留技术术语和代码片段不翻译

**示例**:
```json
// 输入
{
  "input": "本策略基于 顺序三连穿越 原则：当 MA5 依次上穿 MA10、MA30、MA60 时，触发趋势做多信号",
  "output": "ma5 = ta.sma(close, 5)"
}

// 输出
{
  "input": "This strategy is based on the sequential triple crossover principle: when MA5 crosses above MA10, MA30, and MA60 in sequence, it triggers a bullish trend signal",
  "output": "ma5 = ta.sma(close, 5)",
  "_language_converted": true
}
```

#### 2. Description Augment Node (描述增强节点)
**位置**: Language Convert 之后，Quality Score 之前

**功能**:
- 使用 LLM 评估 description 和 code 的匹配度（0-10分）
- 如果匹配度低于阈值（默认6.0），则重新生成 description
- **重要**: 重新生成时，原始 description 会作为参考传递给 LLM
- LLM 会基于 code 生成更准确的描述，同时参考原描述中的有用信息
- 保留原始 description 在 `_original_input` 字段中

**示例**:
```json
// 输入（描述与代码不匹配）
{
  "input": "Uses ADX and DI indicators to confirm trend strength",
  "output": "sma200 = ta.sma(close, 200)\nupperThreshold = sma200 * 1.04"
}

// 输出（重新生成描述）
{
  "input": "Calculates a 200-period Simple Moving Average and sets an upper threshold at 4% above the SMA to identify potential entry points",
  "output": "sma200 = ta.sma(close, 200)\nupperThreshold = sma200 * 1.04",
  "_original_input": "Uses ADX and DI indicators to confirm trend strength",
  "_description_regenerated": true,
  "_match_score": 3
}
```

### 更新的 Filter Node
**新增功能**: 检测并过滤空字段

```python
# 现在会过滤掉以下情况：
- input 或 output 为 None
- input 或 output 为空字符串 ""
- input 或 output 为只包含空格的字符串 "   "
- output 为空列表 []
- output 为只包含空字符串的列表 ["", "  "]
```

## 完整流程

```
1. Pack Node
   └─> 从 restructured_data 提取 segments
   
2. Filter Node (更新)
   ├─> 过滤空字段 (新增)
   ├─> 过滤短描述或无意义代码
   └─> 去重

3. Language Convert Node (新增)
   ├─> 检测非英文内容
   └─> 翻译成英文

4. Description Augment Node (新增)
   ├─> 评估 description-code 匹配度
   ├─> 低于阈值时重新生成（参考原描述）
   └─> 限制新描述在 1024 tokens 以内

5. Quality Score Node
   └─> LLM 打分过滤
```

## 使用方法

### 基本使用（默认配置：语言转换开启，描述增强关闭）
```bash
python main.py --input data.json --output_dir outputs
```

### 启用描述增强（默认关闭）
```bash
python main.py --input data.json --enable_description_augment true
```

### 禁用语言转换
```bash
python main.py --input data.json --enable_language_convert false
```

### 调整描述匹配阈值
```bash
# 更严格（更多描述会被重新生成）
python main.py --input data.json --description_match_threshold 7.0

# 更宽松（更少描述会被重新生成）
python main.py --input data.json --description_match_threshold 5.0
```

### 使用 run.sh
```bash
# 所有功能默认开启
./run.sh input.json output_dir
```

## 配置参数

### 环境变量
```bash
# LLM 配置（用于语言转换和描述增强）
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="http://your-endpoint/v1/"  # 可选，使用自定义端点

# 或使用本地 Qwen 配置
export LOCAL_QWEN_ENDPOINT="http://202.45.128.234:5788/v1/"
export LOCAL_QWEN_API_KEY="none"
export LLM_MODEL="/path/to/model"
```

### 命令行参数
```bash
--input                           # 输入文件路径（必需）
--output_dir                      # 输出目录（默认: outputs）
--enable_language_convert         # 启用语言转换（默认: true）
--enable_description_augment      # 启用描述增强（默认: false）⚠️ 默认关闭
--description_match_threshold     # 描述匹配阈值 0-10（默认: 6.0）
```

## 输出格式

### 正常处理的 segment
```json
{
  "input": "Description in English",
  "output": "code content",
  "_match_score": 8.5  // 如果经过描述增强
}
```

### 语言转换的 segment
```json
{
  "input": "Translated English description",
  "output": "code content",
  "_language_converted": true
}
```

### 描述重新生成的 segment
```json
{
  "input": "Newly generated description",
  "output": "code content",
  "_original_input": "Original description that didn't match",
  "_description_regenerated": true,
  "_match_score": 4.2,
  "_match_reasoning": "Description mentions ADX but code only uses SMA"
}
```

## 注意事项

1. **LLM 依赖**: Language Convert 和 Description Augment 节点需要 LLM 支持
2. **描述增强默认关闭**: 由于处理时间和效果考虑，Description Augment 默认关闭，需要时手动开启
3. **处理时间**: 
   - 仅语言转换: 每个非英文 segment 需要 1 次 LLM 调用
   - 启用描述增强: 每个 segment 额外需要 2 次 LLM 调用（检查+生成）
4. **成本考虑**: 如果使用付费 API，建议先用小数据集测试
5. **质量 vs 速度**: 可以禁用某些节点来加快处理速度

## 测试

```bash
# 测试语言检测（无需 LLM）
python test_detection_only.py

# 测试完整流程（需要 LLM）
bash quick_test.sh
```

## 问题排查

### 输出还有中文
- 检查是否正确设置 `--enable_language_convert true`
- 检查 LLM endpoint 和 API key 是否配置正确
- 查看日志中是否有 "LanguageConvertNode" 的输出

### 描述没有被增强
- 检查 `--description_match_threshold` 设置
- 较高的阈值（如 8.0）会重新生成更多描述
- 较低的阈值（如 4.0）会保留更多原始描述

### LLM 调用失败
- 检查网络连接
- 验证 API endpoint 是否可访问
- 确认模型名称正确
- 查看详细错误日志
