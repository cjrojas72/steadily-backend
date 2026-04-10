import json
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import JWT_SECRET, make_event, make_token

# Patch config before importing handler
os.environ["SUPABASE_JWT_SECRET"] = JWT_SECRET
os.environ["DATABASE_URL"] = ""


def test_health_check():
    from lambda_handler import handler

    event = make_event("GET", "/api/health")
    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["data"] == "ok"
    assert body["error"] is None


def test_cors_preflight():
    from lambda_handler import handler

    event = make_event("OPTIONS", "/api/transactions")
    result = handler(event, None)
    assert result["statusCode"] == 204
    assert "Access-Control-Allow-Origin" in result["headers"]
    assert "Access-Control-Allow-Methods" in result["headers"]


def test_not_found():
    from lambda_handler import handler

    event = make_event("GET", "/api/nonexistent")
    result = handler(event, None)
    assert result["statusCode"] == 404


def test_unauthenticated_transactions():
    from lambda_handler import handler

    event = make_event("GET", "/api/transactions")
    result = handler(event, None)
    assert result["statusCode"] == 401
    body = json.loads(result["body"])
    assert "authorization" in body["error"].lower() or "token" in body["error"].lower()


def test_expired_token():
    from lambda_handler import handler

    token = make_token(expired=True)
    event = make_event("GET", "/api/transactions", token=token)
    result = handler(event, None)
    assert result["statusCode"] == 401
    body = json.loads(result["body"])
    assert "expired" in body["error"].lower()


def test_invalid_token():
    from lambda_handler import handler

    event = make_event("GET", "/api/transactions", token="garbage.token.here")
    result = handler(event, None)
    assert result["statusCode"] == 401


def test_auth_login_missing_body():
    from lambda_handler import handler

    event = make_event("POST", "/api/auth/login")
    result = handler(event, None)
    assert result["statusCode"] == 400


def test_auth_login_missing_fields():
    from lambda_handler import handler

    event = make_event("POST", "/api/auth/login", body={"email": "test@test.com"})
    result = handler(event, None)
    assert result["statusCode"] == 422


def test_response_format():
    """Every response should have data and error keys."""
    from lambda_handler import handler

    event = make_event("GET", "/api/health")
    result = handler(event, None)
    body = json.loads(result["body"])
    assert "data" in body
    assert "error" in body
