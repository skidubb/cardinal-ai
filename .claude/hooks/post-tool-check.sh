#!/usr/bin/env bash
# PostToolUse hook: after any Bash tool call that runs a protocol, verify
# that Langfuse got a span (best-effort — non-blocking).
#
# The Claude Code harness invokes hooks with tool metadata on stdin. This
# hook only cares about Bash calls whose command matches `python -m protocols.*`.

set -u

# Read stdin (tool call metadata) and pass through to caller — hooks receive
# JSON on stdin but we don't need it for this check.
input="$(cat 2>/dev/null || true)"

# If Langfuse isn't configured, nothing to check.
if [ -z "${LANGFUSE_SECRET_KEY:-}" ] || [ -z "${LANGFUSE_BASE_URL:-}" ]; then
  exit 0
fi

# Only fire for protocol invocations — quick grep over the command.
if ! echo "$input" | grep -q "python -m protocols\." 2>/dev/null; then
  exit 0
fi

# Non-blocking: post-run Langfuse span verification would happen here.
# In this container we just log so the user can see the hook fires.
echo "[post-tool-check] protocol tool call detected — Langfuse span check would fire in prod"
