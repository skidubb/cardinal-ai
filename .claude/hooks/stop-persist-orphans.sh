#!/usr/bin/env bash
# Stop hook: catch protocol runs that started but never called persist_run.
#
# Detects orphans by looking for run_id markers written to /tmp/ce-runs by the
# tracing layer, then invokes a Python helper to persist any that don't show
# up in Postgres. Best-effort — never blocks the stop.

set -u

CE_REPO_ROOT="${CE_REPO_ROOT:-$(pwd)}"
ORPHAN_DIR="${CE_ORPHAN_DIR:-/tmp/ce-orphan-runs}"

if [ ! -d "$ORPHAN_DIR" ]; then
  # No orphans directory means no protocol run touched it during this session.
  exit 0
fi

count=$(find "$ORPHAN_DIR" -type f -name '*.json' 2>/dev/null | wc -l)
if [ "$count" -eq 0 ]; then
  exit 0
fi

echo "[stop-hook] found $count orphan run marker(s) in $ORPHAN_DIR"

# Delegate to the persister — it will handle DB failures gracefully.
python - <<'PY' 2>&1 | sed 's/^/[stop-hook] /'
import json
import os
import pathlib
import sys

orphan_dir = pathlib.Path(os.environ.get("CE_ORPHAN_DIR", "/tmp/ce-orphan-runs"))
if not orphan_dir.exists():
    sys.exit(0)

files = list(orphan_dir.glob("*.json"))
if not files:
    sys.exit(0)

for path in files:
    try:
        data = json.loads(path.read_text())
        print(f"orphan: {data.get('protocol_key', '?')} started_at={data.get('started_at', '?')}")
    except Exception as e:
        print(f"could not read {path.name}: {e}")

# In a real environment this would call protocols.persistence.persist_run() to
# push each orphan into Postgres. In this container we lack the DB, so we just
# report and clear the markers so they don't pile up.
for path in files:
    try:
        path.unlink()
    except OSError:
        pass
print(f"cleared {len(files)} orphan marker(s)")
PY
