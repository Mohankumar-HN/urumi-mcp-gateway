
from dataclasses import dataclass

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass
class UpstreamServer:
    name: str
    url: str
    credential: str | None = None

    def headers(self) -> dict[str, str]:
        if not self.credential:
            return {}
        if self.credential.lower().startswith("bearer "):
            return {"Authorization": self.credential}
        return {"X-API-Key": self.credential}


async def discover_tools(upstream: UpstreamServer) -> list[dict]:
    """Connect to an upstream MCP server and discover its tools."""
    async with httpx.AsyncClient(headers=upstream.headers()) as client:
        async with streamable_http_client(upstream.url, http_client=client) as (
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
    async with httpx.AsyncClient(headers=upstream.headers()) as client:
        async with streamable_http_client(upstream.url, http_client=client) as (
        read_stream,
        write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)
