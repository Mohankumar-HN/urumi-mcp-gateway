
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client(
        "http://127.0.0.1:8004/mcp"
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # List available tools
            result = await session.list_tools()
            print("Available tools:")
            for tool in result.tools:
                print(f"- {tool.name}: {tool.description}")

            # Test product listing
            print("\nTesting product listing...")
            products = await session.call_tool(
                "list_products",
                {"per_page": 10},
            )

            for item in products.content:
                if hasattr(item, "text"):
                    print(item.text)

            if products.is_error:
                print("Product listing failed.")
                return

            # Test product creation
            print("\nTesting product creation...")
            created = await session.call_tool(
                "create_product",
                {
                    "name": "MCP Gateway Demo Product",
                    "regular_price": "299",
                    "description": (
                        "Created through the Urumi WooCommerce MCP server."
                    ),
                },
            )

            for item in created.content:
                if hasattr(item, "text"):
                    print(item.text)

            if created.is_error:
                print("Product creation failed.")


if __name__ == "__main__":
    asyncio.run(main())
