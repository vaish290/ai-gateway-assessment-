
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from task3_streaming_guardrail.guardrail import guard_stream


app = FastAPI(title="LLM Streaming Guardrail Gateway")

PROVIDER_URL = os.getenv(
    "LLM_PROVIDER_URL",
    "http://127.0.0.1:9003/generate"
)

PROVIDER_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=10.0,
    pool=5.0
)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_tokens: int = Field(default=256, gt=0, le=50000)


@app.post("/generate")
async def generate(request: GenerateRequest):

    client = httpx.AsyncClient(timeout=PROVIDER_TIMEOUT)

    try:
        upstream_request = client.build_request(
            "POST",
            PROVIDER_URL,
            json={
                "prompt": request.prompt,
                "max_tokens": request.max_tokens
            }
        )

        # Wait for provider response headers before
        # returning HTTP 200 to our client.
        upstream_response = await client.send(
            upstream_request,
            stream=True
        )

        if upstream_response.status_code >= 400:
            status = upstream_response.status_code

            await upstream_response.aclose()
            await client.aclose()

            # Do not expose the provider's raw error details.
            if status == 429:
                raise HTTPException(
                    status_code=503,
                    detail="LLM provider temporarily unavailable"
                )

            raise HTTPException(
                status_code=502,
                detail="Upstream LLM provider error"
            )

        async def provider_chunks():
            try:
                async for chunk in upstream_response.aiter_text():
                    if chunk:
                        yield chunk
            finally:
                await upstream_response.aclose()
                await client.aclose()

        async def safe_stream():
            async for chunk in guard_stream(provider_chunks()):
                yield chunk

        return StreamingResponse(
            safe_stream(),
            media_type="text/plain; charset=utf-8"
        )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        await client.aclose()
        raise HTTPException(
            status_code=504,
            detail="LLM provider timeout"
        )

    except httpx.RequestError:
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to LLM provider"
        )

    except Exception:
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail="LLM gateway request failed"
        )


@app.get("/health")
async def health():
    return {"status": "ok"}
