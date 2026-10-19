@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 goto python
py -3 -m venv .venv
goto dependencies
:python
python --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 or newer from python.org with Add Python to PATH enabled.
  pause
  exit /b 1
)
python -m venv .venv
:dependencies
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open launch.cmd to use the helper.
pause
exit /b 0
:failed
echo Setup failed. Check the error above.
pause
exit /b 1
