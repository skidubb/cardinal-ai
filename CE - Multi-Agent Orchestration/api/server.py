"""FastAPI application for the Cardinal Element Orchestrator UI."""

from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from ce_shared.env import find_and_load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.database import create_db_and_tables
from api.routers import agents, auth as auth_router, integrations, knowledge, pipelines, protocols, reports, router as adaptive_router, runs, teams, webhooks_clerk
from api.routers.agents import tools_router

find_and_load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    # Verify production agents are importable
    try:
        from protocols.server_agent import ServerAgent  # noqa: F401
        logger.info("Production agent provider verified: ServerAgent (direct API + tools)")
    except ImportError as exc:
        raise RuntimeError(
            f"FATAL: ServerAgent import failed: {exc}\n"
            "The API requires protocols/server_agent.py and anthropic SDK."
        ) from exc

    yield


app = FastAPI(title="CE Orchestrator API", version="0.1.0", lifespan=lifespan)

_default_origins = ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"]
_cors_env = os.getenv("CORS_ORIGINS", "")
_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# ── Simple API key auth (skippable in dev) ────────────────────────────────────

API_KEY = os.getenv("API_KEY", "")
SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() in ("1", "true", "yes")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if SKIP_AUTH or request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path == "/api/health" or request.url.path.startswith("/share/"):
        return await call_next(request)
    key = request.headers.get("X-API-Key", "")
    if not API_KEY:
        return JSONResponse(status_code=500, content={"detail": "API_KEY not configured but auth is enabled. Set API_KEY or SKIP_AUTH=true."})
    if not secrets.compare_digest(key, API_KEY):
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(webhooks_clerk.router)
app.include_router(tools_router)
app.include_router(agents.router)
app.include_router(integrations.router)
app.include_router(knowledge.router)
app.include_router(protocols.router)
app.include_router(teams.router)
app.include_router(pipelines.router)
app.include_router(reports.router)
app.include_router(runs.router)
app.include_router(adaptive_router.router)


@app.get("/api/health")
def health():
    from api.database import DATABASE_URL
    db_type = "postgres" if "postgresql" in DATABASE_URL else "sqlite"
    return {"status": "ok", "db": db_type}


# ── Serve built frontend (production) ─────────────────────────────────────────

_ui_dist = Path(__file__).resolve().parent.parent / "ui" / "dist"
if _ui_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_ui_dist / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        file = (_ui_dist / full_path).resolve()
        if not str(file).startswith(str(_ui_dist.resolve())):
            return FileResponse(_ui_dist / "index.html")
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_ui_dist / "index.html")
