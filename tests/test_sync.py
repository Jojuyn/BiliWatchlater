"""Tests for sync.py — incremental sync logic."""

import pandas as pd
import pytest

from src.biliwatchlater.models import BASE_COLUMNS, WatchLaterVideo
from src.biliwatchlater.sync import sync_dataframes


VIDEO_A = WatchLaterVideo(
    bvid="BV1AA", aid=1, cid=1, title="Video A",
    up_mid=101, up_name="Uploader A", pub_date="2026-01-01",
    added_at="2026-06-01 12:00:00", duration_seconds=300,
    category="科技", category_v2="科技数码", parent_category_v2="科技",
    description="First video", cover_url="", short_url="",
    view_count=100, favorite_count=10, coin_count=5, like_count=20,
    reply_count=2, danmaku_count=1, progress_seconds=0,
)

VIDEO_B = WatchLaterVideo(
    bvid="BV1BB", aid=2, cid=2, title="Video B",
    up_mid=102, up_name="Uploader B", pub_date="2026-02-01",
    added_at="2026-06-01 13:00:00", duration_seconds=600,
    category="教育", category_v2="校园学习", parent_category_v2="教育",
    description="Second video", cover_url="", short_url="",
    view_count=200, favorite_count=20, coin_count=10, like_count=40,
    reply_count=4, danmaku_count=2, progress_seconds=0,
)

VIDEO_B_UPDATED = WatchLaterVideo(
    bvid="BV1BB", aid=2, cid=2, title="Video B (new title)",
    up_mid=102, up_name="Uploader B", pub_date="2026-02-01",
    added_at="2026-06-01 13:00:00", duration_seconds=600,
    category="教育", category_v2="校园学习", parent_category_v2="教育",
    description="Updated description", cover_url="", short_url="",
    view_count=250, favorite_count=25, coin_count=10, like_count=45,
    reply_count=5, danmaku_count=3, progress_seconds=50,
)


def _empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=BASE_COLUMNS)


def _df_from_videos(videos: list[WatchLaterVideo]) -> pd.DataFrame:
    rows = [v.to_dict() for v in videos]
    return pd.DataFrame(rows, columns=BASE_COLUMNS)


class TestEmptyScenarios:
    """Edge cases where one or both sides are empty."""

    def test_both_empty(self):
        old = _empty_dataframe()
        result = sync_dataframes(old, [])
        assert result.total == 0
        assert result.added == 0
        assert result.removed == 0
        assert result.updated == 0
        assert len(result.dataframe) == 0

    def test_empty_old_populated_online(self):
        old = _empty_dataframe()
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B])
        assert result.total == 2
        assert result.added == 2
        assert result.removed == 0
        assert result.updated == 0
        assert list(result.dataframe["bvid"]) == ["BV1AA", "BV1BB"]

    def test_populated_old_empty_online(self):
        old = _df_from_videos([VIDEO_A, VIDEO_B])
        result = sync_dataframes(old, [])
        assert result.total == 0
        assert result.added == 0
        assert result.removed == 2
        assert result.updated == 0
        assert len(result.dataframe) == 0


class TestIncrementalSync:
    """Core incremental-add/remove logic."""

    def test_no_changes(self):
        old = _df_from_videos([VIDEO_A, VIDEO_B])
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B])
        assert result.total == 2
        assert result.added == 0
        assert result.removed == 0
        assert result.updated == 0

    def test_add_only(self):
        old = _df_from_videos([VIDEO_A])
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B])
        assert result.total == 2
        assert result.added == 1
        assert result.removed == 0
        assert result.updated == 0
        assert "BV1BB" in result.dataframe["bvid"].values

    def test_remove_only(self):
        old = _df_from_videos([VIDEO_A, VIDEO_B])
        result = sync_dataframes(old, [VIDEO_A])
        assert result.total == 1
        assert result.added == 0
        assert result.removed == 1
        assert result.updated == 0
        assert list(result.dataframe["bvid"]) == ["BV1AA"]

    def test_add_and_remove(self):
        old = _df_from_videos([VIDEO_A])
        result = sync_dataframes(old, [VIDEO_B])
        assert result.total == 1
        assert result.added == 1
        assert result.removed == 1
        assert result.updated == 0
        assert list(result.dataframe["bvid"]) == ["BV1BB"]


class TestFieldUpdates:
    """Field-level change detection."""

    def test_field_updates_detected(self):
        old = _df_from_videos([VIDEO_A, VIDEO_B])
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B_UPDATED])
        assert result.total == 2
        assert result.added == 0
        assert result.removed == 0
        # B has: title, description, view_count, favorite_count,
        # like_count, reply_count, danmaku_count, progress_seconds changed = 8 fields
        assert result.updated == 8
        row = result.dataframe[result.dataframe["bvid"] == "BV1BB"].iloc[0]
        assert row["title"] == "Video B (new title)"
        assert row["description"] == "Updated description"
        assert row["view_count"] == 250

    def test_no_update_when_identical(self):
        old = _df_from_videos([VIDEO_A])
        result = sync_dataframes(old, [VIDEO_A])
        assert result.updated == 0


class TestCustomColumns:
    """Preservation of custom columns outside BASE_COLUMNS."""

    def test_custom_columns_preserved_in_kept_rows(self):
        old = _df_from_videos([VIDEO_A, VIDEO_B])
        old["my_note"] = ["old note", "old note B"]
        old["priority"] = [1, 2]
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B])
        assert result.total == 2
        assert "my_note" in result.dataframe.columns
        assert "priority" in result.dataframe.columns
        assert result.dataframe["my_note"].tolist() == ["old note", "old note B"]

    def test_custom_columns_filled_empty_for_new_rows(self):
        old = _df_from_videos([VIDEO_A])
        old["my_note"] = ["old note"]
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B])
        assert result.total == 2
        new_row = result.dataframe[result.dataframe["bvid"] == "BV1BB"].iloc[0]
        assert new_row["my_note"] == ""

    def test_all_custom_columns_dropped_when_empty_online(self):
        old = _df_from_videos([VIDEO_A])
        old["my_note"] = ["orphan note"]
        result = sync_dataframes(old, [])
        assert result.total == 0
        assert result.removed == 1


class TestDeduplication:
    """Duplicate bvid handling."""

    def test_online_duplicates_deduped(self):
        old = _df_from_videos([VIDEO_A, VIDEO_B])
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B, VIDEO_B])  # duplicate B
        assert result.total == 2
        assert result.added == 0
        assert result.removed == 0

    def test_old_duplicates_keep_first(self):
        dup = VIDEO_B.to_dict()
        old_rows = [VIDEO_A.to_dict(), dup, VIDEO_B.to_dict()]
        old = pd.DataFrame(old_rows, columns=BASE_COLUMNS)
        result = sync_dataframes(old, [VIDEO_A, VIDEO_B])
        assert result.total == 2
        assert result.added == 0
        assert result.removed == 0


class TestDataFrameShape:
    """Column order and row structure."""

    def test_column_order_base_columns_first(self):
        old = _df_from_videos([VIDEO_A])
        old["custom"] = "x"
        result = sync_dataframes(old, [VIDEO_A])
        cols = list(result.dataframe.columns)
        expected = BASE_COLUMNS + ["custom"]
        assert cols == expected

    def test_empty_old_has_no_bvid_column(self):
        weird_old = pd.DataFrame({"not_bvid": [1, 2]})
        result = sync_dataframes(weird_old, [VIDEO_A])
        assert result.total == 1
        assert result.added == 1
        assert result.removed == 0
        assert result.updated == 0


class TestSyncResultType:
    """SyncResult frozen dataclass contract."""

    def test_sync_result_fields(self):
        df = _empty_dataframe()
        result = sync_dataframes(df, [])
        assert isinstance(result.dataframe, pd.DataFrame)
        assert isinstance(result.total, int)
        assert isinstance(result.added, int)
        assert isinstance(result.removed, int)
        assert isinstance(result.updated, int)

    def test_sync_result_immutable(self):
        df = _empty_dataframe()
        result = sync_dataframes(df, [])
        with pytest.raises(AttributeError):
            result.total = 999  # frozen dataclass
