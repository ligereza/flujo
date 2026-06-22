@echo off
chcp 65001 > nul
title Instalar Dependencias - Automatizador Flyers
echo.
echo ======================================
echo Instalador de Dependencias
echo ======================================
echo.

REM Verificar que Python está disponible
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no se encuentra instalado o no está en PATH.
    echo Por favor, instala Python desde https://www.python.org
    echo.
    pause
    exit /b 1
)

echo ✓ Python encontrado
echo.

REM Verificar versión mínima de pip
echo Actualizando pip a la última versión...
py -m pip install --upgrade pip setuptools wheel -q
if errorlevel 1 (
    echo ADVERTENCIA: No se pudo actualizar pip, pero continuaré...
)

echo.
echo Instalando dependencias desde requirements.txt...
echo.

py -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Hubo un problema instalando las dependencias.
    echo Intenta ejecutar manualmente:
    echo   py -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo ✓ Dependencias instaladas correctamente
echo ======================================
echo.
echo Puedes ejecutar el automatizador con:
echo   python automatizador_flyers_gui.pyw
echo.
pause
exit /b 0
