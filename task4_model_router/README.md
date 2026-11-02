# Task 4 — Token-Aware Rate Limiting and Model Failover

## Overview

For this task, I built a Python-based model router that manages LLM requests using token-based rate limiting and automatic provider failover.

The main goal was to prevent individual tenants from exceeding their token limits while keeping the service available when the primary LLM provider fails.

I used SQLite to track token usage and asynchronous Python code to handle requests and provider communication.

## How It Works

The model router sits between the application and the LLM providers.

Before sending a request to a provider, it checks whether the tenant has enough tokens available.

If the request is within the allowed limit, the router attempts to send it to the primary provider.

If the primary provider returns a rate-limit error or takes too long to respond, the router attempts to use the backup provider.

The basic flow is:

1. The application sends a request with a tenant ID and token requirements.
2. The router checks the tenant's recent token usage.
3. If the tenant has exceeded the limit, the request is rejected.
4. Otherwise, the router reserves the required tokens.
5. The request is sent to the primary LLM provider.
6. If the primary provider returns HTTP 429 or times out, the router attempts the backup provider.
7. The router returns the provider's response or a standardized error.

This helps control token usage while providing a fallback when the primary provider is unavailable.

## Features Implemented

### 1. Token-Based Rate Limiting

I implemented a token limit of **50,000 tokens per minute for each tenant**.

Instead of limiting only the number of API requests, the router considers the number of tokens requested.

This is important because LLM requests can vary significantly in size.

For example, one request might require 100 tokens, while another might require 10,000 tokens.

Both should not count equally toward a tenant's usage limit.

### 2. Sliding-Window Rate Limiting

I used a sliding-window approach to calculate token usage over the most recent 60 seconds.

Whenever a new request arrives, the router checks how many tokens the tenant has already reserved within that window.

If the new request would exceed 50,000 tokens, it is rejected.

Older reservations automatically stop counting once they fall outside the 60-second window.

This avoids resetting everyone's quota at a fixed clock boundary.

### 3. SQLite Persistence

I used SQLite to store token reservations.

This allows usage information to remain available even if the application restarts.

It also avoids relying entirely on in-memory counters.

The database is created locally and does not require a separate database server.

### 4. Concurrency Handling

Multiple requests may arrive at the same time for the same tenant.

Without proper coordination, concurrent requests could incorrectly pass the quota check and exceed the limit.

To prevent this, I used SQLite transactions to make the quota check and token reservation atomic.

This helps ensure that concurrent requests do not reserve more tokens than the allowed quota.

### 5. Automatic Model Failover

The router first attempts to use the primary LLM provider.

If the primary provider returns HTTP 429 (Too Many Requests), the router attempts to send the request to the backup provider.

The router also supports failover when the primary provider exceeds the configured timeout of approximately 3 seconds.

This helps maintain availability when the primary provider is rate-limited or unresponsive.

### 6. Standardized Error Handling

I added error handling so the router returns consistent responses when requests fail.

The goal is to avoid exposing unnecessary internal provider details to the client.

The router handles scenarios such as:

- Tenant token quota exceeded.
- Primary provider rate limiting.
- Primary provider timeout.
- Backup provider failure.
- Other provider communication errors.

## Technologies Used

- Python
- SQLite
- Asynchronous programming (`asyncio`)
- HTTPX
- Token-based rate limiting
- Sliding-window algorithm
- Provider failover

## Project Files

The main files for this task are:

| File | Purpose |
|---|---|
| `quota.py` | Handles token usage tracking and sliding-window quota checks |
| `router.py` | Handles provider routing, failover, and error responses |
| `test_quota.py` | Tests quota calculations and token reservations |
| `test_router.py` | Tests routing, failover, and error handling |
| `test_real_timeout.py` | Tests actual timeout behavior and backup selection |

## How to Run

From the project root, install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

The router and quota logic can be tested directly using the included Python test modules.

SQLite creates the local database file when the quota storage is initialized.

## Testing

I added tests to verify the quota system, provider routing, and failover behavior.

Run the following commands from the project root:

```powershell
python -m task4_model_router.test_quota
python -m task4_model_router.test_router
python -m task4_model_router.test_real_timeout
```

The tests cover:

- Accepting requests within the token limit.
- Rejecting requests that exceed the quota.
- Tracking usage separately for different tenants.
- Sliding-window token calculations.
- Concurrent quota reservations.
- Routing requests to the primary provider.
- Switching to the backup provider after HTTP 429.
- Switching to the backup provider after a timeout.
- Returning standardized errors when providers fail.

### Test Results

| Test Suite | Result |
|---|---|
| Quota tests | 6/6 passed |
| Router tests | 10/10 passed |
| Real timeout test | Passed |

In the real timeout test, the router successfully selected the backup provider after the primary provider exceeded the configured timeout.

## Key Design Decisions

**Token-aware limits instead of request counts:** I chose token-based rate limiting because LLM requests have different token requirements.

**Sliding-window approach:** This provides a more consistent limit over time compared with resetting usage at a fixed interval.

**SQLite persistence:** I used SQLite because it is lightweight, requires minimal setup, and preserves usage information across application restarts.

**Atomic quota reservations:** I used database transactions to reduce the risk of concurrent requests exceeding the quota.

**Primary and backup providers:** I separated the routing logic so requests can fall back to another provider when the primary is rate-limited or unresponsive.

**Standardized errors:** I used consistent error handling to make failures easier for client applications to understand.

## Limitations

The current quota system reserves tokens based on the request's configured token allowance rather than reconciling the reservation with the exact number of tokens eventually consumed.

This provides a conservative way to enforce the limit, but it may count more tokens than were actually used.

The tenant ID is supplied by the caller in this implementation. In a production environment, tenant identity should be derived from a verified authentication mechanism.

SQLite is suitable for this assessment and smaller deployments. A larger distributed system might require a centralized quota store and additional coordination.

The router focuses on the required primary-to-backup failover scenarios rather than implementing a full provider health-monitoring system.
