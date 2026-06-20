import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_ENV_VARS = (
    "BILI_SESSDATA",
    "BILI_JCT",
    "BILI_BUVID3",
    "BILI_DEDEUSERID",
)


@dataclass(frozen=True)
class Settings:
    sessdata: str
    bili_jct: str
    buvid3: str
    dedeuserid: str
    ac_time_value: str = ""
    db_path: Path = Path("watch_later.db")
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""


def load_settings(env_path: str | Path = ".env", db_path: str | Path = "watch_later.db") -> Settings:
    load_dotenv(env_path)

    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {names}")

    return Settings(
        sessdata=os.environ["BILI_SESSDATA"],
        bili_jct=os.environ["BILI_JCT"],
        buvid3=os.environ["BILI_BUVID3"],
        dedeuserid=os.environ["BILI_DEDEUSERID"],
        ac_time_value=os.getenv("BILI_AC_TIME_VALUE", ""),
        db_path=Path(db_path),
        ai_provider=os.getenv("AI_PROVIDER", ""),
        ai_api_key=os.getenv("AI_API_KEY", ""),
        ai_base_url=os.getenv("AI_BASE_URL", ""),
        ai_model=os.getenv("AI_MODEL", ""),
    )
