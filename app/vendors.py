"""Vendor and task checklists. Every checklist category matches a budget category."""

from __future__ import annotations

from .models import EventType, VendorTask

# (budget category, task, priority)
_CHECKLISTS: dict[EventType, tuple[tuple[str, str, str], ...]] = {
    EventType.WEDDING: (
        ("Venue", "Shortlist and visit 3 venues; confirm capacity, catering rules and a rain plan", "high"),
        ("Venue", "Sign the contract, pay the deposit and note cancellation terms", "high"),
        ("Catering", "Hold a tasting and confirm vegetarian, vegan and allergy options", "high"),
        ("Catering", "Confirm the final headcount deadline and number of service staff", "medium"),
        ("Attire & Beauty", "Order outfits and schedule fittings and alterations", "medium"),
        ("Attire & Beauty", "Book a makeup artist and hair stylist, with a trial", "medium"),
        ("Photography & Video", "Review portfolios and book a photographer and videographer", "high"),
        ("Photography & Video", "Share a must-capture shot list and a family group list", "low"),
        ("Decor & Flowers", "Finalise the decor concept, florist and lighting plan", "medium"),
        ("Decor & Flowers", "Agree setup and teardown access times with the venue", "medium"),
        ("Music & Entertainment", "Book a DJ or band; share must-play and do-not-play lists", "medium"),
        ("Music & Entertainment", "Confirm sound check time and power requirements", "low"),
        ("Invitations & Stationery", "Design, print and send invitations with an RSVP method", "medium"),
        ("Invitations & Stationery", "Track RSVPs and dietary needs in one shared list", "medium"),
        ("Travel & Stay", "Reserve a hotel room block and plan guest and family transport", "medium"),
        ("Rituals & Officiant", "Book the officiant or priest; confirm timings and ritual materials", "high"),
        ("Contingency", "Keep a reserve for last-minute costs and tips; name a day-of coordinator", "medium"),
    ),
    EventType.BIRTHDAY: (
        ("Venue", "Confirm the venue booking, capacity and decoration rules", "high"),
        ("Venue", "Prepare a rain or backup plan for outdoor spaces", "low"),
        ("Food & Drinks", "Book a caterer or plan the menu, noting allergies", "high"),
        ("Food & Drinks", "Order drinks, ice and serving supplies", "medium"),
        ("Cake", "Order the cake and confirm pickup or delivery time", "high"),
        ("Cake", "Share allergen details and the cake message with the baker", "medium"),
        ("Decor & Balloons", "Buy or hire decor, balloons and tableware", "medium"),
        ("Decor & Balloons", "Plan setup time and who will help", "low"),
        ("Entertainment", "Book an entertainer or DJ, or plan games and activities", "medium"),
        ("Entertainment", "Prepare a playlist and a backup activity", "low"),
        ("Photography", "Book a photographer or assign a friend to take photos", "medium"),
        ("Invitations & Favours", "Send invitations and track RSVPs", "high"),
        ("Invitations & Favours", "Order return gifts or party favours", "low"),
        ("Contingency", "Keep a reserve for last-minute purchases", "medium"),
    ),
    EventType.COMMUNITY: (
        ("Venue & Permits", "Confirm the venue booking and written permission to use it", "high"),
        ("Venue & Permits", "Apply for permits (noise, crowd, food stalls) and keep copies on site", "high"),
        ("Food & Refreshments", "Arrange food vendors who hold valid food-safety licences", "high"),
        ("Food & Refreshments", "Provide water stations and options for common dietary needs", "medium"),
        ("Stage & AV", "Book sound, lighting and stage; check power backup", "high"),
        ("Stage & AV", "Plan accessibility: ramps, seating, captions or sign interpretation", "medium"),
        ("Marketing & Printing", "Design and print posters, banners and signage", "medium"),
        ("Marketing & Printing", "Open registration or an RSVP form", "medium"),
        ("Volunteer Supplies", "Order volunteer badges, vests and contact lists or radios", "low"),
        ("Volunteer Supplies", "Prepare a briefing pack with shifts, roles and contacts", "medium"),
        ("Programme & Performers", "Confirm performers or speakers in writing, with timings", "high"),
        ("Programme & Performers", "Prepare the run of show with backup speakers", "medium"),
        ("Safety & Insurance", "Arrange event insurance and a staffed first-aid point", "high"),
        ("Safety & Insurance", "Mark emergency exits and share the emergency plan with volunteers", "high"),
        ("Contingency", "Hold a reserve for rain cover and unexpected costs", "medium"),
    ),
}


def vendor_checklist(event_type: EventType) -> list[VendorTask]:
    return [
        VendorTask(category=category, task=task, priority=priority)  # type: ignore[arg-type]
        for category, task, priority in _CHECKLISTS[event_type]
    ]
