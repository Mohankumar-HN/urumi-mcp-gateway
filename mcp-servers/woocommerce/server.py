
import os
import asyncio
import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1
from mcp.server.mcpserver import MCPServer

load_dotenv()

STORE_URL = os.environ["WOOCOMMERCE_URL"].rstrip("/")
CONSUMER_KEY = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]

server = MCPServer("Urumi WooCommerce Tools")


def woo_request(method: str, endpoint: str, params: dict | None = None,
                payload: dict | None = None):
    """Send an OAuth-authenticated request to WooCommerce."""
    url = f"{STORE_URL}/wp-json/wc/v3/{endpoint}"

    auth = OAuth1(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        signature_method="HMAC-SHA1",
    )

    response = requests.request(
        method,
        url,
        params=params,
        json=payload,
        auth=auth,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


async def woo_get(endpoint: str, params: dict | None = None):
    """Send an authenticated GET request without blocking the event loop."""
    return await asyncio.to_thread(woo_request, "GET", endpoint, params)


@server.tool()
async def list_products(per_page: int = 10) -> list[dict]:
    """List products from the WooCommerce store."""
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100.")

    products = await woo_get("products", {"per_page": per_page})
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "status": p["status"],
        }
        for p in products
    ]


@server.tool()
async def create_product(
    name: str,
    regular_price: str,
    description: str = "",
) -> dict:
    """Create a simple product in WooCommerce."""
    if not name.strip():
        raise ValueError("Product name cannot be empty.")
    if not regular_price.strip():
        raise ValueError("Regular price cannot be empty.")

    payload = {
        "name": name,
        "type": "simple",
        "regular_price": regular_price,
        "description": description,
    }

    product = await asyncio.to_thread(
        woo_request, "POST", "products", None, payload
    )

    return {
        "id": product["id"],
        "name": product["name"],
        "price": product["price"],
        "status": product["status"],
    }


if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8004,
    )
