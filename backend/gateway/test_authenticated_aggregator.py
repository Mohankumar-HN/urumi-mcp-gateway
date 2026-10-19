
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

                result = await session.list_tools()

                print("\nAvailable tools:")
                for tool in result.tools:
                    print(f"- {tool.name}")

                print("\nTesting analytics tool...")
                response = await session.call_tool(
                    "analytics__calculate_conversion_rate",
                    {"visitors": 100, "purchases": 8},
                )
                print(response)
                print("\nTesting WooCommerce product listing...")
                products = await session.call_tool(
                    "woocommerce__list_products",
                    {"per_page": 5},
                )

                for item in products.content:
                    if hasattr(item, "text"):
                        print(item.text)

                if products.is_error:
                    print("WooCommerce product listing failed.")


if __name__ == "__main__":
    asyncio.run(main())
