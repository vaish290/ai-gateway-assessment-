
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
)


# -----------------------------------
# 1. Create MCP Server
# -----------------------------------

mcp = FastMCP("Customer Support Server")


# -----------------------------------
# 2. Define Validation Types
# -----------------------------------

CustomerID = Annotated[
    str,
    StringConstraints(
        pattern=r"^CUST-[0-9]{5}$",
        strict=True
    )
]

RefundAmount = Annotated[
    FiniteFloat,
    Field(gt=0, strict=True)
]

RefundReason = Annotated[
    str,
    StringConstraints(
        min_length=10,
        strict=True
    )
]


# -----------------------------------
# 3. Define Strict Request Models
# -----------------------------------

class CustomerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: CustomerID


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: CustomerID
    amount: RefundAmount
    reason: RefundReason


# -----------------------------------
# 4. Mock Customer Database
# -----------------------------------

CUSTOMERS = {
    "CUST-12345": {
        "name": "John Smith",
        "email": "john@example.com",
        "status": "active"
    },
    "CUST-67890": {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "status": "active"
    }
}


# -----------------------------------
# 5. Tool 1: Get Customer Record
# -----------------------------------

@mcp.tool()
def get_customer_record(
    customer_id: CustomerID
) -> dict:
    """Retrieve customer information using a customer ID."""

    request = CustomerRequest.model_validate({
        "customer_id": customer_id
    })

    print(
        f"Fetching customer: {request.customer_id}",
        file=sys.stderr
    )

    customer = CUSTOMERS.get(request.customer_id)

    if customer is None:
        return {
            "error": "Customer not found"
        }

    return {
        "customer_id": request.customer_id,
        "customer": customer
    }


# -----------------------------------
# 6. Tool 2: Trigger Refund
# -----------------------------------

@mcp.tool()
def trigger_refund(
    customer_id: CustomerID,
    amount: RefundAmount,
    reason: RefundReason
) -> dict:
    """Simulate a refund for an existing customer."""

    request = RefundRequest.model_validate({
        "customer_id": customer_id,
        "amount": amount,
        "reason": reason
    })

    print(
        f"Refund requested for {request.customer_id}",
        file=sys.stderr
    )

    if request.customer_id not in CUSTOMERS:
        return {
            "error": "Customer not found"
        }

    return {
        "status": "success",
        "customer_id": request.customer_id,
        "amount": request.amount,
        "reason": request.reason,
        "message": "Refund simulated successfully"
    }


# -----------------------------------
# 7. Enforce Strict MCP Validation
# -----------------------------------

def enforce_strict_validation():
    """
    Configure MCP's internal Pydantic argument
    models to reject unexpected input fields.
    """

    for tool in mcp._tool_manager.list_tools():

        # Reject unexpected arguments at runtime
        arg_model = tool.fn_metadata.arg_model

        arg_model.model_config["extra"] = "forbid"
        arg_model.model_rebuild(force=True)

        # Advertise the same restriction
        # in the tool's JSON input schema
        tool.parameters["additionalProperties"] = False


# -----------------------------------
# 8. Start MCP Server
# -----------------------------------

if __name__ == "__main__":
    enforce_strict_validation()
    mcp.run(transport="stdio")
