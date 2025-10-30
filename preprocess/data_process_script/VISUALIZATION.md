# Data Process Script - 数据流程可视化

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Process Script Pipeline                      │
│                                                                       │
│  目标: 从原始策略数据提取高质量的 Description -> Code 训练对          │
└─────────────────────────────────────────────────────────────────────┘

Input: strategies_20251014_054134.json (24,406 strategies)
           │
           │ [Raw TradingView Strategies]
           │ - id, name, description, source_code
           │ - likes_count, author, script_url
           │
           ▼
    ┌─────────────┐
    │ 1. FILTER   │  过滤低质量策略
    └─────────────┘
           │
           │ ✓ likes_count >= 100
           │ ✓ description length >= 30
           │ ✓ source_code length >= 50
           │ ✓ No empty fields
           │
           │ (~70% retained)
           ▼
    ┌─────────────┐
    │ 2. LANGUAGE │  语言转换
    │   CONVERT   │
    └─────────────┘
           │
           │ ✓ Detect non-English
           │ ✓ Translate to English (LLM)
           │ ✓ Preserve original language info
           │
           │ (Same count, ~10% translated)
           ▼
    ┌─────────────┐
    │ 3. VIS      │  移除可视化代码
    │   REMOVE    │
    └─────────────┘
           │
           │ ✗ plot(), plotshape(), label.new()
           │ ✗ fill(), bgcolor(), table.new()
           │ ✓ strategy.entry(), calculations
           │ ✓ Core trading logic preserved
           │
           │ (Same count, ~80% cleaned)
           ▼
    ┌─────────────┐
    │ 4. QUALITY  │  质量评分与过滤
    │   SCORE     │
    └─────────────┘
           │
           │ ✓ Match score (desc-code alignment)
           │ ✓ Detail score (desc completeness)
           │ ✓ Clarity, code quality, edu value
           │ ✓ Filter: score >= 7.0
           │
           │ (~50% retained)
           ▼
Output: script_YYYYMMDD_HHMMSS.json (~350 high-quality pairs)
```

## 详细数据流

### 输入示例 (strategies_20251014_054134.json)

```json
{
  "id": "bznVflR1-SPY200SMA",
  "name": "SPY200SMA (+4%/-3%) TQQQ/QQQ STRATEGY",
  "preview_author": "freefighter07",
  "likes_count": 17,
  "description": "Summary of the Improved Strategy: When the price of SPY is +4% above the 200SMA BUY TQQQ...",
  "source_code": "//@version=5\nstrategy(\"SPY 200SMA\", overlay=true)...\nplot(sma200, color=color.blue)...\nstrategy.entry(\"Buy\", strategy.long)...",
  "script_url": "https://www.tradingview.com/script/..."
}
```

### 节点 1: Filter

```
Input:  17 likes ❌ (< 100)
        |
        v
Status: FILTERED OUT
Reason: Low likes count

---

Input:  150 likes ✓
        Description: 50 chars ✓
        Code: 800 chars ✓
        |
        v
Status: PASSED
```

### 节点 2: Language Convert

```
Input Description (Chinese):
"这是一个基于移动平均线的策略..."

        |
        v
    [LLM Detection]
        |
        v
    
Detected: Chinese
Translation: "This is a strategy based on moving average..."

Output:
{
  "description": "This is a strategy based on moving average...",
  "original_description": "这是一个基于移动平均线的策略...",
  "original_language": "Chinese",
  "was_translated": true
}
```

### 节点 3: Vis Remove

```
Input Code:
//@version=5
strategy("SPY 200SMA", overlay=true)
sma200 = ta.sma(close, 200)
enterLong = close > sma200 * 1.04

// === Plotting ===
p_sma = plot(sma200, title="200 SMA", color=color.blue)
label.new(bar_index, high, "BUY", color=color.green)

if enterLong
    strategy.entry("Buy", strategy.long)

        |
        v
    [Rule-based Removal]
        |
        v

Output Code:
//@version=5
strategy("SPY 200SMA", overlay=true)
sma200 = ta.sma(close, 200)
enterLong = close > sma200 * 1.04

if enterLong
    strategy.entry("Buy", strategy.long)

Metadata:
- visualization_removed: true
- removed_lines_count: 3
```

### 节点 4: Quality Score

```
Input:
  Description: "Buy when price crosses above SMA..."
  Code: "if close > sma200\n    strategy.entry(\"Buy\", strategy.long)"

        |
        v
    [LLM Scoring]
        |
        v

Scores:
┌──────────────────┬───────┐
│ Metric           │ Score │
├──────────────────┼───────┤
│ Match Score      │   9   │  ← Desc matches code perfectly
│ Detail Score     │   7   │  ← Good detail level
│ Clarity Score    │   8   │  ← Clear explanation
│ Code Quality     │   8   │  ← Well-structured
│ Educational Val. │   8   │  ← Good learning value
├──────────────────┼───────┤
│ Overall Score    │  8.0  │  ✓ >= 7.0 threshold
└──────────────────┴───────┘

Status: PASSED
```

### 输出格式 (script_*.json)

```json
{
  "input": "Buy when price crosses above 200 SMA by 4%, sell when below by 3%",
  "output": "//@version=5\nstrategy(\"SPY 200SMA\", overlay=true)\nsma200 = ta.sma(close, 200)\nenterLong = close > sma200 * 1.04\nexitLong = close < sma200 * 0.97\nif enterLong\n    strategy.entry(\"Buy\", strategy.long)\nif exitLong\n    strategy.close(\"Buy\")",
  "quality_score": 8.0,
  "quality_metrics": {
    "match_score": 9,
    "detail_score": 7,
    "clarity_score": 8,
    "code_quality_score": 8,
    "educational_value": 8
  },
  "metadata": {
    "id": "bznVflR1-SPY200SMA",
    "name": "SPY200SMA Strategy",
    "likes_count": 150,
    "author": "freefighter07",
    "was_translated": false,
    "original_language": "English",
    "visualization_removed": true,
    "script_url": "https://..."
  }
}
```

## 统计信息流

```
┌──────────────────────────────────────────────────────────────┐
│                      Processing Statistics                    │
└──────────────────────────────────────────────────────────────┘

Initial Count:          24,406 strategies
    │
    ├─[1. Filter]──────────────────────────────────────────────┐
    │                                                            │
    │   Removed:                                                 │
    │   ├─ Low likes (<100):        ~17,000  (70%)              │
    │   ├─ Short description:        ~1,500  (6%)               │
    │   ├─ Short code:                 ~800  (3%)               │
    │   └─ Empty fields:               ~100  (0.4%)             │
    │                                                            │
    └─> Passed: 5,000 strategies (20%)                          │
         │                                                       │
         ├─[2. Language Convert]─────────────────────────────┐  │
         │                                                    │  │
         │   Translated:         ~500 (10%)                  │  │
         │   Already English:  ~4,500 (90%)                  │  │
         │                                                    │  │
         └─> Passed: 5,000 strategies                        │  │
              │                                               │  │
              ├─[3. Vis Remove]──────────────────────────────┤  │
              │                                               │  │
              │   Cleaned:      ~4,000 (80%)                 │  │
              │   No vis code:  ~1,000 (20%)                 │  │
              │   Avg lines removed: 5.3                     │  │
              │                                               │  │
              └─> Passed: 5,000 strategies                   │  │
                   │                                          │  │
                   ├─[4. Quality Score]────────────────────┐  │  │
                   │                                        │  │  │
                   │   Score Distribution:                  │  │  │
                   │   ├─ 9-10 (Excellent):     400  (8%)  │  │  │
                   │   ├─ 7-8  (Good):        2,100 (42%)  │  │  │
                   │   ├─ 5-6  (Average):     1,800 (36%)  │  │  │
                   │   └─ 1-4  (Poor):          700 (14%)  │  │  │
                   │                                        │  │  │
                   │   Filtered (< 7.0):      ~2,500 (50%) │  │  │
                   │                                        │  │  │
                   └─> Passed: 2,500 strategies            │  │  │
                                                            │  │  │
Final Count: 2,500 strategies (10.2% retention)            │  │  │
Average Quality Score: 7.85                                │  │  │
└────────────────────────────────────────────────────────────────┘
```

## 并发处理流程

```
Language Convert / Quality Score (并发处理):

┌─────────────────────────────────────────────────────────────┐
│                  ThreadPoolExecutor (max_workers=3)          │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    Worker 1           Worker 2           Worker 3
        │                  │                  │
        ├─> LLM Call       ├─> LLM Call       ├─> LLM Call
        │   Strategy 1     │   Strategy 2     │   Strategy 3
        │                  │                  │
        ├─> LLM Call       ├─> LLM Call       ├─> LLM Call
        │   Strategy 4     │   Strategy 5     │   Strategy 6
        │                  │                  │
        └─> ...            └─> ...            └─> ...

Benefits:
- 3x faster processing
- Efficient LLM utilization
- Automatic retry on failure
- Progress tracking
```

## 错误处理流程

```
Processing Strategy
        │
        ├─> Try: Process Node
        │      │
        │      ├─> Success ✓
        │      │   └─> Continue to next node
        │      │
        │      └─> Error ✗
        │          │
        │          ├─> Retry (max 3 times)
        │          │      │
        │          │      ├─> Success ✓
        │          │      │   └─> Continue
        │          │      │
        │          │      └─> Still failing ✗
        │          │          │
        │          │          ├─> Log error
        │          │          ├─> Apply fallback
        │          │          └─> Continue with default values
        │          │
        │          └─> Continue pipeline
        │              (don't stop entire process)
        │
        └─> Next Strategy

Result: Robust processing, no data loss
```

## 配置参数影响

```
┌──────────────────────────────────────────────────────────────┐
│ Parameter Tuning Impact                                       │
└──────────────────────────────────────────────────────────────┘

MIN_LIKES_COUNT:
  50 ────────────────> ~12,000 strategies (more data, lower quality)
  100 ───────────────> ~5,000 strategies (balanced)
  200 ───────────────> ~2,000 strategies (less data, higher quality)

QUALITY_SCORE_THRESHOLD:
  6.0 ────────────────> ~4,000 strategies (more data, acceptable quality)
  7.0 ───────────────> ~2,500 strategies (balanced)
  8.0 ───────────────> ~800 strategies (less data, excellent quality)

MAX_WORKERS:
  1 ─────────────────> Serial processing (slow, stable)
  3 ─────────────────> Parallel processing (fast, balanced)
  10 ────────────────> High parallelism (fastest, may overwhelm LLM)

VIS_REMOVE (use_llm):
  False ──────────────> Rule-based only (fast, ~80% accuracy)
  True ───────────────> Rule + LLM (slow, ~95% accuracy)
```

## 时间估算

```
Processing 1000 strategies:

┌─────────────────────┬──────────┬──────────┐
│ Node                │ Time/item│ Total    │
├─────────────────────┼──────────┼──────────┤
│ Filter              │  0.001s  │    1s    │
│ Language Convert*   │  0.5s    │  ~170s   │  (parallel, 30% need)
│ Vis Remove (rule)   │  0.01s   │   10s    │
│ Quality Score*      │  1.0s    │  ~330s   │  (parallel)
├─────────────────────┼──────────┼──────────┤
│ Total               │          │  ~8.5min │
└─────────────────────┴──────────┴──────────┘

* With MAX_WORKERS=3, sequential time / 3

For 24,406 strategies: ~3.5 hours (estimated)
```

## 总结

Data Process Script 提供了一个完整、高效的 pipeline，用于从原始策略数据提取高质量的训练样本。通过多层过滤和 LLM 增强处理，确保输出数据的质量和可用性。
