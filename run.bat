@echo off
title Kokoro Local ONNX TTS Extension
cd /d "%~dp0"

:: Check if the isolated virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment was not found at .\.venv\
    echo Please make sure the installation has finished successfully.
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   Starting Kokoro-82M Local TTS System Extension...
echo   Minimize this console. The app runs in your System Tray!
echo ============================================================
echo.

:: Run the entry-point script using the local virtual environment interpreter
".venv\Scripts\python.exe" src\main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Application exited with non-zero exit code: %ERRORLEVEL%
    pause
)
