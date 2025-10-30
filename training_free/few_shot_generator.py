import json
import os
import sys
from typing import List, Dict, Any
from langchain.llms.base import LLM
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain.schema import Generation, LLMResult
from langchain.callbacks.manager import CallbackManagerForLLMRun
import requests
from typing import Optional

class LocalQwenLLM(LLM):
    """Local Qwen model wrapper for LangChain"""
    
    def __init__(self, endpoint: str, model_name: str, api_key: str = "none"):
        super().__init__()
        self.endpoint = endpoint
        self.model_name = model_name
        self.api_key = api_key
    
    @property
    def _llm_type(self) -> str:
        return "local_qwen"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the local Qwen model"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "stop": stop
        }
        
        try:
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error calling local Qwen model: {e}")
            return f"Error: {str(e)}"

class FewShotTradingCodeGenerator:
    """Few-shot learning code generator for trading strategies"""
    
    def __init__(self, llm: LLM):
        self.llm = llm
        self.examples = []
        
    def load_data(self, json_file_path: str):
        """Load trading strategy data from JSON file"""
        with open(json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        print(f"Loaded {len(self.data)} trading strategies")
        
    def prepare_examples(self, num_examples: int = 5):
        """Prepare few-shot examples from the data"""
        # 选择一些质量较好的例子（有完整的description和source_code）
        good_examples = []
        for item in self.data:
            if (item.get('description') and 
                item.get('source_code') and 
                len(item['description']) > 50 and 
                len(item['source_code']) > 200):
                good_examples.append(item)
        
        # 按照likes_count排序，选择高质量的例子
        good_examples.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
        
        self.examples = []
        for i, example in enumerate(good_examples[:num_examples]):
            self.examples.append({
                "description": example['description'],
                "code": example['source_code']
            })
            
        print(f"Prepared {len(self.examples)} few-shot examples")
        return self.examples
    
    def create_few_shot_prompt(self):
        """Create few-shot prompt template"""
        
        # 单个例子的模板
        example_template = """
Description: {description}

Generated TradingView Pine Script Code:
{code}
"""
        
        example_prompt = PromptTemplate(
            input_variables=["description", "code"],
            template=example_template
        )
        
        # Few-shot 提示模板
        few_shot_prompt = FewShotPromptTemplate(
            examples=self.examples,
            example_prompt=example_prompt,
            prefix="""You are an expert in generating TradingView Pine Script code for trading strategies. 
Based on the description provided, generate complete and functional Pine Script code.

Here are some examples of descriptions and their corresponding Pine Script code:""",
            suffix="""
Now, based on the following description, generate the corresponding TradingView Pine Script code:

Description: {description}

Generated TradingView Pine Script Code:""",
            input_variables=["description"]
        )
        
        return few_shot_prompt
    
    def create_zero_shot_prompt(self):
        """Create zero-shot prompt template"""
        zero_shot_template = """You are an expert in generating TradingView Pine Script code for trading strategies.
Based on the description provided, generate complete and functional Pine Script code.

Description: {description}

Please generate a complete TradingView Pine Script code that implements the described strategy. 
The code should be functional and follow Pine Script v5 syntax.

Generated TradingView Pine Script Code:"""
        
        return PromptTemplate(
            input_variables=["description"],
            template=zero_shot_template
        )
    
    def generate_code(self, description: str, use_few_shot: bool = True):
        """Generate code using few-shot or zero-shot approach"""
        if use_few_shot:
            prompt_template = self.create_few_shot_prompt()
        else:
            prompt_template = self.create_zero_shot_prompt()
            
        prompt = prompt_template.format(description=description)
        generated_code = self.llm(prompt)
        
        return generated_code
    
    def evaluate_generation(self, test_descriptions: List[str], num_few_shot_examples: int = 5):
        """Evaluate few-shot vs zero-shot generation"""
        
        # 准备few-shot例子
        self.prepare_examples(num_few_shot_examples)
        
        results = {
            "few_shot": [],
            "zero_shot": [],
            "test_descriptions": test_descriptions
        }
        
        print(f"Starting evaluation with {len(test_descriptions)} test cases...")
        
        for i, description in enumerate(test_descriptions):
            print(f"\nProcessing test case {i+1}/{len(test_descriptions)}")
            print(f"Description: {description[:100]}...")
            
            # Few-shot generation
            print("Generating with few-shot...")
            few_shot_code = self.generate_code(description, use_few_shot=True)
            results["few_shot"].append({
                "description": description,
                "generated_code": few_shot_code
            })
            
            # Zero-shot generation
            print("Generating with zero-shot...")
            zero_shot_code = self.generate_code(description, use_few_shot=False)
            results["zero_shot"].append({
                "description": description,
                "generated_code": zero_shot_code
            })
            
        return results
    
    def save_results(self, results: Dict, output_file: str):
        """Save evaluation results to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")

def main():
    # 配置
    LOCAL_QWEN_ENDPOINT = "http://202.45.128.234:5788/v1"
    LOCAL_QWEN_MODEL_NAME = "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct"
    LOCAL_QWEN_API_KEY = "none"
    
    # 数据文件路径
    data_file = "/workspace/trading_indicators/outputs/strategies_20251014_054134.json"
    
    # 初始化LLM
    llm = LocalQwenLLM(
        endpoint=LOCAL_QWEN_ENDPOINT,
        model_name=LOCAL_QWEN_MODEL_NAME,
        api_key=LOCAL_QWEN_API_KEY
    )
    
    # 初始化生成器
    generator = FewShotTradingCodeGenerator(llm)
    
    # 加载数据
    generator.load_data(data_file)
    
    # 选择一些测试用的描述（不包含在few-shot例子中的）
    test_descriptions = []
    
    # 跳过前面用作few-shot例子的数据，选择后面的作为测试
    for item in generator.data[10:20]:  # 选择10个测试用例
        if item.get('description') and len(item['description']) > 30:
            test_descriptions.append(item['description'])
    
    print(f"Selected {len(test_descriptions)} test descriptions")
    
    # 进行评估
    results = generator.evaluate_generation(test_descriptions[:5], num_few_shot_examples=3)  # 先用3个例子测试
    
    # 保存结果
    output_file = "/workspace/trading_indicators/training_free/few_shot_evaluation_results.json"
    generator.save_results(results, output_file)
    
    # 打印简单统计
    print("\n=== Evaluation Summary ===")
    print(f"Number of test cases: {len(test_descriptions[:5])}")
    print(f"Few-shot examples used: 3")
    print(f"Results saved to: {output_file}")
    
    # 展示一个例子的结果
    if results["few_shot"]:
        print("\n=== Sample Results ===")
        sample_idx = 0
        print(f"Description: {results['test_descriptions'][sample_idx][:150]}...")
        print(f"\nFew-shot generated code length: {len(results['few_shot'][sample_idx]['generated_code'])}")
        print(f"Zero-shot generated code length: {len(results['zero_shot'][sample_idx]['generated_code'])}")

if __name__ == "__main__":
    main()