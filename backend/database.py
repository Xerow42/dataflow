"""
Thin database access layer for the FastAPI backend.

Deliberately reuses pipeline.load.get_connection() so the API reads from
exactly the same DATABASE_URL / schema the pipeline writes to -- there is
only one definition of "the database" in this project.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline import load, config  # noqa: E402


def get_db():
    conn = load.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def is_sqlite() -> bool:
    return load._is_sqlite(config.DATABASE_URL)


def placeholder() -> str:
    return "?" if is_sqlite() else "%s"
