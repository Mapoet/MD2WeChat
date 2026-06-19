#!/usr/bin/env python3
"""
卫星新闻分析模块
负责新闻数据的分析、过滤和增强
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import statistics

@dataclass
class NewsStats:
    """新闻统计信息"""
    total_count: int = 0
    important_count: int = 0  # 重要性≥5
    categories: Dict[str, int] = None
    sources: Dict[str, int] = None
    tags: Dict[str, int] = None
    constellations: Dict[str, int] = None
    avg_importance: float = 0.0
    date_range: Tuple[str, str] = ("", "")
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = {}
        if self.sources is None:
            self.sources = {}
        if self.tags is None:
            self.tags = {}
        if self.constellations is None:
            self.constellations = {}
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    def summary(self) -> str:
        """生成文本摘要"""
        lines = []
        lines.append(f"📊 新闻统计摘要")
        lines.append(f"   总计: {self.total_count} 条新闻")
        lines.append(f"   重要新闻: {self.important_count} 条 (重要性≥5)")
        lines.append(f"   平均重要性: {self.avg_importance:.1f}/10")
        
        if self.categories:
            lines.append(f"\n📋 分类分布:")
            for cat, count in sorted(self.categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"   {cat}: {count} 条")
        
        if self.sources:
            lines.append(f"\n📰 来源分布:")
            for source, count in sorted(self.sources.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"   {source}: {count} 条")
        
        return "\n".join(lines)

class NewsAnalyzer:
    """新闻分析器"""
    
    def __init__(self, min_importance: int = 5):
        self.min_importance = min_importance
    
    def analyze_news_batch(self, news_items: List[Any]) -> NewsStats:
        """分析新闻批次"""
        if not news_items:
            return NewsStats()
        
        stats = NewsStats()
        stats.total_count = len(news_items)
        
        # 收集所有数据
        importances = []
        dates = []
        
        for item in news_items:
            # 处理不同类型的item（Dict或NewsItem）
            if hasattr(item, 'to_dict'):
                # 如果是NewsItem对象
                item_dict = item.to_dict()
            else:
                # 如果是字典
                item_dict = item
            
            # 重要性统计
            importance = item_dict.get('importance', 0)
            importances.append(importance)
            if importance >= self.min_importance:
                stats.important_count += 1
            
            # 分类统计
            category = item_dict.get('category', 'unknown')
            stats.categories[category] = stats.categories.get(category, 0) + 1
            
            # 来源统计
            source = item_dict.get('source', 'unknown')
            stats.sources[source] = stats.sources.get(source, 0) + 1
            
            # 标签统计
            for tag in item_dict.get('tags', []):
                stats.tags[tag] = stats.tags.get(tag, 0) + 1
            
            # 星座统计
            for constellation in item_dict.get('constellations', []):
                stats.constellations[constellation] = stats.constellations.get(constellation, 0) + 1
            
            # 日期范围
            date_str = item_dict.get('date', '')
            if date_str:
                dates.append(date_str)
        
        # 计算平均值
        if importances:
            stats.avg_importance = statistics.mean(importances)
        
        # 确定日期范围
        if dates:
            dates.sort()
            stats.date_range = (dates[0][:10], dates[-1][:10])
        
        return stats
    
    def filter_important_news(self, news_items: List[Any]) -> List[Any]:
        """过滤重要新闻"""
        important_items = []
        for item in news_items:
            if hasattr(item, 'to_dict'):
                item_dict = item.to_dict()
            else:
                item_dict = item
            
            if item_dict.get('importance', 0) >= self.min_importance:
                important_items.append(item)
        
        return important_items
    
    def group_by_category(self, news_items: List[Any]) -> Dict[str, List[Any]]:
        """按分类分组"""
        grouped = {}
        for item in news_items:
            if hasattr(item, 'to_dict'):
                item_dict = item.to_dict()
            else:
                item_dict = item
            
            category = item_dict.get('category', 'other')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)
        return grouped
    
    def get_top_news(self, news_items: List[Any], top_n: int = 10) -> List[Any]:
        """获取最重要的新闻"""
        # 创建一个包含重要性和原始item的列表
        items_with_importance = []
        for item in news_items:
            if hasattr(item, 'to_dict'):
                item_dict = item.to_dict()
            else:
                item_dict = item
            
            importance = item_dict.get('importance', 0)
            items_with_importance.append((importance, item))
        
        # 按重要性排序
        items_with_importance.sort(key=lambda x: x[0], reverse=True)
        
        # 返回原始item
        return [item for _, item in items_with_importance[:top_n]]
    
    def generate_daily_report(self, news_items: List[Dict]) -> Dict[str, Any]:
        """生成每日报告"""
        # 过滤今天的重要新闻
        today = datetime.now().strftime("%Y-%m-%d")
        today_news = [
            item for item in news_items 
            if item.get('date', '').startswith(today)
        ]
        
        important_today = self.filter_important_news(today_news)
        stats = self.analyze_news_batch(today_news)
        top_news = self.get_top_news(important_today, 5)
        
        # 按分类分组的重要新闻
        grouped_important = self.group_by_category(important_today)
        
        return {
            "date": today,
            "total_news": len(today_news),
            "important_news": len(important_today),
            "stats": stats.to_dict(),
            "top_news": top_news,
            "grouped_news": grouped_important
        }

class NewsEnhancer:
    """新闻内容增强器"""
    
    # 星座中文名称映射
    CONSTELLATION_NAMES = {
        "starlink": "星链 (Starlink)",
        "gps": "GPS",
        "beidou": "北斗",
        "galileo": "伽利略",
        "glonass": "格洛纳斯",
        "oneweb": "一网 (OneWeb)",
        "kuiper": "柯伊伯 (Kuiper)",
        "spire": "Spire",
        "planet": "行星实验室 (Planet)",
        "iridium": "铱星 (Iridium)",
        "hubble-network": "哈勃网络 (Hubble Network)",
        "bluewalker": "蓝行者 (Bluewalker)",
        "intuitive-machines": "直觉机器 (Intuitive Machines)",
        "oq-technology": "OQ Technology",
        "galaxia-mission-systems": "Galaxia任务系统",
        "airmo": "Airmo",
        "endurosat": "EnduroSat"
    }
    
    # 分类中文名称
    CATEGORY_NAMES = {
        "launch": "🚀 发射新闻",
        "business": "💰 商业动态",
        "technology": "🔬 技术突破",
        "policy": "📜 政策法规",
        "hardware": "🛠️ 硬件更新",
        "constellation": "🛰️ 星座动态",
        "other": "📰 其他新闻"
    }
    
    def enhance_news_item(self, item: Dict) -> Dict:
        """增强单个新闻项"""
        enhanced = item.copy()
        
        # 添加中文分类名称
        category = item.get('category', 'other')
        enhanced['category_cn'] = self.CATEGORY_NAMES.get(category, "📰 其他新闻")
        
        # 添加星座中文名称
        constellations_cn = []
        for constellation in item.get('constellations', []):
            cn_name = self.CONSTELLATION_NAMES.get(constellation, constellation)
            constellations_cn.append(cn_name)
        enhanced['constellations_cn'] = constellations_cn
        
        # 格式化日期
        date_str = item.get('date', '')
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                enhanced['date_formatted'] = dt.strftime("%Y年%m月%d日 %H:%M")
            except:
                enhanced['date_formatted'] = date_str[:10]
        
        # 生成简短摘要（如果原摘要太长）
        summary = item.get('summary', '')
        if len(summary) > 200:
            enhanced['short_summary'] = summary[:200] + "..."
        else:
            enhanced['short_summary'] = summary
        
        # 添加重要性图标
        importance = item.get('importance', 0)
        if importance >= 8:
            enhanced['importance_icon'] = "🔥"
        elif importance >= 6:
            enhanced['importance_icon'] = "⭐"
        elif importance >= 4:
            enhanced['importance_icon'] = "📌"
        else:
            enhanced['importance_icon'] = "📄"
        
        return enhanced
    
    def generate_news_card(self, item: Dict) -> Dict:
        """生成新闻卡片数据（用于飞书/HTML）"""
        enhanced = self.enhance_news_item(item)
        
        card = {
            "title": enhanced.get('title', ''),
            "url": enhanced.get('url', ''),
            "summary": enhanced.get('short_summary', ''),
            "category": enhanced.get('category_cn', ''),
            "importance": enhanced.get('importance', 0),
            "importance_icon": enhanced.get('importance_icon', ''),
            "source": enhanced.get('source', ''),
            "date": enhanced.get('date_formatted', ''),
            "tags": enhanced.get('tags', []),
            "constellations": enhanced.get('constellations_cn', [])
        }
        
        return card

def test_analyzer():
    """测试分析器"""
    print("测试新闻分析模块...")
    print("=" * 60)
    
    # 加载测试数据
    test_file = "data/daily/news_20260226_1320.json"
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        print("请先运行 fetch_daily.py 生成测试数据")
        return False
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        news_items = data.get('news_items', [])
        print(f"加载 {len(news_items)} 条测试新闻")
        
        # 创建分析器
        analyzer = NewsAnalyzer(min_importance=5)
        enhancer = NewsEnhancer()
        
        # 分析统计
        print("\n1. 新闻统计分析:")
        stats = analyzer.analyze_news_batch(news_items)
        print(stats.summary())
        
        # 过滤重要新闻
        print("\n2. 重要新闻过滤:")
        important_news = analyzer.filter_important_news(news_items)
        print(f"找到 {len(important_news)} 条重要新闻 (重要性≥5)")
        
        # 按分类分组
        print("\n3. 按分类分组:")
        grouped = analyzer.group_by_category(important_news)
        for category, items in grouped.items():
            print(f"  {category}: {len(items)} 条")
        
        # 获取最重要的新闻
        print("\n4. 最重要的5条新闻:")
        top_news = analyzer.get_top_news(important_news, 5)
        for i, item in enumerate(top_news):
            print(f"\n  [{i+1}] {item.get('title', '')[:60]}...")
            print(f"     重要性: {item.get('importance')}, 分类: {item.get('category')}")
        
        # 测试内容增强
        print("\n5. 内容增强测试:")
        if important_news:
            enhanced = enhancer.enhance_news_item(important_news[0])
            print(f"  原始分类: {important_news[0].get('category')}")
            print(f"  中文分类: {enhanced.get('category_cn')}")
            print(f"  重要性图标: {enhanced.get('importance_icon')}")
            
            # 生成新闻卡片
            card = enhancer.generate_news_card(important_news[0])
            print(f"\n  新闻卡片数据:")
            print(f"    标题: {card['title'][:50]}...")
            print(f"    分类: {card['category']}")
            print(f"    重要性: {card['importance_icon']} {card['importance']}")
        
        # 生成每日报告
        print("\n6. 每日报告生成:")
        report = analyzer.generate_daily_report(news_items)
        print(f"  日期: {report['date']}")
        print(f"  总新闻数: {report['total_news']}")
        print(f"  重要新闻数: {report['important_news']}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("卫星新闻分析模块测试")
    print("=" * 60)
    
    success = test_analyzer()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 分析模块测试成功！")
        print("\n下一步:")
        print("1. 集成到每日抓取流程中")
        print("2. 创建HTML报告生成器")
        print("3. 实现飞书消息卡片生成")
    else:
        print("❌ 分析模块测试失败")

if __name__ == "__main__":
    main()