import json

from routes import auth, transactions, categories, budgets, analytics
from utils.response import success, error, cors_preflight, set_request_origin


def handler(event, context):
    # Support both HTTP API v2 and REST API v1 event formats
    path = event.get("rawPath") or event.get("path", "")
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod", "")
    )

    # Match CORS origin to the requesting domain
    set_request_origin(event)

    # CORS preflight
    if method == "OPTIONS":
        return cors_preflight()

    # Health check
    if path == "/api/health":
        return success("ok")

    # Route dispatch
    try:
        if path.startswith("/api/auth"):
            return auth.handle(event, method, path)
        elif path.startswith("/api/transactions"):
            return transactions.handle(event, method, path)
        elif path.startswith("/api/categories"):
            return categories.handle(event, method, path)
        elif path.startswith("/api/budgets"):
            return budgets.handle(event, method, path)
        elif path.startswith("/api/analytics"):
            return analytics.handle(event, method, path)
        else:
            return error("Not found", 404)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return error("Internal server error", 500)
