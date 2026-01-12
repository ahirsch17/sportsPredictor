@echo off
REM SportsPredictor Startup Script for Windows
REM This script starts the FastAPI server and opens the web interface
REM For macOS/Linux, use start.command or start.py instead

REM Check if running on Windows
if "%OS%"=="" (
    echo ERROR: This script is for Windows only.
    echo On macOS/Linux, use: start.command or python3 start.py
    pause
    exit /b 1
)

cd /d "%~dp0"

echo Starting SportsPredictor server...
echo.

REM Start the server in a new window so it keeps running
start "SportsPredictor Server" cmd /k "python -m uvicorn api.server:app --reload --port 8001"

echo Waiting for server to be ready...
echo.

REM Wait for server to start (give it enough time)
timeout /t 5 /nobreak >nul

REM Check if server is ready using PowerShell
powershell -Command "$response = $null; $maxAttempts = 10; $attempt = 0; while ($attempt -lt $maxAttempts -and $response -eq $null) { try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/health' -TimeoutSec 1 -UseBasicParsing; Write-Host 'Server is ready!'; break } catch { Start-Sleep -Milliseconds 500; $attempt++ } } if ($response -eq $null) { Write-Host 'Warning: Server may not be ready yet, but opening browser anyway...' }"

echo.
echo.
echo Opening web interface at http://127.0.0.1:8001...
echo.

REM Open the HTTP URL instead of file:// to avoid CORS issues
start "" "http://127.0.0.1:8001"

echo.
echo Server is running on http://127.0.0.1:8001
echo Web interface should open in your browser shortly.
echo.
echo To stop the server, close the "SportsPredictor Server" window.
echo.
pause

