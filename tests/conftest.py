import uuid
from datetime import datetime, timezone

import jwt
import pytest

TEST_USER_ID = str(uuid.uuid4())
JWT_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


def make_token(user_id=None, expired=False):
    payload = {
        "sub": user_id or TEST_USER_ID,
        "aud": "authenticated",
        "iat": datetime.now(timezone.utc),
        "exp": datetime(2000, 1, 1, tzinfo=timezone.utc) if expired else datetime(2099, 1, 1, tzinfo=timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def make_event(method="GET", path="/api/health", body=None, query=None, token=None):
    """Build a fake API Gateway v2 event."""
    event = {
        "rawPath": path,
        "requestContext": {"http": {"method": method, "path": path}},
        "headers": {},
        "queryStringParameters": query,
        "body": None,
        "isBase64Encoded": False,
    }
    if token:
        event["headers"]["authorization"] = f"Bearer {token}"
    if body is not None:
        import json
        event["body"] = json.dumps(body)
        event["headers"]["content-type"] = "application/json"
    return event
