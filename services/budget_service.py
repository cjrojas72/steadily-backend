import uuid
from decimal import Decimal

from db import get_cursor


def _has_column(cur, table, column):
    """Check if a column exists on a table."""
    cur.execute(
        """SELECT 1 FROM information_schema.columns
           WHERE table_name = %s AND column_name = %s""",
        (table, column),
    )
    return cur.fetchone() is not None


def get_budgets(profile_id):
    """
    Fetch all budgets, reading the stored `spent` column directly.
    `spent` is kept in sync by the transaction service (create/update/delete),
    so we no longer need to recompute it from the transactions table here.

    If the income_applied column exists, it raises the budget ceiling.
    Falls back to computing `spent` from transactions when the column is missing.
    """
    with get_cursor() as cur:
        has_income_applied = _has_column(cur, "budgets", "income_applied")
        has_spent = _has_column(cur, "budgets", "spent")
        has_created_at = _has_column(cur, "budgets", "created_at")

        # Income applied increases the budget ceiling, not reduces spent
        if has_income_applied:
            limit_expr = "b.limit_amount + COALESCE(b.income_applied, 0)"
        else:
            limit_expr = "b.limit_amount"

        if has_spent:
            # Stored spent — maintained by transaction service.
            cur.execute(
                f"""
                SELECT b.*,
                       c.name AS category_name,
                       c.color AS category_color,
                       COALESCE(b.spent, 0) AS spent_amount,
                       ({limit_expr}) AS effective_limit
                  FROM budgets b
                  LEFT JOIN categories c ON c.id = b.category_id
                 WHERE b.profile_id = %s
                """,
                (profile_id,),
            )
            return cur.fetchall()

        # Fallback: compute from transactions (pre-migration behavior).
        created_at_filter = (
            "AND t.transaction_date >= b.created_at::date"
            if has_created_at else ""
        )
        spent_expr = """
            COALESCE(SUM(
                CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END
            ), 0)
        """
        cur.execute(
            f"""
            SELECT b.*,
                   c.name AS category_name,
                   c.color AS category_color,
                   {spent_expr} AS spent_amount,
                   ({limit_expr}) AS effective_limit
              FROM budgets b
              LEFT JOIN categories c ON c.id = b.category_id
              LEFT JOIN transactions t
                ON t.profile_id = b.profile_id
               AND t.category_id = b.category_id
               {created_at_filter}
               AND (
                   (b.period = 'monthly'
                    AND EXTRACT(YEAR FROM t.transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                    AND EXTRACT(MONTH FROM t.transaction_date) = EXTRACT(MONTH FROM CURRENT_DATE))
                OR (b.period = 'weekly'
                    AND t.transaction_date >= date_trunc('week', CURRENT_DATE)
                    AND t.transaction_date < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days')
                OR (b.period = 'yearly'
                    AND EXTRACT(YEAR FROM t.transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE))
               )
             WHERE b.profile_id = %s
             GROUP BY b.id, c.name, c.color
            """,
            (profile_id,),
        )
        return cur.fetchall()


def create_budget(profile_id, data):
    """
    Insert a new budget. Returns (row, error_message).

    Multiple budgets for the same (profile, category, period) are allowed —
    each one tracks the same underlying spending independently, so a single
    transaction in the matching category will increment every applicable
    budget's `spent` field.
    """
    period = data.get("period", "monthly")
    category_id = data["category_id"]

    with get_cursor(commit=True) as cur:
        budget_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO budgets (id, profile_id, category_id, limit_amount, period, title, description)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (
                budget_id,
                profile_id,
                category_id,
                data["limit_amount"],
                period,
                data.get("title", ""),
                data.get("description", ""),
            ),
        )
        return cur.fetchone(), None


def create_or_update_budget(profile_id, data):
    """
    Legacy upsert — kept for backwards compatibility with any callers that
    want upsert semantics. Prefer `create_budget` for the REST create flow.
    Returns (row, created: bool).
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id FROM budgets WHERE profile_id = %s AND category_id = %s AND period = %s",
            (profile_id, data["category_id"], data.get("period", "monthly")),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """UPDATE budgets
                   SET limit_amount = %s, title = %s, description = %s
                   WHERE id = %s
                   RETURNING *""",
                (data["limit_amount"], data.get("title", ""), data.get("description", ""), existing["id"]),
            )
            return cur.fetchone(), False

        budget_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO budgets (id, profile_id, category_id, limit_amount, period, title, description)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (
                budget_id,
                profile_id,
                data["category_id"],
                data["limit_amount"],
                data.get("period", "monthly"),
                data.get("title", ""),
                data.get("description", ""),
            ),
        )
        return cur.fetchone(), True


def apply_income_to_budgets(profile_id, allocations):
    """
    Apply income to specific budgets by incrementing their income_applied column.

    allocations: list of { budget_id, amount } dicts where amount is the
    dollar value to apply (already calculated from percentage * total).
    """
    with get_cursor(commit=True) as cur:
        if not _has_column(cur, "budgets", "income_applied"):
            # Column not added yet — skip silently
            return

        for alloc in allocations:
            cur.execute(
                """UPDATE budgets
                   SET income_applied = COALESCE(income_applied, 0) + %s
                   WHERE id = %s AND profile_id = %s""",
                (str(alloc["amount"]), alloc["budget_id"], profile_id),
            )


def delete_budget(profile_id, budget_id):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM budgets WHERE id = %s AND profile_id = %s RETURNING id",
            (budget_id, profile_id),
        )
        return cur.fetchone() is not None
