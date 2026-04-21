import re


# Loose international phone regex: optional +, digits, spaces, dashes, parens
_PHONE_RE = re.compile(r"^[+()\-\s\d]{7,20}$")


def _clean_str(value, max_len=100):
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return ""  # explicit clear
    return stripped[:max_len]


def validate_update(data):
    """
    Validate a profile update payload. Returns (cleaned, errors).
    Only known editable fields are returned in `cleaned`; anything else is ignored.
    """
    errors = {}
    cleaned = {}

    if "first_name" in data:
        val = _clean_str(data["first_name"], 60)
        if val is None:
            errors["first_name"] = "Must be a string"
        else:
            cleaned["first_name"] = val

    if "last_name" in data:
        val = _clean_str(data["last_name"], 60)
        if val is None:
            errors["last_name"] = "Must be a string"
        else:
            cleaned["last_name"] = val

    if "phone1" in data:
        raw = data["phone1"]
        if raw is None or raw == "":
            cleaned["phone1"] = ""
        elif not isinstance(raw, str):
            errors["phone1"] = "Must be a string"
        else:
            stripped = raw.strip()
            if not stripped:
                cleaned["phone1"] = ""
            elif not _PHONE_RE.match(stripped):
                errors["phone1"] = "Invalid phone number"
            else:
                cleaned["phone1"] = stripped[:30]

    if "display_name" in data:
        val = _clean_str(data["display_name"], 80)
        if val is None:
            errors["display_name"] = "Must be a string"
        else:
            cleaned["display_name"] = val

    if errors:
        return None, errors
    return cleaned, None
