@echo off
setlocal enabledelayedexpansion

:: Set the path to the project root directory
set PROJECT_ROOT=%~dp0\..

:: Change directory to the project root
cd /d %PROJECT_ROOT%

:: Check if a filename was provided as a command-line argument
if "%~1"=="" (
    :: Ask for a specific file name to run, without .py extension
    set /p FILE_TO_RUN="Enter filename to run (without extension): "
) else (
    :: Use the provided argument as the filename
    set FILE_TO_RUN=%~1
)

GOTO:MAIN

:Run
    set FILE_NAME=%~1
    echo ====================================================================================================
    echo RUNNING !FILE_NAME! & echo:
    
    :: Run the module using -m to maintain the package context
    python -m Modules.!FILE_NAME!

    echo: & echo EXITING !FILE_NAME!
    echo ====================================================================================================
EXIT /B 0

:MAIN

:: Loop through all .py files in the Modules directory
for %%f in (Modules\*.py) do (
    SET FILE_NAME=%%~nf
    if not defined FILE_TO_RUN (
        call:Run "!FILE_NAME!"
    ) else if /i "!FILE_NAME!"=="!FILE_TO_RUN!" (
        call:Run "!FILE_NAME!"
    )
)

endlocal
pause
