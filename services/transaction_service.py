import uuid

from db import get_cursor


ALLOWED_SORT_COLUMNS = {"transaction_date", "amount", "created_at", "description"}


def _update_budget_spent(cur, profile_id, transaction, multiplier):
    """
    Apply a delta to the `spent` field of every budget affected by this transaction.

    multiplier: +1 when adding (create), -1 when reversing (delete, or old side of update).

    A budget is affected if:
      - it belongs to the same profile and category
      - it was created on or before the transaction date
      - the transaction date falls within the budget's current active period
        (weekly: Monday–Sunday, monthly: same year+month, yearly: same year)

    Only `expense` transactions affect budget `spent`. Income is ignored.
    """
    if not transaction or transaction.get("type") != "expense":
        return

    txn_date = transaction["transaction_date"]
    category_id = transaction["category_id"]
    amount = transaction["amount"]

    cur.execute(
        """
        SELECT id FROM budgets
         WHERE profile_id = %s
           AND category_id = %s
           AND created_at::date <= %s::date
           AND (
               (period = 'monthly'
                AND EXTRACT(YEAR FROM %s::date) = EXTRACT(YEAR FROM CURRENT_DATE)
                AND EXTRACT(MONTH FROM %s::date) = EXTRACT(MONTH FROM CURRENT_DATE))
            OR (period = 'weekly'
                AND %s::date >= date_trunc('week', CURRENT_DATE)::date
                AND %s::date < (date_trunc('week', CURRENT_DATE) + INTERVAL '7 days')::date)
            OR (period = 'yearly'
                AND EXTRACT(YEAR FROM %s::date) = EXTRACT(YEAR FROM CURRENT_DATE))
           )
        """,
        (
            profile_id, category_id, txn_date,
            txn_date, txn_date,          # monthly
            txn_date, txn_date,          # weekly
            txn_date,                    # yearly
        ),
    )
    budget_ids = [row["id"] for row in cur.fetchall()]
    if not budget_ids:
        return

    delta = multiplier * float(amount)
    cur.execute(
        "UPDATE budgets SET spent = COALESCE(spent, 0) + %s WHERE id = ANY(%s)",
        (delta, budget_ids),
    )


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
        txn = cur.fetchone()
        _update_budget_spent(cur, profile_id, txn, +1)
        return txn


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
            txn = cur.fetchone()
            _update_budget_spent(cur, profile_id, txn, +1)
            results.append(txn)
    return results


def update_transaction(profile_id, transaction_id, data):
    if not data:
        return get_transaction(profile_id, transaction_id)

    with get_cursor(commit=True) as cur:
        # Fetch the pre-update version so we can reverse its budget impact
        cur.execute(
            "SELECT * FROM transactions WHERE id = %s AND profile_id = %s",
            (transaction_id, profile_id),
        )
        old = cur.fetchone()
        if not old:
            return None

        set_parts = []
        params = []
        for key, value in data.items():
            set_parts.append(f"{key} = %s")
            params.append(value)
        params.extend([transaction_id, profile_id])

        cur.execute(
            f"UPDATE transactions SET {', '.join(set_parts)} WHERE id = %s AND profile_id = %s RETURNING *",
            params,
        )
        new = cur.fetchone()

        # Reconcile budget spent: reverse old impact, apply new impact
        _update_budget_spent(cur, profile_id, old, -1)
        _update_budget_spent(cur, profile_id, new, +1)

        return new


def delete_transaction(profile_id, transaction_id):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT * FROM transactions WHERE id = %s AND profile_id = %s",
            (transaction_id, profile_id),
        )
        old = cur.fetchone()
        if not old:
            return False

        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND profile_id = %s",
            (transaction_id, profile_id),
        )

        _update_budget_spent(cur, profile_id, old, -1)
        return True
