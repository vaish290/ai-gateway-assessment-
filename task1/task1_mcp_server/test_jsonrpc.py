
import asyncio
import sys
from mcp.types import ClientRequest, PingRequest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

SERVER_PATH = Path(__file__).resolve().parent / "server.py"


async def run_tests():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)]
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Valid MCP method
            tools = await session.list_tools()

            assert len(tools.tools) >= 2
            print("PASS: tools/list works")

            # Test 2: Unknown tool
            try:
                result = await session.call_tool(
                    "nonexistent_tool",
                    {}
                )

            except McpError as error:
                print(
                    "PASS: Unknown tool rejected:",
                    error
                )

            else:
                assert result.isError, (
                    "Unknown tool was unexpectedly accepted"
                )
                print("PASS: Unknown tool rejected")


if __name__ == "__main__":
    asyncio.run(run_tests())
