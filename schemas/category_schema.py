def validate_create(data):
    """Validate category creation payload. Returns (cleaned, errors)."""
    errors = {}

    if not data.get("name"):
        errors["name"] = "Required"

    if errors:
        return None, errors

    return {
        "name": data["name"],
        "color": data.get("color"),
        "icon": data.get("icon"),
        "is_default": bool(data.get("is_default", False)),
    }, None


def validate_update(data):
    """Validate category update payload. Returns (cleaned, errors)."""
    cleaned = {}

    if "name" in data:
        cleaned["name"] = data["name"]
    if "color" in data:
        cleaned["color"] = data["color"]
    if "icon" in data:
        cleaned["icon"] = data["icon"]

    return cleaned, None
