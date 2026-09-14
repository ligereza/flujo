@echo off
REM ============================================================
REM  FLUJO - instalador local editable + diagnostico (Windows)
REM ============================================================
setlocal
cd /d "%~dp0"
echo Installing flujo from: %cd%
echo.
where py >nul 2>nul || (
	echo ERROR: Python launcher ^(py^) was not found in PATH.
	exit /b 127
)
py -m pip install -e ".[dev,web]" || exit /b %errorlevel%
echo Running environment diagnostics...
py -m flujo doctor
set "RC=%errorlevel%"
echo.
echo ============================================================
echo  Commands:
echo    py -m flujo app              (daily browser app)
echo    py -m flujo app --desktop    (native desktop window)
echo    py -m flujo doctor           (chequeo)
echo ============================================================
exit /b %RC%
