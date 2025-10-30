import json
import os
import requests
from typing import List, Dict

class SimpleCodeGenerator:
    """简化的代码生成器，用于快速测试few-shot效果"""
    
    def __init__(self, endpoint: str, model_name: str, api_key: str = "none"):
        self.endpoint = endpoint
        self.model_name = model_name
        self.api_key = api_key
        
    def call_llm(self, prompt: str) -> str:
        """调用本地Qwen模型"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_few_shot_prompt(self, examples: List[Dict], target_description: str) -> str:
        """创建few-shot提示"""
        prompt = """You are an expert TradingView Pine Script developer. Based on strategy descriptions, generate complete Pine Script code.

Here are some examples:

"""
        
        # 添加例子
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Description: {example['description'][:200]}...\n\n"
            prompt += f"Pine Script Code:\n{example['source_code'][:500]}...\n\n"
            prompt += "---\n\n"
        
        prompt += f"""Now generate Pine Script code for this strategy:

Description: {target_description}

Pine Script Code:"""
        
        return prompt
    
    def create_zero_shot_prompt(self, target_description: str) -> str:
        """创建zero-shot提示"""
        prompt = f"""You are an expert TradingView Pine Script developer. Generate complete and functional Pine Script code for the following trading strategy:

Description: {target_description}

Please generate complete Pine Script v5 code that implements this strategy. Include all necessary components like strategy declaration, inputs, calculations, entry/exit logic, and plotting.

Pine Script Code:"""
        
        return prompt
    
    def load_strategies(self, json_file: str) -> List[Dict]:
        """加载策略数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 过滤出质量较好的策略
        good_strategies = []
        for item in data:
            if (item.get('description') and item.get('source_code') and 
                len(item['description']) > 50 and 
                len(item['source_code']) > 200 and
                item.get('likes_count', 0) > 5):
                good_strategies.append(item)
        
        # 按点赞数排序
        good_strategies.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
        return good_strategies
    
    def run_comparison(self, strategies: List[Dict], num_examples: int = 3, num_tests: int = 2):
        """运行few-shot vs zero-shot比较"""
        
        # 选择few-shot例子（前num_examples个）
        few_shot_examples = strategies[:num_examples]
        
        # 选择测试用例（跳过few-shot例子后的几个）
        test_cases = strategies[num_examples:num_examples+num_tests]
        
        results = []
        
        print(f"Using {num_examples} few-shot examples")
        print(f"Testing on {num_tests} cases")
        print("="*50)
        
        for i, test_case in enumerate(test_cases):
            print(f"\nTest Case {i+1}:")
            print(f"Original Title: {test_case['name']}")
            print(f"Description: {test_case['description'][:150]}...")
            print(f"Original Code Length: {len(test_case['source_code'])} chars")
            print(f"Likes: {test_case.get('likes_count', 0)}")
            
            # Few-shot生成
            few_shot_prompt = self.create_few_shot_prompt(few_shot_examples, test_case['description'])
            print("\nGenerating with few-shot...")
            few_shot_result = self.call_llm(few_shot_prompt)
            
            # Zero-shot生成
            zero_shot_prompt = self.create_zero_shot_prompt(test_case['description'])
            print("Generating with zero-shot...")
            zero_shot_result = self.call_llm(zero_shot_prompt)
            
            # 保存结果
            result = {
                "test_case": {
                    "title": test_case['name'],
                    "description": test_case['description'],
                    "original_code": test_case['source_code'],
                    "likes_count": test_case.get('likes_count', 0)
                },
                "few_shot": {
                    "generated_code": few_shot_result,
                    "code_length": len(few_shot_result)
                },
                "zero_shot": {
                    "generated_code": zero_shot_result,
                    "code_length": len(zero_shot_result)
                }
            }
            
            results.append(result)
            
            print(f"Few-shot result length: {len(few_shot_result)} chars")
            print(f"Zero-shot result length: {len(zero_shot_result)} chars")
            
            # 显示生成代码的开头部分
            print(f"\nFew-shot code preview:\n{few_shot_result[:200]}...")
            print(f"\nZero-shot code preview:\n{zero_shot_result[:200]}...")
            print("-"*50)
        
        return results

def main():
    # 配置
    LOCAL_QWEN_ENDPOINT = "http://202.45.128.234:5788/v1"
    LOCAL_QWEN_MODEL_NAME = "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct"
    LOCAL_QWEN_API_KEY = "none"
    
    # 数据文件
    data_file = "/workspace/trading_indicators/outputs/strategies_20251014_054134.json"
    
    # 初始化生成器
    generator = SimpleCodeGenerator(LOCAL_QWEN_ENDPOINT, LOCAL_QWEN_MODEL_NAME, LOCAL_QWEN_API_KEY)
    
    # 加载策略数据
    print("Loading trading strategies...")
    strategies = generator.load_strategies(data_file)
    print(f"Loaded {len(strategies)} good quality strategies")
    
    # 显示将要使用的few-shot例子
    print("\nFew-shot examples to be used:")
    for i, strategy in enumerate(strategies[:3]):
        print(f"{i+1}. {strategy['name']} (Likes: {strategy.get('likes_count', 0)})")
        print(f"   Description: {strategy['description'][:100]}...")
        print()
    
    # 运行比较
    results = generator.run_comparison(strategies, num_examples=3, num_tests=2)
    
    # 保存结果
    output_file = "/workspace/trading_indicators/training_free/comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")
    
    # 简单分析
    print("\n=== Analysis ===")
    for i, result in enumerate(results):
        print(f"\nTest Case {i+1}: {result['test_case']['title']}")
        print(f"Original code: {len(result['test_case']['original_code'])} chars")
        print(f"Few-shot generated: {result['few_shot']['code_length']} chars")
        print(f"Zero-shot generated: {result['zero_shot']['code_length']} chars")
        
        # 简单的质量指标：检查是否包含关键的Pine Script元素
        few_shot_code = result['few_shot']['generated_code']
        zero_shot_code = result['zero_shot']['generated_code']
        
        pine_keywords = ['//@version=5', 'strategy(', 'indicator(', 'ta.', 'strategy.entry', 'strategy.close']
        
        few_shot_keywords = sum(1 for kw in pine_keywords if kw in few_shot_code)
        zero_shot_keywords = sum(1 for kw in pine_keywords if kw in zero_shot_code)
        
        print(f"Few-shot Pine Script keywords found: {few_shot_keywords}/{len(pine_keywords)}")
        print(f"Zero-shot Pine Script keywords found: {zero_shot_keywords}/{len(pine_keywords)}")

if __name__ == "__main__":
    main()