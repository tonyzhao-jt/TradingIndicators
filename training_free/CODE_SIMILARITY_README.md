# Code Analysis Streamlit Application

这个 Streamlit 应用现在包含两个主要功能页面：

## 📝 功能页面

### 1. 🤖 Few-Shot vs Zero-Shot Code Generation
- 原有的代码生成对比功能
- 支持 Pine Script 策略的 Few-shot 和 Zero-shot 生成
- 质量分析和对比可视化

### 2. 📝 Code Similarity Analysis (新增)
用户可以贴入两段代码片段，系统会调用 AI 模型判断这两个代码的相似度和功能一致性。

## 🔍 代码相似度分析功能

### 主要特性：
1. **多维度相似度分析**
   - 文本相似度 (TF-IDF + 余弦相似度)
   - 结构相似度 (基于行匹配)
   - 关键词相似度 (Pine Script 特定关键词)
   - 标识符相似度 (变量名和函数名)
   - 长度相似度

2. **可视化展示**
   - 雷达图显示各维度相似度
   - 详细指标表格
   - 代码统计对比

3. **AI 功能一致性分析**
   - 调用 AI 模型深度分析代码的功能逻辑
   - 评估交易策略的一致性
   - 提供详细的分析报告和评分

4. **代码差异分析**
   - 行级差异对比
   - 关键词和标识符对比
   - 高亮显示差异

5. **示例代码**
   - 内置示例代码供测试
   - 一键加载不同类型的策略代码

## 🚀 使用方法

### 启动应用
```bash
# 方式1: 使用启动脚本
./run_app.sh

# 方式2: 直接运行
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

### 使用代码相似度分析
1. 在侧边栏选择 "📝 Code Similarity Analysis"
2. 配置 AI 模型的 endpoint 和 model name
3. 在两个文本框中分别粘贴要对比的代码
4. 点击 "🔍 Analyze Similarity" 按钮
5. 查看相似度分析结果
6. 可选择点击 "🧠 Analyze Functional Consistency" 进行 AI 深度分析

### 示例测试
- 点击页面底部的示例按钮加载测试代码
- 系统提供了 SMA 策略和 EMA 策略的示例代码
- 可以用这些示例测试相似度分析功能

## 📊 分析结果说明

### 相似度评分
- **Overall Similarity**: 综合相似度评分 (0-100%)
- **Text Similarity**: 基于字符级 n-gram 的文本相似度
- **Structural Similarity**: 基于代码行的结构相似度
- **Keyword Similarity**: Pine Script 关键词匹配度
- **Identifier Similarity**: 变量名和函数名相似度
- **Length Similarity**: 代码长度相似度

### 相似度等级
- **High**: > 70% - 代码高度相似
- **Medium**: 40-70% - 代码部分相似
- **Low**: < 40% - 代码差异较大

### AI 功能一致性分析
AI 模型会从以下角度分析：
- 交易策略类型
- 入场条件相似性
- 出场条件相似性
- 技术指标使用
- 风险管理机制
- 整体功能一致性评分

## 🛠️ 技术实现

### 核心算法
1. **TF-IDF + 余弦相似度**: 用于文本相似度计算
2. **序列匹配算法**: 用于结构相似度分析
3. **正则表达式**: 用于关键词和标识符提取
4. **权重加权平均**: 用于综合相似度计算

### 依赖库
- `streamlit`: Web 应用框架
- `scikit-learn`: 机器学习算法
- `pandas`: 数据处理
- `plotly`: 数据可视化
- `difflib`: 差异分析
- `requests`: API 调用

## 🔗 访问应用

应用启动后，在浏览器中访问：
- 本地访问: http://localhost:8501
- 远程访问: http://0.0.0.0:8501

导航栏在左侧边栏，可以在两个功能页面之间切换。