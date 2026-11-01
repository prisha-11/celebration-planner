from datetime import date, timedelta

import pytest

from conftest import payload


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["ai_enabled"] is False


def test_plan_success_shape(client):
    response = client.post("/api/plan", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"summary", "budget", "timeline", "vendors", "ideas", "notes"}
    assert body["summary"]["event_name"] == "Asha and Rohan"
    assert body["budget"]["total"] == 1_500_000
    assert sum(line["amount"] for line in body["budget"]["lines"]) == pytest.approx(1_500_000)


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_plan_works_for_every_event_type(client, event_type):
    assert client.post("/api/plan", json=payload(event_type=event_type)).status_code == 200


@pytest.mark.parametrize(
    "field, value",
    [
        ("event_type", "funeral"),
        ("event_name", ""),
        ("event_name", "   "),
        ("event_name", "n" * 101),
        ("event_date", "not-a-date"),
        ("guest_count", 0),
        ("guest_count", 5001),
        ("guest_count", "many"),
        ("total_budget", 0),
        ("total_budget", -50),
        ("total_budget", 1e12),
        ("currency", "XYZ"),
        ("city", "c" * 81),
        ("preferences", "p" * 501),
    ],
)
def test_invalid_fields_are_rejected_with_field_location(client, field, value):
    response = client.post("/api/plan", json=payload(**{field: value}))
    assert response.status_code == 422
    locations = [item["loc"][-1] for item in response.json()["detail"]]
    assert field in locations


def test_unknown_fields_are_rejected(client):
    response = client.post("/api/plan", json=payload(is_admin=True))
    assert response.status_code == 422


def test_missing_required_fields(client):
    response = client.post("/api/plan", json={"event_type": "wedding"})
    assert response.status_code == 422
    assert len(response.json()["detail"]) >= 4


def test_past_date_gives_friendly_field_error(client):
    past = (date.today() - timedelta(days=1)).isoformat()
    response = client.post("/api/plan", json=payload(event_date=past))
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["event_date"]


def test_malformed_and_non_object_json(client):
    assert client.post("/api/plan", body=b"{oops").status_code == 400
    assert client.post("/api/plan", json=["a", "list"]).status_code == 422


def test_html_in_text_fields_is_returned_as_inert_data(client):
    response = client.post("/api/plan", json=payload(event_name="<script>alert(1)</script>"))
    assert response.status_code == 200
    # The API returns it verbatim as JSON; the front end only ever renders it as text.
    assert response.json()["summary"]["event_name"] == "<script>alert(1)</script>"
    assert response.headers["content-type"].startswith("application/json")


def test_control_characters_are_stripped(client):
    response = client.post("/api/plan", json=payload(event_name="Party\x00\x07 time"))
    assert response.json()["summary"]["event_name"] == "Party time"


def test_ideas_endpoint_offline(client):
    body = client.post("/api/ideas", json=payload(preferences="beach sunset")).json()
    assert body["source"] == "offline" and len(body["ideas"]) == 6
    assert body["ideas"][0]["title"] == "Beach and Sunset Celebration"


def test_chat_endpoint_offline(client):
    body = client.post("/api/chat", json={"plan": payload(), "question": "What is my budget per guest?"}).json()
    assert body["source"] == "offline" and "per guest" in body["answer"]


def test_chat_validates_question_and_plan(client):
    assert client.post("/api/chat", json={"plan": payload(), "question": ""}).status_code == 422
    assert client.post("/api/chat", json={"plan": payload(), "question": "q" * 501}).status_code == 422
    assert client.post("/api/chat", json={"plan": payload(guest_count=-1), "question": "hi"}).status_code == 422


def test_wrong_method_is_not_allowed(client):
    response = client.get("/api/plan")
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


def test_unknown_api_path_is_404(client):
    assert client.get("/api/does-not-exist").status_code == 404


def test_front_end_is_served(client):
    index = client.get("/")
    assert index.status_code == 200 and "Celebration Planner" in index.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/styles.css").status_code == 200


def test_path_traversal_is_blocked(client):
    response = client.get("/../app/config.py")
    assert response.status_code in (400, 404)
    assert "ANTHROPIC_API_KEY" not in response.text
