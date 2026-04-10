import json
import uuid
from datetime import date, datetime
from decimal import Decimal

import config


class _Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def _cors_headers():
    origin = config.CORS_ORIGINS[0] if config.CORS_ORIGINS else "*"
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
    }


def success(data, status=200):
    return {
        "statusCode": status,
        "headers": _cors_headers(),
        "body": json.dumps({"data": data, "error": None}, cls=_Encoder),
    }


def error(message, status=400):
    return {
        "statusCode": status,
        "headers": _cors_headers(),
        "body": json.dumps({"data": None, "error": message}),
    }


def cors_preflight():
    return {
        "statusCode": 204,
        "headers": _cors_headers(),
        "body": "",
    }


def get_body(event):
    """Parse JSON body from the Lambda event."""
    import base64

    body = event.get("body", "")
    if not body:
        return None
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def get_query_params(event):
    """Return query string parameters dict (never None)."""
    return event.get("queryStringParameters") or {}
