
from fastapi import FastAPI, Request

app = FastAPI(title="Mock MCP Backend")

# Track requests received by the backend
received_requests = []


@app.post("/mcp")
async def handle_mcp_request(request: Request):

    # Read the incoming JSON-RPC request
    body = await request.json()

    # Record the request for testing
    received_requests.append(body)

    method = body.get("method")
    request_id = body.get("id")

    # Handle tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "get_customer_record",
                        "description": "Retrieve customer information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "customer_id": {
                                    "type": "string"
                                }
                            }
                        }
                    },
                    {
                        "name": "admin_delete_customer",
                        "description": "Admin-only customer deletion",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "customer_id": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                ]
            }
        }

    # Handle tools/call
    if method == "tools/call":
        tool_name = body.get("params", {}).get("name")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Executed tool: {tool_name}"
                    }
                ]
            }
        }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": "Method not found"
        }
    }
