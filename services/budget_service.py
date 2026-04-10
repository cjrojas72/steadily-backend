import uuid

from db import get_cursor


def get_budgets(profile_id):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM budgets WHERE profile_id = %s",
            (profile_id,),
        )
        return cur.fetchall()


def create_or_update_budget(profile_id, data):
    """Upsert a budget. Returns (row, created: bool)."""
    with get_cursor(commit=True) as cur:
        # Check if budget already exists for this category+period
        cur.execute(
            "SELECT id FROM budgets WHERE profile_id = %s AND category_id = %s AND period = %s",
            (profile_id, data["category_id"], data.get("period", "monthly")),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                "UPDATE budgets SET limit_amount = %s WHERE id = %s RETURNING *",
                (data["limit_amount"], existing["id"]),
            )
            return cur.fetchone(), False

        budget_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO budgets (id, profile_id, category_id, limit_amount, period)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING *""",
            (budget_id, profile_id, data["category_id"], data["limit_amount"], data.get("period", "monthly")),
        )
        return cur.fetchone(), True


def delete_budget(profile_id, budget_id):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM budgets WHERE id = %s AND profile_id = %s RETURNING id",
            (budget_id, profile_id),
        )
        return cur.fetchone() is not None
