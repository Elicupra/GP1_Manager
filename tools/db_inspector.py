"""Simple SQLite inspector utility for local debugging."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect sqlite tables.")
    parser.add_argument("--db", default="data/game.db", help="Path to sqlite db file")
    parser.add_argument("--table", required=True, help="Table name to inspect")
    parser.add_argument("--limit", type=int, default=10, help="Rows to display")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(f"SELECT * FROM {args.table} LIMIT ?", (args.limit,))
        rows = cursor.fetchall()
        print(f"Rows returned: {len(rows)}")
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
