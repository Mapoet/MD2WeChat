#!/usr/bin/env python3
"""
完整卫星新闻分析流水线
1. 新闻抓取 → 2. 专业分析 → 3. Markdown生成 → 4. HTML渲染
"""

import os
import sys
import json
from datetime import datetime, timedelta
import subprocess
import time


def _project_venv_python(project_dir: str) -> str:
    """ Prefer project venv so subprocesses get the same deps as requirements (e.g. feedparser). """
    if os.name == "nt":
        rel = os.path.join("venv", "Scripts", "python.exe")
    else:
        rel = os.path.join("venv", "bin", "python")
    path = os.path.join(project_dir, rel)
    return path if os.path.isfile(path) else ""


class FullAnalysisPipeline:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        venv_py = _project_venv_python(self.project_dir)
        self.python_executable = venv_py or sys.executable
        self.scripts_dir = os.path.join(self.project_dir, "scripts")
        self.reports_dir = os.path.join(self.project_dir, "reports")
        self.data_dir = os.path.join(self.project_dir, "data")
        self.output_dir = os.path.join(self.project_dir, "output")
        
        # 创建目录
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 日志文件
        self.log_file = os.path.join(self.project_dir, "logs", f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        
        print(log_message)
        
        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + "\n")
    
    def step1_fetch_news(self):
        """步骤1: 新闻抓取"""
        self.log("=" * 80)
        self.log("步骤1: 开始新闻抓取")
        self.log("=" * 80)
        
        try:
            # 运行新闻抓取器
            script_path = os.path.join(self.scripts_dir, "news_fetcher.py")
            
            self.log(f"运行脚本: {script_path}")
            
            result = subprocess.run(
                [self.python_executable, script_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=self.project_dir
            )
            
            # 记录输出
            self.log("新闻抓取输出:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            
            if result.returncode != 0:
                self.log(f"新闻抓取失败: {result.stderr}", "ERROR")
                return None
            
            # 查找最新新闻文件
            news_files = []
            news_dir = os.path.join(self.data_dir, "news")
            if os.path.exists(news_dir):
                for root, dirs, files in os.walk(news_dir):
                    for file in files:
                        if file.endswith('.json'):
                            news_files.append(os.path.join(root, file))
            
            if news_files:
                # 按修改时间排序，取最新的
                latest_news = max(news_files, key=os.path.getmtime)
                self.log(f"找到最新新闻文件: {latest_news}")
                return latest_news
            else:
                self.log("未找到新闻文件", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"新闻抓取异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def step2_daily_analysis(self, news_file):
        """步骤2: 每日分析（使用Cursor深度分析）"""
        self.log("=" * 80)
        self.log("步骤2: 开始每日分析（Cursor深度分析）")
        self.log("=" * 80)
        
        if not news_file or not os.path.exists(news_file):
            self.log("新闻文件不存在，跳过分析步骤", "WARNING")
            return None
        
        try:
            # 运行每日分析器（使用Cursor）
            script_path = os.path.join(self.scripts_dir, "generate_daily_analysis.py")
            
            self.log(f"运行脚本: {script_path} {news_file}")
            
            result = subprocess.run(
                [self.python_executable, script_path, news_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=self.project_dir
            )
            
            # 记录输出
            self.log("每日分析输出:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            
            if result.returncode != 0:
                self.log(f"每日分析失败: {result.stderr}", "ERROR")
                return None
            
            # 查找最新分析文件（新的目录结构）
            analysis_files = []
            analysis_dir = os.path.join(self.data_dir, "analysis", "daily")
            if os.path.exists(analysis_dir):
                for root, dirs, files in os.walk(analysis_dir):
                    for file in files:
                        if file.startswith('daily_analysis_') and file.endswith('.json'):
                            analysis_files.append(os.path.join(root, file))
            
            if analysis_files:
                # 按修改时间排序，取最新的
                latest_analysis = max(analysis_files, key=os.path.getmtime)
                self.log(f"找到最新分析文件: {latest_analysis}")
                return latest_analysis
            else:
                self.log("未找到分析文件", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"每日分析异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def step3_markdown_generation(self, analysis_file):
        """步骤3: Markdown生成"""
        self.log("=" * 80)
        self.log("步骤3: 开始Markdown生成")
        self.log("=" * 80)
        
        if not analysis_file or not os.path.exists(analysis_file):
            self.log("分析文件不存在，跳过Markdown生成", "WARNING")
            return None
        
        try:
            # 运行Markdown生成器
            script_path = os.path.join(self.scripts_dir, "markdown_generator.py")
            
            self.log(f"运行脚本: {script_path} {analysis_file}")
            
            result = subprocess.run(
                [self.python_executable, script_path, analysis_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=self.project_dir
            )
            
            # 记录输出
            self.log("Markdown生成输出:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            
            if result.returncode != 0:
                self.log(f"Markdown生成失败: {result.stderr}", "ERROR")
                return None
            
            # 查找最新Markdown文件
            markdown_files = []
            markdown_dir = os.path.join(self.reports_dir, "markdown")
            if os.path.exists(markdown_dir):
                for root, dirs, files in os.walk(markdown_dir):
                    for file in files:
                        if file.startswith('report_') and file.endswith('.md'):
                            markdown_files.append(os.path.join(root, file))
            
            if markdown_files:
                # 按修改时间排序，取最新的
                latest_markdown = max(markdown_files, key=os.path.getmtime)
                self.log(f"找到最新Markdown文件: {latest_markdown}")
                return latest_markdown
            else:
                self.log("未找到Markdown文件", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"Markdown生成异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def step4_html_rendering(self, markdown_file):
        """步骤4: HTML渲染"""
        self.log("=" * 80)
        self.log("步骤4: 开始HTML渲染")
        self.log("=" * 80)
        
        if not markdown_file or not os.path.exists(markdown_file):
            self.log("Markdown文件不存在，跳过HTML渲染", "WARNING")
            return None
        
        try:
            # 运行HTML渲染器
            script_path = os.path.join(self.scripts_dir, "html_renderer.py")
            
            self.log(f"运行脚本: {script_path} {markdown_file}")
            
            result = subprocess.run(
                [self.python_executable, script_path, markdown_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=self.project_dir
            )
            
            # 记录输出
            self.log("HTML渲染输出:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            
            if result.returncode != 0:
                self.log(f"HTML渲染失败: {result.stderr}", "ERROR")
                return None
            
            # 查找最新HTML文件
            html_files = []
            html_dir = os.path.join(self.output_dir, "html")
            if os.path.exists(html_dir):
                for root, dirs, files in os.walk(html_dir):
                    for file in files:
                        if file.startswith('report_') and file.endswith('.html'):
                            html_files.append(os.path.join(root, file))
            
            if html_files:
                # 按修改时间排序，取最新的
                latest_html = max(html_files, key=os.path.getmtime)
                self.log(f"找到最新HTML文件: {latest_html}")
                return latest_html
            else:
                self.log("未找到HTML文件", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"HTML渲染异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def step5_chart_generation(self, analysis_file, articles_file):
        """步骤5: 图表生成与数据可视化"""
        self.log("=" * 80)
        self.log("步骤5: 开始图表生成与数据可视化")
        self.log("=" * 80)
        
        if not analysis_file or not os.path.exists(analysis_file):
            self.log("分析文件不存在，跳过图表生成", "WARNING")
            return None
        
        if not articles_file or not os.path.exists(articles_file):
            self.log("文章文件不存在，跳过图表生成", "WARNING")
            return None
        
        try:
            # 运行图表生成器
            script_path = os.path.join(self.scripts_dir, "chart_generator.py")
            
            self.log(f"运行脚本: {script_path} {analysis_file} {articles_file}")
            
            result = subprocess.run(
                [self.python_executable, script_path, analysis_file, articles_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=self.project_dir
            )
            
            # 记录输出
            self.log("图表生成输出:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            
            if result.returncode != 0:
                self.log(f"图表生成失败: {result.stderr}", "ERROR")
                return None
            
            # 查找生成的图表文件
            chart_files = []
            charts_dir = os.path.join(self.output_dir, "charts")
            if os.path.exists(charts_dir):
                for root, dirs, files in os.walk(charts_dir):
                    for file in files:
                        if file.endswith(('.png', '.html')):
                            chart_files.append(os.path.join(root, file))
            
            if chart_files:
                # 按修改时间排序，取最新的仪表板
                latest_charts = []
                for ext in ['.html', '.png']:
                    ext_files = [f for f in chart_files if f.endswith(ext)]
                    if ext_files:
                        latest = max(ext_files, key=os.path.getmtime)
                        latest_charts.append(latest)
                
                self.log(f"找到图表文件: {len(chart_files)}个")
                for chart in latest_charts[:3]:  # 显示前3个
                    self.log(f"  {os.path.basename(chart)}")
                
                return latest_charts
            else:
                self.log("未找到图表文件", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"图表生成异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def run_pipeline(self):
        """运行完整流水线"""
        start_time = datetime.now()
        self.log("=" * 80)
        self.log("开始完整卫星新闻分析流水线")
        self.log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"项目目录: {self.project_dir}")
        self.log(f"日志文件: {self.log_file}")
        self.log("=" * 80)
        
        results = {
            'start_time': start_time.isoformat(),
            'steps': {},
            'success': False
        }
        
        try:
            # 步骤1: 新闻抓取
            step1_start = datetime.now()
            news_file = self.step1_fetch_news()
            step1_duration = (datetime.now() - step1_start).total_seconds()
            
            results['steps']['news_fetch'] = {
                'success': news_file is not None,
                'duration': step1_duration,
                'output_file': news_file
            }
            
            if not news_file:
                self.log("新闻抓取失败，终止流水线", "ERROR")
                return results
            
            # 步骤2: 每日分析（Cursor深度分析）
            step2_start = datetime.now()
            analysis_file = self.step2_daily_analysis(news_file)
            step2_duration = (datetime.now() - step2_start).total_seconds()
            
            results['steps']['daily_analysis'] = {
                'success': analysis_file is not None,
                'duration': step2_duration,
                'output_file': analysis_file
            }
            
            if not analysis_file:
                self.log("每日分析失败，终止流水线", "ERROR")
                return results
            
            # 步骤3: Markdown生成
            step3_start = datetime.now()
            markdown_file = self.step3_markdown_generation(analysis_file)
            step3_duration = (datetime.now() - step3_start).total_seconds()
            
            results['steps']['markdown_generation'] = {
                'success': markdown_file is not None,
                'duration': step3_duration,
                'output_file': markdown_file
            }
            
            if not markdown_file:
                self.log("Markdown生成失败，终止流水线", "ERROR")
                return results
            
            # 步骤4: HTML渲染
            step4_start = datetime.now()
            html_file = self.step4_html_rendering(markdown_file)
            step4_duration = (datetime.now() - step4_start).total_seconds()
            
            results['steps']['html_rendering'] = {
                'success': html_file is not None,
                'duration': step4_duration,
                'output_file': html_file
            }
            
            # 步骤5: 图表生成与数据可视化
            step5_start = datetime.now()
            # 查找文章数据文件
            articles_file = None
            analysis_dir = os.path.join(self.data_dir, "analysis", "professional")
            if os.path.exists(analysis_dir):
                for file in os.listdir(analysis_dir):
                    if file.startswith("articles_") and file.endswith(".json"):
                        articles_file = os.path.join(analysis_dir, file)
                        break
            
            if articles_file and analysis_file:
                chart_results = self.step5_chart_generation(analysis_file, articles_file)
                step5_duration = (datetime.now() - step5_start).total_seconds()
                
                results['steps']['chart_generation'] = {
                    'success': chart_results is not None,
                    'duration': step5_duration,
                    'output_files': chart_results
                }
            else:
                self.log("未找到文章数据文件，跳过图表生成", "WARNING")
                results['steps']['chart_generation'] = {
                    'success': False,
                    'duration': 0,
                    'output_files': None
                }
            
            # 汇总结果
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            results['end_time'] = end_time.isoformat()
            results['total_duration'] = total_duration
            results['success'] = all(step['success'] for step in results['steps'].values() if step.get('output_files') is not False)
            
            # 生成摘要报告
            self.generate_summary_report(results)
            
            self.log("=" * 80)
            self.log("流水线执行完成")
            self.log(f"总耗时: {total_duration:.1f}秒")
            self.log(f"成功: {results['success']}")
            self.log("=" * 80)
            
            return results
            
        except Exception as e:
            self.log(f"流水线执行异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            
            results['error'] = str(e)
            results['success'] = False
            
            return results
    def generate_summary_report(self, results):
        """生成摘要报告"""
        try:
            # 构建文件生成列表
            files_generated = {
                'news': results['steps']['news_fetch']['output_file'],
                'analysis': results['steps']['professional_analysis']['output_file'],
                'markdown': results['steps']['markdown_generation']['output_file'],
                'html': results['steps']['html_rendering']['output_file']
            }
            
            # 如果有图表生成，添加到文件列表
            if 'chart_generation' in results['steps'] and results['steps']['chart_generation']['output_files']:
                files_generated['charts'] = results['steps']['chart_generation']['output_files']
            
            summary = {
                'pipeline_run': results,
                'website_info': {
                    'main_url': 'http://10.0.0.9/satellite-news/',
                    'simple_url': 'http://10.0.0.9/satellite-news/simple.html',
                    'charts_url': 'http://10.0.0.9/satellite-news/charts/',
                    'data_url': 'http://10.0.0.9/satellite-news/data/',
                    'main_page': '/var/www/html/satellite-news/index.html',
                    'simple_page': '/var/www/html/satellite-news/simple.html'
                },
                'files_generated': files_generated
            }
            
            # 保存摘要
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = os.path.join(self.project_dir, "logs", f"pipeline_summary_{timestamp}.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            self.log(f"摘要报告已保存: {summary_file}")
            
            # 生成人类可读的摘要
            chart_step_info = ""
            if 'chart_generation' in results['steps']:
                chart_success = results['steps']['chart_generation']['success']
                chart_duration = results['steps']['chart_generation']['duration']
                chart_step_info = f"5. 图表生成: {chart_duration:.1f}秒 - {'成功' if chart_success else '失败'}\n"
            
            chart_files_info = ""
            if 'chart_generation' in results['steps'] and results['steps']['chart_generation']['output_files']:
                chart_files = results['steps']['chart_generation']['output_files']
                if chart_files:
                    chart_files_info = "• 数据可视化: http://10.0.0.9/satellite-news/charts/\n"
            
            human_summary = f"""
            ========================================
            卫星新闻分析流水线执行摘要
            ========================================
            
            执行时间: {results['start_time']} - {results['end_time']}
            总耗时: {results['total_duration']:.1f}秒
            状态: {'成功 ✅' if results['success'] else '失败 ❌'}
            
            各步骤详情:
            1. 新闻抓取: {results['steps']['news_fetch']['duration']:.1f}秒 - {'成功' if results['steps']['news_fetch']['success'] else '失败'}
            2. 专业分析: {results['steps']['professional_analysis']['duration']:.1f}秒 - {'成功' if results['steps']['professional_analysis']['success'] else '失败'}
            3. Markdown生成: {results['steps']['markdown_generation']['duration']:.1f}秒 - {'成功' if results['steps']['markdown_generation']['success'] else '失败'}
            4. HTML渲染: {results['steps']['html_rendering']['duration']:.1f}秒 - {'成功' if results['steps']['html_rendering']['success'] else '失败'}
{chart_step_info}
            生成文件:
            • 新闻数据: {results['steps']['news_fetch']['output_file']}
            • 分析结果: {results['steps']['professional_analysis']['output_file']}
            • Markdown报告: {results['steps']['markdown_generation']['output_file']}
            • HTML报告: {results['steps']['html_rendering']['output_file']}
{chart_files_info}
            网站访问:
            • 主页面: http://10.0.0.9/satellite-news/
            • 简化版: http://10.0.0.9/satellite-news/simple.html
            • 数据可视化: http://10.0.0.9/satellite-news/charts/
            • 数据下载: http://10.0.0.9/satellite-news/data/
            
            ========================================
            生成系统: Mapoet助手专业分析流水线 🛰️
            ========================================
            """
            
            human_summary_file = os.path.join(self.project_dir, "logs", f"pipeline_summary_{timestamp}.txt")
            with open(human_summary_file, 'w', encoding='utf-8') as f:
                f.write(human_summary)
            
            self.log(f"人类可读摘要已保存: {human_summary_file}")
            
            # 打印摘要
            print("\n" + "=" * 80)
            print("流水线执行摘要")
            print("=" * 80)
            print(human_summary)
            
        except Exception as e:
            self.log(f"生成摘要报告失败: {e}", "ERROR")

def main():
    """主函数"""
    pipeline = FullAnalysisPipeline()
    results = pipeline.run_pipeline()
    
    # 返回结果
    return 0 if results.get('success', False) else 1

if __name__ == "__main__":
    sys.exit(main())