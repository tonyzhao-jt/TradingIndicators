# Docker CUDA Support

本项目现在支持CUDA GPU加速。我们提供了两个版本的Docker镜像：

## 版本说明

### CPU版本（原版本）
- **Dockerfile**: `dockerfile`
- **构建脚本**: `build.sh`  
- **运行脚本**: `run_mt.sh`
- **基础镜像**: `python:3.13-slim`
- **用途**: 纯CPU计算，适合没有NVIDIA GPU的环境

### CUDA版本（新增）
- **Dockerfile**: `dockerfile.cuda`
- **构建脚本**: `build_cuda.sh`
- **运行脚本**: `run_cuda.sh`  
- **基础镜像**: `nvidia/cuda:12.2-devel-ubuntu22.04`
- **用途**: GPU加速计算，支持CUDA 12.2

## 前置要求

### 使用CUDA版本需要：
1. **NVIDIA GPU** 支持CUDA 12.2或兼容版本
2. **NVIDIA驱动** 版本 >= 525.60.13
3. **NVIDIA Docker** 运行时：
   ```bash
   # 安装nvidia-docker2
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

## 使用方法

### 构建镜像

#### CPU版本:
```bash
cd docker
./build.sh
```

#### CUDA版本:
```bash
cd docker
./build_cuda.sh
```

### 运行容器

#### CPU版本:
```bash
cd docker
./run_mt.sh
```

#### CUDA版本:
```bash
cd docker  
./run_cuda.sh
```

## CUDA版本特性

### 预装的CUDA相关包：
- **PyTorch**: 支持CUDA 11.8的版本
- **CuPy**: CUDA 12.x版本，用于GPU加速的NumPy兼容库

### 环境变量：
- `NVIDIA_VISIBLE_DEVICES=all`: 使所有GPU对容器可见
- `NVIDIA_DRIVER_CAPABILITIES=compute,utility`: 启用计算和实用功能

### GPU验证：
进入CUDA容器后，可以运行以下命令验证GPU访问：
```bash
# 检查CUDA版本
nvcc --version

# 检查GPU状态
nvidia-smi

# Python中验证PyTorch CUDA支持
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"
```

## 故障排除

### 常见问题：

1. **容器无法访问GPU**
   - 确认nvidia-docker已安装并重启docker服务
   - 检查NVIDIA驱动版本是否兼容

2. **CUDA版本不匹配**
   - 检查主机CUDA驱动版本
   - 必要时修改dockerfile.cuda中的基础镜像版本

3. **内存不足**
   - CUDA镜像比CPU镜像更大，确保有足够的磁盘空间
   - GPU内存不足时考虑调整batch size或模型大小

## 性能优化建议

1. **选择合适的版本**：
   - 仅CPU计算：使用CPU版本
   - 需要GPU加速：使用CUDA版本

2. **内存管理**：
   - 监控GPU内存使用情况
   - 合理设置batch size

3. **数据传输优化**：
   - 尽量将数据保持在GPU内存中
   - 减少CPU-GPU数据传输