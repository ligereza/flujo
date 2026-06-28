@echo off
REM Crear estructura de carpetas
mkdir "%cd%\SCRIPTS" 2>nul
mkdir "%cd%\RECURSOS" 2>nul
mkdir "%cd%\RESULTADOS" 2>nul
mkdir "%cd%\TEMP" 2>nul
mkdir "%cd%\OBJETOS_INTELIGENTES" 2>nul
mkdir "%cd%\CONFIGURACION" 2>nul

REM Copiar recursos existentes
copy "historia.psd" "RECURSOS\" 2>nul
copy "RD.blend" "RECURSOS\" 2>nul
copy "Droplet_Flyer.exe" "RECURSOS\" 2>nul

REM Mover scripts existentes
move "automatizador_flyers_gui.pyw" "SCRIPTS\" 2>nul
move "instalar_dependencias.bat" "SCRIPTS\" 2>nul
move "crear_exe.bat" "SCRIPTS\" 2>nul
move "validar.bat" "SCRIPTS\" 2>nul

REM Mover salidas a RESULTADOS
move "input_ig.jpg" "RESULTADOS\" 2>nul
move "color_predominante_1.png" "RESULTADOS\" 2>nul
move "color_predominante_2.png" "RESULTADOS\" 2>nul
move "flyer_final.jpg" "RESULTADOS\" 2>nul

echo ✓ Estructura de carpetas creada
pause
