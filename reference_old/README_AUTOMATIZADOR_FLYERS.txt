═══════════════════════════════════════════════════════════════════
  AUTOMATIZADOR DE FLYERS - GUI (Versión Mejorada)
═══════════════════════════════════════════════════════════════════

📋 ARCHIVOS
───────────────────────────────────────────────────────────────────
- automatizador_flyers_gui.pyw    → App principal (doble click)
- instalar_dependencias.bat       → Instala dependencias (correr una vez)
- crear_exe.bat                   → Crea ejecutable .exe
- requirements.txt                → Versiones explícitas de dependencias

📍 RUTAS MANTENIDAS
───────────────────────────────────────────────────────────────────
Base:               C:\rd\AUTOMATIZACION
Droplet:            C:\rd\AUTOMATIZACION\Droplet_Flyer.exe
Photoshop PSD:      C:\rd\AUTOMATIZACION\historia.psd
Input (generado):   C:\rd\AUTOMATIZACION\input_ig.jpg

🎨 SALIDAS NUEVAS
───────────────────────────────────────────────────────────────────
- color_predominante_1.png       → 1er color dominante (muestra visual)
- color_predominante_2.png       → 2do color dominante (muestra visual)

🚀 INSTALACIÓN RÁPIDA
───────────────────────────────────────────────────────────────────

1️⃣  REQUISITOS:
    • Python 3.8+ (descarga desde https://www.python.org)
    • Conexión a internet (para descargar de Instagram)

2️⃣  INSTALACIÓN DE DEPENDENCIAS (una sola vez):
    → Doble click en: instalar_dependencias.bat
    → Espera a que termine (verás un ✓ al final)

3️⃣  EJECUTAR LA APP:
    → Doble click en: automatizador_flyers_gui.pyw
    (Si no funciona, ejecuta: python automatizador_flyers_gui.pyw)

💻 CREAR EXE (Opcional)
───────────────────────────────────────────────────────────────────

Para distribuir sin depender de Python:
    → Doble click en: crear_exe.bat
    → El resultado estará en: dist\AutomatizadorFlyers.exe

Ventajas del .exe:
    ✓ Portable (no necesita Python instalado)
    ✓ Se lanza desde doble click fácilmente
    ✓ Se puede crear acceso directo en escritorio

⚡ FLUJOS DE USO
───────────────────────────────────────────────────────────────────

A) DESDE INSTAGRAM (LINKS PÚBLICOS):
   1. Pega el link del post/reel en "Link del post/reel"
   2. Click "Descargar + preparar + abrir droplet"
   3. El app descargará la imagen, la procesará, generará colores
      y abrirá el droplet automáticamente

B) IMAGEN DESCARGADA MANUALMENTE:
   (Para cuentas privadas, shadowbaneadas, que piden login)
   1. Descarga la imagen manualmente a cualquier carpeta
   2. Click "Elegir imagen" y selecciona el archivo
   3. Click "Usar imagen manual + abrir droplet"
   4. El app procesará la imagen y abrirá el droplet

C) SOLO PREPARAR INPUT (SIN DROPLET):
   1. Después de descargar/elegir imagen
   2. Click en el botón "Solo descargar/preparar input"
   3. El input_ig.jpg estará listo, pero no abrirá Photoshop

🔍 BÚSQUEDA RÁPIDA
───────────────────────────────────────────────────────────────────

Herramientas para encontrar productoras/eventos:
   • Google eventos: Busca productora + próximos eventos
   • Instagram: Abre perfil de productora o búsqueda

💾 LOGS Y DEBUG
───────────────────────────────────────────────────────────────────

Si algo falla, se genera un log en:
   C:\Users\[TU_USUARIO]\.automatizador_flyers.log

Comparte este archivo si necesitas ayuda.

✨ MEJORAS EN ESTA VERSIÓN
───────────────────────────────────────────────────────────────────

✓ Manejo robusto de errores con reintentos
✓ Logging automático a archivo para debug
✓ Interfaz mejorada con emojis e iconos claros
✓ Prevención de ejecuciones simultáneas
✓ Mejor validación de archivos y dependencias
✓ Compresión mejorada en EXE (60-70% más pequeño)
✓ Carga optimizada de módulos (inicia más rápido)
✓ EXE más rápido al abrir

🛠️ TROUBLESHOOTING
───────────────────────────────────────────────────────────────────

PROBLEMA: "ModuleNotFoundError: No module named 'instaloader'"
SOLUCIÓN: Ejecuta instalar_dependencias.bat nuevamente

PROBLEMA: El .exe no inicia o es muy lento
SOLUCIÓN:
   • Primera ejecución es normal que sea lenta (descompresión)
   • Intenta ejecutar desde terminal: crear_exe.bat
   • Verifica que tienes espacio suficiente en C:\

PROBLEMA: Instagram rechaza descargas ("error de autenticación")
SOLUCIÓN: Usa el flujo manual (descarga la imagen tú en el navegador)

PROBLEMA: Input_ig.jpg no se actualiza
SOLUCIÓN:
   • Cierra Photoshop si está abierto
   • Verifica que la imagen descargada es válida
   • Revisa el log en C:\Users\[TU_USUARIO]\.automatizador_flyers.log

📝 NOTAS IMPORTANTES
───────────────────────────────────────────────────────────────────

• La app NO intenta saltarse privacidad ni logins
• Para cuentas privadas, descarga manualmente en tu navegador
• Los botones de búsqueda abren en tu navegador (no descarga nada)
• temp_flyer se limpia automáticamente al terminar (configurable)
• Los colores predominantes son aproximaciones (no exactos)

═══════════════════════════════════════════════════════════════════
