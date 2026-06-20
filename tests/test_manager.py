"""Tests for manager.py — tag and annotation CRUD."""

import pytest

from src.biliwatchlater.manager import (
    add_tag,
    batch_archive_watched,
    batch_clear_watched,
    batch_tag_videos,
    get_annotations,
    list_tags,
    list_video_tags,
    remove_tag,
    set_annotation,
    set_archived,
    set_note,
    set_priority,
    set_rating,
    set_watched,
)
from src.biliwatchlater.storage import ensure_schema, write_sqlite
from src.biliwatchlater.storage import videos_to_dataframe
from src.biliwatchlater.models import WatchLaterVideo


VIDEO_A = WatchLaterVideo(
    bvid="BV1ManagerAA", aid=1, cid=1, title="Manager Test A",
    up_mid=101, up_name="Tester", pub_date="2026-01-01",
    added_at="2026-06-01 12:00:00", duration_seconds=300,
    category="Test", category_v2="Test", parent_category_v2="Test",
    description="", cover_url="", short_url="",
    view_count=100, favorite_count=10, coin_count=5, like_count=20,
    reply_count=2, danmaku_count=1, progress_seconds=0,
)

VIDEO_B = WatchLaterVideo(
    bvid="BV1ManagerBB", aid=2, cid=2, title="Manager Test B",
    up_mid=102, up_name="Tester B", pub_date="2026-02-01",
    added_at="2026-06-01 13:00:00", duration_seconds=600,
    category="Test", category_v2="Test", parent_category_v2="Test",
    description="", cover_url="", short_url="",
    view_count=200, favorite_count=20, coin_count=10, like_count=40,
    reply_count=4, danmaku_count=2, progress_seconds=0,
)


def _seed_db(tmp_path) -> tuple:
    """Create a DB with two videos and return (db_path, bvids)."""
    db = tmp_path / "seed.db"
    write_sqlite(db, videos_to_dataframe([VIDEO_A, VIDEO_B]))
    return db, [VIDEO_A.bvid, VIDEO_B.bvid]


# ── Tag tests ──────────────────────────────────────────────────────────────

class TestTagCRUD:
    def test_add_tag_creates_and_assigns(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        tag_id = add_tag(db, bvids[0], "必看")
        assert isinstance(tag_id, int) and tag_id > 0
        tags = list_video_tags(db, bvids[0])
        assert len(tags) == 1
        assert tags[0]["name"] == "必看"

    def test_add_tag_idempotent(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        add_tag(db, bvids[0], "必看")
        add_tag(db, bvids[0], "必看")  # second time
        tags = list_video_tags(db, bvids[0])
        assert len(tags) == 1

    def test_remove_tag(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        add_tag(db, bvids[0], "必看")
        result = remove_tag(db, bvids[0], "必看")
        assert result is True
        tags = list_video_tags(db, bvids[0])
        assert len(tags) == 0

    def test_remove_nonexistent_tag(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        result = remove_tag(db, bvids[0], "不存在的标签")
        assert result is False

    def test_tag_shared_across_videos(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        add_tag(db, bvids[0], "共享标签")
        add_tag(db, bvids[1], "共享标签")
        assert len(list_video_tags(db, bvids[0])) == 1
        assert len(list_video_tags(db, bvids[1])) == 1

    def test_list_tags_sorted_by_count(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        add_tag(db, bvids[0], "稀有")
        add_tag(db, bvids[0], "热门")
        add_tag(db, bvids[1], "热门")
        all_tags = list_tags(db)
        # "热门" should come first (count=2)
        assert all_tags[0]["name"] == "热门"
        assert all_tags[0]["count"] >= all_tags[1]["count"]


# ── Annotation tests ───────────────────────────────────────────────────────

class TestAnnotationCRUD:
    def test_set_priority(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_priority(db, bvids[0], 1)
        ann = get_annotations(db, bvids[0])
        assert ann["priority"] == 1

    def test_set_priority_invalid(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        with pytest.raises(ValueError):
            set_priority(db, bvids[0], 99)

    def test_set_note(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_note(db, bvids[0], "值得反复看")
        ann = get_annotations(db, bvids[0])
        assert ann["note"] == "值得反复看"

    def test_set_watched(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_watched(db, bvids[0], True)
        ann = get_annotations(db, bvids[0])
        assert ann["watched"] == 1

    def test_set_archived_sets_timestamp(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_archived(db, bvids[0], True)
        ann = get_annotations(db, bvids[0])
        assert ann["archived"] == 1
        assert ann["archived_at"] is not None and len(ann["archived_at"]) > 0

    def test_set_rating_valid(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_rating(db, bvids[0], 5)
        ann = get_annotations(db, bvids[0])
        assert ann["rating"] == 5

    def test_set_rating_invalid(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        with pytest.raises(ValueError):
            set_rating(db, bvids[0], 0)
        with pytest.raises(ValueError):
            set_rating(db, bvids[0], 6)

    def test_get_annotations_nonexistent(self, tmp_path):
        db, _ = _seed_db(tmp_path)
        ann = get_annotations(db, "BV1NonExistent")
        assert ann is None

    def test_set_annotation_invalid_field(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        with pytest.raises(ValueError):
            set_annotation(db, bvids[0], "invalid_field", "x")

    def test_annotation_updated_at_changes(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_note(db, bvids[0], "v1")
        import time
        time.sleep(0.5)
        set_note(db, bvids[0], "v2")
        ann = get_annotations(db, bvids[0])
        assert ann["note"] == "v2"


# ── Batch tests ────────────────────────────────────────────────────────────

class TestBatchOperations:
    def test_batch_tag_videos(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        n = batch_tag_videos(db, bvids, "批量标签")
        assert n == 2
        for bvid in bvids:
            tags = list_video_tags(db, bvid)
            assert any(t["name"] == "批量标签" for t in tags)

    def test_batch_archive_watched(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_watched(db, bvids[0], True)
        n = batch_archive_watched(db)
        assert n == 1
        ann = get_annotations(db, bvids[0])
        assert ann["archived"] == 1

    def test_batch_clear_watched(self, tmp_path):
        db, bvids = _seed_db(tmp_path)
        set_watched(db, bvids[0], True)
        set_watched(db, bvids[1], True)
        n = batch_clear_watched(db)
        assert n == 2
        for bvid in bvids:
            ann = get_annotations(db, bvid)
            assert ann["watched"] == 0
