# ejemplos/

Esta carpeta es el lugar donde **cargas trabajos ya hechos** (piezas terminadas, flyers, etiquetas, renders, etc.) para que un agente de IA analice la estética real.

## Cómo usarla

1. Crea una subcarpeta por cada ejemplo (recomendado: fecha + slug corto, ej. `2026-06-20_etiqueta-miel` o `flyer-evento-xyz`).
2. Dentro de cada subcarpeta pon:
   - Los archivos originales o generados (PDF, SVG, PNG, JPG, config.json, manifest.json, etc.)
   - Cualquier referencia (capturas, briefs, fotos de referencia)
3. El agente que entre al repo debe:
   - Explorar esta carpeta
   - Analizar los trabajos
   - Generar (o actualizar) JSON descriptivos en la carpeta hermana `../json/`

## Reglas

- No borres trabajos reales solo porque están aquí.
- Mantén los nombres descriptivos.
- Si un ejemplo ya tiene su JSON descriptivo, ponlo en `../json/<nombre-del-ejemplo>.json` (o subcarpeta).

## Para el agente de IA

Tu tarea cuando veas esta carpeta:
- Lee todos los archivos dentro de cada subcarpeta de ejemplo.
- Extrae información estética (colores exactos si es posible, tipografía, composición, motivos, densidad, tono visual).
- Genera un JSON estructurado en `projects/flujo/json/`.
- Usa el schema `schemas/example_description.schema.json`.
- Sigue las instrucciones en `../json/README.md`.

Esta carpeta + la carpeta `json/` es la forma principal de "alimentar" el proyecto flujo con trabajo real para definir la línea editorial.
