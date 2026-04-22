"""The catch-up page: the network events LinkedIn collects for this account.

Only birthdays are read so far. The page groups each event as a card carrying
the person's profile link and a sentence about the event, and the sentence is
the only thing that dates a birthday — so unlike the rest of this package,
which classifies on URLs and attribute presence, this one has to read words.
That is confined to `CatchupTextTable` below, and the limitation it brings is
documented there.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from typing import Any

import logging
import re

from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from linkedin_mcp_server.linkedin.content import PageContentReader
from linkedin_mcp_server.linkedin.navigation import PageNavigator
from linkedin_mcp_server.linkedin.session import PageSession

logger = logging.getLogger(__name__)

CATCHUP_BIRTHDAYS_URL = "https://www.linkedin.com/mynetwork/catch-up/birthdays/"

# The event kinds this reads. A value outside it is refused rather than
# silently answered with birthdays, which is what a caller asking for
# something else would otherwise get.
SUPPORTED_FILTERS = frozenset({"birthday"})


@dataclass(frozen=True)
class CatchupTextTable:
    """Visible-text policy for dating a birthday card.

    Every entry here is a word on the page, so a catch-up page rendered in
    another language dates nothing: `parse_birthday` answers `(None, "")` for
    each card and the cards themselves still come back. This is the one
    reading in the package that cannot be done on URLs or attribute presence
    — the card's date lives in its sentence and nowhere else.
    """

    # A card for a birthday happening on the day the page was read, and on the
    # day before it. Both are relative, so they are resolved against the
    # capture's own timestamp rather than against the clock.
    today: str
    yesterday: str
    # Month names as the page abbreviates or spells them, keyed by the first
    # three characters, which is how LinkedIn abbreviates them.
    months: dict[str, int]
    # "Apr 12", "April 12", "12 Apr" and "12 April" alike. A card carries one
    # of these only when the birthday is neither today nor yesterday.
    date_pattern: re.Pattern[str]
    # A card has to say this much to be a birthday card at all.
    event_words: tuple[str, ...]


_CATCHUP_TEXT: dict[str, CatchupTextTable] = {
    "en-US": CatchupTextTable(
        today="today",
        yesterday="yesterday",
        months={
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        },
        date_pattern=re.compile(
            r"\b(?:(?P<mname>[A-Za-z]{3,9})\s+(?P<d1>\d{1,2})"
            r"|(?P<d2>\d{1,2})\s+(?P<mname2>[A-Za-z]{3,9}))\b"
        ),
        event_words=("birthday", "born"),
    ),
}

# Same locale contract as the job tables: the browser context is forced to
# en-US, so only this entry is ever used.
CATCHUP_EN_US = _CATCHUP_TEXT["en-US"]


def parse_birthday(
    text: str, retrieved_at: str, table: CatchupTextTable = CATCHUP_EN_US
) -> tuple[str | None, str]:
    """The date a birthday card names, and the label it used to name it.

    Answers `("0000-MM-DD", label)`, the year being absent from the card as
    well as from LinkedIn. `(None, "")` covers a card that dates nothing,
    which a page in another language makes of every card.

    "today" and "yesterday" are resolved against `retrieved_at` rather than
    the clock, so a read that straddles midnight dates its cards by the moment
    the page was read and a replay of the same text answers the same way.
    Both are checked before the written date, because a card saying "today"
    can also carry one in its greeting.
    """
    lower = text.lower()
    read_at = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))

    if table.today in lower:
        return f"0000-{read_at.month:02d}-{read_at.day:02d}", table.today
    if table.yesterday in lower:
        before = read_at - timedelta(days=1)
        return f"0000-{before.month:02d}-{before.day:02d}", table.yesterday

    match = table.date_pattern.search(text)
    if match:
        name = (match.group("mname") or match.group("mname2") or "").lower()[:3]
        day = match.group("d1") or match.group("d2") or ""
        month = table.months.get(name)
        if month and day:
            return f"0000-{month:02d}-{int(day):02d}", match.group(0)

    return None, ""


# Each card is a list item (an `li` or, on the SDUI page, a `role="listitem"`
# div), an article or an SDUI-named container holding the person's profile
# link. Generic on purpose: the catch-up page exposes no stable per-card
# container, and these cover the shapes it has used. The profile link is what
# identifies a card, and `/in/<username>` is read off the href rather than off
# any text. On the SDUI page that link is the bare avatar, so when it carries
# no label the name is the card's first rendered line.
_CATCHUP_CARDS_JS = """(opts) => {
    const normalize = (t) => (t || '').replace(/\\s+/g, ' ').trim();

    const personPath = (href) => {
        if (!href) return null;
        const at = href.indexOf('/in/');
        if (at === -1) return null;
        const rest = href.slice(at + 4);
        const end = rest.search(/[/?#]/);
        const username = end === -1 ? rest : rest.slice(0, end);
        return username ? '/in/' + username + '/' : null;
    };

    const found = Array.from(
        document.querySelectorAll(
            'main li, main [role="listitem"], main article, main [data-view-name]'
        )
    );
    const cards = found.length
        ? found
        : Array.from(document.querySelectorAll('main > * > *'));

    const out = [];
    const seen = new Set();
    for (const card of cards) {
        const link = card.querySelector('a[href*="/in/"]');
        if (!link) continue;
        const path = personPath(link.getAttribute('href'));
        if (!path || seen.has(path)) continue;

        const text = normalize(card.innerText || card.textContent);
        if (!text) continue;
        const lower = text.toLowerCase();
        if (!opts.eventWords.some((word) => lower.includes(word))) continue;

        seen.add(path);
        const firstLine = (card.innerText || '')
            .split('\\n')
            .map(normalize)
            .find(Boolean);
        const name = (
            link.getAttribute('aria-label') ||
            normalize(link.innerText || link.textContent) ||
            firstLine ||
            ''
        ).replace(/[\\u2022\\u00b7].*$/, '').trim();
        out.push({ path, name, text });
    }
    return out;
}"""

# The page has rendered something of its own rather than a shell. A count and
# not a selector, for the reason the card query above gives.
_CATCHUP_READY_JS = (
    "() => {\n"
    "    const main = document.querySelector('main');\n"
    "    return Boolean(main) && main.innerText.length > 100;\n"
    "}"
)

_MAIN_TIMEOUT = 8.0
_CONTENT_TIMEOUT = 10.0


class NetworkReader:
    """Read the catch-up page's network events."""

    def __init__(
        self,
        session: PageSession,
        navigator: PageNavigator,
        content: PageContentReader,
        text: CatchupTextTable = CATCHUP_EN_US,
    ):
        self._session = session
        self._navigator = navigator
        self._content = content
        self._text = text

    async def get_catchup(self, filter_type: str | None = None) -> dict[str, Any]:
        """Read the catch-up page's events.

        Args:
            filter_type: The event kind to read. Only "birthday" is supported;
                None reads the same page, which is what the birthdays route
                serves.

        Returns:
            {url, retrieved_at, birthdays: [{name, profile_url, birthday,
            birthday_text, original_text}]}. `birthday` is "0000-MM-DD" or
            null, the year being absent from the page.
        """
        if filter_type is not None and filter_type not in SUPPORTED_FILTERS:
            raise ValueError(
                f"Unsupported filter_type {filter_type!r}. "
                f"Supported values: {sorted(SUPPORTED_FILTERS)}"
            )

        url = CATCHUP_BIRTHDAYS_URL
        await self._navigator._navigate_to_page(url)
        await self._session.check_rate_limit()

        page = self._session.page
        try:
            await page.wait_for_selector("main", timeout=_MAIN_TIMEOUT * 1000)
        except PlaywrightTimeoutError:
            logger.debug("No main element on the catch-up page")

        await self._session.dismiss_modal()

        try:
            await page.wait_for_function(
                _CATCHUP_READY_JS, timeout=_CONTENT_TIMEOUT * 1000
            )
        except PlaywrightTimeoutError:
            logger.debug("Catch-up cards did not render on %s", url)

        # Stamped before the cards are read and carried into the answer: the
        # relative labels on them mean nothing without the moment they were
        # read, and a caller storing the result needs the same moment to date
        # them again.
        retrieved_at = (
            datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

        raw: list[dict[str, Any]] = (
            await self._session.run_on_linkedin(
                _CATCHUP_CARDS_JS, {"eventWords": list(self._text.event_words)}
            )
            or []
        )

        birthdays = []
        for card in raw:
            path = card.get("path") or ""
            original_text = card.get("text") or ""
            birthday, label = parse_birthday(original_text, retrieved_at, self._text)
            birthdays.append(
                {
                    "name": card.get("name") or "",
                    "profile_url": f"https://www.linkedin.com{path}" if path else None,
                    "birthday": birthday,
                    "birthday_text": label,
                    "original_text": original_text,
                }
            )

        return {
            "url": url,
            "retrieved_at": retrieved_at,
            "birthdays": birthdays,
        }
