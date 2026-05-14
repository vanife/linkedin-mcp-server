"""LinkedIn network tools (catch-up, notifications, etc.)."""

import logging
from typing import Any

from fastmcp import Context, FastMCP

from linkedin_mcp_server.callbacks import MCPContextProgressCallback
from linkedin_mcp_server.config.schema import DEFAULT_TOOL_TIMEOUT_SECONDS
from linkedin_mcp_server.core.exceptions import AuthenticationError
from linkedin_mcp_server.dependencies import get_ready_extractor, handle_auth_error
from linkedin_mcp_server.error_handler import raise_tool_error

logger = logging.getLogger(__name__)


def register_network_tools(
    mcp: FastMCP, *, tool_timeout: float = DEFAULT_TOOL_TIMEOUT_SECONDS
) -> None:
    """Register all network-related tools with the MCP server."""

    @mcp.tool(
        timeout=tool_timeout,
        title="Get Catch-Up",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"network", "scraping"},
        exclude_args=["extractor"],
    )
    async def get_catchup(
        ctx: Context,
        filter_type: str | None = None,
        extractor: Any | None = None,
    ) -> dict[str, Any]:
        """
        Scrape LinkedIn's Catch Up section for network updates.

        Args:
            ctx: FastMCP context for progress reporting
            filter_type: Event type to filter by. Currently supported: "birthday".

        Returns:
            For filter_type="birthday": dict with url, retrieved_at (ISO-8601 UTC),
            and birthdays list. Each birthday entry contains name, profile_url,
            birthday ("0000-MM-DD"), birthday_text (e.g. "today", "Apr 14"),
            and original_text (raw card text).
        """
        try:
            extractor = extractor or await get_ready_extractor(
                ctx, tool_name="get_catchup"
            )
            logger.info("Getting catch-up (filter_type=%s)", filter_type)

            cb = MCPContextProgressCallback(ctx)
            result = await extractor.get_catchup(filter_type=filter_type, callbacks=cb)

            return result

        except AuthenticationError as e:
            try:
                await handle_auth_error(e, ctx)
            except Exception as relogin_exc:
                raise_tool_error(relogin_exc, "get_catchup")
        except Exception as e:
            raise_tool_error(e, "get_catchup")  # NoReturn
