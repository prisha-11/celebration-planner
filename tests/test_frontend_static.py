"""Static checks that keep the front end accessible and CSP-compatible."""

import re
from html.parser import HTMLParser
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def parsed():
    collector = Collector()
    collector.feed(HTML)
    return collector.tags


def test_page_has_language_title_and_viewport():
    tags = parsed()
    assert ("html", {"lang": "en"}) in tags
    assert any(t == "title" for t, _ in tags)
    assert any(t == "meta" and a.get("name") == "viewport" for t, a in tags)


def test_every_form_control_has_a_label():
    tags = parsed()
    label_targets = {a["for"] for t, a in tags if t == "label" and "for" in a}
    controls = [a["id"] for t, a in tags if t in {"input", "select", "textarea"} and a.get("id")]
    assert controls
    assert set(controls) <= label_targets


def test_skip_link_and_main_landmark_exist():
    tags = parsed()
    assert any(t == "a" and a.get("href") == "#main" for t, a in tags)
    assert any(t == "main" and a.get("id") == "main" for t, a in tags)


def test_tabs_are_wired_to_panels():
    tags = parsed()
    ids = {a.get("id") for _, a in tags}
    tabs = [a for t, a in tags if a.get("role") == "tab"]
    assert len(tabs) == 5
    for tab in tabs:
        assert tab["aria-controls"] in ids


def test_live_regions_exist_for_status_and_errors():
    assert 'role="status"' in HTML and 'role="alert"' in HTML and 'role="log"' in HTML


def test_no_inline_scripts_styles_or_handlers_so_csp_holds():
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", HTML)
    assert "<style" not in HTML
    assert not re.search(r"\sstyle=", HTML)
    assert not re.search(r"\son[a-z]+=", HTML)


def test_javascript_never_uses_unsafe_dom_sinks():
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
        assert sink not in JS, sink


def test_css_respects_reduced_motion_and_focus():
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css and ":focus-visible" in css
