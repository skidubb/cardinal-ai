# ============================================================
# Stage 1: Build the React UI
# ============================================================
FROM node:22-slim AS ui-build

WORKDIR /build/ui
COPY ["CE - Multi-Agent Orchestration/ui/package.json", "CE - Multi-Agent Orchestration/ui/package-lock.json*", "./"]
RUN npm ci --ignore-scripts

COPY ["CE - Multi-Agent Orchestration/ui/", "./"]
RUN npm run build


# ============================================================
# Stage 2: Python runtime
# ============================================================
FROM python:3.11-slim AS runtime

# System deps for grpc (pinecone), postgres (psycopg/asyncpg), and WeasyPrint (PDF reports)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-xlib-2.0-0 libffi-dev libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Install local packages first (they change less often) ---

# ce-shared
COPY ce-shared/ /app/ce-shared/
RUN pip install --no-cache-dir /app/ce-shared

# ce-db (strip file:// ref to ce-shared — already installed above)
COPY ce-db/ /app/ce-db/
RUN sed -i '/ce-shared @ file:/d' /app/ce-db/pyproject.toml \
    && pip install --no-cache-dir /app/ce-db

# Agent Builder (strip file:// ref to ce-shared — already installed above)
COPY ["CE - Agent Builder/", "/app/CE-Agent-Builder/"]
RUN sed -i '/ce-shared @ file:/d' /app/CE-Agent-Builder/pyproject.toml \
    && pip install --no-cache-dir -e "/app/CE-Agent-Builder[sdk]"

# --- Orchestration project ---

COPY ["CE - Multi-Agent Orchestration/requirements.txt", "/app/orchestration-requirements.txt"]
COPY ["CE - Multi-Agent Orchestration/api/requirements.txt", "/app/api-requirements.txt"]

# Rewrite file:// refs to absolute paths inside the container
RUN sed -i 's|ce-db @ file:../ce-db|# ce-db (already installed)|' /app/orchestration-requirements.txt \
    && sed -i 's|ce-shared @ file:../ce-shared|# ce-shared (already installed)|' /app/orchestration-requirements.txt

RUN pip install --no-cache-dir -r /app/orchestration-requirements.txt -r /app/api-requirements.txt

# Postgres driver for Railway (SQLModel uses SQLAlchemy under the hood)
RUN pip install --no-cache-dir psycopg2-binary

# Copy orchestration source
COPY ["CE - Multi-Agent Orchestration/", "/app/orchestration/"]

# Copy built UI into the place FastAPI expects
COPY --from=ui-build /build/ui/dist /app/orchestration/ui/dist

# Remove any .env files that leaked past .dockerignore — they contain
# local dev credentials (POSTGRES_HOST=localhost) that poison DATABASE_URL
RUN find /app -name ".env" -o -name ".env.*" | xargs rm -f 2>/dev/null; true

# Point Python at the Agent Builder source for imports
ENV CE_AGENT_BUILDER_PATH=/app/CE-Agent-Builder/src
ENV PYTHONPATH=/app/orchestration

WORKDIR /app/orchestration

EXPOSE ${PORT:-8000}

CMD sh -c "uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}"
