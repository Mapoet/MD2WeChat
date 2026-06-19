#!/usr/bin/env python3
"""
多源卫星新闻抓取器
从多个来源获取GNSS、卫星、气象相关新闻
支持 IGS、GNSS 管理局、EUMETSAT、NOAA 等权威信源
信源配置见 config/sources.yaml，新增信源无需修改代码
"""

import os
import sys
import json
from typing import Optional, Dict, List

import requests
import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


class NewsFetcher:
    def __init__(self, config_path: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # 解析项目根目录
        self.project_dir = Path(__file__).resolve().parent.parent
        config_path = config_path or self.project_dir / "config" / "sources.yaml"

        # 加载信源配置
        self.sources = self._load_sources(config_path)

        # 关键词过滤（GNSS/卫星/气象相关）
        self.keywords = [
            'gps', 'gnss', 'galileo', 'glonass', 'beidou', 'qzss', 'navic',
            'satellite navigation', 'positioning', 'timing',
            'satellite', 'spacecraft', 'launch', 'orbit', 'constellation',
            'starlink', 'oneweb', 'spacex', 'rocket', 'space station',
            'weather', 'meteorological', 'climate', 'atmosphere', 'noaa',
            'eumetsat', 'metop', 'goes', 'himawari', 'fengyun',
            'nasa', 'esa', 'jaxa', 'isro', 'roscosmos', 'cnsa',
            'spacex', 'blue origin', 'virgin galactic', 'rocket lab',
            'remote sensing', 'earth observation', 'telemetry', 'payload',
            'propulsion', 'antenna', 'sensor', 'imaging', 'spectrometer',
            'igs', 'rinex', 'geodesy',  # IGS 相关
        ]

    def _load_sources(self, config_path: Path) -> dict:
        """从 YAML 加载信源配置，若无则使用内置默认"""
        if yaml is None:
            print("⚠️ PyYAML 未安装，使用内置信源。安装: pip install pyyaml")
            return self._default_sources()

        path = Path(config_path)
        if not path.exists():
            print(f"⚠️ 配置文件不存在: {path}，使用内置信源")
            return self._default_sources()

        try:
            with open(path, encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            return cfg or self._default_sources()
        except Exception as e:
            print(f"⚠️ 加载配置失败: {e}，使用内置信源")
            return self._default_sources()

    def _default_sources(self) -> dict:
        """内置默认信源（与旧版兼容）"""
        return {
            'rss': {
                'nasa': {'url': 'https://www.nasa.gov/rss/dyn/breaking_news.rss', 'enabled': True},
                'esa': {'url': 'https://www.esa.int/rssfeed/Our_Activities', 'enabled': True},
                'space_news': {'url': 'https://spacenews.com/feed/', 'enabled': True},
                'space_com': {'url': 'https://www.space.com/feeds/all', 'enabled': True},
                'gps_world': {'url': 'https://www.gpsworld.com/feed/', 'enabled': True},
                'inside_gnss': {'url': 'https://insidegnss.com/feed/', 'enabled': True},
            },
            'api': {
                'satellitemap': {
                    'url': 'https://api.satellitemap.space/news',
                    'enabled': True,
                    'headers': {'X-API-Key': 'development-key'},
                    'params': {'limit': 100, 'hours': 24},  # 增加到100条限制
                },
            },
            'scrape': {
                'noaa': {'url': 'https://www.noaa.gov/news', 'base_url': 'https://www.noaa.gov', 'enabled': True},
                'eumetsat': {'url': 'https://www.eumetsat.int/latest-news', 'base_url': 'https://www.eumetsat.int', 'enabled': True},
                'jaxa': {'url': 'https://global.jaxa.jp/news/', 'base_url': 'https://global.jaxa.jp', 'enabled': True},
            },
        }

    def fetch_rss(self, url: str, source_name: str, skip_keyword_filter: bool = False) -> list:
        """从RSS源获取新闻"""
        try:
            print(f"  获取RSS: {source_name}")
            feed = feedparser.parse(url)

            articles = []
            for entry in feed.entries[:15]:
                if hasattr(entry, 'published_parsed'):
                    pub_time = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_time = datetime(*entry.updated_parsed[:6])
                else:
                    pub_time = datetime.now() - timedelta(hours=1)

                if datetime.now() - pub_time > timedelta(hours=72):
                    continue

                title = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                content = title + ' ' + summary

                if not skip_keyword_filter and not self.contains_keywords(content):
                    continue

                article = {
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'published': pub_time.isoformat(),
                    'source': source_name,
                    'source_type': 'rss',
                    'category': self.categorize_article(content)
                }
                articles.append(article)

            return articles

        except Exception as e:
            print(f"  获取RSS失败 {source_name}: {e}")
            return []

    def fetch_api(self, url: str, source_name: str, headers: Optional[Dict] = None,
                  params: Optional[Dict] = None) -> List[dict]:
        """从API获取新闻"""
        try:
            print(f"  获取API: {source_name}")
            headers = headers or {}
            params = params or {}

            if source_name == 'satellitemap':
                headers.setdefault('X-API-Key', 'development-key')
                params.setdefault('limit', 100)  # 增加到100条限制
                params.setdefault('hours', 24)

            response = self.session.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data.get('items', []):
                title = item.get('title', '').lower()
                summary = item.get('summary', '').lower()
                content = title + ' ' + summary

                if not self.contains_keywords(content):
                    continue

                article = {
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'summary': item.get('summary', ''),
                    'published': item.get('published_at', ''),
                    'source': source_name,
                    'source_type': 'api',
                    'importance': item.get('importance', 5),
                    'category': item.get('category', 'other')
                }
                articles.append(article)

            return articles

        except Exception as e:
            print(f"  获取API失败 {source_name}: {e}")
            return []

    def fetch_scrape(self, url: str, source_name: str, base_url: str = '',
                    selectors: Optional[List[str]] = None, limit: int = 10,
                    skip_keyword_filter: bool = False) -> List[dict]:
        """通过网页爬取获取新闻（支持配置化选择器）"""
        try:
            print(f"  爬取网页: {source_name}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            base_url = base_url or url.rsplit('/', 1)[0]
            if not base_url.startswith('http'):
                base_url = 'https://' + base_url.replace('https://', '').split('/')[0]

            selectors = selectors or [
                'article a', 'main a[href*="/news/"]', 'h3 a', 'h4 a',
                '.news-item a', '.article-preview a',
            ]

            seen_urls = set()
            articles = []

            for sel in selectors:
                if len(articles) >= limit:
                    break
                try:
                    for elem in soup.select(sel)[:limit * 2]:
                        link = elem.get('href')
                        if not link or link.startswith('#') or link.startswith('mailto:'):
                            continue
                        if not link.startswith('http'):
                            link = base_url.rstrip('/') + '/' + link.lstrip('/')
                        if link in seen_urls:
                            continue

                        title = elem.get_text(strip=True)
                        if len(title) < 10 or len(title) > 300:
                            continue
                        if not skip_keyword_filter and not self.contains_keywords(title.lower()):
                            continue

                        seen_urls.add(link)
                        articles.append({
                            'title': title,
                            'url': link,
                            'summary': '',
                            'published': datetime.now().isoformat(),
                            'source': source_name,
                            'source_type': 'scrape',
                            'category': self.categorize_article(title)
                        })
                        if len(articles) >= limit:
                            break
                except Exception:
                    continue

            return articles[:limit]

        except Exception as e:
            print(f"  爬取失败 {source_name}: {e}")
            return []

    def contains_keywords(self, text: str) -> bool:
        """检查文本是否包含关键词"""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)

    def categorize_article(self, text: str) -> str:
        """根据内容分类文章"""
        text_lower = text.lower()
        if any(w in text_lower for w in ['gps', 'gnss', 'galileo', 'glonass', 'beidou', 'navigation']):
            return 'gnss'
        if any(w in text_lower for w in ['weather', 'meteorological', 'climate', 'noaa', 'eumetsat']):
            return 'meteorology'
        if any(w in text_lower for w in ['launch', 'rocket', 'spacex', 'starlink']):
            return 'launch'
        if any(w in text_lower for w in ['satellite', 'spacecraft', 'orbit', 'constellation']):
            return 'satellite'
        if any(w in text_lower for w in ['research', 'study', 'paper', 'scientific']):
            return 'research'
        if any(w in text_lower for w in ['business', 'investment', 'market', 'contract']):
            return 'business'
        return 'other'

    def fetch_all_news(self) -> list:
        """从所有已启用信源获取新闻"""
        print("📥 开始从多个源获取卫星新闻...")
        raw = self.sources

        def get_url(v):
            if isinstance(v, str):
                return v
            return v.get('url', '') if isinstance(v, dict) else ''

        all_articles = []

        # RSS
        print("\n🔗 RSS源:")
        rss_block = raw.get('rss', {})
        for name, cfg in rss_block.items():
            if isinstance(cfg, dict) and not cfg.get('enabled', True):
                continue
            url = get_url(cfg) if isinstance(cfg, dict) else cfg
            skip_kw = isinstance(cfg, dict) and cfg.get('skip_keyword_filter', False)
            arts = self.fetch_rss(url, name, skip_keyword_filter=skip_kw)
            all_articles.extend(arts)
            time.sleep(1)

        # API
        print("\n🔗 API源:")
        api_block = raw.get('api', {})
        for name, cfg in api_block.items():
            if isinstance(cfg, dict) and not cfg.get('enabled', True):
                continue
            url = get_url(cfg) if isinstance(cfg, dict) else cfg
            hd = cfg.get('headers', {}) if isinstance(cfg, dict) else {}
            pr = cfg.get('params', {}) if isinstance(cfg, dict) else {}
            arts = self.fetch_api(url, name, headers=hd, params=pr)
            all_articles.extend(arts)
            time.sleep(1)

        # Scrape
        print("\n🔗 网页源:")
        scrape_block = raw.get('scrape', {})
        for name, cfg in scrape_block.items():
            if isinstance(cfg, dict) and not cfg.get('enabled', True):
                continue
            url = get_url(cfg) if isinstance(cfg, dict) else cfg
            base = cfg.get('base_url', '') if isinstance(cfg, dict) else ''
            sel = cfg.get('selectors', []) if isinstance(cfg, dict) else []
            lim = cfg.get('limit', 10) if isinstance(cfg, dict) else 10
            skip_kw = isinstance(cfg, dict) and cfg.get('skip_keyword_filter', False)
            arts = self.fetch_scrape(url, name, base_url=base, selectors=sel, limit=lim,
                                     skip_keyword_filter=skip_kw)
            all_articles.extend(arts)
            time.sleep(2)

        # 去重
        unique_articles = []
        seen_titles = set()
        for article in all_articles:
            title_key = re.sub(r'[^\w\s]', '', article['title'].lower()).strip()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_articles.append(article)

        print(f"\n✅ 获取完成: 共 {len(unique_articles)} 篇相关新闻")
        unique_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
        return unique_articles

    def save_news(self, articles: list):
        """保存新闻数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        data_dir = self.project_dir / "data" / "news"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        raw_file = raw_dir / f"news_{timestamp}.json"
        latest_file = data_dir / "latest_news.json"

        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'fetched_at': datetime.now().isoformat(),
                    'article_count': len(articles),
                    'sources': list(set(a['source'] for a in articles))
                },
                'articles': articles
            }, f, ensure_ascii=False, indent=2)

        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {'fetched_at': datetime.now().isoformat(), 'article_count': len(articles)},
                'articles': articles  # 移除50条限制，保存所有文章
            }, f, ensure_ascii=False, indent=2)

        print(f"💾 新闻数据已保存:")
        print(f"   原始数据: {raw_file}")
        print(f"   最新数据: {latest_file}")
        return str(raw_file), str(latest_file)


def main():
    """主函数"""
    print("=" * 80)
    print("多源卫星新闻抓取器")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    fetcher = NewsFetcher()

    try:
        articles = fetcher.fetch_all_news()

        if not articles:
            print("\n⚠️ 未获取到相关新闻")
            return None

        raw_file, latest_file = fetcher.save_news(articles)

        print("\n📋 新闻摘要:")
        print("-" * 40)
        categories = {}
        sources = {}
        for article in articles[:15]:
            categories[article.get('category', 'other')] = categories.get(article.get('category', 'other'), 0) + 1
            sources[article.get('source', 'unknown')] = sources.get(article.get('source', 'unknown'), 0) + 1

        print("分类统计:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}篇")
        print("\n来源统计:")
        for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"  {src}: {count}篇")
        print("\n最新新闻:")
        for i, article in enumerate(articles[:5], 1):
            title = article['title'][:57] + "..." if len(article['title']) > 60 else article['title']
            print(f"  {i}. {title}")
            print(f"     来源: {article['source']} | 分类: {article.get('category', 'N/A')}")

        return latest_file

    except Exception as e:
        print(f"\n❌ 抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
