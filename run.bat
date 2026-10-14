@echo off
rem genome-kit launcher for Windows: hands over to run.ps1, which checks WSL (with time limits, so it never hangs
rem silently), offers to install or restart it with your permission, then runs run.sh inside Linux.
echo Starting genome-kit...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
