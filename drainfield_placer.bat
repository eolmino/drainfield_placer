@echo off
REM Drainfield Placer - Main Application Runner

echo ============================================================
echo   DRAINFIELD PLACER - Automatic Configuration Tool
echo ============================================================
echo.

cd /d C:\drainfield_placer

echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo.
echo Checking Shapely...
python -c "import shapely; print('Shapely installed: OK')"
if errorlevel 1 (
    echo Installing Shapely...
    pip install shapely
)

echo.
echo Checking psycopg2 (for database)...
python -c "import psycopg2; print('psycopg2 installed: OK')" 2>nul
if errorlevel 1 (
    echo Note: psycopg2 not installed (optional - only needed for database updates)
    echo To install: pip install psycopg2
)

echo.
echo Starting application...
echo.
python main.py

pause
