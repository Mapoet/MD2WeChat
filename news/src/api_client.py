#!/usr/bin/env python3
"""
卫星新闻API客户端 - 完整版本
"""

import requests
import json
import time
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsCategory(Enum):
    """新闻分类枚举"""
    LAUNCH = "launch"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    POLICY = "policy"
    HARDWARE = "hardware"
    CONSTELLATION = "constellation"
    OTHER = "other"

@dataclass
class NewsItem:
    """新闻数据类"""
    id: int
    title: str
    url: str
    summary: str
    published_at: str
    date: str
    constellations: List[str]
    category: str
    importance: int
    tags: List[str]
    source: str
    source_type: str
    fetched_at: str = None
    
    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NewsItem':
        """从字典创建"""
        return cls(**data)
    
    @property
    def is_important(self) -> bool:
        """是否重要新闻（重要性≥5）"""
        return self.importance >= 5
    
    @property
    def published_date(self) -> str:
        """获取发布日期（YYYY-MM-DD格式）"""
        try:
            return self.date.split('T')[0]
        except:
            return self.date[:10] if len(self.date) >= 10 else ""

class SatelliteNewsAPIClient:
    """卫星新闻API客户端"""
    
    def __init__(self, base_url: str = "https://api.satellitemap.space", 
                 api_key: str = "development-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": "SatelliteNewsBot/1.0",
            "Accept": "application/json"
        })
        self.request_timeout = 30
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """发送HTTP请求，支持重试"""
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"请求 {url}, 参数: {params}, 尝试 {attempt + 1}/{self.max_retries}")
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"所有重试失败: {e}")
                    return None
        return None
    
    def fetch_news_page(self, page: int = 1, limit: int = 50) -> Tuple[List[NewsItem], Dict]:
        """
        获取单页新闻
        
        返回:
            (新闻列表, 分页信息)
        """
        url = f"{self.base_url}/news"
        params = {"page": page, "limit": limit}
        
        data = self._make_request(url, params)
        if not data:
            return [], {}
        
        # 解析新闻项
        news_items = []
        for item_data in data.get("items", []):
            try:
                news_item = NewsItem.from_dict(item_data)
                news_items.append(news_item)
            except Exception as e:
                logger.error(f"解析新闻项失败: {e}, 数据: {item_data}")
        
        # 提取分页信息
        pagination = data.get("pagination", {})
        
        logger.info(f"获取第 {page} 页新闻，共 {len(news_items)} 条")
        return news_items, pagination
    
    def fetch_all_recent_news(self, days: int = 7, max_pages: int = 20) -> List[NewsItem]:
        """
        获取最近几天的所有新闻
        
        参数:
            days: 最近几天
            max_pages: 最大页数限制
        
        返回:
            新闻列表
        """
        all_news = []
        page = 1
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        while page <= max_pages:
            logger.info(f"获取第 {page} 页新闻...")
            news_items, pagination = self.fetch_news_page(page=page, limit=50)
            
            if not news_items:
                break
            
            # 过滤最近几天的新闻
            recent_news = []
            for item in news_items:
                try:
                    item_date = datetime.fromisoformat(item.date.replace('Z', '+00:00')).date()
                    if item_date >= cutoff_date:
                        recent_news.append(item)
                except:
                    # 如果日期解析失败，保留该新闻
                    recent_news.append(item)
            
            all_news.extend(recent_news)
            
            # 检查是否还有更多数据
            if not pagination.get("hasMore", False):
                break
            
            page += 1
            time.sleep(0.5)  # 避免请求过快
        
        logger.info(f"共获取 {len(all_news)} 条最近 {days} 天的新闻")
        return all_news
    
    def fetch_today_news(self, min_importance: int = 0) -> List[NewsItem]:
        """获取今天的新闻"""
        today = datetime.now().date()
        today_str = today.isoformat()
        
        all_today_news = []
        page = 1
        
        while page <= 10:  # 限制最多10页
            news_items, pagination = self.fetch_news_page(page=page, limit=50)
            
            if not news_items:
                break
            
            # 过滤今天的新闻
            today_news = []
            for item in news_items:
                if item.published_date == today_str and item.importance >= min_importance:
                    today_news.append(item)
            
            all_today_news.extend(today_news)
            
            # 如果当前页没有今天的新闻，且日期已经更早，可以提前结束
            if today_news:
                earliest_date = min(item.published_date for item in today_news)
                if earliest_date < today_str:
                    break
            
            if not pagination.get("hasMore", False):
                break
            
            page += 1
            time.sleep(0.3)
        
        # 按重要性排序
        all_today_news.sort(key=lambda x: x.importance, reverse=True)
        
        logger.info(f"获取今天新闻 {len(all_today_news)} 条 (重要性≥{min_importance})")
        return all_today_news
    
    def fetch_constellation_info(self, constellation_name: str) -> Optional[Dict]:
        """获取星座信息"""
        url = f"{self.base_url}/astro/constellation/{constellation_name}"
        return self._make_request(url)
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            news_items, _ = self.fetch_news_page(page=1, limit=1)
            return len(news_items) > 0
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False

class NewsDataManager:
    """新闻数据管理器"""
    
    def __init__(self, data_dir: str = "../data"):
        self.data_dir = os.path.abspath(data_dir)
        self.raw_dir = os.path.join(self.data_dir, "raw")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        self.archive_dir = os.path.join(self.data_dir, "archive")
        
        # 创建目录
        for directory in [self.raw_dir, self.processed_dir, self.archive_dir]:
            os.makedirs(directory, exist_ok=True)
        
        logger.info(f"数据目录: {self.data_dir}")
    
    def save_news_batch(self, news_items: List[NewsItem], 
                       batch_type: str = "daily") -> str:
        """
        保存新闻批次
        
        参数:
            news_items: 新闻列表
            batch_type: 批次类型 (daily/hourly/full)
        
        返回:
            保存的文件路径
        """
        if not news_items:
            logger.warning("没有新闻数据可保存")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 确定保存目录
        if batch_type == "daily":
            save_dir = os.path.join(self.raw_dir, date_str)
        else:
            save_dir = self.raw_dir
        
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名
        filename = f"news_{batch_type}_{timestamp}.json"
        filepath = os.path.join(save_dir, filename)
        
        # 准备数据
        data = {
            "metadata": {
                "batch_type": batch_type,
                "fetched_at": datetime.now().isoformat(),
                "item_count": len(news_items),
                "date_range": {
                    "start": min(item.published_date for item in news_items),
                    "end": max(item.published_date for item in news_items)
                } if news_items else {}
            },
            "news_items": [item.to_dict() for item in news_items]
        }
        
        # 保存文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存新闻批次到: {filepath} ({len(news_items)} 条)")
            return filepath
        except Exception as e:
            logger.error(f"保存新闻数据失败: {e}")
            return ""
    
    def load_news_batch(self, filepath: str) -> Tuple[List[NewsItem], Dict]:
        """加载新闻批次"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            news_items = []
            for item_data in data.get("news_items", []):
                try:
                    news_item = NewsItem.from_dict(item_data)
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"加载新闻项失败: {e}")
            
            metadata = data.get("metadata", {})
            logger.info(f"从 {filepath} 加载 {len(news_items)} 条新闻")
            return news_items, metadata
        except Exception as e:
            logger.error(f"加载新闻批次失败: {e}")
            return [], {}
    
    def get_today_data_file(self) -> Optional[str]:
        """获取今天的数据文件"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        today_dir = os.path.join(self.raw_dir, date_str)
        
        if not os.path.exists(today_dir):
            return None
        
        # 查找最新的文件
        files = [f for f in os.listdir(today_dir) if f.endswith('.json')]
        if not files:
            return None
        
        files.sort(reverse=True)
        return os.path.join(today_dir, files[0])
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """清理旧数据"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for root, dirs, files in os.walk(self.raw_dir):
            for dir_name in dirs:
                try:
                    dir_date = datetime.strptime(dir_name, "%Y-%m-%d")
                    if dir_date < cutoff_date:
                        dir_path = os.path.join(root, dir_name)
                        import shutil
                        shutil.rmtree(dir_path)
                        logger.info(f"删除旧数据目录: {dir_path}")
                except ValueError:
                    # 不是日期格式的目录，跳过
                    pass

def main():
    """主函数 - 测试API客户端"""
    print("卫星新闻API客户端测试")
    print("=" * 60)
    
    # 创建客户端
    client = SatelliteNewsAPIClient()
    
    # 测试连接
    print("1. 测试API连接...")
    if client.test_connection():
        print("   ✅ API连接正常")
    else:
        print("   ❌ API连接失败")
        return
    
    # 获取今天新闻
    print("\n2. 获取今天新闻...")
    today_news = client.fetch_today_news(min_importance=5)
    print(f"   获取到 {len(today_news)} 条重要新闻 (重要性≥5)")
    
    if today_news:
        print("\n   今天的重要新闻:")
        for i, item in enumerate(today_news[:5]):
            print(f"   [{i+1}] {item.title[:60]}...")
            print(f"       重要性: {item.importance}, 分类: {item.category}, 来源: {item.source}")
    
    # 获取最近3天新闻
    print("\n3. 获取最近3天新闻...")
    recent_news = client.fetch_all_recent_news(days=3, max_pages=5)
    print(f"   获取到 {len(recent_news)} 条最近3天新闻")
    
    # 按分类统计
    categories = {}
    for item in recent_news:
        category = item.category
        categories[category] = categories.get(category, 0) + 1
    
    print("\n   分类统计:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"     {category}: {count}条")
    
    # 保存数据
    print("\n4. 保存数据...")
    data_manager = NewsDataManager()
    
    if today_news:
        saved_file = data_manager.save_news_batch(today_news, "daily")
        if saved_file:
            print(f"   数据已保存: {saved_file}")
    
    print("\n" + "=" * 60)
    print("✅ API客户端测试完成！")
    print(f"\n下一步:")
    print("1. 创建新闻分析模块")
    print("2. 开发内容生成器")
    print("3. 集成飞书消息推送")

if __name__ == "__main__":
    main()