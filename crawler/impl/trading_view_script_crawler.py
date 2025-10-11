#!/usr/bin/env python3
"""
TradingView script crawler implementation with pagination support
"""
import time
import re
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os

# 处理相对导入
try:
    from ..core.web_crawler import BaseWebCrawler, DataExtractor
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.web_crawler import BaseWebCrawler, DataExtractor

# Selenium imports for JavaScript rendering
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not installed. JavaScript rendering will not be available.")
    print("To enable JavaScript rendering, install: pip install selenium webdriver-manager")


class TradingViewScriptCrawler(BaseWebCrawler):
    """TradingView-specific crawler implementation"""
    
    def __init__(self, user_agent: str = None):
        super().__init__(user_agent)
        self.base_domain = 'https://www.tradingview.com'
    
    def get_page_url(self, base_url: str, page_num: int) -> str:
        """
        Generate URL for TradingView pagination pattern
        TradingView uses /scripts/page-2/ pattern
        """
        if page_num == 1:
            return base_url
        else:
            # TradingView pagination pattern
            if base_url.endswith('/'):
                return f"{base_url}page-{page_num}/"
            else:
                return f"{base_url}/page-{page_num}/"
    
    def extract_links(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract script links from a TradingView listing page
        
        Args:
            url: TradingView listing page URL
            
        Returns:
            List of dictionaries containing script link information
        """
        try:
            soup = self.browser.get_and_parse(url)
            
            # Find all article elements containing script links
            articles = soup.find_all('article', class_=re.compile(r'.*card.*'))
            script_links = []
            
            for article in articles:
                # Look for links in the article that point to /script/
                links = article.find_all('a', href=re.compile(r'/script/[^/]+/'))
                
                for link in links:
                    href = link.get('href')
                    if href:
                        # Convert relative URLs to absolute
                        full_url = DataExtractor.clean_url(self.base_domain, href)
                        
                        # Extract preview information from the article card
                        preview_info = self._extract_preview_info(article)
                        preview_info['script_url'] = full_url
                        
                        script_links.append(preview_info)
                        break  # Only need one link per article
            
            self.logger.info(f"Found {len(script_links)} script links in listing: {url}")
            return script_links
            
        except Exception as e:
            self.logger.error(f"Error extracting article links from {url}: {e}")
            return []
    
    def _extract_preview_info(self, article_soup) -> Dict[str, Any]:
        """Extract preview information from article card"""
        info = {}
        
        try:
            # Extract title
            title_selectors = [
                'a[data-qa-id="ui-lib-card-link-title"]',
                '.card-title a',
                'h3 a',
                'a[href*="/script/"]'
            ]
            title = DataExtractor.extract_text_by_selectors(article_soup, title_selectors)
            if title:
                info['preview_title'] = title
            
            # Extract author
            author_selectors = [
                'a[class*="author"]',
                '.card-author a',
                '[data-qa-id*="author"] a'
            ]
            author = DataExtractor.extract_text_by_selectors(article_soup, author_selectors)
            if author:
                info['preview_author'] = author.replace('by ', '').strip()
                
                # Get author URL
                author_url = DataExtractor.extract_attribute_by_selectors(
                    article_soup, author_selectors, 'href'
                )
                if author_url:
                    info['preview_author_url'] = DataExtractor.clean_url(self.base_domain, author_url)
            
            # Extract publication time
            time_elem = article_soup.find('time')
            if time_elem:
                info['preview_created_at'] = time_elem.get('datetime')
                info['preview_created_display'] = time_elem.get_text(strip=True)
            
            # Extract likes/boost count
            likes_selectors = [
                'button[class*="boost"]',
                '.boost-button',
                '[data-qa-id*="boost"]',
                '.likes-count'
            ]
            likes_text = DataExtractor.extract_text_by_selectors(article_soup, likes_selectors)
            info['preview_likes_count'] = DataExtractor.extract_number_from_text(likes_text)
            
            # Extract comments count
            comment_selectors = [
                'a[data-qa-id="ui-lib-card-comment-button"]',
                '.comment-button',
                '[href*="comment"]'
            ]
            comment_text = DataExtractor.extract_text_by_selectors(article_soup, comment_selectors)
            info['preview_comments_count'] = DataExtractor.extract_number_from_text(comment_text)
                    
        except Exception as e:
            self.logger.warning(f"Error extracting preview info: {e}")
        
        return info
    
    def extract_detailed_data(self, script_url: str, use_selenium: bool = True) -> Optional[Dict[str, Any]]:
        """
        Extract detailed data from individual TradingView script page
        
        Args:
            script_url: URL of the script page
            use_selenium: Whether to use Selenium for JavaScript rendering (default: True)
            
        Returns:
            Dictionary containing detailed script data or None if failed
        """
        try:
            if use_selenium:
                # 使用Selenium获取JavaScript渲染后的页面
                self.logger.info(f"使用Selenium提取详细信息: {script_url}")
                soup = self.browser.get_and_parse_with_selenium(
                    script_url, 
                    click_element="Source code"
                )
            else:
                # 使用普通HTTP请求
                soup = self.browser.get_and_parse(script_url)
            
            # Extract script ID from URL
            script_id_match = re.search(r'/script/([^/]+)/', script_url)
            script_id = script_id_match.group(1) if script_id_match else None
            
            data = {
                'id': script_id,
                'name': self._extract_script_title(soup),
                'description': self._extract_script_description(soup),
                'created_at': self._extract_script_created_at(soup),
                'chart_url': self._extract_chart_url(soup, script_url),
                'symbol': self._extract_symbol(soup),
                'user': self._extract_user_info(soup),
                'likes_count': self._extract_script_likes_count(soup),
                'source_code': self._extract_source_code(soup),
                'script_url': script_url
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error extracting detailed data from {script_url}: {e}")
            return None
    
    def _extract_script_title(self, soup) -> Optional[str]:
        """Extract the script title from detailed page"""
        title_selectors = [
            'h1[data-name="legend-source-title"]',
            '.tv-chart-view__title',
            'h1.js-script-title',
            '.script-title h1',
            'h1'
        ]
        return DataExtractor.extract_text_by_selectors(soup, title_selectors)
    
    def _extract_script_description(self, soup) -> Optional[str]:
        """Extract full script description"""
        desc_selectors = [
            # New TradingView layout - specific class for description
            '.content-aqIxarm1 .description-aqIxarm1',  # Parent container + description
            '.description-aqIxarm1',                      # Direct description container
            '.description-aqIxarm1 .update-_PPhhqv6',    # Inner content wrapper
            '.description-aqIxarm1 .ast-_PPhhqv6',       # Innermost content wrapper
            # Legacy selectors as fallback
            '.tv-chart-view__description',
            '.js-description-content',
            '[data-name="description"]',
            '.script-description',
            '.description'
        ]
        return DataExtractor.extract_text_by_selectors(soup, desc_selectors)
    
    def _extract_script_created_at(self, soup) -> Optional[str]:
        """Extract creation date from script page"""
        date_selectors = [
            'time[datetime]',
            '.tv-chart-view__published-date time',
            '[data-name="published-date"]',
            '.published-date time'
        ]
        
        # Try to get datetime attribute first
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    return datetime_attr
                # Fallback to text content
                return element.get_text(strip=True)
        
        return None
    
    def _extract_chart_url(self, soup, script_url: str) -> str:
        """Extract chart URL - usually the script URL itself or a chart view"""
        chart_selectors = [
            'a[href*="/chart/"]',
            '.js-chart-link',
            '.chart-link'
        ]
        
        chart_href = DataExtractor.extract_attribute_by_selectors(soup, chart_selectors, 'href')
        if chart_href:
            return DataExtractor.clean_url(self.base_domain, chart_href)
        
        # Fallback to script URL
        return script_url
    
    def _extract_symbol(self, soup) -> Optional[str]:
        """Extract associated trading symbol"""
        symbol_selectors = [
            '[data-name="legend-source-description"] .js-symbol-name',
            '.tv-symbol-header__short-name',
            '.js-symbol-link',
            '.symbol-name'
        ]
        
        symbol = DataExtractor.extract_text_by_selectors(soup, symbol_selectors)
        if symbol:
            return symbol
        
        # Look in meta tags
        meta_symbol = soup.find('meta', {'name': 'symbol'})
        if meta_symbol:
            return meta_symbol.get('content')
            
        return None
    
    def _extract_user_info(self, soup) -> Dict[str, Any]:
        """Extract detailed user information"""
        user_info = {}
        
        # Find user link - updated with new selectors
        user_selectors = [
            '[class*="usernameOutline-"] [class*="username"]',  # 新的选择器
            'a[data-username]',
            '.tv-user-link',
            '.js-username-link',
            '.author-link'
        ]
        
        for selector in user_selectors:
            user_element = soup.select_one(selector)
            if user_element:
                username = user_element.get('data-username') or user_element.get_text(strip=True)
                if username:
                    user_info['username'] = username
                    
                    # 查找父级链接元素
                    link_element = user_element if user_element.name == 'a' else user_element.find_parent('a')
                    if link_element:
                        profile_href = link_element.get('href')
                        if profile_href:
                            user_info['profile_url'] = DataExtractor.clean_url(self.base_domain, profile_href)
                    
                    # Check for pro/premium indicators
                    pro_indicator = user_element.find_next(class_=re.compile(r'.*(pro|premium).*'))
                    user_info['pro_plan'] = pro_indicator is not None
                    break
        
        return user_info
    
    def _extract_script_likes_count(self, soup) -> int:
        """Extract likes/boost count from script page"""
        # 尝试新的Selenium特定提取方法
        likes_count = self._extract_likes_count_selenium(soup)
        if likes_count > 0:
            return likes_count
        
        # 回退到传统选择器
        likes_selectors = [
            '.js-likes-count',
            '.js-boost-count',
            '[data-name="like-count"]',
            '.boost-count',
            '.likes-count'
        ]
        
        likes_text = DataExtractor.extract_text_by_selectors(soup, likes_selectors)
        return DataExtractor.extract_number_from_text(likes_text)

    def _extract_likes_count_selenium(self, soup) -> int:
        """
        专门用于Selenium渲染页面的likes数量提取
        从aria-pressed按钮下的多个digitGrid中提取digit并拼接
        """
        try:
            # 查找带有aria-pressed属性的boost按钮
            boost_buttons = soup.find_all('button', {'aria-pressed': True}) or \
                          soup.find_all('button', {'aria-pressed': 'false'}) or \
                          soup.find_all('button', {'aria-pressed': 'true'})
            
            for button in boost_buttons:
                # 查找button内的container-PEo_qlAm
                container = button.find('span', class_=lambda x: x and 'container-' in str(x))
                if not container:
                    continue
                
                # 查找所有digitGrid元素
                digit_grids = container.find_all('span', class_=lambda x: x and 'digitGrid-' in str(x))
                
                if digit_grids:
                    # 提取每个digit并拼接
                    digits = []
                    for grid in digit_grids:
                        digit_span = grid.find('span', class_=lambda x: x and 'digit-' in str(x))
                        if digit_span and digit_span.get_text().strip().isdigit():
                            digits.append(digit_span.get_text().strip())
                    
                    if digits:
                        # 拼接所有数字
                        likes_str = ''.join(digits)
                        likes_count = int(likes_str)
                        print(f"✓ 从digitGrid提取到likes数量: {likes_count}")
                        return likes_count
            
            # 备用方法：直接搜索digitGrid模式
            digit_grids = soup.find_all('span', class_=re.compile(r'digitGrid-'))
            if digit_grids:
                digits = []
                for grid in digit_grids:
                    digit_span = grid.find('span', class_=re.compile(r'digit-'))
                    if digit_span:
                        digit_text = digit_span.get_text().strip()
                        if digit_text.isdigit():
                            digits.append(digit_text)
                
                if digits:
                    likes_str = ''.join(digits)
                    likes_count = int(likes_str)
                    print(f"✓ 从备用digitGrid提取到likes数量: {likes_count}")
                    return likes_count
                    
        except Exception as e:
            print(f"⚠ digitGrid提取失败: {e}")
        
        return 0
    
    def _extract_source_code(self, soup_or_html) -> Optional[str]:
        """Extract Pine Script source code"""
        # Handle both BeautifulSoup objects and HTML strings (for Selenium results)
        if isinstance(soup_or_html, str):
            soup = BeautifulSoup(soup_or_html, 'html.parser')
            html_content = soup_or_html
        else:
            soup = soup_or_html
            html_content = str(soup)
        
        # Method 1: Extract from Monaco Editor (for JavaScript-rendered pages)
        # 查找所有Monaco Editor相关的语法高亮元素
        monaco_selectors = [
            'span[class*="mtk"]',  # Monaco Editor token spans
            '.monaco-editor span[class*="mtk"]',
            '[class*="monaco"] span[class*="mtk"]'
        ]
        
        monaco_lines = []
        for selector in monaco_selectors:
            found_elements = soup.select(selector)
            if found_elements:
                monaco_lines.extend(found_elements)
                break  # 使用第一个找到的选择器
        
        if monaco_lines:
            print(f"发现{len(monaco_lines)}个Monaco Editor语法高亮元素")
            
            # 改进的代码行重构逻辑
            code_lines = []
            current_line = []
            
            # 按DOM顺序处理所有spans
            for span in monaco_lines:
                text = span.get_text()
                if text:
                    current_line.append(text)
                
                # 检查是否为行尾（通过父级div结构或换行符识别）
                parent_div = span.find_parent('div')
                if parent_div:
                    # 获取当前span在父div中的位置
                    siblings = list(parent_div.children)
                    span_index = None
                    for i, child in enumerate(siblings):
                        if child == span:
                            span_index = i
                            break
                    
                    # 检查是否是该div中的最后一个有意义元素
                    if span_index is not None and span_index == len([s for s in siblings if s.name == 'span']) - 1:
                        if current_line:
                            code_lines.append(''.join(current_line))
                            current_line = []
            
            # 添加最后一行
            if current_line:
                code_lines.append(''.join(current_line))
            
            if code_lines:
                code_text = '\n'.join(code_lines)
                # 验证是否包含Pine Script特征
                pine_indicators = ['@version', 'indicator', 'strategy', '//@version', '// @version']
                if any(keyword in code_text for keyword in pine_indicators):
                    print(f"✓ 从Monaco Editor成功提取Pine Script代码，共{len(code_lines)}行")
                    return code_text
                else:
                    print(f"⚠ Monaco Editor内容未包含Pine Script特征，内容预览: {code_text[:200]}")
            else:
                print("⚠ Monaco Editor元素存在但无法重构代码行")
        
        # Method 2: Look for source code in various possible containers
        code_selectors = [
            'pre.tv-chart-view__source-code',
            '.js-source-code',
            'textarea[name="source"]',
            '.CodeMirror-code',
            '.pine-code',
            '.source-code pre',
            '[class*="monaco-editor"]',
            '[class*="editor"]'
        ]
        
        source_code = DataExtractor.extract_text_by_selectors(soup, code_selectors)
        if source_code and any(keyword in source_code for keyword in ['@version', 'indicator', 'strategy', '//@version']):
            return source_code
        
        # Method 3: Look for Pine Script in script tags or JSON data
        scripts = soup.find_all('script', string=re.compile(r'pine|source'))
        for script in scripts:
            if script.string:
                # Try to extract Pine Script from JSON or JavaScript
                pine_match = re.search(r'"source":\\s*"([^"]*)"', script.string)
                if pine_match:
                    decoded_source = pine_match.group(1).encode().decode('unicode_escape')
                    if any(keyword in decoded_source for keyword in ['@version', 'indicator', 'strategy', '//@version']):
                        return decoded_source
        
        # Method 4: Search in all text for Pine Script patterns
        full_text = soup.get_text()
        pine_patterns = [
            r'@version\s*=\s*\d+.*?(?=\n\s*\n|\Z)',
            r'//@version\s*=\s*\d+.*?(?=\n\s*\n|\Z)',
            r'indicator\s*\([^)]+\).*?(?=\n\s*\n|\Z)',
            r'strategy\s*\([^)]+\).*?(?=\n\s*\n|\Z)'
        ]
        
        for pattern in pine_patterns:
            matches = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if matches:
                # 尝试获取更多上下文
                start_pos = max(0, matches.start() - 100)
                end_pos = min(len(full_text), matches.end() + 2000)
                extended_text = full_text[start_pos:end_pos].strip()
                return extended_text
        
        return None
    
    def sample_fetch(self, base_url='https://www.tradingview.com/script/', 
                     sample_dir='sample_html', use_selenium=True):
        """
        从TradingView script页面和第一个脚本链接获取HTML样本用于调试
        
        Args:
            base_url: TradingView脚本页面的基础URL
            sample_dir: 保存样本HTML文件的目录
            use_selenium: 是否使用Selenium进行JavaScript渲染
            
        Returns:
            Dict: 包含抓取结果的信息
        """
        # 确保样本目录存在
        os.makedirs(sample_dir, exist_ok=True)
        
        results = {
            'base_page': None,
            'script_page': None,
            'first_script_url': None,
            'used_selenium': use_selenium
        }
        
        try:
            print(f"正在获取基础页面: {base_url}")
            response = self.browser.get_page(base_url)
            
            if response and response.status_code == 200:
                # 保存基础页面
                base_html_file = os.path.join(sample_dir, 'trading_view_scripts_page.html')
                with open(base_html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                results['base_page'] = base_html_file
                print(f"基础页面已保存到: {base_html_file}")
                
                # 解析并找到第一个脚本链接
                soup = BeautifulSoup(response.text, 'html.parser')
                first_link = soup.find('a', href=re.compile(r'/script/[^/]+/'))
                
                if first_link:
                    script_href = first_link.get('href')
                    full_script_url = urljoin(base_url, script_href)
                    results['first_script_url'] = full_script_url
                    
                    print(f"正在获取第一个脚本页面: {full_script_url}")
                    
                    if use_selenium:
                        print("使用Selenium进行JavaScript渲染...")
                        try:
                            script_html = self._fetch_with_selenium(full_script_url, wait_for_monaco=True)
                            file_suffix = '_selenium.html'
                        except Exception as e:
                            print(f"Selenium获取失败，回退到普通HTTP请求: {e}")
                            script_response = self.browser.get_page(full_script_url)
                            script_html = script_response.text if script_response and script_response.status_code == 200 else None
                            file_suffix = '_http_fallback.html'
                    else:
                        print("使用普通HTTP请求...")
                        script_response = self.browser.get_page(full_script_url)
                        script_html = script_response.text if script_response and script_response.status_code == 200 else None
                        file_suffix = '.html'
                    
                    if script_html:
                        # 保存脚本页面
                        script_html_file = os.path.join(sample_dir, f'trading_view_script_sample_script{file_suffix}')
                        with open(script_html_file, 'w', encoding='utf-8') as f:
                            f.write(script_html)
                        results['script_page'] = script_html_file
                        print(f"脚本页面已保存到: {script_html_file}")
                        
                        # 测试源码提取
                        print("尝试提取Pine Script源代码...")
                        source_code = self._extract_source_code(script_html)
                        if source_code:
                            print(f"成功提取源代码 (前100字符): {source_code[:100]}...")
                        else:
                            print("未能提取到源代码")
                    else:
                        print(f"获取脚本页面失败")
                else:
                    print("在基础页面中未找到脚本链接")
            else:
                print(f"获取基础页面失败: {response.status_code if response else 'None'}")
                
        except Exception as e:
            print(f"sample_fetch过程中发生错误: {e}")
            
        return results

    def _fetch_with_selenium(self, url, wait_for_monaco=False, timeout=30):
        """
        使用Selenium获取JavaScript渲染后的页面内容 (使用core功能)
        
        Args:
            url: 要访问的URL
            wait_for_monaco: 是否等待Monaco Editor内容
            timeout: 等待超时时间（秒）
            
        Returns:
            str: 渲染后的HTML内容
        """
        wait_element = None
        click_element = "Source code"  # 自动查找并点击Source code按钮
        
        if wait_for_monaco:
            # 等待Monaco Editor元素或Pine Script特征出现
            wait_element = ".mtk1, .monaco-editor, [class*='monaco']"
        
        return self.browser.get_with_selenium(
            url=url, 
            timeout=timeout,
            wait_for_element=wait_element,
            click_element=click_element,
            wait_after_click=3
        )


class TradingViewCrawlerWithPagination(TradingViewScriptCrawler):
    """
    Enhanced TradingView crawler with pagination support
    Provides compatibility with the original crawler interface
    """
    
    def crawl_indicators_from_pages(self, base_url: str, start_page: int = 1, 
                                  end_page: int = 1, max_scripts_per_page: int = None) -> List[Dict[str, Any]]:
        """
        Crawl indicators from multiple pages of TradingView listing
        
        Args:
            base_url: Base URL (e.g., https://www.tradingview.com/scripts/)
            start_page: Starting page number (default: 1)
            end_page: Ending page number (default: 1)
            max_scripts_per_page: Maximum scripts to extract per page (None for all)
        
        Returns:
            List of dictionaries containing script metadata
        """
        all_results = []
        
        for page_num in range(start_page, end_page + 1):
            self.logger.info(f"\\n{'='*60}")
            self.logger.info(f"CRAWLING PAGE {page_num} (of {start_page}-{end_page})")
            self.logger.info(f"{'='*60}")
            
            # Get URL for this page
            page_url = self.get_page_url(base_url, page_num)
            
            # Step 1: Get all script links from the listing page
            script_links = self.extract_links(page_url)
            
            if not script_links:
                self.logger.warning(f"No scripts found on page {page_num}, stopping...")
                break
            
            if max_scripts_per_page:
                script_links = script_links[:max_scripts_per_page]
            
            # Step 2: Visit each script page and extract detailed data
            page_results = []
            for i, link_info in enumerate(script_links):
                script_url = link_info['script_url']
                self.logger.info(f"  Page {page_num} - Script {i+1}/{len(script_links)}: {link_info.get('preview_title', 'Unknown')}")
                
                detailed_data = self.extract_detailed_data(script_url)
                if detailed_data:
                    # Merge preview info with detailed data
                    detailed_data.update(link_info)
                    detailed_data['crawl_page'] = page_num  # Track which page this came from
                    page_results.append(detailed_data)
                
                # Be respectful - add delay between requests
                import time, random
                time.sleep(random.uniform(2, 4))
            
            all_results.extend(page_results)
            self.logger.info(f"✅ Page {page_num} completed: {len(page_results)} scripts extracted")
            
            # Delay between pages
            import time, random
            time.sleep(random.uniform(3, 6))
        
        self.logger.info(f"\\n🎉 CRAWLING COMPLETED!")
        self.logger.info(f"Total pages crawled: {end_page - start_page + 1}")
        self.logger.info(f"Total scripts extracted: {len(all_results)}")
        
        return all_results


# Convenience functions for backward compatibility and easy usage
def crawl_tradingview_scripts_with_pages(base_url: str, start_page: int = 1, end_page: int = 5, 
                                       max_scripts_per_page: int = 5, output_file: str = None) -> List[Dict[str, Any]]:
    """
    Main function to crawl TradingView scripts across multiple pages
    
    Args:
        base_url: URL to a TradingView scripts listing page
        start_page: Starting page number (1-based)
        end_page: Ending page number (inclusive)
        max_scripts_per_page: Maximum scripts per page (None for all)
        output_file: Optional file to save results as JSON
    
    Returns:
        List of dictionaries containing script metadata
    """
    crawler = TradingViewCrawlerWithPagination()
    results = crawler.crawl_indicators_from_pages(
        base_url, 
        start_page=start_page, 
        end_page=end_page, 
        max_scripts_per_page=max_scripts_per_page
    )
    
    if output_file:
        crawler.save_results(results, output_file)
    
    return results


def crawl_tradingview_scripts(listing_url: str, max_scripts: int = 10, output_file: str = None) -> List[Dict[str, Any]]:
    """
    Convenience function for single page crawling (backward compatibility)
    
    Args:
        listing_url: URL to a TradingView scripts listing page
        max_scripts: Maximum number of scripts to crawl (None for all)
        output_file: Optional file to save results as JSON
    
    Returns:
        List of dictionaries containing script metadata
    """
    crawler = TradingViewScriptCrawler()
    results = crawler.crawl_pages(listing_url, max_pages=1, max_items_per_page=max_scripts)
    
    if output_file:
        crawler.save_results(results, output_file)
    
    return results