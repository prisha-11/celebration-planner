# Celebration Planner

A GenAI-assisted planning assistant for **weddings, birthdays and community events**. Enter a few details and get:

- **Budget**: a category split that always adds up exactly to your total, plus cost per guest
- **Timeline**: milestones counted back from your date. If time is short, overdue steps are pulled to today and flagged
- **Vendor checklist**: prioritised tasks per category, with progress that is remembered in your browser
- **Personalised ideas**: built-in themes matched to your wishes, or AI-generated ideas using Claude
- **Ask the planner**: questions answered from your own plan (AI answers when a key is set)

## Do I need an API key?

**No.** The app runs completely without one. Everything works offline with the built-in planner.

An **Anthropic API key is optional** and only adds two things: AI-written, personalised ideas and open-ended chat answers. Get a key at <https://console.anthropic.com>, then put it in `.env` (see below). If the key is missing, invalid or the API is down, the app silently falls back to the built-in logic.

## Quick start

Requires Python 3.10 or newer.

```bash
cd celebration-planner
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m app                      # then open http://127.0.0.1:8000
```

Optional AI features:

```bash
cp .env.example .env               # then edit .env and set ANTHROPIC_API_KEY=...
```

Run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

## Project layout

```
app/
  main.py       HTTP layer: routes, validation errors, rate limiting, static files
  models.py     Pydantic request/response models (the contract)
  planner.py    Builds a full plan from a validated request
  budget.py     Budget allocation (integer-cent largest-remainder method)
  timeline.py   Milestones and short-runway compression
  vendors.py    Vendor and task checklists
  ideas.py      Offline, keyword-driven idea generator
  ai.py         Claude integration, prompt hardening, offline fallbacks
  security.py   Sanitising, rate limiter, body-size limit, security headers
  config.py     Settings from environment / .env
static/         index.html, styles.css, app.js (no build step)
tests/          pytest suite (unit, API, security, static accessibility checks)
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Status and whether AI is enabled |
| POST | `/api/plan` | Full plan: budget, timeline, vendors, ideas |
| POST | `/api/ideas` | Personalised ideas (AI if available, otherwise built-in) |
| POST | `/api/chat` | `{ "plan": {...}, "question": "..." }` returns an answer |

Request body for `/api/plan` and `/api/ideas`:

```json
{
  "event_type": "wedding",
  "event_name": "Asha and Rohan",
  "event_date": "2027-02-14",
  "guest_count": 150,
  "total_budget": 1500000,
  "currency": "INR",
  "city": "Pune",
  "preferences": "outdoor, vegetarian menu"
}
```

The server is stateless: nothing about your event is stored on the server.

## How the quality goals are met

**Code quality.** Small single-purpose modules; plan logic is pure functions with no I/O; typed models define the contract; the HTTP layer is thin. Percentages, milestones and checklists are plain data tables, so changing them needs no logic changes.

**Security.**
- Strict validation (types, ranges, lengths, no unknown fields) and sanitising of control and bidi characters.
- Prompt-injection hardening: user text is escaped and wrapped in delimiter tags, and the system prompt marks it as data, never instructions.
- Strict Content-Security-Policy (no inline scripts or styles), `nosniff`, `X-Frame-Options: DENY`, `no-referrer`, and `no-store` on API responses.
- The front end only inserts text as DOM text nodes, never as HTML strings (checked by a test).
- Per-client rate limits (stricter for AI endpoints), a request-body size limit that also covers chunked uploads, and generic error messages with no stack traces.
- The API key lives only in the environment or `.env` (git-ignored), is never sent to the browser and is never logged.
- Path traversal on static files is blocked.

**Efficiency.** Plan generation is instant and local. AI is called only when asked (the Ideas button or a chat question), with capped output tokens, a timeout, and one retry. The rate limiter's memory is bounded. There is no database and no front-end build.

**Testing.** `pytest` covers budget arithmetic (including awkward totals), timeline compression, checklist/budget consistency, idea matching, validation, rate limiting, body limits, headers, prompt-injection escaping, AI success and failure paths using a fake client, and static accessibility and CSP checks. The test suite needs no network and no API key.

**Accessibility.** Skip link and landmarks; every control has a visible label; errors appear inline and in a summary that receives focus, and are not conveyed by colour alone; the tabs follow the ARIA tabs pattern with arrow, Home and End keys; status and chat regions are live regions; 44px minimum touch targets; visible focus rings; light and dark themes with AA contrast; reduced-motion support; a print-friendly layout.

**Problem-statement alignment.** Weddings, birthdays and community events each have their own budget split, timeline, vendor checklist and idea themes, with GenAI personalisation on top.

## Deployment notes

- Behind a reverse proxy, run uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy ip>` so rate limiting sees real client IPs.
- The rate limiter is in-memory and per process. With several workers, use a shared store such as Redis.
- Serve over HTTPS in production (the CSP already assumes same-origin only).

## Limitations

- Budget percentages and vendor tasks are sensible defaults, not quotes. Real prices vary widely by city and season.
- The planner does not book vendors or contact anyone.
