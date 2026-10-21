
import asyncio
import os
import time
from backend.gateway.audit import record_audit

import uvicorn
from backend.gateway.request_identity import current_user_id
from backend.gateway.mcp_auth import MCPAuthMiddleware
from mcp import types
from mcp.server import Server
from sqlalchemy import select

from backend.gateway.database import SessionLocal
from backend.gateway.models import Upstream as UpstreamRecord
from backend.gateway.upstream import (
    UpstreamServer,
    discover_tools,
    call_upstream_tool,
)


# Public tool definitions and routing information.
TOOL_DEFINITIONS: dict[str, types.Tool] = {}
TOOL_ROUTES: dict[str, tuple[UpstreamServer, str]] = {}

# Prevent simultaneous refreshes from overlapping.
_refresh_lock = asyncio.Lock()


def load_enabled_upstreams() -> list[UpstreamServer]:
    """Load enabled upstream configurations from PostgreSQL."""
    with SessionLocal() as db:
        records = db.scalars(
            select(UpstreamRecord)
            .where(UpstreamRecord.enabled.is_(True))
            .order_by(UpstreamRecord.name)
        ).all()

        return [
            UpstreamServer(name=record.name, url=record.url)
            for record in records
        ]


async def refresh_upstream_tools():
    """Refresh gateway tools using the enabled database configurations."""
    async with _refresh_lock:
        upstreams = await asyncio.to_thread(load_enabled_upstreams)

        new_definitions: dict[str, types.Tool] = {}
        new_routes: dict[str, tuple[UpstreamServer, str]] = {}

        for upstream in upstreams:
            try:
                tools = await asyncio.wait_for(
                    discover_tools(upstream),
                    timeout=10,
                )
            except Exception as exc:
                print(
                    f"Could not discover {upstream.name}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue

            for tool in tools:
                original_name = tool["name"]
                gateway_name = f"{upstream.name}__{original_name}"

                # Keep names unique across different upstream servers.
                if gateway_name in new_definitions:
                    print(f"Duplicate gateway tool ignored: {gateway_name}")
                    continue

                new_definitions[gateway_name] = types.Tool(
                    name=gateway_name,
                    description=f"[{upstream.name}] {tool['description']}",
                    inputSchema=tool["input_schema"],
                )
                new_routes[gateway_name] = (upstream, original_name)

                print(f"Registered: {gateway_name}")

        # Publish the new registry only after the discovery pass completes.
        TOOL_DEFINITIONS.clear()
        TOOL_DEFINITIONS.update(new_definitions)
        TOOL_ROUTES.clear()
        TOOL_ROUTES.update(new_routes)

        print(
            f"Tool registry refreshed: "
            f"{len(TOOL_DEFINITIONS)} tools from enabled upstreams."
        )


def get_tool_input_schema(tool_name: str):
    definition = TOOL_DEFINITIONS.get(tool_name)
    return definition.inputSchema if definition else None


async def list_tools_handler(context, params):
    """Refresh configurations before listing tools."""
    await refresh_upstream_tools()

    return types.ListToolsResult(
        tools=list(TOOL_DEFINITIONS.values())
    )



async def call_tool_handler(context, params):
    """Route a tool call and record its audit details."""
    await refresh_upstream_tools()

    tool_name = params.name
    arguments = params.arguments or {}
    route = TOOL_ROUTES.get(tool_name)

    if route is None:
        record_audit(
            user_id=current_user_id.get(),
            upstream_name="unknown",
            tool_name=tool_name,
            duration_seconds=0,
            outcome="failure",
            error_message="Unknown or unavailable tool",
        )
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Unknown or unavailable tool: {tool_name}",
                )
            ],
            isError=True,
        )

    upstream, original_name = route
    started = time.perf_counter()

    try:
        result = await asyncio.wait_for(
            call_upstream_tool(upstream, original_name, arguments),
            timeout=20,
        )

        elapsed = time.perf_counter() - started
        failed = bool(result.is_error)

        record_audit(
            user_id=current_user_id.get(),
            upstream_name=upstream.name,
            tool_name=original_name,
            duration_seconds=elapsed,
            outcome="failure" if failed else "success",
            error_message="Upstream tool returned an error" if failed else None,
        )

        print(
            f"Tool call: {tool_name} | "
            f"upstream={upstream.name} | "
            f"duration={elapsed:.3f}s | "
            f"error={failed}"
        )
        return result

    except Exception as exc:
        elapsed = time.perf_counter() - started

        record_audit(
            user_id=current_user_id.get(),
            upstream_name=upstream.name,
            tool_name=original_name,
            duration_seconds=elapsed,
            outcome="failure",
            error_message=f"{type(exc).__name__}: {exc}"[:2000],
        )

        print(
            f"Tool call failed: {tool_name} | "
            f"upstream={upstream.name} | "
            f"duration={elapsed:.3f}s | "
            f"error={type(exc).__name__}: {exc}"
        )

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
    version="0.3.0",
    instructions=(
        "This gateway exposes tools from enabled upstream MCP servers "
        "configured in PostgreSQL. Tool names use the format "
        "server__tool_name."
    ),
    get_tool_input_schema=get_tool_input_schema,
    on_list_tools=list_tools_handler,
    on_call_tool=call_tool_handler,
)


async def main():
    # Populate tools before accepting client requests.
    await refresh_upstream_tools()

    print("Starting database-backed MCP gateway on port 8003...")

    host = os.getenv("GATEWAY_HOST", "127.0.0.1")
    port = int(os.getenv("GATEWAY_PORT", "8003"))
    app = gateway.streamable_http_app(host=host)
    app.add_middleware(MCPAuthMiddleware)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
