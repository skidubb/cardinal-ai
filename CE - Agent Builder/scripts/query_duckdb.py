#!/usr/bin/env python3
"""CLI tool for exploring the C-Suite DuckDB agent memory database.

Usage:
    python scripts/query_duckdb.py --tables              # List all tables + schemas
    python scripts/query_duckdb.py --stats               # Row counts per table
    python scripts/query_duckdb.py "SELECT * FROM ..."   # Run a SQL query
    python scripts/query_duckdb.py                       # Interactive SQL shell
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

DEFAULT_DB_PATH = Path("data/agent_memory.duckdb")


def get_db_path() -> Path:
    env_path = os.environ.get("DUCKDB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def show_tables(conn: duckdb.DuckDBPyConnection) -> None:
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    ).fetchall()

    if not tables:
        print("No tables found.")
        return

    for (table_name,) in tables:
        print(f"\n{'=' * 60}")
        print(f"  {table_name}")
        print(f"{'=' * 60}")
        cols = conn.execute(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table_name],
        ).fetchall()
        for col_name, dtype, nullable, default in cols:
            parts = [f"  {col_name:<30} {dtype:<15}"]
            if nullable == "NO":
                parts.append("NOT NULL")
            if default:
                parts.append(f"DEFAULT {default}")
            print("".join(parts))


def show_stats(conn: duckdb.DuckDBPyConnection) -> None:
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    ).fetchall()

    if not tables:
        print("No tables found.")
        return

    print(f"\n{'Table':<30} {'Rows':>10}")
    print("-" * 42)
    for (table_name,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"{table_name:<30} {count:>10}")
    print()


def run_query(conn: duckdb.DuckDBPyConnection, sql: str) -> None:
    try:
        result = conn.execute(sql)
        rows = result.fetchall()
        if not rows:
            print("(0 rows)")
            return

        columns = [desc[0] for desc in result.description]
        # Calculate column widths
        widths = [len(c) for c in columns]
        str_rows = []
        for row in rows:
            str_row = [str(v) if v is not None else "NULL" for v in row]
            # Truncate long values for display
            str_row = [v[:80] + "..." if len(v) > 80 else v for v in str_row]
            str_rows.append(str_row)
            for i, v in enumerate(str_row):
                widths[i] = max(widths[i], len(v))

        # Print header
        header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
        print(header)
        print("-+-".join("-" * w for w in widths))

        # Print rows
        for str_row in str_rows:
            print(" | ".join(v.ljust(widths[i]) for i, v in enumerate(str_row)))

        print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def interactive(conn: duckdb.DuckDBPyConnection) -> None:
    print("DuckDB Interactive Shell (type 'quit' or Ctrl+D to exit)")
    print(f"Database: {get_db_path()}")
    print("Hint: try '.tables' for table list, '.stats' for row counts\n")

    while True:
        try:
            sql = input("duckdb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not sql:
            continue
        if sql.lower() in ("quit", "exit", "\\q"):
            break
        if sql == ".tables":
            show_tables(conn)
            continue
        if sql == ".stats":
            show_stats(conn)
            continue

        run_query(conn, sql)


def main() -> None:
    db_path = get_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        print("Set DUCKDB_PATH or run from the CE - Agent Builder directory.", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect(str(db_path), read_only=True)

    try:
        if "--tables" in sys.argv:
            show_tables(conn)
        elif "--stats" in sys.argv:
            show_stats(conn)
        elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            run_query(conn, sys.argv[1])
        else:
            interactive(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
