from middleware.auth import authenticate
from schemas.profile_schema import validate_update
from services import profile_service
from utils.response import error, get_body, success


def handle(event, method, path):
    user_id, err = authenticate(event)
    if err:
        return err

    sub = path.replace("/api/profile", "").strip("/")

    if method == "GET" and not sub:
        return get(user_id)
    elif method == "PATCH" and not sub:
        return update(event, user_id)

    return error("Not found", 404)


def get(user_id):
    profile = profile_service.get_profile(user_id)
    if not profile:
        return error("Profile not found", 404)
    return success(profile)


def update(event, user_id):
    body = get_body(event)
    if body is None:
        return error("Request body is required", 400)

    cleaned, errs = validate_update(body)
    if errs:
        return error(errs, 422)

    profile = profile_service.update_profile(user_id, cleaned)
    if not profile:
        return error("Profile not found", 404)
    return success(profile)
