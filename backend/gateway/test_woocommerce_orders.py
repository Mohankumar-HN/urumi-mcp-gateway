
import asyncio
from getpass import getpass

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    api_key = getpass("Enter your API key (input hidden): ")

    async with httpx.AsyncClient(
        headers={"X-API-Key": api_key}
    ) as http_client:
        async with streamable_http_client(
            "http://127.0.0.1:8003/mcp",
            http_client=http_client,
        ) as (read_stream, write_stream):
            async with ClientSession(
                read_stream, write_stream
            ) as session:
                await session.initialize()

                print("\nTesting list_orders...")
                result = await session.call_tool(
                    "woocommerce__list_orders",
                    {"per_page": 5},
                )

                print("Error:", result.is_error)
                for item in result.content:
                    if hasattr(item, "text"):
                        print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
