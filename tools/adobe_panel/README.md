# Vibo Adobe Panel (CEP)

Panel acoplable para Illustrator, Photoshop y After Effects. Un solo panel que
lanza los scripts `.jsx` del repo. Los botones cambian segun la app activa.

## Que hace cada boton

- **Illustrator**
  - Titulos -> fotos individuales (`illustrator/scripts/titles_to_photos.jsx`)
  - Revectorizar JPEG + extrusion 3D -> vector (SVG/EPS/PDF) + PNG (`illustrator/scripts/logo_revector_extrude.jsx`)
  - Batch: carpeta de logos -> vector + PNG (`illustrator/scripts/logo_revector_batch.jsx`)
  - Limpiar logo / nodos (`illustrator/scripts/logo_clean_master.jsx`)
- **Photoshop**
  - Capas -> fotos individuales (`photoshop/scripts/layers_to_photos.jsx`)
- **After Effects**
  - Titulos -> composiciones (`after_effects/scripts/titles_to_comps.jsx`)

El panel no duplica scripts: ejecuta los `.jsx` que viven en `tools/`. Si el
panel queda copiado fuera del repo, configura `repo_tools_path` en
`config.json` o en:

```txt
%APPDATA%\Adobe\CEP\preferences\vibo_adobe_panel\config.json
```

## Instalacion (Windows, modo desarrollo)

1. **Activar PlayerDebugMode** (permite paneles sin firmar). Abre PowerShell y ejecuta:

   ```powershell
   New-Item -Path "HKCU:\Software\Adobe\CSXS.11" -Force | Out-Null
   New-ItemProperty -Path "HKCU:\Software\Adobe\CSXS.11" -Name PlayerDebugMode -Value 1 -PropertyType String -Force | Out-Null
   New-Item -Path "HKCU:\Software\Adobe\CSXS.12" -Force | Out-Null
   New-ItemProperty -Path "HKCU:\Software\Adobe\CSXS.12" -Name PlayerDebugMode -Value 1 -PropertyType String -Force | Out-Null
   ```

   (CSXS.11 y CSXS.12 cubren las versiones recientes de las apps. Si tu app usa
   otra, crea la clave equivalente CSXS.N.)

2. **Copiar el panel** a la carpeta de extensiones CEP del usuario:

   `C:\Users\<usuario>\AppData\Roaming\Adobe\CEP\extensions\com.vibo.adobepanel`

   Ejemplo (ajusta la ruta del repo si difiere):

   ```powershell
   $dst = "$env:APPDATA\Adobe\CEP\extensions\com.vibo.adobepanel"
   New-Item -ItemType Directory -Force -Path $dst | Out-Null
   Copy-Item -Recurse -Force "C:\IA\flujo\tools\adobe_panel\*" $dst
   ```

   Alternativa recomendada: crea un enlace simbolico para que el panel siga al
   repo y encuentre `tools/` sin copiar scripts:

   ```powershell
   New-Item -ItemType SymbolicLink -Path "$env:APPDATA\Adobe\CEP\extensions\com.vibo.adobepanel" -Target "C:\IA\flujo\tools\adobe_panel"
   ```

3. **Reinicia** Illustrator / Photoshop / After Effects.

4. Abre el panel desde el menu:
   - Illustrator / Photoshop: `Ventana > Extensiones > Vibo Adobe Panel`
   - After Effects: `Ventana > Extensiones > Vibo Adobe Panel`

5. Diagnostico sin abrir Adobe:

   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\IA\flujo\tools\adobe_panel\check_install.ps1
   ```

## Notas

- Si el panel no aparece, revisa que PlayerDebugMode este en `1` y que la version
  CSXS.N corresponda a tu app.
- Depuracion remota: con `.debug` presente, abre `http://localhost:8088` (AI),
  `8089` (PS) o `8090` (AE) en Chrome mientras el panel esta abierto.
- Para distribuir a otras maquinas conviene firmar un `.zxp` (empaquetado con
  ZXPSignCmd). Para uso local, PlayerDebugMode es suficiente.
- CEP funciona hoy en las tres apps. Si en el futuro quieres versiones UXP
  nativas (Photoshop / Illustrator modernos), se pueden anadir aparte.

## Empaquetar como .zxp (para instalar con doble clic / distribuir)

Para no depender de PlayerDebugMode en cada maquina, se firma un `.zxp`.

1. Descarga **ZXPSignCmd.exe** de Adobe (repo `Adobe-CEP/CEP-Resources`,
   carpeta `ZXPSignCMD`). No viene con Windows.

2. Ejecuta el build (genera certificado autofirmado la primera vez):

   ```powershell
   powershell -ExecutionPolicy Bypass -File build_zxp.ps1 -ZXPSignCmd "C:\ruta\ZXPSignCmd.exe"
   ```

   Salida: `tools/adobe_panel_dist/com.vibo.adobepanel.zxp`

3. Instala el `.zxp`:
   - Facil: **ZXP Installer** de Anastasiy (GUI, doble clic).
   - CLI: **ExManCmd** de Adobe:
     ```powershell
     ExManCmd /install "C:\IA\flujo\tools\adobe_panel_dist\com.vibo.adobepanel.zxp"
     ```

Nota: al ser certificado autofirmado, algunos instaladores avisan que el editor
no esta verificado; es normal para uso propio. El `.debug` incluido es solo para
desarrollo; puedes borrarlo antes de firmar si quieres un paquete limpio.

> No puedo generar el `.zxp` firmado desde aqui (necesita ZXPSignCmd y un
> certificado en tu maquina). El script `build_zxp.ps1` lo automatiza en un paso
> cuando lo corres tu.
