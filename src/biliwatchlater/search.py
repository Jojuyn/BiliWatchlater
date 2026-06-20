"""FTS5 search engine with multi-condition filtering and sorting."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .categories import CATEGORY_MAP, PARENT_GROUP_MAP, get_color, get_group, get_tag


ALLOWED_SORT_COLUMNS = {
    "view_count": "w.view_count",
    "like_count": "w.like_count",
    "favorite_count": "w.favorite_count",
    "duration": "w.duration_seconds",
    "pub_date": "w.pub_date",
    "added_at": "w.added_at",
}

DURATION_RANGES = {
    "<5min": (None, 300),
    "5-10min": (300, 600),
    "10-20min": (600, 1200),
    "20-40min": (1200, 2400),
    ">40min": (2400, None),
}


@dataclass
class SearchFilter:
    query: str = ""
    category_v2: str | None = None
    category_group: str | None = None
    duration_range: str | None = None  # key in DURATION_RANGES
    status: str | None = None          # unwatched / watching / watched
    include_archived: bool = False
    sort_by: str = "added_at"
    ascending: bool = False
    limit: int = 20
    offset: int = 0


@dataclass
class SearchResult:
    items: list[dict]
    total: int


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _compute_status(progress: int | None, duration: int | None) -> str:
    if progress is None or progress == 0:
        return "unwatched"
    if duration and progress >= duration:
        return "watched"
    return "watching"


def _build_where(filters: SearchFilter) -> tuple[str, list]:
    clauses = []
    params: list = []

    # Category exact match
    if filters.category_v2:
        clauses.append("w.category_v2 = ?")
        params.append(filters.category_v2)

    # Category group — resolve to category_v2 list
    if filters.category_group:
        group_cats = [
            cat for cat, meta in CATEGORY_MAP.items()
            if meta["group"] == filters.category_group
        ]
        if group_cats:
            placeholders = ",".join("?" * len(group_cats))
            clauses.append(f"w.category_v2 IN ({placeholders})")
            params.extend(group_cats)

    # Duration range
    if filters.duration_range and filters.duration_range in DURATION_RANGES:
        dmin, dmax = DURATION_RANGES[filters.duration_range]
        if dmin is not None:
            clauses.append("w.duration_seconds >= ?")
            params.append(dmin)
        if dmax is not None:
            clauses.append("w.duration_seconds < ?")
            params.append(dmax)

    # Status (watched / watching / unwatched)
    if filters.status == "unwatched":
        clauses.append("(w.progress_seconds IS NULL OR w.progress_seconds = 0)")
    elif filters.status == "watching":
        clauses.append(
            "w.progress_seconds > 0 "
            "AND (w.duration_seconds IS NULL OR w.progress_seconds < w.duration_seconds)"
        )
    elif filters.status == "watched":
        clauses.append(
            "w.duration_seconds IS NOT NULL "
            "AND w.progress_seconds >= w.duration_seconds"
        )

    # Archived filter
    if not filters.include_archived:
        clauses.append("(va.archived IS NULL OR va.archived = 0)")

    where_sql = " AND ".join(clauses) if clauses else "1=1"
    return where_sql, params


def _build_query(filters: SearchFilter) -> tuple[str, list, str, list]:
    """Return (query_sql, query_params, count_sql, count_params)."""
    where_clause, where_params = _build_where(filters)

    # Determine sort
    sort_col = ALLOWED_SORT_COLUMNS.get(filters.sort_by, "w.added_at")
    sort_dir = "ASC" if filters.ascending else "DESC"

    # Determine FTS join
    fts_join = ""
    fts_where = ""
    if filters.query.strip():
        fts_join = "JOIN watch_later_fts fts ON w.bvid = fts.bvid"
        fts_where = "watch_later_fts MATCH ? AND "
        where_params.insert(0, filters.query)

    full_where = fts_where + where_clause

    select_cols = [
        "w.bvid", "w.title", "w.up_name", "w.up_mid",
        "w.duration_seconds", "w.category", "w.category_v2",
        "w.parent_category_v2", "w.description",
        "w.pub_date", "w.added_at",
        "w.view_count", "w.like_count", "w.favorite_count",
        "w.coin_count", "w.reply_count", "w.danmaku_count",
        "w.progress_seconds", "w.cover_url", "w.short_url",
    ]
    select_sql = ", ".join(select_cols)

    base = f"""
        FROM watch_later w
        {fts_join}
        LEFT JOIN video_annotations va ON w.bvid = va.bvid
        WHERE {full_where}
    """

    # Count query
    count_sql = f"SELECT COUNT(*) {base}"
    count_params = list(where_params)

    # Data query
    data_sql = (
        f"SELECT {select_sql}, "
        f"  va.note, va.priority, va.watched AS ann_watched, "
        f"  va.archived AS ann_archived "
        f"{base}"
        f"ORDER BY {sort_col} {sort_dir} "
        f"LIMIT ? OFFSET ?"
    )
    data_params = list(where_params) + [filters.limit, filters.offset]

    return data_sql, data_params, count_sql, count_params


def search_videos(db_path: Path, filters: SearchFilter | None = None) -> SearchResult:
    """Execute a search and return results with computed display fields."""
    filters = filters or SearchFilter()
    data_sql, data_params, count_sql, count_params = _build_query(filters)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Get total count
        total = conn.execute(count_sql, count_params).fetchone()[0]

        # Get data rows
        rows = conn.execute(data_sql, data_params).fetchall()
        items = [dict(r) for r in rows]

        # Batch fetch tags for all result bvids
        if items:
            bvids = [r["bvid"] for r in items]
            placeholders = ",".join("?" * len(bvids))
            tag_rows = conn.execute(
                f"SELECT vt.bvid, t.name, t.color "
                f"FROM video_tags vt "
                f"JOIN tags t ON vt.tag_id = t.id "
                f"WHERE vt.bvid IN ({placeholders}) "
                f"ORDER BY t.name ASC",
                bvids,
            ).fetchall()
            tag_map: dict[str, list[dict]] = {}
            for bvid, name, color in tag_rows:
                tag_map.setdefault(bvid, []).append(
                    {"name": name, "color": color}
                )

        # Enrich each item with computed fields
        for item in items:
            item["duration_display"] = format_duration(item["duration_seconds"])
            item["status"] = _compute_status(
                item["progress_seconds"], item["duration_seconds"]
            )
            item["category_group"] = get_group(
                item["category_v2"], item["parent_category_v2"] or ""
            )
            item["category_tag"] = get_tag(item["category_v2"])
            item["category_color"] = get_color(item["category_v2"])
            item["note_preview"] = (
                item["note"][:60] + "..." if item["note"] and len(item["note"]) > 60
                else item["note"] or ""
            )
            item["tags"] = tag_map.get(item["bvid"], [])

    return SearchResult(items=items, total=total)
