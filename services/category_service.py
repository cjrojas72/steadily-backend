import uuid

from db import get_cursor


def get_categories(profile_id):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM categories WHERE profile_id = %s ORDER BY name",
            (profile_id,),
        )
        return cur.fetchall()


def get_category(profile_id, category_id):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM categories WHERE id = %s AND profile_id = %s",
            (category_id, profile_id),
        )
        return cur.fetchone()


def create_category(profile_id, data):
    cat_id = str(uuid.uuid4())
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO categories (id, profile_id, name, color, icon, is_default)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (cat_id, profile_id, data["name"], data.get("color"), data.get("icon"), data.get("is_default", False)),
        )
        return cur.fetchone()


def update_category(profile_id, category_id, data):
    if not data:
        return get_category(profile_id, category_id)

    set_parts = []
    params = []
    for key, value in data.items():
        set_parts.append(f"{key} = %s")
        params.append(value)
    params.extend([category_id, profile_id])

    with get_cursor(commit=True) as cur:
        cur.execute(
            f"UPDATE categories SET {', '.join(set_parts)} WHERE id = %s AND profile_id = %s RETURNING *",
            params,
        )
        return cur.fetchone()


def delete_category(profile_id, category_id):
    """Returns (success, error_message)."""
    with get_cursor(commit=True) as cur:
        # Check exists
        cur.execute(
            "SELECT is_default FROM categories WHERE id = %s AND profile_id = %s",
            (category_id, profile_id),
        )
        cat = cur.fetchone()
        if not cat:
            return False, "Category not found"

        if cat["is_default"]:
            return False, "Cannot delete a default category"

        # Check for transactions
        cur.execute(
            "SELECT COUNT(*) AS count FROM transactions WHERE category_id = %s AND profile_id = %s",
            (category_id, profile_id),
        )
        if cur.fetchone()["count"] > 0:
            return False, "Cannot delete category with existing transactions"

        cur.execute(
            "DELETE FROM categories WHERE id = %s AND profile_id = %s",
            (category_id, profile_id),
        )
        return True, None
