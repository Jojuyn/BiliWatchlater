"""Tests for categories.py - display grouping constants."""

from pathlib import Path

import pytest

from src.biliwatchlater.categories import (
    CATEGORY_MAP,
    DEFAULT_COLOR,
    DEFAULT_GROUP,
    GROUP_META,
    PARENT_GROUP_MAP,
    get_color,
    get_group,
    get_groups,
    get_tag,
    group_stats,
)


class TestGetGroup:
    """Display group resolution priority."""

    def test_mapped_category(self):
        assert get_group("计算机技术") == "学习"
        assert get_group("AI杂谈") == "AI"
        assert get_group("商业财经") == "成长"

    def test_parent_group_fallback(self):
        assert get_group("未知子类", "知识") == "成长"
        assert get_group("未知子类", "人工智能") == "AI"
        assert get_group("未知子类", "游戏") == "游戏"

    def test_unknown_falls_to_default(self):
        assert get_group("完全不存在的分类") == DEFAULT_GROUP

    def test_mapped_overrides_parent(self):
        assert get_group("计算机技术", "科技数码") == "学习"
        assert get_group("AI学习", "人工智能") == "学习"

    def test_empty_parent(self):
        assert get_group("商业财经") == "成长"
        assert get_group("完全不存在的分类", "") == DEFAULT_GROUP


class TestGetTag:
    """Short display tag resolution."""

    def test_mapped_category(self):
        assert get_tag("计算机技术") == "编程"
        assert get_tag("商业财经") == "财经"
        assert get_tag("AI杂谈") == "AI"

    def test_unknown_truncates_long(self):
        long_name = "这是一个很长的未知分类名称"
        result = get_tag(long_name)
        assert len(result) <= 8
        assert result == long_name[:8]

    def test_unknown_short_keeps_full(self):
        assert get_tag("音乐") == "音乐"
        assert get_tag("绘画") == "绘画"


class TestGetColor:
    """Color hex resolution."""

    def test_mapped_category(self):
        assert get_color("计算机技术") == "#22c55e"
        assert get_color("AI杂谈") == "#a855f7"

    def test_unknown_returns_default(self):
        assert get_color("不存在的分类") == DEFAULT_COLOR


class TestGetGroups:
    """Sorted group metadata."""

    def test_returns_all_groups(self):
        groups = get_groups()
        assert len(groups) == len(GROUP_META)

    def test_sorted_by_order(self):
        groups = get_groups()
        orders = [g["order"] for g in groups]
        assert orders == sorted(orders)

    def test_first_is_learning(self):
        groups = get_groups()
        assert groups[0]["order"] == 0


class TestGroupStats:
    """Database aggregation."""

    def test_returns_correct_structure(self, tmp_path):
        import sqlite3
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE watch_later ("
            "category_v2 TEXT, parent_category_v2 TEXT)"
        )
        conn.execute(
            "INSERT INTO watch_later VALUES ('计算机技术', '科技数码')"
        )
        conn.execute(
            "INSERT INTO watch_later VALUES ('计算机技术', '科技数码')"
        )
        conn.execute(
            "INSERT INTO watch_later VALUES ('AI杂谈', '人工智能')"
        )
        conn.execute(
            "INSERT INTO watch_later VALUES ('商业财经', '知识')"
        )
        conn.commit()
        conn.close()

        result = group_stats(db)
        assert isinstance(result, list)
        assert len(result) > 0

        # Find 学习 group
        learning = [g for g in result if g["group"] == "学习"]
        assert len(learning) == 1
        assert learning[0]["count"] == 2
        assert learning[0]["subtags"][0]["tag"] == "编程"
        assert learning[0]["subtags"][0]["count"] == 2

    def test_empty_db_returns_empty_list(self, tmp_path):
        import sqlite3
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE watch_later ("
            "category_v2 TEXT, parent_category_v2 TEXT)"
        )
        conn.commit()
        conn.close()

        result = group_stats(db)
        assert result == []

    def test_unknown_category_falls_to_default(self, tmp_path):
        import sqlite3
        db = tmp_path / "unknown.db"
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE watch_later ("
            "category_v2 TEXT, parent_category_v2 TEXT)"
        )
        conn.execute(
            "INSERT INTO watch_later VALUES ('外星语研究', '神秘学')"
        )
        conn.commit()
        conn.close()

        result = group_stats(db)
        other = [g for g in result if g["group"] == "其他"]
        assert len(other) == 1
        assert other[0]["count"] == 1
