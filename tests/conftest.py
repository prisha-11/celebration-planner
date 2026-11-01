from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import AssistantService  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from asgi_client import ASGIClient  # noqa: E402


def payload(**overrides):
    """A valid /api/plan request body (event 200 days away unless overridden)."""
    data = {
        "event_type": "wedding",
        "event_name": "Asha and Rohan",
        "event_date": (date.today() + timedelta(days=200)).isoformat(),
        "guest_count": 150,
        "total_budget": 1_500_000,
        "currency": "INR",
        "city": "Pune",
        "preferences": "outdoor garden, vegetarian menu",
    }
    data.update(overrides)
    return data


@pytest.fixture
def make_client():
    def factory(settings: Settings | None = None, assistant: AssistantService | None = None) -> ASGIClient:
        settings = settings or Settings(rate_limit_per_minute=1000, ai_rate_limit_per_minute=1000)
        return ASGIClient(create_app(settings, assistant))

    return factory


@pytest.fixture
def client(make_client):
    return make_client()
