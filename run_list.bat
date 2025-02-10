@echo off

REM Display the current directory
echo [INFO] Directory before change: %cd%

REM Change to the root directory (assumes the batch file is located here)
cd /d "%~dp0"
echo [INFO] Root directory: %cd%

REM Execute main.py in the src_list folder
python src_list/main.py

REM If an error occurs, pause execution
if errorlevel 1 (
    echo An error has occurred.
    pause
) 