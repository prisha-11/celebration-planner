"""Budget allocation: split a total budget across categories without losing a single paisa/cent."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .models import BudgetLine, BudgetPlan, EventType

# (category, percent). Each event type's percentages must add up to exactly 100.
ALLOCATIONS: dict[EventType, tuple[tuple[str, int], ...]] = {
    EventType.WEDDING: (
        ("Venue", 20),
        ("Catering", 30),
        ("Attire & Beauty", 12),
        ("Photography & Video", 10),
        ("Decor & Flowers", 8),
        ("Music & Entertainment", 6),
        ("Invitations & Stationery", 2),
        ("Travel & Stay", 4),
        ("Rituals & Officiant", 3),
        ("Contingency", 5),
    ),
    EventType.BIRTHDAY: (
        ("Venue", 20),
        ("Food & Drinks", 35),
        ("Cake", 7),
        ("Decor & Balloons", 12),
        ("Entertainment", 12),
        ("Photography", 4),
        ("Invitations & Favours", 5),
        ("Contingency", 5),
    ),
    EventType.COMMUNITY: (
        ("Venue & Permits", 20),
        ("Food & Refreshments", 25),
        ("Stage & AV", 15),
        ("Marketing & Printing", 10),
        ("Volunteer Supplies", 8),
        ("Programme & Performers", 10),
        ("Safety & Insurance", 4),
        ("Contingency", 8),
    ),
}


def budget_categories(event_type: EventType) -> list[str]:
    return [name for name, _ in ALLOCATIONS[event_type]]


def _to_cents(amount: float) -> int:
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _from_cents(cents: int) -> float:
    return float(Decimal(cents) / 100)


def allocate_budget(
    event_type: EventType, total_budget: float, guest_count: int, currency: str
) -> BudgetPlan:
    """Allocate ``total_budget`` by the event type's percentages.

    Uses the largest-remainder method on integer cents so the lines always add up to the total.
    """
    shares = ALLOCATIONS[event_type]
    total_cents = _to_cents(total_budget)

    base = [total_cents * pct // 100 for _, pct in shares]
    remainders = [total_cents * pct % 100 for _, pct in shares]
    leftover = total_cents - sum(base)
    # Give the leftover cents to the lines with the biggest remainders (ties: earlier line first).
    for index in sorted(range(len(shares)), key=lambda i: (-remainders[i], i))[:leftover]:
        base[index] += 1

    lines = [
        BudgetLine(category=name, percent=pct, amount=_from_cents(cents))
        for (name, pct), cents in zip(shares, base)
    ]
    per_guest = _from_cents(int((Decimal(total_cents) / guest_count).quantize(Decimal("1"), ROUND_HALF_UP)))
    return BudgetPlan(
        currency=currency,
        total=_from_cents(total_cents),
        per_guest=per_guest,
        lines=lines,
    )
