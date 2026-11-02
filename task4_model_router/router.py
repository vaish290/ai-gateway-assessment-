
import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from task4_model_router.quota import TokenQuota


app = FastAPI(title="LLM Model Router")

PRIMARY_URL = os.getenv(
    "PRIMARY_LLM_URL",
    "http://127.0.0.1:9001/generate"
)

BACKUP_URL = os.getenv(
    "BACKUP_LLM_URL",
    "http://127.0.0.1:9002/generate"
)

DATABASE_PATH = os.getenv(
    "QUOTA_DB_PATH",
    "quota.db"
)

quota = TokenQuota(DATABASE_PATH)


class GenerateRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    max_tokens: int = Field(gt=0, le=50_000)


async def call_provider(
    client: httpx.AsyncClient,
    url: str,
    prompt: str,
    max_tokens: int
):
    return await client.post(
        url,
        json={
            "prompt": prompt,
            "max_tokens": max_tokens
        }
    )


@app.post("/generate")
async def generate(request: GenerateRequest):

    # 1. Enforce per-tenant token quota
    allowed = quota.check_and_consume(
        tenant_id=request.tenant_id,
        tokens=request.max_tokens
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Tenant token quota exceeded"
        )

    # 2. Call primary provider
    async with httpx.AsyncClient() as client:
        try:
            primary_response = await client.post(
                PRIMARY_URL,
                json={
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens
                },
                timeout=3.0
            )

            # 3. Return successful primary response
            if primary_response.status_code == 200:
                try:
                    return {
                        "provider": "primary",
                        "result": primary_response.json()
                    }
                except ValueError:
                    raise HTTPException(
                        status_code=502,
                        detail="Invalid provider response"
                    )

            # 4. Fail over only on HTTP 429
            if primary_response.status_code != 429:
                raise HTTPException(
                    status_code=502,
                    detail="Primary provider failed"
                )

        except httpx.TimeoutException:
            # Primary timed out; continue to backup
            pass

        except httpx.RequestError:
            raise HTTPException(
                status_code=502,
                detail="Primary provider unavailable"
            )

        # 5. Call backup provider
        try:
            backup_response = await client.post(
                BACKUP_URL,
                json={
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens
                },
                timeout=3.0
            )

            if backup_response.status_code == 200:
                try:
                    return {
                        "provider": "backup",
                        "result": backup_response.json()
                    }
                except ValueError:
                    raise HTTPException(
                        status_code=502,
                        detail="Invalid backup response"
                    )

            raise HTTPException(
                status_code=502,
                detail="Backup provider failed"
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=502,
                detail="Backup provider unavailable"
            )


@app.get("/health")
async def health():
    return {"status": "ok"}
