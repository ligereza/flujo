# Contraportadas Suplementos RD — Guía Operativa

## Descripción General

Las **contraportadas** (10×14 cm) son tarjetas de presentación diseñadas para acompañar suplementos de Reduciendo Daño. Cada una cuenta la historia del producto, sus beneficios, instrucciones de uso y contacto directo.

## Estructura de Archivos

```
svg/suplementos_rd/04_contraportadas/
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

1. Abrir `svg/suplementos_rd/04_contraportadas/01_contraportada_base_10x14cm.svg` en Adobe Illustrator
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
5. Guardar en `svg/suplementos_rd/04_contraportadas/[generadas]/`

### Desde CLI

```bash
py -m flujo suplementos contraportada "Impulso" --output svg/suplementos_rd/04_contraportadas/generadas/impulso_final.svg
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

