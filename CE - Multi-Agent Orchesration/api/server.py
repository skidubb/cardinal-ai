"""FastAPI application for the Cardinal Element Orchestrator UI."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.database import create_db_and_tables
from api.routers import agents, pipelines, protocols, runs, teams
from api.routers.agents import tools_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="CE Orchestrator API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    key = request.headers.get("X-API-Key", "")
    if not API_KEY or key != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(tools_router)
app.include_router(agents.router)
app.include_router(protocols.router)
app.include_router(teams.router)
app.include_router(pipelines.router)
app.include_router(runs.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
