@echo off
REM ============================================================
REM  FLUJO - abrir el hub servido (modo real, con /api activo)
REM  Doble clic: levanta el server y abre el navegador.
REM  (Si solo quieres demo sin servidor, abre context\flujo_hub.html
REM   directamente con doble clic.)
REM ============================================================
cd /d "%~dp0"
call "%~dp0launch-flujo.bat"
exit /b %errorlevel%
