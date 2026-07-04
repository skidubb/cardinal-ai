# Coordination Lab — Protocol Implementations
#
# Preflight intentionally NOT run at package import. CLI entry points
# (`protocols/p*/run.py`) call `print_preflight()` explicitly. Running it here
# would fire on every server/router/test import — and in `ENV=production` the
# strict check calls `sys.exit(2)` on any FAIL, which can kill Railway startup
# before `/api/health` ever responds.
