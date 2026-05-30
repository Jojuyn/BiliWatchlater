import asyncio
from bilibili_api import video
from bilibili_api import Credential

SESSDATA="cd970405%2C1780529043%2C2fb73%2Ac2CjD92NhG6iQbbNEEpS0XW8D_JpLzOgdqJH5G0jqcIJQvhx1P_Czm6vYvYqPTZ7n1a98SVjExTHFuV212NkVyMmhweDdGakZEb3FDTHBERTV6Rm9PV1lSOUFvZlRjMU90azU5SmNObC1Zc093SUlfbTdneHZ5bTlGbTZyeFljMF9pb0IwYzM3cHVRIIEC"
BILI_JCT="86d9c3e3bb89ffe1c70d9a804c1c91ea"
BUVID3="30F64050-5CB5-BF3E-73D4-9440E0E8B33695419infoc"
DEDEUSERID="396956118"
AC_TIME_VALUE="91453573a3911aa731407df4dc6da361"

async def main() -> None:
    credential = Credential(
        sessdata=SESSDATA,
        bili_jct=BILI_JCT,
        buvid3=BUVID3,
        dedeuserid=DEDEUSERID,
        ac_time_value=AC_TIME_VALUE
    )
    v = video.Video(bvid="BV11YGB67E3z", credential=credential)
    info = await v.get_info()
    print(info)
    await v.like(True)

if __name__ == "__main__":
    asyncio.run(main())