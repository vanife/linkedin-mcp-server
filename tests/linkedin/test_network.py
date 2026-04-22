"""Tests for the catch-up page owner and the dating of its birthday cards."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from linkedin_mcp_server.linkedin.content import PageContentReader
from linkedin_mcp_server.linkedin.navigation import PageNavigator
from linkedin_mcp_server.linkedin.network import (
    CATCHUP_BIRTHDAYS_URL,
    NetworkReader,
    parse_birthday,
)
from linkedin_mcp_server.linkedin.session import PageSession


def _reader(page) -> NetworkReader:
    """Wire the catch-up owner the way the facade does."""
    session = PageSession(page)
    return NetworkReader(session, PageNavigator(session), PageContentReader(session))


class TestParseBirthday:
    """A card is dated against the read, not against the clock."""

    READ_AT = "2026-04-22T13:00:00Z"

    def test_today_is_the_day_the_page_was_read(self):
        assert parse_birthday("Celebrate John's birthday today", self.READ_AT) == (
            "0000-04-22",
            "today",
        )

    def test_yesterday_is_the_day_before_it(self):
        assert parse_birthday("Celebrate John's birthday yesterday", self.READ_AT) == (
            "0000-04-21",
            "yesterday",
        )

    def test_yesterday_crosses_a_month(self):
        """The subtraction is on the date, not on the day number."""
        assert parse_birthday("birthday yesterday", "2026-05-01T00:00:00Z") == (
            "0000-04-30",
            "yesterday",
        )

    def test_yesterday_crosses_a_year(self):
        assert parse_birthday("birthday yesterday", "2026-01-01T00:00:00Z") == (
            "0000-12-31",
            "yesterday",
        )

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Celebrate Kaspar's recent birthday on Apr 17", ("0000-04-17", "Apr 17")),
            ("birthday on 17 Apr", ("0000-04-17", "17 Apr")),
            ("birthday on April 3", ("0000-04-03", "April 3")),
        ],
    )
    def test_a_written_date_is_read_in_either_order(self, text, expected):
        assert parse_birthday(text, self.READ_AT) == expected

    def test_a_card_that_dates_nothing_says_so(self):
        assert parse_birthday("Wishing you a happy birthday!", self.READ_AT) == (
            None,
            "",
        )

    def test_today_wins_over_a_date_in_the_greeting(self):
        """A card can carry both; the relative word is the birthday."""
        assert parse_birthday("Apr 22 birthday today", self.READ_AT) == (
            "0000-04-22",
            "today",
        )

    def test_a_month_that_is_not_one_dates_nothing(self):
        assert parse_birthday("birthday on Smarch 4", self.READ_AT) == (None, "")


class TestGetCatchup:
    @staticmethod
    def _cards(reader, cards):
        """Answer the card read with *cards*.

        Patched on the class: `PageSession` is a frozen dataclass, so the
        instance the reader holds will not take an attribute.
        """
        del reader
        return patch.object(
            PageSession,
            "run_on_linkedin",
            new_callable=AsyncMock,
            return_value=cards,
        )

    async def test_each_card_becomes_a_dated_birthday(self, mock_page):
        reader = _reader(mock_page)
        cards = [
            {
                "path": "/in/alice/",
                "name": "Alice",
                "text": "Celebrate Alice's birthday today",
            }
        ]
        with self._cards(reader, cards):
            result = await reader.get_catchup()

        assert result["url"] == CATCHUP_BIRTHDAYS_URL
        [entry] = result["birthdays"]
        assert entry["name"] == "Alice"
        assert entry["profile_url"] == "https://www.linkedin.com/in/alice/"
        assert entry["birthday_text"] == "today"
        assert entry["original_text"] == "Celebrate Alice's birthday today"
        # The label is relative, so the moment it is relative to comes too.
        assert entry["birthday"] == f"0000-{result['retrieved_at'][5:10]}"

    async def test_a_card_without_a_profile_link_carries_no_url(self, mock_page):
        reader = _reader(mock_page)
        cards = [{"path": "", "name": "Someone", "text": "birthday on Apr 17"}]
        with self._cards(reader, cards):
            result = await reader.get_catchup()

        assert result["birthdays"][0]["profile_url"] is None
        assert result["birthdays"][0]["birthday"] == "0000-04-17"

    async def test_a_page_with_no_cards_answers_an_empty_list(self, mock_page):
        reader = _reader(mock_page)
        with self._cards(reader, []):
            result = await reader.get_catchup()

        assert result["birthdays"] == []
        assert result["retrieved_at"].endswith("Z")

    async def test_a_page_that_answered_nothing_is_not_an_error(self, mock_page):
        """A guarded evaluate answers None off LinkedIn; that is no cards."""
        reader = _reader(mock_page)
        with self._cards(reader, None):
            result = await reader.get_catchup()

        assert result["birthdays"] == []

    async def test_an_unsupported_filter_is_refused_before_navigating(self, mock_page):
        reader = _reader(mock_page)
        with patch.object(
            reader._navigator, "_navigate_to_page", new_callable=AsyncMock
        ) as navigate:
            with pytest.raises(ValueError, match="notifications"):
                await reader.get_catchup(filter_type="notifications")

        navigate.assert_not_awaited()

    async def test_the_birthday_filter_is_accepted(self, mock_page):
        reader = _reader(mock_page)
        with self._cards(reader, []):
            result = await reader.get_catchup(filter_type="birthday")

        assert result["url"] == CATCHUP_BIRTHDAYS_URL
