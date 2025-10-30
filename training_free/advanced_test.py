import json
import requests
from typing import List, Dict

class AdvancedFewShotTest:
    """高级Few-shot测试，专注于更具挑战性的案例"""
    
    def __init__(self, endpoint: str, model_name: str, api_key: str = "none"):
        self.endpoint = endpoint
        self.model_name = model_name
        self.api_key = api_key
        
    def call_llm(self, prompt: str) -> str:
        """调用LLM"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2500
        }
        
        try:
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json=data,
                timeout=180
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_challenging_few_shot_prompt(self, examples: List[Dict], target_description: str) -> str:
        """创建具有挑战性的few-shot提示"""
        
        prompt = """You are an expert Pine Script developer specializing in advanced trading strategies. Your task is to generate high-quality, functional Pine Script code based on strategy descriptions.

Key requirements:
- Use Pine Script v5 syntax
- Include proper input parameters 
- Implement robust entry/exit logic
- Add appropriate risk management
- Include visualization elements
- Follow Pine Script best practices

Here are examples of high-quality strategy implementations:

"""
        
        # 添加精选的例子，突出特定的编程模式
        for i, example in enumerate(examples, 1):
            prompt += f"=== EXAMPLE {i} ===\n"
            prompt += f"Strategy: {example.get('name', 'Unknown')}\n"
            prompt += f"Description: {example['description'][:300]}...\n\n"
            
            # 提取关键的代码片段而不是完整代码
            code = example['source_code']
            
            # 提取版本声明
            version_lines = [line for line in code.split('\n') if line.startswith('//@version=')]
            if version_lines:
                prompt += f"Version: {version_lines[0]}\n"
            
            # 提取策略声明
            if "strategy(" in code:
                try:
                    strategy_start = code.find("strategy(")
                    strategy_end = code.find(")", strategy_start) + 1
                    strategy_line = code[strategy_start:strategy_end]
                    if len(strategy_line) > 100:  # 如果太长，截断
                        strategy_line = strategy_line[:100] + "..."
                    prompt += f"Strategy Declaration: {strategy_line}\n"
                except:
                    pass
            
            # 提取输入参数示例
            input_lines = [line.strip() for line in code.split('\n') if 'input.' in line][:3]
            if input_lines:
                prompt += f"Input Examples:\n"
                for line in input_lines:
                    prompt += f"  {line}\n"
            
            # 提取策略逻辑示例
            entry_lines = [line.strip() for line in code.split('\n') if 'strategy.entry' in line][:2]
            if entry_lines:
                prompt += f"Entry Logic Examples:\n"
                for line in entry_lines:
                    prompt += f"  {line}\n"
            
            prompt += "\n" + "="*50 + "\n\n"
        
        prompt += f"""Now, based on the patterns shown above, generate a complete Pine Script strategy for:

Description: {target_description}

Requirements:
1. Start with //@version=5
2. Include strategy() declaration with appropriate parameters
3. Add input parameters for key strategy settings
4. Implement the core strategy logic based on the description
5. Add proper entry and exit conditions
6. Include risk management (stop loss, take profit)
7. Add visualization elements (plots, shapes, etc.)
8. Follow the coding patterns shown in the examples above

Generate the complete Pine Script code:"""
        
        return prompt
    
    def create_minimal_prompt(self, target_description: str) -> str:
        """创建最小化的zero-shot提示"""
        return f"""Generate a Pine Script trading strategy based on this description:

{target_description}

Please provide complete Pine Script v5 code."""
    
    def select_challenging_cases(self, strategies: List[Dict]) -> List[Dict]:
        """选择具有挑战性的测试用例"""
        
        challenging_cases = []
        
        # 按不同类型选择挑战性案例
        categories = {
            "complex_indicators": [],
            "multi_timeframe": [],
            "risk_management": [],
            "machine_learning": [],
            "unusual_patterns": []
        }
        
        for strategy in strategies:
            desc = strategy.get('description', '').lower()
            name = strategy.get('name', '').lower()
            
            # 复杂指标组合
            if any(term in desc for term in ['divergence', 'multiple indicators', 'combine', 'blend']):
                categories["complex_indicators"].append(strategy)
            
            # 多时间框架
            if any(term in desc for term in ['timeframe', 'multi-frame', 'htf', 'higher timeframe']):
                categories["multi_timeframe"].append(strategy)
            
            # 风险管理
            if any(term in desc for term in ['risk management', 'position sizing', 'money management']):
                categories["risk_management"].append(strategy)
            
            # 机器学习/高级算法
            if any(term in desc for term in ['machine learning', 'neural', 'ai', 'algorithm']):
                categories["machine_learning"].append(strategy)
            
            # 非常规模式
            if any(term in desc for term in ['moon phase', 'unusual', 'experimental', 'novel']):
                categories["unusual_patterns"].append(strategy)
        
        # 从每个类别选择最高质量的案例
        for category, cases in categories.items():
            if cases:
                # 按点赞数排序，选择最佳案例
                cases.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
                challenging_cases.extend(cases[:2])  # 每类选择2个
        
        return challenging_cases[:6]  # 总共选择6个挑战性案例
    
    def run_advanced_test(self, strategies: List[Dict]):
        """运行高级测试"""
        
        # 选择高质量的few-shot例子
        few_shot_examples = sorted(strategies, key=lambda x: x.get('likes_count', 0), reverse=True)[:5]
        
        # 选择挑战性测试案例
        test_cases = self.select_challenging_cases(strategies)
        
        print(f"Selected {len(test_cases)} challenging test cases:")
        for i, case in enumerate(test_cases):
            print(f"{i+1}. {case['name']} (Likes: {case.get('likes_count', 0)})")
            print(f"   {case['description'][:100]}...")
            print()
        
        results = []
        
        for i, test_case in enumerate(test_cases[:3]):  # 测试前3个案例
            print(f"\n{'='*60}")
            print(f"Test Case {i+1}: {test_case['name']}")
            print(f"Description: {test_case['description'][:150]}...")
            print(f"Original code length: {len(test_case['source_code'])} chars")
            
            # Advanced Few-shot
            advanced_prompt = self.create_challenging_few_shot_prompt(few_shot_examples, test_case['description'])
            print("\nGenerating with advanced few-shot...")
            advanced_result = self.call_llm(advanced_prompt)
            
            # Minimal Zero-shot
            minimal_prompt = self.create_minimal_prompt(test_case['description'])
            print("Generating with minimal zero-shot...")
            minimal_result = self.call_llm(minimal_prompt)
            
            result = {
                "test_case": {
                    "title": test_case['name'],
                    "description": test_case['description'],
                    "original_code": test_case['source_code'],
                    "likes_count": test_case.get('likes_count', 0),
                    "category": self.categorize_strategy(test_case)
                },
                "advanced_few_shot": {
                    "generated_code": advanced_result,
                    "code_length": len(advanced_result),
                    "quality_metrics": self.analyze_code_quality(advanced_result)
                },
                "minimal_zero_shot": {
                    "generated_code": minimal_result,
                    "code_length": len(minimal_result),
                    "quality_metrics": self.analyze_code_quality(minimal_result)
                }
            }
            
            results.append(result)
            
            print(f"Advanced few-shot length: {len(advanced_result)}")
            print(f"Minimal zero-shot length: {len(minimal_result)}")
            
            # 显示质量比较
            adv_quality = result["advanced_few_shot"]["quality_metrics"]
            min_quality = result["minimal_zero_shot"]["quality_metrics"]
            
            print(f"Quality comparison:")
            print(f"  Advanced few-shot: {adv_quality['overall_score']:.1f}/10")
            print(f"  Minimal zero-shot: {min_quality['overall_score']:.1f}/10")
            print(f"  Improvement: {adv_quality['overall_score'] - min_quality['overall_score']:.1f}")
        
        return results
    
    def categorize_strategy(self, strategy: Dict) -> str:
        """对策略进行分类"""
        desc = strategy.get('description', '').lower()
        name = strategy.get('name', '').lower()
        
        if any(term in desc for term in ['divergence', 'multiple indicators']):
            return "complex_indicators"
        elif any(term in desc for term in ['timeframe', 'multi-frame']):
            return "multi_timeframe"
        elif any(term in desc for term in ['risk', 'money management']):
            return "risk_management"
        elif any(term in desc for term in ['machine learning', 'ai']):
            return "machine_learning"
        elif any(term in desc for term in ['moon', 'unusual', 'experimental']):
            return "unusual_patterns"
        else:
            return "standard"
    
    def analyze_code_quality(self, code: str) -> Dict:
        """分析代码质量"""
        
        # 基本结构检查
        has_version = '//@version=' in code
        has_strategy = 'strategy(' in code
        has_inputs = 'input.' in code
        has_indicators = any(func in code for func in ['ta.', 'math.', 'array.'])
        has_entry_logic = 'strategy.entry' in code
        has_exit_logic = 'strategy.exit' in code or 'strategy.close' in code
        has_plotting = 'plot(' in code or 'plotshape(' in code
        
        # 代码复杂度
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        non_comment_lines = [line for line in lines if not line.startswith('//')]
        
        # 函数使用分析
        pine_functions = [
            'ta.sma', 'ta.ema', 'ta.rsi', 'ta.macd', 'ta.stoch', 'ta.atr',
            'strategy.entry', 'strategy.exit', 'strategy.close',
            'plot', 'plotshape', 'plotchar', 'label.new', 'line.new'
        ]
        
        functions_used = [func for func in pine_functions if func in code]
        
        # 计算总分
        score = 0
        if has_version: score += 1
        if has_strategy: score += 2
        if has_inputs: score += 1
        if has_indicators: score += 1.5
        if has_entry_logic: score += 2
        if has_exit_logic: score += 1.5
        if has_plotting: score += 1
        if len(functions_used) >= 5: score += 1
        
        return {
            "overall_score": min(score, 10.0),
            "has_version": has_version,
            "has_strategy": has_strategy,
            "has_inputs": has_inputs,
            "has_indicators": has_indicators,
            "has_entry_logic": has_entry_logic,
            "has_exit_logic": has_exit_logic,
            "has_plotting": has_plotting,
            "total_lines": len(lines),
            "code_lines": len(non_comment_lines),
            "functions_used": len(functions_used),
            "function_list": functions_used[:5]  # 显示前5个函数
        }

def main():
    # 配置
    LOCAL_QWEN_ENDPOINT = "http://202.45.128.234:5788/v1"
    LOCAL_QWEN_MODEL_NAME = "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct"
    LOCAL_QWEN_API_KEY = "none"
    
    # 数据文件
    data_file = "/workspace/trading_indicators/outputs/strategies_20251014_054134.json"
    
    # 初始化测试器
    tester = AdvancedFewShotTest(LOCAL_QWEN_ENDPOINT, LOCAL_QWEN_MODEL_NAME, LOCAL_QWEN_API_KEY)
    
    # 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        all_strategies = json.load(f)
    
    # 过滤高质量策略
    good_strategies = [
        s for s in all_strategies 
        if (s.get('description') and s.get('source_code') and 
            len(s['description']) > 100 and 
            len(s['source_code']) > 300 and
            s.get('likes_count', 0) > 50)
    ]
    
    print(f"Loaded {len(good_strategies)} high-quality strategies")
    
    # 运行高级测试
    results = tester.run_advanced_test(good_strategies)
    
    # 保存结果
    output_file = "/workspace/trading_indicators/training_free/advanced_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nAdvanced test results saved to: {output_file}")
    
    # 总结报告
    print("\n" + "="*60)
    print("ADVANCED TEST SUMMARY")
    print("="*60)
    
    total_cases = len(results)
    adv_wins = 0
    min_wins = 0
    ties = 0
    
    total_adv_score = 0
    total_min_score = 0
    
    for result in results:
        adv_score = result["advanced_few_shot"]["quality_metrics"]["overall_score"]
        min_score = result["minimal_zero_shot"]["quality_metrics"]["overall_score"]
        
        total_adv_score += adv_score
        total_min_score += min_score
        
        if adv_score > min_score:
            adv_wins += 1
        elif min_score > adv_score:
            min_wins += 1
        else:
            ties += 1
    
    avg_adv_score = total_adv_score / total_cases
    avg_min_score = total_min_score / total_cases
    
    print(f"Test cases: {total_cases}")
    print(f"Advanced few-shot wins: {adv_wins}")
    print(f"Minimal zero-shot wins: {min_wins}")
    print(f"Ties: {ties}")
    print(f"Average advanced few-shot score: {avg_adv_score:.2f}")
    print(f"Average minimal zero-shot score: {avg_min_score:.2f}")
    print(f"Improvement with advanced few-shot: {avg_adv_score - avg_min_score:.2f}")

if __name__ == "__main__":
    main()