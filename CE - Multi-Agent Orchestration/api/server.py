"""FastAPI application for the Cardinal Element Orchestrator UI."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from ce_shared.env import find_and_load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.database import create_db_and_tables
from api.routers import agents, integrations, knowledge, pipelines, protocols, reports, runs, teams
from api.routers.agents import tools_router

find_and_load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    # Verify production agents are importable (AGNT-02)
    try:
        from protocols.agent_provider import _resolve_agent_builder_src
        agent_src = _resolve_agent_builder_src()
        if str(agent_src) not in sys.path:
            sys.path.insert(0, str(agent_src))
        from csuite.agents.sdk_agent import SdkAgent  # noqa: F401
        logger.info("Production agent provider verified: SdkAgent importable from %s", agent_src)
    except ImportError as exc:
        raise RuntimeError(
            f"FATAL: Production agent import failed: {exc}\n"
            "The API requires production-mode agents (SdkAgent from Agent Builder).\n"
            "Fix options:\n"
            "  1. cd 'CE - Agent Builder' && pip install -e '.[sdk]'\n"
            "  2. Set CE_AGENT_BUILDER_PATH=/absolute/path/to/CE - Agent Builder/src\n"
            "Server cannot start without production agents."
        ) from exc

    yield


app = FastAPI(title="CE Orchestrator API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple API key auth (skippable in dev) ────────────────────────────────────

API_KEY = os.getenv("API_KEY", "")
SKIP_AUTH = os.getenv("SKIP_AUTH", "true").lower() in ("1", "true", "yes")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if SKIP_AUTH or request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path.startswith("/share/"):
        return await call_next(request)
    key = request.headers.get("X-API-Key", "")
    if not API_KEY:
        return JSONResponse(status_code=500, content={"detail": "API_KEY not configured but auth is enabled. Set API_KEY or SKIP_AUTH=true."})
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(tools_router)
app.include_router(agents.router)
app.include_router(integrations.router)
app.include_router(knowledge.router)
app.include_router(protocols.router)
app.include_router(teams.router)
app.include_router(pipelines.router)
app.include_router(reports.router)
app.include_router(runs.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Serve built frontend (production) ─────────────────────────────────────────

_ui_dist = Path(__file__).resolve().parent.parent / "ui" / "dist"
if _ui_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_ui_dist / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        file = _ui_dist / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_ui_dist / "index.html")
