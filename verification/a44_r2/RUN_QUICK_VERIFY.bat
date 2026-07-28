@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_QUICK_VERIFY.ps1"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" pause
exit /b %RC%
