@echo off
title Iftar System
color 0A
echo ========================================
echo    IFTAR SYSTEM - START ALL SERVICES
echo ========================================
echo.

echo [1/5] Cleaning up ports...
for %%p in (5000 5001 5002 5003 5004) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| find ":%%p" ^| find "LISTENING"') do (
        taskkill /f /pid %%a >nul 2>&1
    )
)
echo      Done!

echo [2/5] Initializing database...
cd identity_service
python init_db.py
cd ..
echo      Done!

echo [3/5] Starting Identity Service...
start "Identity Service" cmd /k "cd identity_service && python app.py"
timeout /t 2 /nobreak >nul

echo [4/5] Starting Order Service...
start "Order Service" cmd /k "cd order_service && python app.py"
timeout /t 2 /nobreak >nul

start "Kitchen Service" cmd /k "cd kitchen_service && python app.py"
timeout /t 2 /nobreak >nul

start "Stock Service" cmd /k "cd stock_service && python app.py"
timeout /t 2 /nobreak >nul

start "Gateway Service" cmd /k "cd gateway && python app.py"

echo [5/5] Waiting for services...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo    ALL SERVICES STARTED SUCCESSFULLY!
echo ========================================
echo.
echo Access URLs:
echo   Main App:  http://localhost:5000
echo   Admin:     http://localhost:5000/admin
echo.
start http://localhost:5000
echo.
pause