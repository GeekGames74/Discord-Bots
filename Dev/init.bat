@echo off

set FILE_DIR=%~dp0
set FILE_DIR=%FILE_DIR:~0,-1%

for %%I in ("%FILE_DIR%") do set PARENT_DIR=%%~dpI
set PARENT_DIR=%PARENT_DIR:~0,-1%

set PYTHONPATH=%PARENT_DIR%
echo PYTHONPATH is set to %PYTHONPATH%
