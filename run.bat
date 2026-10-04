@echo off
cd /d "%~dp0"
echo Starting Lumina...
call venv\Scripts\activate.bat
python -u main.py
if errorlevel 1 (
  echo.
  echo Lumina exited with an error. See outputs\lumina.log
  pause
)
