import argparse
import asyncio
from pathlib import Path

from .config import load_settings
from .storage import migrate_csv_to_sqlite, read_csv, read_sqlite, write_sqlite
from .sync import sync_dataframes


async def sync_watch_later(
    db_path: str | Path = "watch_later.db",
    import_csv_path: str | Path | None = "watch_later.csv",
) -> None:
    from .client import BilibiliWatchLaterClient

    settings = load_settings(db_path=db_path)
    client = BilibiliWatchLaterClient(settings)
    videos = await client.fetch_watch_later()
    old = read_existing_dataset(settings.db_path, import_csv_path)
    result = sync_dataframes(old, videos)
    write_sqlite(settings.db_path, result.dataframe)

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
    count = migrate_csv_to_sqlite(Path(csv_path), Path(db_path))
    print(f"迁移完成：已从 {csv_path} 写入 {db_path}，共 {count} 条。")


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

    parser.add_argument(
        "--db",
        default=None,
        help="Backward-compatible shortcut for `sync --db`.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    command = args.command or "sync"

    if command == "migrate-csv":
        migrate_csv(args.csv, args.db)
        return

    db_path = args.db or "watch_later.db"
    import_csv_path = getattr(args, "import_csv", "watch_later.csv")
    asyncio.run(sync_watch_later(db_path, import_csv_path))
