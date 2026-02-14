"""
MCP (Model Context Protocol) client for tool integration.
Connects to MCP server for filesystem and database operations.
"""
import httpx
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MCPClient:
    """
    Model Context Protocol client.
    Provides interface to MCP server tools for filesystem and database access.
    """

    def __init__(self):
        """Initialize MCP client."""
        settings = get_settings()
        self.base_url = settings.mcp_server_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Call MCP server tool.

        Args:
            tool_name: Name of tool to invoke
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            httpx.HTTPError: If MCP server request fails
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MCP tool call failed: {tool_name} - {e}")
            raise

    async def read_file(self, path: str) -> str:
        """
        Read file contents via MCP.

        Args:
            path: File path to read

        Returns:
            File contents
        """
        result = await self.call_tool(
            "filesystem_read",
            {"path": path}
        )
        return result.get("content", "")

    async def query_database(
        self,
        query: str,
        params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute database query via MCP.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query results
        """
        result = await self.call_tool(
            "postgres_query",
            {"query": query, "params": params or {}}
        )
        return result.get("rows", [])

    async def fetch_url(self, url: str) -> str:
        """
        Fetch URL content via MCP.

        Args:
            url: URL to fetch

        Returns:
            Response content
        """
        result = await self.call_tool(
            "fetch_url",
            {"url": url}
        )
        return result.get("content", "")

    async def health_check(self) -> bool:
        """
        Check MCP server health.

        Returns:
            True if MCP server is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


# Global MCP client instance
_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """
    Get MCP client instance.

    Returns:
        MCP client instance
    """
    global _mcp_client

    if _mcp_client is None:
        _mcp_client = MCPClient()
        logger.info("MCP client initialized")

    return _mcp_client


async def close_mcp_client() -> None:
    """Close MCP client."""
    global _mcp_client

    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None
        logger.info("MCP client closed")
