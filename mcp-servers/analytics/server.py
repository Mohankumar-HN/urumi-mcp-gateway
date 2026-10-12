
from mcp.server.mcpserver import MCPServer

server = MCPServer("Urumi Analytics Tools")


@server.tool()
def calculate_conversion_rate(
    visitors: int,
    purchases: int,
) -> dict:
    """Calculate the percentage of visitors who made a purchase."""
    if visitors < 0 or purchases < 0:
        raise ValueError("Visitors and purchases cannot be negative.")

    if purchases > visitors:
        raise ValueError("Purchases cannot exceed visitors.")

    rate = (purchases / visitors * 100) if visitors > 0 else 0.0

    return {
        "visitors": visitors,
        "purchases": purchases,
        "conversion_rate_percent": round(rate, 2),
    }


@server.tool()
def calculate_revenue_summary(
    order_amounts: list[float],
) -> dict:
    """Calculate total revenue and average order value."""
    if any(amount < 0 for amount in order_amounts):
        raise ValueError("Order amounts cannot be negative.")

    total = sum(order_amounts)
    count = len(order_amounts)

    return {
        "order_count": count,
        "total_revenue": round(total, 2),
        "average_order_value": round(total / count, 2) if count else 0.0,
    }


if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8002,
    )
