#!/usr/bin/env python3
"""
TradingView脚本爬虫 - 主程序
基于Selenium的完整TradingView Pine Script爬虫，支持多页面爬取和完整源代码提取
"""
import sys
import os
import json
import argparse
import signal
import time
from datetime import datetime
from pathlib import Path

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from impl.trading_view_script_crawler import TradingViewScriptCrawler


def load_existing_output(path):
    """Load existing detailed output file and return mapping by script_url"""
    if not path:
        return {}
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {item.get('script_url'): item for item in data}
    except Exception:
        return {}
    return {}

class TimeoutError(Exception):
    """Timeout exception for long-running operations"""
    pass

def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Operation timed out")

def crawl_with_timeout(func, timeout_seconds=120, *args, **kwargs):
    """
    Execute a function with a timeout. Skip if it takes longer than timeout_seconds.
    Default timeout is 120 seconds (2 minutes).
    """
    # Set up signal alarm for timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        result = func(*args, **kwargs)
        signal.alarm(0)  # Cancel alarm
        return result
    except TimeoutError:
        signal.alarm(0)  # Cancel alarm
        print(f"⏰ Timeout ({timeout_seconds}s) reached, skipping...")
        return None
    except Exception as e:
        signal.alarm(0)  # Cancel alarm
        print(f"❌ Error during crawling: {e}")
        return None

def setup_argparser():
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='TradingView Pine Script爬虫 - 完整源代码提取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s --pages 5                          # 爬取前5页，默认输出路径
  %(prog)s --pages 10 --output ./results      # 爬取前10页，指定输出目录
  %(prog)s --pages 3 --max-per-page 10        # 每页最多10个脚本
  %(prog)s --start-page 2 --pages 3           # 从第2页开始，爬取3页
  %(prog)s --pages 1 --no-selenium           # 禁用Selenium（不推荐）
        """
    )
    
    parser.add_argument(
        '--pages', 
        type=int, 
        default=1,
        help='要爬取的页面数量 (默认: 1)'
    )
    
    parser.add_argument(
        '--start-page',
        type=int,
        default=1,
        help='起始页面编号 (默认: 1)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./output',
        help='输出目录路径 (默认: ./output)'
    )

    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='输出文件路径，若提供将写入该文件（默认: <output>/multi_page_detailed_latest.json）'
    )
    
    parser.add_argument(
        '--max-per-page',
        type=int,
        default=None,
        help='每页最大脚本数量，None表示不限制 (默认: None)'
    )
    
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://www.tradingview.com/scripts/',
        help='TradingView脚本列表基础URL (默认: https://www.tradingview.com/scripts/)'
    )
    
    parser.add_argument(
        '--no-selenium',
        action='store_true',
        help='禁用Selenium JavaScript渲染 (不推荐，会导致源代码提取失败)'
    )
    
    parser.add_argument(
        '--preview-only',
        action='store_true',
        help='仅爬取预览信息，不获取详细信息 (更快但信息不完整)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='启用详细日志输出'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，最小化输出'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='如果已存在输出文件，是否重新爬取已存在的条目（默认: 跳过现有条目）'
    )
    
    return parser

def validate_args(args):
    """验证命令行参数"""
    errors = []
    
    if args.pages <= 0:
        errors.append("页面数量必须大于0")
    
    if args.start_page <= 0:
        errors.append("起始页面编号必须大于0")
    
    if args.max_per_page is not None and args.max_per_page <= 0:
        errors.append("每页最大脚本数量必须大于0")
    
    if args.quiet and args.verbose:
        errors.append("不能同时使用 --quiet 和 --verbose 选项")
    
    return errors

def print_header(args):
    """打印程序头部信息"""
    if args.quiet:
        return
        
    print("=" * 80)
    print("🚀 TradingView Pine Script 爬虫")
    print("=" * 80)
    print(f"📋 爬取配置:")
    print(f"   页面范围: {args.start_page}-{args.start_page + args.pages - 1} (共{args.pages}页)")
    print(f"   基础URL: {args.base_url}")
    print(f"   输出目录: {args.output}")
    print(f"   每页最大脚本: {args.max_per_page or '无限制'}")
    print(f"   使用Selenium: {'否' if args.no_selenium else '是'}")
    print(f"   详细信息: {'否' if args.preview_only else '是'}")
    print()

def crawl_preview_data(crawler, args):
    """爬取预览数据"""
    if not args.quiet:
        print("🔍 第一步: 爬取列表页面预览信息")
        print("-" * 60)
    
    all_preview_data = []
    
    for page_num in range(args.start_page, args.start_page + args.pages):
        if not args.quiet:
            print(f"\n📄 爬取第 {page_num} 页...")
        
        # 构造页面URL
        if page_num == 1:
            page_url = args.base_url
        else:
            separator = '&' if '?' in args.base_url else '?'
            page_url = f"{args.base_url}{separator}page={page_num}"
        
        if args.verbose:
            print(f"   URL: {page_url}")
        
        try:
            # 提取链接和预览信息
            preview_links = crawler.extract_links(page_url)
            
            if preview_links:
                # 限制每页的脚本数量
                if args.max_per_page:
                    limited_links = preview_links[:args.max_per_page]
                else:
                    limited_links = preview_links
                
                # 添加页面标记
                for link_info in limited_links:
                    link_info['crawl_page'] = page_num
                
                all_preview_data.extend(limited_links)
                
                if not args.quiet:
                    print(f"   ✅ 成功提取 {len(limited_links)} 个脚本预览信息")
                
                if args.verbose:
                    for i, script_info in enumerate(limited_links[:3]):  # 显示前3个
                        print(f"     [{i+1}] {script_info.get('preview_title', 'N/A')}")
                        print(f"         作者: {script_info.get('preview_author', 'N/A')}")
                        print(f"         点赞: {script_info.get('preview_likes_count', 0)}")
                    if len(limited_links) > 3:
                        print(f"     ... 还有 {len(limited_links) - 3} 个脚本")
                        
            else:
                if not args.quiet:
                    print(f"   ⚠ 第 {page_num} 页未提取到任何脚本")
                    
        except Exception as e:
            print(f"   ❌ 第 {page_num} 页爬取失败: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    return all_preview_data

def crawl_detailed_data(crawler, preview_data, args):
    """爬取详细数据"""
    if args.preview_only:
        return preview_data
    
    if not args.quiet:
        print(f"\n🔍 第二步: 爬取详细信息 ({'Selenium' if not args.no_selenium else 'HTTP'})")
        print("-" * 60)
    
    detailed_data = []
    total_scripts = len(preview_data)
    
    for i, preview_info in enumerate(preview_data):
        script_url = preview_info.get('script_url')
        if not script_url:
            continue
        
        if not args.quiet:
            title = preview_info.get('preview_title', 'N/A')
            print(f"\n📝 [{i+1}/{total_scripts}] {title}")
            
        if args.verbose:
            print(f"   URL: {script_url}")
        
        try:
            # 提取详细信息（使用超时机制）
            start_time = time.time()
            detailed_info = crawl_with_timeout(
                crawler.extract_detailed_data,
                timeout_seconds=120,  # 2分钟超时
                script_url=script_url,
                use_selenium=not args.no_selenium
            )
            elapsed = time.time() - start_time
            
            if detailed_info:
                # 合并预览信息和详细信息
                combined_info = {**preview_info, **detailed_info}
                detailed_data.append(combined_info)
                
                if not args.quiet:
                    print(f"   ✅ 成功 ({elapsed:.1f}s)")
                
                if args.verbose:
                    print(f"     标题: {detailed_info.get('name', 'N/A')}")
                    print(f"     作者: {detailed_info.get('user', {}).get('username', 'N/A')}")
                    print(f"     点赞: {detailed_info.get('likes_count', 0)}")
                    print(f"     源代码: {len(detailed_info.get('source_code', '') or '')} 字符")
            else:
                if not args.quiet:
                    print(f"   ❌ 详细信息提取失败 ({elapsed:.1f}s)")
                    
        except Exception as e:
            print(f"   ❌ 异常: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    return detailed_data

def save_results(data, args):
    """保存结果到JSON文件"""
    if not args.quiet:
        print(f"\n💾 保存结果")
        print("-" * 60)
    
    # 创建输出目录
    # 如果指定了完整输出文件路径，则使用该路径
    if args.output_file:
        filepath = Path(args.output_file)
        filepath.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_type = "preview" if args.preview_only else "detailed"
        filename = f"tradingview_{data_type}_{timestamp}.json"
        filepath = output_dir / filename
    
    # 保存数据
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    if not args.quiet:
        print(f"   ✅ 数据已保存: {filepath}")
        print(f"   📊 总脚本数: {len(data)}")
    
    return str(filepath)

def print_summary(data, args, filepath):
    """打印总结报告"""
    if args.quiet:
        # 静默模式只输出文件路径
        print(filepath)
        return
    
    print(f"\n📈 爬取总结")
    print("-" * 60)
    print(f"✅ 爬取完成")
    print(f"")
    print(f"📊 数据统计:")
    print(f"   爬取页数: {args.pages}")
    print(f"   总脚本数: {len(data)}")
    
    if not args.preview_only and data:
        # 计算质量指标
        source_code_count = sum(1 for item in data if item.get('source_code'))
        user_info_count = sum(1 for item in data if item.get('user', {}).get('username'))
        
        print(f"")
        print(f"🔍 质量分析:")
        print(f"   源代码提取成功率: {source_code_count}/{len(data)} ({source_code_count/len(data)*100:.1f}%)")
        print(f"   用户信息提取成功率: {user_info_count}/{len(data)} ({user_info_count/len(data)*100:.1f}%)")
        
        # 统计总点赞数
        total_likes = sum(item.get('likes_count', 0) or item.get('preview_likes_count', 0) for item in data)
        if total_likes > 0:
            print(f"   总点赞数: {total_likes:,}")
    
    print(f"")
    print(f"📁 输出文件: {filepath}")
    print(f"\n" + "=" * 80)

def main():
    """主函数"""
    # 解析命令行参数
    parser = setup_argparser()
    args = parser.parse_args()
    
    # 验证参数
    validation_errors = validate_args(args)
    if validation_errors:
        print("❌ 参数错误:")
        for error in validation_errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # 打印头部信息
    print_header(args)
    
    try:
        # 初始化爬虫
        if not args.quiet:
            print("🔧 初始化爬虫...")
        
        crawler = TradingViewScriptCrawler()
        
        # 确定输出文件路径（单一JSON文件保存详细结果）
        if args.output_file:
            output_file = args.output_file
        else:
            # 默认放在输出目录下的 multi_page_detailed_latest.json
            os.makedirs(args.output, exist_ok=True)
            output_file = os.path.join(args.output, 'multi_page_detailed_latest.json')

        # 读取已有结果（如果有），用于跳过已抓取条目
        existing_map = load_existing_output(output_file)
        if not args.quiet:
            print(f"Loaded {len(existing_map)} existing detailed items from {output_file}")

        # 第一步: 爬取预览数据
        preview_data = crawl_preview_data(crawler, args)
        
        if not preview_data:
            print("❌ 未爬取到任何预览数据")
            sys.exit(1)

        # 第二步: 遍历预览并爬取详细数据（跳过已存在，除非 --overwrite）
        detailed_results = []
        # 如果已有数据且不覆盖，先把已有数据加入结果（保持顺序可能不同）
        if not args.overwrite and existing_map:
            # We'll add existing items as placeholders and skip crawling them
            # Note: existing_map values are dicts
            pass

        total = len(preview_data)
        for idx, preview in enumerate(preview_data):
            script_url = preview.get('script_url')
            if not script_url:
                continue

            # 如果已存在并且不覆盖，直接使用已有数据
            if script_url in existing_map and not args.overwrite:
                if not args.quiet:
                    print(f"Skipping existing: {script_url}")
                detailed_results.append(existing_map[script_url])
                continue

            if not args.quiet:
                print(f"[{idx+1}/{total}] Crawling detail: {script_url}")

            # 使用超时机制爬取详细数据（2分钟超时）
            start_time = time.time()
            detail = crawl_with_timeout(
                crawler.extract_detailed_data,
                timeout_seconds=120,  # 2分钟超时
                script_url=script_url,
                use_selenium=not args.no_selenium
            )
            elapsed = time.time() - start_time
            
            if detail:
                if not args.quiet:
                    print(f"✅ Extracted detail in {elapsed:.1f}s")
                merged = {**preview, **detail}
                detailed_results.append(merged)

                # 增量保存到输出文件，防止中途丢失
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Warning: incremental save failed: {e}")
            else:
                if not args.quiet:
                    print(f"❌ Failed to extract detail for {script_url} (took {elapsed:.1f}s)")

        # 第三步: 最终保存（覆盖文件）
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_results, f, indent=2, ensure_ascii=False)
            filepath = output_file
        except Exception as e:
            print(f"Failed to write final output: {e}")
            filepath = None
        
        # 第四步: 打印总结
        print_summary(detailed_results, args, filepath)
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断爬取")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 爬取过程出现异常: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()