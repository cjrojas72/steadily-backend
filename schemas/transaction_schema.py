from datetime import date
from decimal import Decimal, InvalidOperation


def validate_create(data):
    """Validate transaction creation payload. Returns (cleaned, errors)."""
    errors = {}

    if not data.get("category_id"):
        errors["category_id"] = "Required"

    try:
        amount = Decimal(str(data.get("amount", "")))
        if amount <= 0:
            errors["amount"] = "Must be greater than 0"
    except (InvalidOperation, ValueError):
        errors["amount"] = "Must be a valid number"

    txn_type = data.get("type")
    if txn_type not in ("expense", "income"):
        errors["type"] = "Must be 'expense' or 'income'"

    try:
        if isinstance(data.get("transaction_date"), str):
            date.fromisoformat(data["transaction_date"])
        elif not isinstance(data.get("transaction_date"), date):
            errors["transaction_date"] = "Required (YYYY-MM-DD)"
    except ValueError:
        errors["transaction_date"] = "Invalid date format (YYYY-MM-DD)"

    source = data.get("source", "manual")
    if source not in ("manual", "csv_import"):
        errors["source"] = "Must be 'manual' or 'csv_import'"

    if errors:
        return None, errors

    return {
        "category_id": data["category_id"],
        "amount": str(data["amount"]),
        "type": data["type"],
        "description": data.get("description"),
        "transaction_date": data["transaction_date"],
        "source": source,
    }, None


def validate_update(data):
    """Validate transaction update payload. Returns (cleaned, errors)."""
    errors = {}
    cleaned = {}

    if "amount" in data:
        try:
            amount = Decimal(str(data["amount"]))
            if amount <= 0:
                errors["amount"] = "Must be greater than 0"
            else:
                cleaned["amount"] = str(data["amount"])
        except (InvalidOperation, ValueError):
            errors["amount"] = "Must be a valid number"

    if "type" in data:
        if data["type"] not in ("expense", "income"):
            errors["type"] = "Must be 'expense' or 'income'"
        else:
            cleaned["type"] = data["type"]

    if "transaction_date" in data:
        try:
            date.fromisoformat(data["transaction_date"])
            cleaned["transaction_date"] = data["transaction_date"]
        except (ValueError, TypeError):
            errors["transaction_date"] = "Invalid date format (YYYY-MM-DD)"

    if "category_id" in data:
        cleaned["category_id"] = data["category_id"]

    if "description" in data:
        cleaned["description"] = data["description"]

    if errors:
        return None, errors

    return cleaned, None
