"""Natural-language CLI for Bilibili watch-later management."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ai.client import AIClient
from .manager import (
    add_tag,
    list_tags,
    list_video_tags,
    remove_tag,
    set_archived,
    set_note,
    set_priority,
    set_watched,
)
from .search import SearchFilter, search_videos
from .stats import (
    get_duration_breakdown,
    get_hot_unwatched,
    get_overview,
    get_top_uploaders,
)
from .storage import ensure_schema


SYSTEM_PROMPT = """\
You are a parser for a Bilibili watch-later management tool. \
Convert the user's Chinese natural language request into a JSON action object.

Output ONLY valid JSON. Examples:
{"action": "search", "params": {"query": "AI"}}
{"action": "search", "params": {"category_v2": "计算机技术", "status": "unwatched"}}
{"action": "stats", "params": {"type": "overview"}}
{"action": "sync", "params": {}}
{"action": "help", "params": {}}

Actions:
- search: params can include query, category_v2, category_group, duration_range, status, sort_by
- stats: params.type is "overview", "duration", "uploaders", or "hot"
- list_tags: show all tags, no params
- tag: params.bvid (string), params.name, params.sub_action ("add"/"remove")
- note: params.bvid, params.text
- priority: params.bvid, params.level (0-3)
- archive: params.bvid
- watched: params.bvid
- sync: no params
- help: no params
"""

FALLBACK_HELP = """\
\U0001f4ac 说人话就能管理你的\\u7a0d\\u540e\\u518d\\u770b：

  \U0001f50d "\u5e2e\u6211\u627eAI\u6709\u5173\u7684\u89c6\u9891"
  \U0001f4ca "\u7edf\u8ba1\u4e00\u4e0b"
  \U0001f504 "\u540c\u6b65"

"""


@dataclass
class SessionContext:
    last_results: list[dict] = field(default_factory=list)


@dataclass
class ParsedIntent:
    action: str
    params: dict = field(default_factory=dict)
    raw: str = ""


# ── Fallback keyword parser ─────────────────────────────────────────────────

_FALLBACK_RULES: list[tuple[re.Pattern, str, callable]] = []

def _fb(pat: str, action: str, extract: callable | None = None) -> None:
    _FALLBACK_RULES.append((re.compile(pat), action, extract))

_fb(r"(?:搜索|找|查找|查询)\s*(.+)", "search",
    lambda m: {"query": m.group(1)})
_fb(r"(?:帮我|请).*找(.+)", "search",
    lambda m: {"query": m.group(1)})
_fb(r"统计|概览|有多少|看下整体", "stats",
    lambda _: {"type": "overview"})
_fb(r"时长分布|时长", "stats",
    lambda _: {"type": "duration"})
_fb(r"(?:热门|最热).*没看", "stats",
    lambda _: {"type": "hot"})
_fb(r"同步|刷新|更新", "sync",
    lambda _: {})
_fb(r"帮助|怎么用|命令|help|功能", "help",
    lambda _: {})


def _parse_fallback(user_input: str) -> ParsedIntent:
    for pattern, action, extract in _FALLBACK_RULES:
        m = pattern.search(user_input)
        if m:
            return ParsedIntent(action=action, params=extract(m), raw=user_input)
    # Default to search
    return ParsedIntent(action="search", params={"query": user_input.strip()}, raw=user_input)


# ── AI intent parser ────────────────────────────────────────────────────────

_INTENT_JSON_EXTRACTOR = re.compile(r"\\{[^}]+\\}")


async def _parse_with_llm(client: AIClient, user_input: str, ctx: SessionContext) -> ParsedIntent:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if ctx.last_results:
        ctx_str = "Current search results:\n"
        for i, item in enumerate(ctx.last_results[:5], 1):
            ctx_str += f"{i}. {item['title']} (bvid: {item['bvid']})\n"
        messages.append({"role": "system", "content": ctx_str})
    messages.append({"role": "user", "content": user_input})

    try:
        raw = await client.chat(messages, temperature=0.1)
        data = json.loads(raw.strip())
        action = data.get("action", "help")
        params = data.get("params", {})
        return ParsedIntent(action=action, params=params, raw=user_input)
    except (json.JSONDecodeError, KeyError, TypeError):
        return ParsedIntent(action="help", params={}, raw=user_input)


# ── BVID resolution ─────────────────────────────────────────────────────────

def _resolve_bvids(params: dict, ctx: SessionContext) -> dict:
    if "bvid" not in params:
        return params
    ref = str(params["bvid"])
    if ref.startswith("BV"):
        return params
    m = re.search(r"(\d+)", ref)
    if m and ctx.last_results:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(ctx.last_results):
            params["bvid"] = ctx.last_results[idx]["bvid"]
    return params


# ── Intent executor ─────────────────────────────────────────────────────────

async def _execute(intent: ParsedIntent, db_path: Path, ctx: SessionContext) -> dict:
    intent.params = _resolve_bvids(intent.params, ctx)
    action = intent.action
    p = intent.params

    if action == "search":
        q = p.get("query", "")
        if p.get("text"): q = p["text"]
        f = SearchFilter(
            query=q,
            category_v2=p.get("category_v2"),
            category_group=p.get("category_group"),
            duration_range=p.get("duration_range"),
            status=p.get("status"),
            sort_by=p.get("sort_by", "added_at"),
            ascending=p.get("ascending", False),
            limit=int(p.get("limit", 20)),
        )
        result = search_videos(db_path, f)
        ctx.last_results = result.items
        return {"type": "search", "result": result, "filters": f}

    elif action == "stats":
        t = p.get("type", "overview")
        if t == "overview":
            return {"type": "stats_overview", "result": get_overview(db_path)}
        elif t == "duration":
            return {"type": "stats_duration", "result": get_duration_breakdown(db_path)}
        elif t == "hot":
            return {"type": "stats_hot", "result": get_hot_unwatched(db_path)}
        elif t == "uploaders":
            return {"type": "stats_uploaders", "result": get_top_uploaders(db_path)}

    elif action == "sync":
        return {"type": "sync_request"}

    elif action == "list_tags":
        tags = list_tags(db_path)
        return {"type": "tags", "result": tags}

    elif action == "tag":
        bvid = p.get("bvid", "")
        name = p.get("name", "")
        sub = p.get("sub_action", "add")
        if bvid and name:
            if sub == "add":
                add_tag(db_path, bvid, name)
            else:
                remove_tag(db_path, bvid, name)
        return {"type": "tag_done", "bvid": bvid, "name": name, "action": sub}

    elif action == "note":
        bvid = p.get("bvid", "")
        text = p.get("text", "")
        if bvid:
            set_note(db_path, bvid, text)
        return {"type": "note_done", "bvid": bvid}

    elif action == "priority":
        bvid = p.get("bvid", "")
        level = int(p.get("level", 0))
        if bvid:
            set_priority(db_path, bvid, level)
        return {"type": "priority_done", "bvid": bvid, "level": level}

    elif action == "archive":
        bvid = p.get("bvid", "")
        if bvid:
            set_archived(db_path, bvid, True)
        return {"type": "archive_done", "bvid": bvid}

    elif action == "watched":
        bvid = p.get("bvid", "")
        if bvid:
            set_watched(db_path, bvid, True)
        return {"type": "watched_done", "bvid": bvid}

    return {"type": "help"}


# ── Response formatter ──────────────────────────────────────────────────────

def _format_response(executed: dict) -> str:
    t = executed["type"]

    if t == "search":
        r = executed["result"]
        if r.total == 0:
            return "\U0001f50d \u6ca1\u6709\u627e\u5230\u5339\u914d\u7684\u89c6\u9891\u3002"
        lines = [f"\U0001f50d \u627e\u5230 {r.total} \u6761\u89c6\u9891\uff1a"]
        for i, item in enumerate(r.items[:10], 1):
            tag_str = " ".join(
                t["name"] for t in item.get("tags", [])[:3]
            )
            tag_part = f" [{tag_str}]" if tag_str else ""
            dur = item.get("duration_display", "")
            status_icons = {"unwatched": "\U0001f195", "watching": "\\u25b6\ufe0f", "watched": "\\u2705"}
            icon = status_icons.get(item.get("status", ""), "")
            lines.append(
                f"  {i}. {item['title']} | {item['up_name']} | {dur}{tag_part} {icon}"
            )
        if r.total > 10:
            lines.append(f"  ... \u8fd8\u6709 {r.total - 10} \u6761")
        return "\n".join(lines)

    if t == "stats_overview":
        r = executed["result"]
        return (
            f"\U0001f4ca \u5f53\u524d\u7edf\u8ba1\uff1a\n"
            f"  \u603b\u8ba1 {r['total']} \u6761\n"
            f"  \U0001f195 \u672a\u770b\uff1a{r['unwatched']}\n"
            f"  \\u25b6\ufe0f \u89c2\u770b\u4e2d\uff1a{r['watching']}\n"
            f"  \\u2705 \u5df2\u770b\u5b8c\uff1a{r['watched']}\n"
            f"  \U0001f3a5 \u603b\u65f6\u957f\uff1a{r['total_duration_hours']}\u5c0f\u65f6"
        )

    if t == "stats_duration":
        bins = executed["result"]
        lines = ["\U0001f4ca \u65f6\u957f\u5206\u5e03\uff1a"]
        for b in bins:
            lines.append(f"  {b['label']}: {b['count']}")
        return "\n".join(lines)

    if t == "stats_hot":
        items = executed["result"]
        if not items:
            return "\U0001f525 \u6ca1\u6709\u627e\u5230\u70ed\u95e8\u672a\u770b\u89c6\u9891\u3002"
        lines = ["\U0001f525 \u672a\u770b\u4e2d\u6700\u70ed\u95e8\u7684\uff1a"]
        for i, item in enumerate(items[:5], 1):
            lines.append(f"  {i}. {item['title']} ({item['view_count']}\u64ad\u653e) - {item['up_name']}")
        return "\n".join(lines)

    if t == "stats_uploaders":
        ups = executed["result"]
        lines = ["\U0001f465 UP\u4e3b\u6392\u884c\uff1a"]
        for i, u in enumerate(ups[:5], 1):
            lines.append(f"  {i}. {u['name']} - {u['count']}\u6761")
        return "\n".join(lines)

    if t == "tags":
        tags = executed["result"]
        if not tags:
            return "\U0001f3f7\ufe0f \u8fd8\u6ca1\u6709\u6807\u7b7e\uff0c\u7528 `label <bvid> <\u6807\u7b7e\u540d>` \u6dfb\u52a0\u3002"
        lines = ["\U0001f3f7\ufe0f \u6240\u6709\u6807\u7b7e\uff1a"]
        for t in tags:
            lines.append(f"  {t['name']} ({t['count']}\u6b21)")
        return "\n".join(lines)

    if t == "tag_done":
        act = "\u6dfb\u52a0" if executed["action"] == "add" else "\u79fb\u9664"
        return f"\U0001f4cb \u5df2{act}\u6807\u7b7e\u300c{executed['name']}\\u300d"

    if t == "note_done":
        return f"\U0001f4dd \u7b14\u8bb0\u5df2\u4fdd\u5b58"

    if t == "priority_done":
        labels = {0: "\u65e0", 1: "P1 \U0001f534", 2: "P2 \U0001f7e1", 3: "P3 \U0001f535"}
        return f"\U0001f4cc \u4f18\u5148\u7ea7\u5df2\u8bbe\u4e3a {labels.get(executed['level'], str(executed['level']))}"

    if t == "archive_done":
        return f"\U0001f5c4\ufe0f \u89c6\u9891\u5df2\u5f52\u6863"

    if t == "watched_done":
        return f"\\u2705 \u89c6\u9891\u5df2\u6807\u8bb0\u4e3a\u5df2\u770b"

    if t == "sync_request":
        return "\U0001f504 \u8bf7\u8fd0\u884c `python -m src.biliwatchlater sync` \u540c\u6b65"

    return FALLBACK_HELP


# ── Main entry point ────────────────────────────────────────────────────────

async def chat_loop(
    db_path: Path,
    ai_client: AIClient | None = None,
    once: bool = False,
    initial_input: str = "",
) -> None:
    ensure_schema(db_path)
    ctx = SessionContext()

    if not once:
        if ai_client:
            print(f"\U0001f3ac \u7a0d\u540e\u518d\u770b\u52a9\u624b\u5df2\u5c31\u7eea"
                  f" (\u5f53\u524d\u63a5\u5165: {ai_client._settings.provider})")
        else:
            print("\U0001f3ac \u7a0d\u540e\u518d\u770b\u52a9\u624b\u5df2\u5c31\u7eea"
                  " (\u5173\u952e\u8bcd\u6a21\u5f0f)")
        print("\u8f93\u5165 `exit` \u9000\u51fa\n")

    if once and initial_input:
        intent = await _parse_with_llm(ai_client, initial_input, ctx) if ai_client else _parse_fallback(initial_input)
        executed = await _execute(intent, db_path, ctx)
        print(_format_response(executed))
        return

    while True:
        try:
            user_input = await _async_input()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in ("exit", "quit", "\u9000\u51fa"):
            break
        if not user_input.strip():
            continue

        if ai_client:
            intent = await _parse_with_llm(ai_client, user_input, ctx)
        else:
            intent = _parse_fallback(user_input)

        executed = await _execute(intent, db_path, ctx)
        print(_format_response(executed))


async def _async_input() -> str:
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: input("> "))
