"""LinkedIn MCP Server Textual TUI application."""

from __future__ import annotations

import logging
from pathlib import Path

from textual.app import App
from textual.binding import Binding
from textual.widgets import Footer, Header

from linkedin_mcp_server.authentication import get_authentication_source
from linkedin_mcp_server.session_state import get_source_profile_dir
from linkedin_mcp_server.tui.screens.login import LoginScreen
from linkedin_mcp_server.tui.screens.main_menu import MainMenuScreen

logger = logging.getLogger(__name__)


class LinkedInTUI(App[None]):
    """Main TUI application for LinkedIn MCP Server."""

    CSS_PATH = Path(__file__).parent / "styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    def __init__(
        self,
        has_auth: bool = False,
        profile_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self._has_auth = has_auth
        self._profile_dir = profile_dir or get_source_profile_dir()

    def on_mount(self) -> None:
        if self._has_auth:
            try:
                get_authentication_source()
                self.push_screen(MainMenuScreen())
                return
            except Exception as e:
                logger.error("Auth check failed: %s", e)
        self._push_login()

    def _push_login(self) -> None:
        self.push_screen(LoginScreen(), self._on_login_result)

    def _on_login_result(self, success: bool | None) -> None:
        if success:
            self.push_screen(MainMenuScreen())
        else:
            self._push_login()

    def compose(self):
        yield Header()
        yield Footer()
