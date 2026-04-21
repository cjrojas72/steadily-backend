import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.transaction_schema import validate_create as validate_txn_create
from schemas.transaction_schema import validate_update as validate_txn_update
from schemas.category_schema import validate_create as validate_cat_create
from schemas.budget_schema import validate_create as validate_budget_create
from schemas.profile_schema import validate_update as validate_profile_update


def test_transaction_create_valid():
    data = {
        "category_id": "550e8400-e29b-41d4-a716-446655440000",
        "amount": "50.00",
        "type": "expense",
        "transaction_date": "2025-01-15",
    }
    cleaned, errors = validate_txn_create(data)
    assert errors is None
    assert cleaned["amount"] == "50.00"
    assert cleaned["source"] == "manual"


def test_transaction_create_negative_amount():
    data = {
        "category_id": "550e8400-e29b-41d4-a716-446655440000",
        "amount": "-10",
        "type": "expense",
        "transaction_date": "2025-01-15",
    }
    cleaned, errors = validate_txn_create(data)
    assert cleaned is None
    assert "amount" in errors


def test_transaction_create_invalid_type():
    data = {
        "category_id": "550e8400-e29b-41d4-a716-446655440000",
        "amount": "50",
        "type": "refund",
        "transaction_date": "2025-01-15",
    }
    cleaned, errors = validate_txn_create(data)
    assert cleaned is None
    assert "type" in errors


def test_transaction_create_invalid_date():
    data = {
        "category_id": "550e8400-e29b-41d4-a716-446655440000",
        "amount": "50",
        "type": "expense",
        "transaction_date": "not-a-date",
    }
    cleaned, errors = validate_txn_create(data)
    assert cleaned is None
    assert "transaction_date" in errors


def test_transaction_create_missing_fields():
    cleaned, errors = validate_txn_create({})
    assert cleaned is None
    assert "category_id" in errors
    assert "amount" in errors
    assert "type" in errors


def test_transaction_update_partial():
    cleaned, errors = validate_txn_update({"amount": "75.00"})
    assert errors is None
    assert cleaned == {"amount": "75.00"}


def test_category_create_valid():
    cleaned, errors = validate_cat_create({"name": "Food", "color": "#ff0000"})
    assert errors is None
    assert cleaned["name"] == "Food"


def test_category_create_missing_name():
    cleaned, errors = validate_cat_create({})
    assert cleaned is None
    assert "name" in errors


def test_budget_create_valid():
    data = {"category_id": "550e8400-e29b-41d4-a716-446655440000", "limit_amount": "500.00"}
    cleaned, errors = validate_budget_create(data)
    assert errors is None
    assert cleaned["period"] == "monthly"


def test_budget_create_zero_amount():
    data = {"category_id": "550e8400-e29b-41d4-a716-446655440000", "limit_amount": "0"}
    cleaned, errors = validate_budget_create(data)
    assert cleaned is None
    assert "limit_amount" in errors


def test_profile_update_valid():
    data = {
        "first_name": "  Jane  ",
        "last_name": "Doe",
        "phone1": "+1 (555) 123-4567",
    }
    cleaned, errors = validate_profile_update(data)
    assert errors is None
    assert cleaned["first_name"] == "Jane"
    assert cleaned["last_name"] == "Doe"
    assert cleaned["phone1"] == "+1 (555) 123-4567"


def test_profile_update_partial():
    cleaned, errors = validate_profile_update({"first_name": "Alex"})
    assert errors is None
    assert cleaned == {"first_name": "Alex"}


def test_profile_update_clears_phone():
    cleaned, errors = validate_profile_update({"phone1": ""})
    assert errors is None
    assert cleaned == {"phone1": ""}


def test_profile_update_invalid_phone():
    cleaned, errors = validate_profile_update({"phone1": "abc"})
    assert cleaned is None
    assert "phone1" in errors


def test_profile_update_ignores_unknown_fields():
    cleaned, errors = validate_profile_update({"email": "x@y.z", "role": "admin"})
    assert errors is None
    assert cleaned == {}


def test_profile_update_rejects_non_string_name():
    cleaned, errors = validate_profile_update({"first_name": 123})
    assert cleaned is None
    assert "first_name" in errors
