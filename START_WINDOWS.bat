@echo off
REM Windows batch script to properly start the MCP server
REM This ensures ProactorEventLoop is used for subprocess support

echo ========================================
echo MCP Server - Windows Startup Script
echo ========================================
echo.

REM Kill any existing Python processes
echo Killing any existing Python processes...
taskkill /F /IM python.exe >nul 2>&1

echo.
echo Starting server with ProactorEventLoop support...
echo.

REM Start with the Windows-optimized script
python run_windows.py

pause
