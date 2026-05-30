import asyncio
from datetime import datetime
import os
import pandas as pd
from bilibili_api import Credential
from bilibili_api.user import get_toview_list
from dotenv import load_dotenv

load_dotenv()

SESSDATA = os.getenv('BILI_SESSDATA', "")
BILI_JCT = os.getenv('BILI_JCT', "")
BUVID3 = os.getenv('BILI_BUVID3', "")
DEDEUSERID = os.getenv('BILI_DEDEUSERID', "")
AC_TIME_VALUE = os.getenv('BILI_AC_TIME_VALUE', "")

async def main() -> None:
    # 1. 获取credential
    credential = Credential(
        sessdata=SESSDATA,
        bili_jct=BILI_JCT,
        buvid3=BUVID3,
        dedeuserid=DEDEUSERID,
        ac_time_value=AC_TIME_VALUE
    )
    # 2. 获取稍后再看列表，提取为视频列表
    toview_list = await get_toview_list(credential=credential)
    video_list = toview_list.get('list', [])
    # 3. 清洗数据封装成列表
    online_videos = []
    for item in video_list:
        online_videos.append({
            'bvid': item['bvid'],
            'title': item['title'],
            'up_name': item.get('owner', {}).get('name'),
            'pub_date': datetime.fromtimestamp(item.get('pubdate', 0)).strftime('%Y-%m-%d %H:%M:%S')
        })
    df_online = pd.DataFrame(online_videos)
    # 3. 动态维护一个csv文件
    csv_path = 'watch_later.csv'
    if os.path.exists(csv_path):
        df_old = pd.read_csv(csv_path)
        df_remain = df_old[df_old['bvid'].isin(df_online['bvid'])].copy()
        df_new = df_online[~df_online['bvid'].isin(df_remain['bvid'])]
        df_final = pd.concat([df_remain, df_new], ignore_index=True)
        print(f'动态同步完成：新增了{len(df_new)}个视频，移除了{len(df_old) - len(df_remain)}个失效/已看视频。')
    else:
        df_final = df_online
        print(f'初次运行：成功初始化创建本地csv，并写入{len(df_final)}条数据')
    df_final.to_csv(csv_path, index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    asyncio.run(main())