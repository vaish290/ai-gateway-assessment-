# AI Gateway Engineering Assessment

## Overview

This repository contains my implementation of four tasks focused on building and securing AI gateway services.

The assessment covers MCP tool integration, access control, streaming LLM responses, sensitive data protection, token-based rate limiting, and model failover.

I implemented the tasks using Python, with a focus on input validation, security, reliability, and testing.

Each task is organized into its own folder and includes implementation files, automated tests, and a separate README explaining the approach.

## Tasks Implemented

### Task 1 — MCP Server with Tool Validation

Built an MCP server using the official Python MCP SDK.

The server exposes two tools:

- `get_customer_record` — Retrieves a sample customer record using a validated customer ID.
- `trigger_refund` — Simulates a refund request after validating the customer ID, amount, and reason.

The server uses Pydantic for input validation and communicates with MCP clients using JSON-RPC over stdio.

**Key concepts:** MCP, tool discovery, input validation, JSON-RPC, stdio communication.

[View Task 1](task1/task1_mcp_server/README.md)

### Task 2 — MCP Security Gateway

Built an HTTP-based security gateway that sits between an MCP client and a backend service.

The gateway checks bearer tokens, identifies user roles, and controls access to tools.

Regular users can access normal tools, while tools beginning with `admin_` require admin permissions.

Authorized requests are forwarded to the backend, while unauthorized admin tool calls are rejected without reaching the backend.

**Key concepts:** Authentication, role-based access control, reverse proxy, JSON-RPC, request forwarding.

[View Task 2](task2_security_gateway/README.md)

### Task 3 — LLM Streaming Guardrail

Built a streaming LLM gateway that checks generated text for sensitive information before sending it to the client.

The gateway detects and redacts email addresses, Social Security numbers, and credit card numbers using the marker `[REDACTED]`.

It uses buffering to handle sensitive information split across streaming chunks and supports incremental HTTP responses.

I also added upstream error handling and a mock LLM provider for testing.

**Key concepts:** LLM streaming, asynchronous generators, PII redaction, bounded buffering, HTTP error handling.

[View Task 3](task3_streaming_guardrail/README.md)

### Task 4 — Token-Aware Model Router

Built a model router that enforces token-based usage limits and supports automatic provider failover.

The router applies a limit of 50,000 tokens per minute per tenant using a sliding window.

Token reservations are stored in SQLite, with transactions used to handle concurrent requests.

If the primary provider returns HTTP 429 or exceeds the configured timeout, the router attempts to use a backup provider.

**Key concepts:** Token-aware rate limiting, sliding window, SQLite persistence, concurrency, provider failover.

[View Task 4](task4_model_router/README.md)

## Technologies Used

- **Language:** Python
- **API framework:** FastAPI
- **MCP integration:** Official MCP Python SDK
- **Input validation:** Pydantic
- **HTTP communication:** HTTPX
- **Database:** SQLite
- **Streaming:** Python asynchronous generators
- **Data protection:** Regular expressions and bounded buffering
- **Protocols:** HTTP, JSON-RPC, MCP over stdio

## Project Structure

```text
ai-gateway-assessment/
│
├── task1/
│   └── task1_mcp_server/
│       ├── server.py
│       ├── test_mcp_integration.py
│       ├── test_jsonrpc.py
│       ├── test_raw_jsonrpc.py
│       ├── test_server.py
│       ├── test_stdio.py
│       └── README.md
│
├── task2_security_gateway/
│   ├── gateway.py
│   ├── mock_backend.py
│   ├── test_gateway.py
│   ├── test_forwarding.py
│   └── README.md
│
├── task3_streaming_guardrail/
│   ├── gateway.py
│   ├── guardrail.py
│   ├── mock_provider.py
│   ├── test_guardrail.py
│   ├── test_security.py
│   ├── test_gateway.py
│   └── README.md
│
├── task4_model_router/
│   ├── quota.py
│   ├── router.py
│   ├── test_quota.py
│   ├── test_router.py
│   ├── test_real_timeout.py
│   └── README.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/vaish290/ai-gateway-assessment-.git
cd ai-gateway-assessment-
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

All commands below should be run from the project root.

## How to Run and Test

### Task 1 — MCP Server

Start the server:

```bash
python -m task1.task1_mcp_server.server
```

The server uses stdio communication, so it waits for MCP client requests rather than exposing an HTTP endpoint.

Run the tests:

```bash
python -m task1.task1_mcp_server.test_mcp_integration
python -m task1.task1_mcp_server.test_jsonrpc
python -m task1.task1_mcp_server.test_raw_jsonrpc
python -m task1.task1_mcp_server.test_stdio
```

### Task 2 — Security Gateway

Start the mock backend:

```bash
python -m uvicorn task2_security_gateway.mock_backend:app --port 8001
```

In a separate terminal, start the gateway:

```bash
python -m uvicorn task2_security_gateway.gateway:app --port 8000
```

Run the tests:

```bash
python -m task2_security_gateway.test_gateway
python -m task2_security_gateway.test_forwarding
```

The gateway uses the following demonstration bearer tokens:

- `demo-user-token` — Regular user
- `demo-admin-token` — Admin user

### Task 3 — Streaming Guardrail

Start the mock LLM provider:

```bash
python -m uvicorn task3_streaming_guardrail.mock_provider:app --port 9003
```

In another PowerShell terminal, configure the provider URL and start the gateway:

```powershell
$env:LLM_PROVIDER_URL = "http://127.0.0.1:9003/generate"
python -m uvicorn task3_streaming_guardrail.gateway:app --port 8003
```

Run the tests:

```bash
python -m task3_streaming_guardrail.test_guardrail
python -m task3_streaming_guardrail.test_security
python -m task3_streaming_guardrail.test_gateway
```

The HTTP integration test requires both the mock provider and gateway to be running.

### Task 4 — Model Router

Run the quota and routing tests:

```bash
python -m task4_model_router.test_quota
python -m task4_model_router.test_router
python -m task4_model_router.test_real_timeout
```

The tests cover token quota enforcement, concurrent reservations, primary provider failures, and backup provider selection.

## Test Results

The following tests were executed successfully during development:

| Task | Test Results |
|---|---|
| Task 1 — MCP Server | Integration, JSON-RPC, and stdio tests passed |
| Task 2 — Security Gateway | Authentication, authorization, and forwarding tests passed |
| Task 3 — Streaming Guardrail | 8/8 guardrail, 4/4 security, and 4/4 HTTP integration tests passed |
| Task 4 — Model Router | 6/6 quota tests, 10/10 router tests, and real timeout test passed |

For Task 3, I also tested an upstream HTTP 500 response and verified that the gateway returned HTTP 502 instead of incorrectly returning HTTP 200.

## Design Approach

Across the four tasks, I focused on a few important principles.

**Validate requests early:** Incorrect inputs should be rejected before they reach business logic or downstream services.

**Enforce security at the gateway:** Authorization checks should happen before protected tool calls are forwarded.

**Protect streamed output:** Sensitive information should be checked before generated text is released to the client.

**Handle failures gracefully:** Provider errors, rate limits, and timeouts should be handled in a predictable way.

**Keep components easy to test:** I used mock services and separate test modules to verify behavior without depending on production systems or paid LLM APIs.

## Limitations and Future Improvements

These implementations are designed for an engineering assessment and use mock services where appropriate.

Some areas that could be extended for production use include:

- Replacing demonstration bearer tokens with verified authentication and tenant identities.
- Supporting additional LLM streaming formats, such as Server-Sent Events.
- Improving streaming guardrail accuracy and reducing unnecessary redaction.
- Handling provider failures that occur after streaming has already started.
- Reconciling token reservations with actual token usage.
- Using a shared quota store for distributed deployments.
- Adding more observability, metrics, and integration tests.

## What I Learned

Working on these tasks helped me understand how different parts of an AI gateway fit together.

Task 1 focused on making tools available through MCP, while Task 2 introduced security and access control around those tools.

Task 3 showed me the challenges of protecting sensitive information in streaming LLM responses, especially when the information is split across chunks.

Task 4 helped me understand token-aware rate limiting, concurrent request handling, and provider failover.

Overall, the assessment gave me hands-on experience with several important components involved in building secure and reliable AI gateway services.
