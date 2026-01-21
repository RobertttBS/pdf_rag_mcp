@echo off
REM Start RAG Server
REM Usage: start_server.bat [host] [port]

REM === Default Configuration ===
set HOST=%1
set PORT=%2
if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=9527

REM === Change to project root ===
cd /d "%~dp0\.."
echo Working directory: %CD%

REM === Check Python exists ===
if not exist ".\python_env\python.exe" (
    echo [ERROR] Python not found at .\python_env\python.exe
    pause
    exit /b 1
)

REM === Check server script exists ===
if not exist ".\server\rag_server.py" (
    echo [ERROR] Server script not found at .\server\rag_server.py
    pause
    exit /b 1
)

echo.
echo Starting RAG Server on %HOST%:%PORT%...
echo Press Ctrl+C to stop the server gracefully.
echo.

REM Run server directly via Python script for better signal handling
.\python_env\python.exe .\server\rag_server.py --host %HOST% --port %PORT%

echo.
echo Server stopped (exit code: %ERRORLEVEL%).
pause