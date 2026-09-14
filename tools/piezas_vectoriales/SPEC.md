# Tool: piezas_vectoriales

Sistema para generar **archivos gráficos de impresión** desde JSON: flyers, etiquetas, stickers, tarjetas u otros formatos rectangulares.

La herramienta separa:

```txt
brief/correo → config JSON → SVG editable → SVG vectorizado → ZIP/export
```

## Cuándo usar

Usar esta herramienta cuando el usuario pida:

- etiquetas,
- flyers de impresión,
- stickers,
- piezas con medidas específicas,
- archivos para Illustrator,
- letras vectorizadas/convertidas a curvas,
- SVG editable + SVG final,
- flujo desde correo del jefe o brief rápido.

## Script principal genérico

```bash
python3 tools/piezas_vectoriales/scripts/generar_desde_json.py projects/piezas_vectoriales/NOMBRE_PROYECTO/config.json
```

En Windows también puede usarse:

```bash
py tools/piezas_vectoriales/scripts/generar_desde_json.py projects/piezas_vectoriales/NOMBRE_PROYECTO/config.json
```

## Proyecto ejemplo

```txt
projects/piezas_vectoriales/etiquetas_ejemplo/config.json
```

Generar ejemplo:

```bash
python3 tools/piezas_vectoriales/scripts/generar_desde_json.py projects/piezas_vectoriales/etiquetas_ejemplo/config.json
```

## Proyecto real incluido: Suplementos RD

```txt
projects/piezas_vectoriales/suplementos_rd/
├── 01_contenido/contenido_suplementos_rd.json
├── scripts/generar_flyers.py
└── README_FLUJO_OPTIMIZADO.md
```

Generar Suplementos RD:

```bash
cd projects/piezas_vectoriales/suplementos_rd
python3 scripts/generar_flyers.py
```

Salidas esperadas:

```txt
02_editables_svg/
03_final_vectorizado_svg/
04_preview/
05_exports/
```

## Plantillas

```txt
tools/piezas_vectoriales/plantillas/etiqueta_horizontal_2800x2000.config.json
tools/piezas_vectoriales/plantillas/flyer_horizontal_minimo.config.json
```

Para crear un proyecto nuevo:

1. Crear carpeta:

```txt
projects/piezas_vectoriales/mi_proyecto/
```

2. Copiar una plantilla como:

```txt
projects/piezas_vectoriales/mi_proyecto/config.json
```

3. Editar:

- `canvas.width`,
- `canvas.height`,
- `real_size_cm`,
- `palette`,
- `global_elements`,
- `documents`.

4. Ejecutar generador.

## Validación

Ejecutar:

```bash
python3 scripts/piezas_check_outputs.py
```

El chequeo valida:

- JSONs válidos,
- ZIPs generados,
- que los vectorizados no contengan `<text>`.

## Reglas para IA

1. No editar SVG generado si el cambio corresponde a contenido o estructura; editar JSON/config y regenerar.
2. No inventar textos legales, sanitarios o claims nutricionales.
3. Si falta medida, sangrado, formato final o texto exacto, preguntar máximo 3 cosas.
4. Entregar rutas finales de:
   - SVG editable,
   - SVG vectorizado,
   - ZIP editable,
   - ZIP vectorizado,
   - preview.
5. Mantener outputs pesados fuera de git si están ignorados.

## Referencias de etiquetas

Se agregó una referencia documentada:

```txt
docs/REFERENCIA_ETIQUETAS_RELIEVE.md
```

Y una plantilla proporcional:

```txt
tools/piezas_vectoriales/plantillas/etiqueta_horizontal_165x65.config.json
```

Para inspeccionar PDFs de referencia:

```bash
py scripts/pdf_probe_basic.py "ruta/archivo.pdf"
```

## Componentes reutilizables

```txt
tools/piezas_vectoriales/components/
```

Componentes iniciales:

- logo/marca
- footer web
- QR placeholder
- lote/vencimiento
- tabla info básica

Copiar sus objetos JSON dentro de `global_elements` o `documents[].elements`.

## Scripts auxiliares nuevos

Insertar componente:

```bash
py scripts/piezas_add_component.py "projects/piezas_vectoriales/MI_PROYECTO/config.json" qr_placeholder.json doc
```

Validar configs:

```bash
py scripts/piezas_validate_config.py
```

Resumen de proyectos:

```bash
py scripts/piezas_project_summary.py
```
