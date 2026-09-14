# json/

Aquí viven los **archivos JSON descriptivos** de los trabajos de ejemplo.

## Estructura

- Cada ejemplo en `../ejemplos/<carpeta-ejemplo>/` debe tener su contraparte aquí:
  - `json/<carpeta-ejemplo>.json`   (recomendado)
  - o `json/<carpeta-ejemplo>/descripcion.json` + archivos adicionales si hace falta

## Propósito

Estos JSONs son la representación estructurada de la estética real de los trabajos terminados. Sirven para:

- Extraer y refinar la línea editorial (flujo.json, linea_editorial.md)
- Entrenar / guiar a futuros agentes
- Validar que nuevas piezas generadas respeten la identidad
- Referencia para el sistema (futuro: `flujo` podrá leer estos descriptores)

## Qué debe contener un JSON descriptivo

Mínimo recomendado (ver schema si existe):

```json
{
  "example_id": "2026-06-20_etiqueta-miel",
  "source_paths": ["../ejemplos/2026-06-20_etiqueta-miel/"],
  "aesthetic_summary": "...",
  "colors": [ ... ],
  "typography": { ... },
  "layout": { ... },
  "motifs": [ ... ],
  "composition_rules": "...",
  "tone_visual": "...",
  "tags": []
}
```

## Para agentes de IA

Si entras a este repo para trabajar en flujo:
- Ve primero a `../ejemplos/`
- Analiza los trabajos reales (imágenes, configs, SVGs, etc.)
- Genera o actualiza los JSONs aquí.
- Actualiza también `../flujo.json` y `../linea_editorial.md` cuando tengas suficiente información.

Si ya existen JSONs en esta carpeta, úsalos como fuente primaria en vez de re-analizar desde cero.

## Mantenimiento

- Mantén los nombres consistentes con las carpetas de ejemplos.
- Versiónalos cuando la descripción mejore significativamente.
- No guardes archivos pesados aquí (imágenes van en ejemplos/).
