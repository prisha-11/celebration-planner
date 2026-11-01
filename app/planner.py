"""Builds a complete plan (budget, timeline, vendor checklist, ideas) from a validated request."""

from __future__ import annotations

from datetime import date, timedelta

from .budget import allocate_budget
from .ideas import offline_ideas
from .models import PlanRequest, PlanResponse, PlanSummary
from .timeline import build_timeline
from .vendors import vendor_checklist

MAX_PLANNING_DAYS = 5 * 366


class InvalidEventDate(ValueError):
    """The event date is in the past or too far in the future to plan."""


def build_plan(req: PlanRequest, today: date | None = None) -> PlanResponse:
    today = today or date.today()
    if req.event_date < today:
        raise InvalidEventDate("Event date cannot be in the past.")
    if req.event_date > today + timedelta(days=MAX_PLANNING_DAYS):
        raise InvalidEventDate("Event date must be within the next 5 years.")

    days_until = (req.event_date - today).days
    budget = allocate_budget(req.event_type, req.total_budget, req.guest_count, req.currency)
    timeline, compressed = build_timeline(req.event_type, req.event_date, today)

    notes: list[str] = []
    if days_until == 0:
        notes.append("Your event is today. Focus on the high-priority checklist items and day-of logistics.")
    elif compressed:
        notes.append(
            f"Your event is {days_until} day{'s' if days_until != 1 else ''} away, so {compressed} milestone"
            f"{'s' if compressed != 1 else ''} that would normally be scheduled earlier "
            f"{'have' if compressed != 1 else 'has'} been moved to today. Start with the high-priority vendor tasks."
        )

    return PlanResponse(
        summary=PlanSummary(
            event_type=req.event_type,
            event_name=req.event_name,
            event_date=req.event_date,
            days_until_event=days_until,
            guest_count=req.guest_count,
            city=req.city,
        ),
        budget=budget,
        timeline=timeline,
        vendors=vendor_checklist(req.event_type),
        ideas=offline_ideas(req),
        notes=notes,
    )
