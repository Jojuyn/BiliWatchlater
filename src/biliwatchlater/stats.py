"""Statistics queries for the watch-later database."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from .categories import group_stats


def get_overview(db_path: Path) -> dict:
    """Return high-level counts and ratios."""
    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM watch_later").fetchone()[0]
        unwatched = conn.execute(
            "SELECT COUNT(*) FROM watch_later "
            "WHERE progress_seconds IS NULL OR progress_seconds = 0"
        ).fetchone()[0]
        watching = conn.execute(
            "SELECT COUNT(*) FROM watch_later "
            "WHERE progress_seconds > 0 "
            "AND (duration_seconds IS NULL OR progress_seconds < duration_seconds)"
        ).fetchone()[0]
        watched = conn.execute(
            "SELECT COUNT(*) FROM watch_later "
            "WHERE duration_seconds IS NOT NULL "
            "AND progress_seconds >= duration_seconds"
        ).fetchone()[0]
        total_dur = conn.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) FROM watch_later"
        ).fetchone()[0]

    return {
        "total": total,
        "unwatched": unwatched,
        "watching": watching,
        "watched": watched,
        "total_duration_seconds": total_dur,
        "total_duration_hours": round(total_dur / 3600, 1),
    }


def get_duration_breakdown(db_path: Path) -> list[dict]:
    """Return count per duration bin."""
    bins = [
        ("<5min", None, 300),
        ("5-10min", 300, 600),
        ("10-20min", 600, 1200),
        ("20-40min", 1200, 2400),
        (">40min", 2400, None),
    ]
    results = []
    with sqlite3.connect(db_path) as conn:
        for label, lo, hi in bins:
            if lo is None:
                sql = "SELECT COUNT(*) FROM watch_later WHERE duration_seconds < ? OR duration_seconds IS NULL"
                cnt = conn.execute(sql, (hi,)).fetchone()[0]
            elif hi is None:
                sql = "SELECT COUNT(*) FROM watch_later WHERE duration_seconds >= ?"
                cnt = conn.execute(sql, (lo,)).fetchone()[0]
            else:
                sql = "SELECT COUNT(*) FROM watch_later WHERE duration_seconds >= ? AND duration_seconds < ?"
                cnt = conn.execute(sql, (lo, hi)).fetchone()[0]
            results.append({"label": label, "count": cnt})
    return results


def get_recent_changes(db_path: Path, days: int = 7) -> dict | None:
    """Return the most recent sync_history entry within the last N days."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT started_at, finished_at, total_online, total_local, "
            "  added, removed, updated_fields "
            f"FROM sync_history "
            f"WHERE started_at >= datetime('now', ? || ' days') "
            f"ORDER BY id DESC LIMIT 1",
            (f"-{days}",),
        ).fetchall()
    if not rows:
        return None
    r = rows[0]
    return {
        "started_at": r[0],
        "finished_at": r[1],
        "total_online": r[2],
        "total_local": r[3],
        "added": r[4],
        "removed": r[5],
        "updated_fields": r[6],
    }


def get_top_uploaders(db_path: Path, limit: int = 10) -> list[dict]:
    """Return uploaders with most videos in watch-later."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT up_name, COUNT(*) as cnt "
            "FROM watch_later "
            "WHERE up_name != '' "
            "GROUP BY up_name "
            "ORDER BY cnt DESC "
            "LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"name": r[0], "count": r[1]} for r in rows]


def get_hot_unwatched(db_path: Path, limit: int = 10) -> list[dict]:
    """Return highest-viewed unwatched videos."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT bvid, title, up_name, view_count, "
            "  duration_seconds, category_v2 "
            "FROM watch_later "
            "WHERE (progress_seconds IS NULL OR progress_seconds = 0) "
            "ORDER BY view_count DESC NULLS LAST "
            "LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "bvid": r[0], "title": r[1], "up_name": r[2],
            "view_count": r[3], "duration_seconds": r[4],
            "category_v2": r[5],
        }
        for r in rows
    ]
