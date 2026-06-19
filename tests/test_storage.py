"""Tests for storage.py - SQLite / CSV read-write and FTS indexing."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.biliwatchlater.models import BASE_COLUMNS, WatchLaterVideo
from src.biliwatchlater.storage import (
    WATCH_LATER_TABLE,
    FTS_TABLE,
    migrate_csv_to_sqlite,
    read_csv,
    read_sqlite,
    videos_to_dataframe,
    write_sqlite,
)


VIDEO_A = WatchLaterVideo(
    bvid="BV1TestAA", aid=1, cid=1, title="Test A",
    up_mid=101, up_name="Tester A", pub_date="2026-01-01",
    added_at="2026-06-01 12:00:00", duration_seconds=300,
    category="Technology", category_v2="Tech", parent_category_v2="Tech",
    description="First test video", cover_url="", short_url="",
    view_count=100, favorite_count=10, coin_count=5, like_count=20,
    reply_count=2, danmaku_count=1, progress_seconds=0,
)

VIDEO_B = WatchLaterVideo(
    bvid="BV1TestBB", aid=2, cid=2, title="Test B",
    up_mid=102, up_name="Tester B", pub_date="2026-02-01",
    added_at="2026-06-01 13:00:00", duration_seconds=600,
    category="Education", category_v2="Campus", parent_category_v2="Edu",
    description="Second test video", cover_url="", short_url="",
    view_count=200, favorite_count=20, coin_count=10, like_count=40,
    reply_count=4, danmaku_count=2, progress_seconds=0,
)


class TestVideosToDataFrame:
    def test_empty_list(self):
        df = videos_to_dataframe([])
        assert list(df.columns) == BASE_COLUMNS
        assert len(df) == 0

    def test_single_video(self):
        df = videos_to_dataframe([VIDEO_A])
        assert len(df) == 1
        assert df.iloc[0]["bvid"] == "BV1TestAA"
        assert df.iloc[0]["title"] == "Test A"

    def test_multiple_videos(self):
        df = videos_to_dataframe([VIDEO_A, VIDEO_B])
        assert len(df) == 2
        assert list(df["bvid"]) == ["BV1TestAA", "BV1TestBB"]

    def test_column_order_matches_base(self):
        df = videos_to_dataframe([VIDEO_A])
        assert list(df.columns) == BASE_COLUMNS


class TestReadSqlite:
    def test_nonexistent_file_returns_empty(self, tmp_path):
        db = tmp_path / "nonexistent.db"
        df = read_sqlite(db)
        assert list(df.columns) == BASE_COLUMNS
        assert len(df) == 0

    def test_empty_table_returns_empty(self, tmp_path):
        db = tmp_path / "empty.db"
        cols = ", ".join(f"{c} TEXT" for c in BASE_COLUMNS)
        with sqlite3.connect(db) as conn:
            conn.execute(f"CREATE TABLE {WATCH_LATER_TABLE} ({cols})")
        df = read_sqlite(db)
        assert list(df.columns) == BASE_COLUMNS
        assert len(df) == 0

    def test_reads_data(self, tmp_path):
        db = tmp_path / "data.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B]))
        df = read_sqlite(db)
        assert len(df) == 2

    def test_column_preservation(self, tmp_path):
        db = tmp_path / "cols.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B]))
        df = read_sqlite(db)
        for col in BASE_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"


class TestWriteSqlite:
    def test_writes_data(self, tmp_path):
        db = tmp_path / "out.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A]))
        df = read_sqlite(db)
        assert len(df) == 1
        assert df.iloc[0]["bvid"] == "BV1TestAA"

    def test_creates_unique_index(self, tmp_path):
        db = tmp_path / "indexed.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A]))
        with sqlite3.connect(db) as conn:
            idx_name = f"idx_{WATCH_LATER_TABLE}_bvid"
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (idx_name,),
            )
            assert cursor.fetchone() is not None

    def test_creates_parent_directory(self, tmp_path):
        db = tmp_path / "sub" / "nested" / "deep.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A]))
        assert db.exists()
        df = read_sqlite(db)
        assert len(df) == 1


class TestFTS:
    def _count_fts(self, db):
        with sqlite3.connect(db) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {FTS_TABLE}").fetchone()[0]

    def _search_fts(self, db, term):
        with sqlite3.connect(db) as conn:
            return conn.execute(
                f"SELECT bvid, title FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH ?",
                (term,),
            ).fetchall()

    def test_fts_populated_on_write(self, tmp_path):
        db = tmp_path / "fts.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B]))
        assert self._count_fts(db) == 2

    def test_fts_search_title(self, tmp_path):
        db = tmp_path / "search.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B]))
        rows = self._search_fts(db, "Test")
        assert len(rows) == 2

    def test_fts_search_up_name(self, tmp_path):
        db = tmp_path / "search_up.db"
        write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B]))
        rows = self._search_fts(db, "Tester")
        assert len(rows) == 2

    def test_fts_empty_on_empty_write(self, tmp_path):
        db = tmp_path / "empty_fts.db"
        write_sqlite(db, videos_to_dataframe([]))
        assert self._count_fts(db) == 0


class TestMigrateCsv:
    def test_migrate_csv_to_sqlite(self, tmp_path):
        csv = tmp_path / "data.csv"
        db = tmp_path / "data.db"
        videos_to_dataframe([VIDEO_A, VIDEO_B]).to_csv(csv, index=False)
        count = migrate_csv_to_sqlite(csv, db)
        assert count == 2
        df = read_sqlite(db)
        assert len(df) == 2

    def test_migrate_nonexistent_csv_raises(self, tmp_path):
        csv = tmp_path / "missing.csv"
        db = tmp_path / "out.db"
        with pytest.raises(FileNotFoundError):
            migrate_csv_to_sqlite(csv, db)


class TestReadCsv:
    def test_nonexistent_csv_returns_empty(self, tmp_path):
        csv = tmp_path / "nonexistent.csv"
        df = read_csv(csv)
        assert list(df.columns) == BASE_COLUMNS
        assert len(df) == 0

    def test_read_csv_with_data(self, tmp_path):
        csv = tmp_path / "test.csv"
        videos_to_dataframe([VIDEO_A]).to_csv(csv, index=False)
        df = read_csv(csv)
        assert len(df) == 1
        assert df.iloc[0]["bvid"] == "BV1TestAA"
