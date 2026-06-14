# Sistema genérico para flyers, etiquetas y otros formatos

Este sistema sirve para no tener que adaptar pieza por pieza manualmente. La idea es separar:

1. **Contenido y medidas** en un JSON.
2. **Generación automática** desde un script.
3. **SVG editable** para Illustrator.
4. **SVG vectorizado** para entrega final o imprenta.

---

## Estructura

```txt
00_sistema_generico/
├── README_SISTEMA_FORMATOS.md
├── scripts/
│   └── generar_desde_json.py
├── plantillas/
└── proyectos/
    └── etiquetas_ejemplo/
        ├── config.json
        └── salida_generada/
            ├── 01_editables_svg/
            ├── 02_vectorizados_svg/
            ├── 03_preview/
            └── 04_exports/
```

---

## Cómo empezar un formato nuevo

### 1. Duplica una carpeta de proyecto

Por ejemplo, copia:

```txt
00_sistema_generico/proyectos/etiquetas_ejemplo/
```

y renómbrala como:

```txt
00_sistema_generico/proyectos/etiquetas_magnesio/
```

Dentro deja/modifica solo:

```txt
config.json
```

La carpeta `salida_generada/` se puede borrar, porque el script la vuelve a crear.

---

## 2. Cambia las medidas del formato

En `config.json`, busca:

```json
"canvas": {
  "width": 2800,
  "height": 2000,
  "real_size_cm": { "width": 14, "height": 10 },
  "safe_margin_px": 120
}
```

Ejemplos:

### Etiqueta horizontal 14 × 10 cm

```json
"canvas": {
  "width": 2800,
  "height": 2000,
  "real_size_cm": { "width": 14, "height": 10 },
  "safe_margin_px": 120
}
```

### Etiqueta cuadrada

```json
"canvas": {
  "width": 2000,
  "height": 2000,
  "real_size_cm": { "width": 10, "height": 10 },
  "safe_margin_px": 120
}
```

### Etiqueta vertical

```json
"canvas": {
  "width": 2000,
  "height": 2800,
  "real_size_cm": { "width": 10, "height": 14 },
  "safe_margin_px": 120
}
```

La proporción real la defines con `width` y `height`. Si después se imprime a 14 × 10 cm, Illustrator puede escalarlo sin perder calidad porque es vectorial.

---

## 3. Cambia colores globales

En `palette` defines colores reutilizables:

```json
"palette": {
  "cream": "#F6EFE3",
  "ink": "#161513",
  "green": "#173F2F",
  "orange": "#EF7B2D"
}
```

Luego los puedes usar por nombre:

```json
{ "type": "rect", "fill": "green" }
```

O directamente como hexadecimal:

```json
{ "type": "rect", "fill": "#FF0000" }
```

---

## 4. Elementos globales

`global_elements` son elementos que aparecen en todas las piezas del proyecto:

- Fondo decorativo.
- Logo.
- Marco.
- Web.
- Footer.
- Guías visuales.

Ejemplo:

```json
"global_elements": [
  { "type": "rect", "x": 120, "y": 120, "w": 88, "h": 88, "radius": 26, "fill": "green" },
  { "type": "text", "content": "RD", "x": 139, "y": 135, "size": 42, "fill": "white", "weight": "bold" }
]
```

Si algo debe aparecer en todas las etiquetas, va aquí.

---

## 5. Crear documentos/piezas

Cada pieza va dentro de:

```json
"documents": [
  {
    "id": "01_etiqueta_impulso",
    "title": "IMPULSO",
    "elements": []
  }
]
```

El `id` define el nombre del archivo generado.

Ejemplo:

```json
"id": "01_etiqueta_impulso"
```

Generará:

```txt
01_etiqueta_impulso_editable.svg
01_etiqueta_impulso_vectorizado.svg
```

---

# Tipos de elementos disponibles

## Rectángulo

```json
{
  "type": "rect",
  "x": 120,
  "y": 120,
  "w": 500,
  "h": 300,
  "radius": 40,
  "fill": "white",
  "stroke": "line",
  "stroke_width": 3,
  "opacity": 0.7
}
```

## Panel

Es igual que `rect`, pero semánticamente sirve para cajas de contenido:

```json
{
  "type": "panel",
  "x": 125,
  "y": 760,
  "w": 1180,
  "h": 650,
  "radius": 48,
  "fill": "white",
  "stroke": "line",
  "stroke_width": 3,
  "opacity": 0.68
}
```

## Círculo

```json
{
  "type": "circle",
  "cx": 180,
  "cy": 160,
  "r": 360,
  "fill": "orange",
  "opacity": 0.12
}
```

## Línea

```json
{
  "type": "line",
  "x1": 120,
  "y1": 1745,
  "x2": 2680,
  "y2": 1745,
  "stroke": "line",
  "stroke_width": 5
}
```

## Texto corto

```json
{
  "type": "text",
  "content": "IMPULSO",
  "x": 120,
  "y": 360,
  "size": 190,
  "fill": "ink",
  "weight": "bold"
}
```

## Párrafo con ancho máximo

```json
{
  "type": "paragraph",
  "content": "Fórmula diseñada para momentos de alta demanda cognitiva.",
  "x": 195,
  "y": 840,
  "size": 48,
  "fill": "ink",
  "max_width": 1040,
  "line_height": 66
}
```

## Lista con bullets

```json
{
  "type": "list",
  "x": 195,
  "y": 1090,
  "size": 36,
  "fill": "muted",
  "max_width": 1020,
  "line_height": 48,
  "indent": 42,
  "gap": 18,
  "items": [
    "Ingrediente o activo 1.",
    "Ingrediente o activo 2.",
    "Ingrediente o activo 3."
  ]
}
```

---

# Regenerar archivos

Desde la raíz del workspace ejecuta:

```bash
python3 00_sistema_generico/scripts/generar_desde_json.py 00_sistema_generico/proyectos/etiquetas_ejemplo/config.json
```

Si duplicaste el proyecto:

```bash
python3 00_sistema_generico/scripts/generar_desde_json.py 00_sistema_generico/proyectos/mi_nuevo_proyecto/config.json
```

---

# Qué genera

Dentro de tu proyecto se crea:

```txt
salida_generada/
├── 01_editables_svg/
├── 02_vectorizados_svg/
├── 03_preview/
└── 04_exports/
```

## `01_editables_svg/`

Textos vivos/editables. Abre estos archivos en Illustrator para trabajar.

## `02_vectorizados_svg/`

Textos convertidos a trazados. Úsalos para entrega final o imprenta.

## `03_preview/preview.html`

Vista rápida de todas las piezas.

## `04_exports/`

ZIPs listos para compartir.

---

# Recomendación de flujo profesional

```txt
config.json
  ↓
Generar SVG editables
  ↓
Abrir en Illustrator
  ↓
Ajustar diseño/color/fondo
  ↓
Guardar .AI editable
  ↓
Duplicar archivo final
  ↓
Convertir textos a contornos
  ↓
Exportar PDF/SVG final
```

---

# Cómo continuar en otro chat

Si necesitas continuar en otro chat, comparte este resumen:

> Tengo un workspace con un sistema genérico en `00_sistema_generico/`. El archivo principal es `scripts/generar_desde_json.py`. Cada proyecto tiene un `config.json` con canvas, palette, global_elements y documents. El script genera SVG editables y SVG vectorizados en `salida_generada/`. Quiero crear/adaptar un nuevo formato manteniendo este flujo.

También puedes adjuntar:

```txt
00_sistema_generico/README_SISTEMA_FORMATOS.md
00_sistema_generico/proyectos/etiquetas_ejemplo/config.json
```

---

# Limitaciones actuales

- El sistema genera formatos rectangulares con posiciones absolutas.
- No reemplaza Illustrator para ajustes finos.
- La versión vectorizada convierte texto a trazados, pero deja fondos y formas editables.
- Si cambias mucho el tamaño del canvas, probablemente tendrás que ajustar posiciones `x`, `y`, `w`, `h`.

---

# Próximas mejoras posibles

1. Crear plantillas prearmadas para:
   - etiqueta frontal,
   - etiqueta trasera,
   - flyer horizontal,
   - flyer vertical,
   - carrusel Instagram.
2. Agregar soporte para sangrado y área segura automáticos.
3. Agregar grilla visible opcional.
4. Agregar export PDF automático si el entorno tiene herramientas disponibles.
5. Agregar componentes reutilizables: logo, footer, tabla nutricional, QR, código de barras.
