"""
Async CLI entry point for the LinkedIn MCP TUI.

Initializes browser environment, bootstrap policy, then launches a
headless browser for scraping while deferring login to the interactive
(non-headless) flow from the main menu.
"""

import logging
import sys

from linkedin_mcp_server.authentication import get_authentication_source
from linkedin_mcp_server.bootstrap import (
    configure_browser_environment,
    get_runtime_policy,
    initialize_bootstrap,
)
from linkedin_mcp_server.config import get_config
from linkedin_mcp_server.drivers.browser import set_headless
from linkedin_mcp_server.logging_config import configure_logging
from linkedin_mcp_server.session_state import get_source_profile_dir

from .app import LinkedInTUI


async def _run_tui() -> None:
    """Start the LinkedIn TUI application."""
    configure_browser_environment()

    try:
        policy = get_runtime_policy()
        initialize_bootstrap(policy)
        set_headless(True)
        app = LinkedInTUI()
        await app.run_async()
    except Exception as e:
        logging.getLogger(__name__).exception("TUI error: %s", e)
        raise


def main() -> None:
    """TUI application entry point."""
    config = get_config()

    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    profile_dir = get_source_profile_dir()
    has_auth = False
    try:
        get_authentication_source()
        has_auth = True
    except Exception:
        pass

    try:
        app = LinkedInTUI(has_auth=has_auth, profile_dir=profile_dir)
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.getLogger(__name__).exception("TUI error: %s", e)
        sys.exit(1)
