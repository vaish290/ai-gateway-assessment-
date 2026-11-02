# Task 3 — LLM Streaming Guardrail

## Overview

For this task, I built a Python-based LLM gateway that streams responses from a language model provider while checking the generated text for sensitive information.

The main goal was to prevent personally identifiable information (PII), such as email addresses, Social Security numbers, and credit card numbers, from reaching the client.

One of the main challenges was handling sensitive information that might be split across multiple streaming chunks.

I used FastAPI to create the gateway, HTTPX to communicate with the LLM provider, and regular expressions to detect and redact sensitive information.

## How It Works

The gateway sits between the client and the LLM provider.

Instead of receiving the response directly from the provider, the client receives it through the gateway, where the generated text is checked before being sent.

The basic flow is:

1. The client sends a text generation request to the gateway.
2. The gateway forwards the request to the LLM provider.
3. The provider starts streaming its generated response.
4. The gateway temporarily buffers incoming text to check for sensitive information.
5. Any detected PII is replaced with `[REDACTED]`.
6. The cleaned text is streamed back to the client.

This allows the client to receive the response incrementally without waiting for the entire generation to finish.

## Features Implemented

### 1. Streaming LLM Gateway

I created a FastAPI endpoint called `/generate` that accepts a prompt and a maximum token count.

The gateway forwards the request to the configured LLM provider and streams the response back to the client.

I used asynchronous streaming so the gateway can process incoming text without waiting for the complete response.

### 2. PII Detection and Redaction

The guardrail detects three types of sensitive information:

- Email addresses
- Social Security numbers (SSNs)
- Credit card numbers

When sensitive information is detected, it is replaced with:

`[REDACTED]`

For example:

**Original response:**

```text
The customer's email is john.smith@example.com.
```

**After redaction:**

```text
The customer's email is [REDACTED].
```

The goal is to prevent sensitive values from being exposed in the output.

### 3. Handling PII Across Streaming Chunks

One challenge with streaming is that sensitive information may arrive in separate pieces.

For example, an email address could arrive as:

```text
Chunk 1: john
Chunk 2: @example
Chunk 3: .com
```

Checking each chunk independently would not reliably detect the complete email address.

To handle this, I implemented buffering in the guardrail.

The gateway keeps part of the incoming text until enough context is available to check for sensitive information.

Only processed text is released to the client.

### 4. Bounded Buffering

I added a buffer limit to prevent the gateway from continuously storing an unlimited amount of text.

The implementation uses a maximum candidate length of 256 characters and retains additional context when processing streaming boundaries.

If a candidate becomes too long to process safely, the guardrail uses a fail-closed approach and replaces it with `[REDACTED]`.

This favors protecting sensitive information, although it may sometimes remove harmless text as well.

### 5. Upstream Error Handling

I also added error handling for failures from the LLM provider.

For example, if the provider returns HTTP 500 before streaming starts, the gateway returns HTTP 502 instead of incorrectly returning a successful response.

The gateway also handles provider connection errors and timeouts before the streaming response begins.

Provider error details are not directly exposed to the client.

### 6. Mock LLM Provider

I created a mock provider to test the gateway without using a real LLM API.

The mock provider generates text in multiple chunks and includes sample sensitive information.

It also includes a failure endpoint to simulate an upstream provider error.

This helped me test both successful streaming and error handling.

## Technologies Used

- Python
- FastAPI
- HTTPX
- Regular expressions (Regex)
- Asynchronous Python generators
- Streaming HTTP responses
- Pydantic

## How to Run

From the project root, install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Step 1: Start the Mock LLM Provider

Open a terminal and run:

```powershell
python -m uvicorn task3_streaming_guardrail.mock_provider:app --port 9003
```

The mock provider runs on port `9003`.

### Step 2: Start the Streaming Gateway

Open another terminal and run:

```powershell
$env:LLM_PROVIDER_URL = "http://127.0.0.1:9003/generate"
python -m uvicorn task3_streaming_guardrail.gateway:app --port 8003
```

The gateway runs on port `8003`.

### Step 3: Send a Test Request

Open a third PowerShell terminal and run:

```powershell
$body = @{
    prompt = "Give me customer information"
    max_tokens = 256
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8003/generate" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

The gateway returns the generated text with sensitive information replaced by `[REDACTED]`.

## Testing

I added automated tests for the guardrail logic, security checks, and HTTP streaming behavior.

Run these commands from the project root:

```powershell
python -m task3_streaming_guardrail.test_guardrail
python -m task3_streaming_guardrail.test_security
python -m task3_streaming_guardrail.test_gateway
```

The HTTP integration test requires both the mock provider and gateway to be running.

The tests cover:

- Emails, SSNs, and credit card numbers split across chunks.
- Multiple types of sensitive information in one response.
- Credit card numbers crossing buffer boundaries.
- Handling long uninterrupted text.
- Producing output before the provider finishes streaming.
- Checking that partial sensitive values are not exposed in tested cases.
- Keeping memory usage bounded during the tested scenarios.

I also manually tested an upstream HTTP 500 response and verified that the gateway returned HTTP 502.

### Test Results

| Test Suite | Result |
|---|---|
| Guardrail tests | 8/8 passed |
| Security tests | 4/4 passed |
| HTTP integration tests | 4/4 passed |
| Upstream HTTP 500 handling | Passed |

During the final HTTP streaming test, the first response chunk arrived in approximately 0.78 seconds, while the complete response took approximately 1.54 seconds.

These timings were measured locally using the mock provider and are not guaranteed performance benchmarks.

## Key Design Decisions

**Streaming instead of waiting for the complete response:** I used asynchronous generators so cleaned text can be sent to the client incrementally.

**Buffering across chunks:** I avoided checking each chunk independently because sensitive information can be split between chunks.

**Fail-closed behavior:** When the guardrail cannot safely process an excessively long candidate, it redacts the content instead of releasing potentially sensitive text.

**Consistent redaction marker:** I used `[REDACTED]` for all supported PII types to match the assessment requirements.

**Provider error handling:** I check the provider's HTTP status before returning a successful streaming response to the client.

**Independent testing:** I used a mock LLM provider to test the streaming and redaction behavior without depending on external API credentials.

## Limitations

The current implementation focuses on common formats of emails, SSNs, and credit card numbers. It does not cover every possible variation of sensitive information.

The buffering approach can sometimes redact harmless text, especially when a very long uninterrupted candidate exceeds the buffer limit.

The gateway handles upstream errors before streaming begins. If the provider fails after the response has already started, the HTTP status cannot be changed, and additional in-stream error handling would be needed.

The mock provider uses plain-text streaming. Supporting providers that use formats such as Server-Sent Events (SSE) would require parsing their event format.



I also learned the importance of checking upstream errors before starting an HTTP streaming response.

The biggest takeaway was understanding the trade-off between streaming responses quickly and keeping enough context to prevent sensitive information from being exposed.
