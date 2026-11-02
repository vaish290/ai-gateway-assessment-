
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

from task4_model_router import router
from task4_model_router.quota import TokenQuota


async def run_tests():
    results = []

    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test_router.db"

        # Use a fresh SQLite database for testing.
        router.quota = TokenQuota(db_path)

        async def run_request(handler, tenant_id, max_tokens=1000):
            """
            Send a request through the FastAPI application
            while mocking external LLM providers.
            """

            transport = httpx.MockTransport(handler)
            original_client = httpx.AsyncClient

            def mocked_client(*args, **kwargs):
                if "transport" not in kwargs:
                    kwargs["transport"] = transport

                return original_client(*args, **kwargs)

            with patch.object(
                router.httpx,
                "AsyncClient",
                side_effect=mocked_client
            ):
                async with original_client(
                    transport=httpx.ASGITransport(app=router.app),
                    base_url="http://testserver"
                ) as client:
                    return await client.post(
                        "/generate",
                        json={
                            "tenant_id": tenant_id,
                            "prompt": "Explain MCP",
                            "max_tokens": max_tokens
                        }
                    )

        # TEST 1: Primary provider succeeds
        def primary_success(request):
            return httpx.Response(
                200,
                json={"text": "Primary model response"}
            )

        response = await run_request(
            primary_success,
            "tenant-primary"
        )

        passed = (
            response.status_code == 200
            and response.json()["provider"] == "primary"
        )

        results.append(passed)
        print(
            "PASS: Primary provider success"
            if passed else "FAIL: Primary provider success"
        )

        # TEST 2: Primary returns HTTP 429 -> backup
        calls = []

        def primary_rate_limited(request):
            calls.append(str(request.url))

            if "9001" in str(request.url):
                return httpx.Response(
                    429,
                    json={"error": "Rate limited"}
                )

            return httpx.Response(
                200,
                json={"text": "Backup model response"}
            )

        response = await run_request(
            primary_rate_limited,
            "tenant-failover"
        )

        passed = (
            response.status_code == 200
            and response.json()["provider"] == "backup"
            and len(calls) == 2
        )

        results.append(passed)
        print(
            "PASS: HTTP 429 triggers backup"
            if passed else "FAIL: HTTP 429 triggers backup"
        )

        # TEST 3: Primary timeout -> backup
        calls = []

        def primary_timeout(request):
            calls.append(str(request.url))

            if "9001" in str(request.url):
                raise httpx.ReadTimeout("Simulated timeout")

            return httpx.Response(
                200,
                json={"text": "Backup after timeout"}
            )

        response = await run_request(
            primary_timeout,
            "tenant-timeout"
        )

        passed = (
            response.status_code == 200
            and response.json()["provider"] == "backup"
            and len(calls) == 2
        )

        results.append(passed)
        print(
            "PASS: Timeout triggers backup"
            if passed else "FAIL: Timeout triggers backup"
        )

        # TEST 4: Tenant quota exceeded
        response = await run_request(
            primary_success,
            "tenant-quota",
            max_tokens=50000
        )

        second_response = await run_request(
            primary_success,
            "tenant-quota",
            max_tokens=1
        )

        passed = (
            response.status_code == 200
            and second_response.status_code == 429
        )

        results.append(passed)
        print(
            "PASS: Tenant quota enforced"
            if passed else "FAIL: Tenant quota enforced"
        )

        # TEST 5: Primary HTTP 500 must not trigger backup
        calls = []

        def primary_server_error(request):
            calls.append(str(request.url))

            return httpx.Response(
                500,
                json={"error": "Internal provider failure"}
            )

        response = await run_request(
            primary_server_error,
            "tenant-error"
        )

        passed = (
            response.status_code == 502
            and len(calls) == 1
        )

        results.append(passed)
        print(
            "PASS: Non-429 failure does not trigger backup"
            if passed else "FAIL: Non-429 failure handling"
        )

        # TEST 6: Provider errors must be sanitized
        passed = (
            "Internal provider failure" not in response.text
            and "9001" not in response.text
            and "9002" not in response.text
        )

        results.append(passed)
        print(
            "PASS: Provider error sanitized"
            if passed else "FAIL: Provider error sanitization"
        )

        # TEST 7: Both providers fail
        calls = []

        def both_providers_fail(request):
            calls.append(str(request.url))

            if "9001" in str(request.url):
                return httpx.Response(
                    429,
                    json={"error": "Primary secret details"}
                )

            return httpx.Response(
                503,
                json={"error": "Backup secret details"}
            )

        response = await run_request(
            both_providers_fail,
            "tenant-both-fail"
        )

        passed = (
            response.status_code == 502
            and len(calls) == 2
            and "Primary secret details" not in response.text
            and "Backup secret details" not in response.text
        )

        results.append(passed)
        print(
            "PASS: Backup failure returns sanitized error"
            if passed else "FAIL: Backup failure handling"
        )

        # TEST 8: Backup provider times out
        calls = []

        def backup_timeout(request):
            calls.append(str(request.url))

            if "9001" in str(request.url):
                return httpx.Response(429)

            raise httpx.ReadTimeout("Sensitive provider timeout")

        response = await run_request(
            backup_timeout,
            "tenant-backup-timeout"
        )

        passed = (
            response.status_code == 502
            and len(calls) == 2
            and "Sensitive provider timeout" not in response.text
        )

        results.append(passed)
        print(
            "PASS: Backup timeout handled safely"
            if passed else "FAIL: Backup timeout handling"
        )

        # TEST 9: Invalid token budget rejected
        calls = []

        def should_not_be_called(request):
            calls.append(str(request.url))

            return httpx.Response(
                200,
                json={"text": "Unexpected"}
            )

        response = await run_request(
            should_not_be_called,
            "tenant-invalid",
            max_tokens=-10
        )

        passed = (
            response.status_code == 422
            and len(calls) == 0
        )

        results.append(passed)
        print(
            "PASS: Invalid token budget rejected"
            if passed else "FAIL: Invalid token budget validation"
        )

        # TEST 10: Primary returns malformed JSON
        calls = []

        def invalid_provider_json(request):
            calls.append(str(request.url))

            return httpx.Response(
                200,
                content=b"not valid json"
            )

        response = await run_request(
            invalid_provider_json,
            "tenant-invalid-json"
        )

        passed = (
            response.status_code == 502
            and len(calls) == 1
            and "not valid json" not in response.text
        )

        results.append(passed)
        print(
            "PASS: Malformed provider response handled"
            if passed else "FAIL: Malformed provider response"
        )

    # Final test summary
    passed_count = sum(results)
    total = len(results)

    print(f"\n{passed_count}/{total} router tests passed")

    if passed_count != total:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(run_tests())
