# Stack Research

**Domain:** Full-stack integration for multi-agent AI platform
**Researched:** 2026-03-10
**Confidence:** MEDIUM-HIGH

## Recommended Stack

### Core Technologies (Already Established — Keep)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| FastAPI | >=0.104.0 | REST API + SSE streaming | Existing |
| React 19 | ^19.2.0 | Frontend UI framework | Existing |
| PostgreSQL 16 | 16 | Primary data store | Existing |
| SQLAlchemy (async) | >=2.0 | ORM with asyncpg driver | Existing |
| Vite 7 | ^7.3.1 | Frontend build tooling | Existing |
| Tailwind CSS 4 | ^4.2.1 | Styling | Existing |
| Zustand | ^5.0.11 | State management | Existing |

### New Libraries Needed

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| `PyJWT` | >=2.11.0 | JWT token generation/validation | Official FastAPI docs recommend; `python-jose` abandoned 2021, incompatible with Python 3.13 |
| `pwdlib[argon2]` | >=0.3.0 | Password hashing | Modern replacement for passlib; argon2 is current OWASP recommendation |
| `WeasyPrint` | >=68.1 | PDF report generation from HTML/CSS | Takes Jinja2 HTML templates directly, no Chromium dependency; ideal for report-style output |
| `Jinja2` | >=3.1.0 | HTML templating for PDF reports | Used by WeasyPrint to render structured report templates |
| `@microsoft/fetch-event-source` | 2.0.1 | SSE client for React (supports POST) | Native `EventSource` only supports GET; protocol runs need POST body with config |
| `sse-starlette` | >=2.0.0 | Server-Sent Events for FastAPI | Bump from current >=1.8.0; v2.0+ has rewritten async core (current release 3.3.2) |

### Development / Deployment Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Railway | Cloud deployment | Hobby plan ~$15-25/mo total; native FastAPI+React+Postgres template; managed Postgres 16 |
| Docker multi-stage | Production builds | Separate build/runtime stages; Nginx for static React assets |
| Makefile | One-command startup | `make dev` for local, `make deploy` for cloud |

## Installation

```bash
# Backend auth + PDF (add to API requirements.txt)
pip install PyJWT>=2.11.0 pwdlib[argon2]>=0.3.0 WeasyPrint>=68.1 Jinja2>=3.1.0

# Bump SSE library
pip install sse-starlette>=2.0.0

# Frontend SSE client
cd "CE - Multi-Agent Orchestration/ui"
npm install @microsoft/fetch-event-source@2.0.1
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Railway | Render | If you need background workers with separate scaling |
| Railway | Fly.io | If you need edge deployment or multi-region |
| Railway | AWS (ECS/Fargate) | If you need enterprise compliance or massive scale |
| WeasyPrint | Playwright PDF | If you need pixel-perfect browser rendering; much heavier dependency |
| WeasyPrint | ReportLab | If you need programmatic PDF construction (charts, precise layout); more complex API |
| PyJWT | python-jose | Never — abandoned 2021, breaks on Python 3.13 |
| `@microsoft/fetch-event-source` | Native EventSource | Only if you switch to GET-based SSE with pre-persisted run configs |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-jose` | Abandoned 2021, incompatible with Python 3.13 (CI runs 3.13) | `PyJWT>=2.11.0` |
| `passlib` | Deprecated; last release 2020 | `pwdlib[argon2]>=0.3.0` |
| `wkhtmltopdf` | Deprecated, unmaintained, Qt WebKit dependency | `WeasyPrint>=68.1` |
| Native `EventSource` API | Cannot send POST body; protocol runs need config payload | `@microsoft/fetch-event-source` |
| `sse-starlette<2.0` | Old async core | `sse-starlette>=2.0.0` |
| Heroku | Expensive for this use case; no managed Postgres at hobby tier | Railway |

## Stack Patterns

**For PDF report generation:**
- Jinja2 HTML templates with CSS styling → WeasyPrint renders to PDF
- Same templates serve browser-viewable HTML reports (dual use)
- Keep templates in a shared `report_templates/` directory

**For SSE streaming:**
- Backend: `sse-starlette` with `EventSourceResponse` wrapping async generator
- Frontend: `@microsoft/fetch-event-source` with POST body containing run config
- Fallback: if SSE connection drops, poll `/api/runs/{id}` for final result

**For Docker production:**
- Multi-stage Python build: deps in builder, copy to slim runtime
- Nginx serves React static build, proxies `/api` to FastAPI
- WeasyPrint needs system packages: `libpango-1.0-0 libharfbuzz0b libffi-dev libgdk-pixbuf-2.0-0`

**For auth:**
- Simple `users` table with email + argon2 password hash
- JWT access tokens (short-lived) + refresh tokens
- React auth context wrapping protected routes
- FastAPI `Depends(get_current_user)` on protected endpoints

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| PyJWT 2.11+ | Python 3.13 | Verified compatible (python-jose is NOT) |
| WeasyPrint 68.1+ | Python 3.11-3.13 | Requires system packages (Pango, HarfBuzz) in Docker |
| sse-starlette 2.0+ | FastAPI 0.104+ | Async core rewritten; backward compatible API |
| @microsoft/fetch-event-source 2.0.1 | React 19 | Stable; minimally maintained but no alternatives for POST+SSE |

## Open Questions

- WeasyPrint system deps need verification in Railway's Docker build environment
- `@microsoft/fetch-event-source` is minimally maintained (last commit ~2 years ago); if issues arise, fallback is GET-based SSE with run config persisted first via POST

## Sources

- FastAPI security docs (2025) — PyJWT + pwdlib recommendation
- WeasyPrint v68.1 on PyPI — current stable release
- Railway docs — pricing and capabilities
- sse-starlette PyPI — v3.3.2 current release

---
*Stack research for: multi-agent AI platform full-stack integration*
*Researched: 2026-03-10*
