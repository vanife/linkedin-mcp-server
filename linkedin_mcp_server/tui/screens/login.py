"""Login screen for interactive LinkedIn authentication."""

from __future__ import annotations

import threading
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class LoginScreen(ModalScreen[bool]):
    """Screen for interactive LinkedIn login."""

    BINDINGS = [
        ("enter", "login", "Login"),
        ("q", "cancel", "Cancel"),
    ]

    CSS = """
    #login-container {
        align: center middle;
        width: 1fr;
        height: 50%;
        border: solid $accent;
        padding: 1 2;
    }
    #login-container #title {
        text-align: center;
        width: 1fr;
        color: $accent;
        text-style: bold;
    }
    #login-container #instructions {
        text-align: center;
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="login-container"):
            yield Static("LinkedIn MCP TUI", id="title")
            yield Label("")
            yield Label("Not authenticated.", id="status")
            yield Label("")
            yield Static(
                "Press ENTER to open a browser and log in to LinkedIn.",
                id="instructions",
            )
            yield Static("You have 5 minutes to complete login.")
            yield Label("")
            yield Static("Press Q to cancel")

    def _run_login_in_thread(self) -> None:
        """Run profile creation in a background thread."""
        from linkedin_mcp_server.setup import run_profile_creation

        success = run_profile_creation()
        self.app.call_from_thread(self._on_login_complete, success)

    def _on_login_complete(self, success: bool) -> None:
        self.dismiss(success)

    def action_login(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Starting browser, please log in...")
        thread = threading.Thread(
            target=self._run_login_in_thread, daemon=True
        )
        thread.start()

    def action_cancel(self) -> None:
        self.dismiss(False)
