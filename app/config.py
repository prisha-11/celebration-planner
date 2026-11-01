"""Application settings, read once from environment variables (and an optional .env file).

The app runs fully without any API key. If ANTHROPIC_API_KEY is set, the AI-powered
features (personalised ideas and the planning chat) use Claude; otherwise they fall
back to built-in rule-based logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _float_env(name: str, default: float, minimum: float = 1.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    ai_timeout_seconds: float = 30.0
    ai_max_tokens: int = 1200
    rate_limit_per_minute: int = 60
    ai_rate_limit_per_minute: int = 10
    max_body_bytes: int = 16_384

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        # Real environment variables always win over values in .env.
        load_dotenv(PROJECT_ROOT / ".env")
        key = (os.getenv("ANTHROPIC_API_KEY") or "").strip() or None
        model = (os.getenv("ANTHROPIC_MODEL") or "").strip() or cls.anthropic_model
        return cls(
            anthropic_api_key=key,
            anthropic_model=model,
            ai_timeout_seconds=_float_env("AI_TIMEOUT_SECONDS", cls.ai_timeout_seconds),
            ai_max_tokens=_int_env("AI_MAX_TOKENS", cls.ai_max_tokens, minimum=100),
            rate_limit_per_minute=_int_env("RATE_LIMIT_PER_MINUTE", cls.rate_limit_per_minute),
            ai_rate_limit_per_minute=_int_env("AI_RATE_LIMIT_PER_MINUTE", cls.ai_rate_limit_per_minute),
            max_body_bytes=_int_env("MAX_BODY_BYTES", cls.max_body_bytes, minimum=1024),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
