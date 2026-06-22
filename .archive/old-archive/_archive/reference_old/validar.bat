@echo off
cd /d c:\rd\AUTOMATIZACION
python -m py_compile automatizador_flyers_gui.pyw
if %errorlevel% equ 0 (
    echo ✓ Codigo Python validado correctamente
    echo.
    echo Cambios realizados:
    echo - Logging automatico habilitado
    echo - Reintentos para descargas
    echo - Mejor manejo de errores
    echo - Interfaz mejorada con emojis
    echo - EXE mas pequeno y rapido
    echo.
    echo Proximamente ejecuta:
    echo   instalar_dependencias.bat
    echo   crear_exe.bat
) else (
    echo ✗ Error en validacion
)
pause
