#!/usr/bin/env bash
# Start both FastAPI backend and Vite frontend dev servers
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT

# Backend
echo "Starting FastAPI backend on :8000..."
cd "$DIR"
source venv/bin/activate
uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Frontend
echo "Starting Vite frontend on :5173..."
cd "$DIR/ui"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000/api/health"
echo "Frontend: http://localhost:5173"
echo ""

wait
