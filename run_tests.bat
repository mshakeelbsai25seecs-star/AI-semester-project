@echo off
REM Windows helper: run the unit test suite from the repo root.
setlocal EnableExtensions
cd /d "%~dp0"

set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE (
  where python >nul 2>&1 && set "PYEXE=python"
)
if defined PYEXE goto :have_python

where py >nul 2>&1
if errorlevel 1 goto :no_python
echo [INFO] Using Windows launcher: py -3
py -3 -m pytest -q
exit /b %ERRORLEVEL%

:have_python
"%PYEXE%" -m pytest -q
exit /b %ERRORLEVEL%

:no_python
echo.
echo [ERROR] Python 3 not found. Activate .venv or install Python 3.10+.
exit /b 1
