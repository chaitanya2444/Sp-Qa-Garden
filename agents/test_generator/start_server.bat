@echo off
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat

REM Get local IP address (simplified method)
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address" ^| findstr /v "192.168.1.1"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP:~1%
if "%IP%"=="" set IP=192.168.1.61

echo ========================================
echo   Test Case Generator API Server
echo ========================================
echo.
echo Local Access:
echo   http://localhost:8001
echo   Frontend:  http://localhost:8001/frontend
echo   Swagger UI: http://localhost:8001/docs
echo.
echo Network Access:
echo   http://%IP%:8001
echo   Frontend:  http://%IP%:8001/frontend
echo   Swagger UI: http://%IP%:8001/docs
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
pause

