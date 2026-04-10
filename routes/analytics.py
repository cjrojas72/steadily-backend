from middleware.auth import authenticate
from services import analytics_service
from utils.response import error, get_query_params, success


def handle(event, method, path):
    user_id, err = authenticate(event)
    if err:
        return err

    sub = path.replace("/api/analytics", "").strip("/")

    if method == "GET" and sub == "monthly-spending":
        return monthly_spending(event, user_id)
    elif method == "GET" and sub == "monthly-totals":
        return monthly_totals(event, user_id)

    return error("Not found", 404)


def monthly_spending(event, user_id):
    params = get_query_params(event)
    data = analytics_service.get_monthly_spending(
        user_id,
        year=params.get("year"),
        month=params.get("month"),
    )
    return success(data)


def monthly_totals(event, user_id):
    params = get_query_params(event)
    data = analytics_service.get_monthly_totals(
        user_id,
        year=params.get("year"),
    )
    return success(data)
