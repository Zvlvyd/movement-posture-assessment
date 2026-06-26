@echo off
setlocal

:: Navigate to frontend directory
cd /d "%~dp0code\pose-system\pose-system\frontend"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cannot enter frontend directory
    pause
    exit /b 1
)

:: Auto-install on first run
if not exist "node_modules\" (
    echo [INFO] Installing dependencies...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
    echo [INFO] Dependencies installed
)

:: Start Vite dev server
echo [INFO] Starting frontend dev server at http://localhost:5173
echo [INFO] Press Ctrl+C to stop
echo.
call npm run dev

pause
