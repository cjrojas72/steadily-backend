from decimal import Decimal, InvalidOperation


def validate_create(data):
    """Validate budget creation payload. Returns (cleaned, errors)."""
    errors = {}

    if not data.get("category_id"):
        errors["category_id"] = "Required"

    try:
        amount = Decimal(str(data.get("limit_amount", "")))
        if amount <= 0:
            errors["limit_amount"] = "Must be greater than 0"
    except (InvalidOperation, ValueError):
        errors["limit_amount"] = "Must be a valid number"

    if errors:
        return None, errors

    return {
        "category_id": data["category_id"],
        "limit_amount": str(data["limit_amount"]),
        "period": data.get("period", "monthly"),
    }, None
