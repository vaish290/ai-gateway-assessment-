
import asyncio
import time

import httpx


GATEWAY_URL = "http://127.0.0.1:8003/generate"


async def test_streaming_gateway():
    payload = {
        "prompt": "Give me customer information",
        "max_tokens": 256,
    }

    chunks = []
    arrival_times = []
    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream(
            "POST",
            GATEWAY_URL,
            json=payload,
        ) as response:

            assert response.status_code == 200, (
                f"Unexpected status: {response.status_code}"
            )

            async for chunk in response.aiter_text():
                if chunk:
                    chunks.append(chunk)
                    arrival_times.append(
                        time.perf_counter() - start
                    )

    total_time = time.perf_counter() - start
    output = "".join(chunks)

    # Verify sensitive information is removed.
    assert "john.smith@example.com" not in output
    assert "123-45-6789" not in output
    assert "john.smith" not in output

    print("PASS: Email and SSN redacted")

    # Verify required redaction format.
    assert output.count("[REDACTED]") >= 2
    print("PASS: Required redaction markers present")

    # Verify that multiple chunks were received.
    assert len(chunks) > 1
    print("PASS: Gateway returned multiple chunks")

    # Verify output began before the full response finished.
    assert arrival_times[0] < total_time - 0.05
    print("PASS: Output started before completion")

    print(f"\nFirst chunk: {arrival_times[0]:.2f}s")
    print(f"Total time: {total_time:.2f}s")
    print(f"Total chunks: {len(chunks)}")


if __name__ == "__main__":
    asyncio.run(test_streaming_gateway())
