"""
Model Comparison Streamlit App
Compare outputs from two different models with GPU device control
"""

import streamlit as st
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import json
from typing import Optional, Dict, Any
import time
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="Model Comparison Tool",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .model-output {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin: 10px 0;
    }
    .model-a-output {
        border-left-color: #2196F3;
    }
    .model-b-output {
        border-left-color: #FF9800;
    }
    .stats-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .prompt-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)


class ModelLoader:
    """模型加载和管理类"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.tokenizers: Dict[str, Any] = {}
        self.device_map: Dict[str, str] = {}
    
    def load_model(
        self, 
        model_name: str,
        model_path: str, 
        device: str,
        use_4bit: bool = False,
        use_8bit: bool = False
    ) -> bool:
        """加载模型到指定设备"""
        try:
            with st.spinner(f"Loading {model_name} to {device}..."):
                # 加载tokenizer
                tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                )
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
                
                # 配置加载参数
                load_kwargs = {
                    "trust_remote_code": True,
                    "torch_dtype": torch.bfloat16,
                }
                
                # 量化配置
                if use_4bit:
                    from transformers import BitsAndBytesConfig
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                    load_kwargs["device_map"] = device
                elif use_8bit:
                    load_kwargs["load_in_8bit"] = True
                    load_kwargs["device_map"] = device
                else:
                    load_kwargs["device_map"] = device
                
                # 加载模型
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    **load_kwargs
                )
                
                self.models[model_name] = model
                self.tokenizers[model_name] = tokenizer
                self.device_map[model_name] = device
                
                return True
                
        except Exception as e:
            st.error(f"Failed to load {model_name}: {str(e)}")
            return False
    
    def generate(
        self,
        model_name: str,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        do_sample: bool = True
    ) -> Dict[str, Any]:
        """使用指定模型生成文本"""
        if model_name not in self.models:
            return {
                "success": False,
                "error": f"Model {model_name} not loaded"
            }
        
        try:
            model = self.models[model_name]
            tokenizer = self.tokenizers[model_name]
            
            # Tokenize input
            start_time = time.time()
            inputs = tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            input_length = inputs["input_ids"].shape[1]
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=do_sample,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            
            # Decode
            generated_text = tokenizer.decode(
                outputs[0][input_length:], 
                skip_special_tokens=True
            )
            generation_time = time.time() - start_time
            
            # Calculate tokens
            output_length = outputs.shape[1] - input_length
            tokens_per_second = output_length / generation_time if generation_time > 0 else 0
            
            return {
                "success": True,
                "text": generated_text,
                "input_tokens": input_length,
                "output_tokens": output_length,
                "generation_time": generation_time,
                "tokens_per_second": tokens_per_second,
                "device": self.device_map[model_name]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def unload_model(self, model_name: str):
        """卸载模型释放显存"""
        if model_name in self.models:
            del self.models[model_name]
            del self.tokenizers[model_name]
            del self.device_map[model_name]
            torch.cuda.empty_cache()
            return True
        return False
    
    def get_gpu_info(self) -> Dict[int, Dict[str, Any]]:
        """获取GPU信息"""
        gpu_info = {}
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                memory_allocated = torch.cuda.memory_allocated(i) / 1024**3
                memory_reserved = torch.cuda.memory_reserved(i) / 1024**3
                memory_total = props.total_memory / 1024**3
                
                gpu_info[i] = {
                    "name": props.name,
                    "memory_allocated_gb": memory_allocated,
                    "memory_reserved_gb": memory_reserved,
                    "memory_total_gb": memory_total,
                    "memory_free_gb": memory_total - memory_reserved
                }
        return gpu_info


# 初始化session state
if 'model_loader' not in st.session_state:
    st.session_state.model_loader = ModelLoader()

if 'comparison_history' not in st.session_state:
    st.session_state.comparison_history = []

if 'model_a_loaded' not in st.session_state:
    st.session_state.model_a_loaded = False

if 'model_b_loaded' not in st.session_state:
    st.session_state.model_b_loaded = False


def load_top_strategies(file_path: str, top_k: int = 5) -> list:
    """从 strategies 文件中加载 likes_count 最高的 top-k 条策略描述"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            strategies = json.load(f)
        
        # 按 likes_count 排序
        sorted_strategies = sorted(
            strategies, 
            key=lambda x: x.get('likes_count', 0) or x.get('preview_likes_count', 0), 
            reverse=True
        )
        
        # 提取 top-k 描述
        top_strategies = []
        for strategy in sorted_strategies[:top_k]:
            likes = strategy.get('likes_count', 0) or strategy.get('preview_likes_count', 0)
            description = strategy.get('description', '')
            name = strategy.get('name', '') or strategy.get('preview_title', '')
            author = strategy.get('user', {}).get('username', '') or strategy.get('preview_author', '')
            
            if description:
                top_strategies.append({
                    'name': name,
                    'author': author,
                    'likes': likes,
                    'description': description
                })
        
        return top_strategies
    except Exception as e:
        st.error(f"Error loading strategies: {str(e)}")
        return []


def main():
    st.title("🔬 Model Comparison Tool")
    st.markdown("Compare outputs from two different models side-by-side")
    
    # Sidebar - 模型配置
    with st.sidebar:
        st.header("⚙️ Model Configuration")
        
        # GPU信息
        st.subheader("🖥️ GPU Status")
        gpu_info = st.session_state.model_loader.get_gpu_info()
        
        if not gpu_info:
            st.warning("No CUDA GPUs available")
        else:
            for gpu_id, info in gpu_info.items():
                with st.expander(f"GPU {gpu_id}: {info['name']}", expanded=True):
                    st.metric("Total Memory", f"{info['memory_total_gb']:.1f} GB")
                    st.metric("Used Memory", f"{info['memory_reserved_gb']:.1f} GB")
                    st.metric("Free Memory", f"{info['memory_free_gb']:.1f} GB")
                    
                    # 显示使用率进度条
                    usage_percent = (info['memory_reserved_gb'] / info['memory_total_gb']) * 100
                    st.progress(usage_percent / 100)
                    st.caption(f"Usage: {usage_percent:.1f}%")
        
        st.divider()
        
        # Model A配置
        st.subheader("🅰️ Model A")
        model_a_path = st.text_input(
            "Model A Path",
            value="Qwen/Qwen2.5-Coder-7B",
            key="model_a_path",
            help="Path to model A (local path or HuggingFace model ID)"
        )
        
        model_a_device = st.selectbox(
            "Model A Device",
            options=[f"cuda:{i}" for i in range(len(gpu_info))] if gpu_info else ["cpu"],
            key="model_a_device"
        )
        
        model_a_quant = st.selectbox(
            "Model A Quantization",
            options=["None", "4-bit", "8-bit"],
            key="model_a_quant"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Load Model A", use_container_width=True):
                use_4bit = model_a_quant == "4-bit"
                use_8bit = model_a_quant == "8-bit"
                success = st.session_state.model_loader.load_model(
                    "Model A",
                    model_a_path,
                    model_a_device,
                    use_4bit=use_4bit,
                    use_8bit=use_8bit
                )
                if success:
                    st.session_state.model_a_loaded = True
                    st.success("Model A loaded!")
                    st.rerun()
        
        with col2:
            if st.button("Unload A", use_container_width=True, disabled=not st.session_state.model_a_loaded):
                st.session_state.model_loader.unload_model("Model A")
                st.session_state.model_a_loaded = False
                st.success("Model A unloaded!")
                st.rerun()
        
        if st.session_state.model_a_loaded:
            st.success("✅ Model A Ready")
        
        st.divider()
        
        # Model B配置
        st.subheader("🅱️ Model B")
        model_b_path = st.text_input(
            "Model B Path",
            value="/workspace/trading_indicators/posttrain/mid_train/pine-coder-fsdp/final",
            key="model_b_path",
            help="Path to model B (local path or HuggingFace model ID)"
        )
        
        model_b_device = st.selectbox(
            "Model B Device",
            options=[f"cuda:{i}" for i in range(len(gpu_info))] if gpu_info else ["cpu"],
            index=min(1, len(gpu_info) - 1) if len(gpu_info) > 1 else 0,
            key="model_b_device"
        )
        
        model_b_quant = st.selectbox(
            "Model B Quantization",
            options=["None", "4-bit", "8-bit"],
            key="model_b_quant"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Load Model B", use_container_width=True):
                use_4bit = model_b_quant == "4-bit"
                use_8bit = model_b_quant == "8-bit"
                success = st.session_state.model_loader.load_model(
                    "Model B",
                    model_b_path,
                    model_b_device,
                    use_4bit=use_4bit,
                    use_8bit=use_8bit
                )
                if success:
                    st.session_state.model_b_loaded = True
                    st.success("Model B loaded!")
                    st.rerun()
        
        with col2:
            if st.button("Unload B", use_container_width=True, disabled=not st.session_state.model_b_loaded):
                st.session_state.model_loader.unload_model("Model B")
                st.session_state.model_b_loaded = False
                st.success("Model B unloaded!")
                st.rerun()
        
        if st.session_state.model_b_loaded:
            st.success("✅ Model B Ready")
    
    # 主界面
    st.header("💬 Prompt Input")
    
    # 数据源选择
    prompt_source = st.radio(
        "Select prompt source:",
        options=["Predefined Examples", "Load from Strategies File", "Custom Prompt"],
        horizontal=True
    )
    
    prompt = ""
    
    if prompt_source == "Load from Strategies File":
        st.subheader("📊 Top Strategies from TradingView")
        
        # 文件路径和 top-k 设置
        col1, col2 = st.columns([3, 1])
        with col1:
            strategies_file = st.text_input(
                "Strategies JSON file path:",
                value="/workspace/trading_indicators/outputs/strategies_20251014_054134.json",
                help="Path to the strategies JSON file"
            )
        with col2:
            top_k = st.number_input("Top K", min_value=1, max_value=20, value=5, step=1)
        
        # 加载按钮
        if st.button("🔄 Load Top Strategies", use_container_width=True):
            st.session_state.top_strategies = load_top_strategies(strategies_file, top_k)
            if st.session_state.top_strategies:
                st.success(f"Loaded {len(st.session_state.top_strategies)} top strategies!")
        
        # 显示和选择策略
        if 'top_strategies' in st.session_state and st.session_state.top_strategies:
            strategy_options = [
                f"#{i+1}: {s['name'][:50]}... (👍 {s['likes']} by @{s['author']})" 
                for i, s in enumerate(st.session_state.top_strategies)
            ]
            
            selected_idx = st.selectbox(
                "Select a strategy to generate code for:",
                options=range(len(strategy_options)),
                format_func=lambda x: strategy_options[x]
            )
            
            selected_strategy = st.session_state.top_strategies[selected_idx]
            
            # 显示选中策略的详细信息
            with st.expander("📋 Strategy Details", expanded=True):
                st.markdown(f"**Name:** {selected_strategy['name']}")
                st.markdown(f"**Author:** @{selected_strategy['author']}")
                st.markdown(f"**Likes:** 👍 {selected_strategy['likes']}")
                st.markdown(f"**Description:**")
                st.info(selected_strategy['description'])
            
            # 生成 prompt
            prompt_template = st.text_area(
                "Prompt template (use {description} placeholder):",
                value="""Please analyze the following trading strategy description and provide a step-by-step reasoning process for implementing it in Pine Script, followed by the complete implementation (TradingView PineScript).

Strategy Description:
{description}

Provide:
1. A brief analysis of the strategy's core logic
2. Key technical indicators or calculations needed
3. Entry and exit conditions
4. Complete Pine Script v5/v6 implementation""",
                height=200
            )
            
            prompt = prompt_template.replace("{description}", selected_strategy['description'])
            
            st.text_area(
                "Generated prompt (you can edit):",
                value=prompt,
                height=300,
                key="generated_prompt"
            )
            prompt = st.session_state.generated_prompt
        else:
            st.info("👆 Click 'Load Top Strategies' to load strategies from file")
    
    elif prompt_source == "Predefined Examples":
        # 预设示例
        example_prompts = {
            "Pine Script - RSI Strategy": """Generate a Pine Script v5 trading strategy that uses RSI indicator with the following requirements:
- Use RSI with period 14
- Buy when RSI crosses above 30
- Sell when RSI crosses below 70
- Include proper strategy setup and plotting""",
            
            "Pine Script - Moving Average Crossover": """Create a Pine Script v5 strategy implementing a moving average crossover system:
- Use 50-period SMA and 200-period SMA
- Enter long when fast MA crosses above slow MA
- Exit when fast MA crosses below slow MA
- Add visualization with colored fills""",
            
            "Python - Data Analysis": """Write a Python function that analyzes a pandas DataFrame containing stock prices and calculates:
- Daily returns
- Cumulative returns
- Sharpe ratio
- Maximum drawdown
Include proper error handling and type hints."""
        }
        
        selected_example = st.selectbox(
            "Choose an example:",
            options=list(example_prompts.keys()),
            index=0
        )
        
        prompt = st.text_area(
            "Prompt (you can edit):",
            value=example_prompts[selected_example],
            height=200
        )
    
    else:  # Custom Prompt
        prompt = st.text_area(
            "Enter your prompt:",
            height=200,
            placeholder="Type your prompt here..."
        )
    
    # 生成参数
    with st.expander("🎛️ Generation Parameters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_new_tokens = st.slider("Max New Tokens", 128, 4096, 512, step=128)
            temperature = st.slider("Temperature", 0.0, 2.0, 0.7, step=0.1)
        
        with col2:
            top_p = st.slider("Top P", 0.0, 1.0, 0.9, step=0.05)
            top_k = st.slider("Top K", 0, 100, 50, step=5)
        
        with col3:
            do_sample = st.checkbox("Do Sample", value=True)
    
    # 生成按钮
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        generate_button = st.button(
            "🚀 Generate Comparison",
            use_container_width=True,
            disabled=not (st.session_state.model_a_loaded and st.session_state.model_b_loaded),
            type="primary"
        )
    
    if not (st.session_state.model_a_loaded and st.session_state.model_b_loaded):
        st.warning("⚠️ Please load both models before generating")
    
    # 生成和显示结果
    if generate_button and prompt.strip():
        st.divider()
        st.header("📊 Comparison Results")
        
        # 显示prompt
        with st.expander("📝 Prompt Used", expanded=False):
            st.markdown(f'<div class="prompt-box">{prompt}</div>', unsafe_allow_html=True)
        
        # 并行生成
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🅰️ Model A Output")
            with st.spinner("Generating from Model A..."):
                result_a = st.session_state.model_loader.generate(
                    "Model A",
                    prompt,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=do_sample
                )
        
        with col2:
            st.subheader("🅱️ Model B Output")
            with st.spinner("Generating from Model B..."):
                result_b = st.session_state.model_loader.generate(
                    "Model B",
                    prompt,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=do_sample
                )
        
        # 显示结果
        col1, col2 = st.columns(2)
        
        with col1:
            if result_a["success"]:
                st.markdown(f'<div class="model-output model-a-output">', unsafe_allow_html=True)
                st.code(result_a["text"], language="python" if "python" in prompt.lower() else "javascript")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 统计信息
                st.markdown(f"""
                <div class="stats-box">
                <b>Statistics:</b><br>
                • Input tokens: {result_a['input_tokens']}<br>
                • Output tokens: {result_a['output_tokens']}<br>
                • Time: {result_a['generation_time']:.2f}s<br>
                • Speed: {result_a['tokens_per_second']:.1f} tokens/s<br>
                • Device: {result_a['device']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Error: {result_a['error']}")
        
        with col2:
            if result_b["success"]:
                st.markdown(f'<div class="model-output model-b-output">', unsafe_allow_html=True)
                st.code(result_b["text"], language="python" if "python" in prompt.lower() else "javascript")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 统计信息
                st.markdown(f"""
                <div class="stats-box">
                <b>Statistics:</b><br>
                • Input tokens: {result_b['input_tokens']}<br>
                • Output tokens: {result_b['output_tokens']}<br>
                • Time: {result_b['generation_time']:.2f}s<br>
                • Speed: {result_b['tokens_per_second']:.1f} tokens/s<br>
                • Device: {result_b['device']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Error: {result_b['error']}")
        
        # 保存到历史
        if result_a["success"] and result_b["success"]:
            st.session_state.comparison_history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prompt": prompt,
                "model_a": result_a,
                "model_b": result_b,
                "parameters": {
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k
                }
            })
            
            # 导出选项
            st.divider()
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("💾 Save Comparison to JSON", use_container_width=True):
                    output_file = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "timestamp": datetime.now().isoformat(),
                            "prompt": prompt,
                            "model_a_path": model_a_path,
                            "model_b_path": model_b_path,
                            "model_a_output": result_a["text"],
                            "model_b_output": result_b["text"],
                            "statistics": {
                                "model_a": {k: v for k, v in result_a.items() if k != "text"},
                                "model_b": {k: v for k, v in result_b.items() if k != "text"}
                            },
                            "parameters": {
                                "max_new_tokens": max_new_tokens,
                                "temperature": temperature,
                                "top_p": top_p,
                                "top_k": top_k
                            }
                        }, f, indent=2, ensure_ascii=False)
                    st.success(f"Saved to {output_file}")
    
    # 历史记录
    if st.session_state.comparison_history:
        st.divider()
        st.header("📜 Comparison History")
        
        for idx, record in enumerate(reversed(st.session_state.comparison_history[-5:])):
            with st.expander(f"Comparison {len(st.session_state.comparison_history) - idx} - {record['timestamp']}", expanded=False):
                st.text(f"Prompt: {record['prompt'][:100]}...")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Model A Stats")
                    st.write(f"Tokens: {record['model_a']['output_tokens']}")
                    st.write(f"Time: {record['model_a']['generation_time']:.2f}s")
                
                with col2:
                    st.caption("Model B Stats")
                    st.write(f"Tokens: {record['model_b']['output_tokens']}")
                    st.write(f"Time: {record['model_b']['generation_time']:.2f}s")


if __name__ == "__main__":
    main()
