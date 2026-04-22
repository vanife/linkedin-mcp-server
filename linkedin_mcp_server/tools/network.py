"""LinkedIn network tool: the catch-up page's events."""

import logging
from typing import Any

from fastmcp import Context, FastMCP

from linkedin_mcp_server.config.schema import DEFAULT_TOOL_TIMEOUT_SECONDS
from linkedin_mcp_server.dependencies import get_ready_extractor, tool_errors

logger = logging.getLogger(__name__)


def register_network_tools(
    mcp: FastMCP, *, tool_timeout: float = DEFAULT_TOOL_TIMEOUT_SECONDS
) -> None:
    """Register all network-related tools with the MCP server."""

    @mcp.tool(
        timeout=tool_timeout,
        title="Get Catch-Up",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"network"},
    )
    @tool_errors
    async def get_catchup(
        ctx: Context,
        filter_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Get the network events on LinkedIn's Catch Up page.

        Args:
            ctx: FastMCP context for progress reporting
            filter_type: Event kind to read. Only "birthday" is supported;
                omitting it reads the same page.

        Returns:
            Dict with url, retrieved_at (ISO-8601 UTC) and birthdays. Each
            entry carries name, profile_url, birthday ("0000-MM-DD", the year
            being absent from the page, or null when the card dates nothing),
            birthday_text (the card's own label, e.g. "today" or "Apr 17") and
            original_text. A relative label means nothing without
            retrieved_at, so store the two together.
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_catchup")
        logger.info("Reading catch-up (filter_type=%s)", filter_type)

        await ctx.report_progress(
            progress=0, total=100, message="Reading the catch-up page"
        )

        result = await extractor.get_catchup(filter_type=filter_type)

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result
