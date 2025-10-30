#!/usr/bin/env python3
"""
测试 DataFrame 序列化问题
"""
import pandas as pd
import streamlit as st

def test_dataframe_serialization():
    """测试 DataFrame 的序列化"""
    
    # 模拟相似度数据
    similarity_data = {
        'length1': 100,
        'length2': 120,
        'keywords1': {'if', 'strategy', 'plot'},
        'keywords2': {'if', 'strategy', 'entry'},
        'identifiers1': {'close', 'open', 'high'},
        'identifiers2': {'close', 'volume', 'low'},
        'length_similarity': 0.83
    }
    
    # 创建统计数据表格 - 原始方式（可能出错的）
    print("测试原始方式...")
    try:
        stats_df_original = pd.DataFrame({
            'Metric': ['Code Length', 'Keywords Count', 'Identifiers Count'],
            'Code 1': [
                str(similarity_data['length1']),
                str(len(similarity_data['keywords1'])),
                str(len(similarity_data['identifiers1']))
            ],
            'Code 2': [
                str(similarity_data['length2']),
                str(len(similarity_data['keywords2'])),
                str(len(similarity_data['identifiers2']))
            ],
            'Overlap': [
                f"{similarity_data['length_similarity']:.1%}",
                f"{len(similarity_data['keywords1'].intersection(similarity_data['keywords2']))} common",
                f"{len(similarity_data['identifiers1'].intersection(similarity_data['identifiers2']))} common"
            ]
        })
        print("原始方式成功")
        print(stats_df_original)
        print("数据类型:", stats_df_original.dtypes)
    except Exception as e:
        print("原始方式失败:", e)
    
    # 创建统计数据表格 - 修复方式
    print("\n测试修复方式...")
    try:
        stats_df_fixed = pd.DataFrame({
            'Metric': ['Code Length', 'Keywords Count', 'Identifiers Count'],
            'Code 1': [
                str(similarity_data['length1']),
                str(len(similarity_data['keywords1'])),
                str(len(similarity_data['identifiers1']))
            ],
            'Code 2': [
                str(similarity_data['length2']),
                str(len(similarity_data['keywords2'])),
                str(len(similarity_data['identifiers2']))
            ],
            'Overlap': [
                f"{similarity_data['length_similarity']:.1%}",
                f"{len(similarity_data['keywords1'].intersection(similarity_data['keywords2']))} keywords",
                f"{len(similarity_data['identifiers1'].intersection(similarity_data['identifiers2']))} identifiers"
            ]
        })
        
        # 确保所有列都是字符串类型
        stats_df_fixed = stats_df_fixed.astype(str)
        print("修复方式成功")
        print(stats_df_fixed)
        print("数据类型:", stats_df_fixed.dtypes)
        
        # 测试 Arrow 序列化
        try:
            arrow_table = stats_df_fixed.to_arrow()
            print("Arrow 序列化成功!")
        except Exception as e:
            print("Arrow 序列化失败:", e)
            
    except Exception as e:
        print("修复方式失败:", e)

if __name__ == "__main__":
    test_dataframe_serialization()