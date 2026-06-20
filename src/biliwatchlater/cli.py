import argparse
import asyncio
import time
from pathlib import Path

from .config import load_settings
from .storage import ensure_schema, migrate_csv_to_sqlite, read_csv, read_sqlite, \
    record_sync_history, write_sqlite
from .sync import sync_dataframes
from .nl_cli import chat_loop


async def sync_watch_later(
    db_path: str | Path = "watch_later.db",
    import_csv_path: str | Path | None = "watch_later.csv",
) -> None:
    from .client import BilibiliWatchLaterClient

    started_at = time.strftime("%Y-%m-%d %H:%M:%S")
    settings = load_settings(db_path=db_path)
    ensure_schema(settings.db_path)
    client = BilibiliWatchLaterClient(settings)
    videos = await client.fetch_watch_later()
    old = read_existing_dataset(settings.db_path, import_csv_path)
    result = sync_dataframes(old, videos)
    write_sqlite(settings.db_path, result.dataframe)
    record_sync_history(settings.db_path, started_at, len(videos), result)

    print(
        "同步完成："
        f"总计 {result.total} 条，"
        f"新增 {result.added} 条，"
        f"移除 {result.removed} 条，"
        f"更新 {result.updated} 个字段。"
    )


def read_existing_dataset(db_path: Path, import_csv_path: str | Path | None) -> object:
    old = read_sqlite(db_path)
    if not old.empty:
        return old

    if import_csv_path:
        csv_path = Path(import_csv_path)
        if csv_path.exists():
            return read_csv(csv_path)

    return old


def migrate_csv(csv_path: str | Path = "watch_later.csv", db_path: str | Path = "watch_later.db") -> None:
    ensure_schema(Path(db_path))
    count = migrate_csv_to_sqlite(Path(csv_path), Path(db_path))
    print(f"迁移完成：已从 {csv_path} 写入 {db_path}，共 {count} 条。")


def _cmd_chat(args: argparse.Namespace) -> None:
    from .ai.client import AIClient, load_ai_settings
    settings = load_settings(db_path=args.db)
    ensure_schema(settings.db_path)
    ai_client = None
    if args.ai:
        ai_settings = load_ai_settings()
        if ai_settings.available:
            ai_client = AIClient(ai_settings)
    asyncio.run(chat_loop(settings.db_path, ai_client=ai_client, once=args.once, initial_input=args.query))


def _cmd_search(args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.table import Table
    from .search import SearchFilter, search_videos
    settings = load_settings(db_path=args.db)
    ensure_schema(settings.db_path)
    f = SearchFilter(
        query=args.query or "",
        category_v2=args.category,
        category_group=args.group,
        duration_range=args.duration,
        status=args.status,
        sort_by=args.sort,
        ascending=args.asc,
        limit=args.limit,
    )
    result = search_videos(settings.db_path, f)
    console = Console()
    if not result.items:
        console.print("[yellow]No matching videos.[/yellow]")
        return
    table = Table(title=f"Found {result.total} videos" + (f" (showing {len(result.items)})" if result.total > len(result.items) else ""))
    table.add_column("#", style="dim")
    table.add_column("Title", width=50)
    table.add_column("UP", style="cyan")
    table.add_column("Duration", style="green")
    table.add_column("Category")
    table.add_column("Views", justify="right")
    status_icons = {"unwatched": "", "watching": "▶", "watched": "✓"}
    for i, item in enumerate(result.items, 1):
        table.add_row(
            str(i),
            item["title"][:50],
            item["up_name"],
            item.get("duration_display", ""),
            item.get("category_tag", ""),
            f"{item.get('view_count', 0):,}",
        )
    console.print(table)


def _cmd_stats(args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.table import Table
    from .stats import get_duration_breakdown, get_hot_unwatched, get_overview, get_top_uploaders
    settings = load_settings(db_path=args.db)
    ensure_schema(settings.db_path)
    console = Console()
    db = settings.db_path
    if args.type == "overview":
        ov = get_overview(db)
        t = Table(title="Overview")
        t.add_column("Metric", style="cyan")
        t.add_column("Value", justify="right")
        for k, v in [("Total", ov["total"]), ("Unwatched", ov["unwatched"]),
                     ("Watching", ov["watching"]), ("Watched", ov["watched"]),
                     ("Total Hours", ov["total_duration_hours"])]:
            t.add_row(k, str(v))
        console.print(t)
    elif args.type == "duration":
        bins = get_duration_breakdown(db)
        t = Table(title="Duration Breakdown")
        t.add_column("Range", style="cyan")
        t.add_column("Count", justify="right")
        for b in bins:
            t.add_row(b["label"], str(b["count"]))
        console.print(t)
    elif args.type == "uploaders":
        ups = get_top_uploaders(db)
        t = Table(title="Top Uploaders")
        t.add_column("#", style="dim")
        t.add_column("Name", style="cyan")
        t.add_column("Videos", justify="right")
        for i, u in enumerate(ups[:10], 1):
            t.add_row(str(i), u["name"], str(u["count"]))
        console.print(t)
    elif args.type == "hot":
        hot = get_hot_unwatched(db)
        t = Table(title="Hot Unwatched")
        t.add_column("#", style="dim")
        t.add_column("Title", width=50)
        t.add_column("UP", style="cyan")
        t.add_column("Views", justify="right")
        for i, h in enumerate(hot[:10], 1):
            t.add_row(str(i), h["title"][:50], h["up_name"], f"{h['view_count']:,}")
        console.print(t)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync and manage Bilibili watch-later data.")
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Sync Bilibili watch-later list to SQLite.")
    sync_parser.add_argument(
        "--db",
        default="watch_later.db",
        help="SQLite database path. Defaults to watch_later.db.",
    )
    sync_parser.add_argument(
        "--import-csv",
        default="watch_later.csv",
        help="Optional CSV to bootstrap from when the database is empty.",
    )

    migrate_parser = subparsers.add_parser("migrate-csv", help="Migrate an existing CSV file to SQLite.")
    migrate_parser.add_argument(
        "--csv",
        default="watch_later.csv",
        help="CSV file path. Defaults to watch_later.csv.",
    )
    migrate_parser.add_argument(
        "--db",
        default="watch_later.db",
        help="SQLite database path. Defaults to watch_later.db.",
    )

    # chat
    chat_parser = subparsers.add_parser("chat", help="Natural language chat interface.")
    chat_parser.add_argument("query", nargs="?", default="", help="Direct query for --once mode.")
    chat_parser.add_argument("--db", default="watch_later.db")
    chat_parser.add_argument("--ai", action="store_true", help="Use LLM for intent parsing.")
    chat_parser.add_argument("--once", action="store_true", help="Single query then exit.")

    # search
    search_parser = subparsers.add_parser("search", help="Search and filter watch-later videos.")
    search_parser.add_argument("query", nargs="?", default="", help="FTS5 search keywords.")
    search_parser.add_argument("--category", help="Exact category_v2 filter.")
    search_parser.add_argument("--group", help="Display group filter (学习/AI/成长/...).")
    search_parser.add_argument("--duration", choices=["<5min", "5-10min", "10-20min", "20-40min", ">40min"], help="Duration range.")
    search_parser.add_argument("--status", choices=["unwatched", "watching", "watched"], help="Watch status.")
    search_parser.add_argument("--sort", default="added_at", help="Sort field: view_count/like_count/duration/pub_date/added_at")
    search_parser.add_argument("--asc", action="store_true", help="Ascending order.")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results (default: 20).")
    search_parser.add_argument("--db", default="watch_later.db")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show video statistics.")
    stats_parser.add_argument("--type", choices=["overview", "duration", "uploaders", "hot"], default="overview", help="Statistic type.")
    stats_parser.add_argument("--db", default="watch_later.db")

    return parser


def _cmd_not_found(args: argparse.Namespace) -> None:
    from .ai.client import load_ai_settings
    settings = load_settings(db_path=getattr(args, "db", "watch_later.db"))
    ensure_schema(settings.db_path)
    ai_settings = load_ai_settings()
    ai_client = None
    if ai_settings.available:
        from .ai.client import AIClient
        ai_client = AIClient(ai_settings)
    # Treat as a chat query
    asyncio.run(chat_loop(settings.db_path, ai_client=ai_client, once=True, initial_input=args.command))


COMMANDS = {
    "sync": lambda a: asyncio.run(sync_watch_later(
        a.db, getattr(a, "import_csv", "watch_later.csv"))),
    "migrate-csv": lambda a: migrate_csv(a.csv, a.db),
    "chat": _cmd_chat,
    "search": _cmd_search,
    "stats": _cmd_stats,
}


def main() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args()

    # If no subcommand was matched or command is unknown, try treating it as a chat query
    cmd = args.command if hasattr(args, "command") and args.command else None

    if cmd and cmd in COMMANDS:
        # Re-parse fully for the known command
        args = parser.parse_args()
        COMMANDS[cmd](args)
    elif cmd:
        # Unknown command: treat as a chat query
        _cmd_not_found(args)
    else:
        # No command at all: default to interactive chat
        import sys
        sys.argv = [sys.argv[0], "chat"]
        args = parser.parse_args()
        _cmd_chat(args)



