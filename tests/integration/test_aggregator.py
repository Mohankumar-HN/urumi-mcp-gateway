
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client(
        "http://127.0.0.1:8003/mcp"
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.list_tools()

            print("Tools exposed by the unified gateway:")
            for tool in result.tools:
                print(f"- {tool.name}: {tool.description}")
                # print(f"  Input schema: {tool.input_schema}")

            print("\nCalling the Analytics tool through the gateway...")
            response = await session.call_tool(
                "analytics__calculate_conversion_rate",
                {"visitors": 200, "purchases": 30},
            )
            print(response)

            print("\nCalling the Time tool through the gateway...")
            response = await session.call_tool(
                "time__get_date_information",
                {},
            )
            print(response)

            
            print("\nCalling WooCommerce product listing through the gateway...")
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
