"""Safely apply registered migrations to the real local database."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.db import DB_PATH, connect, current_schema_version, integrity_check


def main():
    connection = connect(DB_PATH, migrate=True)
    try:
        result = integrity_check(connection)
        if result != "ok":
            raise RuntimeError("SQLite integrity check failed.")
        version = current_schema_version(connection)
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    finally:
        connection.close()
    print(f"Database migration: {version}")
    print(f"Migration ledger entries: {count}")
    print("SQLite integrity check: ok")


if __name__ == "__main__":
    main()
