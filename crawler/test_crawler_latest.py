#!/usr/bin/env python3
"""
最新的TradingView爬虫测试 - 多页数据提取
测试完整的爬取流程，包括列表页面预览信息和详情页面完整信息
"""
import sys
import os
import json
from datetime import datetime

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from impl.trading_view_script_crawler import TradingViewScriptCrawler

def test_multi_page_crawling():
    """测试多页面爬取功能"""
    
    print("=" * 80)
    print("TradingView爬虫 - 多页数据提取测试")
    print("=" * 80)
    
    # 初始化爬虫
    crawler = TradingViewScriptCrawler()
    
    # 配置参数
    base_url = "https://www.tradingview.com/scripts/"
    start_page = 1
    end_page = 2  # 测试前2页
    max_scripts_per_page = 5  # 每页最多5个脚本
    
    print(f"📋 测试配置:")
    print(f"   基础URL: {base_url}")
    print(f"   页面范围: {start_page}-{end_page}")
    print(f"   每页最大脚本数: {max_scripts_per_page}")
    
    # 1. 测试列表页面预览信息提取
    print(f"\n🔍 第一步: 测试列表页面预览信息提取")
    print("-" * 60)
    
    all_preview_data = []
    
    try:
        for page_num in range(start_page, end_page + 1):
            print(f"\n📄 爬取第 {page_num} 页...")
            
            # 构造页面URL
            page_url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
            print(f"   URL: {page_url}")
            
            # 提取链接和预览信息
            preview_links = crawler.extract_links(page_url)
            
            if preview_links:
                # 限制每页的脚本数量
                limited_links = preview_links[:max_scripts_per_page]
                
                # 添加页面标记
                for link_info in limited_links:
                    link_info['crawl_page'] = page_num
                
                all_preview_data.extend(limited_links)
                
                print(f"   ✅ 成功提取 {len(limited_links)} 个脚本预览信息")
                
                # 显示部分预览信息
                for i, script_info in enumerate(limited_links[:3]):  # 显示前3个
                    print(f"     [{i+1}] {script_info.get('preview_title', 'N/A')}")
                    print(f"         作者: {script_info.get('preview_author', 'N/A')}")
                    print(f"         点赞: {script_info.get('preview_likes_count', 0)}")
                    print(f"         评论: {script_info.get('preview_comments_count', 0)}")
                if len(limited_links) > 3:
                    print(f"     ... 还有 {len(limited_links) - 3} 个脚本")
            else:
                print(f"   ❌ 第 {page_num} 页未提取到任何脚本")
        
        print(f"\n📊 预览信息提取总结:")
        print(f"   总脚本数: {len(all_preview_data)}")
        
        # 统计数据
        total_likes = sum(item.get('preview_likes_count', 0) for item in all_preview_data)
        total_comments = sum(item.get('preview_comments_count', 0) for item in all_preview_data)
        print(f"   总点赞数: {total_likes:,}")
        print(f"   总评论数: {total_comments:,}")
        
    except Exception as e:
        print(f"   ❌ 预览信息提取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 测试详情页面信息提取 (使用Selenium)
    print(f"\n🔍 第二步: 测试详情页面完整信息提取 (Selenium)")
    print("-" * 60)
    
    detailed_data = []
    
    # 选择前3个脚本进行详细信息提取
    test_scripts = all_preview_data[:3]
    
    for i, preview_info in enumerate(test_scripts):
        script_url = preview_info.get('script_url')
        if not script_url:
            continue
        
        print(f"\n📝 [{i+1}/3] 提取详细信息: {preview_info.get('preview_title', 'N/A')}")
        print(f"   URL: {script_url}")
        
        try:
            # 提取详细信息
            detailed_info = crawler.extract_detailed_data(script_url)
            
            if detailed_info:
                # 合并预览信息和详细信息
                combined_info = {**preview_info, **detailed_info}
                detailed_data.append(combined_info)
                
                print(f"   ✅ 成功提取详细信息")
                print(f"     标题: {detailed_info.get('name', 'N/A')}")
                print(f"     作者: {detailed_info.get('user', {}).get('username', 'N/A')}")
                print(f"     详情页点赞数: {detailed_info.get('likes_count', 0)}")
                print(f"     源代码长度: {len(detailed_info.get('source_code', '') or '')}")
                
                # 比较预览和详情的点赞数
                preview_likes = preview_info.get('preview_likes_count', 0)
                detail_likes = detailed_info.get('likes_count', 0)
                if preview_likes != detail_likes:
                    print(f"     ⚠ 点赞数不一致: 预览={preview_likes}, 详情={detail_likes}")
                else:
                    print(f"     ✅ 点赞数一致: {preview_likes}")
            else:
                print(f"   ❌ 详细信息提取失败")
                
        except Exception as e:
            print(f"   ❌ 详细信息提取异常: {e}")
    
    # 3. 保存结果
    print(f"\n💾 第三步: 保存测试结果")
    print("-" * 60)
    
    # 保存预览数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    preview_file = f"test_results/multi_page_preview_{timestamp}.json"
    os.makedirs("test_results", exist_ok=True)
    
    with open(preview_file, 'w', encoding='utf-8') as f:
        json.dump(all_preview_data, f, indent=2, ensure_ascii=False)
    print(f"   ✅ 预览数据已保存: {preview_file}")
    
    # 保存详细数据
    if detailed_data:
        detailed_file = f"test_results/multi_page_detailed_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 详细数据已保存: {detailed_file}")
    
    # 4. 总结报告
    print(f"\n📈 第四步: 测试总结")
    print("-" * 60)
    
    print(f"✅ 成功完成多页爬取测试")
    print(f"")
    print(f"📊 数据统计:")
    print(f"   爬取页数: {end_page - start_page + 1}")
    print(f"   预览脚本总数: {len(all_preview_data)}")
    print(f"   详细信息脚本数: {len(detailed_data)}")
    
    if detailed_data:
        print(f"")
        print(f"🔍 质量分析:")
        
        # 源代码提取成功率
        source_code_count = sum(1 for item in detailed_data if item.get('source_code'))
        print(f"   源代码提取成功率: {source_code_count}/{len(detailed_data)} ({source_code_count/len(detailed_data)*100:.1f}%)")
        
        # 用户信息提取成功率
        user_info_count = sum(1 for item in detailed_data if item.get('user', {}).get('username'))
        print(f"   用户信息提取成功率: {user_info_count}/{len(detailed_data)} ({user_info_count/len(detailed_data)*100:.1f}%)")
        
        # 点赞数对比
        consistent_likes = sum(1 for item in detailed_data 
                             if item.get('preview_likes_count') == item.get('likes_count'))
        print(f"   点赞数一致性: {consistent_likes}/{len(detailed_data)} ({consistent_likes/len(detailed_data)*100:.1f}%)")
    
    print(f"\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    test_multi_page_crawling()