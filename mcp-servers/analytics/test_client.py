
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client(
        "http://127.0.0.1:8002/mcp"
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Discover the tools offered by the server
            tools = await session.list_tools()

            print("Available Analytics Tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # Test the conversion-rate tool
            conversion = await session.call_tool(
                "calculate_conversion_rate",
                {"visitors": 200, "purchases": 30},
            )
            print("\nConversion Rate Result:")
            print(conversion)

            # Test the revenue-summary tool
            revenue = await session.call_tool(
                "calculate_revenue_summary",
                {"order_amounts": [100, 200, 300]},
            )
            print("\nRevenue Summary Result:")
            print(revenue)


if __name__ == "__main__":
    asyncio.run(main())
