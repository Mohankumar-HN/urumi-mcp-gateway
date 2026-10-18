
import asyncio
from backend.gateway.upstream import UpstreamServer, call_upstream_tool


async def main():
    # This port should have no server listening on it.
    upstream = UpstreamServer(
        name="failure-test",
        url="http://127.0.0.1:18999/mcp",
    )

    try:
        await asyncio.wait_for(
            call_upstream_tool(
                upstream,
                "example_tool",
                {},
            ),
            timeout=5,
        )
        print("Unexpected: the unreachable server responded.")
    except Exception as exc:
        print(f"Expected connection failure: {type(exc).__name__}")
        print("The helper fails cleanly instead of crashing the process.")


if __name__ == "__main__":
    asyncio.run(main())
