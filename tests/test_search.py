"""Tests for search.py — FTS5 search engine."""

import pytest

from src.biliwatchlater.search import (
    DURATION_RANGES,
    SearchFilter,
    SearchResult,
    format_duration,
    search_videos,
)
from src.biliwatchlater.storage import ensure_schema, write_sqlite, videos_to_dataframe
from src.biliwatchlater.models import WatchLaterVideo


VIDEO_A = WatchLaterVideo(
    bvid="BV1SearchAA", aid=1, cid=1, title="Python Machine Learning",
    up_mid=101, up_name="Tech Guru", pub_date="2026-01-01",
    added_at="2026-06-01 12:00:00", duration_seconds=600,
    category="科技", category_v2="AI学习", parent_category_v2="人工智能",
    description="Deep dive into ML", cover_url="", short_url="",
    view_count=5000, favorite_count=500, coin_count=200, like_count=800,
    reply_count=50, danmaku_count=20, progress_seconds=0,
)

VIDEO_B = WatchLaterVideo(
    bvid="BV1SearchBB", aid=2, cid=2, title="Cooking 101",
    up_mid=102, up_name="Chef Home", pub_date="2026-02-01",
    added_at="2026-06-02 13:00:00", duration_seconds=1200,
    category="生活", category_v2="美食制作", parent_category_v2="美食",
    description="Learn to cook", cover_url="", short_url="",
    view_count=200, favorite_count=20, coin_count=10, like_count=40,
    reply_count=4, danmaku_count=2, progress_seconds=600,
)

VIDEO_C = WatchLaterVideo(
    bvid="BV1SearchCC", aid=3, cid=3, title="Game Review",
    up_mid=103, up_name="Gamer Pro", pub_date="2026-03-01",
    added_at="2026-06-03 14:00:00", duration_seconds=1800,
    category="游戏", category_v2="射击游戏", parent_category_v2="游戏",
    description="Review of latest games", cover_url="", short_url="",
    view_count=10000, favorite_count=1000, coin_count=500, like_count=2000,
    reply_count=100, danmaku_count=50, progress_seconds=1800,
)


def _seed_db(tmp_path):
    db = tmp_path / "search.db"
    ensure_schema(db)
    write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B, VIDEO_C]))
    return db


class TestFormatDuration:
    def test_zero(self):
        assert format_duration(0) == "0:00"
        assert format_duration(None) == "0:00"

    def test_seconds_only(self):
        assert format_duration(45) == "0:45"

    def test_minutes(self):
        assert format_duration(600) == "10:00"

    def test_hours(self):
        assert format_duration(3661) == "1:01:01"


class TestSearchVideos:
    def test_empty_returns_all_up_to_limit(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db)
        assert result.total == 3
        assert len(result.items) == 3

    def test_text_search_via_fts(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(query="Python"))
        assert result.total == 1
        assert result.items[0]["bvid"] == "BV1SearchAA"

    def test_text_search_multiple_words(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(query="Game"))
        assert result.total == 1
        assert result.items[0]["bvid"] == "BV1SearchCC"

    def test_text_search_no_match(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(query="NonExistent"))
        assert result.total == 0
        assert len(result.items) == 0


class TestCategoryFilter:
    def test_category_v2_exact(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(
            db, SearchFilter(category_v2="AI学习")
        )
        assert result.total == 1
        assert result.items[0]["title"].startswith("Python")

    def test_category_group(self, tmp_path):
        db = _seed_db(tmp_path)
        # "AI学习" maps to group "学习" (from CATEGORY_MAP)
        result = search_videos(
            db, SearchFilter(category_group="学习")
        )
        assert result.total >= 1


class TestDurationFilter:
    def test_duration_range(self, tmp_path):
        db = _seed_db(tmp_path)
        # 5-10min = 300-600s
        result = search_videos(
            db, SearchFilter(duration_range="5-10min")
        )
        for item in result.items:
            assert 300 <= item["duration_seconds"] < 600

    def test_long_duration(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(
            db, SearchFilter(duration_range=">40min")
        )
        # VIDEO_C is 30min (1800s) which is < 40min
        # Only videos > 2400s would match
        assert result.total == 0


class TestStatusFilter:
    def test_unwatched(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(status="unwatched"))
        assert all(item["status"] == "unwatched" for item in result.items)

    def test_watching(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(status="watching"))
        assert all(item["status"] == "watching" for item in result.items)

    def test_watched(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(status="watched"))
        assert all(item["status"] == "watched" for item in result.items)


class TestSort:
    def test_sort_by_view_count_desc(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(
            db, SearchFilter(sort_by="view_count", ascending=False)
        )
        views = [item["view_count"] for item in result.items]
        assert views == sorted(views, reverse=True)

    def test_sort_by_duration_asc(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(
            db, SearchFilter(sort_by="duration", ascending=True)
        )
        durs = [item["duration_seconds"] for item in result.items]
        assert durs == sorted(durs)


class TestPagination:
    def test_limit(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(limit=1))
        assert len(result.items) == 1
        assert result.total == 3

    def test_offset(self, tmp_path):
        db = _seed_db(tmp_path)
        first = search_videos(db, SearchFilter(limit=1, offset=0))
        second = search_videos(db, SearchFilter(limit=1, offset=1))
        assert first.items[0]["bvid"] != second.items[0]["bvid"]


class TestComputedFields:
    def test_duration_display(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(query="Python"))
        assert result.items[0]["duration_display"] == "10:00"

    def test_status_computed(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db)
        statuses = {item["bvid"]: item["status"] for item in result.items}
        assert statuses["BV1SearchAA"] == "unwatched"
        assert statuses["BV1SearchBB"] == "watching"
        assert statuses["BV1SearchCC"] == "watched"

    def test_category_computed(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(query="Python"))
        item = result.items[0]
        assert item["category_group"] == "学习"
        assert item["category_tag"] == "AI"


class TestCombinedFilters:
    def test_search_within_category(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(
            db, SearchFilter(
                query="Python", category_v2="AI学习"
            )
        )
        assert result.total == 1

    def test_unwatched_learning_videos(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(
            db, SearchFilter(
                category_group="学习", status="unwatched"
            )
        )
        assert result.total == 1
        assert result.items[0]["bvid"] == "BV1SearchAA"


class TestSearchResultType:
    def test_search_result_fields(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(limit=1))
        assert isinstance(result, SearchResult)
        assert isinstance(result.items, list)
        assert isinstance(result.total, int)

    def test_item_has_all_computed_fields(self, tmp_path):
        db = _seed_db(tmp_path)
        result = search_videos(db, SearchFilter(query="Python"))
        item = result.items[0]
        for key in (
            "duration_display", "status", "category_group",
            "category_tag", "category_color", "note_preview", "tags",
        ):
            assert key in item, f"Missing computed field: {key}"
