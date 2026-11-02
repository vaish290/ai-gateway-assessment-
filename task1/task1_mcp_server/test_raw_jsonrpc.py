
import asyncio
import json
import sys
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parent / "server.py"


# -----------------------------------
# 1. Send JSON-RPC Message
# -----------------------------------

async def send_message(process, message):
    """Send a JSON-RPC message through stdin."""

    data = json.dumps(message) + "\n"

    process.stdin.write(data.encode("utf-8"))
    await process.stdin.drain()


# -----------------------------------
# 2. Read JSON-RPC Response
# -----------------------------------

async def read_response(process):
    """Read and validate a JSON-RPC response."""

    line = await asyncio.wait_for(
        process.stdout.readline(),
        timeout=5
    )

    assert line, "No response received from MCP server"

    response = json.loads(line.decode("utf-8"))

    assert response.get("jsonrpc") == "2.0", (
        f"Invalid JSON-RPC response: {response}"
    )

    return response


# -----------------------------------
# 3. Run Protocol Tests
# -----------------------------------

async def main():

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SERVER_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:

        # -----------------------------------
        # Test 1: Initialize MCP Connection
        # -----------------------------------

        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "assessment-test-client",
                    "version": "1.0.0"
                }
            }
        }

        await send_message(
            process,
            initialize_request
        )

        response = await read_response(process)

        print("Initialization response:", response)

        assert response.get("id") == 1
        assert "result" in response, (
            f"MCP initialization failed: {response}"
        )

        print("PASS: MCP initialization successful")

        # -----------------------------------
        # Test 2: Initialized Notification
        # -----------------------------------

        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        await send_message(
            process,
            initialized_notification
        )

        print("PASS: Initialized notification sent")

        # -----------------------------------
        # Test 3: Unknown JSON-RPC Method
        # -----------------------------------

        unknown_method_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "nonexistent/method",
            "params": {}
        }

        await send_message(
            process,
            unknown_method_request
        )

        response = await read_response(process)

        print("Unknown method response:", response)

        assert response.get("id") == 2

        assert "error" in response, (
            "Expected a JSON-RPC error response"
        )

        error_code = response["error"]["code"]

        print("Returned error code:", error_code)

        # MCP SDK 1.30.0 observed behavior:
        # Unknown methods are rejected with -32602.
        # Standard JSON-RPC defines -32601 for
        # methods that are not found.

        assert error_code == -32602, (
            f"Expected SDK error -32602, "
            f"but received {error_code}"
        )

        print(
            "PASS: Unknown method rejected "
            "with SDK error -32602"
        )

        # -----------------------------------
        # Test 4: Basic Stdout Validation
        # -----------------------------------

        # Every response read so far was parsed as JSON
        # and checked for jsonrpc == "2.0".

        print("PASS: Responses contain valid JSON-RPC")
        print("PASS: Basic stdout protocol check")

        print("\nAll raw JSON-RPC tests passed!")

    finally:

        # -----------------------------------
        # 4. Shut Down MCP Server
        # -----------------------------------

        if process.stdin and not process.stdin.is_closing():
            process.stdin.close()

        if process.returncode is None:

            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=3
                )

            except asyncio.TimeoutError:

                process.terminate()

                try:
                    await asyncio.wait_for(
                        process.wait(),
                        timeout=3
                    )

                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()


if __name__ == "__main__":
    asyncio.run(main())
