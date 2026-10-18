@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup-KAIRO.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\install_existing.py
pause
