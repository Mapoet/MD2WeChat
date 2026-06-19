#!/usr/bin/env python3
"""
美观的HTML报告渲染器
将Markdown转换为专业美观的HTML页面
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
import re
import markdown
from bs4 import BeautifulSoup

class HTMLRenderer:
    def __init__(self):
        # CSS样式
        self.styles = """
            /* 基础样式 */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            
            /* 头部样式 */
            .header {
                background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
                color: white;
                padding: 40px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }
            
            .header::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                background-size: 50px 50px;
                animation: float 20s linear infinite;
            }
            
            @keyframes float {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .header h1 {
                font-size: 2.8rem;
                margin-bottom: 10px;
                position: relative;
                z-index: 1;
                text-shadow: 0 2px 10px rgba(0,0,0,0.3);
            }
            
            .header .subtitle {
                font-size: 1.2rem;
                opacity: 0.9;
                position: relative;
                z-index: 1;
            }
            
            .header .meta {
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-top: 20px;
                flex-wrap: wrap;
                position: relative;
                z-index: 1;
            }
            
            .meta-item {
                background: rgba(255,255,255,0.1);
                padding: 10px 20px;
                border-radius: 50px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }
            
            /* 内容区域 */
            .content {
                padding: 40px;
            }
            
            /* 章节样式 */
            .section {
                margin-bottom: 40px;
                padding-bottom: 30px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .section:last-child {
                border-bottom: none;
            }
            
            .section-title {
                font-size: 1.8rem;
                color: #1a237e;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #3f51b5;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .section-title::before {
                content: '';
                width: 10px;
                height: 30px;
                background: #3f51b5;
                border-radius: 5px;
            }
            
            /* 卡片样式 */
            .card {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                border-left: 5px solid #3f51b5;
                transition: transform 0.3s, box-shadow 0.3s;
            }
            
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .card-title {
                font-size: 1.3rem;
                color: #1a237e;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            /* 统计卡片 */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                transition: transform 0.3s;
            }
            
            .stat-card:hover {
                transform: scale(1.05);
            }
            
            .stat-number {
                font-size: 2.5rem;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            .stat-label {
                font-size: 1rem;
                opacity: 0.9;
            }
            
            /* 列表样式 */
            .list {
                list-style: none;
            }
            
            .list-item {
                padding: 15px;
                margin-bottom: 10px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 4px solid #3f51b5;
                transition: background 0.3s;
            }
            
            .list-item:hover {
                background: #e8eaf6;
            }
            
            .list-item .icon {
                margin-right: 10px;
                font-size: 1.2rem;
            }
            
            /* 表格样式 */
            .table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            .table th {
                background: #3f51b5;
                color: white;
                padding: 15px;
                text-align: left;
            }
            
            .table td {
                padding: 15px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .table tr:hover {
                background: #f5f5f5;
            }
            
            /* 标签样式 */
            .tag {
                display: inline-block;
                padding: 5px 15px;
                background: #e8eaf6;
                color: #3f51b5;
                border-radius: 20px;
                font-size: 0.9rem;
                margin: 5px;
                border: 1px solid #c5cae9;
            }
            
            .tag.gnss { background: #e3f2fd; color: #1565c0; border-color: #bbdefb; }
            .tag.meteorology { background: #e8f5e8; color: #2e7d32; border-color: #c8e6c9; }
            .tag.launch { background: #fff3e0; color: #ef6c00; border-color: #ffe0b2; }
            .tag.research { background: #f3e5f5; color: #7b1fa2; border-color: #e1bee7; }
            
            /* 重要性指示器 */
            .importance {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.9rem;
                font-weight: bold;
            }
            
            .importance.high { background: #ffebee; color: #c62828; }
            .importance.medium { background: #fff3e0; color: #ef6c00; }
            .importance.low { background: #e8f5e8; color: #2e7d32; }
            
            /* 图表容器 */
            .chart-container {
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin: 20px 0;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            /* 页脚 */
            .footer {
                background: #1a237e;
                color: white;
                padding: 30px;
                text-align: center;
                margin-top: 40px;
            }
            
            .footer p {
                margin: 10px 0;
                opacity: 0.8;
            }
            
            /* 响应式设计 */
            @media (max-width: 768px) {
                .header h1 {
                    font-size: 2rem;
                }
                
                .content {
                    padding: 20px;
                }
                
                .stats-grid {
                    grid-template-columns: 1fr;
                }
                
                .meta {
                    flex-direction: column;
                    align-items: center;
                }
                
                .meta-item {
                    width: 100%;
                    text-align: center;
                }
            }
            
            /* 动画 */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .fade-in {
                animation: fadeIn 0.6s ease-out;
            }
            
            /* 代码块样式 */
            pre {
                background: #263238;
                color: #eceff1;
                padding: 20px;
                border-radius: 10px;
                overflow-x: auto;
                margin: 20px 0;
                font-family: 'Consolas', monospace;
            }
            
            code {
                background: #f5f5f5;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                color: #c62828;
            }
            
            /* 引用样式 */
            blockquote {
                border-left: 4px solid #3f51b5;
                padding: 15px 20px;
                background: #f8f9fa;
                margin: 20px 0;
                border-radius: 0 10px 10px 0;
                font-style: italic;
            }
            
            /* 链接样式 */
            a {
                color: #3f51b5;
                text-decoration: none;
                transition: color 0.3s;
            }
            
            a:hover {
                color: #1a237e;
                text-decoration: underline;
            }
            
            /* Mermaid：由 mermaid 代码块提升为 div 后渲染 */
            .mermaid {
                margin: 24px auto;
                padding: 16px;
                max-width: 100%;
                overflow-x: auto;
                text-align: center;
                background: #fafafa;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """
        
        # JavaScript（纯 JS，勿再包一层 <script>，否则会被写进 script 标签文本）
        self.scripts = """
            // 页面加载动画
            document.addEventListener('DOMContentLoaded', function() {
                // 为所有卡片添加延迟动画
                const cards = document.querySelectorAll('.card, .stat-card, .list-item');
                cards.forEach((card, index) => {
                    card.style.animationDelay = `${index * 0.1}s`;
                    card.classList.add('fade-in');
                });
                
                // 图表数据（示例）
                const categoryData = {
                    labels: ['GNSS', '气象', '发射', '卫星', '研究', '商业'],
                    datasets: [{
                        data: [25, 20, 15, 15, 15, 10],
                        backgroundColor: [
                            '#3f51b5', '#4caf50', '#ff9800', 
                            '#9c27b0', '#2196f3', '#ff5722'
                        ]
                    }]
                };
                
                // 可以在这里添加Chart.js等图表库
                console.log('页面加载完成，可以初始化图表');
                
                // 平滑滚动
                document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                    anchor.addEventListener('click', function(e) {
                        e.preventDefault();
                        const targetId = this.getAttribute('href');
                        if(targetId === '#') return;
                        
                        const targetElement = document.querySelector(targetId);
                        if(targetElement) {
                            window.scrollTo({
                                top: targetElement.offsetTop - 80,
                                behavior: 'smooth'
                            });
                        }
                    });
                });
            });
            
            // 打印功能
            function printReport() {
                window.print();
            }
            
            // 导出功能
            function exportPDF() {
                alert('PDF导出功能需要服务器端支持');
                // 实际实现需要服务器端PDF生成
            }
            
            // 分享功能
            function shareReport() {
                if(navigator.share) {
                    navigator.share({
                        title: document.title,
                        text: '卫星新闻分析报告',
                        url: window.location.href
                    });
                } else {
                    alert('分享链接已复制到剪贴板');
                    navigator.clipboard.writeText(window.location.href);
                }
            }
        """
    
    def _replace_mermaid_code_blocks(self, fragment) -> None:
        """将 codehilite 产出的 mermaid 代码块替换为 div.mermaid，供 mermaid.js 渲染。"""
        from bs4 import NavigableString

        for pre in list(fragment.find_all("pre")):
            code = pre.find("code")
            if not code:
                continue
            classes = code.get("class") or []
            if not any(
                c == "language-mermaid" or (isinstance(c, str) and "mermaid" in c)
                for c in classes
            ):
                continue
            raw = (code.get_text() or "").strip()
            if not raw:
                pre.decompose()
                continue
            div = fragment.new_tag("div", attrs={"class": "mermaid"})
            div.append(NavigableString(raw))
            pre.replace_with(div)

    def load_markdown(self, markdown_file):
        """加载Markdown文件"""
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ 加载Markdown文件失败: {e}")
            return ""
    
    def convert_markdown_to_html(self, markdown_content):
        """将Markdown转换为HTML"""
        # 使用markdown库转换
        html = markdown.markdown(
            markdown_content,
            extensions=[
                'extra',  # 支持表格、脚注等
                'codehilite',  # 代码高亮
                'toc',  # 目录
                'nl2br',  # 换行转换
                'sane_lists'  # 更好的列表支持
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight'
                },
                'toc': {
                    'title': '目录',
                    'permalink': False
                }
            }
        )
        
        return html
    
    def enhance_html(self, html_content, metadata=None):
        """增强HTML内容，添加样式和交互"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 添加容器
        container = soup.new_tag('div', attrs={'class': 'container'})
        
        # 创建头部
        header = soup.new_tag('div', attrs={'class': 'header'})
        
        title = soup.new_tag('h1')
        title.string = "🛰️ 卫星新闻专业分析报告"
        header.append(title)
        
        subtitle = soup.new_tag('div', attrs={'class': 'subtitle'})
        subtitle.string = "GNSS · 卫星 · 气象 · 深度分析"
        header.append(subtitle)
        
        # 元数据区域
        if metadata:
            meta_div = soup.new_tag('div', attrs={'class': 'meta'})
            
            meta_items = [
                f"📅 报告时间: {metadata.get('date', datetime.now().strftime('%Y-%m-%d'))}",
                f"📊 新闻总数: {metadata.get('total_articles', 'N/A')}篇",
                f"⏱️ 分析范围: {metadata.get('time_range', '过去24小时')}",
                f"🔍 数据版本: {metadata.get('version', 'v1.0')}"
            ]
            
            for item in meta_items:
                meta_item = soup.new_tag('div', attrs={'class': 'meta-item'})
                meta_item.string = item
                meta_div.append(meta_item)
            
            header.append(meta_div)
        
        container.append(header)
        
        # 创建内容区域
        content = soup.new_tag('div', attrs={'class': 'content'})
        
        # 添加操作按钮
        actions = soup.new_tag('div', attrs={
            'class': 'actions',
            'style': 'display: flex; gap: 10px; margin-bottom: 30px; flex-wrap: wrap;'
        })
        
        button_styles = {
            'print': {'bg': '#3f51b5', 'icon': '🖨️'},
            'export': {'bg': '#4caf50', 'icon': '📥'},
            'share': {'bg': '#ff9800', 'icon': '🔗'}
        }
        
        for btn_id, style in button_styles.items():
            button = soup.new_tag('button', attrs={
                'class': 'action-btn',
                'style': f'background: {style["bg"]}; color: white; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 1rem;',
                'onclick': f'{btn_id}Report()'
            })
            button.string = f'{style["icon"]} {btn_id.capitalize()}'
            actions.append(button)
        
        content.append(actions)
        
        # 处理现有的HTML内容
        body_content = BeautifulSoup(html_content, 'html.parser')
        
        self._replace_mermaid_code_blocks(body_content)
        
        # 标题层次：逐级略减小，避免 h3/h4 与正文对比突兀
        for h1 in body_content.find_all('h1'):
            h1['class'] = h1.get('class', []) + ['section-title']
            h1['style'] = (
                'font-size: 1.75rem; font-weight: 700; color: #1a237e; '
                'margin-top: 36px; margin-bottom: 12px; padding-bottom: 8px; '
                'border-bottom: 2px solid #e8eaf6;'
            )
        
        for h2 in body_content.find_all('h2'):
            h2['class'] = h2.get('class', []) + ['section-title']
            h2['style'] = (
                'font-size: 1.45rem; font-weight: 600; color: #283593; '
                'margin-top: 28px; margin-bottom: 10px; padding-bottom: 6px; '
                'border-bottom: 2px solid #e8eaf6;'
            )
        
        for h3 in body_content.find_all('h3'):
            h3['class'] = h3.get('class', []) + ['card-title']
            h3['style'] = (
                'font-size: 1.15rem; font-weight: 600; color: #3949ab; '
                'margin-top: 18px; margin-bottom: 8px;'
            )
        
        for h4 in body_content.find_all('h4'):
            h4['style'] = (
                'font-size: 1.05rem; font-weight: 600; color: #455a64; '
                'margin-top: 14px; margin-bottom: 6px;'
            )
        
        for h5 in body_content.find_all('h5'):
            h5['style'] = (
                'font-size: 1rem; font-weight: 600; color: #546e7a; '
                'margin-top: 12px; margin-bottom: 4px;'
            )
        
        for h6 in body_content.find_all('h6'):
            h6['style'] = (
                'font-size: 0.95rem; font-weight: 600; color: #607d8b; '
                'margin-top: 10px; margin-bottom: 4px;'
            )
        
        # 增强列表
        for ul in body_content.find_all('ul'):
            ul['class'] = ul.get('class', []) + ['list']
            for li in ul.find_all('li'):
                li['class'] = li.get('class', []) + ['list-item']
        
        # 增强表格
        for table in body_content.find_all('table'):
            table['class'] = table.get('class', []) + ['table']
        
        # 增强代码块
        for pre in body_content.find_all('pre'):
            pre['class'] = pre.get('class', []) + ['code-block']
        
        # 将处理后的内容添加到内容区域
        content.append(body_content)
        container.append(content)
        
        # 创建页脚
        footer = soup.new_tag('div', attrs={'class': 'footer'})
        
        footer_content = """
        <p>🛰️ 卫星新闻专业分析系统</p>
        <p>生成时间: {}</p>
        <p>数据来源: 多源新闻聚合 | 分析方法: 专业分析引擎</p>
        <p>© 2026 Mapoet助手 | 仅供专业参考</p>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        footer.append(BeautifulSoup(footer_content, 'html.parser'))
        container.append(footer)
        
        # 创建完整的HTML文档
        html_doc = soup.new_tag('html')
        head = soup.new_tag('head')
        
        # 添加meta标签
        meta_charset = soup.new_tag('meta', charset='UTF-8')
        meta_viewport = soup.new_tag('meta', attrs={
            'name': 'viewport',
            'content': 'width=device-width, initial-scale=1.0'
        })
        meta_desc = soup.new_tag('meta', attrs={
            'name': 'description',
            'content': '卫星新闻专业分析报告 - GNSS、卫星、气象领域深度分析'
        })
        
        title = soup.new_tag('title')
        title.string = '卫星新闻专业分析报告'
        
        # 添加样式
        style = soup.new_tag('style')
        style.string = self.styles
        
        head.extend([meta_charset, meta_viewport, meta_desc, title, style])
        html_doc.append(head)
        
        # 添加body
        body = soup.new_tag('body')
        body.append(container)
        
        # 页面交互脚本
        script = soup.new_tag('script')
        script.string = self.scripts
        body.append(script)
        
        # Mermaid：在正文之后加载，startOnLoad 扫描 div.mermaid
        mermaid_src = soup.new_tag(
            'script',
            src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js',
        )
        body.append(mermaid_src)
        mermaid_boot = soup.new_tag('script')
        mermaid_boot.string = """
if (typeof mermaid !== 'undefined') {
  mermaid.initialize({
    startOnLoad: true,
    theme: 'base',
    themeVariables: {
      darkMode: false,
      background: '#fafbff',
      primaryColor: '#c5cae9',
      primaryTextColor: '#1a237e',
      primaryBorderColor: '#3949ab',
      secondaryColor: '#e1bee7',
      secondaryTextColor: '#4a148c',
      secondaryBorderColor: '#7b1fa2',
      tertiaryColor: '#ffcc80',
      tertiaryTextColor: '#bf360c',
      tertiaryBorderColor: '#f57c00',
      lineColor: '#5c6bc0',
      textColor: '#263238',
      mainBkg: '#e8eaf6',
      nodeBorder: '#3949ab',
      clusterBkg: '#f3e5f5',
      titleColor: '#1a237e',
      edgeLabelBackground: '#ffffff'
    },
    securityLevel: 'loose',
    flowchart: { htmlLabels: false, useMaxWidth: true, curve: 'basis',
      padding: 12, nodeSpacing: 50, rankSpacing: 50 }
  });
}
""".strip()
        body.append(mermaid_boot)
        
        html_doc.append(body)
        
        return str(html_doc)
    
    def save_html(self, html_content, output_dir='output/html'):
        """保存HTML文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # 创建目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("/var/www/html/satellite-news", exist_ok=True)
        
        # 保存HTML文件
        html_file = f"{output_dir}/report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 保存为最新报告
        latest_html = f"{output_dir}/latest_report.html"
        with open(latest_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 复制到网站目录
        web_file = "/var/www/html/satellite-news/index.html"
        with open(web_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 同时保存一个简化版本
        simple_html = "/var/www/html/satellite-news/simple.html"
        simple_content = self.create_simple_version(html_content)
        with open(simple_html, 'w', encoding='utf-8') as f:
            f.write(simple_content)
        
        src_assets = os.path.join(output_dir, "assets")
        web_assets_dir = "/var/www/html/satellite-news/assets"
        if os.path.isdir(src_assets):
            os.makedirs(web_assets_dir, exist_ok=True)
            for name in os.listdir(src_assets):
                src_f = os.path.join(src_assets, name)
                if os.path.isfile(src_f):
                    shutil.copy2(src_f, os.path.join(web_assets_dir, name))
        
        print(f"💾 HTML报告已保存:")
        print(f"   HTML文件: {html_file}")
        print(f"   最新HTML: {latest_html}")
        print(f"   网站主页面: {web_file}")
        print(f"   简化版本: {simple_html}")
        
        return html_file, web_file
    
    def create_simple_version(self, html_content):
        """创建简化版本"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除复杂的样式和脚本
        for tag in soup.find_all(['style', 'script']):
            tag.decompose()
        
        # 简化布局
        container = soup.find('div', class_='container')
        if container:
            container['style'] = 'max-width: 800px; margin: 0 auto; padding: 20px;'
        
        # 简化头部
        header = soup.find('div', class_='header')
        if header:
            header['style'] = 'background: #1a237e; color: white; padding: 20px; text-align: center;'
        
        # 简化卡片
        for card in soup.find_all(class_='card'):
            card['style'] = 'background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 3px solid #3f51b5;'
        
        return str(soup)

def main(markdown_file):
    """主函数"""
    print("=" * 80)
    print("HTML报告渲染器")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    renderer = HTMLRenderer()
    
    try:
        # 加载Markdown文件
        markdown_content = renderer.load_markdown(markdown_file)
        
        if not markdown_content:
            print("❌ 无Markdown内容可渲染")
            return None
        
        print(f"📄 加载Markdown文件: {markdown_file}")
        print(f"📊 文件大小: {len(markdown_content.encode('utf-8')) / 1024:.1f}KB")
        
        # 提取元数据
        metadata = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'version': 'v1.0',
            'time_range': '过去24小时'
        }
        
        # 从Markdown中提取文章总数
        total_match = re.search(r'新闻总数.*?(\d+)篇', markdown_content)
        if total_match:
            metadata['total_articles'] = total_match.group(1)
        
        # 转换为HTML
        print("🎨 转换为HTML并增强样式...")
        html_content = renderer.convert_markdown_to_html(markdown_content)
        enhanced_html = renderer.enhance_html(html_content, metadata)
        
        # 保存HTML文件
        html_file, web_file = renderer.save_html(enhanced_html)
        
        # 打印统计信息
        print("\n📊 渲染统计:")
        print(f"   HTML文件大小: {len(enhanced_html.encode('utf-8')) / 1024:.1f}KB")
        print(f"   图片数量: {enhanced_html.count('<img')}")
        print(f"   表格数量: {enhanced_html.count('<table')}")
        print(f"   卡片数量: {enhanced_html.count('card')}")
        
        print("\n🌐 网站访问:")
        print(f"   主页面: https://gnss-x.ac.cn/satellite-news/")
        print(f"   简化版: https://gnss-x.ac.cn/satellite-news/simple.html")
        
        return html_file, web_file
        
    except Exception as e:
        print(f"❌ 渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python html_renderer.py <markdown_file>")
        sys.exit(1)
    
    main(sys.argv[1])