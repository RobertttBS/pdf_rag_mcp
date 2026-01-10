#!/bin/bash
# Start RAG Server
# Usage: ./start_server.sh [host] [port]

HOST=${1:-0.0.0.0}
PORT=${2:-8000}

# Navigate to project root (one level up from server/)
cd "$(dirname "$0")/.."

echo "Starting RAG Server on $HOST:$PORT..."

# Use standalone Python from python_env
./python_env/bin/python -m uvicorn server.rag_server:app --host "$HOST" --port "$PORT"
