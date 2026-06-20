"""Tests for stats.py — statistics queries."""

from src.biliwatchlater.stats import (
    get_duration_breakdown,
    get_hot_unwatched,
    get_overview,
    get_recent_changes,
    get_top_uploaders,
)
from src.biliwatchlater.storage import ensure_schema, record_sync_history, write_sqlite, videos_to_dataframe
from src.biliwatchlater.models import SyncResult, WatchLaterVideo
import pandas as pd


VIDEO_A = WatchLaterVideo(
    bvid="BV1StatsAA", aid=1, cid=1, title="Stats A",
    up_mid=101, up_name="Top Creator", pub_date="2026-01-01",
    added_at="2026-06-01", duration_seconds=300,
    category="T", category_v2="Test", parent_category_v2="Test",
    description="", cover_url="", short_url="",
    view_count=50000, favorite_count=0, coin_count=0, like_count=0,
    reply_count=0, danmaku_count=0, progress_seconds=0,
)

VIDEO_B = WatchLaterVideo(
    bvid="BV1StatsBB", aid=2, cid=2, title="Stats B",
    up_mid=102, up_name="Rare Uploader", pub_date="2026-02-01",
    added_at="2026-06-02", duration_seconds=600,
    category="T", category_v2="Test", parent_category_v2="Test",
    description="", cover_url="", short_url="",
    view_count=100, favorite_count=0, coin_count=0, like_count=0,
    reply_count=0, danmaku_count=0, progress_seconds=300,
)

VIDEO_C = WatchLaterVideo(
    bvid="BV1StatsCC", aid=3, cid=3, title="Stats C",
    up_mid=101, up_name="Top Creator", pub_date="2026-03-01",
    added_at="2026-06-03", duration_seconds=1800,
    category="T", category_v2="Test", parent_category_v2="Test",
    description="", cover_url="", short_url="",
    view_count=2000, favorite_count=0, coin_count=0, like_count=0,
    reply_count=0, danmaku_count=0, progress_seconds=1800,
)


def _seed_db(tmp_path):
    db = tmp_path / "stats.db"
    ensure_schema(db)
    write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B, VIDEO_C]))
    return db


class TestGetOverview:
    def test_counts(self, tmp_path):
        db = _seed_db(tmp_path)
        ov = get_overview(db)
        assert ov["total"] == 3
        assert ov["unwatched"] == 1
        assert ov["watching"] == 1
        assert ov["watched"] == 1

    def test_total_duration(self, tmp_path):
        db = _seed_db(tmp_path)
        ov = get_overview(db)
        assert ov["total_duration_seconds"] == 2700
        assert ov["total_duration_hours"] == 0.8

    def test_empty_db(self, tmp_path):
        db = tmp_path / "empty.db"
        ensure_schema(db)
        write_sqlite(db, videos_to_dataframe([]))
        ov = get_overview(db)
        assert ov["total"] == 0


class TestDurationBreakdown:
    def test_bins(self, tmp_path):
        db = _seed_db(tmp_path)
        bins = get_duration_breakdown(db)
        assert len(bins) == 5
        by_label = {b["label"]: b["count"] for b in bins}
        assert by_label["<5min"] == 0  # none <300s; A at 300s = 5min
        assert by_label["5-10min"] == 1  # VIDEO_A(300s) in [300,600)
        assert by_label["10-20min"] == 1  # VIDEO_B(600s) in [600,1200)
        assert by_label["20-40min"] == 1  # VIDEO_C(1800s) in [1200,2400)
        assert by_label[">40min"] == 0


class TestTopUploaders:
    def test_ranking(self, tmp_path):
        db = _seed_db(tmp_path)
        ups = get_top_uploaders(db, limit=5)
        assert ups[0]["name"] == "Top Creator"
        assert ups[0]["count"] == 2
        assert ups[1]["name"] == "Rare Uploader"
        assert ups[1]["count"] == 1


class TestHotUnwatched:
    def test_returns_unwatched_only(self, tmp_path):
        db = _seed_db(tmp_path)
        hot = get_hot_unwatched(db, limit=10)
        assert len(hot) == 1
        assert hot[0]["bvid"] == "BV1StatsAA"
        assert hot[0]["view_count"] == 50000


class TestRecentChanges:
    def test_no_history_returns_none(self, tmp_path):
        db = _seed_db(tmp_path)
        ch = get_recent_changes(db, days=7)
        assert ch is None

    def test_with_history(self, tmp_path):
        db = _seed_db(tmp_path)
        result = SyncResult(dataframe=pd.DataFrame(), total=5, added=2, removed=1, updated=3)
        record_sync_history(db, "2026-06-20 10:00:00", 10, result)
        ch = get_recent_changes(db, days=30)
        assert ch is not None
        assert ch["added"] == 2
        assert ch["removed"] == 1
        assert ch["total_online"] == 10
        assert ch["total_local"] == 5
