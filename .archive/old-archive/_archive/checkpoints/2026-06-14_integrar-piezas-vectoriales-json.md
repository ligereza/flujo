# Checkpoint — integrar piezas_vectoriales_json

Fecha: 2026-06-14

## Cambio

Se integró al repo `flujo` un sistema para generar archivos de impresión desde JSON.

## Nuevos elementos

- `AGENTS.md`: instrucciones rápidas para agentes IA.
- `tools/piezas_vectoriales/`: herramienta genérica para piezas vectoriales.
- `projects/piezas_vectoriales/etiquetas_ejemplo/config.json`: proyecto ejemplo.
- `projects/piezas_vectoriales/suplementos_rd/`: proyecto real de flyers Suplementos RD.
- `briefs/PROMPT_PARA_OTRA_IA_ARCHIVOS_IMPRESION.md`: prompt para trabajar desde correos.
- `scripts/piezas_generar.py`: wrapper para generar desde config JSON.
- `scripts/piezas_check_outputs.py`: validador de outputs.

## Flujo

```txt
brief/correo → config JSON → SVG editable → SVG vectorizado → ZIP/export
```

## Validación recomendada

```bash
py scripts/piezas_check_outputs.py
```
