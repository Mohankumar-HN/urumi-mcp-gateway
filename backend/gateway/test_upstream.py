
import asyncio

from backend.gateway.upstream import (
    UpstreamServer,
    discover_tools,
    call_upstream_tool,
)


async def main():
    servers = [
        UpstreamServer(
            name="time",
            url="http://127.0.0.1:8001/mcp",
        ),
        UpstreamServer(
            name="analytics",
            url="http://127.0.0.1:8002/mcp",
        ),
    ]

    # Discover tools from both servers.
    for server in servers:
        print(f"\nTools from {server.name}:")
        tools = await discover_tools(server)

        for tool in tools:
            print(f"- {tool['name']}")

    # Call a tool on the Time Tools server.
    print("\nCalling the date tool...")
    result = await call_upstream_tool(
        servers[0],
        "get_date_information",
        {},
    )
    print(result)

    # Call a tool on the Analytics server.
    print("\nCalling the conversion-rate tool...")
    result = await call_upstream_tool(
        servers[1],
        "calculate_conversion_rate",
        {"visitors": 200, "purchases": 30},
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
