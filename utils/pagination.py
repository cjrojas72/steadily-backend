from utils.response import get_query_params


def get_pagination_params(event):
    """Extract page and per_page from query params."""
    params = get_query_params(event)
    page = max(int(params.get("page", 1)), 1)
    per_page = min(max(int(params.get("per_page", 20)), 1), 100)
    offset = (page - 1) * per_page
    return page, per_page, offset
