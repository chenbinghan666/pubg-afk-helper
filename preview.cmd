@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run install.cmd first.
  pause
  exit /b 1
)
echo Detection preview only. No mouse clicks or key presses will be sent.
echo Switch to PUBG. F8: pause. F7: resume. F9: stop.
".venv\Scripts\python.exe" bot.py
pause
