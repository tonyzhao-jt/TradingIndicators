#!/usr/bin/env python3
"""
Generic web crawler base class for simulating browser behavior
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from urllib.parse import urljoin, urlparse
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any

# Selenium imports with availability check
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    pass


class BaseBrowserSession:
    """Base class for managing browser session behavior"""
    
    def __init__(self, user_agent: str = None):
        self.session = requests.Session()
        
        # Default user agent if none provided
        if user_agent is None:
            user_agent = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
        
        # Setup default headers to simulate browser behavior
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def set_custom_headers(self, headers: Dict[str, str]):
        """Set custom headers for the session"""
        self.session.headers.update(headers)
    
    def get_page(self, url: str, max_retries: int = 3, timeout: int = 30) -> requests.Response:
        """
        Fetch a page with retry logic and random delays to simulate human behavior
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If all retry attempts fail
        """
        for attempt in range(max_retries):
            try:
                # Random delay to avoid being blocked (simulate human behavior)
                delay = random.uniform(1, 3)
                self.logger.debug(f"Waiting {delay:.2f}s before request to {url}")
                time.sleep(delay)
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                
                self.logger.info(f"Successfully fetched: {url}")
                return response
                
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                
                if attempt == max_retries - 1:
                    self.logger.error(f"All attempts failed for {url}")
                    raise
                
                # Exponential backoff with jitter
                backoff_delay = random.uniform(2 ** attempt, 2 ** (attempt + 1))
                self.logger.debug(f"Backing off for {backoff_delay:.2f}s")
                time.sleep(backoff_delay)
    
    def parse_html(self, content: bytes) -> BeautifulSoup:
        """Parse HTML content using BeautifulSoup"""
        return BeautifulSoup(content, 'html.parser')
    
    def get_and_parse(self, url: str, max_retries: int = 3) -> BeautifulSoup:
        """Convenience method to fetch and parse HTML"""
        response = self.get_page(url, max_retries)
        return self.parse_html(response.content)
    
    def get_with_selenium(self, url: str, timeout: int = 30, wait_for_element: str = None, 
                         click_element: str = None, wait_after_click: int = 3) -> str:
        """
        使用Selenium获取JavaScript渲染后的页面内容
        
        Args:
            url: 要访问的URL
            timeout: 等待超时时间（秒）
            wait_for_element: 等待特定元素出现的选择器
            click_element: 需要点击的元素选择器
            wait_after_click: 点击后等待时间（秒）
            
        Returns:
            str: 渲染后的HTML内容
            
        Raises:
            ImportError: 如果Selenium不可用
            Exception: Selenium操作失败
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not available. Please install selenium and webdriver-manager.")
        
        driver = None
        try:
            # 设置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 初始化WebDriver
            self.logger.info("正在初始化Chrome WebDriver...")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # 执行反检测脚本
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info(f"Selenium正在访问: {url}")
            driver.get(url)
            
            # 等待页面加载
            self.logger.info("等待页面加载...")
            time.sleep(3)
            
            # 等待特定元素出现
            if wait_for_element:
                try:
                    WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                    )
                    self.logger.info(f"✓ 找到等待元素: {wait_for_element}")
                except Exception as e:
                    self.logger.warning(f"等待元素超时: {wait_for_element}, {e}")
            
            # 点击特定元素（如Source code按钮）
            if click_element:
                try:
                    self.logger.info(f"寻找点击元素: {click_element}")
                    # 尝试多种方法查找元素
                    click_targets = []
                    
                    # 按文本查找
                    if 'Source code' in click_element or '源代码' in click_element:
                        click_targets = driver.find_elements(By.XPATH, 
                            "//*[contains(text(), 'Source code') or contains(text(), '源代码')]")
                    else:
                        click_targets = driver.find_elements(By.CSS_SELECTOR, click_element)
                    
                    if click_targets:
                        self.logger.info(f"发现{len(click_targets)}个匹配元素，点击第一个...")
                        driver.execute_script("arguments[0].click();", click_targets[0])
                        self.logger.info("✓ 元素点击成功")
                        time.sleep(wait_after_click)
                    else:
                        self.logger.warning(f"未找到可点击元素: {click_element}")
                        
                except Exception as e:
                    self.logger.warning(f"点击元素失败: {e}")
            
            # 额外等待JavaScript渲染
            time.sleep(2)
            
            # 获取渲染后的HTML
            html_content = driver.page_source
            self.logger.info(f"✓ 获取到HTML长度: {len(html_content):,} 字符")
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Selenium操作失败: {e}")
            raise
            
        finally:
            if driver:
                driver.quit()
                self.logger.debug("✓ WebDriver已关闭")
    
    def get_and_parse_with_selenium(self, url: str, timeout: int = 30, 
                                  wait_for_element: str = None, click_element: str = None) -> BeautifulSoup:
        """使用Selenium获取并解析HTML"""
        html_content = self.get_with_selenium(url, timeout, wait_for_element, click_element)
        return BeautifulSoup(html_content, 'html.parser')


class BaseWebCrawler(ABC):
    """Abstract base class for web crawlers"""
    
    def __init__(self, user_agent: str = None):
        self.browser = BaseBrowserSession(user_agent)
        self.logger = self.browser.logger
    
    @abstractmethod
    def extract_links(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract links from a listing page
        
        Args:
            url: URL of the listing page
            
        Returns:
            List of dictionaries containing link information
        """
        pass
    
    @abstractmethod
    def extract_detailed_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract detailed data from a specific page
        
        Args:
            url: URL of the page to extract data from
            
        Returns:
            Dictionary containing extracted data or None if failed
        """
        pass
    
    def crawl_pages(self, base_url: str, max_pages: int = 1, max_items_per_page: int = None) -> List[Dict[str, Any]]:
        """
        Generic method to crawl multiple pages
        
        Args:
            base_url: Base URL to start crawling
            max_pages: Maximum number of pages to crawl
            max_items_per_page: Maximum items to extract per page
            
        Returns:
            List of extracted data
        """
        all_results = []
        
        for page_num in range(1, max_pages + 1):
            self.logger.info(f"Crawling page {page_num}/{max_pages}")
            
            # Generate URL for this page
            page_url = self.get_page_url(base_url, page_num)
            
            # Extract links from the listing page
            links = self.extract_links(page_url)
            
            if not links:
                self.logger.warning(f"No links found on page {page_num}, stopping")
                break
            
            if max_items_per_page:
                links = links[:max_items_per_page]
            
            # Extract detailed data from each link
            page_results = []
            for i, link_info in enumerate(links):
                target_url = link_info.get('url') or link_info.get('script_url')
                if not target_url:
                    self.logger.warning(f"No URL found in link info: {link_info}")
                    continue
                
                self.logger.info(f"Processing item {i+1}/{len(links)}: {target_url}")
                
                detailed_data = self.extract_detailed_data(target_url)
                if detailed_data:
                    # Merge preview info with detailed data
                    detailed_data.update(link_info)
                    detailed_data['crawl_page'] = page_num
                    page_results.append(detailed_data)
                
                # Respectful delay between requests
                time.sleep(random.uniform(1, 3))
            
            all_results.extend(page_results)
            self.logger.info(f"Page {page_num} completed: {len(page_results)} items extracted")
            
            # Delay between pages
            time.sleep(random.uniform(2, 5))
        
        self.logger.info(f"Crawling completed: {len(all_results)} total items extracted")
        return all_results
    
    def get_page_url(self, base_url: str, page_num: int) -> str:
        """
        Generate URL for a specific page number
        Override this method for site-specific pagination patterns
        
        Args:
            base_url: Base URL
            page_num: Page number (1-based)
            
        Returns:
            URL for the specific page
        """
        if page_num == 1:
            return base_url
        else:
            # Default pagination pattern
            separator = "" if base_url.endswith('/') else "/"
            return f"{base_url}{separator}page/{page_num}/"
    
    def save_results(self, results: List[Dict[str, Any]], filename: str):
        """Save results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Results saved to {filename}")


class DataExtractor:
    """Utility class for common data extraction patterns"""
    
    @staticmethod
    def extract_text_by_selectors(soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """
        Try multiple CSS selectors and return first match
        
        Args:
            soup: BeautifulSoup object
            selectors: List of CSS selectors to try
            
        Returns:
            Extracted text or None
        """
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None
    
    @staticmethod
    def extract_attribute_by_selectors(soup: BeautifulSoup, selectors: List[str], attribute: str) -> Optional[str]:
        """
        Try multiple CSS selectors and return first attribute match
        
        Args:
            soup: BeautifulSoup object
            selectors: List of CSS selectors to try
            attribute: Attribute name to extract
            
        Returns:
            Attribute value or None
        """
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get(attribute)
        return None
    
    @staticmethod
    def extract_number_from_text(text: str) -> int:
        """
        Extract a number from text string
        
        Args:
            text: Text containing a number
            
        Returns:
            Extracted number or 0 if not found
        """
        if not text:
            return 0
        
        match = re.search(r'(\d+(?:,\d+)*)', text.replace(',', ''))
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                return 0
        return 0
    
    @staticmethod
    def clean_url(base_url: str, relative_url: str) -> str:
        """
        Convert relative URL to absolute URL
        
        Args:
            base_url: Base URL for resolution
            relative_url: Relative or absolute URL
            
        Returns:
            Absolute URL
        """
        return urljoin(base_url, relative_url)