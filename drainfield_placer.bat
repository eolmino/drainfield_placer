@echo off
REM Simple runner - No virtual environment needed!

echo ============================================================
echo   DRAINFIELD PLACER - Quick Test
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
echo Running test...
echo.
python simple_test.py

pause
