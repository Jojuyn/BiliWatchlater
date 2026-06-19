from dataclasses import dataclass

import pandas as pd

from .models import BASE_COLUMNS, WatchLaterVideo
from .storage import videos_to_dataframe


@dataclass(frozen=True)
class SyncResult:
    dataframe: pd.DataFrame
    total: int
    added: int
    removed: int
    updated: int


def sync_dataframes(old: pd.DataFrame, videos: list[WatchLaterVideo]) -> SyncResult:
    online = videos_to_dataframe(videos)
    if online.empty:
        return SyncResult(
            dataframe=old.iloc[0:0].copy(),
            total=0,
            added=0,
            removed=len(old),
            updated=0,
        )

    if old.empty or "bvid" not in old.columns:
        return SyncResult(
            dataframe=online,
            total=len(online),
            added=len(online),
            removed=0,
            updated=0,
        )

    old_indexed = old.drop_duplicates(subset=["bvid"], keep="first").set_index("bvid", drop=False)
    online_indexed = online.drop_duplicates(subset=["bvid"], keep="first").set_index("bvid", drop=False)

    old_bvids = set(old_indexed.index)
    online_bvids = set(online_indexed.index)
    kept_bvids = [bvid for bvid in old_indexed.index if bvid in online_bvids]
    added_bvids = [bvid for bvid in online_indexed.index if bvid not in old_bvids]

    custom_columns = [column for column in old.columns if column not in BASE_COLUMNS]
    final_rows = []
    updated = 0

    for bvid in kept_bvids:
        old_row = old_indexed.loc[bvid].to_dict()
        online_row = online_indexed.loc[bvid].to_dict()
        for column in BASE_COLUMNS:
            if column in online_row:
                old_value = old_row.get(column)
                new_value = online_row.get(column)
                if old_value != new_value:
                    updated += 1
                old_row[column] = new_value
        final_rows.append(old_row)

    for bvid in added_bvids:
        row = online_indexed.loc[bvid].to_dict()
        for column in custom_columns:
            row.setdefault(column, "")
        final_rows.append(row)

    columns = BASE_COLUMNS + [column for column in old.columns if column not in BASE_COLUMNS]
    final = pd.DataFrame(final_rows)
    final = final.reindex(columns=columns)

    return SyncResult(
        dataframe=final,
        total=len(final),
        added=len(added_bvids),
        removed=len(old_bvids - online_bvids),
        updated=updated,
    )

