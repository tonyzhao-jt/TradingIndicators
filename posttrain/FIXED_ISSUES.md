# ✅ VERL 训练配置修复总结

## 🔧 修复的问题

### 1. Hydra 配置语法错误
**问题**: `reward_function.init_kwargs` JSON 格式不被 Hydra 支持
```bash
# ❌ 错误配置
reward_function.init_kwargs='{"validation_file": "/path/to/val.parquet"}'
```

**解决方案**: 使用 VERL 原生的 `custom_reward_function` 配置
```bash
# ✅ 正确配置  
custom_reward_function.path=/workspace/trading_indicators/posttrain/reward_plain.py
custom_reward_function.name=compute_score
```

### 2. Reward Function 接口适配
**问题**: PlainRewardFunction 类不符合 VERL 期望的函数接口

**解决方案**: 添加 VERL 兼容的 `compute_score` 函数
```python
def compute_score(prompts, responses, **kwargs):
    """VERL-compatible reward computation function."""
    if not hasattr(compute_score, '_reward_fn'):
        compute_score._reward_fn = PlainRewardFunction()
    
    scores = []
    for prompt, response in zip(prompts, responses):
        score = compute_score._reward_fn(prompt, response)
        scores.append(score)
    
    return scores
```

### 3. 自动验证数据加载
**问题**: 无法通过配置传递验证数据文件路径

**解决方案**: 在 PlainRewardFunction 初始化时自动检测和加载验证数据
```python
# Auto-load validation data if available
if reference_data is None:
    validation_file = "/workspace/trading_indicators/outputs/data_splits/val.parquet"
    if os.path.exists(validation_file):
        self.load_reference_data(validation_file)
```

## 🎯 最终工作配置

### 训练脚本: `pt_verl_plain.sh`
```bash
python3 -m verl.trainer.main_ppo \
    algorithm.adv_estimator=grpo \
    data.train_files=/workspace/trading_indicators/outputs/data_splits/train.parquet \
    data.val_files=/workspace/trading_indicators/outputs/data_splits/val.parquet \
    data.train_batch_size=8 \
    actor_rollout_ref.model.path=Qwen/Qwen3-Coder-30B-A3B-Instruct \
    custom_reward_function.path=/workspace/trading_indicators/posttrain/reward_plain.py \
    custom_reward_function.name=compute_score \
    trainer.total_epochs=50
```

### 数据配置
- **训练样本**: 25 条
- **验证样本**: 7 条  
- **数据格式**: 包含 `prompt`, `response`, `reward` 列
- **模型**: Qwen3-Coder-30B-A3B-Instruct

### Reward Function 特性
- **相似度评估 (60%)**: LLM 判断与参考数据的相似度
- **代码正确性 (40%)**: 语法检查 + LLM 代码质量评估
- **智能评判**: 使用 Qwen3-Coder-30B 进行语义理解
- **参考对比**: 与验证集数据进行智能比较

## 🚀 使用方法

### 快速启动
```bash
cd /workspace/trading_indicators/posttrain
./pt_verl_plain.sh
```

### 完整设置流程
```bash
cd /workspace/trading_indicators/posttrain  
./setup_plain_training.sh
```

### 验证配置
```bash
cd /workspace/trading_indicators/posttrain
./test_setup.sh
```

## 📊 训练监控

- **Wandb 项目**: `verl_trading_plain_reward`
- **实验名**: `qwen3_30b_plain_reward_v1`  
- **关键指标**: 
  - `reward`: 平均奖励分数
  - `policy_loss`: 策略网络损失
  - `value_loss`: 价值网络损失

## 🎯 配置优化点

### 内存优化
```bash
actor_rollout_ref.actor.fsdp_config.param_offload=True      # 参数offload
actor_rollout_ref.actor.fsdp_config.optimizer_offload=True  # 优化器offload  
actor_rollout_ref.rollout.gpu_memory_utilization=0.8       # 80% GPU内存
```

### 并行配置
```bash
actor_rollout_ref.rollout.tensor_model_parallel_size=4  # 4路张量并行
actor_rollout_ref.rollout.n=2                          # 2个响应候选
```

### 训练参数
```bash
data.train_batch_size=8                     # 批次大小
actor_rollout_ref.actor.ppo_mini_batch_size=4  # PPO小批次
trainer.total_epochs=50                     # 训练轮数
trainer.save_freq=2                        # 每2轮保存
trainer.test_freq=1                        # 每轮测试
```

## ✅ 验证结果

所有测试通过：
- ✅ 数据文件存在且格式正确 (25 train + 7 val)
- ✅ Reward function 正常工作 
- ✅ VERL 配置语法正确
- ✅ LLM 连接正常 (Qwen3-Coder-30B)

**现在可以开始 VERL 训练了！** 🎉