"""Explicitly rebuild Lab 4 embeddings in batches for a selected database."""

import argparse
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-path",
        required=True,
        help="Explicit SQLite database path; the governed academic database is not allowed.",
    )
    parser.add_argument("--course-id", help="Limit indexing to one course.")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    database_path = Path(args.database_path).expanduser().resolve()
    protected_database = (PROJECT_ROOT / "app" / "data" / "governed_academic.db").resolve()
    protected_alias = (
        database_path.exists()
        and protected_database.exists()
        and os.path.samefile(database_path, protected_database)
    )
    if database_path == protected_database or protected_alias:
        parser.error("Refusing to initialize or index the governed academic database.")

    os.environ["DATABASE_PATH"] = str(database_path)
    from app.data.db import init_database
    from app.labs.lab4.knowledge_store import long_term_store

    init_database()
    results = long_term_store.rebuild_embeddings(
        course_id=args.course_id,
        batch_size=args.batch_size,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
