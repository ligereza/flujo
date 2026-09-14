@echo off
setlocal
cd /d "%~dp0"
echo Launching flujo app --desktop from %cd%...
where py >nul 2>nul || (
	echo ERROR: Python launcher ^(py^) was not found in PATH.
	exit /b 127
)
py -m flujo app --desktop
set "RC=%errorlevel%"
if not "%RC%"=="0" echo ERROR: flujo exited with code %RC%.
exit /b %RC%
