#!/usr/bin/env python3
"""
Shared helpers for multi-task cursor-agent analysis: prompts, subprocess runner, article body fetch.

Headless invocation matches: cursor-agent -p --output-format <text|json> --model <name> -f
Environment overrides: CURSOR_AGENT_CMD, CURSOR_AGENT_MODEL (default auto),
CURSOR_AGENT_OUTPUT_FORMAT (default text), CURSOR_TIMEOUT_* .
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# --- Environment-driven config ---

DEFAULT_AGENT_CMD = os.environ.get("CURSOR_AGENT_CMD", "cursor-agent")
# headless：-p + --output-format；--model auto 走 Auto 路由； -f 为 --force（非交互允许命令）
DEFAULT_AGENT_MODEL = os.environ.get("CURSOR_AGENT_MODEL", "auto")
DEFAULT_OUTPUT_FORMAT = os.environ.get("CURSOR_AGENT_OUTPUT_FORMAT", "text")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


TIMEOUT_DEFAULT = _int_env("CURSOR_TIMEOUT_DEFAULT", 300)
TIMEOUT_CATEGORY = _int_env("CURSOR_TIMEOUT_CATEGORY", TIMEOUT_DEFAULT)
TIMEOUT_ARTICLE = _int_env("CURSOR_TIMEOUT_ARTICLE", TIMEOUT_DEFAULT)
TIMEOUT_SECTION = _int_env("CURSOR_TIMEOUT_SECTION", TIMEOUT_DEFAULT)
TIMEOUT_SUMMARY = _int_env("CURSOR_TIMEOUT_SUMMARY", TIMEOUT_DEFAULT)

ARTICLE_BODY_MAX_CHARS = _int_env("ARTICLE_BODY_MAX_CHARS", 20000)
FETCH_TIMEOUT_SEC = _int_env("ARTICLE_FETCH_TIMEOUT_SEC", 22)
FETCH_MAX_BYTES = _int_env("ARTICLE_FETCH_MAX_BYTES", 2_000_000)

IMPORTANT_ARTICLE_LIMIT = _int_env("CURSOR_IMPORTANT_ARTICLE_LIMIT", 5)
CATEGORY_ARTICLE_M = _int_env("CURSOR_CATEGORY_ARTICLE_M", 12)
IMPORTANT_SUMMARY_MAX = _int_env("CURSOR_IMPORTANT_SUMMARY_MAX", 700)
CATEGORY_MIN_COUNT = _int_env("CURSOR_CATEGORY_MIN_COUNT", 1)

# §1.1 批量一句话（字符上限，含标点）
CATEGORY_TAGLINE_MAX_CHARS = _int_env("CATEGORY_TAGLINE_MAX_CHARS", 30)


@dataclass
class CursorAgentResult:
    ok: bool
    markdown: str
    error: Optional[str] = None
    returncode: Optional[int] = None
    stderr: Optional[str] = None


@dataclass
class FetchResult:
    ok: bool
    text: str
    warning: Optional[str] = None


class CursorAgentClient:
    """Runs cursor-agent -p --output-format <fmt> --model <model> -f with stdin prompt."""

    def __init__(
        self,
        cmd: Optional[List[str]] = None,
        agent_cmd: Optional[str] = None,
        model: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> None:
        base = agent_cmd or DEFAULT_AGENT_CMD
        self._model = (model if model is not None else DEFAULT_AGENT_MODEL).strip()
        self._output_format = (
            output_format if output_format is not None else DEFAULT_OUTPUT_FORMAT
        ).strip().lower()
        if cmd is not None:
            self._cmd_prefix = cmd
        else:
            self._cmd_prefix = [
                base,
                "-p",
                "--output-format",
                self._output_format,
                "--model",
                self._model,
                "-f",
            ]

    @staticmethod
    def _coerce_stdout(stdout: str, output_format: str) -> str:
        raw = (stdout or "").strip()
        if output_format != "json":
            return raw
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(data, str):
            return data.strip()
        if isinstance(data, dict):
            for key in (
                "result",
                "response",
                "content",
                "message",
                "output",
                "text",
                "answer",
            ):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            for key in ("choices", "messages"):
                arr = data.get(key)
                if isinstance(arr, list) and arr:
                    item = arr[0]
                    if isinstance(item, dict):
                        for k in ("content", "message", "text"):
                            v = item.get(k)
                            if isinstance(v, str) and v.strip():
                                return v.strip()
        return raw

    def run(self, prompt: str, *, timeout: int = TIMEOUT_DEFAULT) -> CursorAgentResult:
        if not shutil.which(self._cmd_prefix[0]):
            return CursorAgentResult(
                ok=False,
                markdown="",
                error=f"executable not found: {self._cmd_prefix[0]}",
                returncode=-1,
            )
        try:
            proc = subprocess.run(
                self._cmd_prefix,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = self._coerce_stdout(proc.stdout or "", self._output_format)
            err = (proc.stderr or "").strip()
            if proc.returncode == 0 and out:
                return CursorAgentResult(
                    ok=True, markdown=out, returncode=proc.returncode, stderr=err or None
                )
            err_msg = (err or "").strip() or f"exit {proc.returncode}"
            return CursorAgentResult(
                ok=False,
                markdown="",
                error=err_msg[:2000],
                returncode=proc.returncode,
                stderr=err or None,
            )
        except subprocess.TimeoutExpired:
            return CursorAgentResult(ok=False, markdown="", error="timeout", returncode=-2)
        except Exception as e:
            return CursorAgentResult(ok=False, markdown="", error=str(e), returncode=-3)


class ArticleBodyFetcher:
    """Fetch and extract plain text from news URLs."""

    _HARD_SKIP = re.compile(
        r"(twitter\.com|x\.com/|youtube\.com|youtu\.be|\.mp4(\?|$)|\.pdf(\?|$))",
        re.I,
    )

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )

    def _should_skip(self, url: str) -> Optional[str]:
        if not url or not url.startswith("http"):
            return "无效或非 HTTP URL"
        if self._HARD_SKIP.search(url):
            return "该 URL 类型（社交媒体/视频/二进制）不适合自动抓取正文"
        return None

    def fetch(self, url: str, *, retry_once: bool = True) -> FetchResult:
        skip = self._should_skip(url)
        if skip:
            return FetchResult(ok=False, text="", warning=skip)

        last_err: Optional[str] = None
        for attempt in range(2 if retry_once else 1):
            try:
                resp = self.session.get(
                    url,
                    timeout=FETCH_TIMEOUT_SEC,
                    stream=True,
                    allow_redirects=True,
                )
                if resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code}"
                    continue
                raw = b""
                for chunk in resp.iter_content(chunk_size=65536):
                    raw += chunk
                    if len(raw) >= FETCH_MAX_BYTES:
                        break
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if "html" not in ctype and not raw.lstrip().startswith(b"<"):
                    return FetchResult(
                        ok=False,
                        text="",
                        warning="响应非 HTML，跳过正文提取",
                    )
                html = raw.decode(resp.encoding or "utf-8", errors="replace")
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                text = re.sub(r"\n{3,}", "\n\n", text).strip()
                if not text:
                    last_err = "正文为空"
                    continue
                if len(text) > ARTICLE_BODY_MAX_CHARS:
                    text = text[:ARTICLE_BODY_MAX_CHARS] + "\n\n[已截断]"
                return FetchResult(ok=True, text=text, warning=None)
            except requests.RequestException as e:
                last_err = str(e)
        return FetchResult(ok=False, text="", warning=last_err or "抓取失败")


def parse_category_taglines(stdout: str, *, max_chars: int = CATEGORY_TAGLINE_MAX_CHARS) -> Dict[str, str]:
    """Parse JSON object from agent stdout; values truncated to max_chars."""
    s = (stdout or "").strip()
    if not s:
        return {}
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if m:
        s = m.group(1).strip()
    else:
        i = s.find("{")
        j = s.rfind("}")
        if i >= 0 and j > i:
            s = s[i : j + 1]
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in data.items():
        key = str(k).strip()
        if not key:
            continue
        if isinstance(v, str):
            val = v.strip()
        else:
            val = str(v).strip() if v is not None else ""
        if val:
            out[key] = val[:max_chars]
    return out


class PromptTemplates:
    """Render prompts for each cursor-agent subtask."""

    ROLE = "你是卫星、GNSS、导航与气象遥感领域的资深分析师。"

    RETRIEVAL = (
        "【检索】若具备联网或文献检索工具，请检索与主题相关的最新公开报道、行业动态与权威技术资料"
        "（含论文或标准要点），并结合下方用户给定材料；若无法检索，用一两句话说明分析依据仅限所给材料。"
    )

    ANTI_META = (
        "【写作纪律】禁止在输出中复述本提示的任务说明、规则或格式要求；禁止使用「根据上述要求」「本节将」等元话语；"
        "勿输出提示条文；直接给出可阅读的专业内容。"
    )

    STRUCTURED_BODY = (
        "【形态】以科技报告体段落为主；在有助于读者理解时，可穿插 Markdown 表格、无序列表、"
        "以及 Mermaid 图（使用 ```mermaid 代码围栏）。不必每次分析都强行凑齐表、列表与图；"
        "材料单薄时以清晰段落为主即可。\n"
        "【禁止】不要使用 Markdown 标题行（不得以 # 开头的新行划分小节）。允许 **加粗** 与代码块。"
    )

    @classmethod
    def _base_analysis(cls) -> str:
        return (
            f"{cls.ROLE}\n\n{cls.RETRIEVAL}\n\n{cls.ANTI_META}\n\n{cls.STRUCTURED_BODY}\n\n---\n\n"
        )

    @staticmethod
    def format_categories_block(categories: Dict[str, int]) -> str:
        total = sum(categories.values()) or 1
        lines = []
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            pct = 100.0 * count / total
            lines.append(f"- {cat}: {count} 篇 ({pct:.1f}%)")
        return "（以下为供你分析的背景：全量分类统计）\n" + "\n".join(lines)

    @staticmethod
    def format_important_list(
        important: List[dict], *, summary_max: int = IMPORTANT_SUMMARY_MAX
    ) -> str:
        lines = ["（以下为供你分析的背景：重要新闻标题与摘要，不含网页全文）"]
        for i, a in enumerate(important, 1):
            summ = (a.get("summary") or "")[:summary_max]
            lines.append(
                f"{i}. 【{a.get('source', '')}】{a.get('title', '')}\n"
                f"   重要性: {a.get('importance', 0)}/10\n"
                f"   摘要: {summ}"
            )
        return "\n".join(lines)

    @classmethod
    def shared_context(
        cls,
        categories: Dict[str, int],
        important: List[dict],
    ) -> str:
        return (
            cls.format_categories_block(categories)
            + "\n\n"
            + cls.format_important_list(important)
        )

    @classmethod
    def category_taglines_batch(
        cls,
        categories: Dict[str, int],
        category_headlines: Dict[str, List[str]],
    ) -> str:
        mx = CATEGORY_TAGLINE_MAX_CHARS
        body = f"{cls.ROLE}\n\n{cls.RETRIEVAL}\n\n{cls.ANTI_META}\n\n"
        body += (
            f"【任务】下面每个「类别」对应当日新闻稿件。请为**每一个类别**各写**一句**中文概述，"
            f"概括该类稿件当日的聚焦方向。每句不超过 {mx} 个字符（含标点），宜为高密度名词短语。\n\n"
        )
        body += "【类别与篇数】\n"
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            body += f"- {cat}: {count} 篇\n"
        body += "\n【各类代表标题（供归纳，勿逐条照抄）】\n"
        for cat in sorted(categories.keys(), key=lambda c: -categories.get(c, 0)):
            titles = category_headlines.get(cat) or []
            body += f"- {cat}: " + ("；".join(titles[:5]) if titles else "（无标题摘录）") + "\n"
        body += (
            f"\n【输出】仅输出一个 JSON 对象，不要其它说明文字。键必须与上述类别名完全一致，值为字符串。"
            f"每个字符串长度 ≤ {mx}。不要使用 Markdown 代码围栏以外的包裹。"
        )
        return body

    @classmethod
    def category_analysis(cls, cat: str, count: int, samples: List[dict]) -> str:
        body = cls._base_analysis()
        body += f"（任务目的）对类别「{cat}」做分领域技术分析：技术脉络、与 GNSS/航天/气象的关联、风险与影响。\n"
        body += f"本日该类别共 {count} 篇，下列为代表条目（勿重复罗列所有标题）：\n\n"
        for i, a in enumerate(samples, 1):
            body += (
                f"{i}. 标题: {a.get('title', '')}\n"
                f"   来源: {a.get('source', '')} | URL: {a.get('url', '')}\n"
                f"   摘要: {(a.get('summary') or '')[:800]}\n\n"
            )
        body += "引用须可核对（类型或链接线索），勿编造页码。"
        return body

    @classmethod
    def important_article_analysis(
        cls,
        article: dict,
        body_excerpt: str,
        fetch_ok: bool,
        fetch_warning: Optional[str],
    ) -> str:
        body = cls._base_analysis()
        body += "（任务目的）基于下列单条新闻做精读：要点、技术脉络、产业/政策关联、待跟进问题。\n\n"
        body += (
            f"标题: {article.get('title', '')}\n"
            f"来源: {article.get('source', '')}\n"
            f"重要性: {article.get('importance', 0)}/10\n"
            f"URL: {article.get('url', '')}\n"
            f"摘要: {article.get('summary', '')}\n\n"
        )
        if fetch_ok and body_excerpt:
            body += "（以下为系统抓取的网页正文摘录，供交叉验证）\n\n"
            body += body_excerpt[:ARTICLE_BODY_MAX_CHARS] + "\n\n"
        else:
            body += f"（原文抓取：{'成功但正文为空' if fetch_ok else '未成功'}）"
            if fetch_warning:
                body += f" {fetch_warning}"
            body += "\n\n请主要依据摘要分析，并简要说明缺少全文的局限。\n\n"
        return body

    @classmethod
    def section_market(cls, shared: str) -> str:
        return (
            cls._base_analysis()
            + shared
            + "\n\n（任务目的）市场与商业洞察：竞争格局、商业模式与投融资线索、供应链与主要玩家；"
            "避免堆砌纯技术实现细节。\n"
        )

    @classmethod
    def section_policy(cls, shared: str) -> str:
        return (
            cls._base_analysis()
            + shared
            + "\n\n（任务目的）政策与监管：主要国家/地区政策信号、频谱与标准、出口管制与数据跨境等；"
            "仅基于可合理推断的公开信息。\n"
        )

    @classmethod
    def section_trends(cls, shared: str) -> str:
        return (
            cls._base_analysis()
            + shared
            + "\n\n（任务目的）趋势预测：用段落与列表区分短期（约3个月）、中期（约1年）、长期（3年及以上）展望，"
            "并说明不确定性来源；勿用 # 标题分行。\n"
        )

    @classmethod
    def section_recommendations(cls, shared: str) -> str:
        return (
            cls._base_analysis()
            + shared
            + "\n\n（任务目的）专业建议：面向技术团队、产业观察者或政策研究者的可执行建议；分条列出，避免空泛口号。\n"
        )

    @classmethod
    def executive_summary(cls, snippets: List[Tuple[str, str]]) -> str:
        body = cls._base_analysis()
        body += (
            "（任务目的）执行摘要统稿：综合下列摘录，形成一段总述与要点列表；"
            "若材料充分可加总览向 Mermaid 或要点对照表，否则以段落与列表为主即可。"
            "不要逐条重列所有新闻标题。\n\n"
        )
        for title, text in snippets:
            excerpt = (text or "")[:1200]
            body += f"【摘录来源：{title}】\n{excerpt}\n\n---\n\n"
        return body


def section_dict_result(res: CursorAgentResult) -> Dict[str, Any]:
    return {
        "markdown": res.markdown if res.ok else f"本节分析失败：{res.error or 'unknown'}",
        "ok": res.ok,
        "error": None if res.ok else (res.error or "unknown"),
    }


def build_category_headlines(
    articles: List[dict], *, max_titles_per_cat: int = 5
) -> Dict[str, List[str]]:
    by_cat: Dict[str, List[dict]] = {}
    for a in articles:
        c = a.get("category") or "other"
        by_cat.setdefault(c, []).append(a)

    out: Dict[str, List[str]] = {}
    for cat, lst in by_cat.items():
        lst_sorted = sorted(
            lst,
            key=lambda x: (x.get("importance") or 0, x.get("title") or ""),
            reverse=True,
        )
        titles = []
        for a in lst_sorted[:max_titles_per_cat]:
            t = (a.get("title") or "").strip()
            if t:
                titles.append(t)
        if titles:
            out[cat] = titles
    return out


