#!/usr/bin/env python3
"""
卫星新闻数据可视化图表生成器
生成交互式图表和数据可视化页面
"""

import os
import sys
import json
import math
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import numpy as np
from collections import defaultdict

class ChartGenerator:
    def __init__(self):
        # 使用默认英文字体，移除中文字体设置
        plt.rcParams.update({
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10
        })
        
        # 颜色方案
        self.colors = {
            'primary': ['#3f51b5', '#4caf50', '#ff9800', '#9c27b0', '#2196f3', '#ff5722'],
            'pastel': ['#e3f2fd', '#e8f5e9', '#fff3e0', '#f3e5f5', '#fce4ec', '#f3e5f5'],
            'sequential': ['#1a237e', '#283593', '#3f51b5', '#5c6bc0', '#7986cb', '#9fa8da']
        }
        
    def load_analysis_data(self, analysis_file):
        """加载分析数据"""
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('analysis', {})
        except Exception as e:
            print(f"❌ 加载分析数据失败: {e}")
            return {}
    
    def generate_category_chart(self, categories, output_dir='output/charts'):
        """生成新闻分类分布图表"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not categories:
            print("⚠️ 无分类数据可生成图表")
            return None
        
        # 准备数据
        labels = []
        sizes = []
        colors = []
        
        for i, (category, count) in enumerate(sorted(categories.items(), key=lambda x: x[1], reverse=True)):
            labels.append(category)
            sizes.append(count)
            colors.append(self.colors['primary'][i % len(self.colors['primary'])])
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 饼图
        wedges, texts, autotexts = ax1.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10}
        )
        
        ax1.set_title('News Category Distribution - Pie Chart', fontsize=14, fontweight='bold', pad=20)
        ax1.axis('equal')
        
        # 柱状图
        x_pos = np.arange(len(labels))
        bars = ax2.bar(x_pos, sizes, color=colors, alpha=0.8)
        
        ax2.set_title('News Category Distribution - Bar Chart', fontsize=14, fontweight='bold', pad=20)
        ax2.set_xlabel('Category', fontsize=12)
        ax2.set_ylabel('Count', fontsize=12)
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(labels, rotation=45, ha='right')
        
        # 在柱子上显示数值
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        chart_file = f"{output_dir}/category_distribution_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 分类分布图表已保存: {chart_file}")
        return chart_file
    
    def generate_importance_chart(self, importance_scores, output_dir='output/charts'):
        """生成重要性分布图表"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not importance_scores:
            print("⚠️ 无重要性数据可生成图表")
            return None
        
        # 计算分布
        score_ranges = {
            'High Importance (8-10)': sum(1 for s in importance_scores if s >= 8),
            'Medium Importance (5-7)': sum(1 for s in importance_scores if 5 <= s < 8),
            'Low Importance (1-4)': sum(1 for s in importance_scores if s < 5)
        }
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 饼图
        labels = list(score_ranges.keys())
        sizes = list(score_ranges.values())
        colors = ['#ff5252', '#ffb74d', '#81c784']  # 红、橙、绿
        
        wedges, texts, autotexts = ax1.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10}
        )
        
        ax1.set_title('Importance Distribution - Pie Chart', fontsize=14, fontweight='bold', pad=20)
        ax1.axis('equal')
        
        # 直方图
        ax2.hist(importance_scores, bins=10, range=(1, 11), 
                color='#3f51b5', alpha=0.7, edgecolor='black')
        
        ax2.set_title('Importance Score Distribution - Histogram', fontsize=14, fontweight='bold', pad=20)
        ax2.set_xlabel('Importance Score (1-10)', fontsize=12)
        ax2.set_ylabel('Count', fontsize=12)
        ax2.set_xticks(range(1, 11))
        ax2.grid(True, alpha=0.3)
        
        # 添加统计信息
        avg_score = np.mean(importance_scores)
        median_score = np.median(importance_scores)
        ax2.text(0.02, 0.98, f'Average: {avg_score:.1f}\nMedian: {median_score:.1f}',
                transform=ax2.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        chart_file = f"{output_dir}/importance_distribution_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 重要性分布图表已保存: {chart_file}")
        return chart_file
    
    def generate_trend_chart(self, articles, output_dir='output/charts'):
        """生成时间趋势图表"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not articles:
            print("⚠️ 无文章数据可生成趋势图表")
            return None
        
        # 按小时统计发布时间
        hour_counts = defaultdict(int)
        for article in articles:
            try:
                published = article.get('published', '')
                if published:
                    # 解析时间
                    dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    hour = dt.hour
                    hour_counts[hour] += 1
            except:
                continue
        
        if not hour_counts:
            print("⚠️ 无有效时间数据可生成趋势图表")
            return None
        
        # 准备数据
        hours = sorted(hour_counts.keys())
        counts = [hour_counts[h] for h in hours]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 折线图
        ax.plot(hours, counts, marker='o', linestyle='-', 
                color='#3f51b5', linewidth=2, markersize=8)
        
        # 填充区域
        ax.fill_between(hours, counts, alpha=0.2, color='#3f51b5')
        
        ax.set_title('News Publication Time Distribution Trend', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Publication Time (Hour)', fontsize=12)
        ax.set_ylabel('News Count', fontsize=12)
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.3)
        
        # 添加峰值标记
        max_hour = hours[counts.index(max(counts))]
        max_count = max(counts)
        ax.annotate(f'Peak: {max_count} articles\n({max_hour}:00)',
                   xy=(max_hour, max_count),
                   xytext=(max_hour + 2, max_count - 1),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        chart_file = f"{output_dir}/time_trend_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 时间趋势图表已保存: {chart_file}")
        return chart_file
    
    def generate_technical_analysis_chart(self, tech_analysis, output_dir='output/charts'):
        """生成技术分析雷达图"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not tech_analysis:
            print("⚠️ 无技术分析数据可生成图表")
            return None
        
        # 准备数据
        tech_areas = {
            'gnss_system_updates': 'GNSS Systems',
            'satellite_constellations': 'Satellite Constellations',
            'launch_vehicle_developments': 'Launch Vehicles',
            'payload_technologies': 'Payload Technologies',
            'meteorological_systems': 'Meteorological Systems',
            'research_publications': 'Research Publications',
            'policy_regulations': 'Policy Regulations'
        }
        
        labels = []
        values = []
        
        for area_key, area_name in tech_areas.items():
            items = tech_analysis.get(area_key, [])
            if items:
                labels.append(area_name)
                # 计算该领域的平均重要性
                importances = [item.get('importance', 5) for item in items]
                avg_importance = sum(importances) / len(importances) if importances else 0
                values.append(avg_importance)
        
        if len(labels) < 3:
            print("⚠️ 技术领域数据不足，无法生成雷达图")
            return None
        
        # 创建雷达图
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, polar=True)
        
        # 角度计算
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values.append(values[0])  # 闭合图形
        angles.append(angles[0])
        
        # 绘制雷达图
        ax.plot(angles, values, 'o-', linewidth=2, color='#3f51b5')
        ax.fill(angles, values, alpha=0.25, color='#3f51b5')
        
        # 设置角度标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=11)
        
        # 设置径向标签
        ax.set_ylim(0, 10)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=10)
        ax.set_ylabel('Average Importance Score', fontsize=12, labelpad=20)
        
        ax.set_title('Technical Domain Importance Analysis - Radar Chart', fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        chart_file = f"{output_dir}/technical_analysis_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 技术分析雷达图已保存: {chart_file}")
        return chart_file
    
    def generate_html_dashboard(self, analysis_data, articles_data, output_dir='output/charts'):
        """生成HTML数据仪表板"""
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs('/var/www/html/satellite-news/charts', exist_ok=True)
        os.makedirs('/var/www/html/satellite-news/data', exist_ok=True)
        
        # 生成所有图表
        categories = analysis_data.get('categories', {})
        importance_scores = analysis_data.get('importance_scores', [])
        tech_analysis = analysis_data.get('technical_analysis', {})
        
        chart_files = {
            'category': self.generate_category_chart(categories, output_dir),
            'importance': self.generate_importance_chart(importance_scores, output_dir),
            'trend': self.generate_trend_chart(articles_data, output_dir),
            'technical': self.generate_technical_analysis_chart(tech_analysis, output_dir)
        }
        
        # 创建HTML仪表板
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        total_articles = analysis_data.get('metadata', {}).get('total_articles', 0)
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Satellite News Data Visualization Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .stats-bar {{
            display: flex;
            justify-content: space-around;
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            flex-wrap: wrap;
        }}
        
        .stat-card {{
            text-align: center;
            padding: 15px;
            min-width: 200px;
        }}
        
        .stat-number {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #3f51b5;
        }}
        
        .stat-label {{
            font-size: 1rem;
            color: #666;
            margin-top: 5px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            padding: 40px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        
        .chart-container:hover {{
            transform: translateY(-5px);
        }}
        
        .chart-title {{
            font-size: 1.4rem;
            color: #1a237e;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3f51b5;
        }}
        
        .chart-image {{
            width: 100%;
            height: auto;
            border-radius: 10px;
        }}
        
        .chart-description {{
            margin-top: 15px;
            color: #666;
            font-size: 0.95rem;
            line-height: 1.5;
        }}
        
        .footer {{
            background: #1a237e;
            color: white;
            padding: 30px;
            text-align: center;
            margin-top: 40px;
        }}
        
        .footer p {{
            margin: 10px 0;
            opacity: 0.8;
        }}
        
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .stat-card {{
                min-width: 150px;
            }}
        }}
        
        .navigation {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 30px;
            flex-wrap: wrap;
        }}
        
        .nav-button {{
            background: #3f51b5;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
        }}
        
        .nav-button:hover {{
            background: #283593;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛰️ Satellite News Data Visualization Dashboard</h1>
            <div class="subtitle">AI-powered Data Insights and Visualization</div>
            <div class="subtitle">Last Updated: {timestamp}</div>
        </div>
        
        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-number">{total_articles}</div>
                <div class="stat-label">Total News Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(categories)}</div>
                <div class="stat-label">Technical Categories</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{sum(1 for s in importance_scores if s >= 8)}</div>
                <div class="stat-label">High Importance Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(tech_analysis)}</div>
                <div class="stat-label">Technical Analysis Domains</div>
            </div>
        </div>
        
        <div class="charts-grid">
'''
        
        # 添加图表
        for chart_type, chart_file in chart_files.items():
            if chart_file:
                chart_name = {
                    'category': 'News Category Distribution Analysis',
                    'importance': 'Importance Score Distribution',
                    'trend': 'Publication Time Trend Analysis',
                    'technical': 'Technical Domain Importance Radar Chart'
                }.get(chart_type, chart_type)
                
                chart_desc = {
                    'category': 'Shows the distribution of news across different technical domains, helping identify current hot technology directions.',
                    'importance': 'Displays the distribution of news importance scores, highlighting high-importance events that require special attention.',
                    'trend': 'Analyzes news publication time patterns to understand optimal information release timing.',
                    'technical': 'Shows average importance scores across technical domains using radar chart, identifying key technology directions.'
                }.get(chart_type, '')
                
                # 获取图表文件名
                chart_filename = os.path.basename(chart_file)
                web_chart_path = f"/satellite-news/charts/{chart_filename}"
                
                html_content += f'''
            <div class="chart-container">
                <h3 class="chart-title">{chart_name}</h3>
                <img src="{web_chart_path}" alt="{chart_name}" class="chart-image">
                <p class="chart-description">{chart_desc}</p>
            </div>
'''
        
        html_content += f'''
        </div>
        
        <div class="navigation">
            <a href="https://gnss-x.ac.cn/satellite-news/" class="nav-button">Main Report</a>
            <a href="https://gnss-x.ac.cn/satellite-news/simple.html" class="nav-button">Simple Version</a>
        </div>
        
        <div class="footer">
            <p>🛰️ Satellite News Data Visualization System</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Data Sources: Multi-source News Aggregation | Visualization Engine: Matplotlib + Custom Charts</p>
            <p>© 2026 Mapoet Assistant | Data for reference and research purposes only</p>
        </div>
    </div>
    
    <script>
        // 图表交互功能
        document.addEventListener('DOMContentLoaded', function() {{
            // 为所有图表添加点击放大功能
            const chartImages = document.querySelectorAll('.chart-image');
            chartImages.forEach(img => {{
                img.addEventListener('click', function() {{
                    const modal = document.createElement('div');
                    modal.style.position = 'fixed';
                    modal.style.top = '0';
                    modal.style.left = '0';
                    modal.style.width = '100%';
                    modal.style.height = '100%';
                    modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
                    modal.style.display = 'flex';
                    modal.style.justifyContent = 'center';
                    modal.style.alignItems = 'center';
                    modal.style.zIndex = '1000';
                    
                    const modalImg = document.createElement('img');
                    modalImg.src = this.src;
                    modalImg.style.maxWidth = '90%';
                    modalImg.style.maxHeight = '90%';
                    modalImg.style.borderRadius = '10px';
                    
                    modal.appendChild(modalImg);
                    document.body.appendChild(modal);
                    
                    // 点击关闭
                    modal.addEventListener('click', function() {{
                        document.body.removeChild(modal);
                    }});
                }});
            }});
            
            // 添加打印功能
            const printButton = document.createElement('button');
            printButton.textContent = '🖨️ Print Dashboard';
            printButton.className = 'nav-button';
            printButton.style.margin = '20px auto';
            printButton.style.display = 'block';
            printButton.addEventListener('click', function() {{
                window.print();
            }});
            
            document.querySelector('.navigation').appendChild(printButton);
        }});
    </script>
</body>
</html>'''
        
        # 保存HTML文件
        html_file = f"{output_dir}/dashboard.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 复制到网站目录
        web_file = "/var/www/html/satellite-news/charts/index.html"
        with open(web_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 复制图表文件到网站目录
        for chart_file in chart_files.values():
            if chart_file and os.path.exists(chart_file):
                chart_filename = os.path.basename(chart_file)
                web_chart_file = f"/var/www/html/satellite-news/charts/{chart_filename}"
                import shutil
                shutil.copy2(chart_file, web_chart_file)
        
        print(f"🌐 HTML数据仪表板已保存:")
        print(f"   本地文件: {html_file}")
        print(f"   网站文件: {web_file}")
        
        return html_file, web_file
    
    def generate_data_page(self, analysis_file, articles_file, output_dir='output/charts'):
        """生成数据下载页面"""
        os.makedirs('/var/www/html/satellite-news/data', exist_ok=True)
        
        # 复制数据文件到网站目录
        data_files = []
        if os.path.exists(analysis_file):
            import shutil
            analysis_filename = os.path.basename(analysis_file)
            web_analysis_file = f"/var/www/html/satellite-news/data/{analysis_filename}"
            shutil.copy2(analysis_file, web_analysis_file)
            data_files.append(('技术分析数据', analysis_filename))
        
        if os.path.exists(articles_file):
            import shutil
            articles_filename = os.path.basename(articles_file)
            web_articles_file = f"/var/www/html/satellite-news/data/{articles_filename}"
            shutil.copy2(articles_file, web_articles_file)
            data_files.append(('详细文章数据', articles_filename))
        
        # 创建数据页面HTML
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>卫星新闻数据下载</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.2rem;
            margin-bottom: 10px;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .data-section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            color: #1a237e;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3f51b5;
        }}
        
        .data-list {{
            list-style: none;
        }}
        
        .data-item {{
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 4px solid #3f51b5;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .data-info h3 {{
            font-size: 1.2rem;
            color: #1a237e;
            margin-bottom: 5px;
        }}
        
        .data-info p {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .download-button {{
            background: #4caf50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
        }}
        
        .download-button:hover {{
            background: #388e3c;
        }}
        
        .navigation {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 40px;
            flex-wrap: wrap;
        }}
        
        .nav-button {{
            background: #3f51b5;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
        }}
        
        .nav-button:hover {{
            background: #283593;
        }}
        
        .footer {{
            background: #1a237e;
            color: white;
            padding: 30px;
            text-align: center;
            margin-top: 40px;
        }}
        
        @media (max-width: 600px) {{
            .data-item {{
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }}
            
            .download-button {{
                align-self: flex-end;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 卫星新闻数据下载</h1>
            <p>原始数据与分析结果文件</p>
        </div>
        
        <div class="content">
            <div class="data-section">
                <h2 class="section-title">数据文件下载</h2>
                <ul class="data-list">
'''
        
        for data_name, filename in data_files:
            file_size = os.path.getsize(f"/var/www/html/satellite-news/data/{filename}")
            file_size_mb = file_size / 1024 / 1024
            
            html_content += f'''
                    <li class="data-item">
                        <div class="data-info">
                            <h3>{data_name}</h3>
                            <p>文件: {filename} | 大小: {file_size_mb:.2f} MB</p>
                            <p>更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                        </div>
                        <a href="/satellite-news/data/{filename}" class="download-button" download>📥 下载</a>
                    </li>
'''
        
        html_content += f'''
                </ul>
            </div>
            
            <div class="data-section">
                <h2 class="section-title">数据格式说明</h2>
                <div class="data-item">
                    <div class="data-info">
                        <h3>JSON数据格式</h3>
                        <p>所有数据文件均采用标准JSON格式，包含完整的元数据和结构化内容。</p>
                        <p>支持Python、JavaScript、Java等主流编程语言直接解析。</p>
                    </div>
                </div>
            </div>
            
            <div class="navigation">
                <a href="https://gnss-x.ac.cn/satellite-news/charts/" class="nav-button">View Data Visualization</a>
                <a href="https://gnss-x.ac.cn/satellite-news/" class="nav-button">Main Report</a>
                <a href="https://gnss-x.ac.cn/satellite-news/simple.html" class="nav-button">Simple Version</a>
            </div>
        </div>
        
        <div class="footer">
            <p>🛰️ 卫星新闻数据分析系统</p>
            <p>数据仅供参考和研究使用，请遵守相关数据使用协议</p>
            <p>© 2026 Mapoet助手</p>
        </div>
    </div>
</body>
</html>'''
        
        # 保存数据页面
        data_html_file = "/var/www/html/satellite-news/data/index.html"
        with open(data_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📥 数据下载页面已创建: {data_html_file}")
        return data_html_file

def main(analysis_file, articles_file):
    """主函数"""
    print("=" * 80)
    print("卫星新闻数据可视化图表生成器")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    generator = ChartGenerator()
    
    try:
        # 加载分析数据
        analysis_data = generator.load_analysis_data(analysis_file)
        
        if not analysis_data:
            print("❌ 无分析数据可生成图表")
            return None
        
        # 加载文章数据
        articles_data = []
        if os.path.exists(articles_file):
            with open(articles_file, 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
        
        print(f"📊 基于分析数据生成可视化图表...")
        print(f"   分析数据: {analysis_file}")
        print(f"   文章数据: {articles_file}")
        
        # 生成HTML仪表板
        html_file, web_file = generator.generate_html_dashboard(analysis_data, articles_data)
        
        # 生成数据页面
        data_page = generator.generate_data_page(analysis_file, articles_file)
        
        print("\n🌐 网站访问:")
        print(f"   数据可视化: https://gnss-x.ac.cn/satellite-news/charts/")
        print(f"   数据下载: https://gnss-x.ac.cn/satellite-news/data/")
        print(f"   主报告: https://gnss-x.ac.cn/satellite-news/")
        
        return html_file, web_file, data_page
        
    except Exception as e:
        print(f"❌ 生成图表失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python chart_generator.py <analysis_file> <articles_file>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])