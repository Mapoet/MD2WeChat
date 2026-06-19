#!/usr/bin/env python3
"""
专业Markdown报告生成器
生成结构化的卫星新闻分析报告
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
import re

class MarkdownGenerator:
    def __init__(self):
        # 分类图标映射
        self.category_icons = {
            'gnss': '🛰️',
            'meteorology': '🌤️',
            'launch': '🚀',
            'satellite': '🛸',
            'research': '🔬',
            'business': '💼',
            'other': '📰'
        }
        
        # 重要性图标映射
        self.importance_icons = {
            10: '🔴',
            9: '🔴',
            8: '🟠',
            7: '🟡',
            6: '🟡',
            5: '🟢',
            4: '🟢',
            3: '🔵',
            2: '🔵',
            1: '⚪'
        }
        
    def _clean_cursor_analysis(self, cursor_analysis):
        """清理Cursor分析结果中的不需要的文本，并将文件路径转换为HTML链接"""
        if not cursor_analysis:
            return cursor_analysis
        
        # 服务器基础URL
        base_url = "https://gnss-x.ac.cn/satellite-news"
        
        # 1. 检测并转换文件路径为HTML链接
        def convert_file_paths(match):
            """将文件路径转换为HTML链接"""
            full_text = match.group(0)
            # 提取文件路径（在反引号内）
            file_path_match = re.search(r'`([^`]+\.md)`', full_text)
            if file_path_match:
                file_path = file_path_match.group(1)
                # 获取文件名（用于链接文本）
                file_name = os.path.basename(file_path)
                # 构建URL（移除开头的斜杠，如果有）
                url_path = file_path.lstrip('/')
                full_url = f"{base_url}/{url_path}"
                # 返回Markdown链接格式
                return f"深度分析报告已保存，请查看：[{file_name}]({full_url})"
            return full_text
        
        # 匹配"已根据...保存为 `路径`"的模式（包括后面的"下面是报告要点概览"等）
        # 匹配完整句子，包括可能的后续文本
        pattern_saved_as_full = r'已根据.*?保存为\s*`[^`]+\.md`[。.]?\s*(?:下面是报告要点概览[。.]?\s*)?'
        cleaned = re.sub(pattern_saved_as_full, convert_file_paths, cursor_analysis, flags=re.DOTALL | re.IGNORECASE)
        
        # 匹配其他可能的"保存为 `路径`"模式
        pattern_save_as = r'(?:并)?保存为\s*`[^`]+\.md`'
        cleaned = re.sub(pattern_save_as, convert_file_paths, cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # 2. 移除不需要的文本模式
        patterns_to_remove = [
            # 移除"以下是由Cursor AI生成的深度分析报告"相关文本
            r'以下是由Cursor AI生成的深度分析报告[，,].*?：\s*',
            # 移除"已基于...完成分析...报告位置"相关文本
            r'已基于.*?latest_news\.json.*?完成分析.*?报告位置.*?\n',
            r'已基于.*?raw.*?新闻数据完成分析.*?报告位置.*?\n',
            r'已基于.*?完成分析.*?生成报告文件.*?精简版结论.*?报告位置.*?\n',
            # 移除"报告位置"标题及其后内容（直到下一个标题或段落）
            r'报告位置\s*\n+.*?(?=\n##|\n###|\n\n|$)',
            # 移除"完整 Markdown 报告已保存至"及其文件路径（已转换为链接）
            r'完整.*?Markdown.*?报告已保存至[：:]\s*\n.*?/.*?\.md.*?\n',
            r'完整.*?报告已保存至[：:]\s*\n.*?/.*?\.md.*?\n',
            # 移除"请更新"等提示性文本
            r'请更新\s*',
            # 移除"下面是报告要点概览"等提示性文本（保留实际内容）
            r'下面是报告要点概览[。.]?\s*\n',
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)
        
        cleaned = self._strip_markdown_headings(cleaned)
        
        # 3. 移除多余的空行（保留最多两个连续空行）
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 4. 移除开头和结尾的空白
        cleaned = cleaned.strip()
        
        return cleaned

    def _strip_markdown_headings(self, text):
        """Remove leading # heading markers outside fenced code blocks (soft cleanup)."""
        if not text:
            return text
        lines = text.split("\n")
        out = []
        in_fence = False
        for line in lines:
            if re.match(r"^\s*```", line):
                in_fence = not in_fence
                out.append(line)
                continue
            if not in_fence:
                line = re.sub(r"^(\s*)#{1,6}\s+", r"\1", line)
            out.append(line)
        return "\n".join(out)
    
    def load_analysis(self, analysis_file):
        """加载分析数据（支持新旧格式）"""
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否为新的每日分析格式
            if "metadata" in data and "cursor_analysis" in data:
                # 新格式：每日分析结果
                print(f"📋 检测到新格式分析数据")
                
                # 清理Cursor分析结果
                cleaned_analysis = self._clean_cursor_analysis(data["cursor_analysis"])
                
                stats = data.get("statistics") or {}
                gen_at = (data.get("metadata") or {}).get("generated_at", "")
                # 转换为旧格式兼容的结构
                analysis = {
                    "metadata": {
                        "analysis_time": gen_at,
                        "generated_at": gen_at,
                        "total_articles": data["metadata"]["total_articles"],
                        "important_articles": data["metadata"].get("important_articles", 0),
                        "time_range": "过去24小时"
                    },
                    "categories": stats.get("categories", {}),
                    "category_headlines": stats.get("category_headlines", {}),
                    "category_taglines": stats.get("category_taglines") or {},
                    "analysis_tasks": data.get("analysis_tasks"),
                    "key_findings": self._extract_key_findings(cleaned_analysis),
                    "trends": self._extract_trends(cleaned_analysis),
                    "recommendations": self._extract_recommendations(cleaned_analysis),
                    "technical_analysis": self._extract_technical_analysis(cleaned_analysis),
                    "important_articles": data.get("important_articles", []),
                    "cursor_analysis": cleaned_analysis
                }
                return analysis
            else:
                # 旧格式：直接返回analysis字段
                return data.get('analysis', {})
                
        except Exception as e:
            print(f"❌ 加载分析数据失败: {e}")
            return {}
    
    def _extract_key_findings(self, cursor_analysis):
        """从Cursor分析中提取关键发现"""
        # 简单实现：查找包含关键信息的段落
        findings = []
        lines = cursor_analysis.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['关键', '重要', '发现', '突破', '创新']):
                if len(line.strip()) > 20:  # 避免太短的句子
                    findings.append(line.strip())
        
        return findings[:5]  # 返回前5个
    
    def _extract_trends(self, cursor_analysis):
        """从Cursor分析中提取趋势"""
        trends = []
        lines = cursor_analysis.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['趋势', '发展', '增长', '变化', '未来']):
                if len(line.strip()) > 20:
                    trends.append(line.strip())
        
        return trends[:5]
    
    def _extract_recommendations(self, cursor_analysis):
        """从Cursor分析中提取建议"""
        recommendations = []
        lines = cursor_analysis.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['建议', '推荐', '应该', '需要', '考虑']):
                if len(line.strip()) > 20:
                    recommendations.append(line.strip())
        
        return recommendations[:5]
    
    def _extract_technical_analysis(self, cursor_analysis):
        """从Cursor分析中提取技术分析"""
        tech_analysis = {
            'gnss_system_updates': [],
            'satellite_constellations': [],
            'launch_vehicle_developments': [],
            'payload_technologies': [],
            'meteorological_systems': [],
            'research_publications': [],
            'policy_regulations': []
        }
        
        lines = cursor_analysis.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.lower()
            
            # 检测技术部分
            if 'gnss' in line_lower or 'gps' in line_lower or '导航' in line_lower:
                current_section = 'gnss_system_updates'
            elif '卫星' in line_lower and ('星座' in line_lower or '组网' in line_lower):
                current_section = 'satellite_constellations'
            elif '火箭' in line_lower or '发射' in line_lower:
                current_section = 'launch_vehicle_developments'
            elif '载荷' in line_lower or '仪器' in line_lower:
                current_section = 'payload_technologies'
            elif '气象' in line_lower or '天气' in line_lower:
                current_section = 'meteorological_systems'
            elif '研究' in line_lower or '论文' in line_lower:
                current_section = 'research_publications'
            elif '政策' in line_lower or '法规' in line_lower:
                current_section = 'policy_regulations'
            
            # 添加内容到当前部分
            if current_section and len(line.strip()) > 10:
                tech_analysis[current_section].append(line.strip())
        
        return tech_analysis
    
    def generate_report(self, analysis):
        """生成Markdown报告（支持新旧格式）"""
        print("📝 生成Markdown报告...")
        
        metadata = analysis.get('metadata', {})
        categories = analysis.get('categories', {})
        key_findings = analysis.get('key_findings', [])
        trends = analysis.get('trends', [])
        recommendations = analysis.get('recommendations', [])
        tech_analysis = analysis.get('technical_analysis', {})
        cursor_analysis = analysis.get('cursor_analysis', '')
        important_articles = analysis.get('important_articles', [])
        
        # 清理Cursor分析结果
        if cursor_analysis:
            cursor_analysis = self._clean_cursor_analysis(cursor_analysis)
            analysis['cursor_analysis'] = cursor_analysis
        
        # 如果是新格式且有Cursor分析，使用简化版本
        if cursor_analysis and len(cursor_analysis.strip()) > 100:
            return self._generate_simplified_report(analysis, cursor_analysis)
        
        # 开始生成科学报告
        report = []
        
        # 科学报告标题和元数据
        report.append(f"# 卫星技术发展日报 - 科学分析报告")
        report.append("")
        report.append(f"**报告编号**: SAT-TECH-{datetime.now().strftime('%Y%m%d')}")
        report.append(f"**生成时间**: {metadata.get('analysis_time', datetime.now().isoformat())}")
        report.append(f"**分析周期**: {metadata.get('time_range', '过去24小时')}")
        report.append(f"**数据样本**: {metadata.get('total_articles', 0)}篇技术新闻")
        report.append(f"**数据可视化**: [https://gnss-x.ac.cn/satellite-news/charts/](https://gnss-x.ac.cn/satellite-news/charts/)")
        report.append("")
        report.append("---")
        report.append("")
        
        # 执行摘要（科学报告格式）
        report.append("## 1. 执行摘要")
        report.append("")
        
        total = metadata.get('total_articles', 0)
        if total > 0:
            report.append("### 1.1 数据概况")
            report.append("")
            report.append(f"本报告基于{total}篇卫星技术相关新闻报道，涵盖GNSS系统、卫星星座、运载火箭、载荷技术、气象系统、研究出版物和政策法规等七个技术领域。")
            report.append("")
            
            # 技术领域分布
            tech_areas_count = sum(len(items) for items in tech_analysis.values())
            report.append("### 1.2 技术领域分布")
            report.append("")
            
            tech_area_names = {
                'gnss_system_updates': 'GNSS系统更新',
                'satellite_constellations': '卫星星座发展',
                'launch_vehicle_developments': '运载火箭技术',
                'payload_technologies': '载荷与仪器技术',
                'meteorological_systems': '气象卫星系统',
                'research_publications': '科学研究进展',
                'policy_regulations': '政策法规动态'
            }
            
            for tech_area, items in tech_analysis.items():
                if items:
                    area_name = tech_area_names.get(tech_area, tech_area)
                    percentage = (len(items) / tech_areas_count) * 100 if tech_areas_count > 0 else 0
                    report.append(f"- **{area_name}**: {len(items)}项 ({percentage:.1f}%)")
            
            report.append("")
            
            # 重要性分析
            importance_scores = analysis.get('importance_scores', [])
            if importance_scores:
                high = sum(1 for s in importance_scores if s >= 8)
                medium = sum(1 for s in importance_scores if 5 <= s < 8)
                low = sum(1 for s in importance_scores if s < 5)
                
                report.append("### 1.3 技术重要性评估")
                report.append("")
                report.append(f"采用10分制重要性评分系统，分析结果显示：")
                report.append(f"- **高重要性事件（≥8分）**: {high}项，占比{(high/total*100):.1f}%")
                report.append(f"- **中等重要性事件（5-7分）**: {medium}项，占比{(medium/total*100):.1f}%")
                report.append(f"- **低重要性事件（<5分）**: {low}项，占比{(low/total*100):.1f}%")
                report.append("")
        
        # 深度技术分析
        report.append("## 2. 深度技术分析")
        report.append("")
        
        # GNSS系统更新
        if tech_analysis.get('gnss_system_updates'):
            report.append("### 2.1 GNSS系统技术更新")
            report.append("")
            
            # 新格式：tech_analysis中的项目是字符串列表
            items = tech_analysis['gnss_system_updates']
            if items and isinstance(items, list) and len(items) > 0:
                # 检查第一个元素是否是字符串（新格式）
                if isinstance(items[0], str):
                    for i, item_text in enumerate(items[:5]):  # 显示前5项
                        report.append(f"#### GNSS更新 {i+1}")
                        report.append("")
                        report.append(f"{item_text}")
                        report.append("")
                else:
                    # 旧格式：字典列表
                    for item in items[:5]:
                        if isinstance(item, dict):
                            report.append(f"#### {item.get('title', 'GNSS更新')}")
                            report.append("")
                            report.append(f"**技术摘要**: {item.get('summary', '')}")
                            report.append("")
                            if item.get('technical_details'):
                                details = item['technical_details']
                                if details.get('frequencies'):
                                    report.append(f"**频率信息**: {', '.join(details['frequencies'])}")
                                if details.get('organizations'):
                                    report.append(f"**相关机构**: {', '.join(details['organizations'])}")
                                if item.get('gnss_systems'):
                                    report.append(f"**涉及系统**: {', '.join([s.upper() for s in item['gnss_systems']])}")
                            report.append(f"**数据来源**: {item.get('source', '')} | **重要性评分**: {item.get('importance', 0)}/10")
                            report.append("")
            else:
                report.append("暂无GNSS系统更新数据")
                report.append("")
        
        # 卫星星座发展
        if tech_analysis.get('satellite_constellations'):
            report.append("### 2.2 卫星星座技术进展")
            report.append("")
            for item in tech_analysis['satellite_constellations'][:5]:
                report.append(f"#### {item['title']}")
                report.append("")
                report.append(f"**技术摘要**: {item['summary']}")
                report.append("")
                if item.get('technical_details'):
                    details = item['technical_details']
                    if details.get('orbit_parameters'):
                        report.append(f"**轨道参数**: {', '.join(details['orbit_parameters'])}")
                    if details.get('dimensions'):
                        report.append(f"**尺寸参数**: {', '.join(details['dimensions'])}")
                    if details.get('organizations'):
                        report.append(f"**运营机构**: {', '.join(details['organizations'])}")
                    if item.get('constellations'):
                        report.append(f"**涉及星座**: {', '.join([c.title() for c in item['constellations']])}")
                report.append(f"**数据来源**: {item['source']} | **重要性评分**: {item['importance']}/10")
                report.append("")
        
        # 运载火箭技术
        if tech_analysis.get('launch_vehicle_developments'):
            report.append("### 2.3 运载火箭技术发展")
            report.append("")
            for item in tech_analysis['launch_vehicle_developments'][:5]:
                report.append(f"#### {item['title']}")
                report.append("")
                report.append(f"**技术摘要**: {item['summary']}")
                report.append("")
                if item.get('technical_details'):
                    details = item['technical_details']
                    if details.get('dimensions'):
                        report.append(f"**技术参数**: {', '.join(details['dimensions'])}")
                    if details.get('organizations'):
                        report.append(f"**研发机构**: {', '.join(details['organizations'])}")
                    if item.get('launch_vehicles'):
                        report.append(f"**运载火箭**: {', '.join([v.title() for v in item['launch_vehicles']])}")
                report.append(f"**数据来源**: {item['source']} | **重要性评分**: {item['importance']}/10")
                report.append("")
        
        # 载荷与仪器技术
        if tech_analysis.get('payload_technologies'):
            report.append("### 2.4 载荷与仪器技术创新")
            report.append("")
            for item in tech_analysis['payload_technologies'][:5]:
                report.append(f"#### {item['title']}")
                report.append("")
                report.append(f"**技术摘要**: {item['summary']}")
                report.append("")
                if item.get('technical_details'):
                    details = item['technical_details']
                    if details.get('frequencies'):
                        report.append(f"**工作频率**: {', '.join(details['frequencies'])}")
                    if details.get('dimensions'):
                        report.append(f"**物理参数**: {', '.join(details['dimensions'])}")
                    if item.get('payload_technologies'):
                        report.append(f"**技术类型**: {', '.join([p.title() for p in item['payload_technologies']])}")
                report.append(f"**数据来源**: {item['source']} | **重要性评分**: {item['importance']}/10")
                report.append("")
        
        # 关键技术事件分析
        report.append("## 3. 关键技术事件分析")
        report.append("")
        
        if key_findings:
            report.append("### 3.1 高重要性技术事件（重要性≥8）")
            report.append("")
            
            high_importance = [f for f in key_findings if f.get('importance', 0) >= 8]
            if high_importance:
                for i, finding in enumerate(high_importance[:5], 1):  # 只显示前5个高重要性事件
                    report.append(f"#### 3.1.{i} {finding['title']}")
                    report.append("")
                    report.append(f"**事件描述**: {finding.get('summary', '')}")
                    report.append("")
                    report.append(f"**技术影响分析**:")
                    report.append("")
                    
                    # 根据事件类型提供技术影响分析
                    events = finding.get('events', [])
                    if 'failure' in events:
                        report.append("- **技术挑战**: 揭示当前技术瓶颈和可靠性问题")
                        report.append("- **改进方向**: 为后续技术迭代提供重要参考")
                        report.append("- **风险评估**: 有助于完善技术风险管理体系")
                    elif 'launch' in events:
                        report.append("- **技术验证**: 验证运载火箭和卫星平台性能")
                        report.append("- **能力提升**: 展示发射能力和任务执行水平")
                        report.append("- **里程碑意义**: 标志技术发展的重要节点")
                    elif 'achievement' in events:
                        report.append("- **技术进步**: 体现技术突破和创新成果")
                        report.append("- **行业标杆**: 为同类技术发展提供参考")
                        report.append("- **应用前景**: 拓展技术应用领域和市场空间")
                    
                    report.append("")
                    report.append(f"**数据来源**: {finding.get('source', '未知')} | **重要性评分**: {finding.get('importance', 5)}/10")
                    report.append("")
            else:
                report.append("> 本周期内未发现高重要性技术事件")
                report.append("")
            
            report.append("### 3.2 中等重要性技术事件（重要性5-7）")
            report.append("")
            
            medium_importance = [f for f in key_findings if 5 <= f.get('importance', 0) < 8]
            if medium_importance:
                report.append("本周期共发现中等重要性技术事件{}项，主要涉及以下领域：".format(len(medium_importance)))
                report.append("")
                
                # 按类别分组
                category_groups = {}
                for finding in medium_importance:
                    category = finding.get('category', 'other')
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(finding)
                
                for category, findings in category_groups.items():
                    report.append(f"**{category}领域** ({len(findings)}项):")
                    for finding in findings[:3]:  # 每个类别显示前3项
                        title = finding['title']
                        if len(title) > 80:
                            title = title[:77] + "..."
                        report.append(f"- {title}")
                    report.append("")
            else:
                report.append("> 本周期内未发现中等重要性技术事件")
                report.append("")
        else:
            report.append("> 本周期内未发现关键技术事件")
            report.append("")
        
        # 技术发展趋势分析
        report.append("## 4. 技术发展趋势分析")
        report.append("")
        
        report.append("### 4.1 当前技术热点")
        report.append("")
        
        if trends:
            report.append("基于本周期新闻报道分析，识别出以下技术热点：")
            report.append("")
            for i, trend in enumerate(trends, 1):
                report.append(f"{i}. {trend}")
            report.append("")
        else:
            report.append("> 需要更多数据支持热点趋势分析")
            report.append("")
        
        report.append("### 4.2 长期技术发展趋势")
        report.append("")
        report.append("基于卫星技术发展规律和行业动态，识别以下长期趋势：")
        report.append("")
        
        long_term_trends = [
            "**人工智能与自主系统**: 机器学习算法在卫星数据处理、故障诊断、任务规划中的应用持续深化，推动卫星系统向智能化、自主化方向发展。",
            "**小型化与星座规模化**: 微纳卫星技术成熟推动大型星座部署，Starlink、OneWeb等星座规模持续扩大，改变传统卫星应用模式。",
            "**商业航天生态完善**: 商业发射服务、卫星制造、数据应用等产业链环节日趋成熟，推动技术创新和成本降低。",
            "**多源数据融合应用**: GNSS、遥感、气象、通信等多源数据融合，催生新的应用场景和服务模式。",
            "**实时服务能力提升**: 低轨卫星星座和星间链路技术发展，显著提升数据获取到应用服务的响应时间。",
            "**可持续航天发展**: 可重复使用火箭、在轨服务、空间碎片清理等技术受到关注，推动航天可持续发展。"
        ]
        
        for i, trend in enumerate(long_term_trends, 1):
            report.append(f"**趋势{i}**: {trend}")
            report.append("")
        
        # 技术建议与展望
        report.append("## 5. 技术建议与展望")
        report.append("")
        
        report.append("### 5.1 技术发展建议")
        report.append("")
        
        if recommendations:
            report.append("基于本周期技术事件分析，提出以下发展建议：")
            report.append("")
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
        else:
            report.append("> 需要更多数据支持具体技术建议")
            report.append("")
        
        report.append("### 5.2 重点技术领域展望")
        report.append("")
        
        tech_outlook = [
            "**GNSS增强技术**: 多频多系统、PPP-RTK、低轨增强等技术将持续发展，提升定位精度和可靠性。",
            "**卫星通信技术**: 高通量卫星、星间链路、太赫兹通信等技术推动卫星互联网和天地一体化网络发展。",
            "**遥感技术**: 高光谱、合成孔径雷达、激光雷达等新型遥感技术拓展地球观测能力。",
            "**气象监测技术**: 微波探测、GNSS掩星、激光雷达等新技术提升气象预报精度和时效性。",
            "**空间科学仪器**: 新型探测器和科学载荷推动空间科学研究和深空探测能力提升。"
        ]
        
        for i, outlook in enumerate(tech_outlook, 1):
            report.append(f"**领域{i}**: {outlook}")
            report.append("")
        
        # 数据与访问说明
        report.append("## 6. 数据与访问说明")
        report.append("")
        
        # report.append("### 6.1 数据来源")
        # report.append("")
        report.append("本报告基于以下数据源：")
        report.append("")
        report.append("1. **多源新闻聚合**: 整合NASA、ESA、SpaceNews、Space.com、GPS World等权威媒体和技术网站")
        report.append("2. **技术报告**: 航天机构、研究机构发布的技术报告和研究成果")
        report.append("3. **行业动态**: 商业航天公司、技术供应商发布的新闻和公告")
        report.append("")
        
        # report.append("### 6.2 网站数据访问")
        # report.append("")
        # report.append("本报告相关数据可通过以下链接访问：")
        # report.append("")
        # report.append(f"- **交互式数据可视化**: [https://gnss-x.ac.cn/satellite-news/data/](https://gnss-x.ac.cn/satellite-news/data/)")
        # report.append(f"- **新闻分类统计图表**: [https://gnss-x.ac.cn/satellite-news/charts/](https://gnss-x.ac.cn/satellite-news/charts/)")
        # report.append(f"- **技术趋势分析**: [https://gnss-x.ac.cn/satellite-news/trends/](https://gnss-x.ac.cn/satellite-news/trends/)")
        # report.append("")
        
        # 添加Cursor深度分析（如果存在）
        if cursor_analysis and len(cursor_analysis.strip()) > 100:
            report.append("## 7. AI深度分析")
            report.append("")
            report.append("### 7.1 Cursor AI分析结果")
            report.append("")
            report.append("---")
            report.append("")
            report.append(cursor_analysis)
            report.append("")
            report.append("---")
            report.append("")
            report.append("### 7.2 分析说明")
            report.append("")
            report.append("以上分析由Cursor AI基于专业提示生成，结合卫星、GNSS和气象领域的专业知识，提供深度技术洞察和市场趋势分析。")
            report.append("")
        
        report.append("---")
        report.append("")
        report.append("**报告结束**")
        report.append("")
        report.append("*本报告由Mapoet助手卫星技术分析系统自动生成，仅供参考和研究使用。*")
        
        return "\n".join(report)
    
    def _category_one_liner(self, cat, category_headlines, by_category_md, max_len=200):
        """一句话概述：优先分领域分析首句，否则用标题拼接。"""
        md = (by_category_md or {}).get(cat, {}).get("markdown") if isinstance(by_category_md, dict) else None
        if md:
            plain = re.sub(r"#{1,6}\s*", "", md)
            plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", plain)
            plain = re.sub(r"`[^`]+`", "", plain).strip()
            for line in plain.split("\n"):
                line = line.strip()
                if len(line) >= 20:
                    return (line[:max_len] + "…") if len(line) > max_len else line
        titles = (category_headlines or {}).get(cat) or []
        if not titles:
            return "（暂无该类标题摘录）"
        chunk = "；".join(titles[:3])
        return (chunk[:max_len] + "…") if len(chunk) > max_len else chunk

    def _render_category_pie(self, categories):
        """返回 (markdown_image_line_or_none, fallback_bullet_lines)。"""
        if not categories:
            return None, []
        total = sum(categories.values())
        if total <= 0:
            return None, []
        fallback = []
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            fallback.append(f"- **{cat}**: {count}篇 ({pct:.1f}%)")
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception:
            return None, fallback
        try:
            labels = []
            sizes = []
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    labels.append(str(cat))
                    sizes.append(count)
            if not sizes:
                return None, fallback
            # 与 HTML 同目录保存一份，避免 `output/html/*.html` 引用 `assets/` 时 404；
            # 同时在 `reports/markdown/assets` 留副本，便于单独打开 .md。
            os.makedirs("reports/markdown/assets", exist_ok=True)
            os.makedirs("output/html/assets", exist_ok=True)
            fn = f"category_pie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            md_assets = os.path.join("reports/markdown/assets", fn)
            html_assets = os.path.join("output/html/assets", fn)
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            plt.tight_layout()
            plt.savefig(md_assets, dpi=120, bbox_inches="tight")
            plt.close(fig)
            shutil.copy2(md_assets, html_assets)
            rel = f"assets/{fn}"
            return f"![分类分布]({rel})", []
        except Exception:
            return None, fallback

    def _append_section_1_1_pie_and_table(
        self, report, categories, category_headlines, by_category_md, category_taglines=None
    ):
        if not categories:
            return
        report.append("### 1.1 分类分布")
        report.append("")
        img_line, fallback = self._render_category_pie(categories)
        if img_line:
            report.append(img_line)
            report.append("")
        else:
            report.extend(fallback)
            report.append("")
        report.append("**类别 / 关键词一览（一句话概述）**")
        report.append("")
        report.append("| 类别（关键词） | 篇数 | 一句话概述 |")
        report.append("|:---|:---:|:---|")
        tag_map = category_taglines if isinstance(category_taglines, dict) else {}
        total = sum(categories.values()) or 1
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            one = (tag_map.get(cat) or "").strip()
            if not one:
                one = self._category_one_liner(cat, category_headlines, by_category_md)
            one_esc = one.replace("|", "\\|").replace("\n", " ")
            report.append(f"| **{cat}** | {count} ({pct:.1f}%) | {one_esc} |")
        report.append("")

    def _append_section_1_2_important(self, report, important_articles, by_article_list):
        if not important_articles:
            return
        report.append("### 1.2 重要新闻概览")
        report.append("")
        for i, article in enumerate(important_articles[:5], 1):
            title_line = (article.get("title", "") or "").replace("\n", " ").strip()
            title_line = re.sub(r"^#+\s*", "", title_line)
            report.append(f"### {i}. {title_line}")
            report.append("")
            report.append(
                f"来源: {article.get('source', '')} | 重要性: {article.get('importance', 0)}/10"
            )
            summ = article.get("summary", "") or ""
            tail = "…" if len(summ) > 150 else ""
            report.append(f"摘要: {summ[:150]}{tail}")
            report.append("")
            block = (
                by_article_list[i - 1]
                if by_article_list and len(by_article_list) >= i
                else None
            )
            if block and (block.get("markdown") or "").strip():
                if not block.get("fetch_ok"):
                    w = block.get("fetch_warning") or "未能抓取原文"
                    report.append(f"> **原文抓取警告**：{w}。以下分析可能主要依据摘要。")
                    report.append("")
                report.append("---")
                report.append("")
                report.append(
                    "**AI 精读**（基于摘要与网页摘录；与上文条目对应，非独立大节标题）"
                )
                report.append("")
                report.append(self._clean_cursor_analysis(block.get("markdown", "")))
                report.append("")

    def _append_section_2_ai(self, report, analysis_tasks, cursor_analysis):
        report.append("## （二）AI深度分析")
        report.append("")
        report.append("---")
        report.append("")
        sections = (
            (analysis_tasks or {}).get("sections")
            if isinstance(analysis_tasks, dict)
            else None
        )
        if not sections:
            report.append(cursor_analysis)
            report.append("")
            report.append("---")
            report.append("")
            return
        es = sections.get("executive_summary") or {}
        if (es.get("markdown") or "").strip():
            report.append("### 2.1 执行摘要")
            report.append("")
            report.append(self._clean_cursor_analysis(es.get("markdown", "")))
            report.append("")
        by_cat = sections.get("by_category") or {}
        if by_cat:
            report.append("### 2.2 分领域技术分析")
            report.append("")
            for cat in sorted(by_cat.keys()):
                report.append("---")
                report.append("")
                report.append(f"**分领域 · `{cat}`**")
                report.append("")
                report.append(
                    self._clean_cursor_analysis((by_cat[cat] or {}).get("markdown", ""))
                )
                report.append("")
        for key, title in (
            ("market", "2.3 市场与商业洞察"),
            ("policy", "2.4 政策与监管分析"),
            ("trends", "2.5 趋势预测"),
            ("recommendations", "2.6 专业建议"),
        ):
            blk = sections.get(key) or {}
            if (blk.get("markdown") or "").strip():
                report.append(f"### {title}")
                report.append("")
                report.append(self._clean_cursor_analysis(blk.get("markdown", "")))
                report.append("")
        structured_had_body = bool(
            (es.get("markdown") or "").strip()
            or any((v or {}).get("markdown", "").strip() for v in by_cat.values())
            or any(
                (sections.get(k) or {}).get("markdown", "").strip()
                for k in ("market", "policy", "trends", "recommendations")
            )
        )
        if structured_had_body:
            report.append(
                "> **说明**：各条重点新闻的逐条 AI 精读见上文 **§1.2 重要新闻概览**。"
            )
            report.append("")
        else:
            report.append("### 2.x 合并分析稿")
            report.append("")
            report.append(cursor_analysis)
            report.append("")
        report.append("---")
        report.append("")

    def _generate_simplified_report(self, analysis, cursor_analysis):
        """生成简化版报告（主要使用Cursor分析）"""
        metadata = analysis.get('metadata', {})
        categories = analysis.get('categories', {})
        category_headlines = analysis.get('category_headlines', {})
        category_taglines = analysis.get("category_taglines") or {}
        analysis_tasks = analysis.get('analysis_tasks')
        important_articles = analysis.get('important_articles', [])
        by_article_list = (
            ((analysis_tasks or {}).get("sections") or {}).get("by_article") or []
            if isinstance(analysis_tasks, dict)
            else []
        )
        by_category_md = (
            ((analysis_tasks or {}).get("sections") or {}).get("by_category") or {}
            if isinstance(analysis_tasks, dict)
            else {}
        )

        report = []
        gen_time = metadata.get('generated_at') or metadata.get('analysis_time') or datetime.now().isoformat()

        # 报告标题和元数据
        report.append(f"# 卫星技术发展日报 - 科学分析报告")
        report.append("")
        report.append(f"**报告编号**: SAT-TECH-{datetime.now().strftime('%Y%m%d')}")
        report.append(f"**生成时间**: {gen_time}")
        report.append(f"**分析周期**: 过去24小时")
        report.append(f"**数据样本**: {metadata.get('total_articles', 0)}篇技术新闻")
        report.append(f"**重要新闻**: {metadata.get('important_articles', 0)}篇 (重要性≥6)")
        report.append(f"**数据可视化**: [https://gnss-x.ac.cn/satellite-news/charts/](https://gnss-x.ac.cn/satellite-news/charts/)")
        report.append("")
        report.append("---")
        report.append("")
        
        # 1. 执行摘要
        report.append("## （一）内容摘要")
        report.append("")
        report.append(f"本报告基于{metadata.get('total_articles', 0)}篇卫星技术相关新闻报道，涵盖GNSS系统、卫星星座、运载火箭、载荷技术、气象系统等关键技术领域。")
        report.append("")
        
        if categories:
            self._append_section_1_1_pie_and_table(
                report, categories, category_headlines, by_category_md, category_taglines
            )

        self._append_section_1_2_important(report, important_articles, by_article_list)

        self._append_section_2_ai(report, analysis_tasks, cursor_analysis)
        
        # 3. 数据与访问说明
        report.append("##（三）数据与访问说明")
        # report.append("")
        # report.append("### 3.1 数据来源")
        report.append("")
        report.append("本报告基于多源新闻聚合，整合NASA、ESA、SpaceNews、Space.com、GPS World等权威媒体和技术网站。")
        report.append("")
        
        # report.append("### 3.2 网站数据访问")
        # report.append("")
        # report.append("本报告相关数据可通过以下链接访问：")
        # report.append("")
        #report.append(f"- **交互式数据可视化**: [https://gnss-x.ac.cn/satellite-news/data/](https://gnss-x.ac.cn/satellite-news/data/)")
        #report.append(f"- **新闻分类统计图表**: [https://gnss-x.ac.cn/satellite-news/charts/](https://gnss-x.ac.cn/satellite-news/charts/)")
        #report.append(f"- **技术趋势分析**: [https://gnss-x.ac.cn/satellite-news/trends/](https://gnss-x.ac.cn/satellite-news/trends/)")
        report.append("")
        
        report.append("---")
        report.append("")
        report.append("**报告结束**")
        report.append("")
        report.append("*本报告由Mapoet助手卫星技术分析系统自动生成，仅供参考和研究使用。*")
        
        return "\n".join(report)
    
    def save_report(self, markdown_content):
        """保存Markdown报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # 创建目录
        os.makedirs("reports/markdown", exist_ok=True)
        os.makedirs("reports/daily", exist_ok=True)
        
        # 保存Markdown文件
        md_file = f"reports/markdown/report_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 保存为最新报告
        latest_md = "reports/markdown/latest_report.md"
        with open(latest_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 同时保存为文本格式（兼容旧系统）
        txt_file = f"reports/daily/analysis_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            # 将Markdown转换为纯文本
            text_content = re.sub(r'#+\s*', '', markdown_content)  # 移除标题标记
            text_content = re.sub(r'\*\*(.*?)\*\*', r'\1', text_content)  # 移除粗体
            text_content = re.sub(r'\*([^*]+)\*', r'\1', text_content)  # 移除斜体
            text_content = re.sub(r'!\[.*?\]\(.*?\)', '', text_content)  # 移除图片
            text_content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text_content)  # 移除链接
            f.write(text_content)
        
        # 更新最新文本报告
        latest_txt = "reports/daily/latest_analysis.txt"
        with open(latest_txt, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        print(f"💾 Markdown报告已保存:")
        print(f"   Markdown文件: {md_file}")
        print(f"   最新Markdown: {latest_md}")
        print(f"   文本报告: {txt_file}")
        print(f"   最新文本报告: {latest_txt}")
        
        return md_file, txt_file

def main(analysis_file):
    """主函数"""
    print("=" * 80)
    print("Markdown报告生成器")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    generator = MarkdownGenerator()
    
    try:
        # 加载分析数据
        analysis = generator.load_analysis(analysis_file)
        
        if not analysis:
            print("❌ 无分析数据可生成报告")
            return None
        
        print(f"📊 基于分析数据生成报告...")
        
        # 生成Markdown报告
        markdown_content = generator.generate_report(analysis)
        
        # 保存报告
        md_file, txt_file = generator.save_report(markdown_content)
        
        # 打印报告摘要
        print("\n📋 报告摘要:")
        print("-" * 40)
        
        # 显示报告开头部分
        lines = markdown_content.split('\n')
        for line in lines[:20]:  # 显示前20行
            print(line)
        
        print("... [完整报告已保存] ...")
        
        # 统计信息
        word_count = len(markdown_content.split())
        section_count = markdown_content.count('## ')
        
        print(f"\n📊 报告统计:")
        print(f"   字数: {word_count}字")
        print(f"   章节: {section_count}节")
        print(f"   文件大小: {len(markdown_content.encode('utf-8')) / 1024:.1f}KB")
        
        return md_file, txt_file
        
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python markdown_generator.py <analysis_file>")
        sys.exit(1)
    
    main(sys.argv[1])