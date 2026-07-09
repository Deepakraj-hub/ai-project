@echo off
echo ================================================
echo Starting LILY Desktop Application
echo ================================================
echo.

echo [1/3] Checking Python dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing Flask and Flask-CORS...
    pip install flask flask-cors
)

echo.
echo [2/3] Starting Flask Backend (Port 5000)...
start "Lily Backend" cmd /k "cd /d %~dp0 && python app.py"
timeout /t 3 >nul

echo.
echo [3/3] Starting React Frontend...
cd ai-avatar
start "Lily Frontend" cmd /k "npm run dev"

echo.
echo ================================================
echo LILY Desktop Application Started!
echo ================================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: Check the Frontend terminal window for the URL
echo           (Usually http://localhost:5173)
echo.
echo Press any key to open frontend in browser...
pause >nul

timeout /t 5 >nul
start http://localhost:5173

echo.
echo To stop: Close both terminal windows
echo.
