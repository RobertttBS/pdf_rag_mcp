@echo off
REM Start MCP Client for Cursor
REM Configure RAG server connection below

REM === Configuration ===
set RAG_SERVER_LIST=10.8.108.72:9527,10.8.108.23:9527,10.8.108.68:9527,localhost:9527
set RAG_REQUEST_TIMEOUT=120

REM === Start MCP ===
set SCRIPT_DIR=%~dp0

REM New: Run the compiled EXE from the dist folder
REM Ensure mcp_client.exe is placed in the same folder as this script
REM Or adjust the path to "%SCRIPT_DIR%dist\mcp_client.exe"
"%SCRIPT_DIR%mcp_client.exe"