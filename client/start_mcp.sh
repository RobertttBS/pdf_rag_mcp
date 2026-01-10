#!/bin/bash
# Start MCP Client for Cursor
# Configure RAG server connection below

# === Configuration ===
export RAG_SERVER_HOST=${RAG_SERVER_HOST:-localhost}
export RAG_SERVER_PORT=${RAG_SERVER_PORT:-8000}
export RAG_REQUEST_TIMEOUT=${RAG_REQUEST_TIMEOUT:-120}

# === Start MCP ===
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Use standalone Python from python_env (in project root)
"$PROJECT_ROOT/python_env/bin/python" "$SCRIPT_DIR/mcp_client.py"
