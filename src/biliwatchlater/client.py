from bilibili_api import Credential
from bilibili_api.user import get_toview_list

from .config import Settings
from .models import WatchLaterVideo, video_from_api_item


class BilibiliWatchLaterClient:
    def __init__(self, settings: Settings) -> None:
        self._credential = Credential(
            sessdata=settings.sessdata,
            bili_jct=settings.bili_jct,
            buvid3=settings.buvid3,
            dedeuserid=settings.dedeuserid,
            ac_time_value=settings.ac_time_value,
        )

    async def fetch_watch_later(self) -> list[WatchLaterVideo]:
        response = await get_toview_list(credential=self._credential)
        items = response.get("list", [])
        return [video_from_api_item(item) for item in items if item.get("bvid")]

