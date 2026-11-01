"""Offline idea generator: deterministic, keyword-driven suggestions used when no AI key is set."""

from __future__ import annotations

import re
from typing import NamedTuple

from .models import EventType, Idea, PlanRequest

IDEA_COUNT = 6
_THEME_SLOTS = 3


class Theme(NamedTuple):
    title: str
    keywords: frozenset[str]
    description: str


def _kw(*words: str) -> frozenset[str]:
    return frozenset(words)


_THEMES: dict[EventType, tuple[Theme, ...]] = {
    EventType.WEDDING: (
        Theme("Garden Party Romance", _kw("garden", "outdoor", "nature", "floral", "spring", "green", "flowers"),
              "Pastel florals, lawn games and a golden-hour ceremony outdoors, with a covered backup for weather."),
        Theme("Royal Heritage", _kw("royal", "traditional", "heritage", "palace", "classic", "grand", "indian"),
              "Rich jewel tones, brass lanterns, live folk musicians and a ceremonial grand entrance."),
        Theme("Intimate Candlelit Dinner", _kw("intimate", "small", "cosy", "cozy", "candle", "dinner", "minimal"),
              "Long shared tables, warm candlelight and a chef's tasting menu that lets guests really talk."),
        Theme("Beach and Sunset Celebration", _kw("beach", "sunset", "sea", "coastal", "destination", "ocean"),
              "Barefoot ceremony at sunset, seafood stations and lantern-lit pathways."),
        Theme("Boho Rustic", _kw("boho", "rustic", "barn", "vintage", "earthy", "handmade"),
              "Wooden tables, dried flowers, macrame details and a relaxed acoustic playlist."),
    ),
    EventType.BIRTHDAY: (
        Theme("Retro Game Night", _kw("games", "gaming", "retro", "arcade", "board", "fun", "teen"),
              "Arcade corners, board-game tables and a high-score leaderboard with silly prizes."),
        Theme("Garden Picnic Brunch", _kw("picnic", "garden", "brunch", "outdoor", "daytime", "park"),
              "Blankets, grazing boards, lemonade stations and lawn games in the afternoon sun."),
        Theme("Movie Under the Stars", _kw("movie", "film", "cinema", "stars", "night", "popcorn"),
              "A projector, cosy seating, a popcorn bar and themed snacks for a favourite film."),
        Theme("Colour Splash Party", _kw("colour", "color", "kids", "children", "paint", "rainbow", "art"),
              "A bright palette, a craft table and a mural everyone adds to, which becomes the keepsake."),
        Theme("Milestone Memory Lane", _kw("milestone", "surprise", "memories", "photos", "family", "retirement"),
              "A photo timeline, short guest toasts and a recorded video message wall."),
    ),
    EventType.COMMUNITY: (
        Theme("Neighbourhood Food Festival", _kw("food", "festival", "market", "stalls", "street", "cuisine"),
              "Local home cooks and small vendors sharing stalls, with a communal tasting trail."),
        Theme("Clean-up and Celebrate", _kw("clean", "environment", "green", "eco", "sustainability", "tree", "planting"),
              "A morning clean-up or tree planting followed by a shared lunch and recognition for volunteers."),
        Theme("Cultural Evening", _kw("culture", "cultural", "music", "dance", "heritage", "talent", "performance"),
              "Local performers, a talent showcase and an open mic for residents."),
        Theme("Family Fun Day", _kw("family", "kids", "children", "games", "sports", "fair", "carnival"),
              "Relay races, a face-painting corner, a book swap and a quiet space for little ones."),
        Theme("Skills and Learning Fair", _kw("workshop", "learning", "skills", "education", "career", "students"),
              "Hands-on stalls where neighbours teach first aid, repair, coding or crafts for an hour each."),
    ),
}

_EXTRAS: dict[EventType, tuple[Idea, ...]] = {
    EventType.WEDDING: (
        Idea(title="Guest experience touches",
             description="A welcome kit with a local snack, a map and the schedule; a mocktail bar; and a quiet corner for elders."),
        Idea(title="Memory keepsakes",
             description="A guest-book alternative such as a voice-message phone or a signed print, plus an album of candid photos."),
        Idea(title="Low-waste planning",
             description="Reusable decor, seasonal local flowers, food-donation arrangements for leftovers and digital invitations."),
    ),
    EventType.BIRTHDAY: (
        Idea(title="Activity stations",
             description="Set up two or three low-effort stations such as a DIY snack bar, a photo corner and a game table so guests mix naturally."),
        Idea(title="Thoughtful favours",
             description="Small useful gifts such as seed packets, a handwritten note or a mini treat box instead of plastic items."),
        Idea(title="Budget stretch",
             description="Host at home or a park, bake part of the menu, and put the savings into one standout moment like a great cake."),
    ),
    EventType.COMMUNITY: (
        Idea(title="Inclusive access",
             description="Step-free routes, seating with shade, quiet hours, clear signage and multilingual volunteers or flyers."),
        Idea(title="Sponsor and partner plan",
             description="Offer small businesses stall space or a thank-you banner in exchange for cash, food or supplies."),
        Idea(title="Capture the impact",
             description="Collect sign-ups, a short feedback form and photos so you can report results and plan next year."),
    ),
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def offline_ideas(req: PlanRequest) -> list[Idea]:
    """Pick the themes that best match the user's preferences, then add practical extras."""
    themes = _THEMES[req.event_type]
    wanted = _tokens(req.preferences)
    ranked = sorted(
        range(len(themes)),
        key=lambda i: (-len(wanted & themes[i].keywords), i),
    )
    ideas = [Idea(title=themes[i].title, description=themes[i].description) for i in ranked[:_THEME_SLOTS]]
    ideas.extend(_EXTRAS[req.event_type])

    if req.city and ideas:
        first = ideas[0]
        ideas[0] = Idea(
            title=first.title,
            description=f"{first.description} Look for venues and suppliers in {req.city} that fit this style.",
        )
    return ideas[:IDEA_COUNT]
