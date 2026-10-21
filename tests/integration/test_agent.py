
import asyncio
import getpass
import traceback
from mcp.shared.exceptions import MCPError

from backend.chat.agent import chat


async def main():
    api_key = getpass.getpass("Enter your gateway API key: ")

    message = input(
        "Ask the store assistant something: "
    ).strip()

    try:
        answer = await chat(message, api_key)
        print("\nAssistant:", answer)
    except MCPError as exc:
        print("\nMCP error details:")
        print("Error code:", exc.code)
        print("Error message:", exc.message)
        print("Error data:", exc.data)
        traceback.print_exc()
    except Exception:
        print("\nFull error details:")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except MCPError as exc:
        print("\nMCP error details:")
        print("Error code:", exc.code)
        print("Error message:", exc.message)
        print("Error data:", exc.data)
        traceback.print_exc()
    except Exception:
        print("\nFull error details:")
        traceback.print_exc()