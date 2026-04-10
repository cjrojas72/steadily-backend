import os
from contextlib import contextmanager

# AWS Lambda runs on Linux. If psycopg2 was packaged from a Windows wheel,
# its generated __init__.py may call os.add_dll_directory(), which is not
# available on Linux. Provide a no-op fallback so the Lambda runtime can import
# psycopg2 when the shared libs are already present in the package.
if not hasattr(os, "add_dll_directory"):
    def add_dll_directory(path):
        return None

    os.add_dll_directory = add_dll_directory

import psycopg2
from psycopg2.extras import RealDictCursor

_conn = None


def get_conn():
    """Return a reusable connection (persists across warm Lambda invocations)."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            os.environ.get("DATABASE_URL", ""),
            cursor_factory=RealDictCursor,
        )
        _conn.autocommit = False
    return _conn


@contextmanager
def get_cursor(commit=False):
    """Context manager that yields a cursor. Commits or rolls back on exit."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
