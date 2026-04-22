"""Browser-DOM tests for reading the catch-up page's birthday cards.

The unit suite mocks the guarded evaluate, so the program behind
``NetworkReader.get_catchup`` never executes there. These run it against
synthetic catch-up pages in headless chromium, with the navigation stubbed.
The markup carries the shapes the page has used — a list item, an article and
an SDUI-named container — and none of LinkedIn's classes, so it is a claim
about which signals are read, not about LinkedIn's layout.

Skipped automatically when chromium is not installed; run locally after
``uv run patchright install chromium --no-shell``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from patchright.async_api import async_playwright

from linkedin_mcp_server.linkedin.content import PageContentReader
from linkedin_mcp_server.linkedin.navigation import PageNavigator
from linkedin_mcp_server.linkedin.network import NetworkReader
from linkedin_mcp_server.linkedin.session import PageSession

#: CI uses ``--dist loadgroup``. Keep every test that launches Chromium on one
#: worker so browser startups cannot compete with the DOM cases' timers.
pytestmark = [
    pytest.mark.browser_dom,
    pytest.mark.xdist_group("browser_runtime"),
]

CATCHUP_URL = "https://www.linkedin.com/mynetwork/catch-up/birthdays/"


def card(
    username: str,
    sentence: str,
    *,
    tag: str = "li",
    name: str | None = None,
) -> str:
    """One catch-up card: a profile link and a sentence about the event."""
    label = f' aria-label="{name}"' if name else ""
    shown = name or username
    return (
        f"<{tag}>"
        f'<a href="https://www.linkedin.com/in/{username}/"{label}>{shown}</a>'
        f"<p>{sentence}</p>"
        f"</{tag}>"
    )


def page_of(*cards: str) -> str:
    return "<main><ul>" + "".join(cards) + "</ul></main>"


@pytest.fixture
async def dom_page():
    async def answer(route):
        await route.fulfill(status=200, content_type="text/html", body="<p>ok</p>")

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(
                channel="chromium", headless=True
            )
            context = await browser.new_context()
            page = await context.new_page()
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"chromium unavailable: {exc}")
        await context.route("**/*", answer)
        try:
            yield page
        finally:
            await browser.close()


async def read(page, html: str) -> list[dict]:
    """Serve ``html`` as the catch-up page and read it as the workflow does."""
    await page.goto(CATCHUP_URL)
    await page.set_content(html)
    session = PageSession(page)
    reader = NetworkReader(session, PageNavigator(session), PageContentReader(session))
    with patch.object(reader._navigator, "_navigate_to_page", new_callable=AsyncMock):
        result = await reader.get_catchup()
    return result["birthdays"]


async def test_a_birthday_card_is_read_with_its_person_and_sentence(dom_page):
    html = page_of(card("alice", "Celebrate Alice's birthday today", name="Alice"))

    [entry] = await read(dom_page, html)

    assert entry["profile_url"] == "https://www.linkedin.com/in/alice/"
    assert entry["name"] == "Alice"
    assert entry["birthday_text"] == "today"


@pytest.mark.parametrize("tag", ["li", "article"])
async def test_every_container_shape_the_page_has_used_is_read(dom_page, tag):
    html = page_of(card("bob", "Celebrate Bob's birthday on Apr 17", tag=tag))

    [entry] = await read(dom_page, html)

    assert entry["birthday"] == "0000-04-17"


async def test_an_sdui_named_container_is_read(dom_page):
    html = (
        "<main>"
        '<div data-view-name="birthday-card">'
        '<a href="https://www.linkedin.com/in/cleo/">Cleo</a>'
        "<p>Celebrate Cleo's birthday on 3 April</p>"
        "</div>"
        "</main>"
    )

    [entry] = await read(dom_page, html)

    assert entry["birthday"] == "0000-04-03"


async def test_a_card_about_anything_else_is_not_a_birthday(dom_page):
    """The page carries other event kinds, and a job change is not one."""
    html = page_of(
        card("dan", "Dan started a new position as Engineer"),
        card("eve", "Celebrate Eve's birthday today"),
    )

    entries = await read(dom_page, html)

    assert [e["profile_url"] for e in entries] == ["https://www.linkedin.com/in/eve/"]


async def test_one_person_is_answered_once(dom_page):
    """The page renders a card and its nested link; both name one person."""
    html = (
        "<main><ul>"
        "<li>"
        '<a href="https://www.linkedin.com/in/fay/">Fay</a>'
        "<p>Celebrate Fay's birthday today</p>"
        '<a href="https://www.linkedin.com/in/fay/?trk=card">Fay</a>'
        "</li>"
        "</ul></main>"
    )

    entries = await read(dom_page, html)

    assert len(entries) == 1
    assert entries[0]["profile_url"] == "https://www.linkedin.com/in/fay/"


async def test_the_connection_degree_is_not_part_of_the_name(dom_page):
    html = page_of(
        card("gus", "Celebrate Gus's birthday today", name="Gus Smith • 1st")
    )

    [entry] = await read(dom_page, html)

    assert entry["name"] == "Gus Smith"


async def test_a_page_with_no_cards_answers_nothing(dom_page):
    assert await read(dom_page, "<main><p>Nothing to catch up on.</p></main>") == []
