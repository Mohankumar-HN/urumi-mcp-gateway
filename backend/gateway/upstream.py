
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass
class UpstreamServer:
    name: str
    url: str


async def discover_tools(upstream: UpstreamServer) -> list[dict]:
    """Connect to an upstream MCP server and discover its tools."""
    async with streamable_http_client(upstream.url) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()

            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.input_schema,
                }
                for tool in result.tools
            ]


async def call_upstream_tool(
    upstream: UpstreamServer,
    tool_name: str,
    arguments: dict,
):
    """Execute a tool on the upstream MCP server."""
    async with streamable_http_client(upstream.url) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments)
