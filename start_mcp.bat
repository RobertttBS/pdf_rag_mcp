@echo off
:: 切換到這個 bat 檔所在的目錄 (確保路徑正確)
cd /d "%~dp0"

:: 呼叫 資料夾裡的 python 來執行 同一層的 execute.py
.\python_env\python.exe server.py

pause