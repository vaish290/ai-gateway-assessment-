
import asyncio
import tempfile
import threading
import time
from pathlib import Path
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import httpx

from task4_model_router import router
from task4_model_router.quota import TokenQuota


class SlowPrimaryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Simulate a primary LLM that takes 5 seconds.
        time.sleep(5)

        body = b'{"text": "Slow primary response"}'

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Expected if the router times out and disconnects.
            pass

    def log_message(self, format, *args):
        pass


class FastBackupHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = b'{"text": "Fast backup response"}'

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@asynccontextmanager
async def running_servers():
    primary = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        SlowPrimaryHandler
    )

    backup = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        FastBackupHandler
    )

    primary.daemon_threads = True
    backup.daemon_threads = True

    threads = [
        threading.Thread(
            target=primary.serve_forever,
            daemon=True
        ),
        threading.Thread(
            target=backup.serve_forever,
            daemon=True
        )
    ]

    for thread in threads:
        thread.start()

    try:
        yield primary.server_port, backup.server_port
    finally:
        primary.shutdown()
        backup.shutdown()
        primary.server_close()
        backup.server_close()

        for thread in threads:
            thread.join(timeout=2)


async def main():
    with tempfile.TemporaryDirectory() as directory:
        router.quota = TokenQuota(
            Path(directory) / "real_timeout_test.db"
        )

        async with running_servers() as (primary_port, backup_port):
            primary_url = (
                f"http://127.0.0.1:{primary_port}/generate"
            )

            backup_url = (
                f"http://127.0.0.1:{backup_port}/generate"
            )

            with (
                patch.object(router, "PRIMARY_URL", primary_url),
                patch.object(router, "BACKUP_URL", backup_url)
            ):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=router.app),
                    base_url="http://testserver"
                ) as client:

                    start = time.perf_counter()

                    response = await client.post(
                        "/generate",
                        json={
                            "tenant_id": "real-timeout-test",
                            "prompt": "Explain MCP",
                            "max_tokens": 1000
                        }
                    )

                    elapsed = time.perf_counter() - start

                print(f"Response status: {response.status_code}")
                print(f"Selected provider: {response.json().get('provider')}")
                print(f"Elapsed time: {elapsed:.2f} seconds")

                assert response.status_code == 200
                assert response.json()["provider"] == "backup"

                # Allow some overhead for scheduling and HTTP handling.
                assert 3 <= elapsed < 4.5, (
                    f"Unexpected failover time: {elapsed:.2f}s"
                )

                print(
                    "\nPASS: Real primary timeout triggers backup"
                )


if __name__ == "__main__":
    asyncio.run(main())
