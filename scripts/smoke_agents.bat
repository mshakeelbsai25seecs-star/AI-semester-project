@echo off
REM Short headless smoke: one seeded episode per AI agent.
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PYEXE="
if exist "%CD%\.venv\Scripts\python.exe" set "PYEXE=%CD%\.venv\Scripts\python.exe"
if not defined PYEXE (
  where python >nul 2>&1 && set "PYEXE=python"
)
if defined PYEXE goto :have_python

where py >nul 2>&1
if errorlevel 1 goto :no_python
echo [INFO] Using Windows launcher: py -3
py -3 "scripts\smoke_agents.py" %*
exit /b %ERRORLEVEL%

:have_python
"%PYEXE%" "scripts\smoke_agents.py" %*
exit /b %ERRORLEVEL%

:no_python
echo.
echo [ERROR] Python 3 not found. Activate .venv or install Python 3.10+.
exit /b 1
