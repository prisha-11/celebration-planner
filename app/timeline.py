"""Timeline generation: milestones counted back from the event date, compressed if time is short."""

from __future__ import annotations

from datetime import date, timedelta

from .models import EventType, Milestone

# (days before the event, title, detail). Negative values fall after the event.
_TEMPLATES: dict[EventType, tuple[tuple[int, str, str], ...]] = {
    EventType.WEDDING: (
        (365, "Set budget and draft guest list", "Agree who is contributing, a firm total and a first guest list."),
        (330, "Book the venue and date", "Venue availability drives everything else; confirm capacity and rain plan."),
        (300, "Book photographer, planner and officiant", "Top professionals book out a year ahead in peak season."),
        (240, "Book caterer and hold a tasting", "Confirm menu style, dietary options and per-plate pricing."),
        (180, "Send save-the-dates", "Especially important if guests are travelling."),
        (150, "Order attire and book beauty team", "Allow time for fittings and alterations."),
        (120, "Book decor, florist and music", "Share your theme so vendors can quote accurately."),
        (90, "Send formal invitations", "Include the RSVP method, deadline and dress code."),
        (60, "Finalise menu, decor and run of show", "Lock the details with every vendor in writing."),
        (30, "Confirm final headcount and seating draft", "Caterers and venues need final numbers now."),
        (14, "Reconfirm all vendors and pay balances", "Share the day-of timeline and contact numbers."),
        (7, "Final fittings and welcome arrangements", "Prepare guest welcome kits and travel logistics."),
        (1, "Rehearsal and prepare payments and tips", "Walk through the ceremony; pack the emergency kit."),
        (0, "Wedding day", "Delegate a coordinator so you can enjoy it."),
        (-7, "Send thank-you notes and settle final invoices", "Collect photos and leave vendor reviews."),
    ),
    EventType.BIRTHDAY: (
        (60, "Set budget, guest list and theme", "Decide the guest count first; it drives venue and food costs."),
        (45, "Book the venue or plan the home setup", "Check capacity, timing and decoration rules."),
        (40, "Book entertainment and photographer", "Entertainers and caterers fill up on weekends."),
        (30, "Send invitations", "Ask for RSVPs and any dietary needs or allergies."),
        (21, "Order the cake and confirm the menu", "Share allergy details and the writing on the cake."),
        (14, "Buy decor, favours and supplies", "Order online early to allow for delivery delays."),
        (7, "Confirm RSVPs and vendors", "Chase late replies and confirm delivery times."),
        (3, "Prepare playlist and games; buy perishables", "Plan a backup for weather or no-shows."),
        (1, "Set up decor and pack the supplies", "Do as much as possible the day before."),
        (0, "Birthday celebration", "Assign a helper for photos and cake cutting."),
        (-3, "Send thank-you messages", "Share photos with guests."),
    ),
    EventType.COMMUNITY: (
        (120, "Define goals and form the organising committee", "Agree purpose, audience, roles and decision-makers."),
        (105, "Secure the venue and apply for permits", "Permits and noise or crowd approvals can take weeks."),
        (90, "Finalise budget and approach sponsors", "Prepare a short sponsor pack with benefits and reach."),
        (75, "Recruit and schedule volunteers", "Define shifts and a lead for each area."),
        (60, "Book vendors, AV and performers", "Get written quotes and confirm power and space needs."),
        (45, "Launch marketing and registration", "Use posters, WhatsApp groups, social media and local partners."),
        (30, "Confirm speakers and the programme", "Share the schedule, stage and tech requirements."),
        (14, "Finalise safety, first-aid and insurance plan", "Mark exits, first-aid point and emergency contacts."),
        (7, "Brief volunteers and confirm headcount", "Hold a walkthrough, hand out roles and radios or contact lists."),
        (2, "Set up and do an on-site walkthrough", "Test sound, lighting, signage and accessibility routes."),
        (0, "Event day", "Keep a runner and an incident contact available."),
        (-7, "Hold a debrief and send thanks", "Record what worked, publish results and thank sponsors."),
    ),
}


def build_timeline(
    event_type: EventType, event_date: date, today: date
) -> tuple[list[Milestone], int]:
    """Return (milestones sorted by due date, number of milestones compressed to today)."""
    milestones: list[tuple[date, int, Milestone]] = []
    compressed = 0
    for order, (days_before, title, detail) in enumerate(_TEMPLATES[event_type]):
        due = event_date - timedelta(days=days_before)
        urgent = due < today
        if urgent:
            due = today
            compressed += 1
        milestones.append(
            (
                due,
                order,
                Milestone(
                    title=title,
                    detail=detail,
                    due_date=due,
                    days_before=days_before,
                    urgent=urgent,
                ),
            )
        )
    milestones.sort(key=lambda item: (item[0], item[1]))
    return [m for _, _, m in milestones], compressed
