from datetime import date, timedelta

import pytest

from app.budget import budget_categories
from app.ideas import IDEA_COUNT, offline_ideas
from app.models import EventType, PlanRequest
from app.planner import InvalidEventDate, build_plan
from app.timeline import build_timeline
from app.vendors import vendor_checklist

TODAY = date(2026, 11, 1)


def make_request(**overrides):
    data = dict(
        event_type="birthday",
        event_name="Mira's 10th",
        event_date=TODAY + timedelta(days=90),
        guest_count=30,
        total_budget=50_000,
        preferences="",
    )
    data.update(overrides)
    return PlanRequest(**data)


# ---- timeline ----

@pytest.mark.parametrize("event_type", list(EventType))
def test_timeline_is_sorted_and_never_in_the_past(event_type):
    milestones, _ = build_timeline(event_type, TODAY + timedelta(days=400), TODAY)
    dates = [m.due_date for m in milestones]
    assert dates == sorted(dates)
    assert all(d >= TODAY for d in dates)


def test_far_future_event_has_no_urgent_milestones():
    milestones, compressed = build_timeline(EventType.WEDDING, TODAY + timedelta(days=500), TODAY)
    assert compressed == 0
    assert not any(m.urgent for m in milestones)


def test_short_runway_compresses_early_milestones_to_today():
    milestones, compressed = build_timeline(EventType.WEDDING, TODAY + timedelta(days=20), TODAY)
    assert compressed > 0
    urgent = [m for m in milestones if m.urgent]
    assert len(urgent) == compressed
    assert all(m.due_date == TODAY for m in urgent)
    assert all(m.days_before > 20 for m in urgent)


def test_urgent_milestones_keep_their_original_order():
    milestones, _ = build_timeline(EventType.WEDDING, TODAY + timedelta(days=20), TODAY)
    urgent_days = [m.days_before for m in milestones if m.urgent]
    assert urgent_days == sorted(urgent_days, reverse=True)


def test_event_day_and_post_event_milestones_present():
    event = TODAY + timedelta(days=60)
    milestones, _ = build_timeline(EventType.COMMUNITY, event, TODAY)
    assert any(m.due_date == event for m in milestones)
    assert milestones[-1].due_date > event


# ---- vendors ----

@pytest.mark.parametrize("event_type", list(EventType))
def test_vendor_categories_match_budget_categories(event_type):
    categories = set(budget_categories(event_type))
    assert {task.category for task in vendor_checklist(event_type)} <= categories


@pytest.mark.parametrize("event_type", list(EventType))
def test_checklist_has_high_priority_tasks_and_unique_entries(event_type):
    tasks = vendor_checklist(event_type)
    assert any(t.priority == "high" for t in tasks)
    keys = [(t.category, t.task) for t in tasks]
    assert len(keys) == len(set(keys))


# ---- ideas ----

@pytest.mark.parametrize("event_type", list(EventType))
def test_offline_ideas_count_and_content(event_type):
    ideas = offline_ideas(make_request(event_type=event_type.value))
    assert len(ideas) == IDEA_COUNT
    assert all(i.title and i.description for i in ideas)


def test_preferences_steer_theme_choice():
    beach = offline_ideas(make_request(event_type="wedding", preferences="Beach sunset, coastal vibes"))
    assert beach[0].title == "Beach and Sunset Celebration"
    rustic = offline_ideas(make_request(event_type="wedding", preferences="rustic barn and vintage"))
    assert rustic[0].title == "Boho Rustic"


def test_ideas_are_deterministic():
    req = make_request(preferences="movie night")
    assert offline_ideas(req) == offline_ideas(req)


def test_city_is_mentioned_in_first_idea():
    ideas = offline_ideas(make_request(city="Pune"))
    assert "Pune" in ideas[0].description


# ---- planner ----

def test_build_plan_assembles_everything():
    plan = build_plan(make_request(), today=TODAY)
    assert plan.summary.days_until_event == 90
    assert plan.budget.lines and plan.timeline and plan.vendors and plan.ideas


def test_build_plan_rejects_past_dates():
    with pytest.raises(InvalidEventDate):
        build_plan(make_request(event_date=TODAY - timedelta(days=1)), today=TODAY)


def test_build_plan_rejects_dates_too_far_away():
    with pytest.raises(InvalidEventDate):
        build_plan(make_request(event_date=date(2999, 1, 1)), today=TODAY)


def test_event_today_is_allowed_with_a_note():
    plan = build_plan(make_request(event_date=TODAY), today=TODAY)
    assert plan.summary.days_until_event == 0
    assert any("today" in note for note in plan.notes)


def test_compressed_plan_explains_itself():
    plan = build_plan(make_request(event_date=TODAY + timedelta(days=10)), today=TODAY)
    assert plan.notes and "moved to today" in plan.notes[0]
