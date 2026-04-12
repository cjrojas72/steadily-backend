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
    elif method == "POST" and sub == "apply-income":
        return apply_income(event, user_id)
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


def apply_income(event, user_id):
    """
    POST /api/budgets/apply-income
    Body: { allocations: [{ budget_id, amount }] }

    Applies income to specific budgets by incrementing their income_applied column.
    Called by the frontend after creating an income transaction with budget allocations.
    """
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    allocations = body.get("allocations")
    if not allocations or not isinstance(allocations, list):
        return error("allocations array is required", 422)

    for i, alloc in enumerate(allocations):
        if not alloc.get("budget_id"):
            return error(f"allocations[{i}].budget_id is required", 422)
        try:
            amt = float(alloc.get("amount", 0))
            if amt <= 0:
                return error(f"allocations[{i}].amount must be greater than 0", 422)
        except (TypeError, ValueError):
            return error(f"allocations[{i}].amount must be a valid number", 422)

    budget_service.apply_income_to_budgets(user_id, allocations)
    return success("Income applied to budgets")


def delete(user_id, budget_id):
    deleted = budget_service.delete_budget(user_id, budget_id)
    if not deleted:
        return error("Budget not found", 404)
    return success("Budget deleted")
