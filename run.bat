@echo off
setlocal
REM BrakeLab launcher for Windows. Double-click this file, or run it from a terminal.
REM First run creates a local virtual environment (.venv) and installs dependencies;
REM later runs just launch the app.

cd /d "%~dp0"

REM Prefer the "py" launcher; fall back to "python" on PATH.
set "PYCMD=py"
where py >nul 2>nul || set "PYCMD=python"

set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Creating virtual environment ^(first run only^)...
    %PYCMD% -m venv .venv || goto :error
    echo Installing dependencies, this may take a minute...
    "%VENV_PY%" -m pip install --upgrade pip || goto :error
    "%VENV_PY%" -m pip install -e . || goto :error
)

echo Starting BrakeLab...
"%VENV_PY%" -m brakelab
if errorlevel 1 goto :error
goto :end

:error
echo.
echo BrakeLab could not start. Make sure 64-bit Python 3.11 or 3.12 is installed and
echo was added to PATH ^(re-run the Python installer and tick "Add python.exe to PATH"^).
echo.
pause

:end
endlocal
