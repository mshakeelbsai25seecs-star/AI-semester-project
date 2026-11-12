@echo off
REM Windows helper: run the unit test suite from the repo root.
cd /d "%~dp0"
where python >nul 2>&1 && (
  python -m pytest -q
  exit /b %ERRORLEVEL%
)
py -3 -m pytest -q
exit /b %ERRORLEVEL%
