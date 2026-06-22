@echo off
chcp 65001 > nul
title Configurar Automatizador v2
echo.
echo ================================
echo Configurando Automatizador v2
echo ================================
echo.

REM Crear estructura de carpetas
echo Creando estructura de carpetas...
mkdir "SCRIPTS" 2>nul
mkdir "RECURSOS" 2>nul
mkdir "RESULTADOS" 2>nul
mkdir "TEMP" 2>nul
mkdir "OBJETOS_INTELIGENTES" 2>nul
mkdir "CONFIGURACION" 2>nul

REM Mover archivos existentes
echo Reorganizando archivos...
move "historia.psd" "RECURSOS\" 2>nul
move "RD.blend" "RECURSOS\" 2>nul
move "Droplet_Flyer.exe" "RECURSOS\" 2>nul

REM Archivos nuevos
echo ✓ Nuevos scripts:
if exist automatizador_flyers_v2.pyw echo   - automatizador_flyers_v2.pyw (app mejorada)
if exist email_extractor.py echo   - email_extractor.py (lectura de correos)
if exist blender_colorizer.py echo   - blender_colorizer.py (aplicar colores)
if exist blender_manager.py echo   - blender_manager.py (gestión de Blender)

echo.
echo ✓ Estructura lista:
echo   RECURSOS\           - Archivos estables
echo   RESULTADOS\         - Salidas finales
echo   TEMP\               - Archivos temporales
echo   OBJETOS_INTELIGENTES\ - Proyectos Blender por evento
echo   CONFIGURACION\      - Config y logs
echo.
echo ✓ Próximo paso: Ejecuta automatizador_flyers_v2.pyw
echo.
pause
