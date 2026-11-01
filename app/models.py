"""Pydantic models: validated request payloads and plan responses."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .security import sanitize_text

SUPPORTED_CURRENCIES = ("INR", "USD", "EUR", "GBP", "AUD", "CAD", "AED")


class EventType(str, Enum):
    WEDDING = "wedding"
    BIRTHDAY = "birthday"
    COMMUNITY = "community"


class PlanRequest(BaseModel):
    """What the user tells us about their event."""

    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    event_name: str = Field(min_length=1, max_length=100)
    event_date: date
    guest_count: int = Field(ge=1, le=5000)
    total_budget: float = Field(gt=0, le=1_000_000_000, allow_inf_nan=False)
    currency: str = Field(default="INR", pattern=r"^(" + "|".join(SUPPORTED_CURRENCIES) + r")$")
    city: str = Field(default="", max_length=80)
    preferences: str = Field(default="", max_length=500)

    @field_validator("event_name", "city", "preferences", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> object:
        return sanitize_text(value) if isinstance(value, str) else value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: PlanRequest
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question", mode="before")
    @classmethod
    def _clean_question(cls, value: object) -> object:
        return sanitize_text(value) if isinstance(value, str) else value


class BudgetLine(BaseModel):
    category: str
    percent: int
    amount: float


class BudgetPlan(BaseModel):
    currency: str
    total: float
    per_guest: float
    lines: list[BudgetLine]


class Milestone(BaseModel):
    title: str
    detail: str
    due_date: date
    days_before: int
    urgent: bool = False


class VendorTask(BaseModel):
    category: str
    task: str
    priority: Literal["high", "medium", "low"]


class Idea(BaseModel):
    title: str
    description: str


class PlanSummary(BaseModel):
    event_type: EventType
    event_name: str
    event_date: date
    days_until_event: int
    guest_count: int
    city: str


class PlanResponse(BaseModel):
    summary: PlanSummary
    budget: BudgetPlan
    timeline: list[Milestone]
    vendors: list[VendorTask]
    ideas: list[Idea]
    notes: list[str]


class IdeasResponse(BaseModel):
    ideas: list[Idea]
    source: Literal["ai", "offline"]


class ChatResponse(BaseModel):
    answer: str
    source: Literal["ai", "offline"]
