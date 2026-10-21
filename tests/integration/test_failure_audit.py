
import asyncio
from types import SimpleNamespace

from backend.gateway import aggregator
from backend.gateway.request_identity import current_user_id
from backend.gateway.upstream import UpstreamServer


async def fake_refresh():
    # Keep the test route registered for this controlled test.
    return None


async def fake_failed_call(upstream, tool_name, arguments):
    # Simulate the upstream connection failing.
    raise ConnectionError("Simulated upstream connection failure")


async def main():
    upstream = UpstreamServer(
        name="analytics",
        url="http://127.0.0.1:18999/mcp",
    )
    tool_name = "analytics__calculate_conversion_rate"

    # Replace the refresh and call functions only in this test process.
    aggregator.refresh_upstream_tools = fake_refresh
    aggregator.call_upstream_tool = fake_failed_call
    aggregator.TOOL_ROUTES[tool_name] = (
        upstream,
        "calculate_conversion_rate",
    )

    # Give this test's audit entry a clearly identifiable user ID.
    token = current_user_id.set("controlled-failure-test")

    try:
        result = await aggregator.call_tool_handler(
            None,
            SimpleNamespace(
                name=tool_name,
                arguments={"visitors": 100, "purchases": 8},
            ),
        )

        print("Gateway returned an error:", result.is_error)
        print("Response:", result.content[0].text)
        print("Expected audit user ID: controlled-failure-test")
    finally:
        current_user_id.reset(token)


if __name__ == "__main__":
    asyncio.run(main())
