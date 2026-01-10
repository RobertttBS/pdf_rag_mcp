@echo off
REM Start MCP Client for Cursor
REM Configure RAG server connection below

REM === Configuration ===
set RAG_SERVER_HOST=localhost
set RAG_SERVER_PORT=8000
set RAG_REQUEST_TIMEOUT=120

REM === Start MCP ===
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Use standalone Python from python_env (in project root)
"%PROJECT_ROOT%\python_env\python.exe" "%SCRIPT_DIR%mcp_client.py"
