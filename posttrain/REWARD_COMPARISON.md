# VERL Reward Function 比较

本项目提供了两种不同的 reward function 实现，适用于不同的训练需求和模型能力。

## 🎯 Reward Function 对比

### 1. 复杂 Reward Function (`reward_function.py`)
**适用场景**: 模型能力较强，需要细粒度评估

#### 特点：
- **多维度评估**: 5个维度（代码质量、推理质量、完整性、技术准确性、创新性）
- **基于规则**: 使用启发式规则和关键词匹配
- **快速执行**: 不需要额外的 LLM 调用
- **细粒度控制**: 可精确调整各维度权重

#### 评估维度：
```python
code_quality_weight: 0.3        # 代码质量
reasoning_quality_weight: 0.25  # 推理质量  
completeness_weight: 0.2        # 完整性
technical_accuracy_weight: 0.15 # 技术准确性
innovation_weight: 0.1          # 创新性
```

#### 优势：
✅ 执行速度快  
✅ 可解释性强  
✅ 资源消耗少  
✅ 可精确调优  

#### 劣势：
❌ 可能对模型要求过高  
❌ 基于规则，可能不够灵活  
❌ 需要手动调整规则  

---

### 2. 简化 Reward Function (`reward_plain.py`)
**适用场景**: 使用 LLM 判断，更适合当前模型能力

#### 特点：
- **LLM 评估**: 使用 Qwen3-Coder-30B 进行智能评判
- **相似度对比**: 与验证集数据进行相似度比较
- **代码正确性**: 语法检查 + LLM 代码质量评估
- **灵活判断**: LLM 可以理解语义和上下文

#### 评估组件：
```python
similarity_weight: 0.6          # 与参考数据的相似度
code_correctness_weight: 0.4    # 代码正确性
```

#### 优势：
✅ 更智能的语义理解  
✅ 适应性强  
✅ 与参考数据对比  
✅ 更符合人类判断  

#### 劣势：
❌ 执行速度较慢（需要LLM调用）  
❌ 资源消耗较大  
❌ 可能有随机性  

---

## 🚀 使用指南

### 复杂 Reward Function
```bash
# 使用原始的复杂reward function
cd /workspace/trading_indicators/posttrain
./pt_verl.sh
```

### 简化 Reward Function  
```bash
# 使用LLM-based的简化reward function
cd /workspace/trading_indicators/posttrain
./pt_verl_plain.sh

# 或使用交互式设置
./setup_plain_training.sh
```

## 📊 训练配置对比

| 配置项 | 复杂版本 | 简化版本 |
|--------|----------|----------|
| 模型 | Qwen3-Coder-30B | Qwen3-Coder-30B |
| Batch Size | 8 | 8 |
| 训练轮数 | 50 | 50 |
| Reward Function | 规则基础 | LLM基础 |
| 执行速度 | 快 | 中等 |
| 资源消耗 | 低 | 中等 |
| 项目名 | verl_trading_indicators_small | verl_trading_plain_reward |

## 🎯 选择建议

### 选择复杂版本 (`reward_function.py`) 如果：
- 你的模型已经能够生成相对完整的策略代码
- 你希望精确控制每个评估维度的权重
- 你需要快速的训练反馈
- 你有充分的领域知识来调整规则

### 选择简化版本 (`reward_plain.py`) 如果：
- 你觉得当前模型生成质量不够稳定
- 你希望更智能的语义理解和判断
- 你有充足的计算资源
- 你希望奖励更贴近人��判断

## 🔧 自定义配置

### 调整简化版本权重：
```python
# 在 reward_plain.py 中修改
@dataclass
class PlainRewardConfig:
    similarity_weight: float = 0.7      # 提高相似度权重
    code_correctness_weight: float = 0.3 # 降低代码权重
```

### 调整LLM温度：
```python
llm_temperature: float = 0.1  # 更确定的判断
llm_max_tokens: int = 256     # 更简洁的评估
```

## 📈 监控和调试

两种版本都支持 wandb 监控：

- **复杂版本**: `verl_trading_indicators_small`
- **简化版本**: `verl_trading_plain_reward`

### 关键指标：
- `reward`: 平均奖励分数
- `policy_loss`: 策略网络损失  
- `value_loss`: 价值网络损失
- `kl_divergence`: KL散度

## 💡 最佳实践

1. **开始建议**: 先尝试简化版本，观察训练效果
2. **资源充足**: 简化版本提供更好的语义理解
3. **快速迭代**: 复杂版本提供更快的反馈循环
4. **混合使用**: 可以先用简化版本训练，再用复杂版本微调

选择适合你当前需求和资源的版本开始训练！