@echo off
setlocal
REM BrakeLab from-source launcher (developers).
REM Most people should NOT use this — download the ready-made app instead:
REM   GitHub repo -> Releases -> BrakeLab-Windows.zip -> extract -> double-click BrakeLab.exe
REM
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
echo BrakeLab could not start from source. The easy fix: download the ready-made app
echo from the GitHub Releases page ^(BrakeLab-Windows.zip^) - it needs no Python at all.
echo.
echo To keep running from source instead, install 64-bit Python 3.11 or 3.12 and tick
echo "Add python.exe to PATH" in the installer, then double-click run.bat again.
echo.
pause

:end
endlocal
