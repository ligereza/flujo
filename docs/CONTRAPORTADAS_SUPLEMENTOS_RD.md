# Contraportadas de suplementos RD

> **Un solo documento** (2026-07-27). Antes esto vivía en dos archivos del mismo
> día que se solapaban: `CONTRAPORTADAS_SUPLEMENTOS_RD.md` (la guía) y
> `CONTRAPORTADAS_SUPLEMENTOS_OPERATIVO.md` (Illustrator y exportación). Se
> unieron sin quitar una línea de ninguno; lo que sigue son las dos partes, en
> orden. Si algo se repite, se corrige acá y no se abre un tercer archivo.

---

## Descripción General

Las **contraportadas** (10×14 cm) son tarjetas de presentación diseñadas para acompañar suplementos de Reduciendo Daño. Cada una cuenta la historia del producto, sus beneficios, instrucciones de uso y contacto directo.

## Estructura de Archivos

> **Medido el 2026-08-28.** El bloque de abajo describe la estructura pretendida,
> no la del disco. Lo que existe realmente:
>
> - `svg/suplementos_rd/09_contraportadas_dark/` -- 7 SVG por producto
>   (`01_linea_suplementos_rd.svg`, `02_impulso.svg`, `03_hongos_adaptogenos.svg`,
>   `04_pre_fiesta.svg`, `05_magnesio.svg`, `06_creatina_monohidratada.svg`,
>   `contraportada_cambios.svg`). La ruta que este documento declaraba,
>   `04_contraportadas/`, nunca existio.
> - `svg/suplementos_rd/_plantilla/` -- plantillas
> - `svg/suplementos_rd/_master_contraportadas.json` -- el master
>
> No existe `01_contraportada_base_10x14cm.svg`: el archivo base por linea es
> `01_linea_suplementos_rd.svg`.


```
svg/suplementos_rd/09_contraportadas_dark/
├── 01_contraportada_base_10x14cm.svg     # Base template SVG (DO NOT EDIT manually)
├── suplementos_rd_illustrator_spec.json  # Specs Illustrator
├── suplementos_rd_illustrator_artboards.jsx  # Script Illustrator
└── [generadas]/
    ├── suplemento_impulso_final.svg
    ├── suplemento_creatina_final.svg
    └── ... (más)
```

## Método 1: CLI Rápido (Recomendado)

```bash
# Generar contraportada SVG desde CLI
py -m flujo suplementos contraportada "Impulso" --output salida/impulso_final.svg

# Ver lista de suplementos disponibles
py -m flujo suplementos list
```

**Ventajas:**
- ✓ Rápido (sin UI)
- ✓ Automatizado (sin edición manual)
- ✓ Consistente con brand
- ✓ Fácil de integrar en scripts

## Método 2: Edición Manual en Illustrator

### Abrir la Base

1. Abrir `svg/suplementos_rd/09_contraportadas_dark/01_contraportada_base_10x14cm.svg` en Adobe Illustrator
2. Archivo → Documentar propiedades → Confirmar que sea 10×14 cm (1181×1654 px a 300dpi)
3. Ver → Mesas de trabajo → Asegurar que esté visible

### Editar Componentes

#### Zona Hero (Fondo Verde Oscuro)
- **Ubicación**: Arriba, ancho completo
- **Altura recomendada**: ~40% del canvas
- **Color fondo**: `#173F2F` (verde oscuro RD)
- **Qué editar**:
  - Título: `NOMBRE DEL SUPLEMENTO` (texto grande, blanco, 68pt bold)
  - Descripción: `DESCRIPCIÓN` (amarillo `#F5C54D`, 28pt bold)
  - Beneficio: línea 1-2 de texto blanco (26pt, normal)

#### Zona Info Nutricional (Blanco)
- **Ubicación**: Centro, con border gris claro `#D9CEC0`
- **Color de fondo**: Blanco `#FFFFFF`
- **Qué editar**:
  - Encabezado: `INFORMACIÓN NUTRICIONAL` (verde oscuro, 30pt bold)
  - Bullets: 3 líneas máx de beneficios/uso (24pt normal)
  - Boxes contacto: 3 cajas rectangulares (130×110 px) con rounding 28pt:
    - **WhatsApp** (izquierda): fondo verde `#173F2F`, texto amarillo
    - **Contacto** (centro): fondo amarillo `#F5C54D`, texto verde
    - **QR/Link** (derecha): fondo verde `#173F2F` opacity 95%, texto blanco

#### Zona Footer
- **Línea divisor**: Gris claro `#D9CEC0`, grosor 3px
- **Texto de marca**: `@ REDUCIENDODANO.CL` (verde, 24pt bold)
- **Frase llamada**: `SIGUENOS EN REDES` (gris topo, 20pt bold)

### Paleta de Colores Obligatoria

```
Verde Oscuro RD:    #173F2F (RGB: 23, 63, 47)
Amarillo Primario:  #F5C54D (RGB: 245, 197, 77)
Blanco Fondo:       #F6EFE3 (RGB: 246, 239, 227)
Blanco Puro:        #FFFFFF (RGB: 255, 255, 255)
Gris Borde:         #D9CEC0 (RGB: 217, 206, 192)
Gris Topo:          #675F55 (RGB: 103, 95, 85)
Negro Texto:        #161513 (RGB: 22, 21, 19)
```

### Tipografía Recomendada

- **Títulos** (68pt bold): DejaVu Sans, Arial, Helvetica, sans-serif
- **Encabezados** (30pt bold): DejaVu Sans, Arial, Helvetica, sans-serif
- **Cuerpo** (24–26pt normal): DejaVu Sans, Arial, Helvetica, sans-serif
- **Label pequeño** (20pt bold): DejaVu Sans, Arial, Helvetica, sans-serif

**Alternativas fallback**: Arial, Helvetica, sans-serif genérico. (NO usar fuentes propietarias si no están embebidas.)

### Márgenes y Aire

```
Margen exterior (rect borde):   70px
Margen contenido zona hero:     50px (izquierda/derecha)
Margen contenido zona info:     50px (izquierda/derecha)
Separación vertical entre bloques: 30–40px
Altura línea divisor: 3px
Radio redondeo (rounding): 40px (bloques) o 28–30px (cajas)
```

### Checklist Visual Antes de Exportar

- [ ] **Texto legible**: Título y beneficio visible sin zoom
- [ ] **Colores correctos**: Verde/amarillo/blanco en las zonas esperadas
- [ ] **Márgenes respetados**: Nada toca el borde de la página
- [ ] **Fuentes embebidas o fallback sólido**: Usar DejaVu Sans o Arial
- [ ] **Tamaños de letra**: Título 68pt, encabezados 30pt, cuerpo 24–26pt
- [ ] **Boxes contacto alineados**: WhatsApp, Contacto, QR en línea horizontal
- [ ] **Logo RD** (esquina superior izquierda): Visible, 86×86 px, blanco sobre verde
- [ ] **Footer**: `@ REDUCIENDODANO.CL` y `SIGUENOS EN REDES` en posición correcta
- [ ] **Sin overlaps**: Elementos no se solapan, especialmente en footer
- [ ] **Tamaño documento**: 1181×1654 px (10×14 cm a 300dpi)

## Qué NO Hacer

❌ **NO cambiar la paleta de colores** sin aprobación de Brand.
❌ **NO usar fuentes comerciales** no embebidas (Illustrator no las incluirá en SVG).
❌ **NO agregar gradientes complejos** (pueden no renderizar correctamente en web).
❌ **NO usar transparencias** en elementos clave (opacidad máx 95% solo en detalles).
❌ **NO editar el SVG a mano en un editor de texto** (usar Illustrator o comando CLI).
❌ **NO olvidar exportar a SVG** (no PDF, no PNG, solo SVG).
❌ **NO cambiar viewBox** ni tamaño de canvas (mantener 1181×1654).
❌ **NO usar efectos Illustrator avanzados** (blur, shadow nativa) → perderá calidad al exportar SVG.

## Export Final

### Desde Illustrator

1. **File** → **Export As** (Ctrl+Shift+E)
2. **Formato**: SVG
3. **Nombre**: `suplemento_[nombre]_final.svg` (ej. `suplemento_impulso_final.svg`)
4. **SVG Options**:
   - Versión SVG: SVG 1.1
   - Estilos: Internal CSS
   - Decimal places: 2
   - Responsive: ✓ (auto-scale)
5. Guardar en `svg/suplementos_rd/09_contraportadas_dark/[generadas]/`

### Desde CLI

```bash
py -m flujo suplementos contraportada "Impulso" --output svg/suplementos_rd/09_contraportadas_dark/generadas/impulso_final.svg
```

## Integración con Hub / Datadrop

Tras generar la contraportada:

1. Mover SVG a carpeta de entrega (`datadrops/incoming/` o `projects/[proyecto]/outputs/`)
2. Usar `flujo datadrop prepare` para generar manifest con traits (OCR, colores, etc.)
3. En hub, ir a **Datadrop** → Subir archivo → Escanear → Revisar traits

## Troubleshooting

### "El SVG no renderiza correctamente en navegador"
- Verificar que SVG esté en UTF-8
- Abrir en Chrome DevTools → Console para ver errores XML
- Confirmar que no hay referencias a fuentes externas

### "Los colores se ven diferentes en la pantalla"
- Verificar que esté usando valores HEX correctos (copy/paste desde este doc)
- Illustrator puede mostrar RGB ligeramente diferente; exportar y verificar en navegador

### "El texto se ve cortado o deformado"
- Aumentar altura de texto box en Illustrator
- Confirmar que el line-height no esté muy bajo (mínimo 1.2)
- Usar `text-anchor="middle"` si necesitas centrado perfecto en SVG puro

## Próximas Versiones

**v1.1 (Q3 2026)**:
- QR generado automáticamente desde contacto WhatsApp
- Variantes de tamaño (A5, A6, postcard)
- Theme picker (colores alternativos) en CLI

**v1.2 (Q4 2026)**:
- Integración con Google Sheets (pull suplementos desde hoja)
- Batch export (todos los suplementos a la vez)
- Preview en hub antes de descargar

---

## Operación y modificación en Illustrator

Este manual práctico explica cómo trabajar con las contraportadas de suplementos generadas por el sistema **flujo** (formato 10x14 cm) e integrarlas en Illustrator para su revisión final, exportación y envío a imprenta.

---

## 1. Flujo de Trabajo Operativo

El flujo operativo consta de 4 pasos automatizados y asistidos por IA:

```txt
  Intake Hub / CLI ────────> Generación SVG ────────> Script JSX ────────> Imprenta / PDF
(Pedido de Suplemento)     (Base auto-rellenada)     (Mesas de Trabajo)     (Revisión Final)
```

1. **Pedido e Intake:** Al crear un Job para el área de suplementos en el Hub (`py -m flujo app`), el sistema genera automáticamente un archivo SVG base en `jobs/{job_id}/flows/contraportada.svg`.
2. **Personalización (Opcional):** Si necesitas ajustar el texto promocional (el "brief") desde la CLI, puedes regenerar la pieza con:
   ```bash
   py -m flujo suplementos contraportada "Impulso" --brief "Energía ultra limpia sin crash" --output jobs/XXXX/flows/contraportada.svg
   ```
3. **Mapeo a Illustrator:** Ejecuta el generador de paquetes Illustrator para crear un entorno multi-mesa de trabajo:
   ```bash
   py -m flujo suplementos illustrator "Impulso" "Creatina" "Post Fiesta" --project-name "suplementos_revision"
   ```
4. **Edición Vectorial y Cierre:** Se abre el script JSX resultante en Adobe Illustrator, se pule el espaciado tipográfico, y se exporta a PDF/X-1a para producción.

---

## 2. Cómo Modificar en Adobe Illustrator (Quick Guide)

El comando `py -m flujo suplementos illustrator` genera un directorio con la siguiente estructura:
```txt
exports/suplementos_revision_illustrator/suplementos_revision/
  ├── svg/
  │    ├── impulso_final.svg
  │    └── ...
  ├── manifest.json
  ├── README.md
  └── illustrator_artboards.jsx  <-- Abrir con Illustrator
```

### Pasos para cargar el entorno de trabajo:
1. Abre **Adobe Illustrator**.
2. Ve a **Archivo > Scripts > Otras tareas...** (File > Scripts > Other Script...).
3. Selecciona el archivo `illustrator_artboards.jsx`.
4. El script creará un documento de Illustrator nuevo con una mesa de trabajo (Artboard) de **10x14 cm (2362x1654 px @ 300dpi)** por cada suplemento seleccionado, importando los vectores dinámicamente y colocándolos en su posición exacta.

### Ajustes manuales comunes recomendados:
- **Fuentes:** Si el sistema de fuentes DejaVu Sans/Arial se ve distorsionado o deseas usar la tipografía oficial de la línea, selecciona el bloque de texto y cambia la fuente a **Montserrat** o **Inter**.
- **Ajuste de textos de 2 líneas:** Si el beneficio o descripción personalizada es larga y se desplaza hacia abajo cubriendo otros elementos, ajusta el tamaño de la fuente (`T`) o agrega un salto de línea manual.

---

## 3. Exportación Profesional a PDF y PNG

Para garantizar la máxima nitidez en la impresión y visualización digital, sigue estrictamente estas pautas de exportación:

### Exportar PDF para Imprenta (Alta Resolución)
1. Ve a **Archivo > Guardar como...** (Save As...) y selecciona **Adobe PDF (*.PDF)**.
2. En la ventana de configuración del PDF, selecciona el ajuste preestablecido **[Prensa de alta calidad]** (High Quality Print) o **PDF/X-1a:2001** (recomendado para imprentas tradicionales).
3. En la pestaña **Marcas y sangrados** (Marks and Bleeds):
   - Activa **Límite de sangrado del documento** (Use Document Bleed Settings). Asegúrate de que el sangrado esté configurado a **2 mm** por lado.
   - Opcionalmente activa **Marcas de límite** (Trim Marks).
4. Guarda el PDF. El resultado será un archivo de varias páginas (una por suplemento) listo para corte físico.

### Exportar PNG para Redes / Visualización Digital
1. Ve a **Archivo > Exportar > Exportar para pantallas...** (Export for Screens...).
2. Selecciona las mesas de trabajo que deseas exportar.
3. Elige formato **PNG** o **JPEG (100% de calidad)**.
4. Escala la exportación a **300 ppp** (300 dpi) para máxima nitidez de lectura o **1x** para pantallas estándar de WhatsApp/Instagram.

---

## 4. Checklist Pre-Impresión (QA de Calidad)

Antes de enviar cualquier archivo final a imprenta, realiza las siguientes comprobaciones manuales en Illustrator:

- [ ] **Resolución de Imágenes:** Todas las imágenes o logos incrustados deben estar a un mínimo de **300 dpi**.
- [ ] **Modo de Color:** El documento de Illustrator debe estar configurado en **CMYK** para impresión física. (Aunque el SVG se genera en RGB por compatibilidad con visualizadores web, el paso final en Illustrator debe ser convertido a CMYK).
- [ ] **Texto Convertido a Curvas:** Para evitar problemas de fuentes faltantes en la imprenta, selecciona todo el texto (`Ctrl+A`) y presiona `Ctrl+Shift+O` (Texto > Crear contornos / Create Outlines) antes de guardar el PDF final.
- [ ] **Márgenes de Seguridad (Zona Segura):** Ningún texto crítico o logotipo debe estar a menos de **5 mm** del borde de corte físico de la tarjeta (10x14 cm) para evitar que sea rebanado accidentalmente por la guillotina.
- [ ] **Legibilidad del QR:** Escanea el código QR o el texto de contacto de la contraportada directamente desde la pantalla o una prueba impresa en borrador para confirmar que redirecciona correctamente.

---

## 5. Dónde Guardar Versiones Finales

Mantén la higiene del repositorio guardando los archivos ordenados según su etapa:

- **Artefactos Crudos / Automáticos:** Guardar en `jobs/{job_id}/flows/` (ej. `contraportada.svg`, `illustrator_package/`). No los subas a producción hasta estar revisados.
- **Exportaciones PDF/PNG Finales Aprobadas:** Guardar en `jobs/{job_id}/exports/` (crear carpeta si no existe). Ejemplo:
  - `jobs/2026-06-28_magnesio/exports/01_magnesio_contraportada_corte.pdf`
- **Registro en Historial Visual (Datadrops):** Cuando una pieza sea impresa físicamente o publicada en redes, tómale una foto o captura del PNG final y súbela como **Datadrop** a través de la sección correspondiente en el Hub (`py -m flujo app`). Esto entrenará a la IA del sistema para mantener la coherencia en futuros pedidos.
