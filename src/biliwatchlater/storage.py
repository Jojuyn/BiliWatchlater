from pathlib import Path
import sqlite3

import pandas as pd

from .models import BASE_COLUMNS, WatchLaterVideo


WATCH_LATER_TABLE = "watch_later"
FTS_TABLE = "watch_later_fts"


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
