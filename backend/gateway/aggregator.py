
import asyncio
import time

import uvicorn
from mcp import types
from mcp.server import Server

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

# The gateway's public tool definitions and routing information.
TOOL_DEFINITIONS: dict[str, types.Tool] = {}
TOOL_ROUTES: dict[str, tuple[UpstreamServer, str]] = {}


async def register_upstream_tools():
    """Discover upstream tools and preserve their original input schemas."""

    for upstream in UPSTREAM_SERVERS:
        try:
            tools = await discover_tools(upstream)
        except Exception as exc:
            print(f"Could not discover {upstream.name}: {exc}")
            continue

        for tool in tools:
            original_name = tool["name"]
            gateway_name = f"{upstream.name}__{original_name}"

            # Preserve the input schema supplied by the upstream server.
            definition = types.Tool(
                name=gateway_name,
                description=f"[{upstream.name}] {tool['description']}",
                inputSchema=tool["input_schema"],
            )

            TOOL_DEFINITIONS[gateway_name] = definition
            TOOL_ROUTES[gateway_name] = (upstream, original_name)

            print(f"Registered: {gateway_name}")


def get_tool_input_schema(tool_name: str):
    """Return the schema used to validate a gateway tool's arguments."""

    definition = TOOL_DEFINITIONS.get(tool_name)
    return definition.inputSchema if definition else None


async def list_tools_handler(context, params):
    """Return the tools currently exposed by the gateway."""

    return types.ListToolsResult(
        tools=list(TOOL_DEFINITIONS.values())
    )



async def call_tool_handler(context, params):
    """Route a tool call to its owning upstream server."""

    tool_name = params.name
    arguments = params.arguments or {}

    route = TOOL_ROUTES.get(tool_name)

    if route is None:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Unknown tool: {tool_name}",
                )
            ],
            isError=True,
        )

    upstream, original_name = route
    started = time.perf_counter()

    try:
        result = await call_upstream_tool(
            upstream,
            original_name,
            arguments,
        )

        elapsed = time.perf_counter() - started
        print(
            f"Tool call: {tool_name} | "
            f"upstream={upstream.name} | "
            f"duration={elapsed:.3f}s | "
            f"error={result.is_error}"
        )

        return result

    except Exception as exc:
        import traceback

        elapsed = time.perf_counter() - started
        print(
            f"Tool call failed: {tool_name} | "
            f"duration={elapsed:.3f}s | "
            f"error={type(exc).__name__}: {exc}"
        )
        traceback.print_exc()

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Upstream '{upstream.name}' is unavailable.",
                )
            ],
            isError=True,
        )



gateway = Server(
    name="Urumi Unified MCP Gateway",
    version="0.2.0",
    instructions=(
        "This gateway exposes tools from multiple upstream MCP servers. "
        "Tool names use the format server__tool_name."
    ),
    get_tool_input_schema=get_tool_input_schema,
    on_list_tools=list_tools_handler,
    on_call_tool=call_tool_handler,
)


async def main():
    await register_upstream_tools()

    print("Starting schema-preserving gateway on port 8003...")

    app = gateway.streamable_http_app(host="127.0.0.1")

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8003,
        log_level="info",
    )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

