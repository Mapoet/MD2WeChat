#!/usr/bin/env python3
"""
HTML报告生成器
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from jinja2 import Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("警告: Jinja2未安装，HTML生成功能将受限")

# 导入分析器
from src.analyzer import NewsAnalyzer, NewsEnhancer

class HTMLReportGenerator:
    """HTML报告生成器"""
    
    def __init__(self, template_dir: str = None, 
                 output_dir: str = None):
        # 设置默认路径
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "html")
        
        self.template_dir = os.path.abspath(template_dir)
        self.output_dir = os.path.abspath(output_dir)
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化Jinja2环境
        if JINJA2_AVAILABLE:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.env = None
            print("警告: Jinja2未安装，使用简单HTML生成")
        
        # 分析器和增强器
        self.analyzer = NewsAnalyzer(min_importance=5)
        self.enhancer = NewsEnhancer()
        
        # 分类图标映射
        self.category_icons = {
            "launch": "🚀",
            "business": "💰", 
            "technology": "🔬",
            "policy": "📜",
            "hardware": "🛠️",
            "constellation": "🛰️",
            "other": "📰"
        }
        
        # 分类中文名称
        self.category_names = {
            "launch": "发射新闻",
            "business": "商业动态", 
            "technology": "技术突破",
            "policy": "政策法规",
            "hardware": "硬件更新",
            "constellation": "星座动态",
            "other": "其他新闻"
        }
    
    def generate_daily_report(self, news_items: List[Dict]) -> str:
        """生成每日报告"""
        if not news_items:
            return ""
        
        # 分析新闻数据
        report_data = self.analyzer.generate_daily_report(news_items)
        
        # 增强新闻项
        enhanced_top_news = []
        for item in report_data.get("top_news", []):
            if hasattr(item, 'to_dict'):
                item_dict = item.to_dict()
            else:
                item_dict = item
            enhanced = self.enhancer.enhance_news_item(item_dict)
            enhanced_top_news.append(enhanced)
        
        enhanced_grouped_news = {}
        for category, items in report_data.get("grouped_news", {}).items():
            enhanced_items = []
            for item in items:
                if hasattr(item, 'to_dict'):
                    item_dict = item.to_dict()
                else:
                    item_dict = item
                enhanced = self.enhancer.enhance_news_item(item_dict)
                enhanced_items.append(enhanced)
            enhanced_grouped_news[category] = enhanced_items
        
        # 准备模板数据
        template_data = {
            "date": report_data["date"],
            "total_news": report_data["total_news"],
            "important_news": report_data["important_news"],
            "avg_importance": report_data["stats"].get("avg_importance", 0),
            "categories": report_data["stats"].get("categories", {}),
            "top_news": enhanced_top_news,
            "grouped_news": enhanced_grouped_news,
            "category_icons": self.category_icons,
            "category_names": self.category_names,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 渲染模板
        if self.env:
            template = self.env.get_template("daily_report.html")
            html_content = template.render(**template_data)
        else:
            # 简单HTML生成（备用方案）
            html_content = self._generate_simple_html(template_data)
        
        # 保存文件
        date_str = report_data["date"]
        filename = f"daily_report_{date_str}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML报告已生成: {filepath}")
        
        # 同时生成一个index.html（最新报告）
        index_file = os.path.join(self.output_dir, "index.html")
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"索引文件已更新: {index_file}")
        
        return filepath
    
    def generate_news_detail_page(self, news_item: Dict) -> str:
        """生成新闻详情页"""
        enhanced = self.enhancer.enhance_news_item(news_item)
        
        template_data = {
            "news": enhanced,
            "category_icons": self.category_icons,
            "category_names": self.category_names,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 这里可以创建详情页模板
        # 暂时先返回增强后的数据
        return json.dumps(enhanced, ensure_ascii=False, indent=2)
    
    def generate_archive_index(self, reports_dir: str = None) -> str:
        """生成归档索引页"""
        if reports_dir is None:
            reports_dir = self.output_dir
        
        # 查找所有报告文件
        report_files = []
        for filename in os.listdir(reports_dir):
            if filename.startswith("daily_report_") and filename.endswith(".html"):
                date_str = filename[13:-5]  # 提取日期
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    report_files.append({
                        "filename": filename,
                        "date": date_str,
                        "date_obj": date_obj
                    })
                except:
                    continue
        
        # 按日期排序
        report_files.sort(key=lambda x: x["date_obj"], reverse=True)
        
        # 生成简单的索引页
        html_content = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>卫星新闻报告归档</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                    background: #f5f5f5;
                }
                .header {
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 30px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .header h1 {
                    color: #1a237e;
                    margin-bottom: 10px;
                }
                .report-list {
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .report-item {
                    padding: 15px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .report-item:last-child {
                    border-bottom: none;
                }
                .report-item:hover {
                    background: #f8f9fa;
                }
                .report-date {
                    font-weight: bold;
                    color: #1a237e;
                }
                .report-link {
                    padding: 8px 16px;
                    background: #1a237e;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 0.9rem;
                }
                .report-link:hover {
                    background: #283593;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 0.9rem;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛰️ 卫星新闻报告归档</h1>
                <p>历史每日新闻报告</p>
            </div>
            
            <div class="report-list">
        """
        
        for report in report_files:
            html_content += f"""
                <div class="report-item">
                    <div class="report-date">{report['date']}</div>
                    <a href="{report['filename']}" class="report-link">查看报告</a>
                </div>
            """
        
        html_content += """
            </div>
            
            <div class="footer">
                <p>本页面由卫星新闻自动化系统生成 • 最后更新: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
        </body>
        </html>
        """
        
        # 保存归档索引
        archive_file = os.path.join(self.output_dir, "archive.html")
        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"归档索引已生成: {archive_file}")
        return archive_file
    
    def _generate_simple_html(self, data: Dict) -> str:
        """生成简单HTML（备用方案）"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>卫星新闻日报 - {data['date']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #1a237e; color: white; padding: 20px; border-radius: 10px; }}
                .news-item {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .category {{ font-weight: bold; color: #666; }}
                .importance {{ color: #e65100; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛰️ 卫星新闻日报 - {data['date']}</h1>
                <p>共 {data['total_news']} 条新闻，其中 {data['important_news']} 条重要新闻</p>
            </div>
            
            <h2>重要新闻 ({len(data['top_news'])}条)</h2>
        """
        
        for news in data['top_news']:
            html += f"""
            <div class="news-item">
                <div class="category">{news.get('category_cn', news.get('category', ''))}</div>
                <h3>{news.get('title', '')}</h3>
                <p>{news.get('short_summary', '')}</p>
                <div class="importance">重要性: {news.get('importance', 0)}/10</div>
                <div>来源: {news.get('source', '')}</div>
                <a href="{news.get('url', '#')}" target="_blank">阅读原文</a>
            </div>
            """
        
        html += f"""
            <hr>
            <p>生成时间: {data['generated_at']}</p>
        </body>
        </html>
        """
        
        return html

def test_generator():
    """测试HTML生成器"""
    print("测试HTML报告生成器...")
    print("=" * 60)
    
    # 加载测试数据
    test_file = "data/daily/news_20260226_1320.json"
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        return False
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        news_items = data.get('news_items', [])
        print(f"加载 {len(news_items)} 条测试新闻")
        
        # 创建生成器
        generator = HTMLReportGenerator()
        
        # 生成每日报告
        print("\n1. 生成每日HTML报告...")
        report_file = generator.generate_daily_report(news_items)
        
        if report_file and os.path.exists(report_file):
            print(f"✅ 报告文件已生成: {report_file}")
            
            # 检查文件大小
            file_size = os.path.getsize(report_file)
            print(f"   文件大小: {file_size:,} 字节")
            
            # 预览文件内容
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read(500)
                print(f"\n   内容预览:")
                print(f"   {content[:200]}...")
        else:
            print("❌ 报告生成失败")
            return False
        
        # 生成归档索引
        print("\n2. 生成归档索引...")
        archive_file = generator.generate_archive_index()
        
        if archive_file and os.path.exists(archive_file):
            print(f"✅ 归档索引已生成: {archive_file}")
        else:
            print("❌ 归档索引生成失败")
        
        # 测试新闻详情生成
        print("\n3. 测试新闻详情生成...")
        if news_items:
            detail_json = generator.generate_news_detail_page(news_items[0])
            print(f"   新闻详情JSON (长度: {len(detail_json)} 字符)")
            print(f"   预览: {detail_json[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("HTML报告生成器测试")
    print("=" * 60)
    
    success = test_generator()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ HTML生成器测试成功！")
        print("\n生成的报告位于:")
        print(f"  {os.path.abspath('../output/html/')}")
        print("\n下一步:")
        print("1. 设置自动发布到网站目录")
        print("2. 创建飞书消息卡片生成器")
        print("3. 实现完整的自动化流程")
    else:
        print("❌ HTML生成器测试失败")

if __name__ == "__main__":
    main()