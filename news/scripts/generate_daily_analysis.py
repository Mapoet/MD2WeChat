#!/usr/bin/env python3
"""
生成每日卫星新闻分析 - 多子任务 Cursor 深度分析
输入: 新闻JSON文件
输出: 分析结果JSON文件（供 markdown_generator.py 使用）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from cursor_analysis_tools import (
    CATEGORY_ARTICLE_M,
    CATEGORY_MIN_COUNT,
    CursorAgentClient,
    ArticleBodyFetcher,
    PromptTemplates,
    TIMEOUT_ARTICLE,
    TIMEOUT_CATEGORY,
    TIMEOUT_SECTION,
    TIMEOUT_SUMMARY,
    IMPORTANT_ARTICLE_LIMIT,
    build_category_headlines,
    parse_category_taglines,
    section_dict_result,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _articles_by_category(articles: List[dict]) -> Dict[str, List[dict]]:
    by_cat: Dict[str, List[dict]] = {}
    for a in articles:
        c = a.get("category") or "other"
        by_cat.setdefault(c, []).append(a)
    return by_cat


def _sort_by_importance(lst: List[dict]) -> List[dict]:
    return sorted(
        lst,
        key=lambda x: (x.get("importance") or 0, x.get("title") or ""),
        reverse=True,
    )


def _basic_fallback_markdown(
    articles: List[dict], categories: Dict[str, int], important: List[dict]
) -> str:
    lines = [
        "## 执行摘要",
        "",
        "⚠️ Cursor 子任务均未成功完成，以下为基于统计的占位摘要。",
        "",
        "## 分类统计",
    ]
    for c, n in sorted(categories.items(), key=lambda x: -x[1]):
        lines.append(f"- **{c}**: {n} 篇")
    lines.extend(["", "## 重要新闻标题（重要性≥6）", ""])
    for a in important[:8]:
        lines.append(f"- {a.get('title', '')}（{a.get('source', '')}）")
    lines.append("")
    lines.append(f"总稿件数: {len(articles)}")
    return "\n".join(lines)


def generate_daily_analysis(news_file: str) -> Any:
    project_root = _project_root()
    output_dir = project_root / "data" / "analysis" / "daily"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("卫星新闻 Cursor 多子任务深度分析")
    print("=" * 70)

    print(f"\n1. 加载新闻数据: {news_file}")
    try:
        with open(news_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        articles = data.get("articles", [])
        if not articles:
            print("   没有新闻数据")
            return None
        print(f"   加载了 {len(articles)} 条新闻")
    except Exception as e:
        print(f"   加载失败: {e}")
        return None

    categories: Dict[str, int] = {}
    for a in articles:
        cat = a.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    important_all = [a for a in articles if a.get("importance", 0) >= 6]
    important_sorted = _sort_by_importance(important_all)
    important_top = important_sorted[:IMPORTANT_ARTICLE_LIMIT]

    category_headlines = build_category_headlines(articles, max_titles_per_cat=5)

    sources: Dict[str, int] = {}
    for a in articles:
        s = a.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    client = CursorAgentClient()
    fetcher = ArticleBodyFetcher()
    t0 = time.monotonic()
    total_calls = 0

    category_taglines: Dict[str, str] = {}
    if categories:
        tag_prompt = PromptTemplates.category_taglines_batch(categories, category_headlines)
        print("\n   [category_taglines] cursor-agent …")
        res_tags = client.run(tag_prompt, timeout=TIMEOUT_SECTION)
        total_calls += 1
        if res_tags.ok:
            category_taglines = parse_category_taglines(res_tags.markdown)
            if category_taglines:
                print(f"      解析到 {len(category_taglines)} 条类别概述")
        else:
            print(f"      失败: {res_tags.error}")

    sections: Dict[str, Any] = {
        "executive_summary": {"markdown": "", "ok": False, "error": None},
        "by_category": {},
        "by_article": [],
        "market": {"markdown": "", "ok": False, "error": None},
        "policy": {"markdown": "", "ok": False, "error": None},
        "trends": {"markdown": "", "ok": False, "error": None},
        "recommendations": {"markdown": "", "ok": False, "error": None},
    }

    shared = PromptTemplates.shared_context(categories, important_sorted[:20])

    # --- 1) Per category ---
    by_cat_map = _articles_by_category(articles)
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        if count < CATEGORY_MIN_COUNT:
            continue
        samples = _sort_by_importance(by_cat_map.get(cat, []))[:CATEGORY_ARTICLE_M]
        if not samples:
            continue
        prompt = PromptTemplates.category_analysis(cat, count, samples)
        print(f"\n   [category:{cat}] cursor-agent …")
        res = client.run(prompt, timeout=TIMEOUT_CATEGORY)
        total_calls += 1
        sections["by_category"][cat] = section_dict_result(res)
        if not res.ok:
            print(f"      失败: {res.error}")

    # --- 2) Per important article (fetch + analyze) ---
    for idx, article in enumerate(important_top):
        url = article.get("url") or ""
        fr = fetcher.fetch(url)
        body = fr.text if fr.ok else ""
        prompt = PromptTemplates.important_article_analysis(
            article, body, fr.ok, fr.warning
        )
        print(f"\n   [article:{idx + 1}/{len(important_top)}] cursor-agent …")
        res = client.run(prompt, timeout=TIMEOUT_ARTICLE)
        total_calls += 1
        sections["by_article"].append(
            {
                "title": article.get("title", ""),
                "url": url,
                "fetch_ok": fr.ok,
                "fetch_warning": fr.warning,
                "body_excerpt": body[:8000] if body else "",
                **section_dict_result(res),
            }
        )
        if not res.ok:
            print(f"      失败: {res.error}")

    # --- 3) Four section tasks ---
    runners: List[Tuple[str, str]] = [
        ("market", PromptTemplates.section_market(shared)),
        ("policy", PromptTemplates.section_policy(shared)),
        ("trends", PromptTemplates.section_trends(shared)),
        ("recommendations", PromptTemplates.section_recommendations(shared)),
    ]
    for key, prompt in runners:
        print(f"\n   [{key}] cursor-agent …")
        res = client.run(prompt, timeout=TIMEOUT_SECTION)
        total_calls += 1
        sections[key] = section_dict_result(res)
        if not res.ok:
            print(f"      失败: {res.error}")

    # --- 4) Executive summary from snippets ---
    snippets: List[Tuple[str, str]] = []
    if sections["executive_summary"].get("markdown"):
        pass
    for cat, block in sections["by_category"].items():
        snippets.append((f"分领域:{cat}", block.get("markdown") or ""))
    for key in ("market", "policy", "trends", "recommendations"):
        snippets.append((key, sections[key].get("markdown") or ""))
    for i, block in enumerate(sections["by_article"]):
        snippets.append((f"重点新闻{i + 1}", block.get("markdown") or ""))

    summ_prompt = PromptTemplates.executive_summary(snippets)
    print("\n   [executive_summary] cursor-agent …")
    res_sum = client.run(summ_prompt, timeout=TIMEOUT_SUMMARY)
    total_calls += 1
    sections["executive_summary"] = section_dict_result(res_sum)
    if not res_sum.ok:
        print(f"      失败: {res_sum.error}")

    # --- Assemble combined markdown for legacy consumers ---
    parts: List[str] = []

    es = sections["executive_summary"].get("markdown") or ""
    parts.append("## 执行摘要\n\n" + es + "\n\n---\n\n")

    parts.append("## 分领域技术分析\n\n")
    for cat in sorted(sections["by_category"].keys()):
        block = sections["by_category"][cat]
        parts.append(f"### 类别 `{cat}`\n\n" + (block.get("markdown") or "") + "\n\n")
    parts.append("---\n\n")

    parts.append("## 市场与商业洞察\n\n" + (sections["market"].get("markdown") or "") + "\n\n---\n\n")
    parts.append("## 政策与监管分析\n\n" + (sections["policy"].get("markdown") or "") + "\n\n---\n\n")
    parts.append("## 趋势预测\n\n" + (sections["trends"].get("markdown") or "") + "\n\n---\n\n")
    parts.append("## 专业建议\n\n" + (sections["recommendations"].get("markdown") or "") + "\n\n---\n\n")

    parts.append("## 重点新闻精读\n\n")
    for block in sections["by_article"]:
        title = block.get("title") or "(无标题)"
        parts.append(f"### {title}\n\n")
        if not block.get("fetch_ok"):
            w = block.get("fetch_warning") or "未抓取到原文"
            parts.append(f"> **原文抓取**：{w}\n\n")
        parts.append((block.get("markdown") or "") + "\n\n---\n\n")

    combined = "".join(parts).strip()
    has_any_ok = (
        bool(sections["executive_summary"].get("ok"))
        or any(b.get("ok") for b in sections["by_category"].values())
        or any(b.get("ok") for b in sections["by_article"])
        or bool(sections["market"].get("ok"))
        or bool(sections["policy"].get("ok"))
        or bool(sections["trends"].get("ok"))
        or bool(sections["recommendations"].get("ok"))
    )
    if len(combined) < 200 or not has_any_ok:
        combined = _basic_fallback_markdown(articles, categories, important_sorted)

    duration_ms = int((time.monotonic() - t0) * 1000)

    analysis_result = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "news_file": news_file,
            "total_articles": len(articles),
            "important_articles": len(important_all),
            "analysis_type": "cursor_daily_analysis_v2",
            "task_counts": {
                "category_taglines_batch": 1 if categories else 0,
                "categories": len(sections["by_category"]),
                "articles": len(sections["by_article"]),
                "section_tasks": 4,
                "executive_summary": 1,
            },
            "total_cursor_calls": total_calls,
            "duration_ms": duration_ms,
        },
        "statistics": {
            "categories": categories,
            "category_headlines": category_headlines,
            "category_taglines": category_taglines,
            "sources": sources,
            "importance_distribution": {
                "high": len([a for a in articles if a.get("importance", 0) >= 8]),
                "medium": len([a for a in articles if 5 <= a.get("importance", 0) < 8]),
                "low": len([a for a in articles if a.get("importance", 0) < 5]),
            },
            "avg_importance": sum(a.get("importance", 0) for a in articles) / len(articles)
            if articles
            else 0,
        },
        "important_articles": important_sorted[:10],
        "cursor_analysis": combined,
        "analysis_tasks": {"sections": sections},
        "summary": {
            "key_trends": [],
            "technical_insights": [],
            "market_analysis": [],
            "recommendations": [],
        },
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"daily_analysis_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print(f"\n2. 分析结果已保存: {output_file}")
    latest_file = output_dir / "latest_analysis.json"
    try:
        if latest_file.exists() or latest_file.is_symlink():
            latest_file.unlink()
        latest_file.symlink_to(output_file.name)
        print(f"   最新链接: {latest_file}")
    except Exception as e:
        print(f"   创建 latest 链接失败: {e}")

    print("\n" + "=" * 70)
    print("每日分析完成")
    print(f"cursor-agent 调用次数: {total_calls}，耗时约 {duration_ms} ms")
    print("=" * 70)

    return {
        "success": True,
        "analysis_file": str(output_file),
        "latest_file": str(latest_file),
        "statistics": {
            "total_articles": len(articles),
            "important_articles": len(important_all),
            "analysis_length": len(combined),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成每日卫星新闻分析（多子任务）")
    parser.add_argument("news_file", help="新闻JSON文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径（可选）")
    args = parser.parse_args()

    if not os.path.exists(args.news_file):
        print(f"新闻文件不存在: {args.news_file}")
        sys.exit(1)

    result = generate_daily_analysis(args.news_file)
    if not result:
        sys.exit(1)

    if args.output:
        try:
            import shutil

            shutil.copy2(result["analysis_file"], args.output)
            print(f"结果已复制到: {args.output}")
        except Exception as e:
            print(f"复制失败: {e}")


if __name__ == "__main__":
    main()
