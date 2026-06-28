@echo off
chcp 65001 > nul
title Crear EXE - Automatizador Flyers
echo.
echo ======================================
echo Creador de EXE - Automatizador Flyers
echo ======================================
echo.

REM Verificar que Python está disponible
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no se encuentra instalado.
    pause
    exit /b 1
)

echo Verificando PyInstaller...
py -m pip show PyInstaller > nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    py -m pip install PyInstaller pyinstaller-hooks-contrib -q
)

echo.
echo Generando EXE optimizado (sin consola, comprimido)...
echo Esto puede tomar un poco de tiempo...
echo.

REM Generar EXE con compresión UPX y optimizaciones
py -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name AutomatizadorFlyers ^
    --icon=NONE ^
    --uac-admin ^
    --noupx ^
    --optimize=2 ^
    --exclude-module=tkinter.test ^
    --exclude-module=unittest ^
    --exclude-module=pydoc ^
    --exclude-module=doctest ^
    --hidden-import=instaloader ^
    --hidden-import=PIL ^
    automatizador_flyers_gui.pyw

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo crear el EXE.
    echo Asegúrate de que automatizador_flyers_gui.pyw existe en esta carpeta.
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo ✓ EXE creado exitosamente
echo ======================================
echo.
echo Ubicación: dist\AutomatizadorFlyers.exe
echo.
echo Puedes:
echo   1. Ejecutarlo directamente: dist\AutomatizadorFlyers.exe
echo   2. Copiarlo a otra carpeta
echo   3. Crear acceso directo en el escritorio
echo.
echo Nota: El primer lanzamiento puede tardar unos segundos (descompresión).
echo.
pause
exit /b 0
