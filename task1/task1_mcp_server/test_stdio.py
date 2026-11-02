
import asyncio
import json
import sys
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parent / "server.py"


async def main():
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SERVER_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def send(message):
        process.stdin.write(
            (json.dumps(message) + "\n").encode("utf-8")
        )
        await process.stdin.drain()

    async def receive():
        line = await asyncio.wait_for(
            process.stdout.readline(),
            timeout=5
        )
        assert line, "Server produced no response"
        message = json.loads(line)
        assert message.get("jsonrpc") == "2.0"
        return message

    try:
        await send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "stdio-test",
                    "version": "1.0.0"
                }
            }
        })

        response = await receive()
        assert response["id"] == 1
        assert "result" in response

        await send({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })

        await send({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_customer_record",
                "arguments": {
                    "customer_id": "CUST-12345"
                }
            }
        })

        response = await receive()
        assert response["id"] == 2
        assert "result" in response
        print("PASS: Tool response is valid JSON-RPC")

    finally:
        if process.stdin and not process.stdin.is_closing():
            process.stdin.close()

        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()

    stderr_output = (
        await process.stderr.read()
    ).decode("utf-8")

    assert "Fetching customer: CUST-12345" in stderr_output
    print("PASS: Application logs appear on stderr")

    remaining_stdout = await process.stdout.read()

    assert not remaining_stdout.strip(), (
        f"Unexpected stdout output: {remaining_stdout!r}"
    )
    print("PASS: No unexpected stdout output")

    print("\nAll stdio isolation tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
