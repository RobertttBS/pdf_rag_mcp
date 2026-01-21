@echo off
setlocal

:: Configuration variables
set "TARGET_PYTHON=.\python_env\python.exe"
set "PIP_INSTALLER=.\get-pip.py"
set "REQ_FILE=.\client\requirements.txt"

:: Step 1: Install pip
echo [1/2] Installing pip...
"%TARGET_PYTHON%" "%PIP_INSTALLER%" --no-warn-script-location

:: Step 2: Install dependencies from requirements.txt
:: We use '-m pip' to ensure we use the pip module attached to this specific python executable
echo [2/2] Installing client requirements...
"%TARGET_PYTHON%" -m pip install -r "%REQ_FILE%"

echo.
echo Environment setup complete.
pause