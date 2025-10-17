@echo off
REM BookMyMovie Platform - Development Startup Script
REM This script starts all services locally without Docker

echo ============================================
echo   BookMyMovie Platform - Development Mode
echo ============================================

REM Set development environment
set ENVIRONMENT=development
set DATABASE_URL=sqlite:///./bookmymovie_dev.db
set REDIS_URL=memory://localhost
set JWT_SECRET_KEY=dev-jwt-secret-key-not-for-production

REM Check if virtual environment is activated
python -c "import sys; print('Virtual env active' if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else 'No virtual env')"

echo.
echo Starting BookMyMovie services...
echo.

REM Start services in background
echo Starting Auth Service on port 8013...
start "Auth Service" cmd /k "cd /d C:\Bookmymovie_Project && python backend\secure_auth_service.py"

timeout /t 3 /nobreak > nul

echo Starting Catalog Service on port 8012...
start "Catalog Service" cmd /k "cd /d C:\Bookmymovie_Project && python backend\secure_catalog_service.py"

timeout /t 3 /nobreak > nul

echo Starting Booking Service on port 8014...
start "Booking Service" cmd /k "cd /d C:\Bookmymovie_Project && python backend\secure_booking_service.py"

timeout /t 3 /nobreak > nul

echo Starting Payment Service on port 8015...
start "Payment Service" cmd /k "cd /d C:\Bookmymovie_Project && python backend\secure_payment_service.py"

timeout /t 3 /nobreak > nul

echo Starting Real-time Service on port 8016...
start "Realtime Service" cmd /k "cd /d C:\Bookmymovie_Project && python backend\secure_realtime_service.py"

timeout /t 3 /nobreak > nul

echo Starting Frontend on port 8080...
start "Frontend" cmd /k "cd /d C:\Bookmymovie_Project\frontend && python -m http.server 8080"

echo.
echo ============================================
echo All services are starting up...
echo.
echo Service URLs:
echo   Frontend:     http://localhost:8080
echo   Auth API:     http://localhost:8013/docs
echo   Catalog API:  http://localhost:8012/docs  
echo   Booking API:  http://localhost:8014/docs
echo   Payment API:  http://localhost:8015/docs
echo   Realtime API: http://localhost:8016/docs
echo.
echo Press any key to check service status...
echo ============================================
pause

REM Check if services are running
echo.
echo Checking service status...
netstat -ano | findstr "8012 8013 8014 8015 8016 8080"

echo.
echo Setup complete! All services should be running.
echo Press any key to exit...
pause