
from mcp.server.mcpserver import MCPServer

from backend.gateway.upstream import (
    UpstreamServer,
    discover_tools,
    call_upstream_tool,
)


UPSTREAM_SERVERS = [
    UpstreamServer(
        name="time",
        url="http://127.0.0.1:8001/mcp",
    ),
    UpstreamServer(
        name="analytics",
        url="http://127.0.0.1:8002/mcp",
    ),
]

gateway = MCPServer(
    name="Urumi Unified MCP Gateway",
    instructions=(
        "This gateway exposes tools from multiple upstream MCP servers. "
        "Use the available tool descriptions and input schemas."
    ),
)


async def register_upstream_tools():
    """Discover tools and register gateway wrappers for them."""
    for upstream in UPSTREAM_SERVERS:
        try:
            tools = await discover_tools(upstream)
        except Exception as exc:
            print(f"Could not discover tools from {upstream.name}: {exc}")
            continue

        for tool in tools:
            original_name = tool["name"]
            gateway_name = f"{upstream.name}__{original_name}"

            # Create a separate wrapper for this particular upstream tool.
            async def wrapper(
                arguments: dict,
                server=upstream,
                tool_name=original_name,
            ):
                result = await call_upstream_tool(
                    server,
                    tool_name,
                    arguments,
                )

                if result.isError:
                    raise RuntimeError(
                        f"Upstream tool {tool_name} reported an error."
                    )

                return result

            gateway.add_tool(
                wrapper,
                name=gateway_name,
                description=(
                    f"[{upstream.name}] {tool['description']}"
                ),
            )

            print(f"Registered gateway tool: {gateway_name}")


if __name__ == "__main__":
    import asyncio

    async def main():
        await register_upstream_tools()
        print("Starting unified gateway on port 8003...")

        await gateway.run_streamable_http_async(
            host="127.0.0.1",
            port=8003,
        )

    asyncio.run(main())
