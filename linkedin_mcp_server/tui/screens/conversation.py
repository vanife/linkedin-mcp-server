"""Conversation thread viewer screen."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

logger = logging.getLogger(__name__)


class ConversationScreen(Screen[None]):
    """Display a single conversation thread."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
    ]

    CSS = """
    #conv-status {
        height: 1;
        content-align: center middle;
        background: $boost;
    }
    #conv-content {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    """

    _thread_id: str | None
    _name: str

    def __init__(
        self,
        thread_id: str | None = None,
        name: str = "",
    ) -> None:
        super().__init__()
        self._thread_id = thread_id
        self._name = name

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(
            f"Loading conversation with {self._name}...",
            id="conv-status",
        )
        yield Static(id="conv-content")
        yield Footer()

    def on_mount(self) -> None:
        thread_id: str | None = self._thread_id
        name: str = self._name
        screen = self

        async def _load() -> None:
            from linkedin_mcp_server.drivers.browser import (
                close_browser,
                get_or_create_browser,
            )
            from linkedin_mcp_server.scraping import LinkedInExtractor

            browser = None
            try:
                browser = await get_or_create_browser()
                extractor = LinkedInExtractor(browser.page)
                result = await extractor.get_conversation(thread_id=thread_id)

                sections = result.get("sections", {})
                content = sections.get("conversation", "")
                _set_conv_content(screen, content or "(No messages)", None, name)
            except Exception as e:
                logger.error("Failed to load conversation: %s", e, exc_info=True)
                _set_conv_content(screen, "", str(e), name)
            finally:
                if browser is not None:
                    await close_browser()

        self.run_worker(_load(), name="load-conv")

    def action_back(self) -> None:
        self.app.pop_screen()


def _set_conv_content(
    screen: ConversationScreen, content: str, error: str | None, name: str
) -> None:
    status = screen.query_one("#conv-status", Label)
    content_widget = screen.query_one("#conv-content", Static)
    if error:
        status.update(f"Error: {error}")
    else:
        status.update(f"Conversation with {name}")
    content_widget.update(content)
