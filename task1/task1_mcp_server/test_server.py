
import pytest

from pydantic import TypeAdapter, ValidationError

from server import CustomerID, RefundAmount, RefundReason, CustomerRequest, RefundRequest


# Create validators
customer_validator = TypeAdapter(CustomerID)
amount_validator = TypeAdapter(RefundAmount)
reason_validator = TypeAdapter(RefundReason)


# --------------------------------
# Test 1: Customer ID Validation
# --------------------------------

def test_valid_customer_id():
    result = customer_validator.validate_python("CUST-12345")
    assert result == "CUST-12345"


@pytest.mark.parametrize("customer_id", [
    "CUST-123",
    "ABC-12345",
    "CUST-ABCDE",
    "CUST-123456",
    "",
    12345,
    None
])
def test_invalid_customer_id(customer_id):
    with pytest.raises(ValidationError):
        customer_validator.validate_python(customer_id)


# --------------------------------
# Test 2: Refund Amount Validation
# --------------------------------

def test_valid_refund_amount():
    result = amount_validator.validate_python(50.0)
    assert result == 50.0


@pytest.mark.parametrize("amount", [
    -50.0,
    0.0,
    "50",
    float("nan"),
    float("inf"),
    None
])
def test_invalid_refund_amount(amount):
    with pytest.raises(ValidationError):
        amount_validator.validate_python(amount)


# --------------------------------
# Test 3: Refund Reason Validation
# --------------------------------

def test_valid_refund_reason():
    result = reason_validator.validate_python(
        "Product arrived damaged"
    )
    assert result == "Product arrived damaged"


@pytest.mark.parametrize("reason", [
    "Bad",
    "",
    "Too short",
    12345,
    None
])
def test_invalid_refund_reason(reason):
    with pytest.raises(ValidationError):
        reason_validator.validate_python(reason)


# --------------------------------
# Test 4: Boundary Cases
# --------------------------------

def test_customer_id_exactly_five_digits():
    result = customer_validator.validate_python("CUST-00001")
    assert result == "CUST-00001"


def test_small_positive_refund_amount():
    result = amount_validator.validate_python(0.01)
    assert result == 0.01


def test_reason_exactly_ten_characters():
    result = reason_validator.validate_python("1234567890")
    assert result == "1234567890"


def test_customer_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        CustomerRequest.model_validate({
            "customer_id": "CUST-12345",
            "admin": True
        })


def test_refund_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        RefundRequest.model_validate({
            "customer_id": "CUST-12345",
            "amount": 50.0,
            "reason": "Product arrived damaged",
            "admin": True
        })


def test_valid_refund_request():
    request = RefundRequest.model_validate({
        "customer_id": "CUST-12345",
        "amount": 50.0,
        "reason": "Product arrived damaged"
    })

    assert request.customer_id == "CUST-12345"
    assert request.amount == 50.0