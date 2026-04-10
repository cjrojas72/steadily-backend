from middleware.auth import authenticate
from schemas.category_schema import validate_create, validate_update
from services import category_service
from utils.response import error, get_body, success


def handle(event, method, path):
    user_id, err = authenticate(event)
    if err:
        return err

    sub = path.replace("/api/categories", "").strip("/")

    if method == "GET" and not sub:
        return list_categories(user_id)
    elif method == "POST" and not sub:
        return create(event, user_id)
    elif method == "PATCH" and sub:
        return update(event, user_id, sub)
    elif method == "DELETE" and sub:
        return delete(user_id, sub)

    return error("Not found", 404)


def list_categories(user_id):
    cats = category_service.get_categories(user_id)
    return success(cats)


def create(event, user_id):
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    cleaned, errs = validate_create(body)
    if errs:
        return error(errs, 422)

    cat = category_service.create_category(user_id, cleaned)
    return success(cat, 201)


def update(event, user_id, category_id):
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    cleaned, errs = validate_update(body)
    if errs:
        return error(errs, 422)

    cat = category_service.update_category(user_id, category_id, cleaned)
    if not cat:
        return error("Category not found", 404)
    return success(cat)


def delete(user_id, category_id):
    ok, err_msg = category_service.delete_category(user_id, category_id)
    if not ok:
        if err_msg == "Category not found":
            return error(err_msg, 404)
        elif err_msg == "Cannot delete a default category":
            return error(err_msg, 400)
        else:
            return error(err_msg, 409)
    return success("Category deleted")
