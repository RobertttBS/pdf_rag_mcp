@echo off
REM Start RAG Server
REM Usage: start_server.bat [host] [port]

REM === Default Configuration ===
set HOST=%1
set PORT=%2
if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=8000

REM === Start Server ===
cd /d "%~dp0\.."

echo Starting RAG Server on %HOST%:%PORT%...

REM Use standalone Python from python_env
.\python_env\python.exe -m uvicorn server.rag_server:app --host %HOST% --port %PORT%
