# VERL 训练自定义 Reward Function 使用指南

## 概述

本项目为交易指标策略生成创建了自定义的 reward function，专门用于评估交易策略代码和推理的质量。

## 文件结构

```
posttrain/
├── reward_function.py          # 自定义奖励函数实现
├── pt_verl.sh                 # VERL 训练配置脚本
├── setup_and_train.sh         # 完整的设置和训练脚本
└── README.md                  # 本说明文档

preprocess/tools/
├── convert_to_verl.py         # 数据格式转换脚本
├── prepare_verl_data.sh       # 数据准备脚本
└── ...
```

## 自定义 Reward Function 特性

### 评估维度

我们的 `TradingIndicatorRewardFunction` 从以下维度评估生成内容：

1. **代码质量 (30%)**
   - 代码块存在性
   - 函数/类定义
   - 注释和文档
   - 变量命名规范
   - 语法错误检测

2. **推理质量 (25%)**
   - 逻辑结构
   - 策略解释
   - 对 prompt 的响应度

3. **完整性 (20%)**
   - 入场条件
   - 出场条件  
   - 风险管理
   - 技术指标
   - 回测要素

4. **技术准确性 (15%)**
   - 技术术语使用
   - 数学公式
   - 金融术语准确性

5. **创新性 (10%)**
   - 新颖性词汇
   - 策略组合
   - 自定义指标

### 奖励和惩罚

- **风险管理奖励**: +0.15 (包含风险管理元素)
- **良好文档奖励**: +0.20 (包含详细文档)
- **语法错误惩罚**: -0.50 (发现语法错误)
- **不完整策略惩罚**: -0.30 (策略不完整)

## 使用方法

### 快速开始

1. **一键设置和训练**:
   ```bash
   cd /workspace/trading_indicators/posttrain
   ./setup_and_train.sh
   ```

### 手动步骤

1. **准备数据**:
   ```bash
   cd /workspace/trading_indicators/preprocess/tools
   ./prepare_verl_data.sh
   ```

2. **启动训练**:
   ```bash
   cd /workspace/trading_indicators/posttrain
   ./pt_verl.sh
   ```

### 测试 Reward Function

```bash
cd /workspace/trading_indicators/posttrain
python -c "
from reward_function import create_reward_function
reward_fn = create_reward_function()

# 测试示例
prompt = 'Create a RSI-based trading strategy'
response = '''
def rsi_strategy(data, period=14):
    # Calculate RSI
    rsi = calculate_rsi(data, period)
    
    # Entry: RSI oversold
    buy_signal = rsi < 30
    
    # Exit: RSI overbought  
    sell_signal = rsi > 70
    
    # Risk management
    stop_loss = 0.02  # 2% stop loss
    
    return buy_signal, sell_signal, stop_loss
'''

score = reward_fn(prompt, response)
print(f'Reward Score: {score:.3f}')
"
```

## 配置自定义

### 修改奖励权重

编辑 `reward_function.py` 中的 `TradingStrategyReward` 类：

```python
@dataclass 
class TradingStrategyReward:
    # 调整权重
    code_quality_weight: float = 0.4      # 提高代码质量权重
    reasoning_quality_weight: float = 0.3  # 提高推理质量权重
    completeness_weight: float = 0.2
    technical_accuracy_weight: float = 0.1
    innovation_weight: float = 0.0         # 降低创新性权重
    
    # 调整奖励/惩罚
    syntax_error_penalty: float = -0.8     # 加重语法错误惩罚
    risk_management_bonus: float = 0.3     # 增加风险管理奖励
```

### VERL 训练参数

编辑 `pt_verl.sh` 中的关键参数：

```bash
# 数据参数
data.train_batch_size=8                    # 小数据集适合的批次大小
data.max_prompt_length=512                 # 提示最大长度
data.max_response_length=1024              # 响应最大长度

# 学习参数
actor_rollout_ref.actor.optim.lr=5e-6      # 学习率
actor_rollout_ref.actor.kl_loss_coef=0.01  # KL散度系数

# 训练控制
trainer.total_epochs=50                     # 训练轮数
trainer.save_freq=2                        # 保存频率
trainer.test_freq=1                        # 测试频率
```

## 数据格式

### 输入数据结构
原始交易策略数据应包含：
- `id`: 策略ID
- `name`: 策略名称
- `description`: 策略描述（JSON格式）
- `reasoning`: 策略推理
- `source_code`: 源代码
- `relevant_symbols`: 相关交易品种

### VERL 格式
转换后的训练数据包含：
- `prompt`: 训练提示
- `response`: 期望响应
- `reward`: 质量评分 (0-1)

## 监控和调试

### Wandb 监控
- 项目名: `verl_trading_indicators_small`
- 实验名: `qwen3_30b_trading_small_data`
- URL: https://wandb.ai/your-username/verl_trading_indicators_small

### 关键指标
- **Reward Score**: 平均奖励分数
- **Policy Loss**: 策略网络损失
- **Value Loss**: 价值网络损失
- **KL Divergence**: 与参考模型的KL散度

### 调试技巧

1. **检查数据质量**:
   ```bash
   python main.py inspect /path/to/data.parquet --head 5
   ```

2. **测试单个样本**:
   ```bash
   python -c "
   import pandas as pd
   from reward_function import create_reward_function
   
   df = pd.read_parquet('train.parquet')
   reward_fn = create_reward_function()
   
   sample = df.iloc[0]
   score = reward_fn(sample['prompt'], sample['response'])
   print(f'Sample score: {score}')
   "
   ```

3. **检查训练配置**:
   ```bash
   # 验证 VERL 配置
   python3 -m verl.trainer.main_ppo --help
   ```

## 故障排除

### 常见问题

1. **KeyError: 'prompt'**
   - 原因: 数据格式不正确
   - 解决: 运行 `convert_to_verl.py` 转换数据

2. **内存不足**
   - 降低 `train_batch_size` 和 `ppo_micro_batch_size_per_gpu`
   - 启用更多 offload 选项

3. **训练不收敛**
   - 调整学习率
   - 检查奖励函数逻辑
   - 增加训练轮数

4. **奖励分数异常**
   - 检查数据质量
   - 调试奖励函数
   - 验证数据转换逻辑

### 日志分析

训练日志包含重要信息：
```
epoch: 1, step: 10, reward: 0.234, policy_loss: 1.23, value_loss: 0.45
```

- `reward`: 当前批次平均奖励
- `policy_loss`: 策略网络损失
- `value_loss`: 价值网络损失

## 高级配置

### 多GPU 训练
```bash
# 修改 pt_verl.sh
trainer.n_gpus_per_node=4
trainer.nnodes=1
actor_rollout_ref.rollout.tensor_model_parallel_size=2
```

### 自定义模型
```bash
# 更换基础模型
actor_rollout_ref.model.path=microsoft/DialoGPT-large
```

### 实验跟踪
```bash
# 修改实验配置
trainer.project_name='your_custom_project'
trainer.experiment_name='custom_experiment_v1'
```