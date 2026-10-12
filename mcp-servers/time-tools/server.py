from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer

server = MCPServer("Urumi Time Tools")


@server.tool()
def get_current_utc_time() -> str:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).isoformat()


@server.tool()
def get_date_information() -> dict:
    """Return the current UTC date and its weekday."""
    now = datetime.now(timezone.utc)

    return {
        "date": now.date().isoformat(),
        "weekday": now.strftime("%A"),
        "timezone": "UTC",
    }


if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )
