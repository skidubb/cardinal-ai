"""Backfill Run.tenant_slug values to their canonical form.

Clerk auto-appends a long numeric ID to org slugs when the base slug is
already taken (e.g. ``cardinal-element-1776752029963075226``). Runs created
before the auth layer started canonicalizing these values retain the
suffixed form, which makes them invisible to the (now-canonical) session
slug -- so the user can't see, delete, or manage them.

This script scans the ``run`` table and updates any row whose stored
``tenant_slug`` differs from its canonical form.

Usage::

    # Preview (default)
    python scripts/backfill_canonical_tenant_slugs.py

    # Apply changes
    python scripts/backfill_canonical_tenant_slugs.py --apply

Safe to re-run (idempotent).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlmodel import Session, select

from api.database import engine
from api.middleware.clerk_auth import _canonicalize_slug
from api.models import Run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit updates. Without this flag, only previews.",
    )
    args = parser.parse_args()

    before_counts: Counter[str] = Counter()
    after_counts: Counter[str] = Counter()
    updates: list[tuple[int, str, str]] = []

    with Session(engine) as session:
        runs = session.exec(select(Run)).all()
        for r in runs:
            old = r.tenant_slug
            new = _canonicalize_slug(old)
            before_counts[old] += 1
            after_counts[new] += 1
            if old != new:
                updates.append((r.id or -1, old, new))
                if args.apply:
                    r.tenant_slug = new
                    session.add(r)

        print(f"Scanned {len(runs)} runs.")
        print(f"Found {len(updates)} runs with non-canonical tenant_slug.\n")

        if updates:
            print("Non-canonical slugs in use (before):")
            for slug, count in before_counts.most_common():
                canon = _canonicalize_slug(slug)
                if canon != slug:
                    print(f"  {slug!r:<60} -> {canon!r}  ({count} runs)")
            print()
            print("Canonical slug distribution (after):")
            for slug, count in after_counts.most_common():
                print(f"  {slug!r:<60}  ({count} runs)")
            print()

        if args.apply and updates:
            session.commit()
            print(f"Committed updates for {len(updates)} runs.")
        elif updates:
            print("Dry run -- no changes committed. Re-run with --apply to commit.")
        else:
            print("Nothing to do -- all tenant_slugs already canonical.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
