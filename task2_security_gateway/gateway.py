
import os
import secrets

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="MCP Security Gateway")

BACKEND_URL = os.getenv(
    "MCP_BACKEND_URL",
    "http://127.0.0.1:8001/mcp"
)

# Demo tokens for local testing only.
# Configure real values using environment variables.
TOKENS = {
    os.getenv("USER_TOKEN", "demo-user-token"): "user",
    os.getenv("ADMIN_TOKEN", "demo-admin-token"): "admin"
}


def get_role(authorization: str | None):
    """Validate the bearer token and return its role."""

    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")

    if not separator or scheme.lower() != "bearer":
        return None

    for valid_token, role in TOKENS.items():
        if secrets.compare_digest(token, valid_token):
            return role

    return None


def rpc_error(request_id, code, message):
    """Create a JSON-RPC error response."""

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }


@app.post("/mcp")
async def mcp_gateway(request: Request):

    # 1. Authenticate the caller
    role = get_role(request.headers.get("authorization"))

    if role is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"}
        )

    # 2. Read the incoming JSON-RPC request
    raw_body = await request.body()

    try:
        import json
        body = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content=rpc_error(None, -32700, "Parse error")
        )

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content=rpc_error(None, -32600, "Invalid Request")
        )

    method = body.get("method")
    request_id = body.get("id")

    # 3. Apply authorization to tools/call
    if method == "tools/call":
        params = body.get("params")

        if not isinstance(params, dict):
            return JSONResponse(
                status_code=400,
                content=rpc_error(
                    request_id,
                    -32602,
                    "Invalid params"
                )
            )

        tool_name = params.get("name")

        if not isinstance(tool_name, str):
            return JSONResponse(
                status_code=400,
                content=rpc_error(
                    request_id,
                    -32602,
                    "Invalid tool name"
                )
            )

        if tool_name.startswith("admin_") and role != "admin":
            return JSONResponse(
                status_code=403,
                content=rpc_error(
                    request_id,
                    -32001,
                    "Access denied"
                )
            )

    # 4. Forward allowed requests to backend
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            backend_response = await client.post(
                BACKEND_URL,
                content=raw_body,
                headers={"Content-Type": "application/json"}
            )

    except httpx.RequestError:
        return JSONResponse(
            status_code=502,
            content=rpc_error(
                request_id,
                -32603,
                "Backend unavailable"
            )
        )

    # 5. Return backend response without modifying it
    return Response(
        content=backend_response.content,
        status_code=backend_response.status_code,
        media_type=backend_response.headers.get(
            "content-type",
            "application/json"
        )
    )
