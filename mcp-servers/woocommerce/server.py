
import os
import asyncio
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from woocommerce.oauth import OAuth
from mcp.server.mcpserver import MCPServer

load_dotenv()

STORE_URL = os.environ["WOOCOMMERCE_URL"].rstrip("/")
PUBLIC_STORE_URL = os.getenv("WOOCOMMERCE_PUBLIC_URL", STORE_URL).rstrip("/")
CONSUMER_KEY = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]

server = MCPServer("Urumi WooCommerce Tools")

ALLOWED_ORDER_STATUSES = {
    "pending",
    "processing",
    "on-hold",
    "completed",
    "cancelled",
    "refunded",
    "failed",
}


def woo_request(
    method: str,
    endpoint: str,
    params: dict | None = None,
    payload: dict | None = None,
):
    """Send an authenticated request through the WooCommerce client."""
    if method not in {"GET", "POST", "PUT"}:
        raise ValueError(f"Unsupported HTTP method: {method}")

    query = urlencode(params or {}, doseq=True)
    separator = "&" if "?" in endpoint else "?"
    signing_url = f"{PUBLIC_STORE_URL}/wp-json/wc/v3/{endpoint}"
    if query:
        signing_url = f"{signing_url}{separator}{query}"

    signed_url = OAuth(
        url=signing_url,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version="wc/v3",
        method=method,
    ).get_oauth_url()
    request_url = signed_url.replace(PUBLIC_STORE_URL, STORE_URL, 1)
    response = requests.request(
        method,
        request_url,
        headers={
            "user-agent": "WooCommerce-Python-REST-API/3.0.0",
            "accept": "application/json",
            "content-type": "application/json",
        },
        json=payload if method in {"POST", "PUT"} else None,
        timeout=15,
    )

    response.raise_for_status()
    return response.json()


async def woo_get(endpoint: str, params: dict | None = None):
    """Run the HTTP request without blocking the event loop."""
    return await asyncio.to_thread(woo_request, "GET", endpoint, params)


# PRODUCT TOOLS

@server.tool()
async def list_products(per_page: int = 10) -> list[dict]:
    """List products from the WooCommerce store."""
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100.")

    products = await woo_get("products", {"per_page": per_page})

    return [
        {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "status": product["status"],
        }
        for product in products
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

    try:
        price = Decimal(regular_price)
    except InvalidOperation as exc:
        raise ValueError("regular_price must be a valid number.") from exc

    if not price.is_finite() or price < 0:
        raise ValueError("regular_price must be finite and non-negative.")

    payload = {
        "name": name.strip(),
        "type": "simple",
        "regular_price": str(price),
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


# ORDER TOOLS

@server.tool()
async def list_orders(
    per_page: int = 10,
    status: str = "",
) -> list[dict]:
    """List recent orders, optionally filtered by status."""
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100.")

    params = {
        "per_page": per_page,
        "orderby": "date",
        "order": "desc",
    }

    if status:
        if status not in ALLOWED_ORDER_STATUSES:
            raise ValueError(
                "Unsupported status. Choose from: "
                + ", ".join(sorted(ALLOWED_ORDER_STATUSES))
            )
        params["status"] = status

    orders = await woo_get("orders", params)

    return [
        {
            "id": order["id"],
            "status": order["status"],
            "total": order["total"],
            "currency": order["currency"],
            "date_created": order["date_created"],
        }
        for order in orders
    ]


@server.tool()
async def get_order(order_id: int) -> dict:
    """Retrieve an order by ID."""
    if order_id <= 0:
        raise ValueError("order_id must be a positive integer.")

    order = await asyncio.to_thread(
        woo_request, "GET", f"orders/{order_id}"
    )

    return {
        "id": order["id"],
        "status": order["status"],
        "total": order["total"],
        "currency": order["currency"],
        "date_created": order["date_created"],
        "line_items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "total": item["total"],
            }
            for item in order.get("line_items", [])
        ],
    }


@server.tool()
async def update_order_status(order_id: int, status: str) -> dict:
    """Update an order's status."""
    if order_id <= 0:
        raise ValueError("order_id must be a positive integer.")

    if status not in ALLOWED_ORDER_STATUSES:
        raise ValueError(
            "Unsupported status. Choose from: "
            + ", ".join(sorted(ALLOWED_ORDER_STATUSES))
        )

    order = await asyncio.to_thread(
        woo_request,
        "PUT",
        f"orders/{order_id}",
        None,
        {"status": status},
    )

    return {
        "id": order["id"],
        "status": order["status"],
        "total": order["total"],
    }


# SERVER STARTUP

if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8004")),
    )
