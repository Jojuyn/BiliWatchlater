from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


BASE_COLUMNS = [
    "bvid",
    "aid",
    "cid",
    "title",
    "up_mid",
    "up_name",
    "pub_date",
    "added_at",
    "duration_seconds",
    "category",
    "category_v2",
    "parent_category_v2",
    "description",
    "cover_url",
    "short_url",
    "view_count",
    "favorite_count",
    "coin_count",
    "like_count",
    "reply_count",
    "danmaku_count",
    "progress_seconds",
]


@dataclass(frozen=True)
class WatchLaterVideo:
    bvid: str
    aid: int | None
    cid: int | None
    title: str
    up_mid: int | None
    up_name: str
    pub_date: str
    added_at: str
    duration_seconds: int | None
    category: str
    category_v2: str
    parent_category_v2: str
    description: str
    cover_url: str
    short_url: str
    view_count: int | None
    favorite_count: int | None
    coin_count: int | None
    like_count: int | None
    reply_count: int | None
    danmaku_count: int | None
    progress_seconds: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def format_timestamp(value: Any) -> str:
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


def video_from_api_item(item: dict[str, Any]) -> WatchLaterVideo:
    owner = item.get("owner") or {}
    stat = item.get("stat") or {}
    page = item.get("page") or {}

    return WatchLaterVideo(
        bvid=str(item.get("bvid", "")),
        aid=item.get("aid"),
        cid=item.get("cid") or page.get("cid"),
        title=str(item.get("title", "")),
        up_mid=owner.get("mid"),
        up_name=str(owner.get("name", "")),
        pub_date=format_timestamp(item.get("pubdate")),
        added_at=format_timestamp(item.get("add_at")),
        duration_seconds=item.get("duration") or page.get("duration"),
        category=str(item.get("tname", "")),
        category_v2=str(item.get("tnamev2", "")),
        parent_category_v2=str(item.get("pid_name_v2", "")),
        description=str(item.get("desc", "")),
        cover_url=str(item.get("pic", "")),
        short_url=str(item.get("short_link_v2", "")),
        view_count=stat.get("view") or stat.get("vv"),
        favorite_count=stat.get("favorite"),
        coin_count=stat.get("coin"),
        like_count=stat.get("like"),
        reply_count=stat.get("reply"),
        danmaku_count=stat.get("danmaku"),
        progress_seconds=item.get("progress"),
    )

