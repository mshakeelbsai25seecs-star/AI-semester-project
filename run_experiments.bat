@echo off
REM Proposal E1–E4 evaluation suite.
REM   run_experiments.bat              full presets (all E1–E4)
REM   run_experiments.bat smoke        short CI / smoke mode
REM   run_experiments.bat --smoke -e e1
REM Extra args are forwarded to ``python -m experiments``.

setlocal
cd /d "%~dp0"

if /I "%~1"=="smoke" (
  shift /1
  python -m experiments --smoke %*
  exit /b %ERRORLEVEL%
)

if "%~1"=="" (
  python -m experiments --mode full
  exit /b %ERRORLEVEL%
)

python -m experiments %*
exit /b %ERRORLEVEL%
