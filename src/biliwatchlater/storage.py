from pathlib import Path
import sqlite3

import pandas as pd

from .models import BASE_COLUMNS, SyncResult, WatchLaterVideo


WATCH_LATER_TABLE = "watch_later"
TAGS_TABLE = "tags"
VIDEO_TAGS_TABLE = "video_tags"
VIDEO_ANNOTATIONS_TABLE = "video_annotations"
SYNC_HISTORY_TABLE = "sync_history"
FTS_TABLE = "watch_later_fts"

SCHEMA_SQL: dict[str, str] = {
    "tags": """
        CREATE TABLE IF NOT EXISTS tags (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            parent_id   INTEGER REFERENCES tags(id) ON DELETE SET NULL,
            color       TEXT DEFAULT '#6366f1',
            description TEXT DEFAULT '',
            usage_count INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(name, parent_id)
        )
    """,
    "video_tags": """
        CREATE TABLE IF NOT EXISTS video_tags (
            bvid    TEXT NOT NULL REFERENCES watch_later(bvid) ON DELETE CASCADE,
            tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (bvid, tag_id)
        )
    """,
    "video_annotations": """
        CREATE TABLE IF NOT EXISTS video_annotations (
            bvid                TEXT NOT NULL PRIMARY KEY REFERENCES watch_later(bvid) ON DELETE CASCADE,
            note                TEXT DEFAULT '',
            priority            INTEGER DEFAULT 0,
            archived            INTEGER DEFAULT 0,
            archived_at         TEXT,
            watched             INTEGER DEFAULT 0,
            rating              INTEGER,
            ai_summary          TEXT DEFAULT '',
            ai_keywords         TEXT DEFAULT '',
            ai_relevance_score  REAL,
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        )
    """,
    "sync_history": """
        CREATE TABLE IF NOT EXISTS sync_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TEXT NOT NULL,
            finished_at     TEXT NOT NULL,
            total_online    INTEGER,
            total_local     INTEGER,
            added           INTEGER,
            removed         INTEGER,
            updated_fields  INTEGER
        )
    """,
}


def ensure_schema(path: Path) -> None:
    """Create all auxiliary tables if they do not exist.
    Safe to call on existing databases — uses IF NOT EXISTS everywhere.
    """
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for sql in SCHEMA_SQL.values():
            conn.execute(sql)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_tags_tag_id "
            "ON video_tags(tag_id)"
        )


def record_sync_history(path: Path, started_at: str, total_online: int, result: SyncResult) -> None:
    """Append one row to sync_history after a sync completes."""
    with sqlite3.connect(path) as conn:
        conn.execute(
            f"INSERT INTO {SYNC_HISTORY_TABLE} "
            "(started_at, finished_at, total_online, total_local, "
            " added, removed, updated_fields) "
            "VALUES (?, datetime('now'), ?, ?, ?, ?, ?)",
            (
                started_at,
                total_online,
                result.total,
                result.added,
                result.removed,
                result.updated,
            ),
        )


def videos_to_dataframe(videos: list[WatchLaterVideo]) -> pd.DataFrame:
    rows = [video.to_dict() for video in videos]
    return pd.DataFrame(rows, columns=BASE_COLUMNS)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=BASE_COLUMNS)
    return pd.read_csv(path)


def read_sqlite(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=BASE_COLUMNS)
    with sqlite3.connect(path) as connection:
        table_exists = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (WATCH_LATER_TABLE,),
        ).fetchone()
        if not table_exists:
            return pd.DataFrame(columns=BASE_COLUMNS)
        return pd.read_sql_query(f"SELECT * FROM {WATCH_LATER_TABLE}", connection)


def write_sqlite(path: Path, dataframe: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        dataframe.to_sql(WATCH_LATER_TABLE, connection, if_exists="replace", index=False)
        connection.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{WATCH_LATER_TABLE}_bvid "
            f"ON {WATCH_LATER_TABLE}(bvid)"
        )
        rebuild_fts(connection, dataframe)


def rebuild_fts(connection: sqlite3.Connection, dataframe: pd.DataFrame) -> None:
    connection.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE {FTS_TABLE}
        USING fts5(bvid UNINDEXED, title, up_name, category, category_v2, parent_category_v2, description)
        """
    )

    if dataframe.empty:
        return

    fts_columns = [
        "bvid",
        "title",
        "up_name",
        "category",
        "category_v2",
        "parent_category_v2",
        "description",
    ]
    fts_data = dataframe.reindex(columns=fts_columns, fill_value="")
    fts_data.to_sql(FTS_TABLE, connection, if_exists="append", index=False)


def migrate_csv_to_sqlite(csv_path: Path, db_path: Path) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    dataframe = read_csv(csv_path)
    write_sqlite(db_path, dataframe)
    return len(dataframe)
