
import asyncio
import httpx

from task2_security_gateway import gateway


async def run_tests():
    forwarded_requests = []

    async def fake_backend(request):
        forwarded_requests.append(request)

        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "message": "Backend executed successfully"
                }
            }
        )

    # Replace backend HTTP transport with a mock.
    # This counts forwarding attempts without using port 8001.
    original_async_client = gateway.httpx.AsyncClient

    def mock_client(*args, **kwargs):
        return original_async_client(
            transport=httpx.MockTransport(fake_backend),
            **kwargs
        )

    gateway.httpx.AsyncClient = mock_client

    try:
        transport = httpx.ASGITransport(app=gateway.app)

        async with original_async_client(
            transport=transport,
            base_url="http://testserver"
        ) as client:

            # TEST 1: Unauthorized admin request
            response = await client.post(
                "/mcp",
                headers={
                    "Authorization": "Bearer demo-user-token"
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "admin_delete_customer",
                        "arguments": {}
                    }
                }
            )

            assert response.status_code == 403
            assert response.json()["error"]["code"] == -32001
            assert len(forwarded_requests) == 0

            print("PASS: Unauthorized admin call never forwarded")

            # TEST 2: Authorized admin request
            response = await client.post(
                "/mcp",
                headers={
                    "Authorization": "Bearer demo-admin-token"
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "admin_delete_customer",
                        "arguments": {}
                    }
                }
            )

            assert response.status_code == 200
            assert len(forwarded_requests) == 1

            print("PASS: Authorized admin call forwarded")

            # TEST 3: Verify backend response is preserved
            assert response.json() == {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "message": "Backend executed successfully"
                }
            }

            print("PASS: Backend JSON-RPC response preserved")

    finally:
        gateway.httpx.AsyncClient = original_async_client

    print("\nAll forwarding tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())
