"""Main menu screen with navigation options."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Rule, Static

from linkedin_mcp_server.authentication import clear_auth_state
from linkedin_mcp_server.session_state import get_source_profile_dir

from linkedin_mcp_server.tui.screens.inbox import InboxScreen


class MainMenuScreen(Screen[None]):
    """Main menu with navigation options."""

    BINDINGS = [
        ("l", "logout", "Logout"),
        ("i", "inbox", "Inbox"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="menu-container"):
            yield Static("LinkedIn MCP TUI", id="title")
            yield Rule()
            yield Static("[i]Press I[/]  Inbox", id="menu-inbox")
            yield Static("[i]Press L[/]  Logout", id="menu-logout")
            yield Static("[i]Press Q[/]  Quit", id="menu-quit")

    def action_logout(self) -> None:
        """Clear auth state and return to login screen."""
        profile_dir = get_source_profile_dir()
        if clear_auth_state(profile_dir):
            self.notify("Logged out successfully")
            from linkedin_mcp_server.tui.screens.login import LoginScreen

            self.app.push_screen(LoginScreen())
        else:
            self.notify("Failed to clear auth state", severity="error")

    def action_inbox(self) -> None:
        """Navigate to inbox screen."""
        self.app.push_screen(InboxScreen())

    def action_quit(self) -> None:
        self.app.exit()
