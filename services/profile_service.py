from db import get_cursor


PROFILE_FIELDS = (
    "id",
    "email",
    "display_name",
    "first_name",
    "last_name",
    "phone1",
    "currency",
    "created_at",
)


def _has_column(cur, table, column):
    cur.execute(
        """SELECT 1 FROM information_schema.columns
           WHERE table_name = %s AND column_name = %s""",
        (table, column),
    )
    return cur.fetchone() is not None


def _serialize(profile):
    if not profile:
        return None
    created = profile.get("created_at")
    return {
        "id": str(profile["id"]) if profile.get("id") else None,
        "email": profile.get("email"),
        "display_name": profile.get("display_name"),
        "first_name": profile.get("first_name"),
        "last_name": profile.get("last_name"),
        "phone1": profile.get("phone1"),
        "currency": profile.get("currency"),
        "created_at": created.isoformat() if created else None,
    }


def get_profile(profile_id):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM profiles WHERE id = %s", (profile_id,))
        row = cur.fetchone()
    return _serialize(row)


# Fields that callers may modify via the update endpoint.
UPDATABLE_FIELDS = ("first_name", "last_name", "phone1", "display_name")


def update_profile(profile_id, data):
    """
    Update one or more editable profile fields. Silently ignores fields that
    don't exist on the profiles table (e.g. if a migration hasn't been run).
    Returns the full serialized profile after update.
    """
    if not data:
        return get_profile(profile_id)

    with get_cursor(commit=True) as cur:
        set_parts = []
        params = []
        for key in UPDATABLE_FIELDS:
            if key in data and _has_column(cur, "profiles", key):
                set_parts.append(f"{key} = %s")
                params.append(data[key])

        if not set_parts:
            cur.execute("SELECT * FROM profiles WHERE id = %s", (profile_id,))
            return _serialize(cur.fetchone())

        params.append(profile_id)
        cur.execute(
            f"UPDATE profiles SET {', '.join(set_parts)} WHERE id = %s RETURNING *",
            params,
        )
        return _serialize(cur.fetchone())
