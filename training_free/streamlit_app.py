import streamlit as st
import json
import requests
import pandas as pd
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib
import re
import ast

# 设置页面配置
st.set_page_config(
    page_title="Few-Shot Code Generation Visualizer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# LLM调用函数
@st.cache_data
def call_qwen_model(prompt: str, endpoint: str, model_name: str, api_key: str = "none") -> str:
    """调用Qwen模型生成代码"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2500
    }
    
    try:
        response = requests.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json=data,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"

@st.cache_data
def load_trading_strategies(file_path: str) -> List[Dict]:
    """加载交易策略数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 过滤高质量策略
        good_strategies = [
            s for s in data 
            if (s.get('description') and s.get('source_code') and 
                len(s['description']) > 100 and 
                len(s['source_code']) > 300 and
                s.get('likes_count', 0) > 50)
        ]
        
        # 按点赞数排序
        good_strategies.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
        return good_strategies
    except Exception as e:
        st.error(f"Failed to load strategies: {e}")
        return []

def create_few_shot_prompt(examples: List[Dict], target_description: str, num_examples: int) -> str:
    """创建few-shot提示"""
    
    selected_examples = examples[:num_examples]
    
    prompt = f"""You are an expert Pine Script developer. Generate high-quality Pine Script v5 code based on strategy descriptions.

Here are {num_examples} examples of successful trading strategies:

"""
    
    for i, example in enumerate(selected_examples, 1):
        prompt += f"{'='*50}\n"
        prompt += f"EXAMPLE {i}\n"
        prompt += f"{'='*50}\n"
        prompt += f"Strategy: {example.get('name', 'Unknown')}\n"
        prompt += f"Likes: {example.get('likes_count', 0)}\n\n"
        prompt += f"Description:\n{example['description'][:400]}...\n\n"
        
        # 提取关键代码片段
        code = example['source_code']
        
        # 版本和策略声明
        lines = code.split('\n')
        version_line = next((line for line in lines if line.startswith('//@version=')), '')
        strategy_lines = [line for line in lines if 'strategy(' in line][:1]
        input_lines = [line.strip() for line in lines if 'input.' in line][:3]
        entry_lines = [line.strip() for line in lines if 'strategy.entry' in line][:2]
        
        if version_line:
            prompt += f"Version: {version_line}\n"
        if strategy_lines:
            prompt += f"Strategy Declaration: {strategy_lines[0][:100]}...\n"
        if input_lines:
            prompt += f"Input Examples:\n"
            for line in input_lines:
                prompt += f"  {line[:80]}...\n"
        if entry_lines:
            prompt += f"Entry Logic:\n"
            for line in entry_lines:
                prompt += f"  {line[:80]}...\n"
        
        prompt += "\n"
    
    prompt += f"""
{'='*60}
TARGET STRATEGY
{'='*60}

Generate complete Pine Script v5 code for this strategy:

Description: {target_description}

Requirements:
1. Use //@version=5
2. Include strategy() declaration
3. Add input parameters
4. Implement core strategy logic
5. Add entry/exit conditions
6. Include risk management
7. Add plotting/visualization
8. Follow the patterns shown in examples above

Pine Script Code:"""
    
    return prompt

def create_zero_shot_prompt(target_description: str) -> str:
    """创建zero-shot提示"""
    return f"""Generate a complete Pine Script v5 trading strategy based on this description:

{target_description}

Please provide functional Pine Script code with proper structure, inputs, logic, and visualization.

Pine Script Code:"""

def analyze_code_quality(code: str) -> Dict:
    """分析代码质量"""
    
    # 基本结构检查
    has_version = '//@version=' in code
    has_strategy = 'strategy(' in code
    has_inputs = 'input.' in code
    has_indicators = any(func in code for func in ['ta.', 'math.', 'array.'])
    has_entry_logic = 'strategy.entry' in code
    has_exit_logic = 'strategy.exit' in code or 'strategy.close' in code
    has_plotting = 'plot(' in code or 'plotshape(' in code
    
    # 代码行数统计
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    non_comment_lines = [line for line in lines if not line.startswith('//')]
    
    # Pine Script函数使用统计
    pine_functions = [
        'ta.sma', 'ta.ema', 'ta.rsi', 'ta.macd', 'ta.stoch', 'ta.atr',
        'strategy.entry', 'strategy.exit', 'strategy.close',
        'plot', 'plotshape', 'plotchar', 'label.new', 'line.new'
    ]
    
    functions_used = [func for func in pine_functions if func in code]
    
    # 计算质量分数
    score = 0
    if has_version: score += 1
    if has_strategy: score += 2
    if has_inputs: score += 1
    if has_indicators: score += 1.5
    if has_entry_logic: score += 2
    if has_exit_logic: score += 1.5
    if has_plotting: score += 1
    if len(functions_used) >= 5: score += 1
    
    return {
        "overall_score": min(score, 10.0),
        "has_version": has_version,
        "has_strategy": has_strategy,
        "has_inputs": has_inputs,
        "has_indicators": has_indicators,
        "has_entry_logic": has_entry_logic,
        "has_exit_logic": has_exit_logic,
        "has_plotting": has_plotting,
        "total_lines": len(lines),
        "code_lines": len(non_comment_lines),
        "functions_used": len(functions_used),
        "function_list": functions_used[:5]
    }

def calculate_code_similarity(code1: str, code2: str) -> Dict[str, Any]:
    """计算两段代码的相似度"""
    
    # 清理代码文本
    def clean_code(code):
        # 移除注释
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # 移除多余空白
        code = re.sub(r'\s+', ' ', code)
        return code.strip()
    
    clean_code1 = clean_code(code1)
    clean_code2 = clean_code(code2)
    
    # 1. 文本相似度 (TF-IDF + 余弦相似度)
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), analyzer='char')
    try:
        tfidf_matrix = vectorizer.fit_transform([clean_code1, clean_code2])
        text_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except:
        text_similarity = 0.0
    
    # 2. 结构相似度 (基于行匹配)
    lines1 = [line.strip() for line in clean_code1.split('\n') if line.strip()]
    lines2 = [line.strip() for line in clean_code2.split('\n') if line.strip()]
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    structural_similarity = matcher.ratio()
    
    # 3. 功能关键词相似度
    def extract_keywords(code):
        keywords = []
        # Pine Script 关键词
        pine_keywords = ['strategy', 'indicator', 'input', 'plot', r'ta\.', r'math\.', r'request\.', 'security']
        for keyword in pine_keywords:
            matches = re.findall(keyword, code, re.IGNORECASE)
            keywords.extend(matches)
        return keywords
    
    keywords1 = set(extract_keywords(clean_code1))
    keywords2 = set(extract_keywords(clean_code2))
    
    if keywords1 or keywords2:
        keyword_similarity = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
    else:
        keyword_similarity = 0.0
    
    # 4. 函数/变量名相似度
    def extract_identifiers(code):
        identifiers = set()
        # 提取变量名和函数名
        pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        matches = re.findall(pattern, code)
        for match in matches:
            if len(match) > 2 and not match.isupper():  # 过滤短名称和常量
                identifiers.add(match.lower())
        return identifiers
    
    identifiers1 = extract_identifiers(clean_code1)
    identifiers2 = extract_identifiers(clean_code2)
    
    if identifiers1 or identifiers2:
        identifier_similarity = len(identifiers1.intersection(identifiers2)) / len(identifiers1.union(identifiers2))
    else:
        identifier_similarity = 0.0
    
    # 5. 代码长度相似度
    len1, len2 = len(clean_code1), len(clean_code2)
    length_similarity = 1 - abs(len1 - len2) / max(len1, len2, 1)
    
    # 综合相似度计算
    weights = {
        'text': 0.3,
        'structural': 0.25,
        'keyword': 0.25, 
        'identifier': 0.15,
        'length': 0.05
    }
    
    overall_similarity = (
        weights['text'] * text_similarity +
        weights['structural'] * structural_similarity +
        weights['keyword'] * keyword_similarity +
        weights['identifier'] * identifier_similarity +
        weights['length'] * length_similarity
    )
    
    return {
        'overall_similarity': overall_similarity,
        'text_similarity': text_similarity,
        'structural_similarity': structural_similarity,
        'keyword_similarity': keyword_similarity,
        'identifier_similarity': identifier_similarity,
        'length_similarity': length_similarity,
        'keywords1': keywords1,
        'keywords2': keywords2,
        'identifiers1': identifiers1,
        'identifiers2': identifiers2,
        'length1': len1,
        'length2': len2
    }

def analyze_functional_consistency(code1: str, code2: str, endpoint: str, model_name: str) -> str:
    """使用AI模型分析功能一致性"""
    
    prompt = f"""
请分析以下两段Pine Script代码的功能一致性。评估它们是否实现了相同或相似的交易策略逻辑。

代码1:
```
{code1[:2000]}...
```

代码2:
```
{code2[:2000]}...
```

请从以下方面进行分析：
1. 交易策略类型 (trend following, mean reversion, breakout等)
2. 入场条件的相似性
3. 出场条件的相似性
4. 技术指标使用的相似性
5. 风险管理机制的相似性
6. 整体功能一致性评分 (0-100分)

请提供详细的分析结果和最终评分。
"""
    
    try:
        return call_qwen_model(prompt, endpoint, model_name)
    except Exception as e:
        return f"AI分析失败: {str(e)}"

def create_similarity_radar_chart(similarity_data: Dict) -> go.Figure:
    """创建相似度雷达图"""
    
    categories = ['Text Similarity', 'Structural Similarity', 'Keyword Similarity', 
                 'Identifier Similarity', 'Length Similarity']
    
    values = [
        similarity_data['text_similarity'],
        similarity_data['structural_similarity'], 
        similarity_data['keyword_similarity'],
        similarity_data['identifier_similarity'],
        similarity_data['length_similarity']
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Code Similarity',
        line=dict(color='rgb(255, 140, 0)'),
        fillcolor='rgba(255, 140, 0, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="Code Similarity Analysis",
        height=400
    )
    
    return fig

def code_similarity_page():
    """代码相似度分析页面"""
    st.title("📝 Code Similarity Analysis")
    st.markdown("Compare two code snippets and analyze their similarity and functional consistency using AI")
    
    # LLM配置
    st.sidebar.header("🔧 AI Configuration")
    endpoint = st.sidebar.text_input(
        "Endpoint", 
        value="http://202.45.128.234:5788/v1",
        help="AI model endpoint URL"
    )
    model_name = st.sidebar.text_input(
        "Model Name", 
        value="/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct",
        help="AI model name/path"
    )
    
    # 代码输入区域
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📄 Code Snippet 1")
        code1 = st.text_area(
            "Enter first code snippet:",
            height=300,
            placeholder="Paste your first Pine Script code here...",
            key="code1"
        )
        
        if code1:
            st.info(f"Length: {len(code1)} characters, {len(code1.split())} words")
    
    with col2:
        st.header("📄 Code Snippet 2") 
        code2 = st.text_area(
            "Enter second code snippet:",
            height=300,
            placeholder="Paste your second Pine Script code here...",
            key="code2"
        )
        
        if code2:
            st.info(f"Length: {len(code2)} characters, {len(code2.split())} words")
    
    # 分析按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("🔍 Analyze Similarity", type="primary", use_container_width=True)
    
    # 分析结果
    if analyze_button and code1 and code2:
        with st.spinner("Analyzing code similarity..."):
            
            # 计算基础相似度
            similarity_data = calculate_code_similarity(code1, code2)
            
            # 显示结果
            st.header("📊 Similarity Analysis Results")
            
            # 总体相似度展示
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Overall Similarity",
                    f"{similarity_data['overall_similarity']:.1%}",
                    help="Weighted average of all similarity metrics"
                )
            
            with col2:
                similarity_level = "High" if similarity_data['overall_similarity'] > 0.7 else "Medium" if similarity_data['overall_similarity'] > 0.4 else "Low"
                st.metric(
                    "Similarity Level", 
                    similarity_level,
                    help="Qualitative assessment of similarity"
                )
            
            with col3:
                confidence = "High" if max(similarity_data['text_similarity'], similarity_data['structural_similarity']) > 0.6 else "Medium" if max(similarity_data['text_similarity'], similarity_data['structural_similarity']) > 0.3 else "Low"
                st.metric(
                    "Confidence",
                    confidence,
                    help="Confidence in similarity assessment"
                )
            
            # 详细指标和可视化
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # 雷达图
                fig = create_similarity_radar_chart(similarity_data)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # 详细指标
                st.subheader("📈 Detailed Metrics")
                
                metrics_df = pd.DataFrame({
                    'Metric': [
                        'Text Similarity',
                        'Structural Similarity', 
                        'Keyword Similarity',
                        'Identifier Similarity',
                        'Length Similarity'
                    ],
                    'Score': [
                        f"{similarity_data['text_similarity']:.1%}",
                        f"{similarity_data['structural_similarity']:.1%}",
                        f"{similarity_data['keyword_similarity']:.1%}",
                        f"{similarity_data['identifier_similarity']:.1%}",
                        f"{similarity_data['length_similarity']:.1%}"
                    ]
                })
                
                # 确保所有列都是字符串类型以避免序列化问题
                metrics_df = metrics_df.astype(str)
                st.dataframe(metrics_df, use_container_width=True)
                
                # 代码统计
                st.subheader("📊 Code Statistics")
                # 创建详细统计数据表格
                stats_df = pd.DataFrame({
                    'Metric': ['Code Length', 'Keywords Count', 'Identifiers Count'],
                    'Code 1': [
                        str(similarity_data['length1']),
                        str(len(similarity_data['keywords1'])),
                        str(len(similarity_data['identifiers1']))
                    ],
                    'Code 2': [
                        str(similarity_data['length2']),
                        str(len(similarity_data['keywords2'])),
                        str(len(similarity_data['identifiers2']))
                    ],
                    'Overlap': [
                        f"{similarity_data['length_similarity']:.1%}",
                        f"{len(similarity_data['keywords1'].intersection(similarity_data['keywords2']))} keywords",
                        f"{len(similarity_data['identifiers1'].intersection(similarity_data['identifiers2']))} identifiers"
                    ]
                })
                
                # 确保所有列都是字符串类型以避免序列化问题
                stats_df = stats_df.astype(str)
                st.dataframe(stats_df, use_container_width=True)
            
            # AI功能一致性分析
            st.header("🤖 AI Functional Consistency Analysis")
            
            if st.button("🧠 Analyze Functional Consistency", type="secondary"):
                with st.spinner("AI is analyzing functional consistency..."):
                    ai_analysis = analyze_functional_consistency(code1, code2, endpoint, model_name)
                    
                    st.subheader("🎯 AI Analysis Results")
                    st.markdown(ai_analysis)
            
            # 代码差异展示
            st.header("🔍 Code Differences")
            
            # 行级差异
            lines1 = code1.splitlines()
            lines2 = code2.splitlines()
            
            diff = list(difflib.unified_diff(lines1, lines2, lineterm='', fromfile='Code 1', tofile='Code 2'))
            
            if diff:
                st.subheader("📝 Line-by-line Differences")
                diff_text = '\n'.join(diff)
                st.code(diff_text, language='diff')
            else:
                st.success("No differences found at line level!")
            
            # 关键词和标识符对比
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔑 Keywords Comparison")
                
                if similarity_data['keywords1'] or similarity_data['keywords2']:
                    common_keywords = similarity_data['keywords1'].intersection(similarity_data['keywords2'])
                    unique_keywords1 = similarity_data['keywords1'] - similarity_data['keywords2']
                    unique_keywords2 = similarity_data['keywords2'] - similarity_data['keywords1']
                    
                    if common_keywords:
                        st.success(f"**Common Keywords:** {', '.join(common_keywords)}")
                    if unique_keywords1:
                        st.info(f"**Unique to Code 1:** {', '.join(unique_keywords1)}")
                    if unique_keywords2:
                        st.warning(f"**Unique to Code 2:** {', '.join(unique_keywords2)}")
                else:
                    st.info("No Pine Script keywords detected")
            
            with col2:
                st.subheader("🏷️ Identifiers Comparison")
                
                if similarity_data['identifiers1'] or similarity_data['identifiers2']:
                    common_identifiers = similarity_data['identifiers1'].intersection(similarity_data['identifiers2'])
                    unique_identifiers1 = list(similarity_data['identifiers1'] - similarity_data['identifiers2'])[:10]  # 限制显示数量
                    unique_identifiers2 = list(similarity_data['identifiers2'] - similarity_data['identifiers1'])[:10]
                    
                    if common_identifiers:
                        st.success(f"**Common Identifiers:** {', '.join(list(common_identifiers)[:10])}")
                    if unique_identifiers1:
                        st.info(f"**Unique to Code 1:** {', '.join(unique_identifiers1)}")
                    if unique_identifiers2:
                        st.warning(f"**Unique to Code 2:** {', '.join(unique_identifiers2)}")
                else:
                    st.info("No identifiers detected")
    
    elif analyze_button:
        st.error("Please enter both code snippets to perform analysis!")
    
    # 目标策略示例代码
    with st.expander("🎯 Target Strategy Example (PowerHouse SwiftEdge AI v2.10)", expanded=False):
        st.markdown("**Complete Pine Script v5 trading strategy with multi-timeframe analysis, smart money concepts, and AI dashboard:**")
        
        target_strategy_code = '''
//@version=5
strategy("PowerHouse SwiftEdge AI v2.10", shorttitle="PSAI v2.10", overlay=true, max_bars_back=2000)

// ============================================================================
// INPUTS
// ============================================================================

// Basic Settings
pivotLength = input.int(5, "Pivot Length", minval=1, maxval=50, group="Basic Settings")
momentumThreshold = input.float(0.01, "Momentum Threshold (%)", minval=0.001, maxval=5.0, step=0.001, group="Basic Settings")
takeProfitPoints = input.int(10, "Take Profit (Points)", minval=1, group="Risk Management")
stopLossPoints = input.int(10, "Stop Loss (Points)", minval=1, group="Risk Management")

// Timeframe Settings
higherTimeframe = input.timeframe("60", "Higher Timeframe", group="Timeframes")
lowerTimeframe = input.timeframe("15", "Lower Timeframe", group="Timeframes")

// Filter Settings
enableMomentumFilter = input.bool(true, "Enable Momentum Filter", group="Filters")
enableVolumeFilter = input.bool(true, "Enable Volume Filter", group="Filters")
enableBreakoutFilter = input.bool(true, "Enable Breakout Filter", group="Filters")

// Trend Period Settings
shortTrendPeriod = input.int(30, "Short Trend Period", minval=10, maxval=500, group="Trend Analysis")
longTrendPeriod = input.int(100, "Long Trend Period", minval=50, maxval=500, group="Trend Analysis")

// AI Dashboard Settings
enableAIDashboard = input.bool(true, "Enable AI Market Analysis", group="AI Dashboard")
dashboardPosition = input.string("top_right", "Dashboard Position", options=["top_right", "top_left", "bottom_right", "bottom_left"], group="AI Dashboard")
showPredictionTable = input.bool(true, "Show Prediction Table", group="AI Dashboard")

// ============================================================================
// TECHNICAL INDICATORS
// ============================================================================

// EMAs
ema20 = ta.ema(close, 20)
ema50 = ta.ema(close, 50)
ema200 = ta.ema(close, 200)

// VWAP
vwap = ta.vwap

// ATR for volatility adjustment
atr = ta.atr(14)

// Volume indicators
volumeMA = ta.sma(volume, 20)
volumeChange = volume - volume[1]

// ============================================================================
// MULTI-TIMEFRAME ANALYSIS
// ============================================================================

// Get higher timeframe data
[htf_close, htf_ema20, htf_vwap] = request.security(syminfo.tickerid, higherTimeframe, [close, ta.ema(close, 20), ta.vwap])
[htf_4h_close, htf_4h_ema20, htf_4h_vwap] = request.security(syminfo.tickerid, "240", [close, ta.ema(close, 20), ta.vwap])
[htf_daily_close, htf_daily_ema20, htf_daily_vwap] = request.security(syminfo.tickerid, "1D", [close, ta.ema(close, 20), ta.vwap])

// Trend analysis function
getTrendDirection(price, ema, vwap_val) =>
    if price > ema and price > vwap_val
        1  // Bullish
    else if price < ema and price < vwap_val
        -1 // Bearish
    else
        0  // Neutral

// Current timeframe trend
currentTrend = getTrendDirection(close, ema20, vwap)

// Higher timeframe trends
htfTrend = getTrendDirection(htf_close, htf_ema20, htf_vwap)
htf4hTrend = getTrendDirection(htf_4h_close, htf_4h_ema20, htf_4h_vwap)
htfDailyTrend = getTrendDirection(htf_daily_close, htf_daily_ema20, htf_daily_vwap)

// ============================================================================
// MOMENTUM FILTER
// ============================================================================

// Calculate momentum
priceChange = (close - close[1]) / close[1] * 100
atrThreshold = atr / close * 100 * 2 // ATR-based threshold

// Momentum condition
momentumCondition = not enableMomentumFilter or math.abs(priceChange) > (momentumThreshold + atrThreshold)

// ============================================================================
// VOLUME FILTER
// ============================================================================

volumeCondition = not enableVolumeFilter or (volume > volumeMA and volumeChange > 0)

// ============================================================================
// BREAKOUT FILTER
// ============================================================================

// Recent highs and lows
recentHigh = ta.highest(high, 20)
recentLow = ta.lowest(low, 20)

breakoutBuyCondition = not enableBreakoutFilter or close > recentHigh[1]
breakoutSellCondition = not enableBreakoutFilter or close < recentLow[1]

// ============================================================================
// PIVOT POINTS AND SMART MONEY CONCEPTS
// ============================================================================

// Pivot highs and lows
pivotHigh = ta.pivothigh(high, pivotLength, pivotLength)
pivotLow = ta.pivotlow(low, pivotLength, pivotLength)

// Store pivot levels
var float lastPivotHigh = na
var float lastPivotLow = na

if not na(pivotHigh)
    lastPivotHigh := pivotHigh
if not na(pivotLow)
    lastPivotLow := pivotLow

// CHoCH (Change of Character) conditions
chochSellCondition = not na(lastPivotHigh) and close < lastPivotHigh and close[1] >= lastPivotHigh and close < open
chochBuyCondition = not na(lastPivotLow) and close > lastPivotLow and close[1] <= lastPivotLow and close > open

// BOS (Break of Structure) conditions
bosSellCondition = not na(lastPivotLow) and close < lastPivotLow and close[1] >= lastPivotLow and (close - open) < -atr * 0.5
bosBuyCondition = not na(lastPivotHigh) and close > lastPivotHigh and close[1] <= lastPivotHigh and (close - open) > atr * 0.5

// ============================================================================
// AI TREND SCORING
// ============================================================================

// Calculate trend scores
calculateTrendScore(trend, momentum, volatility) =>
    trendScore = trend * 0.4
    momentumScore = math.sign(momentum) * math.min(math.abs(momentum) / 2, 0.3)
    volatilityScore = math.min(volatility / (atr / close * 100), 0.3)
    trendScore + momentumScore + volatilityScore

currentScore = calculateTrendScore(currentTrend, priceChange, atr / close * 100)
htfScore = calculateTrendScore(htfTrend, 0, 0)
htf4hScore = calculateTrendScore(htf4hTrend, 0, 0)
htfDailyScore = calculateTrendScore(htfDailyTrend, 0, 0)

// AI trend predictions
getTrendPrediction(score) =>
    if score > 0.5
        "Up"
    else if score < -0.5
        "Down"
    else
        "Neutral"

currentPrediction = getTrendPrediction(currentScore)
htfPrediction = getTrendPrediction(htfScore)
htf4hPrediction = getTrendPrediction(htf4hScore)
htfDailyPrediction = getTrendPrediction(htfDailyScore)

// ============================================================================
// SIGNAL GENERATION
// ============================================================================

// Base conditions
baseBuyCondition = currentTrend == 1 and htfTrend >= 0
baseSellCondition = currentTrend == -1 and htfTrend <= 0

// Combined buy condition
buyCondition = baseBuyCondition and momentumCondition and volumeCondition and breakoutBuyCondition and (chochBuyCondition or bosBuyCondition)

// Combined sell condition
sellCondition = baseSellCondition and momentumCondition and volumeCondition and breakoutSellCondition and (chochSellCondition or bosSellCondition)

// Get Ready signals
getReadyBuy = baseBuyCondition and momentumCondition and not buyCondition
getReadySell = baseSellCondition and momentumCondition and not sellCondition

// ============================================================================
// STRATEGY EXECUTION
// ============================================================================

// Execute trades
if buyCondition and strategy.position_size == 0
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", profit=takeProfitPoints, loss=stopLossPoints)

if sellCondition and strategy.position_size == 0
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", profit=takeProfitPoints, loss=stopLossPoints)

// ============================================================================
// DYNAMIC TRENDLINES
// ============================================================================

// Calculate trend lines
var line shortTrendLine = na
var line longTrendLine = na

// Short trend line
if bar_index % shortTrendPeriod == 0
    shortHigh = ta.highest(high, shortTrendPeriod)
    shortLow = ta.lowest(low, shortTrendPeriod)
    
    if not na(shortTrendLine)
        line.delete(shortTrendLine)
    
    trendColor = currentTrend == 1 ? color.green : currentTrend == -1 ? color.red : color.gray
    shortTrendLine := line.new(bar_index - shortTrendPeriod, currentTrend == 1 ? shortLow : shortHigh, 
                              bar_index, currentTrend == 1 ? shortLow : shortHigh, 
                              color=trendColor, style=line.style_dashed, width=1)

// ============================================================================
// VISUALIZATIONS
// ============================================================================

// Plot EMAs
plot(ema20, "EMA 20", color=color.blue, linewidth=1)
plot(ema50, "EMA 50", color=color.orange, linewidth=1)
plot(vwap, "VWAP", color=color.purple, linewidth=2)

// Plot signals
plotshape(buyCondition, title="Buy Signal", location=location.belowbar, style=shape.labelup, 
          size=size.normal, color=color.green, textcolor=color.white, text="BUY")
plotshape(sellCondition, title="Sell Signal", location=location.abovebar, style=shape.labeldown, 
          size=size.normal, color=color.red, textcolor=color.white, text="SELL")

// Plot Get Ready signals
plotshape(getReadyBuy, title="Get Ready Buy", location=location.belowbar, style=shape.circle, 
          size=size.small, color=color.yellow, text="Get Ready BUY")
plotshape(getReadySell, title="Get Ready Sell", location=location.abovebar, style=shape.circle, 
          size=size.small, color=color.orange, text="Get Ready SELL")

// Plot CHoCH and BOS levels
plotshape(chochSellCondition, title="CHoCH Sell", location=location.abovebar, style=shape.diamond, 
          size=size.tiny, color=color.aqua, text="CHoCH")
plotshape(chochBuyCondition, title="CHoCH Buy", location=location.belowbar, style=shape.diamond, 
          size=size.tiny, color=color.lime, text="CHoCH")

// ============================================================================
// AI DASHBOARD
// ============================================================================

if enableAIDashboard
    // Calculate trend strength percentages
    currentStrength = math.round(math.abs(currentScore) * 100)
    htfStrength = math.round(math.abs(htfScore) * 100)
    
    // Calculate AI confidence
    alignmentScore = (math.sign(currentScore) == math.sign(htfScore) ? 0.5 : 0)
    aiConfidence = math.round(alignmentScore * 100)
    
    // Main dashboard table
    var table dashboardTable = na
    if na(dashboardTable)
        position = dashboardPosition == "top_right" ? position.top_right : position.top_left
        dashboardTable := table.new(position, 3, 5, bgcolor=color.new(color.black, 80), border_width=1)
        
        // Headers
        table.cell(dashboardTable, 0, 0, "Timeframe", text_color=color.white, bgcolor=color.new(color.blue, 50))
        table.cell(dashboardTable, 1, 0, "Trend", text_color=color.white, bgcolor=color.new(color.blue, 50))
        table.cell(dashboardTable, 2, 0, "Strength", text_color=color.white, bgcolor=color.new(color.blue, 50))

// ============================================================================
// ALERTS
// ============================================================================

alertcondition(buyCondition, title="Buy Signal", message="PowerHouse SwiftEdge AI: BUY signal generated")
alertcondition(sellCondition, title="Sell Signal", message="PowerHouse SwiftEdge AI: SELL signal generated")
'''
        
        st.code(target_strategy_code, language='pinescript')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Load Target Strategy as Code 1", key="load_target_1"):
                st.session_state.code1 = target_strategy_code
                st.success("Target strategy loaded into Code 1!")
                st.rerun()
        
        with col2:
            if st.button("📋 Load Target Strategy as Code 2", key="load_target_2"):
                st.session_state.code2 = target_strategy_code
                st.success("Target strategy loaded into Code 2!")
                st.rerun()
    
    # 示例代码
    with st.expander("💡 Try with Example Code"):
        st.markdown("Click the buttons below to load example Pine Script code for testing:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Load Example 1: Simple SMA Strategy"):
                st.session_state.code1 = '''
//@version=5
strategy("Simple SMA Strategy", overlay=true)

length = input.int(20, "SMA Length")
sma = ta.sma(close, length)

longCondition = ta.crossover(close, sma)
shortCondition = ta.crossunder(close, sma)

if longCondition
    strategy.entry("Long", strategy.long)
if shortCondition
    strategy.entry("Short", strategy.short)

plot(sma, color=color.blue)
'''
        
        with col2:
            if st.button("Load Example 2: EMA Strategy"):
                st.session_state.code2 = '''
//@version=5
strategy("EMA Crossover Strategy", overlay=true)

fastLength = input.int(12, "Fast EMA")
slowLength = input.int(26, "Slow EMA")

fastEMA = ta.ema(close, fastLength)
slowEMA = ta.ema(close, slowLength)

buySignal = ta.crossover(fastEMA, slowEMA)
sellSignal = ta.crossunder(fastEMA, slowEMA)

if buySignal
    strategy.entry("Buy", strategy.long)
if sellSignal
    strategy.entry("Sell", strategy.short)

plot(fastEMA, color=color.green)
plot(slowEMA, color=color.red)
'''

def create_quality_comparison_chart(few_shot_quality: Dict, zero_shot_quality: Dict) -> go.Figure:
    """创建质量比较图表"""
    
    categories = [
        'Has Version', 'Has Strategy', 'Has Inputs', 'Has Indicators',
        'Has Entry Logic', 'Has Exit Logic', 'Has Plotting'
    ]
    
    few_shot_values = [
        few_shot_quality['has_version'],
        few_shot_quality['has_strategy'],
        few_shot_quality['has_inputs'],
        few_shot_quality['has_indicators'],
        few_shot_quality['has_entry_logic'],
        few_shot_quality['has_exit_logic'],
        few_shot_quality['has_plotting']
    ]
    
    zero_shot_values = [
        zero_shot_quality['has_version'],
        zero_shot_quality['has_strategy'],
        zero_shot_quality['has_inputs'],
        zero_shot_quality['has_indicators'],
        zero_shot_quality['has_entry_logic'],
        zero_shot_quality['has_exit_logic'],
        zero_shot_quality['has_plotting']
    ]
    
    # 转换布尔值为数值
    few_shot_numeric = [1 if v else 0 for v in few_shot_values]
    zero_shot_numeric = [1 if v else 0 for v in zero_shot_values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=few_shot_numeric,
        theta=categories,
        fill='toself',
        name='Few-Shot',
        line_color='rgba(255, 99, 132, 0.8)'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=zero_shot_numeric,
        theta=categories,
        fill='toself',
        name='Zero-Shot',
        line_color='rgba(54, 162, 235, 0.8)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="Code Quality Comparison"
    )
    
    return fig

def main():
    # 页面导航
    st.sidebar.title("🔍 Navigation")
    page = st.sidebar.radio(
        "Choose a page:",
        ["🤖 Few-Shot vs Zero-Shot", "📝 Code Similarity Analysis"],
        index=0
    )
    
    if page == "🤖 Few-Shot vs Zero-Shot":
        few_shot_page()
    elif page == "📝 Code Similarity Analysis":
        code_similarity_page()

def few_shot_page():
    st.title("🤖 Few-Shot vs Zero-Shot Code Generation Visualizer")
    st.markdown("Interactive comparison of Pine Script code generation with different prompting strategies")
    
    # 侧边栏配置
    st.sidebar.header("🔧 Configuration")
    
    # LLM配置
    st.sidebar.subheader("LLM Settings")
    endpoint = st.sidebar.text_input(
        "Endpoint", 
        value="http://202.45.128.234:5788/v1",
        help="Qwen model endpoint URL"
    )
    model_name = st.sidebar.text_input(
        "Model Name", 
        value="/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct",
        help="Qwen model name/path"
    )
    
    # Few-shot配置
    st.sidebar.subheader("Few-Shot Settings")
    num_examples = st.sidebar.slider(
        "Number of Examples", 
        min_value=1, 
        max_value=10, 
        value=3,
        help="Number of examples to include in few-shot prompt"
    )
    
    # 加载数据
    data_file = "/workspace/trading_indicators/outputs/strategies_20251014_054134.json"
    strategies = load_trading_strategies(data_file)
    
    if not strategies:
        st.error("Failed to load trading strategies. Please check the data file.")
        return
    
    st.sidebar.success(f"Loaded {len(strategies)} high-quality strategies")
    
    # 主界面
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📝 Target Strategy")
        
        # 选择目标策略
        strategy_options = [
            f"{s['name'][:50]}... (👍{s.get('likes_count', 0)})" 
            for s in strategies[10:20]  # 避免与few-shot例子重复
        ]
        
        selected_idx = st.selectbox(
            "Select Target Strategy",
            range(len(strategy_options)),
            format_func=lambda x: strategy_options[x]
        )
        
        target_strategy = strategies[10 + selected_idx]
        target_description = target_strategy['description']
        
        st.text_area(
            "Strategy Description",
            value=target_description[:500] + "..." if len(target_description) > 500 else target_description,
            height=150,
            disabled=True
        )
        
        # 或者输入自定义描述
        st.subheader("Or Enter Custom Description")
        custom_description = st.text_area(
            "Custom Strategy Description",
            height=100,
            placeholder="Enter your own trading strategy description here..."
        )
        
        if custom_description:
            target_description = custom_description
    
    with col2:
        st.header("📚 Few-Shot Examples")
        
        # 显示将要使用的例子
        st.write(f"**Using top {num_examples} examples:**")
        
        for i, strategy in enumerate(strategies[:num_examples]):
            with st.expander(f"Example {i+1}: {strategy['name'][:40]}... (👍{strategy.get('likes_count', 0)})"):
                st.write(f"**Description:** {strategy['description'][:200]}...")
                st.write(f"**Code Length:** {len(strategy['source_code'])} characters")
                if st.checkbox(f"Show code for example {i+1}", key=f"show_code_{i}"):
                    st.code(strategy['source_code'][:500] + "...", language="javascript")
    
    # 生成按钮
    st.header("🚀 Generate Code")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        generate_few_shot = st.button("🎯 Generate Few-Shot", type="primary")
    
    with col2:
        generate_zero_shot = st.button("🎲 Generate Zero-Shot", type="secondary")
    
    with col3:
        generate_both = st.button("⚡ Generate Both", type="primary")
    
    # 结果展示区域
    if 'few_shot_result' not in st.session_state:
        st.session_state.few_shot_result = None
    if 'zero_shot_result' not in st.session_state:
        st.session_state.zero_shot_result = None
    if 'few_shot_prompt' not in st.session_state:
        st.session_state.few_shot_prompt = None
    if 'zero_shot_prompt' not in st.session_state:
        st.session_state.zero_shot_prompt = None
    
    # 生成逻辑
    if generate_few_shot or generate_both:
        with st.spinner("Generating few-shot code..."):
            few_shot_prompt = create_few_shot_prompt(strategies, target_description, num_examples)
            few_shot_result = call_qwen_model(few_shot_prompt, endpoint, model_name)
            st.session_state.few_shot_result = few_shot_result
            st.session_state.few_shot_prompt = few_shot_prompt
    
    if generate_zero_shot or generate_both:
        with st.spinner("Generating zero-shot code..."):
            zero_shot_prompt = create_zero_shot_prompt(target_description)
            zero_shot_result = call_qwen_model(zero_shot_prompt, endpoint, model_name)
            st.session_state.zero_shot_result = zero_shot_result
            st.session_state.zero_shot_prompt = zero_shot_prompt
    
    # 结果比较
    if st.session_state.few_shot_result or st.session_state.zero_shot_result:
        st.header("📊 Results Comparison")
        
        # 创建标签页
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Generated Code", "🎯 Prompts", "📈 Quality Analysis", "📋 Summary"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Few-Shot Generated Code")
                if st.session_state.few_shot_result:
                    st.code(st.session_state.few_shot_result, language="javascript", line_numbers=True)
                    st.info(f"**Length:** {len(st.session_state.few_shot_result)} characters")
                else:
                    st.info("Click 'Generate Few-Shot' to see results")
            
            with col2:
                st.subheader("🎲 Zero-Shot Generated Code")
                if st.session_state.zero_shot_result:
                    st.code(st.session_state.zero_shot_result, language="javascript", line_numbers=True)
                    st.info(f"**Length:** {len(st.session_state.zero_shot_result)} characters")
                else:
                    st.info("Click 'Generate Zero-Shot' to see results")
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Few-Shot Prompt")
                if st.session_state.few_shot_prompt:
                    st.text_area(
                        "Few-Shot Prompt", 
                        value=st.session_state.few_shot_prompt,
                        height=400,
                        disabled=True
                    )
                    st.info(f"**Prompt Length:** {len(st.session_state.few_shot_prompt)} characters")
                else:
                    st.info("No few-shot prompt generated yet")
            
            with col2:
                st.subheader("🎲 Zero-Shot Prompt")
                if st.session_state.zero_shot_prompt:
                    st.text_area(
                        "Zero-Shot Prompt", 
                        value=st.session_state.zero_shot_prompt,
                        height=400,
                        disabled=True
                    )
                    st.info(f"**Prompt Length:** {len(st.session_state.zero_shot_prompt)} characters")
                else:
                    st.info("No zero-shot prompt generated yet")
        
        with tab3:
            if st.session_state.few_shot_result and st.session_state.zero_shot_result:
                few_shot_quality = analyze_code_quality(st.session_state.few_shot_result)
                zero_shot_quality = analyze_code_quality(st.session_state.zero_shot_result)
                
                # 质量分数比较
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Few-Shot Quality Score",
                        f"{few_shot_quality['overall_score']:.1f}/10",
                        delta=f"{few_shot_quality['overall_score'] - zero_shot_quality['overall_score']:.1f}"
                    )
                
                with col2:
                    st.metric(
                        "Zero-Shot Quality Score", 
                        f"{zero_shot_quality['overall_score']:.1f}/10"
                    )
                
                with col3:
                    improvement = few_shot_quality['overall_score'] - zero_shot_quality['overall_score']
                    st.metric(
                        "Few-Shot Improvement",
                        f"{improvement:+.1f}",
                        delta=f"{improvement/zero_shot_quality['overall_score']*100:+.1f}%" if zero_shot_quality['overall_score'] > 0 else "N/A"
                    )
                
                # 雷达图比较
                st.plotly_chart(
                    create_quality_comparison_chart(few_shot_quality, zero_shot_quality),
                    use_container_width=True
                )
                
                # 详细指标比较
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🎯 Few-Shot Metrics")
                    st.json(few_shot_quality)
                
                with col2:
                    st.subheader("🎲 Zero-Shot Metrics")
                    st.json(zero_shot_quality)
            
            else:
                st.info("Generate both few-shot and zero-shot code to see quality comparison")
        
        with tab4:
            st.subheader("📋 Experiment Summary")
            
            if st.session_state.few_shot_result and st.session_state.zero_shot_result:
                summary_data = {
                    "Metric": [
                        "Examples Used",
                        "Few-Shot Prompt Length",
                        "Zero-Shot Prompt Length", 
                        "Few-Shot Code Length",
                        "Zero-Shot Code Length",
                        "Few-Shot Quality Score",
                        "Zero-Shot Quality Score",
                        "Quality Improvement"
                    ],
                    "Value": [
                        f"{num_examples} strategies",
                        f"{len(st.session_state.few_shot_prompt)} chars",
                        f"{len(st.session_state.zero_shot_prompt)} chars",
                        f"{len(st.session_state.few_shot_result)} chars", 
                        f"{len(st.session_state.zero_shot_result)} chars",
                        f"{analyze_code_quality(st.session_state.few_shot_result)['overall_score']:.1f}/10",
                        f"{analyze_code_quality(st.session_state.zero_shot_result)['overall_score']:.1f}/10",
                        f"{analyze_code_quality(st.session_state.few_shot_result)['overall_score'] - analyze_code_quality(st.session_state.zero_shot_result)['overall_score']:+.1f}"
                    ]
                }
                
                df = pd.DataFrame(summary_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Complete both generations to see summary")

if __name__ == "__main__":
    main()