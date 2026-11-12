@echo off
REM Windows demo entry: launch the Panda3D viewer from the repo root.
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
py -3 -c "import panda3d" >nul 2>&1
if errorlevel 1 goto :no_panda
echo Starting Subway Surfers Lite ...
py -3 -m viewer %*
exit /b %ERRORLEVEL%

:have_python
"%PYEXE%" -c "import panda3d" >nul 2>&1
if errorlevel 1 goto :no_panda
echo Starting Subway Surfers Lite ...
"%PYEXE%" -m viewer %*
exit /b %ERRORLEVEL%

:no_python
echo.
echo [ERROR] Python 3 not found.
echo From this folder run:
echo   python -m venv .venv
echo   .venv\Scripts\activate
echo   python -m pip install -r requirements.txt
echo Then double-click run_game.bat again.
exit /b 1

:no_panda
echo.
echo [ERROR] Panda3D is not installed for this Python.
if defined PYEXE echo   Interpreter: %PYEXE%
echo Install deps:
echo   python -m pip install -r requirements.txt
echo.
echo If the game window still fails to open after install:
echo   - Update GPU drivers / try another display
echo   - Close other full-screen apps that grab the GPU
echo   - Core + agents still work headless: run_tests.bat
exit /b 1
