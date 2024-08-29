@echo off
setlocal enabledelayedexpansion

:: Set the path to the project root directory
set PROJECT_ROOT=%~dp0\..

:: Change directory to the project root
cd /d %PROJECT_ROOT%

:: Loop through all .py files in the Modules directory
for %%f in (Modules\*.py) do (
    :: Get the filename without extension
    set FILE_NAME=%%~nf

    :: Skip __init__.py
    if /i not "!FILE_NAME!"=="__init__" (
        echo ====================================================================================================
        echo RUNNING !FILE_NAME! & echo:
        
        :: Run the module using -m to maintain the package context
        python -m Modules.!FILE_NAME!

        echo: & echo EXITING !FILE_NAME!
        echo ====================================================================================================
        echo: & echo: & echo: & echo:
    )
)

endlocal
pause
