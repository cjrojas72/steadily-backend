from db import get_cursor


def get_monthly_spending(profile_id, year=None, month=None):
    query = "SELECT * FROM monthly_spending WHERE profile_id = %s"
    params = [profile_id]

    if year:
        query += " AND year = %s"
        params.append(year)
    if month:
        query += " AND month = %s"
        params.append(month)

    query += " ORDER BY year DESC, month DESC"

    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_monthly_totals(profile_id, year=None):
    query = "SELECT * FROM monthly_totals WHERE profile_id = %s"
    params = [profile_id]

    if year:
        query += " AND year = %s"
        params.append(year)

    query += " ORDER BY year DESC, month DESC"

    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()
