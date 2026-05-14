"""Inbox screen showing list of recent LinkedIn conversations."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from linkedin_mcp_server.drivers.browser import close_browser, get_or_create_browser
from linkedin_mcp_server.scraping import LinkedInExtractor

from linkedin_mcp_server.tui.screens.conversation import ConversationScreen

logger = logging.getLogger(__name__)


@dataclass
class ConversationInfo:
    name: str
    thread_id: str


class InboxScreen(Screen[None]):
    """Display inbox conversations and allow navigation into threads."""

    BINDINGS = [
        Binding("enter", "open", "Open", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("up", "up", "", show=False),
        Binding("down", "down", "", show=False),
        Binding("k", "up", "", show=False),
        Binding("j", "down", "", show=False),
    ]

    CSS = """
    #inbox-status {
        height: 1;
        content-align: center middle;
        background: $boost;
    }
    #inbox-list {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._conversations: list[ConversationInfo] = []
        self._selected_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Loading inbox...", id="inbox-status")
        yield Static(id="inbox-list")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_inbox, name="load-inbox")

    async def _load_inbox(self) -> None:
        browser = None
        try:
            browser = await get_or_create_browser()
            extractor = LinkedInExtractor(browser.page)
            result = await extractor.get_inbox(limit=30)

            convs: list[ConversationInfo] = []
            refs = result.get("references", {}).get("inbox", [])
            for ref in refs:
                if ref.get("kind") == "conversation":
                    thread_url = ref.get("url", "")
                    thread_id = ""
                    if "/thread/" in thread_url:
                        thread_id = thread_url.split("/thread/")[1].rstrip("/")
                    convs.append(
                        ConversationInfo(
                            name=ref.get("text", "Unknown"),
                            thread_id=thread_id,
                        )
                    )

            sections = result.get("sections", {})
            inbox_text = sections.get("inbox", "")
            if not convs and inbox_text:
                lines = inbox_text.strip().splitlines()
                for line in lines[:30]:
                    name = line.strip().split()[0] if line.strip() else "Unknown"
                    convs.append(
                        ConversationInfo(
                            name=name,
                            thread_id="",
                        )
                    )

            self.app.call_from_thread(
                self._set_conversations, convs, None
            )
        except Exception as e:
            logger.error("Failed to load inbox: %s", e, exc_info=True)
            self.app.call_from_thread(
                self._set_conversations, [], str(e)
            )
        finally:
            if browser is not None:
                await close_browser()

    def _set_conversations(
        self, convs: list[ConversationInfo], error: str | None
    ) -> None:
        self._conversations = convs
        self._selected_index = 0

        status = self.query_one("#inbox-status", Label)
        list_widget = self.query_one("#inbox-list", Static)

        if error:
            status.update(f"Error: {error}")
            return

        if not convs:
            status.update("Inbox is empty")
            list_widget.update("")
            return

        status.update(f"Inbox ({len(convs)} conversations)")
        self._render_list()

    def _render_list(self) -> None:
        lines: list[str] = []
        for i, conv in enumerate(self._conversations):
            marker = ">" if i == self._selected_index else " "
            if conv.thread_id:
                lines.append(f"{marker} {conv.name}")
            else:
                lines.append(
                    f"{marker} [dim]{conv.name}[/] [dim](no thread ID)[/]"
                )
        list_widget = self.query_one("#inbox-list", Static)
        list_widget.update("\n".join(lines))

    def _update_selection(self) -> None:
        if self._conversations:
            self._render_list()

    def _open_selected(self) -> None:
        if not self._conversations:
            return

        conv = self._conversations[self._selected_index]
        if conv.thread_id:
            self.app.push_screen(
                ConversationScreen(
                    thread_id=conv.thread_id,
                    name=conv.name,
                )
            )
        else:
            self.notify(
                "No thread ID available for this conversation",
                severity="warning",
            )

    def action_open(self) -> None:
        self._open_selected()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_up(self) -> None:
        if self._selected_index > 0:
            self._selected_index -= 1
            self._update_selection()

    def action_down(self) -> None:
        if self._selected_index < len(self._conversations) - 1:
            self._selected_index += 1
            self._update_selection()
