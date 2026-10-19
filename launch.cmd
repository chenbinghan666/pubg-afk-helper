@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please follow README.md to install the Python environment first.
  pause
  exit /b 1
)
echo Starting with the saved templates. No capture is required.
echo Switch to PUBG. F8: pause. F7: resume. F9: stop.
echo A topmost status panel will show the current step.
".venv\Scripts\python.exe" bot.py --live
pause
