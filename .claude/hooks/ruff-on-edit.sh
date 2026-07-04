#!/bin/bash
# PostToolUse hook: auto-fix + format any edited Python file with ruff.
# Receives the tool-use payload as JSON on stdin. Silent no-op when the edit
# isn't a .py file or ruff isn't available. Never blocks the edit (always exit 0).

FILE_PATH=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

[[ "$FILE_PATH" == *.py ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

# Prefer a ruff on PATH, then any project venv that has one
RUFF="$(command -v ruff)"
if [[ -z "$RUFF" ]]; then
  for v in "$CLAUDE_PROJECT_DIR/CE - Agent Builder/venv/bin/ruff" \
           "$CLAUDE_PROJECT_DIR/CE - Multi-Agent Orchestration/venv/bin/ruff"; do
    [[ -x "$v" ]] && RUFF="$v" && break
  done
fi
[[ -z "$RUFF" ]] && exit 0

"$RUFF" check --fix --quiet "$FILE_PATH" 2>/dev/null
"$RUFF" format --quiet "$FILE_PATH" 2>/dev/null
exit 0
