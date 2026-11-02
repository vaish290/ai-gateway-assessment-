# Task 1 — MCP Server with Tool Validation

## Overview

For this task, I built a Python-based MCP (Model Context Protocol) server that exposes two tools for handling customer information and refunds.

The goal was to understand how an MCP server makes tools available to an AI application and how to validate requests before executing them.

I used the official Python MCP SDK, along with Pydantic for input validation.

## Tools Implemented

### 1. get_customer_record

This tool retrieves a sample customer record using a customer ID.

The customer ID must follow this format:

`CUST-XXXXX`

For example: `CUST-12345`

If the ID is invalid, the server rejects the request instead of processing it.

### 2. trigger_refund

This tool simulates a refund request for a customer.

It accepts three inputs:

- **customer_id:** Must follow the `CUST-XXXXX` format.
- **amount:** Must be greater than zero.
- **reason:** Must contain at least 10 characters.

The tool validates these inputs before processing the refund.

For this assessment, the refund operation is simulated. No real payments or refunds are processed.

## How It Works

The MCP server uses standard input and output (stdio) to communicate with an MCP client.

The basic flow is:

1. The MCP client connects to the server.
2. The client discovers the available tools.
3. The client calls a tool with the required arguments.
4. The server validates the arguments.
5. If the input is valid, the server returns the tool result. Otherwise, it returns an error.

The server uses JSON-RPC for communication and keeps standard output reserved for MCP protocol messages.

## Technologies Used

- Python
- Official MCP Python SDK
- Pydantic
- JSON-RPC
- stdio transport

## How to Run

From the project root, activate your virtual environment and install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the MCP server:

```powershell
python -m task1.task1_mcp_server.server
```

Since the server uses stdio transport, it waits for MCP client requests rather than starting an HTTP endpoint.

## Testing

I added tests to verify tool discovery, valid requests, invalid inputs, JSON-RPC behavior, and stdio communication.

Run the tests from the project root:

```powershell
python -m task1.task1_mcp_server.test_mcp_integration
python -m task1.task1_mcp_server.test_jsonrpc
python -m task1.task1_mcp_server.test_raw_jsonrpc
python -m task1.task1_mcp_server.test_stdio
```

The tests cover cases such as invalid customer IDs, negative refund amounts, and incorrect JSON-RPC requests.

## Key Design Decisions

**Strict input validation:** I used Pydantic to ensure incorrect inputs are rejected before the tool logic runs.

**Standard MCP communication:** I used the official MCP SDK instead of creating a custom tool-calling protocol.

**Clean stdout:** MCP protocol messages are kept separate from diagnostic output so communication with the client is not interrupted.

**Simulated operations:** Customer lookups and refunds use sample behavior, making the implementation safe to test without external services.
