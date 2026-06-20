"""CRUD operations for tags, annotations, and batch management."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from .storage import (
    TAGS_TABLE,
    VIDEO_TAGS_TABLE,
    VIDEO_ANNOTATIONS_TABLE,
    ensure_schema,
)


# ── Tag operations ──────────────────────────────────────────────────────────

def add_tag(db_path: Path, bvid: str, tag_name: str) -> int:
    """Assign tag_name to bvid. Creates the tag if it doesn't exist.
    Returns tag_id.
    """
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            f"INSERT OR IGNORE INTO {TAGS_TABLE} (name) VALUES (?)",
            (tag_name,),
        )
        tag_id = conn.execute(
            f"SELECT id FROM {TAGS_TABLE} WHERE name = ?", (tag_name,)
        ).fetchone()[0]
        conn.execute(
            f"INSERT OR IGNORE INTO {VIDEO_TAGS_TABLE} (bvid, tag_id) VALUES (?, ?)",
            (bvid, tag_id),
        )
        conn.execute(
            f"UPDATE {TAGS_TABLE} SET usage_count = ("
            f"SELECT COUNT(*) FROM {VIDEO_TAGS_TABLE} WHERE tag_id = ?"
            f") WHERE id = ?",
            (tag_id, tag_id),
        )
    return tag_id


def remove_tag(db_path: Path, bvid: str, tag_name: str) -> bool:
    """Remove tag_name from bvid. Cleans up orphaned tags.
    Returns True if tag was removed.
    """
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        tag = conn.execute(
            f"SELECT id FROM {TAGS_TABLE} WHERE name = ?", (tag_name,)
        ).fetchone()
        if not tag:
            return False
        tag_id = tag[0]
        cursor = conn.execute(
            f"DELETE FROM {VIDEO_TAGS_TABLE} WHERE bvid = ? AND tag_id = ?",
            (bvid, tag_id),
        )
        if cursor.rowcount == 0:
            return False
        # Cleanup orphan tags
        conn.execute(
            f"DELETE FROM {TAGS_TABLE} WHERE id = ? AND NOT EXISTS ("
            f"SELECT 1 FROM {VIDEO_TAGS_TABLE} WHERE tag_id = ?"
            f")",
            (tag_id, tag_id),
        )
    return True


def list_tags(db_path: Path) -> list[dict]:
    """Return all tags with usage counts, sorted by count descending."""
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT id, name, color, usage_count, "
            f"  parent_id FROM {TAGS_TABLE} "
            f"ORDER BY usage_count DESC, name ASC"
        ).fetchall()
    return [
        {"id": r[0], "name": r[1], "color": r[2],
         "count": r[3], "parent_id": r[4]}
        for r in rows
    ]


def list_video_tags(db_path: Path, bvid: str) -> list[dict]:
    """Return tags assigned to a specific video."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT t.id, t.name, t.color FROM {TAGS_TABLE} t "
            f"JOIN {VIDEO_TAGS_TABLE} vt ON t.id = vt.tag_id "
            f"WHERE vt.bvid = ? "
            f"ORDER BY t.name ASC",
            (bvid,),
        ).fetchall()
    return [
        {"id": r[0], "name": r[1], "color": r[2]}
        for r in rows
    ]


# ── Annotation operations ──────────────────────────────────────────────────

ANNOTATION_FIELDS = [
    "note", "priority", "archived", "archived_at",
    "watched", "rating",
]


def _ensure_annotation(db_path: Path, bvid: str) -> None:
    """Ensure a row exists in video_annotations for this bvid."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"INSERT OR IGNORE INTO {VIDEO_ANNOTATIONS_TABLE} "
            f"(bvid) VALUES (?)",
            (bvid,),
        )


def set_annotation(
    db_path: Path, bvid: str, field: str, value: object,
) -> None:
    """Set a single annotation field for a video."""
    if field not in ANNOTATION_FIELDS:
        raise ValueError(
            f"Unknown annotation field: {field}. "
            f"Valid: {', '.join(ANNOTATION_FIELDS)}"
        )
    ensure_schema(db_path)
    _ensure_annotation(db_path, bvid)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"UPDATE {VIDEO_ANNOTATIONS_TABLE} "
            f"SET {field} = ?, updated_at = datetime('now') "
            f"WHERE bvid = ?",
            (value, bvid),
        )


def set_priority(db_path: Path, bvid: str, level: int) -> None:
    """Set priority level: 0=none, 1=high, 2=medium, 3=low."""
    if level not in (0, 1, 2, 3):
        raise ValueError("Priority must be 0, 1, 2, or 3")
    set_annotation(db_path, bvid, "priority", level)


def set_note(db_path: Path, bvid: str, text: str) -> None:
    set_annotation(db_path, bvid, "note", text)


def set_watched(db_path: Path, bvid: str, watched: bool = True) -> None:
    set_annotation(db_path, bvid, "watched", int(watched))


def set_archived(db_path: Path, bvid: str, archived: bool = True) -> None:
    set_annotation(
        db_path, bvid, "archived", int(archived),
    )
    if archived:
        set_annotation(
            db_path, bvid, "archived_at",
            __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        )


def set_rating(db_path: Path, bvid: str, rating: int | None) -> None:
    if rating is not None and not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5, or None")
    set_annotation(db_path, bvid, "rating", rating)


def get_annotations(db_path: Path, bvid: str) -> dict | None:
    """Return the annotation row for a video, or None."""
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"SELECT * FROM {VIDEO_ANNOTATIONS_TABLE} WHERE bvid = ?",
            (bvid,),
        ).fetchone()
    if not row:
        return None
    columns = [
        "bvid", "note", "priority", "archived", "archived_at",
        "watched", "rating", "ai_summary", "ai_keywords",
        "ai_relevance_score", "created_at", "updated_at",
    ]
    return dict(zip(columns, row))


# ── Batch operations ────────────────────────────────────────────────────────

def batch_archive_watched(db_path: Path) -> int:
    """Archive all videos marked as watched.
    Returns number of videos affected.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE {VIDEO_ANNOTATIONS_TABLE} SET "
            f"archived = 1, archived_at = datetime('now'), "
            f"updated_at = datetime('now') "
            f"WHERE watched = 1 AND archived = 0"
        )
    return cursor.rowcount


def batch_clear_watched(db_path: Path) -> int:
    """Reset all watched flags to 0.
    Returns number of videos affected.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE {VIDEO_ANNOTATIONS_TABLE} SET "
            f"watched = 0, updated_at = datetime('now') "
            f"WHERE watched = 1"
        )
    return cursor.rowcount


def batch_tag_videos(
    db_path: Path, bvids: list[str], tag_name: str,
) -> int:
    """Assign a tag to multiple videos. Returns number tagged."""
    count = 0
    for bvid in bvids:
        add_tag(db_path, bvid, tag_name)
        count += 1
    return count
