from db import get_cursor


def get_monthly_spending(profile_id, year=None, month=None):
    """
    Spending by category per month, computed from the transactions table.
    Returns rows with: year, month, category_id, category_name, color, total
    """
    query = """
        SELECT EXTRACT(YEAR FROM t.transaction_date)::int  AS year,
               EXTRACT(MONTH FROM t.transaction_date)::int AS month,
               t.category_id,
               c.name  AS category_name,
               c.color AS color,
               SUM(t.amount) AS total
          FROM transactions t
          LEFT JOIN categories c ON c.id = t.category_id
         WHERE t.profile_id = %s
           AND t.type = 'expense'
    """
    params = [profile_id]

    if year:
        query += " AND EXTRACT(YEAR FROM t.transaction_date) = %s"
        params.append(int(year))
    if month:
        query += " AND EXTRACT(MONTH FROM t.transaction_date) = %s"
        params.append(int(month))

    query += """
         GROUP BY year, month, t.category_id, c.name, c.color
         ORDER BY year DESC, month DESC, total DESC
    """

    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_monthly_totals(profile_id, year=None):
    """
    Monthly income and expense totals, computed from the transactions table.
    Returns rows with: year, month, income, expenses
    """
    query = """
        SELECT EXTRACT(YEAR FROM transaction_date)::int  AS year,
               EXTRACT(MONTH FROM transaction_date)::int AS month,
               SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses
          FROM transactions
         WHERE profile_id = %s
    """
    params = [profile_id]

    if year:
        query += " AND EXTRACT(YEAR FROM transaction_date) = %s"
        params.append(int(year))

    query += """
         GROUP BY year, month
         ORDER BY year DESC, month DESC
    """

    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()
