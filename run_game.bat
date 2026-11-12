@echo off
REM Windows entry: launch the Panda3D viewer from the repo root.
cd /d "%~dp0"

where python >nul 2>&1 && (
  python -m viewer %*
  exit /b %ERRORLEVEL%
)
py -3 -m viewer %*
exit /b %ERRORLEVEL%
