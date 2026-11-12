@echo off
cd /d "%~dp0\.."
where python >nul 2>&1 && (
  python scripts\smoke_agents.py
  exit /b %ERRORLEVEL%
)
py -3 scripts\smoke_agents.py
exit /b %ERRORLEVEL%
