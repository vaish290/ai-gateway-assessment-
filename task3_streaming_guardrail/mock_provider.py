
import asyncio

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel


app = FastAPI(title="Mock LLM Provider")


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 256


@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Simulate an LLM provider that streams text
    in multiple chunks.
    """

    async def stream_response():
        chunks = [
            "This is a safe introductory message. " * 10,
            "Here is more ordinary information. ",
            "The customer's email is john.",
            "smith@example.com. ",
            "Their SSN is 123-",
            "45-6789. ",
            "Thank you!"
        ]

        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.1)

    return StreamingResponse(
        stream_response(),
        media_type="text/plain"
    )


@app.post("/fail")
async def simulate_provider_failure():
    """
    Simulate an upstream LLM provider failure.

    This endpoint intentionally returns HTTP 500
    so we can verify how the gateway handles errors.
    """

    return JSONResponse(
        status_code=500,
        content={
            "error": "Simulated upstream provider failure"
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
