@echo off
REM Start MCP Client for Cursor
REM Configure RAG server connection below

REM === Configuration ===
REM Server list format: host1:port1,host2:port2,...
REM Client will try each server in order until one responds
set RAG_SERVER_LIST=10.8.108.72:9527,10.8.108.23:9527,localhost:9527
set RAG_REQUEST_TIMEOUT=120

REM === Start MCP ===
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Use standalone Python from python_env (in project root)
"%PROJECT_ROOT%\python_env\python.exe" "%SCRIPT_DIR%mcp_client.py"
