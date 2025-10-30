# Data Process 0 Pipeline

这是一个数据处理管道，用于处理交易策略数据。该管道包含三个主要处理节点。

## 处理流程

### 1. Filter 节点
过滤条件：
- Likes > 100
- Description > 100 words
- Code > 100 characters

只有满足所有条件的数据才会继续处理。

### 2. Visualization Remove 节点
移除代码中的可视化和仪表板相关内容：
- 移除 AI dashboard 相关代码
- 移除图表和绘图函数
- 移除纯展示性的代码
- 保留核心交易逻辑

### 3. Restructure 节点
重新组织描述和代码结构，按以下组件分类（core_method 放在最后）：

1. **strategy_setup**: 初始设置和配置
2. **input_params**: 输入参数和设置
3. **filtering_sys**: 过滤系统和条件
4. **smart_money**: 智能资金概念和逻辑
5. **signal_gen**: 信号生成逻辑
6. **risk_management**: 风险管理
7. **core_method**: 核心计算方法（放在最后）

## 输出格式

每个组件包含两部分：
```json
{
  "strategy_setup": {
    "description": "描述内容",
    "code": "代码内容"
  },
  "input_params": {
    "description": "描述内容",
    "code": "代码内容"
  },
  // ... 其他组件
  "core_method": {
    "description": "描述内容",
    "code": "代码内容"
  }
}
```

## 使用方法

### 直接运行
```bash
python main.py input_file.json --output-dir output_directory
```

### 使用运行脚本
```bash
./run.sh input_file.json output_directory [samples]
```

## 配置

主要配置参数在 `config.py` 中：
- `MIN_LIKES`: 最小点赞数 (默认: 100)
- `MIN_DESCRIPTION_WORDS`: 最小描述词数 (默认: 100)
- `MIN_CODE_LENGTH`: 最小代码长度 (默认: 100)

LLM 配置在 `.env` 文件中：
- `LOCAL_QWEN_ENDPOINT`: LLM API 端点
- `LOCAL_QWEN_MODEL_NAME`: 模型名称
- `DEBUG_NODE_OUTPUT`: 调试输出开关