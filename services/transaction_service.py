import uuid

from db import get_cursor


ALLOWED_SORT_COLUMNS = {"transaction_date", "amount", "created_at", "description"}


def get_transactions(profile_id, filters):
    where = "WHERE profile_id = %s"
    params = [profile_id]

    if filters.get("category_id"):
        where += " AND category_id = %s"
        params.append(filters["category_id"])
    if filters.get("start_date"):
        where += " AND transaction_date >= %s"
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where += " AND transaction_date <= %s"
        params.append(filters["end_date"])
    if filters.get("search"):
        where += " AND description ILIKE %s"
        params.append(f"%{filters['search']}%")

    # Sort (column is whitelisted to prevent injection)
    sort_by = filters.get("sort_by", "transaction_date")
    if sort_by not in ALLOWED_SORT_COLUMNS:
        sort_by = "transaction_date"
    sort_order = "DESC" if filters.get("sort_order", "desc").lower() == "desc" else "ASC"

    page = int(filters.get("page", 1))
    per_page = min(int(filters.get("per_page", 20)), 100)
    offset = (page - 1) * per_page

    with get_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS count FROM transactions {where}", params)
        total = cur.fetchone()["count"]

        cur.execute(
            f"SELECT * FROM transactions {where} ORDER BY {sort_by} {sort_order} LIMIT %s OFFSET %s",
            params + [per_page, offset],
        )
        items = cur.fetchall()

    return {"page": page, "per_page": per_page, "total": total, "items": items}


def get_transaction(profile_id, transaction_id):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM transactions WHERE id = %s AND profile_id = %s",
            (transaction_id, profile_id),
        )
        return cur.fetchone()


def create_transaction(profile_id, data):
    txn_id = str(uuid.uuid4())
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO transactions (id, profile_id, category_id, amount, type, description, transaction_date, source)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (
                txn_id, profile_id, data["category_id"], data["amount"],
                data["type"], data.get("description"), data["transaction_date"],
                data.get("source", "manual"),
            ),
        )
        return cur.fetchone()


def create_transactions_bulk(profile_id, data_list):
    results = []
    with get_cursor(commit=True) as cur:
        for data in data_list:
            txn_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO transactions (id, profile_id, category_id, amount, type, description, transaction_date, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    txn_id, profile_id, data["category_id"], data["amount"],
                    data["type"], data.get("description"), data["transaction_date"],
                    data.get("source", "manual"),
                ),
            )
            results.append(cur.fetchone())
    return results


def update_transaction(profile_id, transaction_id, data):
    if not data:
        return get_transaction(profile_id, transaction_id)

    set_parts = []
    params = []
    for key, value in data.items():
        set_parts.append(f"{key} = %s")
        params.append(value)
    params.extend([transaction_id, profile_id])

    with get_cursor(commit=True) as cur:
        cur.execute(
            f"UPDATE transactions SET {', '.join(set_parts)} WHERE id = %s AND profile_id = %s RETURNING *",
            params,
        )
        return cur.fetchone()


def delete_transaction(profile_id, transaction_id):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND profile_id = %s RETURNING id",
            (transaction_id, profile_id),
        )
        return cur.fetchone() is not None
