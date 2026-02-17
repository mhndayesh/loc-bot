@echo off
title new-agent-mohannad
echo ============================================
echo   new-agent-mohannad  -  Agent System
echo ============================================
echo.
echo Starting server on http://localhost:7777 ...
echo Press Ctrl+C to stop.
echo.

:: Open browser after a short delay
start "" /B cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:7777"

:: Start server (blocks until Ctrl+C)
python "%~dp0server.py" --port 7777
