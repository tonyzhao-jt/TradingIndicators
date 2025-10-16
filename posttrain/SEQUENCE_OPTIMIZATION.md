# 长序列优化配置说明

## 🎯 序列长度分析结果

根据数据分析：
- **Prompt 长度**: 203-282 tokens (平均 240 tokens)
- **Response 长度**: 781-2644 tokens (平均 1452 tokens) 
- **总长度**: 最大约 2926 tokens

## ⚙️ 优化配置调整

### 序列长度设置
```bash
data.max_prompt_length=600      # 增加到 600 (原 512)
data.max_response_length=3200   # 增加到 3200 (原 1024)
data.filter_overlong_prompts=False  # 关闭过滤
data.truncation='truncate'      # 使用截断而非报错
```

### 批次大小优化（应对长序列）
```bash
data.train_batch_size=4                              # 从 8 减少到 4
actor_rollout_ref.actor.ppo_mini_batch_size=2       # 从 4 减少到 2  
actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1  # 从 2 减少到 1
```

### 内存优化
```bash
actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1  # 减少微批次
actor_rollout_ref.rollout.gpu_memory_utilization=0.7          # 降低 GPU 利用率
actor_rollout_ref.rollout.n=1                                 # 减少候选数量
actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=1     # 减少参考模型批次
```

## 📊 内存影响估算

长序列对内存的影响：
- **原配置** (512 + 1024 = 1536 tokens): ~基准内存
- **新配置** (600 + 3200 = 3800 tokens): ~2.5x 内存需求

批次调整补偿：
- **train_batch_size**: 8→4 (50% 减少)
- **micro_batch_size**: 2→1 (50% 减少)
- **总体内存**: ~1.25x (可接受范围)

## 🔧 如果仍有内存问题，可进一步调整：

### 更激进的内存优化
```bash
# 1. 进一步减少批次
data.train_batch_size=2
actor_rollout_ref.actor.ppo_mini_batch_size=1

# 2. 增加 offload
actor_rollout_ref.actor.fsdp_config.gradient_offload=True
actor_rollout_ref.actor.fsdp_config.state_dict_offload=True

# 3. 减少并行
actor_rollout_ref.rollout.tensor_model_parallel_size=2

# 4. 降低 GPU 利用率
actor_rollout_ref.rollout.gpu_memory_utilization=0.6
```

### 序列长度限制
```bash
# 如果内存仍不足，可以限制响应长度
data.max_response_length=2500  # 从 3200 减少
```

## ✅ 当前配置适合场景

- ✅ **完整的交易策略内容**: 不会被过度截断
- ✅ **内存使用合理**: 批次调整补偿了长序列开销  
- ✅ **训练效果保证**: 保持了足够的批次大小进行有效学习
- ✅ **30B 模型兼容**: 针对大模型优化的参数设置