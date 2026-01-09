@echo off
:: Switch to the directory where this bat file is located
cd /d "%~dp0"

:: Run server.py using the local python environment
.\python_env\python.exe server.py
