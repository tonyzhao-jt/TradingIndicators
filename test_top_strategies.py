#!/usr/bin/env python3
"""Test script to verify top strategies extraction"""
import json
import sys

def load_top_strategies(file_path: str, top_k: int = 5) -> list:
    """从 strategies 文件中加载 likes_count 最高的 top-k 条策略描述"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            strategies = json.load(f)
        
        print(f"Loaded {len(strategies)} strategies from file")
        
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
        print(f"Error loading strategies: {str(e)}")
        return []


if __name__ == "__main__":
    file_path = "/workspace/trading_indicators/outputs/strategies_20251014_054134.json"
    top_k = 5
    
    if len(sys.argv) > 1:
        top_k = int(sys.argv[1])
    
    print(f"Loading top {top_k} strategies from {file_path}")
    print("=" * 80)
    
    top_strategies = load_top_strategies(file_path, top_k)
    
    if top_strategies:
        print(f"\n✅ Successfully loaded {len(top_strategies)} top strategies:\n")
        
        for i, strategy in enumerate(top_strategies, 1):
            print(f"\n{'='*80}")
            print(f"#{i} - {strategy['name']}")
            print(f"{'='*80}")
            print(f"Author: @{strategy['author']}")
            print(f"Likes: 👍 {strategy['likes']}")
            print(f"\nDescription:")
            print(f"{strategy['description'][:300]}...")
            print()
        
        print(f"\n{'='*80}")
        print(f"Total: {len(top_strategies)} strategies")
        
        # 生成示例 prompt
        print(f"\n{'='*80}")
        print("Example prompt for first strategy:")
        print(f"{'='*80}")
        prompt = f"""Please analyze the following trading strategy description and provide a step-by-step reasoning process for implementing it in Pine Script, followed by the complete implementation (TradingView PineScript).

Strategy Description:
{top_strategies[0]['description']}

Provide:
1. A brief analysis of the strategy's core logic
2. Key technical indicators or calculations needed
3. Entry and exit conditions
4. Complete Pine Script v5/v6 implementation"""
        print(prompt)
    else:
        print("❌ No strategies loaded")
