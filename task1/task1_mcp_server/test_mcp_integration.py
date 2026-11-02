
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PATH = Path(__file__).resolve().parent / "server.py"


async def run_tests():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Discover tools
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]

            assert "get_customer_record" in names
            assert "trigger_refund" in names
            print("PASS: Both tools discovered")

            # Test 2: Valid customer lookup
            result = await session.call_tool(
                "get_customer_record",
                {"customer_id": "CUST-12345"}
            )

            assert not result.isError
            print("PASS: Valid customer lookup")

            # Test 3: Invalid customer ID
            result = await session.call_tool(
                "get_customer_record",
                {"customer_id": "CUST-123"}
            )

            assert result.isError
            print("PASS: Invalid customer ID rejected")

            # Test 4: Negative refund amount
            result = await session.call_tool(
                "trigger_refund",
                {
                    "customer_id": "CUST-12345",
                    "amount": -50,
                    "reason": "Product arrived damaged"
                }
            )

            assert result.isError
            print("PASS: Negative refund rejected")

            # Test 5: Unexpected field
            result = await session.call_tool(
                "trigger_refund",
                {
                    "customer_id": "CUST-12345",
                    "amount": 50,
                    "reason": "Product arrived damaged",
                    "admin": True
                }
            )

            assert result.isError
            print("PASS: Unexpected field rejected")


if __name__ == "__main__":
    asyncio.run(run_tests())
