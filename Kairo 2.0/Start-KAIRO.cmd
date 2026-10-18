@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup-KAIRO.cmd first.
  pause
  exit /b 1
)
set "PYTHONPATH=%~dp0src"
start "" ".venv\Scripts\pythonw.exe" -m kairo native --ui "%~dp0ui\out"
