# Task 2 — MCP Security Gateway

## Overview

For this task, I built a Python-based security gateway that sits between an MCP client and a backend MCP service.

The main goal was to control which tools a user can access based on their permissions, while allowing authorized requests to reach the backend normally.

I used FastAPI to build the gateway and HTTPX to forward requests to the backend.

## How It Works

The gateway acts as a reverse proxy.

Instead of sending requests directly to the backend, the client sends them to the gateway first.

The gateway checks the user's authorization and decides whether the request should be forwarded or rejected.

The basic flow is:

1. The client sends a JSON-RPC request to the gateway.
2. The gateway checks the bearer token.
3. The token is used to determine the user's role.
4. If the request is authorized, it is forwarded to the backend.
5. The backend processes the request and returns a response.
6. The gateway sends the backend's response back to the client.

Unauthorized tool calls are blocked before reaching the backend.

## Features Implemented

### 1. Bearer Token Authentication

The gateway requires a bearer token in the Authorization header.

For this assessment, I used two sample tokens:

- `demo-user-token` — Regular user
- `demo-admin-token` — Admin user

These are demonstration tokens, not production authentication credentials.

Requests with missing or invalid tokens are rejected.

### 2. Role-Based Access Control

The gateway supports two roles: regular user and admin.

Regular users can access normal tools, while admin users can access both normal and admin tools.

Any tool whose name starts with `admin_` is treated as an admin-only tool.

For example:

- `get_customer_record` — Accessible to authorized regular and admin users.
- `admin_delete_record` — Accessible only to admin users.

If a regular user tries to call an admin-only tool, the gateway returns a JSON-RPC error:

```json
{
  "code": -32001,
  "message": "Unauthorized Tool Call"
}
```

The unauthorized request is not forwarded to the backend.

### 3. Transparent Tool Discovery

The gateway forwards `tools/list` requests to the backend.

This allows clients to discover the available tools without the gateway changing the tool list.

### 4. Request Forwarding

Authorized `tools/call` requests are forwarded to the backend, and the backend's response is returned to the client.

This keeps the gateway focused on authentication and authorization rather than implementing the tools themselves.

## Technologies Used

- Python
- FastAPI
- HTTPX
- JSON-RPC
- Bearer token authentication
- Role-based access control

## How to Run

Open a terminal in the project root and install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Step 1: Start the Mock Backend

```powershell
python -m uvicorn task2_security_gateway.mock_backend:app --port 8001
```

The mock backend runs on port `8001`.

### Step 2: Start the Security Gateway

Open another terminal and run:

```powershell
python -m uvicorn task2_security_gateway.gateway:app --port 8000
```

The gateway runs on port `8000`.

Clients should send their requests to the gateway rather than directly to the mock backend.

## Testing

I added tests to verify authentication, authorization, and request forwarding.

Run these commands from the project root while both servers are running:

```powershell
python -m task2_security_gateway.test_gateway
python -m task2_security_gateway.test_forwarding
```

The tests cover:

- Valid regular-user and admin requests.
- Missing or invalid bearer tokens.
- Regular users attempting to call admin-only tools.
- Authorized requests reaching the backend.
- Unauthorized requests being blocked before forwarding.
- Backend responses being preserved.

All the implemented tests passed.

## Key Design Decisions

**Centralized authorization:** I placed the permission checks in the gateway so that access control happens before a tool request reaches the backend.

**Role-based permissions:** I used a simple regular-user and admin model to demonstrate how access restrictions can be applied to MCP tools.

**Transparent forwarding:** Authorized requests and tool discovery are forwarded to the backend without unnecessary changes.

**JSON-RPC errors:** Unauthorized tool calls return the required JSON-RPC error instead of a generic application response.

**Mock backend:** I used a mock service so the gateway could be tested independently without connecting to a real production system.

