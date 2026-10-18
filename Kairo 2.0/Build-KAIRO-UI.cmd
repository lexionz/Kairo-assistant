@echo off
setlocal
cd /d "%~dp0ui"
if not exist "node_modules\next\dist\bin\next" (
  echo Frontend build dependencies are missing.
  echo After approving the local installation, run: npm ci --ignore-scripts --no-audit --no-fund
  exit /b 1
)
call npm run build
if errorlevel 1 exit /b 1
echo KAIRO UI rebuilt in ui\out. Restart Start-KAIRO.cmd to load it.
endlocal
