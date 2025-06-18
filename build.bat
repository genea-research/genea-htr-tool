@echo off
REM Simple build script for Windows

echo 🚀 Building Genea HTR GUI Standalone Application
echo ================================================

REM Make sure we're in the right directory
if not exist "genea_htr_gui.py" (
    echo ❌ Error: genea_htr_gui.py not found in current directory
    echo Please run this script from the directory containing your application files.
    pause
    exit /b 1
)

REM Run the Python build script
python build_standalone.py

echo.
echo Build script completed. Check the output above for results.
pause
