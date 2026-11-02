
import httpx

GATEWAY_URL = "http://127.0.0.1:8000/mcp"

USER_HEADERS = {
    "Authorization": "Bearer demo-user-token"
}

ADMIN_HEADERS = {
    "Authorization": "Bearer demo-admin-token"
}


def send_request(method, params, headers):
    response = httpx.post(
        GATEWAY_URL,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        },
        timeout=10.0
    )
    return response


# TEST 1: Regular user calling a normal tool
response = send_request(
    "tools/call",
    {
        "name": "get_customer_record",
        "arguments": {
            "customer_id": "CUST-12345"
        }
    },
    USER_HEADERS
)

assert response.status_code == 200
assert "result" in response.json()
print("PASS: Regular user can call normal tools")


# TEST 2: Admin calling an admin-only tool
response = send_request(
    "tools/call",
    {
        "name": "admin_delete_customer",
        "arguments": {
            "customer_id": "CUST-12345"
        }
    },
    ADMIN_HEADERS
)

assert response.status_code == 200
assert "result" in response.json()
print("PASS: Admin can call admin-only tools")


# TEST 3: tools/list should be forwarded unchanged
response = send_request(
    "tools/list",
    {},
    USER_HEADERS
)

assert response.status_code == 200

tools = response.json()["result"]["tools"]
tool_names = [tool["name"] for tool in tools]

assert "get_customer_record" in tool_names
assert "admin_delete_customer" in tool_names

print("PASS: tools/list forwarded without filtering")


# TEST 4: Missing bearer token
response = send_request(
    "tools/list",
    {},
    {}
)

assert response.status_code == 401
print("PASS: Missing bearer token rejected")


# TEST 5: Invalid bearer token
response = send_request(
    "tools/list",
    {},
    {"Authorization": "Bearer invalid-token"}
)

assert response.status_code == 401
print("PASS: Invalid bearer token rejected")


# TEST 6: Regular user calling an admin-only tool
response = send_request(
    "tools/call",
    {
        "name": "admin_delete_customer",
        "arguments": {
            "customer_id": "CUST-12345"
        }
    },
    USER_HEADERS
)

assert response.status_code == 403
assert response.json()["error"]["code"] == -32001

print("PASS: Unauthorized admin tool call blocked")

print("\nAll six gateway tests passed!")
