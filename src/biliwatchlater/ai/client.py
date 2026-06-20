"""Unified AI client supporting OpenAI-compatible APIs (DeepSeek, Qwen, Kimi, etc.)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AISettings:
    provider: str = ""
    api_key: str = ""
    base_url: str = ""
    model: str = ""

    @property
    def available(self) -> bool:
        return bool(self.api_key) and bool(self.base_url)


def load_ai_settings() -> AISettings:
    return AISettings(
        provider=os.getenv("AI_PROVIDER", ""),
        api_key=os.getenv("AI_API_KEY", ""),
        base_url=os.getenv("AI_BASE_URL", ""),
        model=os.getenv("AI_MODEL", ""),
    )


class AIClient:
    """Thin wrapper around OpenAI-compatible chat completion API."""

    def __init__(self, settings: AISettings) -> None:
        self._settings = settings

    async def chat(self, messages: list[dict], **kwargs: object) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=self._settings.api_key,
            base_url=self._settings.base_url,
        )
        response = await client.chat.completions.create(
            model=self._settings.model or "deepseek-chat",
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""
