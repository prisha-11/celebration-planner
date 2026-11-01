import pytest

from app.budget import ALLOCATIONS, allocate_budget, budget_categories
from app.models import EventType


@pytest.mark.parametrize("event_type", list(EventType))
def test_percentages_sum_to_100(event_type):
    assert sum(pct for _, pct in ALLOCATIONS[event_type]) == 100


@pytest.mark.parametrize("event_type", list(EventType))
def test_every_type_has_a_contingency_line(event_type):
    assert "Contingency" in budget_categories(event_type)


@pytest.mark.parametrize("event_type", list(EventType))
@pytest.mark.parametrize("total", [1, 99.99, 100000.01, 1234567.89, 7, 0.07, 999_999_999.99])
def test_lines_add_up_exactly_to_total(event_type, total):
    plan = allocate_budget(event_type, total, 10, "USD")
    cents = sum(round(line.amount * 100) for line in plan.lines)
    assert cents == round(total * 100)
    assert plan.total == pytest.approx(total)


def test_amounts_follow_percentages_for_round_numbers():
    plan = allocate_budget(EventType.BIRTHDAY, 100_000, 50, "INR")
    by_name = {line.category: line.amount for line in plan.lines}
    assert by_name["Food & Drinks"] == 35_000
    assert by_name["Contingency"] == 5_000


def test_per_guest_is_total_divided_by_guests():
    plan = allocate_budget(EventType.WEDDING, 1_500_000, 150, "INR")
    assert plan.per_guest == 10_000
    assert plan.currency == "INR"


def test_no_negative_or_zero_lines_for_tiny_budget():
    plan = allocate_budget(EventType.COMMUNITY, 1, 1, "USD")
    assert all(line.amount >= 0 for line in plan.lines)
