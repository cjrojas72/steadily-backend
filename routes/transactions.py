from middleware.auth import authenticate
from schemas.transaction_schema import validate_create, validate_update
from services import transaction_service
from utils.response import error, get_body, get_query_params, success


def handle(event, method, path):
    user_id, err = authenticate(event)
    if err:
        return err

    sub = path.replace("/api/transactions", "").strip("/")

    if method == "GET" and not sub:
        return list_transactions(event, user_id)
    elif method == "POST" and not sub:
        return create(event, user_id)
    elif method == "GET" and sub:
        return get_one(user_id, sub)
    elif method == "PATCH" and sub:
        return update(event, user_id, sub)
    elif method == "DELETE" and sub:
        return delete(user_id, sub)

    return error("Not found", 404)


def list_transactions(event, user_id):
    filters = get_query_params(event)
    result = transaction_service.get_transactions(user_id, filters)
    return success({
        "page": result["page"],
        "per_page": result["per_page"],
        "total": result["total"],
        "items": result["items"],
    })


def get_one(user_id, transaction_id):
    txn = transaction_service.get_transaction(user_id, transaction_id)
    if not txn:
        return error("Transaction not found", 404)
    return success(txn)


def create(event, user_id):
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    # Bulk create (array)
    if isinstance(body, list):
        items = []
        for i, item in enumerate(body):
            cleaned, errs = validate_create(item)
            if errs:
                return error(f"Item {i}: {errs}", 422)
            items.append(cleaned)
        transactions = transaction_service.create_transactions_bulk(user_id, items)
        return success(transactions, 201)

    # Single create
    cleaned, errs = validate_create(body)
    if errs:
        return error(errs, 422)
    txn = transaction_service.create_transaction(user_id, cleaned)
    return success(txn, 201)


def update(event, user_id, transaction_id):
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    cleaned, errs = validate_update(body)
    if errs:
        return error(errs, 422)

    txn = transaction_service.update_transaction(user_id, transaction_id, cleaned)
    if not txn:
        return error("Transaction not found", 404)
    return success(txn)


def delete(user_id, transaction_id):
    deleted = transaction_service.delete_transaction(user_id, transaction_id)
    if not deleted:
        return error("Transaction not found", 404)
    return success("Transaction deleted")
