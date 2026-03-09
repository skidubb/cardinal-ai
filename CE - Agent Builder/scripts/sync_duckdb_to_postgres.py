#!/usr/bin/env python3
"""Sync DuckDB agent memory tables to Postgres for Metabase access.

Reads all 7 DuckDB tables and writes them to Postgres with a `duckdb_` prefix.
Uses truncate + reload (full refresh) strategy.

Usage:
    python scripts/sync_duckdb_to_postgres.py              # Sync all tables
    python scripts/sync_duckdb_to_postgres.py --dry-run    # Show what would be synced

Environment:
    DUCKDB_PATH     - DuckDB file (default: data/agent_memory.duckdb)
    DATABASE_URL    - Postgres URL (default: postgresql://ce:ce_local@localhost:5432/ce_platform)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

DEFAULT_DB_PATH = Path("data/agent_memory.duckdb")
DEFAULT_PG_URL = "postgresql://ce:ce_local@localhost:5432/ce_platform"

# DuckDB type -> Postgres type mapping
TYPE_MAP = {
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "VARCHAR": "TEXT",
    "TEXT": "TEXT",
    "FLOAT": "DOUBLE PRECISION",
    "DOUBLE": "DOUBLE PRECISION",
    "BOOLEAN": "BOOLEAN",
    "JSON": "JSONB",
}

TABLES = [
    "experience_logs",
    "preferences",
    "sessions",
    "messages",
    "memories",
    "debate_sessions",
    "causal_traces",
    "evaluation_runs",
]


def get_duck_conn() -> duckdb.DuckDBPyConnection:
    db_path = Path(os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH))
    if not db_path.exists():
        print(f"DuckDB not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    return duckdb.connect(str(db_path), read_only=True)


def get_pg_conn():
    pg_url = os.environ.get("DATABASE_URL", DEFAULT_PG_URL)
    return psycopg2.connect(pg_url)


def map_dtype(duck_type: str) -> str:
    """Map a DuckDB column type to Postgres."""
    upper = duck_type.upper()
    # Handle array types like FLOAT[384]
    if "[" in upper and upper.startswith("FLOAT"):
        return "DOUBLE PRECISION[]"
    for prefix, pg_type in TYPE_MAP.items():
        if upper.startswith(prefix):
            return pg_type
    return "TEXT"


def get_table_schema(duck: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    """Return [(column_name, duckdb_type), ...] for a table."""
    cols = duck.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = ? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    return cols


def sync_table(
    duck: duckdb.DuckDBPyConnection,
    pg,
    table: str,
    dry_run: bool = False,
) -> int:
    """Sync a single DuckDB table to Postgres. Returns row count."""
    pg_table = f"duckdb_{table}"
    schema = get_table_schema(duck, table)

    if not schema:
        print(f"  Skipping {table} — no schema found")
        return 0

    rows = duck.execute(f"SELECT * FROM {table}").fetchall()

    if dry_run:
        print(f"  {table} -> {pg_table}: {len(rows)} rows, {len(schema)} columns")
        return len(rows)

    cur = pg.cursor()

    # Create table if not exists
    col_defs = ", ".join(
        f'"{col_name}" {map_dtype(col_type)}' for col_name, col_type in schema
    )
    cur.execute(f"DROP TABLE IF EXISTS {pg_table}")
    cur.execute(f"CREATE TABLE {pg_table} ({col_defs})")

    if rows:
        # Convert values — stringify any non-primitive types for JSONB compat
        import json

        clean_rows = []
        for row in rows:
            clean_row = []
            for i, val in enumerate(row):
                col_type = schema[i][1].upper()
                if col_type == "JSON" and val is not None and not isinstance(val, str):
                    val = json.dumps(val, default=str)
                # Convert DuckDB fixed-size arrays to Python lists for Postgres
                if "[" in schema[i][1] and val is not None:
                    val = list(val)
                clean_row.append(val)
            clean_rows.append(tuple(clean_row))

        col_names = ", ".join(f'"{col_name}"' for col_name, _ in schema)
        template = "(" + ", ".join(["%s"] * len(schema)) + ")"
        execute_values(
            cur,
            f"INSERT INTO {pg_table} ({col_names}) VALUES %s",
            clean_rows,
            template=template,
        )

    pg.commit()
    cur.close()
    return len(rows)


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    duck = get_duck_conn()
    if dry_run:
        print("DRY RUN — showing what would be synced:\n")
        for table in TABLES:
            sync_table(duck, None, table, dry_run=True)
        duck.close()
        return

    pg = get_pg_conn()
    print("Syncing DuckDB -> Postgres (ce_platform)...\n")

    total_rows = 0
    for table in TABLES:
        count = sync_table(duck, pg, table)
        print(f"  {table} -> duckdb_{table}: {count} rows")
        total_rows += count

    duck.close()
    pg.close()
    print(f"\nDone. {len(TABLES)} tables synced, {total_rows} total rows.")


if __name__ == "__main__":
    main()
