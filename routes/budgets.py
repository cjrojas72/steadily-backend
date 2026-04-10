from middleware.auth import authenticate
from schemas.budget_schema import validate_create
from services import budget_service
from utils.response import error, get_body, success


def handle(event, method, path):
    user_id, err = authenticate(event)
    if err:
        return err

    sub = path.replace("/api/budgets", "").strip("/")

    if method == "GET" and not sub:
        return list_budgets(user_id)
    elif method == "POST" and not sub:
        return create(event, user_id)
    elif method == "DELETE" and sub:
        return delete(user_id, sub)

    return error("Not found", 404)


def list_budgets(user_id):
    budgets = budget_service.get_budgets(user_id)
    return success(budgets)


def create(event, user_id):
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    cleaned, errs = validate_create(body)
    if errs:
        return error(errs, 422)

    budget, created = budget_service.create_or_update_budget(user_id, cleaned)
    return success(budget, 201 if created else 200)


def delete(user_id, budget_id):
    deleted = budget_service.delete_budget(user_id, budget_id)
    if not deleted:
        return error("Budget not found", 404)
    return success("Budget deleted")
