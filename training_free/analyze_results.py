import json
import re
from typing import Dict, List

def analyze_pine_script_quality(code: str) -> Dict:
    """分析生成的Pine Script代码质量"""
    
    # 基本结构检查
    has_version = '//@version=' in code
    has_strategy_or_indicator = 'strategy(' in code or 'indicator(' in code
    has_input = 'input.' in code
    has_ta_functions = 'ta.' in code
    has_strategy_logic = 'strategy.entry' in code or 'strategy.close' in code
    has_plot = 'plot(' in code
    
    # 计算代码行数
    lines = code.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # 检查注释
    comment_lines = [line for line in lines if line.strip().startswith('//')]
    
    # 检查基本语法结构
    has_proper_syntax = check_basic_syntax(code)
    
    # 检查常见的Pine Script函数
    pine_functions = [
        'ta.sma', 'ta.ema', 'ta.rsi', 'ta.macd', 'ta.stoch',
        'strategy.entry', 'strategy.close', 'strategy.exit',
        'plot', 'plotshape', 'label.new', 'line.new'
    ]
    
    functions_used = [func for func in pine_functions if func in code]
    
    return {
        'has_version': has_version,
        'has_strategy_or_indicator': has_strategy_or_indicator,
        'has_input': has_input,
        'has_ta_functions': has_ta_functions,
        'has_strategy_logic': has_strategy_logic,
        'has_plot': has_plot,
        'total_lines': len(lines),
        'non_empty_lines': len(non_empty_lines),
        'comment_lines': len(comment_lines),
        'has_proper_syntax': has_proper_syntax,
        'functions_used': functions_used,
        'functions_count': len(functions_used),
        'quality_score': calculate_quality_score(
            has_version, has_strategy_or_indicator, has_input, 
            has_ta_functions, has_strategy_logic, has_plot, 
            len(functions_used), has_proper_syntax
        )
    }

def check_basic_syntax(code: str) -> bool:
    """检查基本语法结构"""
    # 检查括号是否匹配
    open_parens = code.count('(')
    close_parens = code.count(')')
    
    open_brackets = code.count('[')
    close_brackets = code.count(']')
    
    # 基本的语法检查
    return (open_parens == close_parens and 
            open_brackets == close_brackets and
            not code.strip().endswith(','))

def calculate_quality_score(has_version, has_strategy_or_indicator, has_input, 
                          has_ta_functions, has_strategy_logic, has_plot, 
                          functions_count, has_proper_syntax) -> float:
    """计算代码质量分数 (0-10)"""
    score = 0
    
    if has_version: score += 1
    if has_strategy_or_indicator: score += 2
    if has_input: score += 1
    if has_ta_functions: score += 1.5
    if has_strategy_logic: score += 2
    if has_plot: score += 1
    if functions_count >= 3: score += 1
    if has_proper_syntax: score += 0.5
    
    return min(score, 10.0)

def compare_results(results_file: str):
    """比较few-shot和zero-shot的结果"""
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print("=== Detailed Analysis ===\n")
    
    few_shot_scores = []
    zero_shot_scores = []
    
    for i, result in enumerate(results):
        print(f"Test Case {i+1}: {result['test_case']['title']}")
        print(f"Description: {result['test_case']['description'][:100]}...")
        print(f"Original likes: {result['test_case']['likes_count']}")
        print()
        
        # 分析few-shot结果
        few_shot_analysis = analyze_pine_script_quality(result['few_shot']['generated_code'])
        few_shot_scores.append(few_shot_analysis['quality_score'])
        
        # 分析zero-shot结果
        zero_shot_analysis = analyze_pine_script_quality(result['zero_shot']['generated_code'])
        zero_shot_scores.append(zero_shot_analysis['quality_score'])
        
        print("Few-shot Analysis:")
        print(f"  Quality Score: {few_shot_analysis['quality_score']:.1f}/10")
        print(f"  Code Lines: {few_shot_analysis['non_empty_lines']}")
        print(f"  Functions Used: {few_shot_analysis['functions_count']} ({', '.join(few_shot_analysis['functions_used'][:3])}...)")
        print(f"  Has Version: {few_shot_analysis['has_version']}")
        print(f"  Has Strategy/Indicator: {few_shot_analysis['has_strategy_or_indicator']}")
        print(f"  Has Proper Syntax: {few_shot_analysis['has_proper_syntax']}")
        
        print("\nZero-shot Analysis:")
        print(f"  Quality Score: {zero_shot_analysis['quality_score']:.1f}/10")
        print(f"  Code Lines: {zero_shot_analysis['non_empty_lines']}")
        print(f"  Functions Used: {zero_shot_analysis['functions_count']} ({', '.join(zero_shot_analysis['functions_used'][:3])}...)")
        print(f"  Has Version: {zero_shot_analysis['has_version']}")
        print(f"  Has Strategy/Indicator: {zero_shot_analysis['has_strategy_or_indicator']}")
        print(f"  Has Proper Syntax: {zero_shot_analysis['has_proper_syntax']}")
        
        print(f"\nQuality Difference: {few_shot_analysis['quality_score'] - zero_shot_analysis['quality_score']:.1f}")
        print("="*60)
        print()
    
    # 总体统计
    print("=== Overall Statistics ===")
    print(f"Number of test cases: {len(results)}")
    print(f"Average Few-shot Quality Score: {sum(few_shot_scores)/len(few_shot_scores):.2f}")
    print(f"Average Zero-shot Quality Score: {sum(zero_shot_scores)/len(zero_shot_scores):.2f}")
    print(f"Few-shot wins: {sum(1 for f, z in zip(few_shot_scores, zero_shot_scores) if f > z)}")
    print(f"Zero-shot wins: {sum(1 for f, z in zip(few_shot_scores, zero_shot_scores) if z > f)}")
    print(f"Ties: {sum(1 for f, z in zip(few_shot_scores, zero_shot_scores) if f == z)}")
    
    improvement = sum(few_shot_scores)/len(few_shot_scores) - sum(zero_shot_scores)/len(zero_shot_scores)
    print(f"Average improvement with few-shot: {improvement:.2f} points")

def show_code_samples(results_file: str):
    """显示生成的代码样例"""
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print("=== Code Samples ===\n")
    
    for i, result in enumerate(results):
        print(f"Test Case {i+1}: {result['test_case']['title']}")
        print(f"Description: {result['test_case']['description'][:150]}...")
        print()
        
        print("Original Code (first 300 chars):")
        print(result['test_case']['original_code'][:300] + "...")
        print()
        
        print("Few-shot Generated (first 300 chars):")
        print(result['few_shot']['generated_code'][:300] + "...")
        print()
        
        print("Zero-shot Generated (first 300 chars):")
        print(result['zero_shot']['generated_code'][:300] + "...")
        print()
        print("="*80)
        print()

if __name__ == "__main__":
    results_file = "/workspace/trading_indicators/training_free/comparison_results.json"
    
    try:
        print("Analyzing results...")
        compare_results(results_file)
        print("\n" + "="*80 + "\n")
        show_code_samples(results_file)
    except FileNotFoundError:
        print(f"Results file not found: {results_file}")
        print("Please run simple_test.py first to generate results.")
    except Exception as e:
        print(f"Error analyzing results: {e}")